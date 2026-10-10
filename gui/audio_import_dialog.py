"""
Dialogo di importazione audio: registrazione da microfono o file
.wav/.mp3/.m4a (anche via drag-and-drop), pannello di quantizzazione
(griglia + terzine) e conversione in notazione testuale, con anteprima
prima dell'inserimento nella traccia corrente (vedi core.audio_import).
"""

import os
import re

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QCheckBox, QFrame, QDialogButtonBox, QFileDialog,
    QMessageBox, QProgressDialog, QRadioButton, QButtonGroup,
    QGroupBox, QSpinBox, QDoubleSpinBox
)

from core import settings as app_settings
from core.model import Project, copy_synth
from core.instruments import get_instrument
from core.audio_import import ConversionCancelled, convert_audio_to_track_text
from core.audio_decode import can_decode_compressed_audio
from core.audio_pitch import PITCH_CONFIDENCE_THRESHOLD, MIN_NOTE_DURATION_SEC
from core.audio_recorder import MicRecorder, is_sounddevice_available
from core.notation import validate_track_text
from core.playback import PlaybackEngine
from .worker import Worker
from .highlighter import NotationHighlighter
from .metronome_engine import MetronomeEngine
from .play_highlight import PlayHighlighter
from .selection_actions import handle_selection_context_menu
from .voicing_picker import NotationEditor
from core.i18n import tr
from .file_dialogs import file_dialog_options


def _min_freq_hz_for_instrument(instr) -> float:
    """Frequenza (Hz) corrispondente alla nota MIDI piu' bassa suonabile
    dallo strumento, usata per dimensionare la finestra di analisi del
    pitch detector sulle note piu' gravi (vedi core.audio_pitch)."""
    return 440.0 * (2 ** ((instr.range_low - 69) / 12))

AUDIO_FILE_FILTER = tr("Audio (*.wav *.mp3 *.m4a)")
AUDIO_EXTENSIONS = (".wav", ".mp3", ".m4a")

GRID_CHOICES = [
    (tr("Off (griglia finissima)"), 64),
    ("1/4", 4),
    ("1/8", 8),
    (tr("1/16 (predefinito)"), 16),
    ("1/32", 32),
]
TERNARY_ENABLED_GRIDS = (8, 16)

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


