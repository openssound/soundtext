"""
Fase 2 del piano per la grafica: display del tempo, riga del Master in
fondo alla colonna delle tracce, testate delle tracce (nome una volta sola,
bilanciamento tradotto, FX acceso solo con il pannello aperto, traccia
selezionata tinta).

Esecuzione:
    python3 -m pytest tests/test_headers_and_time_look.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.model import Effect  # noqa: E402

_app = QApplication.instance() or QApplication([])


def _window():
    from gui.main_window import MainWindow
    w = MainWindow()
    w.resize(1400, 800)
    w.show()
    w.project.add_track("Bass", "Bass", "4: c")
    w.project.add_track("Guitar 1", "Guitar", "4: c")
    w.refresh_mixer()
    _app.processEvents()
    return w


# ------------------------------------------------------------ display del tempo

def test_time_display_counts_bars_and_beats_with_meter_and_pickup():
    from gui.time_display import TimeDisplay
    display = TimeDisplay()
    display.set_meter("4/4", [], 0)
    assert display.position_of(0.0) == (1, 1) and display.position_of(5.5) == (2, 2)
    display.set_meter("3/4", [], 0)
    assert display.position_of(6.0) == (3, 1)
    display.set_meter("4/4", [], 1)                       # un quarto in levare: e' la battuta 0
    assert display.position_of(0.5) == (0, 1) and display.position_of(1.0) == (1, 1)
    display.set_meter("4/4", [(3, "3/4")], 0)            # dalla battuta 3 in 3/4
    assert display.position_of(8.0) == (3, 1) and display.position_of(11.0) == (4, 1)


def test_time_display_shows_the_progress_text_and_swaps_on_click():
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    w = _window()
    w.playback_progress.setFormat("01:23 / 03:40")
    w.arrangement_view.set_playhead_beat(5.0)
    assert w.time_display._big.text() == "01:23 / 03:40" and w.time_display._small.text() == "battuta 2 · 2"
    QTest.mouseClick(w.time_display, Qt.LeftButton, pos=QPoint(5, 5))
    assert w.time_display._big.text() == "battuta 2 · 2"
    w.close()


# ------------------------------------------------------------ Master

def test_master_strip_keeps_volume_fx_and_meter_working(monkeypatch):
    w = _window()
    w.master_vol_slider.setValue(80)
    assert w.project.master_volume == 80 and w.master_vol_value_label.text() == "80%"
    opened = []
    # il pannello vero avvierebbe l'ascolto di prova del master
    monkeypatch.setattr(w.effects_panel, "open_master", lambda: opened.append(True))
    w.master_fx_btn.click()
    assert opened == [True]
    assert w.level_meter.parentWidget() is w.master_strip
    w._dirty = False             # il volume cambiato: alla chiusura chiederebbe di salvare
    w.close()


# ------------------------------------------------------------ testate

def test_instrument_line_only_when_it_differs_from_the_name():
    w = _window()
    headers = w.arrangement_view.canvas.header_widgets
    assert not headers["Bass"].instr_label.isVisibleTo(headers["Bass"])          # "Bass / Bass"
    assert headers["Guitar 1"].instr_label.isVisibleTo(headers["Guitar 1"])      # "Guitar 1 / Guitar"
    w.close()


def test_pan_label_speaks_the_interface_language():
    from gui.track_widget import _pan_label
    assert (_pan_label(64), _pan_label(20), _pan_label(127)) == ("C", "S70", "D100")


def test_fx_button_is_full_only_while_its_panel_is_open():
    w = _window()
    bass = w.project.get_track("Bass")
    bass.effects = [Effect("delay", {})]
    w.refresh_mixer()
    header = w.arrangement_view.canvas.header_widgets["Bass"]
    assert header.fx_btn.objectName() == "fxBtnOn"                # effetti, pannello chiuso: tenue
    w.open_effects_panel("Bass")
    _app.processEvents()
    header = w.arrangement_view.canvas.header_widgets["Bass"]
    assert header.fx_btn.objectName() == "fxBtnOpen"
    assert w.arrangement_view.canvas.header_widgets["Guitar 1"].fx_btn.objectName() == "fxBtn"
    w.effects_panel.close_panel()
    _app.processEvents()
    assert w.arrangement_view.canvas.header_widgets["Bass"].fx_btn.objectName() == "fxBtnOn"
    w.close()


def test_selected_track_header_is_tinted_with_its_color():
    w = _window()
    w.select_track("Guitar 1")
    header = w.arrangement_view.canvas.header_widgets["Bass"]
    plain = header.styleSheet()
    w.select_track("Bass")
    header = w.arrangement_view.canvas.header_widgets["Bass"]
    assert header.styleSheet() != plain
    w.close()
