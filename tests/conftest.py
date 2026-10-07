# Isola i test dalla configurazione dell'utente prima che qualunque test importi core.
import _config_isolation  # noqa: F401

import os

# Qt senza schermo in tutti i test (anche quelli che non creano finestre ma
# usano Qt Multimedia, vedi core.audio_decode)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
