from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QListWidget,
    QComboBox, QInputDialog, QMessageBox,
)

from core.model import Project
from core.notation import validate_track_text, tokenize, Pattern
from core.completion import completions_for_word
from core.instruments import get_instrument, list_instrument_names
from core.playback import PlaybackEngine
from core import midi_library

from .play_highlight import PlayHighlighter
from .voicing_picker import NotationEditor, handle_chord_double_click
from .selection_actions import handle_selection_context_menu
from .audio_import_dialog import AudioImportDialog
from .keyboard_play_dialog import KeyboardPlayDialog
from .highlighter import NotationHighlighter
from core.i18n import tr


class PatternEditorDialog(QDialog):
    """Gestione della libreria di pattern universali (sezione 6 delle specifiche)."""

    def __init__(self, project: Project, parent=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle(tr("Libreria Pattern (%Nome)"))
        self.resize(560, 420)

        layout = QHBoxLayout(self)

        left = QVBoxLayout()
        self.list_widget = QListWidget()
        self.list_widget.addItems(sorted(self.project.patterns.keys()))
        self.list_widget.currentTextChanged.connect(self._load_pattern)
        left.addWidget(QLabel(tr("Pattern definiti:")))
        left.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        add_btn = QPushButton(tr("Nuovo"))
        add_btn.setToolTip(tr("Crea un nuovo pattern vuoto da riempire."))
        add_btn.clicked.connect(self._new_pattern)
        rename_btn = QPushButton(tr("Rinomina"))
        rename_btn.setToolTip(
            tr("Rinomina il pattern selezionato, aggiornando automaticamente tutti i "
            "riferimenti %nome nelle tracce e negli altri pattern.")
        )
        rename_btn.clicked.connect(self._rename_pattern)
        del_btn = QPushButton(tr("Elimina"))
        del_btn.setToolTip(tr("Elimina il pattern selezionato (le tracce che lo richiamano smetteranno di funzionare)."))
        del_btn.clicked.connect(self._delete_pattern)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(rename_btn)
        btn_row.addWidget(del_btn)
        left.addLayout(btn_row)

        right = QVBoxLayout()
        right.addWidget(QLabel(tr("Corpo del pattern (token separati da spazi):")))
        self.body_edit = NotationEditor()
        self.body_edit.setFont(QFont("Monospace"))
        self.body_edit.setToolTip(
            tr("Sequenza di token della notazione (note, accordi, percussioni, comandi di stato...). "
            "Doppio click su un accordo per scegliere un voicing alternativo.")
        )
        self.body_edit.on_double_click_token = self._on_body_double_click
        self.body_edit.on_selection_context_menu = self._on_body_selection_context_menu
        self.body_edit.on_completion_request = self._body_completions
        self.body_edit.setToolTip(
            self.body_edit.toolTip() +
            tr("\nSeleziona una sequenza e tasto destro per Play / Raggruppa / Trasforma in pattern.")
        )
        self._highlighter = NotationHighlighter(self.body_edit.document())
        right.addWidget(self.body_edit)
        save_btn = QPushButton(tr("Salva pattern corrente"))
        save_btn.setToolTip(tr("Salva le modifiche al pattern selezionato."))
        save_btn.clicked.connect(self._save_current)
        right.addWidget(save_btn)

        import_audio_btn = QPushButton(tr("Importa audio (in questo pattern)"))
        import_audio_btn.setToolTip(
            tr("Registra dal microfono o carica un file audio (.wav/.mp3/.m4a) e lo converte "
            "in notazione, sostituendo il corpo del pattern corrente. Usa lo strumento scelto "
            "in 'Ascolta con:' per decidere modalita' melodica/percussiva e anteprima.")
        )
        import_audio_btn.clicked.connect(self._import_audio)
        right.addWidget(import_audio_btn)

        keyboard_play_btn = QPushButton(tr("Suona con la tastiera (in questo pattern)"))
        keyboard_play_btn.setToolTip(
            tr("Registra una performance suonata con la tastiera del computer e la converte in "
            "notazione, sostituendo il corpo del pattern corrente. Usa lo strumento scelto in "
            "'Ascolta con:' per decidere modalita' melodica/percussiva e anteprima.")
        )
        keyboard_play_btn.clicked.connect(self._play_keyboard)
        right.addWidget(keyboard_play_btn)

        play_row = QHBoxLayout()
        play_row.addWidget(QLabel(tr("Ascolta con:")))
        self.instrument_combo = QComboBox()
        self.instrument_combo.addItems(list_instrument_names())
        self.instrument_combo.setToolTip(tr("Strumento usato solo per l'anteprima audio (il pattern resta universale)."))
        play_row.addWidget(self.instrument_combo)
        self.play_btn = QPushButton(tr("▶ Ascolta"))
        self.play_btn.setToolTip(tr("Riproduce il pattern selezionato con lo strumento scelto qui a fianco."))
        self.play_btn.clicked.connect(self._play_current)
        play_row.addWidget(self.play_btn)
        self.stop_btn = QPushButton(tr("■ Stop"))
        self.stop_btn.clicked.connect(self._stop_playback)
        play_row.addWidget(self.stop_btn)
        right.addLayout(play_row)

        layout.addLayout(left, 1)
        layout.addLayout(right, 2)

        self._current_name = None
        self._playback = PlaybackEngine()
        # Evidenziazione, nel corpo del pattern, di cio' che sta suonando
        # (l'anteprima suona %nome, che si espande nello stesso testo).
        self._play_highlight = PlayHighlighter(self.body_edit, self, "_playback")
        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)

    def _load_pattern(self, name):
        self._current_name = name or None
        if name and name in self.project.patterns:
            self.body_edit.setPlainText(" ".join(self.project.patterns[name].tokens))
        else:
            self.body_edit.setPlainText("")

    def _new_pattern(self):
        name, ok = QInputDialog.getText(self, tr("Nuovo pattern"), tr("Nome pattern (senza %):"))
        if ok and name.strip():
            name = name.strip()
            self.project.patterns[name] = Pattern(name=name, tokens=[])
            self.list_widget.addItem(name)
            self.list_widget.setCurrentRow(self.list_widget.count() - 1)

    def _rename_pattern(self):
        if not self._current_name:
            QMessageBox.information(self, tr("Nessun pattern selezionato"), tr("Seleziona un pattern da rinominare."))
            return
        new_name, ok = QInputDialog.getText(self, tr("Rinomina pattern"), tr("Nuovo nome (senza %):"),
                                             text=self._current_name)
        new_name = new_name.strip()
        if not ok or not new_name or new_name == self._current_name:
            return
        old_name = self._current_name
        try:
            self.project.rename_pattern(old_name, new_name)
        except (KeyError, ValueError) as e:
            QMessageBox.critical(self, tr("Impossibile rinominare"), str(e))
            return
        self.list_widget.clear()
        self.list_widget.addItems(sorted(self.project.patterns.keys()))
        items = self.list_widget.findItems(new_name, Qt.MatchExactly)
        if items:
            self.list_widget.setCurrentItem(items[0])
        QMessageBox.information(
            self, tr("Pattern rinominato"),
            tr("'%{old_name}' rinominato in '%{new_name}'. Riferimenti nelle tracce e negli altri pattern aggiornati automaticamente.", old_name=old_name, new_name=new_name)
        )

    def _delete_pattern(self):
        if self._current_name and self._current_name in self.project.patterns:
            places = self.project.pattern_usages(self._current_name)
            if places:
                shown = "\n".join("  - " + p for p in places[:12])
                if len(places) > 12:
                    shown += "\n  ..."
                answer = QMessageBox.question(
                    self, tr("Pattern in uso"),
                    tr("'%{name}' e' usato in:\n{places}\n\nSe lo elimini, quei richiami daranno errore. Eliminarlo lo stesso?",
                       name=self._current_name, places=shown),
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if answer != QMessageBox.Yes:
                    return
            del self.project.patterns[self._current_name]
            row = self.list_widget.currentRow()
            self.list_widget.takeItem(row)

    def _save_current(self):
        if not self._current_name:
            QMessageBox.warning(self, tr("Nessun pattern selezionato"), tr("Seleziona o crea un pattern prima di salvare."))
            return
        self.project.patterns[self._current_name] = Pattern(
            name=self._current_name, tokens=tokenize(self.body_edit.toPlainText())
        )
        QMessageBox.information(self, tr("Salvato"), tr("Pattern '%{_current_name}' aggiornato.", _current_name=self._current_name))

    def _import_audio(self):
        if not self._current_name:
            QMessageBox.information(self, tr("Nessun pattern"), tr("Seleziona o crea un pattern prima di importare audio."))
            return
        instrument_name = self.instrument_combo.currentText()
        dlg = AudioImportDialog(self, project=self.project, instrument_name=instrument_name,
                                 context_label=tr("pattern '%{_current_name}'", _current_name=self._current_name))
        if dlg.exec() != QDialog.Accepted:
            return
        self.body_edit.setPlainText(dlg.result_text())

    def _play_keyboard(self):
        if not self._current_name:
            QMessageBox.information(self, tr("Nessun pattern"), tr("Seleziona o crea un pattern prima di suonare."))
            return
        instrument_name = self.instrument_combo.currentText()
        dlg = KeyboardPlayDialog(self, project=self.project, instrument_name=instrument_name,
                                  context_label=tr("pattern '%{_current_name}'", _current_name=self._current_name))
        if dlg.exec() != QDialog.Accepted:
            return
        self.body_edit.setPlainText(dlg.result_text())

    def _play_current(self):
        if not self._current_name:
            QMessageBox.information(self, tr("Nessun pattern"), tr("Seleziona un pattern da ascoltare."))
            return
        # Salva prima le eventuali modifiche non ancora confermate, cosi' l'anteprima
        # riflette esattamente cio' che si vede nell'editor.
        self.project.patterns[self._current_name] = Pattern(
            name=self._current_name, tokens=tokenize(self.body_edit.toPlainText())
        )
        preview = Project(name="preview", tempo_bpm=self.project.tempo_bpm)
        preview.patterns = self.project.patterns
        preview.add_track("Anteprima", self.instrument_combo.currentText(), f"%{self._current_name}")

        ok, msg = validate_track_text(preview.tracks[0].text, preview.patterns,
                                       default_octave=preview.tracks[0].instrument.default_octave)
        if not ok:
            QMessageBox.critical(self, tr("Errore di sintassi"), tr("Impossibile riprodurre:\n{msg}", msg=msg))
            return
        self._play_highlight.play(preview, preview.patterns, preview.tracks[0].instrument.default_octave)

    def _stop_playback(self):
        self._play_highlight.stop()

    def _on_body_double_click(self, char_offset: int, global_pos) -> bool:
        instrument_name = self.instrument_combo.currentText()
        instrument = get_instrument(instrument_name)
        return handle_chord_double_click(
            self.body_edit, self.body_edit.toPlainText(), char_offset, global_pos,
            self.project.patterns, instrument, instrument_name,
            self.project.tempo_bpm, self._playback,
        )

    def _on_body_selection_context_menu(self, sel_start: int, sel_end: int, global_pos) -> bool:
        instrument_name = self.instrument_combo.currentText()
        instrument = get_instrument(instrument_name)
        return handle_selection_context_menu(
            self.body_edit, self.body_edit.toPlainText(), sel_start, sel_end,
            self.project.patterns, instrument, instrument_name,
            self.project.tempo_bpm, self._playback, global_pos, before_play=self._play_highlight.stop,
        )

    def _body_completions(self, word: str):
        instrument = get_instrument(self.instrument_combo.currentText())
        return completions_for_word(
            word, patterns=self.project.patterns, instrument=instrument,
            midi_ref_names=midi_library.list_midi_library,
        )

    def closeEvent(self, event):
        self._play_highlight.stop()
        super().closeEvent(event)

    def done(self, result):
        # Esc chiude il dialogo passando da qui, senza closeEvent: l'anteprima
        # non deve continuare a suonare a dialogo chiuso.
        self._play_highlight.stop()
        super().done(result)
