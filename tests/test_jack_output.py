"""Uscita audio su JACK (core.jack_output): il ricampionamento, il flusso
con la forma di sounddevice.OutputStream provato con un JACK finto, e,
dove c'e' jackd, la riproduzione vera su un server di prova senza scheda
audio (driver "dummy"), riascoltata da una porta di ingresso."""

import os
import shutil
import subprocess
import threading
import time

import numpy as np
import pytest

from core import audio_stream, jack_output, settings


# ------------------------------------------------------------ ricampionamento

@pytest.mark.parametrize("source, target", [(44100, 48000), (48000, 44100), (44100, 96000), (48000, 48000)])
def test_resampler_keeps_a_sine(source, target):
    freq = 1000.0
    position = [0]

    def pull(frames):
        n = np.arange(position[0], position[0] + frames)
        position[0] += frames
        wave = np.sin(2 * np.pi * freq * n / source).astype(np.float32)
        return np.stack([wave, wave], axis=1)

    resampler = jack_output.SincResampler(source, target, 2, pull)
    out = np.concatenate([resampler.read(n) for n in (1024, 700, 1024, 33, 2048)])
    expected = np.sin(2 * np.pi * freq * np.arange(len(out)) / target)
    settled = slice(200, None)                      # dopo l'attacco (prima del frame 0 c'e' silenzio)
    assert np.max(np.abs(out[settled, 0] - expected[settled])) < 0.01
    assert np.allclose(out[:, 0], out[:, 1])


def test_resampler_removes_what_the_target_rate_cannot_carry():
    """Scendendo da 96 a 44,1 kHz un suono a 30 kHz non deve ripiegarsi nell'udibile."""
    position = [0]

    def pull(frames):
        n = np.arange(position[0], position[0] + frames)
        position[0] += frames
        return np.sin(2 * np.pi * 30000.0 * n / 96000).astype(np.float32).reshape(-1, 1)

    out = jack_output.SincResampler(96000, 44100, 1, pull).read(8192)
    assert np.max(np.abs(out[500:])) < 0.02


# ------------------------------------------------------------------ JACK finto

class _FakeRing:
    def __init__(self, size):
        self.size, self.data = size, bytearray()

    @property
    def read_space(self):
        return len(self.data)

    @property
    def write_space(self):
        return self.size - len(self.data)

    def read(self, count):
        out, self.data = bytes(self.data[:count]), self.data[count:]
        return out

    def write(self, data):
        self.data += data


class _FakePort:
    def __init__(self, name):
        self.name, self.array = name, np.zeros(0, dtype=np.float32)

    def get_array(self):
        return self.array

    def get_latency_range(self, _mode):
        return (0, 0)


class _FakePorts(list):
    def register(self, name):
        self.append(_FakePort(name))
        return self[-1]


class _FakeClient:
    samplerate, blocksize = 48000, 256

    def __init__(self, name, no_start_server=False):
        self.name, self.outports = name, _FakePorts()
        self.frame_time = self.last_frame_time = 0
        self.process = None
        self.active = self.closed = False
        self.connections = []

    def set_process_callback(self, callback):
        self.process = callback

    def set_shutdown_callback(self, callback):
        pass

    def activate(self):
        self.active = True

    def deactivate(self):
        self.active = False

    def close(self):
        self.closed = True

    def get_ports(self, **_kw):
        return ["system:playback_1", "system:playback_2"]

    def connect(self, source, target):
        self.connections.append((source.name, target))

    def run(self, frames):
        """Un periodo del server: quello che esce dalle porte."""
        for port in self.outports:
            port.array = np.zeros(frames, dtype=np.float32)
        self.last_frame_time = self.frame_time
        self.process(frames)
        self.frame_time += frames
        return np.stack([p.array for p in self.outports], axis=1)


class _FakeJack:
    PLAYBACK = 1
    Client, RingBuffer = _FakeClient, _FakeRing


def _run_until(client, condition, seconds=3.0):
    out = []
    deadline = time.monotonic() + seconds
    while not condition() and time.monotonic() < deadline:
        out.append(client.run(256))
        time.sleep(0.002)
    return np.concatenate(out) if out else np.zeros((0, 2), np.float32)


