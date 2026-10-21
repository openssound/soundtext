"""
Test della riduzione del rumore di fondo (core.denoise, effetto "Riduzione
rumore" di core.effects), su segnali sintetici.

Esecuzione:
    python3 -m pytest tests/test_denoise.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)

import numpy as np
import pytest

from core.denoise import noise_profile, reduce_noise
from core.effects import apply_effect_chain
from core.model import Effect

RATE = 48000


def _db(x):
    return 20 * np.log10(np.sqrt(np.mean(np.square(x, dtype=np.float64))) + 1e-12)


def _noisy(seconds=6.0, silence_gap=False):
    rng = np.random.default_rng(1)
    t = np.arange(int(seconds * RATE)) / RATE
    noise = 0.01 * rng.normal(size=len(t))
    if silence_gap:
        noise[:RATE] = 0.0                                   # silenzio digitale fra due clip
    tone = np.where((t > 2) & (t < 5), 0.3 * np.sin(2 * np.pi * 440 * t), 0.0)
    x = (tone + noise).astype(np.float32)
    return np.column_stack([x, x]), tone


def test_noise_goes_down_and_the_sound_stays():
    x, tone = _noisy()
    y = reduce_noise(x, RATE, 18.0, 6.0)
    assert y.shape == x.shape
    assert _db(y[:RATE, 0]) < _db(x[:RATE, 0]) - 12               # fruscio: almeno 12 dB in meno
    assert _db(y[3 * RATE:4 * RATE, 0]) == pytest.approx(_db(x[3 * RATE:4 * RATE, 0]), abs=0.5)
    assert _db(y[3 * RATE:4 * RATE, 0] - tone[3 * RATE:4 * RATE]) < -45


def test_digital_silence_is_not_the_noise_profile():
    x, _tone = _noisy(silence_gap=True)
    profile = noise_profile(x[:, 0], RATE)
    assert profile is not None and profile.mean() > 1e-3          # imparato dal fruscio, non dagli zeri
    assert _db(reduce_noise(x, RATE)[RATE:2 * RATE, 0]) < _db(x[RATE:2 * RATE, 0]) - 8


def test_nothing_to_learn_leaves_the_track_alone():
    silent = np.zeros((3 * RATE, 2), np.float32)
    assert reduce_noise(silent, RATE) is silent


def test_effect_in_the_chain():
    pytest.importorskip("pedalboard")
    x, _tone = _noisy()
    y = apply_effect_chain(x, RATE, [Effect("riduzione_rumore", {"riduzione": 20, "soglia": 6})])
    assert _db(y[:RATE, 0]) < _db(x[:RATE, 0]) - 12
