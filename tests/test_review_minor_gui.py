"""Note minori della revisione, lato interfaccia (offscreen): ascolto di un
box con le ancore bar=N, editor ricaricato dopo la rinomina di un pattern,
richiami &Nome aggiornati dopo la rinomina di un file della libreria MIDI."""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QMessageBox

from core.model import Clip
from gui import main_window_project
from gui.main_window import MainWindow
from gui.midi_library_dialog import MidiLibraryDialog

_app = QApplication.instance() or QApplication([])


class _FakePlayback:
    def __init__(self):
        self.project = None
        self.offset = None

    def is_playing(self):
        return False

    def play(self, project, only_audible=True, start_offset_beats=0.0, on_audio_started=None):
        self.project, self.offset = project, start_offset_beats

    def stop(self):
        pass


def _window_with_box(text, start_beat):
    w = MainWindow()
    w.project.add_track("Piano", "Piano", "")
    clip = Clip(name="A", text=text, start_beat=start_beat)
    w.project.tracks[0].clips.append(clip)
    w.arrangement_action.setChecked(True)
    w.arrangement_view.refresh()
    w.arrangement_view._preview_playback = _FakePlayback()
    return w, clip


def test_box_preview_with_anchor_starts_from_the_box_position():
    w, clip = _window_with_box("4: c bar=5 d", 8)
    w.arrangement_view._play_clip("Piano", clip)
    fake = w.arrangement_view._preview_playback
    assert fake.offset == 8.0
    assert fake.project.tracks[0].text.startswith("16: 32r ")
    w.close()


def test_box_preview_without_anchor_is_unchanged():
    w, clip = _window_with_box("4: c d", 8)
    w.arrangement_view._play_clip("Piano", clip)
    fake = w.arrangement_view._preview_playback
    assert fake.offset == 0.0 and fake.project.tracks[0].text == "4: c d"
    w.close()


def test_editor_shows_the_renamed_pattern(monkeypatch):
    w = MainWindow()
    w.project.add_pattern("Giro", "4: c d e f |")
    w.project.add_track("Piano", "Piano", "%Giro %Giro")
    w.select_track("Piano")

    class _RenamingDialog:
        def __init__(self, project, parent):
            self.project = project

        def exec(self):
            self.project.rename_pattern("Giro", "Strofa")

    monkeypatch.setattr(main_window_project, "PatternEditorDialog", _RenamingDialog)
    w.manage_patterns()
    assert w.editor.toPlainText() == "%Strofa %Strofa"
    # una modifica successiva non riporta il testo vecchio
    w.editor.insertPlainText(" ")
    assert w.project.get_track("Piano").text.strip() == "%Strofa %Strofa"
    w._dirty = False      # niente domanda "salvare?" alla chiusura
    w.close()


def test_midi_library_rename_updates_the_song(monkeypatch, tmp_path):
    w = MainWindow()
    w.project.add_track("Basso", "Bass", '&"riff" 2&"Blues/riff"+3 &"riff"-1')
    dlg = MidiLibraryDialog(w, midi_dir=str(tmp_path), project=w.project)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    dlg._update_project_refs("Blues/riff", "Funk/groove", ["Blues/riff", "altro"])
    assert dlg.project_changed
    assert w.project.get_track("Basso").text == '&"groove" 2&"Funk/groove"+3 &"groove"-1'
    dlg.close()
    w.close()


def test_midi_library_rename_keeps_the_folder_when_the_new_name_is_not_unique(monkeypatch, tmp_path):
    w = MainWindow()
    w.project.add_track("Basso", "Bass", '&"riff"')
    dlg = MidiLibraryDialog(w, midi_dir=str(tmp_path), project=w.project)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    dlg._update_project_refs("riff", "Funk/groove", ["riff", "Rock/groove"])
    assert w.project.get_track("Basso").text == '&"Funk/groove"'
    dlg.close()
    w.close()
