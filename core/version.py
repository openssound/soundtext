"""
Nome e numero di versione dell'applicazione, in un unico punto cosi' che il
dialogo "Informazioni su" (gui.about_dialog) e chiunque altro ne abbia
bisogno (titolo finestra, export, log...) non debbano duplicarlo.
"""

import os
import sys

APP_NAME = "SoundText"
APP_VERSION = "1.6.0"


def get_app_root() -> str:
    """Cartella radice dell'app, da cui si ricavano assets/, docs/, songs/,
    midi/, soundfonts/: quella dell'eseguibile quando SoundText e'
    impacchettato con PyInstaller (sys.frozen None e __file__ non
    corrisponde piu' a un percorso reale su disco), altrimenti la cartella
    del repository/installazione sorgente (due livelli sopra core/)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


USER_DATA_ROOT = os.path.join(os.path.expanduser("~"), "SoundText")


def pick_writable_dir(preferred: str, fallback: str) -> str:
    """Ritorna 'preferred' (creandola se serve) se ci si puo' scrivere,
    altrimenti 'fallback' (creata). Serve per songs/, midi/ e soundfonts/
    accanto all'app: in un AppImage l'eseguibile gira da un mount di sola
    lettura, e in un'installazione di sistema puo' mancare il permesso di
    scrittura - li' salvare/importare fallirebbe."""
    try:
        os.makedirs(preferred, exist_ok=True)
        if os.access(preferred, os.W_OK):
            return preferred
    except OSError:
        pass
    os.makedirs(fallback, exist_ok=True)
    return fallback
