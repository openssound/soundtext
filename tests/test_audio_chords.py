import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)

import numpy as np
import pytest

from core.audio_chords import (FLAT_NAMES, QUALITIES, SHARP_NAMES, chords_to_text, detect_chords,
                               note_names_for)
from core.audio_tracks import write_wav
from core.notation import validate_track_text

RATE = 44100


def _tone_mix(notes_hz, seconds):
    """Note con gli armonici che calano come 1/h (un timbro da strumento: la
    compensazione degli armonici di core.audio_chords e' tarata su suoni veri)."""
    t = np.arange(int(seconds * RATE)) / RATE
    x = np.zeros_like(t)
    for f in notes_hz:
        for h in range(1, 9):
            if f * h < RATE / 2:
                x += np.sin(2 * np.pi * f * h * t) / h
    return (0.8 * x / np.abs(x).max()).astype(np.float32)


def _hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def _wav(tmp_path, chords_midi, tempo=120, beats=4):
    seconds = beats * 60.0 / tempo
    x = np.concatenate([_tone_mix([_hz(m) for m in chord], seconds) for chord in chords_midi])
    path = str(tmp_path / "accordi.wav")
    write_wav(path, x[:, None], RATE, bits=16)
    return path


def test_triads_are_recognized_bar_by_bar(tmp_path):
    # C (C3 E4 G4), Am, F, G a 120 BPM, una battuta ciascuno
    path = _wav(tmp_path, [(48, 64, 67), (45, 60, 64), (41, 60, 65), (43, 59, 62)])
    chords, step_q, _start = detect_chords(path, 120, 4)
    assert chords_to_text(chords, step_q, 4) == "4: 4C | 4Am | 4F | 4G"


def test_bass_note_makes_an_inversion(tmp_path):
    path = _wav(tmp_path, [(48, 64, 67), (40, 60, 67), (48, 64, 67)])     # C, C/E, C
    chords, step_q, _start = detect_chords(path, 120, 4)
    assert chords_to_text(chords, step_q, 4) == "4: 4C | 4C/E | 4C"


def test_silence_is_a_rest_and_trailing_rests_are_dropped(tmp_path):
    seconds = 2.0
    x = np.concatenate([np.zeros(int(seconds * RATE), np.float32), _tone_mix([_hz(m) for m in (48, 64, 67)], seconds)])
    path = str(tmp_path / "pausa.wav")
    write_wav(path, x[:, None], RATE, bits=16)
    chords, step_q, _start = detect_chords(path, 120, 4)
    assert chords_to_text(chords, step_q, 4) == "4: 4r | 4C"


def test_text_ties_chords_across_bars_and_spells_by_key():
    assert chords_to_text([(0, "", None, 6), (7, "", None, 2)], 1.0, 4) == "4: 4C~ | 2C 2G"
    assert note_names_for([(4, "", None, 4), (11, "", None, 4), (9, "", None, 4)]) == SHARP_NAMES   # Mi
    assert note_names_for([(3, "", None, 4), (10, "", None, 4), (8, "", None, 4)]) == FLAT_NAMES    # Mib
    # 6/8: tre quarti per battuta; 7/8: a ottavi
    assert chords_to_text([(0, "", None, 3), (7, "", None, 3)], 1.0, 3) == "4: 3C | 3G"
    assert chords_to_text([(0, "", None, 7)], 0.5, 3.5) == "8: 7C"


@pytest.mark.parametrize("names", [SHARP_NAMES, FLAT_NAMES])
def test_every_chord_name_is_valid_notation(names):
    from core.audio_chords import chord_name
    tokens = [chord_name(root, quality, bass, names)
              for root in range(12) for quality in QUALITIES for bass in (None, (root + 4) % 12)]
    ok, msg = validate_track_text("4: " + " ".join(tokens), {})
    assert ok, msg


def test_import_pipeline_in_chord_mode(tmp_path):
    from core.audio_import import convert_audio_to_track_text
    path = _wav(tmp_path, [(48, 64, 67), (43, 59, 62)])
    text = convert_audio_to_track_text(path, False, 120, 16, False, {}, already_wav=True,
                                       chords=True, beats_per_bar=4)
    assert text == "4: 4C | 4G"


def test_dialog_has_the_chord_mode():
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from core.model import Project
    from gui.audio_import_dialog import AudioImportDialog, _beats_per_bar
    project = Project(name="p")
    project.add_track("Piano", "Piano", "")
    dialog = AudioImportDialog(None, project, "Piano", "Piano")
    dialog.show()
    assert not dialog.sevenths_check.isVisible()
    dialog.chords_radio.setChecked(True)
    assert dialog.sevenths_check.isVisible()
    assert not dialog.voice_source_check.isVisible()
    dialog.close()
    assert _beats_per_bar("6/8") == 3.0 and _beats_per_bar("??") == 4.0
