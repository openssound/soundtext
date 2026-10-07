"""
Test della registrazione delle tracce audio (fase 2, core.audio_recording)
senza scheda audio: lo stream di sounddevice e' sostituito da uno stream
finto che fa da cavo "loopback" (cio' che esce rientra dall'ingresso con
una latenza nota), per verificare che la ripresa finisca a tempo.

Esecuzione:
    python3 -m pytest tests/test_audio_recording.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import audio_recording, settings
from core.audio_recording import (
    build_calibration_backing, measure_latency_ms,
    Backing, ClickSchedule, DuplexRecorder, InputMonitor, Take, build_backing, build_click_schedule,
    InputDevice, channel_choices, parse_channel_spec, pick_input_device, recorded_clip, save_take,
)
from core.audio_tracks import AUDIO_SAMPLE_RATE, read_wav_info, write_wav
from core.model import AudioClip, Project
from core.project_io import parse_project_text, project_to_text

RATE = AUDIO_SAMPLE_RATE


class LoopbackStream:
    """Stream full-duplex finto: a ogni blocco chiama il callback con
    l'ingresso = uscita di 'delay' frame prima (sul canale input_channel),
    e tempi DAC/ADC coerenti con quel ritardo (uscita out_latency nel
    futuro, ingresso in_latency nel passato)."""

    def __init__(self, callback, rate, in_channels, in_latency=0.004, out_latency=0.006,
                 block=256, input_channel=0, report_times=True, hidden_delay=0.0, noise=0.0):
        self.callback = callback
        self.rate = rate
        self.in_channels = in_channels
        self.in_latency, self.out_latency = in_latency, out_latency
        self.block = block
        self.input_channel = input_channel
        self.report_times = report_times
        # hidden_delay: ritardo in piu' che il driver non dichiara (quello che
        # la compensazione manuale / la calibrazione devono correggere)
        self.delay = int(round((in_latency + out_latency + hidden_delay) * rate))
        self.noise = noise
        self.rng = np.random.default_rng(0)
        self.played = np.zeros(0, dtype=np.float32)
        self.now = 100.0

    def start(self):
        pass

    def pump(self, blocks):
        for _ in range(blocks):
            n = self.block
            start = len(self.played)
            indata = np.zeros((n, self.in_channels), dtype=np.float32)
            for i in range(n):
                src = start + i - self.delay
                if 0 <= src < len(self.played):
                    indata[i, self.input_channel] = self.played[src]
            if self.noise:
                indata[:, self.input_channel] += self.rng.standard_normal(n).astype(np.float32) * self.noise
            outdata = np.zeros((n, 2), dtype=np.float32)
            times = SimpleNamespace(
                outputBufferDacTime=(self.now + self.out_latency) if self.report_times else 0.0,
                inputBufferAdcTime=(self.now - self.in_latency) if self.report_times else 0.0)
            self.callback(indata, outdata, n, times, None)
            self.played = np.concatenate([self.played, outdata[:, 0]])
            self.now += n / float(self.rate)

    def stop(self):
        pass

    def close(self):
        pass


def _recorder(backing, channels=(0,), **stream_kwargs):
    holder = {}

    def factory(callback, rate, in_channels, input_device, output_device):
        holder["stream"] = LoopbackStream(callback, rate, in_channels, **stream_kwargs)
        return holder["stream"]

    rec = DuplexRecorder(backing, input_device=None, channels=channels, stream_factory=factory)
    rec.start()
    return rec, holder["stream"]


def _silent_clicks(rate=RATE):
    return ClickSchedule([], np.zeros(10, np.float32), np.zeros(10, np.float32), 0.0, rate)


# --------------------------------------------------------------- canali

def test_channel_choices_and_specs():
    assert channel_choices(2) == [("Ingresso 1 (mono)", "1"), ("Ingresso 2 (mono)", "2"),
                                  ("Ingressi 1+2 (stereo)", "1+2")]
    assert [spec for _, spec in channel_choices(4)][-2:] == ["1+2", "3+4"]
    assert parse_channel_spec("2", 2) == (1,)
    assert parse_channel_spec("1+2", 2) == (0, 1)
    assert parse_channel_spec("3+4", 2) == (0,)       # il dispositivo non li ha
    assert parse_channel_spec("abc", 2) == (0,)


def test_input_settings_are_saved_per_track_in_the_project():
    p = Project()
    t = p.add_audio_track("Chitarra")
    t.input_profile, t.input_channels = "chitarra", "2"
    p.add_audio_track("Tastiera").input_channels = "1+2"
    q = parse_project_text(project_to_text(p))
    assert (q.get_track("Chitarra").input_profile, q.get_track("Chitarra").input_channels) == ("chitarra", "2")
    assert (q.get_track("Tastiera").input_profile, q.get_track("Tastiera").input_channels) == ("", "1+2")


def test_recording_settings_round_trip():
    settings.set_audio_input_device("Scarlett 2i2 (ALSA)")
    settings.set_input_latency_ms("Scarlett 2i2 (ALSA)", 12.5)
    settings.set_record_count_in_bars(2)
    settings.set_record_metronome(False)
    assert settings.get_audio_input_device() == "Scarlett 2i2 (ALSA)"
    assert settings.get_input_latency_ms("Scarlett 2i2 (ALSA)") == 12.5
    assert settings.get_input_latency_ms("altro") == 0.0
    assert settings.get_record_count_in_bars() == 2
    assert settings.get_record_metronome() is False
    settings.set_record_metronome(True)
    settings.set_record_count_in_bars(1)


# --------------------------------------------------------------- click

def test_count_in_follows_tempo_and_meter_at_the_start_beat():
    p = Project(tempo_bpm=120)
    clicks, count_in = build_click_schedule(p, 0.0, count_in_bars=1, with_metronome=False, volume=1.0)
    assert count_in == pytest.approx(2.0)
    assert [f for f, _ in clicks._events] == [0, 24000, 48000, 72000]
    assert [a for _, a in clicks._events] == [True, False, False, False]

    p = Project(tempo_bpm=60, time_sig="6/8")
    clicks, count_in = build_click_schedule(p, 0.0, count_in_bars=2, with_metronome=False, volume=1.0)
    assert len(clicks) == 12 and count_in == pytest.approx(6.0)   # 12 ottavi a 60 BPM (quarto)


def test_metronome_continues_after_the_count_in_on_the_song_grid():
    p = Project(tempo_bpm=120)
    clicks, count_in = build_click_schedule(p, 6.0, count_in_bars=1, with_metronome=True, volume=1.0,
                                            max_seconds=5.0)
    frames = [f for f, _ in clicks._events]
    assert frames[:4] == [0, 24000, 48000, 72000]        # conteggio
    assert frames[4:7] == [96000, 120000, 144000]        # beat 6, 7, 8 del brano
    accents = [a for _, a in clicks._events][4:8]
    assert accents == [False, False, True, False]        # beat 8 = inizio della battuta 3


def test_click_schedule_adds_clicks_across_block_boundaries():
    click = np.ones(100, dtype=np.float32)
    sched = ClickSchedule([(0.001, True)], click, click * 0.5, 0.5, 1000)   # frame 1
    out = np.zeros((60, 2), dtype=np.float32)
    sched.add_into(out, 0)
    assert out[0, 0] == 0 and out[1, 0] == 0.5 and out[59, 1] == 0.5
    out2 = np.zeros((60, 2), dtype=np.float32)
    sched.add_into(out2, 60)
    assert np.all(out2[:41] == 0.5) and np.all(out2[41:] == 0)


# --------------------------------------------------------------- base

def test_backing_is_count_in_silence_then_the_song_from_the_start_beat(tmp_path, monkeypatch):
    src = str(tmp_path / "g.wav")
    ramp = np.linspace(0, 0.5, RATE * 4, dtype=np.float32).reshape(-1, 1)
    write_wav(src, ramp, RATE, bits=24)
    p = Project(tempo_bpm=120)
    p.add_audio_track("Gtr").audio_clips.append(AudioClip("r", src, 0.0))
    backing = build_backing(p, start_beat=2.0, count_in_bars=1, with_metronome=False)
    assert backing.count_in_seconds == pytest.approx(2.0)
    assert len(backing.samples) == RATE * 2 + RATE * 3   # conteggio + i 3 s che restano dal beat 2
    assert np.all(backing.samples[:RATE * 2] == 0)
    assert backing.samples[RATE * 2, 0] == pytest.approx(ramp[RATE, 0], abs=1e-5)
    assert not backing.midi_skipped


def test_backing_without_soundfont_keeps_audio_and_says_so(tmp_path, monkeypatch):
    from core import playback
    monkeypatch.setattr(playback, "_shared_synth", None)
    monkeypatch.setattr(playback.shutil, "which", lambda name: None)
    p = Project()
    p.add_track("Piano", "Piano", "4: c d e f")
    backing = build_backing(p, 0.0, count_in_bars=1, with_metronome=True)
    assert backing.midi_skipped
    assert len(backing.clicks) > 4


def test_backing_can_leave_out_the_track_being_recorded(tmp_path):
    src = str(tmp_path / "g.wav")
    write_wav(src, np.full((RATE, 1), 0.5, np.float32), RATE, bits=16)
    p = Project()
    p.add_audio_track("Voce").audio_clips.append(AudioClip("vecchia", src, 0.0))
    assert np.max(np.abs(build_backing(p, 0.0, 0, False).samples)) > 0.4
    backing = build_backing(p, 0.0, 0, False, mute_track="Voce")
    assert len(backing.samples) == 0
    assert not p.get_track("Voce").mute   # il progetto vero non viene toccato


# --------------------------------------------------------------- registrazione

def _song_backing(count_in_seconds=0.5, song_seconds=1.0):
    rng = np.random.default_rng(1)
    song = (rng.standard_normal((int(song_seconds * RATE), 1)) * 0.2).astype(np.float32)
    lead = np.zeros((int(count_in_seconds * RATE), 2), dtype=np.float32)
    return Backing(np.concatenate([lead, np.repeat(song, 2, axis=1)]), RATE, _silent_clicks(),
                   count_in_seconds), song[:, 0]


def test_loopback_take_lines_up_with_the_song_after_trim():
    backing, song = _song_backing()
    rec, stream = _recorder(backing, in_latency=0.004, out_latency=0.006)
    stream.pump(400)
    take = rec.stop()
    assert take.alignment_seconds == pytest.approx(0.010)
    clip = recorded_clip("Take", "x.wav", 4.0, backing.count_in_seconds, take.alignment_seconds, 0.0)
    assert clip.start_beat == 4.0 and clip.trim_start == pytest.approx(0.51)
    trim = int(round(clip.trim_start * RATE))
    recorded = take.samples[trim:trim + len(song), 0]
    assert np.allclose(recorded, song[:len(recorded)], atol=1e-6)


def test_manual_latency_compensation_adds_to_the_trim():
    clip = recorded_clip("T", "x.wav", 0.0, count_in_seconds=2.0, alignment_seconds=0.01,
                         manual_latency_ms=15)
    assert clip.trim_start == pytest.approx(2.025)
    assert recorded_clip("T", "x.wav", 0.0, 0.0, 0.0, -50).trim_start == 0.0   # mai negativo


def test_without_driver_times_the_declared_latency_is_used():
    backing, _song = _song_backing()
    rec, stream = _recorder(backing, report_times=False)
    rec._latency_estimate = 0.02
    stream.pump(10)
    assert rec.stop().alignment_seconds == pytest.approx(0.02)


def test_records_only_the_chosen_input_channels_and_reports_peaks():
    backing, _song = _song_backing()
    rec, stream = _recorder(backing, channels=(1,), input_channel=1)
    stream.pump(200)
    assert rec.read_peak() > 0.1
    assert rec.read_peak() == 0.0            # azzerato dopo la lettura
    take = rec.stop()
    assert take.samples.shape[1] == 1 and take.peak > 0.1 and not take.clipped
    assert rec.elapsed_seconds == pytest.approx(200 * 256 / RATE)


def test_output_keeps_going_with_silence_and_clicks_after_the_backing_ends():
    click = np.ones(10, dtype=np.float32)
    sched = ClickSchedule([(1.0, True)], click, click, 1.0, RATE)
    backing = Backing(np.zeros((100, 2), np.float32), RATE, sched, 0.0)
    rec, stream = _recorder(backing, block=1024)
    stream.pump(60)   # ~1,3 s: il click a 1 s e' ben oltre la fine della base
    rec.stop()
    assert stream.played[RATE:RATE + 10].tolist() == [1.0] * 10


def test_fallback_rate_resamples_backing_and_clicks():
    backing, _ = _song_backing(count_in_seconds=0.5, song_seconds=1.0)
    rec = DuplexRecorder(backing, None, (0,), fallback_rate=44100)
    rec._use_rate(44100)
    assert rec.rate == 44100 and len(rec.backing.samples) == pytest.approx(1.5 * 44100, abs=2)


def test_save_take_converts_to_project_rate(tmp_path):
    samples = (np.sin(np.arange(44100) / 10.0) * 0.3).astype(np.float32).reshape(-1, 1)
    path = save_take(Take(samples, 44100, 0.0, 0.3), str(tmp_path), "Voce take")
    info = read_wav_info(path)
    assert os.path.basename(path) == "Voce take.wav"
    assert (info.samplerate, info.bits, info.channels) == (RATE, 24, 1)
    assert info.seconds == pytest.approx(1.0, abs=0.001)


def test_input_monitor_reports_peak():
    holder = {}

    def factory(callback, in_channels, device):
        holder["cb"] = callback
        return SimpleNamespace(start=lambda: None, stop=lambda: None, close=lambda: None)

    mon = InputMonitor(None, (1,), stream_factory=factory)
    mon.start()
    data = np.zeros((64, 2), np.float32)
    data[5, 1] = -0.7
    data[6, 0] = 0.9   # canale non scelto: ignorato
    holder["cb"](data, 64, None, None)
    assert mon.read_peak() == pytest.approx(0.7)
    assert mon.read_peak() == 0.0
    mon.stop()


def test_level_to_db():
    assert audio_recording.level_to_db(1.0) == pytest.approx(0.0)
    assert audio_recording.level_to_db(0.5) == pytest.approx(-6.02, abs=0.01)
    assert audio_recording.level_to_db(0.0) == pytest.approx(-120.0)


# --------------------------------------------------------------- calibrazione

def _calibrate(**stream_kwargs):
    backing, times = build_calibration_backing()
    rec, stream = _recorder(backing, **stream_kwargs)
    stream.pump(int(len(backing.samples) / 256) + 20)
    return measure_latency_ms(rec.stop(), times)


def test_calibration_measures_the_delay_the_driver_does_not_report():
    assert _calibrate(hidden_delay=0.0123) == pytest.approx(12.3, abs=0.1)
    assert _calibrate(hidden_delay=0.0) == pytest.approx(0.0, abs=0.1)


def test_calibration_tolerates_some_noise():
    assert _calibrate(hidden_delay=0.004, noise=0.002) == pytest.approx(4.0, abs=0.2)


def test_calibration_without_signal_explains():
    backing, times = build_calibration_backing()
    rec, stream = _recorder(backing, input_channel=0, channels=(1,))   # si registra l'ingresso sbagliato
    stream.pump(int(len(backing.samples) / 256) + 20)
    with pytest.raises(RuntimeError, match="Click non rilevati"):
        measure_latency_ms(rec.stop(), times)


# ------------------------------------------------------------------ scheda audio esterna

def test_external_input_is_recognised_on_every_system(monkeypatch):
    from core.audio_recording import is_external_input
    monkeypatch.setattr(audio_recording.sys, "platform", "linux")
    paths = {"/sys/class/sound/card0": "/sys/devices/pci0000:00/0000:00:1b.0/sound/card0",
             "/sys/class/sound/card3": "/sys/devices/pci0000:00/0000:00:1a.7/usb2/2-1/sound/card3"}
    monkeypatch.setattr(audio_recording.os.path, "realpath", lambda p: paths.get(p, p))
    assert is_external_input("Qualsiasi Scheda: Audio (hw:3,0)")
    assert not is_external_input("HDA Intel PCH: ALC892 Analog (hw:0,0)")
    assert not is_external_input("default") and not is_external_input("pipewire")
    for system in ("win32", "darwin"):
        monkeypatch.setattr(audio_recording.sys, "platform", system)
        assert is_external_input("Line In (Behringer UMC204HD 192k)")
        assert is_external_input("Input 1/2 (Qualsiasi interfaccia)")
        assert is_external_input("Microphone (USB Audio CODEC)")
        assert not is_external_input("Microphone Array (Realtek(R) Audio)")
        assert not is_external_input("MacBook Pro Microphone")
        assert not is_external_input("BlackHole 2ch")
        assert not is_external_input("Microsoft Sound Mapper - Input")


def _dev(index, name, external=False):
    return InputDevice(index, name, "ALSA", 0, 2, AUDIO_SAMPLE_RATE, external)


def test_an_external_card_is_proposed_unless_a_precise_input_was_chosen(monkeypatch):
    monkeypatch.setattr(audio_recording, "_sounddevice", lambda: None)
    internal, generic, card = _dev(0, "HDA Intel: Analog (hw:0,0)"), _dev(9, "default"), _dev(3, "Scheda (hw:3,0)", True)
    devices = [internal, card, generic]
    assert pick_input_device(devices, generic.label) is card           # "default" non e' una scelta precisa
    assert pick_input_device(devices, "") is card
    assert pick_input_device(devices, internal.label) is internal      # scelta precisa: rispettata
    assert pick_input_device([internal, generic], generic.label) is generic


class _FakeSd:
    """sounddevice finto: la scheda lavora solo a 44100 Hz."""

    def __init__(self):
        self.opened = []
        self.attempts = 0

    def _open(self, kind, samplerate, **kw):
        self.attempts += 1
        if samplerate != 44100:
            raise RuntimeError("Invalid sample rate")
        self.opened.append((kind, samplerate, kw.get("device")))
        latency = (0.01, 0.01) if kind == "duplex" else 0.01        # come sounddevice
        return SimpleNamespace(start=lambda: None, stop=lambda: None, close=lambda: None, latency=latency)

    def InputStream(self, samplerate, **kw):
        return self._open("in", samplerate, **kw)

    def OutputStream(self, samplerate, **kw):
        return self._open("out", samplerate, **kw)

    def Stream(self, samplerate, **kw):
        return self._open("duplex", samplerate, **kw)


def test_level_monitor_falls_back_to_the_card_rate(monkeypatch):
    sd = _FakeSd()
    monkeypatch.setattr(audio_recording, "_sounddevice", lambda: sd)
    InputMonitor(3, [0], fallback_rate=44100).start()
    assert sd.opened == [("in", 44100, 3)]
    with pytest.raises(RuntimeError):
        InputMonitor(3, [0]).start()


def test_two_different_cards_use_two_streams(monkeypatch):
    sd = _FakeSd()
    monkeypatch.setattr(audio_recording, "_sounddevice", lambda: sd)
    z = np.zeros(1, np.float32)
    backing = Backing(np.zeros((4800, 2), np.float32), AUDIO_SAMPLE_RATE, ClickSchedule([], z, z, 0.0, AUDIO_SAMPLE_RATE), 0.0)
    two = DuplexRecorder(backing, 3, [0], output_device=22, fallback_rate=44100)
    two.start()
    one = DuplexRecorder(backing, 22, [0], output_device=22, fallback_rate=44100)
    one.start()
    assert (len(two._streams), len(one._streams), two.rate, one.rate) == (2, 1, 44100, 44100)


def test_unsupported_rate_is_skipped_without_failed_attempts(monkeypatch):
    sd = _FakeSd()

    def check_input_settings(device=None, samplerate=None, **kw):
        if samplerate != 44100:
            raise RuntimeError("Invalid sample rate")
    sd.check_input_settings = check_input_settings
    monkeypatch.setattr(audio_recording, "_sounddevice", lambda: sd)
    InputMonitor(3, [0], fallback_rate=44100).start()
    z = np.zeros(1, np.float32)
    backing = Backing(np.zeros((4800, 2), np.float32), AUDIO_SAMPLE_RATE, ClickSchedule([], z, z, 0.0, AUDIO_SAMPLE_RATE), 0.0)
    rec = DuplexRecorder(backing, 3, [0], output_device=22, fallback_rate=44100)
    rec.start()
    assert rec.rate == 44100 and sd.attempts == len(sd.opened) == 3      # monitor + ingresso + uscita


# ------------------------------------------------------------------ riascolto della ripresa

def test_take_preview_is_aligned_like_the_clip():
    from core.audio_recording import take_preview
    rate = AUDIO_SAMPLE_RATE
    z = np.zeros(1, np.float32)
    base = np.zeros((3 * rate, 2), np.float32)
    base[2 * rate + 100] = 0.25                                  # un colpo nella base, 100 frame dopo il conteggio
    backing = Backing(base, rate, ClickSchedule([], z, z, 0.0, rate), 2.0)
    rec = np.zeros((4 * rate, 1), np.float32)
    shift = round((2.0 + 0.010 + 0.005) * rate)                 # conteggio + ritardo misurato + manuale
    rec[shift + 100] = 0.5                                       # suonato a tempo con quel colpo
    take = Take(rec, rate, 0.010, 0.5)
    alone = take_preview(take, backing, 5.0, with_backing=False)
    assert alone.shape[1] == 2 and np.argmax(alone[:, 0]) == 100 and alone[100, 1] == 0.5
    mixed = take_preview(take, backing, 5.0)
    assert mixed[100, 0] == pytest.approx(0.75)                  # ripresa e base nello stesso istante
    take_44 = Take(np.zeros((3 * 44100, 1), np.float32), 44100, 0.0, 0.0)  # scheda a 44,1 kHz
    assert len(take_preview(take_44, backing, 0.0, with_backing=False)) == pytest.approx(rate, abs=1)


def test_take_player_plays_to_the_end_and_stops():
    from core.audio_recording import TakePlayer
    streams = []

    class FakeOut:
        def __init__(self, callback, rate, device):
            self.callback = callback
            streams.append(self)

        def start(self):
            pass

        def stop(self):
            self.stopped = True

        def close(self):
            pass
    audio = np.full((1000, 2), 0.5, np.float32)
    player = TakePlayer(audio, AUDIO_SAMPLE_RATE, output_device=7, stream_factory=FakeOut)
    player.start()
    out = np.ones((600, 2), np.float32)
    streams[0].callback(out, 600, None, None)
    assert player.playing and np.all(out == 0.5)
    streams[0].callback(out, 600, None, None)
    assert np.all(out[:400] == 0.5) and np.all(out[400:] == 0) and not player.playing
    player.stop()
    assert streams[0].stopped and not player.playing
