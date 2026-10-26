"""
Dialogo di modifica del contenuto di un box (Clip) della vista Struttura
brano: aperto con doppio click su un box nel canvas (gui.arrangement_view).
Stesso schema di gui.pattern_editor_dialog (un box e' autosufficiente come
il corpo di un pattern) ridotto all'essenziale: nome + editor con
evidenziazione/autocompletamento/menu contestuale, Play/Stop di anteprima,
Ok/Annulla con validazione della sintassi prima di chiudere.
"""

import re
from typing import Optional

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core import midi_library
from core.completion import completions_for_word
from core.instruments import get_instrument
from core.arrangement import anchored_preview_text, expand_pattern_refs_text
from core.model import Project, copy_synth
from core.notation import validate_track_text, notation_warnings, bar_issues_summary, NotationError
from core.playback import PlaybackEngine

from .highlighter import NotationHighlighter
from .pattern_editor_dialog import PatternEditorDialog, pattern_ref_at
from .theme import BAD, good_text, warn_text
from .play_highlight import PlayHighlighter
from .selection_actions import handle_selection_context_menu
from .voicing_picker import NotationEditor, handle_chord_double_click
from core.i18n import tr

class BoxEditDialog(QDialog):
    def __init__(self, parent, project: Project, instrument_name: str, tempo_bpm: int,
                 clip_name: str = "", clip_text: str = "", title: str = tr("Modifica box"),
                 with_name: bool = True, start_beat: float = 0.0, track_name: Optional[str] = None,
                 on_patterns_edited=None):
        """with_name=False: senza il campo Nome, per modificare il testo libero
        di una traccia senza box (vedi gui.arrangement_view.edit_free_text).
        start_beat: dove il box comincia nel brano, per i controlli di
        battuta '|' (le stanghette sono quelle del brano, non del box).
        on_patterns_edited: richiamata dopo la Libreria Pattern aperta con un
        doppio click su un %Nome (aggiornare il resto della finestra)."""
        super().__init__(parent)
        self.project = project
        self.track_name = track_name    # traccia reale (per lo strumento plugin delle anteprime)
        self.on_patterns_edited = on_patterns_edited
        self.start_beat = start_beat
        self.instrument_name = instrument_name
        self.instrument = get_instrument(instrument_name)
        self.tempo_bpm = tempo_bpm
        self.setWindowTitle(title)
        self.resize(560, 420)

        layout = QVBoxLayout(self)

        self.name_edit = None
        if with_name:
            name_row = QHBoxLayout()
            name_row.addWidget(QLabel(tr("Nome:")))
            self.name_edit = QLineEdit(clip_name)
            name_row.addWidget(self.name_edit)
            layout.addLayout(name_row)

        score_row = QHBoxLayout()
        score_row.addWidget(QLabel(tr("Partitura (strumento: {instrument_name}):", instrument_name=instrument_name)))
        score_row.addStretch(1)
        # Mostra il box con il contenuto dei pattern al posto dei %Nome, in
        # sola lettura: un secondo editor, cosi' quello vero resta com'e'
        # (testo, cursore, Annulla). Visibile solo se il box usa dei pattern.
        self.expand_check = QCheckBox(tr("Espandi i pattern"))
        self.expand_check.setToolTip(tr("Mostra il contenuto dei pattern usati nel box (in sola lettura)"))
        self.expand_check.toggled.connect(self._on_expand_toggled)
        score_row.addWidget(self.expand_check)
        layout.addLayout(score_row)
        self.body_edit = NotationEditor()
        self.body_edit.setFont(QFont("Monospace", 10))
        self.body_edit.setPlainText(clip_text)
        self.body_edit.on_double_click_token = self._on_body_double_click
        self.body_edit.on_selection_context_menu = self._on_body_selection_context_menu
        self.body_edit.on_completion_request = self._body_completions
        self._highlighter = NotationHighlighter(self.body_edit.document())
        layout.addWidget(self.body_edit)

        self.expanded_edit = NotationEditor()
        self.expanded_edit.setFont(QFont("Monospace", 10))
        self.expanded_edit.setReadOnly(True)
        self._expanded_highlighter = NotationHighlighter(self.expanded_edit.document())
        self.expanded_edit.hide()
        layout.addWidget(self.expanded_edit)

        # Sintassi e controlli di battuta, ricalcolati poco dopo ogni modifica.
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.setInterval(250)
        self._status_timer.timeout.connect(self._update_status)
        self.body_edit.textChanged.connect(self._status_timer.start)

        play_row = QHBoxLayout()
        self.play_btn = QPushButton(tr("▶ Play"))
        self.play_btn.clicked.connect(self._play)
        play_row.addWidget(self.play_btn)
        self.stop_btn = QPushButton(tr("■ Stop"))
        self.stop_btn.clicked.connect(self._stop)
        play_row.addWidget(self.stop_btn)
        play_row.addStretch(1)
        layout.addLayout(play_row)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self._playback = PlaybackEngine()

        # Evidenziazione del token in esecuzione durante il Play.
        self._play_highlight = PlayHighlighter(self.body_edit, self, "_playback")
        self._update_status()

    def _expanded_text(self) -> str:
        text = self.body_edit.toPlainText()
        try:
            return expand_pattern_refs_text(text, self.project.patterns, self.instrument.default_octave)
        except (NotationError, ValueError):
            return text   # testo non ancora valido (es. virgolette aperte): niente da espandere

    def _on_expand_toggled(self, checked: bool):
        if checked:
            self.expanded_edit.setPlainText(self._expanded_text())
        self.body_edit.setVisible(not checked)
        self.expanded_edit.setVisible(checked)
        # Se sta suonando, l'evidenziazione passa all'editor visibile.
        self._play_highlight.follow_editor(self.expanded_edit if checked else self.body_edit)

    def _update_status(self):
        text = self.body_edit.toPlainText()
        if not self.expand_check.isChecked():
            self.expand_check.setVisible(self._expanded_text() != text)
        octave = self.instrument.default_octave
        ok, msg = validate_track_text(text, self.project.patterns, default_octave=octave)
        issues = notation_warnings(text, self.project.patterns, self.project.time_sig,
                                 self.project.metrica_changes, start_beat=self.start_beat,
                                 default_octave=octave, pickup=self.project.pickup) if ok else []
        self._highlighter.set_bar_errors(i.char_start for i in issues)
        self.status_label.setToolTip("\n".join(i.message for i in issues))
        if not text.strip():
            self.status_label.setText("")
        elif not ok:
            self.status_label.setText(tr("✗  Errore di sintassi: {msg}", msg=msg))
            self.status_label.setStyleSheet(f"color: {BAD};")
        elif issues:
            self.status_label.setText(bar_issues_summary(issues))
            self.status_label.setStyleSheet(f"color: {warn_text()};")
        else:
            self.status_label.setText(tr("✓  Sintassi valida"))
            self.status_label.setStyleSheet(f"color: {good_text()};")

    def _preview_project(self, text: str) -> Project:
        preview = Project(name="preview", tempo_bpm=self.tempo_bpm, time_sig=self.project.time_sig,
                          metrica_changes=list(self.project.metrica_changes))
        preview.patterns = self.project.patterns
        copy_synth(preview.add_track("Anteprima", self.instrument_name, text), self._synth_track())
        return preview

    def _synth_track(self):
        return self.project.find_track(self.track_name) if self.track_name else None

    def _play(self):
        text = self.body_edit.toPlainText().strip()
        ok, msg = validate_track_text(text, self.project.patterns, default_octave=self.instrument.default_octave)
        if not ok:
            QMessageBox.critical(self, tr("Errore di sintassi"), tr("Impossibile riprodurre il box:\n{msg}", msg=msg))
            return
        # Con le ancore bar=N il box suona dal suo punto del brano.
        text, lead = anchored_preview_text(text, self.start_beat, self.project.patterns)
        self._play_highlight.play(self._preview_project(text), self.project.patterns,
                                  self.instrument.default_octave, only_audible=False, lead_beats=lead)

    def _stop(self):
        self._play_highlight.stop()

    def _on_body_double_click(self, char_offset: int, global_pos) -> bool:
        name = pattern_ref_at(self.body_edit.toPlainText(), char_offset, self.project.patterns)
        if name:
            self._open_pattern(name)
            return True
        return handle_chord_double_click(
            self.body_edit, self.body_edit.toPlainText(), char_offset, global_pos,
            self.project.patterns, self.instrument, self.instrument_name,
            self.tempo_bpm, self._playback, synth_track=self._synth_track(),
        )

    def _open_pattern(self, name: str):
        """Libreria Pattern gia' su %name e con lo strumento della traccia. Una
        rinomina aggiorna i richiami nel brano (core.model.Project.rename_pattern)
        ma non questo testo, ancora da confermare: la si applica anche qui."""
        self._play_highlight.stop()
        names_before = {id(p): n for n, p in self.project.patterns.items()}
        dlg = PatternEditorDialog(self.project, self, pattern_name=name, instrument_name=self.instrument_name)
        dlg.exec()
        text = self.body_edit.toPlainText()
        for n, p in self.project.patterns.items():
            old = names_before.get(id(p))
            if old is not None and old != n:
                text = re.sub("%" + re.escape(old) + r"(?!\w)", "%" + n, text)
        if text != self.body_edit.toPlainText():
            cursor = self.body_edit.textCursor()
            cursor.select(QTextCursor.Document)
            cursor.insertText(text)         # come una modifica: si puo' annullare
        if self.expand_check.isChecked():
            self.expanded_edit.setPlainText(self._expanded_text())
        self._update_status()
        if self.on_patterns_edited is not None:
            self.on_patterns_edited()

    def _on_body_selection_context_menu(self, sel_start: int, sel_end: int, global_pos) -> bool:
        return handle_selection_context_menu(
            self.body_edit, self.body_edit.toPlainText(), sel_start, sel_end,
            self.project.patterns, self.instrument, self.instrument_name,
            self.tempo_bpm, self._playback, global_pos, before_play=self._play_highlight.stop,
            synth_track=self._synth_track(), host_project=self.project, origin_beat=self.start_beat,
        )

    def _body_completions(self, word: str):
        return completions_for_word(
            word, patterns=self.project.patterns, instrument=self.instrument,
            midi_ref_names=midi_library.list_midi_library,
        )

    def accept(self):
        name = self.name_edit.text().strip() if self.name_edit is not None else ""
        if self.name_edit is not None and not name:
            QMessageBox.warning(self, tr("Nome mancante"), tr("Dai un nome al box prima di confermare."))
            return
        text = self.body_edit.toPlainText().strip()
        ok, msg = validate_track_text(text, self.project.patterns, default_octave=self.instrument.default_octave)
        if not ok:
            QMessageBox.critical(self, tr("Errore di sintassi"), tr("Correggi il box prima di confermare:\n{msg}", msg=msg))
            return
        self._result_name = name
        self._result_text = text
        self._stop_playback_on_exit()
        super().accept()

    def reject(self):
        self._stop_playback_on_exit()
        super().reject()

    def result_name(self) -> str:
        return getattr(self, "_result_name", "")

    def result_text(self) -> str:
        return getattr(self, "_result_text", "")

    def _stop_playback_on_exit(self):
        """Richiamato da accept()/reject() (Ok, Annulla, Esc - QDialog.done()
        nasconde il dialogo senza generare QCloseEvent, quindi closeEvent da
        solo non basta) oltre che da closeEvent (chiusura dalla X della
        finestra): senza fermarla qui, l'anteprima di Play continuerebbe a
        suonare in sottofondo anche a dialogo chiuso, senza alcun controllo
        piu' raggiungibile per fermarla."""
        self._play_highlight.stop()

    def closeEvent(self, event):
        self._stop_playback_on_exit()
        super().closeEvent(event)
