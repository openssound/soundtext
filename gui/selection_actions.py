"""
Menu contestuale (tasto destro) su una selezione di token nell'editor della
notazione (traccia o corpo di un pattern): Play (ascolta la selezione),
View (la mostra in partitura),
Raggruppa (la racchiude tra parentesi tonde, N(...)), Trasforma in
pattern... (la sostituisce con un riferimento %Nome a un nuovo pattern
contenente la selezione). Se la selezione include un riferimento a un
pattern (%Nome) o a un file MIDI (&Nome), solo Play e View vengono proposti: non ha
senso raggruppare o "impacchettare in un pattern" un'indirezione gia'
esistente (vedi _is_reusable_ref).
"""

import re
from typing import Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import QPoint
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QMenu, QInputDialog, QMessageBox, QPlainTextEdit

from core.arrangement import anchored_preview_text, has_bar_anchor
from core.model import Project, Track, copy_synth
from core.notation import (
    tokenize, RE_GRID, RE_VELOCITY, Pattern, validate_track_text, compute_token_spans,
    all_token_spans as _all_token_spans, context_prefix_before as _context_prefix_before,
)
from core.instruments import InstrumentProfile
from core.playback import PlaybackEngine
from core.i18n import tr

_VALID_PATTERN_NAME = re.compile(r"^\w+$")


# ---------------------------------------------------------------------------
# Individuazione dei token di primo livello e aggancio della selezione
# ---------------------------------------------------------------------------
#
# _all_token_spans/_context_prefix_before sono ora in core.notation
# (all_token_spans/context_prefix_before), riusabili anche fuori dalla GUI
# (vedi core.arrangement.split_text_into_box_segments): qui restano solo
# come alias locali, per non toccare tutti i richiami sottostanti.

def _is_reusable_ref(tok: str) -> bool:
    stripped = tok.lstrip("0123456789")
    return stripped.startswith("%") or stripped.startswith("&")


def _is_state_command(tok: str) -> bool:
    return bool(RE_GRID.match(tok) or RE_VELOCITY.match(tok))


def snap_selection_to_tokens(text: str, sel_start: int, sel_end: int
                              ) -> Optional[Tuple[int, int, List[str]]]:
    """Espande [sel_start, sel_end) al piu' piccolo intervallo che contiene
    per intero ogni token di primo livello con cui si sovrappone, poi
    scarta un eventuale comando di stato (N:/N@) rimasto in fondo (un
    gruppo o un pattern non deve mai terminare "in sospeso", con un cambio
    di griglia/velocity senza alcun evento sonoro associato — stessa regola
    di core.reorganize._is_state_command). Ritorna (char_start, char_end,
    tokens) oppure None se la selezione non contiene nulla di utilizzabile."""
    spans = _all_token_spans(text)
    overlapping = [(cs, ce) for cs, ce in spans if cs < sel_end and ce > sel_start]
    while overlapping and _is_state_command(text[overlapping[-1][0]:overlapping[-1][1]]):
        overlapping = overlapping[:-1]
    if not overlapping:
        return None
    char_start = overlapping[0][0]
    char_end = overlapping[-1][1]
    tokens = [text[cs:ce] for cs, ce in overlapping]
    return char_start, char_end, tokens


# ---------------------------------------------------------------------------
# Azioni
# ---------------------------------------------------------------------------

def _replace_range(editor: QPlainTextEdit, char_start: int, char_end: int, replacement: str):
    cursor = editor.textCursor()
    cursor.setPosition(char_start)
    cursor.setPosition(char_end, QTextCursor.KeepAnchor)
    cursor.insertText(replacement)


def _preview_project(tempo_bpm: int, host_project: Optional[Project]) -> Project:
    """Progetto provvisorio per un'anteprima, con la metrica del brano (per
    le ancore bar=N)."""
    if host_project is None:
        return Project(name="preview", tempo_bpm=tempo_bpm)
    return Project(name="preview", tempo_bpm=tempo_bpm, time_sig=host_project.time_sig,
                   metrica_changes=list(host_project.metrica_changes))


def _selection_origin(full_text: str, char_start: int, patterns: Dict[str, Pattern], default_octave: int,
                      midi_dir: Optional[str], host_project: Optional[Project], origin_beat: float) -> float:
    """Il beat del brano in cui comincia la selezione: l'inizio del testo
    nel brano (origin_beat) piu' dove la selezione cade nel testo."""
    meter = host_project.meter() if host_project is not None else None
    try:
        spans = compute_token_spans(full_text, patterns, midi_dir=midi_dir, default_octave=default_octave,
                                    meter=meter, origin_beat=origin_beat)
    except Exception:
        return origin_beat
    after = [span[2] for span in spans if span[0] >= char_start]
    return origin_beat + (min(after) if after else 0.0)


def _play_selection(editor: QPlainTextEdit, playback: PlaybackEngine,
                     patterns: Dict[str, Pattern], instrument_name: str, tempo_bpm: int,
                     full_text: str, char_start: int, selected_text: str,
                     default_octave: int, midi_dir: Optional[str], synth_track: Optional[Track] = None,
                     host_project: Optional[Project] = None, origin_beat: float = 0.0):
    combined = (_context_prefix_before(full_text, char_start) + selected_text).strip()
    ok, msg = validate_track_text(combined, patterns, default_octave=default_octave, midi_dir=midi_dir)
    if not ok:
        QMessageBox.critical(editor, tr("Errore di sintassi"), tr("Impossibile riprodurre la selezione:\n{msg}", msg=msg))
        return
    project = _preview_project(tempo_bpm, host_project)
    project.patterns = patterns
    lead = 0.0
    if host_project is not None and has_bar_anchor(combined, patterns, midi_dir):
        # Con le ancore bar=N la selezione suona dal suo punto del brano.
        start = _selection_origin(full_text, char_start, patterns, default_octave, midi_dir,
                                  host_project, origin_beat)
        combined, lead = anchored_preview_text(combined, start, patterns, midi_dir)
    copy_synth(project.add_track("Anteprima", instrument_name, combined), synth_track)
    playback.play(project, only_audible=False, start_offset_beats=lead)


