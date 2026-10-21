"""
Test della cache dei rendering su disco (core.disk_cache): time-stretch e
tracce con effetti salvati accanto al progetto, riusati alla riapertura e
mai riusati dopo una modifica; senza scheda audio.

Esecuzione:
    python3 -m pytest tests/test_disk_cache.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)

import os

import numpy as np
import pytest

from core import audio_tracks as at
from core import disk_cache, effect_render
from core.audio_tracks import AUDIO_SAMPLE_RATE as RATE, write_wav
from core.model import AudioClip, Effect, Project
from core.tempo_map import build_tempo_beat_map


@pytest.fixture
def project_cache(tmp_path):
    disk_cache.set_project(str(tmp_path / "Brano.st"))
    yield tmp_path / "Brano_audio" / "cache"
    disk_cache.wait_writes()
    disk_cache.set_project(None)


def _forget_memory():
    with at._stretch_lock:
        at._stretch_cache.clear()
    effect_render.clear_stem_cache()


def _sine(tmp_path, seconds=3.0):
    t = np.arange(int(seconds * RATE)) / RATE
    path = str(tmp_path / "s.wav")
    write_wav(path, (0.4 * np.sin(2 * np.pi * 330 * t)).reshape(-1, 1).astype(np.float32), RATE)
    return path


def _mix(project):
    layers = at.build_audio_layers(project, project.tracks, build_tempo_beat_map(project))
    return at.mix_layers(np.zeros((0, 2), np.float32), RATE, layers)


def test_stretch_is_reused_after_reopening_and_invalidated_by_a_change(tmp_path, project_cache, monkeypatch):
    pytest.importorskip("pedalboard")
    p = Project(tempo_bpm=120)
    clip = AudioClip("S", _sine(tmp_path), stretch=1.25)
    p.add_audio_track("A").audio_clips.append(clip)
    first = _mix(p)
    assert disk_cache.wait_writes()
    assert len(list(project_cache.glob("*.npy"))) == 1

    _forget_memory()                                   # "riapertura": la memoria e' vuota
    calls = []
    import pedalboard

    def counting(*args, **kwargs):          # si ricalcolerebbe: lo si conta (poi il ripiego ricampiona)
        calls.append(1)
        raise RuntimeError("non doveva servire")
    monkeypatch.setattr(pedalboard, "time_stretch", counting)
    again = _mix(p)
    assert calls == [] and np.array_equal(first, again)

    clip.trim_start = 0.5                              # la clip cambia: si ricalcola
    _forget_memory()
    _mix(p)
    assert calls


def test_effect_stem_is_saved_and_reloaded(tmp_path, project_cache, monkeypatch):
    p = Project(tempo_bpm=120)
    track = p.add_audio_track("Chitarra")
    track.audio_clips.append(AudioClip("S", _sine(tmp_path)))
    track.effects = [Effect("volume", {"guadagno": -6.0})]
    tempo = build_tempo_beat_map(p)
    request = effect_render.prepare_stem(p, track, tempo)
    wet = effect_render.render_stem(request)
    assert wet is not None
    assert disk_cache.wait_writes()
    _forget_memory()
    monkeypatch.setattr(effect_render, "apply_effect_chain", lambda *a, **k: pytest.fail("ricalcolata"))
    again = effect_render.render_stem(effect_render.prepare_stem(p, track, tempo))
    assert np.array_equal(wet, again)
    # un'altra regolazione dell'effetto e' un'altra chiave
    track.effects[0].params["guadagno"] = -3.0
    assert effect_render.prepare_stem(p, track, tempo).wet_key != request.wet_key


def test_no_project_no_disk_cache(tmp_path):
    disk_cache.set_project(None)
    disk_cache.store("x", np.zeros((RATE, 2), np.float32), wait=True)
    assert disk_cache.load("x") is None


def test_prune_removes_the_least_recently_used(tmp_path, project_cache):
    for i, key in enumerate(("vecchio", "medio", "nuovo")):
        disk_cache.store(key, np.full((RATE, 2), i, np.float32), wait=True)
        path = disk_cache._file_for(key, str(project_cache))
        os.utime(path, (1000 + i, 1000 + i))
    size = os.path.getsize(disk_cache._file_for("nuovo", str(project_cache)))
    assert disk_cache.prune(max_bytes=2 * size) == 1
    assert disk_cache.load("vecchio") is None and disk_cache.load("nuovo") is not None
