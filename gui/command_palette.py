"""
"Cerca un comando" (Ctrl+K): una casella in cui si scrive cosa si vuole
fare ("esporta", "registra", "genera basso"...) e si preme Invio, invece di
cercare la voce fra i menu. Elenca le voci dei menu della finestra (piu'
quelle del menu "+ Aggiungi traccia"), con il percorso del menu e la
scorciatoia, cosi' la volta dopo si puo' usare quella.
"""

import unicodedata
from dataclasses import dataclass
from typing import List

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu, QMenuBar, QVBoxLayout,
)

from .theme import TEXT_DIM
from core.i18n import tr


@dataclass
class Command:
    title: str        # testo della voce, senza "&"
    path: str         # menu in cui si trova, es. "Progetto" o "Traccia › Genera"
    action: QAction

    @property
    def shortcut(self) -> str:
        return self.action.shortcut().toString(QKeySequence.NativeText)


def _clean(text: str) -> str:
    return text.replace("&&", "\x00").replace("&", "").replace("\x00", "&").strip()


def _norm(text: str) -> str:
    """Minuscolo e senza accenti/apostrofi: 'tonalità' trova 'tonalita''."""
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c)).replace("'", "")


def collect_commands(menubar: QMenuBar, extra_menus=()) -> List[Command]:
    """Tutte le voci eseguibili dei menu (sottomenu compresi); extra_menus:
    [(percorso, QMenu)] da aggiungere (menu costruiti al volo)."""
    commands: List[Command] = []
    seen = set()

    def walk(menu: QMenu, path: str):
        for action in menu.actions():
            if action.isSeparator() or not action.isVisible():
                continue
            sub = action.menu()
            if sub is not None:
                walk(sub, f"{path} › {_clean(action.text())}" if path else _clean(action.text()))
                continue
            title = _clean(action.text())
            if not title or id(action) in seen:
                continue
            seen.add(id(action))
            commands.append(Command(title, path, action))

    for top in menubar.actions():
        if top.menu() is not None:
            walk(top.menu(), _clean(top.text()))
    for path, menu in extra_menus:
        walk(menu, path)
    return commands


def rank_commands(commands: List[Command], query: str) -> List[Command]:
    """Voci che contengono tutte le parole cercate (nel titolo o nel
    percorso), prima quelle il cui titolo inizia con la ricerca, poi quelle
    che la contengono nel titolo, poi le altre; a parita', l'ordine dei menu."""
    words = _norm(query).split()
    if not words:
        return list(commands)
    scored = []
    for index, cmd in enumerate(commands):
        title, path = _norm(cmd.title), _norm(cmd.path)
        if not all(w in title or w in path for w in words):
            continue
        joined = " ".join(words)
        if title.startswith(joined):
            score = 0
        elif all(w in title for w in words):
            score = 1
        else:
            score = 2
        scored.append((score, index, cmd))
    return [cmd for _score, _index, cmd in sorted(scored, key=lambda t: (t[0], t[1]))]


class CommandPalette(QDialog):
    """Casella di ricerca + elenco dei risultati: frecce per scegliere,
    Invio per eseguire, Esc per chiudere."""

    def __init__(self, parent, commands: List[Command]):
        super().__init__(parent)
        self.setWindowTitle(tr("Cerca un comando"))
        self.setMinimumSize(560, 420)
        self._commands = commands
        self._chosen = None

        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("Scrivi cosa vuoi fare: esporta, registra, genera basso, metronomo..."))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._refresh)
        self.search.installEventFilter(self)
        layout.addWidget(self.search)

        self.results = QListWidget()
        self.results.itemActivated.connect(lambda _item: self.run_selected())
        layout.addWidget(self.results, 1)

        hint = QLabel(tr("↑ ↓ scegli · Invio esegui · Esc chiudi"))
        hint.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        layout.addWidget(hint)

        self._refresh("")

    def _refresh(self, text: str):
        self.results.clear()
        for cmd in rank_commands(self._commands, text):
            label = cmd.title
            details = cmd.path + (f"   ·   {cmd.shortcut}" if cmd.shortcut else "")
            item = QListWidgetItem(f"{label}\n    {details}")
            item.setData(Qt.UserRole, cmd)
            if not cmd.action.isEnabled():
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            self.results.addItem(item)
        for row in range(self.results.count()):
            if self.results.item(row).flags() & Qt.ItemIsEnabled:
                self.results.setCurrentRow(row)
                break

    def visible_titles(self) -> List[str]:
        return [self.results.item(r).data(Qt.UserRole).title for r in range(self.results.count())]

    def eventFilter(self, obj, event):
        if obj is self.search and event.type() == event.Type.KeyPress:
            key = event.key()
            if key in (Qt.Key_Down, Qt.Key_Up, Qt.Key_PageDown, Qt.Key_PageUp):
                self.results.keyPressEvent(event)
                return True
            if key in (Qt.Key_Return, Qt.Key_Enter):
                self.run_selected()
                return True
        return super().eventFilter(obj, event)

    def run_selected(self):
        item = self.results.currentItem()
        if item is None or not item.flags() & Qt.ItemIsEnabled:
            return
        self._chosen = item.data(Qt.UserRole)
        self.accept()
        # Eseguita dopo la chiusura: molte voci aprono a loro volta un dialogo.
        QTimer.singleShot(0, self._chosen.action.trigger)

    def chosen(self):
        return self._chosen
