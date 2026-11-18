"""
Tonalita' del brano... (core.song_key, gui.song_key_dialog): tutto il brano si
sposta di semitoni, si prova ascoltando e cambia solo confermando.

Esecuzione:
    python3 -m pytest tests/test_song_key.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from core.model import AudioClip
from core.project_io import parse_project_text, project_to_text
from core.song_key import apply_transposition, transposed_song, warnings_for

_app = QApplication.instance() or QApplication([])

SONG = ("ST: 2.12\nTempo: 120 BPM\nTonalita: C\n\nPattern %Tema:\n  8: c*4 d*4 e*4 g*4\n\n"
        "Traccia Melodia [Pianoforte]:\n  4: @@\n\nTraccia Batteria [Batteria]:\n  4: kick snare kick snare\n")


def _song(body="c*4 %Tema e*4", text=SONG):
    return parse_project_text(text.replace("@@", body))


def _pitches(project, name="Melodia"):
    track = project.get_track(name)
    return [(e.start, e.duration, e.velocity, e.letter, e.octave)
            for e in track.parsed_events(project.patterns, meter=project.meter()) if e.kind == "note"]


def _midi(project, name="Melodia"):
    from core.chords import pitch_to_midi
    return [pitch_to_midi(e[3], e[4]) for e in _pitches(project, name)]


@pytest.mark.parametrize("semitones", [2, -3, 12])
def test_notes_move_and_the_original_stays(semitones):
    project = _song()
    before, text = _midi(project), project_to_text(project)
    moved = transposed_song(project, semitones)
    assert _midi(moved) == [n + semitones for n in before]
    assert project_to_text(project) == text
    assert moved.get_track("Batteria").text == project.get_track("Batteria").text


def test_key_and_key_changes_follow():
    project = _song(text=SONG.replace("Tonalita: C\n", "Tonalita: 1: C, 3: Am\n"))
    moved = transposed_song(project, 2)
    assert (moved.key, moved.key_changes) == ("D", [(1, "D"), (3, "Bm")])
    assert "Tonalita" in project_to_text(moved) and "Bm" in project_to_text(moved)


def test_patterns_stay_when_a_suffix_is_enough():
    moved = transposed_song(_song(), 2)
    assert moved.patterns["Tema"].tokens == _song().patterns["Tema"].tokens
    assert "%Tema+2" in moved.get_track("Melodia").text


@pytest.mark.parametrize("body", ["%Tema.step(1)", "%Tema.sequence(2,1)", "%Tema.thirds", "%Tema.invert(e*4).step(2)"])
def test_functions_on_the_scale_move_with_the_song(body):
    project = _song(body)
    before = _midi(project)
    moved = transposed_song(project, 2)
    assert _midi(moved) == [n + 2 for n in before]


@pytest.mark.parametrize("semitones", range(-6, 7))
def test_functions_on_the_scale_in_every_key(semitones):
    project = _song("%Tema.step(1) %Tema.sequence(3,-1) %Tema.thirds")
    assert _midi(transposed_song(project, semitones)) == [n + semitones for n in _midi(project)]


def test_functions_on_the_scale_without_a_declared_key():
    project = _song("%Tema.step(1)", SONG.replace("Tonalita: C\n", ""))
    assert _midi(transposed_song(project, 2)) == [n + 2 for n in _midi(project)]


def test_chords_harmony_key_mode_and_boxes():
    from core.arrangement import flatten_clips_to_text
    from core.model import Clip
    moved = transposed_song(_song("C Am7 $F key=G f*4 2C.arpeggio(up,8)"), 2)
    text = moved.get_track("Melodia").text
    assert "D " in text and "Bm7" in text and "$G" in text and "key=A" in text and ".arpeggio(up,8)" in text
    project = _song("c*4")
    track = project.get_track("Melodia")
    track.clips = [Clip(name="A", text="c*4 %Tema", start_beat=0.0)]
    track.text = flatten_clips_to_text(track.clips, project.patterns, 4, meter=project.meter())
    moved = transposed_song(project, -1)
    assert moved.get_track("Melodia").clips[0].text.startswith("b*3") and "%Tema-1" in moved.get_track("Melodia").text


def test_audio_clips_follow_without_touching_the_file():
    project = _song()
    track = project.add_track("Voce", "Pianoforte")
    track.audio_clips = [AudioClip(name="v", file="v.wav", transpose=23.5)]
    moved = transposed_song(project, 2)
    assert moved.get_track("Voce").audio_clips[0].transpose == 24.0
    assert project.get_track("Voce").audio_clips[0].transpose == 23.5


def test_refuses_what_leaves_the_midi_range_and_invalid_text():
    with pytest.raises(ValueError):
        transposed_song(_song("g*9"), 12)
    with pytest.raises(ValueError, match="Melodia"):
        transposed_song(_song("%Nessuno"), 2)


def test_warnings_before_confirming():
    project = _song("c*8")
    assert any("estensione" in w for w in warnings_for(project, transposed_song(project, 12), 12))
    project = _song()
    track = project.add_track("Voce", "Pianoforte")
    track.audio_clips = [AudioClip(name="v", file="v.wav")]
    assert any("audio" in w for w in warnings_for(project, transposed_song(project, 4), 4))
    assert not any("audio" in w for w in warnings_for(project, transposed_song(project, 1), 1))


class _Playback:
    def __init__(self):
        self.played, self.playing = [], False

    def play(self, project, start_offset_beats=0.0, **_kwargs):
        self.played.append((project, start_offset_beats))
        self.playing = True

    def stop(self):
        self.playing = False

    def is_playing(self):
        return self.playing


def test_dialog_tries_without_changing_the_song():
    from gui.song_key_dialog import SongKeyDialog
    project = _song()
    text = project_to_text(project)
    playback = _Playback()
    dialog = SongKeyDialog(None, project, playback, start_beat=8.0)
    assert dialog.key_label.text() == "C"
    assert not dialog.buttons.button(dialog.buttons.StandardButton.Ok).isEnabled()
    dialog.up_btn.click()
    dialog.up_btn.click()
    assert dialog.key_label.text() == "C → D"
    dialog.play_btn.click()
    played, start = playback.played[-1]
    assert played.key == "D" and start == 8.0
    dialog.down_btn.click()
    assert dialog.semitones.value() == 1 and dialog.key_label.text() == "C → Db"
    dialog.reject()
    assert not playback.playing and project_to_text(project) == text


def test_dialog_shows_a_refusal():
    from gui.song_key_dialog import SongKeyDialog
    dialog = SongKeyDialog(None, _song("g*9"), _Playback())
    dialog.semitones.setValue(12)
    assert dialog.status.text() and not dialog.buttons.button(dialog.buttons.StandardButton.Ok).isEnabled()
    assert not dialog.play_btn.isEnabled()


def test_window_applies_and_undo_brings_it_back(tmp_path, monkeypatch):
    from core.project_io import save_project_file
    from gui.main_window import MainWindow
    from gui.song_key_dialog import SongKeyDialog
    for name in ("information", "warning"):
        monkeypatch.setattr(QMessageBox, name, staticmethod(lambda *a, **k: QMessageBox.Ok))
    song = tmp_path / "brano.st"
    save_project_file(_song(), str(song))
    window = MainWindow()
    window._load_and_apply_project(str(song))
    window.select_track("Melodia")

    def accept(dialog):
        dialog.semitones.setValue(2)
        dialog.accept()
        return QDialog.Accepted
    monkeypatch.setattr(SongKeyDialog, "exec", accept)
    window.change_song_key()
    assert window.project.key == "D" and "%Tema+2" in window.editor.toPlainText()
    window.undo()
    assert window.project.key == "C" and "%Tema+2" not in window.project.get_track("Melodia").text


def test_apply_keeps_the_objects_of_the_window():
    project = _song()
    patterns, track = project.patterns, project.get_track("Melodia")
    apply_transposition(project, transposed_song(project, 2))
    assert project.patterns is patterns and project.get_track("Melodia") is track and project.key == "D"
