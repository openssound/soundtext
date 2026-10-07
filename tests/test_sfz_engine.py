"""
Test del motore SFZ interno (core.sfz_engine) sulla libreria sfizioso o
sfizz: si saltano se la libreria non c'e' (vedi SOUNDTEXT_SFZ_LIB).

Esecuzione:
    python3 -m pytest tests/test_sfz_engine.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from core.sfz_engine import SfzError, SfzInstance, sfz_available

RATE = 48000
needs_lib = pytest.mark.skipif(not sfz_available(), reason="libreria SFZ (sfizioso o sfizz) non trovata")


def _sfz(tmp_path, sample):
    path = tmp_path / f"{sample.strip('*')}.sfz"
    path.write_text(f"<region> sample={sample}\n")
    return str(path)


def _rms(x):
    return float(np.sqrt(np.mean(np.square(x)))) if len(x) else 0.0


@needs_lib
def test_plays_notes_at_their_time(tmp_path):
    inst = SfzInstance(_sfz(tmp_path, "*sine"), RATE)
    assert inst.regions == 1
    y = inst.render([(0.5, bytes([0x90, 69, 100])), (1.0, bytes([0x80, 69, 0]))], 1.5)
    assert y.shape == (int(1.5 * RATE), 2) and y.dtype == np.float32
    assert _rms(y[:int(0.45 * RATE)]) < 1e-5
    assert _rms(y[int(0.6 * RATE):int(0.9 * RATE)]) > 0.05
    inst.close()


@needs_lib
def test_silence_sfz_and_reset(tmp_path):
    inst = SfzInstance(_sfz(tmp_path, "*silence"), RATE)
    assert _rms(inst.render([(0.0, bytes([0x90, 60, 100]))], 0.3)) < 1e-6
    inst.close()
    inst = SfzInstance(_sfz(tmp_path, "*sine"), RATE)
    inst.render([(0.0, bytes([0x90, 60, 100]))], 0.3)            # nota lasciata accesa
    inst.reset()
    assert _rms(inst.render([], 0.3)[int(0.1 * RATE):]) < 1e-5
    inst.close()


@needs_lib
def test_missing_file_is_a_clear_error(tmp_path):
    with pytest.raises(SfzError, match="non trovato"):
        SfzInstance(str(tmp_path / "manca.sfz"), RATE)


# ------------------------------------------------------------------ come strumento di una traccia

@pytest.fixture
def _plugins():
    from core import plugins
    yield plugins
    plugins.shutdown()


@needs_lib
def test_describe_and_names(tmp_path, _plugins):
    path = _sfz(tmp_path, "*sine")
    ref = "sfz:" + path
    assert _plugins.display_name(ref) == "sine"
    info = _plugins.describe(ref)
    assert (info.format, info.format_label, info.name, info.instrument, info.params) == ("sfz", "SFZ", "sine", True, [])
    with pytest.raises(_plugins.PluginError, match="non trovato"):
        _plugins.describe("sfz:" + str(tmp_path / "manca.sfz"))


@needs_lib
def test_track_played_by_the_sfz_engine(tmp_path, _plugins):
    from core.effect_render import clear_stem_cache
    from core.model import Project
    from core.playback import render_project_mix
    p = Project(name="prova")
    track = p.add_track("Synth", "Piano", "4: c*4 e*4 g*4 c*5")
    for sample, loud in (("*sine", True), ("*silence", False)):
        clear_stem_cache()
        track.synth = "sfz:" + _sfz(tmp_path, sample)
        y, _rate = render_project_mix(p)
        assert (_rms(y) > 1e-3) == loud, sample


# ------------------------------------------------------------------ interfaccia

def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _picker(monkeypatch, found=True, current_ref=""):
    from core import plugins, sfz_engine
    from gui.plugin_dialogs import SFZ_CHOICE, PluginPickerDialog
    monkeypatch.setattr(plugins, "scan_plugins", lambda refresh=False, progress=None: [])
    monkeypatch.setattr(sfz_engine, "library_found", lambda: "/x/libsfizz.so" if found else "")
    dialog = PluginPickerDialog(None, instrument=True, current_ref=current_ref)
    item = next(dialog.tree.topLevelItem(i) for i in range(dialog.tree.topLevelItemCount())
                if dialog.tree.topLevelItem(i).data(0, 0x0100) == SFZ_CHOICE)
    return dialog, item


def test_picker_chooses_an_sfz_file(tmp_path, monkeypatch):
    _app()
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QFileDialog
    path = _sfz(tmp_path, "*sine")
    dialog, item = _picker(monkeypatch)
    assert item.flags() & Qt.ItemIsEnabled
    dialog.tree.setCurrentItem(item)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: ("", "")))
    dialog._accept_if_usable()                                   # scelta del file annullata: si resta qui
    assert dialog.result() == 0 and dialog.selected_ref() is None
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (path, "")))
    dialog._accept_if_usable()
    assert dialog.result() == 1 and dialog.selected_ref() == "sfz:" + path


def test_picker_shows_the_current_sfz_and_a_missing_library(tmp_path, monkeypatch):
    _app()
    from PySide6.QtCore import Qt
    path = _sfz(tmp_path, "*sine")
    dialog, item = _picker(monkeypatch, current_ref="sfz:" + path)
    assert dialog.tree.currentItem() is item and "sine" in item.text(0)
    assert dialog.selected_ref() == "sfz:" + path
    dialog, item = _picker(monkeypatch, found=False)
    from gui.plugin_dialogs import SFZ_LIBRARY_COMMAND     # il comando cambia col sistema
    assert not item.flags() & Qt.ItemIsEnabled and SFZ_LIBRARY_COMMAND in item.toolTip(0)


def test_track_gets_the_sfz_instrument_without_parameters_window(tmp_path, monkeypatch):
    _app()
    from PySide6.QtWidgets import QDialog
    from gui import plugin_dialogs
    from gui.main_window import MainWindow
    ref = "sfz:" + _sfz(tmp_path, "*sine")

    class FakePicker:
        def __init__(self, *a, **k):
            pass

        def exec(self):
            return QDialog.Accepted

        def selected_ref(self):
            return ref
    opened = []
    monkeypatch.setattr(plugin_dialogs, "PluginPickerDialog", FakePicker)
    monkeypatch.setattr(plugin_dialogs.PluginParamsDialog, "exec", lambda self: opened.append(self) or 1)
    w = MainWindow()
    w.project.add_track("Marimba", "Piano", "4: c d e f")
    w.refresh_mixer()
    w.choose_track_synth("Marimba")
    assert w.project.get_track("Marimba").synth == ref and not opened
    assert "sine (SFZ)" in w.track_headers["Marimba"].instr_label.toolTip() + w.track_headers["Marimba"].instr_label.text()


@needs_lib
def test_signature_follows_the_sfz_file(tmp_path, _plugins):
    path = _sfz(tmp_path, "*sine")
    before = _plugins.signature("sfz:" + path, {}, "")
    os.utime(path, (1, 1))
    assert _plugins.signature("sfz:" + path, {}, "") != before
