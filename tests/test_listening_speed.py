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


def test_playback_menu_speed_follows_the_combo(monkeypatch):
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    import core.playback as pb
    from gui.main_window import MainWindow
    monkeypatch.setattr(pb, "streaming_available", lambda: True)
    w = MainWindow()
    actions = {a.text(): a for a in w.speed_actions.actions()}
    assert list(actions) == [w.speed_combo.itemText(i) for i in range(w.speed_combo.count())]
    assert actions["100%"].isChecked()
    actions["50%"].trigger()                                   # dal menu Riproduzione
    assert w.speed_combo.currentText() == "50%" and w.playback.speed == 0.5
    w.speed_combo.setCurrentIndex(w.speed_combo.findData(0.75))   # dalla tendina della barra
    assert actions["75%"].isChecked() and not actions["50%"].isChecked()
    assert w.playback.speed == 0.75
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


def test_slowed_mix_starts_from_the_chosen_chunk_and_joins_cleanly():
    """Rallentare la prima volta: si comincia appena e' pronto il pezzo da
    cui si parte, il resto si riempie dopo; alle giunture niente buchi."""
    pytest.importorskip("pedalboard")
    import time
    from core.playback import SlowedMix
    t = np.arange(30 * RATE) / RATE
    tone = (0.4 * np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
    mix = SlowedMix((np.column_stack([tone, tone]), RATE), 0.75)
    assert len(mix.samples) == 40 * RATE
    mix.start_from(20.0)
    assert mix.wait_ready(20.0, timeout=60)
    assert not mix._done[0]                         # l'inizio del brano arriva dopo
    deadline = time.time() + 120
    while not mix.complete and time.time() < deadline:
        time.sleep(0.05)
    assert mix.complete
    y = mix.samples[:, 0].astype(np.float32) / 32767.0
    rms = [np.sqrt(np.mean(y[i:i + 960] ** 2)) for i in range(RATE, len(y) - RATE, 480)]
    assert min(rms) > 0.9 * np.median(rms)          # nessun buco di volume alle giunture
    assert _peak_hz(y[5 * RATE:6 * RATE]) == pytest.approx(440.0, abs=2.0)


def test_slowed_mix_job_is_shared_and_replaced(monkeypatch):
    import core.playback as pb
    monkeypatch.setattr(pb.SlowedMix, "start_from", lambda self, seconds: None)
    monkeypatch.setattr(pb, "_slowed_job", None)
    entry = (np.zeros((RATE, 2), np.int16), RATE)
    first = pb.slowed_mix("brano|speed0.750", entry, 0.75, 0.0)
    assert pb.slowed_mix("brano|speed0.750", entry, 0.75, 0.5) is first      # stesso brano: lo stesso lavoro
    other = pb.slowed_mix("brano|speed0.500", entry, 0.5, 0.0)
    assert other is not first and first._cancelled                         # un'altra velocita': il vecchio si ferma


def test_is_playing_covers_the_gap_before_the_audio_starts(monkeypatch):
    """Da play() fino all'apertura dello stream is_playing() resta True:
    l'anteprima dei box controlla ogni 200 ms se l'ascolto e' finito, e un
    False in quel momento (dopo il rendering, prima dello stream: il box
    Inizio della chitarra di bossa_nova.st) la fermava prima di suonare."""
    import threading
    import core.playback as pb
    from core.model import Project
    gate, entered = threading.Event(), threading.Event()

    def slow_cache_get(key):
        entered.set()
        gate.wait(5)
        return None
    monkeypatch.setattr(pb, "_cache_get", slow_cache_get)
    project = Project()
    project.add_track("P", "Piano", "4: c*4")
    engine = PlaybackEngine()
    engine.play(project, only_audible=False)
    assert entered.wait(5)
    assert engine.is_playing()               # ne' rendering ne' stream ancora: ma sta partendo
    engine.stop()
    assert not engine.is_playing()
    gate.set()
