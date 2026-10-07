import os
import shutil

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QLabel, QPushButton,
    QComboBox, QMessageBox, QFileDialog, QInputDialog
)

from core import midi_convert, midi_library
from core.instruments import get_instrument, list_instrument_names
from core.playback import PlaybackEngine
from core.i18n import tr


class MidiLibraryDialog(QDialog):
    """Vedi/modifica i file MIDI della libreria (cartella 'midi/', anche in
    sottocartelle), richiamabili nelle tracce con il prefisso &Nome,
    analogamente ai pattern %Nome."""

    def __init__(self, parent=None, midi_dir=None, project=None):
        """project: il brano aperto, per aggiornarne i richiami &"Nome" quando
        si rinomina un file (project_changed dice poi se e' successo)."""
        super().__init__(parent)
        self.project = project
        self.project_changed = False
        self.midi_dir = midi_library.ensure_midi_dir(midi_dir)
        self.setWindowTitle(tr('Libreria MIDI (&"Nome") — {midi_dir}', midi_dir=self.midi_dir))
        self.resize(680, 480)

        layout = QHBoxLayout(self)

        left = QVBoxLayout()
        left.addWidget(QLabel(tr("File .mid disponibili (incluse le sottocartelle):")))
        self.list_widget = QListWidget()
        self.list_widget.currentTextChanged.connect(self._load_selected)
        left.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        import_btn = QPushButton(tr("Importa file..."))
        import_btn.setToolTip(tr("Copia un file .mid esistente nella libreria, opzionalmente in una sottocartella."))
        import_btn.clicked.connect(self._import_file)
        rename_btn = QPushButton(tr("Rinomina/sposta"))
        rename_btn.setToolTip(tr("Rinomina il file selezionato o spostalo in un'altra sottocartella."))
        rename_btn.clicked.connect(self._rename_selected)
        delete_btn = QPushButton(tr("Elimina"))
        delete_btn.setToolTip(tr("Elimina definitivamente il file dalla libreria."))
        delete_btn.clicked.connect(self._delete_selected)
        btn_row.addWidget(import_btn)
        btn_row.addWidget(rename_btn)
        btn_row.addWidget(delete_btn)
        left.addLayout(btn_row)

        right = QVBoxLayout()
        right.addWidget(QLabel(
            tr("Anteprima/modifica (canale con piu' note, convertito in notazione testuale).\n"
            "Richiamabile in una traccia con &\"Nome\" (ricerca in tutte le sottocartelle) o\n"
            "&\"Sottocartella/Nome\" (percorso esplicito, per evitare ambiguita').\n"
            "Combinabile con ripetizione e trasposizione: 2&\"Nome\"+5.")
        ))
        from .voicing_picker import NotationEditor
        self.preview_edit = NotationEditor()
        self.preview_edit.setFont(QFont("Monospace", 10))
        from .highlighter import NotationHighlighter
        self._highlighter = NotationHighlighter(self.preview_edit.document())
        self.preview_edit.on_selection_context_menu = self._on_preview_selection_context_menu
        right.addWidget(self.preview_edit)

        instr_row = QHBoxLayout()
        instr_row.addWidget(QLabel(tr("Strumento per rigenerare il MIDI:")))
        self.instrument_combo = QComboBox()
        self.instrument_combo.addItems(list_instrument_names())
        instr_row.addWidget(self.instrument_combo)
        right.addLayout(instr_row)

        save_btn = QPushButton(tr("Rigenera file MIDI dal testo modificato"))
        save_btn.setToolTip(tr("Riscrive il file .mid a partire dal testo modificato qui sopra, con lo strumento scelto."))
        save_btn.clicked.connect(self._save_current)
        right.addWidget(save_btn)

        style_btn = QPushButton(tr("Salva come stile del generatore..."))
        style_btn.setToolTip(
            tr("Ricava da un canale del file (batteria, basso, accompagnamento, riff) un nuovo stile "
            "per i generatori; gli accordi si possono leggere da un altro canale dello stesso file."))
        style_btn.clicked.connect(self._save_as_style)
        right.addWidget(style_btn)

        play_row = QHBoxLayout()
        self.play_btn = QPushButton(tr("▶ Ascolta file originale"))
        self.play_btn.setToolTip(tr("Riproduce il file .mid selezionato cosi' com'e' (tutti i canali, non solo l'anteprima)."))
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
        self._refresh_list()

    def _abspath(self, rel_name: str) -> str:
        """Percorso assoluto di un nome relativo tipo 'Guitar/Intro' -> midi_dir/Guitar/Intro.mid"""
        return os.path.join(self.midi_dir, *rel_name.split("/")) + ".mid"

    def _refresh_list(self, select=None):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        names = midi_library.list_midi_library(self.midi_dir)
        self.list_widget.addItems(names)
        self.list_widget.blockSignals(False)
        if select and select in names:
            self.list_widget.setCurrentRow(names.index(select))
        elif names:
            self.list_widget.setCurrentRow(0)

    def _load_selected(self, name):
        self._current_name = name or None
        if not name:
            self.preview_edit.setPlainText("")
            return
        path = self._abspath(name)
        try:
            tempo, tpb, channels = midi_convert.analyze_midi(path)
            primary = midi_convert.pick_primary_channel(channels)
            if primary is None:
                self.preview_edit.setPlainText(tr("(nessuna nota trovata nel file)"))
                return
            tokens = midi_convert.channel_to_tokens(primary, tpb)
            guess = midi_convert.guess_instrument_name(primary.program, primary.is_percussion)
            idx = self.instrument_combo.findText(guess)
            if idx >= 0:
                self.instrument_combo.setCurrentIndex(idx)
            self.preview_edit.setPlainText(" ".join(tokens))
        except Exception as e:
            self.preview_edit.setPlainText(tr("(errore lettura file: {e})", e=e))

    def _import_file(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("Importa MIDI nella libreria"), "", tr("MIDI (*.mid *.midi)"),
                                              options=QFileDialog.Option.DontUseNativeDialog)
        if not path:
            return
        dest_name, ok = QInputDialog.getText(
            self, tr("Nome nella libreria"),
            tr("Nome da usare per &\"Nome\" (senza estensione).\n"
            "Puoi includere una sottocartella, es. Blues/bass_line:"),
            text=os.path.splitext(os.path.basename(path))[0]
        )
        if not ok or not dest_name.strip():
            return
        dest_name = dest_name.strip().strip("/")
        dest_path = self._abspath(dest_name)
        if os.path.exists(dest_path):
            if QMessageBox.question(self, tr("Sovrascrivere?"),
                                     tr("'{dest_name}' esiste gia' nella libreria. Sovrascrivere?", dest_name=dest_name)) != QMessageBox.Yes:
                return
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.copy(path, dest_path)
        midi_library.clear_midi_ref_cache()
        self._refresh_list(select=dest_name)

    def _rename_selected(self):
        if not self._current_name:
            return
        new_name, ok = QInputDialog.getText(
            self, "Rinomina/sposta",
            tr("Nuovo nome (senza estensione). Puoi includere una sottocartella\n"
            "per spostare il file, es. Blues/bass_line:"),
            text=self._current_name)
        if not ok or not new_name.strip():
            return
        new_name = new_name.strip().strip("/")
        if new_name == self._current_name:
            return
        src = self._abspath(self._current_name)
        dst = self._abspath(new_name)
        if os.path.exists(dst):
            QMessageBox.warning(self, tr("Errore"), tr("Esiste gia' un file con questo nome/percorso."))
            return
        before = midi_library.list_midi_library(self.midi_dir)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        os.rename(src, dst)
        midi_library.clear_midi_ref_cache()
        self._update_project_refs(self._current_name, new_name, before)
        self._refresh_list(select=new_name)

    def _update_project_refs(self, old_rel: str, new_rel: str, before):
        """Dopo la rinomina di old_rel in new_rel: propone di aggiornare i
        richiami &Nome del brano aperto. Un richiamo con la sottocartella
        (&Sub/Nome) resta con la sottocartella; uno col solo nome
        (&Nome, valido solo se il nome era unico nella libreria) resta col
        solo nome, se anche il nuovo lo e'."""
        if self.project is None:
            return
        after = [new_rel if rel == old_rel else rel for rel in before]
        basename = lambda rel: rel.split("/")[-1]
        old_base, new_base = basename(old_rel), basename(new_rel)
        old_unique = [basename(r) for r in before].count(old_base) == 1
        new_short = new_base if [basename(r) for r in after].count(new_base) == 1 else new_rel
        renames = []
        if "/" in old_rel:
            renames.append(([old_rel], new_rel))
        if old_unique:
            renames.append(([old_base], new_short))
        count = sum(self.project.rename_midi_ref(names, new, apply=False) for names, new in renames)
        if not count:
            return
        answer = QMessageBox.question(
            self, tr("Aggiorna il brano"),
            tr("Il brano aperto richiama '&{old}' {n} volte. Aggiornare i richiami a '&{new}'?",
               old=old_rel, n=count, new=new_rel),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if answer != QMessageBox.Yes:
            return
        for names, new in renames:
            self.project.rename_midi_ref(names, new)
        self.project_changed = True

    def _delete_selected(self):
        if not self._current_name:
            return
        reply = QMessageBox.question(self, tr("Conferma"), tr("Eliminare '{_current_name}.mid' dalla libreria?", _current_name=self._current_name))
        if reply == QMessageBox.Yes:
            os.remove(self._abspath(self._current_name))
            midi_library.clear_midi_ref_cache()
            self._current_name = None
            self._refresh_list()

    def _save_current(self):
        if not self._current_name:
            QMessageBox.warning(self, tr("Nessun file selezionato"), tr("Seleziona o importa un file MIDI prima."))
            return
        path = self._abspath(self._current_name)
        try:
            midi_library.render_tokens_to_midi(
                self.preview_edit.toPlainText(),
                self.instrument_combo.currentText(),
                tempo_bpm=120,
                path=path,
            )
            QMessageBox.information(self, tr("Salvato"), tr("'{_current_name}.mid' rigenerato dal testo.", _current_name=self._current_name))
        except Exception as e:
            QMessageBox.critical(self, tr("Errore"), tr("Impossibile rigenerare il file MIDI:\n{e}", e=e))

    def _save_as_style(self):
        from .save_style_dialog import SaveStyleDialog, source_for_part
        if not self._current_name:
            QMessageBox.warning(self, tr("Nessun file selezionato"), tr("Seleziona o importa un file MIDI prima."))
            return
        try:
            _tempo, tpb, channels = midi_convert.analyze_midi(self._abspath(self._current_name))
        except Exception as e:
            QMessageBox.critical(self, tr("Errore"), tr("Impossibile leggere il file MIDI:\n{e}", e=e))
            return
        sources, chord_sources = [], []
        for number, channel in sorted(channels.items()):
            if channel.note_count <= 0:
                continue
            text = " ".join(midi_convert.channel_to_tokens(channel, tpb))
            name = midi_convert.guess_instrument_name(channel.program, channel.is_percussion)
            label = tr("canale {0} ({name})", number + 1, name=name)
            sources.append(source_for_part(label, text, get_instrument(name)))
            if not channel.is_percussion:
                chord_sources.append((label, text))
        if not sources:
            QMessageBox.information(self, tr("Niente da salvare"), tr("Il file non contiene note."))
            return
        dlg = SaveStyleDialog(self, sources, chord_sources, midi_dir=self.midi_dir)
        dlg.exec()

    def _play_current(self):
        if not self._current_name:
            QMessageBox.information(self, tr("Nessun file selezionato"), tr("Seleziona un file da ascoltare."))
            return
        path = self._abspath(self._current_name)
        if not os.path.exists(path):
            QMessageBox.warning(self, tr("File non trovato"), tr("Il file selezionato non esiste piu' su disco."))
            return
        self._playback.play_file(path)

    def _stop_playback(self):
        self._playback.stop()

    def _on_preview_selection_context_menu(self, sel_start: int, sel_end: int, global_pos) -> bool:
        """Tasto destro su una selezione del testo: ▶ Play la ascolta con lo
        strumento scelto sotto (a 120 BPM: la libreria non ha un progetto)."""
        from .selection_actions import handle_selection_context_menu
        instrument_name = self.instrument_combo.currentText()
        return handle_selection_context_menu(
            self.preview_edit, self.preview_edit.toPlainText(), sel_start, sel_end,
            {}, get_instrument(instrument_name), instrument_name, 120, self._playback, global_pos,
            midi_dir=self.midi_dir, play_only=True,
        )

    def closeEvent(self, event):
        self._playback.stop()
        super().closeEvent(event)
