from PySide6.QtWidgets import QDialog, QFormLayout, QComboBox, QLineEdit, QDialogButtonBox, QCheckBox

from core.instruments import list_instrument_names
from core.i18n import tr


class AddTrackDialog(QDialog):
    """Usato sia per aggiungere una nuova traccia sia, in modalita' modifica,
    per rinominarla e/o cambiarne lo strumento (funzionalita' 2)."""

    def __init__(self, parent=None, existing_names=None, edit_name=None, edit_instrument=None):
        super().__init__(parent)
        self.edit_mode = edit_name is not None
        self.setWindowTitle(tr("Modifica traccia") if self.edit_mode else tr("Aggiungi traccia"))
        self.existing_names = existing_names or []
        layout = QFormLayout(self)

        self.instrument_combo = QComboBox()
        self.instrument_combo.addItems(list_instrument_names())
        self.instrument_combo.setToolTip(tr("Strumento assegnato alla traccia (determina voicing, registro e suono)."))

        self.name_edit = QLineEdit()
        self.name_edit.setToolTip(tr("Nome visualizzato della traccia (puoi personalizzarlo liberamente)."))

        if self.edit_mode:
            idx = self.instrument_combo.findText(edit_instrument)
            if idx >= 0:
                self.instrument_combo.setCurrentIndex(idx)
            self.name_edit.setText(edit_name)
            self.rename_checkbox = QCheckBox(tr("Aggiorna anche il nome della traccia"))
            self.rename_checkbox.setToolTip(
                tr("Se spuntato, cambiando lo strumento qui sopra il nome della traccia "
                "viene proposto uguale al nuovo strumento, invece di restare quello attuale.")
            )
            # Selezionata di default: setChecked() PRIMA di collegare
            # 'toggled' (altrimenti scatterebbe subito _on_rename_checkbox_toggled,
            # sovrascrivendo il nome attuale ancora prima di un cambio
            # strumento vero e proprio, con quello - identico - gia' in
            # combo). Un cambio strumento successivo propone comunque il
            # nuovo nome; deselezionandola si torna al comportamento
            # originale (nome invariato).
            self.rename_checkbox.setChecked(True)
            self.rename_checkbox.toggled.connect(self._on_rename_checkbox_toggled)
            self.instrument_combo.currentTextChanged.connect(self._on_instrument_changed_edit_mode)
        else:
            self.instrument_combo.currentTextChanged.connect(self._suggest_name)
            self._suggest_name(self.instrument_combo.currentText())

        layout.addRow(tr("Strumento:"), self.instrument_combo)
        if self.edit_mode:
            layout.addRow("", self.rename_checkbox)
        layout.addRow(tr("Nome traccia:"), self.name_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _on_rename_checkbox_toggled(self, checked):
        if checked:
            self._suggest_name(self.instrument_combo.currentText())

    def _on_instrument_changed_edit_mode(self, instrument):
        if self.rename_checkbox.isChecked():
            self._suggest_name(instrument)

    def _suggest_name(self, instrument):
        base = instrument
        n = 1
        name = base
        taken = set(self.existing_names)
        while name in taken:
            n += 1
            name = f"{base} {n}"
        self.name_edit.setText(name)

    def result_values(self):
        return self.name_edit.text().strip(), self.instrument_combo.currentText()
