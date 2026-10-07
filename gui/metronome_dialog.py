from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QSlider, QLabel,
    QPushButton, QHBoxLayout, QDialogButtonBox,
)

from core import settings as app_settings
from core.metronome_sounds import SOUND_PRESETS
from core.i18n import tr


class MetronomeSettingsDialog(QDialog):
    """Opzioni → Metronomo: scelta del suono e del volume del click,
    applicate immediatamente (come 'Scegli SoundFont') cosi' da poterle
    sentire subito con il pulsante 'Prova', senza un OK/Annulla separato."""

    def __init__(self, owner):
        """owner e' la finestra/il dialogo che possiede il MetronomeEngine da
        aggiornare in diretta (gui.metronome_engine.MetronomeEngine, tramite
        l'attributo owner.metronome_engine): oggi la finestra principale,
        ma qualunque altro host con un proprio motore funziona allo stesso modo."""
        super().__init__(owner)
        self.owner = owner
        self.setWindowTitle(tr("Metronomo"))
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.sound_combo = QComboBox()
        for name in sorted(SOUND_PRESETS.keys()):
            self.sound_combo.addItem(tr(name), name)      # testo tradotto, dato = nome salvato
        self.sound_combo.setCurrentIndex(max(0, self.sound_combo.findData(app_settings.get_metronome_sound())))
        self.sound_combo.currentIndexChanged.connect(
            lambda _i: self._on_sound_changed(self.sound_combo.currentData()))
        form.addRow(tr("Suono:"), self.sound_combo)

        volume_row = QHBoxLayout()
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(app_settings.get_metronome_volume())
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        volume_row.addWidget(self.volume_slider)
        self.volume_value_label = QLabel(f"{self.volume_slider.value()}%")
        self.volume_value_label.setFixedWidth(38)
        volume_row.addWidget(self.volume_value_label)
        form.addRow(tr("Volume:"), volume_row)

        layout.addLayout(form)

        test_btn = QPushButton(tr("Prova"))
        test_btn.setToolTip(tr("Riproduce un click di accento seguito da un click normale, "
                             "con le impostazioni correnti."))
        test_btn.clicked.connect(self._on_test)
        layout.addWidget(test_btn)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.accept)
        layout.addWidget(buttons)

    def _on_sound_changed(self, name):
        app_settings.set_metronome_sound(name)
        self.owner.metronome_engine.reload_sounds()

    def _on_volume_changed(self, value):
        app_settings.set_metronome_volume(value)
        self.volume_value_label.setText(f"{value}%")
        self.owner.metronome_engine.reload_sounds()

    def _on_test(self):
        self.owner.metronome_engine.preview()
