"""
Test di core.audio_track_notation (senza rete e senza scheda audio): una
traccia audio convertita tutta in una traccia di note, un box per clip, e
gli accordi di una traccia audio come sorgente per i generatori.

Esecuzione:
    python3 -m pytest tests/test_audio_track_notation.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)

import numpy as np
import pytest

from core import audio_track_notation as atn
from core.audio_tracks import import_audio_file, write_wav
from core.key_detect import detect_key_of_text
from core.model import AudioClip, Project
from core.rhythm_generate import extract_chords_from_track, project_has_chords
from test_audio_chords import RATE, _hz, _tone_mix

C, AM, F, G = (48, 64, 67), (45, 60, 64), (41, 60, 65), (43, 59, 62)


def _chord_wav(tmp_path, chords, name="giro.wav", seconds_per_chord=2.0):
    """Un accordo per battuta a 120 BPM (2 s), importato come le clip vere."""
    x = np.concatenate([_tone_mix([_hz(m) for m in chord], seconds_per_chord) for chord in chords])
    src = str(tmp_path / ("src_" + name))
    write_wav(src, x[:, None], RATE, bits=16)
    return import_audio_file(src, str(tmp_path / "audio"))


def _project(tmp_path):
    p = Project(tempo_bpm=120)
    p.add_track("Piano", "Piano", "4: c d e f")
    gtr = p.add_audio_track("Chitarra")
    gtr.audio_clips += [AudioClip("Strofa", _chord_wav(tmp_path, [C, AM, F, G]), 8.0),
                        AudioClip("Ritornello", _chord_wav(tmp_path, [F, G, C, C], "rit.wav"), 32.0),
                        AudioClip("Prova", _chord_wav(tmp_path, [G, G], "prova.wav"), 64.0, muted=True)]
    return p, gtr


def test_chords_of_an_audio_track_are_placed_at_their_clips(tmp_path):
    p, gtr = _project(tmp_path)
    spans = atn.extract_chords_from_audio_track(p, gtr)
    assert [(s.start_beat, s.duration_beats, s.root_pc, s.third) for s in spans] == [
        (8.0, 4.0, 0, 4), (12.0, 4.0, 9, 3), (16.0, 4.0, 5, 4), (20.0, 4.0, 7, 4),   # Strofa
        (32.0, 4.0, 5, 4), (36.0, 4.0, 7, 4), (40.0, 8.0, 0, 4),                     # Ritornello
    ]                                                                                # Prova: silenziata
    assert detect_key_of_text(atn.audio_track_chord_text(p, gtr), p.patterns) == "C"


def test_chord_analysis_is_cached_until_the_clip_changes(tmp_path, monkeypatch):
    p, gtr = _project(tmp_path)
    atn.extract_chords_from_audio_track(p, gtr)
    assert atn.AudioChordSource(p, gtr).is_ready()
    calls = []
    original = atn._convert_clip
    monkeypatch.setattr(atn, "_convert_clip", lambda *a, **k: calls.append(1) or original(*a, **k))
    atn.extract_chords_from_audio_track(p, gtr)
    assert calls == []
    gtr.audio_clips[0].trim_end = 2.0                    # tolta l'ultima battuta: si rianalizza
    assert not atn.chords_are_cached(p, gtr)
    spans = atn.extract_chords_from_audio_track(p, gtr)
    assert len(calls) == 1 and [s.start_beat for s in spans][:3] == [8.0, 12.0, 16.0]
    p.tempo_bpm = 100                                    # anche il tempo cambia i beat
    assert not atn.chords_are_cached(p, gtr)


def test_audio_tracks_count_as_chord_sources_only_on_request(tmp_path):
    p, gtr = _project(tmp_path)
    assert not project_has_chords(p)                     # la traccia di note non ha accordi
    assert project_has_chords(p, audio=True)
    assert not project_has_chords(p, audio=True, exclude_track_name="Chitarra")
    for clip in gtr.audio_clips:
        clip.muted = True
    assert not project_has_chords(p, audio=True)


def test_convert_track_makes_one_box_per_audible_clip(tmp_path):
    p, gtr = _project(tmp_path)
    silent = _chord_wav(tmp_path, [C], "muto.wav")
    write_wav(silent, np.zeros((RATE * 2, 1), np.float32), RATE, bits=16)
    gtr.audio_clips.append(AudioClip("Silenzio", silent, 48.0))
    progress = []
    boxes, skipped = atn.convert_audio_track(p, gtr, atn.ConversionOptions(mode="chords"), 4,
                                             progress_callback=progress.append)
    assert [(b.name, b.start_beat) for b in boxes] == [("Strofa", 8.0), ("Ritornello", 32.0)]
    assert skipped == ["Silenzio"]
    assert progress[-1] == 1.0 and progress == sorted(progress)
    chords = extract_chords_from_track(boxes[0].text, p.patterns)
    assert [c.root_pc for c in chords] == [0, 9, 5, 7]


def test_conversion_can_be_cancelled(tmp_path):
    from core.audio_import import ConversionCancelled
    p, gtr = _project(tmp_path)

    def cancel(_frac):
        raise ConversionCancelled()

    with pytest.raises(ConversionCancelled):
        atn.convert_audio_track(p, gtr, atn.ConversionOptions(mode="chords"), 4, progress_callback=cancel)


def test_generators_cover_the_audio_clips_too(tmp_path):
    from core.rhythm_generate import tracks_duration_beats
    p, gtr = _project(tmp_path)
    # fino alla fine della Prova (64 + 8): silenziata, ma resta nel brano e si puo' riattivare
    assert tracks_duration_beats(p) == pytest.approx(72.0)
    assert tracks_duration_beats(p, exclude_track_name="Chitarra") == pytest.approx(4.0)
