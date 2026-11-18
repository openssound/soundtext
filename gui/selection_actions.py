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
from PySide6.QtGui import QAction, QTextCursor
from PySide6.QtWidgets import QMenu, QInputDialog, QMessageBox, QPlainTextEdit

from core.arrangement import anchored_preview_text, has_bar_anchor
from core.model import Project, Track, copy_synth
from core.notation import (
    tokenize, NotationError, RE_ARP, RE_GRID, RE_VELOCITY, Pattern, validate_track_text, compute_token_spans, upgrade_pattern_state,
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
    return bool(RE_GRID.match(tok) or RE_VELOCITY.match(tok) or RE_ARP.match(tok))


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
                   metrica_changes=list(host_project.metrica_changes), key=host_project.key,
                   key_changes=list(host_project.key_changes))


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
                     default_octave: int, midi_dir: Optional[str], synth_track: Optional[Track] = None,
                     host_project: Optional[Project] = None):
    """Mostra la selezione in partitura (stessa anteprima di Play)."""
    combined = (_context_prefix_before(full_text, char_start) + selected_text).strip()
    ok, msg = validate_track_text(combined, patterns, default_octave=default_octave, midi_dir=midi_dir)
    if not ok:
        QMessageBox.critical(editor, tr("Errore di sintassi"), tr("Impossibile mostrare la selezione:\n{msg}", msg=msg))
        return
    from .score_view import show_selection_score
    project = _preview_project(tempo_bpm, host_project)
    project.patterns = patterns
    # Il nome della traccia e' quello scritto accanto al pentagramma: lo
    # strumento, non "Anteprima" (che restava in italiano in ogni lingua).
    copy_synth(project.add_track(instrument_name or "Anteprima", instrument_name, combined), synth_track)
    show_selection_score(editor, project)


def _replace_with_pattern(editor: QPlainTextEdit, char_start: int, char_end: int, name: str, pattern: Pattern):
    """La selezione diventa %name. Quello che il pattern scrive finisce con
    lui: se le note dopo lo usavano, upgrade_pattern_state lo riscrive dopo il
    richiamo (solo per questo pattern, gli altri richiami seguono gia' la
    regola). Una modifica sola per Annulla."""
    text = editor.toPlainText()
    written = text[:char_start] + f"%{name}" + text[char_end:]
    upgraded = upgrade_pattern_state(written, {name: pattern})
    tail = 0                # la coda uguale resta fuori dalla sostituzione
    while tail < min(len(text) - char_end, len(upgraded) - char_start) and text[-1 - tail] == upgraded[-1 - tail]:
        tail += 1
    _replace_range(editor, char_start, len(text) - tail, upgraded[char_start:len(upgraded) - tail])


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
    _replace_with_pattern(editor, char_start, char_end, name, patterns[name])


def open_transform(editor: QPlainTextEdit, char_start: int, char_end: int, token: str, project: Project,
                   track: Track, playback: PlaybackEngine, origin_beat: float = 0.0,
                   on_pattern_created: Optional[Callable[[], None]] = None):
    """La finestra Trasforma sul richiamo [char_start, char_end) dell'editor:
    il testo si riscrive con l'editor, quindi entra in Annulla/Ripeti."""
    from core.transform_preview import reference_point
    from .transform_dialog import TransformDialog
    point = reference_point(editor.toPlainText(), char_start, project.patterns, track.instrument,
                            project.meter(), origin_beat)
    dialog = TransformDialog(editor, project, playback, track.instrument_name, track, token=token, point=point)
    if dialog.exec() != TransformDialog.Accepted:
        return
    if dialog.result_token and dialog.result_token != token:
        _replace_range(editor, char_start, char_end, dialog.result_token)
    if dialog.freeze:
        freeze_in_editor(editor, char_start, char_start + len(dialog.result_token), project, track, origin_beat)
    if dialog.created_pattern and on_pattern_created is not None:
        on_pattern_created()


def freeze_in_editor(editor: QPlainTextEdit, char_start: int, char_end: int, project: Project, track: Track,
                     origin_beat: float = 0.0) -> bool:
    """Congela la trasformazione su [char_start, char_end) dell'editor: una
    modifica sola per Annulla. Se il suono cambierebbe lo dice e non congela."""
    from core.settings import get_freeze_comment
    from core.transform_preview import freeze_span
    text = editor.toPlainText()
    try:
        frozen = freeze_span(text, char_start, char_end, project, track.instrument, origin_beat, get_freeze_comment())
    except (NotationError, ValueError) as e:
        QMessageBox.warning(editor, tr("Congela la trasformazione"), str(e))
        return False
    _replace_range(editor, char_start, char_end, frozen[char_start:len(frozen) - (len(text) - char_end)])
    return True


def _arpeggiate_token(editor: QPlainTextEdit, char_start: int, char_end: int, token: str, project: Project,
                      track: Track, playback: PlaybackEngine):
    """Arpeggia...: il suffisso .arpeggio(tipo,griglia) sull'accordo."""
    from core.transform_preview import with_arpeggio
    from .transform_dialog import ArpeggioDialog
    dialog = ArpeggioDialog(editor, tr("Arpeggia"), lambda kind, grid: with_arpeggio(token, kind, grid),
                            project, playback, track.instrument_name, track)
    if dialog.exec() == ArpeggioDialog.Accepted:
        _replace_range(editor, char_start, char_end, dialog.result_text())


