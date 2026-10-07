"""
Analisi audio in numpy (core.audio_dsp), che ha preso il posto di aubio:
- YIN trova l'altezza giusta (entro pochi cent) dal basso al registro acuto
  e non scende di un'ottava sui suoni ricchi di armoniche;
- il rumore non ha altezza (confidenza bassa);
- gli attacchi cadono entro pochi millisecondi da quelli veri, anche nel
  registro del basso e a inizio file;
- il vibrato e la fine brusca di un suono (anche a fine file) non sono
  attacchi.
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from core.audio_dsp import detect_onsets, yin

R = 44100


def _hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def _tone(freq, dur, amp=0.5, harmonics=5, decay=3.0):
    t = np.arange(int(dur * R)) / R
    env = np.minimum(1, t / 0.005) * np.exp(-t * decay) * np.minimum(1, (dur - t) / 0.01)
    return (sum(amp / k * np.sin(2 * np.pi * freq * k * t) for k in range(1, harmonics + 1)) * env).astype(np.float32)


@pytest.mark.parametrize("midi,buf", [(28, 8192), (40, 4096), (57, 2048), (69, 2048), (84, 2048), (96, 2048)])
def test_yin_finds_the_pitch(midi, buf):
    centers, freqs, conf = yin(_tone(_hz(midi), 0.5), R, buf, buf // 4)
    good = freqs[conf > 0.8]
    assert len(good) > len(freqs) // 2
    cents = 1200 * np.log2(np.median(good) / _hz(midi))
    assert abs(cents) < 10


def test_yin_does_not_drop_an_octave_on_rich_tones():
    # fondamentale debole e armoniche forti (voce, ottoni): niente ottava sotto
    t = np.arange(int(0.5 * R)) / R
    f = _hz(60)
    x = (0.1 * np.sin(2 * np.pi * f * t) + sum(0.4 / k * np.sin(2 * np.pi * f * k * t) for k in range(2, 8)))
    _, freqs, conf = yin(x.astype(np.float32), R, 2048, 512)
    good = freqs[conf > 0.6]
    assert abs(1200 * np.log2(np.median(good) / f)) < 10


def test_noise_has_no_pitch():
    x = np.random.RandomState(0).randn(R // 2).astype(np.float32) * 0.3
    _, _, conf = yin(x, R, 2048, 512)
    assert np.median(conf) < 0.6


def test_onsets_on_a_bass_line_and_at_file_start():
    starts = [0.0, 0.5, 1.0, 1.25, 1.5]
    x = np.zeros(int(2.2 * R), np.float32)
    for s, m in zip(starts, [40, 43, 45, 45, 40]):
        y = _tone(_hz(m), 0.24)
        i = int(s * R)
        x[i:i + len(y)] += y
    found = [p / R for p in detect_onsets(x, R)]
    assert len(found) == len(starts), found
    for got, want in zip(found, starts):
        assert abs(got - want) < 0.02


def test_percussive_onsets_on_noise_bursts():
    rng = np.random.RandomState(2)
    t = np.arange(int(0.125 * R)) / R
    x = np.concatenate([rng.randn(len(t)) * np.exp(-t * 40) * a for a in (0.8, 0.2, 0.5, 0.2)] * 2).astype(np.float32)
    found = [p / R for p in detect_onsets(x, R, percussive=True)]
    assert len(found) == 8
    for got, want in zip(found, np.arange(8) * 0.125):
        assert abs(got - want) < 0.01


def test_vibrato_and_abrupt_end_are_not_onsets():
    t = np.arange(2 * R) / R
    f = _hz(57) * 2 ** (0.6 / 12 * np.sin(2 * np.pi * 6 * t))
    amp = 0.4 * (1 + 0.3 * np.sin(2 * np.pi * 6 * t)) * np.minimum(1, t / 0.02)
    x = sum(amp / k * np.sin(2 * np.pi * k * np.cumsum(f) / R) for k in range(1, 5)).astype(np.float32)
    assert len(detect_onsets(x, R)) == 1                                   # taglio a fine file
    cut = np.concatenate([x[:R], np.zeros(R // 2, np.float32)])
    assert len(detect_onsets(cut, R)) == 1                                 # taglio a meta' file


def test_silence_has_no_onsets():
    assert detect_onsets(np.zeros(R, np.float32), R) == []
    assert detect_onsets(np.zeros(0, np.float32), R) == []
