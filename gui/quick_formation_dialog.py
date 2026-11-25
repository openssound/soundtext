"""
La formazione di «Un brano in 60 secondi» (core.quick_formation): l'elenco di tutti gli strumenti disponibili, a gruppi
(batteria, pianoforti, organi, chitarre...), ognuno con la sua casella. Si spuntano quelli da usare e si esce con
«Conferma formazione»; senza nessuno strumento il brano usa l'organico della ricetta.
"""

from typing import List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
)

from core import quick_formation
from core.i18n import tr

_NAME, _ROLE = 0, 1


class FormationDialog(QDialog):
    def __init__(self, parent=None, selected: List[str] = ()):
        super().__init__(parent)
        self.setWindowTitle(tr("Formazione"))
        self.resize(520, 640)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr("Spunta gli strumenti che devono suonare nel brano. Ogni strumento suona la parte "
                                   "del suo ruolo: accordi, basso, melodia, tappeto o batteria. Senza nessuno strumento "
                                   "vale l'organico della ricetta.")))
        self.filter = QLineEdit()
        self.filter.setPlaceholderText(tr("Cerca uno strumento"))
        self.filter.setAccessibleName(tr("Cerca uno strumento"))
        self.filter.textChanged.connect(self._filter)
        layout.addWidget(self.filter)

        self.tree = QTreeWidget()
        self.tree.setAccessibleName(tr("Strumenti"))
        self.tree.setHeaderLabels([tr("Strumento"), tr("Suona")])
        self.tree.setRootIsDecorated(True)
        self.tree.setColumnWidth(_NAME, 300)
        wanted = set(selected)
        for group in quick_formation.catalog():
            top = QTreeWidgetItem([group["label"], ""])
            top.setFlags(top.flags() | Qt.ItemIsAutoTristate | Qt.ItemIsUserCheckable)
            top.setCheckState(_NAME, Qt.Unchecked)
            self.tree.addTopLevelItem(top)
            for instrument in group["instruments"]:
                item = QTreeWidgetItem([instrument["label"], quick_formation.role_label(instrument["role"])])
                item.setData(_NAME, Qt.UserRole, instrument["value"])
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(_NAME, Qt.Checked if instrument["value"] in wanted else Qt.Unchecked)
                top.addChild(item)
            top.setExpanded(any(top.child(i).checkState(_NAME) == Qt.Checked for i in range(top.childCount()))
                            or group["label"] == tr("Batteria"))
        self.tree.itemChanged.connect(lambda *_: self._update_summary())
        layout.addWidget(self.tree, 1)

        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        row = QHBoxLayout()
        clear = QPushButton(tr("Nessuno strumento"))
        clear.setToolTip(tr("Toglie tutte le spunte: il brano torna all'organico della ricetta."))
        clear.clicked.connect(self._clear)
        row.addWidget(clear)
        row.addStretch(1)
        layout.addLayout(row)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText(tr("Conferma formazione"))
        self.buttons.button(QDialogButtonBox.Cancel).setText(tr("Annulla"))
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self._update_summary()

    # ---- le scelte

    def _items(self):
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            for j in range(top.childCount()):
                yield top.child(j)

    def selected(self) -> List[str]:
        """Gli strumenti spuntati, nell'ordine dell'elenco."""
        return [item.data(_NAME, Qt.UserRole) for item in self._items() if item.checkState(_NAME) == Qt.Checked]

    def _clear(self):
        for item in self._items():
            item.setCheckState(_NAME, Qt.Unchecked)

    def _filter(self, text: str):
        text = text.strip().lower()
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            shown = 0
            for j in range(top.childCount()):
                child = top.child(j)
                match = not text or text in child.text(_NAME).lower() or text in child.text(_ROLE).lower()
                child.setHidden(not match)
                shown += match
            top.setHidden(not shown)
            if text and shown:
                top.setExpanded(True)

    def _update_summary(self):
        chosen = self.selected()
        if not chosen:
            self.summary.setText(tr("Nessuno strumento scelto: vale l'organico della ricetta."))
            return
        try:
            parts, left_out = quick_formation.assign(chosen)
        except ValueError as e:
            self.summary.setText("✗ " + str(e))
            return
        text = tr("{n} strumenti: {list}", n=len(chosen), list=quick_formation.describe(parts))
        if left_out:
            text += "\n" + tr("Non c'e' posto per: {list} (ogni ruolo ha un numero limitato di parti).",
                              list=", ".join(n.replace("_", " ") for n in left_out))
        if "melody" not in parts:
            text += "\n" + tr("Senza uno strumento melodico il brano non ha la melodia.")
        self.summary.setText(text)
