"""
"Arrangia il brano": dalle sezioni della traccia degli accordi (i suoi box:
Intro, Strofa, Pre-ritornello, Ritornello, Ponte, Finale...) tutte le parti
in un passaggio, una sezione alla volta:

- l'intensita' di ogni sezione viene dal suo nome (SECTION_INTENSITY: la
  strofa leggera, il pre-ritornello in crescendo, il ritornello pieno...),
  modificabile prima di generare;
- batteria con un fill completo alla fine di ogni sezione (salvo l'ultima,
  che chiude con il colpo finale); un'intro suona senza batteria ne' basso;
- basso e accompagnamento sugli accordi di quella sezione; nell'ultima
  battuta del brano una nota lunga e un accordo tenuto, con il rallentando
  (marcatori tempo= che scendono) se richiesto;
- un box "Stop" fa tacere tutte le parti, un "Break" lascia un solo colpo
  d'insieme sul primo tempo;
- la dinamica sale lungo ogni frase di quattro battute, con un accento in
  piu' sull'ingresso del ritornello;
- l'accompagnamento si dirada nelle battute in cui la melodia e' fitta;
- l'ultimo ritornello (e quel che segue) puo' salire di uno o due semitoni:
  si traspongono anche i box degli accordi;
- ogni parte e' un box per sezione, allineato al box degli accordi, con lo
  stesso nome: si possono rigenerare o modificare uno per uno.
"""

import math
import re
from dataclasses import dataclass, replace
from fractions import Fraction
from typing import Dict, List, Optional, Tuple

from .i18n import tr
from .model import Clip, Project, Track

# Parole del nome di un box -> intensita' (core.rhythm_generate.INTENSITIES,
# piu' 'intro', 'outro', 'stop' e 'break'). La prima che compare nel nome
# vale; il resto e' "normal".
SECTION_INTENSITY = [
    (("stop", "stacco"), "stop"),
    (("break",), "break"),
    (("intro", "introduzione", "inizio"), "intro"),
    (("pre-ritornello", "preritornello", "pre ritornello", "pre-rit", "pre-chorus", "prechorus",
      "pre chorus", "bridge", "ponte", "build"), "build"),
    (("ritornello", "rit", "chorus", "refrain", "climax", "finale pieno"), "full"),
    (("strofa", "verse", "couplet", "estrofa"), "light"),
    (("outro", "coda", "finale", "fine", "ending"), "outro"),
    (("assolo", "solo", "special", "interludio", "interlude"), "normal"),
]

# Sezioni senza il loro disegno: tutti tacciono ('stop') o un solo colpo
# d'insieme sul primo tempo ('break').
PAUSES = ("stop", "break")


def section_intensity(name: str) -> str:
    """L'intensita' di una sezione dal suo nome: 'intro', 'light', 'normal',
    'build', 'full', 'outro', 'stop' o 'break'."""
    lower = name.lower()
    for words, level in SECTION_INTENSITY:
        for word in words:
            if re.search(rf"(^|[^a-z]){re.escape(word)}([^a-z]|$)", lower):
                return level
    return "normal"


@dataclass
class Section:
    name: str
    start_beat: float
    length_beats: float
    text: str
    intensity: str


def song_sections(project: Project, chord_track: Track) -> List[Section]:
    """Le sezioni del brano: i box della traccia degli accordi, in ordine."""
    from .arrangement import clip_duration_beats
    out = []
    for clip in sorted(chord_track.clips, key=lambda c: c.start_beat):
        length = clip_duration_beats(clip.text, project.patterns, chord_track.instrument.default_octave,
                                     start_beat=clip.start_beat, meter=project.meter())
        if length > 0:
            out.append(Section(clip.name, clip.start_beat, length, clip.text, section_intensity(clip.name)))
    return out


@dataclass
class ArrangeOptions:
    drum_style: Optional[str] = "rock"
    bass_style: Optional[str] = "root"
    comping_style: Optional[str] = "block_chords"
    comping_instrument: str = "Piano"
    bass_instrument: str = "Bass"
    variability: float = 0.3
    seed: Optional[int] = None
    ending: bool = True             # ultima battuta: nota lunga del basso, accordo tenuto
    rallentando: bool = True        # e il tempo che scende nelle ultime battute
    phrase_dynamics: bool = True    # crescendo di frase, accento sull'ingresso del ritornello
    melody_track: Optional[str] = None   # l'accompagnamento si dirada dove questa melodia e' fitta
    modulation: int = 0             # semitoni dell'ultimo ritornello (e di quel che segue)


def _level(intensity: str) -> str:
    return {"intro": "light", "outro": "light"}.get(intensity, intensity)


# ---------------------------------------------------------------------------
# Testi generati come elenco di attacchi (vedi rhythm_generate._generated_timeline)
# ---------------------------------------------------------------------------

