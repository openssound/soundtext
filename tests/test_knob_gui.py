"""Manopola Volume/Pan delle testate della vista Struttura (gui.knob)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from gui.knob import Knob

app = QApplication.instance() or QApplication([])


def test_drag_up_increases_and_down_decreases():
    k = Knob("Vol", 0, 200, 100)
    k.show()
    center = k.rect().center()
    QTest.mousePress(k, Qt.LeftButton, Qt.NoModifier, center)
    QTest.mouseMove(k, center - QPoint(0, 15))
    QTest.mouseRelease(k, Qt.LeftButton, Qt.NoModifier, center - QPoint(0, 15))
    assert k.value() > 100
    up = k.value()
    QTest.mousePress(k, Qt.LeftButton, Qt.NoModifier, center)
    QTest.mouseMove(k, center + QPoint(0, 15))
    QTest.mouseRelease(k, Qt.LeftButton, Qt.NoModifier, center + QPoint(0, 15))
    assert k.value() < up


def test_double_click_restores_default():
    k = Knob("Pan", 0, 127, 64, bipolar=True)
    k.setValue(10)
    QTest.mouseDClick(k, Qt.LeftButton, Qt.NoModifier, k.rect().center())
    assert k.value() == 64


def test_keyboard_steps_and_range_clamp():
    k = Knob("Vol", 0, 200, 100)
    k.setValue(199)
    QTest.keyClick(k, Qt.Key_Up)
    QTest.keyClick(k, Qt.Key_Up)
    assert k.value() == 200


def test_paints_without_errors_at_extremes():
    for value in (0, 64, 127):
        k = Knob("Pan", 0, 127, 64, bipolar=True)
        k.setValue(value)
        assert not k.grab().isNull()
