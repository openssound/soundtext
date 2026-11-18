"""
Il display del tempo nella barra dei comandi, come quello di un registratore:
in grande il tempo trascorso e la durata (01:23 / 03:40), sotto la
posizione musicale (battuta 12 · 3). Un clic scambia quale dei due e' in
grande.

Il testo del tempo arriva dalla barra di avanzamento (PlaybackProgress, che
lo annuncia a ogni aggiornamento: e' scritto in molti punti di
gui.main_window_playback), la posizione dalla testina della vista Struttura
(ArrangementView.set_playhead_beat).
"""

import bisect

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QFrame, QLabel, QProgressBar, QSizePolicy, QVBoxLayout

from core.i18n import tr
from core.notation import bar_starts


class PlaybackProgress(QProgressBar):
    """La barra di avanzamento: sottile, cliccabile (vedi l'eventFilter
    della finestra); il suo testo (il tempo) lo mostra TimeDisplay."""
    textChanged = Signal(str)

    def setFormat(self, text: str):
        super().setFormat(text)
        self.textChanged.emit(text)


class TimeDisplay(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("timeDisplay")
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(tr("Tempo trascorso e durata, e la posizione nel brano (battuta · movimento).\n"
                           "Clic: scambia quale dei due e' in grande."))
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 2, 10, 2)
        layout.setSpacing(0)
        mono = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        self._big = QLabel()
        self._small = QLabel()
        for label, size, bold in ((self._big, 15, True), (self._small, 10, False)):
            font = QFont(mono)
            font.setPixelSize(size)
            font.setBold(bold)
            label.setFont(font)
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
        self._time = "00:00 / 00:00"
        self._position = ""
        self._bars_first = False
        self._meter = None
        self._starts = []
        self._bars = None
        self._big.setMinimumWidth(self._big.fontMetrics().horizontalAdvance("000:00 / 000:00"))
        self.set_beat(None)

    # ------------------------------------------------------------ stato
    def set_time_text(self, text: str):
        self._time = text
        self._refresh()

    def set_meter(self, time_sig, metrica_changes, pickup):
        """La metrica del brano, per contare battute e movimenti."""
        meter = (time_sig, tuple(metrica_changes or ()), pickup)
        if meter != self._meter:
            self._meter = meter
            self._bars = bar_starts(time_sig, list(metrica_changes or ()), pickup)
            self._starts = []
            if pickup:
                self._starts.append(0.0)
            self._first_bar = 0 if pickup else 1

    def position_of(self, beat: float):
        """(battuta, movimento) del beat: la battuta da 1 (0 nel levare), il
        movimento da 1 dentro la battuta."""
        if self._meter is None:
            self.set_meter("4/4", (), 0)
        while not self._starts or self._starts[-1] <= beat:
            self._starts.append(float(next(self._bars)))
        index = max(0, bisect.bisect_right(self._starts, beat) - 1)
        return index + self._first_bar, int(beat - self._starts[index]) + 1

    def set_beat(self, beat):
        if beat is None:
            self._position = tr("battuta {bar} · {beat}", bar=1, beat=1)
        else:
            bar, in_bar = self.position_of(max(0.0, beat))
            self._position = tr("battuta {bar} · {beat}", bar=bar, beat=in_bar)
        self._refresh()

    def _refresh(self):
        big, small = (self._position, self._time) if self._bars_first else (self._time, self._position)
        self._big.setText(big)
        self._small.setText(small)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._bars_first = not self._bars_first
            self._refresh()
        super().mousePressEvent(event)

