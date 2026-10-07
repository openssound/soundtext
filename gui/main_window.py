import os
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QFont, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QSplitter, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QSlider, QSpinBox, QToolBar, QStatusBar, QProgressBar,
    QComboBox, QApplication, QStackedWidget, QMessageBox, QToolButton, QButtonGroup, QFrame,
    QSizePolicy, QMenu, QDialog, QDoubleSpinBox,
)
from core.i18n import tr

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.model import Project
from core.instruments import set_session_instruments
from core.history import ProjectHistory
from core.playback import PlaybackEngine
from core import settings as app_settings

from .voicing_picker import NotationEditor
from .highlighter import NotationHighlighter
from .theme import ACCENT, ACCENT_DIM, BAD, TEXT_DIM, get_active_theme, palette_for, stylesheet_for, set_active_theme
from .icons import icon
from .main_window_mixer import MixerMixin
from .main_window_project import ProjectMixin
from .main_window_playback import PlaybackMixin
from .metronome_engine import MetronomeEngine
from .arrangement_view import HEADER_WIDTH, ROW_GAP, ArrangementView
from .track_header import make_add_track_button, refresh_add_track_icon
from .effects_panel import EffectsPanel


class MainWindow(MixerMixin, ProjectMixin, PlaybackMixin, QMainWindow):
    def __init__(self):
        super().__init__()
        # Va fatto prima di costruire qualunque testata di traccia (vedi
        # refresh_mixer): quelle testate leggono il tema attivo per colorarsi,
        # non seguono automaticamente lo QSS globale (vedi
        # theme.track_card_colors/_apply_theme).
        set_active_theme(app_settings.get_theme())
        self.setWindowTitle(self.APP_TITLE)
        self.resize(1200, 720)

        self.project = Project(name=tr("Nuovo progetto"))
        self.current_path = None
        self.current_track_name = None
        # Modifiche non ancora salvate (vedi _mark_dirty/closeEvent in
        # gui.main_window_project): azzerato da _replace_project (nuovo/apri/
        # importa - il progetto appena caricato e' per definizione "a
        # riposo") e da save_project/save_project_as.
        self._dirty = False
        # Copia di recupero delle modifiche non salvate (vedi
        # gui.main_window_project._init_autosave e core.autosave).
        self._init_autosave()
        self.playback = PlaybackEngine()
        # Cronologia di Annulla/Ripeti dell'intero progetto (vedi _mark_dirty)
        self.history = ProjectHistory()
        self._restoring_history = False
        self.track_headers = {}

        # Stato di riproduzione (barra di avanzamento + evidenziazione token)
        self._playback_start_wall = None       # time.time() dell'inizio riproduzione corrente
        self._playback_offset_beats = 0.0        # da quale beat e' partito questo "segmento" di playback
        self._playback_duration_beats = 0.0
        # Beat a cui e' stata messa in pausa la riproduzione (vedi pause()),
        # None se non e' in pausa: distinto da uno Stop vero e proprio (che
        # invece azzera la posizione), permette al pulsante Play/Pausa in
        # toolbar di farla ripartire da dove si era interrotta.
        self._playback_paused_beat = None
        self._playback_timer = QTimer(self)
        self._playback_timer.setInterval(100)
        self._playback_timer.timeout.connect(self._update_playback_progress)
        # (chiave, span) dell'ultima traccia evidenziata durante la
        # riproduzione, vedi _update_playback_highlight.
        self._highlight_spans_cache = None
        # Debounce del riavvio playback su modifica Mute/Solo/Volume/Pan/Master:
        # ogni modifica riarma questo timer invece di riavviare subito, cosi'
        # un trascinamento rapido di uno slider (molti valueChanged ravvicinati)
        # produce UN SOLO riavvio (con re-render/re-play) quando l'interazione
        # si ferma, invece di uno per ogni tick — che altrimenti si accodano
        # tutti sul lock del synth condiviso, facendo crescere enormemente
        # l'attesa prima che si senta l'ultima impostazione scelta.
        self._mixer_restart_timer = QTimer(self)
        self._mixer_restart_timer.setSingleShot(True)
        self._mixer_restart_timer.setInterval(150)
        self._mixer_restart_timer.timeout.connect(self._perform_pending_mixer_restart)
        self._mixer_restart_pending = False

        # Mappa (beat -> bpm/metrica) del brano in riproduzione: calcolata da
        # play() (vedi core.tempo_map) e usata per tenere sincronizzati barra
        # di avanzamento, campi Tempo/Metrica e metronomo con eventuali cambi
        # dichiarati nel progetto, invece di assumere un tempo/metrica
        # costante per tutto il brano.
        self._playback_tempo_map = []
        self._playback_metrica_map = []

        # Metronomo della riproduzione ensemble (gui.metronome_engine): il
        # checkbox in toolbar parte SEMPRE deselezionato all'avvio del
        # programma (non e' un'impostazione persistente tra sessioni).
        self.metronome_engine = MetronomeEngine(self)
        self.metronome_engine.set_position_source(self._stream_position_beats)
        # Sezione in loop (beat di inizio/fine, vedi set_loop_start/set_loop_end
        # in gui.main_window_playback): None finche' non viene impostata.
        self._loop_a_beat = None
        self._loop_b_beat = None

        self._build_ui()
        self._build_menu()
        self.refresh_mixer()
        self.refresh_master_fx_button()
        # Vista di default all'avvio: Struttura brano (vedi
        # _toggle_arrangement_view), utile per farsi un'idea d'insieme del
        # brano appena aperto invece del testo di una singola traccia.
        self.arrangement_action.setChecked(True)

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        splitter = QSplitter(Qt.Horizontal)

        # --- Colonna sinistra: tracce (solo vista Testo) -----------------
        # Le stesse testate (gui.track_header: nome, strumento, M/S/●, ⋯,
        # manopole Vol e Pan) che nella vista Struttura brano stanno a
        # sinistra di ogni riga: qui una sotto l'altra, per scegliere la
        # traccia di cui modificare il testo.
        left = QWidget()
        self.mixer_panel = left
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 4, 0)
        left_layout.setSpacing(8)
        title = QLabel(tr("Tracce"))
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 2px 4px;")
        left_layout.addWidget(title)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.mixer_container = QWidget()
        self.mixer_layout = QVBoxLayout(self.mixer_container)
        self.mixer_layout.setContentsMargins(0, 0, 0, 0)
        self.mixer_layout.setSpacing(ROW_GAP)
        self.empty_state_label = QLabel(
            tr("Nessuna traccia nel progetto.\n\nUsa '+ Aggiungi traccia' qui sotto\nper iniziare a comporre.")
        )
        self.empty_state_label.setAlignment(Qt.AlignCenter)
        self.empty_state_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 13px; padding: 30px 10px;")
        self.empty_state_label.setWordWrap(True)
        self.mixer_layout.addWidget(self.empty_state_label)
        # Come nella vista Struttura: un solo pulsante, subito sotto l'ultima
        # testata (refresh_mixer inserisce le testate prima di lui); le
        # azioni sulle singole tracce stanno nel menu ⋯ di ogni testata.
        self.mixer_add_track_btn = make_add_track_button(self.populate_add_track_menu, HEADER_WIDTH - 20)
        self.mixer_layout.addWidget(self.mixer_add_track_btn, 0, Qt.AlignHCenter)
        self.mixer_layout.addStretch()
        self.scroll.setWidget(self.mixer_container)
        left_layout.addWidget(self.scroll)
        # Larga quanto le testate (piu' la barra di scorrimento): il resto
        # della finestra va all'editor.
        left.setFixedWidth(HEADER_WIDTH + self.scroll.verticalScrollBar().sizeHint().width() + 6)

        # --- Colonna destra: editor notazione ---------------------------
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setSpacing(8)

        self.track_title = QLabel(tr("Nessuna traccia selezionata"))
        self.track_title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 2px 0;")
        # Senza word-wrap, il suffisso "vista Struttura brano attiva: ..."
        # (select_track, per una traccia con box) rende il testo cosi' lungo
        # da far crescere il minimumSizeHint della finestra oltre la sua
        # larghezza corrente: Qt/il window manager sono allora costretti a
        # ridimensionarla (osservato dopo ogni import MIDI, che porta sempre
        # le tracce in modalita' box), perdendo anche il doppio click sulla
        # barra del titolo su alcuni window manager.
        self.track_title.setWordWrap(True)
        right_layout.addWidget(self.track_title)

        self.editor = NotationEditor()
        # Ctrl+Z/Ctrl+Y dell'editor vanno alla cronologia unica del progetto
        # (menu Modifica), che raggruppa la digitazione per pause.
        self.editor.use_window_undo()
        self.editor.setFont(QFont("Monospace", 11))
        self.editor.setToolTip(
            tr("Notazione della traccia corrente. Colori: note (azzurro), accordi (ambra), "
            "percussioni (viola), comandi di stato N: N@ (verde), riferimenti %pattern e &midi "
            "(corallo), blocchi [...] (giallo), pause (grigio). Doppio click su un accordo per "
            "scegliere un voicing alternativo. Seleziona una sequenza e tasto destro per "
            "Play / Raggruppa / Trasforma in pattern. Durante la digitazione compare un "
            "autocompletamento per qualita' d'accordo, stili di voicing, percussioni/dinamiche "
            "e riferimenti %pattern/&midi: frecce per scorrere, Invio/Tab per confermare, Esc per chiudere.")
        )
        self.editor.setPlaceholderText(
            tr("Seleziona o crea una traccia per scrivere la notazione, es:\n"
            "16: 100@ c*4 e*4 g*4 e*4 [c*4 e*4 g*4]")
        )
        self.editor.textChanged.connect(self.on_editor_changed)
        self.editor.on_double_click_token = self._on_editor_double_click
        self.editor.on_selection_context_menu = self._on_editor_selection_context_menu
        self.editor.on_completion_request = self._editor_completions
        self.highlighter = NotationHighlighter(self.editor.document())
        right_layout.addWidget(self.editor)

        self.validation_label = QLabel("")
        self.validation_label.setStyleSheet("padding: 5px 10px; border-radius: 5px;")
        right_layout.addWidget(self.validation_label)

        freeze_btn = QPushButton(tr("Congela accordi in note esplicite (voicing automatico)"))
        freeze_btn.setToolTip(
            tr("Sostituisce ogni accordo astratto (es. Cmaj7) con il blocco di note concrete\n"
            "generato dal motore di voicing per lo strumento di questa traccia.")
        )
        freeze_btn.clicked.connect(self.freeze_chords)
        relative_btn = QPushButton(tr("Altezze relative e tonalità"))
        relative_btn.setToolTip(
            tr("Riscrive le note della traccia con le ottave relative (rel:) e, se il brano ha una\n"
               "tonalità, con le sue alterazioni (key=): stesse note, testo più corto.")
        )
        relative_btn.clicked.connect(self.rewrite_relative)
        tools_row = QHBoxLayout()
        tools_row.addWidget(freeze_btn, 1)
        tools_row.addWidget(relative_btn)
        right_layout.addLayout(tools_row)

        # Area centrale: due pagine intercambiabili (vedi
        # _toggle_arrangement_view) - l'editor di testo classico (sopra) e la
        # vista "Struttura brano" ad arrangiamento a box (gui.arrangement_view),
        # alternativa per lavorare sulla struttura del brano su piu' tracce
        # invece che nota per nota su una traccia alla volta. La colonna
        # mixer a sinistra resta invariata in entrambe le modalita'.
        self.center_stack = QStackedWidget()
        self.center_stack.addWidget(right)
        self.arrangement_view = ArrangementView(self)
        self.center_stack.addWidget(self.arrangement_view)

        splitter.addWidget(left)
        splitter.addWidget(self.center_stack)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        # Pannello Effetti in fondo (gui.effects_panel), nascosto finche' non
        # si preme FX su una traccia.
        self.effects_panel = EffectsPanel(self)
        outer_splitter = QSplitter(Qt.Vertical)
        outer_splitter.addWidget(splitter)
        outer_splitter.addWidget(self.effects_panel)
        outer_splitter.setStretchFactor(0, 3)
        outer_splitter.setStretchFactor(1, 1)
        outer_splitter.setChildrenCollapsible(False)
        self.central_splitter = outer_splitter

        self.setCentralWidget(outer_splitter)
        self.setStatusBar(QStatusBar())
        # Promemoria delle scorciatoie della vista Struttura brano, a destra
        # nella barra di stato (visibile solo in quella vista).
        self.shortcuts_hint = QLabel(
            tr("Spazio Play · R Registra · Shift+Spazio ascolta il box · Canc elimina · "
            "Ctrl+D duplica · S dividi · Ctrl+rotella zoom · Ctrl+K cerca un comando"))
        self.shortcuts_hint.setStyleSheet(f"color: {TEXT_DIM}; padding-right: 8px;")
        self.statusBar().addPermanentWidget(self.shortcuts_hint)

    def _build_menu(self):
        menubar = self.menuBar()

        # Ordine: Progetto, Modifica, Vista, Traccia, Componi, Riproduzione,
        # Suoni, Opzioni, Aiuto. Import ed export stanno in sottomenu (del
        # progetto e della traccia): la palette dei comandi (Ctrl+K) li
        # trova comunque per nome, col percorso "Progetto › Esporta".
        file_menu = menubar.addMenu(tr("&Progetto"))
        file_menu.addAction(self._action(tr("Nuovo"), self.new_project, "Ctrl+N", tr("Crea un nuovo progetto vuoto.")))
        file_menu.addAction(self._action(tr("Apri..."), self.open_project, "Ctrl+O", tr("Apri un progetto .st esistente.")))
        file_menu.addAction(self._action(tr("Salva"), self.save_project, "Ctrl+S", tr("Salva il progetto corrente.")))
        file_menu.addAction(self._action(tr("Salva con nome..."), self.save_project_as, "Ctrl+Shift+S",
                                          tr("Salva il progetto corrente con un nuovo nome/percorso.")))
        file_menu.addSeparator()
        import_menu = file_menu.addMenu(tr("Importa"))
        import_menu.addAction(self._action(tr("MIDI..."), self.import_midi, "Ctrl+Shift+I",
                                            tr("Crea un nuovo progetto da un file MIDI (una traccia per canale).")))
        import_menu.addAction(self._action(tr("MusicXML..."), self.import_musicxml, None,
                                            tr("Crea un nuovo progetto da una partitura MusicXML (MuseScore, Finale, "
                                               "Sibelius, Dorico...): una traccia per parte, con le sigle degli accordi.")))
        import_menu.addAction(self._action(tr("ABC..."), self.import_abc, None,
                                            tr("Crea un nuovo progetto da un brano in notazione ABC (.abc: abcjs, "
                                               "EasyABC, raccolte di musica tradizionale): una traccia per voce.")))
        import_menu.addAction(self._action(tr("MTXT..."), self.import_mtxt, None,
                                            tr("Crea un nuovo progetto da un file MTXT (.mtxt, un evento per riga "
                                               "con i tempi in quarti): una traccia per canale, come un MIDI.")))
        export_menu = file_menu.addMenu(tr("Esporta"))
        export_menu.addAction(self._action(
            tr("Mix audio (WAV)..."), self.export_mix_wav,
            tooltip=tr("Esporta il brano come si sente (tracce udibili, comprese le tracce audio) "
            "in un file WAV 48 kHz / 24 bit.")))
        export_menu.addAction(self._action(tr("MIDI..."), self.export_midi, "Ctrl+Shift+E",
                                            tr("Esporta l'intero ensemble (tracce udibili) in un file MIDI.")))
        export_menu.addSeparator()
        export_menu.addAction(self._action(
            tr("Partitura PDF..."), self.export_score_pdf,
            tooltip=tr("Esporta le tracce udibili come partitura in PDF, pronta da stampare.")))
        export_menu.addAction(self._action(
            tr("Partitura MusicXML..."), self.export_musicxml,
            tooltip=tr("Esporta le tracce udibili come partitura MusicXML, da aprire e stampare "
            "con MuseScore, Finale, Sibelius o Dorico: note, sigle degli accordi, tonalità e metrica.")))
        export_menu.addAction(self._action(
            tr("Partitura ABC..."), self.export_abc,
            tooltip=tr("Esporta le tracce udibili in notazione ABC (testo), da aprire con abcjs, "
            "EasyABC o abcm2ps: note, sigle degli accordi, tonalità, metrica e testo cantato.")))
        export_menu.addSeparator()
        export_menu.addAction(self._action(
            tr("MTXT..."), self.export_mtxt,
            tooltip=tr("Esporta le tracce udibili in MTXT (testo, un evento per riga): note, strumenti, "
            "automazioni, tempo e metrica, come nel MIDI.")))
        file_menu.addSeparator()
        file_menu.addAction(self._action(tr("Esci"), self.close, "Ctrl+Q"))

        edit_menu = menubar.addMenu(tr("&Modifica"))
        self.undo_action = self._action(tr("Annulla"), self.undo, tooltip=tr("Annulla l'ultima modifica al progetto."))
        self.undo_action.setShortcuts([QKeySequence(QKeySequence.Undo)])
        self.redo_action = self._action(tr("Ripeti"), self.redo, tooltip=tr("Ripete la modifica appena annullata."))
        self.redo_action.setShortcuts([QKeySequence("Ctrl+Y"), QKeySequence("Ctrl+Shift+Z")])
        edit_menu.addAction(self.undo_action)
        edit_menu.addAction(self.redo_action)
        self._update_undo_actions()
        # Azioni sul box selezionato: le scorciatoie valgono nella vista
        # Struttura (Canc, S nell'editor di testo restano tasti normali).
        edit_menu.addSeparator()
        edit_menu.addAction(self._view_action(tr("Elimina il box selezionato"), self.arrangement_view.delete_selected_box,
                                              [QKeySequence.Delete]))
        edit_menu.addAction(self._view_action(tr("Duplica il box selezionato"),
                                              self.arrangement_view.duplicate_selected_box, ["Ctrl+D"]))
        edit_menu.addAction(self._view_action(tr("Dividi la clip audio alla testina"),
                                              self.arrangement_view.split_selected_at_playhead, ["S"]))

        view_menu = menubar.addMenu(tr("&Vista"))
        self.arrangement_action = QAction(tr("Struttura brano (a box)"), self, checkable=True)
        self.arrangement_action.setShortcut(QKeySequence("Ctrl+Shift+B"))
        self.arrangement_action.setToolTip(
            tr("Passa alla vista ad arrangiamento a box (tutte le tracce sullo stesso asse tempo) "
            "per lavorare sulla struttura del brano invece che sul testo di una traccia alla volta.")
        )
        self.arrangement_action.toggled.connect(self._toggle_arrangement_view)
        view_menu.addAction(self.arrangement_action)
        view_menu.addAction(self._action(
            tr("Partitura..."), self.show_score_view, "Ctrl+Shift+P",
            tr("Mostra le tracce su pentagramma, aggiornate mentre scrivi; da li' esporti in PDF e stampi.")))
        view_menu.addSeparator()
        view_menu.addAction(self._view_action(tr("Ingrandisci (zoom)"), self.arrangement_view.zoom_in,
                                              ["Ctrl+=", "Ctrl++"]))
        view_menu.addAction(self._view_action(tr("Riduci (zoom)"), self.arrangement_view.zoom_out, ["Ctrl+-"]))
        view_menu.addAction(self._view_action(tr("Zoom normale"), self.arrangement_view.zoom_reset, ["Ctrl+0"]))
        # Spazio e R: tasti singoli, solo nella vista Struttura (nell'editor
        # di testo servono a scrivere); nei menu restano F5 e Ctrl+R.
        self._view_action("Play/Pausa", self.toggle_play_pause, ["Space"])
        self._view_action(tr("Registra nella traccia audio"), lambda: self.record_into_audio_track(), ["R"])

        track_menu = menubar.addMenu(tr("&Traccia"))
        add_menu = track_menu.addMenu(tr("Aggiungi"))
        add_menu.addAction(self._action(tr("Traccia..."), self.add_track, "Ctrl+T"))
        add_menu.addAction(self._action(
            tr("Traccia con strumento virtuale (VST3/LV2)..."), self.add_plugin_track,
            tooltip=tr("Traccia le cui note le suona un plugin VST3 (o LV2) invece del SoundFont.")))
        add_menu.addAction(self._action(
            tr("Traccia audio..."), self.add_audio_track,
            tooltip=tr("Traccia per file audio registrati (voce, chitarra, tastiera...).")))
        track_menu.addAction(self._action(tr("Modifica nome/strumento..."), self.edit_track, "Ctrl+E"))
        synth_menu = track_menu.addMenu(tr("Strumento plugin"))
        synth_menu.addAction(self._action(
            tr("Scegli (VST3/LV2)..."), self.choose_track_synth,
            tooltip=tr("Fa suonare le note della traccia a uno strumento virtuale installato (VST3, o LV2 "
                    "su Linux) invece che al SoundFont.")))
        synth_menu.addAction(self._action(
            tr("Parametri..."), self.edit_track_synth,
            tooltip=tr("Riapre i parametri (e l'interfaccia grafica) dello strumento plugin della traccia selezionata.")))
        track_menu.addAction(self._action(tr("Rimuovi traccia selezionata"), self.remove_track))
        track_menu.addSeparator()
        track_import_menu = track_menu.addMenu(tr("Importa in questa traccia"))
        track_import_menu.addAction(self._action(tr("MIDI..."), self.import_midi_into_selected_track))
        track_import_menu.addAction(self._action(
            tr("Audio → notazione (microfono o file)..."), self.import_audio_into_selected_track,
            tooltip=tr("Registra dal microfono o carica un file audio (.wav/.mp3/.m4a) e lo converte in notazione.")
        ))
        track_import_menu.addAction(self._action(
            tr("File audio come clip (traccia audio)..."), self.import_audio_clip_into_selected_track,
            tooltip=tr("Aggiunge un file audio (.wav, mp3, flac, m4a, ogg...) come clip in coda "
            "alla traccia audio selezionata.")
        ))
        track_export_menu = track_menu.addMenu(tr("Esporta questa traccia"))
        track_export_menu.addAction(self._action(tr("MIDI..."), self.export_selected_track_midi))
        track_export_menu.addAction(self._action(
            tr("WAV..."), self.export_selected_track_wav,
            tooltip=tr("Esporta in un WAV solo la traccia selezionata, come si sente in Solo (con i suoi effetti).")
        ))
        track_export_menu.addAction(self._action(
            tr("WAV asciutto (per il re-amping)..."), lambda: self.export_selected_track_wav(dry=True),
            tooltip=tr("Esporta la traccia senza effetti, riverbero/chorus e pan, da far passare "
            "in un simulatore di amplificatore esterno.")
        ))
        track_menu.addSeparator()
        track_menu.addAction(self._action(
            tr("Registra nella traccia audio..."), self.record_into_audio_track, "Ctrl+R",
            tooltip=tr("Registra voce, chitarra o tastiera dalla scheda audio mentre suona il resto del brano.")
        ))
        track_menu.addAction(self._action(
            tr("Suona con la tastiera in questa traccia..."), self.play_keyboard_into_selected_track,
            tooltip=tr("Registra una performance suonata con la tastiera del computer e la converte in notazione.")
        ))

        compose_menu = menubar.addMenu(tr("&Componi"))
        generate_menu = compose_menu.addMenu(tr("Genera nella traccia selezionata"))
        generate_menu.addAction(self._action(
            tr("Batteria..."), self.generate_drums_into_selected_track,
            tooltip=tr("Genera un giro di batteria per genere (rock, funk, disco, reggae, punk, soul, bossa nova, rock'n'roll, shuffle, swing), senza IA: "
            "istantaneo, con variabilita' regolabile, nessun modello. Richiede una traccia percussiva.")
        ))
        generate_menu.addAction(self._action(
            tr("Basso da accordi..."), self.generate_bass_into_selected_track,
            tooltip=tr("Genera una linea di basso che segue gli accordi gia' scritti in un'altra traccia "
            "del progetto (fondamentale, walking, blues, ottavi, reggae, bossa, shuffle...), senza IA.")
        ))
        generate_menu.addAction(self._action(
            tr("Giro armonico..."), self.generate_progression_into_selected_track,
            tooltip=tr("Genera una progressione di accordi (pop, rock, blues, jazz, cadenza andalusa...) "
            "nella tonalita' scelta, da cui far derivare poi basso e accompagnamento, senza IA. "
            "Richiede uno strumento polifonico.")
        ))
        generate_menu.addAction(self._action(
            tr("Accompagnamento o riff..."), self.generate_melody_into_selected_track,
            tooltip=tr("Genera un accompagnamento (strumenti polifonici: accordi battuti, arpeggio, "
            "accordo spezzato, sostenuto, montuno) o un riff/melodia (strumenti monofonici: riff, "
            "botta e risposta, note guida, passaggio scalare, lick blues) che segue gli accordi gia' "
            "scritti in un'altra traccia del progetto, senza IA. Non per tracce percussive.")
        ))
        styles_menu = compose_menu.addMenu(tr("Stili dei generatori"))
        styles_menu.addAction(self._action(
            tr("Salva la traccia come stile..."), self.save_selected_track_as_style,
            tooltip=tr("Ricava dalla traccia selezionata un nuovo stile per Genera batteria/basso/"
            "accompagnamento/riff (giro base, alternative, fill; note come gradi dell'accordo).")
        ))
        styles_menu.addAction(self._action(
            tr("Stili personali..."), self.manage_user_styles,
            tooltip=tr("Rinomina o elimina gli stili salvati dai tuoi box, tracce o file MIDI.")
        ))
        compose_menu.addSeparator()
        compose_menu.addAction(self._action(tr("Gestisci libreria pattern (%Nome)..."), self.manage_patterns))
        compose_menu.addAction(self._action(tr("Gestisci libreria MIDI (&Nome)..."), self.manage_midi_library))
        compose_menu.addAction(self._action(
            tr("Estrai pattern dalle tracce..."), self.extract_patterns_action,
            tooltip=tr("Individua blocchi ripetuti in tutte le tracce e li converte in pattern riutilizzabili.")
        ))
        compose_menu.addAction(self._action(
            tr("Espandi pattern nelle tracce..."), self.expand_patterns_action,
            tooltip=tr("Sostituisce ogni riferimento %pattern e &midi con i token letterali corrispondenti.")
        ))
        compose_menu.addSeparator()
        compose_menu.addAction(self._action(
            tr("Analizza tonalità..."), self.analyze_key_action,
            tooltip=tr("Analizza le note di tutte le tracce non percussive del progetto e stima la "
            "tonalità (algoritmo di Krumhansl-Schmuckler), impostandola nel campo Tonalità.")))

        playback_menu = menubar.addMenu(tr("&Riproduzione"))
        self.play_pause_action = self._action(tr("Play ensemble"), self.toggle_play_pause, "F5")
        playback_menu.addAction(self.play_pause_action)
        playback_menu.addAction(self._action(tr("Stop"), self.stop, "F6"))
        # Shift+Spazio vale nella vista Struttura (vedi ArrangementView.preview_action).
        playback_menu.addAction(self.arrangement_view.preview_action)
        playback_menu.addSeparator()
        loop_menu = playback_menu.addMenu(tr("Loop"))
        loop_menu.addAction(self._action(
            tr("Loop: inizio (A) qui"), self.set_loop_start, tr("Ctrl+["),
            tooltip=tr("Imposta l'inizio della sezione da ripetere sul beat in riproduzione "
                    "(o sul punto di pausa).")
        ))
        loop_menu.addAction(self._action(
            tr("Loop: fine (B) qui"), self.set_loop_end, tr("Ctrl+]"),
            tooltip=tr("Imposta la fine della sezione da ripetere sul beat in riproduzione "
                    "(o sul punto di pausa).")
        ))
        self.loop_action = self._action(tr("Ripeti la sezione A-B"), self.toggle_loop, "Ctrl+L",
                                        tooltip=tr("Riproduce in loop la sezione tra A e B."))
        self.loop_action.setCheckable(True)
        self.loop_action.setEnabled(False)
        loop_menu.addAction(self.loop_action)
        loop_menu.addAction(self._action(tr("Cancella loop"), self.clear_loop))
        # Nome storico (era una casella nella barra dei comandi): e' un'azione
        # spuntabile con la stessa interfaccia (isChecked/setChecked/toggled).
        self.humanize_checkbox = QAction(tr("Umanizza"), self, checkable=True)
        self.humanize_checkbox.setChecked(app_settings.get_humanize_enabled())
        self.humanize_checkbox.setToolTip(
            tr("Aggiunge una piccola variazione casuale a timing e velocity delle note "
            "(non alla batteria, che riceve solo la variazione di velocity), diversa "
            "ad ogni riproduzione. Intensita' regolabile in Opzioni → Umanizza.")
        )
        self.humanize_checkbox.toggled.connect(self._on_humanize_toggled)
        playback_menu.addAction(self.humanize_checkbox)

        # Suoni: tutto cio' che decide come suonano le tracce.
        sounds_menu = menubar.addMenu(tr("&Suoni"))
        sounds_menu.addAction(self._action(tr("Gestisci strumenti..."), self.manage_instruments,
                                           tooltip=tr("Crea o rimuovi strumenti personalizzati.")))
        soundfont_menu = sounds_menu.addMenu(tr("SoundFont"))
        soundfont_menu.addAction(self._action(tr("Scegli SoundFont (.sf2)..."), self.choose_soundfont))
        soundfont_menu.addAction(self._action(tr("Usa rilevamento automatico del SoundFont"), self.reset_soundfont))
        soundfont_menu.addAction(self._action(tr("Mostra SoundFont in uso"), self.show_soundfont_info))
        sounds_menu.addAction(self._action(
            tr("Volume di sintesi (gain)..."), self.show_playback_gain_settings,
            tooltip=tr("Regola il guadagno del sintetizzatore: troppo alto puo' causare "
                    "crepitii/distorsione nei passaggi piu' densi.")
        ))
        sounds_menu.addAction(self._action(
            tr("Cartelle dei plugin VST3..."), self.show_plugin_dirs,
            tooltip=tr("Le cartelle in cui cercare i plugin VST3, oltre a quelle standard del sistema.")))
        sounds_menu.addSeparator()
        download_menu = sounds_menu.addMenu(tr("Scarica"))
        download_menu.addAction(self._action(
            tr("Scarica profili NAM consigliati..."), self.download_nam_profiles,
            tooltip=tr("Scarica nella cartella profili_nam una dozzina di profili NAM di amplificatori "
                    "e pedali famosi, da usare con l'effetto Profilo NAM.")))
        download_menu.addAction(self._action(
            tr("Scarica casse IR per gli amplificatori NAM..."), self.download_cab_irs,
            tooltip=tr("Scarica una ventina di casse per chitarra (risposte all'impulso) da abbinare "
                    "ai profili NAM di sola testata, con Cassa → File IR…")))

        options_menu = menubar.addMenu(tr("&Opzioni"))
        options_menu.addAction(self._action(
            tr("Metronomo..."), self.show_metronome_settings,
            tooltip=tr("Imposta il suono e il volume del click del metronomo.")
        ))
        options_menu.addAction(self._action(
            tr("Umanizza..."), self.show_humanize_settings,
            tooltip=tr("Imposta l'intensita' della variazione casuale di timing/velocity.")
        ))

        midi_import_menu = options_menu.addMenu(tr("Import MIDI"))
        recognize_chords_action = QAction(tr("Riconosci accordi nell'import MIDI"), self, checkable=True)
        recognize_chords_action.setChecked(app_settings.get_midi_import_recognize_chords())
        recognize_chords_action.setToolTip(
            tr("Se spuntato, un gruppo di note simultanee riconosciuto come accordo standard "
            "viene importato in forma implicita (es. 'Cmaj7') invece che come blocco "
            "esplicito '[...]'. L'accordo verra' pero' ri-vocalizzato automaticamente dal "
            "motore per lo strumento di destinazione al prossimo export, invece di "
            "riprodurre esattamente il voicing/registro originale del MIDI importato.")
        )
        recognize_chords_action.toggled.connect(app_settings.set_midi_import_recognize_chords)
        midi_import_menu.addAction(recognize_chords_action)
        midi_import_menu.addAction(self._action(
            tr("Slide nell'import MIDI..."), self.show_midi_import_slide_settings,
            tooltip=tr("Spunta 'Slide' per riconoscere anche i bend piu' piccoli come slide "
                    "(slide guitar) e regolare la soglia.")
        ))

        theme_menu = options_menu.addMenu(tr("Tema"))
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)
        current_theme = app_settings.get_theme()
        dark_action = QAction(tr("Scuro"), self, checkable=True)
        light_action = QAction(tr("Chiaro"), self, checkable=True)
        dark_action.setChecked(current_theme != "light")
        light_action.setChecked(current_theme == "light")
        dark_action.triggered.connect(lambda: self._apply_theme("dark"))
        light_action.triggered.connect(lambda: self._apply_theme("light"))
        for act in (dark_action, light_action):
            theme_group.addAction(act)
            theme_menu.addAction(act)

        language_menu = options_menu.addMenu(tr("Lingua"))
        language_group = QActionGroup(self)
        language_group.setExclusive(True)
        from core.i18n import LANGUAGES, current_language
        for code, name in LANGUAGES.items():
            act = QAction(name, self, checkable=True)
            act.setChecked(code == current_language())
            act.triggered.connect(lambda _checked=False, c=code: self._choose_language(c))
            language_group.addAction(act)
            language_menu.addAction(act)

        help_menu = menubar.addMenu(tr("&Aiuto"))
        self.command_palette_action = self._action(
            tr("Cerca un comando..."), self.open_command_palette, "Ctrl+K",
            tooltip=tr("Trova qualsiasi funzione scrivendone il nome (esporta, registra, genera...)."))
        help_menu.addAction(self.command_palette_action)
        help_menu.addAction(self._action(tr("Guida utente..."), self.show_help, "F1"))
        palette_btn = QPushButton(tr("Cerca un comando…   Ctrl+K"))
        palette_btn.setObjectName("paletteButton")
        palette_btn.setToolTip(tr("Trova qualsiasi funzione scrivendone il nome (Ctrl+K)"))
        palette_btn.setStyleSheet(f"QPushButton#paletteButton {{ color: {TEXT_DIM}; padding: 2px 14px; "
                                  "text-align: left; min-width: 220px; }")
        palette_btn.clicked.connect(self.open_command_palette)
        menubar.setCornerWidget(palette_btn, Qt.TopRightCorner)
        self.palette_btn = palette_btn
        help_menu.addAction(self._action(
            tr("Apri il file di log"), self.open_log_file,
            tooltip=tr("Errori e problemi registrati dall'app (utile per capire perche' qualcosa non funziona).")
        ))
        from core.version import SUPPORT_URL
        self.support_action = None
        if SUPPORT_URL:
            self.support_action = self._action(
                tr("Sostieni SoundText..."), self.open_support_page,
                tooltip=tr("SoundText e' gratuito e libero: se ti e' utile puoi sostenerne lo sviluppo "
                           "(si apre la pagina nel browser)."))
            help_menu.addAction(self.support_action)
        help_menu.addSeparator()
        help_menu.addAction(self._action(tr("Informazioni su SoundText..."), self.show_about))

        self._toolbar_icons = []   # (pulsante, icona, colore o None = colore del testo): vedi _refresh_toolbar_icons
        toolbar = QToolBar("Comandi")
        toolbar.setMovable(False)
        toolbar.setObjectName("mainToolbar")
        self.addToolBar(toolbar)

        # --- Trasporto ---------------------------------------------------
        self.rewind_btn = self._tool_button("rewind", tr("Torna all'inizio del brano"), lambda: self.seek_to_beat(0.0))
        toolbar.addWidget(self.rewind_btn)

        self.play_pause_btn = QPushButton(tr("Play"))
        self.play_pause_btn.setObjectName("playButton")
        self.play_pause_btn.setToolTip(tr("Riproduce l'ensemble, o riprende dal punto di pausa (F5)"))
        self.play_pause_btn.setStyleSheet(
            f"QPushButton#playButton {{ font-weight: bold; color: #10151a; background: {ACCENT}; "
            f"border: 1px solid {ACCENT}; border-radius: 6px; padding: 5px 14px; }}")
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        toolbar.addWidget(self.play_pause_btn)
        self._toolbar_icons.append((self.play_pause_btn, "play", "#10151a"))

        stop_btn = self._tool_button("stop", tr("Interrompe la riproduzione (F6)"), self.stop)
        toolbar.addWidget(stop_btn)
        self.record_btn = self._tool_button(
            "record", tr("Registra nella traccia audio selezionata (Ctrl+R)"),
            lambda: self.record_into_audio_track(), color=BAD)
        toolbar.addWidget(self.record_btn)

        toolbar.addSeparator()
        self.loop_btn = QToolButton()
        self.loop_btn.setDefaultAction(self.loop_action)
        self.loop_btn.setToolTip(tr("Ripeti la sezione A-B (Ctrl+L). A e B si impostano dal menu Playback "
                                 "(Ctrl+[ e Ctrl+]) o dal righello."))
        self._toolbar_icons.append((self.loop_btn, "loop", None))
        toolbar.addWidget(self.loop_btn)

        # Nome storico: ora e' un pulsante a icona, con la stessa interfaccia
        # di una casella (isChecked/setChecked/toggled).
        self.metronome_checkbox = self._tool_button(
            "metronome", tr("Metronomo: click a tempo durante la riproduzione.\n"
            "Suono e volume in Opzioni → Metronomo."), None, checkable=True)
        self.metronome_checkbox.setChecked(False)
        self.metronome_checkbox.toggled.connect(self._on_metronome_toggled)
        toolbar.addWidget(self.metronome_checkbox)

        toolbar.addSeparator()

        # --- Brano: tempo, metrica, tonalita' ------------------------------
        song_box = QFrame()
        song_box.setObjectName("songBox")
        song_box.setStyleSheet("QFrame#songBox { border: 1px solid palette(mid); border-radius: 6px; }")
        song_layout = QHBoxLayout(song_box)
        song_layout.setContentsMargins(8, 2, 8, 2)
        song_layout.setSpacing(12)

        self.tempo_spin = QSpinBox()
        self.tempo_spin.setRange(20, 300)
        self.tempo_spin.setValue(self.project.tempo_bpm)
        self.tempo_spin.setSuffix(" BPM")
        self.tempo_spin.setToolTip(tr("Tempo del progetto in battiti al minuto."))
        self.tempo_spin.valueChanged.connect(self._on_tempo_changed)

        self.metrica_combo = QComboBox()
        self.metrica_combo.setEditable(True)
        self.metrica_combo.addItems(["2/4", "3/4", "4/4", "5/4", "6/8", "7/8", "9/8", "12/8"])
        self.metrica_combo.setCurrentText(self.project.time_sig)
        self.metrica_combo.setFixedWidth(70)
        self.metrica_combo.setToolTip(
            tr("Metrica (indicazione di tempo) del progetto, es. 4/4, 3/4, 6/8.\n"
            "Durante la riproduzione mostra la metrica in vigore in quel punto, "
            "se il brano contiene cambi di metrica.")
        )
        self.metrica_combo.currentTextChanged.connect(self._on_metrica_changed)

        self.key_combo = QComboBox()
        self.key_combo.setEditable(True)
        self.key_combo.addItems([
            "", "C", "G", "D", "A", "E", "B", "F#", "Db", "Ab", "Eb", "Bb", "F",
            "Am", "Em", "Bm", "F#m", "C#m", "G#m", "Ebm", "Bbm", "Fm", "Cm", "Gm", "Dm",
        ])
        self.key_combo.setCurrentText(self.project.key)
        self.key_combo.setFixedWidth(70)
        self.key_combo.setToolTip(
            tr("Tonalita' del brano, es. C, Am, G, Em... (vuota = non impostata).\n"
            "Importando un file MIDI viene riconosciuta e impostata automaticamente, se presente.\n"
            "In 'Suona con la tastiera' puo' essere usata per limitare i tasti alle sole note della scala.")
        )
        self.key_combo.currentTextChanged.connect(self._on_key_changed)

        self.pickup_spin = QDoubleSpinBox()
        self.pickup_spin.setRange(0.0, 16.0)
        self.pickup_spin.setSingleStep(0.5)
        self.pickup_spin.setDecimals(2)
        self.pickup_spin.setSpecialValueText(tr("no"))
        self.pickup_spin.setValue(self.project.pickup)
        self.pickup_spin.setFixedWidth(70)
        self.pickup_spin.setToolTip(
            tr("Battuta in levare, in quarti (0 = nessuna): la battuta 1 e' la prima intera "
               "e comincia dopo il levare. Conta per i controlli di battuta '|', le ancore bar=N, "
               "i cambi di tempo e di metrica per battuta, il metronomo e la partitura.")
        )
        self.pickup_spin.valueChanged.connect(self._on_pickup_changed)

        for caption, widget in ((tr("Tempo"), self.tempo_spin), (tr("Metrica"), self.metrica_combo),
                                (tr("Levare"), self.pickup_spin), (tr("Tonalita'"), self.key_combo)):
            column = QVBoxLayout()
            column.setSpacing(0)
            label = QLabel(caption.upper())
            label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 9px; letter-spacing: 1px;")
            column.addWidget(label)
            column.addWidget(widget)
            song_layout.addLayout(column)
        toolbar.addWidget(song_box)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)

        # --- Vista: Struttura / Testo ------------------------------------
        self.view_structure_btn = QToolButton()
        self.view_structure_btn.setText(tr("Struttura"))
        self.view_structure_btn.setToolTip(tr("Vista Struttura brano: tutte le tracce a box sullo stesso "
                                           "asse del tempo (Ctrl+Shift+B)"))
        self.view_text_btn = QToolButton()
        self.view_text_btn.setText(tr("Testo"))
        self.view_text_btn.setToolTip(tr("Vista Testo: la notazione della traccia selezionata (Ctrl+Shift+B)"))
        self._view_group = QButtonGroup(self)
        self._view_group.setExclusive(True)
        for b in (self.view_structure_btn, self.view_text_btn):
            b.setCheckable(True)
            b.setObjectName("viewToggle")
            self._view_group.addButton(b)
            toolbar.addWidget(b)
        self.view_structure_btn.clicked.connect(lambda: self.arrangement_action.setChecked(True))
        self.view_text_btn.clicked.connect(lambda: self.arrangement_action.setChecked(False))
        self.view_text_btn.setChecked(True)

        toolbar.addSeparator()
        toolbar.addWidget(QLabel(" Master "))
        # Catena di effetti sul master (mix finale): apre il pannello Effetti.
        self.master_fx_btn = QPushButton("FX")
        self.master_fx_btn.setMinimumWidth(52)
        self.master_fx_btn.setAccessibleName(tr("Effetti sul master"))
        self.master_fx_btn.clicked.connect(lambda: self.effects_panel.open_master())
        toolbar.addWidget(self.master_fx_btn)
        self.master_vol_slider = QSlider(Qt.Horizontal)
        self.master_vol_slider.setRange(0, 200)
        self.master_vol_slider.setValue(self.project.master_volume)
        self.master_vol_slider.setFixedWidth(100)
        self.master_vol_slider.setToolTip(
            tr("Volume master: scala il volume di tutte le tracce insieme, "
            "in aggiunta al volume di ciascuna (100% = guadagno originale).")
        )
        self.master_vol_slider.valueChanged.connect(self._on_master_volume_changed)
        toolbar.addWidget(self.master_vol_slider)
        self.master_vol_value_label = QLabel(f"{self.project.master_volume}%")
        self.master_vol_value_label.setFixedWidth(38)
        toolbar.addWidget(self.master_vol_value_label)

        # --- Avanzamento: riga propria, a tutta larghezza -----------------
        self.addToolBarBreak()
        progress_bar = QToolBar("Avanzamento")
        progress_bar.setMovable(False)
        progress_bar.setObjectName("progressToolbar")
        self.addToolBar(progress_bar)
        self.playback_progress = QProgressBar()
        self.playback_progress.setRange(0, 100)
        self.playback_progress.setValue(0)
        self.playback_progress.setMinimumWidth(200)
        self.playback_progress.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.playback_progress.setTextVisible(True)
        self.playback_progress.setFormat("00:00 / 00:00")
        self.playback_progress.setToolTip(tr("Avanzamento della riproduzione: clicca per saltare in quel punto."))
        self.playback_progress.installEventFilter(self)
        progress_bar.addWidget(self.playback_progress)

        self._refresh_toolbar_icons()

    def _tool_button(self, icon_name, tooltip, slot, color=None, checkable=False):
        """Pulsante a icona della barra dei comandi (vedi gui.icons)."""
        button = QToolButton()
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip.split("\n")[0].split(" (")[0])
        button.setCheckable(checkable)
        button.setAutoRaise(True)
        if slot is not None:
            button.clicked.connect(slot)
        self._toolbar_icons.append((button, icon_name, color))
        return button

    def _refresh_toolbar_icons(self):
        """Ridisegna le icone nel colore del tema attivo (vedi _apply_theme)."""
        text_color = "#333333" if get_active_theme() == "light" else "#e0e0e0"
        for button, name, color in self._toolbar_icons:
            if button is self.play_pause_btn:
                name = "pause" if self.play_pause_btn.text() == "Pausa" else "play"
            ic = icon(name, color or text_color)
            # Pulsanti legati a un'azione checkable (loop): a ogni toggle
            # QToolButton ricopia l'icona dall'azione, e se questa ne e'
            # priva mostra il testo dell'azione al posto dell'icona.
            action = button.defaultAction() if isinstance(button, QToolButton) else None
            if action is not None:
                action.setIcon(ic)
            button.setIcon(ic)

    def _apply_theme(self, name: str):
        app_settings.set_theme(name)
        set_active_theme(name)
        QApplication.instance().setPalette(palette_for(name))
        QApplication.instance().setStyleSheet(stylesheet_for(name))
        # Le testate delle tracce si disegnano con un QSS per-istanza
        # indipendente dal foglio di stile globale (vedi
        # theme.track_card_colors): senza ridisegnarle esplicitamente qui
        # resterebbero nei colori del tema precedente, illeggibili se il
        # nuovo tema ha un contrasto testo/sfondo opposto. (Quelle della
        # vista Struttura le ricrea arrangement_view.refresh() piu' sotto.)
        for header in self.track_headers.values():
            header.sync_from_track()
        refresh_add_track_icon(self.mixer_add_track_btn)
        self.effects_panel.theme_changed()
        # I colori dell'evidenziazione sintattica (es. [ ... ] in giallo/ambra,
        # vedi highlighter.py) dipendono dal tema attivo ma i QTextCharFormat
        # vengono creati solo alla costruzione del NotationHighlighter: un
        # semplice rehighlight() riuserebbe gli stessi oggetti e i colori del
        # tema precedente, quindi va rigenerata anche la palette.
        self.highlighter.update_theme()
        # Il canvas a box ha uno sfondo esplicito (vedi ArrangementView.refresh).
        self.arrangement_view.refresh()
        self._refresh_toolbar_icons()

    def _view_action(self, label, slot, shortcuts, tooltip=None):
        """Azione le cui scorciatoie valgono solo con la vista Struttura
        brano attiva (e il fuoco dentro di essa)."""
        act = QAction(label, self)
        act.setShortcuts([QKeySequence(k) for k in shortcuts])
        act.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        act.triggered.connect(lambda _checked=False: slot())
        if tooltip:
            act.setToolTip(tooltip)
        self.arrangement_view.addAction(act)
        return act

    def open_command_palette(self, *_):
        from .command_palette import CommandPalette, collect_commands
        # Il menu "+ Aggiungi traccia" si costruisce al volo: se ne tiene una
        # copia viva finche' la voce scelta non e' stata eseguita.
        if not hasattr(self, "_palette_add_menu"):
            self._palette_add_menu = QMenu(self)
        self.populate_add_track_menu(self._palette_add_menu)
        commands = [c for c in collect_commands(self.menuBar(), [(tr("+ Aggiungi traccia"), self._palette_add_menu)])
                    if c.action is not self.command_palette_action]
        self._command_palette = CommandPalette(self, commands)
        self._command_palette.exec()

    def _toggle_arrangement_view(self, checked):
        self.center_stack.setCurrentIndex(1 if checked else 0)
        (self.view_structure_btn if checked else self.view_text_btn).setChecked(True)
        self.shortcuts_hint.setVisible(checked)
        # Colonna delle tracce solo nella vista Testo: nella Struttura le
        # stesse testate stanno gia' a sinistra delle righe.
        self.mixer_panel.setVisible(not checked)
        if checked:
            self.arrangement_view.refresh()
        else:
            # L'anteprima di un box usa un motore di riproduzione dedicato,
            # separato dal trasporto principale: uscendo dalla vista va
            # fermata esplicitamente, altrimenti resterebbe a suonare in
            # sottofondo senza alcun controllo piu' raggiungibile.
            self.arrangement_view._preview_playback.stop()

    def refresh_master_fx_button(self):
        """Pulsante FX accanto al Master: acceso con la catena del master
        attiva, con il numero di effetti accesi."""
        from core.effects import active_effects
        from .effects_panel import master_fx_summary
        count = len(active_effects(self.project.master_effects))
        self.master_fx_btn.setText(f"FX {count}" if count else "FX")
        self.master_fx_btn.setToolTip(master_fx_summary(self.project))
        # Padding ridotto: quello globale dei pulsanti non lascia spazio a "FX 3".
        self.master_fx_btn.setStyleSheet(
            "QPushButton { padding: 3px 6px; "
            + (f"background-color: {ACCENT_DIM}; color: white; border-color: {ACCENT}; " if count else "")
            + "}")

    def _mark_dirty(self, *_args, merge_key=None):
        """Segna il progetto come modificato dall'ultimo salvataggio/
        caricamento: connesso direttamente a molti segnali Qt (accetta e
        ignora qualunque argomento passato, es. valueChanged/toggled), oltre
        che chiamato a mano ovunque il codice modifichi self.project senza
        passare da uno di quei segnali. Letto da closeEvent (vedi
        gui.main_window_project) per chiedere conferma prima di uscire con
        modifiche non salvate.

        E' anche il punto in cui ogni modifica entra nella cronologia di
        Annulla/Ripeti (core.history): merge_key raggruppa in un solo passo
        le modifiche a raffica dello stesso tipo (digitazione in una
        traccia, trascinamento di uno slider)."""
        self._dirty = True
        self._autosave_generation += 1
        if not self._restoring_history:
            self.history.record(self.project, self.current_track_name, merge_key)
            self._update_undo_actions()

    def _choose_language(self, code):
        """Opzioni -> Lingua: la scelta vale dal prossimo avvio (i testi
        si traducono quando le finestre vengono create, vedi core.i18n)."""
        from core.i18n import LANGUAGES, current_language
        app_settings.set_language(code)
        if code == current_language():
            return
        answer = QMessageBox.question(
            self, tr("Lingua"),
            tr("La lingua dell'interfaccia sarà {language} dal prossimo avvio di SoundText.\n\n"
               "Riavviare SoundText adesso?", language=LANGUAGES[code]),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer == QMessageBox.Yes:
            self._restart_requested = True
            if not self.close():          # chiusura annullata (modifiche da salvare)
                self._restart_requested = False

    def show_plugin_dirs(self, *_):
        from .plugin_dialogs import PluginDirsDialog
        if PluginDirsDialog(self).exec() == QDialog.Accepted:
            from core import plugins
            plugins.forget_scan()
            self.statusBar().showMessage(tr("Cartelle dei plugin aggiornate: l'elenco si rifa' alla prossima scelta."),
                                         5000)

    def open_support_page(self, *_):
        """Apre nel browser la pagina per sostenere il progetto (SUPPORT_URL)."""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        from core.version import SUPPORT_URL
        if not QDesktopServices.openUrl(QUrl(SUPPORT_URL)):
            QMessageBox.information(self, tr("Sostieni SoundText"),
                                    tr("Puoi sostenere SoundText da questa pagina:\n{url}", url=SUPPORT_URL))

    def open_log_file(self, *_):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        from core.log import LOG_FILE
        if not os.path.exists(LOG_FILE):
            QMessageBox.information(self, tr("File di log"), tr("Nessun problema registrato finora.\n\n({LOG_FILE})", LOG_FILE=LOG_FILE))
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(LOG_FILE)):
            QMessageBox.information(self, tr("File di log"), tr("Il file di log si trova in:\n{LOG_FILE}", LOG_FILE=LOG_FILE))

    # ------------------------------------------------------------ annulla/ripeti

    def _update_undo_actions(self):
        if hasattr(self, "undo_action"):
            self.undo_action.setEnabled(self.history.can_undo())
            self.redo_action.setEnabled(self.history.can_redo())

    def undo(self, *_):
        state = self.history.undo()
        if state is not None:
            self._restore_history_state(state, tr("Modifica annullata."))

    def redo(self, *_):
        state = self.history.redo()
        if state is not None:
            self._restore_history_state(state, tr("Modifica ripetuta."))

    def _restore_history_state(self, state, message):
        project, track_name = state
        self._restoring_history = True
        try:
            self.project = project
            set_session_instruments(project.instruments)
            if track_name is not None and any(t.name == track_name for t in project.tracks):
                self.current_track_name = track_name
            self.arrangement_view.select_box(None, None)
            self._sync_tempo_metrica_fields()
            self._sync_master_volume_slider()
            self.refresh_mixer()
            if self.current_track_name in self.track_headers:
                self.select_track(self.current_track_name)
        finally:
            self._restoring_history = False
        self._dirty = True
        self._update_undo_actions()
        self.statusBar().showMessage(message, 3000)

    def _action(self, label, slot, shortcut=None, tooltip=None):
        act = QAction(label, self)
        act.triggered.connect(slot)
        if shortcut:
            act.setShortcut(QKeySequence(shortcut))
        if tooltip:
            act.setToolTip(tooltip)
            act.setStatusTip(tooltip)
        return act
