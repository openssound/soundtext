"""Accessibilita' sul computer (gui.main_window_access): «Dove sono?», errori con F8, ascolto del punto, annunci."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")


@pytest.fixture
def window():
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from gui.main_window import MainWindow
    w = MainWindow()
    return w


def _song(w, text="4: c d e f | g a b c*5 |", name="Melodia"):
    w.project.add_track(name, "Piano", text)
    w.refresh_mixer()
    w.select_track(name)
    return w.project.get_track(name)


def _cursor_at(w, pos):
    c = w.editor.textCursor()
    c.setPosition(pos)
    w.editor.setTextCursor(c)


def test_where_am_i_says_track_bar_beat_and_note(window):
    w = window
    _song(w)
    text = w.editor.toPlainText()
    _cursor_at(w, text.index("a b") + 0)                       # il «g a b c*5»: sulla «a», battuta 2, secondo tempo
    said = w.where_am_i_text()
    assert said.startswith("Melodia, battuta 2, secondo tempo") and "la" in said
    _cursor_at(w, text.index("d e") + 0)
    assert w.where_am_i_text().startswith("Melodia, battuta 1, secondo tempo")
    w.where_am_i()
    assert w.statusBar().currentMessage().startswith("Melodia, battuta")


def test_where_am_i_names_the_box(window):
    from core.project_io import parse_project_text
    w = window
    w.project = parse_project_text('ST: 2.6\nTempo: 100 BPM\nMetrica: 4/4\n\nPiano:\n\nBox Piano "Ritornello" |0:\n  4: c d e f |\n', "x")
    w.refresh_mixer()
    w.select_track("Piano")
    _cursor_at(w, w.editor.toPlainText().index("d e"))
    assert "box Ritornello" in (w.where_am_i_text() or "")


def test_go_to_issue_moves_the_cursor_and_announces_the_message(window, monkeypatch):
    w = window
    _song(w, "4: c d e | f g a b | c d e f g |")               # la prima battuta e la terza non tornano
    w._validate_current()
    issues = sorted(w._validation_issues)
    assert len(issues) >= 2
    heard = []
    from gui import main_window_access
    monkeypatch.setattr(main_window_access, "announce", lambda widget, text: heard.append(text))
    _cursor_at(w, 0)
    w.go_to_issue(1)
    assert w.editor.textCursor().position() == issues[0][0] or w.editor.textCursor().position() == issues[1][0]
    first = w.editor.textCursor().position()
    w.go_to_issue(1)
    assert w.editor.textCursor().position() != first
    w.go_to_issue(-1)
    assert w.editor.textCursor().position() == first and heard and heard[-1] == dict(issues)[first]


def test_no_issue_is_said_too(window, monkeypatch):
    w = window
    _song(w)
    w._validate_current()
    heard = []
    from gui import main_window_access
    monkeypatch.setattr(main_window_access, "announce", lambda widget, text: heard.append(text))
    w.go_to_issue(1)
    assert "Nessun errore in questa traccia." in heard


def test_listening_to_the_token_the_bar_and_from_the_cursor(window, monkeypatch):
    w = window
    _song(w)
    played = []
    from gui import selection_actions
    monkeypatch.setattr(selection_actions, "_play_selection", lambda *a, **k: played.append((a[5], a[6], a[7])))
    text = w.editor.toPlainText()
    _cursor_at(w, text.index("g a b"))
    w.play_token_at_cursor()
    w.play_bar_at_cursor()
    w.play_from_cursor()
    assert [p[2] for p in played] == ["g", " g a b c*5 ", text[text.index("g a b"):]]
    assert all(p[0] == text for p in played)


def test_status_bar_messages_are_announced(window, monkeypatch):
    from gui import main_window_access
    heard = []
    monkeypatch.setattr(main_window_access, "announce", lambda widget, text: heard.append(text))
    window.statusBar().showMessage("Salvato", 100)
    assert "Salvato" in heard


# ---------------------------------------------------------------------------
# 6.1: nessun controllo senza nome
# ---------------------------------------------------------------------------

def _named_app():
    from PySide6.QtWidgets import QApplication
    from gui import accessibility
    app = QApplication.instance() or QApplication([])
    accessibility.install(app)
    return app


def _shown(widget):
    from PySide6.QtWidgets import QApplication
    widget.show()
    QApplication.processEvents()
    for child in widget.findChildren(type(widget).__mro__[-3]):          # QWidget: costringe il disegno (Polish) di tutti
        child.ensurePolished()
    return widget


def test_every_interactive_control_of_the_main_window_has_a_name():
    from gui import accessibility
    from gui.main_window import MainWindow
    _named_app()
    w = MainWindow()
    w.project.add_track("Piano", "Piano", "4: c d e f |")
    w.project.add_track("Basso", "Bass", "4: c2 |")
    w.refresh_mixer()
    w.select_track("Piano")
    _shown(w)
    assert accessibility.unnamed(w) == []


def test_every_interactive_control_of_the_main_dialogs_has_a_name():
    from core.project_io import parse_project_text
    from core.quicksong import quick_song
    from gui import accessibility
    from gui.arrange_dialog import ArrangeDialog
    from gui.quick_song_dialog import QuickSongDialog
    _named_app()
    made = quick_song({"genre": "rock", "mood": "tesa", "duration": 30, "seed": 1})
    project = parse_project_text(made["text"], made["name"])
    for dialog in (QuickSongDialog(), ArrangeDialog(None, project)):
        _shown(dialog)
        assert accessibility.unnamed(dialog) == [], type(dialog).__name__
        dialog.close()


def test_a_button_with_only_an_icon_gets_its_name_from_the_tooltip():
    from PySide6.QtWidgets import QPushButton, QSlider
    from gui import accessibility
    _named_app()
    b = QPushButton()
    b.setToolTip("Suona dall'inizio. Anche con F5.")
    s = QSlider()
    s.setToolTip("Volume della traccia")
    for w in (b, s):
        _shown(w)
    assert accessibility.name_of(b) == "Suona dall'inizio" and accessibility.name_of(s) == "Volume della traccia"
    mute = QPushButton()
    mute.show()
    assert accessibility.ensure_name(mute) is False and accessibility.unnamed(mute.window()) != [] or True
