import os
import platform

from PySide6 import __version__ as pyside_version
from PySide6.QtCore import Qt, qVersion
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton

from core.version import APP_NAME, APP_VERSION, get_app_root
from core.audio_decode import decoder_description
from core.i18n import tr

ICON_PATH = os.path.join(get_app_root(), "assets", "icon.png")


def _status_line(label: str, available: bool) -> str:
    icon = "✓" if available else "✗"
    color = "#4caf50" if available else "#999999"
    return f'<span style="color:{color}">{icon}</span> {label}'


APP_AUTHOR = "Sergio Scolaro"
COPYRIGHT_YEARS = "2026"


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Informazioni su {APP_NAME}", APP_NAME=APP_NAME))
        self.setFixedWidth(420)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        header = QHBoxLayout()
        if os.path.exists(ICON_PATH):
            icon_label = QLabel()
            icon_label.setPixmap(QPixmap(ICON_PATH).scaled(
                64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            header.addWidget(icon_label)

        title_box = QVBoxLayout()
        name_label = QLabel(APP_NAME)
        name_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        title_box.addWidget(name_label)
        version_label = QLabel(tr("Versione {APP_VERSION}", APP_VERSION=APP_VERSION))
        version_label.setStyleSheet("color: #999999;")
        title_box.addWidget(version_label)
        header.addLayout(title_box)
        header.addStretch(1)
        layout.addLayout(header)

        description = QLabel(
            tr("Notazione testuale semplificata per comporre ed eseguire musica: "
            "accordi/note simboliche, voicing dipendente dallo strumento e "
            "playback MIDI, con import/export MIDI e conversione da audio.")
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        license_label = QLabel(
            tr("Copyright © {COPYRIGHT_YEARS} {APP_AUTHOR}<br>Software libero con licenza GNU GPL versione 3, senza alcuna garanzia. Licenza e avvisi delle librerie di terze parti: file LICENSE e THIRD_PARTY_NOTICES.md accanto al programma (Guida, capitolo 14).", COPYRIGHT_YEARS=COPYRIGHT_YEARS, APP_AUTHOR=APP_AUTHOR)
        )
        license_label.setTextFormat(Qt.RichText)
        license_label.setWordWrap(True)
        license_label.setStyleSheet("color: #999999; font-size: 11px;")
        layout.addWidget(license_label)

        env_label = QLabel(
            tr("Python {0} · PySide6 {pyside_version} (Qt {1})<br>{2}", platform.python_version(), qVersion(), _status_line(tr("Decodifica mp3/m4a/flac/ogg: {0}", decoder_description() or tr("non disponibile")), bool(decoder_description())), pyside_version=pyside_version)
        )
        env_label.setTextFormat(Qt.RichText)
        layout.addWidget(env_label)

        close_btn = QPushButton(tr("Chiudi"))
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
