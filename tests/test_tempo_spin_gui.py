"""
Test GUI (offscreen) del campo del tempo con un decimale (gui.tempo_spin)
nella barra della finestra principale.

Esecuzione:
    python3 -m pytest tests/test_tempo_spin_gui.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QLocale
from PySide6.QtWidgets import QApplication

from gui.tempo_spin import TempoSpinBox, tempo_value

_app = QApplication.instance() or QApplication([])


def test_whole_tempos_have_no_decimals_and_decimals_use_the_locale():
    spin = TempoSpinBox()
    spin.setLocale(QLocale(QLocale.Italian))
    spin.setValue(120)
    assert spin.text() == "120 BPM" and spin.bpm() == 120 and isinstance(spin.bpm(), int)
    spin.setValue(101.4)
    assert spin.text() == "101,4 BPM" and spin.bpm() == 101.4
    spin.setLocale(QLocale(QLocale.English))
    spin.setValue(96.5)
    assert spin.text() == "96.5 BPM"
    assert tempo_value(99.96) == 100 and tempo_value(99.94) == 99.9


def test_the_toolbar_writes_a_decimal_tempo_into_the_song():
    from core.project_io import project_to_text
    from gui.main_window import MainWindow
    w = MainWindow()
    w.tempo_spin.setValue(101.4)
    assert w.project.tempo_bpm == 101.4
    text = project_to_text(w.project)
    assert text.startswith("ST: 2.9\n") and "Tempo: 101.4 BPM" in text
    w.tempo_spin.setValue(120)
    assert w.project.tempo_bpm == 120 and isinstance(w.project.tempo_bpm, int)
    assert project_to_text(w.project).startswith("ST: 2.8\n")
    w.undo()
    assert w.project.tempo_bpm == 101.4 and w.tempo_spin.bpm() == 101.4
