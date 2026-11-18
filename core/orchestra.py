"""
Il file dell'orchestra (VSCO 2 CE e VCSL, gruppi ORCHESTRA di
scarica_strumenti.py) adatto allo strumento di una traccia: la finestra
"Strumento plugin" lo propone accanto allo strumento SFZ interno, per
esempio una traccia [Flauto] (programma GM 73) -> FluteSusVib.sfz del
gruppo vsco-legni. Il suono sostenuto di base, non le articolazioni
(staccato, pizzicato...), che restano da scegliere a mano.
"""

import os
from dataclasses import dataclass
from typing import Optional

from .downloads import _split, load_script
from .i18n import tr

_IDIOFONI = "Idiophones/Struck Idiophones/"

# programma General MIDI -> (gruppo, file .sfz nel gruppo)
FILE_PER_PROGRAMMA = {
    6: ("vcsl-clavicembalo", "Chordophones/Zithers/Harpsichord, Flemish - 8'.sfz"),
    9: ("vsco-percussioni", "Glockenspiel.sfz"),
    11: ("vcsl-vibrafono", _IDIOFONI + "Vibraphone - Soft Mallets.sfz"),
    12: ("vsco-percussioni", "Marimba.sfz"),
    13: ("vsco-percussioni", "Xylophone.sfz"),
    14: ("vsco-percussioni", "TubularBells.sfz"),
    40: ("vsco-archi", "SViolinVib.sfz"),
    41: ("vsco-archi", "ViolaEnsSusVib.sfz"),
    42: ("vsco-archi", "CelloEnsSusVib.sfz"),
    43: ("vsco-archi", "ContrabassSusVB.sfz"),
    44: ("vsco-archi", "ViolinEnsTrem.sfz"),
    45: ("vsco-archi", "ViolinEnsPizz.sfz"),
    46: ("vsco-percussioni", "Harp.sfz"),
    47: ("vsco-percussioni", "Timpani.sfz"),
    48: ("vsco-archi", "ViolinEnsSusVib.sfz"),
    49: ("vsco-archi", "ViolinEnsSusVib.sfz"),
    56: ("vsco-ottoni", "TrumpetSus.sfz"),
    57: ("vsco-ottoni", "TromboneSus.sfz"),
    58: ("vsco-ottoni", "TubaSus.sfz"),
    59: ("vsco-ottoni", "TrumpetStraightMuteSus.sfz"),
    60: ("vsco-ottoni", "FHornSus.sfz"),
    68: ("vsco-legni", "OboeSusVib.sfz"),
    70: ("vsco-legni", "BassoonSus.sfz"),
    71: ("vsco-legni", "ClarinetSus.sfz"),
    72: ("vsco-legni", "PiccoloSus.sfz"),
    73: ("vsco-legni", "FluteSusVib.sfz"),
}


@dataclass
class Proposta:
    group: str           # il gruppo di scarica_strumenti ("vsco-legni")
    group_label: str     # come lo chiama "Scarica e installa", tradotto
    path: str            # dove sta (o starebbe) il file .sfz
    installed: bool      # il gruppo e' scaricato tutto e il file c'e'

    @property
    def file_name(self) -> str:
        return os.path.basename(self.path)


def proposta_per(profile) -> Optional[Proposta]:
    """Il file dell'orchestra per lo strumento 'profile' (InstrumentProfile),
    o None se l'orchestra non ne ha uno (percussioni, chitarre...) o
    scarica_strumenti.py non c'e'."""
    if profile is None or profile.is_percussion or profile.gm_program not in FILE_PER_PROGRAMMA:
        return None
    script = load_script()
    if script is None:
        return None
    group, sfz = FILE_PER_PROGRAMMA[profile.gm_program]
    voce = script.trova(group)
    if voce is None:
        return None
    _name, desc, _url, sub = voce
    folder = script.DEST / sub / group
    path = folder / sfz
    return Proposta(group, tr(_split(desc)[0]), str(path),
                    (folder / ".completo").exists() and path.is_file())
