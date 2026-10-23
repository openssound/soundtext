"""
Armonizza una melodia (core.harmonize): dal box, dalla traccia o dalla clip
audio scelta, gli accordi in tre versioni (semplice, diatonica, ricca), un
accordo per battuta o per mezza battuta; il risultato va in una traccia di
accordi nuova, allineata alla melodia.
"""

import random

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout,
)

from core.harmonize import VERSIONS, harmonize, melody_key, melody_notes
from core.i18n import tr

from .reharmonize_dialog import KEYS
from .rhythm_generate_dialog import project_bar_beats


def version_labels():
    return {"simple": tr("Semplice (I, IV, V)"), "diatonic": tr("Diatonica (tutti i gradi)"),
            "rich": tr("Ricca (settime, dominanti secondarie)")}


class HarmonizeDialog(QDialog):
    def __init__(self, parent, project, melody_text: str, source_name: str):
        super().__init__(parent)
        self.setWindowTitle(tr("Armonizza '{name}'", name=source_name))
        self.project = project
        self.notes = melody_notes(melody_text, project.patterns)
        self._seed = random.randrange(1 << 30)
        self._result = None
        self.bar_beats = project_bar_beats(project) or 4.0
        layout = QVBoxLayout(self)

        row = QHBoxLayout()
        row.addWidget(QLabel(tr("Versione:")))
        self.version_combo = QComboBox()
        for key, label in version_labels().items():
            self.version_combo.addItem(label, key)
        self.version_combo.setCurrentIndex(1)
        self.version_combo.currentIndexChanged.connect(self._update)
        row.addWidget(self.version_combo)
        row.addSpacing(12)
        row.addWidget(QLabel(tr("Un accordo ogni:")))
        self.step_combo = QComboBox()
        self.step_combo.addItem(tr("battuta"), 1.0)
        self.step_combo.addItem(tr("mezza battuta"), 0.5)
        self.step_combo.currentIndexChanged.connect(self._update)
        row.addWidget(self.step_combo)
        row.addSpacing(12)
        row.addWidget(QLabel(tr("Tonalita':")))
        self.key_combo = QComboBox()
        self.key_combo.setEditable(True)
        self.key_combo.addItems(KEYS)
        self.key_combo.setCurrentText(melody_key(self.notes) if self.notes else (project.key or "C"))
        self.key_combo.currentTextChanged.connect(self._update)
        row.addWidget(self.key_combo)
        self.other_btn = QPushButton(tr("Altra versione"))
        self.other_btn.setToolTip(tr("Solo per la versione ricca: altre dominanti secondarie e sostituzioni."))
        self.other_btn.clicked.connect(self._reroll)
        row.addWidget(self.other_btn)
        layout.addLayout(row)

        layout.addWidget(QLabel(tr("Accordi proposti (la traccia nuova si puo' poi modificare):")))
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMaximumHeight(90)
        layout.addWidget(self.preview)
        self.error_label = QLabel()
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText(tr("Crea la traccia di accordi"))
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.resize(680, self.sizeHint().height())
        self._update()

    def version(self) -> str:
        return self.version_combo.currentData()

    def _reroll(self):
        self._seed = random.randrange(1 << 30)
        self._update()

    def _update(self, *_args):
        self.other_btn.setEnabled(self.version() == "rich")
        try:
            self._result = harmonize(self.notes, self.key_combo.currentText().strip() or "C", self.version(),
                                     step_beats=self.bar_beats * self.step_combo.currentData(),
                                     bar_beats=self.bar_beats, seed=self._seed)
            self.error_label.setText("")
        except ValueError as e:
            self._result = None
            self.error_label.setText(str(e))
        self.preview.setPlainText(self._result or "")
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(bool(self._result))

    def result_text(self):
        return self._result


def add_harmony_track(view, source_name: str, text: str, start_beat: float) -> str:
    """Una traccia di accordi nuova (Piano) con un box all'inizio della
    melodia; ritorna il suo nome."""
    from core.model import Clip
    project = view.host.project
    base = tr("Accordi di {name}", name=source_name)
    name, n = base, 2
    while project.find_track(name) is not None:
        name, n = f"{base} {n}", n + 1
    track = project.add_track(name, "Piano", "")
    track.clips = [Clip(name=tr("Armonia"), text=text, start_beat=round(start_beat, 6))]
    view.on_clip_changed(name)
    if hasattr(view.host, "refresh_mixer"):
        view.host.refresh_mixer()
    return name
