"""
Vista Partitura (gui.score_view, core.score_render): impaginazione con
Verovio, SVG riscritto per QtSvg, aggiornamento mentre si scrive, ultima
partitura valida in caso di errore, esportazione PDF. Senza Verovio la
vista spiega come installarlo.
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from core import score_render
from core.model import Project

_app = QApplication.instance() or QApplication([])

needs_verovio = pytest.mark.skipif(not score_render.available(), reason="verovio non installato")

SVG_NESTED = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="100px" height="200px">'
    '<svg class="definition-scale" viewBox="0 0 1000 2000"><g>'
    '<text x="5" y="6" font-size="0px"><tspan id="a" class="text"><tspan font-size="40px">Ma</tspan></tspan></text>'
    '<text x="1" y="2" font-size="0px" font-family="Times, serif"><tspan class="rend">'
    '<tspan font-family="Leipzig" font-size="100px"></tspan><tspan>=120</tspan></tspan></text>'
    "</g></svg></svg>")


def test_qt_svg_removes_nested_svg_and_tspans():
    import xml.etree.ElementTree as ET
    out = score_render.qt_svg(SVG_NESTED)
    root = ET.fromstring(out)
    ns = "{http://www.w3.org/2000/svg}"
    assert [el for el in root.iter(f"{ns}svg")] == [root]
    group = root.find(f"{ns}g")
    assert group.get("transform") == "scale(0.100000 0.100000)"
    texts = list(root.iter(f"{ns}text"))
    for text in texts:
        assert all(len(list(t)) == 0 for t in text)          # niente tspan annidati
    assert [(t.text, t.get("font-size")) for t in texts[0]] == [("Ma", "40px")]
    assert [(t.text, t.get("font-size")) for t in texts[1]] == [("♩", "60px"), ("=120", None)]
    assert texts[1].get("font-family") == score_render.SERIF_FONT


def _project():
    p = Project(name="Canzone")
    p.add_track("Voce", "Trumpet", '4: { c*5 d*5 e*5 f*5 ; 1c*4 } g*5\'1 "Ma- ri- a sei qui"')
    p.add_track("Accordi", "Piano", "4: 4C 4G")
    return p


@needs_verovio
def test_render_pages_and_pdf(tmp_path):
    from gui.score_view import export_pdf, render_score
    p = _project()
    pages = render_score(p, p.tracks)
    assert len(pages) == 1 and "<svg" in pages[0] and "Canzone" in pages[0] and ">Ma<" in pages[0]
    path = str(tmp_path / "partitura.pdf")
    export_pdf(pages, path)
    assert open(path, "rb").read(5) == b"%PDF-"


@needs_verovio
def test_syntax_error_keeps_the_last_score():
    from gui.score_view import render_score
    p = _project()
    p.tracks[0].text = "4: c [d"
    with pytest.raises(ValueError, match="Voce"):
        render_score(p, p.tracks)


def _window():
    from gui.main_window import MainWindow
    w = MainWindow()
    w.project.add_track("Voce", "Trumpet", "4: c*5 d*5 e*5 f*5")
    w.project.add_track("Basso", "Bass", "4: 4c*2")
    w.refresh_mixer()
    w.select_track("Voce")
    return w


def _close(w, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Discard)
    w.close()


@needs_verovio
def test_score_dialog_follows_the_project(monkeypatch):
    w = _window()
    w.show_score_view()
    dlg = w._score_dialog
    assert dlg.status_label.text() == "1 pagina"
    first = dlg.pages()
    assert "Basso" in first[0]
    dlg.tracks_combo.setCurrentIndex(1)                     # solo la traccia selezionata
    assert "Basso" not in dlg.pages()[0]
    w.editor.setPlainText("4: c*5 [d")                      # errore: resta l'ultima partitura
    dlg.refresh()
    assert "non aggiornata" in dlg.status_label.text() and dlg.pages()
    w.editor.setPlainText("4: g*5 a*5")
    dlg._check_changes()
    assert dlg._delay.isActive()                            # aspetta una pausa nella digitazione
    dlg.refresh()
    assert dlg.status_label.text() == "1 pagina"
    dlg._step_zoom(1)
    assert dlg.zoom_label.text() == "125%"
    w.show_score_view()
    assert w._score_dialog is dlg                           # una finestra sola
    dlg.close()
    _close(w, monkeypatch)


@needs_verovio
def test_export_score_pdf_from_the_menu(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog
    w = _window()
    path = str(tmp_path / "brano")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (path, ""))
    w.export_score_pdf()
    assert open(path + ".pdf", "rb").read(5) == b"%PDF-"
    _close(w, monkeypatch)


def test_without_verovio_the_view_explains_how_to_install(monkeypatch):
    w = _window()
    monkeypatch.setattr(score_render, "available", lambda: False)
    shown = []
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: shown.append(a[2]))
    w.show_score_view()
    assert getattr(w, "_score_dialog", None) is None
    assert "pip install verovio" in shown[0]
    _close(w, monkeypatch)


@needs_verovio
def test_packaged_app_uses_the_bundled_verovio_data(tmp_path, monkeypatch):
    """Nelle build gli script copiano i dati di Verovio in verovio-data
    accanto all'eseguibile: il programma li usa da li'."""
    import verovio
    from core import version
    (tmp_path / score_render.BUNDLED_DATA_DIR).mkdir()
    monkeypatch.setattr(version, "get_app_root", lambda: str(tmp_path))
    used = []
    monkeypatch.setattr(verovio, "setDefaultResourcePath", lambda path: used.append(path))
    monkeypatch.setattr(verovio, "toolkit", lambda: "tk")
    monkeypatch.setattr(score_render, "_toolkit", None)
    assert score_render._get_toolkit() == "tk"
    assert used == [str(tmp_path / score_render.BUNDLED_DATA_DIR)]
    monkeypatch.setattr(score_render, "_toolkit", None)
    monkeypatch.setattr(version, "get_app_root", lambda: str(tmp_path / "altrove"))
    used.clear()
    score_render._get_toolkit()
    assert used == []                     # senza la cartella: i dati del pacchetto
