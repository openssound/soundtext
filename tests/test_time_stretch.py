"""
Test del time-stretch delle clip audio (AudioClip.stretch e source_bpm, vedi
core.audio_tracks) e dell'adattamento di una ripresa libera a un tempo fisso
(core.performance_tempo.warp_to_fixed_tempo), senza scheda audio.

Esecuzione:
    python3 -m pytest tests/test_time_stretch.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)

import numpy as np
import pytest

from core import audio_tracks as at
from core import performance_tempo as pt
from core.audio_tracks import AUDIO_SAMPLE_RATE as RATE, write_wav
from core.beat_track import analyze_beats
from core.model import AudioClip, Project
from core.project_io import parse_project_text, project_to_text
from core.tempo_map import build_tempo_beat_map
from test_beat_track import RATE as HIT_RATE, _accelerando, _hits

pedalboard = pytest.importorskip("pedalboard")
TEMPO = build_tempo_beat_map(Project(tempo_bpm=120))       # 1 beat = 0,5 s


def _sine(tmp_path, seconds=2.0, freq=440.0, name="s.wav"):
    t = np.arange(int(seconds * RATE)) / RATE
    path = str(tmp_path / name)
    write_wav(path, (0.5 * np.sin(2 * np.pi * freq * t)).reshape(-1, 1).astype(np.float32), RATE)
    return path


def _mix(project):
    tm = build_tempo_beat_map(project)
    return at.mix_layers(np.zeros((0, 2), np.float32), RATE, at.build_audio_layers(project, project.tracks, tm))[:, 0]


def _peak_hz(x):
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    return np.fft.rfftfreq(len(x), 1.0 / RATE)[int(np.argmax(spectrum))]


def test_stretch_changes_the_length_not_the_pitch(tmp_path):
    p = Project(tempo_bpm=120)
    clip = AudioClip("S", _sine(tmp_path), 0.0, stretch=1.5)
    p.add_audio_track("A").audio_clips.append(clip)
    assert at.clip_play_seconds(clip) == pytest.approx(3.0)
    assert at.clip_duration_beats(clip, TEMPO) == pytest.approx(6.0)
    mixed = _mix(p)
    assert len(mixed) == pytest.approx(3.0 * RATE, rel=0.01)
    assert _peak_hz(mixed[RATE // 2:RATE // 2 + RATE]) == pytest.approx(440.0, abs=2.0)


def test_trims_split_and_slip_work_in_song_time(tmp_path):
    clip = AudioClip("S", _sine(tmp_path, seconds=4.0), 0.0, stretch=2.0)          # 8 s = 16 beat
    at.trim_clip_end_to_beat(clip, 8.0, TEMPO)                                      # 4 s nel brano = 2 s di file
    assert clip.trim_end == pytest.approx(2.0)
    at.trim_clip_start_to_beat(clip, 2.0, TEMPO)                                    # +1 s nel brano = 0,5 s di file
    assert (clip.start_beat, clip.trim_start) == (pytest.approx(2.0), pytest.approx(0.5))
    second = at.split_clip(clip, 4.0, TEMPO)                                        # a 1 s dall'inizio
    assert second.trim_start == pytest.approx(1.0) and second.stretch == 2.0
    assert at.clip_play_seconds(clip) + at.clip_play_seconds(second) == pytest.approx(3.0)
    at.slip_clip_content(second, 1.0)                                               # 1 s nel brano = 0,5 s di file
    assert second.trim_start == pytest.approx(1.5)


def test_stretch_and_tempo_round_trip_and_defaults_are_not_written(tmp_path):
    path = _sine(tmp_path)
    p = Project(tempo_bpm=120)
    p.add_audio_track("A").audio_clips.append(AudioClip("S", path, 0.0))
    assert "stretch=" not in project_to_text(p, base_dir=str(tmp_path))
    clip = p.get_track("A").audio_clips[0]
    clip.stretch, clip.source_bpm = 1.25, 96.0
    text = project_to_text(p, base_dir=str(tmp_path))
    assert 'file="s.wav" stretch=1.25 bpm=96' in text
    back = parse_project_text(text, base_dir=str(tmp_path)).get_track("A").audio_clips[0]
    assert (back.stretch, back.source_bpm) == (1.25, 96.0)


def test_clips_following_the_tempo_adapt_when_it_changes(tmp_path):
    p = Project(tempo_bpm=100)
    follow = AudioClip("F", _sine(tmp_path), 0.0, source_bpm=120.0)
    fixed = AudioClip("X", _sine(tmp_path, name="x.wav"), 8.0)
    p.add_audio_track("A").audio_clips.extend([follow, fixed])
    assert at.adapt_clips_to_tempo(p) == [follow]
    assert follow.stretch == pytest.approx(1.2) and fixed.stretch == 1.0
    assert at.adapt_clips_to_tempo(p) == []                     # gia' a posto
    p.tempo_changes = [(1, 100), (3, 150)]
    follow.start_beat = 8.0
    at.adapt_clips_to_tempo(p)
    assert follow.stretch == pytest.approx(0.8)                 # il tempo dove comincia


def test_stretched_audio_is_cached(tmp_path):
    x = np.random.default_rng(0).standard_normal((RATE, 1)).astype(np.float32) * 0.1
    a = at.stretched(x, RATE, 1.3, key=("k", 1))
    assert at.stretched(x, RATE, 1.3, key=("k", 1)) is a
    assert len(a) == pytest.approx(1.3 * RATE, rel=0.01)


def test_free_take_warped_to_a_fixed_tempo(tmp_path):
    times = _accelerando(90, 110, 32)
    path = str(tmp_path / "acc.wav")
    write_wav(path, _hits(times, 2.0)[:, None], HIT_RATE)
    p = Project(tempo_bpm=100)
    clip = AudioClip("Ritmica", path, 0.0)
    p.add_audio_track("A").audio_clips.append(clip)
    analysis = pt.analyze_clip(p, clip)
    pieces = pt.warp_to_fixed_tempo(p, clip, analysis, 2, 100)
    assert p.tempo_changes == [] and p.tempo_bpm == 100
    assert len(pieces) == analysis.bars + 2                     # attacco, una per battuta, coda
    assert [c.start_beat for c in pieces[1:4]] == pytest.approx([3.99, 7.99, 11.99], abs=0.01)
    # la prima battuta (a ~92 BPM, lunga) si accorcia, l'ultima (~109 BPM) si allunga
    assert pieces[1].stretch < 0.95 and pieces[-2].stretch > 1.05
    p.get_track("A").audio_clips = pieces
    result = analyze_beats(_mix(p)[:, None], RATE)
    assert all(abs(b - 100) <= 0.3 for b in result.bar_tempos)
    assert result.first_beat == pytest.approx(2.4, abs=0.005)    # battuta 2 a 100 BPM
    assert max(abs(t - (2.4 + i * 0.6)) for i, t in enumerate(result.beats)) < 0.015


def test_a_clip_follows_a_tempo_that_changes_inside_it(tmp_path):
    from core.audio_slice import detect_attacks
    from core.tempo_map import seconds_for_beats
    clicks = np.zeros((8 * RATE, 1), np.float32)              # registrata a 120 BPM: un beat ogni 0,5 s
    n = np.arange(int(0.03 * RATE))
    for k in range(16):
        clicks[k * RATE // 2:k * RATE // 2 + len(n), 0] = 0.8 * np.sin(2 * np.pi * 1000 * n / RATE) * np.exp(-n / 300)
    path = str(tmp_path / "clicks.wav")
    write_wav(path, clicks, RATE)
    p = Project(tempo_bpm=120)
    p.tempo_changes = [(1, 120), (3, 60)]                     # dalla battuta 3 (beat 8) a 60 BPM
    clip = AudioClip("Click", path, 0.0, source_bpm=120.0)
    p.add_audio_track("A").audio_clips.append(clip)
    assert at.adapt_clips_to_tempo(p) == [clip]
    assert clip.stretch == pytest.approx(1.5)                  # 4 s a 120 + 8 s a 60 = 12 s
    tm = build_tempo_beat_map(p)
    assert at.clip_duration_beats(clip, tm) == pytest.approx(16.0)
    layer = at.build_audio_layers(p, p.tracks, tm)[0]
    assert layer.segments == ((0.0, 4.0, 1.0), (4.0, 8.0, 2.0))
    found = detect_attacks(_mix(p)[:, None], RATE)
    expected = [seconds_for_beats(tm, k) for k in range(16)]   # 0, 0.5 ... 3.5, poi 4, 5 ... 11
    assert len(found) >= 15
    for t in found:
        assert min(abs(t - e) for e in expected) < 0.012        # ogni click sul suo beat
    assert max(found) == pytest.approx(11.0, abs=0.012)


def test_a_constant_tempo_keeps_a_single_stretch(tmp_path):
    p = Project(tempo_bpm=100)
    clip = AudioClip("S", _sine(tmp_path), 0.0, source_bpm=120.0)
    p.add_audio_track("A").audio_clips.append(clip)
    at.adapt_clips_to_tempo(p)
    assert clip.stretch == pytest.approx(1.2)
    assert at.build_audio_layers(p, p.tracks, build_tempo_beat_map(p))[0].segments == ()
