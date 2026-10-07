"""
Test della traduzione del livello "Latenza tasti" (Bassa/Media/Alta) in
impostazioni del buffer del synth in tempo reale (core.playback).

Regressione coperta: su Windows (WASAPI condiviso) il livello veniva
applicato come audio.period-size, che quel driver ignora - Bassa, Media e
Alta davano tutte lo stesso ritardo di ~40ms.
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.playback import _live_buffer_settings, _live_buffer_ms
from core.settings import LIVE_PERIOD_SIZE_CHOICES


def test_wasapi_levels_change_number_of_periods():
    periods = [_live_buffer_settings("wasapi", lv)[1] for lv in LIVE_PERIOD_SIZE_CHOICES]
    assert periods == [2, 3, 4]
    ms = [_live_buffer_ms("wasapi", *_live_buffer_settings("wasapi", lv)) for lv in LIVE_PERIOD_SIZE_CHOICES]
    assert ms == sorted(ms) and ms[0] < ms[-1]


def test_other_drivers_keep_four_periods_and_scale_period_size():
    for driver in ("pulseaudio", "dsound", "alsa", None):
        for lv in LIVE_PERIOD_SIZE_CHOICES:
            assert _live_buffer_settings(driver, lv) == (lv, 4)
    assert _live_buffer_ms("dsound", 256, 4) == 21
    assert _live_buffer_ms("pulseaudio", 1024, 4) == 85
