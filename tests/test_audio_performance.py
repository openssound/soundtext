"""
Test delle ottimizzazioni delle tracce audio: file decodificati in cache per
il mix, mix con molti pezzi dello stesso file, stretch calcolato in
anticipo, analisi fuori dal thread dell'interfaccia.

Esecuzione:
    python3 -m pytest tests/test_audio_performance.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys
import time

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import audio_tracks as at
from core.audio_tracks import AUDIO_SAMPLE_RATE as RATE, AudioLayer, write_wav
from core.beat_track import onset_envelope


def _noise(tmp_path, seconds=4.0, name="n.wav"):
    path = str(tmp_path / name)
    write_wav(path, (np.random.default_rng(0).standard_normal((int(seconds * RATE), 1)) * 0.1).astype(np.float32), RATE)
    return path


def test_decoded_files_are_read_once_and_follow_changes(tmp_path):
    path = _noise(tmp_path)
    first = at.decoded_wav(path)[0]
    assert at.decoded_wav(path)[0] is first and not first.flags.writeable
    time.sleep(0.01)
    write_wav(path, np.zeros((RATE, 1), np.float32), RATE)
    assert len(at.decoded_wav(path)[0]) == RATE                  # file cambiato: si rilegge


def test_many_pieces_mix_like_one_clip(tmp_path):
    path = _noise(tmp_path)
    whole = [AudioLayer(path, 0.0, 0.0, 0.0, 1.0, 64)]
    pieces = [AudioLayer(path, k * 0.1, k * 0.1, 4.0 - (k + 1) * 0.1, 1.0, 64, fade_in=0.0, fade_out=0.0)
              for k in range(40)]
    a = at.mix_layers(np.zeros((0, 2), np.float32), RATE, whole)
    b = at.mix_layers(np.zeros((0, 2), np.float32), RATE, pieces)
    assert len(a) == len(b) == 4 * RATE
    # uguali lontano dai bordi dei pezzi (dove c'e' la microdissolvenza)
    inside = np.concatenate([np.arange(int((k * 0.1 + 0.01) * RATE), int(((k + 1) * 0.1 - 0.01) * RATE)) for k in range(40)])
    assert np.allclose(a[inside], b[inside], atol=1e-6)


def test_onset_envelope_of_a_very_short_signal():
    env, _fps = onset_envelope(np.ones((3000, 1), np.float32) * 0.1, RATE)
    assert len(env) > 0


def test_stretch_is_warmed_with_the_same_key_as_the_mix(tmp_path, monkeypatch):
    pytest.importorskip("pedalboard")
    path = _noise(tmp_path, 1.0)
    layer = AudioLayer(path, 0.0, 0.0, 0.0, 1.0, 64, stretch=1.25)
    assert at.warm_stretched_layers([layer]) == 1
    calls = []
    original = at.stretched
    monkeypatch.setattr(at, "stretched", lambda *a, **k: calls.append(k.get("key")) or original(*a, **k))
    at.mix_layers(np.zeros((0, 2), np.float32), RATE, [layer])
    assert at.warm_stretched_layers([layer]) == 0                # gia' pronto
    with at._stretch_lock:
        assert calls and calls[0] in at._stretch_cache


def test_run_with_wait_returns_the_result_or_the_error():
    from PySide6.QtWidgets import QApplication
    from gui.worker import run_with_wait
    QApplication.instance() or QApplication([])
    assert run_with_wait(None, "prova", lambda x: x * 2, 21) == 42

    def fail():
        raise ValueError("niente da fare")

    with pytest.raises(RuntimeError, match="niente da fare"):
        run_with_wait(None, "prova", fail)
