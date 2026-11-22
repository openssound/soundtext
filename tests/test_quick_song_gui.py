"""«Nuovo brano in 60 secondi» sul computer (gui.quick_song_dialog, core.quicksong): la finestra compone, ascolta e, con
Crea il brano, il brano diventa il progetto (da salvare)."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")


@pytest.fixture
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _dialog(app, monkeypatch):
    from gui.quick_song_dialog import QuickSongDialog
    dlg = QuickSongDialog()
    monkeypatch.setattr(dlg._playback, "play", lambda project, *a, **k: setattr(dlg, "played", project))
    monkeypatch.setattr(dlg._playback, "stop", lambda *a, **k: None)
    return dlg


def test_the_dialog_lists_every_genre_and_only_the_moods_of_the_genre(app, monkeypatch):
    from core.quicksong import GENRES, GENRES_DATA
    dlg = _dialog(app, monkeypatch)
    assert dlg.genre_list.count() == len(GENRES) == 25
    for row in (0, 4, 24):
        dlg.genre_list.setCurrentRow(row)
        genre = GENRES[row]
        assert [dlg.mood_combo.itemData(i) for i in range(dlg.mood_combo.count())] == list(GENRES_DATA[genre]["moods"])
    assert dlg.duration_combo.currentData() == 60
    assert not dlg.buttons.button(dlg.buttons.StandardButton.Ok).isEnabled()           # niente da creare prima di comporre


def test_compose_makes_a_valid_song_and_listens_to_it(app, monkeypatch):
    dlg = _dialog(app, monkeypatch)
    dlg.genre_list.setCurrentRow(4)
    dlg.duration_combo.setCurrentIndex(0)                                              # 15 secondi
    dlg.compose()
    assert dlg.song and dlg.song["genre"] == "jazz" and dlg.song["text"].startswith("//")
    assert dlg.played is not None and dlg.played.tracks
    assert dlg.buttons.button(dlg.buttons.StandardButton.Ok).isEnabled()
    assert "BPM" in dlg.summary.text() and str(dlg.song["seed"]) in dlg.summary.text()


def test_details_and_seed_give_the_same_song(app, monkeypatch):
    dlg = _dialog(app, monkeypatch)
    dlg.detail_check.setChecked(True)
    dlg.seed_spin.setValue(12345)
    dlg.key_combo.setCurrentIndex(dlg.key_combo.findData("Am"))
    dlg.bpm_spin.setValue(90)
    dlg.duration_combo.setCurrentIndex(0)
    dlg.compose(listen=False)
    first = dlg.song
    dlg.compose(listen=False)
    assert dlg.song["text"] == first["text"] and first["key"] == "Am" and first["bpm"] == 90
    dlg.chords_edit.setText("Dm G C")
    dlg.compose(listen=False)
    assert dlg.song["text"] != first["text"]


def test_another_and_surprise_change_the_song_and_the_menu_command_replaces_the_project(app, monkeypatch):
    from PySide6.QtWidgets import QDialog
    from gui.main_window import MainWindow
    from gui.quick_song_dialog import QuickSongDialog
    monkeypatch.setattr(QuickSongDialog, "_listen", lambda self: None)
    dlg = QuickSongDialog()
    dlg.duration_combo.setCurrentIndex(0)
    dlg.compose(listen=False)
    seed = dlg.song["seed"]
    dlg._another()
    assert dlg.song["seed"] != seed
    dlg._surprise()
    assert dlg.song is not None and dlg.song["seconds"] > 0

    w = MainWindow()

    def fake_exec(d):
        d.genre_list.setCurrentRow(1)
        d.duration_combo.setCurrentIndex(0)
        d.compose(listen=False)
        d.accept()
        return QDialog.Accepted

    monkeypatch.setattr(QuickSongDialog, "exec", fake_exec)
    monkeypatch.setattr(QuickSongDialog, "_listen", lambda self: None)
    w.new_quick_song()
    assert w._quick_song_dialog.song["genre"] == "rock"
    assert len(w.project.tracks) >= 4 and w.project.name == w._quick_song_dialog.song["name"]
    assert any(t.clips for t in w.project.tracks)                                    # box, uno per sezione
    assert w._dirty                                                                  # un brano nuovo da salvare


def test_arrange_dialog_lists_every_section_and_says_where_the_chords_are_missing(app):
    from core.project_io import parse_project_text
    from core.quicksong import quick_song
    from gui.arrange_dialog import ArrangeDialog
    made = quick_song({"genre": "pop", "mood": "allegra", "duration": 60, "seed": 3, "variety": 0})
    project = parse_project_text(made["text"], made["name"])
    dlg = ArrangeDialog(None, project)
    names = [dlg.table.item(r, 0).text() for r in range(dlg.table.rowCount())]
    assert names == [s["name"] for s in made["sections"]]                                   # tutte, anche l'Intro
    assert dlg.table.item(0, 3).text() == "senza accordi" and dlg.table.item(names.index("Ritornello"), 3).text() == "della traccia scelta"
    dlg.accept()
    assert dlg.parts() and dlg.parts()["drums"]
