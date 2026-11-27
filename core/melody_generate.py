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

# Tessiture vocali (estensioni di un cantante di coro, MIDI): una melodia da
# cantare sta qui invece che in tutta l'estensione dello strumento.
VOICE_RANGES: Dict[str, Tuple[int, int]] = {
    "soprano": (60, 81),     # Do4 - La5
    "contralto": (53, 74),   # Fa3 - Re5
    "tenore": (48, 69),      # Do3 - La4
    "basso": (40, 62),       # Mi2 - Re4
}


def voice_octave(voice: str) -> int:
    """L'ottava di partenza per una tessitura: quella del centro dell'estensione."""
    low, high = VOICE_RANGES[voice]
    return (low + high) // 2 // 12 - 1


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
# Figure sincopate (pulsazione semplice): la nota lunga parte in levare. Il loro peso si moltiplica per la sincope dello
# stile (0 = mai, 1 = spesso): croma-semiminima-croma e croma-semiminima puntata.
_SYNCOPATED_SIMPLE = {
    0: [(2, [0.5, 1.5], 2)],
    1: [(2, [0.5, 1.0, 0.5], 4), (2, [0.5, 1.5], 2)],
    2: [(2, [0.5, 1.0, 0.5], 4), (2, [0.5, 1.5], 1)],
}
DEFAULT_SYNCOPATION = 0.3
DEFAULT_APPOGGIATURA = 0.25
BREATH = 0.5                  # beat: la pausa per respirare alla fine di una frase (tolta alla nota lunga di cadenza)
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
    alterata prende il posto di quella naturale vicina. Se le due vicine
    sono in scala si toglie quella da cui la nota e' alterata: di solito la
    sopra (la nota e' abbassata: sib al posto del si, lab al posto del la,
    anche come fondamentale di bII, bVI, bVII), la sotto per la terza e la
    settima maggiori (sol# al posto del sol). Una nota dell'accordo non si
    toglie mai."""
    pcs = set(scale_pcs)
    chord = _chord_pcs(span)
    for pc in chord:
        if pc in pcs:
            continue
        interval = (pc - span.root_pc) % 12
        near = [n for n in ((pc + 1) % 12, (pc - 1) % 12) if n in pcs and n not in chord]
        if interval == 0 and len(near) == 1:
            pass                                  # una fondamentale cromatica con una sola vicina in scala: prende il suo posto
        else:
            # la nota da cui e' alterata: sotto per la terza e la settima maggiori, sopra per le altre (abbassate); se quella non e'
            # in scala non si toglie nulla (il fa di G7 nella pentatonica di do non toglie il mi)
            from_note = (pc - 1) % 12 if interval in (4, 11) else (pc + 1) % 12
            near = [from_note] if from_note in near else []
        for n in near:
            pcs.discard(n)
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
                rng: random.Random, flatten: float, syncopation: float = 0.0) -> List[Tuple[float, float]]:
    """[(inizio, durata)] delle note di una battuta. Nella battuta di
    cadenza, dopo la prima meta' la nota finale lunga. 'syncopation' (0-1):
    quanto spesso entrano le figure sincopate (_SYNCOPATED_SIMPLE)."""
    pulses = _pulses(bar_beats, compound)
    base = 1.5 if compound else 1.0
    figures = list((_FIGURES_COMPOUND if compound else _FIGURES_SIMPLE)[density])
    if syncopation > 0 and not compound:
        figures += [(span, durations, w * syncopation) for span, durations, w in _SYNCOPATED_SIMPLE[density]]
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
                   rng: random.Random, flatten: float, syncopation: float = 0.0, space: int = 0) -> List[Tuple[float, float]]:
    """Il ritmo di una frase. Il motivo e' la prima battuta: con piu' di due
    battute, la terza (non di cadenza) la riprende uguale, come nelle frasi
    vere (motivo, risposta, motivo, cadenza). Con 'space' (il riff e il
    blues, a botta e risposta) le ultime 'space' battute sono della band:
    la prima ha solo la nota d'arrivo sul primo tempo (un tempo nel riff,
    due nel blues), poi silenzio."""
    bars = []
    base = 1.5 if compound else 1.0
    for b in range(phrase_bars):
        if space and b >= phrase_bars - space:
            bars.append([(0.0, min(bar_beats, base * (1 if space == 1 else 2)))] if b == phrase_bars - space else [])
            continue
        cadence = b == phrase_bars - 1
        if b == 2 and not cadence:
            bars.append(bars[0])
            continue
        bars.append(_bar_rhythm(bar_beats, compound, density, cadence, rng, flatten, syncopation))
    return [(b * bar_beats + t, d) for b, bar in enumerate(bars) for t, d in bar]


# ---------------------------------------------------------------------------
# Altezze
# ---------------------------------------------------------------------------

class _Harmony:
    def __init__(self, chords: List[ChordSpan], scale_pcs: List[int], low: int, high: int):
        self.chords = chords
        self.scale_pcs = scale_pcs
        self.low, self.high = low, high
        self.bass: List[Tuple[float, float, int]] = []     # le note del basso gia' scritto, se si conoscono

    def bass_at(self, t: float) -> List[int]:
        return [n % 12 for a, b, n in self.bass if a <= t + 1e-6 < b]

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
    if duration >= pulse - 1e-6:
        return "beat"          # la nota sincopata: parte in levare ma tiene sul tempo, si sente come quella del tempo
    return "weak"


def _leap_cost(prev: Optional[int], note: int) -> float:
    if prev is None:
        return 0.0
    d = abs(note - prev)
    if d == 0:
        return 0.8            # la nota ribattuta: nel canto e' comune (tre uguali di fila restano vietate, vedi _realize)
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
             fixed: Optional[Dict[int, int]] = None, ceiling: Optional[int] = None, soft_tonic: bool = False) -> List[int]:
    """Le altezze delle note della frase: 'targets' e' il profilo voluto
    (nota MIDI "ideale" per ogni nota), 'fixed' le note gia' decise (indice
    -> nota: il motivo ripreso cosi' com'e'), 'ceiling' la nota piu' alta
    che la frase puo' toccare (il culmine del brano resta alla frase B)."""
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
                    if soft_tonic and span.seventh == 11 and triad:
                        # una frase che non e' l'ultima, sopra un accordo con la settima maggiore (Fmaj7): la tonica starebbe un
                        # semitono sopra la settima dell'accompagnamento; chiude sulla terza o sulla quinta
                        pcs = triad
                else:
                    others = [pc for pc in chord if pc != tonic]
                    pcs = others or chord
                candidates = harmony.notes(pcs)
            elif strength == "strong":
                # le note dell'accordo a un semitono da un'altra (fondamentale e settima di un maj7) stridono con l'accompagnamento che suona
                # l'altra: sul tempo forte la terza e la quinta
                strong = [pc for pc in chord if not any((pc - other) % 12 in (1, 11) for other in chord if other != pc)] or chord
                candidates = harmony.notes(strong)
            else:
                candidates = harmony.notes(_allowed_pcs(harmony.scale_pcs, span))
                # nelle metriche composte (6/8) e con la battuta non intera (7/8) il levare puo' cadere su un quarto intero del
                # brano, dove l'accompagnamento batte: li' vale la regola dei tempi
                on_quarter = abs((start + onset) - round(start + onset)) < 1e-6
                if strength == "beat" or (on_quarter and (compound or abs(bar_beats - round(bar_beats)) > 1e-6)):
                    # sui tempi non forti niente tritono dal basso ne' seconda minore (sopra o sotto) una nota dell'accordo (la7b sopra si7b
                    # col basso re): restano al levare, dove passano
                    bass = span.bass_pc if span.bass_pc is not None else span.root_pc
                    avoid = {(bass + 6) % 12} | {(pc + d) % 12 for pc in chord for d in (1, -1)}
                    candidates = [m for m in candidates if m % 12 not in avoid or m % 12 in chord] or candidates
            candidates = candidates or harmony.notes(chord) or [harmony.low]
            if harmony.bass and (abs(onset - round(onset)) < 1e-6 or duration >= 1.0 - 1e-6):
                # dove la nota pesa (sul tempo, o lunga): niente tritono con la nota che il basso suona davvero
                clash = {(b + 6) % 12 for b in harmony.bass_at(start + onset)}
                candidates = [m for m in candidates if m % 12 not in clash] or candidates
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
                if ceiling is not None and c > ceiling:
                    value += 1.5          # sopra il culmine riservato alla B: solo se ogni altra scelta salta troppo
                return value
            note = _choose(candidates, cost, rng, freedom)
        out.append(note)
        prev2, prev = prev, note
    return out



