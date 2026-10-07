import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem, QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QListWidget, QLabel,
    QPushButton, QLineEdit, QSpinBox, QCheckBox, QComboBox, QMessageBox,
    QDialogButtonBox, QCompleter, QFileDialog, QFrame
)

from core import settings as app_settings
from core.instruments import (
    all_instruments, add_custom_instrument, remove_custom_instrument,
    is_custom_instrument, InstrumentProfile, DEFAULT_INSTRUMENTS,
    gm_instrument_catalog, gm_family_for_program, GM_FAMILY_DEFAULTS,
    GM_DRUM_KITS, sorted_instrument_names,
)
from core.i18n import tr

VOICING_STYLES = ["spread", "root_only", "root_fifth", "monophonic"]


class GMInstrumentPicker(QComboBox):
    """Tendina per scegliere uno strumento General MIDI per NOME (non per
    numero), raggruppata per famiglia, con ricerca digitando il nome.

    Ha due modalita' (vedi set_percussion_mode): quella normale elenca i 128
    suoni melodici GM raggruppati per famiglia; quella percussioni elenca
    invece i 9 drum kit General MIDI 2 (core.instruments.GM_DRUM_KITS), cosi'
    da poter scegliere il kit (Standard, Jazz, Room, ...) con la stessa
    ricerca/autocompletamento. L'ultima selezione fatta in ciascuna modalita'
    viene ricordata quando si torna indietro."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        self._percussion_mode = False
        self._last_melodic_program = None
        self._last_drum_program = None
        self._items = []  # (program, nome) del catalogo correntemente mostrato

        self._set_catalog(gm_instrument_catalog_grouped())
        self.setCurrentIndex(1)  # primo strumento reale (dopo l'intestazione famiglia)

    def _set_catalog(self, grouped):
        model = QStandardItemModel(self)
        self._items = []
        for family, names in grouped:
            if family:
                header = QStandardItem(f"— {tr(family)} —")
                header.setFlags(header.flags() & ~Qt.ItemIsSelectable & ~Qt.ItemIsEnabled)
                f = header.font()
                f.setItalic(True)
                header.setFont(f)
                model.appendRow(header)
            for program, name in names:
                item = QStandardItem(name)
                item.setData(program, Qt.UserRole)
                model.appendRow(item)
                self._items.append((program, name))

        self.setModel(model)

        completer = QCompleter([n for _, n in self._items], self)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        self.setCompleter(completer)
        completer.activated.connect(self._select_by_name)

    def set_percussion_mode(self, is_percussion: bool):
        """Passa dal catalogo GM melodico ai drum kit GM2 (o viceversa),
        ricordando l'ultima selezione fatta in ciascuna delle due modalita'."""
        if is_percussion == self._percussion_mode:
            return
        if self._percussion_mode:
            self._last_drum_program = self.selected_program()
        else:
            self._last_melodic_program = self.selected_program()
        self._percussion_mode = is_percussion
        if is_percussion:
            self._set_catalog(drum_kit_catalog_grouped())
            self._select_program(self._last_drum_program)
        else:
            self._set_catalog(gm_instrument_catalog_grouped())
            self._select_program(self._last_melodic_program)

    def _select_program(self, program):
        model = self.model()
        if program is not None:
            for row in range(model.rowCount()):
                item = model.item(row)
                if item is not None and item.data(Qt.UserRole) == program:
                    self.setCurrentIndex(row)
                    return
        self.setCurrentIndex(1 if model.rowCount() > 1 else 0)

    def _select_by_name(self, text):
        idx = self.findText(text, Qt.MatchExactly)
        if idx >= 0:
            self.setCurrentIndex(idx)

    def selected_program(self):
        idx = self.currentIndex()
        if idx < 0:
            idx = self.findText(self.currentText(), Qt.MatchExactly)
        item = self.model().item(idx)
        if item is None or item.data(Qt.UserRole) is None:
            return None
        return item.data(Qt.UserRole)

    def selected_name(self):
        program = self.selected_program()
        if program is None:
            return None
        for p, n in self._items:
            if p == program:
                return n
        return None


def gm_instrument_catalog_grouped():
    """[(famiglia, [(program, nome), ...]), ...] per i 128 suoni GM melodici."""
    from core.instruments import GM_FAMILIES
    return [(family, [(start + i, n) for i, n in enumerate(names)])
            for family, start, names in GM_FAMILIES]


def drum_kit_catalog_grouped():
    """[(famiglia, [(program, nome), ...])] per i 9 drum kit General MIDI 2."""
    from core.instruments import GM_DRUM_KITS
    return [(tr("Kit percussioni (GM2)"), sorted(GM_DRUM_KITS.items()))]


class NewInstrumentDialog(QDialog):
    """Form per creare un nuovo strumento personalizzato: lo strumento si
    sceglie per NOME dall'elenco General MIDI (ricercabile), non digitando
    un numero. I parametri tecnici vengono suggeriti automaticamente in
    base alla famiglia scelta e restano comunque modificabili."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Nuovo strumento"))
        self.resize(420, 0)
        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        layout.addRow(tr("Nome nel programma (una parola, senza spazi):"), self.name_edit)

        self.gm_picker = GMInstrumentPicker()
        self.gm_picker.currentIndexChanged.connect(self._on_gm_changed)
        layout.addRow(tr("Suono General MIDI:"), self.gm_picker)

        hint = QLabel(tr("Digita per cercare (es. \"sax\", \"organ\", \"synth\")"))
        hint.setStyleSheet("color: #888; font-size: 11px;")
        layout.addRow("", hint)

        self.percussion_check = QCheckBox(tr("Usa il canale percussioni (10) invece del suono scelto sopra"))
        self.percussion_check.toggled.connect(self._on_percussion_toggled)
        layout.addRow(self.percussion_check)

        layout.addRow(QLabel(tr("<b>Parametri avanzati</b> (precompilati, modificabili se serve):")))

        self.octave_spin = QSpinBox()
        self.octave_spin.setRange(0, 8)
        layout.addRow(tr("Ottava predefinita:"), self.octave_spin)

        self.range_low_spin = QSpinBox()
        self.range_low_spin.setRange(0, 127)
        layout.addRow(tr("Nota MIDI minima suonabile:"), self.range_low_spin)

        self.range_high_spin = QSpinBox()
        self.range_high_spin.setRange(0, 127)
        layout.addRow(tr("Nota MIDI massima suonabile:"), self.range_high_spin)

        self.voicing_combo = QComboBox()
        self.voicing_combo.addItems(VOICING_STYLES)
        layout.addRow(tr("Stile di voicing per gli accordi:"), self.voicing_combo)

        self.poly_check = QCheckBox(tr("Strumento polifonico"))
        layout.addRow(self.poly_check)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self._apply_family_defaults()
        if not self.name_edit.text():
            self._suggest_name_from_gm()
        self.name_edit.textEdited.connect(lambda _: setattr(self, "_name_edited", True))
        self._name_edited = False

    def _on_gm_changed(self, _index):
        # I preset per famiglia (GM_FAMILY_DEFAULTS) valgono solo per il
        # catalogo melodico: in modalita' percussioni il picker elenca i
        # drum kit, i cui numeri di programma non c'entrano con le famiglie
        # melodiche (es. programma 8 = "Room Kit", non "Percussioni intonate").
        if not self.percussion_check.isChecked():
            self._apply_family_defaults()
        if not self._name_edited:
            self._suggest_name_from_gm()

    def _on_percussion_toggled(self, checked):
        self.gm_picker.set_percussion_mode(checked)
        if checked:
            self.voicing_combo.setCurrentText("root_only")
            self.poly_check.setChecked(True)
        else:
            self._apply_family_defaults()

    def _apply_family_defaults(self):
        program = self.gm_picker.selected_program()
        if program is None:
            return
        family = gm_family_for_program(program)
        defaults = GM_FAMILY_DEFAULTS.get(family)
        if not defaults:
            return
        self.octave_spin.setValue(defaults["default_octave"])
        self.range_low_spin.setValue(defaults["range_low"])
        self.range_high_spin.setValue(defaults["range_high"])
        self.voicing_combo.setCurrentText(defaults["voicing_style"])
        self.poly_check.setChecked(defaults["polyphonic"])

    def _suggest_name_from_gm(self):
        name = self.gm_picker.selected_name()
        if not name:
            return
        # Nome-programma: solo lettere/numeri, senza spazi ne' parentesi
        simplified = "".join(ch for ch in name if ch.isalnum())
        self.name_edit.setText(simplified)

    def build_profile(self) -> InstrumentProfile:
        name = self.name_edit.text().strip()
        if not name or not name.isalnum():
            raise ValueError(tr("Il nome dello strumento deve essere una sola parola alfanumerica (senza spazi)."))

        is_percussion = self.percussion_check.isChecked()
        gm_program = self.gm_picker.selected_program()
        if gm_program is None:
            if is_percussion:
                raise ValueError(tr("Seleziona un kit percussioni dall'elenco."))
            raise ValueError(tr("Seleziona uno strumento General MIDI dall'elenco."))

        return InstrumentProfile(
            name=name,
            gm_program=gm_program,
            is_percussion=is_percussion,
            default_octave=self.octave_spin.value(),
            range_low=self.range_low_spin.value(),
            range_high=self.range_high_spin.value(),
            polyphonic=self.poly_check.isChecked(),
            voicing_style=self.voicing_combo.currentText(),
        )


