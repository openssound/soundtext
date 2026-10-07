"""
Test GUI (PySide6, piattaforma offscreen) per il canvas a box della vista
Struttura brano (gui.arrangement_view).

Regressioni coperte:
- Selezionare un box con un semplice click lo spostava silenziosamente sul
  beat intero piu' vicino quando il box non era gia' su un beat esatto
  (es. dopo una tuplet, sezione 2.1bis) - un micro-movimento del mouse di
  pochi pixel tra press e release (quasi inevitabile con un mouse vero,
  anche per un click "fermo") veniva interpretato da itemChange() come
  l'inizio di un trascinamento, che aggancia gia' "dal vivo" la posizione
  al beat piu' vicino.
- Il menu tasto-destro su un punto vuoto della riga di una traccia (non la
  stretta colonna nomi a sinistra) non offriva "Genera batteria/basso in
  questa traccia..." anche quando lo strumento della traccia lo rendeva
  applicabile - disponibile solo dal tasto-destro sull'etichetta della
  traccia (show_track_menu), non intuitivo per chi clicca in un punto
  qualunque della riga.
- Il pulsante "Play anteprima" non aveva un vero Play/Pausa: premuto di
  nuovo durante la riproduzione non faceva nulla di utile, invece di
  mettere in pausa (e riprendere dallo stesso punto al prossimo Play, sullo
  stesso box) come il trasporto principale (vedi gui.main_window_playback).

Esecuzione:
    python3 -m pytest tests/test_arrangement_view_gui.py -v
oppure:
    python3 tests/test_arrangement_view_gui.py
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QPoint, QPointF, Qt, QTimer
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

from core.model import Clip
from gui.main_window import MainWindow
from gui.arrangement_view import BoxItem

_app = QApplication.instance() or QApplication([])


def _make_window_with_boxed_track(start_beat: float):
    w = MainWindow()
    w.resize(900, 600)
    w.show()
    w.project.add_track("Piano", "Piano", "")
    track = w.project.tracks[0]
    clip = Clip(name="A", text="c*4", start_beat=start_beat)
    track.clips.append(clip)
    w.history.reset(w.project)   # punto di partenza della cronologia: il progetto appena preparato
    w.arrangement_action.setChecked(True)
    _app.processEvents()
    w.arrangement_view.refresh()
    _app.processEvents()
    canvas = w.arrangement_view.canvas
    item = next(it for it in canvas._scene.items() if isinstance(it, BoxItem))
    return w, canvas, item, clip


def _view_point_for(canvas, item):
    return canvas.mapFromScene(item.sceneBoundingRect().center())


def test_click_with_tiny_jitter_does_not_move_box_off_grid():
    w, canvas, item, clip = _make_window_with_boxed_track(start_beat=2.4)
    view_pt = _view_point_for(canvas, item)

    QTest.mousePress(canvas.viewport(), Qt.LeftButton, Qt.NoModifier, view_pt)
    _app.processEvents()
    QTest.mouseMove(canvas.viewport(), view_pt + type(view_pt)(2, 0))
    _app.processEvents()
    QTest.mouseRelease(canvas.viewport(), Qt.LeftButton, Qt.NoModifier, view_pt + type(view_pt)(2, 0))
    _app.processEvents()

    assert clip.start_beat == 2.4
    assert not w.history.can_undo()


def test_still_click_does_not_move_box_or_touch_undo():
    w, canvas, item, clip = _make_window_with_boxed_track(start_beat=2.4)
    view_pt = _view_point_for(canvas, item)

    QTest.mouseClick(canvas.viewport(), Qt.LeftButton, Qt.NoModifier, view_pt)
    _app.processEvents()

    assert clip.start_beat == 2.4
    assert not w.history.can_undo()


def test_real_drag_still_snaps_and_moves_the_box():
    w, canvas, item, clip = _make_window_with_boxed_track(start_beat=2.4)
    view_pt = _view_point_for(canvas, item)

    QTest.mousePress(canvas.viewport(), Qt.LeftButton, Qt.NoModifier, view_pt)
    _app.processEvents()
    QTest.mouseMove(canvas.viewport(), view_pt + type(view_pt)(48, 0))  # ~2 beat
    _app.processEvents()
    QTest.mouseRelease(canvas.viewport(), Qt.LeftButton, Qt.NoModifier, view_pt + type(view_pt)(48, 0))
    _app.processEvents()

    assert clip.start_beat != 2.4
    assert clip.start_beat == round(clip.start_beat)  # agganciato a un beat intero
    assert w.history.can_undo()

    # Ctrl+Z (cronologia unica del progetto) riporta il box dov'era
    w.undo()
    _app.processEvents()
    assert w.project.tracks[0].clips[0].start_beat == 2.4
    assert not w.history.can_undo()
    w.redo()
    _app.processEvents()
    assert w.project.tracks[0].clips[0].start_beat == clip.start_beat


def _open_menu_and_capture_actions(open_menu_fn):
    """Apre un QMenu modale (exec() blocca finche' non si chiude) e ne
    legge i testi delle azioni da un QTimer che scatta mentre e' ancora
    aperto, poi lo chiude per sbloccare la exec() - tecnica standard per
    testare un QMenu in un ambiente headless (QMenu.exec non e'
    monkeypatchabile: e' un binding Shiboken, non un metodo Python)."""
    captured = {}

    def check_and_close():
        menu = QApplication.activePopupWidget()
        if menu is not None:
            captured["actions"] = [a.text() for a in menu.actions()]
            menu.close()

    QTimer.singleShot(50, check_and_close)
    open_menu_fn()
    return captured.get("actions", [])


def test_empty_row_menu_offers_generate_drums_for_percussion_track():
    w = MainWindow()
    w.resize(900, 600)
    w.show()
    w.project.add_track("Drums 2", "Drums", "")
    w.arrangement_action.setChecked(True)
    _app.processEvents()
    w.arrangement_view.refresh()
    _app.processEvents()

    global_pos = w.mapToGlobal(w.rect().center())
    actions = _open_menu_and_capture_actions(
        lambda: w.arrangement_view.show_empty_menu("Drums 2", 4.0, global_pos)
    )
    assert any("batteria" in t.lower() for t in actions)


def test_empty_row_menu_offers_generate_bass_for_bass_track():
    w = MainWindow()
    w.resize(900, 600)
    w.show()
    from core.instruments import resolve_or_create_instrument_by_program
    # programma GM 35 (Fretless Bass), non fra i predefiniti: lo registra (nella
    # configurazione isolata dei test) invece di presupporne l'esistenza
    w.project.add_track("Fretless bass", resolve_or_create_instrument_by_program(35, False), "")
    w.arrangement_action.setChecked(True)
    _app.processEvents()
    w.arrangement_view.refresh()
    _app.processEvents()

    global_pos = w.mapToGlobal(w.rect().center())
    actions = _open_menu_and_capture_actions(
        lambda: w.arrangement_view.show_empty_menu("Fretless bass", 4.0, global_pos)
    )
    assert any("basso" in t.lower() for t in actions)


def test_empty_row_menu_omits_generate_actions_for_unrelated_instrument():
    w = MainWindow()
    w.resize(900, 600)
    w.show()
    w.project.add_track("Piano", "Piano", "")
    w.arrangement_action.setChecked(True)
    _app.processEvents()
    w.arrangement_view.refresh()
    _app.processEvents()

    global_pos = w.mapToGlobal(w.rect().center())
    actions = _open_menu_and_capture_actions(
        lambda: w.arrangement_view.show_empty_menu("Piano", 4.0, global_pos)
    )
    assert not any("batteria" in t.lower() or "basso" in t.lower() for t in actions)


def _menu_actions_for(track_specs, target, empty_row=True):
    """Voci del menu tasto-destro della traccia 'target' in un progetto con
    le tracce (nome, strumento, testo) di 'track_specs'."""
    w = MainWindow()
    w.resize(900, 600)
    w.show()
    for name, instrument, text in track_specs:
        w.project.add_track(name, instrument, text)
    w.arrangement_action.setChecked(True)
    _app.processEvents()
    w.arrangement_view.refresh()
    _app.processEvents()
    global_pos = w.mapToGlobal(w.rect().center())
    if empty_row:
        return _open_menu_and_capture_actions(
            lambda: w.arrangement_view.show_empty_menu(target, 4.0, global_pos))
    return _open_menu_and_capture_actions(
        lambda: w.arrangement_view.show_track_menu(target, global_pos))


def test_menus_offer_chord_progression_for_polyphonic_track_when_song_has_no_chords():
    specs = [("Piano", "Piano", ""), ("Tromba", "Trumpet", "4: c*5 d*5 e*5")]
    for empty_row in (True, False):
        actions = _menu_actions_for(specs, "Piano", empty_row)
        assert any("giro armonico" in t.lower() for t in actions), actions


def test_chord_progression_not_offered_once_the_song_has_chords():
    specs = [("Piano", "Piano", ""), ("Chitarra", "Guitar", "4: 4Am 4F 4C 4G")]
    for empty_row in (True, False):
        actions = _menu_actions_for(specs, "Piano", empty_row)
        assert not any("giro armonico" in t.lower() for t in actions), actions


def test_track_with_the_chords_keeps_offering_chord_progression_for_next_boxes():
    specs = [("Piano", "Piano", "4: 4Am 4F 4C 4G"), ("Basso", "Bass", "")]
    for empty_row in (True, False):
        actions = _menu_actions_for(specs, "Piano", empty_row)
        assert any("giro armonico" in t.lower() for t in actions), actions
        assert not _offers_melody_entry(actions), actions


def test_chord_progression_not_offered_for_monophonic_or_percussion_tracks():
    specs = [("Tromba", "Trumpet", ""), ("Drums", "Drums", "")]
    for target in ("Tromba", "Drums"):
        actions = _menu_actions_for(specs, target)
        assert not any("giro armonico" in t.lower() for t in actions), (target, actions)


def _offers_melody_entry(actions):
    return any("accompagnamento" in t.lower() or "riff" in t.lower() for t in actions)


def test_accompaniment_and_riff_hidden_until_another_track_has_chords():
    no_chords = [("Piano", "Piano", ""), ("Tromba", "Trumpet", "4: c*5 d*5")]
    with_chords = no_chords + [("Chitarra", "Guitar", "4: 4Am 4F 4C 4G")]
    for empty_row in (True, False):
        for target in ("Piano", "Tromba"):
            assert not _offers_melody_entry(_menu_actions_for(no_chords, target, empty_row)), target
            assert _offers_melody_entry(_menu_actions_for(with_chords, target, empty_row)), target


def test_accompaniment_hidden_when_the_only_chords_are_in_the_same_track():
    # l'accompagnamento legge gli accordi dalle ALTRE tracce
    specs = [("Piano", "Piano", "4: 4Am 4F 4C 4G"), ("Organo", "Piano", "")]
    assert not _offers_melody_entry(_menu_actions_for(specs, "Piano"))
    assert _offers_melody_entry(_menu_actions_for(specs, "Organo"))


def test_track_menu_accompaniment_without_chords_explains_instead_of_opening_the_dialog(monkeypatch):
    import gui.main_window_mixer as mixer
    from PySide6.QtWidgets import QMessageBox
    opened, shown = [], []
    monkeypatch.setattr(mixer, "MelodyGenerateDialog", lambda *a, **k: opened.append(1))
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: shown.append(a[1])))
    w = MainWindow()
    w.project.add_track("Piano", "Piano", "")
    w.project.add_track("Tromba", "Trumpet", "4: c*5 d*5")
    w.refresh_mixer()
    w.select_track("Piano")
    w.generate_melody_into_selected_track()
    assert opened == [] and shown == ["Nessun giro di accordi"]