DEFAULT_VELOCITY = 80        # quella della notazione senza 'N@'
RALLENTANDO_RATIO = 0.75     # il tempo finale del rallentando, rispetto a quello in vigore
PHRASE_BARS = 4              # battute di una frase per il crescendo
PHRASE_STEPS = (-6, -2, 2, 6)   # velocity in piu' battuta per battuta lungo la frase
CHORUS_ACCENT = 12           # in piu' sul primo attacco di un ritornello
DENSE_PER_BEAT = 1.5         # attacchi della melodia per beat da cui l'accompagnamento si dirada

_TOKEN = re.compile(r"(\d*)(.*)", re.S)


@dataclass
class _Item:
    start: Fraction
    end: Fraction
    body: str                 # il token senza moltiplicatore ('r' = pausa)
    velocity: Optional[int]

    @property
    def rest(self) -> bool:
        return self.body == "r"


def _parse(text: str) -> Tuple[str, Fraction, List[_Item]]:
    from .rhythm_generate import _generated_timeline
    grid, raw = _generated_timeline(text)
    m = re.match(r"(\d+)(T?):", grid)
    unit = Fraction(4, int(m.group(1))) * (Fraction(2, 3) if m.group(2) else 1)
    items = [_Item(s, e, _TOKEN.fullmatch(tok).group(2), vel) for s, e, tok, vel in raw]
    return grid, unit, items


def _emit(grid: str, unit: Fraction, items: List[_Item], markers=()) -> str:
    """Il testo degli attacchi; 'markers' = [(beat, token)] da scrivere prima
    del primo attacco che comincia da quel beat (es. 'tempo=90')."""
    tokens, current = [grid], None
    pending = sorted(markers, key=lambda m: m[0])
    for item in items:
        due = []
        while pending and pending[0][0] <= item.start:
            due.append(pending.pop(0)[1])
        if due:
            tokens.append(due[-1])        # piu' marcatori dentro lo stesso attacco: vale l'ultimo
        if not item.rest and item.velocity is not None and item.velocity != current:
            tokens.append(f"{item.velocity}@")
            current = item.velocity
        mult = (item.end - item.start) / unit
        assert mult.denominator == 1, (item, unit)
        tokens.append((f"{mult.numerator}" if mult > 1 else "") + item.body)
    if pending:
        tokens.append(pending[-1][1])
    return " ".join(tokens)


def _cut(items: List[_Item], at: Fraction) -> List[_Item]:
    """Gli attacchi prima di 'at'; quello che lo attraversa si accorcia."""
    out = []
    for item in items:
        if item.start >= at:
            break
        out.append(replace(item, end=min(item.end, at)))
    return out


def _hold_last_bar(text: str, bar_start: float, body: Optional[str] = None) -> str:
    """L'ultima battuta (da 'bar_start') diventa una sola nota o un solo
    accordo tenuto fino alla fine: 'body' (es. 'C*2'), o l'accordo che la
    linea suona su quella battuta (il primo dopo il suo inizio, se no
    l'ultimo prima), con la sua velocity."""
    grid, unit, items = _parse(text)
    at = Fraction(bar_start).limit_denominator(64)
    total = items[-1].end if items else at
    if not items or at >= total or (at / unit).denominator != 1:
        return text
    sounding = [i for i in items if not i.rest]
    if not sounding:
        return text
    source = next((i for i in sounding if i.start >= at), sounding[-1])
    head = _cut(items, at)
    head.append(_Item(at, total, body or source.body, source.velocity))
    return _emit(grid, unit, head)


def _first_hit_only(text: str, hit_beats: float = 1.0) -> Optional[str]:
    """Break: resta solo l'attacco sul primo tempo (al massimo 'hit_beats'
    beat), poi pausa fino alla fine; None se la linea non suona sul primo
    tempo."""
    grid, unit, items = _parse(text)
    if not items or items[0].rest:
        return None
    first, total = items[0], items[-1].end
    end = min(first.end, first.start + Fraction(hit_beats).limit_denominator(64))
    end = first.start + unit * max(1, math.floor((end - first.start) / unit))
    out = [replace(first, end=end)]
    if end < total:
        out.append(_Item(end, total, "r", None))
    return _emit(grid, unit, out)


def _break_drums(length_beats: float) -> str:
    """Batteria del break: piatto e cassa sul primo tempo, poi silenzio."""
    slots = max(1, round(length_beats * 4))
    return "16: 110@ [crash kick]" + (f" {slots - 1}r" if slots > 2 else " r" if slots == 2 else "")


