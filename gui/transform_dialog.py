"""
Finestra Trasforma...: si sceglie una funzione sui pattern, si regolano gli
argomenti, si guarda e si ascolta prima e dopo, e il programma scrive il testo
del richiamo. Le funzioni aggiunte alla catena si possono riordinare e togliere.
La funzione scelta e non ancora aggiunta fa gia' parte del risultato: si vede
subito che cosa fa. Qui sta anche la finestrella Arpeggia...
"""

from typing import Callable, List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QGridLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QListWidget, QMessageBox, QPushButton, QSpinBox, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)
from st_language.transform import format_reference, list_transforms, parse_reference

from core.completion import arpeggio_kinds
from core.i18n import current_language, tr
from core.instruments import get_instrument
from core.model import Project, copy_synth
from core.notation import NotationError, Pattern, tokenize
from core.transform_preview import ReferencePoint, expansion, preview_project
from .theme import BAD, warn_text
from .transform_preview import ScoreSnippet

MAX_CHAIN_HINT = 3
GRIDS = ("", "4", "8", "16")


def argument_label(name: str, argument: str) -> str:
    """L'etichetta di un argomento: in st_language ha solo il nome breve."""
    return {
        ("octave", "n"): tr("Ottave"),
        ("invert", "asse"): tr("Asse (una nota, se vuoi)"),
        ("step", "n"): tr("Gradi"),
        ("augment", "k"): tr("Fattore"),
        ("diminish", "k"): tr("Fattore"),
        ("sequence", "n"): tr("Ripetizioni"),
        ("sequence", "passo"): tr("Gradi a ogni passo"),
        ("vel", "x"): tr("Velocity (+10, 80, mf)"),
        ("canon", "ritardo"): tr("Ritardo"),
        ("canon", "int"): tr("Intervallo"),
        ("canon", "voci"): tr("Voci"),
        ("arpeggio", "tipo"): tr("Tipo"),
        ("arpeggio", "griglia"): tr("Griglia"),
    }.get((name, argument), argument)


def _grid_label(grid: str) -> str:
    return grid or tr("quella in vigore")


