"""
La vista Struttura brano, fase 1 del piano per la grafica: le note dentro i
box (core.clip_preview), la griglia dietro i box, le sezioni nel righello
(core.arrangement.song_sections) e l'altezza delle righe.

Esecuzione:
    python3 -m pytest tests/test_arrangement_look.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402
from PySide6.QtCore import QPoint, QPointF  # noqa: E402
from PySide6.QtGui import QColor  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from core.arrangement import song_sections  # noqa: E402
from core.clip_preview import clip_preview  # noqa: E402
from core.instruments import get_instrument  # noqa: E402
from core.model import Clip, Project  # noqa: E402

_app = QApplication.instance() or QApplication([])


# ------------------------------------------------------------ miniatura delle note

def test_preview_of_a_melody_uses_the_pitches():
    p = clip_preview("4: c d e f", get_instrument("Piano"), {})
    assert [(s, d) for s, d, _l in p.notes] == [(0.0, 1.0), (1.0, 1.0), (2.0, 1.0), (3.0, 1.0)]
    assert [lane for _s, _d, lane in p.notes] == [60, 62, 64, 65] and not p.percussion


def test_preview_of_chords_has_every_note_and_drums_one_lane_per_sound():
    chords = clip_preview("4: 4C", get_instrument("Piano"), {})
    assert len(chords.notes) >= 3 and len({s for s, _d, _l in chords.notes}) == 1     # le note insieme
    drums = clip_preview("16: kick r hihat r snare r hihat r", get_instrument("Drums"), {})
    assert drums.percussion and [lane for _s, _d, lane in drums.notes] == [0, 1, 2, 1]


def test_preview_times_start_from_the_box_and_errors_give_nothing():
    late = clip_preview("4: c d", get_instrument("Piano"), {}, origin_beat=32.0, meter_key="4/4")
    assert late.notes[0][0] == 0.0                         # dall'inizio del box, non del brano
    assert clip_preview("4: !!!", get_instrument("Piano"), {}) is None
    assert clip_preview("4: r r r r", get_instrument("Piano"), {}) is None   # solo pause


def test_preview_follows_the_patterns():
    p = Project()
    p.add_pattern("Riff", "c e g")
    before = clip_preview("4: %Riff", get_instrument("Piano"), p.patterns)
    p.add_pattern("Riff", "c e g b")
    after = clip_preview("4: %Riff", get_instrument("Piano"), p.patterns)
    assert len(before.notes) == 3 and len(after.notes) == 4


# ------------------------------------------------------------ sezioni

def test_sections_come_from_boxes_that_start_together():
    p = Project()
    for name, boxes in (("Bass", [("Groove", 0.0)]), ("Drums", [("Introduzione", 0.0), ("Strofa", 16.0)]),
                        ("Guitar", [("Introduzione", 8.0), ("Strofa", 16.0)])):
        t = p.add_track(name, name, "")
        t.clips = [Clip(name=n, text="4: c", start_beat=b) for n, b in boxes]
    # alla battuta 1 cominciano Groove e Introduzione: vince il nome che compare su piu' tracce;
    # l'Introduzione della chitarra a 8 e' sola, non e' una sezione
    assert song_sections(p) == [(0.0, "Introduzione"), (16.0, "Strofa")]
    solo = Project()
    solo.add_track("Piano", "Piano", "").clips = [Clip(name="A", text="4: c", start_beat=0.0),
                                                  Clip(name="B", text="4: c", start_beat=4.0)]
    assert song_sections(solo) == [(0.0, "A"), (4.0, "B")]           # una traccia sola: ogni box
    assert song_sections(Project()) == []


# ------------------------------------------------------------ nella finestra

def _window():
    from gui.main_window import MainWindow
    w = MainWindow()
    w.resize(1200, 720)
    w.show()
    for name, inst in (("Piano", "Piano"), ("Drums", "Drums")):
        t = w.project.add_track(name, inst, "")
        t.clips = [Clip(name="Intro", text="4: c d e f | g a b c*5", start_beat=0.0),
                   Clip(name="Strofa", text="4: e f g a", start_beat=8.0)] if inst == "Piano" else \
            [Clip(name="Intro", text="16: kick r hihat r snare r hihat r", start_beat=0.0),
             Clip(name="Strofa", text="16: kick r snare r", start_beat=8.0)]
    w.history.reset(w.project)
    w.refresh_mixer()
    w.arrangement_action.setChecked(True)
    _app.processEvents()
    return w


def test_ruler_shows_the_sections_and_a_click_jumps_there(monkeypatch):
    w = _window()
    canvas = w.arrangement_view.canvas
    assert canvas.sections == [(0.0, "Intro"), (8.0, "Strofa")]
    rects = canvas._section_rects(canvas.viewport().width())
    assert [name for _r, _b, name in rects] == ["Intro", "Strofa"]
    jumps = []
    monkeypatch.setattr(w, "seek_to_beat", lambda beat: jumps.append(beat))
    assert canvas.section_at(rects[1][0].center().toPoint()) == 8.0
    w.close()


def test_selected_box_is_redrawn_although_boxes_keep_their_image():
    from gui import arrangement_view as av
    w = _window()
    view = w.arrangement_view
    item = next(it for it in view.canvas._scene.items() if isinstance(it, av.BoxItem) and it.clip.name == "Strofa")
    corner = view.canvas.mapFromScene(item.mapToScene(QPointF(0, 20)))     # il bordo sinistro del box
    border = av._selection_color(item.brush().color()).name()

    def accent_at_border():
        image = view.canvas.viewport().grab().toImage()
        return any(QColor(image.pixel(corner.x() + dx, corner.y())).name() == border
                   for dx in range(0, 3))

    assert not accent_at_border()
    view.select_box("Piano", item.clip)
    _app.processEvents()
    assert accent_at_border()
    view.select_box(None, None)
    _app.processEvents()
    assert not accent_at_border()
    w.close()


def test_selection_border_stands_out_on_every_box_color():
    """Il bordo del box selezionato si vede su ogni colore di box: in
    boom_bap il Rhodes (famiglia Pianoforti, #7ec9e8) aveva un box quasi
    dello stesso azzurro dell'accento, e selezionarlo non cambiava nulla."""
    from gui import arrangement_view as av
    from gui.track_widget import _FAMILY_COLORS, _PERCUSSION_COLOR, AUDIO_TRACK_COLOR
    from gui.theme import ACCENT

    def distance(a, b):
        return sum((x - y) ** 2 for x, y in zip(a.getRgb()[:3], b.getRgb()[:3])) ** 0.5

    colors = list(_FAMILY_COLORS.values()) + [_PERCUSSION_COLOR, AUDIO_TRACK_COLOR, ACCENT,
                                              av.MUTED_CLIP_COLOR]
    for name in colors:
        box = QColor(name)
        assert distance(av._selection_color(box), box) > 90, name
    assert av._selection_color(QColor("#e8c96d")).name() == QColor(ACCENT).name()   # dove si vede resta l'accento


def test_row_height_changes_rows_and_headers_and_is_remembered():
    from core import settings
    from gui import arrangement_view as av
    w = _window()
    view = w.arrangement_view
    try:
        view.set_row_height(128)
        _app.processEvents()
        assert av.ROW_HEIGHT == 128 and settings.get_arrangement_row_height() == 128
        assert all(h.height() == 128 for h in view.canvas.header_widgets.values())
        assert w._row_height_actions[128].isChecked()
        view.step_row_height(-1)
        assert av.ROW_HEIGHT == 96
        view.step_row_height(-5)
        assert av.ROW_HEIGHT == 64                                   # non piu' basse delle testate
    finally:
        view.set_row_height(av.DEFAULT_ROW_HEIGHT)
        settings.set_arrangement_row_height(0)
        w.close()


def test_grid_is_drawn_behind_the_boxes():
    """Dentro un box non si vedono le stanghette: la griglia sta dietro."""
    from gui import arrangement_view as av
    w = _window()
    view = w.arrangement_view
    item = next(it for it in view.canvas._scene.items() if isinstance(it, av.BoxItem) and it.clip.name == "Intro"
                and it.track_name == "Piano")
    # la stanghetta della battuta 2 (beat 4) cade dentro il box Intro (beat 0-8)
    x = view.canvas.mapFromScene(QPointF(av.HEADER_WIDTH + 4 * av.PX_PER_BEAT, 0)).x()
    y = view.canvas.mapFromScene(item.mapToScene(QPointF(0, item.rect().height() - 3))).y()
    image = view.canvas.viewport().grab().toImage()
    box_color = item.brush().color().name()
    assert QColor(image.pixel(x, y)).name() == box_color
    w.close()
