"""
Test dell'esecuzione per strumento (core.performance_style): strumming
della chitarra, pedale del pianoforte, note fantasma e slide del basso.

Esecuzione:
    python3 -m pytest tests/test_performance_style.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)

import os

import pytest

from core.instruments import get_instrument
from core.notation import parse_track_text, validate_track_text
from core.performance_style import STRUM_MS, perform, style_for

COMP = "8: [c*4 e*4 g*4] [c*4 e*4 g*4] 2r [f*4 a*4 c*5] 3r"


def test_style_by_instrument():
    assert [style_for(get_instrument(n)) for n in ("Guitar", "Piano", "Bass", "Trumpet", "Drums")] == \
        ["guitar", "piano", "bass", None, None]


def test_guitar_strums_down_on_the_beat_and_up_in_between():
    text = perform(COMP, "guitar")
    assert validate_track_text(text, {})[0]
    events = [e for e in parse_track_text(text, {}) if e.kind == "note"]
    down = [(e.letter, e.shift or 0) for e in events if e.start == 0.0]
    up = [(e.letter, e.shift or 0, e.velocity) for e in events if e.start == 0.5]
    assert down == [("c", 0), ("e", STRUM_MS), ("g", 2 * STRUM_MS)]
    assert [n for n, _s, _v in up] == ["g", "e", "c"] and up[0][2] < 80
    assert sum(e.duration for e in parse_track_text(text, {}) if e.voice == 1) == pytest.approx(4.0)


def test_piano_pedal_changes_with_each_chord():
    text = perform(COMP, "piano")
    pedal = [(e.start, e.name) for e in parse_track_text(text, {}) if e.kind == "sustain"]
    assert pedal == [(0.0, "on"), (0.5, "off"), (0.5, "on"), (2.0, "off"), (2.0, "on"), (4.0, "off")]


def test_bass_ghost_notes_and_slides():
    text = perform("8: 2c*2 2r 2g*2 2a*2 4f*2 4g*2", "bass", seed=1)
    assert validate_track_text(text, {})[0]
    events = parse_track_text(text, {})
    ghosts = [e for e in events if e.articulation == "mute"]
    assert len(ghosts) == 1 and ghosts[0].start == 1.5 and ghosts[0].letter == "g" and ghosts[0].velocity < 50
    found = set()
    for seed in range(20):
        found |= {e.kind for e in parse_track_text(perform("8: 4c*2 4d*2 4e*2 4f*2 4g*2", "bass", seed=seed), {})}
    assert "slide" in found
    assert sum(e.duration for e in events) == pytest.approx(8.0)


def test_text_it_cannot_rewrite_stays_as_it_is():
    assert perform("4: 4C 4G", "guitar") == "4: 4C 4G"
    assert perform("c d e", "piano") == "c d e"


def test_dialog_option_for_the_destination_instrument():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from core.model import Project
    from gui.rhythm_generate_dialog import BassGenerateDialog, MelodyGenerateDialog, chord_source_tracks
    p = Project(tempo_bpm=100)
    p.add_track("Accordi", "Piano", "4: 4C 4Am 4F 4G")
    p.add_track("Chitarra", "Guitar", "")
    dlg = MelodyGenerateDialog(None, p, "Guitar", "prova", chord_source_tracks(p, "Chitarra"), polyphonic=True,
                               default_octave=4, range_low=40, range_high=88, default_bars=4,
                               track_name="Chitarra")
    assert not dlg.performance_check.isChecked()
    plain = dlg._compose_text()
    dlg.performance_check.setChecked(True)
    assert "shift=" in dlg._compose_text() and "shift=" not in plain
    dlg.reject()
    p.add_track("Basso", "Bass", "")
    dlg = BassGenerateDialog(None, p, "Bass", "prova", chord_source_tracks(p, "Basso"), default_bars=4,
                             track_name="Basso")
    assert dlg.performance_check is not None
    dlg.reject()
