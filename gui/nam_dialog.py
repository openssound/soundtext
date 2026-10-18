"""
Finestra di scelta del profilo NAM: i profili della cartella profili_nam
(e di quella del profilo attuale), raggruppati per tipologia
(amplificatori senza cassa, con la cassa, pedali, altri), con il tipo e
l'uso di ciascuno, per aiutare a scegliere. "Altro file..." apre la normale
finestra dei file per un .nam qualsiasi.
"""

import os
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout,
)

from core.i18n import tr
from core.nam import GEAR_TYPE_LABELS
from core.nam_profiles import (GROUP_AMP, GROUP_AMP_CAB, GROUP_OTHER, GROUP_PEDAL, GROUPS, existing_nam_dir,
                               list_profiles)

from .file_dialogs import file_dialog_options

_PATH_ROLE = Qt.UserRole


def _group_title(group: str) -> str:
    return {GROUP_AMP: tr("Amplificatori (senza cassa: SoundText ne aggiunge una interna)"),
            GROUP_AMP_CAB: tr("Amplificatori con la cassa (pronti, niente IR)"),
            GROUP_PEDAL: tr("Pedali (da mettere prima di un amplificatore)"),
            GROUP_OTHER: tr("Altri profili")}[group]


def _sound_label(sound) -> str:
    return ", ".join(tr(word) for word in sound)


def _type_label(gear_type: str) -> str:
    label = GEAR_TYPE_LABELS.get(gear_type)
    return tr(label) if label else tr("tipo non indicato")


class NamProfileDialog(QDialog):
    """Dopo exec(), selected_path() e' il profilo scelto ('' = nessuno)."""

    def __init__(self, parent=None, current: str = "", start_dir: str = ""):
        super().__init__(parent)
        self.setWindowTitle(tr("Scegli un profilo NAM"))
        self.resize(760, 520)
        self.current = current
        self.start_dir = start_dir
        self._path = ""
        folders = [existing_nam_dir()]
        if current and os.path.dirname(current) not in folders:
            folders.append(os.path.dirname(current))
        self.entries = list_profiles([f for f in folders if f])

        layout = QVBoxLayout(self)
        intro = QLabel(
            tr("Profili NAM sul computer, per tipologia. Un amplificatore senza cassa riceve da solo una cassa "
               "interna; i pedali vanno messi prima di un amplificatore (interno o profilo).")
            if self.entries else
            tr("Nessun profilo NAM nella cartella dei profili: scaricane una trentina con Suoni → Scarica → "
               "Scarica profili NAM consigliati..., oppure scegli un file con «Altro file…»."))
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("Cerca per nome, tipo, suono o uso…"))
        self.search.textChanged.connect(self._fill)
        layout.addWidget(self.search)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([tr("Profilo"), tr("Tipo"), tr("Suono"), tr("Adatto a")])
        self.tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree.itemDoubleClicked.connect(lambda item, _col: self._accept_item(item))
        self.tree.currentItemChanged.connect(lambda *_: self._update_ok())
        layout.addWidget(self.tree, 1)
        row = QHBoxLayout()
        other = QPushButton(tr("Altro file…"))
        other.setToolTip(tr("Scegli un file .nam qualsiasi"))
        other.clicked.connect(self._choose_file)
        row.addWidget(other)
        row.addStretch(1)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(lambda: self._accept_item(self.tree.currentItem()))
        self.buttons.rejected.connect(self.reject)
        row.addWidget(self.buttons)
        layout.addLayout(row)
        self._fill()

    def selected_path(self) -> str:
        return self._path

    def _fill(self):
        query = self.search.text().strip().lower()
        self.tree.clear()
        bold = QFont()
        bold.setBold(True)
        current_item: Optional[QTreeWidgetItem] = None
        for group in GROUPS:
            entries = [e for e in self.entries if e.group == group and
                       (not query or query in f"{e.name} {_type_label(e.gear_type)} {_sound_label(e.sound)} "
                                          f"{tr(e.use) if e.use else ''}".lower())]
            if not entries:
                continue
            head = QTreeWidgetItem([_group_title(group), "", "", ""])
            head.setFont(0, bold)
            head.setFlags(Qt.ItemIsEnabled)
            head.setFirstColumnSpanned(True)
            self.tree.addTopLevelItem(head)
            for e in sorted(entries, key=lambda e: e.name.lower()):
                item = QTreeWidgetItem([e.name, _type_label(e.gear_type), _sound_label(e.sound),
                                        tr(e.use) if e.use else ""])
                item.setData(0, _PATH_ROLE, e.path)
                item.setToolTip(0, e.path)
                item.setToolTip(3, tr(e.use) if e.use else "")
                head.addChild(item)
                if self.current and os.path.normcase(os.path.abspath(e.path)) == \
                        os.path.normcase(os.path.abspath(self.current)):
                    current_item = item
            head.setExpanded(True)
        for col in range(4):
            self.tree.resizeColumnToContents(col)
        if current_item is not None:
            self.tree.setCurrentItem(current_item)
        self._update_ok()

    def _update_ok(self):
        item = self.tree.currentItem()
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(item is not None and bool(item.data(0, _PATH_ROLE)))

    def _accept_item(self, item):
        path = item.data(0, _PATH_ROLE) if item is not None else None
        if path:
            self._path = path
            self.accept()

    def _choose_file(self):
        start = os.path.dirname(self.current) if self.current else self.start_dir or os.path.expanduser("~")
        path, _filter = QFileDialog.getOpenFileName(
            self, tr("Scegli un profilo NAM"), start, tr("Profili NAM (*.nam)"), options=file_dialog_options())
        if path:
            self._path = path
            self.accept()
