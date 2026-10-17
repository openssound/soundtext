"""
Test delle ottimizzazioni dell'avvio della riproduzione con i plugin:
precaricamento dei plugin del brano (core.effect_render.warm_plugins),
rendering in parallelo delle tracce con plugin (render_stems, piu'
processi di rendering in core.plugins), niente caricamento doppio dello
strumento plugin e mix in memoria (core.audio_tracks.float_to_int16).

Esecuzione:
    python3 -m pytest tests/test_plugin_playback_speed.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from core import effect_render, plugins
from core.audio_tracks import float_to_int16, write_wav
from core.audio_stream import load_wav_samples
from core.effect_render import StemRequest, plugin_uses, render_stems
from core.lv2_host import lv2_available, lv2_plugin_info
from core.model import Effect, Project
from core.plugin_worker import parse_ref

A_DELAY = "lv2:urn:ardour:a-delay"
needs_delay = pytest.mark.skipif(not (lv2_available() and lv2_plugin_info(parse_ref(A_DELAY)[1])),
                                 reason="plugin LV2 ACE Delay non installato")


@pytest.fixture(autouse=True, scope="module")
def _stop_hosts():
    yield
    plugins.shutdown()


def _project():
    project = Project()
    drums = project.add_track("Batteria", "Piano", "4: c d e f")
    drums.synth = "lv2:urn:esempio:batteria"
    project.add_track("Vuota", "Piano", "").synth = "lv2:urn:esempio:mai-usato"
    bass = project.add_track("Basso", "Piano", "4: c d e f")
    bass.effects = [Effect("plugin", {"mix": 100}, plugin=A_DELAY, plugin_params={"time": 200.0}),
                    Effect("plugin", {"mix": 100}, enabled=False, plugin="lv2:urn:esempio:spento"),
                    Effect("riverbero", {})]
    piano = project.add_track("Piano", "Piano", "4: c d e f")
    piano.effects = [Effect("plugin", {"mix": 100}, plugin=A_DELAY, plugin_params={"time": 200.0})]
    project.master_effects = [Effect("plugin", {"mix": 100}, plugin="lv2:urn:esempio:master")]
    return project


def test_plugin_uses_lists_each_configured_plugin_once():
    refs = [ref for ref, _params, _state in plugin_uses(_project())]
    if effect_render.effects_available():
        assert refs == ["lv2:urn:esempio:batteria", A_DELAY, "lv2:urn:esempio:master"]
    else:
        assert refs == ["lv2:urn:esempio:batteria"]


def test_warm_plugins_does_nothing_without_plugins():
    assert effect_render.warm_plugins(Project()) is None


def test_warm_plugins_survives_a_plugin_that_does_not_load(monkeypatch):
    called = []

    def fake_warm(ref, params, state, rate):
        called.append(ref)
        raise plugins.PluginError("non si carica")

    monkeypatch.setattr(plugins, "warm", fake_warm)
    thread = effect_render.warm_plugins(_project())
    thread.join(10)
    assert not thread.is_alive()
    assert called[0] == "lv2:urn:esempio:batteria" and len(called) == len(plugin_uses(_project()))


def test_each_plugin_always_goes_to_the_same_render_host():
    for ref in ("lv2:urn:a", "vst3:/x/Synth.vst3", "sfz:/y/piano.sfz"):
        channel = plugins.render_channel(ref)
        assert channel == plugins.render_channel(ref)
        assert channel in plugins._hosts


def test_render_stems_runs_tracks_in_parallel_and_keeps_their_order(monkeypatch):
    running, peak, lock = [0], [0], threading.Lock()

    def slow_render(request, stop_check=None):
        with lock:
            running[0] += 1
            peak[0] = max(peak[0], running[0])
        time.sleep(0.2)
        with lock:
            running[0] -= 1
        return np.full((10, 2), float(request.track_name), dtype=np.float32)

    monkeypatch.setattr(effect_render, "render_stem", slow_render)
    requests = [StemRequest(str(i), f"k{i}", []) for i in range(4)]
    out = render_stems(requests)
    assert [float(x[0, 0]) for x in out] == [0.0, 1.0, 2.0, 3.0]
    assert peak[0] > 1


def test_synth_track_is_not_loaded_twice(monkeypatch, tmp_path):
    """render_synth non chiede piu' la descrizione del plugin (che lo
    caricava una seconda volta, nel processo dell'interfaccia)."""
    monkeypatch.setattr(plugins, "describe", lambda ref: pytest.fail("describe() non serve al rendering"))
    monkeypatch.setattr(plugins, "midi_file_events", lambda path: ([(0.0, bytes([0x90, 60, 100]))], 1.0))
    monkeypatch.setattr(plugins, "render_events",
                        lambda *a, **k: np.full((48000 * 5, 2), 0.1, dtype=np.float32))
    request = StemRequest("T", "k", [], midi_path=str(tmp_path / "x.mid"), synth="lv2:urn:esempio:batteria")
    y = effect_render.render_synth(request)
    assert y is not None and len(y) == 48000 * 5


