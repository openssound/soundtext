"""
Test delle riprese multiple e del comping (core.audio_takes) e della
registrazione in loop e in punch-in (core.audio_recording), senza scheda
audio: file sintetici a valore costante, cosi' dal mix si vede quale
ripresa suona in ogni punto.

Esecuzione:
    python3 -m pytest tests/test_audio_takes.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)

import os
from types import SimpleNamespace

import numpy as np
import pytest

from core import audio_recording as rec
from core import audio_takes as at
from core.audio_tracks import (
    AUDIO_SAMPLE_RATE as RATE, build_audio_layers, clip_play_seconds, consolidate_project_audio, mix_layers,
    write_wav,
)
from core.model import AudioClip, AudioTake, Project
from core.project_io import parse_project_text, project_to_text
from core.tempo_map import build_tempo_beat_map

TEMPO = build_tempo_beat_map(Project(tempo_bpm=120))       # 1 beat = 0,5 s


def _const(tmp_path, name, value, seconds=10.0):
    path = str(tmp_path / name)
    write_wav(path, np.full((int(seconds * RATE), 1), value, np.float32), RATE)
    return path


def _three_takes(tmp_path):
    """Strofa a beat 0, 4 s (8 beat): tre riprese con conteggi un po' diversi."""
    clip = AudioClip("Ripresa 1", _const(tmp_path, "a.wav", 0.1), 0.0, trim_start=2.0, trim_end=4.0)
    at.add_take(clip, "Ripresa 2", _const(tmp_path, "b.wav", 0.2), 2.02)
    at.add_take(clip, "Ripresa 3", _const(tmp_path, "c.wav", 0.3), 1.98)
    return clip


def _mix(clips):
    p = Project(tempo_bpm=120)
    p.add_audio_track("Voce").audio_clips.extend(clips)
    return mix_layers(np.zeros((0, 2), np.float32), RATE, build_audio_layers(p, p.tracks, TEMPO))[:, 0]


def test_new_takes_become_active_and_keep_the_clip_in_place(tmp_path):
    clip = _three_takes(tmp_path)
    assert [t.name for t in clip.takes] == ["Ripresa 1", "Ripresa 2", "Ripresa 3"] and clip.active_take == 2
    assert os.path.basename(clip.file) == "c.wav" and clip.trim_start == pytest.approx(1.98)
    assert clip_play_seconds(clip) == pytest.approx(4.0)
    assert [t.delta for t in clip.takes] == pytest.approx([0.02, 0.04, 0.0])
    at.set_active_take(clip, 0)
    assert os.path.basename(clip.file) == "a.wav" and clip.trim_start == pytest.approx(2.0)
    assert clip.start_beat == 0.0 and clip_play_seconds(clip) == pytest.approx(4.0)
    assert clip.takes[0].delta == 0.0
    assert np.allclose(_mix([clip])[1000:-1000], 0.1, atol=1e-4)


def test_takes_follow_trimming_and_copies_do_not_share_them(tmp_path):
    clip = _three_takes(tmp_path)
    copy = AudioClip(**{f: getattr(clip, f) for f in clip.__dataclass_fields__})
    clip.trim_start += 1.0                      # taglio dell'inizio: i delta restano validi
    at.set_active_take(clip, 1)
    assert clip.trim_start == pytest.approx(3.02)
    assert copy.active_take == 2 and os.path.basename(copy.file) == "c.wav"


def test_takes_round_trip_in_the_st_file(tmp_path):
    clip = _three_takes(tmp_path)
    clip.takes = clip.takes[:2] + [AudioTake('Prova "mute" 3', clip.takes[2].file, clip.takes[2].delta)]
    p = Project(tempo_bpm=120)
    p.add_audio_track("Voce").audio_clips.append(clip)
    text = project_to_text(p, base_dir=str(tmp_path))
    assert 'file="c.wav" trim=1.98,4.02 take=3\n  take "Ripresa 1" file="a.wav" delta=0.02' in text
    back = parse_project_text(text, base_dir=str(tmp_path)).get_track("Voce").audio_clips[0]
    assert back.active_take == 2 and not back.muted          # "mute" nel nome di una ripresa non conta
    assert [(t.name, os.path.basename(t.file), t.delta) for t in back.takes] == \
        [("Ripresa 1", "a.wav", 0.02), ("Ripresa 2", "b.wav", 0.04), ("Prova 'mute' 3", "c.wav", 0.0)]
    # la riga principale da sola (una versione vecchia) e' la ripresa attiva
    old = parse_project_text(text.split("\n  take ")[0] + "\n", base_dir=str(tmp_path))
    single = old.get_track("Voce").audio_clips[0]
    assert os.path.basename(single.file) == "c.wav" and single.takes == []


