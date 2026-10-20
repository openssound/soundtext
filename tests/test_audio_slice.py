"""
Test della quantizzazione dell'audio (core.audio_slice) su una ripresa
sintetica suonata un po' fuori tempo.

Esecuzione:
    python3 -m pytest tests/test_audio_slice.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)

import numpy as np
import pytest

from core.audio_quantize import QuantizeSettings
from core.audio_slice import clip_attacks, detect_attacks, quantize_clip
from core.audio_tracks import build_audio_layers, mix_layers, write_wav
from core.model import AudioClip, Project
from core.tempo_map import build_tempo_beat_map
from test_beat_track import RATE, _hits

GRID = [0.3 + k * 0.25 for k in range(16)]            # ottavi a 120 BPM, da 0,3 s


def _sloppy(tmp_path):
    rng = np.random.default_rng(1)
    played = [t + rng.uniform(-0.04, 0.04) for t in GRID]
    path = str(tmp_path / "sloppy.wav")
    write_wav(path, _hits(played, 1.0)[:, None], RATE)
    p = Project(tempo_bpm=120)
    clip = AudioClip("Batteria", path, 0.0)
    p.add_audio_track("Batteria").audio_clips.append(clip)
    return p, clip, played


def _attacks_after(p):
    mixed = mix_layers(np.zeros((0, 2), np.float32), RATE, build_audio_layers(p, p.tracks, build_tempo_beat_map(p)))
    return detect_attacks(mixed[:, :1], RATE)


def test_attacks_are_found_where_they_are(tmp_path):
    _p, clip, played = _sloppy(tmp_path)
    attacks = clip_attacks(clip)
    assert len(attacks) == len(played)
    assert max(abs(a - t) for a, t in zip(attacks, played)) < 0.002


def test_full_quantization_puts_every_attack_on_the_grid(tmp_path):
    p, clip, _played = _sloppy(tmp_path)
    pieces = quantize_clip(p, clip, 0.5)
    assert len(pieces) == 17                         # il tratto prima del primo attacco + uno per attacco
    p.get_track("Batteria").audio_clips = pieces
    after = _attacks_after(p)
    expected = [0.25 + k * 0.25 for k in range(16)]  # 0,3 s va sull'ottavo piu' vicino, 0,25
    assert len(after) == 16 and max(abs(a - e) for a, e in zip(after, expected)) < 0.002
    assert all(c.file == clip.file for c in pieces)  # il file e' sempre quello


def test_half_strength_moves_halfway(tmp_path):
    p, clip, played = _sloppy(tmp_path)
    p.get_track("Batteria").audio_clips = quantize_clip(p, clip, 0.5, QuantizeSettings(strength=0.5))
    after = _attacks_after(p)
    expected = [t + 0.5 * (g - 0.05 - t) for t, g in zip(played, GRID)]
    assert max(abs(a - e) for a, e in zip(after, expected)) < 0.003


def test_no_attacks_leaves_the_clip(tmp_path):
    path = str(tmp_path / "zero.wav")
    write_wav(path, np.zeros((RATE, 1), np.float32), RATE)
    p = Project(tempo_bpm=120)
    clip = AudioClip("Muta", path, 0.0)
    assert quantize_clip(p, clip, 0.5) == [clip]
