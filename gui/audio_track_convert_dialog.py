"""
"Converti la traccia in notazione..." (menu ⋯ di una traccia audio): le
scelte, una volta sola per tutte le clip della traccia (cosa riconoscere,
quantizzazione, dove mettere il risultato). La conversione la fa
core.audio_track_notation.convert_audio_track, lanciata da
gui.arrangement_view: una traccia SoundText con un box per clip, ciascuno
alla posizione e con il nome della sua clip.

Per rifare la conversione dopo una modifica all'audio c'e' la destinazione
"Sostituisci il contenuto della traccia". Il dialogo propone la traccia di
note nata da questa traccia audio con le scelte di allora (Track.conversion,
salvata nel file dalla 2.10); senza, le scelte dell'ultima conversione fatta
finche' SoundText resta aperto e la traccia "Nome (note)" se esiste gia'.
Riconverti (menu delle tracce) rifa' la conversione senza dialogo.
"""

from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel,
    QRadioButton, QVBoxLayout, QWidget,
)

from core import settings as app_settings
from core.audio_track_notation import ConversionOptions, audible_clips, converted_from
from core.i18n import tr
from core.instruments import get_instrument, list_instrument_names
from .quantize_options import QuantizeOptionsWidget
from .audio_import_dialog import GRID_CHOICES, TERNARY_ENABLED_GRIDS, _min_freq_hz_for_instrument

# per traccia audio: le scelte dell'ultima conversione (vedi remember_choices)
_last_choices = {}

MODES = (("melody", tr("Melodia")), ("drums", tr("Percussioni")), ("chords", tr("Accordi")))


def _suggested_instrument(mode: str, input_profile: str) -> str:
    if mode == "drums":
        return "Drums"
    if mode == "chords":
        return "Guitar" if input_profile == "chitarra" else "Piano"
    return {"chitarra": "Guitar", "tastiera": "Piano", "voce": "Trumpet"}.get(input_profile, "Piano")


