"""
Armonizza una melodia: dalla melodia (scritta in una traccia o in un box)
propone gli accordi, in tre versioni da semplice a ricca:

- "simple": solo i tre accordi principali (I IV V, in minore i iv V);
- "diatonic": tutti gli accordi della tonalita' (ii, iii, vi... in minore
  III, VI, VII), con la dominante maggiore anche in minore;
- "rich": la versione diatonica con le settime dove la melodia le permette,
  poi arricchita come il giro armonico generato (dominanti secondarie,
  II-V, sostituti di tritono: vedi rhythm_generate.reharmonize_text).

Metodo: un accordo per tratto (una battuta, o mezza); per ogni tratto ogni
accordo candidato prende punti per le note della melodia che contiene
(pesate per durata e per quanto cade sul tempo forte), ne perde per quelle
che lo urtano (un semitono sopra una sua nota), e la sequenza migliore si
sceglie con Viterbi: le successioni tipiche (V-I, IV-V, ii-V, vi-IV...)
costano meno, il primo e l'ultimo accordo preferiscono la tonica.
"""

import random
from fractions import Fraction
from typing import Dict, List, Optional, Tuple

from .chords import pitch_to_midi
from .i18n import tr
from .notation import parse_track_text
from .rhythm_generate import _FLAT_ROOTS, _SHARP_ROOTS, parse_key, reharmonize_text

VERSIONS = ("simple", "diatonic", "rich")

# Accordi candidati per modo: (semitoni sopra la tonica, qualita').
_SIMPLE = {"major": [(0, ""), (5, ""), (7, "")],
           "minor": [(0, "m"), (5, "m"), (7, "")]}
_DIATONIC = {"major": [(0, ""), (2, "m"), (4, "m"), (5, ""), (7, ""), (9, "m")],
             "minor": [(0, "m"), (3, ""), (5, "m"), (7, ""), (8, ""), (10, "")]}
_TRIADS = {"": (0, 4, 7), "m": (0, 3, 7)}
# Settima diatonica di ogni grado (per la versione ricca).
_SEVENTHS = {"major": {0: "maj7", 2: "m7", 4: "m7", 5: "maj7", 7: "7", 9: "m7"},
             "minor": {0: "m7", 3: "maj7", 5: "m7", 7: "7", 8: "maj7", 10: "7"}}

# Successioni (da, a) in gradi che suonano "naturali": costano meno.
_GOOD_MOVES = {(7, 0), (5, 7), (2, 7), (9, 5), (9, 2), (0, 5), (0, 7), (4, 9), (5, 0), (0, 9),
               (3, 8), (8, 7), (10, 3), (5, 10), (8, 5), (10, 0)}
_MOVE_BONUS = 0.6
_STAY_PENALTY = 0.35          # restare sullo stesso accordo: ammesso, ma meno interessante
_TONIC_EDGE_BONUS = 1.0       # primo e ultimo accordo sulla tonica
_CLASH = 1.0                  # una nota a un semitono da una nota dell'accordo
_TENSION = -0.3               # nona, sesta, quarta: si puo', ma toglie un po'
_ROOT_BONUS = 0.15


def melody_notes(text: str, patterns) -> List[Tuple[float, float, int]]:
    """[(inizio, durata, nota MIDI)] della melodia di un testo: le note, e
    di un accordo o di un blocco la nota piu' alta."""
    out = []
    for ev in parse_track_text(text, patterns):
        if ev.kind == "note" and ev.letter:
            out.append((ev.start, ev.duration, pitch_to_midi(ev.letter, ev.octave)))
        elif ev.kind == "block" and ev.items:
            pitches = [pitch_to_midi(it["letter"], it["octave"]) for it in ev.items
                       if it.get("kind") == "note" and it.get("letter")]
            if pitches:
                out.append((ev.start, ev.duration, max(pitches)))
    return out


# Una melodia finisce quasi sempre sulla tonica (o su una nota del suo
# accordo): l'ultima nota pesa quanto la correlazione con il profilo.
_LAST_NOTE_TONIC = 0.35
_LAST_NOTE_TRIAD = 0.12


def melody_key(notes) -> str:
    """La tonalita' della melodia: profilo di Krumhansl-Schmuckler (come
    core.key_detect) piu' l'indizio dell'ultima nota."""
    from .key_detect import _key_name, _key_scores
    histogram = [0.0] * 12
    for _start, dur, pitch in notes:
        histogram[pitch % 12] += dur
    if sum(histogram) <= 0:
        return "C"
    last = max(notes, key=lambda n: n[0])[2] % 12
    scores = {}
    for (tonic, minor), score in _key_scores(histogram).items():
        triad = {tonic, (tonic + (3 if minor else 4)) % 12, (tonic + 7) % 12}
        scores[(tonic, minor)] = score + (_LAST_NOTE_TONIC if last == tonic else
                                          _LAST_NOTE_TRIAD if last in triad else 0.0)
    return _key_name(*max(scores, key=scores.get))


def _weight(start: float, duration: float, bar_beats: float) -> float:
    pos = start % bar_beats
    strong = 1.6 if abs(pos) < 1e-6 else 1.2 if abs(pos - round(pos)) < 1e-6 else 0.8
    return duration * strong