def _view_selection(editor: QPlainTextEdit, patterns: Dict[str, Pattern], instrument_name: str,
                     tempo_bpm: int, full_text: str, char_start: int, selected_text: str,
                     default_octave: int, midi_dir: Optional[str], synth_track: Optional[Track] = None):
    """Mostra la selezione in partitura (stessa anteprima di Play)."""
    combined = (_context_prefix_before(full_text, char_start) + selected_text).strip()
    ok, msg = validate_track_text(combined, patterns, default_octave=default_octave, midi_dir=midi_dir)
    if not ok:
        QMessageBox.critical(editor, tr("Errore di sintassi"), tr("Impossibile mostrare la selezione:\n{msg}", msg=msg))
        return
    from .score_view import show_selection_score
    project = Project(name="preview", tempo_bpm=tempo_bpm)
    project.patterns = patterns
    copy_synth(project.add_track("Anteprima", instrument_name, combined), synth_track)
    show_selection_score(editor, project)


def _transform_into_pattern(editor: QPlainTextEdit, patterns: Dict[str, Pattern],
                             char_start: int, char_end: int, selected_text: str):
    name, ok = QInputDialog.getText(editor, tr("Trasforma in pattern"), tr("Nome del nuovo pattern (senza %):"))
    if not ok:
        return
    name = name.strip()
    if not name:
        return
    if not _VALID_PATTERN_NAME.match(name):
        QMessageBox.warning(
            editor, tr("Nome non valido"),
            tr("Il nome del pattern puo' contenere solo lettere, cifre e underscore (nessuno spazio).")
        )
        return
    if name in patterns:
        reply = QMessageBox.question(
            editor, tr("Pattern gia' esistente"),
            tr("Esiste gia' un pattern '%{name}': sovrascriverlo?", name=name)
        )
        if reply != QMessageBox.Yes:
            return
    patterns[name] = Pattern(name=name, tokens=tokenize(selected_text))
    _replace_range(editor, char_start, char_end, f"%{name}")


# ---------------------------------------------------------------------------
# Orchestrazione: dal tasto destro al menu (o al fallback nativo)
# ---------------------------------------------------------------------------

def handle_selection_context_menu(editor: QPlainTextEdit, text: str, sel_start: int, sel_end: int,
                                   patterns: Dict[str, Pattern], instrument: InstrumentProfile,
                                   instrument_name: str, tempo_bpm: int, playback: PlaybackEngine,
                                   global_pos: QPoint, midi_dir: Optional[str] = None,
                                   play_only: bool = False,
                                   before_play: Optional[Callable[[], None]] = None,
                                   synth_track: Optional[Track] = None,
                                   host_project: Optional[Project] = None,
                                   origin_beat: float = 0.0) -> bool:
    """Punto di ingresso unico per un tasto-destro con selezione attiva:
    ritorna True se la selezione conteneva almeno un token utilizzabile
    (menu contestuale mostrato, indipendentemente dal fatto che l'utente
    abbia scelto una voce o l'abbia chiuso senza scegliere), False se va
    lasciato il menu contestuale nativo dell'editor (nessuna selezione
    utile, es. solo spazi).

    play_only: solo Play e View (anteprime dei dialoghi, dove Raggruppa/Trasforma
    in pattern non servono). before_play: richiamato prima di suonare la
    selezione, es. per fermare l'evidenziazione di un ascolto in corso
    sullo stesso playback (vedi gui.play_highlight). synth_track: la traccia
    reale di cui si ascolta la selezione, se suonata da uno strumento plugin.
    host_project/origin_beat: il brano e il beat in cui il testo dell'editor
    vi comincia (una traccia: 0; un box: il suo inizio), perche' le ancore
    bar=N della selezione cadano nella battuta giusta."""
    snap = snap_selection_to_tokens(text, sel_start, sel_end)
    if snap is None:
        return False
    char_start, char_end, tokens = snap
    selected_text = text[char_start:char_end]
    has_refs = play_only or any(_is_reusable_ref(t) for t in tokens)

    menu = QMenu(editor)
    play_action = menu.addAction(tr("▶ Play"))
    view_action = menu.addAction(tr("View"))
    group_action = None
    pattern_action = None
    if not has_refs:
        group_action = menu.addAction(tr("Raggruppa"))
        pattern_action = menu.addAction(tr("Trasforma in pattern..."))

    chosen = menu.exec(global_pos)
    if chosen is play_action:
        if before_play is not None:
            before_play()
        _play_selection(editor, playback, patterns, instrument_name, tempo_bpm,
                         text, char_start, selected_text, instrument.default_octave, midi_dir, synth_track,
                         host_project=host_project, origin_beat=origin_beat)
    elif chosen is view_action:
        _view_selection(editor, patterns, instrument_name, tempo_bpm,
                        text, char_start, selected_text, instrument.default_octave, midi_dir, synth_track)
    elif group_action is not None and chosen is group_action:
        _replace_range(editor, char_start, char_end, f"({selected_text})")
    elif pattern_action is not None and chosen is pattern_action:
        _transform_into_pattern(editor, patterns, char_start, char_end, selected_text)

    return True