def _half_bar(pos: float, bar_beats: float, compound: bool) -> bool:
    """Il secondo tempo forte della battuta: il terzo quarto del 4/4, la seconda pulsazione del 6/8, la terza del 12/8."""
    if compound:
        return abs(pos - bar_beats / 2) < 1e-6 and abs(pos / 1.5 - round(pos / 1.5)) < 1e-6
    return bar_beats >= 4 - 1e-6 and abs(pos - bar_beats / 2) < 1e-6


def _add_appoggiature(notes, harmony: _Harmony, bar_beats: float, compound: bool, amount: float, seed: str, phrase_beats: float):
    """Appoggiature: una nota dell'accordo sul secondo tempo forte della battuta, lunga almeno un tempo, si divide in due: prima
    la nota della scala un grado sopra (o sotto) (sul tempo, dove si sente), poi la nota dell'accordo che la risolve di grado. Solo
    note che non stridono con l'accompagnamento: non a un semitono da una nota dell'accordo ne' a un tritono dal basso (la
    nona che va sulla fondamentale, la sesta che va sulla quinta). Anche sulla nota di cadenza di una frase (la chiusa
    "femminile"), mai sull'ultima del brano; il primo tempo resta sempre una nota dell'accordo. Il caso dipende dalla nota e dal suo posto nella frase:
    un motivo che torna uguale ha le stesse appoggiature."""
    if amount <= 0:
        return notes
    notes = sorted(notes)
    out = []
    for i, (t, d, pitch, b) in enumerate(notes):
        nxt = notes[i + 1] if i + 1 < len(notes) else None
        prev = out[-1][2] if out else None
        span = harmony.chord_at(t)
        chord = _chord_pcs(span)
        ok = (nxt is not None and d >= 1.0 - 1e-6 and prev is not None
              and _half_bar(t % bar_beats, bar_beats, compound) and pitch % 12 in chord)
        if ok:
            rng = random.Random(f"{seed}/appoggiatura/{pitch}/{round((t % phrase_beats) * 2)}")
            ok = rng.random() < amount
        if ok:
            allowed = set(_allowed_pcs(harmony.scale_pcs, span))
            bass = span.bass_pc if span.bass_pc is not None else span.root_pc

            def fits(n):
                return (n is not None and harmony.low <= n <= harmony.high and n % 12 not in chord
                        and not any((n - pc) % 12 in (1, 11) for pc in chord) and (n - bass) % 12 != 6
                        and n != prev and abs(n - prev) <= 4)          # ci si arriva vicini, e non ribattuta
            # il grado sopra (la nona sulla fondamentale, la sesta sulla quinta) o, se non va, quello sotto (la nona sulla terza)
            above = next((pitch + k for k in (1, 2) if (pitch + k) % 12 in allowed), None)
            below = next((pitch - k for k in (1, 2) if (pitch - k) % 12 in allowed), None)
            above = above if fits(above) else (below if fits(below) else None)
            ok = above is not None
        if ok:
            half = round(d / 2 / 0.5) * 0.5
            out.append((t, half, above, b))
            out.append((t + half, d - half, pitch, b))
        else:
            out.append((t, d, pitch, b))
    return out


