"""
"Salva come stile" (sezione "E" della proposta): ricava da un box, da una
traccia o da un canale di un file MIDI un nuovo modello per i generatori di
core.rhythm_generate, da salvare fra gli stili personali (core.user_styles).

- Batteria: le battute vengono messe sulla griglia (sedicesimi, terzine o
  ottavi); la piu' frequente diventa il giro base, le altre diverse i giri
  alternativi, quella con i tom il fill.
- Basso, accompagnamento, riff: ogni nota diventa un grado dell'accordo che
  suona in quel momento (fondamentale, terza, quinta... nella sua ottava),
  cosi' il disegno si adatta a qualunque giro di accordi, con la terza e la
  settima giuste. Gli accordi vengono da un'altra traccia (o dallo stesso
  file MIDI); senza, la prima nota di ogni battuta fa da fondamentale.
"""

from collections import Counter
from typing import Dict, List, Optional, Tuple

from .chords import midi_note, note_name_to_pc, parse_chord_symbol
from .notation import parse_track_text
from .rhythm_generate import ChordSpan, DEFAULT_GRID, TRIPLET_GRID, meter_beats, _normalize_meter
from .i18n import tr

MAX_ALTS = 3            # giri/disegni alternativi conservati, oltre al principale (e alla variante)
_TOMS = ("tom1", "tom2", "floor", "tom_lowmid", "tom_hi", "tom_highfloor")
_TOLERANCE = 0.03       # scarto (in unita' di griglia) entro cui un attacco "sta" sulla griglia

# Griglie provate, dalla piu' larga: (dichiarazione, durata in beat).
_LINE_GRIDS = [("4:", 1.0), ("8:", 0.5), ("16:", 0.25), ("8T:", 1.0 / 3.0)]


def _fits(starts, unit: float) -> bool:
    return all(abs(t / unit - round(t / unit)) < _TOLERANCE for t in starts)


def _error(starts, unit: float) -> float:
    return sum(abs(t / unit - round(t / unit)) for t in starts)


def _pick_grid(starts, candidates) -> Tuple[str, float]:
    """La prima griglia (la piu' larga) che spiega tutti gli attacchi, o
    quella che li spiega meglio."""
    for grid, unit in candidates:
        if _fits(starts, unit):
            return grid, unit
    return min(candidates, key=lambda c: _error(starts, c[1]))


def _ranked_bars(bars: Dict[int, tuple], key) -> List[tuple]:
    """Le battute diverse, dalla piu' frequente (a parita', la prima che
    compare), senza le battute vuote."""
    counts = Counter()
    first = {}
    for index in sorted(bars):
        bar = bars[index]
        k = key(bar)
        if k is None:
            continue
        counts[k] += 1
        first.setdefault(k, (index, bar))
    return [first[k][1] for k, _n in sorted(counts.items(), key=lambda kv: (-kv[1], first[kv[0]][0]))]


# ---------------------------------------------------------------------------
# Batteria
# ---------------------------------------------------------------------------

def learn_drum_style(text: str, patterns=None, meter: str = "4/4", midi_dir: Optional[str] = None) -> dict:
    """Stile di batteria (formato di DRUM_STYLES, piu' 'alts') da un testo
    percussivo. ValueError se non contiene colpi di batteria."""
    meter = _normalize_meter(meter)
    bar_beats = meter_beats(meter)
    hits = []   # (inizio, nome, velocity)
    for ev in parse_track_text(text, patterns or {}, midi_dir=midi_dir):
        if ev.kind == "percussion":
            hits.append((ev.start, ev.name, ev.velocity))
        elif ev.kind == "block":
            hits.extend((ev.start, it["name"], ev.velocity) for it in ev.items if it.get("kind") == "percussion")
    if not hits:
        raise ValueError(tr("Nessun colpo di batteria da cui ricavare uno stile."))

    eighths_meter = meter.endswith("/8")
    candidates = ([("8:", 0.5), (DEFAULT_GRID, 0.25)] if eighths_meter
                  else [(DEFAULT_GRID, 0.25), (TRIPLET_GRID, 1.0 / 3.0)])
    grid, unit = _pick_grid([t for t, _n, _v in hits], candidates)
    length = round(bar_beats / unit)

    bars: Dict[int, list] = {}
    for t, name, velocity in hits:
        slot = round(t / unit)
        index, i = divmod(slot, length)
        bar = bars.setdefault(index, [dict() for _ in range(length)])
        bar[i][name] = max(velocity, bar[i].get(name, 0))

    # Il crash sul primo tempo lo aggiunge il generatore (dopo i fill, con
    # l'intensita' piena): si toglie, salvo che faccia parte del giro.
    with_crash = sum(1 for bar in bars.values() if "crash" in bar[0])
    if with_crash * 2 <= len(bars):
        for bar in bars.values():
            bar[0].pop("crash", None)

    def slots(bar):
        return [sorted(((n, int(v)) for n, v in slot.items()), key=lambda h: -h[1]) or None for slot in bar]

    def shape(bar):
        sig = tuple(tuple(sorted(slot)) for slot in bar)
        return sig if any(sig) else None

    ranked = _ranked_bars(bars, shape)
    if not ranked:
        raise ValueError(tr("Nessun colpo di batteria da cui ricavare uno stile."))
    fills = [bar for bar in ranked if any(name in _TOMS for slot in bar for name in slot)]
    grooves = [bar for bar in ranked if bar not in fills] or ranked
    fill = next((bar for bar in reversed(fills) if bar is not grooves[0]), None)
    spec = {
        "main": slots(grooves[0]),
        "fill": slots(fill) if fill is not None else None,
        "alts": [slots(bar) for bar in grooves[1:1 + MAX_ALTS]],
        "grid": grid,
        "meter": meter,
        "bars_learned": len(bars),
    }
    num = int(meter.split("/")[0])
    if eighths_meter and num % 3 == 0 and num > 3:
        spec["pulse"] = round(1.5 / unit)   # 6/8, 9/8, 12/8: la pulsazione e' il quarto puntato
    return spec


