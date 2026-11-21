"""
«Un brano in 60 secondi» (core.quicksong): genere, atmosfera e durata, e un brano completo, scritto in box (uno per
sezione e per traccia), si ascolta e, con «Crea il brano», diventa il progetto. Con «Dettagli» si scelgono anche
tonalita', tempo, metrica, forma, organico, melodia, finale, modulazione, densita', un giro di accordi scritto a mano e
il seme: con le stesse scelte e lo stesso seme esce lo stesso brano, come sul telefono (SoundText Mobile).
"""

import random

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QSlider, QSpinBox, QVBoxLayout,
)

from core.i18n import tr
from core.playback import PlaybackEngine
from core.project_io import parse_project_text
from core.quicksong import quick_choices, quick_song


def _clock(seconds: float) -> str:
    seconds = int(round(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


class QuickSongDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Un brano in 60 secondi"))
        self.resize(560, 640)
        self.choices = quick_choices()
        self.song = None                   # l'ultimo brano composto (il dizionario di quick_song)
        self._seed = None                  # None: un seme nuovo a ogni brano
        self._playback = PlaybackEngine()

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr("Scegli un genere, un'atmosfera e una durata: il brano si scrive da solo, "
                                   "in sezioni che poi puoi cambiare.")))
        self.genre_list = QListWidget()
        self.genre_list.setAccessibleName(tr("Genere"))
        for genre in self.choices["genres"]:
            item = QListWidgetItem(genre["label"])
            item.setData(Qt.UserRole, genre["value"])
            self.genre_list.addItem(item)
        self.genre_list.setCurrentRow(0)
        self.genre_list.currentRowChanged.connect(self._genre_changed)
        layout.addWidget(self.genre_list, 1)

        form = QFormLayout()
        self.mood_combo = QComboBox()
        form.addRow(tr("Atmosfera:"), self.mood_combo)
        self.duration_combo = QComboBox()
        for d in self.choices["durations"]:
            self.duration_combo.addItem(d["label"], d["value"])
        self.duration_combo.setCurrentIndex(3)             # 1 minuto
        form.addRow(tr("Durata:"), self.duration_combo)
        layout.addLayout(form)

        self.detail_check = QCheckBox(tr("Dettagli"))
        self.detail_check.toggled.connect(lambda on: self.detail_box.setVisible(on))
        layout.addWidget(self.detail_check)
        self.detail_box = QGroupBox()
        detail = QFormLayout(self.detail_box)
        self.key_combo = QComboBox()
        self.key_combo.addItem(tr("della ricetta"), "")
        for key in self.choices["keys"]:
            for suffix, label in (("", key), ("m", key + "m")):
                self.key_combo.addItem(label, key + suffix)
        detail.addRow(tr("Tonalita':"), self.key_combo)
        self.bpm_spin = QSpinBox()
        self.bpm_spin.setRange(0, 240)
        self.bpm_spin.setSpecialValueText(tr("automatico"))
        detail.addRow(tr("Tempo (BPM):"), self.bpm_spin)
        self.meter_combo = self._combo(self.choices["meters"], tr("della ricetta"))
        detail.addRow(tr("Metrica:"), self.meter_combo)
        self.form_combo = self._combo([(f["value"], f["label"]) for f in self.choices["forms"]], tr("della ricetta"))
        detail.addRow(tr("Forma:"), self.form_combo)
        self.ensemble_combo = self._combo([(e["value"], e["label"]) for e in self.choices["ensembles"]], tr("della ricetta"))
        detail.addRow(tr("Organico:"), self.ensemble_combo)
        self.melody_combo = self._combo([(m["value"], m["label"]) for m in self.choices["melodies"]], tr("della ricetta"))
        detail.addRow(tr("Melodia:"), self.melody_combo)
        self.ending_combo = self._combo([(e["value"], e["label"]) for e in self.choices["endings"]], tr("della ricetta"))
        detail.addRow(tr("Finale:"), self.ending_combo)
        self.modulation_check = QCheckBox(tr("L'ultimo ritornello sale di un tono"))
        detail.addRow("", self.modulation_check)
        self.density = QSlider(Qt.Horizontal)
        self.density.setRange(0, 100)
        self.density.setValue(50)
        detail.addRow(tr("Densita' (piu' semplice - piu' ricco):"), self.density)
        self.loop_check = QCheckBox(tr("Un loop senza fine"))
        detail.addRow("", self.loop_check)
        self.compact_check = QCheckBox(tr("Testo compatto (battute e pattern)"))
        self.compact_check.setChecked(True)
        detail.addRow("", self.compact_check)
        self.chords_edit = QLineEdit()
        self.chords_edit.setPlaceholderText("Am F C G")
        detail.addRow(tr("Parto da un giro scritto:"), self.chords_edit)
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(0, 2 ** 31 - 1)
        self.seed_spin.setSpecialValueText(tr("nuovo ogni volta"))
        detail.addRow(tr("Seme:"), self.seed_spin)
        self.detail_box.setVisible(False)
        layout.addWidget(self.detail_box)

        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        self.summary.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.summary)

        row = QHBoxLayout()
        self.make_btn = QPushButton(tr("▶ Componi e ascolta"))
        self.make_btn.clicked.connect(lambda: self.compose(listen=True))
        self.again_btn = QPushButton(tr("Un'altra"))
        self.again_btn.setToolTip(tr("Un brano nuovo con le stesse scelte, con un altro seme."))
        self.again_btn.clicked.connect(self._another)
        self.surprise_btn = QPushButton(tr("Sorprendimi"))
        self.surprise_btn.setToolTip(tr("Una combinazione di genere e atmosfera scelta a caso."))
        self.surprise_btn.clicked.connect(self._surprise)
        self.stop_btn = QPushButton(tr("■ Ferma"))
        self.stop_btn.clicked.connect(self._playback.stop)
        for b in (self.make_btn, self.again_btn, self.surprise_btn, self.stop_btn):
            row.addWidget(b)
        layout.addLayout(row)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText(tr("Crea il brano"))
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self._genre_changed(0)

    # ---- campi

    @staticmethod
    def _combo(items, blank):
        combo = QComboBox()
        if blank is not None:
            combo.addItem(blank, "")
        for item in items:
            value, label = item if isinstance(item, tuple) else (item, item)
            combo.addItem(label, value)
        return combo

    def _genre(self) -> str:
        item = self.genre_list.currentItem()
        return item.data(Qt.UserRole) if item else "pop"

    def _genre_changed(self, _row):
        data = next(g for g in self.choices["genres"] if g["value"] == self._genre())
        labels = {m["value"]: m["label"] for m in self.choices["moods"]}
        previous = self.mood_combo.currentData()
        self.mood_combo.clear()
        for mood in data["moods"]:
            self.mood_combo.addItem(labels[mood], mood)
        i = self.mood_combo.findData(previous)
        self.mood_combo.setCurrentIndex(max(0, i))

    def options(self) -> dict:
        """Le scelte per core.quicksong.quick_song."""
        o = {"genre": self._genre(), "mood": self.mood_combo.currentData(), "duration": self.duration_combo.currentData()}
        self._seed = None
        if self.detail_check.isChecked():
            if self.key_combo.currentData():
                o["key"] = self.key_combo.currentData()
            if self.bpm_spin.value():
                o["bpm"] = self.bpm_spin.value()
            for name, combo in (("meter", self.meter_combo), ("form", self.form_combo), ("ensemble", self.ensemble_combo),
                                ("melody", self.melody_combo), ("ending", self.ending_combo)):
                if combo.currentData():
                    o[name] = combo.currentData()
            o["modulation"] = self.modulation_check.isChecked()
            o["density"] = self.density.value() / 100.0
            o["loop"] = self.loop_check.isChecked()
            if self.chords_edit.text().strip():
                o["chords"] = self.chords_edit.text().strip()
            if self.seed_spin.value():
                self._seed = self.seed_spin.value()
        if not self.compact_check.isChecked():
            o["compact"] = False
        o["seed"] = self._seed if self._seed is not None else random.randrange(2 ** 31)
        return o

    # ---- comporre e ascoltare

    def compose(self, listen: bool = True):
        self._playback.stop()
        try:
            self.song = quick_song(self.options())
        except (ValueError, KeyError) as e:
            self.song = None
            self.summary.setText("✗ " + str(e))
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)
            return
        s = self.song
        parts = [s["name"], _clock(s["seconds"]), s["key"], f"{s['bpm']} BPM", s["meter"], tr("{n} battute", n=s["bars"])]
        text = " · ".join(str(p) for p in parts) + (f"\n{s['fallback']}" if s.get("fallback") else "")
        self.summary.setText(text + "\n" + tr("Seme: {seed}", seed=s["seed"]))
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(True)
        if listen:
            self._listen()

    def _listen(self):
        if not self.song:
            return
        try:
            project = parse_project_text(self.song["text"], self.song["name"])
        except Exception as e:                         # un brano che non si legge e' un errore nostro: lo si dice
            QMessageBox.critical(self, tr("Un brano in 60 secondi"), str(e))
            return
        self._playback.play(project)

    def _another(self):
        self._seed = None
        self.seed_spin.setValue(0)
        self.compose(listen=True)

    def _surprise(self):
        genres = self.choices["genres"]
        data = random.choice(genres)
        self.genre_list.setCurrentRow(genres.index(data))
        self.mood_combo.setCurrentIndex(random.randrange(self.mood_combo.count()))
        self.duration_combo.setCurrentIndex(random.randrange(self.duration_combo.count()))
        self._seed = None
        self.seed_spin.setValue(0)
        self.compose(listen=True)

    def done(self, result):
        self._playback.stop()                          # l'ascolto non continua dopo Ok o Annulla
        super().done(result)
