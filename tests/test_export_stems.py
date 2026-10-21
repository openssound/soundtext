"""
Test di "Esporta tutte le tracce" (core.playback.render_stems_to_dir): un WAV
per traccia non silenziata, tutti dall'inizio del brano e lunghi uguale,
senza scheda audio (solo tracce audio: non serve il SoundFont).

Esecuzione:
    python3 -m pytest tests/test_export_stems.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)

import os

import numpy as np
import pytest

from core.audio_tracks import AUDIO_SAMPLE_RATE as RATE, read_wav, write_wav
from core.model import AudioClip, Project
from core.playback import render_stems_to_dir, stem_tracks


def _wav(tmp_path, name, seconds, value):
    path = str(tmp_path / name)
    write_wav(path, np.full((int(seconds * RATE), 1), value, np.float32), RATE)
    return path


def _project(tmp_path):
    p = Project(tempo_bpm=120)                                   # 1 beat = 0,5 s
    p.add_audio_track("Voce").audio_clips.append(AudioClip("V", _wav(tmp_path, "v.wav", 1.0, 0.25), 2.0))
    p.add_audio_track("Basso/DI").audio_clips.append(AudioClip("B", _wav(tmp_path, "b.wav", 3.0, 0.1), 0.0))
    muted = p.add_audio_track("Prova")
    muted.audio_clips.append(AudioClip("P", _wav(tmp_path, "p.wav", 1.0, 0.5), 0.0))
    muted.mute = True
    p.add_audio_track("Vuota")
    return p


def test_one_file_per_audible_track_aligned_and_same_length(tmp_path):
    p = _project(tmp_path)
    assert [t.name for t in stem_tracks(p)] == ["Voce", "Basso/DI"]
    seen = []
    paths = render_stems_to_dir(p, str(tmp_path / "out"), progress=lambda done, total: seen.append((done, total)))
    assert [os.path.basename(x) for x in paths] == ["01 Voce.wav", "02 Basso_DI.wav"]
    assert seen == [(1, 2), (2, 2)]
    voice, rate = read_wav(paths[0])
    bass, _ = read_wav(paths[1])
    assert rate == RATE and len(voice) == len(bass) >= 3 * RATE
    # la voce comincia al beat 2 (1 s), non all'inizio del file
    assert np.abs(voice[:int(0.9 * RATE)]).max() < 1e-4
    assert voice[int(1.5 * RATE), 0] == pytest.approx(0.25, abs=1e-3)
    assert np.abs(voice[int(2.1 * RATE):]).max() < 1e-4          # coda di silenzio
    assert bass[int(1.5 * RATE), 0] == pytest.approx(0.1, abs=1e-3)


def test_nothing_to_export_is_an_error(tmp_path):
    p = Project(tempo_bpm=120)
    p.add_audio_track("Vuota")
    with pytest.raises(RuntimeError):
        render_stems_to_dir(p, str(tmp_path / "out"))