class AudioImportDialog(QDialog):
    """Registra/carica audio, lo converte in notazione con il motore di
    quantizzazione (core.audio_quantize) e restituisce il testo tramite
    result_text() se l'utente conferma con Ok. L'anteprima e' modificabile
    a mano una volta completata la conversione (per aggiustare una nota
    sbagliata, provare un'alternativa, ecc.): "Ascolta anteprima" riproduce
    sempre il contenuto ATTUALE dell'editor (comprese le modifiche
    dell'utente, non il testo originale generato dall'analisi), e Ok
    valida quel contenuto al momento della conferma, rifiutando la chiusura
    del dialogo se non e' sintatticamente valido."""

    def __init__(self, parent, project, instrument_name, context_label, midi_dir=None, track_name=None):
        super().__init__(parent)
        self.project = project
        self.track_name = track_name    # traccia reale (per lo strumento plugin delle anteprime)
        self.instrument_name = instrument_name
        self.context_label = context_label
        self.midi_dir = midi_dir

        self.setWindowTitle(tr("Converti audio in SoundText — {context_label}", context_label=context_label))
        self.resize(680, 620)
        self.setAcceptDrops(True)

        self.source_path = None
        self._from_mic = False
        # Registrazione fatta col metronomo acceso (ripartito all'inizio della
        # registrazione): il tempo 0 del file e' il primo battito, altrimenti
        # la trascrizione parte dalla prima nota (vedi _on_convert_clicked).
        self._recorded_with_metronome = False
        self._mic_files = []       # WAV temporanei delle registrazioni, da eliminare
        self._generated_text = None
        self._worker = None
        self._cancelled = False
        self._progress_dlg = None
        self.recorder = MicRecorder() if is_sounddevice_available() else None
        self._rec_timer = None
        self._preview_playback = PlaybackEngine()
        # Metronomo utilizzabile durante la registrazione dal microfono, per
        # tenere il tempo: click semplice a tempo/metrica costante (nessun
        # cambio di tempo/metrica qui, a differenza della riproduzione
        # dell'ensemble), parte sempre deselezionato.
        self.metronome_engine = MetronomeEngine(self)

        self._build_ui()

    # ------------------------------------------------------------ UI

    def _build_ui(self):
        layout = QVBoxLayout(self)

        instr = get_instrument(self.instrument_name)
        layout.addWidget(QLabel(
            tr("Destinazione: <b>{context_label}</b> (strumento: {instrument_name})", context_label=self.context_label, instrument_name=self.instrument_name)
        ))

        # --- tempo / metrica / metronomo (utili per registrare a tempo dal
        # microfono; il tempo e' anche usato per quantizzare la conversione)
        tempo_row = QHBoxLayout()
        tempo_row.addWidget(QLabel(tr("Tempo (BPM):")))
        self.tempo_spin = QSpinBox()
        self.tempo_spin.setRange(20, 300)
        self.tempo_spin.setValue(self.project.tempo_bpm)
        self.tempo_spin.setToolTip(tr("Tempo del progetto: usato anche per quantizzare la registrazione."))
        self.tempo_spin.valueChanged.connect(self._on_tempo_changed)
        tempo_row.addWidget(self.tempo_spin)

        tempo_row.addSpacing(12)
        tempo_row.addWidget(QLabel(tr("Metrica:")))
        self.metrica_combo = QComboBox()
        self.metrica_combo.setEditable(True)
        self.metrica_combo.addItems(["2/4", "3/4", "4/4", "5/4", "6/8", "7/8", "9/8", "12/8"])
        self.metrica_combo.setCurrentText(self.project.time_sig)
        self.metrica_combo.setFixedWidth(70)
        self.metrica_combo.setToolTip(tr("Metrica del progetto, es. 4/4, 3/4, 6/8."))
        self.metrica_combo.currentTextChanged.connect(self._on_metrica_changed)
        tempo_row.addWidget(self.metrica_combo)

        tempo_row.addSpacing(12)
        self.metronome_checkbox = QCheckBox(tr("Metronomo"))
        self.metronome_checkbox.setChecked(False)
        self.metronome_checkbox.setToolTip(
            tr("Fa sentire un click a tempo, utile per registrare a tempo dal microfono.\n"
            "Suono e volume si impostano in Opzioni → Metronomo, nella finestra principale.")
        )
        self.metronome_checkbox.toggled.connect(self._on_metronome_toggled)
        tempo_row.addWidget(self.metronome_checkbox)
        tempo_row.addStretch(1)
        layout.addLayout(tempo_row)

        # --- microfono
        mic_row = QHBoxLayout()
        self.record_btn = QPushButton(tr("🎙 Registra dal microfono"))
        self.record_btn.clicked.connect(self._toggle_recording)
        if self.recorder is None:
            self.record_btn.setEnabled(False)
            self.record_btn.setToolTip(
                tr("sounddevice/libportaudio2 non disponibili: vedi README.md, sezione Requisiti.")
            )
        else:
            self.record_btn.setToolTip(
                tr("Con il Metronomo acceso il click riparte insieme alla registrazione e la "
                "trascrizione segue i suoi battiti; senza, parte dalla prima nota.")
            )
        mic_row.addWidget(self.record_btn)
        self.timer_label = QLabel("")
        mic_row.addWidget(self.timer_label)
        mic_row.addStretch(1)
        layout.addLayout(mic_row)

        # --- file / drag-and-drop
        self.drop_frame = QFrame()
        self.drop_frame.setFrameShape(QFrame.StyledPanel)
        self.drop_frame.setObjectName("panelBox")
        self.drop_frame.setMinimumHeight(70)
        drop_layout = QVBoxLayout(self.drop_frame)
        self.source_label = QLabel(tr("Trascina qui un file .wav/.mp3/.m4a, oppure:"))
        self.source_label.setAlignment(Qt.AlignCenter)
        drop_layout.addWidget(self.source_label)
        browse_btn = QPushButton(tr("Sfoglia file..."))
        browse_btn.clicked.connect(self._browse_file)
        browse_row = QHBoxLayout()
        browse_row.addStretch(1)
        browse_row.addWidget(browse_btn)
        browse_row.addStretch(1)
        drop_layout.addLayout(browse_row)
        layout.addWidget(self.drop_frame)

        # --- quantizzazione
        quant_row = QHBoxLayout()
        quant_row.addWidget(QLabel(tr("Quantizzazione:")))
        self.grid_combo = QComboBox()
        for label, denom in GRID_CHOICES:
            self.grid_combo.addItem(label, denom)
        self.grid_combo.currentIndexChanged.connect(self._on_grid_changed)
        quant_row.addWidget(self.grid_combo)
        self.ternary_check = QCheckBox(tr("Ternario (terzine, 8T/16T)"))
        self.ternary_check.toggled.connect(self._on_grid_changed)
        quant_row.addWidget(self.ternary_check)
        quant_row.addStretch(1)
        layout.addLayout(quant_row)

        self._load_last_quantization()

        # --- modalita' melodica/percussiva
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel(tr("Modalita' di analisi:")))
        self.melodic_radio = QRadioButton(tr("Melodica (pitch detection)"))
        self.perc_radio = QRadioButton(tr("Percussiva (batteria/beatbox)"))
        mode_group = QButtonGroup(self)
        mode_group.addButton(self.melodic_radio)
        mode_group.addButton(self.perc_radio)
        if instr.is_percussion:
            self.perc_radio.setChecked(True)
        else:
            self.melodic_radio.setChecked(True)
        self.melodic_radio.toggled.connect(self._on_mode_changed)
        mode_row.addWidget(self.melodic_radio)
        mode_row.addWidget(self.perc_radio)
        mode_row.addStretch(1)
        layout.addLayout(mode_row)

        # --- parametri avanzati di pitch tracking (solo modalita' melodica)
        self.pitch_advanced_group = QGroupBox(tr("Parametri avanzati di pitch tracking"))
        advanced_layout = QVBoxLayout(self.pitch_advanced_group)

        freq_row = QHBoxLayout()
        freq_row.addWidget(QLabel(tr("Frequenza minima:")))
        self.min_freq_auto_check = QCheckBox(tr("Automatica (in base allo strumento)"))
        self.min_freq_auto_check.setChecked(True)
        self.min_freq_auto_check.toggled.connect(self._on_min_freq_auto_toggled)
        freq_row.addWidget(self.min_freq_auto_check)
        self.min_freq_spin = QDoubleSpinBox()
        self.min_freq_spin.setRange(20.0, 2000.0)
        self.min_freq_spin.setDecimals(1)
        self.min_freq_spin.setSuffix(" Hz")
        self.min_freq_spin.setValue(_min_freq_hz_for_instrument(instr))
        self.min_freq_spin.setEnabled(False)
        self.min_freq_spin.setToolTip(
            tr("Dimensiona la finestra di analisi sulle note piu' gravi attese: troppo bassa "
            "puo' rendere la stima del pitch meno precisa sui bassi, troppo alta peggiora "
            "la risoluzione temporale.")
        )
        freq_row.addWidget(self.min_freq_spin)
        freq_row.addStretch(1)
        advanced_layout.addLayout(freq_row)

        window_row = QHBoxLayout()
        window_row.addWidget(QLabel(tr("Finestra di analisi:")))
        self.buf_size_combo = QComboBox()
        for label, value in BUF_SIZE_CHOICES:
            self.buf_size_combo.addItem(label, value)
        self.buf_size_combo.setToolTip(
            tr("Numero di campioni analizzati per ogni stima di pitch. Finestre piu' ampie "
            "aiutano sulle note gravi (piu' periodi coperti) ma peggiorano la risoluzione "
            "temporale (attacchi/note brevi meno precisi).")
        )
        window_row.addWidget(self.buf_size_combo)
        window_row.addStretch(1)
        advanced_layout.addLayout(window_row)

        hop_row = QHBoxLayout()
        hop_row.addWidget(QLabel(tr("Passo di analisi (hop size):")))
        self.hop_size_combo = QComboBox()
        for label, value in HOP_SIZE_CHOICES:
            self.hop_size_combo.addItem(label, value)
        self.hop_size_combo.setToolTip(
            tr("Distanza in campioni tra una stima e la successiva. Piu' piccolo = piu' "
            "risoluzione temporale ma analisi piu' lenta.")
        )
        hop_row.addWidget(self.hop_size_combo)
        hop_row.addStretch(1)
        advanced_layout.addLayout(hop_row)

        confidence_row = QHBoxLayout()
        self.confidence_label = QLabel(tr("Soglia di confidenza:"))
        confidence_row.addWidget(self.confidence_label)
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.0, 1.0)
        self.confidence_spin.setSingleStep(0.01)
        self.confidence_spin.setDecimals(2)
        confidence_row.addWidget(self.confidence_spin)
        confidence_row.addStretch(1)
        advanced_layout.addLayout(confidence_row)

        duration_row = QHBoxLayout()
        duration_row.addWidget(QLabel(tr("Durata minima nota:")))
        self.min_note_duration_spin = QSpinBox()
        self.min_note_duration_spin.setRange(0, 1000)
        self.min_note_duration_spin.setSingleStep(5)
        self.min_note_duration_spin.setSuffix(" ms")
        self.min_note_duration_spin.setValue(MIN_NOTE_DURATION_MS_DEFAULT)
        self.min_note_duration_spin.setToolTip(
            tr("Note piu' brevi di questa soglia vengono scartate come probabili artefatti "
            "(onset spuri ravvicinati, es. per vibrato marcato).")
        )
        duration_row.addWidget(self.min_note_duration_spin)
        duration_row.addStretch(1)
        advanced_layout.addLayout(duration_row)

        reset_row = QHBoxLayout()
        reset_row.addStretch(1)
        self.pitch_reset_btn = QPushButton(tr("Ripristina valori standard"))
        self.pitch_reset_btn.clicked.connect(self._reset_pitch_advanced_params)
        reset_row.addWidget(self.pitch_reset_btn)
        advanced_layout.addLayout(reset_row)

        layout.addWidget(self.pitch_advanced_group)
        self._reset_pitch_advanced_params()
        self._on_mode_changed()

        # --- sorgente voce/beatbox (invece dello strumento reale)
        voice_row = QHBoxLayout()
        self.voice_source_check = QCheckBox(tr("Sorgente: voce/beatbox (non lo strumento reale)"))
        self.voice_source_check.setToolTip(
            tr("Attiva se stai cantando/canticchiando la parte (basso, melodia...) o imitando la "
            "batteria con la bocca, invece di registrare lo strumento vero: la voce umana ha "
            "caratteristiche acustiche diverse (intonazione meno stabile, nessuna vera risonanza "
            "grave come quella di una cassa) e l'analisi viene ricalibrata di conseguenza.")
        )
        voice_row.addWidget(self.voice_source_check)
        voice_row.addStretch(1)
        layout.addLayout(voice_row)

        # --- conversione
        self.convert_btn = QPushButton(tr("Converti in SoundText"))
        self.convert_btn.setEnabled(False)
        self.convert_btn.clicked.connect(self._on_convert_clicked)
        layout.addWidget(self.convert_btn)

        layout.addWidget(QLabel(
            tr("Anteprima (modificabile a conversione completata; verra' inserita in ")
            + self.context_label + "):"
        ))
        self.preview_edit = NotationEditor()
        self.preview_edit.setFont(QFont("Monospace", 10))
        self.preview_edit.setReadOnly(True)
        self.preview_edit.on_selection_context_menu = self._on_preview_selection_context_menu
        self._highlighter = NotationHighlighter(self.preview_edit.document())
        # Evidenziazione, nell'anteprima, di cio' che sta suonando.
        self._preview_highlight = PlayHighlighter(self.preview_edit, self, "_preview_playback")
        layout.addWidget(self.preview_edit)

        preview_play_row = QHBoxLayout()
        self.preview_play_btn = QPushButton(tr("▶ Ascolta anteprima"))
        self.preview_play_btn.setEnabled(False)
        self.preview_play_btn.setToolTip(
            tr("Riproduce il contenuto attuale dell'anteprima, comprese le eventuali "
            "modifiche fatte a mano dopo la conversione.")
        )
        self.preview_play_btn.clicked.connect(self._on_preview_play)
        preview_play_row.addWidget(self.preview_play_btn)
        self.preview_stop_btn = QPushButton(tr("■ Stop"))
        self.preview_stop_btn.clicked.connect(self._stop_preview_playback)
        preview_play_row.addWidget(self.preview_stop_btn)
        preview_play_row.addStretch(1)
        layout.addLayout(preview_play_row)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    # ------------------------------------------------------------ sorgente audio

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and any(
            u.toLocalFile().lower().endswith(AUDIO_EXTENSIONS) for u in event.mimeData().urls()
        ):
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(AUDIO_EXTENSIONS):
                self._set_source(path)
                break

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("Scegli file audio"), "", AUDIO_FILE_FILTER,
                                              options=file_dialog_options())
        if path:
            self._set_source(path)

    def _set_source(self, path, from_mic=False):
        self.source_path = path
        self._from_mic = from_mic
        self.source_label.setText(tr("Sorgente: {0}", os.path.basename(path)))
        self.convert_btn.setEnabled(True)

    def _toggle_recording(self):
        if self.recorder is None:
            QMessageBox.warning(
                self, tr("Microfono non disponibile"),
                tr("sounddevice/libportaudio2 non installati. Vedi README.md, sezione Requisiti.")
            )
            return
        if not self.recorder.is_recording:
            try:
                self.recorder.start()
            except Exception as e:
                QMessageBox.critical(self, tr("Errore microfono"), str(e))
                return
            # Il click riparte adesso: il primo battito coincide con l'inizio
            # del file, cosi' la quantizzazione segue il metronomo.
            self._recorded_with_metronome = self.metronome_checkbox.isChecked()
            if self._recorded_with_metronome:
                self._restart_metronome()
            self.record_btn.setText(tr("⏹ Ferma registrazione"))
            self._rec_timer = QTimer(self)
            self._rec_timer.timeout.connect(self._tick_timer)
            self._rec_timer.start(200)
        else:
            if self._rec_timer:
                self._rec_timer.stop()
                self._rec_timer = None
            try:
                wav_path = self.recorder.stop()
            except Exception as e:
                QMessageBox.critical(self, tr("Errore microfono"), str(e))
                self.record_btn.setText(tr("🎙 Registra dal microfono"))
                return
            self.record_btn.setText(tr("🎙 Registra dal microfono"))
            self.timer_label.setText("")
            self._mic_files.append(wav_path)
            self._set_source(wav_path, from_mic=True)

    def _tick_timer(self):
        self.timer_label.setText(f"{self.recorder.elapsed_seconds:0.1f}s")

    # ------------------------------------------------------------ tempo / metrica / metronomo

    def _on_tempo_changed(self, value):
        self.project.tempo_bpm = value
        if self.metronome_checkbox.isChecked():
            self._restart_metronome()

    def _on_metrica_changed(self, text):
        text = text.strip()
        m = re.match(r"^(\d+)/(\d+)$", text)
        # Solo metriche valide: il valore finisce nel progetto (4/0 o 0/4
        # non vanno salvati ne' dati al metronomo).
        if m and 1 <= int(m.group(1)) <= 32 and int(m.group(2)) in (1, 2, 4, 8, 16, 32):
            self.project.time_sig = text
            if self.metronome_checkbox.isChecked():
                self._restart_metronome()

    def _on_metronome_toggled(self, checked):
        if checked:
            self._restart_metronome()
        else:
            self.metronome_engine.stop()

    def _restart_metronome(self):
        # Tempo/metrica costanti (nessun cambio a meta' qui): il click parte
        # SUBITO, non c'e' un rendering offline da aspettare come per la
        # riproduzione dell'ensemble.
        self.metronome_engine.start([(0.0, self.project.tempo_bpm)], [(0.0, self.project.time_sig)],
                                     offset_beats=0.0, start_immediately=True)

    # ------------------------------------------------------------ quantizzazione

    def _load_last_quantization(self):
        saved_grid = app_settings.get_last_quantization_grid()
        idx = self.grid_combo.findData(saved_grid)
        self.grid_combo.setCurrentIndex(idx if idx >= 0 else 3)  # 3 = 1/16 predefinito
        self.ternary_check.setChecked(app_settings.get_last_quantization_ternary())
        self._on_grid_changed()

    def _selected_grid(self):
        denom = self.grid_combo.currentData()
        ternary = self.ternary_check.isChecked() and denom in TERNARY_ENABLED_GRIDS
        return denom, ternary

    def _on_grid_changed(self):
        denom = self.grid_combo.currentData()
        enable = denom in TERNARY_ENABLED_GRIDS
        self.ternary_check.setEnabled(enable)
        if not enable:
            self.ternary_check.setChecked(False)

    # ------------------------------------------------------------ algoritmo pitch

    def _on_mode_changed(self):
        is_melodic = self.melodic_radio.isChecked()
        self.pitch_advanced_group.setEnabled(is_melodic)

    def _on_min_freq_auto_toggled(self, checked: bool):
        self.min_freq_spin.setEnabled(not checked)
        if checked:
            instr = get_instrument(self.instrument_name)
            self.min_freq_spin.setValue(_min_freq_hz_for_instrument(instr))

    def _reset_pitch_advanced_params(self):
        """Riporta i parametri di pitch tracking ai valori standard. Usato
        sia dal pulsante "Ripristina valori standard" sia per inizializzare
        i controlli all'apertura del dialogo."""
        self.min_freq_auto_check.setChecked(True)
        self.buf_size_combo.setCurrentIndex(0)   # Automatica
        self.hop_size_combo.setCurrentIndex(0)   # Automatico
        self.min_note_duration_spin.setValue(MIN_NOTE_DURATION_MS_DEFAULT)
        self.confidence_spin.setValue(PITCH_CONFIDENCE_THRESHOLD)

    def _selected_pitch_advanced_params(self, instr, is_percussion: bool, voice_source: bool):
        """Ritorna (min_freq_hz, buf_size, hop_size, confidence_threshold,
        min_note_duration_sec) da passare a convert_audio_to_track_text,
        ignorati per la batteria (is_percussion=True)."""
        if is_percussion:
            return None, None, None, None, None
        if self.min_freq_auto_check.isChecked():
            # Se la sorgente e' voce (non lo strumento reale), non ha senso
            # allargare la finestra di analisi sull'estensione grave dello
            # strumento di destinazione: chi canta/canticchia difficilmente
            # raggiunge davvero quel registro, e una finestra troppo larga
            # peggiorerebbe solo la risoluzione temporale (vedi core.audio_pitch).
            min_freq_hz = None if voice_source else _min_freq_hz_for_instrument(instr)
        else:
            min_freq_hz = self.min_freq_spin.value()
        buf_size = self.buf_size_combo.currentData()
        hop_size = self.hop_size_combo.currentData()
        confidence_threshold = self.confidence_spin.value()
        min_note_duration_sec = self.min_note_duration_spin.value() / 1000.0
        return min_freq_hz, buf_size, hop_size, confidence_threshold, min_note_duration_sec

    # ------------------------------------------------------------ conversione

    def _on_convert_clicked(self):
        if not self.source_path:
            return
        grid_denom, ternary = self._selected_grid()
        is_percussion = self.perc_radio.isChecked()
        instr = get_instrument(self.instrument_name)

        if (not self._from_mic and os.path.splitext(self.source_path)[1].lower() != ".wav"
                and not can_decode_compressed_audio()):
            QMessageBox.critical(
                self, tr("Decodificatore audio mancante"),
                tr("Per leggere mp3/m4a/flac/ogg serve il decodificatore di Qt Multimedia (incluso "
                   "in PySide6 installato con pip) oppure ffmpeg. In alternativa converti il file in WAV.")
            )
            return

        self._stop_preview_playback()
        self.convert_btn.setEnabled(False)
        self.preview_play_btn.setEnabled(False)
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
        self.preview_edit.setReadOnly(True)  # eventuali modifiche manuali precedenti verrebbero comunque sovrascritte dal nuovo risultato
        self.preview_edit.setPlainText(tr("Analisi audio in corso..."))

        voice_source = self.voice_source_check.isChecked()
        min_freq_hz, buf_size, hop_size, confidence_threshold, min_note_duration_sec = (
            self._selected_pitch_advanced_params(instr, is_percussion, voice_source)
        )
        self._cancelled = False

        def progress(frac):
            # Gira nel thread della conversione: l'annullamento la interrompe
            # al passo successivo (niente QThread.terminate, che puo' uccidere
            # il thread dentro il decodificatore o numpy e lasciare il dialogo bloccato).
            if self._cancelled:
                raise ConversionCancelled()
            worker.progress.emit(frac)

        worker = Worker(
            convert_audio_to_track_text,
            self.source_path, is_percussion, self.project.tempo_bpm,
            grid_denom, ternary, self.project.patterns, instr.default_octave,
            self.midi_dir, self._from_mic, min_freq_hz=min_freq_hz, voice_source=voice_source,
            buf_size=buf_size, hop_size=hop_size,
            pitch_confidence_threshold=confidence_threshold,
            min_note_duration_sec=min_note_duration_sec,
            align_to_first_note=self._from_mic and not self._recorded_with_metronome,
            progress_callback=progress, pass_progress=False,
        )
        self._worker = worker

        progress_dlg = QProgressDialog(tr("Analisi audio in corso..."), tr("Annulla"), 0, 100, self)
        progress_dlg.setWindowModality(Qt.WindowModal)
        progress_dlg.setMinimumDuration(0)
        progress_dlg.setAutoClose(False)
        progress_dlg.setValue(0)
        self._progress_dlg = progress_dlg

        worker.progress.connect(lambda frac: progress_dlg.setValue(min(100, int(frac * 100))))
        worker.finished_ok.connect(self._on_convert_ok)
        worker.finished_error.connect(self._on_convert_error)
        progress_dlg.canceled.connect(self._cancel_conversion)
        worker.start()

    def _cancel_conversion(self):
        self._cancelled = True

    def _on_convert_ok(self, text):
        self._worker.wait()
        self._progress_dlg.close()
        self._generated_text = text
        self.preview_edit.setPlainText(text)
        self.preview_edit.setReadOnly(False)
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(True)
        self.convert_btn.setEnabled(True)
        self.preview_play_btn.setEnabled(True)
        self._worker = None

    def _on_convert_error(self, msg):
        self._worker.wait()
        self._progress_dlg.close()
        if not self._cancelled:
            QMessageBox.critical(self, tr("Errore nella conversione"), msg)
        self.preview_edit.setPlainText("")
        self.convert_btn.setEnabled(True)
        self._worker = None

    # ------------------------------------------------------------ anteprima audio

    def _validate_preview_text(self):
        """Valida il contenuto ATTUALE dell'editor di anteprima (comprese
        eventuali modifiche manuali dell'utente dopo la conversione), con
        le stesse regole usate da core.audio_import per il testo generato
        automaticamente. Ritorna (ok, msg, text)."""
        text = self.preview_edit.toPlainText()
        instr = get_instrument(self.instrument_name)
        ok, msg = validate_track_text(
            text, self.project.patterns, default_octave=instr.default_octave, midi_dir=self.midi_dir
        )
        return ok, msg, text

    def _on_preview_play(self):
        ok, msg, text = self._validate_preview_text()
        if not text.strip():
            return
        if not ok:
            QMessageBox.critical(self, tr("Errore di sintassi"), tr("Impossibile riprodurre le modifiche:\n{msg}", msg=msg))
            return
        project = Project(name="preview", tempo_bpm=self.project.tempo_bpm)
        copy_synth(project.add_track("Anteprima", self.instrument_name, text), self.project.find_track(self.track_name))

        self._preview_highlight.play(project, self.project.patterns, get_instrument(self.instrument_name).default_octave,
                                     midi_dir=self.midi_dir, only_audible=False)

    def _stop_preview_playback(self):
        self._preview_highlight.stop()

    def _on_preview_selection_context_menu(self, sel_start: int, sel_end: int, global_pos) -> bool:
        """Tasto destro su una selezione dell'anteprima: ▶ Play la ascolta."""
        return handle_selection_context_menu(
            self.preview_edit, self.preview_edit.toPlainText(), sel_start, sel_end,
            self.project.patterns, get_instrument(self.instrument_name), self.instrument_name,
            self.project.tempo_bpm, self._preview_playback, global_pos, midi_dir=self.midi_dir,
            play_only=True, before_play=self._preview_highlight.stop,
            synth_track=self.project.find_track(self.track_name),
        )

    # ------------------------------------------------------------ esito

    def accept(self):
        ok, msg, text = self._validate_preview_text()
        if not ok:
            QMessageBox.critical(self, tr("Errore di sintassi"), tr("Correggi l'anteprima prima di confermare:\n{msg}", msg=msg))
            return
        self._stop_preview_playback()
        self.metronome_engine.stop()
        grid_denom, ternary = self._selected_grid()
        app_settings.set_last_quantization_grid(grid_denom)
        app_settings.set_last_quantization_ternary(ternary)
        self._generated_text = text  # riflette le eventuali modifiche manuali, non solo il testo generato
        super().accept()

    def reject(self):
        self._stop_preview_playback()
        self.metronome_engine.stop()
        super().reject()

    def done(self, result):
        # Chiusura in qualunque modo (Ok, Annulla, Esc, X): niente deve
        # restare attivo dopo il dialogo.
        if self.recorder is not None and self.recorder.is_recording:
            if self._rec_timer:
                self._rec_timer.stop()
                self._rec_timer = None
            try:
                self._mic_files.append(self.recorder.stop())
            except Exception:
                pass
        if self._worker is not None:
            self._cancelled = True
            self._worker.wait()
        self._stop_preview_playback()
        self.metronome_engine.stop()
        for path in self._mic_files:
            try:
                os.remove(path)
            except OSError:
                pass
        self._mic_files = []
        super().done(result)

    def result_text(self):
        return self._generated_text
