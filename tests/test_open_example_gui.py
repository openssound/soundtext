"""
Test GUI (PySide6, offscreen) di Progetto -> Apri esempio...: il dialogo
parte dalla cartella examples/ e l'esempio si apre senza restare legato al
file, cosi' Salva non sovrascrive l'originale.

Esecuzione:
    python3 -m pytest tests/test_open_example_gui.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QFileDialog

from core.project_io import EXAMPLES_DIR
from gui.main_window import MainWindow

_app = QApplication.instance() or QApplication([])


def test_open_example_starts_in_examples_and_keeps_original(monkeypatch):
    example = os.path.join(EXAMPLES_DIR, "funk_in_mi.st")
    with open(example, "rb") as f:
        original = f.read()
    captured = {}

    def fake_open(_parent, _caption, directory, *a, **k):
        captured["dir"] = directory
        return example, ""

    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(fake_open))
    w = MainWindow()
    w.open_example()

    assert captured["dir"] == EXAMPLES_DIR
    assert w.project.tracks
    assert w.current_path is None
    assert "funk_in_mi.st" in w.windowTitle()

    # Salva chiede un nuovo percorso (nella cartella dei brani) invece di
    # sovrascrivere l'esempio.
    proposed = {}

    def fake_save(_parent, _caption, directory, *a, **k):
        proposed["path"] = directory
        return "", ""

    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(fake_save))
    w.save_project()
    assert os.path.dirname(proposed["path"]) != EXAMPLES_DIR
    assert os.path.basename(proposed["path"]) == "funk_in_mi.st"
    with open(example, "rb") as f:
        assert f.read() == original


def test_open_example_cancelled_keeps_current_project(monkeypatch):
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: ("", "")))
    w = MainWindow()
    before = w.project
    w.open_example()
    assert w.project is before
