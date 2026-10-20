"""
"Ricava il tempo dalla ripresa..." (tasto destro su una clip audio): il
tempo dell'esecuzione battuta per battuta (core.beat_track), con la curva,
e la battuta su cui cade il primo battito. Applicando, il brano prende quel
tempo (core.performance_tempo.apply_performance_tempo) oppure resta a un
tempo fisso e la ripresa si adatta (warp_to_fixed_tempo).
"""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QButtonGroup, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel, QRadioButton, QSpinBox,
    QVBoxLayout, QWidget,
)

from core.beat_track import BeatAnalysis, tempo_spread
from core.i18n import tr
from .theme import ACCENT


class TempoCurve(QWidget):
    """Il tempo di ogni battuta, come una linea."""

    def __init__(self, tempos, parent=None):
        super().__init__(parent)
        self.tempos = list(tempos)
        self.setMinimumSize(420, 110)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(40, 8, -8, -18)
        text = self.palette().windowText().color()
        if not self.tempos:
            p.end()
            return
        lo, hi = min(self.tempos), max(self.tempos)
        if hi - lo < 4:
            lo, hi = lo - 2, hi + 2
        p.setFont(QFont("Sans", 8))
        p.setPen(text)
        p.drawText(QRectF(0, rect.top() - 6, 36, 14), Qt.AlignRight | Qt.AlignVCenter, str(hi))
        p.drawText(QRectF(0, rect.bottom() - 8, 36, 14), Qt.AlignRight | Qt.AlignVCenter, str(lo))
        grid = QColor(text)
        grid.setAlpha(60)
        p.setPen(QPen(grid, 1))
        p.drawRect(rect)
        n = len(self.tempos)

        def point(i, bpm):
            x = rect.left() + (i + 0.5) / n * rect.width()
            return QPointF(x, rect.bottom() - (bpm - lo) / (hi - lo) * rect.height())

        p.setPen(QPen(QColor(ACCENT), 2))
        p.drawPolyline(QPolygonF([point(i, b) for i, b in enumerate(self.tempos)]))
        p.setPen(text)
        p.drawText(QRectF(rect.left(), rect.bottom() + 2, rect.width(), 14), Qt.AlignCenter,
                   tr("battute 1-{n} della ripresa", n=n))
        p.end()


class TempoFromTakeDialog(QDialog):
    def __init__(self, parent, clip_name: str, analysis: BeatAnalysis, suggested_bar: int):
        super().__init__(parent)
        self.analysis = analysis
        self.setWindowTitle(tr("Tempo dalla ripresa — {name}", name=clip_name))
        layout = QVBoxLayout(self)
        lo, hi = tempo_spread(analysis)
        summary = tr("Tempo dell'esecuzione: in media {mean} BPM, da {lo} a {hi}, su {n} battute.",
                     mean=f"{analysis.mean_bpm:.1f}", lo=lo, hi=hi, n=analysis.bars)
        layout.addWidget(QLabel(summary))
        layout.addWidget(TempoCurve(analysis.bar_tempos), 1)
        form = QFormLayout()
        self.bar_spin = QSpinBox()
        self.bar_spin.setRange(1, 9999)
        self.bar_spin.setValue(max(1, suggested_bar))
        self.bar_spin.setToolTip(tr("La clip si sposta perche' il suo primo battito cada sull'inizio di "
                                    "questa battuta."))
        form.addRow(tr("Il primo battito e' l'inizio della battuta:"), self.bar_spin)
        layout.addLayout(form)
        self.follow_radio = QRadioButton(tr("Il brano segue il tempo dell'esecuzione"))
        self.follow_radio.setToolTip(tr(
            "Un cambio di tempo per battuta: le note scritte, il metronomo e i generatori seguono "
            "l'esecuzione. Dopo la ripresa torna il tempo di prima."))
        self.fixed_radio = QRadioButton(tr("Tempo fisso, la ripresa si adatta:"))
        self.fixed_radio.setToolTip(tr(
            "Il brano resta a questo tempo e la ripresa si divide a ogni battuta: ogni pezzo si allunga "
            "o si accorcia (time-stretch, senza cambiare l'intonazione) per durare una battuta giusta."))
        group = QButtonGroup(self)
        group.addButton(self.follow_radio)
        group.addButton(self.fixed_radio)
        self.follow_radio.setChecked(True)
        self.bpm_spin = QSpinBox()
        self.bpm_spin.setRange(20, 400)
        self.bpm_spin.setSuffix(" BPM")
        self.bpm_spin.setValue(int(round(analysis.mean_bpm)) or 120)
        self.bpm_spin.setEnabled(False)
        self.fixed_radio.toggled.connect(self.bpm_spin.setEnabled)
        layout.addWidget(self.follow_radio)
        fixed_row = QHBoxLayout()
        fixed_row.addWidget(self.fixed_radio)
        fixed_row.addWidget(self.bpm_spin)
        fixed_row.addStretch(1)
        layout.addLayout(fixed_row)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText(tr("Applica il tempo"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def first_bar(self) -> int:
        return self.bar_spin.value()

    def fixed_bpm(self):
        """Il tempo fisso scelto, o None se il brano segue l'esecuzione."""
        return self.bpm_spin.value() if self.fixed_radio.isChecked() else None
