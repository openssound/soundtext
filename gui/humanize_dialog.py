from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QSlider, QLabel, QHBoxLayout, QDialogButtonBox,
)

from core import settings as app_settings
from core.i18n import tr


class HumanizeSettingsDialog(QDialog):
    """Opzioni → Umanizza: intensita' della variazione casuale di timing/
    velocity applicata in riproduzione (vedi core.midi_export, funzionalita'
    14), applicata immediatamente come le altre impostazioni di Opzioni,
    senza un OK/Annulla separato."""

    def __init__(self, owner):
        """owner e' la finestra che possiede il checkbox 'Umanizza' e il
        meccanismo di riavvio a caldo della riproduzione (gui.main_window,
        tramite _on_mixer_changed): un cambio di intensita' mentre la
        riproduzione e' in corso e umanizzazione e' attiva la riavvia con il
        nuovo valore, come un volume o un pan."""
        super().__init__(owner)
        self.owner = owner
        self.setWindowTitle(tr("Umanizza"))
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        amount_row = QHBoxLayout()
        self.amount_slider = QSlider(Qt.Horizontal)
        self.amount_slider.setRange(0, 100)
        self.amount_slider.setValue(app_settings.get_humanize_amount())
        self.amount_slider.valueChanged.connect(self._on_amount_changed)
        amount_row.addWidget(self.amount_slider)
        self.amount_value_label = QLabel(f"{self.amount_slider.value()}%")
        self.amount_value_label.setFixedWidth(38)
        amount_row.addWidget(self.amount_value_label)
        form.addRow(tr("Intensita':"), amount_row)
        layout.addLayout(form)

        note = QLabel(
            tr("Aggiunge una piccola variazione casuale a timing e velocity delle note "
            "(solo velocity per la batteria), diversa ad ogni riproduzione — nessuna "
            "impostazione fissa da riprodurre identica ogni volta, come un musicista "
            "vero. Si attiva/disattiva con la casella \"Umanizza\" in toolbar.")
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.accept)
        layout.addWidget(buttons)

    def _on_amount_changed(self, value):
        app_settings.set_humanize_amount(value)
        self.amount_value_label.setText(f"{value}%")
        if self.owner.humanize_checkbox.isChecked():
            self.owner._on_mixer_changed(None)
