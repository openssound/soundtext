"""
"Arrangia il brano" (core.arrange): le sezioni della traccia degli accordi
con l'intensita' proposta dal loro nome (modificabile), gli stili delle
parti; con OK tutte le parti, un box per sezione, in tracce nuove (un solo
Ctrl+Z le toglie).
"""

import random

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHeaderView, QLabel, QMessageBox, QSpinBox, QTableWidget,
    QTableWidgetItem, QVBoxLayout,
)

from core.arrange import ArrangeOptions, arrange, song_sections
from core.i18n import tr
from core.instruments import get_instrument, list_instrument_names
from core.rhythm_generate import drum_styles_for_meter, extract_chords_from_track

from .rhythm_generate_dialog import BASS_STYLE_LABELS, COMPING_STYLE_LABELS, DRUM_STYLE_LABELS, project_bar_beats


def section_levels():
    return [("intro", tr("Intro (senza batteria e basso)")), ("light", tr("Leggera")), ("normal", tr("Normale")),
            ("build", tr("In crescendo")), ("full", tr("Piena")), ("outro", tr("Finale (leggera)"))]


def chord_tracks(project):
    """Le tracce di note con box che contengono accordi: le sezioni."""
    out = []
    for track in project.tracks:
        if track.is_audio or not track.clips:
            continue
        try:
            if any(extract_chords_from_track(c.text, project.patterns) for c in track.clips):
                out.append(track)
        except Exception:
            continue
    return out


class ArrangeDialog(QDialog):
    def __init__(self, parent, project):
        super().__init__(parent)
        self.setWindowTitle(tr("Arrangia il brano"))
        self.project = project
        self.tracks = chord_tracks(project)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr("Le sezioni sono i box della traccia degli accordi; l'intensita' viene dal loro "
                                   "nome (Intro, Strofa, Pre-ritornello, Ritornello, Ponte, Finale...).")))
        form = QFormLayout()
        self.source_combo = QComboBox()
        for track in self.tracks:
            self.source_combo.addItem(track.name)
        self.source_combo.currentIndexChanged.connect(self._fill_sections)
        form.addRow(tr("Accordi e sezioni da:"), self.source_combo)

        self.drum_combo = QComboBox()
        self.drum_combo.addItem(tr("nessuna"), None)
        allowed = set(drum_styles_for_meter(project.time_sig))
        for value, label in DRUM_STYLE_LABELS:
            if value in allowed:
                self.drum_combo.addItem(label, value)
        self.drum_combo.setCurrentIndex(1 if self.drum_combo.count() > 1 else 0)
        form.addRow(tr("Batteria:"), self.drum_combo)
        self.bass_combo = QComboBox()
        self.bass_combo.addItem(tr("nessuno"), None)
        for value, label in BASS_STYLE_LABELS:
            self.bass_combo.addItem(label, value)
        self.bass_combo.setCurrentIndex(1)
        form.addRow(tr("Basso:"), self.bass_combo)
        self.comp_combo = QComboBox()
        self.comp_combo.addItem(tr("nessuno"), None)
        for value, label in COMPING_STYLE_LABELS:
            self.comp_combo.addItem(label, value)
        self.comp_combo.setCurrentIndex(1)
        form.addRow(tr("Accompagnamento:"), self.comp_combo)
        self.comp_instrument = QComboBox()
        names = [n for n in list_instrument_names() if get_instrument(n).polyphonic and not get_instrument(n).is_percussion]
        self.comp_instrument.addItems(names)
        if "Piano" in names:
            self.comp_instrument.setCurrentText("Piano")
        form.addRow(tr("Strumento dell'accompagnamento:"), self.comp_instrument)
        self.variability_spin = QSpinBox()
        self.variability_spin.setRange(0, 100)
        self.variability_spin.setValue(30)
        self.variability_spin.setSuffix(" %")
        form.addRow(tr("Variabilita':"), self.variability_spin)
        layout.addLayout(form)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([tr("Sezione"), tr("Battute"), tr("Intensita'")])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText(tr("Arrangia"))
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.resize(620, 520)
        self._parts = None
        self._fill_sections()

    def source_track(self):
        return self.tracks[self.source_combo.currentIndex()] if self.tracks else None

    def _fill_sections(self, *_args):
        track = self.source_track()
        self.sections = song_sections(self.project, track) if track is not None else []
        bar_beats = project_bar_beats(self.project) or 4.0
        self.table.setRowCount(len(self.sections))
        for row, section in enumerate(self.sections):
            name = QTableWidgetItem(section.name)
            name.setFlags(name.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, name)
            bars = QTableWidgetItem(f"{section.length_beats / bar_beats:g}")
            bars.setFlags(bars.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 1, bars)
            combo = QComboBox()
            for value, label in section_levels():
                combo.addItem(label, value)
            combo.setCurrentIndex(max(0, combo.findData(section.intensity)))
            self.table.setCellWidget(row, 2, combo)
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(bool(self.sections))

    def options(self) -> ArrangeOptions:
        return ArrangeOptions(drum_style=self.drum_combo.currentData(), bass_style=self.bass_combo.currentData(),
                              comping_style=self.comp_combo.currentData(),
                              comping_instrument=self.comp_instrument.currentText(),
                              variability=self.variability_spin.value() / 100.0, seed=random.randrange(1 << 30))

    def accept(self):
        for row, section in enumerate(self.sections):
            section.intensity = self.table.cellWidget(row, 2).currentData()
        try:
            self._parts = arrange(self.project, self.sections, self.options(), project_bar_beats(self.project) or 4.0)
        except ValueError as e:
            QMessageBox.warning(self, tr("Arrangia il brano"), str(e))
            return
        super().accept()

    def parts(self):
        return self._parts
