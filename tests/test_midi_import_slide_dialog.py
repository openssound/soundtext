"""Test GUI (piattaforma offscreen) del dialogo Opzioni -> Slide nell'import
MIDI: la soglia si modifica solo con 'Slide' spuntato, e OK salva."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])

from core import settings
from gui.midi_import_slide_dialog import MidiImportSlideDialog


def test_threshold_enabled_only_when_slide_checked_and_ok_saves():
    orig = (settings.get_midi_import_slide_sensitive(), settings.get_midi_import_slide_threshold())
    try:
        settings.set_midi_import_slide_sensitive(False)
        dlg = MidiImportSlideDialog()
        assert not dlg.slide_check.isChecked()
        assert not dlg.threshold_spin.isEnabled()
        dlg.slide_check.setChecked(True)
        assert dlg.threshold_spin.isEnabled()
        dlg.threshold_spin.setValue(0.65)
        dlg._accept()
        assert settings.get_midi_import_min_bend_semitones() == 0.65

        # Cancel non salva.
        dlg2 = MidiImportSlideDialog()
        dlg2.slide_check.setChecked(False)
        dlg2.reject()
        assert settings.get_midi_import_min_bend_semitones() == 0.65
    finally:
        settings.set_midi_import_slide_threshold(orig[1])
        settings.set_midi_import_slide_sensitive(orig[0])


if __name__ == "__main__":
    test_threshold_enabled_only_when_slide_checked_and_ok_saves()
    print("OK  test_threshold_enabled_only_when_slide_checked_and_ok_saves")
