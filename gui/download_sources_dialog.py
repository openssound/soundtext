"""
Opzioni -> Sorgenti dei download... (anche dal pulsante Sorgenti... di
"Scarica e installa"): gli indirizzi da cui si scarica ogni voce, a gruppi,
modificabili. Si salvano solo quelli diversi dall'originale
(core.settings.set_download_sources) e valgono per le installazioni avviate
da SoundText (vedi core.downloads.apply_source_overrides).
"""

from typing import Dict, List

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                               QPushButton, QStyledItemDelegate, QTreeWidget, QTreeWidgetItem, QVBoxLayout)

from core import downloads
from core import settings as app_settings
from core.i18n import tr

from .theme import dim

KEY_ROLE = Qt.UserRole


class _AddressDelegate(QStyledItemDelegate):
    """Righe alte quanto il campo di modifica: con il padding dei QLineEdit
    del tema, nella riga normale il testo da modificare restava schiacciato."""

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setStyleSheet("QLineEdit { padding: 1px 4px; }")
        editor.setFrame(True)
        return editor

    def sizeHint(self, option, index):
        hint = super().sizeHint(option, index)
        return QSize(hint.width(), max(hint.height(), option.fontMetrics.height() + 12))

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class DownloadSourcesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Sorgenti dei download"))
        self.resize(980, 620)
        self._sources: Dict[str, downloads.Source] = {s.key: s for s in downloads.sources()}
        self._values: Dict[str, str] = {key: s.default for key, s in self._sources.items()}
        self._values.update({k: v for k, v in app_settings.get_download_sources().items() if k in self._sources})
        layout = QVBoxLayout(self)
        intro = QLabel(tr("Gli indirizzi da cui \"Scarica e installa\" prende ogni voce. Doppio clic su un "
                          "indirizzo per cambiarlo, per esempio per usare un mirror o una versione diversa; "
                          "quelli cambiati sono in grassetto. Valgono per le installazioni avviate da SoundText."))
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText(tr("Cerca per nome o indirizzo..."))
        self.filter_edit.textChanged.connect(self._apply_filter)
        layout.addWidget(self.filter_edit)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels([tr("Voce"), tr("Indirizzo")])
        self.tree.setColumnWidth(0, 300)
        self.tree.setItemDelegate(_AddressDelegate(self.tree))
        self.tree.itemChanged.connect(self._on_item_changed)
        heads: Dict[str, QTreeWidgetItem] = {}
        for source in self._sources.values():
            head = heads.get(source.section)
            if head is None:
                head = heads[source.section] = QTreeWidgetItem([source.section])
                font = head.font(0)
                font.setBold(True)
                head.setFont(0, font)
                head.setFlags(Qt.ItemIsEnabled)
                self.tree.addTopLevelItem(head)
            row = QTreeWidgetItem([source.label, self._values[source.key]])
            row.setData(0, KEY_ROLE, source.key)
            row.setFlags(row.flags() | Qt.ItemIsEditable)
            row.setToolTip(1, tr("Originale: {url}", url=source.default))
            head.addChild(row)
        for head in heads.values():
            head.setExpanded(True)
        self.tree.itemDoubleClicked.connect(lambda item, _col: self._edit(item))
        self.tree.currentItemChanged.connect(lambda *_a: self._update_buttons())
        layout.addWidget(self.tree, 1)

        self.status = QLabel("")
        dim(self.status)
        layout.addWidget(self.status)

        row = QHBoxLayout()
        self.reset_btn = QPushButton(tr("Ripristina l'originale"))
        self.reset_btn.clicked.connect(self.reset_current)
        self.reset_all_btn = QPushButton(tr("Ripristina tutti"))
        self.reset_all_btn.clicked.connect(self.reset_all)
        row.addWidget(self.reset_btn)
        row.addWidget(self.reset_all_btn)
        row.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        row.addWidget(buttons)
        layout.addLayout(row)
        self._refresh_marks()

    # ------------------------------------------------------------ righe
    def _rows(self) -> List[QTreeWidgetItem]:
        out = []
        for i in range(self.tree.topLevelItemCount()):
            head = self.tree.topLevelItem(i)
            out += [head.child(j) for j in range(head.childCount())]
        return out

    def _row(self, key: str) -> QTreeWidgetItem:
        return next(r for r in self._rows() if r.data(0, KEY_ROLE) == key)

    def _edit(self, item: QTreeWidgetItem):
        if item.data(0, KEY_ROLE):
            self.tree.editItem(item, 1)

    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        key = item.data(0, KEY_ROLE)
        if not key or column != 1:
            return
        value = item.text(1).strip()
        problem = downloads.check_source(self._sources[key], value)
        if problem:
            self.status.setText(tr("{label}: {problem}", label=self._sources[key].label, problem=problem))
            self.tree.blockSignals(True)
            item.setText(1, self._values[key])
            self.tree.blockSignals(False)
            return
        self._values[key] = value
        self.status.setText("")
        self._refresh_marks()

    def _refresh_marks(self):
        self.tree.blockSignals(True)
        for row in self._rows():
            key = row.data(0, KEY_ROLE)
            changed = self._values[key] != self._sources[key].default
            for column in (0, 1):
                font = row.font(column)
                font.setBold(changed)
                row.setFont(column, font)
        self.tree.blockSignals(False)
        self._update_buttons()

    def _update_buttons(self):
        current = self.tree.currentItem()
        key = current.data(0, KEY_ROLE) if current is not None else None
        self.reset_btn.setEnabled(bool(key) and self._values[key] != self._sources[key].default)
        self.reset_all_btn.setEnabled(bool(self.changed_values()))

    def _apply_filter(self, text: str):
        text = text.strip().lower()
        for i in range(self.tree.topLevelItemCount()):
            head = self.tree.topLevelItem(i)
            visible = 0
            for j in range(head.childCount()):
                row = head.child(j)
                hidden = bool(text) and text not in row.text(0).lower() and text not in row.text(1).lower()
                row.setHidden(hidden)
                visible += not hidden
            head.setHidden(visible == 0)

    # ------------------------------------------------------------ azioni
    def set_value(self, key: str, value: str) -> str:
        """Cambia un indirizzo come farebbe l'utente; '' se accettato, altrimenti il motivo."""
        row = self._row(key)
        row.setText(1, value)
        return "" if self._values[key] == value.strip() else self.status.text()

    def reset_current(self):
        current = self.tree.currentItem()
        key = current.data(0, KEY_ROLE) if current is not None else None
        if key:
            self.set_value(key, self._sources[key].default)

    def reset_all(self):
        for key in list(self.changed_values()):
            self.set_value(key, self._sources[key].default)

    def changed_values(self) -> Dict[str, str]:
        return {k: v for k, v in self._values.items() if v != self._sources[k].default}

    def accept(self):
        changed = self.changed_values()
        if changed and QMessageBox.question(
                self, tr("Sorgenti dei download"),
                tr("Hai cambiato {n} indirizzi. Scaricare da fonti diverse da quelle originali puo' dare file "
                   "diversi o non affidabili: salvare?", n=len(changed))) != QMessageBox.Yes:
            return
        app_settings.set_download_sources(changed)
        super().accept()
