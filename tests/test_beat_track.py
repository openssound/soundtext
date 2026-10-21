"""
Test del beat tracking (core.beat_track) e della mappa del tempo ricavata da
una ripresa (core.performance_tempo), su riprese sintetiche: colpi
alternati grave/acuto, il primo di ogni battuta piu' forte.

Esecuzione:
    python3 -m pytest tests/test_beat_track.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)

import numpy as np
import pytest

from core import performance_tempo as pt
from core.audio_tracks import write_wav
from core.beat_track import analyze_beats, bar_tempos, meter_beats, tempo_changes_for
from core.model import AudioClip, Project
from core.tempo_map import beat_at_elapsed_seconds, build_tempo_beat_map, seconds_for_beats

RATE = 48000


def _hits(times, tail=1.5):
    x = np.zeros(int((times[-1] + tail) * RATE), np.float32)
    n = np.arange(int(0.08 * RATE))
    for i, t in enumerate(times):
        tone = 180 if i % 2 == 0 else 900
        hit = ((1.0 if i % 4 == 0 else 0.6) * np.sin(2 * np.pi * tone * n / RATE)
               * np.exp(-n / (0.015 * RATE))).astype(np.float32)
        s = int(t * RATE)
        x[s:s + len(hit)] += hit[:max(0, len(x) - s)]
    return x


def _accelerando(start_bpm, end_bpm, beats, first=1.0):
    times = [first]
    for k in range(1, beats + 1):
        times.append(times[-1] + 60.0 / (start_bpm + (end_bpm - start_bpm) * k / beats))
    return times


def test_steady_take_gives_one_tempo():
    times = [0.5 + i * 0.6 for i in range(49)]               # 100 BPM, 12 battute
    a = analyze_beats(_hits(times), RATE)
    assert a.bar_tempos == [100] * 12
    assert a.first_beat == pytest.approx(0.5, abs=0.002)
    assert a.mean_bpm == pytest.approx(100.0, abs=0.2)


def test_accelerating_take_is_followed_bar_by_bar():
    times = _accelerando(90, 110, 64)
    a = analyze_beats(_hits(times), RATE)
    assert len(a.beats) == len(times)
    assert max(abs(b - t) for b, t in zip(a.beats, times)) < 0.005
    expected = [60.0 * 4 / (times[4 * (k + 1)] - times[4 * k]) for k in range(16)]
    assert all(abs(got - want) <= 2 for got, want in zip(a.bar_tempos, expected))
    assert a.bar_tempos[0] <= 93 and a.bar_tempos[-1] >= 107


def test_decimal_tempos_do_not_drift():
    beats = [i * 60.0 / 101.43 for i in range(81)]          # 101,43 BPM: un decimale e la compensazione
    tempos = bar_tempos(beats, 4, 1.0)
    assert set(tempos) <= {101.4, 101.5}
    end = sum(60.0 * 4 / bpm for bpm in tempos)
    assert end == pytest.approx(beats[-1], abs=0.002)
    assert bar_tempos([i * 0.6 for i in range(9)], 4, 1.0) == [100, 100]   # un tempo intero resta intero
    assert all(isinstance(b, int) for b in bar_tempos([i * 0.6 for i in range(9)], 4, 1.0))


def test_meters():
    assert meter_beats("4/4") == (4, 1.0)
    assert meter_beats("3/4") == (3, 1.0)
    assert meter_beats("6/8") == (2, 1.5)
    assert meter_beats("12/8") == (4, 1.5)


def test_tempo_changes_replace_those_bars_and_restore_the_tempo_after():
    times = [0.5 + i * 0.6 for i in range(17)]
    a = analyze_beats(_hits(times), RATE)
    assert tempo_changes_for(a, 5, [(1, 120), (6, 90), (12, 140)], 90) == [(1, 120), (5, 100), (9, 90), (12, 140)]


def test_project_follows_the_take_and_the_clip_lands_on_the_bar(tmp_path):
    times = _accelerando(90, 110, 32)
    path = str(tmp_path / "acc.wav")
    write_wav(path, _hits(times, 2.0)[:, None], RATE)
    p = Project(tempo_bpm=120)
    clip = AudioClip("Chitarra", path, 6.0)
    p.add_audio_track("Chitarra").audio_clips.append(clip)
    a = pt.analyze_clip(p, clip)
    bar = pt.suggested_first_bar(p, clip, a)
    assert bar == 3
    assert pt.apply_performance_tempo(p, clip, a, bar) == 8
    assert p.tempo_bpm == 120 and p.tempo_changes[0] == (1, 120) and p.tempo_changes[-1] == (11, 120)
    tm = build_tempo_beat_map(p)
    start = seconds_for_beats(tm, clip.start_beat)
    where = [beat_at_elapsed_seconds(tm, 0.0, start + t) for t in a.beats]
    assert where[0] == pytest.approx(8.0, abs=0.01)                      # battuta 3 = beat 8
    assert max(abs(w - round(w)) for w in where) < 0.05                # ogni battito su un beat
    assert where[-1] == pytest.approx(40.0, abs=0.05)


def test_conversion_follows_the_tempo_map(tmp_path):
    from core.audio_track_notation import ConversionOptions, convert_audio_track
    from core.notation import parse_track_text
    times = _accelerando(90, 110, 32)
    path = str(tmp_path / "acc.wav")
    write_wav(path, _hits(times, 2.0)[:, None], RATE)
    p = Project(tempo_bpm=120)
    clip = AudioClip("Batteria", path, 0.0)
    p.add_audio_track("Batteria").audio_clips.append(clip)
    a = pt.analyze_clip(p, clip)
    pt.apply_performance_tempo(p, clip, a, 2)
    boxes, _silent = convert_audio_track(p, p.get_track("Batteria"), ConversionOptions(mode="drums", grid_denominator=4), 4)
    starts = [e.start for e in parse_track_text(boxes[0].text, {}) if e.kind in ("percussion", "block")]
    offset = 4.0 - clip.start_beat                                     # il primo battito e' a battuta 2
    assert starts[:8] == pytest.approx([offset + k for k in range(8)], abs=0.01)


def test_decimal_tempos_are_saved_and_the_file_declares_2_9_only_when_needed():
    from core.project_io import parse_project_text, project_to_text
    p = Project(tempo_bpm=120)
    p.add_track("Piano", "Piano", "4: c d e f")
    assert project_to_text(p).startswith("ST: 2.8\n")                  # tempi interi: leggibile dalla 2.8
    p.tempo_changes = [(1, 120), (3, 96.5), (5, 101.4)]
    text = project_to_text(p)
    assert text.startswith("ST: 2.9\n") and "Tempo: 1: 120, 3: 96.5, 5: 101.4" in text
    back = parse_project_text(text)
    assert back.tempo_changes == [(1, 120), (3, 96.5), (5, 101.4)] and isinstance(back.tempo_bpm, int)
    single = Project(tempo_bpm=101.4)
    assert "Tempo: 101.4 BPM" in project_to_text(single) and parse_project_text(project_to_text(single)).tempo_bpm == 101.4


def test_tempo_from_the_take_writes_decimals(tmp_path):
    times = [1.0 + i * 60.0 / 101.43 for i in range(33)]
    path = str(tmp_path / "steady.wav")
    write_wav(path, _hits(times, 2.0)[:, None], RATE)
    p = Project(tempo_bpm=120)
    clip = AudioClip("Ritmica", path, 0.0)
    p.add_audio_track("Ritmica").audio_clips.append(clip)
    a = pt.analyze_clip(p, clip)
    pt.apply_performance_tempo(p, clip, a, 2)
    assert {v for b, v in p.tempo_changes if 2 <= b < 10} <= {101.4, 101.5}