# ---------------------------------------------------------------------------
# Basso, accompagnamento, riff
# ---------------------------------------------------------------------------

def _attacks(text: str, patterns, default_octave: int, midi_dir) -> List[tuple]:
    """(inizio, durata, [note MIDI] oppure [ruoli] per un simbolo d'accordo)."""
    out = []
    for ev in parse_track_text(text, patterns or {}, default_octave=default_octave, midi_dir=midi_dir):
        if ev.kind == "note":
            out.append((ev.start, ev.duration, [midi_note(note_name_to_pc(ev.letter), ev.octave)], False))
        elif ev.kind == "block":
            notes = [midi_note(note_name_to_pc(it["letter"]), it["octave"])
                     for it in ev.items if it.get("kind") == "note"]
            if notes:
                out.append((ev.start, ev.duration, sorted(notes), False))
        elif ev.kind == "chord":
            try:
                chord = parse_chord_symbol(ev.symbol)
            except ValueError:
                continue
            roles = ["root", "third", "fifth"]
            if 10 in chord.intervals or 11 in chord.intervals:
                roles.append("seventh")
            out.append((ev.start, ev.duration, roles, True))
    return sorted(out, key=lambda a: a[0])


def _degree(interval: int, span: ChordSpan) -> str:
    if interval == 0:
        return "root"
    if interval in (3, 4) and (span.third is None or span.third == interval):
        return "third"
    if interval == 7:
        return "fifth"
    if interval == 9:
        return "sixth"
    if interval == 10:
        return "seventh" if span.seventh == 10 else "flat7"
    if interval == 11 and span.seventh == 11:
        return "seventh"
    return f"i{interval}"


