"""
Curva esatta del pitch bend per l'import MIDI (opzione "Bottleneck" in
Opzioni > Slide nell'import MIDI...).

Gli slide della notazione (c*4>d*4) vanno da un semitono all'altro sulla
griglia: bastano per i bending della chitarra, non per il bottleneck, che
scivola di continuo, si ferma fra due semitoni e fa piu' movimenti dentro la
stessa nota. Con l'opzione le note si importano senza slide e la curva vera
del pitch wheel diventa un'automazione bend= (in semitoni, con decimali e
rampe >>) in una voce di pause parallela alle note:

    { <note importate> ; 64: bend=0 12r bend=-0.5 >> 6r bend=-1 ... }

La curva si semplifica (Ramer-Douglas-Peucker) entro CURVE_TOLERANCE
semitoni e si allinea ai sessantaquattresimi: un tratto fermo resta un
valore solo, una rampa diventa bend=a >> ... bend=b, un salto due valori
nello stesso punto.
"""

from typing import List, Optional, Sequence, Tuple

CURVE_GRID = 64                 # la voce della curva in sessantaquattresimi
CURVE_TOLERANCE = 0.1           # semitoni di scarto massimo dalla curva vera
MIN_CURVE_SEMITONES = 0.25      # sotto questa escursione il canale non ha curva
MAX_BEND = 24.0                 # i limiti di bend=


def _rdp(points, tolerance):
    """Ramer-Douglas-Peucker sulla distanza verticale, senza ricorsione
    (una curva di un brano intero ha migliaia di punti)."""
    if len(points) < 3:
        return list(points)
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        (t0, y0), (t1, y1) = points[first], points[last]
        worst, worst_i = 0.0, None
        for i in range(first + 1, last):
            t, y = points[i]
            line = y0 + (y1 - y0) * ((t - t0) / (t1 - t0) if t1 != t0 else 0.0)
            if abs(y - line) > worst:
                worst, worst_i = abs(y - line), i
        if worst_i is not None and worst > tolerance:
            keep[worst_i] = True
            stack.append((first, worst_i))
            stack.append((worst_i, last))
    return [p for p, k in zip(points, keep) if k]


def _value(semitones: float) -> str:
    text = f"{max(-MAX_BEND, min(MAX_BEND, semitones)):.2f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def curve_points(events: Sequence[Tuple[int, int]], bend_range: float, start: int,
                 end: int) -> List[Tuple[int, float]]:
    """La curva del pitch wheel fra i tick start ed end come spezzata
    [(tick, semitoni)]: il wheel resta su un valore fino all'evento
    successivo (scalini), che la semplificazione riduce a rampe e tenute."""
    value = 0.0
    points = []
    for tick, raw in events:
        semitones = raw / 8192.0 * bend_range
        if tick <= start:
            value = semitones
            continue
        if tick > end:
            break
        if not points:
            points.append((start, value))
        if semitones != value:
            points.append((tick, value))
            points.append((tick, semitones))
            value = semitones
    if not points:
        points.append((start, value))
    points.append((end, value))
    return _rdp(points, CURVE_TOLERANCE)


