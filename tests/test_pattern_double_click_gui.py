"""
Test GUI (PySide6, offscreen): doppio click su un richiamo %Nome nel dialogo
del box (vista Struttura) e nell'editor di testo apre la Libreria Pattern gia'
su quel pattern e con lo strumento della traccia.

Esecuzione:
    python3 -m pytest tests/test_pattern_double_click_gui.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication

from core.model import Pattern, Project
from gui import box_edit_dialog
from gui.box_edit_dialog import BoxEditDialog
from gui.pattern_editor_dialog import PatternEditorDialog, pattern_ref_at

_app = QApplication.instance() or QApplication([])


def _project():
    p = Project(name="t", tempo_bpm=120)
    p.patterns["Aaa"] = Pattern(name="Aaa", tokens=["c"])
    p.patterns["Riff"] = Pattern(name="Riff", tokens=["d", "e"])
    return p


def test_pattern_ref_at():
    patterns = _project().patterns
    text = "c 2%Riff+3 d // %Riff"
    assert pattern_ref_at(text, text.index("Riff"), patterns) == "Riff"
    assert pattern_ref_at(text, text.index("2%"), patterns) == "Riff"
    assert pattern_ref_at(text, 0, patterns) == ""
    assert pattern_ref_at(text, text.rindex("Riff"), patterns) == ""       # nel commento
    assert pattern_ref_at("%Nessuno", 2, patterns) == ""


def test_pattern_dialog_opens_on_pattern_and_instrument():
    dlg = PatternEditorDialog(_project(), pattern_name="Riff", instrument_name="Bass")
    assert dlg.list_widget.currentItem().text() == "Riff"
    assert dlg.instrument_combo.currentText() == "Bass"
    assert dlg.body_edit.toPlainText() == "d e"


def test_box_double_click_on_pattern_opens_the_library(monkeypatch):
    opened, edited = [], []

    def fake_exec(dlg):
        opened.append((dlg.list_widget.currentItem().text(), dlg.instrument_combo.currentText()))
        dlg.project.rename_pattern("Riff", "Giro")
        return 0

    monkeypatch.setattr(box_edit_dialog.PatternEditorDialog, "exec", fake_exec)
    dlg = BoxEditDialog(None, _project(), "Bass", 120, clip_text="4: c %Riff f",
                        on_patterns_edited=lambda: edited.append(True))
    assert dlg._on_body_double_click(dlg.body_edit.toPlainText().index("Riff"), None)
    assert opened == [("Riff", "Bass")]
    assert dlg.body_edit.toPlainText() == "4: c %Giro f"      # la rinomina vale anche qui
    assert edited == [True]


def test_editor_double_click_on_pattern_opens_the_library(monkeypatch):
    from gui import main_window_project
    from gui.main_window import MainWindow

    opened = []
    monkeypatch.setattr(main_window_project.PatternEditorDialog, "exec",
                        lambda dlg: opened.append((dlg.list_widget.currentItem().text(),
                                                   dlg.instrument_combo.currentText())))
    win = MainWindow()
    win.project.patterns.update(_project().patterns)
    win.project.add_track("Basso", "Bass", "4: c %Riff f")
    win.select_track("Basso")
    assert win._on_editor_double_click(win.editor.toPlainText().index("Riff"), None)
    assert opened == [("Riff", "Bass")]


def test_completion_opens_while_typing_but_not_on_click():
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    dlg = BoxEditDialog(None, _project(), "Piano", 120, clip_text="")
    dlg.show()
    editor, popup = dlg.body_edit, dlg.body_edit._completer.popup()
    dlg.activateWindow()
    QTest.qWaitForWindowActive(dlg)
    editor.setFocus()
    assert editor.hasFocus()
    QTest.keyClicks(editor, "4: c %Ri")
    assert popup.isVisible()                               # scrivendo: suggerimenti
    QTest.keyClick(popup, Qt.Key_Escape)
    assert not popup.isVisible()
    QTest.mouseClick(editor.viewport(), Qt.LeftButton, pos=editor.cursorRect(editor.textCursor()).center())
    cursor = editor.textCursor()
    cursor.setPosition(len("4: c %R"))
    editor.setTextCursor(cursor)                           # click/frecce su una parola
    assert not popup.isVisible()
    dlg.reject()
