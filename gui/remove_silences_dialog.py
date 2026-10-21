"""
"Rimuovi i silenzi..." (tasto destro su una clip audio): soglia, durata
minima di un silenzio e margine prima degli attacchi, con il risultato
(pezzi e secondi tolti) che si aggiorna a ogni modifica. Il livello della
clip si misura una volta sola, prima di aprire il dialogo
(core.audio_silence.clip_levels_db).
"""

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QLabel, QSpinBox, QVBoxLayout

from core import audio_silence
from core.i18n import tr


class RemoveSilencesDialog(QDialog):
    def __init__(self, parent, clip_name: str, levels_db, total: float):
        super().__init__(parent)
        self._levels, self._total = levels_db, total
        self.setWindowTitle(tr("Rimuovi i silenzi — {name}", name=clip_name))
        layout = QVBoxLayout(self)
        info = QLabel(tr("Dove il livello resta sotto la soglia almeno per la durata scelta, la clip si "
                         "divide e il pezzo vuoto sparisce; il file non cambia."))
        info.setWordWrap(True)
        layout.addWidget(info)
        form = QFormLayout()
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(-90.0, -10.0)
        self.threshold_spin.setDecimals(0)
        self.threshold_spin.setSuffix(" dB")
        self.threshold_spin.setValue(audio_silence.THRESHOLD_DB)
        form.addRow(tr("Soglia:"), self.threshold_spin)
        self.min_silence_spin = QSpinBox()
        self.min_silence_spin.setRange(50, 10000)
        self.min_silence_spin.setSingleStep(50)
        self.min_silence_spin.setSuffix(" ms")
        self.min_silence_spin.setValue(int(audio_silence.MIN_SILENCE * 1000))
        form.addRow(tr("Silenzio di almeno:"), self.min_silence_spin)
        self.pre_roll_spin = QSpinBox()
        self.pre_roll_spin.setRange(0, 1000)
        self.pre_roll_spin.setSingleStep(10)
        self.pre_roll_spin.setSuffix(" ms")
        self.pre_roll_spin.setValue(int(audio_silence.PRE_ROLL * 1000))
        form.addRow(tr("Margine prima dell'attacco:"), self.pre_roll_spin)
        layout.addLayout(form)
        self.result_label = QLabel()
        layout.addWidget(self.result_label)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText(tr("Rimuovi"))
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        for spin in (self.threshold_spin, self.min_silence_spin, self.pre_roll_spin):
            spin.valueChanged.connect(self._update_result)
        self._update_result()

    def regions(self):
        return audio_silence.sound_regions(self._levels, self._total, self.threshold_spin.value(),
                                           self.min_silence_spin.value() / 1000, self.pre_roll_spin.value() / 1000)

    def _update_result(self, *_args):
        regions = self.regions()
        removed = self._total - sum(b - a for a, b in regions)
        if not regions:
            text = tr("La clip e' tutta sotto la soglia.")
        elif removed < 0.005:
            text = tr("Nessun silenzio da togliere.")
        else:
            text = tr("{n} pezzi, {seconds} s di silenzio tolti.", n=len(regions), seconds=f"{removed:.1f}")
        self.result_label.setText(text)
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(bool(regions) and removed >= 0.005)
