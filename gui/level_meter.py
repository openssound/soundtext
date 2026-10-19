"""Indicatore di livello del master con spia di clipping (vedi core.levels).

La barra va da METER_FLOOR_DB a 0 dBFS: verde fino a -12, gialla fino a
-3, rossa oltre. Il segno del picco resta fermo un attimo e poi scende. La
spia CLIP si accende quando il master clippa e resta accesa (anche dopo
lo Stop e nei nuovi ascolti) finche' non la si clicca.
"""

import time

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from core.i18n import tr
from core.levels import to_dbfs
from .theme import BAD, GOOD, WARN

METER_FLOOR_DB = -48.0
PEAK_HOLD_SECONDS = 1.0
PEAK_FALL_DB_PER_SECOND = 12.0
LED_WIDTH = 38


def _fraction(db: float) -> float:
    return max(0.0, min(1.0, (db - METER_FLOOR_DB) / -METER_FLOOR_DB))


class LevelMeter(QWidget):
    clipResetRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(18)
        self.setMinimumWidth(150)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setFixedWidth(170)
        self._db = METER_FLOOR_DB
        self._peak_db = METER_FLOOR_DB
        self._peak_time = 0.0
        self._clipped = False
        self._available = True
        self._clip_detail = ""
        self._refresh_tooltip()

    # -- stato --------------------------------------------------------------
    def set_level(self, level: float):
        """Livello attuale (0..1 del fondo scala)."""
        self._db = to_dbfs(level)
        now = time.monotonic()
        if self._db >= self._peak_db:
            self._peak_db, self._peak_time = self._db, now
        elif now - self._peak_time > PEAK_HOLD_SECONDS:
            fall = (now - self._peak_time - PEAK_HOLD_SECONDS) * PEAK_FALL_DB_PER_SECOND
            self._peak_db = max(self._db, self._peak_db - fall)
        self.update()

    def set_clipped(self, clipped: bool, detail: str = ""):
        """Accende (o spegne) la spia; 'detail' (le battute) va nel suggerimento."""
        if clipped != self._clipped or detail != self._clip_detail:
            self._clipped, self._clip_detail = clipped, detail
            self._refresh_tooltip()
            self.update()

    def set_available(self, available: bool):
        """False quando la riproduzione non permette di misurare i livelli
        (player esterno, senza streaming): la barra resta grigia."""
        if available != self._available:
            self._available = available
            self._refresh_tooltip()
            self.update()

    def silence(self):
        """Barra a zero (Stop o fine del brano); la spia resta com'e'."""
        self._db = self._peak_db = METER_FLOOR_DB
        self.update()

    @property
    def clipped(self) -> bool:
        return self._clipped

    def _refresh_tooltip(self):
        if not self._available:
            text = tr("Livello del master: non disponibile con questo modo di riproduzione.")
        else:
            text = tr("Livello del master (picco, dBFS). La spia CLIP si accende quando il "
                      "master supera il fondo scala e il suono si rompe; clicca la spia per spegnerla.")
            if self._clipped and self._clip_detail:
                text += "\n" + self._clip_detail
        self.setToolTip(text)

    # -- disegno ------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.position().x() >= self.width() - LED_WIDTH and self._clipped:
            self.set_clipped(False)
            self.clipResetRequested.emit()
        super().mousePressEvent(event)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        pal = self.palette()
        bar = QRectF(0, 3, self.width() - LED_WIDTH - 6, self.height() - 6)
        p.fillRect(bar, pal.base())
        p.setPen(pal.mid().color())
        p.drawRect(bar.adjusted(0, 0, -1, -1))
        if self._available:
            inner = bar.adjusted(1, 1, -1, -1)
            filled = inner.width() * _fraction(self._db)
            # tre zone colorate, disegnate fino al livello attuale
            for lo, hi, color in ((METER_FLOOR_DB, -12.0, GOOD), (-12.0, -3.0, WARN), (-3.0, 0.0, BAD)):
                x0 = inner.left() + inner.width() * _fraction(lo)
                x1 = min(inner.left() + filled, inner.left() + inner.width() * _fraction(hi))
                if x1 > x0:
                    p.fillRect(QRectF(x0, inner.top(), x1 - x0, inner.height()), QColor(color))
            if self._peak_db > METER_FLOOR_DB:
                x = inner.left() + inner.width() * _fraction(self._peak_db)
                p.fillRect(QRectF(min(x, inner.right() - 2), inner.top(), 2, inner.height()),
                           QColor(BAD if self._peak_db > -3 else pal.text().color()))
            # tacche a -24, -12, -6, -3
            p.setPen(pal.mid().color())
            for db in (-24.0, -12.0, -6.0, -3.0):
                x = inner.left() + inner.width() * _fraction(db)
                p.drawLine(int(x), int(inner.bottom()) - 3, int(x), int(inner.bottom()))
        led = QRectF(self.width() - LED_WIDTH, 2, LED_WIDTH, self.height() - 4)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(BAD) if self._clipped else pal.base())
        p.drawRoundedRect(led, 3, 3)
        p.setPen(QColor("#ffffff") if self._clipped else pal.mid().color())
        font = p.font()
        font.setPointSizeF(max(6.5, font.pointSizeF() - 2))
        font.setBold(True)
        p.setFont(font)
        p.drawText(led, Qt.AlignCenter, "CLIP")
        p.end()