CONTOURS = {"arch": None, "early": 0.25, "late": 0.85}     # dove sta l'apice della frase (None: l'arco di sempre, a due terzi)


def _arch(rhythm, phrase_beats: float, base: float, height: float, ending: str, peak: Optional[float] = None) -> List[float]:
    """Profilo ad arco: sale fino a circa due terzi della frase, poi scende
    verso la nota di cadenza (piu' in basso se chiusa). 'peak' (0-1) sposta
    l'apice: presto (lo slancio in su e poi la discesa per gradi) o tardi
    (la frase che sale e ricade solo alla fine)."""
    out = []
    for onset, _d in rhythm:
        x = onset / phrase_beats
        if peak is None:
            rise = math.sin(math.pi * min(1.0, x / 1.3))
        elif x <= peak:
            rise = math.sin(math.pi / 2 * x / peak)
        else:
            rise = 1.0 - 0.7 * (x - peak) / (1.0 - peak)
        out.append(base + height * rise)
    if out:
        out[-1] = base + (0 if ending == "closed" else 2)
    return out


# ---------------------------------------------------------------------------
# Generatore
# ---------------------------------------------------------------------------

# Le scale per genere (8.8.3), come gradi dalla tonica: (maggiore, minore); None = la scala di sempre. Le note dell'accordo che
# non ne fanno parte si aggiungono comunque (vedi _allowed_pcs).
SCALE_KINDS = {"pentatonic": ((0, 2, 4, 7, 9), (0, 3, 5, 7, 10)),
               "blues": ((0, 2, 3, 4, 7, 9), (0, 3, 5, 6, 7, 10)),
               "harmonic_minor": (None, (0, 2, 3, 5, 7, 8, 11)),
               # le scale modali dei generi da groove: misolidia in maggiore, dorica in minore (funk, soul, lo-fi, reggae)
               "groove": ((0, 2, 4, 5, 7, 9, 10), (0, 2, 3, 5, 7, 9, 10)),
               # rock: misolidia in maggiore, blues in minore
               "rock": ((0, 2, 4, 5, 7, 9, 10), (0, 3, 5, 6, 7, 10)),
               # bebop maggiore (con la sesta bemolle di passaggio): jazz e swing; in minore la scala di sempre
               "bebop": ((0, 2, 4, 5, 7, 8, 9, 11), None),
               # frigia dominante in maggiore (balcanico: do re b mi fa sol la b si b), minore armonica in minore
               "latin": ((0, 2, 4, 5, 7, 9, 11), (0, 2, 3, 5, 7, 9, 11)),           # maggiore e minore melodico: la melodia latina sale con la sesta e la settima naturali
    "classical": ((0, 2, 4, 5, 7, 9, 11), (0, 2, 3, 5, 7, 8, 11)),       # minore armonica: valzer e ballate hanno la sensibile
    "modal": ((0, 2, 4, 6, 7, 9, 11), (0, 2, 3, 5, 7, 9, 10)),           # lidia e dorica: elettronica e colonne sonore
    "phrygian_dominant": ((0, 1, 4, 5, 7, 8, 10), (0, 2, 3, 5, 7, 8, 11)),
               # metal: blues in maggiore, frigia in minore (do re b mi b fa sol la b si b)
               "metal": ((0, 2, 3, 4, 7, 9), (0, 1, 3, 5, 7, 8, 10))}


