"""
Questo modulo e' st_language.chords (accordi, voicing e altezze), che sta nella libreria
st_language perche' si possa usare anche senza SoundText (vedi
st_language/README.md): core.chords e' lo stesso modulo, con gli stessi
nomi, cosi' il resto del programma continua a importarlo da qui.
"""

import sys

from . import _st  # noqa: F401  (traduzioni e libreria MIDI per la notazione)
from st_language import chords as _module

sys.modules[__name__] = _module
