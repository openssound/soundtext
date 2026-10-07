"""
Test per la riproduzione in streaming (core.audio_stream) e la cache dei
rendering di core.playback: partenza da un punto qualsiasi, loop A-B e
ripresa senza rifare il rendering. Nessun dispositivo audio reale: il
callback di PcmPlayer viene chiamato direttamente, e il motore usa un
synth e un player finti.

Esecuzione:
    python3 -m pytest tests/test_audio_stream.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import contextlib
import os
import sys
import types
import wave

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from core import audio_stream, playback
from core.project_io import parse_project_text


class _FakeTime:
    outputBufferDacTime = 1.0
    currentTime = 0.9


def _player(n_frames, loop=None):
    samples = np.arange(n_frames, dtype=np.int16).reshape(-1, 1)
    player = audio_stream.PcmPlayer(samples, 1000)
    player._stream = types.SimpleNamespace(latency=0.1, time=1.0)
    player.set_loop(loop)
    return player


def _pull(player, frames):
    out = np.zeros((frames, 1), dtype=np.int16)
    stopped = False
    try:
        player._callback(out, frames, _FakeTime(), None)
    except audio_stream._sd.CallbackStop:
        stopped = True
    return out[:, 0].tolist(), stopped


@pytest.mark.skipif(audio_stream._sd is None, reason="sounddevice non installato")
def test_callback_plays_from_start_frame_and_stops_at_the_end():
    player = _player(10)
    player._pos = 6
    data, stopped = _pull(player, 6)
    assert data == [6, 7, 8, 9, 0, 0]
    assert stopped


@pytest.mark.skipif(audio_stream._sd is None, reason="sounddevice non installato")
def test_callback_wraps_inside_the_loop_without_gaps():
    player = _player(20, loop=(4, 8))
    player._pos = 2
    data, stopped = _pull(player, 12)
    assert data == [2, 3, 4, 5, 6, 7, 4, 5, 6, 7, 4, 5]
    assert not stopped


@pytest.mark.skipif(audio_stream._sd is None, reason="sounddevice non installato")
def test_position_accounts_for_driver_latency_and_loop():
    player = _player(100, loop=(10, 20))
    player._pos = 15
    _pull(player, 10)                      # blocco che iniziera' a suonare a t=1.0 dal frame 15
    player._stream.time = 1.003            # 3 ms dopo -> frame 18
    assert player.position_frames() == 18
    player._stream.time = 1.008            # 8 ms dopo -> 23, cioe' 13 dopo il riavvolgimento
    assert player.position_frames() == 13


# ------------------------------------------------------------ motore + cache

class _FakeSynth:
    """Scrive un WAV di 'seconds' secondi (frame numerati, per verificare da
    dove parte la riproduzione) e conta i rendering."""

    def __init__(self, seconds=10, rate=1000):
        self.renders = 0
        self.seconds, self.rate = seconds, rate

    def render_to_wav(self, midi_path, wav_path, soundfont, stop_check, channel_overrides=None,
                      reverb_room=None):
        self.renders += 1
        self.reverb_room = reverb_room
        frames = (np.arange(self.seconds * self.rate) % 30000).astype(np.int16)
        with contextlib.closing(wave.open(wav_path, "wb")) as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self.rate)
            w.writeframes(frames.tobytes())
        return True


class _FakePlayer:
    started = []

    last_samples = None

    def __init__(self, samples, rate):
        self.samplerate, self.loop = rate, None
        _FakePlayer.last_samples = samples

    def set_loop(self, loop):
        self.loop = loop

    def start(self, start_frame=0):
        _FakePlayer.started.append((int(start_frame), self.loop))

    def wait(self):
        pass

    def stop(self):
        pass

    def is_active(self):
        return False

    def position_frames(self):
        return 0


@pytest.fixture
def streaming_engine(monkeypatch):
    synth = _FakeSynth()
    monkeypatch.setattr(playback, "_shared_synth", synth)
    monkeypatch.setattr(playback, "_find_soundfont", lambda: "/fake.sf2")
    monkeypatch.setattr(playback, "_stream_available", True)
    monkeypatch.setattr(audio_stream, "is_available", lambda: True)
    monkeypatch.setattr(audio_stream, "PcmPlayer", _FakePlayer)
    monkeypatch.setattr(playback, "_RENDER_CACHE", {})
    _FakePlayer.started = []
    return playback.PlaybackEngine(), synth


PROJECT = "Tempo: 120 BPM\nMetrica: 4/4\n\nPiano:\n  c d e f g a b c\n"


def _play_and_wait(engine, project, **kwargs):
    engine.play(project, **kwargs)
    engine._thread.join(5)


def test_resume_and_seek_reuse_the_cached_render(streaming_engine):
    engine, synth = streaming_engine
    project = parse_project_text(PROJECT)
    _play_and_wait(engine, project)
    _play_and_wait(engine, project, start_offset_beats=4)   # 120 BPM: beat 4 = 2 s
    _play_and_wait(engine, project, start_offset_beats=6)
    assert synth.renders == 1
    assert [start for start, _ in _FakePlayer.started] == [0, 2000, 3000]


def test_a_change_to_the_music_renders_again(streaming_engine):
    engine, synth = streaming_engine
    project = parse_project_text(PROJECT)
    _play_and_wait(engine, project)
    project.tracks[0].volume = 50
    _play_and_wait(engine, project)
    assert synth.renders == 2


def test_reverb_send_and_room_are_part_of_the_render(streaming_engine):
    engine, synth = streaming_engine
    project = parse_project_text(PROJECT)
    _play_and_wait(engine, project)
    assert synth.reverb_room == "stanza"
    project.tracks[0].reverb = 40              # nel MIDI (CC91): nuovo rendering
    _play_and_wait(engine, project)
    project.reverb_room = "sala_grande"        # non nel MIDI: conta nella chiave della cache
    _play_and_wait(engine, project)
    _play_and_wait(engine, project)
    assert synth.renders == 3 and synth.reverb_room == "sala_grande"


@pytest.mark.skipif(not __import__("core.effects", fromlist=["x"]).effects_available(),
                    reason="pedalboard non installato")
def test_master_chain_is_applied_and_a_master_change_does_not_resynthesize(streaming_engine):
    from core.effects import preset_params
    from core.model import Effect
    engine, synth = streaming_engine
    project = parse_project_text(PROJECT)
    _play_and_wait(engine, project)
    plain = _FakePlayer.last_samples.copy()
    project.master_effects = [Effect("limiter", dict(preset_params("limiter", "Sicurezza"), tetto=-12))]
    _play_and_wait(engine, project)
    limited = _FakePlayer.last_samples.copy()
    assert synth.renders == 1                                  # il mix prima del master era in cache
    assert np.abs(limited.astype(float)).max() < 0.5 * np.abs(plain.astype(float)).max()
    project.master_effects[0].params["tetto"] = -6
    _play_and_wait(engine, project)
    assert synth.renders == 1
    project.master_effects[0].enabled = False                 # master spento: il mix di sempre
    _play_and_wait(engine, project)
    assert synth.renders == 1 and np.array_equal(_FakePlayer.last_samples, plain)


def test_loop_is_converted_to_seconds_and_start_past_b_jumps_to_a(streaming_engine):
    engine, _ = streaming_engine
    project = parse_project_text(PROJECT)
    _play_and_wait(engine, project, start_offset_beats=1, loop_beats=(2.0, 4.0))
    _play_and_wait(engine, project, start_offset_beats=6, loop_beats=(2.0, 4.0))
    assert _FakePlayer.started == [(500, (1000.0, 2000.0)), (1000, (1000.0, 2000.0))]


# ------------------------------------------------------------ GUI: salto e loop

def test_main_window_seek_and_loop_markers_while_stopped():
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from gui.main_window import MainWindow

    win = MainWindow()
    win._replace_project(parse_project_text(PROJECT))   # 8 beat
    bar = win.playback_progress
    QTest.mouseClick(bar, Qt.LeftButton, pos=QPoint(bar.width() // 2, bar.height() // 2))
    assert win._playback_paused_beat == pytest.approx(4.0, abs=0.2)

    win.seek_to_beat(2)
    win.set_loop_start()
    assert not win.loop_action.isEnabled()          # manca ancora B
    win.seek_to_beat(6)
    win.set_loop_end()
    assert win.loop_action.isChecked()
    assert win._active_loop_beats() == (2.0, 6.0)

    win.seek_to_beat(1)
    win.set_loop_end()                               # B prima di A: rifiutato
    assert win._active_loop_beats() is None

    win.clear_loop()
    assert (win._loop_a_beat, win._loop_b_beat) == (None, None)
    win._dirty = False
    win.close()
    app.processEvents()


# ------------------------------------------------------------------ stderr silenziato durante il probing

def _same_file(fd_a, fd_b):
    a, b = os.fstat(fd_a), os.fstat(fd_b)
    return (a.st_dev, a.st_ino) == (b.st_dev, b.st_ino)


def test_native_stderr_suppression_is_restored_across_overlapping_threads():
    """Due render in thread diversi si sovrappongono: lo stderr resta
    silenziato finché ne è attivo uno e, alla fine, torna quello di prima
    (non la copia di /dev/null salvata dal secondo thread). Il file dietro
    a sys.stderr, se è diverso dal descrittore 2 come con la cattura di
    pytest, non viene mai toccato."""
    import threading
    import tempfile
    from core.playback import _suppress_native_stderr
    original = os.dup(2)
    null_fd = os.open(os.devnull, os.O_WRONLY)
    try:
        with tempfile.TemporaryFile("w+") as fake_stderr:
            real_stderr, sys.stderr = sys.stderr, fake_stderr
            try:
                first_in, second_in, first_out = (threading.Event() for _ in range(3))
                seen = {}

                def first():
                    with _suppress_native_stderr():
                        first_in.set()
                        second_in.wait(5)
                        seen["fake_untouched"] = not _same_file(fake_stderr.fileno(), null_fd)
                    first_out.set()

                def second():
                    first_in.wait(5)
                    with _suppress_native_stderr():
                        second_in.set()
                        first_out.wait(5)
                        seen["still_silent"] = _same_file(2, null_fd)   # l'altro è uscito

                threads = [threading.Thread(target=first), threading.Thread(target=second)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join(10)
                assert seen == {"fake_untouched": True, "still_silent": True}
            finally:
                sys.stderr = real_stderr
        assert _same_file(2, original) and not _same_file(2, null_fd)
    finally:
        os.dup2(original, 2)
        os.close(original)
        os.close(null_fd)