def generate_phrase_melody(chords: List[ChordSpan], style: str, octave: int, range_low: int, range_high: int,
                           key: Optional[str] = None, min_total_beats: float = 0.0, variability=0.0,
                           seed: Optional[int] = None, bar_beats: float = 4.0, meter: Optional[str] = None,
                           intensity: str = "normal", repeats=(), scale_kind: str = "", figure: str = "",
                           syncopation: float = DEFAULT_SYNCOPATION, appoggiatura: float = DEFAULT_APPOGGIATURA,
                           bass_notes=(), comfort_high: Optional[int] = None, lift: int = 0) -> str:
    """Melodia a frasi (vedi il commento del modulo) sugli accordi 'chords',
    nella tonalita' 'key' (formato di Project.key; None = ricavata dagli
    accordi, vedi estimate_key), all'ottava 'octave' e dentro l'estensione
    [range_low, range_high]. 'style' e' uno di MELODY_STYLES. 'repeats'
    (vedi section_repeats): le sezioni che tornano, dove la melodia torna
    uguale a quella della prima volta (un ritornello riconoscibile).
    'syncopation' (0-1): quanto spesso entrano le figure sincopate;
    'appoggiatura' (0-1): quanto spesso il secondo tempo forte e'
    un'appoggiatura (vedi _add_appoggiature). 'bass_notes': le note del
    basso gia' scritto, [(inizio, fine, nota MIDI)] in beat: dove la nota
    pesa la melodia non fa il tritono con quella che il basso suona;
    'comfort_high': la nota piu' alta dove lo strumento suona pieno;
    'lift': di quanti semitoni si sposta il centro delle frasi, dentro lo stesso
    registro (la strofa del grunge, piu' bassa: il ritornello sale). Solleva
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
    kind = SCALE_KINDS.get(scale_kind or "")
    if kind and kind[0 if mode == "major" else 1]:
        scale = [(tonic + s) % 12 for s in kind[0 if mode == "major" else 1]]

    # A variabilita' 0 il motivo non dipende dal seme.
    free = amount.rhythm > 0 or amount.notes > 0
    rng = random.Random(seed if free else 0)
    dyn_rng = random.Random(seed)

    compound = bool(meter) and meter.replace(" ", "").endswith("/8") and int(meter.split("/")[0]) % 3 == 0
    phrase_bars = int(spec.get("phrase_bars", 4 if bar_beats <= 3 + 1e-6 else 2))
    phrase_beats = phrase_bars * bar_beats
    # frasi di lunghezza diversa (8.4): una frase B puo' durare piu' battute delle A ("b_bars" dello stile)
    form = spec["form"]
    long_b = (int(spec.get("b_bars", phrase_bars))
              if total >= sum(int(spec.get("b_bars", phrase_bars)) if f[0][0] == "B" else phrase_bars for f in form) * bar_beats - 1e-9
              else phrase_bars)                      # la B lunga solo se c'e' posto per tutta la forma (A A' B A)

    def bars_of(label: str) -> int:
        return long_b if label[0] == "B" else phrase_bars
    # Le frasi devono stare nella lunghezza: l'ultima non resta tagliata a meta' (finiva su una croma qualsiasi invece che sulla
    # cadenza). Una B che non ci sta diventa la ripresa di A; l'ultima frase dura le battute che restano.
    starts: List[float] = []
    lengths: List[int] = []
    phrase_form: List[Tuple[str, str]] = []
    cursor = 0.0
    while not starts or cursor < total - 1e-9:
        label, ending = form[len(starts) % len(form)]
        remaining = max(1, math.ceil((total - cursor) / bar_beats - 1e-9))
        if label[0] == "B" and bars_of(label) > remaining:
            label, ending = "A", "closed"
        starts.append(cursor)
        lengths.append(min(bars_of(label), remaining))
        phrase_form.append((label, ending))
        cursor += lengths[-1] * bar_beats
    n_phrases = len(starts)
    has_b = any(label[0] == "B" for label, _e in phrase_form)

    # Registro: intorno alla tonica dell'ottava scelta, dentro l'estensione.
    center = midi_note(tonic, octave)
    while center > range_high - 7 and center - 12 >= range_low:
        center -= 12
    while center < range_low + 5 and center + 12 <= range_high:
        center += 12
    low, high = max(range_low, center - 7), min(range_high, center + 17)
    if high - low < 12:
        low, high = range_low, range_high
    if comfort_high:
        # dove il fiato suona pieno: un tetto sopra il registro (non lo sposta), almeno un'ottava sopra la nota piu' bassa
        high = max(low + 12, min(high, comfort_high))
    harmony = _Harmony(chords, scale, low, high)
    harmony.bass = sorted(bass_notes or ())

    # il culmine del brano: nelle forme con la B, le frasi A non arrivano dove arriva la B
    a_ceiling = center + lift + spec["height"] + 2 if has_b else None
    space = int(spec.get("space", 0))       # il riff e il blues a botta e risposta: le ultime battute di ogni frase sono della band

    motifs: Dict[Tuple[str, int, int], dict] = {}
    notes: List[Tuple[float, float, int, bool]] = []   # (inizio, durata, nota, frase-B?)
    prev = prev2 = None
    for p in range(n_phrases):
        label, ending = phrase_form[p]
        if p == n_phrases - 1:
            ending = "closed"
        letter = label[0]
        start = starts[p]
        phrase_bars_p = lengths[p]
        phrase_beats_p = phrase_bars_p * bar_beats
        level = _intensity_at(intensity, p, n_phrases)
        density = spec["density"] if letter == "A" else spec["b_density"]
        density = max(0, min(2, density + {"light": -1, "normal": 0, "full": 1}[level]))
        base = center + lift + (spec["b_lift"] if letter == "B" else 0)
        height = spec["height"] + (2 if letter == "B" else 0)
        ceiling = a_ceiling if letter == "A" else None
        space_p = min(space, phrase_bars_p - 1)      # una frase accorciata (l'ultima) tiene almeno una battuta cantata
        # il motivo: per lettera e densita'; se la densita' cambia (l'intensita' "crescendo") si riprende il ritmo che c'e'
        motif = motifs.get((letter, density, phrase_bars_p))
        if motif is None and intensity == "build":
            motif = next((m for (lt, _dn, bars), m in motifs.items() if lt == letter and bars == phrase_bars_p), None)

        if motif is None:
            rhythm = _phrase_rhythm(phrase_bars_p, bar_beats, compound, density, rng, amount.rhythm, syncopation, space_p)
            contour = rng.choices(("arch", "early", "late"), weights=(3, 2, 1) if letter == "A" else (2, 0, 1))[0]
            targets = _arch(rhythm, phrase_beats_p, base, height, ending, CONTOURS[contour])
            pitches = _realize(rhythm, start, harmony, bar_beats, compound, targets, ending, tonic,
                               prev, prev2, rng, amount.notes, ceiling=ceiling, soft_tonic=p < n_phrases - 1)
            motifs[(letter, density, phrase_bars_p)] = {"rhythm": rhythm, "pitches": pitches, "start": start}
        else:
            rhythm = list(motif["rhythm"])
            # con la variabilita' del ritmo cambia figura una battuta, mai la prima (e' il motivo che si riconosce): la seconda
            # o una delle seguenti, anche quella di cadenza
            changed_bar = None
            sung = phrase_bars_p - space_p                   # le battute di risposta (il riff, il blues) non cambiano
            if amount.rhythm > 0 and sung > 1 and rng.random() < 0.5 * amount.rhythm:
                changed_bar = rng.randrange(1, sung)
                lo, hi = changed_bar * bar_beats, (changed_bar + 1) * bar_beats
                new_bar = [(lo + t, d) for t, d in
                           _bar_rhythm(bar_beats, compound, density, changed_bar == phrase_bars_p - 1, rng, amount.rhythm,
                                       syncopation)]
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
                # (la prima battuta resta sempre quella del motivo)
                keep = {onset: pitch for (onset, _d), pitch in zip(old_rhythm, old_pitches)}
                for i, (onset, _d) in enumerate(rhythm[:-1] if space_p else rhythm[:-2]):   # il riff: cambia solo la nota d'arrivo
                    first_bar = onset < bar_beats - 1e-6
                    if onset in keep and (first_bar or not (amount.notes > 0 and rng.random() < 0.3 * amount.notes)):
                        fixed[i] = keep[onset]
            # ripreso su altri accordi: piu' vicino al profilo del motivo, meno liberta'
            pitches = _realize(rhythm, start, harmony, bar_beats, compound, targets, ending, tonic,
                               prev, prev2, rng, 0.5 * amount.notes, contour_weight=1.6, fixed=fixed, ceiling=ceiling,
                               soft_tonic=p < n_phrases - 1)
        last = len(rhythm) - 1
        if space_p and p == n_phrases - 1 and rhythm:
            # l'ultima frase del brano non lascia il silenzio: la nota d'arrivo tiene fino alla fine
            rhythm = rhythm[:-1] + [(rhythm[-1][0], phrase_beats_p - rhythm[-1][0])]
        for i, ((onset, duration), pitch) in enumerate(zip(rhythm, pitches)):
            if i == last and p < n_phrases - 1 and duration >= 1.0 + BREATH - 1e-6:
                duration -= BREATH            # il respiro prima della frase dopo
            notes.append((start + onset, duration, pitch, letter == "B"))
        if pitches:
            prev2, prev = (pitches[-2] if len(pitches) > 1 else prev), pitches[-1]

    notes = _add_appoggiature(notes, harmony, bar_beats, compound, appoggiatura, f"{seed if free else 0}", phrase_beats)
    if amount.rhythm > 0 and not compound:                   # prima delle ripetizioni: una sezione che torna copia anche le sue anacrusi interne
        notes = _add_pickups(notes, starts[1:], scale, 0.5 * amount.rhythm, random.Random(f"{seed}/pickup"), range_low, range_high)
    figures = [f for f in (figure or "").split(",") if f]
    approach = next((f for f in figures if f in ("approach", "approach_below")), "")
    if approach and not compound:                            # anche questa prima delle ripetizioni: una sezione che torna copia le sue figure
        notes = _add_approaches(notes, approach, 0.3, random.Random(f"{seed if free else 0}/figure"), range_low, range_high)
    notes = _apply_repeats(notes, repeats)
    ornaments = _ornaments(notes, figures, scale, tonic, f"{seed if free else 0}", phrase_beats, range_low, range_high)
    return _write(notes, total, amount.dynamics, phrase_beats, dyn_rng, ornaments)


def _add_pickups(notes, phrase_starts, scale, probability: float, rng: random.Random, range_low: int, range_high: int):
    """Anacrusi (8.4): una frase puo' partire un ottavo prima della battuta, con una nota di avvicinamento (un grado sotto la
    prima nota, della scala) presa dalla fine della nota lunga che chiude la frase prima. Solo dove quella nota dura almeno un
    tempo: una frase che finisce su note brevi non ha posto per l'attacco."""
    notes = sorted(notes)
    for start in phrase_starts:
        if rng.random() >= probability:
            continue
        # la nota che chiude la frase prima: finisce sull'attacco, o mezzo tempo prima (il respiro, vedi BREATH); col respiro
        # l'anacrusi le toglie un altro ottavo, perche' la pausa resti prima dell'attacco
        previous = next((i for i, n in enumerate(notes) if abs(n[0] + n[1] - start) < 1e-6 and n[1] >= 1.0 - 1e-6), None)
        if previous is None:
            previous = next((i for i, n in enumerate(notes)
                             if abs(n[0] + n[1] + BREATH - start) < 1e-6 and n[1] >= 1.0 - 1e-6), None)
        first = next((n for n in notes if abs(n[0] - start) < 1e-6), None)
        if previous is None or first is None:
            continue
        t, d, p, b = notes[previous]
        # un grado sotto la prima nota (o sopra, se sotto non c'e' posto): sempre nella scala e dentro l'estensione
        approach = next((first[2] + step for step in (-2, -1, 2, 1)
                         if (first[2] + step) % 12 in scale and range_low <= first[2] + step <= range_high), None)
        if approach is None:
            continue
        notes[previous] = (t, d - 0.5, p, b)
        notes.append((start - 0.5, 0.5, approach, first[3]))
    return sorted(notes)