def learn_line_style(text: str, kind: str, patterns=None, meter: str = "4/4",
                     chords: Optional[List[ChordSpan]] = None, offset_beats: float = 0.0,
                     default_octave: int = 3, midi_dir: Optional[str] = None) -> dict:
    """Stile di basso ('bass'), accompagnamento ('comping') o riff ('riff')
    nel formato di BASS_PATTERNS/MELODIC_PATTERNS (piu' 'alts'), da un testo
    di note, blocchi o simboli d'accordo. 'chords' (tempo assoluto) sono gli
    accordi su cui il testo suonava, che inizia a 'offset_beats'. ValueError
    se il testo non ha note."""
    if kind not in ("bass", "comping", "riff"):
        raise ValueError(tr("Tipo di stile non valido per una linea: '{kind}'", kind=kind))
    meter = _normalize_meter(meter)
    bar_beats = meter_beats(meter)
    attacks = _attacks(text, patterns, default_octave, midi_dir)
    if not attacks:
        raise ValueError(tr("Nessuna nota da cui ricavare uno stile."))
    grid, unit = _pick_grid([a[0] for a in attacks], _LINE_GRIDS)

    def chord_at(t: float) -> Optional[Tuple[ChordSpan, Optional[ChordSpan]]]:
        if not chords:
            return None
        t_abs = t + offset_beats
        for i, span in enumerate(chords):
            if span.start_beat - 1e-6 <= t_abs < span.start_beat + span.duration_beats - 1e-6:
                return span, (chords[i + 1] if i + 1 < len(chords) else None)
        return None

    def bar_chord(index: int) -> ChordSpan:
        """Senza accordi: la nota piu' bassa del primo attacco della battuta
        fa da fondamentale; terza e settima dalle note della battuta."""
        in_bar = [a for a in attacks if index * bar_beats - 1e-6 <= a[0] < (index + 1) * bar_beats - 1e-6
                  and not a[3]]
        if not in_bar:
            return ChordSpan(0.0, bar_beats, 0, True)
        root = in_bar[0][2][0] % 12
        pcs = {(n - root) % 12 for a in in_bar for n in a[2]}
        third = 3 if 3 in pcs and 4 not in pcs else 4
        seventh = 10 if 10 in pcs else 11 if 11 in pcs else None
        return ChordSpan(index * bar_beats, bar_beats, root, True, third, seventh)

    # Ogni attacco: (inizio, fine, accordo, accordo successivo, note o ruoli)
    placed = []
    for start, duration, content, is_symbol in attacks:
        found = chord_at(start)
        span, following = found if found else (bar_chord(int(start // bar_beats)), None)
        placed.append((start, start + duration, span, following, content, is_symbol))

    # Ottava di riferimento della fondamentale: la piu' comune sotto le note.
    registers = Counter()
    for _s, _e, span, _f, content, is_symbol in placed:
        if not is_symbol:
            low = content[0]
            registers[(low - ((low - span.root_pc) % 12)) // 12] += 1
    reference = registers.most_common(1)[0][0] if registers else 0

    def role_of(note: int, span: ChordSpan) -> str:
        interval = (note - span.root_pc) % 12
        root_midi = reference * 12 + span.root_pc
        octave = (note - interval - root_midi) // 12
        return f"L:{_degree(interval, span)}:{octave}"

    polyphonic = kind == "comping"
    bars: Dict[int, list] = {}
    for n, (start, end, span, following, content, is_symbol) in enumerate(placed):
        if is_symbol:
            role = list(content)
        else:
            notes = content if polyphonic else [content[0] if kind == "bass" else content[-1]]
            role = [role_of(x, span) for x in notes]
            # l'ultima nota prima del cambio d'accordo, mezzo tono dalla
            # fondamentale successiva: e' una nota di avvicinamento
            if not polyphonic and following is not None:
                change = following.start_beat - offset_beats
                next_start = placed[n + 1][0] if n + 1 < len(placed) else None
                if start < change <= start + 1.0 + 1e-6 and (next_start is None or next_start >= change - 1e-6):
                    semitones = notes[0] - (reference * 12 + following.root_pc)
                    if semitones % 12 in (1, 11):
                        role = [f"L:next:{semitones}"]
            role = role if polyphonic else role[0]
        index = int((start + 1e-6) // bar_beats)
        offset = round((start - index * bar_beats) / unit) * unit
        if offset >= bar_beats - 1e-6:
            index, offset = index + 1, 0.0
        events = bars.setdefault(index, [])
        if not events or events[-1][0] < offset - 1e-6:
            events.append((round(offset, 6), role))
        # pausa dopo la nota, se prima dell'attacco successivo resta almeno un'unita'
        next_start = placed[n + 1][0] if n + 1 < len(placed) else (index + 1) * bar_beats
        next_start = min(next_start, (index + 1) * bar_beats)
        end_q = round((end - index * bar_beats) / unit) * unit
        if next_start - index * bar_beats - end_q >= unit - 1e-6 and end_q < bar_beats - 1e-6:
            events.append((round(end_q, 6), "rest"))

    def shape(events):
        if not any(role != "rest" for _t, role in events):
            return None
        return tuple((t, tuple(role) if isinstance(role, list) else role) for t, role in events)

    ranked = _ranked_bars(bars, shape)
    return {
        "grid": grid,
        "polyphonic": polyphonic,
        "bar": ranked[0],
        "variant": ranked[1] if len(ranked) > 1 else None,
        "alts": ranked[2:2 + MAX_ALTS],
        "meter": meter,
        "bars_learned": len(bars),
    }


# ---------------------------------------------------------------------------
# Riassunto per il dialogo
# ---------------------------------------------------------------------------

_GRID_NAMES = {"4:": "quarti", "8:": "ottavi", "16:": "sedicesimi", "8T:": "terzine di ottavo"}


def describe_style(kind: str, spec: dict) -> str:
    grid = _GRID_NAMES.get(spec.get("grid"), spec.get("grid"))
    learned = spec.get("bars_learned", 0)
    if kind == "drums":
        others = len(spec.get("alts", []))
        parts = [f"giro base in {spec['meter']} a {grid}"]
        if others:
            parts.append(f"{others} giro alternativo" if others == 1 else f"{others} giri alternativi")
        parts.append("fill ricavato dal box" if spec.get("fill") else "fill generico (nessuna battuta con i tom)")
        return tr("{learned} battute lette: ", learned=learned) + ", ".join(parts) + "."
    others = (1 if spec.get("variant") else 0) + len(spec.get("alts", []))
    text = f"{learned} battute lette: disegno di una battuta in {spec['meter']} a {grid}"
    if others:
        text += f", piu' {others} alternativ{'o' if others == 1 else 'i'}"
    return text + "."
