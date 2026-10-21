"""
Test di "Arrangia il brano" (core.arrange, gui.arrange_dialog): intensita'
dalle sezioni, parti generate un box per sezione, fill di sezione e finale.

Esecuzione:
    python3 -m pytest tests/test_arrange.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)

import os

import pytest

from core.arrange import ArrangeOptions, arrange, section_intensity, song_sections
from core.model import Clip, Project
from core.notation import parse_track_text, validate_track_text


def _song():
    p = Project(tempo_bpm=100)
    acc = p.add_track("Accordi", "Piano", "")
    acc.clips = [Clip("Intro", "4: 4C 4G", 0.0), Clip("Strofa", "4: 4C 4Am 4F 4G", 8.0),
                 Clip("Pre-ritornello", "4: 4Dm 4G", 24.0), Clip("Ritornello", "4: 4F 4G 4C 4C", 32.0),
                 Clip("Finale", "4: 4C 4C", 48.0)]
    return p, acc


@pytest.mark.parametrize("name, level", [("Intro", "intro"), ("Strofa 2", "light"), ("Verse", "light"),
                                         ("Pre-ritornello", "build"), ("Ritornello", "full"),
                                         ("Chorus 2", "full"), ("Ponte", "build"), ("Finale", "outro"),
                                         ("Coda", "outro"), ("Tema", "normal")])
def test_intensity_from_the_section_name(name, level):
    assert section_intensity(name) == level


def test_parts_one_box_per_section_with_fills_and_ending():
    p, acc = _song()
    sections = song_sections(p, acc)
    assert [(s.name, s.start_beat, s.length_beats) for s in sections] == [
        ("Intro", 0.0, 8.0), ("Strofa", 8.0, 16.0), ("Pre-ritornello", 24.0, 8.0), ("Ritornello", 32.0, 16.0),
        ("Finale", 48.0, 8.0)]
    parts = arrange(p, sections, ArrangeOptions(seed=3), 4.0)
    assert [c.name for c in parts["drums"]] == ["Strofa", "Pre-ritornello", "Ritornello", "Finale"]   # intro: niente
    assert [c.name for c in parts["bass"]] == ["Strofa", "Pre-ritornello", "Ritornello", "Finale"]
    assert [c.start_beat for c in parts["comping"]] == [0.0, 8.0, 24.0, 32.0, 48.0]
    for clips in parts.values():
        for clip in clips:
            assert validate_track_text(clip.text, {})[0]
    verse = parse_track_text(parts["drums"][0].text, {})
    names = lambda ev: [ev.name] if ev.kind == "percussion" else [i["name"] for i in (ev.items or [])]   # noqa: E731
    last_bar = [n for ev in verse if 12.0 <= ev.start < 16.0 for n in names(ev)]
    assert any(n.startswith("tom") for n in last_bar)                    # fill a fine sezione
    chorus = parse_track_text(parts["drums"][2].text, {})
    assert any("ride" in names(ev) or "crash" in names(ev) for ev in chorus)   # ritornello pieno


def test_dialog_creates_the_tracks_in_one_undo_step(monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QDialog
    QApplication.instance() or QApplication([])
    from gui.arrange_dialog import ArrangeDialog
    from gui.main_window import MainWindow
    w = MainWindow()
    w.arrangement_action.setChecked(True)
    p, acc = _song()
    track = w.project.add_track("Accordi", "Piano", "")
    track.clips = acc.clips
    w.arrangement_view.on_clip_changed("Accordi")

    def fake_exec(dlg):
        assert dlg.table.rowCount() == 5
        assert dlg.table.cellWidget(0, 2).currentData() == "intro"
        dlg.table.cellWidget(1, 2).setCurrentIndex(dlg.table.cellWidget(1, 2).findData("full"))
        dlg.accept()
        return QDialog.Accepted

    monkeypatch.setattr(ArrangeDialog, "exec", fake_exec)
    w.arrange_song()
    names = [t.name for t in w.project.tracks]
    assert names == ["Accordi", "Batteria", "Basso", "Accompagnamento"]
    assert [c.name for c in w.project.get_track("Basso").clips][0] == "Strofa"
    assert w.project.get_track("Batteria").text.strip()
    w.undo()
    assert [t.name for t in w.project.tracks] == ["Accordi"]
