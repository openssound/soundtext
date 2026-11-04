"""
Note che lo strumento SFZ di una traccia non suona (core.sfz_coverage):
la lettura dei tasti e delle dinamiche delle regioni di un .sfz e
l'avviso nella testata della traccia, nella riga sotto l'editor e
all'avvio della riproduzione.

Esecuzione:
    python3 -m pytest tests/test_sfz_coverage.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QMessageBox

from core.project_io import parse_project_text
from core.sfz_coverage import sfz_regions, silent_notes, sounds

_app = QApplication.instance() or QApplication([])


def _sfz(tmp_path, text, name="strumento.sfz"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_regions_follow_the_sfz_hierarchy_and_note_names(tmp_path):
    path = _sfz(tmp_path, """
        // commento <region> lokey=0
        <control> default_path=Campioni\\
        #define $BASSO 36
        <global> hivel=100
        <group> lokey=$BASSO hikey=c3          /* c3 = 48 */
        <region> sample=a.wav
        <region> sample=b.wav lovel=50
        <group>
        <region> key=60 sample=c.wav
        <region> lokey=61 hikey=62 trigger=release sample=d.wav
        #include "altre.sfz"
    """)
    _sfz(tmp_path, "<region> lokey=d#4 hikey=72 sample=e.wav", "altre.sfz")
    regions = sfz_regions(path)
    assert (36, 48, 1, 100) in regions and (36, 48, 50, 100) in regions
    assert (60, 60, 1, 100) in regions and (63, 72, 1, 100) in regions
    assert not any(lo == 61 for lo, *_ in regions)            # il rilascio non suona all'attacco
    assert sounds(regions, 40, 80) and not sounds(regions, 40, 110)   # oltre hivel del <global>
    assert not sounds(regions, 30, 80) and not sounds(regions, 61, 80)


def test_octave_offset_shifts_the_played_keys(tmp_path):
    path = _sfz(tmp_path, "<control> octave_offset=1\n<region> lokey=48 hikey=60 sample=a.wav\n")
    assert sfz_regions(path) == [(36, 48, 1, 127)]


def _project(sfz_path, notes):
    project = parse_project_text(f"Tempo: 120 BPM\n\nTraccia Timpani [Timpani]:\n  4: {notes} |\n")
    project.get_track("Timpani").synth = "sfz:" + sfz_path
    return project


def test_silent_notes_count_and_message(tmp_path):
    path = _sfz(tmp_path, "<region> lokey=36 hikey=60 sample=t.wav\n", "Timpani.sfz")
    project = _project(path, "g*1 a*1 d*2 d*2")
    silent = silent_notes(project, project.get_track("Timpani"))
    assert (silent.silent, silent.total, silent.low, silent.high) == (2, 4, 31, 33)
    assert silent.message() == "2 note su 4 restano mute (g*1–a*1): «Timpani.sfz» suona solo da c*2 a c*4"
    assert silent_notes(*_with(_project(path, "d*2 a*2 c*4 r"))) is None              # tutte dentro
    one = silent_notes(*_with(_project(path, "c#*4 d*2 d*2 d*2")))
    assert one.message().startswith("1 nota su 4 resta muta (c#*4)")
    plain = _project(path, "g*1 a*1 d*2 d*2")
    plain.get_track("Timpani").synth = ""                                              # SoundFont: niente
    assert silent_notes(*_with(plain)) is None


def _with(project):
    return project, project.get_track("Timpani")


def test_window_warns_in_header_editor_and_on_play(tmp_path, monkeypatch):
    for name in ("information", "warning"):
        monkeypatch.setattr(QMessageBox, name, staticmethod(lambda *a, **k: QMessageBox.Ok))
    from gui.main_window import MainWindow
    path = _sfz(tmp_path, "<region> lokey=36 hikey=60 sample=t.wav\n", "Timpani.sfz")
    window = MainWindow()
    window.project = _project(path, "g*1 a*1 d*2 d*2")
    window.refresh_mixer()
    header = window.track_headers["Timpani"]
    assert header.instr_label.text().startswith("⚠") and "restano mute" in header.instr_label.toolTip()
    window.select_track("Timpani")
    assert "2 note su 4 restano mute" in window.validation_label.text()
    assert window.silent_tracks_message().endswith("Timpani: 2 note mute (passa il mouse sulla traccia "
                                                   "per sapere quali)")
    window.project.get_track("Timpani").mute = True                 # una traccia muta non si segnala
    assert window.silent_tracks_message() == ""


# ---------------------------------------------------------- Ottava della traccia

def test_transpose_track_moves_boxes_and_keeps_the_patterns():
    from core.arrange import transpose_track
    from core.model import Clip
    project = parse_project_text("Tempo: 120 BPM\n\nPattern %colpi:\n  4: g*1 a*1 |\n\n"
                                 "Traccia Timpani [Timpani]:\n  4: c d e f |\n")
    track = project.get_track("Timpani")
    transpose_track(project, track, 12)                        # testo libero
    assert "*" in track.text or track.text.split()[1:] != ["c", "d", "e", "f"]
    track.clips = [Clip(name="A", text="%colpi", start_beat=0), Clip(name="B", text="4: d*2 r d*2 r |",
                                                                    start_beat=4)]
    transpose_track(project, track, 12)
    assert [c.text for c in track.clips] == ["%colpi+12", "4: d*3 r d*3 r |"]
    assert " ".join(map(str, project.patterns["colpi"].tokens)).count("*1") == 2      # pattern intatto


def test_octave_dialog_suggests_and_previews(tmp_path):
    from gui.track_octave_dialog import TrackOctaveDialog
    path = _sfz(tmp_path, "<region> lokey=36 hikey=60 sample=t.wav\n", "Timpani.sfz")
    project = _project(path, "g*1 a*1 d*2 d*2")
    dialog = TrackOctaveDialog(None, project, project.get_track("Timpani"))
    assert dialog.octaves.value() == 1 and "le suona tutte" in dialog.status.text()
    dialog.octaves.setValue(0)
    assert "2 note su 4 restano mute" in dialog.status.text()
    assert not dialog.buttons.button(dialog.buttons.StandardButton.Ok).isEnabled()   # 0: niente da fare
    dialog.octaves.setValue(-4)
    assert "escono dalle note possibili" in dialog.status.text()
    dialog.octaves.setValue(2)
    assert dialog.semitones() == 24


def test_window_moves_the_track_and_undo_brings_it_back(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QDialog
    for name in ("information", "warning"):
        monkeypatch.setattr(QMessageBox, name, staticmethod(lambda *a, **k: QMessageBox.Ok))
    from gui.main_window import MainWindow
    from gui.track_octave_dialog import TrackOctaveDialog
    path = _sfz(tmp_path, "<region> lokey=36 hikey=60 sample=t.wav\n", "Timpani.sfz")
    from core.project_io import save_project_file
    song = tmp_path / "brano.st"
    save_project_file(_project(path, "g*1 a*1 d*2 d*2"), str(song))
    window = MainWindow()
    window._load_and_apply_project(str(song))                 # come l'app: con la cronologia di Annulla
    window.select_track("Timpani")
    assert "(clic: cambia ottava)" in window.validation_label.text()
    monkeypatch.setattr(TrackOctaveDialog, "exec", lambda self: QDialog.Accepted)    # accetta la proposta (+1)
    window.jump_to_first_issue()                                # il clic sull'avviso
    assert window.project.get_track("Timpani").text.split()[1:5] == ["g*2", "a*2", "d*3", "d*3"]
    assert window.validation_label.text().startswith("✓")
    window.undo()
    assert window.project.get_track("Timpani").text.split()[1:5] == ["g*1", "a*1", "d*2", "d*2"]