def test_synth_that_fails_falls_back_to_none(monkeypatch, tmp_path):
    monkeypatch.setattr(plugins, "midi_file_events", lambda path: ([], 1.0))

    def broken(*a, **k):
        raise plugins.PluginError("il plugin non risponde")

    monkeypatch.setattr(plugins, "render_events", broken)
    request = StemRequest("T", "k", [], midi_path=str(tmp_path / "x.mid"), synth="lv2:urn:esempio:batteria")
    assert effect_render.render_synth(request) is None


def test_float_to_int16_matches_the_16_bit_wav(tmp_path):
    x = np.random.default_rng(1).uniform(-1.3, 1.3, size=(5000, 2)).astype(np.float32)
    path = str(tmp_path / "x.wav")
    write_wav(path, x, 48000, bits=16)
    from_disk, _rate = load_wav_samples(path)
    assert np.array_equal(float_to_int16(x), from_disk)


@needs_delay
def test_warm_loads_the_plugin_in_its_render_host():
    plugins.warm(A_DELAY, {}, "", 48000)
    x = np.zeros((4800, 2), dtype=np.float32)
    x[0] = 0.5
    y = plugins.process_audio(A_DELAY, {}, "", x, 48000)
    assert y.shape == x.shape and np.isfinite(y).all()


# ------------------------------------------------------------------ pre-rendering

def test_same_track_requested_twice_is_rendered_once(monkeypatch):
    calls = []

    def slow_synth(request, stop_check=None):
        calls.append(request.track_name)
        time.sleep(0.3)
        return np.zeros((100, 2), dtype=np.float32)

    monkeypatch.setattr(effect_render, "render_synth", slow_synth)
    effect_render.clear_stem_cache()
    request = StemRequest("Synth", "chiave-unica-test", [], synth="lv2:urn:esempio:batteria")
    results = []
    threads = [threading.Thread(target=lambda: results.append(effect_render.render_stem(request)))
               for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(5)
    assert calls == ["Synth"]
    assert len(results) == 2 and all(r is not None for r in results)


def _synth_project():
    project = Project()
    project.add_track("Synth", "Piano", "4: c d e f").synth = "lv2:urn:esempio:batteria"
    project.add_track("Piano", "Piano", "4: c d e f")
    return project


def test_prerender_fills_the_cache_with_the_keys_play_uses(monkeypatch):
    rendered = []

    def fake_synth(request, stop_check=None):
        rendered.append(request.dry_key)
        return np.zeros((100, 2), dtype=np.float32)

    monkeypatch.setattr(effect_render, "render_synth", fake_synth)
    effect_render.clear_stem_cache()
    project = _synth_project()
    effect_render.prerender_stems(project).join(10)
    assert len(rendered) == 1

    from core.tempo_map import build_tempo_beat_map
    tracks = project.audible_tracks()
    request = effect_render.prepare_stem(project, tracks[0], build_tempo_beat_map(project, tracks=tracks))
    try:
        assert effect_render._cache_get(request.wet_key) is not None
    finally:
        request.cleanup()


def test_prerender_is_cancelled_by_a_newer_one(monkeypatch):
    started, release = threading.Event(), threading.Event()
    stopped = []

    def blocking_synth(request, stop_check=None):
        started.set()
        release.wait(5)
        if stop_check and stop_check():
            stopped.append(request.track_name)
            raise RuntimeError("annullato")
        return np.zeros((100, 2), dtype=np.float32)

    monkeypatch.setattr(effect_render, "render_synth", blocking_synth)
    effect_render.clear_stem_cache()
    project = _synth_project()
    first = effect_render.prerender_stems(project)
    assert started.wait(5)
    project.tracks[0].text = "4: g a b c"       # una modifica: il pre-rendering di prima non serve piu'
    monkeypatch.setattr(effect_render, "render_synth", lambda request, stop_check=None: None)
    second = effect_render.prerender_stems(project)
    release.set()
    first.join(5)
    second.join(5)
    assert stopped == ["Synth"]


def test_prerender_does_nothing_without_plugins_or_effects(monkeypatch):
    monkeypatch.setattr(effect_render, "render_stems", lambda *a, **k: pytest.fail("niente da renderizzare"))
    project = Project()
    project.add_track("Piano", "Piano", "4: c d e f")
    effect_render.prerender_stems(project).join(5)


def test_side_synth_follows_the_shared_one(monkeypatch):
    """Il secondo synth (tracce con effetti, esportazione) si usa solo se si
    usa la libreria FluidSynth: chi disattiva _shared_synth li spegne tutti e due."""
    from core import playback
    if playback._shared_synth is None:
        assert playback._side_synth() is None
        return
    assert playback._side_synth() is playback._stem_synth is not playback._shared_synth
    monkeypatch.setattr(playback, "_shared_synth", None)
    assert playback._side_synth() is None
