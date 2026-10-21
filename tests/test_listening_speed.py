"""
Test di Rallenta l'ascolto (core.playback: PlaybackEngine.set_speed e
slowed_entry): il mix rallentato dura di piu' senza cambiare intonazione e
la posizione si riporta al tempo del brano; senza scheda audio.

Esecuzione:
    python3 -m pytest tests/test_listening_speed.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)

import numpy as np
import pytest

from core.playback import PlaybackEngine, slowed_entry

RATE = 48000


def _peak_hz(x):
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    return np.fft.rfftfreq(len(x), 1.0 / RATE)[int(np.argmax(spectrum))]


def test_slowed_mix_is_longer_with_the_same_pitch():
    pytest.importorskip("pedalboard")
    t = np.arange(2 * RATE) / RATE
    tone = (0.4 * np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
    entry = (np.column_stack([tone, tone]), RATE)
    slow, rate = slowed_entry(entry, 0.5)
    assert rate == RATE and slow.dtype == np.int16
    assert len(slow) == pytest.approx(4 * RATE, rel=0.01)
    assert _peak_hz(slow[RATE:2 * RATE, 0].astype(np.float32)) == pytest.approx(440.0, abs=2.0)
    assert slowed_entry(entry, 1.0) is entry


class _FakePlayer:
    samplerate = RATE

    def __init__(self):
        self.loop = None

    def is_active(self):
        return True

    def position_frames(self):
        return 2 * RATE                         # 2 s di buffer suonati

    def set_loop(self, loop):
        self.loop = loop


def test_position_and_loop_follow_the_song_time():
    engine = PlaybackEngine()
    engine.set_speed(0.3)
    assert engine.speed == 0.5                  # al massimo meta' velocita'
    engine._pcm_player, engine._playing_speed = _FakePlayer(), 0.5
    assert engine.position_seconds() == pytest.approx(1.0)   # 2 s rallentati = 1 s di brano
    engine.set_loop_seconds((1.0, 3.0))
    assert engine._pcm_player.loop == (2 * RATE, 6 * RATE)
    engine._pcm_player = None


def test_speed_combo_sets_the_engine_and_slows_the_click(monkeypatch):
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    import core.playback as pb
    from gui.main_window import MainWindow
    monkeypatch.setattr(pb, "streaming_available", lambda: True)
    w = MainWindow()
    w.speed_combo.setCurrentIndex(w.speed_combo.findData(0.75))
    assert w.playback.speed == 0.75
    w._playback_tempo_map = [(0.0, 120), (16.0, 100)]
    assert w._metronome_tempo_map() == [(0.0, 90.0), (16.0, 75.0)]
    w.speed_combo.setCurrentIndex(0)
    assert w.playback.speed == 1.0 and w._metronome_tempo_map() is w._playback_tempo_map
    w.close()


def test_comparison_buffer_sequence_and_together(tmp_path, monkeypatch):
    import core.playback as pb
    from core.audio_tracks import write_wav
    from core.model import Project
    path = str(tmp_path / "voce.wav")
    write_wav(path, np.full((RATE, 1), 0.4, np.float32), RATE)
    notes = np.full((RATE // 2, 2), 0.2, np.float32)
    monkeypatch.setattr(pb, "render_project_mix", lambda project, stop_check=None: (notes, RATE))
    seq = pb.comparison_buffer(Project(), path, "sequence")
    gap = int(pb.COMPARE_GAP_SECONDS * RATE)
    assert seq.shape == (RATE + gap + RATE // 2, 2)
    assert seq[10, 0] == pytest.approx(0.4, abs=1e-3) and seq[-10, 1] == pytest.approx(0.2)
    together = pb.comparison_buffer(Project(), path, "together")
    assert together.shape == (RATE, 2)
    assert together[10, 0] == pytest.approx(0.3, abs=1e-3)          # meta' di ciascuno
    assert together[-10, 0] == pytest.approx(0.2, abs=1e-3)         # solo l'audio