FIGURES = ("approach", "approach_below", "grace_above", "grace_below", "blue_bend")
ORNAMENT_PROBABILITY = {"grace_above": 0.15, "grace_below": 0.15, "blue_bend": 0.16}
BEND_MIN_BEATS = 1.5          # il bend solo sulle note lunghe: poche, e che si sentono


def _ornaments(notes, figures, scale, tonic: int, seed: str, phrase_beats: float, range_low: int, range_high: int) -> dict:
    """Abbellimenti e bend (terza revisione, 2a e 2b): {inizio della nota: ("grace", nota) o ("bend", nota di partenza)}.
    Solo sulle note lunghe (almeno un tempo) sul tempo. Si scelgono dopo le ripetizioni con un caso che dipende dalla nota e
    dal suo posto nella frase: una sezione che torna ha gli stessi abbellimenti.
    - grace_above: acciaccatura un grado sopra, nella scala; grace_below: un semitono sotto;
    - blue_bend: la terza maggiore presa dalla terza minore, o la quinta dalla quinta diminuita (parte un semitono sotto e sale)."""
    out = {}
    wanted = [f for f in figures if f in ORNAMENT_PROBABILITY]
    if not wanted:
        return out
    for start, duration, pitch, _b in notes:
        if duration < 1.0 - 1e-6 or abs(start - round(start)) > 1e-6:
            continue
        for kind in wanted:
            if kind == "blue_bend" and duration < BEND_MIN_BEATS - 1e-6:
                continue
            rng = random.Random(f"{seed}/{kind}/{pitch}/{round((start % phrase_beats) * 2)}")
            if rng.random() >= ORNAMENT_PROBABILITY[kind]:
                continue
            if kind == "blue_bend":
                if (pitch - tonic) % 12 not in (4, 7) or pitch - 1 < range_low:
                    continue
                out[start] = ("bend", pitch - 1)
            elif kind == "grace_below":
                if pitch - 1 >= range_low:
                    out[start] = ("grace", pitch - 1)
            else:
                above = next((pitch + k for k in (1, 2) if (pitch + k) % 12 in scale), None)
                if above is not None and above <= range_high:
                    out[start] = ("grace", above)
            break
    return out