class _FakePreviewPlayback:
    """Sostituisce ArrangementView._preview_playback nei test di Play/Pausa:
    un vero PlaybackEngine dipende da un synth esterno (fluidsynth/timidity)
    non garantito nell'ambiente di test, e le sue tempistiche reali
    renderebbero i test non deterministici."""

    def __init__(self):
        self.playing = False
        self.last_offset = None

    def is_playing(self):
        return self.playing

    def play(self, project, only_audible=True, start_offset_beats=0.0, on_audio_started=None):
        self.playing = True
        self.last_offset = start_offset_beats
        if on_audio_started:
            on_audio_started()

    def stop(self):
        self.playing = False


def _make_window_with_selected_clip(text="c*4 d*4 e*4 f*4"):
    w = MainWindow()
    w.resize(900, 600)
    w.show()
    w.project.add_track("Piano", "Piano", "")
    track = w.project.tracks[0]
    clip = Clip(name="A", text=text, start_beat=0)
    track.clips.append(clip)
    w.history.reset(w.project)   # punto di partenza della cronologia: il progetto appena preparato
    w.arrangement_action.setChecked(True)
    _app.processEvents()
    w.arrangement_view.refresh()
    _app.processEvents()
    w.arrangement_view._preview_playback = _FakePreviewPlayback()
    w.arrangement_view.select_box("Piano", clip)
    return w, track, clip


