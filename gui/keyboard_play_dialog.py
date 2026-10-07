"""
Dialogo "Suona con la tastiera": registra una sequenza di note/accordi
(traccia melodica) o colpi (traccia percussiva) suonati con la tastiera del
computer, li quantizza sulla griglia ritmica scelta e li converte in
notazione testuale, con anteprima riascoltabile e modificabile prima
dell'inserimento nella traccia corrente (vedi core.audio_quantize).

Intestazione (Tempo/Metrica/Metronomo) e flusso finale (anteprima
modificabile, "Ascolta anteprima", Ok/Annulla) analoghi a
gui.audio_import_dialog, di cui questo dialogo e' il pendant "strumento
suonato dal vivo" invece che "audio registrato/caricato".
"""

import re
import threading
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QCheckBox, QDialogButtonBox, QMessageBox,
    QSpinBox,
)

from core import settings as app_settings
from core.model import Project, copy_synth
from core.instruments import get_instrument, DRUM_MIDI_CHANNEL, PERCUSSION_MAP
from core.chords import parse_key_signature
from core.audio_quantize import audio_events_to_validated_text
from core.notation import validate_track_text
from core.playback import PlaybackEngine, LiveSynth, LivePluginSynth
from .audio_import_dialog import GRID_CHOICES, TERNARY_ENABLED_GRIDS
from .highlighter import NotationHighlighter
from .metronome_engine import MetronomeEngine
from .play_highlight import PlayHighlighter
from .selection_actions import handle_selection_context_menu
from .voicing_picker import NotationEditor
from .theme import TEXT_DIM
from .keyboard_note_map import build_note_key_map, build_scale_key_map, build_janko_key_map
from .keyboard_performance import (  # noqa: F401  (BEND_*: riesportati per i test)
    KeyboardPerformanceMixin, BEND_SEMITONES, BEND_RAMP_UP_MS, BEND_RAMP_DOWN_MS, LIVE_MELODIC_CHANNEL,
)
from .keyboard_surface import KeySurface
from .midi_keyboard import MidiKeyboardMixin
from .piano_keyboard_widget import PianoKeyboardWidget
from core.i18n import tr

# Opzioni del selettore "Layout": (etichetta, (modo, parametro)).
# modo 'chromatic': tutti e 12 i semitoni per riga (comportamento originale).
# modo 'scale': solo le note della scala di project.key, parametro = scale_type
#   per core.chords.scale_pitch_classes ('diatonica'/'pentatonica'/'blues').
# modo 'janko': disposizione isomorfa a toni interi (vedi build_janko_key_map),
#   parametro non usato (None) - non dipende dalla tonalita'.
LAYOUT_CHOICES = [
    (tr("Cromatica"), ("chromatic", None)),
    (tr("Scala della tonalità (diatonica)"), ("scale", "diatonica")),
    (tr("Scala della tonalità (pentatonica)"), ("scale", "pentatonica")),
    (tr("Scala della tonalità (blues)"), ("scale", "blues")),
    (tr("Jankó (isomorfa)"), ("janko", None)),
]

PIANO_OCTAVES = 4  # ottave mostrate dalla tastiera pianistica visuale (vedi _piano_start_octave)

# Etichette a video delle tre righe fisiche usate da PERCUSSION_KEYS (vedi
# gui.keyboard_note_map.NOTE_ROW_KEYS, stessa disposizione delle righe note):
# la legenda (vedi _legend_text) accoppia ogni etichetta al nome di
# percussione nella stessa posizione, riga per riga, fermandosi alla prima
# riga non riempita da core.instruments.PERCUSSION_MAP.
_PERCUSSION_ROW_LABELS = [
    ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "'", "ì"],
    ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "È", "+"],
    ["A", "S", "D", "F", "G", "H", "J", "K", "L", "Ò", "À", "Ù"],
]