def _add_approaches(notes, figure: str, probability: float, rng: random.Random, range_low: int, range_high: int):
    """Note di avvicinamento cromatiche (8.9): davanti a una nota sul tempo, l'ultimo ottavo della nota lunga che la precede diventa
    la nota un semitono sotto (figure="approach_below": il passaggio del blues) o, a caso, sotto o sopra ("approach": il jazz).
    Solo dove la nota prima dura almeno un tempo e non e' gia' quella: cade sul levare, fuori dai tempi forti."""
    if figure not in FIGURES:
        return notes
    notes = sorted(notes)
    for target in [n for n in notes if abs(n[0] - round(n[0])) < 1e-6]:
        previous = next((i for i, n in enumerate(notes) if abs(n[0] + n[1] - target[0]) < 1e-6 and n[1] >= 1.0 - 1e-6), None)
        if previous is None or rng.random() >= probability:
            continue
        step = -1 if figure == "approach_below" else rng.choice((-1, 1))
        approach = target[2] + step
        t, d, p, b = notes[previous]
        if approach == p or not range_low <= approach <= range_high:
            continue
        notes[previous] = (t, d - 0.5, p, b)
        notes.append((target[0] - 0.5, 0.5, approach, target[3]))
    return sorted(notes)


def _apply_repeats(notes, repeats):
    """Le note delle sezioni che tornano rimpiazzate da quelle della prima
    volta: [(inizio, fine, inizio della sezione da ripetere)] in beat."""
    for start, end, source in sorted(repeats):
        length = end - start
        if length <= 0 or source >= start:
            continue
        copied = [(t - source + start, min(d, end - (t - source + start)), p, b)
                  for t, d, p, b in notes if source - 1e-6 <= t < source + length - 1e-6]
        kept = [n for n in notes if not start - 1e-6 <= n[0] < end - 1e-6]
        # la nota prima della sezione non deve suonarci sopra
        kept = [(t, min(d, start - t) if t < start < t + d else d, p, b) for t, d, p, b in kept]
        notes = sorted(kept + copied)
    return notes


