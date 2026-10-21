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
