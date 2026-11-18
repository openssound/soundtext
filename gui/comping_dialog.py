"""
Comping di una clip con piu' riprese (core.audio_takes): le riprese una
sotto l'altra con la loro forma d'onda; trascinando su una corsia si sceglie
quella ripresa per quel tratto. In cima la riga "Comp" mostra il risultato,
con il colore della ripresa scelta in ogni tratto. Ok divide la clip nei
tratti scelti (core.audio_takes.comp_clip), con le dissolvenze incrociate
nei punti di cambio.
"""

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from core import audio_takes, audio_tracks
from core.i18n import tr

LABEL_WIDTH = 120
COMP_ROW = 26
LANE_HEIGHT = 52
SNAP_BEATS = 0.25           # aggancio della scelta (Shift: libera), come il taglio delle clip
TAKE_COLORS = ("#5aa9e6", "#e6a35a", "#7bc96f", "#c97bd0", "#e66b6b", "#d8c85a", "#5ad1c9", "#9a9ae6")


def _take_color(index: int) -> QColor:
    return QColor(TAKE_COLORS[index % len(TAKE_COLORS)])


class CompLanes(QWidget):
    """Le corsie delle riprese e la riga del comp. segments: [(inizio, fine,
    ripresa)] in beat, contigui, dall'inizio alla fine della clip."""
    changed = Signal()

    def __init__(self, clip, start_beat: float, end_beat: float, parent=None):
        super().__init__(parent)
        self.clip = clip
        self.start_beat, self.end_beat = start_beat, end_beat
        self.segments = [(start_beat, end_beat, clip.active_take)]
        self._drag = None          # (corsia, beat di partenza, beat attuale)
        self._peaks = {}
        self.setMinimumSize(560, COMP_ROW + LANE_HEIGHT * len(clip.takes) + 4)
        self.setMouseTracking(True)

    # ------------------------------------------------------------ geometria

    def _x(self, beat: float) -> float:
        width = max(1, self.width() - LABEL_WIDTH - 4)
        return LABEL_WIDTH + (beat - self.start_beat) / max(1e-9, self.end_beat - self.start_beat) * width

    def _beat(self, x: float, free: bool) -> float:
        width = max(1, self.width() - LABEL_WIDTH - 4)
        beat = self.start_beat + (x - LABEL_WIDTH) / width * (self.end_beat - self.start_beat)
        if not free:
            beat = round(beat / SNAP_BEATS) * SNAP_BEATS
        return max(self.start_beat, min(self.end_beat, beat))

    def _lane_at(self, y: float):
        lane = int((y - COMP_ROW) // LANE_HEIGHT)
        return lane if y >= COMP_ROW and 0 <= lane < len(self.clip.takes) else None

    def _lane_rect(self, lane: int) -> QRectF:
        return QRectF(LABEL_WIDTH, COMP_ROW + lane * LANE_HEIGHT + 2, self.width() - LABEL_WIDTH - 4, LANE_HEIGHT - 4)

    # ------------------------------------------------------------ scelta

    def choose(self, lane: int, start: float, end: float):
        self.segments = audio_takes.assign_range(self.segments, start, end, lane)
        self.update()
        self.changed.emit()

    def mousePressEvent(self, event):
        lane = self._lane_at(event.position().y())
        if lane is None or event.button() != Qt.LeftButton:
            return
        free = bool(event.modifiers() & Qt.ShiftModifier)
        beat = self._beat(event.position().x(), free)
        self._drag = (lane, beat, beat)
        self.update()

    def mouseMoveEvent(self, event):
        if self._drag is None:
            return
        lane, start, _ = self._drag
        self._drag = (lane, start, self._beat(event.position().x(), bool(event.modifiers() & Qt.ShiftModifier)))
        self.update()

    def mouseReleaseEvent(self, event):
        if self._drag is None:
            return
        lane, start, end = self._drag
        self._drag = None
        if abs(end - start) < 1e-9:
            # un click senza trascinare: tutto il tratto del comp sotto il mouse
            beat = self._beat(event.position().x(), True)
            seg = next((s for s in self.segments if s[0] <= beat <= s[1]), None)
            if seg is not None:
                start, end = seg[0], seg[1]
        self.choose(lane, start, end)

    # ------------------------------------------------------------ disegno

    def _lane_peaks(self, lane: int, buckets: int):
        key = (lane, buckets)
        if key not in self._peaks:
            self._peaks[key] = audio_takes.take_waveform(self.clip, lane, buckets)
        return self._peaks[key]

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), self.palette().window())
        text_color = self.palette().windowText().color()
        p.setFont(_app_font(12))
        # riga del comp
        p.setPen(text_color)
        p.drawText(QRectF(4, 0, LABEL_WIDTH - 8, COMP_ROW), Qt.AlignVCenter | Qt.AlignLeft, tr("Comp"))
        for a, b, take in self.segments:
            rect = QRectF(self._x(a), 3, self._x(b) - self._x(a), COMP_ROW - 6)
            p.fillRect(rect, _take_color(take))
            p.setPen(QPen(QColor("#10151a")))
            p.drawText(rect.adjusted(4, 0, -2, 0), Qt.AlignVCenter | Qt.AlignLeft | Qt.TextSingleLine,
                       self.clip.takes[take].name)
        for lane, take in enumerate(self.clip.takes):
            rect = self._lane_rect(lane)
            p.setPen(text_color)
            label = QRectF(4, rect.top(), LABEL_WIDTH - 8, rect.height())
            p.drawText(label, Qt.AlignVCenter | Qt.AlignLeft | Qt.TextSingleLine, take.name)
            base = QColor(_take_color(lane))
            dim = QColor(base)
            dim.setAlpha(60)
            p.fillRect(rect, dim)
            for a, b, chosen in self.segments:          # dove la ripresa e' quella scelta
                if chosen == lane:
                    used = QColor(base)
                    used.setAlpha(170)
                    p.fillRect(QRectF(self._x(a), rect.top(), self._x(b) - self._x(a), rect.height()), used)
            buckets = max(1, int(rect.width() / 2))
            peaks = self._lane_peaks(lane, buckets)
            if peaks is not None:
                mid, half = rect.center().y(), rect.height() / 2 - 3
                step = rect.width() / buckets
                p.setPen(QPen(QColor(16, 21, 26, 170), 1))
                for i, peak in enumerate(peaks):
                    x = rect.left() + (i + 0.5) * step
                    h = max(0.5, float(peak) * half)
                    p.drawLine(QPointF(x, mid - h), QPointF(x, mid + h))
        if self._drag is not None:
            lane, a, b = self._drag
            rect = self._lane_rect(lane)
            sel = QRectF(self._x(min(a, b)), rect.top(), abs(self._x(b) - self._x(a)), rect.height())
            p.setPen(QPen(QColor("#ffffff"), 2))
            p.setBrush(Qt.NoBrush)
            p.drawRect(sel)
        # stanghette dei punti di cambio
        p.setPen(QPen(text_color, 1, Qt.DashLine))
        for a, _b, _t in self.segments[1:]:
            p.drawLine(QPointF(self._x(a), 0), QPointF(self._x(a), self.height()))
        p.end()