def section_repeats(project, track, part_start: float = 0.0) -> List[Tuple[float, float, float]]:
    """Le sezioni della traccia (i suoi box nella Struttura brano) che
    ripetono una sezione precedente: stesso nome (senza numeri o "copia")
    o stesso contenuto. [(inizio, fine, inizio della prima volta)] in beat
    contati da part_start (dove comincia la parte generata)."""
    import re
    from .arrangement import clip_duration_beats
    if track is None or track.is_audio or not track.clips:
        return []

    def name_key(name):
        name = re.sub(r"\s*\((?:copia|\d+)\)\s*$", "", name.strip().lower())
        return re.sub(r"\s*\d+$", "", name)

    seen_names: Dict[str, float] = {}
    seen_texts: Dict[str, float] = {}
    out = []
    for clip in sorted(track.clips, key=lambda c: c.start_beat):
        length = clip_duration_beats(clip.text, project.patterns, track.instrument.default_octave,
                                     start_beat=clip.start_beat, meter=project.meter())
        key, text = name_key(clip.name), " ".join(clip.text.split())
        first = seen_names.get(key) if key else None
        if first is None:
            first = seen_texts.get(text)
        if first is not None and length > 0:
            out.append((clip.start_beat - part_start, clip.start_beat + length - part_start, first - part_start))
        else:
            if key:
                seen_names.setdefault(key, clip.start_beat)
            seen_texts.setdefault(text, clip.start_beat)
    return [r for r in out if r[2] >= 0]