def _phrase_dynamics(text: str, bar_beats: float, chorus_entry: bool) -> str:
    """Crescendo di frase: la velocity sale battuta per battuta lungo ogni
    frase di PHRASE_BARS battute (PHRASE_STEPS); con 'chorus_entry' il primo
    attacco ha CHORUS_ACCENT in piu'."""
    grid, unit, items = _parse(text)
    bar = Fraction(bar_beats).limit_denominator(64)
    first = next((i for i in items if not i.rest), None)
    out = []
    for item in items:
        if item.rest:
            out.append(item)
            continue
        step = PHRASE_STEPS[int(item.start // bar) % PHRASE_BARS]
        if chorus_entry and item is first and item.start < 1:
            step += CHORUS_ACCENT
        base = item.velocity if item.velocity is not None else DEFAULT_VELOCITY
        out.append(replace(item, velocity=max(1, min(127, base + step))))
    return _emit(grid, unit, out)


def _thin_where_busy(text: str, busy_bars, bar_beats: float) -> str:
    """Nelle battute 'busy_bars' (da 0) restano solo gli attacchi sul primo
    tempo e a meta' battuta (sul 1 e sul 3 in 4/4): gli altri allungano
    l'attacco che li precede, cosi' l'accompagnamento lascia spazio alla
    melodia."""
    if not busy_bars:
        return text
    grid, unit, items = _parse(text)
    bar = Fraction(bar_beats).limit_denominator(64)
    strong = bar / 2 if bar % 2 == 0 else bar     # in 3/4 e simili solo il primo tempo
    out: List[_Item] = []
    for item in items:
        pos = item.start % bar
        if out and int(item.start // bar) in busy_bars and pos % strong != 0:
            out[-1] = replace(out[-1], end=item.end)
            continue
        if out and item.rest and out[-1].rest:
            out[-1] = replace(out[-1], end=item.end)
            continue
        out.append(item)
    return _emit(grid, unit, out)


def _with_rallentando(text: str, from_beat: float, to_beat: float, tempo: float) -> str:
    """Rallentando: dopo 'from_beat' un marcatore 'tempo=' per beat, che scende
    da 'tempo' fino a tempo * RALLENTANDO_RATIO su 'to_beat' (beat
    dall'inizio del box). Scalini e non una rampa '<<': dentro una rampa di
    tempo non si possono cambiare le velocity."""
    grid, unit, items = _parse(text)
    steps = max(1, int(round(to_beat - from_beat)))
    slow = tempo * RALLENTANDO_RATIO
    markers = []
    for i in range(1, steps + 1):
        value = round((tempo - (tempo - slow) * i / steps) * 10) / 10
        markers.append((Fraction(from_beat + (to_beat - from_beat) * i / steps).limit_denominator(64),
                        f"tempo={value:g}"))
    return _emit(grid, unit, items, markers)


# ---------------------------------------------------------------------------
# Melodia, tempo e modulazione
# ---------------------------------------------------------------------------

def melody_attacks(project: Project, track: Track) -> List[float]:
    """Gli attacchi (in beat) di una traccia di note: dove la melodia e' fitta."""
    kinds = ("note", "chord", "block", "slide")
    return sorted({round(ev.start, 6) for ev in track.parsed_events(project.patterns, meter=project.meter())
                   if ev.kind in kinds})


def busy_bars(attacks: List[float], start_beat: float, length_beats: float, bar_beats: float) -> set:
    """Le battute (da 0) della sezione in cui la melodia ha almeno
    DENSE_PER_BEAT attacchi per beat."""
    counts: Dict[int, int] = {}
    for beat in attacks:
        if start_beat - 1e-9 <= beat < start_beat + length_beats - 1e-9:
            idx = int((beat - start_beat + 1e-9) // bar_beats)
            counts[idx] = counts.get(idx, 0) + 1
    return {idx for idx, n in counts.items() if n >= DENSE_PER_BEAT * bar_beats}


def _tempo_at(project: Project, beat: float) -> float:
    try:
        from .tempo_map import build_tempo_beat_map, value_at_beat
        return float(value_at_beat(build_tempo_beat_map(project), beat) or project.tempo_bpm)
    except Exception:
        return float(project.tempo_bpm)


def modulated_from(sections: List[Section]) -> Optional[int]:
    """L'indice dell'ultimo ritornello (intensita' 'full'), da cui parte la
    modulazione, o None."""
    return next((k for k in range(len(sections) - 1, -1, -1) if sections[k].intensity == "full"), None)


def transpose_text(text: str, semitones: int, default_octave: int = 4) -> str:
    from .notation import PitchRewriter, rewrite_tokens
    return rewrite_tokens(text, PitchRewriter(semitones, default_octave))


# ---------------------------------------------------------------------------
# Arrangia
# ---------------------------------------------------------------------------

def arrange(project: Project, sections: List[Section], options: ArrangeOptions,
            bar_beats: float, chord_octave: int = 4) -> Dict[str, List[Clip]]:
    """{"drums"/"bass"/"comping": [box, uno per sezione]} delle parti scelte
    (uno stile None = quella parte non si genera), e con la modulazione
    {"chords": [i box degli accordi trasposti]} da mettere al posto di
    quelli con lo stesso inizio. Solleva ValueError se le sezioni non hanno
    accordi."""
    from .instruments import get_instrument
    from .rhythm_generate import (_expand_chords_to_cover, _note_token, extract_chords_from_track,
                                  generate_bass_from_chords, generate_drum_pattern, generate_melodic_line)
    parts: Dict[str, List[Clip]] = {"drums": [], "bass": [], "comping": []}
    comp = get_instrument(options.comping_instrument)
    melody = project.find_track(options.melody_track)
    attacks = melody_attacks(project, melody) if melody is not None and not melody.is_audio else []
    playing = [k for k, s in enumerate(sections) if s.intensity not in PAUSES]
    last_index = playing[-1] if playing else -1
    modulate_at = modulated_from(sections) if options.modulation else None
    if modulate_at is not None:
        parts["chords"] = []
    previous_chords = []
    for k, section in enumerate(sections):
        if modulate_at is not None and k >= modulate_at:
            section = replace(section, text=transpose_text(section.text, options.modulation, chord_octave))
            parts["chords"].append(Clip(section.name, section.text, section.start_beat))
        if section.intensity == "stop":
            continue
        last = k == last_index
        pause = section.intensity == "break"
        level = "full" if pause else _level(section.intensity)
        seed = None if options.seed is None else options.seed + k
        chords = extract_chords_from_track(section.text, project.patterns)
        if not chords and pause and previous_chords:
            # un break senza accordi: il colpo d'insieme sull'ultimo accordo suonato
            chords = [previous_chords[-1]._replace(start_beat=0.0, duration_beats=section.length_beats)]
        previous_chords = chords or previous_chords
        bars = max(1, math.ceil(section.length_beats / bar_beats - 1e-6))
        ending_bar = (bars - 1) * bar_beats
        chorus_entry = section.intensity == "full" and (k == 0 or sections[k - 1].intensity != "full")
        texts: Dict[str, str] = {}
        if options.drum_style and section.intensity != "intro":
            if pause:
                texts["drums"] = _break_drums(section.length_beats)
            else:
                texts["drums"] = generate_drum_pattern(
                    options.drum_style, bars, fill_every=0, variability=options.variability, seed=seed,
                    intensity=level, phrase_fills=True, ending=last and bars > 1,
                    section_fill_bars=[] if last else [bars - 1])
        if chords and options.bass_style and section.intensity != "intro":
            text = generate_bass_from_chords(chords, options.bass_style, octave=2,
                                             min_total_beats=section.length_beats, variability=options.variability,
                                             seed=seed, bar_beats=bar_beats, intensity=level)
            if pause:
                text = _first_hit_only(text)
            elif last and options.ending:
                spans = _expand_chords_to_cover(chords, section.length_beats)
                final = next((s for s in reversed(spans) if s.start_beat <= ending_bar + 1e-9), spans[-1])
                text = _hold_last_bar(text, ending_bar, _note_token(final.root_pc, 2))
            if text:
                texts["bass"] = text
        if chords and options.comping_style:
            text = generate_melodic_line(chords, options.comping_style, comp.default_octave, comp.range_low,
                                         comp.range_high, True, min_total_beats=section.length_beats,
                                         variability=options.variability, seed=seed, bar_beats=bar_beats,
                                         intensity=level, voice_leading=True)
            if pause:
                text = _first_hit_only(text)
            else:
                text = _thin_where_busy(text, busy_bars(attacks, section.start_beat, section.length_beats,
                                                        bar_beats), bar_beats)
                if last and options.ending:
                    text = _hold_last_bar(text, ending_bar)
            if text:
                texts["comping"] = text
        if options.phrase_dynamics and not pause:
            texts = {kind: _phrase_dynamics(text, bar_beats, chorus_entry) for kind, text in texts.items()}
        if last and options.ending and options.rallentando and bars > 1 and texts:
            kind = next(kind for kind in ("drums", "bass", "comping") if kind in texts)
            rit_bars = 2 if bars >= 3 else 1
            texts[kind] = _with_rallentando(texts[kind], ending_bar - rit_bars * bar_beats, ending_bar,
                                            _tempo_at(project, section.start_beat + ending_bar - rit_bars * bar_beats))
        for kind, text in texts.items():
            parts[kind].append(Clip(section.name, text, section.start_beat))
    if not any(parts[kind] for kind in ("drums", "bass", "comping")):
        raise ValueError(tr("Nelle sezioni della traccia non ci sono accordi da arrangiare."))
    return parts