def arp_selection_text(selected_text: str, kind: str, grid: str = "") -> str:
    """La selezione fra arp=tipo e arp=off."""
    return f"arp={kind}{',' + grid if grid else ''} {selected_text} arp=off"


def _arpeggiate_selection(editor: QPlainTextEdit, char_start: int, char_end: int, selected_text: str,
                          project: Project, track: Track, playback: PlaybackEngine):
    from .transform_dialog import ArpeggioDialog
    dialog = ArpeggioDialog(editor, tr("Arpeggia la selezione"),
                            lambda kind, grid: arp_selection_text(selected_text, kind, grid),
                            project, playback, track.instrument_name, track)
    if dialog.exec() == ArpeggioDialog.Accepted:
        _replace_range(editor, char_start, char_end, dialog.result_text())


def handle_token_context_menu(editor: QPlainTextEdit, pos: int, project: Project, track: Track,
                              playback: PlaybackEngine, global_pos: QPoint, origin_beat: float = 0.0,
                              on_pattern_created: Optional[Callable[[], None]] = None) -> bool:
    """Tasto destro senza selezione: su un richiamo Trasforma..., su un accordo
    Arpeggia..., sopra le voci di sempre dell'editor. False se il token sotto il
    mouse non ha voci sue (resta il menu nativo)."""
    from core.transform_preview import arp_region, arpeggiable, reference_at
    from st_language.transform import is_transform_reference
    text = editor.toPlainText()
    reference = reference_at(text, pos, with_functions=False)
    chord = None
    if reference is None:
        chord = next(((cs, ce) for cs, ce in _all_token_spans(text)
                      if cs <= pos < ce and arpeggiable(text[cs:ce])), None)
    if reference is None and chord is None:
        return False
    menu = editor.createStandardContextMenu()
    first = menu.actions()[0] if menu.actions() else None
    action = QAction(tr("Trasforma...") if reference else tr("Arpeggia..."), menu)
    menu.insertAction(first, action)
    # le note per esteso: un richiamo con funzioni, un accordo con .arpeggio, un tratto arp=
    frozen_span = None
    if reference is not None and is_transform_reference(reference[2]):
        frozen_span = reference[:2]
    elif chord is not None:
        frozen_span = arp_region(text, pos) or (chord if ".arpeggio" in text[chord[0]:chord[1]].lower() else None)
    freeze_action = None
    if frozen_span is not None:
        freeze_action = QAction(tr("Congela la trasformazione"), menu)
        menu.insertAction(first, freeze_action)
    menu.insertSeparator(first)
    chosen = menu.exec(global_pos)
    if freeze_action is not None and chosen is freeze_action:
        freeze_in_editor(editor, *frozen_span, project, track, origin_beat)
    elif chosen is action and reference is not None:
        open_transform(editor, *reference, project, track, playback, origin_beat, on_pattern_created)
    elif chosen is action:
        _arpeggiate_token(editor, *chord, text[chord[0]:chord[1]], project, track, playback)
    return True


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
    from core.transform_preview import arpeggiable

    menu = QMenu(editor)
    play_action = menu.addAction(tr("▶ Play"))
    view_action = menu.addAction(tr("View"))
    group_action = None
    pattern_action = None
    if not has_refs:
        group_action = menu.addAction(tr("Raggruppa"))
        pattern_action = menu.addAction(tr("Trasforma in pattern..."))
    # un solo richiamo selezionato: Trasforma...; degli accordi: Arpeggia la selezione...
    can_edit = not play_only and host_project is not None and synth_track is not None
    transform_action = arpeggio_action = None
    if can_edit and len(tokens) == 1 and tokens[0].lstrip("0123456789").startswith("%"):
        transform_action = menu.addAction(tr("Trasforma..."))
    elif can_edit and not has_refs and any(arpeggiable(t) for t in tokens):
        arpeggio_action = menu.addAction(tr("Arpeggia la selezione..."))

    chosen = menu.exec(global_pos)
    if chosen is play_action:
        if before_play is not None:
            before_play()
        _play_selection(editor, playback, patterns, instrument_name, tempo_bpm,
                         text, char_start, selected_text, instrument.default_octave, midi_dir, synth_track,
                         host_project=host_project, origin_beat=origin_beat)
    elif chosen is view_action:
        _view_selection(editor, patterns, instrument_name, tempo_bpm,
                        text, char_start, selected_text, instrument.default_octave, midi_dir, synth_track,
                        host_project=host_project)
    elif group_action is not None and chosen is group_action:
        _replace_range(editor, char_start, char_end, f"({selected_text})")
    elif pattern_action is not None and chosen is pattern_action:
        _transform_into_pattern(editor, patterns, char_start, char_end, selected_text)
    elif transform_action is not None and chosen is transform_action:
        open_transform(editor, char_start, char_end, selected_text, host_project, synth_track, playback, origin_beat)
    elif arpeggio_action is not None and chosen is arpeggio_action:
        _arpeggiate_selection(editor, char_start, char_end, selected_text, host_project, synth_track, playback)

    return True
