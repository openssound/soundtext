import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)

import numpy as np
import pytest

from core.audio_import import SilentAudio, convert_audio_to_track_text, drop_background_noise
from core.audio_quantize import AudioEvent
from core.audio_tracks import write_wav

RATE = 44100


def _wav(tmp_path, x, name="x.wav"):
    path = str(tmp_path / name)
    write_wav(path, x[:, None].astype(np.float32), RATE, bits=16)
    return path


def _noise(db, seconds, seed=1):
    return np.random.default_rng(seed).normal(0, 10 ** (db / 20), int(RATE * seconds))


@pytest.mark.parametrize("mode", [{}, {"chords": True}, {"is_percussion": True}])
def test_silent_recording_gives_no_notes(tmp_path, mode):
    """Registrando in silenzio, il fruscio del microfono (anche con un clic,
    quello su Ferma) diventava una serie di note a velocity alta."""
    x = np.concatenate([_noise(-45, 2.0), np.full(200, 0.8), _noise(-45, 0.5)])
    path = _wav(tmp_path, x)
    percussion = mode.pop("is_percussion", False)
    with pytest.raises(SilentAudio):
        convert_audio_to_track_text(path, percussion, 120, 16, False, {}, already_wav=True, **mode)


def test_soft_playing_is_still_converted(tmp_path):
    t = np.arange(RATE * 2) / RATE
    tone = 10 ** (-35 / 20) * 1.41 * np.sin(2 * np.pi * 220 * t) * (t % 0.5 < 0.4)
    text = convert_audio_to_track_text(_wav(tmp_path, tone + _noise(-55, 2)), False, 120, 16, False, {},
                                       already_wav=True)
    assert "a" in text


def test_background_noise_events_are_dropped():
    events = [AudioEvent(0.0, 0.5, 100, midi_pitch=60), AudioEvent(1.0, 1.5, 2, midi_pitch=61),
              AudioEvent(2.0, 2.5, 20, midi_pitch=62)]
    assert [e.midi_pitch for e in drop_background_noise(events)] == [60, 62]     # 2 e' 34 dB sotto


def test_dialog_shows_silence_without_an_error_popup(tmp_path, monkeypatch):
    import time
    from PySide6.QtWidgets import QApplication, QMessageBox
    app = QApplication.instance() or QApplication([])
    errors = []
    monkeypatch.setattr(QMessageBox, "critical", lambda *a: errors.append(a))
    from core.model import Project
    from gui.audio_import_dialog import AudioImportDialog
    dlg = AudioImportDialog(None, Project(name="p"), "Piano", "Piano")
    dlg._set_source(_wav(tmp_path, _noise(-50, 2.0)), from_mic=True)
    end = time.time() + 10
    while time.time() < end and "silenzios" not in dlg.result_status.text():
        app.processEvents()
        time.sleep(0.01)
    assert "silenzios" in dlg.result_status.text() and errors == []
    assert dlg.preview_edit.toPlainText() == "" and dlg.result_text() is None
    dlg.reject()
