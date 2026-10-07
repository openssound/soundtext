"""
Dialoghi "Genera batteria", "Genera basso da accordi", "Genera
accompagnamento"/"Genera riff o melodia": generazione algoritmica (non
basata su IA, vedi core.rhythm_generate) di batteria, basso, accompagnamento
(strumenti polifonici) e riff/melodia (strumenti monofonici), istantanea e
senza dipendenze pesanti. L'anteprima e' sempre rigenerata dal vivo ad ogni
modifica dei controlli, modificabile a mano prima di confermare, come gli
altri dialoghi di importazione dell'app.

Metrica: si usa quella del progetto (Metrica iniziale). La batteria
propone solo gli stili scritti per quella metrica (vedi
core.rhythm_generate.drum_styles_for_meter) e lo segnala se non ce ne sono;
basso e accompagnamento ripetono il disegno su battute della durata giusta.
"""

import dataclasses
import random
from typing import Optional

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QSpinBox, QDialogButtonBox, QMessageBox, QCheckBox, QSlider, QWidget,
)
from PySide6.QtCore import Qt

from core.instruments import get_instrument
from core.key_detect import detect_key_of_text
from core.model import Project, copy_synth
from core.playback import PlaybackEngine

from core.rhythm_generate import (
    DRUM_STYLES, BASS_STYLES, COMPING_STYLES, RIFF_STYLES, PROGRESSION_STYLES, generate_drum_pattern,
    extract_chords_from_track, generate_bass_from_chords, generate_melodic_line,
    generate_chord_progression, parse_key, drum_styles_for_meter, meter_beats, INTENSITIES,
    Variability, splice_bars, MELODY_STYLES,
)
from core import user_styles
from core.notation import NotationError, validate_track_text
from .highlighter import NotationHighlighter
from .play_highlight import PlayHighlighter
from .selection_actions import handle_selection_context_menu
from .voicing_picker import NotationEditor
from core.i18n import tr

DRUM_STYLE_LABELS = [
    ("rock", "Rock"),
    ("funk", "Funk"),
    ("disco", tr("Four-on-the-floor (disco)")),
    ("reggae", tr("Reggae (one drop)")),
    ("punk", "Punk"),
    ("soul", tr("Soul (Motown)")),
    ("bossa", tr("Bossa nova")),
    ("rocknroll", "Rock'n'roll"),
    ("shuffle", tr("Shuffle (blues, terzine)")),
    ("swing", tr("Swing (jazz, terzine)")),
    ("waltz", tr("Valzer (3/4)")),
    ("jazz_waltz", tr("Valzer jazz (3/4, terzine)")),
    ("ballad_68", tr("Ballata (6/8)")),
    ("afro_68", tr("Afro-cubano (6/8)")),
    ("blues_128", tr("Slow blues (12/8)")),
    ("slow_rock_128", tr("Slow rock anni '50 (12/8)")),
    ("hiphop", tr("Hip-hop (boom bap)")),
    ("halftime", "Half-time"),
    ("metal", tr("Metal (doppia cassa)")),
    ("country", tr("Country (train beat)")),
    ("samba", "Samba"),
    ("cha_cha", "Cha-cha-cha"),
    ("march", tr("Marcia")),
    ("rock_54", tr("Rock in 5/4 (3+2)")),
    ("jazz_54", tr("Jazz in 5/4 (terzine)")),
    ("rock_78", tr("Rock in 7/8 (2+2+3)")),
    ("balkan_78", tr("Balcanico in 7/8 (3+2+2)")),
]
BASS_STYLE_LABELS = [
    ("root", tr("Fondamentale")),
    ("root_fifth", tr("Fondamentale/quinta")),
    ("walking", tr("Walking bass")),
    ("pedal", tr("Pedale (nota lunga)")),
    ("two_feel", tr("Due quarti (two-feel)")),
    ("octaves", tr("Ottave")),
    ("blues", tr("Blues 1-3-5-6")),
    ("eighths", tr("Ottavi (rock/pop/punk)")),
    ("reggae", "Reggae"),
    ("bossa", tr("Bossa nova")),
    ("shuffle", tr("Shuffle blues (terzine)")),
    ("waltz", tr("Valzer (1 del 3/4, oom-pah-pah)")),
]
COMPING_STYLE_LABELS = [
    ("block_chords", tr("Accordi battuti (comping)")),
    ("arpeggio_up", tr("Arpeggio ascendente")),
    ("broken_chord", tr("Accordo spezzato (Alberti)")),
    ("sustained", tr("Accordo sostenuto")),
    ("montuno", tr("Montuno (latin)")),
    ("skank_chords", tr("Skank reggae (in levare)")),
    ("quarter_chords", tr("Accordi su ogni quarto")),
    ("bossa_comp", tr("Bossa nova")),
    ("funk_stab", tr("Stop-time funk")),
    ("waltz_comp", tr("Valzer (accordi sul 2 e sul 3)")),
    ("arpeggio_68", tr("Arpeggio in 6/8")),
]
RIFF_STYLE_LABELS = [
    ("riff_short", tr("Riff breve")),
    ("call_response", tr("Botta e risposta")),
    ("guide_tones", tr("Note guida (3ª/7ª)")),
    ("scale_run", tr("Passaggio scalare")),
    ("blues_lick", tr("Lick blues (terzine)")),
    ("arpeggio_updown", tr("Arpeggio su e giù")),
    ("reggae_skank", tr("Skank reggae (in levare)")),
    ("pedal_riff", tr("Nota ribattuta (drone)")),
    ("held_note", tr("Nota sostenuta")),
    ("melody_aaba", tr("Melodia a frasi (A A' B A)")),
    ("melody_period", tr("Melodia domanda e risposta (A A')")),
    ("melody_ballad", tr("Melodia lenta (ballad, A A' B A)")),
    ("melody_lively", tr("Melodia mossa (A A' B A)")),
]
PROGRESSION_STYLE_LABELS = [
    ("pop", tr("Pop (I-V-vi-IV)")),
    ("doo_wop", tr("Anni '50 / doo-wop (I-vi-IV-V)")),
    ("rock", tr("Rock (I-IV-I-V)")),
    ("canon", tr("Canone di Pachelbel")),
    ("blues_12", tr("Blues 12 battute")),
    ("jazz_251", tr("Jazz II-V-I")),
    ("turnaround", tr("Turnaround jazz (I-vi-ii-V)")),
    ("minor_pop", tr("Pop minore (i-VI-III-VII)")),
    ("andalusian", tr("Cadenza andalusa (i-VII-VI-V)")),
    ("minor_rock", tr("Rock minore (i-VII-VI-VII)")),
    ("minor_cadence", tr("Cadenza minore (i-iv-i-V7)")),
    ("minor_251", tr("Jazz II-V-I minore")),
    ("minor_blues_12", tr("Blues minore 12 battute")),
    ("three_chord", tr("Tre accordi (I-IV-V-I)")),
    ("ballad", tr("Ballata (I-iii-IV-V)")),
    ("royal_road", tr("J-pop / royal road (IV-V-iii-vi-ii-V-I)")),
    ("mixolydian", tr("Rock misolidio (I-bVII-IV-I)")),
    ("gospel", tr("Gospel (I-I7-IV-iv)")),
    ("circle", tr("Circolo delle quinte (maggiore)")),
    ("rhythm_changes", tr("Rhythm changes (jazz, due accordi per battuta)")),
    ("jazz_blues", tr("Blues jazz 12 battute")),
    ("minor_three", tr("Minore semplice (i-iv-v-i)")),
    ("minor_epic", tr("Minore epico (i-VI-VII-i)")),
    ("dorian_vamp", tr("Vamp dorico (i7-IV7)")),
    ("line_cliche", tr("Line cliché (i - i maj7 - i7 - i6)")),
    ("minor_circle", tr("Circolo delle quinte (minore)")),
    ("phrygian", tr("Frigio (i-bII)")),
]
def user_style_items(kind: str, meter: Optional[str] = None) -> list:
    """[(chiave, etichetta)] degli stili personali del tipo dato (vedi
    core.user_styles), solo quelli della metrica 'meter' se data."""
    items = []
    styles = user_styles.load_user_styles()[kind]
    for name in user_styles.user_style_names(kind):
        if meter is not None and styles[name].get("meter", "4/4") != meter.replace(" ", ""):
            continue
        items.append((user_styles.style_key(name), f"★ {name}"))
    return items


