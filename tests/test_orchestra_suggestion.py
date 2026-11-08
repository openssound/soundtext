"""
Il file dell'orchestra proposto per lo strumento di una traccia (core.orchestra,
finestra "Strumento plugin") e la correzione "Usa «...»" dello strumento
sconosciuto anche nel menu della colonna delle tracce della vista Testo.

Esecuzione:
    python3 -m pytest tests/test_orchestra_suggestion.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMenu

from core import downloads
from core.instruments import resolve_instrument_type
from core.orchestra import FILE_PER_PROGRAMMA, proposta_per

_app = QApplication.instance() or QApplication([])


@pytest.fixture
def strumenti(tmp_path, monkeypatch):
    script = downloads.load_script()
    monkeypatch.setattr(script, "DEST", tmp_path)
    return tmp_path


def _installa(dest, group, sfz):
    folder = dest / "sfz" / group
    (folder / sfz).parent.mkdir(parents=True, exist_ok=True)
    (folder / sfz).write_text("<region> sample=a.wav\n")
    (folder / ".completo").touch()
    return folder / sfz


def test_every_proposed_file_belongs_to_its_group():
    script = downloads.load_script()
    for program, (group, sfz) in FILE_PER_PROGRAMMA.items():
        assert sfz in script.ORCHESTRA_SFZ[group], (program, group, sfz)


def test_proposal_follows_the_track_instrument(strumenti):
    flauto = proposta_per(resolve_instrument_type("Flauto", "Flauto"))
    assert flauto.group == "vsco-legni" and flauto.file_name == "FluteSusVib.sfz" and not flauto.installed
    assert "Legni" in flauto.group_label
    _installa(strumenti, "vsco-legni", "FluteSusVib.sfz")
    assert proposta_per(resolve_instrument_type("Flauto", "Flauto")).installed
    assert proposta_per(resolve_instrument_type("Violoncello", "Violoncello")).file_name == "CelloEnsSusVib.sfz"
    # "Clavicembalo" si riconosce dalla 2.11.1 di st-language
    assert proposta_per(resolve_instrument_type("Clavicembalo", "Clavicembalo")).group == "vcsl-clavicembalo"
    assert proposta_per(resolve_instrument_type("Drums", "Drums")) is None        # percussioni
    assert proposta_per(resolve_instrument_type("Chitarra", "Chitarra")) is None  # non c'e' nell'orchestra
    assert proposta_per(None) is None


def _orchestra_row(dialog):
    for i in range(dialog.tree.topLevelItemCount()):
        item = dialog.tree.topLevelItem(i)
        if item.text(0).startswith("Orchestra"):
            return item
    return None


def test_picker_offers_the_installed_file(strumenti, monkeypatch):
    import core.sfz_engine
    from gui.plugin_dialogs import PluginPickerDialog
    monkeypatch.setattr(core.sfz_engine, "library_found", lambda: "/libsfizz.so")
    path = _installa(strumenti, "vsco-legni", "FluteSusVib.sfz")
    dialog = PluginPickerDialog(instrument=True, profile=resolve_instrument_type("Flauto", "Flauto"))
    row = _orchestra_row(dialog)
    assert row is not None and row.flags() & Qt.ItemIsEnabled and "FluteSusVib.sfz" in row.text(0)
    dialog.tree.setCurrentItem(row)
    ref = dialog.selected_ref()
    # il riferimento usa "/" (vale su ogni sistema): su Windows si confronta normalizzato
    assert ref.startswith("sfz:") and os.path.normpath(os.path.expanduser(ref[4:])) == os.path.normpath(str(path))


def test_picker_greys_the_file_still_to_download(strumenti, monkeypatch):
    import core.sfz_engine
    from gui.plugin_dialogs import PluginPickerDialog
    monkeypatch.setattr(core.sfz_engine, "library_found", lambda: "/libsfizz.so")
    dialog = PluginPickerDialog(instrument=True, profile=resolve_instrument_type("Oboe", "Oboe"))
    row = _orchestra_row(dialog)
    assert not row.flags() & Qt.ItemIsEnabled and "da scaricare" in row.text(0)
    assert "Scarica e installa" in row.toolTip(0)
    assert _orchestra_row(PluginPickerDialog(instrument=True)) is None          # senza traccia: niente
    assert _orchestra_row(PluginPickerDialog(instrument=True, profile=resolve_instrument_type(
        "Chitarra", "Chitarra"))) is None


def test_text_view_column_menu_fixes_an_unknown_instrument(monkeypatch):
    from core.project_io import parse_project_text
    from gui.main_window import MainWindow
    for name in ("information", "warning"):
        from PySide6.QtWidgets import QMessageBox
        monkeypatch.setattr(QMessageBox, name, staticmethod(lambda *a, **k: QMessageBox.Ok))
    window = MainWindow()
    window.project = parse_project_text("Tempo: 120 BPM\n\nTraccia Melodia [Flautoo]:\n  4: c d e f |\n")
    window.refresh_mixer()
    window.select_track("Melodia")
    from PySide6.QtCore import QPoint
    from _menus import scripted_menus
    with scripted_menus(lambda text: text.startswith("Usa")) as menus:      # si sceglie la correzione
        window.show_track_actions_menu("Melodia", QPoint(0, 0))
    assert "Usa «Flauto»" in menus.actions
    assert window.project.get_track("Melodia").instrument_name == "Flauto"
