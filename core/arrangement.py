"""
Logica di supporto per la vista "Struttura brano": durata di un box (Clip) e
appiattimento di una lista di box posizionati nel tempo nell'unico blocco di
testo st-language che core.notation/core.playback/core.midi_export sanno gia'
consumare (Track.text) - vedi core.model.Clip/Track.clips.

Salvataggio/caricamento del singolo box su file .box: stesso stile testuale
leggibile a mano del formato .st (core.project_io), ma a blocco singolo.
"""

import bisect
import itertools
import math
import re
from fractions import Fraction
from typing import Dict, List, Optional, Tuple

from .model import Clip
from .notation import (Pattern, compute_token_spans, context_prefix_before, RE_REST,
                       BAR_CHECK, all_token_spans, is_lyric, tokenize, expand_patterns,
                       RE_BAR_ANCHOR, NotationError, upgrade_midi_refs, Meter, RE_TEMPO_SET)
from .i18n import tr
from st_language.song import (  # noqa: F401  (unione dei box: nella libreria)
    FILL_GRID_BEATS, _FILL_GRID_TOKEN, _DEFAULT_STATE_PREFIX, clip_duration_beats, flatten_clips_to_text,
)


RE_BOX_FILE_HDR = re.compile(r'^Box\s+"(.*)"\s*:$')

# Oltre questa pausa continua (in beat/quarti) core.arrangement.
# split_text_into_box_segments apre un nuovo box invece di includerla nel
# box corrente: "piu' di tre pause" nel senso comune di tre note/pause della
# griglia di default (1/4 = 1 beat).
GAP_SPLIT_THRESHOLD_BEATS = 3.0


def split_text_into_box_segments(text: str, patterns: Dict[str, Pattern], default_octave: int,
                                  gap_threshold_beats: float = GAP_SPLIT_THRESHOLD_BEATS,
                                  meter: Optional[Meter] = None) -> List[Tuple[float, str]]:
    """Divide il testo di una traccia in segmenti (start_beat, testo) nei
    punti dove una pausa continua supera gap_threshold_beats beat, scartando
    le pause iniziali/finali di ogni segmento (il vuoto tra un segmento e il
    successivo, se diventano box, viene poi ricostruito automaticamente da
    flatten_clips_to_text - qui si minimizzano solo le pause "incollate"
    dentro il testo di un box). Un gap piu' breve della soglia resta incluso
    nel segmento cosi' com'e' (non vale la pena spezzare per una pausa
    breve). Ogni segmento porta con se' l'ultimo comando di griglia/velocity
    attivo nel punto in cui inizia (vedi core.notation.context_prefix_before),
    cosi' suona esattamente come nel testo originale anche se poi, diventando
    un box, viene fatto precedere dal reset di stato di default di un box
    (vedi _DEFAULT_STATE_PREFIX/flatten_clips_to_text - i due si sommano
    senza conflitti, l'ultimo vince).

    Con 'meter' ogni segmento comincia all'inizio della battuta in cui cade
    la sua prima nota, con una pausa fino a quella nota (vedi
    _snap_to_bar_starts): i box si allineano alle battute e il brano suona
    uguale.

    Se il testo non contiene pause abbastanza lunghe da dividerlo, ritorna
    un solo segmento (start_beat 0.0, testo invariato) - stesso comportamento
    di prima di avere questa funzione."""
    spans = compute_token_spans(text, patterns, default_octave=default_octave)
    segments: List[Tuple[float, int, int]] = []
    seg_end_beats: List[float] = []
    seg_start_beat = seg_start_char = seg_end_char = None
    seg_end_beat = 0.0
    trailing_rest = 0.0

    for char_start, char_end, beat_start, beat_duration in spans:
        is_rest = bool(RE_REST.match(text[char_start:char_end]))
        if is_rest:
            if seg_start_char is not None:
                trailing_rest += beat_duration
            continue
        if seg_start_char is None:
            seg_start_beat, seg_start_char = beat_start, char_start
        elif trailing_rest > gap_threshold_beats:
            segments.append((seg_start_beat, seg_start_char, seg_end_char))
            seg_end_beats.append(seg_end_beat)
            seg_start_beat, seg_start_char = beat_start, char_start
        trailing_rest = 0.0
        seg_end_char = char_end
        seg_end_beat = max(seg_end_beat, beat_start + beat_duration)

    if seg_start_char is not None:
        segments.append((seg_start_beat, seg_start_char, seg_end_char))
        seg_end_beats.append(seg_end_beat)

    if not segments:
        return [(0.0, text.strip())]
    # Un testo cantato o una '|' subito dopo l'ultima nota di un segmento
    # (non occupano tempo, quindi non hanno uno span) restano col segmento.
    all_spans = all_token_spans(text)
    extended = []
    for start_beat, cs, ce in segments:
        for a, b in all_spans:
            if a < ce:
                continue
            if not (is_lyric(text[a:b]) or text[a:b] == BAR_CHECK):
                break
            ce = b
        extended.append((start_beat, cs, ce))
    # Un cambio di tempo (tempo=N, non occupa tempo) fra due segmenti o prima
    # del primo andrebbe perso con la pausa che lo contiene, e con lui il
    # tempo di tutto il seguito: la traccia resta un solo box.
    if any(RE_TEMPO_SET.match(text[a:b]) and not any(cs <= a < ce for _s, cs, ce in extended)
           for a, b in all_spans):
        return [(0.0, text.strip())]
    result = [
        (start_beat, (context_prefix_before(text, cs) + text[cs:ce]).strip())
        for start_beat, cs, ce in extended
    ]
    if meter is not None:
        result = _snap_to_bar_starts(result, seg_end_beats, meter)
    return _align_to_fill_grid(result, seg_end_beats)


