"""
La riga del Master in fondo alla colonna delle tracce, come l'ultimo canale
di un mixer: volume del mix finale, FX (la catena di effetti del master,
gui.effects_panel) e il misuratore di livello con la spia di clipping
(gui.level_meter). E' larga quanto la colonna delle testate e sta sotto
tutte e due le viste (Struttura e Testo), con accanto la barra di
avanzamento sottile.

Prima il Master stava in testa alla barra dei comandi, accanto a Play, e il
livello in una seconda riga della barra: vedi il piano per la grafica, 3.3.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout

from core.i18n import tr

from . import theme
from .level_meter import LevelMeter

MASTER_STRIP_HEIGHT = 56     # contiene il misuratore a due barre (sinistra e destra)


class MasterStrip(QFrame):
    def __init__(self, width: int, volume: int, on_volume, on_fx, parent=None):
        super().__init__(parent)
        self.setObjectName("masterStrip")
        self.setFixedSize(width, MASTER_STRIP_HEIGHT)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 8, 6)
        layout.setSpacing(4)
        row = QHBoxLayout()
        row.setSpacing(6)
        self.title = QLabel(tr("Master"))
        self.title.setFont(QFont(self.font().family(), 9, QFont.Bold))
        row.addWidget(self.title)
        self.fx_btn = QPushButton("FX")
        self.fx_btn.setObjectName("masterFx")
        self.fx_btn.setFixedHeight(20)
        self.fx_btn.setMinimumWidth(40)
        self.fx_btn.setAccessibleName(tr("Effetti sul master"))
        self.fx_btn.clicked.connect(on_fx)
        row.addWidget(self.fx_btn)
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 200)
        self.vol_slider.setValue(volume)
        self.vol_slider.setToolTip(tr("Volume master: scala il volume di tutte le tracce insieme, "
                                      "in aggiunta al volume di ciascuna (100% = guadagno originale)."))
        self.vol_slider.setAccessibleName(tr("Volume master"))
        self.vol_slider.valueChanged.connect(on_volume)
        row.addWidget(self.vol_slider, 1)
        self.vol_label = QLabel(f"{volume}%")
        self.vol_label.setFixedWidth(38)
        self.vol_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addWidget(self.vol_label)
        layout.addLayout(row)
        self.meter = LevelMeter()
        self.meter.setFixedWidth(width - 18)
        layout.addWidget(self.meter)
        self.refresh_style()

    def refresh_style(self):
        """Lo stesso aspetto delle testate delle tracce (gui.track_header),
        con la striscia a sinistra nel colore dell'accento."""
        colors = theme.track_card_colors()
        self.setStyleSheet(
            f"QFrame#masterStrip {{ background-color: {colors['bg']}; border: none; "
            f"border-left: 4px solid {theme.ACCENT}; border-top: 1px solid {colors['border']}; }}"
            "QFrame#masterStrip QPushButton#masterFx { padding: 0px 6px; font-size: 11px; font-weight: bold; }")