def bend_curve_span(events: Sequence[Tuple[int, int]], bend_range: float, ticks_per_beat: int,
                    start: int, end: int) -> Optional[str]:
    """La voce di pause con l'automazione bend= del tratto [start, end) del
    canale (tick), con le posizioni contate da start; None se nel tratto il
    wheel non si muove abbastanza da servire."""
    if not events or end <= start:
        return None
    value_at_start = 0.0
    peak = 0.0
    for tick, raw in events:
        if tick <= start:
            value_at_start = abs(raw) / 8192.0 * bend_range
        elif tick <= end:
            peak = max(peak, abs(raw) / 8192.0 * bend_range)
    if max(peak, value_at_start) < MIN_CURVE_SEMITONES:
        return None
    points = curve_points(events, bend_range, start, end)
    unit = ticks_per_beat * 4 / CURVE_GRID          # tick per sessantaquattresimo
    steps = []
    for tick, semitones in points:
        step = (round((tick - start) / unit), semitones)
        # lo stesso valore nello stesso punto (dopo l'allineamento) e' un doppione
        if steps and steps[-1][0] == step[0] and _value(steps[-1][1]) == _value(semitones):
            continue
        steps.append(step)
    # una tenuta sul centro in fondo non serve (fuori centro invece la fine
    # della tenuta e' il punto in cui il wheel torna a 0, sotto)
    while len(steps) > 1 and _value(steps[-1][1]) == _value(steps[-2][1]) == "0":
        steps.pop()
    tokens = [f"{CURVE_GRID}:"]
    position = 0
    for i, (step, semitones) in enumerate(steps):
        gap = step - position
        if gap > 0:
            tokens.append(f"{gap}r" if gap > 1 else "r")
            position = step
        tokens.append(f"bend={_value(semitones)}")
        following = steps[i + 1] if i + 1 < len(steps) else None
        # rampa verso il punto dopo, se e' piu' avanti e su un altro valore
        if (following is not None and following[0] > step
                and _value(following[1]) != _value(semitones)):
            tokens.append(">>")
    # in fondo il wheel torna al centro, come dopo una nota
    if _value(steps[-1][1]) != "0":
        tokens.append("bend=0")
    return " ".join(tokens)


def bend_curve_voice(events: Sequence[Tuple[int, int]], bend_range: float, ticks_per_beat: int,
                     notes: Sequence[tuple]) -> Optional[str]:
    """La voce della curva per tutta la traccia (dall'inizio del brano alla
    fine dell'ultima nota 'notes' [(inizio, fine, nota, velocity)]); None se
    il wheel non si muove abbastanza (resta allora l'import di sempre)."""
    if not notes:
        return None
    first = min(n[0] for n in notes)
    last = max(n[1] for n in notes)
    peak = max((abs(raw) / 8192.0 * bend_range for tick, raw in events if first <= tick <= last), default=0.0)
    if peak < MIN_CURVE_SEMITONES:
        return None
    return bend_curve_span(events, bend_range, ticks_per_beat, 0, last)


def strip_slides(channel) -> None:
    """Le note del canale senza slide: la curva le piega gia' tutte."""
    for attr in ("bends", "bend_release", "bend_onset", "bend_paths"):
        getattr(channel, attr).clear()


def with_curve(text: str, curve: Optional[str]) -> str:
    """Il testo della traccia con la voce della curva in parallelo."""
    if not curve:
        return text
    return "{ " + text + " ; " + curve + " }"


class TrackCurve:
    """La curva di una traccia importata, per rimetterla nei box dopo la
    divisione (vedi split_with_curves): il testo senza curva e i dati del
    canale."""

    def __init__(self, plain_text: str, events, bend_range: float, ticks_per_beat: int):
        self.plain_text = plain_text
        self.events = list(events)
        self.bend_range = bend_range
        self.ticks_per_beat = ticks_per_beat


def split_with_curves(project, split_track_into_boxes) -> None:
    """Divide in box le tracce del progetto importato (split_track_into_boxes,
    vedi core.box_conversion): quelle con la curva si dividono sulle sole
    note, poi ogni box riceve il pezzo di curva del suo tratto, senza
    allungarsi. Senza la divisione la curva resta su tutta la traccia."""
    from .arrangement import clip_duration_beats, flatten_clips_to_text
    curves = getattr(project, "imported_bend_curves", None) or {}
    for track in project.tracks:
        data = curves.get(track.name)
        if data is None:
            split_track_into_boxes(project, track)
            continue
        whole = track.text
        track.text = data.plain_text
        split_track_into_boxes(project, track)
        if not track.clips:
            track.text = whole
            continue
        meter = project.meter()
        octave = track.instrument.default_octave
        tpb = data.ticks_per_beat
        for clip in track.clips:
            beats = clip_duration_beats(clip.text, project.patterns, octave, clip.start_beat, meter)
            start = int(round(clip.start_beat * tpb))
            curve = bend_curve_span(data.events, data.bend_range, tpb, start, start + int(round(beats * tpb)))
            clip.text = with_curve(clip.text, curve)
        track.text = flatten_clips_to_text(track.clips, project.patterns, octave, meter=meter)
    if curves:
        project.imported_bend_curves = {}