def test_saving_copies_the_files_of_every_take(tmp_path):
    staging = tmp_path / "staging"
    staging.mkdir()
    clip = _three_takes(staging)
    p = Project(tempo_bpm=120)
    p.add_audio_track("Voce").audio_clips.append(clip)
    assert consolidate_project_audio(p, str(tmp_path / "brano.st")) == 3
    audio_dir = str(tmp_path / "brano_audio")
    assert all(os.path.dirname(f) == audio_dir for f in at.all_files(clip))
    assert clip.file == clip.takes[clip.active_take].file


def test_comping_splits_the_clip_with_crossfades(tmp_path):
    clip = _three_takes(tmp_path)
    segments = at.assign_range([(0.0, 8.0, 2)], 0.0, 3.0, 0)
    segments = at.assign_range(segments, 3.0, 5.0, 1)
    assert segments == [(0.0, 3.0, 0), (3.0, 5.0, 1), (5.0, 8.0, 2)]
    parts = at.comp_clip(clip, segments, TEMPO)
    assert [os.path.basename(c.file) for c in parts] == ["a.wav", "b.wav", "c.wav"]
    assert [c.start_beat for c in parts] == pytest.approx([0.0, 2.99, 4.99])
    assert [(c.fade_in, c.fade_out) for c in parts] == [(0.0, 0.01), (0.01, 0.01), (0.01, 0.0)]
    assert all(len(c.takes) == 3 for c in parts)               # il comping si puo' rifare
    mixed = _mix(parts)
    for second, value in ((0.5, 0.1), (2.0, 0.2), (3.5, 0.3)):
        assert mixed[int(second * RATE)] == pytest.approx(value, abs=1e-4)
    # nei punti di cambio niente buco: le due riprese si incrociano
    for second in (1.5, 2.5):
        around = mixed[int((second - 0.01) * RATE):int((second + 0.01) * RATE)]
        assert around.min() > 0.09


def test_assign_range_merges_and_clamps():
    segments = [(0.0, 8.0, 0)]
    assert at.assign_range(segments, 6.0, 2.0, 1) == [(0.0, 2.0, 0), (2.0, 6.0, 1), (6.0, 8.0, 0)]
    assert at.assign_range([(0.0, 2.0, 0), (2.0, 8.0, 1)], 0.0, 2.0, 1) == [(0.0, 8.0, 1)]
    assert at.assign_range(segments, -4.0, 1.0, 2) == [(0.0, 1.0, 2), (1.0, 8.0, 0)]


def test_punch_in_recording_becomes_a_take_of_that_stretch(tmp_path):
    old = AudioClip("Strofa", _const(tmp_path, "old.wav", 0.1), 0.0, trim_start=2.0)      # 8 s = 16 beat
    clips = [old]
    new = AudioClip("Punch", _const(tmp_path, "new.wav", 0.3, 12.0), 4.0, trim_start=5.0, trim_end=5.0,
                    fade_in=0.01, fade_out=0.01)                                            # beat 4-8
    target = at.add_recording_as_take(clips, new, TEMPO)
    clips.sort(key=lambda c: c.start_beat)
    assert [c.start_beat for c in clips] == [0.0, 4.0, 8.0] and target is clips[1]
    assert [t.name for t in target.takes] == ["Strofa (2)", "Punch"] and target.active_take == 1
    assert (target.fade_in, target.fade_out) == (0.01, 0.01)
    mixed = _mix(clips)
    assert mixed[int(1.0 * RATE)] == pytest.approx(0.1, abs=1e-4)
    assert mixed[int(3.0 * RATE)] == pytest.approx(0.3, abs=1e-4)
    assert mixed[int(5.0 * RATE)] == pytest.approx(0.1, abs=1e-4)
    at.set_active_take(target, 0)                                # il tratto originale e' ancora li'
    assert _mix(clips)[int(3.0 * RATE)] == pytest.approx(0.1, abs=1e-4)
    far = AudioClip("Altrove", new.file, 40.0, trim_start=5.0, trim_end=5.0)
    assert at.add_recording_as_take(clips, far, TEMPO) is None


class _Stream:
    def start(self):
        pass

    def stop(self):
        pass

    def close(self):
        pass


