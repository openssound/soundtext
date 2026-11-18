"""
Tonalita' del brano...: si alza o si abbassa tutto il brano di semitoni, per
esempio per trovare la tonalita' giusta per chi canta. Si ascolta dal punto in
cui si e', e il brano cambia solo confermando (core.song_key).
"""

from typing import Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout,
)

from core.i18n import tr
from core.model import Project
from core.song_key import MAX_SEMITONES, transposed_key, transposed_song, warnings_for
from .theme import BAD, warn_text


class SongKeyDialog(QDialog):
    def __init__(self, parent, project: Project, playback, start_beat: float = 0.0):
        super().__init__(parent)
        self.setWindowTitle(tr("Tonalità del brano"))
        self.setMinimumWidth(460)
        self.project, self.playback, self.start_beat = project, playback, start_beat
        self.result_song: Optional[Project] = None
        self._results = {}
        layout = QVBoxLayout(self)
        intro = QLabel(tr("Sposta tutto il brano di semitoni. Ascolta le prove: il brano cambia solo con OK."))
        intro.setWordWrap(True)
        layout.addWidget(intro)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("Semitoni:")))
        self.down_btn = QPushButton("−")
        self.down_btn.setFixedWidth(36)
        self.down_btn.clicked.connect(lambda: self.semitones.stepDown())
        row.addWidget(self.down_btn)
        self.semitones = QSpinBox()
        self.semitones.setRange(-MAX_SEMITONES, MAX_SEMITONES)
        self.semitones.valueChanged.connect(self._update)
        row.addWidget(self.semitones)
        self.up_btn = QPushButton("+")
        self.up_btn.setFixedWidth(36)
        self.up_btn.clicked.connect(lambda: self.semitones.stepUp())
        row.addWidget(self.up_btn)
        row.addStretch(1)
        layout.addLayout(row)
        self.key_label = QLabel()
        font = self.key_label.font()
        font.setPointSize(font.pointSize() + 3)
        font.setBold(True)
        self.key_label.setFont(font)
        layout.addWidget(self.key_label)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        listen = QHBoxLayout()
        self.play_btn = QPushButton(tr("▶ Ascolta"))
        self.play_btn.setToolTip(tr("Suona il brano in questa tonalità dal punto in cui eri"))
        self.play_btn.clicked.connect(self.play)
        self.stop_btn = QPushButton(tr("■ Stop"))
        self.stop_btn.clicked.connect(self.playback.stop)
        listen.addWidget(self.play_btn)
        listen.addWidget(self.stop_btn)
        listen.addStretch(1)
        layout.addLayout(listen)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        # cambiando tonalita' mentre suona, si riascolta quella nuova
        self._replay = QTimer(self)
        self._replay.setSingleShot(True)
        self._replay.setInterval(400)
        self._replay.timeout.connect(self.play)
        self._update()

    def _song(self, semitones: int) -> Project:
        if semitones not in self._results:
            try:
                self._results[semitones] = transposed_song(self.project, semitones) if semitones else self.project
            except ValueError as e:
                self._results[semitones] = e
        return self._results[semitones]

    def _key_text(self, semitones: int) -> str:
        key = self.project.key
        if not key:
            return tr("{n} semitoni", n=f"{semitones:+d}") if semitones else tr("Tonalità di partenza")
        return f"{key} → {transposed_key(key, semitones)}" if semitones else key

    def _update(self):
        semitones = self.semitones.value()
        self.key_label.setText(self._key_text(semitones))
        song = self._song(semitones)
        failed = isinstance(song, ValueError)
        if failed:
            self.status.setText(str(song))
            self.status.setStyleSheet(f"color: {BAD};")
        else:
            warnings = warnings_for(self.project, song, semitones) if semitones else []
            self.status.setText("\n".join(warnings))
            self.status.setStyleSheet(f"color: {warn_text()};")
        self.play_btn.setEnabled(not failed)
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(not failed and semitones != 0)
        if self.playback.is_playing() and not failed:
            self._replay.start()

    def play(self):
        song = self._song(self.semitones.value())
        if not isinstance(song, ValueError):
            self.playback.stop()
            self.playback.play(song, start_offset_beats=self.start_beat)

    def accept(self):
        song = self._song(self.semitones.value())
        if isinstance(song, ValueError):
            return
        self.result_song = song
        self._stop()
        super().accept()

    def reject(self):
        self._stop()
        super().reject()

    def _stop(self):
        self._replay.stop()
        if self.playback.is_playing():
            self.playback.stop()
