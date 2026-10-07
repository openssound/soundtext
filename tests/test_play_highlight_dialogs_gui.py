"""
Test GUI (PySide6, offscreen) dell'evidenziazione di cio' che sta suonando
(gui.play_highlight.PlayHighlighter) nei dialoghi che la usano oltre a
quelli di generazione (vedi tests/test_rhythm_generate_dialog_preview.py):
modifica del box, "Suona con la tastiera", conversione audio.

Esecuzione:
    python3 -m pytest tests/test_play_highlight_dialogs_gui.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication

from core.model import Project
from gui.audio_import_dialog import AudioImportDialog
from gui.box_edit_dialog import BoxEditDialog
from gui.keyboard_play_dialog import KeyboardPlayDialog

_app = QApplication.instance() or QApplication([])


class ClockPlayback:
    """Riproduzione finta in streaming: position_seconds dice a che punto e'."""

    def __init__(self):
        self.seconds = None
        self.played = []

    def play(self, project, **kwargs):
        self.played.append(project)
        self.seconds = 0.0

    def stop(self):
        self.seconds = None

    def is_playing(self):
        return self.seconds is not None

    def position_seconds(self):
        return self.seconds


def _highlighted_at(editor, highlighter, playback, seconds):
    playback.seconds = seconds
    highlighter._update()
    sel = editor.extraSelections()
    return sel[0].cursor.selectedText() if sel else None


def _check(editor, highlighter, playback, stop):
    # 120 BPM: 1 beat = 0,5 s; "4: c d e f" = una nota per beat
    assert _highlighted_at(editor, highlighter, playback, 0.1) == "c"
    assert _highlighted_at(editor, highlighter, playback, 1.1) == "e"
    stop()
    assert not highlighter.is_active() and editor.extraSelections() == []


def test_box_edit_dialog_highlights_what_is_playing():
    dlg = BoxEditDialog(None, Project(name="t"), "Piano", 120, clip_text="4: c d e f")
    dlg._playback = ClockPlayback()
    dlg._play()
    _check(dlg.body_edit, dlg._play_highlight, dlg._playback, dlg._stop)


def test_keyboard_dialog_preview_highlights_what_is_playing():
    dlg = KeyboardPlayDialog(None, project=Project(name="t", tempo_bpm=120), instrument_name="Piano",
                             context_label="test")
    dlg._preview_playback = ClockPlayback()
    dlg.preview_edit.setPlainText("4: c d e f")
    dlg._on_preview_play()
    _check(dlg.preview_edit, dlg._preview_highlight, dlg._preview_playback, dlg._stop_preview_playback)


def test_audio_import_dialog_preview_highlights_what_is_playing():
    dlg = AudioImportDialog(None, Project(name="t", tempo_bpm=120), "Piano", "test")
    dlg._preview_playback = ClockPlayback()
    dlg.preview_edit.setPlainText("4: c d e f")
    dlg._on_preview_play()
    _check(dlg.preview_edit, dlg._preview_highlight, dlg._preview_playback, dlg._stop_preview_playback)


def test_pattern_editor_highlights_the_pattern_body_while_playing():
    from core.model import Pattern
    from gui.pattern_editor_dialog import PatternEditorDialog
    p = Project(name="t", tempo_bpm=120)
    p.patterns["Riff"] = Pattern(name="Riff", tokens=["4:", "c", "d", "e", "f"])
    dlg = PatternEditorDialog(p)
    dlg._playback = ClockPlayback()
    dlg.body_edit.setPlainText("4: c d e f")
    dlg._play_current()
    _check(dlg.body_edit, dlg._play_highlight, dlg._playback, dlg._stop_playback)
    dlg._play_current()
    dlg.reject()                                    # Esc: ferma anche l'ascolto
    assert not dlg._play_highlight.is_active() and not dlg._playback.is_playing()


# --------------------------------------------------------------- Play della selezione

def _choose_from_context_menu(editor, sel_start, sel_end, choose=None):
    """Seleziona [sel_start, sel_end) nell'editor, apre il menu del tasto
    destro sulla selezione e, se choose e' dato, sceglie quella voce.
    Ritorna i testi delle voci del menu."""
    from PySide6.QtCore import QPoint, QTimer
    from PySide6.QtGui import QContextMenuEvent, QTextCursor
    from PySide6.QtTest import QTest
    from PySide6.QtCore import Qt
    cursor = editor.textCursor()
    cursor.setPosition(sel_start)
    cursor.setPosition(sel_end, QTextCursor.KeepAnchor)
    editor.setTextCursor(cursor)
    captured = {}

    def pick():
        menu = QApplication.activePopupWidget()
        if menu is None:
            return
        captured["actions"] = [a.text() for a in menu.actions() if a.text()]
        target = next((a for a in menu.actions() if a.text() == choose), None)
        if target is None:
            menu.close()
            return
        menu.setActiveAction(target)
        QTest.keyClick(menu, Qt.Key_Return)

    QTimer.singleShot(50, pick)
    pos = QPoint(5, 5)
    editor.contextMenuEvent(QContextMenuEvent(QContextMenuEvent.Mouse, pos, editor.mapToGlobal(pos)))
    return captured.get("actions", [])


def test_generate_dialog_preview_offers_play_of_the_selection():
    from gui.rhythm_generate_dialog import ChordProgressionDialog
    dlg = ChordProgressionDialog(None, Project(name="t", tempo_bpm=120), "Piano", "nuovo box", track_name="Piano")
    dlg._playback = ClockPlayback()
    dlg.preview_edit.setPlainText("4: 4C 4F 4G 4C")
    dlg._play_preview()                                    # ascolto completo in corso...
    actions = _choose_from_context_menu(dlg.preview_edit, 6, 12, choose="▶ Play")   # "4F 4G"
    assert actions == ["▶ Play", "View"]                 # nei dialoghi solo Play e View
    assert not dlg._play_highlight.is_active()             # ...fermato con la sua evidenziazione
    played = dlg._playback.played[-1].tracks[0].text
    assert played.endswith("4F 4G") and "4C" not in played


def test_keyboard_and_audio_previews_offer_play_of_the_selection():
    for dlg in (KeyboardPlayDialog(None, project=Project(name="t"), instrument_name="Piano", context_label="t"),
                AudioImportDialog(None, Project(name="t"), "Piano", "test")):
        dlg._preview_playback = ClockPlayback()
        dlg.preview_edit.setPlainText("4: c d e f")
        _choose_from_context_menu(dlg.preview_edit, 5, 8, choose="▶ Play")        # "d e"
        played = dlg._preview_playback.played[-1].tracks[0].text
        assert played.endswith("d e") and " c" not in played and "f" not in played, (type(dlg), played)


def test_box_editor_selection_menu_keeps_all_its_actions():
    dlg = BoxEditDialog(None, Project(name="t"), "Piano", 120, clip_text="4: c d e f")
    actions = _choose_from_context_menu(dlg.body_edit, 3, 6)
    assert actions == ["▶ Play", "View", "Raggruppa", "Trasforma in pattern..."]


def test_selection_menu_view_shows_the_score_of_the_selection(monkeypatch):
    shown = []
    monkeypatch.setattr("gui.score_view.show_selection_score", lambda parent, project: shown.append(project))
    dlg = BoxEditDialog(None, Project(name="t"), "Piano", 120, clip_text="4: c d e f")
    _choose_from_context_menu(dlg.body_edit, 5, 8, choose="View")                 # "d e"
    assert len(shown) == 1
    text = shown[0].tracks[0].text
    assert text.endswith("d e") and "f" not in text
