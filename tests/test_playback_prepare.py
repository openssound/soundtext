"""
Prima che parta l'audio si preparano le tracce con effetti o strumenti
plugin (con i profili NAM anche un minuto): la barra di avanzamento lo dice,
e uno Stop in quel momento non butta via il lavoro (le tracce finiscono in
sottofondo e il Play dopo le trova pronte).

Esecuzione:
    python3 -m pytest tests/test_playback_prepare.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication  # noqa: E402

from core import effect_render  # noqa: E402

_app = QApplication.instance() or QApplication([])


def test_render_stems_reports_each_finished_track(monkeypatch):
    monkeypatch.setattr(effect_render, "render_stem",
                        lambda request, stop_check=None: np.zeros((10, 2), dtype=np.float32))
    seen = []
    out = effect_render.render_stems(["a", "b", "c"], None, on_done=lambda: seen.append(1))
    assert len(out) == 3 and len(seen) == 3
    seen.clear()
    effect_render.render_stems(["solo"], None, on_done=lambda: seen.append(1))
    assert seen == [1]


def test_progress_bar_shows_the_preparation_and_stop_clears_it():
    from gui.main_window import MainWindow
    w = MainWindow()
    w._playback_start_wall = None
    w.playback.stem_progress = (2, 5)
    w._update_playback_progress()
    assert "2" in w.playback_progress.format() and "5" in w.playback_progress.format()
    assert w.playback_progress.value() == 40
    w.playback.stop()
    assert w.playback.stem_progress is None
    w.close()
