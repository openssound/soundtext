"""
Test di "Rimuovi i silenzi" (core.audio_silence) su una ripresa sintetica:
tre frasi separate da silenzi di lunghezza diversa.

Esecuzione:
    python3 -m pytest tests/test_remove_silences.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)

import numpy as np
import pytest

from core.audio_silence import EDGE_FADE, PRE_ROLL, TAIL, clip_levels_db, remove_silences, sound_regions
from core.audio_tracks import build_audio_layers, mix_layers, write_wav
from core.model import AudioClip, Project
from core.tempo_map import build_tempo_beat_map

RATE = 44100
# (inizio, fine) delle frasi in secondi; fra la seconda e la terza solo 0,2 s
PHRASES = [(0.5, 1.5), (2.5, 3.0), (3.2, 4.0)]
LENGTH = 5.0


def _take(tmp_path, noise_db=-70.0):
    rng = np.random.default_rng(3)
    n = int(LENGTH * RATE)
    t = np.arange(n) / RATE
    samples = rng.normal(0.0, 10 ** (noise_db / 20), n)
    for a, b in PHRASES:
        part = (t >= a) & (t < b)
        samples[part] += 0.5 * np.sin(2 * np.pi * 220 * t[part])
    path = str(tmp_path / "voce.wav")
    write_wav(path, samples.astype(np.float32)[:, None], RATE)
    p = Project(tempo_bpm=120)
    clip = AudioClip("Voce", path, 4.0)
    p.add_audio_track("Voce").audio_clips.append(clip)
    return p, clip


def test_long_silences_go_short_ones_stay(tmp_path):
    _p, clip = _take(tmp_path)
    levels, total = clip_levels_db(clip)
    assert total == pytest.approx(LENGTH)
    regions = sound_regions(levels, total)
    assert len(regions) == 2                           # 0,2 s fra la seconda e la terza frase: restano unite
    (a1, b1), (a2, b2) = regions
    assert a1 == pytest.approx(0.5 - PRE_ROLL, abs=0.011)
    assert b1 == pytest.approx(1.5 + TAIL, abs=0.011)
    assert a2 == pytest.approx(2.5 - PRE_ROLL, abs=0.011)
    assert b2 == pytest.approx(4.0 + TAIL, abs=0.011)


def test_threshold_and_minimum_silence_are_respected(tmp_path):
    _p, clip = _take(tmp_path, noise_db=-40.0)
    levels, total = clip_levels_db(clip)
    assert sound_regions(levels, total, threshold_db=-45.0) == [(0.0, total)]   # il fruscio supera la soglia
    assert len(sound_regions(levels, total, threshold_db=-30.0)) == 2
    assert len(sound_regions(levels, total, threshold_db=-30.0, min_silence=0.1)) == 3
    assert sound_regions(np.full(100, -90.0), 1.0) == []


def test_pieces_play_where_they_were(tmp_path):
    p, clip = _take(tmp_path)
    levels, total = clip_levels_db(clip)
    tempo_map = build_tempo_beat_map(p)
    before = mix_layers(np.zeros((0, 2), np.float32), RATE, build_audio_layers(p, p.tracks, tempo_map))
    pieces = remove_silences(p, clip, sound_regions(levels, total))
    assert len(pieces) == 2 and all(c.file == clip.file for c in pieces)
    assert pieces[0].start_beat == pytest.approx(4.0 + (0.5 - PRE_ROLL) * 2, abs=0.03)   # 120 BPM: 2 beat al secondo
    assert pieces[0].fade_in == EDGE_FADE and pieces[1].fade_out == EDGE_FADE
    p.get_track("Voce").audio_clips = pieces
    after = mix_layers(np.zeros((0, 2), np.float32), RATE, build_audio_layers(p, p.tracks, tempo_map))
    start = int(2.0 * RATE)                            # la clip comincia al beat 4 = 2 s
    middle = slice(start + int(0.7 * RATE), start + int(1.3 * RATE))
    assert np.allclose(after[middle], before[middle], atol=1e-4)
    gap = slice(start + int(1.7 * RATE), start + int(2.3 * RATE))
    assert np.abs(after[gap]).max() == 0.0             # il fruscio nel silenzio non c'e' piu'


def test_nothing_to_remove_keeps_the_clip(tmp_path):
    p, clip = _take(tmp_path)
    assert remove_silences(p, clip, [(0.0, LENGTH)]) == [clip]
    assert remove_silences(p, clip, []) == [clip]
