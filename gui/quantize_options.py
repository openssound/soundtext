"""
Le opzioni della quantizzazione regolabile (core.audio_quantize.
QuantizeSettings) in un pannello solo, usato sotto la scelta della griglia
in "Importa audio", "Suona con la tastiera" e "Converti la traccia in
notazione": forza, finestra di cattura, swing e pulizia. Chiuso di base
(una riga "Regola la quantizzazione"); i valori scelti si ricordano.
"""

import dataclasses

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSpinBox, QToolButton, QVBoxLayout, QWidget

from core import settings as app_settings
from core.audio_quantize import SWING_GRIDS, QuantizeSettings
from core.i18n import tr


class QuantizeOptionsWidget(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.toggle = QToolButton()
        self.toggle.setText(tr("Regola la quantizzazione"))
        self.toggle.setCheckable(True)
        self.toggle.setAutoRaise(True)
        self.toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle.toggled.connect(self._on_toggled)
        layout.addWidget(self.toggle)

        self.panel = QWidget()
        rows = QVBoxLayout(self.panel)
        rows.setContentsMargins(16, 0, 0, 0)
        first, second = QHBoxLayout(), QHBoxLayout()
        self.strength_spin = self._spin(first, tr("Forza:"), 0, 100, "%", tr(
            "Di quanto ogni nota si sposta verso la griglia: 100% la porta sulla griglia, 50% a meta' "
            "strada. Sotto il 100% (e con lo swing) il testo si scrive a 1/64, per tenere le sfumature."))
        self.window_spin = self._spin(first, tr("Finestra:"), 0, 100, "%", tr(
            "Si correggono solo le note vicine alla griglia (100% = tutte; 50% = entro un quarto di "
            "suddivisione): gli anticipi e i ritardi piu' grandi, voluti, restano."))
        self.swing_spin = self._spin(first, tr("Swing:"), 50, 75, "%", tr(
            "Con la griglia da 1/8 o 1/16 la seconda suddivisione di ogni coppia va piu' tardi: 50% = "
            "dritto, 66% = shuffle in terzine. Cosi' un'esecuzione swing non viene raddrizzata."))
        first.addStretch(1)
        self.min_note_spin = self._spin(second, tr("Scarta le note piu' corte di:"), 0, 500, " ms", tr(
            "Toglie le note brevissime, come una corda sfiorata o un tasto premuto per sbaglio."))
        self.merge_spin = self._spin(second, tr("Unisci le note uguali entro:"), 0, 500, " ms", tr(
            "Due note uguali di fila, separate da meno di cosi', diventano una nota sola (un attacco "
            "riconosciuto due volte)."))
        second.addStretch(1)
        rows.addLayout(first)
        rows.addLayout(second)
        layout.addWidget(self.panel)
        self._load()
        self.panel.setVisible(False)

    def _spin(self, row, label, low, high, suffix, tooltip):
        caption = QLabel(label)
        spin = QSpinBox()
        spin.setRange(low, high)
        spin.setSuffix(suffix)
        spin.setToolTip(tooltip)
        caption.setToolTip(tooltip)
        spin.valueChanged.connect(self._on_value_changed)
        row.addWidget(caption)
        row.addWidget(spin)
        row.addSpacing(8)
        return spin

    def _on_toggled(self, shown: bool):
        self.panel.setVisible(shown)
        self.toggle.setArrowType(Qt.DownArrow if shown else Qt.RightArrow)

    def _on_value_changed(self, _value):
        self._update_toggle_text()
        self.changed.emit()

    def _update_toggle_text(self):
        custom = self.settings() != QuantizeSettings()
        self.toggle.setText(tr("Regola la quantizzazione (valori personalizzati)") if custom
                            else tr("Regola la quantizzazione"))

    def _load(self):
        values = dataclasses.asdict(QuantizeSettings())
        values.update({k: v for k, v in app_settings.get_quantize_settings().items() if k in values})
        self.set_settings(QuantizeSettings(**values))

    def set_settings(self, s: QuantizeSettings):
        for spin, value in ((self.strength_spin, s.strength * 100), (self.window_spin, s.window * 100),
                            (self.swing_spin, s.swing * 100), (self.min_note_spin, s.min_note_sec * 1000),
                            (self.merge_spin, s.merge_gap_sec * 1000)):
            spin.blockSignals(True)
            spin.setValue(int(round(value)))
            spin.blockSignals(False)
        self._update_toggle_text()
        self._on_toggled(self.toggle.isChecked())

    def set_grid(self, denominator: int, ternary: bool):
        """Lo swing vale solo sulle griglie da 1/8 e 1/16 dritte."""
        self.swing_spin.setEnabled(denominator in SWING_GRIDS and not ternary)

    def settings(self) -> QuantizeSettings:
        swing = self.swing_spin.value() / 100.0 if self.swing_spin.isEnabled() else 0.5
        return QuantizeSettings(strength=self.strength_spin.value() / 100.0, window=self.window_spin.value() / 100.0,
                                swing=swing, min_note_sec=self.min_note_spin.value() / 1000.0,
                                merge_gap_sec=self.merge_spin.value() / 1000.0)

    def remember(self):
        """Salva le scelte (fatto alla conferma del dialogo, come la griglia)."""
        default = dataclasses.asdict(QuantizeSettings())
        current = dataclasses.asdict(self.settings())
        if not self.swing_spin.isEnabled():
            current["swing"] = self.swing_spin.value() / 100.0
        app_settings.set_quantize_settings({k: v for k, v in current.items() if v != default[k]})