class InstrumentManagerDialog(QDialog):
    """Elenco degli strumenti disponibili, con possibilita' di aggiungerne
    di nuovi e rimuovere quelli personalizzati (funzionalita' 1)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Gestione strumenti"))
        self.resize(420, 460)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr("Strumenti disponibili (i predefiniti non sono modificabili):")))

        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_widget)
        self._refresh_list()

        btn_row = QHBoxLayout()
        add_btn = QPushButton(tr("+ Nuovo strumento"))
        add_btn.setToolTip(tr("Crea un nuovo strumento personalizzato scegliendo un suono General MIDI."))
        add_btn.clicked.connect(self._add_instrument)
        del_btn = QPushButton(tr("Rimuovi selezionato"))
        del_btn.setToolTip(tr("Rimuove lo strumento personalizzato selezionato (i predefiniti non si possono rimuovere)."))
        del_btn.clicked.connect(self._remove_selected)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(del_btn)
        layout.addLayout(btn_row)

        sf_frame = QFrame()
        sf_frame.setFrameShape(QFrame.StyledPanel)
        sf_frame.setObjectName("panelBox")
        sf_layout = QVBoxLayout(sf_frame)
        sf_layout.addWidget(QLabel(tr("<b>SoundFont per lo strumento selezionato</b>")))
        self.sf_value_label = QLabel("—")
        self.sf_value_label.setWordWrap(True)
        sf_layout.addWidget(self.sf_value_label)
        sf_btn_row = QHBoxLayout()
        self.sf_choose_btn = QPushButton(tr("Scegli SoundFont..."))
        self.sf_choose_btn.setToolTip(
            tr("Assegna un file .sf2 specifico a questo strumento: verra' usato al posto di quello "
            "predefinito (Playback -> Scegli SoundFont) su ogni traccia che usa questo strumento. "
            "Richiede il motore fluidsynth persistente (libreria FluidSynth): con i fallback CLI/timidity/"
            "wildmidi/player di sistema l'override viene ignorato.")
        )
        self.sf_choose_btn.clicked.connect(self._choose_instrument_soundfont)
        self.sf_clear_btn = QPushButton(tr("Usa predefinito"))
        self.sf_clear_btn.clicked.connect(self._clear_instrument_soundfont)
        sf_btn_row.addWidget(self.sf_choose_btn)
        sf_btn_row.addWidget(self.sf_clear_btn)
        sf_layout.addLayout(sf_btn_row)
        layout.addWidget(sf_frame)
        self._update_soundfont_panel()

        # Kit percussioni: a differenza degli altri campi, si puo' cambiare
        # anche per uno strumento a percussioni predefinito (es. 'Drums'),
        # non solo per quelli personalizzati - vedi core.settings
        # get/set_drum_kit_override. Il pannello resta nascosto per gli
        # strumenti melodici, dove non ha senso.
        self.kit_frame = QFrame()
        self.kit_frame.setFrameShape(QFrame.StyledPanel)
        self.kit_frame.setObjectName("panelBox")
        kit_layout = QVBoxLayout(self.kit_frame)
        kit_layout.addWidget(QLabel(tr("<b>Kit percussioni</b> (General MIDI 2)")))
        self.kit_combo = QComboBox()
        for program, kit_name in sorted(GM_DRUM_KITS.items()):
            self.kit_combo.addItem(kit_name, program)
        self.kit_combo.currentIndexChanged.connect(self._on_kit_changed)
        kit_layout.addWidget(self.kit_combo)
        layout.addWidget(self.kit_frame)
        self._update_kit_panel()

        close_btn = QPushButton(tr("Chiudi"))
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _refresh_list(self):
        self.list_widget.clear()
        catalog = all_instruments()
        for name in sorted_instrument_names():
            instr = catalog[name]
            tag = " (predefinito)" if name in DEFAULT_INSTRUMENTS else " (personalizzato)"
            if instr.is_percussion:
                kit_name = GM_DRUM_KITS.get(instr.gm_program, f"kit {instr.gm_program}")
                sound = tr("Percussioni (canale 10) — {kit_name}", kit_name=kit_name)
            else:
                sound = tr("{0} — program {gm_program}", gm_family_for_program(instr.gm_program), gm_program=instr.gm_program)
            override = app_settings.get_instrument_soundfont(name)
            sf_tag = tr(" · SoundFont: {0}", os.path.basename(override)) if override else ""
            self.list_widget.addItem(f"{name}{tag} · {sound}{sf_tag}")

    def _selected_instrument_name(self):
        row = self.list_widget.currentRow()
        if row < 0:
            return None
        return sorted_instrument_names()[row]

    def _on_selection_changed(self, _row):
        self._update_soundfont_panel()
        self._update_kit_panel()

    def _update_kit_panel(self):
        name = self._selected_instrument_name()
        instr = all_instruments().get(name) if name is not None else None
        is_perc = instr is not None and instr.is_percussion
        self.kit_frame.setVisible(is_perc)
        if not is_perc:
            return
        idx = self.kit_combo.findData(instr.gm_program)
        self.kit_combo.blockSignals(True)
        self.kit_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.kit_combo.blockSignals(False)

    def _on_kit_changed(self, _index):
        name = self._selected_instrument_name()
        if name is None:
            return
        program = self.kit_combo.currentData()
        if program is None:
            return
        app_settings.set_drum_kit_override(name, program)
        self._refresh_list()
        names = sorted_instrument_names()
        if name in names:
            self.list_widget.setCurrentRow(names.index(name))

    def _update_soundfont_panel(self):
        name = self._selected_instrument_name()
        enabled = name is not None
        self.sf_choose_btn.setEnabled(enabled)
        if not enabled:
            self.sf_value_label.setText("—")
            self.sf_clear_btn.setEnabled(False)
            return
        override = app_settings.get_instrument_soundfont(name)
        if override:
            self.sf_value_label.setText(override)
            self.sf_clear_btn.setEnabled(True)
        else:
            self.sf_value_label.setText(tr("Predefinito (Playback -> Scegli SoundFont)"))
            self.sf_clear_btn.setEnabled(False)

    def _choose_instrument_soundfont(self):
        name = self._selected_instrument_name()
        if name is None:
            return
        from core.project_io import ensure_soundfonts_dir
        path, _ = QFileDialog.getOpenFileName(self, tr("Scegli SoundFont per '{name}'", name=name), ensure_soundfonts_dir(),
                                              tr("SoundFont (*.sf2)"),
                                              options=QFileDialog.Option.DontUseNativeDialog)
        if not path:
            return
        app_settings.set_instrument_soundfont(name, path)
        self._refresh_list()
        self.list_widget.setCurrentRow(sorted_instrument_names().index(name))
        self._update_soundfont_panel()

    def _clear_instrument_soundfont(self):
        name = self._selected_instrument_name()
        if name is None:
            return
        app_settings.clear_instrument_soundfont(name)
        self._refresh_list()
        self.list_widget.setCurrentRow(sorted_instrument_names().index(name))
        self._update_soundfont_panel()

    def _add_instrument(self):
        dlg = NewInstrumentDialog(self)
        if dlg.exec() == QDialog.Accepted:
            try:
                profile = dlg.build_profile()
                add_custom_instrument(profile)
                self._refresh_list()
            except ValueError as e:
                QMessageBox.warning(self, tr("Errore"), str(e))

    def _remove_selected(self):
        row = self.list_widget.currentRow()
        if row < 0:
            return
        name = sorted_instrument_names()[row]
        if not is_custom_instrument(name):
            QMessageBox.warning(self, tr("Non consentito"), tr("Gli strumenti predefiniti non possono essere rimossi."))
            return
        reply = QMessageBox.question(self, tr("Conferma"), tr("Rimuovere lo strumento '{name}'?", name=name))
        if reply == QMessageBox.Yes:
            remove_custom_instrument(name)
            app_settings.clear_instrument_soundfont(name)
            self._refresh_list()
            self._update_soundfont_panel()
