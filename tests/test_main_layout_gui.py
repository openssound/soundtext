"""
Test GUI (offscreen) della nuova disposizione della finestra principale:
barra dei comandi in gruppi (trasporto a icone, blocco Brano, vista
Struttura/Testo, Master) con l'avanzamento su una riga propria, e mixer
dentro le righe della vista Struttura brano (gui.track_header).

Esecuzione:
    python3 -m pytest tests/test_main_layout_gui.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow
from gui.track_header import TrackHeaderWidget

_app = QApplication.instance() or QApplication([])


def _window(width=1200, height=720, tracks=(("Piano", "Piano"),), audio=("Voce",)):
    w = MainWindow()
    w.resize(width, height)
    w.show()
    for name, instrument in tracks:
        w.project.add_track(name, instrument, "")
    for name in audio:
        w.project.add_audio_track(name)
    w.history.reset(w.project)
    w.refresh_mixer()
    _app.processEvents()
    return w


def _menu_texts(open_menu_fn):
    captured = {}

    def grab():
        menu = QApplication.activePopupWidget()
        if menu is not None:
            captured["actions"] = [a.text() for a in menu.actions() if a.text()]
            menu.close()

    QTimer.singleShot(50, grab)
    open_menu_fn()
    return captured.get("actions", [])


# --------------------------------------------------------------- barra dei comandi

def test_toolbar_fits_a_1200_px_window():
    w = _window(width=1200)
    for widget in (w.master_vol_slider, w.master_vol_value_label, w.view_text_btn, w.metronome_checkbox):
        assert widget.isVisible()
        right = widget.mapTo(w, QPoint(widget.width(), 0)).x()
        assert right <= w.width()
    # l'avanzamento ha una riga tutta sua, larga quasi quanto la finestra
    assert w.playback_progress.isVisible() and w.playback_progress.width() > 900


def test_view_buttons_switch_view_and_tracks_column():
    w = _window()
    assert w.arrangement_action.isChecked() and w.view_structure_btn.isChecked()
    assert not w.mixer_panel.isVisible()                 # Struttura: testate nelle righe
    w.view_text_btn.click()
    assert not w.arrangement_action.isChecked()
    assert w.mixer_panel.isVisible()                     # Testo: serve per scegliere la traccia
    w.view_structure_btn.click()
    assert w.arrangement_action.isChecked() and not w.mixer_panel.isVisible()


def test_no_separate_mixer_button_or_menu_item():
    w = _window()
    assert not hasattr(w, "mixer_panel_action") and not hasattr(w, "mixer_btn")
    view_menu = next(a.menu() for a in w.menuBar().actions() if a.text() == "&Vista")
    assert all("mixer" not in a.text().lower() for a in view_menu.actions())


def test_text_view_column_uses_the_same_headers_as_the_structure_view():
    from gui.arrangement_view import HEADER_WIDTH, ROW_HEIGHT
    w = _window()
    w.view_text_btn.click()
    text_headers = w.track_headers
    structure_headers = w.arrangement_view.canvas.header_widgets
    assert list(text_headers) == list(structure_headers) == ["Piano", "Voce"]
    for name, header in text_headers.items():
        assert isinstance(header, TrackHeaderWidget)
        assert (header.width(), header.height()) == (HEADER_WIDTH, ROW_HEIGHT)
        other = structure_headers[name]
        assert header.name_label.text() == other.name_label.text()
        assert header.instr_label.text() == other.instr_label.text()
    assert text_headers["Voce"].record_btn is not None
    # La colonna e' larga quanto le testate: il resto va all'editor.
    assert w.mixer_panel.width() < HEADER_WIDTH + 40


def test_transport_buttons(monkeypatch):
    w = _window()
    w._playback_paused_beat = 12.0
    w.rewind_btn.click()
    assert w._playback_paused_beat == 0.0

    calls = []
    monkeypatch.setattr(w, "record_into_audio_track", lambda *a, **k: calls.append(a))
    w.record_btn.click()
    assert calls == [()]

    w._set_play_pause_button(playing=True)
    assert w.play_pause_btn.text() == "Pausa"
    w._set_play_pause_button(playing=False)
    assert w.play_pause_btn.text() == "Play"
    assert not w.play_pause_btn.icon().isNull()


def test_metronome_and_humanize_keep_their_interface():
    w = _window()
    w.metronome_checkbox.setChecked(True)
    assert w.metronome_checkbox.isChecked()
    playback_menu = next(a.menu() for a in w.menuBar().actions() if a.text() == "&Riproduzione")
    assert w.humanize_checkbox in playback_menu.actions()


def test_theme_switch_redraws_icons_and_headers():
    w = _window()
    w._apply_theme("light")
    w._apply_theme("dark")
    assert set(w.arrangement_view.canvas.header_widgets) == {"Piano", "Voce"}


# --------------------------------------------------------------- testate traccia

def test_one_header_per_track_with_record_only_on_audio_tracks():
    w = _window(tracks=(("Piano", "Piano"), ("Basso", "Bass")), audio=("Voce",))
    headers = w.arrangement_view.canvas.header_widgets
    assert list(headers) == ["Piano", "Basso", "Voce"]
    assert all(isinstance(h, TrackHeaderWidget) for h in headers.values())
    assert headers["Voce"].record_btn is not None and headers["Piano"].record_btn is None
    assert "Audio" in headers["Voce"].instr_label.text()


def test_header_mute_solo_volume_change_the_track_and_the_text_view_header():
    w = _window()
    header = w.arrangement_view.canvas.header_widgets["Piano"]
    header.mute_btn.click()
    header.solo_btn.click()
    header.vol_knob.setValue(140)
    track = w.project.get_track("Piano")
    assert (track.mute, track.solo, track.volume) == (True, True, 140)
    other = w.track_headers["Piano"]
    assert other.mute_btn.isChecked() and other.solo_btn.isChecked() and other.vol_knob.value() == 140
    assert w.history.can_undo()


def test_text_view_header_changes_update_the_structure_header():
    w = _window()
    w.view_text_btn.click()
    w.track_headers["Voce"].mute_btn.click()
    w.track_headers["Voce"].vol_knob.setValue(60)
    header = w.arrangement_view.canvas.header_widgets["Voce"]
    assert header.mute_btn.isChecked() and header.vol_knob.value() == 60


def test_header_pan_knob_changes_the_track_and_the_text_view_header():
    w = _window()
    header = w.arrangement_view.canvas.header_widgets["Piano"]
    header.pan_knob.setValue(20)
    assert w.project.get_track("Piano").pan == 20
    assert w.track_headers["Piano"].pan_knob.value() == 20
    assert "L" in header.pan_knob.toolTip()
    assert w.history.can_undo()


def test_text_view_pan_updates_the_structure_header_knob():
    w = _window()
    w.view_text_btn.click()
    w.track_headers["Voce"].pan_knob.setValue(100)
    assert w.arrangement_view.canvas.header_widgets["Voce"].pan_knob.value() == 100


def test_header_keeps_its_size_with_knobs_and_long_names():
    w = _window()
    header = w.arrangement_view.canvas.header_widgets["Piano"]
    size = header.size()
    header.track.name = "Un nome di traccia molto molto lungo"
    header.sync_from_track()
    assert header.size() == size
    assert header.name_label.text().endswith("…")
    assert header.name_label.toolTip() == header.track.name
    # Le manopole stanno dentro la testata, alla sua destra.
    for knob in (header.vol_knob, header.pan_knob):
        assert knob.geometry().right() < header.width()
        assert knob.geometry().bottom() < header.height()


def test_header_click_selects_the_track_and_double_click_opens_rename(monkeypatch):
    w = _window()
    header = w.arrangement_view.canvas.header_widgets["Voce"]
    QTest.mouseClick(header, Qt.LeftButton, Qt.NoModifier, QPoint(150, 8))
    assert w.current_track_name == "Voce"
    assert header._active and not w.arrangement_view.canvas.header_widgets["Piano"]._active

    opened = []
    monkeypatch.setattr(w, "_open_edit_dialog_for", lambda name: opened.append(name))
    QTest.mouseDClick(header, Qt.LeftButton, Qt.NoModifier, QPoint(150, 8))
    assert opened == ["Voce"]


def test_header_menu_has_all_track_actions(monkeypatch):
    w = _window()
    view = w.arrangement_view
    midi = _menu_texts(lambda: view.canvas.header_widgets["Piano"]._open_menu())
    for label in ("Suona con la tastiera...", "Importa MIDI...", "Importa audio → note...",
                  "Nome e strumento...", "Esporta MIDI (solo questa)...", "Esporta WAV (solo questa)...",
                  "Rimuovi traccia"):
        assert label in midi
    audio = _menu_texts(lambda: view.canvas.header_widgets["Voce"]._open_menu())
    assert audio[:2] == ["● Registra...", "Importa file audio..."] and "Rimuovi traccia" in audio

    removed = []
    monkeypatch.setattr(w, "remove_track", lambda: removed.append(w.current_track_name))
    view._remove_track("Voce")
    assert removed == ["Voce"]


def _add_menu_entries(w, button):
    menu = button.menu()
    menu.aboutToShow.emit()
    return [(a.text(), a.isEnabled()) for a in menu.actions() if a.text() and not a.isSeparator()]


def test_add_track_button_offers_both_kinds_and_follows_the_last_row():
    w = _window()
    canvas = w.arrangement_view.canvas
    texts = [t for t, _ in _add_menu_entries(w, canvas.add_track_btn)]
    assert "Traccia con strumento..." in texts and "Traccia audio (voce, chitarra, tastiera)..." in texts
    last = canvas.header_widgets["Voce"]
    assert canvas.add_track_btn.y() >= last.y() + last.height()


def test_headers_follow_vertical_scrolling():
    w = _window(height=420, tracks=[(f"Piano {i}", "Piano") for i in range(12)], audio=())
    canvas = w.arrangement_view.canvas
    first = canvas.header_widgets["Piano 0"]
    y_before = first.y()
    canvas.verticalScrollBar().setValue(canvas.verticalScrollBar().maximum())
    _app.processEvents()
    assert first.y() < y_before
    row_top_in_view = canvas.mapFromScene(0, canvas.row_ys["Piano 11"]).y()
    assert canvas.header_widgets["Piano 11"].y() == row_top_in_view - canvas.header_panel.y()


def test_renaming_from_a_header_rebuilds_headers_safely(monkeypatch):
    from PySide6.QtWidgets import QInputDialog
    w = _window()
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("Voce solista", True)))
    header = w.arrangement_view.canvas.header_widgets["Voce"]
    QTest.mouseDClick(header, Qt.LeftButton, Qt.NoModifier, QPoint(150, 8))
    _app.processEvents()
    assert "Voce solista" in w.arrangement_view.canvas.header_widgets


# --------------------------------------------------------------- menu "+ Aggiungi traccia" e menu ⋯

def test_add_menu_lists_generators_and_disables_the_ones_needing_chords():
    w = _window(tracks=(), audio=())
    entries = dict(_add_menu_entries(w, w.arrangement_view.canvas.add_track_btn))
    assert entries["Batteria..."] and entries["Giro armonico..."] and entries["Traccia da un file MIDI..."]
    assert entries["Basso dagli accordi...  (serve un giro di accordi)"] is False
    assert entries["Accompagnamento o riff...  (serve un giro di accordi)"] is False
    w.project.add_track("Piano", "Piano", "4: Am F C G")
    entries = dict(_add_menu_entries(w, w.mixer_add_track_btn))    # stesso menu anche nel mixer a colonna
    assert entries["Basso dagli accordi..."] and entries["Accompagnamento o riff..."]


class _FakeGenerator:
    """Sostituisce un dialogo di generazione: registra i parametri e
    restituisce un testo fisso."""
    seen = []

    def __init__(self, parent, **kwargs):
        _FakeGenerator.seen.append(kwargs)

    def exec(self):
        return 1

    def result_text(self):
        return "4: c d e f"


def test_generated_track_is_created_only_when_confirmed(monkeypatch):
    import gui.main_window_mixer as mixer
    w = _window(tracks=(), audio=())
    _FakeGenerator.seen = []
    monkeypatch.setattr(mixer, "DrumGenerateDialog", _FakeGenerator)
    w.add_generated_track("drums")
    track = w.project.get_track("Batteria")
    assert track.instrument_name == "Drums" and [c.name for c in track.clips] == ["Groove"]
    assert _FakeGenerator.seen[0]["track_name"] == "Batteria"
    assert w.current_track_name == "Batteria"

    class Cancelled(_FakeGenerator):
        def exec(self):
            return 0

    monkeypatch.setattr(mixer, "ChordProgressionDialog", Cancelled)
    w.add_generated_track("progression")
    assert [t.name for t in w.project.tracks] == ["Batteria"]


def test_generated_track_in_text_view_is_free_text(monkeypatch):
    import gui.main_window_mixer as mixer
    from PySide6.QtWidgets import QInputDialog
    w = _window(tracks=(("Piano", "Piano"),), audio=())
    w.project.get_track("Piano").text = "4: Am F C G"
    w.view_text_btn.click()
    monkeypatch.setattr(mixer, "MelodyGenerateDialog", _FakeGenerator)
    monkeypatch.setattr(QInputDialog, "getItem", staticmethod(lambda *a, **k: ("Trumpet", True)))
    _FakeGenerator.seen = []
    w.add_generated_track("melody")
    track = w.project.get_track("Trumpet")
    assert track.clips == [] and track.text == "4: c d e f"
    assert _FakeGenerator.seen[0]["polyphonic"] is False


def test_tracks_column_has_one_add_button_and_a_menu_per_header():
    from PySide6.QtWidgets import QAbstractButton
    w = _window()
    w.view_text_btn.click()
    labels = [b.text().strip() for b in w.mixer_panel.findChildren(QAbstractButton)]
    assert labels.count("Aggiungi traccia") == 1
    # Come nella vista Struttura: subito sotto l'ultima testata.
    last = w.track_headers["Voce"]
    assert w.mixer_add_track_btn.y() >= last.y() + last.height()
    assert w.mixer_add_track_btn.y() < last.y() + last.height() + 30
    for gone in ("Rimuovi traccia selezionata", "Esporta MIDI (solo questa)", "Importa MIDI (in questa)",
                 "Suona con la tastiera (in questa)", "+ Aggiungi traccia audio"):
        assert gone not in labels
    assert all(header.menu_btn is not None for header in w.track_headers.values())


def test_header_menu_on_free_text_track_writes_into_the_text(monkeypatch):
    w = _window(tracks=(("Piano", "Piano"),), audio=())
    w.project.get_track("Piano").text = "4: c d e f"
    w.view_text_btn.click()
    header = w.track_headers["Piano"]
    texts = _menu_texts(lambda: header.menu_btn.click())
    assert "Genera giro armonico..." in texts            # nel brano non ci sono ancora accordi
    assert "Suona con la tastiera..." in texts and "Rimuovi traccia" in texts

    called = []
    monkeypatch.setattr(w, "play_keyboard_into_selected_track", lambda: called.append(w.current_track_name))

    def pick():
        menu = QApplication.activePopupWidget()
        menu.setActiveAction(next(a for a in menu.actions() if a.text() == "Suona con la tastiera..."))
        QTest.keyClick(menu, Qt.Key_Return)

    QTimer.singleShot(50, pick)
    w.show_track_actions_menu("Piano", header.mapToGlobal(QPoint(0, 0)))
    assert called == ["Piano"]


def test_first_box_on_a_free_text_track_keeps_the_text(monkeypatch):
    from PySide6.QtWidgets import QInputDialog
    w = _window(tracks=(("Piano", "Piano"),), audio=())
    track = w.project.get_track("Piano")
    track.text = "4: c d e f"
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("Nuovo", True)))
    w.arrangement_view._create_box_from_recorded_text("Piano", 0.0, "4: g a b c")
    assert [(c.name, c.text, c.start_beat) for c in track.clips] == [("Piano", "4: c d e f", 0.0),
                                                                    ("Nuovo", "4: g a b c", 4.0)]
    assert "c d e f" in track.text and "g a b c" in track.text


# --------------------------------------------------------------- un solo Play, suggerimenti

class _FakePreview:
    def __init__(self):
        self.playing = False

    def is_playing(self):
        return self.playing

    def play(self, project, only_audible=True, start_offset_beats=0.0, on_audio_started=None):
        self.playing = True

    def stop(self):
        self.playing = False


def _window_with_box():
    from core.model import Clip
    w = _window(tracks=(("Piano", "Piano"),), audio=())
    clip = Clip(name="A", text="4: c d e f", start_beat=0.0)
    w.project.get_track("Piano").clips.append(clip)
    w.refresh_mixer()
    view = w.arrangement_view
    view._preview_playback = _FakePreview()
    view.select_box("Piano", clip)
    return w, view


def test_no_preview_buttons_or_fixed_instructions_above_the_canvas():
    from PySide6.QtWidgets import QLabel, QPushButton
    w = _window()
    view = w.arrangement_view
    assert not [b for b in view.findChildren(QPushButton) if "anteprima" in b.text()]
    assert not [l for l in view.findChildren(QLabel) if "trascina un box" in l.text()]
    assert view.canvas.help_btn.text().startswith("?") and "Shift+Spazio" in view.canvas.help_btn.toolTip()
    playback_menu = next(a.menu() for a in w.menuBar().actions() if a.text() == "&Riproduzione")
    assert view.preview_action in playback_menu.actions()


def test_shift_space_plays_the_selected_box_only_in_the_structure_view():
    w, view = _window_with_box()
    view.canvas.setFocus()
    QTest.keyClick(view.canvas.viewport(), Qt.Key_Space, Qt.ShiftModifier)
    assert view._preview_playback.is_playing()
    assert view.preview_action.text() == "Pausa ascolto del box"
    QTest.keyClick(view.canvas.viewport(), Qt.Key_Space, Qt.ShiftModifier)
    assert not view._preview_playback.is_playing()

    # nell'editor di testo Shift+Spazio resta uno spazio
    w.project.get_track("Piano").clips = []
    w.project.get_track("Piano").text = "4: c"
    w.view_text_btn.click()
    w.select_track("Piano")
    w.editor.setFocus()
    from PySide6.QtGui import QTextCursor
    w.editor.moveCursor(QTextCursor.End)
    QTest.keyClick(w.editor, Qt.Key_Space, Qt.ShiftModifier)
    assert w.editor.toPlainText().endswith(" ")
    assert not view._preview_playback.is_playing()


def test_main_stop_and_play_also_stop_the_box_preview(monkeypatch):
    w, view = _window_with_box()
    view._toggle_play_selected()
    assert view._preview_playback.is_playing()
    w.stop()
    assert not view._preview_playback.is_playing()
    assert view.preview_action.text() == "Ascolta il box selezionato"

    view._toggle_play_selected()
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))  # "synth non trovato"
    monkeypatch.setattr(w.playback, "play", lambda *a, **k: True)
    w.play()
    assert not view._preview_playback.is_playing()
    w.stop()


def test_empty_rows_show_a_hint():
    from core.model import AudioClip, Clip
    from gui import arrangement_view as av
    w = _window(tracks=(("Piano", "Piano"), ("Basso", "Bass"), ("Organo", "Piano")), audio=("Voce", "Gtr"))
    w.project.get_track("Basso").clips.append(Clip(name="B", text="4: c", start_beat=0.0))
    w.project.get_track("Organo").text = "4: c e g"
    w.project.get_track("Gtr").audio_clips.append(AudioClip("x", "/manca.wav", 0.0))
    canvas = w.arrangement_view.canvas
    assert canvas._row_hint("Piano") == av.EMPTY_ROW_HINT
    assert canvas._row_hint("Basso") is None
    assert canvas._row_hint("Organo") == av.FREE_TEXT_ROW_HINT
    assert canvas._row_hint("Voce") == av.EMPTY_AUDIO_ROW_HINT
    assert canvas._row_hint("Gtr") is None
    canvas.viewport().grab()   # disegna i suggerimenti senza errori


# --------------------------------------------------------------- scorciatoie e zoom

def _window_with_audio_clip(tmp_path, start_beat=0.0, seconds=2.0):
    import numpy as np
    from core.audio_tracks import AUDIO_SAMPLE_RATE, write_wav
    from core.model import AudioClip
    path = str(tmp_path / "c.wav")
    write_wav(path, np.zeros((int(AUDIO_SAMPLE_RATE * seconds), 1), np.float32), AUDIO_SAMPLE_RATE, bits=16)
    w = _window(tracks=(), audio=("Voce",))
    clip = AudioClip("C", path, start_beat)
    w.project.get_track("Voce").audio_clips.append(clip)
    w.history.reset(w.project)
    w.refresh_mixer()
    w.arrangement_view.select_box("Voce", clip)
    w.arrangement_view.canvas.setFocus()
    _app.processEvents()
    return w, clip


def test_space_plays_in_structure_view_but_types_in_the_editor(monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    w = _window()
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(w.playback, "play", lambda *a, **k: True)
    w.arrangement_view.canvas.setFocus()
    QTest.keyClick(w.arrangement_view.canvas.viewport(), Qt.Key_Space)
    assert w.play_pause_btn.text() == "Pausa"
    w.stop()

    w.project.get_track("Piano").text = "4: c"
    w.view_text_btn.click()
    w.select_track("Piano")
    w.editor.setFocus()
    from PySide6.QtGui import QTextCursor
    w.editor.moveCursor(QTextCursor.End)
    QTest.keyClick(w.editor, Qt.Key_Space)
    QTest.keyClick(w.editor, Qt.Key_R)
    assert w.editor.toPlainText().endswith(" r")
    assert w.play_pause_btn.text() == "Play"


def test_r_records_in_structure_view(monkeypatch, tmp_path):
    w, _clip = _window_with_audio_clip(tmp_path)
    calls = []
    monkeypatch.setattr(w, "record_into_audio_track", lambda *a, **k: calls.append(a))
    QTest.keyClick(w.arrangement_view.canvas.viewport(), Qt.Key_R)
    assert calls == [()]


def test_delete_duplicate_and_split_the_selected_box(tmp_path):
    w, clip = _window_with_audio_clip(tmp_path, seconds=2.0)       # 4 beat a 120 BPM
    viewport = w.arrangement_view.canvas.viewport()
    track = w.project.get_track("Voce")

    QTest.keyClick(viewport, Qt.Key_D, Qt.ControlModifier)
    assert sorted(c.start_beat for c in track.audio_clips) == [0.0, 4.0]

    w._playback_paused_beat = 2.0                                   # testina a meta' della prima clip
    QTest.keyClick(viewport, Qt.Key_S)
    assert sorted((c.start_beat, c.trim_start, c.trim_end) for c in track.audio_clips) == \
        [(0.0, 0.0, 1.0), (2.0, 1.0, 0.0), (4.0, 0.0, 0.0)]

    QTest.keyClick(viewport, Qt.Key_Delete)
    assert sorted(c.start_beat for c in track.audio_clips) == [2.0, 4.0]
    assert w.arrangement_view.selected_clip is None
    w.undo()
    assert len(w.project.get_track("Voce").audio_clips) == 3


def test_ctrl_wheel_and_menu_zoom_change_the_horizontal_scale(tmp_path):
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QWheelEvent
    import gui.arrangement_view as av
    w, clip = _window_with_audio_clip(tmp_path, seconds=2.0)
    view = w.arrangement_view
    canvas = view.canvas

    def width():
        from gui.arrangement_view import AudioBoxItem
        return next(i for i in canvas._scene.items() if isinstance(i, AudioBoxItem)).rect().width()

    try:
        assert width() == pytest.approx(4 * 24)
        pos = QPointF(400, 100)
        event = QWheelEvent(pos, canvas.viewport().mapToGlobal(pos.toPoint()), QPoint(0, 0), QPoint(0, 120),
                            Qt.NoButton, Qt.ControlModifier, Qt.NoScrollPhase, False)
        canvas.wheelEvent(event)
        assert av.PX_PER_BEAT == pytest.approx(30.0)
        assert width() == pytest.approx(4 * 30)
        view.zoom_out()
        view.zoom_out()
        assert av.PX_PER_BEAT == pytest.approx(19.2)
        view.set_zoom(1000)
        assert av.PX_PER_BEAT == av.MAX_PX_PER_BEAT
    finally:
        view.zoom_reset()
    assert av.PX_PER_BEAT == 24


# --------------------------------------------------------------- ricerca comandi


def test_palette_finds_menu_commands_ignoring_accents_and_case():
    from gui.command_palette import collect_commands, rank_commands
    w = _window()
    commands = collect_commands(w.menuBar())
    titles = [c.title for c in commands]
    assert "Mix audio (WAV)..." in titles and "Ingrandisci (zoom)" in titles
    # le voci dei sottomenu si trovano anche per percorso: "esporta" e' il sottomenu
    first = rank_commands(commands, "esporta")[0]
    assert first.title == "Mix audio (WAV)..." and first.path == "Progetto › Esporta"
    assert [(c.path, c.title) for c in rank_commands(commands, "esporta midi")][:2] == \
        [("Progetto › Esporta", "MIDI..."), ("Traccia › Esporta questa traccia", "MIDI...")]
    assert any(c.title == "Analizza tonalità..." for c in rank_commands(commands, "TONALITA"))
    assert [c.title for c in rank_commands(commands, "registra traccia audio")][:1] == \
        ["Registra nella traccia audio..."]
    reg = next(c for c in commands if c.title == "Registra nella traccia audio...")
    # come la mostra il sistema: "Ctrl+R" su Linux e Windows, "⌘R" su macOS
    assert reg.shortcut == QKeySequence("Ctrl+R").toString(QKeySequence.NativeText)


def test_palette_includes_add_track_entries_and_opens_from_the_corner(monkeypatch):
    from gui.command_palette import CommandPalette
    w = _window()
    monkeypatch.setattr(CommandPalette, "exec", lambda self: 0)
    w.palette_btn.click()
    titles = w._command_palette.visible_titles()
    assert "Batteria..." in titles and "Cerca un comando..." not in titles
    w._command_palette.search.setText("batteria")
    assert w._command_palette.visible_titles()[0] == "Batteria..."


def test_palette_enter_runs_the_selected_command():
    from PySide6.QtGui import QAction
    from gui.command_palette import Command, CommandPalette
    w = _window()
    ran = []
    a1 = QAction("Esporta qualcosa", w)
    a2 = QAction("Registra qualcosa", w)
    a1.triggered.connect(lambda: ran.append("esporta"))
    a2.triggered.connect(lambda: ran.append("registra"))
    palette = CommandPalette(w, [Command("Esporta qualcosa", "Progetto", a1),
                                 Command("Registra qualcosa", "Traccia", a2)])
    palette.show()
    palette.search.setText("reg")
    assert palette.visible_titles() == ["Registra qualcosa"]
    QTest.keyClick(palette.search, Qt.Key_Return)
    _app.processEvents()
    assert ran == ["registra"] and not palette.isVisible()


def test_menus_group_import_and_export_in_submenus(monkeypatch):
    from gui.command_palette import collect_commands
    w = _window()
    assert [a.text() for a in w.menuBar().actions()] == [
        "&Progetto", "&Modifica", "&Vista", "&Traccia", "&Componi", "&Riproduzione", "&Suoni", "&Opzioni", "&Aiuto"]
    commands = {(c.path, c.title): c.action for c in collect_commands(w.menuBar())}
    for fmt in ("MIDI...", "MusicXML...", "ABC...", "MTXT..."):
        assert ("Progetto › Importa", fmt) in commands
    for fmt in ("Mix audio (WAV)...", "MIDI...", "Partitura PDF...", "Partitura MusicXML...",
                "Partitura ABC...", "MTXT..."):
        assert ("Progetto › Esporta", fmt) in commands
    # le scorciatoie restano anche dentro i sottomenu
    assert commands[("Progetto › Importa", "MIDI...")].shortcut() == QKeySequence("Ctrl+Shift+I")
    assert commands[("Progetto › Esporta", "MIDI...")].shortcut() == QKeySequence("Ctrl+Shift+E")

    # Traccia → Esporta questa traccia: MIDI, WAV e WAV asciutto della traccia selezionata
    exported = []
    monkeypatch.setattr(w, "export_track_wav", lambda name, dry=False: exported.append((name, dry)))
    w.current_track_name = "Voce"
    commands[("Traccia › Esporta questa traccia", "WAV...")].trigger()
    commands[("Traccia › Esporta questa traccia", "WAV asciutto (per il re-amping)...")].trigger()
    assert exported == [("Voce", False), ("Voce", True)]
    assert ("Traccia › Esporta questa traccia", "MIDI...") in commands
