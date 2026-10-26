"""
Suoni -> Scarica e installa...: strumenti SFZ, plugin, profili
NAM e motori in un'unica finestra. Si spuntano le voci, Installa le esegue
in un processo a parte (core.downloads, che usa scarica_strumenti.py) e la
finestra ne mostra l'avanzamento e il registro; Annulla lo ferma (i
download interrotti riprendono la volta dopo).
"""

import shutil
from typing import Dict, List, Optional

from PySide6.QtCore import QProcess, Qt
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QMessageBox,
                               QPlainTextEdit, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout)

from core import downloads
from core.i18n import tr

from .theme import dim

KEY_ROLE = Qt.UserRole


class DownloadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Scarica e installa"))
        self.resize(900, 640)
        self._process: Optional[QProcess] = None
        self._pending = ""
        self.changed = False                 # qualcosa e' stato installato (per chi ha aperto la finestra)
        layout = QVBoxLayout(self)
        intro = QLabel(tr("Spunta quello che vuoi e premi Installa. Gli strumenti vanno in ~/Strumenti; "
                          "quello che c'e' gia' si salta, e un download interrotto riprende la volta dopo."))
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels([tr("Nome"), tr("Dettagli"), tr("Stato")])
        self.tree.setColumnWidth(0, 330)
        self.tree.setColumnWidth(1, 400)
        self.tree.itemChanged.connect(lambda *_a: self._update_buttons())
        layout.addWidget(self.tree, 3)

        self.status = QLabel("")
        dim(self.status)
        layout.addWidget(self.status)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(5000)
        layout.addWidget(self.log, 2)

        row = QHBoxLayout()
        self.install_btn = QPushButton(tr("Installa"))
        self.install_btn.clicked.connect(self.install)
        self.cancel_btn = QPushButton(tr("Ferma"))
        self.cancel_btn.clicked.connect(self.cancel)
        self.cancel_btn.setEnabled(False)
        row.addWidget(self.install_btn)
        row.addWidget(self.cancel_btn)
        row.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        row.addWidget(buttons)
        layout.addLayout(row)
        self.refresh()

    # ------------------------------------------------------------ elenco
    def refresh(self):
        """Ricostruisce l'elenco con lo stato attuale (mantenendo le spunte)."""
        checked = set(self.checked_keys())
        self.tree.blockSignals(True)
        self.tree.clear()
        self._items: Dict[str, downloads.Item] = {}
        heads: Dict[str, QTreeWidgetItem] = {}
        script = downloads.load_script()
        for item in downloads.catalog():
            head = heads.get(item.category)
            if head is None:
                head = heads[item.category] = QTreeWidgetItem([downloads.category_label(item.category)])
                head.setFlags(head.flags() & ~Qt.ItemIsUserCheckable)
                font = head.font(0)
                font.setBold(True)
                head.setFont(0, font)
                self.tree.addTopLevelItem(head)
            row = QTreeWidgetItem([item.label, item.detail, self._state_text(item)])
            row.setData(0, KEY_ROLE, item.key)
            row.setToolTip(1, item.detail)
            linux_host = item.key == "host" and script is not None and script.SISTEMA == "linux"
            terminal_only = linux_host and not shutil.which("pkexec")
            unavailable = item.key == "nam-plugin" and script is not None and script.SISTEMA not in script.NAM_PLUGIN_FILES
            if terminal_only:
                row.setText(2, tr("dal terminale"))
                row.setToolTip(2, tr("Su Linux si installano con apt, che chiede la password: dal terminale, "
                                     "nella cartella di SoundText, esegui ./scarica_strumenti.sh host"))
                row.setFlags(row.flags() & ~Qt.ItemIsEnabled)
            elif unavailable:
                row.setFlags(row.flags() & ~Qt.ItemIsEnabled)
            else:
                if linux_host:
                    row.setToolTip(2, tr("Su Linux si installano con apt: la password di amministratore la "
                                         "chiede una finestra del sistema."))
                row.setFlags(row.flags() | Qt.ItemIsUserCheckable)
                row.setCheckState(0, Qt.Checked if item.key in checked else Qt.Unchecked)
            head.addChild(row)
            self._items[item.key] = item
        for category, head in heads.items():
            head.setExpanded(category != downloads.CATEGORY_SFZ_EXTRA)
        self.tree.blockSignals(False)
        self._update_buttons()

    @staticmethod
    def _state_text(item: downloads.Item) -> str:
        if item.installed is True:
            return tr("installato")
        if item.installed is False:
            return tr("da installare")
        return tr("installa o aggiorna")

    def _rows(self) -> List[QTreeWidgetItem]:
        out = []
        for i in range(self.tree.topLevelItemCount()):
            head = self.tree.topLevelItem(i)
            out += [head.child(j) for j in range(head.childCount())]
        return out

    def checked_keys(self) -> List[str]:
        if not hasattr(self, "_items"):
            return []
        return [row.data(0, KEY_ROLE) for row in self._rows()
                if row.flags() & Qt.ItemIsUserCheckable and row.checkState(0) == Qt.Checked]

    def set_checked(self, keys):
        for row in self._rows():
            if row.flags() & Qt.ItemIsUserCheckable:
                row.setCheckState(0, Qt.Checked if row.data(0, KEY_ROLE) in keys else Qt.Unchecked)

    def _update_buttons(self):
        running = self._process is not None
        self.install_btn.setEnabled(not running and bool(self.checked_keys()))
        self.cancel_btn.setEnabled(running)
        self.tree.setEnabled(not running)

    # ------------------------------------------------------------ esecuzione
    def install(self):
        keys = self.checked_keys()
        if not keys or self._process is not None:
            return
        builds = [k for k in keys if self._items[k].needs_build and not self._items[k].installed]
        if builds:
            problem = downloads.build_tools_problem()
            if problem:
                QMessageBox.warning(self, tr("Servono gli strumenti per compilare"),
                                    tr("Il motore SFZ interno si compila sul tuo computer, e mancano alcuni "
                                       "strumenti. Installali e riprova:\n\n{problem}", problem=problem))
                keys = [k for k in keys if k not in builds]
                if not keys:
                    return
        program, *args = downloads.command(keys)
        self.log.appendPlainText("$ " + " ".join(keys))
        self._pending = ""
        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._read)
        self._process.finished.connect(self._finished)
        self._process.errorOccurred.connect(self._error)
        self._process.start(program, args)
        self.status.setText(tr("In corso…"))
        self._update_buttons()

    def cancel(self):
        if self._process is not None:
            self._process.kill()
            self.log.appendPlainText(tr("Fermato: rilancia per riprendere da dove era arrivato."))

    def _read(self):
        text = self._pending + bytes(self._process.readAllStandardOutput()).decode("utf-8", "replace")
        lines = text.replace("\r\n", "\n").split("\n")
        self._pending = lines.pop()             # l'ultima riga puo' essere incompleta
        for line in lines:
            self._line(line)
        if "\r" in self._pending:              # avanzamento di un download (riscritto sulla stessa riga)
            self.status.setText(self._pending.rsplit("\r", 1)[-1].strip() or self.status.text())

    def _line(self, line: str):
        last = line.rsplit("\r", 1)[-1].rstrip()
        if not last.strip():
            return
        if last.startswith("== "):
            self.status.setText(last[3:])
        self.log.appendPlainText(last)

    def _finished(self, code, _status=None):
        if self._pending.strip():
            self._line(self._pending)
        self._pending = ""
        self._process = None
        self.changed = True
        self.status.setText(tr("Fatto.") if code == 0 else tr("Finito con degli errori: vedi il registro."))
        self.refresh()
        self.set_checked([])

    def _error(self, error):
        if error == QProcess.FailedToStart:
            self.log.appendPlainText(tr("Impossibile avviare il processo di download."))
            self._process = None
            self._update_buttons()

    def reject(self):
        if self._process is not None:
            if QMessageBox.question(self, tr("Scarica e installa"),
                                    tr("C'e' un'installazione in corso: fermarla e chiudere?")) != QMessageBox.Yes:
                return
            self._process.kill()
            self._process.waitForFinished(3000)
        super().reject()
