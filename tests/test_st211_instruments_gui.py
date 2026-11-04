"""
Test GUI (PySide6, offscreen) dello strumento sconosciuto (st-language 2.11):
la riga della sintassi lo segnala in ambra col nome suggerito, un clic lo
corregge; all'avvio i pianoforti salvati dalle versioni vecchie si correggono
dopo conferma, e un rifiuto non viene chiesto di nuovo.

Esecuzione:
    python3 -m pytest tests/test_st211_instruments_gui.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from core import instruments, settings
from core.instruments import InstrumentProfile, all_instruments, replace_custom_instrument
from core.project_io import parse_project_text
from gui.main_window import MainWindow

_app = QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    for name in ("information", "warning"):
        monkeypatch.setattr(QMessageBox, name, staticmethod(lambda *a, **k: QMessageBox.Ok))
    yield
    for name in list(instruments._load_custom_instruments()):
        instruments.remove_custom_instrument(name)
    instruments._unresolved_instruments.clear()
    settings._load()
    settings._cache.pop("instrument_fixes_accepted", None)
    settings._cache.pop("instrument_fixes_declined", None)


def test_unknown_instrument_warning_and_quick_fix():
    window = MainWindow()
    window.project = parse_project_text("Tempo: 120 BPM\n\nTraccia Melodia [Flautoo]:\n  4: c d e f |\n")
    window.refresh_mixer()
    window.select_track("Melodia")
    text = window.validation_label.text()
    assert "Flautoo" in text and "Flauto" in text
    window.jump_to_first_issue()          # il clic sulla riga
    track = window.project.get_track("Melodia")
    assert track.instrument_name == "Flauto" and track.instrument.gm_program == 73
    assert "Flautoo" not in window.validation_label.text()


def test_startup_fix_of_legacy_pianos(monkeypatch):
    piano = dict(gm_program=0, is_percussion=False, default_octave=4, range_low=21, range_high=108,
                 polyphonic=True, voicing_style="spread")
    replace_custom_instrument(InstrumentProfile(name="Flauto", **piano))
    replace_custom_instrument(InstrumentProfile(name="Violoncelle", **piano))
    answers = iter([QMessageBox.Yes, QMessageBox.No])
    asked = []

    def question(_parent, _title, text, *a, **k):
        asked.append(text)
        return next(answers)

    monkeypatch.setattr(QMessageBox, "question", staticmethod(question))
    window = MainWindow()
    window.offer_instrument_fixes()
    assert len(asked) == 2
    assert all_instruments()["Flauto"].gm_program == 73
    assert all_instruments()["Violoncelle"].gm_program == 0
    window.offer_instrument_fixes()        # il rifiuto non si richiede
    assert len(asked) == 2
