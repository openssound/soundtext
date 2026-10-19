import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)

from PySide6.QtWidgets import QApplication

from core import settings as app_settings
from core.model import Project

_app = QApplication.instance() or QApplication([])


def _clean():
    app_settings.set_audio_pitch_params({})


def test_pitch_settings_are_saved_only_when_changed():
    from gui.audio_pitch_dialog import DEFAULTS, AudioPitchDialog, current_pitch_params, is_customized
    _clean()
    dialog = AudioPitchDialog()
    dialog.accept()
    assert app_settings.get_audio_pitch_params() == {} and not is_customized()
    dialog = AudioPitchDialog()
    dialog.min_freq_auto_check.setChecked(False)
    dialog.min_freq_spin.setValue(110.0)
    dialog.buf_size_combo.setCurrentIndex(dialog.buf_size_combo.findData(4096))
    dialog.accept()
    assert app_settings.get_audio_pitch_params() == {"min_freq_auto": False, "min_freq_hz": 110.0, "buf_size": 4096}
    params = current_pitch_params()
    assert params["buf_size"] == 4096 and params["hop_size"] == DEFAULTS["hop_size"] and is_customized()
    reopened = AudioPitchDialog()                           # riapre con i valori salvati
    assert not reopened.min_freq_auto_check.isChecked() and reopened.min_freq_spin.isEnabled()
    _clean()


def test_reset_restores_the_standard_values():
    from gui.audio_pitch_dialog import DEFAULTS, AudioPitchDialog
    app_settings.set_audio_pitch_params({"min_note_ms": 200, "hop_size": 128})
    dialog = AudioPitchDialog()
    assert dialog.params()["min_note_ms"] == 200
    dialog._show(DEFAULTS)
    assert dialog.params() == DEFAULTS
    _clean()


def test_import_dialog_uses_the_saved_parameters():
    from gui.audio_import_dialog import AudioImportDialog
    from core.instruments import get_instrument
    app_settings.set_audio_pitch_params({"min_freq_auto": False, "min_freq_hz": 123.0, "confidence": 0.5})
    project = Project(name="p")
    project.add_track("Piano", "Piano", "")
    dialog = AudioImportDialog(None, project, "Piano", "Piano")
    min_freq, buf, hop, confidence, min_note = dialog._selected_pitch_advanced_params(
        get_instrument("Piano"), False, False)
    assert (min_freq, buf, hop, confidence) == (123.0, None, None, 0.5)
    assert "personalizzati" in dialog.pitch_hint_label.text()
    assert dialog._selected_pitch_advanced_params(get_instrument("Piano"), True, False) == (None,) * 5
    _clean()
    dialog = AudioImportDialog(None, project, "Piano", "Piano")
    assert "personalizzati" not in dialog.pitch_hint_label.text()
