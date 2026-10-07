"""
Questo modulo e' st_language.timing (mappa di tempo e metrica), che sta nella libreria
st_language perche' si possa usare anche senza SoundText (vedi
st_language/README.md): core.tempo_map e' lo stesso modulo, con gli stessi
nomi, cosi' il resto del programma continua a importarlo da qui.
"""

import sys

from . import _st  # noqa: F401  (traduzioni e libreria MIDI per la notazione)
from st_language import timing as _module

sys.modules[__name__] = _module