class CompingDialog(QDialog):
    def __init__(self, parent, clip, tempo_map, player_factory=None):
        super().__init__(parent)
        self.clip = clip
        self.tempo_map = tempo_map
        self._player = None
        self._player_factory = player_factory
        start = clip.start_beat
        end = start + audio_tracks.clip_duration_beats(clip, tempo_map)
        self.setWindowTitle(tr("Comping — {name}", name=clip.name))
        self.resize(820, 140 + COMP_ROW + LANE_HEIGHT * len(clip.takes))
        layout = QVBoxLayout(self)
        hint = QLabel(tr("Trascina su una ripresa per usarla in quel tratto (Shift: senza aggancio); un click "
                         "sceglie la ripresa per tutto il tratto sotto il mouse. Nei punti di cambio va una "
                         "dissolvenza incrociata di 10 ms."))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.lanes = CompLanes(clip, start, end)
        layout.addWidget(self.lanes, 1)

        row = QHBoxLayout()
        self.play_btn = QPushButton(tr("▶ Ascolta il comp"))
        self.play_btn.clicked.connect(self.toggle_listen)
        row.addWidget(self.play_btn)
        row.addStretch(1)
        self.keep_takes_check = QCheckBox(tr("Tieni tutte le riprese nei tratti (per rifare il comping)"))
        self.keep_takes_check.setChecked(True)
        row.addWidget(self.keep_takes_check)
        layout.addLayout(row)

        self._listen_timer = QTimer(self)
        self._listen_timer.setInterval(200)
        self._listen_timer.timeout.connect(self._check_listening)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText(tr("Applica il comp"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def result_clips(self):
        """Le clip del comp (vedi core.audio_takes.comp_clip)."""
        parts = audio_takes.comp_clip(self.clip, self.lanes.segments, self.tempo_map)
        if not self.keep_takes_check.isChecked():
            for part in parts:
                audio_takes.keep_only_active_take(part)
        return parts

    def _comp_audio(self):
        import numpy as np
        from core.tempo_map import seconds_for_beats
        parts = audio_takes.comp_clip(self.clip, self.lanes.segments, self.tempo_map)
        offset = seconds_for_beats(self.tempo_map, self.clip.start_beat)
        layers = []
        for part in parts:
            start = seconds_for_beats(self.tempo_map, part.start_beat) - offset
            layers.append(audio_tracks.AudioLayer(
                path=part.file, start_seconds=max(0.0, start), trim_start=part.trim_start, trim_end=part.trim_end,
                gain=audio_tracks.db_to_gain(part.gain_db), pan=64, fade_in=part.fade_in, fade_out=part.fade_out,
                fade_shape=part.fade_shape, stretch=audio_tracks._stretch(part)))
        return audio_tracks.mix_layers(np.zeros((0, 2), dtype=np.float32), audio_tracks.AUDIO_SAMPLE_RATE, layers)

    def toggle_listen(self):
        from core.audio_recording import TakePlayer
        if self._player is not None:
            self.stop_listening()
            return
        player = TakePlayer(self._comp_audio(), audio_tracks.AUDIO_SAMPLE_RATE, stream_factory=self._player_factory)
        try:
            player.start()
        except Exception as e:
            QMessageBox.warning(self, tr("Ascolto non riuscito"), str(e))
            return
        self._player = player
        self.play_btn.setText(tr("■ Ferma"))
        self._listen_timer.start()

    def _check_listening(self):
        if self._player is not None and not self._player.playing:
            self.stop_listening()

    def stop_listening(self):
        self._listen_timer.stop()
        if self._player is not None:
            self._player.stop()
            self._player = None
        self.play_btn.setText(tr("▶ Ascolta il comp"))

    def done(self, result):
        self.stop_listening()
        super().done(result)


def _app_font(pixels: int) -> QFont:
    """Il carattere del programma a 'pixels' px (non "Sans" fisso)."""
    from PySide6.QtWidgets import QApplication
    font = QFont(QApplication.font())
    font.setPixelSize(pixels)
    return font