class KeyboardPlayDialog(MidiKeyboardMixin, KeyboardPerformanceMixin, QDialog):
    """Registra una performance dalla tastiera del computer (o da una
    tastiera MIDI collegata, vedi gui.midi_keyboard) e restituisce il testo
    tramite result_text() se l'utente conferma con Ok."""

    def __init__(self, parent, project, instrument_name, context_label, midi_dir=None,
                 current_track_name=None):
        super().__init__(parent)
        self.project = project
        self.instrument_name = instrument_name
        self.context_label = context_label
        self.midi_dir = midi_dir
        # Nome della traccia REALE del progetto che questa sessione sta
        # popolando (se ce n'e' una: il dialogo puo' anche essere aperto per
        # un pattern, che non corrisponde a nessuna traccia esistente). Se
        # nota, viene esclusa dall'ascolto delle "altre tracce" (vedi
        # other_tracks_checkbox) per non sovrapporre il suo contenuto
        # vecchio a quello che si sta registrando/riascoltando al suo posto.
        self.current_track_name = current_track_name
        self.instr = get_instrument(instrument_name)

        self.setWindowTitle(tr("Suona con la tastiera — {context_label}", context_label=context_label))
        self.resize(700, 660)

        self._generated_text = None
        self._recording = False
        self._playing_live = False
        self._record_start_wall = None
        self._active_notes = {}      # Qt.Key -> {"start": t, "midi_notes": [...], "velocity": v} oppure {"start": t, "perc_name": ...}
        self._captured_events = []   # List[AudioEvent]
        self._rec_timer = None

        # Tasti esecutivi laterali (vedi gui.keyboard_note_map): stato di
        # "tenuto premuto" tracciato a mano (non tramite event.modifiers() di
        # Qt, che copre solo Maiusc/Ctrl/Alt come modificatori di ALTRI
        # tasti, non Z/X/C/... della riga qualita').
        self._held_quality_key = None   # Qt.Key tenuto tra QUALITY_ROW_KEYS/BASS_DOUBLE_KEY, o None
        self._sustain_active = False     # SUSTAIN_KEY (default Bloc Maiusc) tenuto premuto
        self._strum_active = False       # STRUM_KEY (default L-Alt) tenuto premuto
        self._bend_active = False        # BEND_KEY (default L-Maiusc) tenuto premuto
        # Tasto-nota che possiede al momento la rampa di pitch bend dal vivo
        # (vedi BEND_SEMITONES): None se nessun bending "vero" e' in corso.
        # Un solo bending alla volta puo' controllare davvero il canale
        # condiviso (vedi limite noto su BEND_SEMITONES); un bending piu'
        # recente prende il controllo, quello precedente si limita a fermare
        # la propria nota senza piu' toccare il pitch bend del canale.
        self._live_bend_key = None
        self._inversion_active = False   # INVERSION_KEY (default L-Ctrl) tenuto premuto
        self._velocity_low = False       # VELOCITY_TOGGLE_KEY (default Tab): commuta, non tenuto
        # Note il cui tasto e' stato rilasciato mentre il sustain era attivo:
        # restano "in sostegno" (suono dal vivo e durata registrata non ancora
        # chiuse) finche' il sustain stesso non viene rilasciato (vedi
        # _finish_note/_flush_sustained_notes).
        self._sustained_notes = []

        # Arpeggiatore (ARPEGGIATOR_KEY, default Barra spaziatrice): mentre
        # tenuto premuto, ricicla a tempo tra le altezze di tutti i tasti-nota
        # premuti DOPO di lui (vedi _current_arpeggio_pool/_on_arpeggio_tick) -
        # un tasto gia' suonato PRIMA di premere lo spazio continua invece
        # normalmente, non retroattivamente arpeggiato.
        self._arpeggiator_active = False
        self._arpeggio_index = 0
        self._arpeggio_current_live_note = None
        self._arpeggio_timer = QTimer(self)
        self._arpeggio_timer.timeout.connect(self._on_arpeggio_tick)

        # Synth in tempo reale per il feedback sonoro dei tasti (vedi
        # core.playback.LiveSynth): creato pigramente al primo Registra/Suona,
        # None se la libreria FluidSynth o il SoundFont non sono disponibili (in quel caso
        # si registra/suona comunque, semplicemente senza sentire i tasti).
        self._live_synth = None
        # Se la traccia ha uno strumento plugin (SFZ interno, LV2, VST3) i
        # tasti li suona quello (core.playback.LivePluginSynth). Aprirlo puo'
        # richiedere secondi: lo si comincia a caricare in sottofondo
        # all'apertura del dialogo (_start_plugin_loader), cosi' al primo
        # Registra/Suona di solito e' gia' pronto.
        self._plugin_loader = None       # threading.Thread che lo sta aprendo
        self._plugin_loaded = None       # LivePluginSynth (o None) aperto dal thread
        self._plugin_generation = 0      # cambia quando un caricamento non serve piu'
        self._plugin_lock = threading.Lock()

        self.metronome_engine = MetronomeEngine(self)

        self._preview_playback = PlaybackEngine()
        # Motore separato per l'ascolto di sottofondo delle "altre tracce"
        # durante la registrazione/prova dal vivo (vedi other_tracks_checkbox):
        # indipendente da _preview_playback, che riproduce invece l'anteprima
        # gia' registrata quando non si sta suonando dal vivo.
        self._backing_playback = PlaybackEngine()

        self._init_midi_keyboard()
        self._build_ui()
        # Evidenziazione, nell'anteprima, di cio' che sta suonando.
        self._preview_highlight = PlayHighlighter(self.preview_edit, self, "_preview_playback")
        self._start_plugin_loader()

    # ------------------------------------------------------------ UI

    def _build_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            tr("Destinazione: <b>{context_label}</b> (strumento: {instrument_name})", context_label=self.context_label, instrument_name=self.instrument_name)
        ))

        # --- tempo / metrica / metronomo (identico a gui.audio_import_dialog)
        tempo_row = QHBoxLayout()
        tempo_row.addWidget(QLabel(tr("Tempo (BPM):")))
        self.tempo_spin = self._make_tempo_spin()
        tempo_row.addWidget(self.tempo_spin)

        tempo_row.addSpacing(12)
        tempo_row.addWidget(QLabel(tr("Metrica:")))
        self.metrica_combo = self._make_metrica_combo()
        tempo_row.addWidget(self.metrica_combo)

        tempo_row.addSpacing(12)
        tempo_row.addWidget(QLabel(tr("Tonalità:")))
        self.key_combo = self._make_key_combo()
        tempo_row.addWidget(self.key_combo)

        tempo_row.addSpacing(12)
        tempo_row.addWidget(QLabel(tr("Ottava:")))
        self.octave_spin = self._make_octave_spin()
        tempo_row.addWidget(self.octave_spin)

        tempo_row.addSpacing(12)
        tempo_row.addWidget(QLabel(tr("Layout:")))
        self.layout_combo = self._make_layout_combo()
        tempo_row.addWidget(self.layout_combo)
        self._rebuild_note_key_map()

        tempo_row.addSpacing(12)
        self.metronome_checkbox = QCheckBox(tr("Metronomo"))
        self.metronome_checkbox.setChecked(False)
        self.metronome_checkbox.setToolTip(
            tr("Fa sentire un click a tempo durante la registrazione, per suonare a tempo.\n"
            "Suono e volume si impostano in Opzioni → Metronomo, nella finestra principale.")
        )
        tempo_row.addWidget(self.metronome_checkbox)
        tempo_row.addStretch(1)
        layout.addLayout(tempo_row)

        # --- quantizzazione (stessa scelta di gui.audio_import_dialog)
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
        # Buffer del synth in tempo reale (vedi core.settings.get_live_period_size):
        # l'utente sceglie tra reattivita' dei tasti e rischio di crepitii.
        quant_row.addWidget(QLabel(tr("Latenza tasti:")))
        self.latency_combo = QComboBox()
        self._latency_tooltip = (
            tr("Ritardo tra la pressione di un tasto e il suono.\n"
            "Se senti crepitii o suono 'fritto', scegli un valore più alto."))
        self.latency_combo.setToolTip(self._latency_tooltip)
        # Niente millisecondi nelle etichette: dipendono dal driver audio
        # (vedi core.playback._live_buffer_settings), li mostra latency_info_label.
        for period_size, label in ((256, tr("Bassa")), (512, tr("Media")), (1024, tr("Alta"))):
            self.latency_combo.addItem(label, period_size)
        self.latency_combo.setCurrentIndex(
            max(0, self.latency_combo.findData(app_settings.get_live_period_size())))
        self.latency_combo.currentIndexChanged.connect(self._on_latency_changed)
        quant_row.addWidget(self.latency_combo)
        # Driver audio aperto davvero e buffer (vedi LiveSynth.description):
        # compilato al primo Registra/Suona, quando il synth viene creato.
        self.latency_info_label = QLabel("")
        self.latency_info_label.setStyleSheet(f"color: {TEXT_DIM};")
        quant_row.addWidget(self.latency_info_label)
        layout.addLayout(quant_row)
        self._load_last_quantization()

        # --- ascolto delle altre tracce
        other_tracks_row = QHBoxLayout()
        self.other_tracks_checkbox = QCheckBox(tr("Ascolta anche le altre tracce (rispetta Solo/Mute)"))
        self.other_tracks_checkbox.setChecked(False)
        self.other_tracks_checkbox.setToolTip(
            tr("Se spuntato, mentre suoni con la tastiera (Registra/Suona) o riascolti "
            "l'anteprima senti anche le altre tracce del progetto, con lo stesso stato "
            "Solo/Mute che hanno nel mixer — utile per suonare/valutare la nuova parte "
            "nel contesto dell'arrangiamento invece che isolata.\n"
            "Se non spuntato (comportamento di sempre): senti solo lo strumento corrente.")
        )
        other_tracks_row.addWidget(self.other_tracks_checkbox)
        other_tracks_row.addStretch(1)
        layout.addLayout(other_tracks_row)

        # --- tastiera MIDI esterna (vedi gui.midi_keyboard)
        self._build_midi_row(layout)

        # --- legenda tastiera
        self.legend_label = QLabel(self._legend_text())
        self.legend_label.setWordWrap(True)
        self.legend_label.setObjectName("panelBox")
        self.legend_label.setStyleSheet("padding: 6px 8px;")
        self.legend_label.setFont(QFont("Monospace", 9))
        layout.addWidget(self.legend_label)

        # --- registrazione / prova
        record_row = QHBoxLayout()
        self.record_btn = QPushButton(tr("🎹 Registra"))
        self.record_btn.setToolTip(tr("Avvia/ferma la registrazione della performance dalla tastiera."))
        self.record_btn.clicked.connect(self._toggle_recording)
        record_row.addWidget(self.record_btn)
        self.play_btn = QPushButton(tr("🔊 Suona"))
        self.play_btn.setToolTip(
            tr("Suona con la tastiera senza registrare, per provare la parte prima di registrarla.")
        )
        self.play_btn.clicked.connect(self._toggle_play)
        record_row.addWidget(self.play_btn)
        self.timer_label = QLabel("")
        record_row.addWidget(self.timer_label)
        record_row.addStretch(1)
        layout.addLayout(record_row)

        self.key_surface = KeySurface(self._on_surface_key_press, self._on_surface_key_release)
        self.key_surface.setMinimumHeight(70)
        self.key_surface.setObjectName("panelBox")
        surface_layout = QVBoxLayout(self.key_surface)
        self.surface_label = QLabel(tr("Premi 'Registra' o 'Suona' e poi usa la tastiera come strumento..."))
        self.surface_label.setAlignment(Qt.AlignCenter)
        self.surface_label.setWordWrap(True)
        surface_layout.addWidget(self.surface_label)

        # Riscontro visivo di cio' che si sta suonando in questo momento
        # (vedi _update_piano_display): sempre utile per sapere a quale
        # suono corrisponde il tasto appena premuto, coi 36 identificatori
        # percussivi disponibili (vedi core.instruments.PERCUSSION_MAP) - la
        # tastiera pianistica invece no, per le percussioni, che non hanno
        # un'altezza.
        self.now_playing_label = QLabel(" ")
        self.now_playing_label.setAlignment(Qt.AlignCenter)
        self.now_playing_label.setFont(QFont("Monospace", 11, QFont.Bold))
        surface_layout.addWidget(self.now_playing_label)
        if self.instr.is_percussion:
            self.piano_widget = None
        else:
            self.piano_widget = PianoKeyboardWidget(
                n_octaves=PIANO_OCTAVES, start_octave=self._piano_start_octave())
            surface_layout.addWidget(self.piano_widget, alignment=Qt.AlignHCenter)
        layout.addWidget(self.key_surface)

        # --- anteprima
        layout.addWidget(QLabel(
            tr("Anteprima (modificabile a registrazione completata; verra' inserita in ")
            + self.context_label + "):"
        ))
        self.preview_edit = NotationEditor()
        self.preview_edit.setFont(QFont("Monospace", 10))
        self.preview_edit.setReadOnly(True)
        self.preview_edit.on_selection_context_menu = self._on_preview_selection_context_menu
        self._highlighter = NotationHighlighter(self.preview_edit.document())
        layout.addWidget(self.preview_edit)

        preview_play_row = QHBoxLayout()
        self.preview_play_btn = QPushButton(tr("▶ Ascolta anteprima"))
        self.preview_play_btn.setEnabled(False)
        self.preview_play_btn.setToolTip(
            tr("Riproduce il contenuto attuale dell'anteprima, comprese le eventuali "
            "modifiche fatte a mano dopo la registrazione.")
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

    def _make_tempo_spin(self):
        spin = QSpinBox()
        spin.setRange(20, 300)
        spin.setValue(self.project.tempo_bpm)
        spin.setToolTip(tr("Tempo del progetto: usato anche per quantizzare la registrazione."))
        spin.valueChanged.connect(self._on_tempo_changed)
        return spin

    def _make_metrica_combo(self):
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItems(["2/4", "3/4", "4/4", "5/4", "6/8", "7/8", "9/8", "12/8"])
        combo.setCurrentText(self.project.time_sig)
        combo.setFixedWidth(70)
        combo.setToolTip(tr("Metrica del progetto, es. 4/4, 3/4, 6/8."))
        combo.currentTextChanged.connect(self._on_metrica_changed)
        return combo

    def _make_key_combo(self):
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItems([
            "", "C", "G", "D", "A", "E", "B", "F#", "Db", "Ab", "Eb", "Bb", "F",
            "Am", "Em", "Bm", "F#m", "C#m", "G#m", "Ebm", "Bbm", "Fm", "Cm", "Gm", "Dm",
        ])
        combo.setCurrentText(self.project.key)
        combo.setFixedWidth(70)
        combo.setToolTip(
            tr("Tonalità del progetto, es. C, Am, G, Em... (vuota = non impostata).\n"
            "Usata dal layout 'Scala della tonalità' qui sotto: cambiarla qui si riflette "
            "anche nella toolbar principale e viceversa (stesso progetto).")
        )
        combo.currentTextChanged.connect(self._on_key_changed)
        return combo

    def _make_octave_spin(self):
        spin = QSpinBox()
        # Limite superiore scelto perche' anche la riga piu' acuta (A, due
        # ottave sopra) resti sempre entro il range MIDI valido (0-127) per
        # una nota singola (gli accordi sono comunque ricondotti nel range
        # dello strumento da voice_chord, ma una nota singola no).
        spin.setRange(0, 6)
        # Preimpostata cosi' che la riga A (la piu' "centrale", due ottave
        # sopra quella numerica) corrisponda all'ottava predefinita dello
        # strumento scelto (core.instruments.InstrumentProfile.default_octave).
        spin.setValue(max(0, min(6, self.instr.default_octave - 2)))
        spin.setFixedWidth(60)
        spin.setToolTip(
            tr("Ottava di partenza (riga numerica 1..0): la riga Q e' un'ottava sopra, "
            "la riga A due ottave sopra. Preimpostata su un valore adatto allo strumento scelto.")
        )
        spin.setEnabled(not self.instr.is_percussion)
        spin.valueChanged.connect(self._on_octave_changed)
        return spin

    def _make_layout_combo(self):
        combo = QComboBox()
        for label, data in LAYOUT_CHOICES:
            combo.addItem(label, data)
        combo.setEnabled(not self.instr.is_percussion)
        combo.setToolTip(
            tr("Disposizione dei tasti-nota sulle tre righe:\n"
            "- Cromatica: 12 semitoni per riga, un'ottava ciascuna (3 ottave totali).\n"
            "- Scala della tonalità (diatonica/pentatonica/blues): solo le note della scala "
            "scelta - richiede una Tonalità valida nella toolbar principale, altrimenti ricade "
            "sulla cromatica; copre più ottave quanto più corta e' la scala.\n"
            "- Jankó: righe a toni interi sfalsate di un semitono, isomorfa (stessa forma = "
            "stesso intervallo ovunque) - copre 2 ottave, indipendente dalla tonalità.")
        )
        combo.currentIndexChanged.connect(self._on_layout_changed)
        return combo

    def _legend_text(self) -> str:
        if self.instr.is_percussion:
            names = list(PERCUSSION_MAP.keys())
            lines = []
            for row_labels in _PERCUSSION_ROW_LABELS:
                row_names = names[:len(row_labels)]
                names = names[len(row_labels):]
                if not row_names:
                    break
                lines.append(" ".join(f"{lbl}={n}" for lbl, n in zip(row_labels, row_names)))
            return "Percussioni:\n" + "\n".join(lines)
        base = self.octave_spin.value() if hasattr(self, "octave_spin") else max(0, self.instr.default_octave - 2)
        chord_legend = (
            tr("Accordi: tieni premuto un tasto della fila Z-/ insieme alla nota — "
            "Z maggiore · X minore · C 7ª dominante · V minore 7 · B maggiore 7 · N sospeso (sus4) · "
            "M aggiunta 9ª · , diminuito 7 · . power chord · / basso profondo (ottava sotto)\n"
            "Bloc Maiusc = sustain (tenuto) · L-Alt = strumming (tenuto) · L-Maiusc = bending (tenuto) · "
            "L-Ctrl = inversione (tenuto) · Tab = commuta Piano/Forte (60/110) · "
            "Barra spazio = arpeggio continuo a tempo (tenuto)")
        )
        mode, param = self.layout_combo.currentData() if hasattr(self, "layout_combo") else ("chromatic", None)

        if mode == "janko":
            return (
                tr("Modalita' Jankó — riga numeri e riga A suonano le stesse note (toni interi pari), "
                "la riga Q le note dispari un semitono sopra: stessa forma = stesso intervallo ovunque\n")
                + chord_legend
            )

        if mode == "scale":
            try:
                parse_key_signature(self.project.key)
                return (
                    tr("Modalita' scala {param} ({key}) — ogni riga percorre solo le note della scala, dal grado 1 all'ottava {base} in su\n", param=param, key=self.project.key, base=base) + chord_legend
                )
            except ValueError:
                return (
                    tr("Nessuna tonalita' valida in toolbar: uso la disposizione cromatica al suo posto.\n")
                    + chord_legend
                )

        return (
            tr("Riga numeri (1..0 ' ì) → ottava {base} · Riga Q (Q..P È +) → ottava {0} · Riga A (A..L Ò À Ù) → ottava {1}\nOgni riga, in ordine: do do# re re# mi fa fa# sol sol# la la# si\n", base + 1, base + 2, base=base)
            + chord_legend
        )

    def _rebuild_note_key_map(self):
        mode, param = self.layout_combo.currentData()
        if mode == "janko":
            self._note_key_map = build_janko_key_map(self.octave_spin.value())
            return
        if mode == "scale":
            try:
                self._note_key_map = build_scale_key_map(self.octave_spin.value(), self.project.key, param)
                return
            except ValueError:
                pass  # tonalita' non valida (o diventata tale nel frattempo): ricade sul cromatico
        self._note_key_map = build_note_key_map(self.octave_spin.value())

    def _piano_start_octave(self) -> int:
        """Ottava di partenza (Do piu' grave mostrato) della tastiera
        pianistica visuale: la piu' bassa raggiungibile dalla mappa
        tasto->nota ATTUALE (self._note_key_map, che dipende da ottava/
        layout/tonalita' scelti - vedi _rebuild_note_key_map), non una
        posizione fissa: ancorarla un'ottava sotto quella scelta in 'Ottava'
        (comportamento originale) sprecava sempre la prima ottava mostrata
        nella disposizione cromatica (usata di fatto solo dal raro basso
        profondo, vedi BASS_DOUBLE_KEY) e, all'opposto, con una scala corta
        come la pentatonica - che copre piu' ottave a parita' di 12 tasti
        per riga, vedi gui.keyboard_note_map.build_scale_key_map - lasciava
        le note piu' acute fuori dalle PIANO_OCTAVES ottave visibili a
        destra. Partire dalla piu' bassa raggiunta usa quindi la prima
        ottava per davvero e mostra piu' dell'estensione realmente in uso,
        anche se una scala molto corta puo' comunque superare le
        PIANO_OCTAVES ottave totali disponibili (limite di una tastiera a
        dimensione fissa)."""
        if not self._note_key_map:
            return max(0, self.octave_spin.value())
        return max(0, min(octave for _, octave in self._note_key_map.values()))

    def _refresh_piano_range(self):
        if self.piano_widget is not None:
            self.piano_widget.set_range(self._piano_start_octave())

    def _on_octave_changed(self, value):
        self._rebuild_note_key_map()
        self.legend_label.setText(self._legend_text())
        self._refresh_piano_range()

    def _on_layout_changed(self, index):
        self._rebuild_note_key_map()
        self.legend_label.setText(self._legend_text())
        self._refresh_piano_range()

    # ------------------------------------------------------------ tempo / metrica

    def _on_tempo_changed(self, value):
        self.project.tempo_bpm = value
        if self.metronome_checkbox.isChecked() and (self._recording or self._playing_live):
            self._restart_metronome()

    def _on_metrica_changed(self, text):
        text = text.strip()
        if re.match(r"^\d+/\d+$", text):
            self.project.time_sig = text
            if self.metronome_checkbox.isChecked() and (self._recording or self._playing_live):
                self._restart_metronome()

    def _on_key_changed(self, text):
        # Come project.tempo_bpm/time_sig: scrive direttamente sull'oggetto
        # Project condiviso con la finestra principale, che si riallinea da
        # sola alla chiusura del dialogo (vedi _sync_tempo_metrica_fields).
        self.project.key = text.strip()
        # Il layout 'Scala della tonalita'' dipende da project.key: se era
        # ricaduto sulla cromatica per mancanza di una tonalita' valida (o va
        # ricalcolato per la nuova), va rigenerata subito la mappa e la legenda.
        self._rebuild_note_key_map()
        self.legend_label.setText(self._legend_text())
        self._refresh_piano_range()

    def _restart_metronome(self):
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

    # ------------------------------------------------------------ registrazione

    def _set_controls_enabled(self, enabled: bool):
        for w in (self.tempo_spin, self.metrica_combo, self.metronome_checkbox,
                  self.grid_combo, self.ternary_check, self.preview_play_btn,
                  self.other_tracks_checkbox, self.latency_combo):
            w.setEnabled(enabled)
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(enabled and self._generated_text is not None)

    def _build_context_project(self, preview_text=None):
        """Costruisce il progetto da riprodurre per l'ascolto dal vivo o
        dell'anteprima: se 'Ascolta anche le altre tracce' e' spuntato,
        include le altre tracce del progetto reale COSI' COME SONO ORA
        (rispettando lo stato Solo/Mute che hanno nel mixer in questo
        momento), escludendo quella corrente se nota (current_track_name) -
        altrimenti se ne sentirebbe il contenuto vecchio insieme a quello
        nuovo che si sta registrando/riascoltando al suo posto. Se
        preview_text e' dato, aggiunge anche una traccia "Anteprima" con
        quel testo (usata da _on_preview_play; per l'ascolto dal vivo invece
        None, il feedback sonoro dei tasti lo da' gia' _live_synth)."""
        combined = Project(name="context", tempo_bpm=self.project.tempo_bpm,
                            time_sig=self.project.time_sig)
        if self.other_tracks_checkbox.isChecked():
            for t in self.project.audible_tracks():
                if self.current_track_name and t.name == self.current_track_name:
                    continue
                nt = combined.add_track(t.name, t.instrument_name, t.text)
                nt.volume = t.volume
                nt.pan = t.pan
                copy_synth(nt, t)
        if preview_text is not None:
            copy_synth(combined.add_track("Anteprima", self.instrument_name, preview_text),
                       self.project.find_track(self.current_track_name))
        return combined

    def _start_backing_playback(self):
        if not self.other_tracks_checkbox.isChecked():
            return
        bg = self._build_context_project()
        if not bg.tracks:
            return
        self._backing_playback.play(bg, only_audible=False)

    def _stop_backing_playback(self):
        self._backing_playback.stop()

    def _instrument_active(self) -> bool:
        return self._recording or self._playing_live

    def _plugin_source_track(self):
        """La traccia con lo strumento plugin che deve suonare i tasti, o None
        (nessuna traccia, traccia col SoundFont o traccia audio)."""
        if not self.current_track_name:
            return None
        track = self.project.find_track(self.current_track_name)
        if track is None or not track.synth or track.is_audio:
            return None
        return track

    def _start_plugin_loader(self):
        """Comincia ad aprire in sottofondo lo strumento plugin della traccia
        (se ce n'e' uno e non lo si sta gia' aprendo)."""
        track = self._plugin_source_track()
        if track is None or self._plugin_loader is not None:
            return
        ref, params, state, pan = track.synth, dict(track.synth_params), track.synth_state, track.pan
        generation = self._plugin_generation

        def load():
            synth = LivePluginSynth.create(ref, params, state, pan)
            with self._plugin_lock:
                if generation == self._plugin_generation:
                    self._plugin_loaded = synth
                    return
            if synth is not None:       # non serve piu' (dialogo chiuso, buffer cambiato)
                synth.close()

        self._plugin_loader = threading.Thread(target=load, daemon=True)
        self._plugin_loader.start()

    def _take_plugin_synth(self):
        """Lo strumento plugin pronto da suonare (aspetta che finisca di
        aprirsi), o None se la traccia non ne ha o non si apre."""
        if self._plugin_loader is None:
            self._start_plugin_loader()
        loader = self._plugin_loader
        if loader is None:
            return None
        if loader.is_alive():
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                loader.join()
            finally:
                QApplication.restoreOverrideCursor()
        synth, self._plugin_loaded, self._plugin_loader = self._plugin_loaded, None, None
        return synth

    def _ensure_live_synth(self):
        """Crea il synth in tempo reale per il feedback sonoro dei tasti, se
        non gia' presente: lo strumento plugin della traccia se ne ha uno
        (e si apre), altrimenti FluidSynth col SoundFont. Fallisce
        silenziosamente (self._live_synth resta None) se la libreria
        FluidSynth o un SoundFont non sono disponibili: si puo' comunque
        registrare/suonare, solo senza sentire i tasti."""
        if self._live_synth is not None:
            return
        track = self._plugin_source_track()
        if track is not None:
            self._live_synth = self._take_plugin_synth()
            if self._live_synth is not None:
                self.latency_combo.setToolTip(self._latency_tooltip + "\n\n" + self._live_synth.description())
                self.latency_info_label.setText(self._live_synth.description())
                channel = DRUM_MIDI_CHANNEL if self.instr.is_percussion else LIVE_MELODIC_CHANNEL
                self._live_synth.set_program(channel, self.instr.gm_program)
                return
            self.surface_label.setText(
                self.surface_label.text()
                + tr("\n(lo strumento della traccia non suona dal vivo: uso il SoundFont)")
            )
        self._live_synth = LiveSynth.create()
        if self._live_synth is None:
            self.surface_label.setText(
                self.surface_label.text() + tr("\n(nessun feedback sonoro: SoundFont non trovato)")
            )
        else:
            self.latency_combo.setToolTip(self._latency_tooltip + "\n\n" + self._live_synth.description())
            self.latency_info_label.setText(self._live_synth.description())
            if not self.instr.is_percussion:
                self._live_synth.set_program(LIVE_MELODIC_CHANNEL, self.instr.gm_program)

    def _on_latency_changed(self):
        app_settings.set_live_period_size(self.latency_combo.currentData())
        # Il buffer si fissa all'apertura del driver audio: si chiude il
        # synth, verra' ricreato con il nuovo valore al prossimo Registra/Suona.
        self._close_live_synth()

    def _close_live_synth(self):
        if self._live_synth is not None:
            self._live_synth.close()
            self._live_synth = None
        self._discard_plugin_loader()

    def _discard_plugin_loader(self):
        """Lo strumento plugin aperto in anticipo non serve piu': lo chiude
        (subito se e' pronto, altrimenti il thread appena ha finito)."""
        with self._plugin_lock:
            self._plugin_generation += 1
            loaded, self._plugin_loaded = self._plugin_loaded, None
            self._plugin_loader = None
        if loaded is not None:
            loaded.close()

    def _grab_keyboard(self):
        # Cattura la tastiera a livello di sistema (non solo di widget Qt):
        # su X11 impedisce anche alle scorciatoie globali del desktop (es.
        # Ctrl+Alt+T per aprire un terminale) di scattare mentre si sta
        # suonando/registrando, dato che i tasti usati qui (numeri, lettere,
        # con Maiusc/Ctrl/Alt) si sovrappongono facilmente a quelle. Su
        # Wayland alcuni compositor riservano comunque certe scorciatoie
        # globali al di fuori del controllo delle applicazioni: in quel caso
        # questa chiamata non basta a prevenirle (limite della piattaforma,
        # non di questo dialogo).
        self.key_surface.grabKeyboard()

    def _ungrab_keyboard(self):
        self.key_surface.releaseKeyboard()

    def _toggle_recording(self):
        if not self._recording:
            self._stop_preview_playback()
            self._captured_events = []
            self._active_notes = {}
            self._generated_text = None
            self.preview_edit.setPlainText("")
            self._recording = True
            self._record_start_wall = time.time()
            self.record_btn.setText(tr("⏹ Ferma registrazione"))
            self.play_btn.setEnabled(False)
            self.surface_label.setText(tr("🎧 Registrazione in corso — suona con la tastiera..."))
            self._set_controls_enabled(False)
            self.key_surface.setFocus()
            self._grab_keyboard()
            self._ensure_live_synth()
            self._rec_timer = QTimer(self)
            self._rec_timer.timeout.connect(self._tick_record_timer)
            self._rec_timer.start(200)
            if self.metronome_checkbox.isChecked():
                self._restart_metronome()
            self._start_backing_playback()
        else:
            self._recording = False
            self._ungrab_keyboard()
            now = time.time()
            for key in list(self._active_notes.keys()):
                self._release_note(key, now)
            self._flush_sustained_notes(now)
            self._stop_arpeggiator()
            self._reset_live_bend()
            self._sustain_active = False
            self._strum_active = False
            self._bend_active = False
            self._inversion_active = False
            self._held_quality_key = None
            if self._rec_timer:
                self._rec_timer.stop()
                self._rec_timer = None
            self.metronome_engine.stop()
            self._stop_backing_playback()
            self.record_btn.setText(tr("🎹 Registra"))
            self.play_btn.setEnabled(True)
            self.timer_label.setText("")
            self.surface_label.setText(tr("Premi 'Registra' o 'Suona' e poi usa la tastiera come strumento..."))
            self._set_controls_enabled(True)
            self.record_btn.setFocus()
            self._generate_preview_from_events()

    def _toggle_play(self):
        if not self._playing_live:
            self._stop_preview_playback()
            self._active_notes = {}
            self._playing_live = True
            self.play_btn.setText(tr("⏹ Ferma"))
            self.record_btn.setEnabled(False)
            self.surface_label.setText(tr("🔊 Prova in corso — suona con la tastiera (non registrato)..."))
            self._set_controls_enabled(False)
            self.key_surface.setFocus()
            self._grab_keyboard()
            self._ensure_live_synth()
            if self.metronome_checkbox.isChecked():
                self._restart_metronome()
            self._start_backing_playback()
        else:
            self._playing_live = False
            self._ungrab_keyboard()
            now = time.time()
            for key in list(self._active_notes.keys()):
                self._release_note(key, now)
            self._flush_sustained_notes(now)
            self._stop_arpeggiator()
            self._reset_live_bend()
            self._sustain_active = False
            self._strum_active = False
            self._bend_active = False
            self._inversion_active = False
            self._held_quality_key = None
            self.metronome_engine.stop()
            self._stop_backing_playback()
            self.play_btn.setText(tr("🔊 Suona"))
            self.record_btn.setEnabled(True)
            self.surface_label.setText(tr("Premi 'Registra' o 'Suona' e poi usa la tastiera come strumento..."))
            self._set_controls_enabled(True)
            self.play_btn.setFocus()

    def _tick_record_timer(self):
        self.timer_label.setText(f"{time.time() - self._record_start_wall:0.1f}s")

    def _generate_preview_from_events(self):
        if not self._captured_events:
            QMessageBox.information(self, tr("Nessuna nota registrata"),
                                     tr("Non e' stata suonata nessuna nota durante la registrazione."))
            return
        grid_denom, ternary = self._selected_grid()
        try:
            text = audio_events_to_validated_text(
                self._captured_events, self.project.tempo_bpm, grid_denom, ternary,
                self.project.patterns, default_octave=self.instr.default_octave, midi_dir=self.midi_dir)
        except ValueError as e:
            QMessageBox.critical(self, tr("Errore nella conversione"), str(e))
            return
        self._generated_text = text
        self.preview_edit.setPlainText(text)
        self.preview_edit.setReadOnly(False)
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(True)
        self.preview_play_btn.setEnabled(True)

    # ------------------------------------------------------------ anteprima audio
    # (identico a gui.audio_import_dialog.AudioImportDialog)

    def _validate_preview_text(self):
        text = self.preview_edit.toPlainText()
        ok, msg = validate_track_text(
            text, self.project.patterns, default_octave=self.instr.default_octave, midi_dir=self.midi_dir
        )
        return ok, msg, text

    def _on_preview_play(self):
        ok, msg, text = self._validate_preview_text()
        if not text.strip():
            return
        if not ok:
            QMessageBox.critical(self, tr("Errore di sintassi"), tr("Impossibile riprodurre le modifiche:\n{msg}", msg=msg))
            return
        project = self._build_context_project(preview_text=text)

        self._preview_highlight.play(project, self.project.patterns, self.instr.default_octave,
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
            synth_track=self.project.find_track(self.current_track_name),
        )

    # ------------------------------------------------------------ esito

    def accept(self):
        if self._recording:
            self._toggle_recording()
        if self._playing_live:
            self._toggle_play()
        ok, msg, text = self._validate_preview_text()
        if not ok:
            QMessageBox.critical(self, tr("Errore di sintassi"), tr("Correggi l'anteprima prima di confermare:\n{msg}", msg=msg))
            return
        self._stop_preview_playback()
        self._stop_backing_playback()
        self.metronome_engine.stop()
        self._close_live_synth()
        self._close_midi_input()
        grid_denom, ternary = self._selected_grid()
        app_settings.set_last_quantization_grid(grid_denom)
        app_settings.set_last_quantization_ternary(ternary)
        self._generated_text = text
        super().accept()

    def reject(self):
        if self._recording or self._playing_live:
            self._ungrab_keyboard()
        if self._recording:
            self._recording = False
            if self._rec_timer:
                self._rec_timer.stop()
                self._rec_timer = None
        self._playing_live = False
        now = time.time()
        for key in list(self._active_notes.keys()):
            self._release_note(key, now)
        self._flush_sustained_notes(now)
        self._stop_arpeggiator()
        self._reset_live_bend()
        self._sustain_active = False
        self._strum_active = False
        self._bend_active = False
        self._inversion_active = False
        self._held_quality_key = None
        self._stop_preview_playback()
        self._stop_backing_playback()
        self.metronome_engine.stop()
        self._close_live_synth()
        self._close_midi_input()
        super().reject()

    def result_text(self):
        return self._generated_text