class TransformDialog(QDialog):
    """token: il richiamo da cui si parte, se c'e' (allora si puo' sostituire);
    pattern: il pattern da cui si parte altrimenti. Dopo exec(): result_token e'
    il testo da scrivere al posto del richiamo, created_pattern il pattern nuovo."""

    def __init__(self, parent, project: Project, playback, instrument_name: str, track=None, token: str = "",
                 pattern: str = "", point: Optional[ReferencePoint] = None):
        super().__init__(parent)
        self.setWindowTitle(tr("Trasforma"))
        self.resize(980, 620)
        self.project, self.playback, self.track = project, playback, track
        self.instrument_name = instrument_name
        self.point = point or ReferencePoint()
        self.result_token = ""
        self.created_pattern = ""
        self.freeze = False           # il richiamo va scritto nota per nota
        self.mult = 1
        self.chain: List[str] = []
        self._transforms = {t["name"]: t for t in list_transforms()}
        self._controls: List[QWidget] = []
        self._can_replace = bool(token)
        if token:
            reference = parse_reference(token)
            self.mult, pattern = reference.mult, reference.pattern
            self.chain = [token[step.start:step.end] for step in reference.steps]
        self._build(pattern)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(150)
        self._timer.timeout.connect(self._refresh)
        self._refresh_chain()
        self._refresh()

    # ------------------------------------------------------------ costruzione
    def _build(self, pattern: str):
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel(tr("Pattern:")))
        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems(sorted(self.project.patterns))
        if pattern:
            self.pattern_combo.setCurrentText(pattern)
        self.pattern_combo.currentTextChanged.connect(self._schedule)
        top.addWidget(self.pattern_combo)
        top.addStretch(1)
        layout.addLayout(top)

        columns = QHBoxLayout()
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setMinimumWidth(270)
        italian = current_language() == "it"
        groups = {}
        for name, transform in self._transforms.items():
            parent = groups.get(transform["group"])
            if parent is None:
                parent = groups[transform["group"]] = QTreeWidgetItem(self.tree, [transform["group_label"]])
                parent.setFlags(Qt.ItemIsEnabled)
                parent.setExpanded(True)
            item = QTreeWidgetItem(parent, [f"{transform['alias'] if italian else name}  —  {transform['help']}"])
            item.setToolTip(0, transform["help"])
            item.setData(0, Qt.UserRole, name)
        self.tree.currentItemChanged.connect(self._on_function)
        columns.addWidget(self.tree, 3)

        middle = QVBoxLayout()
        self.arguments = QWidget()
        self.form = QFormLayout(self.arguments)
        middle.addWidget(self.arguments)
        self.add_btn = QPushButton(tr("Aggiungi alla catena"))
        self.add_btn.clicked.connect(self._add_to_chain)
        middle.addWidget(self.add_btn)
        middle.addWidget(QLabel(tr("Catena:")))
        self.chain_list = QListWidget()
        middle.addWidget(self.chain_list, 1)
        row = QHBoxLayout()
        for text, tip, handler in (("↑", tr("Prima"), lambda: self._move(-1)), ("↓", tr("Dopo"), lambda: self._move(1)),
                                   ("✕", tr("Togli dalla catena"), self._remove)):
            button = QPushButton(text)
            button.setToolTip(tip)
            button.clicked.connect(handler)
            row.addWidget(button)
        middle.addLayout(row)
        self.hint = QLabel(tr("Per leggerlo meglio, crea un pattern intermedio."))
        self.hint.setWordWrap(True)
        middle.addWidget(self.hint)
        columns.addLayout(middle, 2)

        right = QGridLayout()
        self.before = ScoreSnippet()
        self.after = ScoreSnippet()
        self.play_before = QPushButton(tr("▶ Prima"))
        self.play_after = QPushButton(tr("▶ Dopo"))
        self.play_before.clicked.connect(lambda: self._play(self._before_project()))
        self.play_after.clicked.connect(lambda: self._play(self._after_project()))
        right.addWidget(self.play_before, 0, 0)
        right.addWidget(self.before, 1, 0)
        right.addWidget(self.play_after, 2, 0)
        right.addWidget(self.after, 3, 0)
        right.setRowStretch(1, 1)
        right.setRowStretch(3, 1)
        columns.addLayout(right, 4)
        layout.addLayout(columns, 1)

        self.text = QLineEdit()
        self.text.setReadOnly(True)
        layout.addWidget(self.text)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.replace_btn = QPushButton(tr("Sostituisci"))
        self.replace_btn.setVisible(self._can_replace)
        self.replace_btn.clicked.connect(self._replace)
        self.freeze_btn = QPushButton(tr("Scrivi le note"))
        self.freeze_btn.setToolTip(tr("Scrive per esteso le note del risultato, da ritoccare a mano."))
        self.freeze_btn.setVisible(self._can_replace)
        self.freeze_btn.clicked.connect(self._write_notes)
        self.create_btn = QPushButton(tr("Crea pattern..."))
        self.create_btn.clicked.connect(self._create_pattern)
        cancel = QPushButton(tr("Annulla"))
        cancel.clicked.connect(self.reject)
        for button in (self.replace_btn, self.freeze_btn, self.create_btn, cancel):
            buttons.addWidget(button)
        layout.addLayout(buttons)

    # ------------------------------------------------------------ la funzione scelta
    def current_function(self) -> str:
        item = self.tree.currentItem()
        return item.data(0, Qt.UserRole) or "" if item is not None else ""

    def select_function(self, name: str):
        for i in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(i)
            for k in range(group.childCount()):
                if group.child(k).data(0, Qt.UserRole) == name:
                    self.tree.setCurrentItem(group.child(k))
                    return

    def _on_function(self, *_args):
        while self.form.rowCount():
            self.form.removeRow(0)
        self._controls = []
        name = self.current_function()
        for argument in self._transforms[name]["arguments"] if name else ():
            control = self._control(argument)
            self._controls.append(control)
            self.form.addRow(argument_label(name, argument["name"]), control)
        self._schedule()

    def _control(self, argument: dict) -> QWidget:
        kind, value = argument["type"], argument["default"]
        if kind == "integer":
            control = QSpinBox()
            control.setRange(argument["min"], argument["max"])
            control.setValue(value)
            control.valueChanged.connect(self._schedule)
        elif kind == "factor":
            control = QDoubleSpinBox()
            control.setRange(0.25, 16.0)
            control.setSingleStep(0.25)
            control.setValue(value)
            control.valueChanged.connect(self._schedule)
        elif kind in ("word", "grid"):
            control = QComboBox()
            for choice in (arpeggio_kinds() if kind == "word" else GRIDS):
                control.addItem(choice if kind == "word" else _grid_label(choice), choice)
            control.currentIndexChanged.connect(self._schedule)
        else:
            control = QLineEdit(str(value or ""))
            control.textChanged.connect(self._schedule)
        return control

    @staticmethod
    def _value(control) -> str:
        if isinstance(control, QSpinBox):
            return str(control.value())
        if isinstance(control, QDoubleSpinBox):
            return f"{control.value():g}"
        if isinstance(control, QComboBox):
            return control.currentData()
        return control.text().strip()

    def current_call(self) -> str:
        """La funzione scelta come si scrive ('.sequence(3,-1)'), '' se non ce n'e'."""
        name = self.current_function()
        if not name:
            return ""
        values = [self._value(c) for c in self._controls]
        while values and not values[-1]:
            values.pop()
        return f".{name}({','.join(values)})" if values else f".{name}"

    # ------------------------------------------------------------ la catena
    def _add_to_chain(self):
        call = self.current_call()
        if call:
            self.chain.append(call)
            self.tree.setCurrentItem(None)
            self._refresh_chain()
            self._schedule()

    def _move(self, delta: int):
        row = self.chain_list.currentRow()
        if row >= 0 and 0 <= row + delta < len(self.chain):
            self.chain.insert(row + delta, self.chain.pop(row))
            self._refresh_chain()
            self.chain_list.setCurrentRow(row + delta)
            self._schedule()

    def _remove(self):
        row = self.chain_list.currentRow()
        if row >= 0:
            del self.chain[row]
            self._refresh_chain()
            self._schedule()

    def _refresh_chain(self):
        self.chain_list.clear()
        self.chain_list.addItems(self.chain)
        self.hint.setVisible(len(self.chain) + bool(self.current_function()) > MAX_CHAIN_HINT)
        made_voices = any(self._transforms.get(call[1:].partition("(")[0], {}).get("makes_voices")
                          for call in self.chain if call.startswith("."))
        for i in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(i)
            for k in range(group.childCount()):
                item = group.child(k)
                single = self._transforms[item.data(0, Qt.UserRole)]["single_voice"]
                item.setDisabled(made_voices and single)

    # ------------------------------------------------------------ il risultato
    def base_token(self) -> str:
        return "%" + self.pattern_combo.currentText()

    def token(self) -> str:
        """Il richiamo come si scrive, nella lingua dell'interfaccia. Solleva
        NotationError se non e' valido."""
        written = (str(self.mult) if self.mult > 1 else "") + self.base_token() + "".join(self.chain) + self.current_call()
        return format_reference(parse_reference(written), italian=current_language() == "it")

    def _before_project(self) -> Project:
        return preview_project(self.project, self.base_token(), self.point, self.instrument_name, self.track)

    def _after_project(self) -> Project:
        return preview_project(self.project, self.token(), self.point, self.instrument_name, self.track)

    def _play(self, project: Project):
        self.playback.play(project, only_audible=False)

    def _schedule(self, *_args):
        self.hint.setVisible(len(self.chain) + bool(self.current_function()) > MAX_CHAIN_HINT)
        self._timer.start()

    def _refresh(self):
        self.before.set_project(self._before_project())
        message, color, valid = "", "", False
        try:
            token = self.token()
            self.text.setText(token)
            result = expansion(token, self.project, self.point, get_instrument(self.instrument_name))
            valid = True
            message, color = "\n".join(result.warnings), warn_text()
            self.after.set_project(self._after_project())
        except NotationError as e:
            message, color = str(e), BAD
            self.after.clear(message)
        self.status.setText(message)
        self.status.setStyleSheet(f"color: {color};")
        changed = valid and bool(self.chain or self.current_function())
        self.replace_btn.setEnabled(changed)
        self.create_btn.setEnabled(changed)
        self.freeze_btn.setEnabled(valid)
        self.play_after.setEnabled(valid)

    # ------------------------------------------------------------ i pulsanti
    def _replace(self):
        self.result_token = self.token()
        self.accept()

    def _write_notes(self):
        self.freeze = True
        self._replace()

    def _ask_name(self) -> str:
        name, ok = QInputDialog.getText(self, tr("Crea pattern"), tr("Nome del nuovo pattern (senza %):"))
        return name.strip() if ok else ""

    def _create_pattern(self):
        name = self._ask_name()
        if not name:
            return
        if not name.replace("_", "a").isalnum():
            QMessageBox.warning(self, tr("Nome non valido"),
                                tr("Il nome del pattern puo' contenere solo lettere, cifre e underscore (nessuno spazio)."))
            return
        if name in self.project.patterns:
            QMessageBox.warning(self, tr("Pattern gia' esistente"), tr("Esiste gia' un pattern '%{name}'.", name=name))
            return
        self.project.patterns[name] = Pattern(name=name, tokens=tokenize(self.token()))
        self.created_pattern = name
        self.accept()


