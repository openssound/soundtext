"""
Test delle elaborazioni non distruttive di una clip audio (AudioClip.transpose,
reverse, invert e channel, vedi core.audio_tracks), del loro formato nel file
.st e della cache, senza scheda audio.

Esecuzione:
    python3 -m pytest tests/test_clip_processing.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)

import dataclasses

import numpy as np
import pytest

from core import audio_tracks as at
from core.audio_tracks import AUDIO_SAMPLE_RATE as RATE, write_wav
from core.model import AudioClip, Project
from core.project_io import parse_project_text, project_to_text
from core.tempo_map import build_tempo_beat_map

TEMPO = build_tempo_beat_map(Project(tempo_bpm=120))       # 1 beat = 0,5 s


def _ramp(tmp_path, seconds=1.0):
    """Mono: una rampa da 0 a 0,5, cosi' si vede da che parte suona."""
    path = str(tmp_path / "ramp.wav")
    x = np.linspace(0.0, 0.5, int(seconds * RATE), dtype=np.float32).reshape(-1, 1)
    write_wav(path, x, RATE)
    return path


def _stereo(tmp_path):
    """Sinistro a 0,4, destro a -0,2 (costanti)."""
    path = str(tmp_path / "lr.wav")
    n = RATE // 2
    x = np.column_stack([np.full(n, 0.4, np.float32), np.full(n, -0.2, np.float32)])
    write_wav(path, x, RATE)
    return path


def _sine(tmp_path, freq, seconds=2.0):
    t = np.arange(int(seconds * RATE)) / RATE
    path = str(tmp_path / f"sine{freq:g}.wav")
    write_wav(path, (0.5 * np.sin(2 * np.pi * freq * t)).reshape(-1, 1).astype(np.float32), RATE)
    return path


def _mix(clip, tempo=120):
    p = Project(tempo_bpm=tempo)
    p.add_audio_track("A").audio_clips.append(clip)
    layers = at.build_audio_layers(p, p.tracks, build_tempo_beat_map(p))
    return at.mix_layers(np.zeros((0, 2), np.float32), RATE, layers)


def _middle(x, a, b):
    return x[int(a * RATE):int(b * RATE)]


def test_invert_flips_the_sign(tmp_path):
    path = _ramp(tmp_path)
    normal = _mix(AudioClip("R", path))
    inverted = _mix(AudioClip("R", path, invert=True))
    assert np.allclose(_middle(inverted, 0.1, 0.9), -_middle(normal, 0.1, 0.9), atol=1e-4)


def test_reverse_plays_the_trimmed_part_backwards(tmp_path):
    path = _ramp(tmp_path)                            # 0 -> 0,5 in 1 s
    clip = AudioClip("R", path, trim_start=0.2, trim_end=0.4, reverse=True)
    out = _mix(clip)[:, 0]
    assert len(out) == pytest.approx(0.4 * RATE, abs=4)
    # suona da 0,6 s del file (0,3) indietro fino a 0,2 s (0,1)
    assert out[int(0.05 * RATE)] == pytest.approx(0.5 * 0.55, abs=0.01)
    assert out[int(0.35 * RATE)] == pytest.approx(0.5 * 0.25, abs=0.01)
    assert out[int(0.05 * RATE)] > out[int(0.35 * RATE)]


def test_reverse_split_and_trim_follow_what_you_hear(tmp_path):
    path = _ramp(tmp_path)                            # 1 s = 2 beat
    clip = AudioClip("R", path, reverse=True)
    whole = _mix(dataclasses.replace(clip))[:, 0]
    second = at.split_clip(clip, 1.0, TEMPO)          # a meta'
    assert second is not None
    first_part = _mix(clip)[:, 0]
    second_part = _mix(second)[:, 0]
    second_alone = second_part[int(0.5 * RATE):]
    assert np.allclose(first_part[int(0.1 * RATE):int(0.4 * RATE)],
                       whole[int(0.1 * RATE):int(0.4 * RATE)], atol=1e-3)
    assert np.allclose(second_alone[int(0.1 * RATE):int(0.4 * RATE)],
                       whole[int(0.6 * RATE):int(0.9 * RATE)], atol=1e-3)
    # accorciare la fine toglie la fine di quello che si sente (l'inizio del file)
    at.trim_clip_end_to_beat(clip, 0.5, TEMPO)
    assert clip.trim_start == pytest.approx(0.75) and clip.trim_end == pytest.approx(0.0)


