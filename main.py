#!/usr/bin/env python3
"""
SoundText — punto di ingresso dell'applicazione desktop.

Avvio:
    python3 main.py
    python3 main.py examples/ensemble_demo.st
"""

import logging
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# L'app impacchettata avvia se stessa come processo host dei plugin
# (core.plugin_worker): va riconosciuto prima di importare Qt.
if __name__ == "__main__" and "--plugin-worker" in sys.argv[1:]:
    from core.plugin_worker import main as _plugin_worker_main
    _plugin_worker_main()
    sys.exit(0)

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon
from gui.main_window import MainWindow
from gui.theme import palette_for, stylesheet_for
from core.version import get_app_root
from core import settings
from core.log import LOG_FILE, setup_logging

# Nella build PyInstaller, FluidSynth (DLL + fluidsynth.exe opzionale) viene
# affiancato a SoundText.exe da build-windows-portable.ps1: senza questa
# riga, shutil.which("fluidsynth") in core/playback.py non lo troverebbe
# perche' la cartella dell'eseguibile non e' automaticamente nel PATH del
# processo (a differenza della ricerca DLL di Windows, che la include gia').
if getattr(sys, "frozen", False):
    os.environ["PATH"] = get_app_root() + os.pathsep + os.environ.get("PATH", "")

ICON_PATH = os.path.join(get_app_root(), "assets", "icon.png")


_last_error_dialog = 0.0


def _excepthook(exc_type, exc, tb):
    """Eccezioni non gestite (es. dentro uno slot Qt): nel log con il
    traceback, e un avviso all'utente invece del solo messaggio su stderr,
    invisibile nell'app impacchettata. L'app resta aperta, come prima. Al
    massimo un avviso ogni 10 secondi, per non sommergere l'utente se lo
    stesso errore si ripete a ogni tick di un timer."""
    global _last_error_dialog
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc, tb)
        return
    logging.getLogger("soundtext").critical("Eccezione non gestita", exc_info=(exc_type, exc, tb))
    now = time.monotonic()
    if QApplication.instance() is not None and now - _last_error_dialog > 10:
        _last_error_dialog = now
        QMessageBox.critical(
            None, "Errore imprevisto",
            f"Si e' verificato un errore imprevisto:\n{exc}\n\n"
            f"L'app resta aperta: per sicurezza salva il progetto con un nome nuovo.\n"
            f"I dettagli sono nel file di log:\n{LOG_FILE}")


def _install_qt_translations(app):
    """Testi standard di Qt (pulsanti Si'/No/Annulla, finestre di scelta dei
    file) nella lingua dell'interfaccia (vedi core.i18n)."""
    from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
    from core.i18n import current_language
    language = current_language()
    QLocale.setDefault(QLocale(language))
    translator = QTranslator(app)
    if translator.load(f"qtbase_{language}", QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
        app.installTranslator(translator)
        app._qt_translator = translator      # resta vivo quanto l'app


def main():
    setup_logging()
    sys.excepthook = _excepthook
    # Fusion e' l'unico stile Qt che rispetta in modo affidabile un QSS
    # personalizzato applicato a livello di QApplication: lo stile nativo di
    # Windows (windowsvista, predefinito altrimenti) disegna alcuni
    # sottocontrolli (es. le frecce su/giu' di QSpinBox) ignorando parte del
    # box model CSS, causando testo e frecce sovrapposti — riproducibile
    # solo su Windows reale, non nell'ambiente di test (Fusion e' gia' il
    # fallback li'). Va impostato PRIMA di creare la QApplication.
    QApplication.setStyle("Fusion")
    app = QApplication(sys.argv)
    _install_qt_translations(app)
    app.setApplicationName("SoundText")
    app.setPalette(palette_for(settings.get_theme()))
    app.setStyleSheet(stylesheet_for(settings.get_theme()))
    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))

    window = MainWindow()
    if os.path.exists(ICON_PATH):
        window.setWindowIcon(QIcon(ICON_PATH))

    if len(sys.argv) > 1:
        path = sys.argv[1]
        if os.path.exists(path):
            if path.lower().endswith((".musicxml", ".mxl")):
                window._import_musicxml_as_new_project(path)
            elif path.lower().endswith(".abc"):
                window._import_abc_as_new_project(path)
            else:
                window._load_and_apply_project(path)

    window.show()
    # Copia di recupero lasciata da una sessione chiusa male (core.autosave):
    # si chiede quando la finestra e' gia' visibile.
    QTimer.singleShot(0, window.offer_recovery)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
