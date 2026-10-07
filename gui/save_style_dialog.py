"""
"Salva come stile del generatore" (vedi core.style_learn): da un box, da una
traccia o da un canale di un file della libreria MIDI, un nuovo stile per
Genera batteria / basso / accompagnamento / riff, salvato fra gli stili
personali (core.user_styles) e da li' proposto nei dialoghi dei generatori
con una ★ davanti al nome.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QMessageBox, QVBoxLayout,
)

from core import user_styles
from core.notation import NotationError
from core.rhythm_generate import extract_chords_from_track
from core.style_learn import describe_style, learn_drum_style, learn_line_style
from core.i18n import tr

METERS = ["4/4", "3/4", "2/4", "5/4", "6/8", "7/8", "9/8", "12/8"]


@dataclass
class StyleSource:
    """Una parte da cui ricavare lo stile."""
    label: str                  # es. "box 'Strofa'" o "canale 2 (Bass)"
    text: str
    is_percussion: bool
    polyphonic: bool = False    # lo strumento suona accordi (proposta: accompagnamento)
    is_bass: bool = False       # lo strumento e' un basso (proposta: basso)
    offset_beats: float = 0.0   # dove inizia 'text' nel tempo degli accordi
    default_octave: int = 4


def source_for_part(label: str, text: str, instrument, offset_beats: float = 0.0) -> StyleSource:
    """StyleSource di una traccia o di un box con lo strumento dato."""
    from core.instruments import gm_family_for_program
    is_bass = not instrument.is_percussion and gm_family_for_program(instrument.gm_program) == "Bassi"
    return StyleSource(label, text, instrument.is_percussion, polyphonic=instrument.polyphonic and not is_bass,
                       is_bass=is_bass, offset_beats=offset_beats, default_octave=instrument.default_octave)


def chord_sources_of(project, exclude_track_name: str) -> List[Tuple[str, str]]:
    """Le altre tracce (non audio, non percussive) che possono dare gli accordi."""
    return [(t.name, t.text) for t in project.tracks
            if t.name != exclude_track_name and not t.is_audio and not t.instrument.is_percussion]


class SaveStyleDialog(QDialog):
    """'sources': le parti fra cui scegliere; 'chord_sources': [(nome,
    testo)] delle parti che possono fornire gli accordi (tempo assoluto)."""

    def __init__(self, parent, sources: List[StyleSource], chord_sources: List[Tuple[str, str]],
                 patterns=None, meter: str = "4/4", midi_dir: Optional[str] = None):
        super().__init__(parent)
        self.setWindowTitle(tr("Salva come stile del generatore"))
        self.sources = sources
        self.patterns = patterns or {}
        self.midi_dir = midi_dir
        self._spec = None
        self._saved = None
        # Solo le parti che contengono davvero accordi.
        self.chord_sources = []
        for name, text in chord_sources:
            try:
                spans = extract_chords_from_track(text, self.patterns, midi_dir=midi_dir)
            except (NotationError, ValueError):
                continue
            if spans:
                self.chord_sources.append((name, spans))

        self.resize(560, 300)
        layout = QVBoxLayout(self)
        intro = QLabel(
            tr("Il disegno diventa un nuovo stile per i generatori: le battute piu' frequenti "
            "fanno il giro base, le altre le alternative (per la batteria, quella con i tom il fill); "
            "le note diventano gradi dell'accordo, cosi' lo stile segue qualunque giro."))
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form = QFormLayout()
        self.source_combo = QComboBox()
        for source in sources:
            self.source_combo.addItem(source.label)
        form.addRow(tr("Parte:"), self.source_combo)
        self.kind_combo = QComboBox()
        form.addRow(tr("Tipo:"), self.kind_combo)
        self.chords_combo = QComboBox()
        self.chords_combo.addItem(tr("(nessuno: la prima nota di ogni battuta fa da fondamentale)"), None)
        for name, _spans in self.chord_sources:
            self.chords_combo.addItem(name, name)
        if self.chord_sources:
            self.chords_combo.setCurrentIndex(1)
        self.chords_combo.setToolTip(
            tr("La parte con gli accordi su cui il disegno suonava: serve a capire quale nota e' "
            "la fondamentale, la terza, la quinta..."))
        form.addRow(tr("Accordi da:"), self.chords_combo)
        self.meter_combo = QComboBox()
        self.meter_combo.addItems(METERS if meter in METERS else [meter] + METERS)
        self.meter_combo.setCurrentText(meter)
        form.addRow(tr("Metrica:"), self.meter_combo)
        self.name_edit = QLineEdit()
        form.addRow(tr("Nome:"), self.name_edit)
        layout.addLayout(form)

        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self.source_combo.currentIndexChanged.connect(self._on_source_changed)
        self.kind_combo.currentIndexChanged.connect(self._relearn)
        self.chords_combo.currentIndexChanged.connect(self._relearn)
        self.meter_combo.currentIndexChanged.connect(self._relearn)
        self.name_edit.textChanged.connect(self._update_ok)
        self._on_source_changed()

    def _source(self) -> StyleSource:
        return self.sources[self.source_combo.currentIndex()]

    def _kind(self) -> str:
        return self.kind_combo.currentData()

    def _on_source_changed(self):
        source = self._source()
        self.kind_combo.blockSignals(True)
        self.kind_combo.clear()
        kinds = ["drums"] if source.is_percussion else ["bass", "comping", "riff"]
        for kind in kinds:
            self.kind_combo.addItem(user_styles.KIND_LABELS[kind], kind)
        guess = ("drums" if source.is_percussion else "bass" if source.is_bass
                 else "comping" if source.polyphonic else "riff")
        self.kind_combo.setCurrentIndex(self.kind_combo.findData(guess))
        self.kind_combo.blockSignals(False)
        if not self.name_edit.text().strip() or getattr(self, "_auto_name", None) == self.name_edit.text():
            self._auto_name = source.label.replace("'", "")
            self.name_edit.setText(self._auto_name)
        self._relearn()

    def _chords(self):
        name = self.chords_combo.currentData()
        return next((spans for n, spans in self.chord_sources if n == name), None)

    def _relearn(self):
        source, kind = self._source(), self._kind()
        self.chords_combo.setEnabled(kind != "drums")
        try:
            if kind == "drums":
                self._spec = learn_drum_style(source.text, self.patterns, meter=self.meter_combo.currentText(),
                                              midi_dir=self.midi_dir)
            else:
                self._spec = learn_line_style(source.text, kind, self.patterns, meter=self.meter_combo.currentText(),
                                              chords=self._chords(), offset_beats=source.offset_beats,
                                              default_octave=source.default_octave, midi_dir=self.midi_dir)
            self.summary_label.setText(describe_style(kind, self._spec))
        except (NotationError, ValueError) as e:
            self._spec = None
            self.summary_label.setText(f"<b style='color:#e05555'>✗ {e}</b>")
        self._update_ok()

    def _update_ok(self):
        self.button_box.button(QDialogButtonBox.Save).setEnabled(
            self._spec is not None and bool(self.name_edit.text().strip()))

    def accept(self):
        kind, name = self._kind(), self.name_edit.text().strip()
        if self._spec is None or not name:
            return
        if name in user_styles.user_style_names(kind):
            answer = QMessageBox.question(
                self, tr("Stile gia' esistente"),
                tr("Esiste gia' uno stile «{name}» ({0}). Sostituirlo?", user_styles.KIND_LABELS[kind], name=name))
            if answer != QMessageBox.Yes:
                return
        user_styles.save_user_style(kind, name, self._spec)
        self._saved = (kind, name)
        super().accept()

    def saved_style(self) -> Optional[Tuple[str, str]]:
        """(tipo, nome) dello stile salvato, o None."""
        return self._saved


class UserStylesDialog(QDialog):
    """Elenco degli stili personali, per rinominarli o eliminarli."""

    def __init__(self, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QHBoxLayout, QListWidget, QListWidgetItem, QPushButton
        self._item_cls = QListWidgetItem
        self.setWindowTitle(tr("Stili personali dei generatori"))
        self.resize(460, 360)
        layout = QVBoxLayout(self)
        intro = QLabel(
            tr("Stili salvati con «Salva come stile del generatore» (tasto destro su un box, "
            "menu Traccia o Libreria MIDI). Nei generatori compaiono con una ★."))
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget, 1)
        row = QHBoxLayout()
        self.rename_btn = QPushButton(tr("Rinomina..."))
        self.rename_btn.clicked.connect(self._rename)
        self.delete_btn = QPushButton(tr("Elimina"))
        self.delete_btn.clicked.connect(self._delete)
        row.addWidget(self.rename_btn)
        row.addWidget(self.delete_btn)
        row.addStretch(1)
        close = QDialogButtonBox(QDialogButtonBox.Close)
        close.rejected.connect(self.reject)
        row.addWidget(close)
        layout.addLayout(row)
        self._refresh()

    def _refresh(self):
        from PySide6.QtCore import Qt
        self.list_widget.clear()
        styles = user_styles.load_user_styles()
        for kind in user_styles.KINDS:
            for name in user_styles.user_style_names(kind):
                meter = styles[kind][name].get("meter", "4/4")
                item = self._item_cls(f"{user_styles.KIND_LABELS[kind]} — {name}  ({meter})")
                item.setData(Qt.UserRole, (kind, name))
                self.list_widget.addItem(item)
        has = self.list_widget.count() > 0
        if has:
            self.list_widget.setCurrentRow(0)
        self.rename_btn.setEnabled(has)
        self.delete_btn.setEnabled(has)

    def _selected(self):
        from PySide6.QtCore import Qt
        item = self.list_widget.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _rename(self):
        from PySide6.QtWidgets import QInputDialog
        selected = self._selected()
        if not selected:
            return
        kind, name = selected
        new, ok = QInputDialog.getText(self, tr("Rinomina stile"), tr("Nuovo nome:"), text=name)
        if not ok or not new.strip() or new.strip() == name:
            return
        try:
            user_styles.rename_user_style(kind, name, new)
        except ValueError as e:
            QMessageBox.warning(self, tr("Rinomina stile"), str(e))
            return
        self._refresh()

    def _delete(self):
        selected = self._selected()
        if not selected:
            return
        kind, name = selected
        if QMessageBox.question(self, tr("Elimina stile"), tr("Eliminare lo stile «{name}»?", name=name)) != QMessageBox.Yes:
            return
        user_styles.delete_user_style(kind, name)
        self._refresh()
