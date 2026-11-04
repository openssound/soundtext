"""
"Ottava della traccia...": sposta di una o piu' ottave tutte le note di una
traccia (box e testo libero, con core.arrange.transpose_track: i pattern
richiamati prendono il suffisso +12/-12 e restano com'erano). Mentre si
sceglie dice da dove a dove vanno le note e, se la traccia suona con il
motore SFZ interno, quante ne resterebbero mute (core.sfz_coverage);
"Ottava consigliata" sceglie quella con meno note mute.
"""

import copy

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout

from core.arrange import transpose_track
from core.chords import midi_to_token
from core.i18n import tr
from core.sfz_coverage import sfz_path, silent_notes, track_notes
from .theme import good_text, warn_text

OCTAVES = 4         # fino a quante ottave in su o in giu'


class TrackOctaveDialog(QDialog):
    def __init__(self, parent, project, track):
        super().__init__(parent)
        self.project, self.track = project, track
        self.setWindowTitle(tr("Ottava della traccia «{name}»", name=track.name))
        layout = QVBoxLayout(self)
        intro = QLabel(tr("Sposta tutte le note della traccia, in tutti i box, di una o più ottave. I pattern "
                          "richiamati restano com'erano per le altre tracce."))
        intro.setWordWrap(True)
        layout.addWidget(intro)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("Ottave:")))
        self.octaves = QSpinBox()
        self.octaves.setRange(-OCTAVES, OCTAVES)
        self.octaves.valueChanged.connect(self._update)
        row.addWidget(self.octaves)
        self.best_btn = QPushButton(tr("Ottava consigliata"))
        self.best_btn.setToolTip(tr("Quella con meno note mute per lo strumento SFZ della traccia"))
        self.best_btn.clicked.connect(lambda: self.octaves.setValue(self.best_octave()))
        self.best_btn.setVisible(bool(sfz_path(track)))
        row.addWidget(self.best_btn)
        row.addStretch(1)
        layout.addLayout(row)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self._results = {}
        if sfz_path(track) and silent_notes(project, track) is not None:
            self.octaves.setValue(self.best_octave())
        self._update()

    def _preview(self, octaves: int):
        """(note, note mute) della traccia spostata di 'octaves' ottave."""
        if octaves not in self._results:
            moved = copy.deepcopy(self.track)
            if octaves:
                transpose_track(self.project, moved, 12 * octaves)
            try:
                notes = track_notes(self.project, moved)
            except Exception:                   # fuori dalle note possibili
                notes = None
            self._results[octaves] = (notes, silent_notes(self.project, moved) if notes else None)
        return self._results[octaves]

    def best_octave(self) -> int:
        """L'ottava con meno note mute (a parita', la piu' vicina a quella di ora)."""
        def cost(k):
            notes, silent = self._preview(k)
            if notes is None:
                return (float("inf"), abs(k))
            return (silent.silent if silent else 0, abs(k))
        return min(range(-OCTAVES, OCTAVES + 1), key=cost)

    def _update(self):
        notes, silent = self._preview(self.octaves.value())
        ok = notes is not None
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(ok and self.octaves.value() != 0)
        if not ok:
            self.status.setText(tr("Con questa ottava alcune note escono dalle note possibili."))
            self.status.setStyleSheet(f"color: {warn_text()};")
            return
        pitches = [n for n, _v in notes]
        text = tr("Le note vanno da {low} a {high}.", low=midi_to_token(min(pitches)),
                  high=midi_to_token(max(pitches))) if pitches else tr("La traccia non ha note.")
        color = ""
        if sfz_path(self.track) and pitches:
            if silent is None:
                text += " " + tr("Lo strumento SFZ le suona tutte.")
                color = good_text()
            else:
                text += " " + silent.message()
                color = warn_text()
        self.status.setText(text)
        self.status.setStyleSheet(f"color: {color};" if color else "")

    def semitones(self) -> int:
        return 12 * self.octaves.value()
