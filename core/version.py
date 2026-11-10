"""
Nome e numero di versione dell'applicazione, in un unico punto cosi' che il
dialogo "Informazioni su" (gui.about_dialog) e chiunque altro ne abbia
bisogno (titolo finestra, export, log...) non debbano duplicarlo.
"""

import os
import sys

APP_NAME = "SoundText"
APP_VERSION = "1.19.0"
# Pagina per sostenere il progetto (donazioni), aperta da Aiuto -> Sostieni
# SoundText...; vuota = la voce non c'e'.
SUPPORT_URL = "https://ko-fi.com/openssound"


def macos_app_resources() -> str:
    """Contents/Resources di SoundText.app quando SoundText gira dall'app
    per macOS (packaging/macos), dove stanno assets/, docs/, locales/...;
    '' altrimenti. L'eseguibile e' in Contents/MacOS."""
    if not getattr(sys, "frozen", False) or sys.platform != "darwin":
        return ""
    resources = os.path.normpath(os.path.join(os.path.dirname(sys.executable), "..", "Resources"))
    return resources if os.path.isdir(os.path.join(resources, "assets")) else ""


def get_app_root() -> str:
    """Cartella radice dell'app, da cui si ricavano assets/, docs/, songs/,
    midi/, soundfonts/: quella dell'eseguibile quando SoundText e'
    impacchettato con PyInstaller (sys.frozen None e __file__ non
    corrisponde piu' a un percorso reale su disco), Contents/Resources
    nell'app per macOS, altrimenti la cartella del repository/installazione
    sorgente (due livelli sopra core/)."""
    resources = macos_app_resources()
    if resources:
        return resources
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Dove vanno progetti, SoundFont, libreria MIDI... quando la cartella
# dell'app non e' scrivibile (o, sul Mac, non si deve scrivere: vedi
# pick_writable_dir). Nell'app per macOS in Documenti, dove un utente Mac
# cerca i propri file (e rientra nei backup di iCloud).
USER_DATA_ROOT = os.path.join(os.path.expanduser("~"), "Documents" if macos_app_resources() else "", "SoundText")


def pick_writable_dir(preferred: str, fallback: str) -> str:
    """Ritorna 'preferred' (creandola se serve) se ci si puo' scrivere,
    altrimenti 'fallback' (creata). Serve per songs/, midi/ e soundfonts/
    accanto all'app: in un AppImage l'eseguibile gira da un mount di sola
    lettura, e in un'installazione di sistema puo' mancare il permesso di
    scrittura - li' salvare/importare fallirebbe. Mai dentro SoundText.app,
    anche se il disco lo permetterebbe: romperebbe la firma dell'app, e un
    aggiornamento (app nuova al posto della vecchia) cancellerebbe i file."""
    resources = macos_app_resources()
    app = os.path.dirname(os.path.dirname(resources)) if resources else ""
    inside_app = bool(app) and os.path.commonpath([os.path.abspath(preferred), app]) == app
    try:
        if inside_app:
            raise OSError("dentro SoundText.app")
        os.makedirs(preferred, exist_ok=True)
        if os.access(preferred, os.W_OK):
            return preferred
    except OSError:
        pass
    os.makedirs(fallback, exist_ok=True)
    return fallback
