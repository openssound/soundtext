"""
Test dei generatori della seconda fase (core.harmonize, core.rhythm_generate,
core.melody_generate): armonizzare una melodia, registri che non si
sovrappongono, ritornello riconoscibile.

Esecuzione:
    python3 -m pytest tests/test_generators_phase2.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)

import pytest

from core.chords import pitch_to_midi
from core.harmonize import VERSIONS, harmonize, melody_key, melody_notes
from core.melody_generate import _apply_repeats, section_repeats
from core.model import Clip, Project
from core.notation import parse_track_text
from core.rhythm_generate import (
    extract_chords_from_track, fit_register, generate_melodic_line, part_registers,
)

MARY = "4: e d c d e e 2e d d 2d e g 2g e d c d e e e e d d e d 4c"


def _chords(text):
    return [ev.symbol for ev in parse_track_text(text, {}) if ev.kind == "chord"]


def test_melody_key_uses_the_last_note():
    assert melody_key(melody_notes(MARY, {})) == "C"
    assert melody_key(melody_notes("4: a b c*5 b a 2e g# a b 2c*5 b a g# 2a", {})) == "Am"


def test_three_versions_from_simple_to_rich():
    notes = melody_notes(MARY, {})
    texts = {v: harmonize(notes, "C", v, 4.0, 4.0, seed=1) for v in VERSIONS}
    assert set(_chords(texts["simple"])) <= {"C", "F", "G"}
    assert _chords(texts["simple"])[0] == "C" and _chords(texts["simple"])[-1] == "C"
    assert set(_chords(texts["diatonic"])) <= {"C", "Dm", "Em", "F", "G", "Am"}
    assert any(len(c) > 2 for c in _chords(texts["rich"]))           # settime e colori
    for text in texts.values():                                       # copre tutta la melodia
        assert sum(ev.duration for ev in parse_track_text(text, {})) == pytest.approx(32.0)


def test_minor_melody_gets_the_major_dominant_and_leading_rest():
    notes = melody_notes("4: a b c*5 b a 2e g# a b 2c*5 b a g# 2a", {})
    assert "E" in _chords(harmonize(notes, "Am", "simple", 4.0, 4.0))
    late = melody_notes("4: 4r 2r e d c d e e 2e", {})
    text = harmonize(late, "C", "diatonic", 2.0, 4.0)
    assert parse_track_text(text, {})[0].kind == "rest" and parse_track_text(text, {})[0].duration == 6.0


def test_harmonize_needs_notes():
    with pytest.raises(ValueError):
        harmonize([], "C")


def test_registers_leave_room_for_the_other_parts():
    p = Project(tempo_bpm=120)
    p.add_track("Basso", "Bass", "4: c*2 g*2 e*2 2c*3")               # fino a C3 = 48
    p.add_track("Tromba", "Trumpet", "4: e*5 g*5 c*6 2a*5")           # dal Mi5 = 76
    regs = part_registers(p, exclude_track_name="Piano")
    assert regs["bass_top"] == 48 and regs["melody_low"] == 76
    low, high = fit_register(21, 108, True, regs)
    assert (low, high) == (49, 75)
    chords = extract_chords_from_track("4: 4C 4F 4G 4C", {})
    text = generate_melodic_line(chords, "block_chords", 4, low, high, True)
    pitches = [pitch_to_midi(i["letter"], i["octave"]) for ev in parse_track_text(text, {})
               if ev.kind == "block" for i in ev.items]
    assert pitches and min(pitches) >= 49 and max(pitches) <= 75
    # meno di un'ottava di spazio: il limite non si applica
    assert fit_register(40, 55, True, {"bass_top": 50}) == (40, 55)


def test_chorus_melody_repeats_when_the_section_comes_back():
    p = Project(tempo_bpm=120)
    acc = p.add_track("Accordi", "Piano", "")
    acc.clips = [Clip("Strofa", "4: 4C 4Am 4F 4G", 0.0), Clip("Ritornello", "4: 4F 4G 4C 4C", 16.0),
                 Clip("Strofa 2", "4: 4C 4Am 4F 4G", 32.0), Clip("Ritornello (copia)", "4: 4F 4G 4C 4C", 48.0)]
    assert section_repeats(p, acc) == [(32.0, 48.0, 0.0), (48.0, 64.0, 16.0)]
    chords = extract_chords_from_track("4: 4C 4Am 4F 4G 4F 4G 4C 4C 4C 4Am 4F 4G 4F 4G 4C 4C", {})
    text = generate_melodic_line(chords, "melody_aaba", 5, 60, 84, False, variability=0.7, seed=3,
                                 repeats=section_repeats(p, acc))
    notes = [(ev.start, ev.duration, ev.letter, ev.octave) for ev in parse_track_text(text, {}) if ev.kind == "note"]
    chorus1 = [(s - 16, d, l, o) for s, d, l, o in notes if 16 <= s < 32]
    chorus2 = [(s - 48, d, l, o) for s, d, l, o in notes if 48 <= s < 64]
    assert chorus1 and chorus1[:-1] == chorus2[:-1]


def test_apply_repeats_cuts_a_note_hanging_over_the_section():
    notes = [(0.0, 1.0, 60, False), (3.0, 3.0, 62, False), (6.0, 1.0, 64, False)]
    out = _apply_repeats(notes, [(4.0, 8.0, 0.0)])
    assert out == [(0.0, 1.0, 60, False), (3.0, 1.0, 62, False), (4.0, 1.0, 60, False), (7.0, 1.0, 62, False)]


# ---------------------------------------------------------------------------
# Dialoghi (offscreen)
# ---------------------------------------------------------------------------

def _qt():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_harmonize_dialog_and_the_new_chord_track(monkeypatch):
    _qt()
    from gui.harmonize_dialog import HarmonizeDialog
    from gui.main_window import MainWindow
    w = MainWindow()
    w.arrangement_action.setChecked(True)
    mel = w.project.add_track("Voce", "Trumpet", "")
    mel.clips = [Clip("Tema", MARY, 8.0)]
    w.arrangement_view.on_clip_changed("Voce")
    dlg = HarmonizeDialog(None, w.project, MARY, "Tema")
    assert dlg.key_combo.currentText() == "C" and dlg.version() == "diatonic"
    dlg.version_combo.setCurrentIndex(0)
    assert set(_chords(dlg.result_text())) <= {"C", "F", "G"} and not dlg.other_btn.isEnabled()
    dlg.reject()
    monkeypatch.setattr(HarmonizeDialog, "exec", lambda self: HarmonizeDialog.Accepted)
    w.arrangement_view.harmonize_melody("Tema", MARY, 8.0)
    chords = w.project.get_track("Accordi di Tema")
    assert chords.instrument_name == "Piano" and chords.clips[0].start_beat == 8.0
    assert _chords(chords.clips[0].text)
    w.undo()
    assert w.project.find_track("Accordi di Tema") is None


def test_melody_dialog_registers_and_chorus_options():
    _qt()
    from gui.rhythm_generate_dialog import MelodyGenerateDialog, chord_source_tracks
    p = Project(tempo_bpm=100)
    acc = p.add_track("Accordi", "Piano", "")
    acc.clips = [Clip("Strofa", "4: 4C 4Am 4F 4G", 0.0), Clip("Ritornello", "4: 4F 4G 4C 4C", 16.0),
                 Clip("Ritornello", "4: 4F 4G 4C 4C", 32.0)]
    acc.text = "4: 4C 4Am 4F 4G 4F 4G 4C 4C 4F 4G 4C 4C"
    p.add_track("Chitarra", "Guitar", "4: [c*3 e*3 g*3] [a*3 c*4 e*4] [f*3 a*3 c*4] [g*3 b*3 d*4]")
    p.add_track("Tromba", "Trumpet", "")
    dlg = MelodyGenerateDialog(None, p, "Trumpet", "prova", chord_source_tracks(p, "Tromba"), polyphonic=False,
                               default_octave=5, range_low=54, range_high=82, default_bars=12,
                               track_name="Tromba")
    assert dlg.space_check.isChecked() and dlg._register()[0] > 54
    assert dlg.repeat_check.isChecked()
    dlg.style_combo.setCurrentIndex(dlg.style_combo.findData("melody_aaba"))
    text = dlg._generate_text(seed=2)
    notes = [(ev.start, ev.letter, ev.octave) for ev in parse_track_text(text, {}) if ev.kind == "note"]
    first = [(s - 16, l, o) for s, l, o in notes if 16 <= s < 31]
    second = [(s - 32, l, o) for s, l, o in notes if 32 <= s < 47]
    assert first and first == second
    dlg.reject()
