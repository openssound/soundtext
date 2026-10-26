"""
Editor della clip: la forma d'onda grande di una clip audio, con lo zoom
fino al singolo campione (rotella; Shift+rotella scorre), la selezione di
un tratto trascinando, e sul tratto: ascoltarlo, silenziarlo, attenuarlo,
togliere le modifiche, dividere la clip ai suoi bordi. Silenziare e
attenuare scrivono la curva del volume della clip (AudioClip.gain_points,
core.audio_tracks.adjust_gain_range): il file non cambia e Ctrl+Z annulla.
"""

from typing import Optional, Tuple

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QInputDialog, QLabel, QMessageBox, QPushButton, QScrollBar, QVBoxLayout, QWidget,
)

from core import audio_tracks
from core.i18n import tr

from .theme import ACCENT, dim, text_dim

MIN_VISIBLE_SAMPLES = 64        # zoom massimo: tanti campioni su tutta la larghezza
CURVE_TOP_DB, CURVE_BOTTOM_DB = 6.0, -40.0
RULER_PX = 18


class WaveformView(QWidget):
    """La forma d'onda (mono) di 'samples' a 'rate', fra view_start e
    view_end secondi, con la selezione e la curva del volume."""
    selection_changed = Signal()
    view_changed = Signal()

    def __init__(self, samples: np.ndarray, rate: int, parent=None):
        super().__init__(parent)
        self.setMinimumSize(640, 240)
        self.setMouseTracking(True)
        mono = samples.mean(axis=1) if samples.ndim == 2 else samples
        self.mono = np.ascontiguousarray(mono, dtype=np.float32)
        self.rate = rate
        self.total = len(self.mono) / rate if rate else 0.0
        self.view_start, self.view_end = 0.0, max(self.total, 1e-3)
        self.selection: Optional[Tuple[float, float]] = None
        self.gain_points = []
        self._drag_from = None

    # --- coordinate ---------------------------------------------------------

    def _x_of(self, t: float) -> float:
        span = max(1e-9, self.view_end - self.view_start)
        return (t - self.view_start) / span * self.width()

    def _t_of(self, x: float) -> float:
        span = self.view_end - self.view_start
        return max(0.0, min(self.total, self.view_start + x / max(1, self.width()) * span))

    def set_view(self, start: float, end: float):
        min_span = MIN_VISIBLE_SAMPLES / self.rate
        span = max(min_span, min(self.total, end - start)) if self.total > 0 else 1e-3
        start = max(0.0, min(start, self.total - span))
        self.view_start, self.view_end = start, start + span
        self.update()
        self.view_changed.emit()

    def zoom(self, factor: float, around: Optional[float] = None):
        """factor < 1 avvicina, > 1 allontana, attorno al tempo 'around'."""
        around = (self.view_start + self.view_end) / 2 if around is None else around
        span = (self.view_end - self.view_start) * factor
        p = (around - self.view_start) / max(1e-9, self.view_end - self.view_start)
        self.set_view(around - p * span, around - p * span + span)

    def show_all(self):
        self.set_view(0.0, self.total)

    # --- disegno ------------------------------------------------------------

    def _db_to_y(self, db: float) -> float:
        top, h = RULER_PX + 2, self.height() - RULER_PX - 4
        p = (CURVE_TOP_DB - max(CURVE_BOTTOM_DB, min(CURVE_TOP_DB, db))) / (CURVE_TOP_DB - CURVE_BOTTOM_DB)
        return top + p * h

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#1b1d21"))
        w, h = self.width(), self.height()
        top = RULER_PX
        mid = top + (h - top) / 2
        half = (h - top) / 2 - 4
        if self.selection is not None:
            a, b = self.selection
            painter.fillRect(QRectF(self._x_of(a), top, max(1.0, self._x_of(b) - self._x_of(a)), h - top),
                             QColor(90, 169, 230, 70))
        first = int(self.view_start * self.rate)
        last = min(len(self.mono), int(np.ceil(self.view_end * self.rate)) + 1)
        part = self.mono[first:last]
        painter.setPen(QPen(QColor("#9fd3ff"), 1))
        if len(part) > 0:
            per_px = len(part) / max(1, w)
            if per_px > 1.5:
                edges = np.linspace(0, len(part), w + 1).astype(int)
                edges = np.minimum(edges, len(part) - 1)
                lo = np.minimum.reduceat(part, edges[:-1])
                hi = np.maximum.reduceat(part, edges[:-1])
                for x in range(w):
                    painter.drawLine(QPointF(x + 0.5, mid - hi[x] * half), QPointF(x + 0.5, mid - lo[x] * half))
            else:
                # fino al singolo campione: una linea che li unisce, e i punti
                xs = [self._x_of((first + i) / self.rate) for i in range(len(part))]
                line = QPolygonF([QPointF(x, mid - v * half) for x, v in zip(xs, part)])
                painter.drawPolyline(line)
                if per_px < 0.25:
                    painter.setBrush(QColor("#9fd3ff"))
                    for x, v in zip(xs, part):
                        painter.drawEllipse(QPointF(x, mid - v * half), 2, 2)
        painter.setPen(QPen(QColor(text_dim()), 1, Qt.DotLine))
        painter.drawLine(QPointF(0, mid), QPointF(w, mid))
        if self.gain_points:
            xs = np.linspace(self.view_start, self.view_end, max(2, w // 3))
            dbs = audio_tracks.gain_curve_db(xs, self.gain_points)
            painter.setPen(QPen(QColor("#ffd54f"), 1.5))
            painter.drawPolyline(QPolygonF([QPointF(self._x_of(t), self._db_to_y(float(db)))
                                            for t, db in zip(xs, dbs)]))
        self._paint_ruler(painter)
        painter.end()

    def _paint_ruler(self, painter):
        painter.fillRect(QRectF(0, 0, self.width(), RULER_PX), QColor("#25282d"))
        span = self.view_end - self.view_start
        step = 10 ** np.floor(np.log10(max(span, 1e-6) / 8))
        for mult in (1, 2, 5, 10):
            if span / (step * mult) <= 10:
                step *= mult
                break
        painter.setPen(QPen(QColor(text_dim()), 1))
        t = np.ceil(self.view_start / step) * step
        decimals = max(0, int(-np.floor(np.log10(step))))
        while t <= self.view_end:
            x = self._x_of(t)
            painter.drawLine(QPointF(x, RULER_PX - 5), QPointF(x, RULER_PX))
            painter.drawText(QPointF(x + 3, RULER_PX - 6), f"{t:.{decimals}f} s")
            t += step

    # --- mouse --------------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_from = self._t_of(event.position().x())
            self.selection = None
            self.update()
            self.selection_changed.emit()

    def mouseMoveEvent(self, event):
        if self._drag_from is not None:
            t = self._t_of(event.position().x())
            a, b = sorted((self._drag_from, t))
            self.selection = (a, b) if b - a > 0 else None
            self.update()
            self.selection_changed.emit()

    def mouseReleaseEvent(self, event):
        self._drag_from = None

    def mouseDoubleClickEvent(self, event):
        self.selection = None
        self.update()
        self.selection_changed.emit()

    def wheelEvent(self, event):
        delta = event.angleDelta().y() or event.angleDelta().x()
        if not delta:
            return
        if event.modifiers() & Qt.ShiftModifier:
            span = self.view_end - self.view_start
            self.set_view(self.view_start - delta / 120 * span * 0.1, self.view_end - delta / 120 * span * 0.1)
        else:
            self.zoom(0.8 if delta > 0 else 1.25, self._t_of(event.position().x()))
        event.accept()


class ClipEditorDialog(QDialog):
    """La finestra dell'editor per la clip 'clip' della traccia
    'track_name' della vista Struttura brano 'view'."""

    def __init__(self, view, track_name: str, clip):
        super().__init__(view)
        self.view = view
        self.track_name = track_name
        self.clip = clip
        self.setWindowTitle(tr("Editor della clip — {name}", name=clip.name))
        samples, rate = audio_tracks.clip_audio(clip)
        self._samples, self._rate = samples, rate
        layout = QVBoxLayout(self)

        tools = QHBoxLayout()
        for label, slot, tip in ((tr("Zoom +"), lambda: self.wave.zoom(0.5), tr("Avvicina (anche con la rotella)")),
                                 (tr("Zoom −"), lambda: self.wave.zoom(2.0), tr("Allontana")),
                                 (tr("Tutta"), lambda: self.wave.show_all(), tr("Tutta la clip")),
                                 (tr("Sulla selezione"), self._zoom_selection, tr("Lo zoom sul tratto scelto"))):
            button = QPushButton(label)
            button.setToolTip(tip)
            button.clicked.connect(slot)
            tools.addWidget(button)
        tools.addStretch(1)
        self.play_btn = QPushButton(tr("▶ Ascolta"))
        self.play_btn.setToolTip(tr("Ascolta il tratto selezionato (o tutta la clip), con la curva del volume."))
        self.play_btn.clicked.connect(self._play)
        tools.addWidget(self.play_btn)
        stop_btn = QPushButton(tr("■ Stop"))
        stop_btn.clicked.connect(self._stop)
        tools.addWidget(stop_btn)
        layout.addLayout(tools)

        self.wave = WaveformView(samples, rate, self)
        self.wave.gain_points = list(clip.gain_points)
        layout.addWidget(self.wave, 1)
        self.scroll = QScrollBar(Qt.Horizontal)
        self.scroll.valueChanged.connect(self._on_scroll)
        layout.addWidget(self.scroll)
        self.wave.view_changed.connect(self._sync_scroll)
        self.wave.selection_changed.connect(self._on_selection)

        self.info = QLabel()
        dim(self.info)
        layout.addWidget(self.info)

        edits = QHBoxLayout()
        self.silence_btn = QPushButton(tr("Silenzia il tratto"))
        self.silence_btn.clicked.connect(lambda: self._apply(None))
        self.attenuate_btn = QPushButton(tr("Attenua il tratto..."))
        self.attenuate_btn.clicked.connect(self._attenuate)
        self.restore_btn = QPushButton(tr("Togli le modifiche nel tratto"))
        self.restore_btn.clicked.connect(self._restore)
        self.split_btn = QPushButton(tr("Dividi ai bordi del tratto"))
        self.split_btn.setToolTip(tr("Divide la clip all'inizio e alla fine del tratto (o nel punto scelto): "
                                     "il tratto diventa una clip a se', da spostare o eliminare."))
        self.split_btn.clicked.connect(self._split)
        for button in (self.silence_btn, self.attenuate_btn, self.restore_btn, self.split_btn):
            edits.addWidget(button)
        edits.addStretch(1)
        close_btn = QPushButton(tr("Chiudi"))
        close_btn.clicked.connect(self.accept)
        edits.addWidget(close_btn)
        layout.addLayout(edits)
        self.resize(1000, 420)
        self._sync_scroll()
        self._on_selection()

    # --- vista --------------------------------------------------------------

    def _sync_scroll(self):
        wave = self.wave
        span = wave.view_end - wave.view_start
        steps = 10000
        self.scroll.blockSignals(True)
        self.scroll.setRange(0, max(0, int(steps * (1 - span / max(wave.total, 1e-9)))))
        self.scroll.setPageStep(max(1, int(steps * span / max(wave.total, 1e-9))))
        self.scroll.setValue(int(steps * wave.view_start / max(wave.total, 1e-9)))
        self.scroll.blockSignals(False)

    def _on_scroll(self, value):
        wave = self.wave
        span = wave.view_end - wave.view_start
        start = value / 10000 * wave.total
        wave.view_start, wave.view_end = start, start + span
        wave.update()

    def _zoom_selection(self):
        if self.wave.selection is not None:
            a, b = self.wave.selection
            margin = (b - a) * 0.05
            self.wave.set_view(a - margin, b + margin)

    def _on_selection(self):
        sel = self.wave.selection
        has = sel is not None and sel[1] - sel[0] > 0
        for button in (self.silence_btn, self.attenuate_btn, self.restore_btn):
            button.setEnabled(has)
        self.split_btn.setEnabled(has)
        if has:
            a, b = sel
            self.info.setText(tr("Selezione: da {a:.3f} a {b:.3f} s ({d:.3f} s)", a=a, b=b, d=b - a))
        else:
            self.info.setText(tr("Trascina sulla forma d'onda per scegliere un tratto; rotella per lo zoom "
                                 "(fino al singolo campione), Shift+rotella per scorrere."))

    # --- modifiche ----------------------------------------------------------

    def _set_points(self, points):
        self.clip.gain_points = [(float(t), float(db)) for t, db in points]
        self.wave.gain_points = list(self.clip.gain_points)
        self.wave.update()
        self.view.on_clip_changed(self.track_name)

    def _apply(self, change_db):
        a, b = self.wave.selection
        self._set_points(audio_tracks.adjust_gain_range(self.clip.gain_points, a, b, change_db))

    def _attenuate(self):
        value, ok = QInputDialog.getDouble(self, tr("Attenua il tratto"), tr("Di quanti dB abbassarlo?"),
                                           6.0, 0.5, 40.0, 1)
        if ok:
            self._apply(value)

    def _restore(self):
        """Il tratto torna com'era: via i punti della curva al suo interno."""
        a, b = self.wave.selection
        ramp = audio_tracks.RANGE_RAMP_SECONDS
        self._set_points([(t, db) for t, db in self.clip.gain_points if not a - ramp - 1e-6 <= t <= b + ramp + 1e-6])

    def _split(self):
        from core.tempo_map import beat_at_elapsed_seconds, seconds_for_beats
        a, b = self.wave.selection
        tempo_map = self.view._tempo_map()
        start_s = seconds_for_beats(tempo_map, self.clip.start_beat)
        cuts = [t for t in (b, a) if audio_tracks.MIN_CLIP_SECONDS < t < self.wave.total - audio_tracks.MIN_CLIP_SECONDS]
        if not cuts:
            QMessageBox.information(self, tr("Dividi"), tr("Il tratto copre tutta la clip: non c'e' niente da dividere."))
            return
        track = self.view.host.project.get_track(self.track_name)
        for t in cuts:                       # prima la fine: la clip resta la prima parte
            second = audio_tracks.split_clip(self.clip, beat_at_elapsed_seconds(tempo_map, 0.0, start_s + t),
                                             tempo_map)
            if second is not None:
                track.audio_clips.append(second)
        self.view.on_clip_changed(self.track_name)     # un solo Ctrl+Z per le due divisioni
        self.accept()

    # --- ascolto ------------------------------------------------------------

    def _play(self):
        from core.audio_tracks import resample
        samples = self._samples
        if self.clip.gain_points:
            samples = audio_tracks.apply_gain_curve(samples, self._rate, self.clip.gain_points)
        sel = self.wave.selection
        if sel is not None and sel[1] - sel[0] > 0.01:
            samples = samples[int(sel[0] * self._rate):int(sel[1] * self._rate)]
        if samples.ndim == 1 or samples.shape[1] == 1:
            samples = np.repeat(samples.reshape(-1, 1), 2, axis=1)
        if self._rate != audio_tracks.AUDIO_SAMPLE_RATE:
            samples = resample(samples, self._rate, audio_tracks.AUDIO_SAMPLE_RATE)
        engine = getattr(self.view, "_preview_engine", None) or self._engine()
        if not engine.play_buffer(samples[:, :2].astype(np.float32), audio_tracks.AUDIO_SAMPLE_RATE):
            QMessageBox.information(self, tr("Ascolta"), tr("L'ascolto richiede la riproduzione diretta "
                                                            "(libreria sounddevice)."))

    def _engine(self):
        from core.playback import PlaybackEngine
        if not hasattr(self, "_own_engine"):
            self._own_engine = PlaybackEngine()
        return self._own_engine

    def _stop(self):
        engine = getattr(self, "_own_engine", None)
        if engine is not None:
            engine.stop()

    def done(self, result):
        self._stop()
        super().done(result)
