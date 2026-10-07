"""
Dialogo "Trasponi..." del menu tasto-destro su un box (gui.arrangement_view):
spinner semitoni + anteprima live, stesso schema "preview rigenerata ad ogni
modifica" di gui.rhythm_generate_dialog._GeneratedTrackDialogBase. La
trasposizione vera e propria e' core.notation.PitchRewriter, gia'
esistente e usata cosi' com'e' - nessuna nuova logica musicale qui.
"""

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QPlainTextEdit,
    QDialogButtonBox, QMessageBox,
)

from core.notation import PitchRewriter, rewrite_tokens, validate_track_text
from .highlighter import NotationHighlighter
from core.i18n import tr


class BoxTransposeDialog(QDialog):
    def __init__(self, parent, original_text: str, patterns, default_octave: int):
        super().__init__(parent)
        self.original_text = original_text
        self.patterns = patterns
        self.default_octave = default_octave
        self.setWindowTitle(tr("Trasponi box"))
        self.resize(520, 380)

        layout = QVBoxLayout(self)

        controls_row = QHBoxLayout()
        controls_row.addWidget(QLabel(tr("Semitoni:")))
        self.semitones_spin = QSpinBox()
        self.semitones_spin.setRange(-48, 48)
        self.semitones_spin.setValue(0)
        self.semitones_spin.valueChanged.connect(self._regenerate_preview)
        controls_row.addWidget(self.semitones_spin)
        controls_row.addStretch(1)
        layout.addLayout(controls_row)

        layout.addWidget(QLabel(tr("Anteprima:")))
        self.preview_edit = QPlainTextEdit()
        self.preview_edit.setFont(QFont("Monospace", 10))
        self.preview_edit.setReadOnly(True)
        self._highlighter = NotationHighlighter(self.preview_edit.document())
        layout.addWidget(self.preview_edit)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self._regenerate_preview()

    def _regenerate_preview(self):
        semitones = self.semitones_spin.value()
        # un trasportatore per testo: tiene il filo del modo relativo e della tonalita'
        text = rewrite_tokens(self.original_text, PitchRewriter(semitones, self.default_octave))
        self.preview_edit.setPlainText(text)

    def accept(self):
        text = self.preview_edit.toPlainText()
        ok, msg = validate_track_text(text, self.patterns, default_octave=self.default_octave)
        if not ok:
            QMessageBox.critical(self, tr("Errore di sintassi"), tr("Trasposizione non valida:\n{msg}", msg=msg))
            return
        self._result_text = text
        super().accept()

    def result_text(self) -> str:
        return getattr(self, "_result_text", self.original_text)
