import os

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextBrowser, QPushButton

from core.version import get_app_root
from core.i18n import localized_doc, tr

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

        buttons = QHBoxLayout()
        top_btn = QPushButton(tr("Indice"))
        top_btn.clicked.connect(lambda: self.browser.verticalScrollBar().setValue(0))
        buttons.addWidget(top_btn)
        buttons.addStretch(1)
        close_btn = QPushButton(tr("Chiudi"))
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

    def _on_link(self, url: QUrl):
        if url.scheme():
            QDesktopServices.openUrl(url)
        else:
            self.goto_section(url.fragment())

    def goto_section(self, ref: str) -> bool:
        """Porta in vista il titolo della sezione `ref` (es. "8.4", "10bis");
        "inst" e' l'inizio delle istruzioni di installazione."""
        doc = self.browser.document()
        block = doc.begin()
        h1_seen = 0
        while block.isValid():
            level = block.blockFormat().headingLevel()
            text = block.text().strip()
            if level and (
                (ref == "inst" and level == 1 and (h1_seen := h1_seen + 1) == 2)
                or (ref != "inst" and (text == ref or text.startswith((ref + " ", ref + ".")))
                    and level > 1)
            ):
                top = doc.documentLayout().blockBoundingRect(block).top()
                self.browser.verticalScrollBar().setValue(int(top))
                return True
            block = block.next()
        return False
