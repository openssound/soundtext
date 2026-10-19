"""Opzioni -> Import audio -> Parametri avanzati del pitch tracking: i
parametri dell'analisi melodica dell'import audio (vedi core.audio_pitch),
salvati nelle impostazioni e usati da ogni import (gui.audio_import_dialog).
Di solito non servono: i valori standard si adattano allo strumento."""

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QVBoxLayout,
)

from core import settings as app_settings
from core.audio_pitch import MIN_NOTE_DURATION_SEC, PITCH_CONFIDENCE_THRESHOLD
from core.i18n import tr

# Scelte per la finestra di analisi (buf_size) e l'hop size del pitch
# tracker: None = automatico (vedi core.audio_pitch, adattato al registro
# dello strumento), le altre sono potenze di due esplicite passate
# direttamente all'analisi (core.audio_dsp).
BUF_SIZE_CHOICES = [
    (tr("Automatica (in base al registro)"), None),
    (tr("1024 (piu' risoluzione temporale)"), 1024),
    (tr("2048 (predefinito)"), 2048),
    (tr("4096 (bassi/note gravi)"), 4096),
    (tr("8192 (bassi molto gravi)"), 8192),
    ("16384", 16384),
]
HOP_SIZE_CHOICES = [
    (tr("Automatico (finestra / 4)"), None),
    ("128", 128),
    ("256", 256),
    (tr("512 (predefinito)"), 512),
    ("1024", 1024),
    ("2048", 2048),
]
MIN_NOTE_DURATION_MS_DEFAULT = int(round(MIN_NOTE_DURATION_SEC * 1000))

# Valori standard: frequenza minima automatica (dallo strumento della
# traccia), finestra e passo automatici.
DEFAULTS = {
    "min_freq_auto": True,
    "min_freq_hz": 82.4,          # Mi2, la corda piu' grave della chitarra
    "buf_size": None,
    "hop_size": None,
    "confidence": PITCH_CONFIDENCE_THRESHOLD,
    "min_note_ms": MIN_NOTE_DURATION_MS_DEFAULT,
}


def current_pitch_params() -> dict:
    """I parametri in uso: i valori standard con quelli cambiati in Opzioni."""
    params = dict(DEFAULTS)
    params.update({k: v for k, v in app_settings.get_audio_pitch_params().items() if k in DEFAULTS})
    return params


def is_customized() -> bool:
    return current_pitch_params() != DEFAULTS


class AudioPitchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Parametri avanzati del pitch tracking"))
        layout = QVBoxLayout(self)
        intro = QLabel(tr("Valgono per l'import audio in modalita' melodica. Di solito non servono: "
                          "i valori standard si adattano allo strumento della traccia."))
        intro.setWordWrap(True)
        layout.addWidget(intro)

        freq_row = QHBoxLayout()
        freq_row.addWidget(QLabel(tr("Frequenza minima:")))
        self.min_freq_auto_check = QCheckBox(tr("Automatica (in base allo strumento)"))
        self.min_freq_auto_check.toggled.connect(lambda checked: self.min_freq_spin.setEnabled(not checked))
        freq_row.addWidget(self.min_freq_auto_check)
        self.min_freq_spin = QDoubleSpinBox()
        self.min_freq_spin.setRange(20.0, 2000.0)
        self.min_freq_spin.setDecimals(1)
        self.min_freq_spin.setSuffix(" Hz")
        self.min_freq_spin.setToolTip(
            tr("Dimensiona la finestra di analisi sulle note piu' gravi attese: troppo bassa "
               "puo' rendere la stima del pitch meno precisa sui bassi, troppo alta peggiora "
               "la risoluzione temporale."))
        freq_row.addWidget(self.min_freq_spin)
        freq_row.addStretch(1)
        layout.addLayout(freq_row)

        window_row = QHBoxLayout()
        window_row.addWidget(QLabel(tr("Finestra di analisi:")))
        self.buf_size_combo = QComboBox()
        for label, value in BUF_SIZE_CHOICES:
            self.buf_size_combo.addItem(label, value)
        self.buf_size_combo.setToolTip(
            tr("Numero di campioni analizzati per ogni stima di pitch. Finestre piu' ampie "
               "aiutano sulle note gravi (piu' periodi coperti) ma peggiorano la risoluzione "
               "temporale (attacchi/note brevi meno precisi)."))
        window_row.addWidget(self.buf_size_combo)
        window_row.addStretch(1)
        layout.addLayout(window_row)

        hop_row = QHBoxLayout()
        hop_row.addWidget(QLabel(tr("Passo di analisi (hop size):")))
        self.hop_size_combo = QComboBox()
        for label, value in HOP_SIZE_CHOICES:
            self.hop_size_combo.addItem(label, value)
        self.hop_size_combo.setToolTip(
            tr("Distanza in campioni tra una stima e la successiva. Piu' piccolo = piu' "
               "risoluzione temporale ma analisi piu' lenta."))
        hop_row.addWidget(self.hop_size_combo)
        hop_row.addStretch(1)
        layout.addLayout(hop_row)

        confidence_row = QHBoxLayout()
        confidence_row.addWidget(QLabel(tr("Soglia di confidenza:")))
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.0, 1.0)
        self.confidence_spin.setSingleStep(0.01)
        self.confidence_spin.setDecimals(2)
        confidence_row.addWidget(self.confidence_spin)
        confidence_row.addStretch(1)
        layout.addLayout(confidence_row)

        duration_row = QHBoxLayout()
        duration_row.addWidget(QLabel(tr("Durata minima nota:")))
        self.min_note_duration_spin = QSpinBox()
        self.min_note_duration_spin.setRange(0, 1000)
        self.min_note_duration_spin.setSingleStep(5)
        self.min_note_duration_spin.setSuffix(" ms")
        self.min_note_duration_spin.setToolTip(
            tr("Note piu' brevi di questa soglia vengono scartate come probabili artefatti "
               "(onset spuri ravvicinati, es. per vibrato marcato)."))
        duration_row.addWidget(self.min_note_duration_spin)
        duration_row.addStretch(1)
        layout.addLayout(duration_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        reset_btn = QPushButton(tr("Ripristina valori standard"))
        reset_btn.clicked.connect(lambda: self._show(DEFAULTS))
        buttons.addButton(reset_btn, QDialogButtonBox.ResetRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._show(current_pitch_params())

    def _show(self, params: dict):
        self.min_freq_auto_check.setChecked(params["min_freq_auto"])
        self.min_freq_spin.setValue(params["min_freq_hz"])
        self.min_freq_spin.setEnabled(not params["min_freq_auto"])
        self.buf_size_combo.setCurrentIndex(max(0, self.buf_size_combo.findData(params["buf_size"])))
        self.hop_size_combo.setCurrentIndex(max(0, self.hop_size_combo.findData(params["hop_size"])))
        self.confidence_spin.setValue(params["confidence"])
        self.min_note_duration_spin.setValue(params["min_note_ms"])

    def params(self) -> dict:
        return {
            "min_freq_auto": self.min_freq_auto_check.isChecked(),
            "min_freq_hz": self.min_freq_spin.value(),
            "buf_size": self.buf_size_combo.currentData(),
            "hop_size": self.hop_size_combo.currentData(),
            "confidence": round(self.confidence_spin.value(), 2),
            "min_note_ms": self.min_note_duration_spin.value(),
        }

    def accept(self):
        params = self.params()
        # si salvano solo i valori diversi da quelli standard
        app_settings.set_audio_pitch_params({k: v for k, v in params.items() if v != DEFAULTS[k]})
        super().accept()
