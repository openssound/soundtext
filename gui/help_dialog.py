import os

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QKeySequence, QShortcut, QTextCursor
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextBrowser, QPushButton, QLineEdit,
                               QLabel, QTextEdit, QWidget, QApplication)

from core.version import get_app_root
from core.i18n import localized_doc, tr

from . import theme

HELP_PATH = os.path.join(get_app_root(), "docs", "HELP.md")


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Guida utente — SoundText"))
        self.resize(760, 700)

        layout = QVBoxLayout(self)
        browser = QTextBrowser()
        # I rimandi dell'indice (#8.4) li gestiamo noi; i link esterni li apre il sistema.
        browser.setOpenLinks(False)
        browser.anchorClicked.connect(self._on_link)
        self.browser = browser

        try:
            with open(localized_doc(HELP_PATH), "r", encoding="utf-8") as f:
                content = f.read()
            browser.setMarkdown(content)
        except OSError as e:
            browser.setPlainText(tr("Impossibile caricare la guida ({HELP_PATH}):\n{e}", HELP_PATH=HELP_PATH, e=e))

        layout.addWidget(browser)
        layout.addWidget(self._build_search_bar())

        buttons = QHBoxLayout()
        top_btn = QPushButton(tr("Indice"))
        top_btn.clicked.connect(lambda: self.browser.verticalScrollBar().setValue(0))
        buttons.addWidget(top_btn)
        search_btn = QPushButton(tr("Cerca"))
        search_btn.setToolTip(tr("Cerca un testo nella guida (Ctrl+F)"))
        search_btn.clicked.connect(self.show_search)
        buttons.addWidget(search_btn)
        QShortcut(QKeySequence.StandardKey.Find, self, self.show_search)
        buttons.addStretch(1)
        close_btn = QPushButton(tr("Chiudi"))
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)
        # Invio nel campo di ricerca deve solo passare al risultato successivo, non
        # premere anche il pulsante predefinito del dialogo (Precedente, Chiudi...).
        for button in self.findChildren(QPushButton):
            button.setAutoDefault(False)

    def _build_search_bar(self) -> QWidget:
        """Barra di ricerca sotto la guida, nascosta finche' non si preme Cerca:
        Invio va al risultato successivo, Maiusc+Invio al precedente, Esc la chiude."""
        bar = QWidget()
        row = QHBoxLayout(bar)
        row.setContentsMargins(0, 0, 0, 0)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(tr("Testo da cercare nella guida…"))
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._on_search_text)
        self.search_edit.returnPressed.connect(self._on_return)
        row.addWidget(self.search_edit, 1)
        prev_btn = QPushButton(tr("Precedente"))
        prev_btn.clicked.connect(lambda: self.find(backward=True))
        row.addWidget(prev_btn)
        next_btn = QPushButton(tr("Successivo"))
        next_btn.clicked.connect(lambda: self.find())
        row.addWidget(next_btn)
        self.search_status = QLabel()
        self.search_status.setMinimumWidth(110)
        row.addWidget(self.search_status)
        close_btn = QPushButton("✕")
        close_btn.setToolTip(tr("Chiudi la ricerca (Esc)"))
        close_btn.clicked.connect(self.hide_search)
        row.addWidget(close_btn)
        bar.hide()
        self.search_bar = bar
        self._matches = []
        self._current = -1
        return bar

    def show_search(self):
        self.search_bar.show()
        self.search_edit.setFocus()
        self.search_edit.selectAll()

    def hide_search(self):
        self.search_bar.hide()
        self.browser.setExtraSelections([])
        self.browser.setFocus()

    def keyPressEvent(self, event):
        # Esc chiude prima la barra di ricerca, poi (alla seconda pressione) la guida.
        if event.key() == Qt.Key.Key_Escape and self.search_bar.isVisible():
            self.hide_search()
            return
        super().keyPressEvent(event)

    def _on_return(self):
        self.find(backward=bool(QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier))

    def _on_search_text(self, text: str):
        """Trova tutte le occorrenze e porta in vista la prima."""
        doc = self.browser.document()
        self._matches = []
        if text:
            cursor = doc.find(text, 0)
            while not cursor.isNull():
                self._matches.append(cursor)
                cursor = doc.find(text, cursor)
        self._current = -1
        if self._matches:
            self.find()
        else:
            self._show_current()

    def find(self, backward: bool = False) -> bool:
        """Passa all'occorrenza successiva (o precedente) del testo cercato,
        ricominciando dall'altra estremita' della guida quando finiscono."""
        if not self._matches:
            return False
        step = -1 if backward else 1
        self._current = (self._current + step) % len(self._matches)
        self._show_current()
        return True

    def _show_current(self):
        """Tutte le occorrenze in arancio, quella corrente nel blu del tema, e
        il conteggio accanto ai pulsanti."""
        selections = []
        for i, match in enumerate(self._matches):
            sel = QTextEdit.ExtraSelection()
            sel.cursor = match
            sel.format.setBackground(QColor(theme.ACCENT if i == self._current else theme.WARN))
            sel.format.setForeground(QColor("#10151a"))
            selections.append(sel)
        self.browser.setExtraSelections(selections)
        if not self.search_edit.text():
            self.search_status.setText("")
        elif not self._matches:
            self.search_status.setText(tr("Nessun risultato"))
        else:
            cursor = QTextCursor(self._matches[self._current])
            cursor.clearSelection()
            self.browser.setTextCursor(cursor)
            self.browser.ensureCursorVisible()
            self.search_status.setText(tr("{current} di {total}", current=self._current + 1,
                                          total=len(self._matches)))

    def _on_link(self, url: QUrl):
        if url.scheme():
            QDesktopServices.openUrl(url)
        else:
            self.goto_section(url.fragment())

    def goto_section(self, ref: str) -> bool:
        """Porta in vista il titolo della sezione `ref` (es. "19", "19.3")."""
        doc = self.browser.document()
        block = doc.begin()
        while block.isValid():
            level = block.blockFormat().headingLevel()
            text = block.text().strip()
            if level > 1 and (text == ref or text.startswith((ref + " ", ref + "."))):
                top = doc.documentLayout().blockBoundingRect(block).top()
                self.browser.verticalScrollBar().setValue(int(top))
                return True
            block = block.next()
        return False
