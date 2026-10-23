"""
"Arrangia il brano" (core.arrange): le sezioni della traccia degli accordi
con l'intensita' proposta dal loro nome (modificabile), gli stili delle
parti, la melodia a cui lasciare spazio, la modulazione e il finale; con OK
tutte le parti, un box per sezione, in tracce nuove, e i box degli accordi
trasposti dalla modulazione (un solo Ctrl+Z toglie tutto).
"""

import random

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHeaderView, QLabel, QMessageBox, QSpinBox, QTableWidget,
    QTableWidgetItem, QVBoxLayout,
)

from core.arrange import ArrangeOptions, arrange, song_sections
from core.i18n import tr
from core.instruments import get_instrument, list_instrument_names
from core.rhythm_generate import drum_styles_for_meter, extract_chords_from_track

from .rhythm_generate_dialog import BASS_STYLE_LABELS, COMPING_STYLE_LABELS, DRUM_STYLE_LABELS, project_bar_beats


def section_levels():
    return [("intro", tr("Intro (senza batteria e basso)")), ("light", tr("Leggera")), ("normal", tr("Normale")),
            ("build", tr("In crescendo")), ("full", tr("Piena")), ("outro", tr("Finale (leggera)")),
            ("stop", tr("Stop (tutti tacciono)")), ("break", tr("Break (un colpo d'insieme)"))]


def melody_tracks(project, exclude=None):
    """Le tracce di note di uno strumento monofonico (non percussioni) con
    delle note: le melodie a cui l'accompagnamento lascia spazio."""
    out = []
    for track in project.tracks:
        instrument = track.instrument
        if track.is_audio or track is exclude or instrument.polyphonic or instrument.is_percussion:
            continue
        if (track.text or "").strip() or track.clips:
            out.append(track)
    return out


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
        self.melody_combo = QComboBox()
        self.melody_combo.setToolTip(tr(
            "Nelle battute in cui questa melodia ha molte note l'accompagnamento suona solo sul primo tempo "
            "e a meta' battuta."))
        form.addRow(tr("Lascia spazio alla melodia di:"), self.melody_combo)
        self.modulation_combo = QComboBox()
        for value, label in ((0, tr("nessuna")), (1, tr("ultimo ritornello mezzo tono sopra")),
                             (2, tr("ultimo ritornello un tono sopra"))):
            self.modulation_combo.addItem(label, value)
        self.modulation_combo.setToolTip(tr(
            "L'ultimo ritornello e le sezioni dopo di lui salgono: si traspongono anche i loro box degli "
            "accordi."))
        form.addRow(tr("Modulazione:"), self.modulation_combo)
        self.ending_check = QCheckBox(tr("Finale con nota lunga e accordo tenuto"))
        self.ending_check.setChecked(True)
        self.ending_check.setToolTip(tr(
            "Nell'ultima battuta il basso tiene la fondamentale dell'ultimo accordo e l'accompagnamento "
            "tiene l'accordo, insieme al colpo finale della batteria."))
        self.rallentando_check = QCheckBox(tr("Rallentando"))
        self.rallentando_check.setChecked(True)
        self.rallentando_check.setToolTip(tr(
            "Nelle ultime una o due battute il tempo scende di un quarto, con un marcatore tempo= per beat."))
        self.ending_check.toggled.connect(self.rallentando_check.setEnabled)
        self.dynamics_check = QCheckBox(tr("Crescendo di frase"))
        self.dynamics_check.setChecked(True)
        self.dynamics_check.setToolTip(tr(
            "La dinamica sale lungo ogni frase di quattro battute, con un accento in piu' sul primo "
            "colpo di ogni ritornello."))
        for check in (self.ending_check, self.rallentando_check, self.dynamics_check):
            form.addRow("", check)
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
        current = self.melody_combo.currentData()
        self.melody_combo.clear()
        self.melody_combo.addItem(tr("nessuna"), None)
        for melody in melody_tracks(self.project, exclude=track):
            self.melody_combo.addItem(melody.name, melody.name)
        index = self.melody_combo.findData(current) if current else -1
        self.melody_combo.setCurrentIndex(index if index >= 0 else min(1, self.melody_combo.count() - 1))
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
                              variability=self.variability_spin.value() / 100.0, seed=random.randrange(1 << 30),
                              ending=self.ending_check.isChecked(), rallentando=self.rallentando_check.isChecked(),
                              phrase_dynamics=self.dynamics_check.isChecked(),
                              melody_track=self.melody_combo.currentData(),
                              modulation=self.modulation_combo.currentData())

    def accept(self):
        for row, section in enumerate(self.sections):
            section.intensity = self.table.cellWidget(row, 2).currentData()
        try:
            self._options = self.options()
            self._parts = arrange(self.project, self.sections, self._options, project_bar_beats(self.project) or 4.0,
                                  chord_octave=self.source_track().instrument.default_octave)
        except ValueError as e:
            QMessageBox.warning(self, tr("Arrangia il brano"), str(e))
            return
        super().accept()

    def parts(self):
        return self._parts

    def used_options(self) -> ArrangeOptions:
        """Le opzioni con cui si e' arrangiato (lo stesso seme)."""
        return getattr(self, "_options", None) or self.options()
