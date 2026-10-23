"""
Test del groove di una ripresa (core.groove) e della batteria che lo segue
(core.rhythm_generate.generate_drum_pattern con kick_accents).

Esecuzione:
    python3 -m pytest tests/test_groove.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import groove
from core.audio_tracks import write_wav
from core.model import AudioClip, Project
from core.rhythm_generate import generate_drum_pattern
from core.notation import parse_track_text

RATE = 48000
STRONG = (0, 6, 8, 11)          # sedicesimi con l'accento, in ogni battuta


def _groove_take(tmp_path, bars=4, bpm=120):
    sixteenth = 60.0 / bpm / 4
    x = np.zeros(int((bars * 16 * sixteenth + 1.0) * RATE), np.float32)
    n = np.arange(int(0.06 * RATE))
    for bar in range(bars):
        for slot in range(0, 16, 2):
            amp = 1.0 if slot in STRONG else 0.15
            start = int((bar * 16 + slot) * sixteenth * RATE)
            hit = amp * np.sin(2 * np.pi * 150 * n / RATE) * np.exp(-n / (0.012 * RATE))
            x[start:start + len(n)] += hit.astype(np.float32)
        start = int((bar * 16 + 11) * sixteenth * RATE)             # l'accento in levare
        x[start:start + len(n)] += (np.sin(2 * np.pi * 150 * n / RATE) * np.exp(-n / (0.012 * RATE))).astype(np.float32)
    path = str(tmp_path / "groove.wav")
    write_wav(path, x[:, None], RATE)
    p = Project(tempo_bpm=bpm)
    t = p.add_audio_track("Chitarra")
    t.audio_clips.append(AudioClip("Ritmica", path, 4.0))           # dalla battuta 2
    return p, t


def test_groove_finds_the_strong_sixteenths(tmp_path):
    p, t = _groove_take(tmp_path)
    weights = groove.groove_of_track(p, t)
    assert len(weights) == 16
    strong = sorted(range(16), key=lambda i: -weights[i])[:4]
    assert sorted(strong) == list(STRONG)
    assert all(weights[i] < 0.4 for i in range(16) if i not in STRONG)
    assert groove.is_cached(p, t)


def test_drums_put_the_kick_on_the_accents(tmp_path):
    p, t = _groove_take(tmp_path)
    text = generate_drum_pattern("rock", bars=2, fill_every=0, kick_accents=groove.groove_of_track(p, t))
    kicks = sorted({round(ev.start % 4.0, 3) for ev in parse_track_text(text, {})
                    if ev.kind in ("percussion", "block") and "kick" in str(ev.items or ev.symbol or ev.__dict__)})
    plain = generate_drum_pattern("rock", bars=2, fill_every=0)
    assert text != plain
    assert {1.5, 2.75} <= set(kicks)                                  # sedicesimi 6 e 11


def test_drum_dialog_follows_the_take(tmp_path):
    from PySide6.QtWidgets import QApplication
    from gui.rhythm_generate_dialog import DrumGenerateDialog
    _app = QApplication.instance() or QApplication([])
    p, t = _groove_take(tmp_path)
    p.add_track("Batteria", "Drums", "")
    dlg = DrumGenerateDialog(None, project=p, instrument_name="Drums", context_label="prova", default_bars=2,
                             track_name="Batteria")
    dlg.fill_every_spin.setValue(0)
    plain = dlg.preview_edit.toPlainText()
    assert [dlg.groove_combo.itemData(i) for i in range(dlg.groove_combo.count())] == [None, "Chitarra"]
    dlg.groove_combo.setCurrentIndex(1)
    followed = dlg.preview_edit.toPlainText()
    assert followed != plain and followed.count("kick") > plain.count("kick")
    dlg.reject()
