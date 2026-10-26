"""
Il motore NAM veloce (core.nam_plugin): il segnale diviso in pezzi, uno per
processo dei plugin, ricomposto uguale al calcolo in un colpo solo; se il
plugin non risponde si torna alla rete in numpy.

Qui il plugin e' finto: ogni pezzo lo calcola core.nam (lo stesso motore del
confronto), cosi' si verifica la divisione in pezzi senza il plugin vero.

Esecuzione:
    python3 -m pytest tests/test_nam_plugin.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import nam, nam_plugin, plugins  # noqa: E402
from core.lv2_host import decode_state  # noqa: E402

PROFILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "profili_nam",
                       "Maxon OD808.nam")
needs_profile = pytest.mark.skipif(not os.path.exists(PROFILE), reason="profili NAM non scaricati")


@pytest.fixture
def fake_plugin(monkeypatch, tmp_path):
    """Plugin "installato" che calcola con core.nam; registra i canali usati."""
    bundle = tmp_path / nam_plugin.BUNDLE
    bundle.mkdir()
    (bundle / "manifest.ttl").write_text("")
    monkeypatch.setenv("LV2_PATH", str(tmp_path))
    monkeypatch.setattr(nam_plugin, "_disabled_reason", "")
    calls = []

    def process_audio_on(channel, ref, params, state, samples, rate):
        calls.append(channel)
        assert ref == nam_plugin.REF
        path = decode_state(state)[nam_plugin.MODEL_PROPERTY]
        y = nam.process(nam.load_nam(path), samples[:, 0])
        return np.stack([y, y], axis=1)

    monkeypatch.setattr(plugins, "process_audio_on", process_audio_on)
    return calls


def test_plugin_is_found_in_the_lv2_folders(fake_plugin, tmp_path):
    assert nam_plugin.bundle_path() == str(tmp_path / nam_plugin.BUNDLE)
    assert nam_plugin.available()


@needs_profile
def test_segments_join_into_the_same_result(fake_plugin, monkeypatch):
    monkeypatch.setattr(plugins, "NAM_HOSTS", 4)
    model = nam.load_nam(PROFILE)
    x = (0.1 * np.random.default_rng(0).standard_normal(48000 * 20)).astype(np.float32)
    y = nam_plugin.process(PROFILE, x, 48000, model.receptive_field)
    assert sorted(set(fake_plugin)) == ["nam0", "nam1", "nam2", "nam3"]      # quattro pezzi, in parallelo
    assert np.allclose(y, nam.process(model, x), atol=1e-5)                 # e ricomposti uguali


@needs_profile
def test_short_signal_is_one_segment(fake_plugin):
    model = nam.load_nam(PROFILE)
    x = np.zeros(48000, dtype=np.float32)
    nam_plugin.process(PROFILE, x, 48000, model.receptive_field)
    assert fake_plugin == ["nam0"]


def test_without_the_plugin_numpy_does_the_work(monkeypatch, tmp_path):
    monkeypatch.setenv("LV2_PATH", str(tmp_path))                          # cartella vuota
    assert nam_plugin.process("x.nam", np.zeros(48000, np.float32), 48000, 100) is None


def test_a_failing_plugin_is_not_retried(fake_plugin, monkeypatch):
    def broken(*_a, **_k):
        raise plugins.PluginError("si e' chiuso")
    monkeypatch.setattr(plugins, "process_audio_on", broken)
    x = np.zeros(48000, dtype=np.float32)
    assert nam_plugin.process("x.nam", x, 48000, 100) is None
    assert not nam_plugin.available()                                       # per questa sessione: numpy


@needs_profile
def test_the_plugin_normalization_is_taken_back(fake_plugin, monkeypatch):
    """Il plugin porta a -18 dB i profili che dichiarano la loudness; la
    normalizzazione la fa gia' core.effects, quindi process() la toglie."""
    model = nam.load_nam(PROFILE)
    gain = 10.0 ** ((nam_plugin.PLUGIN_TARGET_LOUDNESS_DB - (-12.0)) / 20.0)

    def normalizing(channel, ref, params, state, samples, rate):
        y = gain * nam.process(model, samples[:, 0])
        return np.stack([y, y], axis=1)
    monkeypatch.setattr(plugins, "process_audio_on", normalizing)
    x = (0.1 * np.random.default_rng(1).standard_normal(48000)).astype(np.float32)
    y = nam_plugin.process(PROFILE, x, 48000, model.receptive_field, loudness=-12.0)
    assert np.allclose(y, nam.process(model, x), atol=1e-5)
