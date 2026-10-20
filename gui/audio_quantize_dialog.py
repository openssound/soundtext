"""
"Quantizza l'audio..." (tasto destro su una clip audio): la griglia e la
quantizzazione regolabile (forza, finestra, swing); la clip si taglia agli
attacchi e i pezzi vanno verso la griglia (core.audio_slice.quantize_clip).
"""

from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QVBoxLayout

from core.audio_quantize import grid_slot_beats
from core.i18n import tr
from .audio_import_dialog import TERNARY_ENABLED_GRIDS
from .quantize_options import QuantizeOptionsWidget

GRIDS = (("1/4", 4), ("1/8", 8), ("1/16", 16), ("1/32", 32))


class AudioQuantizeDialog(QDialog):
    def __init__(self, parent, clip_name: str, attack_count: int):
        super().__init__(parent)
        self.setWindowTitle(tr("Quantizza l'audio — {name}", name=clip_name))
        layout = QVBoxLayout(self)
        info = QLabel(tr("Attacchi trovati: {n}. La clip si taglia poco prima di ognuno e i pezzi si spostano "
                         "verso la griglia; il file non cambia.", n=attack_count))
        info.setWordWrap(True)
        layout.addWidget(info)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("Griglia:")))
        self.grid_combo = QComboBox()
        for label, denom in GRIDS:
            self.grid_combo.addItem(label, denom)
        self.grid_combo.setCurrentIndex(self.grid_combo.findData(16))
        row.addWidget(self.grid_combo)
        self.ternary_check = QCheckBox(tr("Ternario (terzine, 8T/16T)"))
        row.addWidget(self.ternary_check)
        row.addStretch(1)
        layout.addLayout(row)
        self.quant_options = QuantizeOptionsWidget(cleanup=False, expanded=True)
        layout.addWidget(self.quant_options)
        self.grid_combo.currentIndexChanged.connect(self._on_grid_changed)
        self.ternary_check.toggled.connect(self._on_grid_changed)
        self._on_grid_changed()
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText(tr("Quantizza"))
        buttons.button(QDialogButtonBox.Ok).setEnabled(attack_count > 0)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _grid(self):
        denom = self.grid_combo.currentData()
        return denom, self.ternary_check.isChecked() and denom in TERNARY_ENABLED_GRIDS

    def _on_grid_changed(self, *_args):
        denom = self.grid_combo.currentData()
        self.ternary_check.setEnabled(denom in TERNARY_ENABLED_GRIDS)
        if denom not in TERNARY_ENABLED_GRIDS:
            self.ternary_check.setChecked(False)
        self.quant_options.set_grid(*self._grid())

    def grid_beats(self) -> float:
        return grid_slot_beats(*self._grid())

    def settings(self):
        return self.quant_options.settings()

    def accept(self):
        self.quant_options.remember()
        super().accept()