def _run(recorder, seconds, value=0.25, block=480):
    outs = []
    recorder.start()
    for _ in range(int(seconds * RATE / block)):
        out = np.zeros((block, 2), np.float32)
        recorder._duplex_callback(np.full((block, 1), value, np.float32), out, block,
                                  SimpleNamespace(outputBufferDacTime=0.0, inputBufferAdcTime=0.0), None)
        outs.append(out)
    return recorder.stop(), np.concatenate(outs)


def test_loop_backing_repeats_a_to_b_and_each_pass_is_a_take(tmp_path):
    p = Project(tempo_bpm=120)
    backing = rec.build_backing(p, 4.0, count_in_bars=1, with_metronome=True, end_beat=8.0, loop=True)
    assert backing.loop and backing.loop_seconds == pytest.approx(2.0) and backing.count_in_seconds == 2.0
    recorder = rec.DuplexRecorder(backing, None, [0], stream_factory=lambda *a: _Stream())
    take, out = _run(recorder, 7.1)
    hits = np.flatnonzero((np.abs(out[1:, 0]) > 0.05) & (np.abs(out[:-1, 0]) <= 0.05)) / RATE
    starts = hits[np.r_[True, np.diff(hits) > 0.2]]
    assert starts == pytest.approx(np.arange(15) * 0.5, abs=0.002)    # conteggio, poi un click per beat a ogni giro
    assert rec.loop_pass_count(take, backing, 0.0) == 2
    path = rec.save_take(take, str(tmp_path), "loop")
    clip = rec.loop_clip("Ripresa 1", path, 4.0, take, backing, 0.0)
    assert [t.name for t in clip.takes] == ["Giro 1", "Giro 2"] and clip.active_take == 1
    assert clip.start_beat == 4.0 and clip_play_seconds(clip) == pytest.approx(2.0)
    assert clip.trim_start == pytest.approx(4.0)
    assert rec.take_preview(take, backing, 0.0, with_backing=False).shape[0] == 2 * RATE


def test_stop_during_the_first_pass_gives_no_take(tmp_path):
    backing = rec.build_backing(Project(tempo_bpm=120), 0.0, count_in_bars=0, with_metronome=False,
                                end_beat=8.0, loop=True)
    take, _out = _run(rec.DuplexRecorder(backing, None, [0], stream_factory=lambda *a: _Stream()), 2.0)
    assert rec.loop_pass_count(take, backing, 0.0) == 0
    assert rec.loop_clip("Ripresa 1", "/x.wav", 0.0, take, backing, 0.0) is None


def test_punch_clip_keeps_only_a_to_b(tmp_path):
    backing = rec.build_backing(Project(tempo_bpm=120), 0.0, count_in_bars=1, with_metronome=False)
    take = rec.Take(np.full((12 * RATE, 1), 0.2, np.float32), RATE, 0.0, 0.2)
    clip = rec.punch_clip("P", "/p.wav", 0.0, 4.0, 8.0, take, backing, 0.0, TEMPO)
    assert clip.start_beat == 4.0 and clip.trim_start == pytest.approx(2.0 + 2.0)
    assert clip.trim_end == pytest.approx(12.0 - 4.0 - 2.0)
    assert (clip.fade_in, clip.fade_out) == (rec.PUNCH_FADE, rec.PUNCH_FADE)
    short = rec.Take(np.full((3 * RATE, 1), 0.2, np.float32), RATE, 0.0, 0.2)
    assert rec.punch_clip("P", "/p.wav", 0.0, 4.0, 8.0, short, backing, 0.0, TEMPO) is None


def test_a_longer_take_extends_the_clip_up_to_the_next_one(tmp_path):
    old = AudioClip("Strofa", _const(tmp_path, "old.wav", 0.1, 6.0), 0.0, trim_start=2.0)      # 4 s = beat 0-8
    after = AudioClip("Dopo", _const(tmp_path, "after.wav", 0.2, 3.0), 12.0)
    clips = [old, after]
    longer = AudioClip("Ripresa 2", _const(tmp_path, "long.wav", 0.3, 12.0), 0.0, trim_start=2.0)  # 10 s
    target = at.add_recording_as_take(clips, longer, TEMPO)
    assert target is old and target.active_take == 1
    assert clip_play_seconds(target) == pytest.approx(6.0)        # fino all'inizio di "Dopo" (beat 12)
    assert after.start_beat == 12.0
