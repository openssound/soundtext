"""Isola i test dalla configurazione reale dell'utente.

Va importato PRIMA di qualunque modulo di 'core' (lo fanno tests/conftest.py per
pytest e gli script di test lanciati direttamente): imposta
SOUNDTEXT_CONFIG_DIR su una cartella temporanea, cosi' impostazioni, strumenti
personalizzati e suoni del metronomo dei test non toccano
~/.config/soundtext (prima gli import MIDI dei test vi registravano strumenti
e alcuni test azzeravano il percorso del SoundFont dell'utente, rendendo i test
successivi dipendenti dall'ordine e dai residui dei precedenti).
"""

import atexit
import os
import shutil
import sys
import tempfile

_ENV = "SOUNDTEXT_CONFIG_DIR"

# I test controllano i testi dell'interfaccia in italiano, la lingua in cui
# e' scritto il programma (vedi core.i18n): la si fissa qui, qualunque sia
# la lingua del sistema.
os.environ.setdefault("SOUNDTEXT_LANGUAGE", "it")


def _remove_config_dir(path):
    """Toglie la cartella temporanea a fine test. Prima chiude le sessioni di
    recupero (core.autosave) delle finestre rimaste aperte: i loro QLockFile si
    sbloccherebbero solo alla chiusura di Python, a cartella gia' tolta,
    stampando "Could not remove our own lock file" per ciascuna."""
    autosave = sys.modules.get("core.autosave")
    if autosave is not None:
        import gc
        for obj in gc.get_objects():
            if isinstance(obj, autosave.RecoverySession):
                obj.close()
    shutil.rmtree(path, ignore_errors=True)


if _ENV not in os.environ:
    _dir = tempfile.mkdtemp(prefix="soundtext-test-config-")
    os.environ[_ENV] = _dir
    atexit.register(_remove_config_dir, _dir)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import settings as _settings  # noqa: E402

assert os.path.abspath(_settings.CONFIG_DIR) == os.path.abspath(os.environ[_ENV]), (
    "l'isolamento della configurazione dei test non e' attivo: un modulo di core "
    "e' stato importato prima di tests/_config_isolation.py"
)
