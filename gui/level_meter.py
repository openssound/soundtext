"""Indicatore di livello del master con spia di clipping (vedi core.levels).

Due barre, il canale sinistro sopra e il destro sotto, da METER_FLOOR_DB a
0 dBFS: verdi fino a -12, gialle fino a -3, rosse oltre. Il segno del picco
di ciascuna resta fermo un attimo e poi scende. La
spia CLIP si accende quando il master clippa e resta accesa (anche dopo
lo Stop e nei nuovi ascolti) finche' non la si clicca.
"""

import time

from PySide6.QtCore import QEvent, QPoint, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCursor, QPainter
from PySide6.QtWidgets import QApplication, QLabel, QSizePolicy, QWidget
from shiboken6 import isValid

from core.i18n import tr
from core.levels import to_dbfs
from .theme import BAD, GOOD, WARN, text_dim, tooltip_style

METER_FLOOR_DB = -48.0
PEAK_HOLD_SECONDS = 1.0
PEAK_FALL_DB_PER_SECOND = 12.0
LED_WIDTH = 38


class HoverTip(QLabel):
    """Un suggerimento che SoundText mostra e nasconde da se', sopra il
    widget e dentro l'area utile dello schermo, con il testo a capo; resta
    finche' il cursore e' sul widget (lo si controlla ogni 150 ms) e si
    aggiorna se il testo cambia. Al posto di QToolTip per l'indicatore in
    fondo alla finestra: li' il gestore delle finestre spingeva il
    suggerimento contro il cursore e Qt lo chiudeva al primo movimento, o
    per un "mouse uscito" che X11 manda quando una finestra compare
    vicino al cursore."""

    def __init__(self, owner: QWidget):
        super().__init__(None, Qt.ToolTip | Qt.FramelessWindowHint)
        self._owner = owner
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setTextFormat(Qt.PlainText)
        self.setWordWrap(True)
        self.setMaximumWidth(380)
        self._poll = QTimer(self)
        self._poll.setInterval(150)
        self._poll.timeout.connect(self._check_cursor)
        owner.destroyed.connect(self.deleteLater)      # e' una finestra a se': va via con il widget

    def popup(self, text: str):
        if not text:
            self.hide()
            return
        self.setStyleSheet(tooltip_style())
        self.setText(text)
        self.adjustSize()
        self._place()
        self.show()
        self.raise_()
        self._poll.start()

    def update_text(self, text: str):
        if self.isVisible():
            self.popup(text)

    def _place(self):
        owner = self._owner
        top_left = owner.mapToGlobal(QPoint(0, 0))
        screen = (owner.screen() or QApplication.primaryScreen()).availableGeometry()
        x = max(screen.left(), min(top_left.x(), screen.right() + 1 - self.width()))
        y = top_left.y() - self.height() - 6
        if y < screen.top():                   # niente spazio sopra: sotto il widget
            y = top_left.y() + owner.height() + 6
        self.move(x, y)

    def _check_cursor(self):
        owner = self._owner
        inside = owner.isVisible() and owner.rect().contains(owner.mapFromGlobal(QCursor.pos()))
        if not inside:
            self.hide()

    def hideEvent(self, event):
        self._poll.stop()
        super().hideEvent(event)


def _fraction(db: float) -> float:
    return max(0.0, min(1.0, (db - METER_FLOOR_DB) / -METER_FLOOR_DB))


