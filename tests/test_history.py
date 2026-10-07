"""
Test per Annulla/Ripeti (core.history + integrazione nella finestra
principale): ogni modifica al progetto, qualunque sia la sua origine, e'
annullabile con Ctrl+Z e ripetibile con Ctrl+Y.

Esecuzione:
    python3 -m pytest tests/test_history.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from core.history import ProjectHistory
from core.model import Project

_app = QApplication.instance() or QApplication([])


class _Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def _project(text="c d"):
    p = Project()
    p.add_track("Piano", "Piano", text)
    return p


# ------------------------------------------------------------ core

def test_undo_and_redo_restore_previous_states():
    p = _project()
    h = ProjectHistory()
    h.reset(p, "Piano")
    p.tracks[0].text = "c d e"
    assert h.record(p, "Piano")
    p.tempo_bpm = 90
    assert h.record(p, "Piano")

    project, track = h.undo()
    assert (project.tempo_bpm, project.tracks[0].text, track) == (120, "c d e", "Piano")
    project, _ = h.undo()
    assert project.tracks[0].text == "c d"
    assert h.undo() is None
    project, _ = h.redo()
    assert project.tracks[0].text == "c d e"


def test_unchanged_project_is_not_recorded():
    p = _project()
    h = ProjectHistory()
    h.reset(p)
    assert not h.record(p)
    assert not h.can_undo()


def test_bursts_with_the_same_merge_key_become_one_step():
    clock = _Clock()
    p = _project("c")
    h = ProjectHistory(merge_seconds=1.5, clock=clock)
    h.reset(p)
    for i, text in enumerate(["c d", "c d e", "c d e f"]):
        clock.t = i * 0.5
        p.tracks[0].text = text
        h.record(p, "Piano", merge_key="text:Piano")
    clock.t = 10.0                      # pausa lunga: nuovo passo
    p.tracks[0].text = "c d e f g"
    h.record(p, "Piano", merge_key="text:Piano")

    assert h.undo()[0].tracks[0].text == "c d e f"
    assert h.undo()[0].tracks[0].text == "c"
    assert not h.can_undo()


def test_a_new_change_clears_redo():
    p = _project()
    h = ProjectHistory()
    h.reset(p)
    p.tempo_bpm = 100
    h.record(p)
    h.undo()
    p = _project()
    p.tempo_bpm = 80
    h.record(p)
    assert not h.can_redo()


def test_returned_states_are_independent_copies():
    p = _project()
    h = ProjectHistory()
    h.reset(p)
    p.tempo_bpm = 100
    h.record(p)
    restored, _ = h.undo()
    restored.tracks[0].text = "modificato dopo l'undo"
    again, _ = h.redo()
    assert again.tracks[0].text == "c d"


def test_history_is_limited():
    p = _project()
    h = ProjectHistory(limit=3)
    h.reset(p)
    for bpm in range(100, 110):
        p.tempo_bpm = bpm
        h.record(p)
    steps = 0
    while h.undo() is not None:
        steps += 1
    assert steps == 3


# ------------------------------------------------------------ finestra principale

def _window():
    from gui.main_window import MainWindow
    w = MainWindow()
    w.show()
    w._replace_project(_project("c d"))
    _app.processEvents()
    return w


def _close(w):
    w._dirty = False
    w.close()
    _app.processEvents()


def test_ctrl_z_in_the_editor_undoes_typing_through_project_history():
    w = _window()
    w.editor.setFocus()
    cursor = w.editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    w.editor.setTextCursor(cursor)
    QTest.keyClicks(w.editor, " e f")
    assert w.project.tracks[0].text == "c d e f"
    QTest.keyClick(w.editor, Qt.Key_Z, Qt.ControlModifier)
    _app.processEvents()
    assert w.project.tracks[0].text == "c d"
    assert w.editor.toPlainText() == "c d"
    QTest.keyClick(w.editor, Qt.Key_Y, Qt.ControlModifier)
    _app.processEvents()
    assert w.editor.toPlainText() == "c d e f"
    _close(w)


def test_operations_that_replace_track_text_are_undoable():
    w = _window()
    track = w.project.tracks[0]
    w._append_or_replace_track_text(track, "Cmaj7 F")   # come dopo Genera/Importa
    assert "Cmaj7" in w.project.tracks[0].text
    w.undo()
    assert w.project.tracks[0].text == "c d"
    assert w.editor.toPlainText() == "c d"
    _close(w)


def test_track_removal_and_mixer_changes_are_undoable():
    w = _window()
    w.project.add_track("Bass", "Bass", "c*2")
    w.refresh_mixer()
    w._mark_dirty()
    w.project.tracks[1].volume = 40
    w._on_mixer_changed("Bass")
    w.project.remove_track("Bass")
    w.refresh_mixer()
    w._mark_dirty()
    assert [t.name for t in w.project.tracks] == ["Piano"]

    w.undo()
    assert [t.name for t in w.project.tracks] == ["Piano", "Bass"]
    assert w.project.tracks[1].volume == 40
    assert "Bass" in w.track_headers
    w.undo()
    assert w.project.tracks[1].volume == 100
    _close(w)


def test_opening_another_project_clears_the_history():
    w = _window()
    w.project.tempo_bpm = 99
    w._mark_dirty()
    assert w.undo_action.isEnabled()
    w._replace_project(_project("e"))
    assert not w.undo_action.isEnabled()
    _close(w)


def test_opening_a_project_does_not_mark_it_modified():
    """Aprire un progetto aggiorna i campi Tempo/Metrica/Tonalita' della
    toolbar: non deve risultare modificato (niente richiesta di salvataggio
    alla chiusura) ne' creare passi da annullare."""
    from gui.main_window import MainWindow
    w = MainWindow()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    w._load_and_apply_project(os.path.join(root, "examples", "blues_12bar.st"))
    _app.processEvents()
    assert w.tempo_spin.value() == w.project.tempo_bpm == 96
    assert not w._dirty
    assert not w.history.can_undo()
    w.close()
