"""
Logica di supporto per la vista "Struttura brano": durata di un box (Clip) e
appiattimento di una lista di box posizionati nel tempo nell'unico blocco di
testo st-language che core.notation/core.playback/core.midi_export sanno gia'
consumare (Track.text) - vedi core.model.Clip/Track.clips.

Salvataggio/caricamento del singolo box su file .box: stesso stile testuale
leggibile a mano del formato .st (core.project_io), ma a blocco singolo.
"""

import re
from typing import Dict, List, Optional, Tuple

from .model import Clip
from .notation import (Pattern, parse_track_text, compute_token_spans, context_prefix_before, RE_REST,
                       COMMENT_MARK, BAR_CHECK, all_token_spans, is_lyric, tokenize, expand_patterns,
                       RE_BAR_ANCHOR, NotationError, upgrade_midi_refs)
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
                                  gap_threshold_beats: float = GAP_SPLIT_THRESHOLD_BEATS
                                  ) -> List[Tuple[float, str]]:
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

    Se il testo non contiene pause abbastanza lunghe da dividerlo, ritorna
    un solo segmento (start_beat 0.0, testo invariato) - stesso comportamento
    di prima di avere questa funzione."""
    spans = compute_token_spans(text, patterns, default_octave=default_octave)
    segments: List[Tuple[float, int, int]] = []
    seg_start_beat = seg_start_char = seg_end_char = None
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
            seg_start_beat, seg_start_char = beat_start, char_start
        trailing_rest = 0.0
        seg_end_char = char_end

    if seg_start_char is not None:
        segments.append((seg_start_beat, seg_start_char, seg_end_char))

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
    return [
        (start_beat, (context_prefix_before(text, cs) + text[cs:ce]).strip())
        for start_beat, cs, ce in extended
    ]


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
