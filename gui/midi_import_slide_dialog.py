from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QCheckBox, QDoubleSpinBox, QLabel, QDialogButtonBox,
)

from core import settings as app_settings
from core.i18n import tr


class MidiImportSlideDialog(QDialog):
    """Opzioni → Slide nell'import MIDI...: con "Slide" spuntato l'import
    usa una soglia piu' sensibile per riconoscere i pitch bend come slide
    (vedi core.midi_convert.analyze_midi, min_bend_semitones) e la soglia
    diventa modificabile. Utile per la slide guitar, i cui bend brevi
    restano appena sopra il semitono. Le impostazioni si applicano al
    prossimo import."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Slide nell'import MIDI"))
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)

        self.slide_check = QCheckBox(tr("Slide"))
        self.slide_check.setToolTip(
            tr("Se spuntato, l'import MIDI riconosce come slide anche i pitch bend piu' piccoli "
            "(tipici della slide guitar) e permette di regolare la soglia.")
        )
        self.slide_check.setChecked(app_settings.get_midi_import_slide_sensitive())
        layout.addWidget(self.slide_check)

        form = QFormLayout()
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(app_settings.MIDI_IMPORT_SLIDE_THRESHOLD_MIN,
                                     app_settings.MIDI_IMPORT_SLIDE_THRESHOLD_MAX)
        self.threshold_spin.setSingleStep(0.05)
        self.threshold_spin.setDecimals(2)
        self.threshold_spin.setSuffix(" semitoni")
        self.threshold_spin.setValue(app_settings.get_midi_import_slide_threshold())
        self.threshold_spin.setToolTip(
            tr("Ampiezza minima del bend per diventare uno slide. Piu' bassa = piu' slide "
            "(ma anche piu' rischio di scambiare per slide un'espressione del pitch wheel). "
            "Vale solo per i canali con sensibilita' del pitch bend ampia; su quelli stretti "
            "la soglia di sempre e' gia' piu' bassa.")
        )
        form.addRow(tr("Soglia:"), self.threshold_spin)
        layout.addLayout(form)

        hint = QLabel(tr("Si applica al prossimo import MIDI. Senza la spunta l'import resta come sempre."))
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.slide_check.toggled.connect(self.threshold_spin.setEnabled)
        self.threshold_spin.setEnabled(self.slide_check.isChecked())

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept(self):
        app_settings.set_midi_import_slide_sensitive(self.slide_check.isChecked())
        app_settings.set_midi_import_slide_threshold(self.threshold_spin.value())
        self.accept()
