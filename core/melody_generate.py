"""
Melodia a frasi (sezione "F" della proposta): invece di ripetere un disegno
fisso sulle note dell'accordo, come gli stili di riff, costruisce una vera
melodia.

- Frasi di due battute (quattro nelle metriche corte, 3/4 e 6/8) organizzate
  in una forma: A A' B A (tema, tema variato, contrasto, ripresa) oppure
  domanda-risposta (A A': la seconda frase riprende la prima e la chiude).
- Il motivo di A si ripete: stesso ritmo e stesso profilo, adattato agli
  accordi che trova; A' cambia il finale (e, con la variabilita', qualche
  nota); B ha un ritmo diverso e sta piu' in alto.
- Sui tempi forti note dell'accordo, sui deboli note della scala (per grado
  congiunto, di passaggio); dopo un salto la melodia torna indietro.
- Ogni frase ha un andamento ad arco (sale, poi scende) e termina su una
  cadenza: "aperta" (quinta o seconda: una domanda) o "chiusa" (la tonica:
  la risposta). L'ultima frase del brano e' sempre chiusa.

Il generatore e' deterministico a variabilita' 0 (non dipende dal seme);
con la variabilita' il seme sceglie un altro motivo e la variabilita' decide
quanto la melodia si prende liberta': ritmi piu' vari, note scelte meno
"ovvie", A' piu' diversa da A.
"""

import math
import random
from typing import Dict, List, Optional, Tuple

from .chords import midi_note
from .rhythm_generate import (
    ChordSpan, INTENSITIES, MELODY_STYLES, Variability, _expand_chords_to_cover, _intensity_at,
    _note_token, _variability, parse_key,
)
from .i18n import tr

MAJOR_SCALE = (0, 2, 4, 5, 7, 9, 11)
MINOR_SCALE = (0, 2, 3, 5, 7, 8, 10)

# Figure ritmiche per pulsazione: (pulsazioni occupate, durate in beat, peso),
# per densita' 0 (calma), 1 (media), 2 (mossa). Pulsazione semplice = un
# quarto; composta (6/8, 9/8, 12/8) = un quarto puntato.
_FIGURES_SIMPLE = {
    0: [(2, [2.0], 3), (2, [1.5, 0.5], 1), (1, [1.0], 2)],
    1: [(1, [1.0], 4), (1, [0.5, 0.5], 2), (2, [1.5, 0.5], 2), (2, [2.0], 1)],
    2: [(1, [0.5, 0.5], 5), (1, [1.0], 2), (2, [1.5, 0.5], 1)],
}
_FIGURES_COMPOUND = {
    0: [(1, [1.5], 3), (2, [3.0], 1)],
    1: [(1, [1.0, 0.5], 3), (1, [1.5], 2), (1, [0.5, 0.5, 0.5], 1)],
    2: [(1, [0.5, 0.5, 0.5], 3), (1, [1.0, 0.5], 2)],
}


# ---------------------------------------------------------------------------
# Tonalita' e armonia
# ---------------------------------------------------------------------------

def _chord_pcs(span: ChordSpan) -> List[int]:
    pcs = [span.root_pc]
    if span.third is not None:
        pcs.append((span.root_pc + span.third) % 12)
    if span.has_fifth:
        pcs.append((span.root_pc + 7) % 12)
    if span.seventh is not None:
        pcs.append((span.root_pc + span.seventh) % 12)
    return pcs


def estimate_key(chords: List[ChordSpan]) -> Tuple[int, str]:
    """(tonica, 'major'/'minor') che meglio spiega gli accordi: note degli
    accordi dentro la scala, pesate per durata, piu' un premio se il giro
    parte o finisce su quella tonica (con la terza giusta)."""
    total = sum(s.duration_beats for s in chords) or 1.0
    best, best_score = (0, "major"), -1.0
    for tonic in range(12):
        for mode, scale in (("major", MAJOR_SCALE), ("minor", MINOR_SCALE)):
            pcs = {(tonic + s) % 12 for s in scale}
            score = sum(span.duration_beats * sum(pc in pcs for pc in _chord_pcs(span)) for span in chords) / total
            third = 4 if mode == "major" else 3
            for span, weight in ((chords[0], 0.6), (chords[-1], 0.4)):
                if span.root_pc == tonic and span.third in (third, None):
                    score += weight
            if score > best_score + 1e-9:
                best, best_score = (tonic, mode), score
    return best