class ArpeggioDialog(QDialog):
    """Arpeggia...: tipo e griglia, con l'ascolto. render(tipo, griglia) e' il
    testo che risulterebbe."""

    def __init__(self, parent, title: str, render: Callable[[str, str], str], project: Project, playback,
                 instrument_name: str, track=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.project, self.playback, self.track = project, playback, track
        self.render, self.instrument_name = render, instrument_name
        form = QFormLayout(self)
        self.kind = QComboBox()
        self.kind.addItems(arpeggio_kinds())
        form.addRow(tr("Tipo"), self.kind)
        self.grid = QComboBox()
        for grid in GRIDS:
            self.grid.addItem(_grid_label(grid), grid)
        self.grid.setCurrentIndex(GRIDS.index("8"))
        form.addRow(tr("Griglia"), self.grid)
        row = QHBoxLayout()
        listen = QPushButton(tr("▶ Ascolta"))
        listen.clicked.connect(self._listen)
        ok = QPushButton(tr("Scrivi"))
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        cancel = QPushButton(tr("Annulla"))
        cancel.clicked.connect(self.reject)
        for button in (listen, ok, cancel):
            row.addWidget(button)
        form.addRow(row)

    def result_text(self) -> str:
        return self.render(self.kind.currentText(), self.grid.currentData())

    def _listen(self):
        preview = Project(name="preview", tempo_bpm=self.project.tempo_bpm, time_sig=self.project.time_sig,
                          key=self.project.key, key_changes=list(self.project.key_changes))
        preview.patterns = self.project.patterns
        preview.instruments = self.project.instruments
        copy_synth(preview.add_track("Anteprima", self.instrument_name, self.result_text()), self.track)
        self.playback.play(preview, only_audible=False)