def test_stream_plays_int16_blocks_and_finishes():
    samples = (np.arange(12000, dtype=np.int16) % 2000 + 100).reshape(-1, 1)
    position = [0]
    finished = threading.Event()
    times = []

    class CallbackStop(Exception):
        pass

    def callback(outdata, frames, time_info, status):
        times.append(time_info.outputBufferDacTime)
        chunk = samples[position[0]:position[0] + frames]
        outdata[:len(chunk)] = chunk
        position[0] += len(chunk)
        if len(chunk) < frames:
            raise CallbackStop

    stream = jack_output.JackOutputStream(samplerate=48000, channels=1, dtype="int16", latency=0.05,
                                          callback=callback, finished_callback=finished.set,
                                          jack_module=_FakeJack)
    client = stream._client
    stream.start()
    assert client.connections == [("out_1", "system:playback_1"), ("out_2", "system:playback_2")]
    out = _run_until(client, finished.is_set)
    stream.close()
    assert finished.is_set() and client.closed and not stream.active
    heard = out[np.any(out != 0, axis=1)]
    assert len(heard) == len(samples)
    assert np.allclose(heard[:, 0], samples[:, 0] / 32768.0, atol=1e-6)
    assert np.allclose(heard[:, 0], heard[:, 1])            # mono su tutte e due le porte
    assert times == sorted(times)                            # l'orologio dei blocchi non torna indietro


def test_abort_stops_at_once():
    def callback(outdata, frames, _time_info, _status):
        outdata.fill(0.5)

    stream = jack_output.JackOutputStream(samplerate=48000, channels=2, dtype="float32", latency="low",
                                          callback=callback, jack_module=_FakeJack)
    stream.start()
    _run_until(stream._client, lambda: stream._written > 0)
    stream.abort()
    assert not stream.active and not stream._client.active
    stream.close()


# -------------------------------------------------------------- scelta dell'uscita

def test_system_output_is_the_default(monkeypatch):
    monkeypatch.delenv("SOUNDTEXT_AUDIO_OUTPUT", raising=False)
    settings._load()
    settings._cache.pop("audio_output", None)
    assert settings.get_audio_output() == "system"
    assert not jack_output.wants_jack()
    assert jack_output.fluidsynth_jack_driver() is None


def test_jack_choice_falls_back_when_no_server(monkeypatch):
    monkeypatch.setenv("SOUNDTEXT_AUDIO_OUTPUT", "jack")
    monkeypatch.setattr(jack_output, "jack_available", lambda: False)
    assert jack_output.wants_jack() and not jack_output.use_jack()


# -------------------------------------------------------------- server JACK vero

@pytest.fixture
def jack_server(monkeypatch, tmp_path):
    """Un jackd senza scheda audio, con un nome suo: non tocca il server
    (o PipeWire) dell'utente."""
    if shutil.which("jackd") is None or not jack_output.jack_supported():
        pytest.skip("jackd o JACK-Client non installati")
    name = f"soundtext-test-{os.getpid()}"
    monkeypatch.setenv("JACK_DEFAULT_SERVER", name)
    monkeypatch.setenv("SOUNDTEXT_AUDIO_OUTPUT", "jack")
    server = subprocess.Popen(["jackd", "-n", name, "-d", "dummy", "-r", "48000", "-p", "1024"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 5
        while not jack_output.jack_available():
            if time.monotonic() > deadline or server.poll() is not None:
                pytest.skip("jackd non parte in questo ambiente")
            time.sleep(0.1)
        yield name
    finally:
        server.terminate()
        try:
            server.wait(timeout=3)
        except subprocess.TimeoutExpired:
            server.kill()


def test_pcm_player_on_a_real_jack_server(jack_server):
    import jack
    rate = 44100                                   # diversa dai 48000 del server: si ricampiona
    wave = (np.sin(2 * np.pi * 440.0 * np.arange(rate) / rate) * 20000).astype(np.int16)
    recorded = []
    listener = jack.Client("listener", no_start_server=True)
    inport = listener.inports.register("in_1")
    listener.set_process_callback(lambda frames: recorded.append(inport.get_array().copy()))
    listener.activate()
    try:
        player = audio_stream.PcmPlayer(np.stack([wave, wave], axis=1), rate)
        player.start()
        assert type(player._stream).__name__ == "JackOutputStream"
        listener.connect(f"{jack_output.CLIENT_NAME}:out_1", inport)
        middle = None
        deadline = time.monotonic() + 6
        while player.is_active() and time.monotonic() < deadline:
            if middle is None and time.monotonic() > deadline - 5.4:
                middle = player.position_frames()
            time.sleep(0.02)
        assert not player.is_active(), "la riproduzione non e' finita"
        assert middle is not None and 0.2 * rate < middle < 0.95 * rate
    finally:
        listener.deactivate()
        listener.close()
    heard = np.concatenate(recorded)
    loud = heard[np.abs(heard) > 0.05]
    assert len(loud) > 0.8 * 48000                 # quasi un secondo di suono, a 48 kHz
    spectrum = np.abs(np.fft.rfft(heard * np.hanning(len(heard))))
    peak = np.argmax(spectrum) * 48000.0 / len(heard)
    assert abs(peak - 440.0) < 3.0                 # la nota e' rimasta un La: frequenza giusta dopo il ricampionamento
    assert np.max(np.abs(heard)) == pytest.approx(20000 / 32768.0, abs=0.03)