# Preset della variabilita': (chiave, etichetta, (generale, ritmo, note, dinamica) in %).
VARIABILITY_PRESETS = [
    ("faithful", tr("Fedele"), (15, 60, 30, 100)),
    ("musician", tr("Musicista"), (35, 100, 100, 100)),
    ("creative", tr("Creativo"), (75, 100, 100, 100)),
]
ASPECT_LABELS = {
    "rhythm": (tr("Ritmo:"), tr("Giri e ritmi alternativi, fill, anticipi, note o colpi che saltano, "
                         "si allungano o si aggiungono.")),
    "notes": (tr("Note e armonia:"), tr("Varianti del disegno, note di passaggio, salti d'ottava, note "
                                 "fantasma della batteria; nel giro armonico colori e sostituzioni "
                                 "degli accordi.")),
    "dynamics": (tr("Dinamica:"), tr("Velocity diverse colpo per colpo e nota per nota, con gli accenti "
                              "sui tempi forti.")),
}

INTENSITY_LABELS = [
    ("light", tr("Leggera (strofa, intro)")),
    ("normal", tr("Normale")),
    ("full", tr("Piena (ritornello)")),
    ("build", tr("In crescendo")),
]
assert [v for v, _ in INTENSITY_LABELS] == list(INTENSITIES)
KEY_CHOICES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B",
               "Cm", "C#m", "Dm", "Ebm", "Em", "Fm", "F#m", "Gm", "G#m", "Am", "Bbm", "Bm"]
CHORD_DURATION_CHOICES = [(tr("Mezza battuta"), 0.5), (tr("1 battuta"), 1.0), (tr("2 battute"), 2.0)]
assert {v for v, _ in DRUM_STYLE_LABELS} == set(DRUM_STYLES)
assert {v for v, _ in PROGRESSION_STYLE_LABELS} == set(PROGRESSION_STYLES)
assert {v for v, _ in BASS_STYLE_LABELS} == set(BASS_STYLES)
assert {v for v, _ in COMPING_STYLE_LABELS} == set(COMPING_STYLES)
assert {v for v, _ in RIFF_STYLE_LABELS} == set(RIFF_STYLES)


def project_bar_beats(project) -> float:
    """Durata in beat di una battuta nella metrica iniziale del progetto (4
    se la metrica non e' leggibile)."""
    try:
        return meter_beats(project.time_sig)
    except ValueError:
        return 4.0


