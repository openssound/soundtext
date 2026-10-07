"""
Registro degli errori dell'app (file 'soundtext.log' nella cartella di
configurazione, vedi core.settings.CONFIG_DIR).

Molti fallimenti vengono gestiti ripiegando su un'alternativa (rendering
fluidsynth -> CLI -> player esterno, stima della tonalita', stream audio...)
senza disturbare l'utente: giusto, ma senza una traccia scritta nessuno sa
poi perche' la riproduzione "suona diversa" o non parte, specie nell'app
impacchettata per Windows/macOS dove non c'e' un terminale. Qui finiscono
quei fallimenti (con il traceback) e le eccezioni non gestite.

Menu Aiuto -> Apri il file di log per trovarlo.
"""

import logging
import logging.handlers
import os
import sys
import threading

from .settings import CONFIG_DIR

LOG_FILE = os.path.join(CONFIG_DIR, "soundtext.log")
_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

_configured = False


def setup_logging(level: int = logging.INFO) -> None:
    """Da chiamare una volta all'avvio dell'app (main.py): file di log a
    rotazione (1 MB, 3 file) + stderr per gli avvisi, e registrazione delle
    eccezioni non gestite nel thread principale e negli altri thread (es.
    quello di riproduzione, vedi core.playback)."""
    global _configured
    if _configured:
        return
    _configured = True
    root = logging.getLogger()
    root.setLevel(level)
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE, maxBytes=1_000_000, backupCount=2, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(_FORMAT))
        root.addHandler(file_handler)
    except OSError:
        pass  # cartella non scrivibile: resta solo stderr
    stderr_handler = logging.StreamHandler()
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(stderr_handler)

    def _thread_hook(args):
        if args.exc_type is SystemExit:
            return
        logging.getLogger("soundtext.thread").error(
            "Eccezione non gestita nel thread %s", getattr(args.thread, "name", "?"),
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback))

    threading.excepthook = _thread_hook
    logging.getLogger("soundtext").info("Avvio SoundText (Python %s, %s)", sys.version.split()[0], sys.platform)
