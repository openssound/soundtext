"""
Riarmonizza un giro gia' scritto (un box di soli accordi): le stesse
trasformazioni del giro armonico generato (core.rhythm_generate.
reharmonize_text) con un cursore "quanto ricco" e un'altra versione a ogni
clic. Il risultato si vede prima di sostituire il box.
"""

import random

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QSlider,
    QVBoxLayout,
)

from core.i18n import tr
from core.key_detect import detect_key_of_text
from core.rhythm_generate import reharmonize_text

from .rhythm_generate_dialog import project_bar_beats

KEYS = ["C", "G", "D", "A", "E", "B", "F#", "F", "Bb", "Eb", "Ab", "Db",
        "Am", "Em", "Bm", "F#m", "C#m", "G#m", "Dm", "Gm", "Cm", "Fm", "Bbm", "Ebm"]


def can_reharmonize(text: str, patterns) -> bool:
    try:
        reharmonize_text(text, patterns, "C", 0.0)
        return True
    except Exception:       # testo non valido (NotationError) o con note: non si offre
        return False


class ReharmonizeDialog(QDialog):
    def __init__(self, parent, project, text: str, box_name: str):
        super().__init__(parent)
        self.setWindowTitle(tr("Riarmonizza '{name}'", name=box_name))
        self.project = project
        self.source = text
        self._seed = random.randrange(1 << 30)
        self._result = None
        layout = QVBoxLayout(self)

        row = QHBoxLayout()
        row.addWidget(QLabel(tr("Tonalita':")))
        self.key_combo = QComboBox()
        self.key_combo.setEditable(True)
        self.key_combo.addItems(KEYS)
        key = project.key or detect_key_of_text(text, project.patterns) or "C"
        self.key_combo.setCurrentText(key)
        self.key_combo.currentTextChanged.connect(self._update)
        row.addWidget(self.key_combo)
        row.addSpacing(12)
        row.addWidget(QLabel(tr("Quanto ricco:")))
        self.richness = QSlider(Qt.Horizontal)
        self.richness.setRange(0, 100)
        self.richness.setValue(50)
        self.richness.setToolTip(tr(
            "0 = il giro com'e'. Salendo: settime e none, dominanti secondarie e II-V verso l'accordo "
            "dopo, sostituti di tritono, iv minore prima del I."))
        self.richness.valueChanged.connect(self._update)
        row.addWidget(self.richness, 1)
        self.other_btn = QPushButton(tr("Altra versione"))
        self.other_btn.clicked.connect(self._reroll)
        row.addWidget(self.other_btn)
        layout.addLayout(row)

        layout.addWidget(QLabel(tr("Prima:")))
        before = QPlainTextEdit(text)
        before.setReadOnly(True)
        before.setMaximumHeight(70)
        layout.addWidget(before)
        layout.addWidget(QLabel(tr("Dopo:")))
        self.after = QPlainTextEdit()
        self.after.setReadOnly(True)
        self.after.setMaximumHeight(70)
        layout.addWidget(self.after)
        self.error_label = QLabel()
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.resize(640, self.sizeHint().height())
        self._update()

    def _reroll(self):
        self._seed = random.randrange(1 << 30)
        self._update()

    def _update(self, *_args):
        try:
            self._result = reharmonize_text(self.source, self.project.patterns, self.key_combo.currentText().strip(),
                                            self.richness.value() / 100.0, seed=self._seed,
                                            bar_beats=project_bar_beats(self.project) or 4.0)
            self.error_label.setText("")
        except ValueError as e:
            self._result = None
            self.error_label.setText(str(e))
        self.after.setPlainText(self._result or "")
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(bool(self._result))

    def result_text(self):
        return self._result
