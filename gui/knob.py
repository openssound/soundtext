"""
Manopola compatta (Volume/Pan) per le testate della vista Struttura brano
(gui.track_header): un QAbstractSlider disegnato a mano, piccolo abbastanza
da starne due accanto ai pulsanti senza allargare la testata.

- trascinamento verticale (su = aumenta; con Maiusc piu' fine), rotellina e
  frecce/PagSu/PagGiu' da tastiera come un normale slider;
- doppio clic: torna al valore di default (100% il volume, centro il pan);
- 'bipolar': l'arco colorato parte dal centro (pan) invece che dal minimo.

Il valore si legge dentro la manopola, l'etichetta (Vol/Pan) sotto.
"""

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QAbstractSlider

from . import theme

_START_ANGLE = 225.0   # gradi (convenzione Qt: 0 = ore 3, antiorario): minimo in basso a sinistra
_SPAN = 270.0          # fino al massimo in basso a destra
_KNOB = 34             # diametro del disco
_CAPTION_H = 11        # altezza dell'etichetta sotto il disco


class Knob(QAbstractSlider):
    def __init__(self, caption: str, minimum: int, maximum: int, default: int,
                 format_value=str, bipolar: bool = False, parent=None):
        super().__init__(parent)
        self.caption = caption
        self.default = default
        self.format_value = format_value
        self.bipolar = bipolar
        self.setRange(minimum, maximum)
        self.setValue(default)
        self.setSingleStep(1)
        self.setPageStep(max(1, (maximum - minimum) // 10))
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.SizeVerCursor)
        self.setFixedSize(self.sizeHint())
        self._drag_y = None
        self._drag_value = 0.0
        self.valueChanged.connect(self.update)

    def sizeHint(self) -> QSize:
        return QSize(_KNOB + 4, _KNOB + _CAPTION_H)

    # ------------------------------------------------------------ mouse

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_y = event.position().y()
            self._drag_value = float(self.value())
            self.setSliderDown(True)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_y is None:
            return
        y = event.position().y()
        # ~150 px per tutta la corsa; con Maiusc dieci volte piu' fine.
        per_px = (self.maximum() - self.minimum()) / 150.0
        if event.modifiers() & Qt.ShiftModifier:
            per_px /= 10.0
        self._drag_value += (self._drag_y - y) * per_px
        self._drag_value = max(self.minimum(), min(self.maximum(), self._drag_value))
        self._drag_y = y
        self.setValue(round(self._drag_value))
        event.accept()

    def mouseReleaseEvent(self, event):
        if self._drag_y is not None and event.button() == Qt.LeftButton:
            self._drag_y = None
            self.setSliderDown(False)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        # Accettato: non deve arrivare alla testata (che aprirebbe l'editor).
        self.setValue(self.default)
        event.accept()

    # ------------------------------------------------------------ disegno

    def _angle_for(self, value: float) -> float:
        span = self.maximum() - self.minimum()
        frac = 0.0 if span <= 0 else (value - self.minimum()) / span
        return _START_ANGLE - frac * _SPAN

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        light = theme.get_active_theme() == "light"
        colors = theme.track_card_colors()
        text_color = QColor("#333333" if light else "#e0e0e0")
        groove = QColor("#d9d9dd" if light else "#3f3f44")
        face = QColor("#f0f0f2" if light else "#2d2d30")
        accent = QColor(theme.ACCENT)
        if not self.isEnabled():
            accent = QColor(colors["text_dim"])

        x = (self.width() - _KNOB) / 2
        disc = QRectF(x + 2, 2, _KNOB - 4, _KNOB - 4)

        # Solco dell'intera corsa e arco del valore (dal minimo, o dal centro
        # per il pan).
        pen = QPen(groove, 3, Qt.SolidLine, Qt.FlatCap)
        p.setPen(pen)
        p.drawArc(disc, int(_START_ANGLE * 16), int(-_SPAN * 16))
        origin = (self.minimum() + self.maximum()) / 2 if self.bipolar else self.minimum()
        a0, a1 = self._angle_for(origin), self._angle_for(self.value())
        if abs(a1 - a0) > 0.1:
            pen.setColor(accent)
            p.setPen(pen)
            p.drawArc(disc, int(a0 * 16), int((a1 - a0) * 16))

        # Disco interno con il valore scritto dentro.
        inner = disc.adjusted(4, 4, -4, -4)
        p.setPen(Qt.NoPen)
        p.setBrush(face)
        p.drawEllipse(inner)
        if self.hasFocus():
            p.setPen(QPen(accent, 1))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(inner)

        font = QFont(self.font())
        text = self.format_value(self.value())
        font.setPixelSize(9 if len(text) <= 3 else 8)
        font.setBold(True)
        p.setFont(font)
        p.setPen(text_color)
        p.drawText(inner, Qt.AlignCenter, text)

        font.setPixelSize(9)
        font.setBold(False)
        p.setFont(font)
        p.setPen(QColor(colors["text_dim"]))
        p.drawText(QRectF(0, _KNOB - 1, self.width(), _CAPTION_H), Qt.AlignHCenter | Qt.AlignTop, self.caption)
        p.end()
