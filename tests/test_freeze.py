"""
Test di Congela in audio (core.freeze): la traccia congelata suona come dal
vivo (entro -60 dB), resta nel brano silenziata, si salva e si riapre, e
Scongela la riporta com'era; senza scheda audio (tracce audio con effetti:
non serve il SoundFont).

Esecuzione:
    python3 -m pytest tests/test_freeze.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)

import numpy as np
import pytest

from core import freeze
from core.audio_tracks import AUDIO_SAMPLE_RATE as RATE, write_wav
from core.model import AudioClip, Effect, Project
from core.playback import render_project_mix
from core.project_io import parse_project_text, project_to_text


def _project(tmp_path):
    t = np.arange(2 * RATE) / RATE
    path = str(tmp_path / "chitarra.wav")
    write_wav(path, (0.3 * np.sin(2 * np.pi * 196 * t)).reshape(-1, 1).astype(np.float32), RATE)
    p = Project(tempo_bpm=120)
    gtr = p.add_audio_track("Chitarra")
    gtr.audio_clips.append(AudioClip("Riff", path, 2.0))
    gtr.volume, gtr.pan = 80, 30
    gtr.effects = [Effect("volume", {"guadagno": -3.0}), Effect("passa_basso", {})]
    p.add_audio_track("Voce")
    return p, gtr


def _db(x):
    return 20 * np.log10(max(1e-12, float(np.sqrt(np.mean(np.square(x, dtype=np.float64))))))


def test_frozen_track_sounds_like_the_live_one(tmp_path):
    p, gtr = _project(tmp_path)
    live, _ = render_project_mix(p)
    path = freeze.render_frozen_audio(p, gtr, str(tmp_path / "audio"))
    audio = freeze.apply_freeze(p, gtr, path)
    assert [t.name for t in p.tracks] == ["Chitarra", "Chitarra (congelata)", "Voce"]
    assert gtr.mute and gtr.frozen == audio.name and freeze.is_frozen(p, gtr)
    assert (audio.volume, audio.pan, audio.effects) == (100, 64, [])
    frozen, _ = render_project_mix(p)
    n = max(len(live), len(frozen))
    pad = lambda x: np.concatenate([x, np.zeros((n - len(x), 2), np.float32)])   # noqa: E731
    assert _db(pad(frozen) - pad(live)) - _db(live) < -60


def test_freeze_survives_saving_and_unfreeze_restores(tmp_path):
    p, gtr = _project(tmp_path)
    audio = freeze.apply_freeze(p, gtr, freeze.render_frozen_audio(p, gtr, str(tmp_path / "audio")))
    text = project_to_text(p, str(tmp_path))
    assert 'congelata: "Chitarra (congelata)"' in text
    back = parse_project_text(text, base_dir=str(tmp_path))
    gtr2 = back.get_track("Chitarra")
    assert gtr2.frozen == audio.name and gtr2.mute and freeze.is_frozen(back, gtr2)
    assert project_to_text(back, str(tmp_path)) == text

    assert freeze.unfreeze(back, gtr2) == audio.name
    assert back.find_track(audio.name) is None and not gtr2.mute and gtr2.frozen == ""
    assert "congelata" not in project_to_text(back, str(tmp_path))


def test_renaming_or_removing_the_frozen_audio_track(tmp_path):
    p, gtr = _project(tmp_path)
    audio = freeze.apply_freeze(p, gtr, freeze.render_frozen_audio(p, gtr, str(tmp_path / "audio")))
    p.update_track(audio.name, "Chitarra stampata", audio.instrument_name)
    assert gtr.frozen == "Chitarra stampata"
    p.remove_track("Chitarra stampata")
    assert gtr.frozen == "" and not gtr.mute


def test_nothing_to_freeze(tmp_path):
    p = Project(tempo_bpm=120)
    empty = p.add_audio_track("Vuota")
    with pytest.raises(RuntimeError):
        freeze.render_frozen_audio(p, empty, str(tmp_path))
