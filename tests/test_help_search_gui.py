"""Ricerca di un testo nella Guida utente (gui.help_dialog)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from gui.help_dialog import HELP_PATH, HelpDialog

app = QApplication.instance() or QApplication([])


def _dialog():
    d = HelpDialog()
    d.show()
    d.show_search()
    return d


def test_search_bar_hidden_until_requested():
    d = HelpDialog()
    d.show()
    assert not d.search_bar.isVisible()
    d.show_search()
    assert d.search_bar.isVisible()


def test_finds_every_match_and_wraps_around():
    d = _dialog()
    d.search_edit.setText("tempo")
    total = len(d._matches)
    assert total > 1
    assert d._current == 0
    d.find()
    assert d._current == 1
    d.find(backward=True)
    d.find(backward=True)
    assert d._current == total - 1          # dall'inizio riparte dall'ultima
    d.find()
    assert d._current == 0
    selected = d.browser.document().find("tempo", 0)
    assert len(d.browser.extraSelections()) == total
    assert d._matches[0].selectionStart() == selected.selectionStart()


def test_no_match_and_escape_closes_search():
    d = _dialog()
    d.search_edit.setText("zzz-testo-che-non-esiste")
    assert d._matches == []
    assert d.search_status.text()
    QTest.keyClick(d.search_edit, Qt.Key_Escape)
    assert not d.search_bar.isVisible()
    assert d.isVisible()                     # Esc chiude solo la ricerca
    assert d.browser.extraSelections() == []


def test_enter_goes_forward_and_shift_enter_back():
    d = _dialog()
    d.search_edit.setText("tempo")
    QTest.keyClick(d.search_edit, Qt.Key_Return)
    QTest.keyClick(d.search_edit, Qt.Key_Return)
    assert d._current == 2
    QTest.keyClick(d.search_edit, Qt.Key_Return, Qt.ShiftModifier)
    assert d._current == 1
    assert d.isVisible()                     # Invio non preme "Chiudi"


def test_every_index_link_reaches_its_section():
    """L'indice in cima alla guida: in ogni lingua ogni voce porta a un
    titolo che esiste, e le sezioni sono numerate di seguito."""
    import re

    from core import i18n
    try:
        for code in ("it", "en", "es", "fr"):
            i18n.set_language(code)
            d = HelpDialog()
            d.show()
            with open(i18n.localized_doc(HELP_PATH), encoding="utf-8") as f:
                text = f.read()
            refs = re.findall(r"\]\(#([0-9][0-9.]*)\)", text)
            assert len(refs) > 90
            for ref in refs:
                assert d.goto_section(ref), (code, ref)
            chapters = [int(n) for n in re.findall(r"^## ([0-9]+)\. ", text, re.M)]
            assert chapters == list(range(1, len(chapters) + 1)), code
            d.close()
    finally:
        i18n.set_language("it")