class AudioTrackConvertDialog(QDialog):
    def __init__(self, parent, project, track):
        super().__init__(parent)
        self.project = project
        self.track = track
        self.setWindowTitle(tr("Converti la traccia in notazione — {name}", name=track.name))
        layout = QVBoxLayout(self)

        clips = audible_clips(track)
        skipped = len(track.audio_clips) - len(clips)
        summary = tr("Clip da convertire: {n}, ciascuna in un box alla sua posizione.", n=len(clips))
        if skipped:
            summary += "\n" + tr("Saltate: {n} (silenziate o con il file mancante).", n=skipped)
        layout.addWidget(QLabel(summary))

        form = self._form = QFormLayout()
        self.mode_combo = QComboBox()
        for value, label in MODES:
            self.mode_combo.addItem(label, value)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        form.addRow(tr("Cosa riconoscere:"), self.mode_combo)

        quant = QWidget()
        quant_row = QHBoxLayout(quant)
        quant_row.setContentsMargins(0, 0, 0, 0)
        self.grid_combo = QComboBox()
        for label, denom in GRID_CHOICES:
            self.grid_combo.addItem(label, denom)
        # l'ultima griglia scelta, come in "Importa audio"
        index = self.grid_combo.findData(app_settings.get_last_quantization_grid())
        self.grid_combo.setCurrentIndex(index if index >= 0 else self.grid_combo.findData(16))
        self.grid_combo.currentIndexChanged.connect(self._on_grid_changed)
        quant_row.addWidget(self.grid_combo)
        self.ternary_check = QCheckBox(tr("Ternario (terzine, 8T/16T)"))
        self.ternary_check.setChecked(app_settings.get_last_quantization_ternary())
        self.ternary_check.toggled.connect(self._on_grid_changed)
        quant_row.addWidget(self.ternary_check)
        quant_row.addStretch(1)
        self._quant_row = quant
        form.addRow(tr("Quantizzazione:"), quant)
        self.quant_options = QuantizeOptionsWidget()
        form.addRow("", self.quant_options)
        self.voice_check = QCheckBox()
        form.addRow("", self.voice_check)
        self.sevenths_check = QCheckBox(tr("Riconosci le settime (7, maj7, m7)"))
        form.addRow("", self.sevenths_check)
        layout.addLayout(form)

        dest_form = QFormLayout()
        self.new_radio = QRadioButton(tr("Nuova traccia, strumento:"))
        self.existing_radio = QRadioButton(tr("Aggiungi alla traccia:"))
        self.replace_radio = QRadioButton(tr("Sostituisci il contenuto della traccia:"))
        group = QButtonGroup(self)
        group.addButton(self.new_radio)
        group.addButton(self.existing_radio)
        group.addButton(self.replace_radio)
        self.instrument_combo = QComboBox()
        self.instrument_combo.addItems(list_instrument_names())
        dest_form.addRow(self.new_radio, self.instrument_combo)
        self.target_combo = QComboBox()
        self.target_combo.addItems([t.name for t in project.tracks if not t.is_audio])
        dest_form.addRow(self.existing_radio, self.target_combo)
        self.replace_combo = QComboBox()
        self.replace_combo.addItems([t.name for t in project.tracks if not t.is_audio])
        dest_form.addRow(self.replace_radio, self.replace_combo)
        self.new_radio.setChecked(True)
        self.existing_radio.setEnabled(self.target_combo.count() > 0)
        self.replace_radio.setEnabled(self.replace_combo.count() > 0)
        self.existing_radio.setToolTip(tr("I box vanno dove sono le clip, o nello spazio libero piu' vicino."))
        self.replace_radio.setToolTip(tr("Per rifare la conversione dopo una modifica all'audio: i box e il testo "
                                         "della traccia si tolgono e al loro posto vanno quelli nuovi "
                                         "(Ctrl+Z riporta quelli di prima)."))
        self.new_radio.toggled.connect(self._on_destination_changed)
        self.replace_radio.toggled.connect(self._on_destination_changed)
        layout.addLayout(dest_form)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText(tr("Converti"))
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(bool(clips))
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self._on_mode_changed()
        self._restore_choices()
        self._on_destination_changed()

    def _restore_choices(self):
        """Le scelte proposte (vedi docstring del modulo)."""
        linked = converted_from(self.project, self.track.name)
        if linked:
            self._restore_conversion(linked[0])
            return
        last = _last_choices.get(self.track.name, {})
        if last:
            self.mode_combo.setCurrentIndex(max(0, self.mode_combo.findData(last["mode"])))
            self.voice_check.setChecked(last["voice"])
            self.sevenths_check.setChecked(last["sevenths"])
        target = last.get("target") or tr("{name} (note)", name=self.track.name)
        index = self.replace_combo.findText(target)
        if index >= 0:
            self.replace_combo.setCurrentIndex(index)
            self.replace_radio.setChecked(True)

    def _restore_conversion(self, target):
        conversion = target.conversion
        self.mode_combo.setCurrentIndex(max(0, self.mode_combo.findData(conversion["mode"])))
        self.grid_combo.setCurrentIndex(max(0, self.grid_combo.findData(conversion["grid"])))
        self.ternary_check.setChecked(conversion["triplets"])
        from core.audio_track_notation import options_from_conversion
        quantize = options_from_conversion(dict(conversion, mode="melody")).quantize
        self.quant_options.set_settings(quantize)
        self.voice_check.setChecked(conversion["voice"])
        self.sevenths_check.setChecked(conversion["sevenths"])
        self.replace_combo.setCurrentIndex(self.replace_combo.findText(target.name))
        self.replace_radio.setChecked(True)

    def _mode(self) -> str:
        return self.mode_combo.currentData()

    def _on_mode_changed(self):
        mode = self._mode()
        self._form.setRowVisible(self._quant_row, mode != "chords")
        self._form.setRowVisible(self.quant_options, mode != "chords")
        self._form.setRowVisible(self.voice_check, mode != "chords")
        self._form.setRowVisible(self.sevenths_check, mode == "chords")
        self.voice_check.setText(tr("Sto cantando (non lo strumento)") if mode == "melody"
                                 else tr("Sto facendo beatbox (non la batteria)"))
        suggested = _suggested_instrument(mode, self.track.input_profile)
        index = self.instrument_combo.findText(suggested)
        if index >= 0:
            self.instrument_combo.setCurrentIndex(index)
        self._on_grid_changed()

    def _on_grid_changed(self):
        enable = self.grid_combo.currentData() in TERNARY_ENABLED_GRIDS
        self.ternary_check.setEnabled(enable)
        if not enable:
            self.ternary_check.setChecked(False)
        self.quant_options.set_grid(self.grid_combo.currentData(), self.ternary_check.isChecked())

    def _on_destination_changed(self):
        self.instrument_combo.setEnabled(self.new_radio.isChecked())
        self.target_combo.setEnabled(self.existing_radio.isChecked())
        self.replace_combo.setEnabled(self.replace_radio.isChecked())

    def remember_choices(self, target_name: str):
        """Dopo la conversione: le scelte e la traccia in cui sono finiti i
        box, proposte la prossima volta per questa traccia audio."""
        _last_choices[self.track.name] = {
            "mode": self._mode(), "voice": self.voice_check.isChecked(),
            "sevenths": self.sevenths_check.isChecked(), "target": target_name,
        }

    def accept(self):
        if self._mode() != "chords":
            app_settings.set_last_quantization_grid(self.grid_combo.currentData())
            app_settings.set_last_quantization_ternary(self.ternary_check.isChecked())
            self.quant_options.remember()
        super().accept()

    def destination(self):
        """("new", strumento), ("existing", nome della traccia) o
        ("replace", nome della traccia)."""
        if self.replace_radio.isChecked():
            return "replace", self.replace_combo.currentText()
        if self.existing_radio.isChecked():
            return "existing", self.target_combo.currentText()
        return "new", self.instrument_combo.currentText()

    def instrument_name(self) -> str:
        kind, value = self.destination()
        return value if kind == "new" else self.project.get_track(value).instrument_name

    def options(self) -> ConversionOptions:
        mode = self._mode()
        options = ConversionOptions(mode=mode, grid_denominator=self.grid_combo.currentData(),
                                    ternary=self.ternary_check.isChecked() and mode != "chords",
                                    sevenths=mode == "chords" and self.sevenths_check.isChecked(),
                                    voice_source=mode != "chords" and self.voice_check.isChecked(),
                                    quantize=None if mode == "chords" else self.quant_options.settings())
        return with_pitch_params(options, self.instrument_name())


def with_pitch_params(options: ConversionOptions, instrument_name: str) -> ConversionOptions:
    """Per la melodia, gli stessi parametri del pitch tracking di "Importa
    audio" (Opzioni -> Import audio, vedi AudioImportDialog): valgono anche
    per Riconverti, perche' non sono salvati nel brano."""
    from .audio_pitch_dialog import current_pitch_params
    if options.mode == "melody":
        params = current_pitch_params()
        if params["min_freq_auto"]:
            if not options.voice_source:
                options.min_freq_hz = _min_freq_hz_for_instrument(get_instrument(instrument_name))
        else:
            options.min_freq_hz = params["min_freq_hz"]
        options.buf_size = params["buf_size"]
        options.hop_size = params["hop_size"]
        options.pitch_confidence_threshold = params["confidence"]
        options.min_note_duration_sec = params["min_note_ms"] / 1000.0
    return options
