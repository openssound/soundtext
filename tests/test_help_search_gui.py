"""Ricerca di un testo nella Guida utente (gui.help_dialog)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from gui.help_dialog import HelpDialog

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
