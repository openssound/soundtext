from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QSlider, QLabel, QHBoxLayout, QDialogButtonBox,
)

from core import settings as app_settings
from core.playback import set_shared_synth_gain
from core.i18n import tr


class PlaybackGainDialog(QDialog):
    """Playback -> Volume di sintesi (gain)...: guadagno lineare applicato
    dal synth fluidsynth PRIMA che il segnale venga scritto nel WAV di
    rendering (vedi core.playback). Troppo alto e un mix denso (piu'
    strumenti/percussioni insieme) satura, sentito come un crepitio/
    distorsione anche con un impianto audio perfettamente funzionante —
    non e' un problema di driver audio (vedi la docstring del modulo
    core.playback sul rendering offline). Applicato immediatamente al
    synth condiviso gia' in uso, come Metronomo/Umanizza, senza un OK/
    Annulla separato."""

    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.setWindowTitle(tr("Volume di sintesi"))
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        gain_row = QHBoxLayout()
        self.gain_slider = QSlider(Qt.Horizontal)
        self.gain_slider.setRange(10, 200)
        self.gain_slider.setValue(round(app_settings.get_playback_gain() * 100))
        self.gain_slider.valueChanged.connect(self._on_gain_changed)
        gain_row.addWidget(self.gain_slider)
        self.gain_value_label = QLabel(f"{self.gain_slider.value() / 100:.2f}")
        self.gain_value_label.setFixedWidth(38)
        gain_row.addWidget(self.gain_value_label)
        form.addRow(tr("Gain:"), gain_row)
        layout.addLayout(form)

        note = QLabel(
            tr("Guadagno applicato dal sintetizzatore prima del rendering. Troppo alto "
            "puo' saturare il segnale nei passaggi piu' densi (piu' strumenti/percussioni "
            "insieme), sentito come un crepitio/distorsione anche con un impianto audio "
            "perfettamente funzionante — non e' un problema di driver audio. Predefinito: 0.90.")
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.accept)
        layout.addWidget(buttons)

    def _on_gain_changed(self, value):
        gain = value / 100
        app_settings.set_playback_gain(gain)
        self.gain_value_label.setText(f"{gain:.2f}")
        set_shared_synth_gain(gain)