def _score(chord_pcs, root_pc, span_notes, tonic) -> float:
    score = 0.0
    for pc, w in span_notes:
        if pc in chord_pcs:
            score += w * (1.0 + (_ROOT_BONUS if pc == root_pc else 0.0))
        elif any((pc - c) % 12 in (1, 11) for c in chord_pcs):
            score -= w * _CLASH
        else:
            score += w * _TENSION
    return score


def harmonize(notes, key: str, version: str = "diatonic", step_beats: float = 4.0,
              bar_beats: float = 4.0, seed: Optional[int] = None) -> str:
    """Il testo degli accordi ("4: 4C 4G ...") che armonizza 'notes'
    (vedi melody_notes) nella tonalita' 'key', un accordo ogni 'step_beats'
    beat, nella versione scelta (VERSIONS). Dove la melodia tace l'accordo
    di prima continua; prima della prima nota, pausa. Solleva ValueError
    senza note."""
    if version not in VERSIONS:
        raise ValueError(tr("Versione sconosciuta: '{version}'", version=version))
    if not notes:
        raise ValueError(tr("La melodia non ha note da armonizzare."))
    tonic, mode, flats = parse_key(key)
    roots = _FLAT_ROOTS if flats else _SHARP_ROOTS
    candidates = (_SIMPLE if version == "simple" else _DIATONIC)[mode]
    first = min(s for s, _d, _p in notes)
    first = (first // step_beats) * step_beats
    end = max(s + d for s, d, _p in notes)
    steps = max(1, int(-(-(end - first) // step_beats)))

    spans: List[List[Tuple[int, float]]] = [[] for _ in range(steps)]
    for start, dur, pitch in notes:
        t = start
        while t < start + dur - 1e-9:
            k = int((t - first) // step_beats)
            if k >= steps:
                break
            piece_end = min(start + dur, first + (k + 1) * step_beats)
            spans[k].append((pitch % 12, _weight(t, piece_end - t, bar_beats) if t == start
                             else 0.5 * (piece_end - t)))
            t = piece_end

    def pcs(off, quality):
        return {(tonic + off + i) % 12 for i in _TRIADS[quality]}

    n = len(candidates)
    local = [[_score(pcs(o, q), (tonic + o) % 12, span, tonic) for o, q in candidates] for span in spans]
    # Viterbi
    best = [list(local[0])]
    back = []
    for k in range(steps):
        if k == 0:
            best[0] = [v + (_TONIC_EDGE_BONUS if candidates[j][0] == 0 else 0.0) for j, v in enumerate(local[0])]
            continue
        row, ptr = [], []
        for j, (oj, _qj) in enumerate(candidates):
            options = []
            for i, (oi, _qi) in enumerate(candidates):
                move = best[k - 1][i]
                if (oi, oj) in _GOOD_MOVES:
                    move += _MOVE_BONUS
                elif oi == oj:
                    move -= _STAY_PENALTY if spans[k] else 0.0
                options.append((move, i))
            value, i = max(options)
            row.append(value + local[k][j])
            ptr.append(i)
        best.append(row)
        back.append(ptr)
    last = [v + (_TONIC_EDGE_BONUS if candidates[j][0] == 0 else 0.0) for j, v in enumerate(best[-1])]
    j = max(range(n), key=lambda x: last[x])
    path = [j]
    for ptr in reversed(back):
        j = ptr[j]
        path.append(j)
    path.reverse()

    chords = []
    for k, j in enumerate(path):
        off, quality = candidates[j]
        if version == "rich":
            seventh = _SEVENTHS[mode].get(off)
            if seventh:
                extra = {(tonic + off + (10 if seventh in ("7", "m7") else 11)) % 12}
                if not any(_score(extra, -1, [(pc, w)], tonic) < 0 for pc, w in spans[k]):
                    quality = seventh
        symbol = roots[(tonic + off) % 12] + quality
        if chords and chords[-1][0] == symbol:
            chords[-1][1] += Fraction(step_beats).limit_denominator(64)
        else:
            chords.append([symbol, Fraction(step_beats).limit_denominator(64)])
    pieces = ([("r", Fraction(first).limit_denominator(64))] if first > 1e-9 else []) + \
        [(s, d) for s, d in chords]
    unit = next(u for u in (Fraction(1), Fraction(1, 2), Fraction(1, 4))
                if all((d / u).denominator == 1 for _s, d in pieces))
    tokens = [f"{int(4 / unit)}:"]
    for symbol, dur in pieces:
        mult = int(dur / unit)
        tokens.append(f"{mult}{symbol}" if mult > 1 else symbol)
    text = " ".join(tokens)
    if version == "rich":
        rng = random.Random(seed)
        text = reharmonize_text(text, {}, key, 0.6, seed=rng.randrange(1 << 30), bar_beats=bar_beats)
    return text


def harmonize_versions(notes, key: str, step_beats: float, bar_beats: float,
                       seed: Optional[int] = None) -> Dict[str, str]:
    """Le tre versioni insieme (per il dialogo)."""
    return {v: harmonize(notes, key, v, step_beats, bar_beats, seed) for v in VERSIONS}
