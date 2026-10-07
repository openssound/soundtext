"""
Test GUI (PySide6, offscreen) dei nomi proposti da "Salva progetto come",
"Esporta MIDI" ed "Esporta mix audio": il nome del progetto, anche subito
dopo il primo salvataggio di un progetto nuovo.

Esecuzione:
    python3 -m pytest tests/test_export_default_names_gui.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QFileDialog

from gui.main_window import MainWindow

_app = QApplication.instance() or QApplication([])


def _proposed(monkeypatch, action):
    """Esegue action (che apre un QFileDialog di salvataggio) annullandolo, e
    restituisce il percorso che il dialogo proponeva."""
    captured = {}

    def fake_dialog(_parent, _caption, directory, *a, **k):
        captured["path"] = directory
        return "", ""

    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(fake_dialog))
    action()
    return captured["path"]


def test_new_project_proposes_generic_name(monkeypatch):
    w = MainWindow()
    assert os.path.basename(_proposed(monkeypatch, w.save_project_as)) == "progetto.st"
    assert os.path.basename(_proposed(monkeypatch, w.export_midi)) == "progetto.mid"
    assert os.path.basename(_proposed(monkeypatch, w.export_mix_wav)) == "progetto.wav"


def test_after_save_as_exports_propose_the_file_name(tmp_path, monkeypatch):
    w = MainWindow()
    target = str(tmp_path / "La mia canzone.st")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (target, "")))
    w.save_project_as()
    assert w.current_path == target

    assert _proposed(monkeypatch, w.save_project_as) == target
    assert _proposed(monkeypatch, w.export_midi) == str(tmp_path / "La mia canzone.mid")
    assert _proposed(monkeypatch, w.export_mix_wav) == str(tmp_path / "La mia canzone.wav")


def test_track_midi_export_proposes_track_name_in_project_folder(tmp_path, monkeypatch):
    w = MainWindow()
    w.current_path = str(tmp_path / "Brano.st")
    w.project.add_track("Piano elettrico", "Piano", "4: c d e f")
    w.select_track("Piano elettrico")
    assert _proposed(monkeypatch, w.export_selected_track_midi) == str(tmp_path / "Piano_elettrico.mid")
