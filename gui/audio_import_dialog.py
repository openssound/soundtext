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
    QMessageBox, QButtonGroup,
    QSpinBox, QGroupBox, QProgressBar, QWidget
)

from core import settings as app_settings
from core.model import Project, copy_synth
from core.instruments import get_instrument
from core.audio_import import ConversionCancelled, SilentAudio, convert_audio_to_track_text
from core.audio_decode import can_decode_compressed_audio
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

class _Silence(str):
    """Risultato di una conversione di un audio quasi silenzioso: il
    messaggio da mostrare (vedi core.audio_import.SilentAudio)."""


def _convert_or_silence(*args, **kwargs):
    """convert_audio_to_track_text, ma un audio silenzioso non e' un errore
    da finestra a comparsa: torna il messaggio da mostrare nel passo 3."""
    try:
        return convert_audio_to_track_text(*args, **kwargs)
    except SilentAudio as e:
        return _Silence(str(e))


def _audio_seconds(path: str):
    """Durata di un WAV in secondi, o None (altri formati, file illeggibile)."""
    try:
        from core.audio_tracks import read_wav_info
        info = read_wav_info(path)
        return info.frames / float(info.samplerate)
    except Exception:
        return None


def _beats_per_bar(time_sig: str) -> float:
    """Quarti per battuta della metrica del brano ("6/8" -> 3); 4 se non si legge."""
    try:
        num, den = (int(x) for x in str(time_sig).split("/"))
        return 4.0 * num / den
    except (ValueError, ZeroDivisionError):
        return 4.0


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
        # Conversione automatica: parte poco dopo l'ultima scelta (audio,
        # modalita', opzioni). Se ne serve una nuova mentre un'altra e' in
        # corso, quella viene annullata e si riparte. Un'anteprima modificata a
        # mano non si sovrascrive da sola (resta "Converti di nuovo").
        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.setInterval(350)
        self._auto_timer.timeout.connect(self._auto_convert)
        self._restart_after_cancel = False
        self._preview_edited = False
        self._setting_preview = False
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

        # ================= 2. Audio: registrazione o file, tempo del brano
        # (costruito prima, mostrato dopo "Cosa riconoscere": prima si sceglie
        # cosa riconoscere, poi si registra o si sceglie il file)
        audio_box = QGroupBox(tr("2. Audio"))
        audio_layout = QVBoxLayout(audio_box)
        self.drop_frame = QFrame()                  # tutta la finestra accetta il trascinamento
        self.drop_frame.setFrameShape(QFrame.StyledPanel)
        self.drop_frame.setObjectName("panelBox")
        source_row = QHBoxLayout(self.drop_frame)
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
        source_row.addWidget(self.record_btn)
        browse_btn = QPushButton(tr("📂 Scegli file..."))
        browse_btn.clicked.connect(self._browse_file)
        source_row.addWidget(browse_btn)
        drop_hint = QLabel(tr("oppure trascina qui un file .wav/.mp3/.m4a"))
        drop_hint.setEnabled(False)
        source_row.addWidget(drop_hint)
        source_row.addStretch(1)
        self.timer_label = QLabel("")
        source_row.addWidget(self.timer_label)
        audio_layout.addWidget(self.drop_frame)
        self.source_label = QLabel(tr("Nessun audio scelto."))
        audio_layout.addWidget(self.source_label)

        # tempo / metrica / metronomo (per registrare a tempo; il tempo serve
        # anche alla conversione)
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
        self.metronome_checkbox = QCheckBox(tr("Metronomo durante la registrazione"))
        self.metronome_checkbox.setChecked(False)
        self.metronome_checkbox.setToolTip(
            tr("Fa sentire un click a tempo, utile per registrare a tempo dal microfono.\n"
            "Suono e volume si impostano in Opzioni → Metronomo, nella finestra principale.")
        )
        self.metronome_checkbox.toggled.connect(self._on_metronome_toggled)
        tempo_row.addWidget(self.metronome_checkbox)
        tempo_row.addStretch(1)
        audio_layout.addLayout(tempo_row)
        layout.addWidget(audio_box)

        # ================= 1. Cosa riconoscere: modalita' e solo le sue opzioni
        mode_box = QGroupBox(tr("1. Cosa riconoscere"))
        mode_layout = QVBoxLayout(mode_box)
        mode_row = QHBoxLayout()
        mode_row.setSpacing(0)
        self.melodic_radio = QPushButton(tr("Melodia"))
        self.perc_radio = QPushButton(tr("Percussioni"))
        self.chords_radio = QPushButton(tr("Accordi"))
        mode_group = QButtonGroup(self)
        mode_group.setExclusive(True)
        for button in (self.melodic_radio, self.perc_radio, self.chords_radio):
            button.setCheckable(True)
            button.setMinimumWidth(110)
            button.setObjectName("modeTab")
            mode_group.addButton(button)
            mode_row.addWidget(button)
        # la scheda scelta col colore di evidenziazione del tema (chiaro o scuro)
        mode_box.setStyleSheet("QPushButton#modeTab:checked { background: palette(highlight); "
                               "color: palette(highlighted-text); font-weight: bold; }")
        mode_row.addStretch(1)
        if instr.is_percussion:
            self.perc_radio.setChecked(True)
        else:
            self.melodic_radio.setChecked(True)
        mode_layout.addLayout(mode_row)
        self.mode_description = QLabel()
        self.mode_description.setWordWrap(True)
        mode_layout.addWidget(self.mode_description)

        options_row = QHBoxLayout()
        # quantizzazione: melodia e percussioni (gli accordi vanno a quarti)
        self.quant_widget = QWidget()
        quant_row = QHBoxLayout(self.quant_widget)
        quant_row.setContentsMargins(0, 0, 0, 0)
        quant_row.addWidget(QLabel(tr("Quantizzazione:")))
        self.grid_combo = QComboBox()
        for label, denom in GRID_CHOICES:
            self.grid_combo.addItem(label, denom)
        self.grid_combo.currentIndexChanged.connect(self._on_grid_changed)
        quant_row.addWidget(self.grid_combo)
        self.ternary_check = QCheckBox(tr("Ternario (terzine, 8T/16T)"))
        self.ternary_check.toggled.connect(self._on_grid_changed)
        quant_row.addWidget(self.ternary_check)
        options_row.addWidget(self.quant_widget)
        # voce invece dello strumento: melodia e percussioni (riga sua: con la
        # quantizzazione accanto non ci stava)
        voice_row = QHBoxLayout()
        self.voice_source_check = QCheckBox()
        self.voice_source_check.setToolTip(
            tr("Attiva se stai cantando/canticchiando la parte (basso, melodia...) o imitando la "
            "batteria con la bocca, invece di registrare lo strumento vero: la voce umana ha "
            "caratteristiche acustiche diverse (intonazione meno stabile, nessuna vera risonanza "
            "grave come quella di una cassa) e l'analisi viene ricalibrata di conseguenza.")
        )
        self.voice_source_check.toggled.connect(self._schedule_conversion)
        voice_row.addWidget(self.voice_source_check)
        voice_row.addStretch(1)
        # settime: solo accordi
        self.sevenths_check = QCheckBox(tr("Riconosci le settime (7, maj7, m7)"))
        self.sevenths_check.setToolTip(
            tr("Le settime si confondono con gli armonici delle altre note: di base si scrivono "
               "solo triadi (maggiori, minori, diminuite, sus4). Con questa opzione si cercano anche "
               "le settime; capita di perderne qualcuna."))
        self.sevenths_check.toggled.connect(self._schedule_conversion)
        options_row.addWidget(self.sevenths_check)
        options_row.addStretch(1)
        mode_layout.addLayout(options_row)
        mode_layout.addLayout(voice_row)

        # parametri avanzati del pitch tracking: solo melodia (Opzioni -> Import audio)
        self.pitch_widget = QWidget()
        pitch_row = QHBoxLayout(self.pitch_widget)
        pitch_row.setContentsMargins(0, 0, 0, 0)
        self.pitch_params_btn = QPushButton(tr("Parametri avanzati..."))
        self.pitch_params_btn.setToolTip(tr("Gli stessi di Opzioni → Import audio: valgono per tutti gli import."))
        self.pitch_params_btn.clicked.connect(self._edit_pitch_params)
        pitch_row.addWidget(self.pitch_params_btn)
        self.pitch_hint_label = QLabel()
        pitch_row.addWidget(self.pitch_hint_label)
        pitch_row.addStretch(1)
        mode_layout.addWidget(self.pitch_widget)
        self._refresh_pitch_hint()
        layout.insertWidget(layout.indexOf(audio_box), mode_box)

        self._load_last_quantization()
        mode_group.buttonToggled.connect(lambda _button, checked: checked and self._on_mode_changed())
        self._on_mode_changed()

        # ================= 3. Risultato: conversione (automatica) e anteprima
        result_box = QGroupBox(tr("3. Risultato"))
        result_layout = QVBoxLayout(result_box)
        convert_row = QHBoxLayout()
        self.convert_btn = QPushButton(tr("Converti di nuovo"))
        self.convert_btn.setEnabled(False)
        self.convert_btn.setToolTip(
            tr("La conversione parte da sola quando scegli l'audio o cambi le opzioni; questo "
               "pulsante la rifa' (anche dopo aver modificato a mano l'anteprima)."))
        self.convert_btn.clicked.connect(self._on_convert_clicked)
        convert_row.addWidget(self.convert_btn)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximumHeight(10)
        self.progress_bar.hide()
        convert_row.addWidget(self.progress_bar, 1)
        self.cancel_btn = QPushButton(tr("Annulla"))
        self.cancel_btn.clicked.connect(self._cancel_conversion)
        self.cancel_btn.hide()
        convert_row.addWidget(self.cancel_btn)
        convert_row.addStretch(0)
        result_layout.addLayout(convert_row)
        self.result_status = QLabel(tr("Scegli o registra un audio: la conversione parte da sola."))
        self.result_status.setEnabled(False)
        result_layout.addWidget(self.result_status)

        self.preview_edit = NotationEditor()
        self.preview_edit.setFont(QFont("Monospace", 10))
        self.preview_edit.setReadOnly(True)
        self.preview_edit.on_selection_context_menu = self._on_preview_selection_context_menu
        self.preview_edit.textChanged.connect(self._on_preview_edited)
        self._highlighter = NotationHighlighter(self.preview_edit.document())
        # Evidenziazione, nell'anteprima, di cio' che sta suonando.
        self._preview_highlight = PlayHighlighter(self.preview_edit, self, "_preview_playback")
        result_layout.addWidget(self.preview_edit)

        preview_play_row = QHBoxLayout()
        self.preview_play_btn = QPushButton(tr("▶ Ascolta"))
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
        result_layout.addLayout(preview_play_row)
        layout.addWidget(result_box, 1)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok = self.button_box.button(QDialogButtonBox.Ok)
        ok.setText(tr("Inserisci nella traccia"))
        ok.setEnabled(False)
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
        name = tr("registrazione dal microfono") if from_mic else os.path.basename(path)
        seconds = _audio_seconds(path)
        self.source_label.setText("✓ " + name + (f" — {int(seconds // 60)}:{int(seconds % 60):02d}"
                                                  if seconds is not None else ""))
        self.convert_btn.setEnabled(True)
        self._preview_edited = False            # audio nuovo: risultato nuovo
        self._schedule_conversion()

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
        self._schedule_conversion()

    def _on_metrica_changed(self, text):
        text = text.strip()
        m = re.match(r"^(\d+)/(\d+)$", text)
        # Solo metriche valide: il valore finisce nel progetto (4/0 o 0/4
        # non vanno salvati ne' dati al metronomo).
        if m and 1 <= int(m.group(1)) <= 32 and int(m.group(2)) in (1, 2, 4, 8, 16, 32):
            self.project.time_sig = text
            if self.metronome_checkbox.isChecked():
                self._restart_metronome()
            self._schedule_conversion()

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
        self._schedule_conversion()

    # ------------------------------------------------------------ algoritmo pitch

    def _on_mode_changed(self):
        """Si vedono solo le opzioni della modalita' scelta."""
        melodic, chords = self.melodic_radio.isChecked(), self.chords_radio.isChecked()
        self.mode_description.setText(
            tr("Una nota alla volta: voce, basso, chitarra solista, fiati...") if melodic else
            tr("Gli accordi di una chitarra, di un pianoforte o di un brano intero, un accordo per "
               "quarto al tempo del brano: \"4: 4C | 2Am 2G | ...\".") if chords else
            tr("Colpi di batteria o beatbox, riconosciuti come kick, snare e hihat."))
        self.quant_widget.setVisible(not chords)
        self.voice_source_check.setVisible(not chords)
        self.voice_source_check.setText(
            tr("Sto cantando (non lo strumento)") if melodic else tr("Sto facendo beatbox (non la batteria)"))
        self.sevenths_check.setVisible(chords)
        self.pitch_widget.setVisible(melodic)
        self._schedule_conversion()

    def _refresh_pitch_hint(self):
        from .audio_pitch_dialog import is_customized
        self.pitch_hint_label.setText(tr("In uso: valori personalizzati.") if is_customized() else "")

    def _edit_pitch_params(self):
        from .audio_pitch_dialog import AudioPitchDialog
        if AudioPitchDialog(self).exec():
            self._refresh_pitch_hint()
            self._schedule_conversion()

    def _selected_pitch_advanced_params(self, instr, is_percussion: bool, voice_source: bool):
        """Ritorna (min_freq_hz, buf_size, hop_size, confidence_threshold,
        min_note_duration_sec) da passare a convert_audio_to_track_text,
        ignorati per la batteria (is_percussion=True)."""
        if is_percussion:
            return None, None, None, None, None
        from .audio_pitch_dialog import current_pitch_params
        params = current_pitch_params()
        if params["min_freq_auto"]:
            # Se la sorgente e' voce (non lo strumento reale), non ha senso
            # allargare la finestra di analisi sull'estensione grave dello
            # strumento di destinazione: chi canta/canticchia difficilmente
            # raggiunge davvero quel registro, e una finestra troppo larga
            # peggiorerebbe solo la risoluzione temporale (vedi core.audio_pitch).
            min_freq_hz = None if voice_source else _min_freq_hz_for_instrument(instr)
        else:
            min_freq_hz = params["min_freq_hz"]
        buf_size = params["buf_size"]
        hop_size = params["hop_size"]
        confidence_threshold = params["confidence"]
        min_note_duration_sec = params["min_note_ms"] / 1000.0
        return min_freq_hz, buf_size, hop_size, confidence_threshold, min_note_duration_sec

    # ------------------------------------------------------------ conversione

    def _schedule_conversion(self, *_args):
        """Conversione automatica poco dopo l'ultima scelta (vedi __init__)."""
        if getattr(self, "source_path", None) and hasattr(self, "preview_edit") and not self._preview_edited:
            self._auto_timer.start()

    def _auto_convert(self):
        if self._preview_edited:
            return
        self._start_conversion()

    def _on_convert_clicked(self):
        """Converti di nuovo: anche sopra le modifiche fatte a mano."""
        self._preview_edited = False
        self._start_conversion()

    def _on_preview_edited(self):
        if not self._setting_preview and not self.preview_edit.isReadOnly():
            self._preview_edited = True
            self.result_status.setText(tr("Anteprima modificata a mano: le nuove scelte non la "
                                          "sovrascrivono, premi \"Converti di nuovo\" per rifarla."))

    def _set_preview_text(self, text):
        self._setting_preview = True
        try:
            self.preview_edit.setPlainText(text)
        finally:
            self._setting_preview = False

    def _start_conversion(self):
        self._auto_timer.stop()              # questa conversione vale anche per quella in attesa
        if not self.source_path:
            return
        if self._worker is not None:
            # se ne vuole una nuova: si annulla quella in corso e si riparte
            self._restart_after_cancel = True
            self._cancelled = True
            return
        grid_denom, ternary = self._selected_grid()
        is_percussion = self.perc_radio.isChecked()
        is_chords = self.chords_radio.isChecked()
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
        self.preview_play_btn.setEnabled(False)
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
        self.preview_edit.setReadOnly(True)  # eventuali modifiche manuali precedenti verrebbero comunque sovrascritte dal nuovo risultato
        self.result_status.setText(tr("Analisi audio in corso..."))

        voice_source = self.voice_source_check.isChecked() and not is_chords
        min_freq_hz, buf_size, hop_size, confidence_threshold, min_note_duration_sec = (
            self._selected_pitch_advanced_params(instr, is_percussion or is_chords, voice_source)
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
            _convert_or_silence,
            self.source_path, is_percussion, self.project.tempo_bpm,
            grid_denom, ternary, self.project.patterns, instr.default_octave,
            self.midi_dir, self._from_mic, min_freq_hz=min_freq_hz, voice_source=voice_source,
            buf_size=buf_size, hop_size=hop_size,
            pitch_confidence_threshold=confidence_threshold,
            min_note_duration_sec=min_note_duration_sec,
            align_to_first_note=self._from_mic and not self._recorded_with_metronome,
            chords=is_chords, sevenths=is_chords and self.sevenths_check.isChecked(),
            beats_per_bar=_beats_per_bar(self.project.time_sig),
            progress_callback=progress, pass_progress=False,
        )
        self._worker = worker

        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.cancel_btn.show()
        worker.progress.connect(lambda frac: self.progress_bar.setValue(min(100, int(frac * 100))))
        worker.finished_ok.connect(self._on_convert_ok)
        worker.finished_error.connect(self._on_convert_error)
        worker.start()

    def _cancel_conversion(self):
        """Annulla dell'avanzamento: ferma la conversione in corso."""
        self._restart_after_cancel = False
        self._cancelled = True

    def _conversion_finished(self) -> bool:
        """Pulizia comune; True se va rifatta subito (le scelte sono
        cambiate mentre girava)."""
        self._worker.wait()
        self._worker = None
        self.progress_bar.hide()
        self.cancel_btn.hide()
        if self._restart_after_cancel:
            self._restart_after_cancel = False
            self._start_conversion()
            return True
        return False

    def _on_convert_ok(self, text):
        if self._conversion_finished():
            return
        if isinstance(text, _Silence):
            self._generated_text = None
            self._set_preview_text("")
            self.result_status.setText(str(text))
            self.convert_btn.setEnabled(True)
            return
        self._generated_text = text
        self._set_preview_text(text)
        self.preview_edit.setReadOnly(False)
        self.result_status.setText(tr("Fatto: puoi ascoltarlo, modificarlo e inserirlo nella traccia."))
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(True)
        self.convert_btn.setEnabled(True)
        self.preview_play_btn.setEnabled(True)

    def _on_convert_error(self, msg):
        cancelled = self._cancelled
        if self._conversion_finished():
            return
        if not cancelled:
            QMessageBox.critical(self, tr("Errore nella conversione"), msg)
        self.result_status.setText(tr("Conversione annullata.") if cancelled else tr("Conversione non riuscita."))
        self.convert_btn.setEnabled(True)

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