def test_preview_play_button_toggles_to_pause_while_playing():
    w, track, clip = _make_window_with_selected_clip()
    av = w.arrangement_view

    assert av.preview_action.text() == "Ascolta il box selezionato"
    av._toggle_play_selected()
    assert av.preview_action.text() == "Pausa ascolto del box"
    assert av._preview_playback.is_playing()


def test_preview_pause_then_play_resumes_from_same_beat():
    w, track, clip = _make_window_with_selected_clip()
    av = w.arrangement_view

    av._toggle_play_selected()  # play
    av._preview_paused_beat = None
    av._preview_start_wall -= 1.0  # simula un secondo di riproduzione trascorso
    av._toggle_play_selected()  # pausa
    assert not av._preview_playback.is_playing()
    assert av.preview_action.text() == "Ascolta il box selezionato"
    paused_at = av._preview_paused_beat
    assert paused_at is not None and paused_at > 0

    av._toggle_play_selected()  # riprende
    assert av._preview_playback.is_playing()
    assert av.preview_action.text() == "Pausa ascolto del box"
    assert av._preview_playback.last_offset == paused_at


def test_preview_stop_clears_pause_state():
    w, track, clip = _make_window_with_selected_clip()
    av = w.arrangement_view

    av._toggle_play_selected()
    av._toggle_play_selected()  # pausa
    assert av._preview_paused_beat is not None

    av._stop_preview()
    assert not av._preview_playback.is_playing()
    assert av._preview_paused_beat is None
    assert av.preview_action.text() == "Ascolta il box selezionato"


