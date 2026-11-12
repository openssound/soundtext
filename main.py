#!/usr/bin/env python3
"""
SoundText — punto di ingresso dell'applicazione desktop.

Avvio:
    python3 main.py
    python3 main.py examples/funk_in_e.st
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

# La finestra "Scarica e installa" (gui.download_dialog) avvia se stessa con
# --scarica-strumenti <voci>: esegue scarica_strumenti.py (accanto al
# programma) in un processo a parte, anche nell'app impacchettata, dove non
# c'e' un Python da usare.
if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "--scarica-strumenti":
    from core.downloads import run_script as _run_download_script
    sys.exit(_run_download_script(sys.argv[2:]))

from PySide6.QtCore import QEvent, QTimer, QTranslator
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon
from gui.main_window import MainWindow
from gui.theme import palette_for, stylesheet_for
from gui.file_dialogs import install_file_dialog_sizing, repair_sidebar_shortcuts
from core.version import get_app_root
from core import settings
from core.project_io import ensure_songs_dir
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
    from PySide6.QtCore import QLibraryInfo, QLocale
    from core.i18n import current_language
    language = current_language()
    QLocale.setDefault(QLocale(language))
    translator = QTranslator(app)
    if translator.load(f"qtbase_{language}", QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
        app.installTranslator(translator)
        app._qt_translator = translator      # resta vivo quanto l'app
    if language in _QFILEDIALOG_MISSING:
        fallback = _MissingQtStrings(_QFILEDIALOG_MISSING[language], app)
        app.installTranslator(fallback)
        app._qt_fallback_translator = fallback


# Etichette del dialogo file di Qt (Linux) che qtbase_*.qm non traduce: Qt le
# cerca con la scorciatoia ("&Look in:", "Files of &type:"), mentre i file di
# traduzione hanno solo le versioni senza "&", e il dialogo restava in parte
# in inglese.
_QFILEDIALOG_MISSING = {
    "it": {"&Look in:": "&Cerca in:", "Files of &type:": "File di &tipo:"},
    "es": {"&Look in:": "&Ver en:", "Files of &type:": "Ficheros de &tipo:"},
    "fr": {"&Look in:": "&Voir dans :", "Files of &type:": "Fichiers de &type :"},
}


class _MissingQtStrings(QTranslator):
    def __init__(self, strings, parent=None):
        super().__init__(parent)
        self._strings = strings

    def translate(self, context, source, disambiguation=None, n=-1):
        if context == "QFileDialog":
            return self._strings.get(source)
        return None

    def isEmpty(self):
        return False


def _disable_console_quick_edit():
    """Windows: un clic nella finestra del prompt da cui e' partito SoundText
    la mette in modalita' selezione ("Modifica rapida"), e Windows blocca
    ogni programma che vi scrive finche' non si preme un tasto. Bastava un
    avviso di fluidsynth (Analizza livelli, riproduzione) per fermare
    SoundText. Si toglie la Modifica rapida solo a questa console; nessun
    effetto se non c'e' una console (app impacchettata, pythonw)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-10)          # STD_INPUT_HANDLE
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return                                    # nessuna console
        ENABLE_QUICK_EDIT_MODE, ENABLE_EXTENDED_FLAGS = 0x0040, 0x0080
        kernel32.SetConsoleMode(handle, (mode.value & ~ENABLE_QUICK_EDIT_MODE) | ENABLE_EXTENDED_FLAGS)
    except Exception:
        pass                                          # solo una comodita'


class _SoundTextApp(QApplication):
    """Su macOS il doppio clic su un brano nel Finder (o il trascinamento
    sull'icona nel Dock) arriva come evento, non come argomento: anche
    all'avvio, prima che la finestra esista. I file si tengono da parte
    finche' la finestra non c'e' (open_files_with)."""

    def __init__(self, argv):
        super().__init__(argv)
        self._window = None
        self._pending = []

    def event(self, event):
        if event.type() == QEvent.FileOpen and event.file():
            if self._window is None:
                self._pending.append(event.file())
            else:
                self._window.open_path(event.file())
            return True
        return super().event(event)

    def open_files_with(self, window):
        self._window = window
        pending, self._pending = self._pending, []
        for path in pending:
            window.open_path(path, ask_to_save=False)