def _allowed_pcs(scale_pcs: List[int], span: ChordSpan) -> List[int]:
    """Le note della scala, corrette con le note dell'accordo che non ne
    fanno parte (il sol# di E7 in la minore, il sib di C7 in do): la nota
    alterata prende il posto di quella naturale vicina."""
    pcs = set(scale_pcs)
    for i, pc in enumerate(_chord_pcs(span)):
        if pc in pcs:
            continue
        interval = (pc - span.root_pc) % 12
        lowered = interval in (3, 10) or (i == 0 and (pc + 1) % 12 in pcs and (pc - 1) % 12 not in pcs)
        pcs.discard((pc + 1) % 12 if lowered else (pc - 1) % 12)
        pcs.add(pc)
    return sorted(pcs)


# ---------------------------------------------------------------------------
# Ritmo
# ---------------------------------------------------------------------------

def _pulses(bar_beats: float, compound: bool) -> List[Tuple[float, float]]:
    """(inizio, durata) delle pulsazioni di una battuta."""
    step = 1.5 if compound else 1.0
    out, t = [], 0.0
    while t < bar_beats - 1e-6:
        length = min(step, bar_beats - t)
        out.append((t, length))
        t += length
    return out


def _weighted(options, rng: random.Random, flatten: float):
    """Scelta pesata; 'flatten' (0-1) avvicina i pesi (piu' varieta')."""
    weights = [w ** (1.0 - 0.6 * flatten) for *_rest, w in options]
    return rng.choices(options, weights=weights)[0]