class TrackMeter(QWidget):
    """Vu-meter verticale sottile di una traccia (nella sua testata):
    durante l'ascolto il livello (vedi core.levels.TrackLevels), con un
    segno di picco; la cima diventa rossa e resta rossa (fino al prossimo
    ascolto) se la traccia supera il fondo scala. Fuori dall'ascolto puo'
    mostrare il picco misurato da Analizza livelli (set_static)."""

    WIDTH = 5

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(self.WIDTH)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self._db = METER_FLOOR_DB
        self._peak_db = METER_FLOOR_DB
        self._peak_time = 0.0
        self._over = False
        self._static = None          # (picco dB, clippa) da Analizza livelli

    def set_level(self, level: float):
        self._db = to_dbfs(level)
        if level >= 1.0:
            self._over = True
        now = time.monotonic()
        if self._db >= self._peak_db:
            self._peak_db, self._peak_time = self._db, now
        elif now - self._peak_time > PEAK_HOLD_SECONDS:
            fall = (now - self._peak_time - PEAK_HOLD_SECONDS) * PEAK_FALL_DB_PER_SECOND
            self._peak_db = max(self._db, self._peak_db - fall)
        self.update()

    def start(self):
        """Nuovo ascolto: la spia rossa riparte spenta."""
        self._over = False
        self.silence()

    def silence(self):
        self._db = self._peak_db = METER_FLOOR_DB
        self.update()

    def set_static(self, peak_db, clipped: bool = False):
        """Picco da mostrare fuori dall'ascolto (None per toglierlo)."""
        self._static = None if peak_db is None else (peak_db, clipped)
        self.update()

    @property
    def over(self) -> bool:
        return self._over

    def paintEvent(self, _event):
        p = QPainter(self)
        pal = self.palette()
        rect = QRectF(0, 0, self.width(), self.height())
        p.fillRect(rect, pal.base())
        h = rect.height()
        db = self._db
        peak_db = self._peak_db
        if db <= METER_FLOOR_DB and self._static is not None:
            peak_db = self._static[0]
        # dal basso verso l'alto: verde, giallo, rosso
        for lo, hi, color in ((METER_FLOOR_DB, -12.0, GOOD), (-12.0, -3.0, WARN), (-3.0, 0.0, BAD)):
            y_top = h * (1 - min(_fraction(db), _fraction(hi)))
            y_bottom = h * (1 - _fraction(lo))
            if y_bottom > y_top and _fraction(db) > _fraction(lo):
                p.fillRect(QRectF(0, y_top, rect.width(), y_bottom - y_top), QColor(color))
        if peak_db > METER_FLOOR_DB:
            y = h * (1 - _fraction(peak_db))
            p.fillRect(QRectF(0, min(max(0.0, y), h - 2), rect.width(), 2),
                       QColor(BAD if peak_db > -3 else pal.text().color()))
        if self._over or (self._static is not None and self._static[1] and db <= METER_FLOOR_DB):
            p.fillRect(QRectF(0, 0, rect.width(), 4), QColor(BAD))
        p.end()