def main():
    _disable_console_quick_edit()
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
    app = _SoundTextApp(sys.argv)
    _install_qt_translations(app)
    app.setApplicationName("SoundText")
    app.setPalette(palette_for(settings.get_theme()))
    app.setStyleSheet(stylesheet_for(settings.get_theme()))
    repair_sidebar_shortcuts([ensure_songs_dir()])
    install_file_dialog_sizing(app)
    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))

    window = MainWindow()
    if os.path.exists(ICON_PATH):
        window.setWindowIcon(QIcon(ICON_PATH))

    # Strumenti salvati come pianoforte dalle versioni vecchie e ora
    # riconosciuti: si chiede prima di aprire il brano, che li userebbe.
    window.offer_instrument_fixes()

    if len(sys.argv) > 1 and not sys.argv[1].startswith("-psn_"):    # -psn_: vecchi macOS dal Finder
        window.open_path(sys.argv[1], ask_to_save=False)
    app.open_files_with(window)

    window.show()
    # Copia di recupero lasciata da una sessione chiusa male (core.autosave):
    # si chiede quando la finestra e' gia' visibile.
    QTimer.singleShot(0, window, window.autosave.offer_recovery)
    # SoundText non include un SoundFont: senza nessuno propone di scaricarlo
    QTimer.singleShot(0, window, window.offer_soundfont_download)
    # Il SoundFont si carica in sottofondo: il primo Play non lo aspetta
    from core.playback import preload_soundfont
    QTimer.singleShot(500, window, preload_soundfont)
    sys.exit(app.exec())


def _self_test() -> int:
    """`SoundText --self-test`: controlla che l'app impacchettata abbia
    tutto quello che serve per suonare (Qt con i plugin multimediali,
    FluidSynth, il motore SFZ interno, pedalboard, PortAudio, dati e guida)
    ed esce, senza aprire finestre. Lo usa la build per macOS prima di
    pubblicare (packaging/macos/build-macos.sh). 0 = tutto a posto."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    problems = []

    def check(label, fn):
        try:
            detail = fn()
            print(f"ok    {label}: {detail}")
        except Exception as e:  # noqa: BLE001 - qualunque errore e' un problema da dire
            problems.append(label)
            print(f"ERRORE {label}: {e}")

    def qt():
        app = QApplication.instance() or QApplication(sys.argv[:1])
        from PySide6 import QtMultimedia  # noqa: F401 - decodifica audio (FFmpeg di Qt)
        from PySide6.QtCore import qVersion
        return f"Qt {qVersion()}, piattaforma {app.platformName()}"

    def fluidsynth():
        from core import fluid
        if not fluid.available():
            raise RuntimeError(fluid.load_error() or "libreria non trovata")
        return f"{'.'.join(map(str, fluid.version()))} da {getattr(fluid._lib, '_name', '?')}"

    def sfz():
        from core import sfz_engine
        if not sfz_engine.sfz_available():
            raise RuntimeError("libsfizz non trovata")
        return sfz_engine.library_path()

    def data():
        root = get_app_root()
        for rel in ("assets/icon.png", "docs/HELP.md", "locales/en.json", "examples", "scarica_strumenti.py"):
            if not os.path.exists(os.path.join(root, rel)):
                raise RuntimeError(f"manca {rel} in {root}")
        return root

    check("Qt", qt)
    check("FluidSynth", fluidsynth)
    check("motore SFZ", sfz)
    check("pedalboard", lambda: __import__("pedalboard").__version__)
    check("PortAudio", lambda: __import__("sounddevice").get_portaudio_version()[1])
    check("verovio", lambda: __import__("verovio").toolkit(False).getVersion())
    check("dati", data)
    print("tutto a posto" if not problems else "problemi: " + ", ".join(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv[1:]:
        sys.exit(_self_test())
    main()
