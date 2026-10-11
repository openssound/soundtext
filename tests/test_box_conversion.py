"""
Test della conversione in box delle tracce a testo libero
(core.box_conversion e il comando "Converti le tracce in box").

Esecuzione:
    python3 -m pytest tests/test_box_conversion.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import box_conversion
from core.box_conversion import _midi_signature, convert_project_to_boxes, convertible_tracks
from core.model import Clip, Project


def _project():
    p = Project(name="t", tempo_bpm=120)
    p.add_track("Piano", "Piano", "4: c d e f  4: r r r r r r r r  4: g a b c")
    p.add_track("Vuota", "Piano", "")
    boxed = p.add_track("Box", "Piano", "")
    boxed.clips = [Clip(name="B", text="4: c d", start_beat=0.0)]
    return p


def test_free_text_tracks_become_boxes_and_sound_the_same():
    p = _project()
    piano = p.get_track("Piano")
    before = _midi_signature(p, piano)
    assert [t.name for t in convertible_tracks(p)] == ["Piano"]
    converted, kept = convert_project_to_boxes(p)
    assert (converted, kept) == (["Piano"], [])
    assert len(piano.clips) == 2                          # divisa dalla pausa lunga
    assert piano.clips[1].start_beat > piano.clips[0].start_beat
    assert _midi_signature(p, piano) == before
    assert p.get_track("Vuota").clips == []               # niente da dividere
    assert [c.name for c in p.get_track("Box").clips] == ["B"]   # gia' in box: intatta


def _broken(project, track):
    track.clips = [Clip(name="x", text="4: c", start_beat=0.0)]
    track.text = "4: c"


def test_if_splitting_changes_the_sound_the_track_becomes_one_box(monkeypatch):
    p = _project()
    piano = p.get_track("Piano")
    before = _midi_signature(p, piano)
    monkeypatch.setattr(box_conversion, "split_track_into_boxes", _broken)
    assert convert_project_to_boxes(p) == (["Piano"], [])
    assert len(piano.clips) == 1 and piano.clips[0].start_beat == 0.0
    assert _midi_signature(p, piano) == before


def test_volume_in_the_rest_between_boxes_is_not_lost():
    p = Project(name="t", tempo_bpm=120)
    t = p.add_track("Piano", "Piano", "4: c d e f  4: r r r r vol=40 r r r r  4: g a b c")
    before = _midi_signature(p, t)
    assert convert_project_to_boxes(p) == (["Piano"], [])
    assert _midi_signature(p, t) == before


def test_a_track_that_would_sound_different_anyway_is_left_alone(monkeypatch):
    p = _project()
    piano = p.get_track("Piano")
    text = piano.text
    monkeypatch.setattr(box_conversion, "split_track_into_boxes", _broken)
    monkeypatch.setattr(box_conversion, "_single_box", _broken)
    assert convert_project_to_boxes(p) == ([], ["Piano"])
    assert piano.text == text and piano.clips == []


def test_menu_command_converts_and_undo_restores(monkeypatch):
    from PySide6.QtWidgets import QApplication, QMessageBox
    from gui.main_window import MainWindow

    QApplication.instance() or QApplication([])
    messages = []
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: messages.append(a[2]))
    win = MainWindow()
    win.project.add_track("Piano", "Piano", "4: c d e f  4: r r r r r r r r  4: g a b c")
    win._mark_dirty()
    win.convert_to_boxes_action()
    assert len(win.project.get_track("Piano").clips) == 2
    assert "1" in messages[-1]
    win.undo()
    assert win.project.get_track("Piano").clips == []
    win.convert_to_boxes_action()
    win.convert_to_boxes_action()                          # gia' tutto in box
    assert len(messages) == 3
