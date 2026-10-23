"""
Test GUI (PySide6, offscreen) del pannello della quantizzazione regolabile
(gui.quantize_options) e del suo uso nei dialoghi.

Esecuzione:
    python3 -m pytest tests/test_quantize_options_gui.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication

from core import settings as app_settings
from core.audio_quantize import QuantizeSettings
from gui.quantize_options import QuantizeOptionsWidget

_app = QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _clean_settings():
    app_settings.set_quantize_settings({})
    yield
    app_settings.set_quantize_settings({})


def test_defaults_are_the_usual_quantization_and_the_panel_starts_closed():
    w = QuantizeOptionsWidget()
    w.show()
    assert w.settings() == QuantizeSettings()
    assert not w.panel.isVisible()
    w.toggle.setChecked(True)
    assert w.panel.isVisible()


def test_values_are_read_remembered_and_flagged_as_custom():
    w = QuantizeOptionsWidget()
    seen = []
    w.changed.connect(lambda: seen.append(1))
    w.strength_spin.setValue(60)
    w.window_spin.setValue(50)
    w.swing_spin.setValue(66)
    w.min_note_spin.setValue(40)
    w.merge_spin.setValue(30)
    assert seen and "personalizzati" in w.toggle.text()
    assert w.settings() == QuantizeSettings(strength=0.6, window=0.5, swing=0.66, min_note_sec=0.04,
                                            merge_gap_sec=0.03)
    w.remember()
    again = QuantizeOptionsWidget()
    assert again.settings() == w.settings()
    again.set_settings(QuantizeSettings())
    again.remember()
    assert app_settings.get_quantize_settings() == {}


def test_swing_only_on_straight_eighths_and_sixteenths():
    w = QuantizeOptionsWidget()
    w.swing_spin.setValue(66)
    for grid, ternary, enabled in ((8, False, True), (16, False, True), (16, True, False), (4, False, False)):
        w.set_grid(grid, ternary)
        assert w.swing_spin.isEnabled() is enabled
        assert w.settings().swing == (0.66 if enabled else 0.5)
    w.remember()                                   # lo swing scelto resta per quando torna valido
    assert app_settings.get_quantize_settings()["swing"] == 0.66


def test_dialogs_pass_the_settings_to_the_conversion(tmp_path):
    import numpy as np
    from core.audio_tracks import write_wav
    from core.model import AudioClip, Project
    from gui.audio_track_convert_dialog import AudioTrackConvertDialog
    path = str(tmp_path / "a.wav")
    write_wav(path, np.zeros((4800, 1), np.float32), 48000)
    p = Project()
    t = p.add_audio_track("Voce")
    t.audio_clips.append(AudioClip("A", path, 0.0))
    dlg = AudioTrackConvertDialog(None, p, t)
    dlg.quant_options.strength_spin.setValue(70)
    assert dlg.options().quantize.strength == pytest.approx(0.7)
    dlg.mode_combo.setCurrentIndex(dlg.mode_combo.findData("chords"))
    assert dlg.options().quantize is None