def _bar_rhythm(bar_beats: float, compound: bool, density: int, cadence: bool,
                rng: random.Random, flatten: float) -> List[Tuple[float, float]]:
    """[(inizio, durata)] delle note di una battuta. Nella battuta di
    cadenza, dopo la prima meta' la nota finale lunga."""
    pulses = _pulses(bar_beats, compound)
    base = 1.5 if compound else 1.0
    figures = (_FIGURES_COMPOUND if compound else _FIGURES_SIMPLE)[density]
    stop = len(pulses)
    if cadence:
        stop = max(1, (len(pulses) + 1) // 2) if len(pulses) > 1 else 0
    notes, i = [], 0
    while i < stop:
        start, length = pulses[i]
        if abs(length - base) > 1e-6:          # pulsazione corta (7/8): una nota
            notes.append((start, length))
            i += 1
            continue
        room = sum(1 for p in pulses[i:stop] if abs(p[1] - base) < 1e-6)
        span, durations, _w = _weighted([f for f in figures if f[0] <= room], rng, flatten)
        t = start
        for d in durations:
            notes.append((t, d))
            t += d
        i += span
    if cadence:
        start = pulses[stop][0] if stop < len(pulses) else 0.0
        notes.append((start, bar_beats - start))
    return notes


def _phrase_rhythm(phrase_bars: int, bar_beats: float, compound: bool, density: int,
                   rng: random.Random, flatten: float) -> List[Tuple[float, float]]:
    out = []
    for b in range(phrase_bars):
        out += [(b * bar_beats + t, d) for t, d in
                _bar_rhythm(bar_beats, compound, density, b == phrase_bars - 1, rng, flatten)]
    return out


# ---------------------------------------------------------------------------
# Altezze
# ---------------------------------------------------------------------------

class _Harmony:
    def __init__(self, chords: List[ChordSpan], scale_pcs: List[int], low: int, high: int):
        self.chords = chords
        self.scale_pcs = scale_pcs
        self.low, self.high = low, high

    def chord_at(self, t: float) -> ChordSpan:
        current = self.chords[0]
        for span in self.chords:
            if span.start_beat <= t + 1e-6:
                current = span
            else:
                break
        return current

    def notes(self, pcs) -> List[int]:
        pcs = set(pcs)
        return [m for m in range(self.low, self.high + 1) if m % 12 in pcs]


def _strength(onset: float, duration: float, bar_beats: float, compound: bool) -> str:
    """'strong' (inizio o meta' battuta, o nota lunga), 'beat' (altre
    pulsazioni), 'weak' (in levare)."""
    pos = onset % bar_beats
    pulse = 1.5 if compound else 1.0
    if abs(pos) < 1e-6 or duration >= 1.5 - 1e-6:
        return "strong"
    if not compound and bar_beats >= 4 - 1e-6 and abs(pos - 2.0) < 1e-6:
        return "strong"
    if abs(pos / pulse - round(pos / pulse)) < 1e-6:
        return "beat"
    return "weak"


def _leap_cost(prev: Optional[int], note: int) -> float:
    if prev is None:
        return 0.0
    d = abs(note - prev)
    if d == 0:
        return 2.0
    if d <= 2:
        return 0.0
    if d <= 4:
        return 0.6
    if d <= 7:
        return 2.0
    if d <= 12:
        return 4.5
    return 12.0


def _choose(candidates: List[int], cost, rng: random.Random, freedom: float) -> int:
    """La nota di costo minimo, oppure (con 'freedom' > 0) una fra le
    migliori, piu' probabile quanto meno costa."""
    scored = sorted((cost(c), c) for c in candidates)
    if freedom <= 0 or len(scored) == 1:
        return scored[0][1]
    top = scored[:4]
    temperature = 0.25 + 1.5 * freedom
    weights = [math.exp(-(s - top[0][0]) / temperature) for s, _c in top]
    return rng.choices([c for _s, c in top], weights=weights)[0]


def _realize(rhythm, start: float, harmony: _Harmony, bar_beats: float, compound: bool,
             targets: List[float], ending: str, tonic: int, prev: Optional[int], prev2: Optional[int],
             rng: random.Random, freedom: float, contour_weight: float = 0.5,
             fixed: Optional[Dict[int, int]] = None) -> List[int]:
    """Le altezze delle note della frase: 'targets' e' il profilo voluto
    (nota MIDI "ideale" per ogni nota), 'fixed' le note gia' decise (indice
    -> nota: il motivo ripreso cosi' com'e')."""
    out = []
    last = len(rhythm) - 1
    for i, (onset, duration) in enumerate(rhythm):
        if fixed and i in fixed:
            note = fixed[i]
        else:
            span = harmony.chord_at(start + onset)
            chord = _chord_pcs(span)
            strength = _strength(onset, duration, bar_beats, compound)
            if i == last:
                if ending == "closed":
                    # la tonica; se l'accordo non ce l'ha (una frase che finisce
                    # sul V), una nota della triade di tonica (terza o quinta)
                    triad = [pc for pc in chord if (pc - tonic) % 12 in (3, 4, 7)]
                    pcs = [tonic] if tonic in chord else (triad or chord)
                else:
                    others = [pc for pc in chord if pc != tonic]
                    pcs = others or chord
                candidates = harmony.notes(pcs)
            elif strength == "strong":
                candidates = harmony.notes(chord)
            else:
                candidates = harmony.notes(_allowed_pcs(harmony.scale_pcs, span))
            candidates = candidates or harmony.notes(chord) or [harmony.low]
            target = targets[i]

            def cost(c, strength=strength, chord=chord, target=target, is_last=(i == last)):
                value = contour_weight * abs(c - target) / 2.0 + _leap_cost(prev, c)
                if strength == "beat" and c % 12 in chord:
                    value -= 1.0          # sui tempi: meglio una nota dell'accordo
                if strength == "weak" and prev is not None and abs(c - prev) > 2:
                    value += 1.0          # in levare: meglio di grado congiunto
                if prev is not None and prev2 is not None:
                    if abs(prev - prev2) >= 5 and (c - prev) * (prev - prev2) > 0:
                        value += 3.0      # dopo un salto si torna indietro
                    if c == prev == prev2:
                        value += 3.0      # niente tre note uguali di fila
                    elif c == prev2 != prev and abs(c - prev) <= 2:
                        value += 1.0      # niente trilli (mi-fa-mi-fa)
                if is_last and ending == "open" and c % 12 in ((tonic + 7) % 12, (tonic + 2) % 12):
                    value -= 1.5          # domanda: quinta o seconda
                return value
            note = _choose(candidates, cost, rng, freedom)
        out.append(note)
        prev2, prev = prev, note
    return out


def _arch(rhythm, phrase_beats: float, base: float, height: float, ending: str) -> List[float]:
    """Profilo ad arco: sale fino a circa due terzi della frase, poi scende
    verso la nota di cadenza (piu' in basso se chiusa)."""
    out = []
    for onset, _d in rhythm:
        x = onset / phrase_beats
        rise = math.sin(math.pi * min(1.0, x / 1.3))
        out.append(base + height * rise)
    if out:
        out[-1] = base + (0 if ending == "closed" else 2)
    return out


# ---------------------------------------------------------------------------
# Generatore
# ---------------------------------------------------------------------------

def generate_phrase_melody(chords: List[ChordSpan], style: str, octave: int, range_low: int, range_high: int,
                           key: Optional[str] = None, min_total_beats: float = 0.0, variability=0.0,
                           seed: Optional[int] = None, bar_beats: float = 4.0, meter: Optional[str] = None,
                           intensity: str = "normal") -> str:
    """Melodia a frasi (vedi il commento del modulo) sugli accordi 'chords',
    nella tonalita' 'key' (formato di Project.key; None = ricavata dagli
    accordi, vedi estimate_key), all'ottava 'octave' e dentro l'estensione
    [range_low, range_high]. 'style' e' uno di MELODY_STYLES. Solleva
    ValueError se lo stile non esiste, gli accordi mancano o l'intensita'
    non e' valida."""
    spec = MELODY_STYLES.get(style)
    if spec is None:
        raise ValueError(tr("Stile di melodia sconosciuto: '{style}'", style=style))
    if not chords:
        raise ValueError(tr("Nessun accordo da seguire: la traccia sorgente non ne contiene."))
    if intensity not in INTENSITIES:
        raise ValueError(tr("Intensita' sconosciuta: '{intensity}' (valide: {0})", ', '.join(INTENSITIES), intensity=intensity))
    amount: Variability = _variability(variability)
    chords = _expand_chords_to_cover(chords, min_total_beats)
    total = max(min_total_beats, chords[-1].start_beat + chords[-1].duration_beats)
    if key and key.strip():
        tonic, mode, _flats = parse_key(key)
    else:
        tonic, mode = estimate_key(chords)
    scale = [(tonic + s) % 12 for s in (MAJOR_SCALE if mode == "major" else MINOR_SCALE)]

    # A variabilita' 0 il motivo non dipende dal seme.
    free = amount.rhythm > 0 or amount.notes > 0
    rng = random.Random(seed if free else 0)
    dyn_rng = random.Random(seed)

    compound = bool(meter) and meter.replace(" ", "").endswith("/8") and int(meter.split("/")[0]) % 3 == 0
    phrase_bars = 4 if bar_beats <= 3 + 1e-6 else 2
    phrase_beats = phrase_bars * bar_beats
    n_phrases = max(1, math.ceil(total / phrase_beats - 1e-9))

    # Registro: intorno alla tonica dell'ottava scelta, dentro l'estensione.
    center = midi_note(tonic, octave)
    while center > range_high - 7 and center - 12 >= range_low:
        center -= 12
    while center < range_low + 5 and center + 12 <= range_high:
        center += 12
    low, high = max(range_low, center - 7), min(range_high, center + 17)
    if high - low < 12:
        low, high = range_low, range_high
    harmony = _Harmony(chords, scale, low, high)

    form = spec["form"]
    motifs: Dict[Tuple[str, int], dict] = {}
    notes: List[Tuple[float, float, int, bool]] = []   # (inizio, durata, nota, frase-B?)
    prev = prev2 = None
    for p in range(n_phrases):
        label, ending = form[p % len(form)]
        if p == n_phrases - 1:
            ending = "closed"
        letter = label[0]
        start = p * phrase_beats
        level = _intensity_at(intensity, p, n_phrases)
        density = spec["density"] if letter == "A" else spec["b_density"]
        density = max(0, min(2, density + {"light": -1, "normal": 0, "full": 1}[level]))
        base = center + (spec["b_lift"] if letter == "B" else 0)
        height = spec["height"] + (2 if letter == "B" else 0)
        motif = motifs.get((letter, density))

        if motif is None:
            rhythm = _phrase_rhythm(phrase_bars, bar_beats, compound, density, rng, amount.rhythm)
            targets = _arch(rhythm, phrase_beats, base, height, ending)
            pitches = _realize(rhythm, start, harmony, bar_beats, compound, targets, ending, tonic,
                               prev, prev2, rng, amount.notes)
            motifs[(letter, density)] = {"rhythm": rhythm, "pitches": pitches, "start": start}
        else:
            rhythm = list(motif["rhythm"])
            # con la variabilita' del ritmo, una battuta (non l'ultima) cambia figura
            changed_bar = None
            if amount.rhythm > 0 and phrase_bars > 1 and rng.random() < 0.5 * amount.rhythm:
                changed_bar = rng.randrange(phrase_bars - 1)
                lo, hi = changed_bar * bar_beats, (changed_bar + 1) * bar_beats
                new_bar = [(lo + t, d) for t, d in
                           _bar_rhythm(bar_beats, compound, density, False, rng, amount.rhythm)]
                rhythm = [n for n in rhythm if not lo - 1e-6 <= n[0] < hi - 1e-6] + new_bar
                rhythm.sort()
            # stesso profilo del motivo, spostato sul primo accordo della frase
            old_rhythm, old_pitches = motif["rhythm"], motif["pitches"]
            first_chord = _chord_pcs(harmony.chord_at(start))
            anchor = min(harmony.notes(first_chord) or [old_pitches[0]], key=lambda c: abs(c - old_pitches[0]))
            shift = anchor - old_pitches[0]

            def old_pitch_at(onset):
                return min(zip(old_rhythm, old_pitches), key=lambda rp: abs(rp[0][0] - onset))[1]
            targets = [old_pitch_at(onset) + shift for onset, _d in rhythm]
            targets[-1] = base + (0 if ending == "closed" else 2)
            same_chords = all(_chord_pcs(harmony.chord_at(start + t)) == _chord_pcs(harmony.chord_at(motif["start"] + t))
                              for t, _d in rhythm)
            fixed = {}
            if same_chords and shift == 0:
                # stessi accordi: il motivo torna identico (tranne il finale e
                # le note che la variabilita' sceglie di cambiare)
                keep = {onset: pitch for (onset, _d), pitch in zip(old_rhythm, old_pitches)}
                for i, (onset, _d) in enumerate(rhythm[:-2]):
                    if onset in keep and not (amount.notes > 0 and rng.random() < 0.3 * amount.notes):
                        fixed[i] = keep[onset]
            pitches = _realize(rhythm, start, harmony, bar_beats, compound, targets, ending, tonic,
                               prev, prev2, rng, amount.notes, contour_weight=1.6, fixed=fixed)
        for (onset, duration), pitch in zip(rhythm, pitches):
            notes.append((start + onset, duration, pitch, letter == "B"))
        if pitches:
            prev2, prev = (pitches[-2] if len(pitches) > 1 else prev), pitches[-1]

    return _write(notes, total, amount.dynamics, phrase_beats, dyn_rng)


def _write(notes, total: float, dynamics: float, phrase_beats: float, rng: random.Random) -> str:
    """Token '8:' della melodia, tagliata a 'total' beat; con la dinamica,
    velocity che seguono l'arco della frase e accentano i tempi forti."""
    tokens = ["8:"]
    t = 0.0
    current = None
    for start, duration, pitch, _is_b in notes:
        if start >= total - 1e-6:
            break
        duration = min(duration, total - start)
        if start > t + 1e-6:
            rest = round((start - t) / 0.5)
            tokens.append(f"{rest}r" if rest > 1 else "r")
        if dynamics > 0:
            x = (start % phrase_beats) / phrase_beats
            accent = 6 if abs(start - round(start)) < 1e-6 else -4
            velocity = max(1, min(127, 84 + round(dynamics * (12 * math.sin(math.pi * x) + accent
                                                              + rng.randint(-5, 5)))))
            if velocity != current:
                tokens.append(f"{velocity}@")
                current = velocity
        mult = max(1, round(duration / 0.5))
        tokens.append((f"{mult}" if mult > 1 else "") + _note_token(pitch % 12, pitch // 12 - 1))
        t = start + mult * 0.5
    return " ".join(tokens)