def test_selecting_different_box_while_paused_restarts_from_zero():
    w, track, clip = _make_window_with_selected_clip()
    av = w.arrangement_view
    clip2 = Clip(name="B", text="g*4", start_beat=4)
    track.clips.append(clip2)
    av.refresh()

    av.select_box("Piano", clip)
    av._toggle_play_selected()
    av._preview_start_wall -= 1.0
    av._toggle_play_selected()  # pausa clip
    assert av._preview_paused_beat > 0

    av.select_box("Piano", clip2)
    av._toggle_play_selected()  # play su un box diverso: deve ripartire da 0
    assert av._preview_playback.last_offset == 0.0


def test_preview_natural_end_resets_button_to_play():
    w, track, clip = _make_window_with_selected_clip()
    av = w.arrangement_view

    av._toggle_play_selected()
    assert av.preview_action.text() == "Pausa ascolto del box"

    av._preview_playback.playing = False  # fine naturale, nessuno Stop/Pausa esplicito
    QTest.qWait(400)  # lascia scattare _preview_status_timer (200ms)

    assert av.preview_action.text() == "Ascolta il box selezionato"
    assert av._preview_paused_beat is None


def test_preview_play_after_track_rename_uses_new_name():
    # Regressione: dopo "Modifica nome/strumento traccia" la selezione
    # ricordava il vecchio nome e Play anteprima sollevava KeyError.
    w, track, clip = _make_window_with_selected_clip()
    av = w.arrangement_view
    w.project.update_track("Piano", "Pianoforte", "Piano")

    av._toggle_play_selected()

    assert av._preview_playback.is_playing()
    assert av.selected_track_name == "Pianoforte"
    assert w._resolve_edit_target() == (track, clip)


def test_selection_dropped_when_project_replaced_by_one_with_equal_box():
    # Un box identico (uguale per contenuto, non lo stesso oggetto) in un
    # altro progetto non deve tenere in vita la selezione del precedente.
    w, track, clip = _make_window_with_selected_clip()
    av = w.arrangement_view
    w.project.tracks.clear()
    w.project.add_track("Basso", "Piano", "")
    w.project.tracks[0].clips.append(Clip(name=clip.name, text=clip.text, start_beat=clip.start_beat))

    av.refresh()

    assert av.selected_clip is None
    assert av.selected_track_name is None