def test_channel_picks_left_right_or_mono(tmp_path):
    path = _stereo(tmp_path)
    left = _middle(_mix(AudioClip("S", path, channel="left")), 0.1, 0.4)
    right = _middle(_mix(AudioClip("S", path, channel="right")), 0.1, 0.4)
    mono = _middle(_mix(AudioClip("S", path, channel="mono")), 0.1, 0.4)
    assert np.allclose(left, 0.4, atol=1e-3)          # su entrambi i lati
    assert np.allclose(right, -0.2, atol=1e-3)
    assert np.allclose(mono, 0.1, atol=1e-3)
    assert at.clip_peak(AudioClip("S", path, channel="right")) == pytest.approx(0.2, abs=1e-3)


def test_transpose_an_octave_doubles_the_frequency(tmp_path):
    pytest.importorskip("pedalboard")
    clip = AudioClip("S", _sine(tmp_path, 440.0), transpose=12.0)
    out = _mix(clip)[:, 0]
    assert len(out) == pytest.approx(2.0 * RATE, abs=4)        # stessa durata
    x = out[RATE // 2:RATE // 2 + RATE]
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    assert np.fft.rfftfreq(len(x), 1.0 / RATE)[int(np.argmax(spectrum))] == pytest.approx(880.0, abs=1.0)


def test_every_field_changes_the_layers_signature(tmp_path):
    path = _stereo(tmp_path)
    p = Project(tempo_bpm=120)
    track = p.add_audio_track("A")
    base = AudioClip("S", path)
    track.audio_clips = [base]
    signatures = {at.layers_signature(at.build_audio_layers(p, p.tracks, TEMPO))}
    for change in ({"transpose": 1.0}, {"reverse": True}, {"invert": True}, {"channel": "left"}):
        track.audio_clips = [dataclasses.replace(base, **change)]
        signatures.add(at.layers_signature(at.build_audio_layers(p, p.tracks, TEMPO)))
    assert len(signatures) == 5


def test_new_keys_round_trip_in_the_st_file(tmp_path):
    path = _stereo(tmp_path)
    p = Project(tempo_bpm=120)
    p.add_audio_track("A").audio_clips.append(
        AudioClip("S", path, transpose=-0.3, reverse=True, invert=True, channel="left"))
    p.add_audio_track("B").audio_clips.append(AudioClip("T", path))
    text = project_to_text(p, str(tmp_path))
    assert "transpose=-0.3" in text and "reverse" in text and "invert" in text and "channel=left" in text
    back = parse_project_text(text, base_dir=str(tmp_path))
    a, b = back.get_track("A").audio_clips[0], back.get_track("B").audio_clips[0]
    assert (a.transpose, a.reverse, a.invert, a.channel) == (-0.3, True, True, "left")
    assert (b.transpose, b.reverse, b.invert, b.channel) == (0.0, False, False, "stereo")
    assert project_to_text(back, str(tmp_path)) == text


# ---------------------------------------------------------------------------
# Dissolvenza incrociata automatica (core.audio_tracks.auto_crossfades)
# ---------------------------------------------------------------------------

def _const(tmp_path, name, seconds, value):
    path = str(tmp_path / name)
    write_wav(path, np.full((int(seconds * RATE), 1), value, np.float32), RATE)
    return path


def test_overlapping_clips_crossfade_without_jumps(tmp_path):
    p = Project(tempo_bpm=120)                                       # 1 beat = 0,5 s
    track = p.add_audio_track("A")
    a = AudioClip("A", _const(tmp_path, "a.wav", 2.0, 0.5), 0.0)     # 0-2 s
    b = AudioClip("B", _const(tmp_path, "b.wav", 2.0, 0.5), 3.0)     # 1,5-3,5 s
    track.audio_clips = [a, b]
    assert at.auto_crossfades(track.audio_clips, TEMPO) == {id(a): (0.0, 0.5), id(b): (0.5, 0.0)}
    layers = at.build_audio_layers(p, p.tracks, TEMPO)
    assert [(l.fade_in, l.fade_out, l.fade_shape) for l in layers] == [(0.0, 0.5, "linear/equal"),
                                                                       (0.5, 0.0, "equal/linear")]
    out = at.mix_layers(np.zeros((0, 2), np.float32), RATE, layers)[:, 0]
    zone = out[int(1.4 * RATE):int(2.1 * RATE)]
    assert np.abs(np.diff(zone)).max() < 1e-3                       # nessun salto
    assert out[int(1.0 * RATE)] == pytest.approx(0.5, abs=1e-3)
    assert out[int(2.6 * RATE)] == pytest.approx(0.5, abs=1e-3)


def test_long_or_nested_overlaps_are_left_alone(tmp_path):
    long_a = AudioClip("A", _const(tmp_path, "a.wav", 6.0, 0.2), 0.0)    # 0-6 s
    long_b = AudioClip("B", _const(tmp_path, "b.wav", 6.0, 0.2), 4.0)    # 2-8 s: 4 s insieme, voluto
    inner = AudioClip("C", _const(tmp_path, "c.wav", 1.0, 0.2), 2.0)     # 1-2 s, dentro A
    assert at.auto_crossfades([long_a, long_b], TEMPO) == {}
    assert at.auto_crossfades([long_a, inner], TEMPO) == {}
    muted = AudioClip("M", _const(tmp_path, "m.wav", 2.0, 0.2), 11.0, muted=True)
    assert at.auto_crossfades([long_b, muted], TEMPO) == {}


def test_own_longer_fade_wins(tmp_path):
    a = AudioClip("A", _const(tmp_path, "a.wav", 2.0, 0.5), 0.0, fade_out=1.0)
    b = AudioClip("B", _const(tmp_path, "b.wav", 2.0, 0.5), 3.0)
    p = Project(tempo_bpm=120)
    p.add_audio_track("A").audio_clips = [a, b]
    first = at.build_audio_layers(p, p.tracks, TEMPO)[0]
    assert (first.fade_out, first.fade_shape) == (1.0, "linear")


# ---------------------------------------------------------------------------
# Ripeti in loop (AudioClip.loop_length, core.audio_tracks.loop_repeats)
# ---------------------------------------------------------------------------

def test_loop_repeats_the_clip_and_cuts_the_last_round(tmp_path):
    clip = AudioClip("R", _ramp(tmp_path), 2.0, fade_in=0.1, fade_out=0.1, loop_length=5.0)   # 1 s = 2 beat
    copies = at.loop_repeats(clip, TEMPO)
    assert [c.start_beat for c in copies] == [2.0, 4.0, 6.0]
    assert at.clip_duration_beats(copies[-1], TEMPO) == pytest.approx(1.0)
    assert [(c.fade_in, c.fade_out) for c in copies] == [(0.1, 0.0), (0.0, 0.0), (0.0, 0.1)]
    assert at.clip_span_beats(clip, TEMPO) == 5.0
    out = _mix(clip)[:, 0]
    assert len(out) == pytest.approx(3.5 * RATE, abs=8)               # da 1 s a 3,5 s
    for second in (1.5, 2.5, 3.25):                                   # stesso punto della rampa a ogni giro
        lag = second - 1.0 - int(second - 1.0)
        assert out[int(second * RATE)] == pytest.approx(0.5 * lag, abs=0.01)


def test_shorter_loop_length_means_no_loop(tmp_path):
    clip = AudioClip("R", _ramp(tmp_path), 0.0, loop_length=1.0)     # la clip dura 2 beat
    assert at.loop_repeats(clip, TEMPO) == [clip] and at.clip_span_beats(clip, TEMPO) == pytest.approx(2.0)


def test_split_removes_the_loop_and_loop_round_trips(tmp_path):
    clip = AudioClip("R", _ramp(tmp_path), 0.0, loop_length=8.0)
    second = at.split_clip(clip, 1.0, TEMPO)
    assert second is not None and clip.loop_length == second.loop_length == 0.0
    p = Project(tempo_bpm=120)
    p.add_audio_track("A").audio_clips.append(AudioClip("R", _ramp(tmp_path), 0.0, loop_length=6.5))
    text = project_to_text(p, str(tmp_path))
    assert "loop=6.5" in text
    assert parse_project_text(text, base_dir=str(tmp_path)).get_track("A").audio_clips[0].loop_length == 6.5


# ---------------------------------------------------------------------------
# Curva del volume (AudioClip.gain_points)
# ---------------------------------------------------------------------------

def test_gain_curve_follows_the_points(tmp_path):
    path = _const(tmp_path, "c.wav", 2.0, 0.5)
    clip = AudioClip("C", path, 0.0, gain_points=[(0.5, 0.0), (1.5, -20.0)])
    out = _mix(clip)[:, 0]
    assert out[int(0.25 * RATE)] == pytest.approx(0.5, abs=1e-3)          # prima del primo punto: 0 dB
    assert out[int(1.0 * RATE)] == pytest.approx(0.5 * 10 ** (-10 / 20), abs=1e-3)
    assert out[int(1.75 * RATE)] == pytest.approx(0.05, abs=1e-3)          # dopo l'ultimo: -20 dB
    assert np.abs(np.diff(out[int(0.4 * RATE):int(1.6 * RATE)])).max() < 1e-3


def test_gain_curve_survives_trim_split_and_the_file(tmp_path):
    path = _const(tmp_path, "c.wav", 2.0, 0.5)
    clip = AudioClip("C", path, 0.0, gain_points=[(0.5, 0.0), (1.5, -20.0)])
    at.trim_clip_start_to_beat(clip, 1.0, TEMPO)                            # toglie 0,5 s davanti
    assert clip.gain_points == [(0.0, 0.0), (1.0, -20.0)]
    second = at.split_clip(clip, 2.0, TEMPO)                                # a 0,5 s della parte suonata
    assert clip.gain_points == [(0.0, 0.0), (0.5, -10.0)]
    assert second.gain_points == [(0.0, -10.0), (0.5, -20.0)]
    p = Project(tempo_bpm=120)
    p.add_audio_track("A").audio_clips.append(AudioClip("C", path, 0.0, gain_points=[(0.0, 0.0), (2.5, -6.0)]))
    text = project_to_text(p, str(tmp_path))
    assert "gain_points=0:0,2.5:-6" in text
    back = parse_project_text(text, base_dir=str(tmp_path)).get_track("A").audio_clips[0]
    assert back.gain_points == [(0.0, 0.0), (2.5, -6.0)] and back.gain_db == 0.0


# ---------------------------------------------------------------------------
# Correzione dell'intonazione (AudioClip.pitch_correct, core.pitch_correct)
# ---------------------------------------------------------------------------

def _peak_hz(x):
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    freqs = np.fft.rfftfreq(len(x), 1.0 / RATE)
    k = int(np.argmax(spectrum))
    a, b, c = spectrum[k - 1], spectrum[k], spectrum[k + 1]          # interpolazione parabolica
    return freqs[k] + 0.5 * (a - c) / (a - 2 * b + c) * (freqs[1] - freqs[0])


def _mix_in_key(clip, key):
    p = Project(tempo_bpm=120, key=key)
    p.add_audio_track("A").audio_clips.append(clip)
    layers = at.build_audio_layers(p, p.tracks, build_tempo_beat_map(p))
    return at.mix_layers(np.zeros((0, 2), np.float32), RATE, layers)[:, 0]


def test_pitch_correction_moves_notes_to_the_scale(tmp_path):
    pytest.importorskip("pedalboard")
    path = _sine(tmp_path, 450.0, seconds=2.0)                         # La crescente di 39 cent
    full = _mix_in_key(AudioClip("S", path, pitch_correct=100), "C")
    half = _mix_in_key(AudioClip("S", path, pitch_correct=50), "C")
    assert _peak_hz(full[RATE // 2:3 * RATE // 2]) == pytest.approx(440.0, abs=1.5)
    assert _peak_hz(half[RATE // 2:3 * RATE // 2]) == pytest.approx(445.0, abs=1.5)
    assert len(full) == pytest.approx(2 * RATE, abs=4)
    # il Sib non e' in Do: in Fa maggiore il 450 Hz va al La (440), il 470 al Sib (466)
    up = _mix_in_key(AudioClip("S", _sine(tmp_path, 470.0), pitch_correct=100), "F")
    assert _peak_hz(up[RATE // 2:3 * RATE // 2]) == pytest.approx(466.2, abs=1.5)


def test_pitch_correct_round_trips_and_changes_the_signature(tmp_path):
    path = _stereo(tmp_path)
    p = Project(tempo_bpm=120)
    track = p.add_audio_track("A")
    track.audio_clips = [AudioClip("S", path, pitch_correct=60)]
    text = project_to_text(p, str(tmp_path))
    assert "pitch_correct=60" in text
    assert parse_project_text(text, base_dir=str(tmp_path)).get_track("A").audio_clips[0].pitch_correct == 60
    with_correction = at.layers_signature(at.build_audio_layers(p, p.tracks, TEMPO))
    track.audio_clips[0].pitch_correct = 0
    assert at.layers_signature(at.build_audio_layers(p, p.tracks, TEMPO)) != with_correction