def _write(notes, total: float, dynamics: float, phrase_beats: float, rng: random.Random, ornaments=None) -> str:
    """Token '8:' della melodia, tagliata a 'total' beat; con la dinamica,
    velocity che seguono l'arco della frase e accentano i tempi forti.
    'ornaments' (vedi _ornaments): l'acciaccatura (d*5'g) subito prima della nota, o il bend scritto come slide (d#*4>3e*4)."""
    ornaments = ornaments or {}
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
        ornament = ornaments.get(start)
        note = _note_token(pitch % 12, pitch // 12 - 1)
        if ornament and ornament[0] == "grace":
            tokens.append(_note_token(ornament[1] % 12, ornament[1] // 12 - 1) + "'g")
        if ornament and ornament[0] == "bend" and mult >= 2:
            tokens.append(_note_token(ornament[1] % 12, ornament[1] // 12 - 1) + f">{mult - 1}" + note)
        else:
            tokens.append((f"{mult}" if mult > 1 else "") + note)
        t = start + mult * 0.5
    return " ".join(tokens)


# ---------------------------------------------------------------------------
# Melodia nei silenzi della voce
# ---------------------------------------------------------------------------

VOICE_MIN_SILENCE = 0.5      # secondi: una pausa piu' corta della voce non lascia spazio


def voice_regions(project, track) -> List[Tuple[float, float]]:
    """Dove la traccia audio suona (canta), [(beat d'inizio, beat di fine)]
    del brano: lo stesso rilevamento di "Rimuovi i silenzi" (core.audio_silence),
    con pause di almeno VOICE_MIN_SILENCE."""
    from .audio_silence import clip_levels_db, sound_regions
    from .audio_track_notation import audible_clips
    from .tempo_map import beat_at_elapsed_seconds, build_tempo_beat_map, seconds_for_beats
    tempo_map = build_tempo_beat_map(project)
    out = []
    for clip in audible_clips(track):
        levels, total = clip_levels_db(clip)
        start_s = seconds_for_beats(tempo_map, clip.start_beat)
        for a, b in sound_regions(levels, total, min_silence=VOICE_MIN_SILENCE, pre_roll=0.0):
            out.append((beat_at_elapsed_seconds(tempo_map, 0.0, start_s + a),
                        beat_at_elapsed_seconds(tempo_map, 0.0, start_s + b)))
    return sorted(out)


def _grid_unit(text: str) -> Optional[float]:
    import re
    m = re.match(r"\s*(\d+)(T?):", text)
    if not m:
        return None
    unit = 4.0 / int(m.group(1))
    return unit * 2.0 / 3.0 if m.group(2) else unit


def rest_where(text: str, regions, patterns=None, min_overlap: float = 0.25) -> str:
    """Il testo generato con una pausa al posto di ogni nota (o accordo)
    che cade per almeno 'min_overlap' della sua durata dentro 'regions'
    (beat, vedi voice_regions): la melodia suona nei silenzi della voce.
    Se il testo non ha una griglia sola, lo lascia com'e'."""
    import re
    from .notation import parse_track_text
    words = text.split()
    # le opzioni prima della griglia (swing16=54, shift=...) restano davanti: la griglia e' la prima parola "N:" o "NT:"
    grid_at = next((i for i, w in enumerate(words) if re.fullmatch(r"\d+T?:", w)), None)
    if grid_at is None or not regions or any("=" not in w for w in words[:grid_at]):
        return text
    unit = _grid_unit(words[grid_at])
    if unit is None:
        return text
    tokens = words[:grid_at + 1]
    velocity = None
    for ev in parse_track_text(text, patterns or {}):
        mult = ev.duration / unit
        if abs(mult - round(mult)) > 1e-6 or round(mult) < 1:
            return text
        mult = int(round(mult))
        prefix = f"{mult}" if mult > 1 else ""
        body = None
        if ev.kind in ("note", "block"):
            overlap = sum(max(0.0, min(b, ev.start + ev.duration) - max(a, ev.start)) for a, b in regions)
            if overlap < min_overlap * ev.duration:
                if ev.kind == "note":
                    body = f"{ev.letter}*{ev.octave}"
                else:
                    body = "[" + " ".join(f"{it['letter']}*{it['octave']}" for it in ev.items
                                          if it.get("kind") == "note") + "]"
        elif ev.kind != "rest":
            return text                       # altro (accordi per sigla, percussioni): non si tocca
        if body is None:
            tokens.append(f"{prefix}r")
            continue
        if ev.velocity != velocity:
            tokens.append(f"{ev.velocity}@")
            velocity = ev.velocity
        tokens.append(prefix + body)
    return " ".join(tokens)