class _GeneratedTrackDialogBase(QDialog):
    """Comune a DrumGenerateDialog/BassGenerateDialog: riga di controlli (a
    cura della sottoclasse, vedi _build_controls) + anteprima con evidenziazione
    sintattica, rigenerata ad ogni modifica, e Ok/Annulla."""

    # Aspetti della variabilita' regolabili nei Dettagli (vedi core.rhythm_generate.Variability).
    VARIABILITY_ASPECTS = ("rhythm", "notes", "dynamics")

    def __init__(self, parent, project, instrument_name, context_label, title, track_name=None):
        super().__init__(parent)
        self.project = project
        self.bar_beats = project_bar_beats(project)
        # Traccia di destinazione (se nota): il suo contenuto attuale non si
        # ascolta nell'anteprima insieme alle altre tracce, per non suonarlo
        # due volte (il testo generato la affianca o la sostituisce).
        self.track_name = track_name
        self._playback = PlaybackEngine()
        self.instrument_name = instrument_name
        self.context_label = context_label
        self.setWindowTitle(title)
        self.resize(640, 480)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            tr("Destinazione: <b>{context_label}</b> (strumento: {instrument_name})", context_label=context_label, instrument_name=instrument_name)
        ))

        controls_row = QHBoxLayout()
        self._build_controls(controls_row)
        controls_row.addStretch(1)
        layout.addLayout(controls_row)
        # Seconda riga: struttura della parte (intensita', fill, finale).
        options_row = QHBoxLayout()
        self._build_options(options_row)
        options_row.addStretch(1)
        layout.addLayout(options_row)

        # Variabilita': 0 = sempre lo stesso risultato per lo stesso stile; piu'
        # in alto il generatore aggiunge variazioni (vedi core.rhythm_generate).
        # Il seme e' fisso finche' non si preme "Nuova variazione": cambiare
        # stile o parametri non fa "saltare" la variazione, e a parita' di
        # controlli il testo e' riproducibile.
        self._seed = random.randrange(2 ** 31)
        # Battute rigenerate a parte: [(prima, ultima, seme)], applicate in
        # ordine sopra il testo generato col seme principale (vedi _compose_text).
        self._overrides = []
        variability_row = QHBoxLayout()
        variability_row.addWidget(QLabel(tr("Variabilità:")))
        self.variability_slider = QSlider(Qt.Horizontal)
        self.variability_slider.setRange(0, 100)
        self.variability_slider.setValue(35)
        self.variability_slider.setFixedWidth(180)
        self.variability_slider.setToolTip(
            tr("0% = a parita' di stile il risultato e' sempre identico. Piu' alta: note fantasma, "
            "cassa extra, giri e fill diversi (batteria); ritmi alternativi battuta per battuta, "
            "note di passaggio verso l'accordo successivo, anticipi sincopati, pause, note tenute "
            "e salti d'ottava (basso, accompagnamento, riff). Il disegno di base dello stile "
            "resta riconoscibile.")
        )
        variability_row.addWidget(self.variability_slider)
        self.variability_label = QLabel("35%")
        self.variability_label.setFixedWidth(38)
        variability_row.addWidget(self.variability_label)
        self.preset_combo = QComboBox()
        for key, label, _values in VARIABILITY_PRESETS:
            self.preset_combo.addItem(label, key)
        self.preset_combo.addItem(tr("Personalizzata"), "custom")
        self.preset_combo.setToolTip(
            tr("Fedele: vicino al disegno dello stile, poche note cambiate.\n"
            "Musicista: variazioni come quelle di un turnista (predefinito).\n"
            "Creativo: molte variazioni, per cercare idee."))
        variability_row.addWidget(self.preset_combo)
        self.reroll_btn = QPushButton(tr("🎲 Nuova variazione"))
        self.reroll_btn.setToolTip(tr("Estrae una nuova variazione con gli stessi controlli."))
        variability_row.addWidget(self.reroll_btn)
        self.details_btn = QPushButton(tr("Dettagli ▸"))
        self.details_btn.setCheckable(True)
        self.details_btn.setToolTip(tr("Quanto della variabilita' va al ritmo, alle note e alla dinamica."))
        variability_row.addWidget(self.details_btn)
        variability_row.addStretch(1)
        layout.addLayout(variability_row)

        # Dettagli: quota della variabilita' per aspetto (ritmo, note, dinamica).
        self.details_widget = QWidget()
        details_row = QHBoxLayout(self.details_widget)
        details_row.setContentsMargins(0, 0, 0, 0)
        self.aspect_sliders = {}
        self.aspect_labels = {}
        for aspect in self.VARIABILITY_ASPECTS:
            label, tooltip = ASPECT_LABELS[aspect]
            details_row.addWidget(QLabel(label))
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(100)
            slider.setFixedWidth(110)
            slider.setToolTip(tooltip)
            details_row.addWidget(slider)
            value_label = QLabel("100%")
            value_label.setFixedWidth(38)
            details_row.addWidget(value_label)
            self.aspect_sliders[aspect] = slider
            self.aspect_labels[aspect] = value_label
            slider.valueChanged.connect(self._on_aspect_changed)
        details_row.addStretch(1)
        self.details_widget.setVisible(False)
        layout.addWidget(self.details_widget)
        self.details_btn.toggled.connect(self._toggle_details)
        self.variability_slider.valueChanged.connect(self._on_variability_changed)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_chosen)
        self.reroll_btn.clicked.connect(self._reroll)
        self._sync_preset_combo()

        unsupported = self._unsupported_reason()
        if unsupported:
            layout.addWidget(QLabel(f"<b style='color:#e05555'>{unsupported}</b>"))

        layout.addWidget(QLabel(tr("Anteprima (modificabile prima di confermare):")))
        self.preview_edit = NotationEditor()
        self.preview_edit.setFont(QFont("Monospace", 10))
        self.preview_edit.on_selection_context_menu = self._on_preview_selection_context_menu
        self._highlighter = NotationHighlighter(self.preview_edit.document())
        layout.addWidget(self.preview_edit)
        # Durante l'ascolto evidenzia nell'anteprima cio' che sta suonando.
        self._play_highlight = PlayHighlighter(self.preview_edit, self, "_playback")

        bars_row = QHBoxLayout()
        bars_row.addWidget(QLabel(tr("Rigenera solo le battute da")))
        self.regen_from_spin = QSpinBox()
        self.regen_from_spin.setRange(1, 1)
        bars_row.addWidget(self.regen_from_spin)
        bars_row.addWidget(QLabel(tr("a")))  # "da battuta ... a ..."
        self.regen_to_spin = QSpinBox()
        self.regen_to_spin.setRange(1, 1)
        bars_row.addWidget(self.regen_to_spin)
        self.regen_bars_btn = QPushButton(tr("🎲 Rigenera queste"))
        self.regen_bars_btn.setToolTip(
            tr("Estrae una nuova variazione solo per queste battute e tiene le altre come sono. "
            "Le battute rigenerate restano anche cambiando gli altri controlli; "
            "'Nuova variazione' rigenera tutto."))
        self.regen_bars_btn.clicked.connect(self._regenerate_bars)
        bars_row.addWidget(self.regen_bars_btn)
        self.undo_bars_btn = QPushButton(tr("↺ Annulla ritocchi"))
        self.undo_bars_btn.setToolTip(tr("Toglie le battute rigenerate a parte: torna alla variazione intera."))
        self.undo_bars_btn.clicked.connect(self._clear_overrides)
        bars_row.addWidget(self.undo_bars_btn)
        bars_row.addStretch(1)
        layout.addLayout(bars_row)

        play_row = QHBoxLayout()
        self.play_btn = QPushButton(tr("▶ Ascolta"))
        self.play_btn.setToolTip(tr("Riproduce l'anteprima qui sopra (com'e' scritta ora) prima di confermare."))
        self.play_btn.clicked.connect(self._play_preview)
        play_row.addWidget(self.play_btn)
        self.stop_btn = QPushButton(tr("■ Stop"))
        self.stop_btn.clicked.connect(self._stop_preview)
        play_row.addWidget(self.stop_btn)
        self.with_others_check = QCheckBox(tr("Con le altre tracce"))
        self.with_others_check.setChecked(True)
        self.with_others_check.setToolTip(
            tr("Ascolta l'anteprima insieme alle altre tracce del progetto (senza Solo: "
            "restano rispettati i Mute), per sentire come si inserisce. "
            "Senza la spunta suona da sola.")
        )
        play_row.addWidget(self.with_others_check)
        play_row.addStretch(1)
        layout.addLayout(play_row)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self.button_box.button(QDialogButtonBox.Ok).setEnabled(not unsupported)
        if not unsupported:
            self._regenerate_preview()

    def _unsupported_reason(self) -> str:
        """Messaggio se il generatore non puo' lavorare nella metrica del
        progetto ('' se puo'): di default basso e accompagnamento vanno bene
        per qualunque metrica."""
        return ""

    def _build_controls(self, controls_row):
        raise NotImplementedError

    def _build_options(self, options_row):
        """Controlli della seconda riga: di default nessuno."""

    def _add_intensity_combo(self, options_row, tooltip: str):
        options_row.addWidget(QLabel(tr("Intensità:")))
        self.intensity_combo = QComboBox()
        for value, label in INTENSITY_LABELS:
            self.intensity_combo.addItem(label, value)
        self.intensity_combo.setCurrentIndex(1)
        self.intensity_combo.setToolTip(tooltip)
        self.intensity_combo.currentIndexChanged.connect(self._regenerate_preview)
        options_row.addWidget(self.intensity_combo)

    def _intensity(self) -> str:
        combo = getattr(self, "intensity_combo", None)
        return combo.currentData() if combo is not None else "normal"

    def _generate_text(self, seed=None) -> str:
        """Il testo generato con i controlli attuali e il seme dato (None =
        il seme principale del dialogo)."""
        raise NotImplementedError

    def _variability(self) -> Variability:
        """Variabilita' per aspetto: quella generale per la quota di ciascuno."""
        slider = getattr(self, "variability_slider", None)
        main = (slider.value() / 100.0) if slider is not None else 0.0
        shares = {a: s.value() / 100.0 for a, s in getattr(self, "aspect_sliders", {}).items()}
        return Variability(*(main * shares.get(a, 1.0) for a in ("rhythm", "notes", "dynamics")))

    def _variation_kwargs(self, seed=None) -> dict:
        return {"variability": self._variability(),
                "seed": seed if seed is not None else getattr(self, "_seed", None)}

    def _on_variability_changed(self, value):
        self.variability_label.setText(f"{value}%")
        self._sync_preset_combo()
        self._regenerate_preview()

    def _on_aspect_changed(self):
        for aspect, slider in self.aspect_sliders.items():
            self.aspect_labels[aspect].setText(f"{slider.value()}%")
        self._sync_preset_combo()
        self._regenerate_preview()

    def _toggle_details(self, shown: bool):
        self.details_widget.setVisible(shown)
        self.details_btn.setText(tr("Dettagli ▾") if shown else tr("Dettagli ▸"))

    def _current_values(self) -> tuple:
        shares = tuple(self.aspect_sliders[a].value() if a in self.aspect_sliders else 100
                       for a in ("rhythm", "notes", "dynamics"))
        return (self.variability_slider.value(),) + shares

    def _sync_preset_combo(self):
        """Il preset che corrisponde ai cursori, o 'Personalizzata'."""
        if not hasattr(self, "preset_combo"):
            return
        values = self._current_values()
        key = next((k for k, _label, v in VARIABILITY_PRESETS if self._preset_values(v) == values), "custom")
        self.preset_combo.blockSignals(True)
        self.preset_combo.setCurrentIndex(self.preset_combo.findData(key))
        self.preset_combo.blockSignals(False)

    def _preset_values(self, values: tuple) -> tuple:
        """I valori di un preset visti da questo dialogo: gli aspetti che non
        ha (il giro armonico ha solo le note) restano al 100%."""
        main, rhythm, notes, dynamics = values
        shares = dict(zip(("rhythm", "notes", "dynamics"), (rhythm, notes, dynamics)))
        return (main,) + tuple(shares[a] if a in self.VARIABILITY_ASPECTS else 100
                               for a in ("rhythm", "notes", "dynamics"))

    def _on_preset_chosen(self):
        key = self.preset_combo.currentData()
        preset = next((v for k, _label, v in VARIABILITY_PRESETS if k == key), None)
        if preset is None:
            return
        main, *shares = self._preset_values(preset)
        widgets = [self.variability_slider] + list(self.aspect_sliders.values())
        for w in widgets:
            w.blockSignals(True)
        self.variability_slider.setValue(main)
        self.variability_label.setText(f"{main}%")
        for aspect, value in zip(("rhythm", "notes", "dynamics"), shares):
            if aspect in self.aspect_sliders:
                self.aspect_sliders[aspect].setValue(value)
                self.aspect_labels[aspect].setText(f"{value}%")
        for w in widgets:
            w.blockSignals(False)
        self._regenerate_preview()

    def _reroll(self):
        self._seed = random.randrange(2 ** 31)
        self._overrides = []
        self._regenerate_preview()

    def _compose_text(self) -> str:
        """Il testo col seme principale, con sopra le battute rigenerate a
        parte (vedi core.rhythm_generate.splice_bars)."""
        text = self._generate_text()
        for first, last, seed in self._overrides:
            text = splice_bars(text, self._generate_text(seed=seed), first, last, self.bar_beats)
        return text

    def _regenerate_bars(self):
        first, last = self.regen_from_spin.value(), self.regen_to_spin.value()
        if last < first:
            first, last = last, first
        self._overrides.append((first, last, random.randrange(2 ** 31)))
        self._regenerate_preview()

    def _clear_overrides(self):
        self._overrides = []
        self._regenerate_preview()

    def _update_bar_spins(self, text: str):
        """Battute selezionabili per 'Rigenera solo le battute': quelle del testo."""
        if not hasattr(self, "regen_from_spin"):
            return
        try:
            from core.notation import parse_track_text
            events = parse_track_text(text, self.project.patterns)
            total = max((e.start + e.duration for e in events), default=0.0)
        except (NotationError, ValueError):
            total = 0.0
        bars = max(1, int(-(-round(total, 6) // self.bar_beats)))
        for spin in (self.regen_from_spin, self.regen_to_spin):
            spin.blockSignals(True)
            spin.setRange(1, bars)
            spin.blockSignals(False)
        can = self._variability().any()
        self.regen_bars_btn.setEnabled(can and bool(text))
        self.undo_bars_btn.setEnabled(bool(self._overrides))

    def _build_preview_project(self, text: str) -> Project:
        """Progetto di sola riproduzione: la traccia generata (col testo
        dell'anteprima, anche se modificato a mano) e, con la spunta, una
        copia delle altre tracce del progetto (senza la traccia di
        destinazione e senza Solo, che silenzierebbe l'anteprima)."""
        src = self.project
        preview = Project(
            name="preview", tempo_bpm=src.tempo_bpm, time_sig=src.time_sig, key=src.key,
            patterns=src.patterns, tempo_changes=list(src.tempo_changes),
            metrica_changes=list(src.metrica_changes), master_volume=src.master_volume,
        )
        if self.with_others_check.isChecked():
            for track in src.tracks:
                if track.name != self.track_name:
                    preview.tracks.append(dataclasses.replace(track, solo=False))
        copy_synth(preview.add_track(tr("Anteprima generata"), self.instrument_name, text),
                   src.find_track(self.track_name))
        return preview

    def _play_preview(self):
        text = self.preview_edit.toPlainText().strip()
        if not text:
            QMessageBox.information(self, tr("Niente da ascoltare"), tr("L'anteprima e' vuota."))
            return
        preview = self._build_preview_project(text)
        track = preview.tracks[-1]
        ok, msg = validate_track_text(track.text, preview.patterns,
                                       default_octave=track.instrument.default_octave)
        if not ok:
            QMessageBox.critical(self, tr("Errore di sintassi"), tr("Impossibile riprodurre:\n{msg}", msg=msg))
            return
        self._play_highlight.play(preview, preview.patterns, track.instrument.default_octave)

    def _stop_preview(self):
        self._play_highlight.stop()

    def _on_preview_selection_context_menu(self, sel_start: int, sel_end: int, global_pos) -> bool:
        """Tasto destro su una selezione dell'anteprima: ▶ Play la ascolta."""
        return handle_selection_context_menu(
            self.preview_edit, self.preview_edit.toPlainText(), sel_start, sel_end,
            self.project.patterns, get_instrument(self.instrument_name), self.instrument_name,
            self.project.tempo_bpm, self._playback, global_pos,
            play_only=True, before_play=self._play_highlight.stop,
            synth_track=self.project.find_track(self.track_name),
        )

    def done(self, result):
        # accept(), reject() e la chiusura della finestra passano tutti da qui:
        # l'anteprima non deve continuare a suonare dopo Ok/Annulla.
        self._play_highlight.stop()
        super().done(result)

    def _regenerate_preview(self):
        if not hasattr(self, "preview_edit"):
            return   # costruzione del dialogo non ancora finita
        try:
            text = self._compose_text()
        except ValueError as e:
            self.preview_edit.setPlainText("")
            self.status_label.setText(f"✗ {e}")
            self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
            self._update_bar_spins("")
            return
        self.preview_edit.setPlainText(text)
        self._update_bar_spins(text)
        self.status_label.setText("")
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(not self._unsupported_reason())

    def accept(self):
        text = self.preview_edit.toPlainText()
        ok, msg = validate_track_text(text, self.project.patterns)
        if not ok:
            QMessageBox.critical(self, tr("Errore di sintassi"), tr("Correggi l'anteprima prima di confermare:\n{msg}", msg=msg))
            return
        self._result_text = text
        super().accept()

    def result_text(self):
        return getattr(self, "_result_text", None)


class DrumGenerateDialog(_GeneratedTrackDialogBase):
    def __init__(self, parent, project, instrument_name, context_label, default_bars=8, track_name=None):
        # Preimpostato (dal chiamante, vedi gui.main_window_mixer) al numero
        # di battute che copre l'estensione delle altre tracce gia' scritte
        # nel progetto, cosi' la batteria generata le copre per intero di
        # default invece di fermarsi a meta' - resta comunque modificabile.
        self.default_bars = max(1, min(256, default_bars))
        super().__init__(parent, project, instrument_name, context_label, tr("Genera batteria"), track_name)

    def _unsupported_reason(self) -> str:
        if drum_styles_for_meter(self.project.time_sig) or user_style_items("drums", self.project.time_sig):
            return ""
        meters = sorted({spec.get("meter", "4/4") for spec in DRUM_STYLES.values()},
                        key=lambda m: (int(m.split("/")[1]), int(m.split("/")[0])))
        return (tr("Nessuno stile di batteria per la metrica del progetto ({time_sig}). Metriche disponibili: {0}.", ', '.join(meters), time_sig=self.project.time_sig))

    def _build_controls(self, controls_row):
        controls_row.addWidget(QLabel(tr("Stile:")))
        self.style_combo = QComboBox()
        allowed = set(drum_styles_for_meter(self.project.time_sig))
        for value, label in DRUM_STYLE_LABELS:
            if value in allowed:
                self.style_combo.addItem(label, value)
        for value, label in user_style_items("drums", self.project.time_sig):
            self.style_combo.addItem(label, value)
        self.style_combo.currentIndexChanged.connect(self._regenerate_preview)
        controls_row.addWidget(self.style_combo)

        controls_row.addSpacing(12)
        controls_row.addWidget(QLabel(tr("Battute:")))
        self.bars_spin = QSpinBox()
        self.bars_spin.setRange(1, 256)
        self.bars_spin.setValue(self.default_bars)
        self.bars_spin.valueChanged.connect(self._regenerate_preview)
        controls_row.addWidget(self.bars_spin)

        controls_row.addSpacing(12)
        controls_row.addWidget(QLabel(tr("Fill ogni N battute:")))
        self.fill_every_spin = QSpinBox()
        self.fill_every_spin.setRange(0, 64)
        self.fill_every_spin.setValue(4)
        self.fill_every_spin.setToolTip(
            tr("Ogni N battute inserisce un fill (con crash di rientro alla battuta successiva) "
            "invece di ripetere il giro base identico. 0 = nessun fill.")
        )
        self.fill_every_spin.valueChanged.connect(self._regenerate_preview)
        controls_row.addWidget(self.fill_every_spin)

    def _build_options(self, options_row):
        self._add_intensity_combo(
            options_row,
            tr("Leggera: niente colpi di charleston in levare ne' note fantasma, suono piu' morbido.\n"
            "Piena: ride al posto del charleston, crash all'inizio di ogni frase, suono piu' forte.\n"
            "In crescendo: leggera, poi normale, poi piena lungo le battute."))
        options_row.addSpacing(12)
        self.phrase_fills_check = QCheckBox(tr("Fill a frasi"))
        self.phrase_fills_check.setChecked(True)
        self.phrase_fills_check.setToolTip(
            tr("Fill piccolo (solo l'ultimo beat) ogni N battute e fill completo ogni 2N, "
            "come fa un batterista alla fine delle frasi. Senza spunta: sempre fill completi."))
        self.phrase_fills_check.toggled.connect(self._regenerate_preview)
        options_row.addWidget(self.phrase_fills_check)
        self.ending_check = QCheckBox(tr("Finale sull'ultima battuta"))
        self.ending_check.setToolTip(tr("Chiude la parte con un colpo di piatto e cassa sul primo tempo "
                                     "dell'ultima battuta, poi silenzio."))
        self.ending_check.toggled.connect(self._regenerate_preview)
        options_row.addWidget(self.ending_check)

    def _generate_text(self, seed=None) -> str:
        style = self.style_combo.currentData()
        return generate_drum_pattern(style, bars=self.bars_spin.value(), fill_every=self.fill_every_spin.value(),
                                     intensity=self._intensity(),
                                     phrase_fills=self.phrase_fills_check.isChecked(),
                                     ending=self.ending_check.isChecked(),
                                     **self._variation_kwargs(seed))


class BassGenerateDialog(_GeneratedTrackDialogBase):
    """other_tracks: [(nome, testo), ...] - le tracce da cui si puo' leggere
    la sequenza di accordi da seguire (tutte tranne quella di destinazione)."""

    def __init__(self, parent, project, instrument_name, context_label, other_tracks,
                 min_total_beats=0.0, default_bars=None, track_name=None):
        self.other_tracks = other_tracks
        # Le battute sono un controllo esplicito del dialogo (vedi
        # _build_controls, come in DrumGenerateDialog): il chiamante puo'
        # preimpostarle direttamente (default_bars, es. per un nuovo box
        # nella vista Struttura brano) oppure indirettamente passando quante
        # battute servono a coprire le altre tracce gia' scritte nel
        # progetto (min_total_beats, vedi gui.main_window_mixer/
        # core.rhythm_generate.tracks_duration_beats) - resta comunque
        # modificabile a mano prima di confermare.
        if default_bars is None:
            default_bars = max(1, round(min_total_beats / project_bar_beats(project))) if min_total_beats > 0 else 4
        self.default_bars = max(1, min(256, default_bars))
        super().__init__(parent, project, instrument_name, context_label, tr("Genera basso da accordi"), track_name)

    def _build_controls(self, controls_row):
        controls_row.addWidget(QLabel(tr("Accordi da:")))
        self.source_combo = QComboBox()
        for name, _text in self.other_tracks:
            self.source_combo.addItem(name)
        self.source_combo.currentIndexChanged.connect(self._regenerate_preview)
        controls_row.addWidget(self.source_combo)

        controls_row.addSpacing(12)
        controls_row.addWidget(QLabel(tr("Stile:")))
        self.style_combo = QComboBox()
        for value, label in BASS_STYLE_LABELS + user_style_items("bass"):
            self.style_combo.addItem(label, value)
        self.style_combo.currentIndexChanged.connect(self._regenerate_preview)
        controls_row.addWidget(self.style_combo)

        controls_row.addSpacing(12)
        controls_row.addWidget(QLabel(tr("Ottava:")))
        self.octave_spin = QSpinBox()
        self.octave_spin.setRange(0, 6)
        self.octave_spin.setValue(2)
        self.octave_spin.valueChanged.connect(self._regenerate_preview)
        controls_row.addWidget(self.octave_spin)

        controls_row.addSpacing(12)
        controls_row.addWidget(QLabel(tr("Battute:")))
        self.bars_spin = QSpinBox()
        self.bars_spin.setRange(1, 256)
        self.bars_spin.setValue(self.default_bars)
        self.bars_spin.setToolTip(
            tr("La progressione di accordi scelta sopra viene ripetuta ciclicamente finche' "
            "non copre queste battute.")
        )
        self.bars_spin.valueChanged.connect(self._regenerate_preview)
        controls_row.addWidget(self.bars_spin)

        controls_row.addSpacing(12)
        controls_row.addWidget(QLabel(tr("Variazione ogni N accordi:")))
        self.variation_every_spin = QSpinBox()
        self.variation_every_spin.setRange(0, 64)
        self.variation_every_spin.setValue(4)
        self.variation_every_spin.setToolTip(
            tr("Ogni N accordi usa un trattamento leggermente diverso dello stesso accordo "
            "(salto d'ottava, nota diversa...) invece di ripetere identico il disegno. "
            "0 = nessuna variazione.")
        )
        self.variation_every_spin.valueChanged.connect(self._regenerate_preview)
        controls_row.addWidget(self.variation_every_spin)

    def _generate_text(self, seed=None) -> str:
        source_name, source_text = self.other_tracks[self.source_combo.currentIndex()]
        chords = extract_chords_from_track(source_text, self.project.patterns, midi_dir=None)
        if not chords:
            raise ValueError(
                tr("La traccia '{source_name}' non contiene accordi da seguire: servono accordi scritti come simbolo (es. Cmaj7) o blocchi [...] di almeno due note; note singole (melodie, arpeggi) non bastano.", source_name=source_name)
            )
        style = self.style_combo.currentData()
        return generate_bass_from_chords(
            chords, style, octave=self.octave_spin.value(),
            variation_every=self.variation_every_spin.value(),
            min_total_beats=self.bars_spin.value() * self.bar_beats, bar_beats=self.bar_beats,
            intensity=self._intensity(), **self._variation_kwargs(seed),
        )

    def _build_options(self, options_row):
        self._add_intensity_combo(
            options_row,
            tr("Leggera: restano le note sul 1 e sul 3 (piu' lunghe), per strofe e intro.\n"
            "Piena: accordi con l'ottava sopra, basso che sale d'ottava a fine accordo.\n"
            "In crescendo: leggera, poi normale, poi piena lungo il brano."))


class MelodyGenerateDialog(_GeneratedTrackDialogBase):
    """Genera un accompagnamento (strumenti polifonici, vedi
    core.rhythm_generate.COMPING_STYLES) o una melodia/riff (strumenti
    monofonici, RIFF_STYLES) che segue gli accordi di un'altra traccia -
    stessa struttura di BassGenerateDialog, con lo stile e il registro
    (range_low/range_high, dall'InstrumentProfile dello strumento di
    destinazione) che dipendono da 'polyphonic' invece di essere fissi come
    per il basso."""

    def __init__(self, parent, project, instrument_name, context_label, other_tracks,
                 polyphonic, default_octave, range_low, range_high,
                 min_total_beats=0.0, default_bars=None, track_name=None):
        self.other_tracks = other_tracks
        self.polyphonic = polyphonic
        self.default_octave = default_octave
        self.range_low = range_low
        self.range_high = range_high
        if default_bars is None:
            default_bars = max(1, round(min_total_beats / project_bar_beats(project))) if min_total_beats > 0 else 4
        self.default_bars = max(1, min(256, default_bars))
        title = tr("Genera accompagnamento") if polyphonic else tr("Genera riff/melodia")
        super().__init__(parent, project, instrument_name, context_label, title, track_name)

    def _build_controls(self, controls_row):
        controls_row.addWidget(QLabel(tr("Accordi da:")))
        self.source_combo = QComboBox()
        for name, _text in self.other_tracks:
            self.source_combo.addItem(name)
        self.source_combo.currentIndexChanged.connect(self._regenerate_preview)
        controls_row.addWidget(self.source_combo)

        controls_row.addSpacing(12)
        controls_row.addWidget(QLabel(tr("Stile:")))
        self.style_combo = QComboBox()
        labels = (COMPING_STYLE_LABELS + user_style_items("comping") if self.polyphonic
                  else RIFF_STYLE_LABELS + user_style_items("riff"))
        for value, label in labels:
            self.style_combo.addItem(label, value)
        self.style_combo.currentIndexChanged.connect(self._regenerate_preview)
        controls_row.addWidget(self.style_combo)

        controls_row.addSpacing(12)
        controls_row.addWidget(QLabel(tr("Ottava:")))
        self.octave_spin = QSpinBox()
        self.octave_spin.setRange(0, 8)
        self.octave_spin.setValue(self.default_octave)
        self.octave_spin.setToolTip(
            tr("Punto di partenza: le note fuori dall'estensione dello strumento vengono comunque "
            "riportate dentro spostandole di ottava.")
        )
        self.octave_spin.valueChanged.connect(self._regenerate_preview)
        controls_row.addWidget(self.octave_spin)

        controls_row.addSpacing(12)
        controls_row.addWidget(QLabel(tr("Battute:")))
        self.bars_spin = QSpinBox()
        self.bars_spin.setRange(1, 256)
        self.bars_spin.setValue(self.default_bars)
        self.bars_spin.setToolTip(
            tr("La progressione di accordi scelta sopra viene ripetuta ciclicamente finche' "
            "non copre queste battute.")
        )
        self.bars_spin.valueChanged.connect(self._regenerate_preview)
        controls_row.addWidget(self.bars_spin)

        controls_row.addSpacing(12)
        controls_row.addWidget(QLabel(tr("Variazione ogni N accordi:")))
        self.variation_every_spin = QSpinBox()
        self.variation_every_spin.setRange(0, 64)
        self.variation_every_spin.setValue(4)
        self.variation_every_spin.setToolTip(
            tr("Ogni N accordi usa un trattamento leggermente diverso dello stesso accordo "
            "invece di ripetere identico il disegno. 0 = nessuna variazione.")
        )
        self.variation_every_spin.valueChanged.connect(self._regenerate_preview)
        controls_row.addWidget(self.variation_every_spin)

    def _generate_text(self, seed=None) -> str:
        source_name, source_text = self.other_tracks[self.source_combo.currentIndex()]
        chords = extract_chords_from_track(source_text, self.project.patterns, midi_dir=None)
        if not chords:
            raise ValueError(
                tr("La traccia '{source_name}' non contiene accordi da seguire: servono accordi scritti come simbolo (es. Cmaj7) o blocchi [...] di almeno due note; note singole (melodie, arpeggi) non bastano.", source_name=source_name)
            )
        style = self.style_combo.currentData()
        is_melody = style in MELODY_STYLES
        self.variation_every_spin.setEnabled(not is_melody)   # le melodie a frasi hanno la loro forma
        return generate_melodic_line(
            chords, style, octave=self.octave_spin.value(),
            range_low=self.range_low, range_high=self.range_high, polyphonic=self.polyphonic,
            variation_every=self.variation_every_spin.value(),
            min_total_beats=self.bars_spin.value() * self.bar_beats, bar_beats=self.bar_beats,
            intensity=self._intensity(), voice_leading=self._voice_leading(),
            key=self._melody_key(source_text) if is_melody else None, meter=self.project.time_sig,
            **self._variation_kwargs(seed),
        )

    def _melody_key(self, source_text: str):
        """Tonalita' della melodia: quella del progetto, o quella riconosciuta
        dagli accordi della traccia sorgente (None: la stima il generatore)."""
        if (self.project.key or "").strip():
            return self.project.key
        try:
            return detect_key_of_text(source_text, self.project.patterns)
        except (NotationError, ValueError):
            return None

    def _voice_leading(self) -> bool:
        check = getattr(self, "voice_leading_check", None)
        return check is not None and check.isChecked()

    def _build_options(self, options_row):
        self._add_intensity_combo(
            options_row,
            tr("Leggera: restano le note sul 1 e sul 3 (piu' lunghe), per strofe e intro.\n"
            "Piena: accordi con l'ottava sopra, basso che sale d'ottava a fine accordo.\n"
            "In crescendo: leggera, poi normale, poi piena lungo il brano."))
        if self.polyphonic:
            options_row.addSpacing(12)
            self.voice_leading_check = QCheckBox(tr("Rivolti vicini"))
            self.voice_leading_check.setChecked(True)
            self.voice_leading_check.setToolTip(
                tr("Ogni accordo sceglie il rivolto piu' vicino al precedente (condotta delle voci), "
                "come farebbe un pianista, invece di stare sempre in posizione fondamentale "
                "e saltare da una posizione all'altra."))
            self.voice_leading_check.toggled.connect(self._regenerate_preview)
            options_row.addWidget(self.voice_leading_check)


def last_box_key(project, track) -> Optional[str]:
    """Tonalita' (formato di Project.key) dell'ultimo box della traccia, o
    del suo testo se non usa i box: quella da proporre per il giro armonico
    che gli verra' accodato. None se non c'e' niente da cui ricavarla."""
    text = max(track.clips, key=lambda c: c.start_beat).text if track.clips else track.text
    if not text.strip():
        return None
    try:
        return detect_key_of_text(text, project.patterns, track.instrument.default_octave)
    except (NotationError, ValueError):
        return None   # testo con errori di sintassi: si ripiega sulla tonalita' del progetto


class ChordProgressionDialog(_GeneratedTrackDialogBase):
    """Genera un giro armonico (simboli di accordo, vedi
    core.rhythm_generate.generate_chord_progression) per una traccia
    polifonica: il punto di partenza quando il brano non ha ancora accordi
    da far seguire a basso e accompagnamento. Gli stili proposti sono quelli
    del modo (maggiore/minore) della tonalita' scelta."""

    VARIABILITY_ASPECTS = ("notes",)   # nel giro armonico contano solo note e armonia

    def __init__(self, parent, project, instrument_name, context_label, default_bars=0, track_name=None,
                 default_key=None):
        """Propone la tonalita' del progetto se impostata, altrimenti
        default_key (es. quella del box dopo cui va il giro, vedi
        last_box_key), altrimenti Do maggiore."""
        self.default_bars = max(0, min(256, default_bars))
        tonic, mode, _flats = parse_key((project.key or "").strip() or default_key or "")
        self.default_key = next(k for k in KEY_CHOICES if parse_key(k)[:2] == (tonic, mode))
        super().__init__(parent, project, instrument_name, context_label, tr("Genera giro armonico"), track_name)
        self.variability_slider.setToolTip(
            tr("0% = gli accordi dello stile cosi' come sono. Piu' alta: accordi arricchiti "
            "(settime, none, sus), dominanti secondarie e II-V verso l'accordo successivo, "
            "sostituti di tritono, IV minore prima della tonica; con la cadenza finale, "
            "cadenze diverse (plagale, iv minore, bVII7...).")
        )

    def _build_controls(self, controls_row):
        controls_row.addWidget(QLabel(tr("Tonalità:")))
        self.key_combo = QComboBox()
        for key in KEY_CHOICES:
            self.key_combo.addItem(key, key)
        self.key_combo.setCurrentIndex(KEY_CHOICES.index(self.default_key))
        self.key_combo.currentIndexChanged.connect(self._on_key_changed)
        controls_row.addWidget(self.key_combo)

        controls_row.addSpacing(12)
        controls_row.addWidget(QLabel(tr("Stile:")))
        self.style_combo = QComboBox()
        self._fill_styles()
        self.style_combo.currentIndexChanged.connect(self._regenerate_preview)
        controls_row.addWidget(self.style_combo)

        controls_row.addSpacing(12)
        controls_row.addWidget(QLabel(tr("Durata di ogni accordo:")))
        self.chord_duration_combo = QComboBox()
        for label, value in CHORD_DURATION_CHOICES:
            self.chord_duration_combo.addItem(label, value)
        self.chord_duration_combo.setCurrentIndex(1)
        self.chord_duration_combo.setToolTip(
            tr("Moltiplica la durata prevista dallo stile (di solito una battuta per accordo; "
            "nel blues alcuni accordi durano di piu').")
        )
        self.chord_duration_combo.currentIndexChanged.connect(self._regenerate_preview)
        controls_row.addWidget(self.chord_duration_combo)

        controls_row.addSpacing(12)
        controls_row.addWidget(QLabel(tr("Battute:")))
        self.bars_spin = QSpinBox()
        self.bars_spin.setRange(0, 256)
        self.bars_spin.setSpecialValueText(tr("Giro intero"))
        self.bars_spin.setValue(self.default_bars)
        self.bars_spin.setToolTip(
            tr("Il giro viene ripetuto finche' non copre queste battute. "
            "'Giro intero' = il giro una volta sola.")
        )
        self.bars_spin.valueChanged.connect(self._regenerate_preview)
        controls_row.addWidget(self.bars_spin)

    def _fill_styles(self):
        """Riempie la combo degli stili con quelli del modo della tonalita'
        scelta, mantenendo lo stile corrente se e' ancora fra quelli."""
        mode = parse_key(self.key_combo.currentData())[1]
        current = self.style_combo.currentData()
        self.style_combo.blockSignals(True)
        self.style_combo.clear()
        for value, label in PROGRESSION_STYLE_LABELS:
            if PROGRESSION_STYLES[value]["mode"] == mode:
                self.style_combo.addItem(label, value)
        index = self.style_combo.findData(current)
        self.style_combo.setCurrentIndex(max(0, index))
        self.style_combo.blockSignals(False)

    def _on_key_changed(self):
        self._fill_styles()
        self._regenerate_preview()

    def _generate_text(self, seed=None) -> str:
        return generate_chord_progression(
            self.key_combo.currentData(), self.style_combo.currentData(),
            bars=self.bars_spin.value(), chord_bars=self.chord_duration_combo.currentData(),
            bar_beats=self.bar_beats, ending=self.ending_check.isChecked(), **self._variation_kwargs(seed),
        )

    def _build_options(self, options_row):
        self.ending_check = QCheckBox(tr("Cadenza finale"))
        self.ending_check.setToolTip(
            tr("Chiude il giro sulla tonica: l'ultima battuta diventa l'accordo di tonica, preceduto "
            "da un accordo di cadenza (V7; con la variabilita' anche plagale, iv minore, bVII7...). "
            "Senza spunta il giro resta aperto, pronto a ripetersi."))
        self.ending_check.toggled.connect(self._regenerate_preview)
        options_row.addWidget(self.ending_check)