def _rest_text(beats: float) -> Optional[str]:
    """Una pausa di 'beats' quarti in notazione ("16: 3r", "12: 2r" per le
    terzine...), o None se non si scrive esatta con una griglia fino a 1/192."""
    value = Fraction(beats).limit_denominator(192)
    if abs(float(value) - beats) > 1e-6 or value <= 0:
        return None
    for grid in (4, 8, 16, 32, 64, 6, 12, 24, 48, 96, 192):
        count = value * grid / 4
        if count.denominator == 1:
            return f"{grid}: {count.numerator}r"
    return None


def _align_to_fill_grid(segments: List[Tuple[float, str]], end_beats: List[float]
                        ) -> List[Tuple[float, str]]:
    """flatten_clips_to_text riempie lo spazio fra un box e l'altro a
    sedicesimi (FILL_GRID_BEATS): un box che comincia o finisce fuori da
    quella griglia (in terzina, a 295,333...) farebbe slittare tutto il
    seguito dell'arrotondamento. Qui ogni segmento comincia e finisce sulla
    griglia, con una pausa esatta prima e dopo le note: lo spazio fra i
    segmenti (piu' di GAP_SPLIT_THRESHOLD_BEATS) assorbe i due ritocchi."""
    grid = FILL_GRID_BEATS
    out = []
    for (start, body), end in zip(segments, end_beats):
        on_grid = math.floor(start / grid + 1e-9) * grid
        lead = _rest_text(start - on_grid) if start - on_grid > 1e-6 else None
        if lead:
            start, body = on_grid, f"{lead} {_DEFAULT_STATE_PREFIX}{body}"
        tail_beats = math.ceil(end / grid - 1e-9) * grid - end
        tail = _rest_text(tail_beats) if tail_beats > 1e-6 else None
        out.append((start, f"{body} {tail}" if tail else body))
    return out


def _snap_to_bar_starts(segments: List[Tuple[float, str]], end_beats: List[float],
                        meter: Meter) -> List[Tuple[float, str]]:
    """Fa cominciare ogni segmento all'inizio della battuta della sua prima
    nota, con una pausa fino alla nota e poi 'reset:' (che riporta griglia e
    velocity allo stato iniziale, come all'inizio di un box). Un segmento resta
    dov'e' se l'inizio della battuta cade prima della fine del segmento
    precedente (i box si sovrapporrebbero) o se la pausa non si scrive esatta."""
    if not segments:
        return segments
    last = max(start for start, _ in segments)
    starts = [0.0]       # 0: anche l'eventuale battuta in levare (la 0)
    for bar in itertools.count(1):
        starts.append(float(meter.start_of(bar)))
        if starts[-1] > last:
            break
    out = []
    prev_end = 0.0
    for (start, body), end in zip(segments, end_beats):
        bar = starts[bisect.bisect_right(starts, start + 1e-9) - 1]
        gap = start - bar
        rest = _rest_text(gap) if gap > 1e-6 and bar >= prev_end - 1e-6 else None
        out.append((bar, f"{rest} {_DEFAULT_STATE_PREFIX}{body}") if rest else (start, body))
        prev_end = end
    return out


def has_bar_anchor(text: str, patterns: Dict[str, Pattern], midi_dir: Optional[str] = None) -> bool:
    """True se il testo (o un pattern che richiama) contiene un'ancora bar=N."""
    tokens = tokenize(text)
    try:
        tokens = expand_patterns(tokens, patterns, midi_dir=midi_dir)
    except (NotationError, ValueError):
        pass
    return any(RE_BAR_ANCHOR.match(t) for t in tokens)


def anchored_preview_text(text: str, origin_beat: float, patterns: Dict[str, Pattern],
                          midi_dir: Optional[str] = None) -> Tuple[str, float]:
    """Per ascoltare da solo un testo che nel brano comincia al beat
    origin_beat (un box, una selezione): se contiene ancore bar=N, il testo
    preceduto da una pausa fino a origin_beat - cosi' l'ancora porta alla
    battuta giusta del brano e non a quella contata da 0 - e il beat da cui
    far partire l'ascolto (la pausa non si sente). Senza ancore, o a 0, il
    testo resta com'e' e l'ascolto parte da 0."""
    if origin_beat <= 0 or not has_bar_anchor(text, patterns, midi_dir):
        return text, 0.0
    n = round(origin_beat / FILL_GRID_BEATS)
    if n <= 0:
        return text, 0.0
    return f"{_FILL_GRID_TOKEN} {n}r {_DEFAULT_STATE_PREFIX}{text}", n * FILL_GRID_BEATS


def save_box_file(clip: Clip, path: str) -> None:
    """Salva un singolo box su disco (per riuso/libreria: import in
    un'altra traccia o un altro progetto)."""
    name = clip.name.replace('"', "'")
    body = "\n".join("  " + line for line in clip.text.splitlines())
    with open(path, "w", encoding="utf-8") as f:
        f.write(f'Box "{name}":\n{body}\n')


def load_box_file(path: str) -> Clip:
    """Carica un box salvato con save_box_file. start_beat resta a 0.0: la
    posizione va decisa da chi importa (punto di rilascio nel canvas)."""
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    if not lines:
        raise ValueError(tr("File .box vuoto: {path}", path=path))
    m = RE_BOX_FILE_HDR.match(lines[0].strip())
    if not m:
        raise ValueError(tr("File .box non valido (intestazione mancante): {path}", path=path))
    name = m.group(1)
    body_lines = [line[2:] if line.startswith("  ") else line for line in lines[1:]]
    text = upgrade_midi_refs("\n".join(body_lines).strip())     # &Nome delle versioni prima della 2.6
    return Clip(name=name, text=text, start_beat=0.0)