if __name__ == "__main__":
    import inspect
    here = sys.modules[__name__]
    tests = [f for name, f in inspect.getmembers(here) if name.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        passed += 1
        print(f"OK  {t.__name__}")
    print(f"\n{passed}/{len(tests)} test superati.")


def _scrolled_window_with_long_box():
    """Finestra con un box lungo, scorsa a destra quanto basta perche' il box
    passi sotto la colonna (ferma) dei nomi traccia."""
    w = MainWindow()
    w.resize(900, 600)
    w.show()
    t = w.project.add_track("Piano", "Piano", "")
    t.clips = [Clip("Lungo", "4: " + " ".join(["c"] * 128), 0.0)]
    w.arrangement_action.setChecked(True)
    _app.processEvents()
    w.arrangement_view.refresh()
    _app.processEvents()
    canvas = w.arrangement_view.canvas
    canvas.horizontalScrollBar().setValue(400)
    _app.processEvents()
    row_y = canvas.mapFromScene(QPointF(0, canvas.row_ys["Piano"] + 10)).y()
    return w, canvas, QPoint(40, row_y)


def test_right_click_on_track_name_opens_track_menu_even_with_a_box_scrolled_under_it(monkeypatch):
    w, canvas, header_pos = _scrolled_window_with_long_box()
    assert isinstance(canvas.itemAt(header_pos), BoxItem)     # il box e' davvero li' sotto
    opened = []
    monkeypatch.setattr(w.arrangement_view, "show_track_menu", lambda name, pos: opened.append(("traccia", name)))
    monkeypatch.setattr(w.arrangement_view, "show_box_menu", lambda item, pos: opened.append(("box", item)))
    canvas.contextMenuEvent(QContextMenuEvent(QContextMenuEvent.Mouse, header_pos, canvas.mapToGlobal(header_pos)))
    assert opened == [("traccia", "Piano")]


def test_double_click_on_track_name_does_not_open_the_box_scrolled_under_it(monkeypatch):
    w, canvas, header_pos = _scrolled_window_with_long_box()
    edited = []
    monkeypatch.setattr(w.arrangement_view, "edit_box", lambda item: edited.append(item))
    QTest.mouseDClick(canvas.viewport(), Qt.LeftButton, Qt.NoModifier, header_pos)
    assert edited == []


def test_convert_to_free_text_is_the_last_entry_of_the_track_menu_when_it_has_boxes(monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    w = MainWindow()
    w.resize(900, 600)
    w.show()
    boxed = w.project.add_track("Piano", "Piano", "")
    boxed.clips = [Clip("Strofa", "4: c d e f", 0.0)]
    w.project.add_track("Tromba", "Trumpet", "4: c d")         # senza box
    w.arrangement_action.setChecked(True)
    _app.processEvents()
    w.arrangement_view.refresh()
    _app.processEvents()
    pos = w.mapToGlobal(w.rect().center())
    actions = [a for a in _open_menu_and_capture_actions(lambda: w.arrangement_view.show_track_menu("Piano", pos)) if a]
    assert actions[-1] == "Converti in testo libero..."
    actions = _open_menu_and_capture_actions(lambda: w.arrangement_view.show_track_menu("Tromba", pos))
    assert "Converti in testo libero..." not in actions

    text_before = boxed.text
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))
    w.arrangement_view._convert_to_free_text("Piano")
    assert boxed.clips == [] and boxed.text == text_before


def test_track_without_boxes_offers_editing_its_free_text(monkeypatch):
    from gui import arrangement_view
    w = MainWindow()
    w.resize(900, 600)
    w.show()
    w.project.add_track("Tromba", "Trumpet", "4: c d")         # testo libero, senza box
    w.history.reset(w.project)
    w.arrangement_action.setChecked(True)
    _app.processEvents()
    w.arrangement_view.refresh()
    _app.processEvents()
    pos = w.mapToGlobal(w.rect().center())
    actions = [a for a in _open_menu_and_capture_actions(lambda: w.arrangement_view.show_track_menu("Tromba", pos)) if a]
    assert actions[-1] == "Modifica testo libero..."

    opened = {}

    class FakeDialog:
        Accepted = 1

        def __init__(self, parent, project, instrument_name, tempo_bpm, clip_text="", title="", with_name=True, track_name=None):
            opened.update(text=clip_text, with_name=with_name)

        def exec(self):
            return self.Accepted

        def result_text(self):
            return "4: e f g"

    monkeypatch.setattr(arrangement_view, "BoxEditDialog", FakeDialog)
    w.arrangement_view.edit_free_text("Tromba")
    assert opened == {"text": "4: c d", "with_name": False}
    assert w.project.get_track("Tromba").text == "4: e f g"
    assert w.project.get_track("Tromba").clips == []           # resta testo libero
    w.undo()
    assert w.project.get_track("Tromba").text == "4: c d"


def test_box_dialog_without_name_accepts_the_text():
    from core.model import Project
    from gui.box_edit_dialog import BoxEditDialog
    dlg = BoxEditDialog(None, Project(name="t"), "Piano", 120, clip_text="4: c d", with_name=False)
    assert dlg.name_edit is None
    dlg.accept()
    assert dlg.result_text() == "4: c d"