class LevelMeter(QWidget):
    clipResetRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(20)
        self.setMinimumWidth(150)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setFixedWidth(170)
        # per canale (0 = sinistro, 1 = destro): livello, picco trattenuto e quando
        self._db = [METER_FLOOR_DB, METER_FLOOR_DB]
        self._peak_db = [METER_FLOOR_DB, METER_FLOOR_DB]
        self._peak_time = [0.0, 0.0]
        self._clipped = False
        self._available = True
        self._clip_detail = ""
        self._tip = HoverTip(self)
        self._refresh_tooltip()

    # -- stato --------------------------------------------------------------
    def set_level(self, level: float):
        """Livello attuale (0..1 del fondo scala), uguale sui due canali."""
        self.set_levels(level, level)

    def set_levels(self, left: float, right: float):
        """Livello attuale del canale sinistro e del destro (0..1 del fondo scala)."""
        now = time.monotonic()
        for ch, level in enumerate((left, right)):
            db = to_dbfs(level)
            self._db[ch] = db
            if db >= self._peak_db[ch]:
                self._peak_db[ch], self._peak_time[ch] = db, now
            elif now - self._peak_time[ch] > PEAK_HOLD_SECONDS:
                fall = (now - self._peak_time[ch] - PEAK_HOLD_SECONDS) * PEAK_FALL_DB_PER_SECOND
                self._peak_db[ch] = max(db, self._peak_db[ch] - fall)
        self.update()

    def levels_db(self):
        """(sinistro, destro) in dBFS: quello che le barre mostrano adesso."""
        return tuple(self._db)

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
        """Barre a zero (Stop o fine del brano); la spia resta com'e'."""
        self._db = [METER_FLOOR_DB, METER_FLOOR_DB]
        self._peak_db = [METER_FLOOR_DB, METER_FLOOR_DB]
        self.update()

    @property
    def clipped(self) -> bool:
        return self._clipped

    def _refresh_tooltip(self):
        if not self._available:
            text = tr("Livello del master: non disponibile con questo modo di riproduzione.")
        else:
            text = tr("Livello del master (picco, dBFS): sopra il canale sinistro, sotto il destro. "
                      "La spia CLIP si accende quando il master supera il fondo scala e il suono si "
                      "rompe; clicca la spia per spegnerla.")
            if self._clipped and self._clip_detail:
                text += "\n\n" + self._clip_detail
        self.setToolTip(text)
        if isValid(self._tip):                 # alla chiusura puo' essere gia' andato
            self._tip.update_text(text)

    def event(self, event):
        # sta in fondo alla finestra: il suggerimento lo mostra HoverTip, sopra
        if event.type() == QEvent.ToolTip:
            self._tip.popup(self.toolTip())
            return True
        return super().event(event)

    def hideEvent(self, event):
        if isValid(self._tip):
            self._tip.hide()
        super().hideEvent(event)

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
            half = (inner.height() - 1) / 2            # due barre, 1 px fra l'una e l'altra
            for ch in (0, 1):
                row = QRectF(inner.left(), inner.top() + ch * (half + 1), inner.width(), half)
                filled = row.width() * _fraction(self._db[ch])
                # tre zone colorate, disegnate fino al livello attuale
                for lo, hi, color in ((METER_FLOOR_DB, -12.0, GOOD), (-12.0, -3.0, WARN), (-3.0, 0.0, BAD)):
                    x0 = row.left() + row.width() * _fraction(lo)
                    x1 = min(row.left() + filled, row.left() + row.width() * _fraction(hi))
                    if x1 > x0:
                        p.fillRect(QRectF(x0, row.top(), x1 - x0, row.height()), QColor(color))
                if self._peak_db[ch] > METER_FLOOR_DB:
                    x = row.left() + row.width() * _fraction(self._peak_db[ch])
                    p.fillRect(QRectF(min(x, row.right() - 2), row.top(), 2, row.height()),
                               QColor(BAD if self._peak_db[ch] > -3 else pal.text().color()))
            # tacche a -24, -12, -6, -3
            p.setPen(pal.mid().color())
            for db in (-24.0, -12.0, -6.0, -3.0):
                x = inner.left() + inner.width() * _fraction(db)
                p.drawLine(int(x), int(inner.bottom()) - 3, int(x), int(inner.bottom()))
        led = QRectF(self.width() - LED_WIDTH, 2, LED_WIDTH, self.height() - 4)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(BAD) if self._clipped else pal.base())
        p.drawRoundedRect(led, 3, 3)
        p.setPen(QColor("#ffffff") if self._clipped else QColor(text_dim()))
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
