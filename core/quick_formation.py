"""
La formazione di «Un brano in 60 secondi»: invece di una delle cinque formazioni fisse (organico), si scelgono i singoli
strumenti, fra tutti quelli disponibili (i 128 General MIDI, la batteria e quelli di «Gestione strumenti»): «solo
chitarra», «chitarra, basso e batteria», «sax, piano, basso e batteria», «solo basso».

Ogni strumento ha un ruolo, dal suo numero General MIDI: accordi (pianoforti, organi, chitarre...), basso, melodia
(archi solisti, fiati, synth lead...), tappeto (archi d'insieme, cori, synth pad), fiati d'insieme e batteria. Il ruolo
dice a quale parte del brano va (comp, comp2, pad, horn, melody, bass, drums); gli strumenti in piu' di quelli che una
parte puo' ospitare restano fuori, e il brano lo dice. Con una formazione scelta le parti che nessuno suona spariscono.
"""

import re
from typing import Dict, List, Optional, Tuple

from .i18n import tr

DRUMS = "Drums"                      # la batteria: il kit lo sceglie il genere

# (primo programma, ultimo programma, ruolo) dei 128 suoni General MIDI
_ROLES = (
    (0, 7, "chords"),        # pianoforti
    (8, 15, "melody"),       # percussioni intonate: celesta, vibrafono, marimba, xilofono...
    (16, 20, "chords"),      # organi
    (21, 21, "chords"),      # fisarmonica
    (22, 22, "melody"),      # armonica
    (23, 23, "chords"),      # fisarmonica tango
    (24, 31, "chords"),      # chitarre
    (32, 39, "bass"),
    (40, 42, "melody"),      # violino, viola, violoncello
    (43, 43, "bass"),        # contrabbasso
    (44, 44, "pad"),         # archi tremolo
    (45, 46, "chords"),      # archi pizzicati, arpa
    (47, 47, "melody"),      # timpani
    (48, 54, "pad"),         # archi d'insieme, cori
    (55, 55, "horn"),        # orchestra hit
    (56, 59, "melody"),      # tromba, trombone, tuba, tromba con sordina
    (60, 63, "horn"),        # corno e sezioni d'ottoni
    (64, 79, "melody"),      # ance e fiati
    (80, 87, "melody"),      # synth lead
    (88, 103, "pad"),        # synth pad e fx
    (104, 104, "melody"),    # sitar
    (105, 105, "chords"),    # banjo
    (106, 111, "melody"),    # shamisen, koto, kalimba, cornamusa, violino popolare, shanai
    (112, 119, "melody"),    # percussivi
    (120, 127, "pad"),       # effetti sonori
)

# le parti dove puo' finire uno strumento di un ruolo, in ordine di preferenza
_PARTS_FOR_ROLE = {
    "chords": ("comp", "comp2", "pad"),
    "pad": ("pad", "comp2", "comp"),
    "melody": ("melody", "horn"),
    "horn": ("horn", "melody"),
    "bass": ("bass",),
    "drums": ("drums",),
}



def token(name: str) -> str:
    """Il nome come si scrive nell'intestazione di una traccia («Acoustic Guitar (nylon)» -> «Acoustic_Guitar_nylon»)."""
    return re.sub(r"[^\w]+", "_", name).strip("_")


def role_of_program(program: int) -> str:
    for low, high, role in _ROLES:
        if low <= program <= high:
            return role
    return "melody"


def role_of(name: str) -> Optional[str]:
    """Il ruolo di uno strumento (per nome: General MIDI, alias, o uno di «Gestione strumenti»); None se non si conosce."""
    if token(name) == DRUMS:
        return "drums"
    from .instruments import get_instrument, make_instrument_available
    try:
        make_instrument_available(name)
        profile = get_instrument(name)
    except Exception:
        profile = None
    if profile is None:
        from st_language.instruments import instrument_for, is_instrument_name
        if not is_instrument_name(name):                # instrument_for() prova anche i nomi simili: qui no
            return None
        try:
            profile = instrument_for(name)
        except Exception:
            return None
    if profile is None or not getattr(profile, "resolved", True):         # un nome che nessuno strumento riconosce
        return None
    if profile.is_percussion:
        return "drums"
    return role_of_program(profile.gm_program)


def catalog() -> List[dict]:
    """Tutti gli strumenti da proporre, a gruppi: [{label, instruments: [{value, label, role}]}]. Le famiglie General
    MIDI nell'ordine del programma, la batteria, e gli strumenti personalizzati di «Gestione strumenti»."""
    from st_language.instruments import gm_instrument_catalog
    groups: Dict[str, dict] = {}
    for program, name, family in gm_instrument_catalog():
        group = groups.setdefault(family, {"label": tr(family), "instruments": []})
        group["instruments"].append({"value": token(name), "label": tr(name), "role": role_of_program(program)})
    out = [{"label": tr("Batteria"), "instruments": [{"value": DRUMS, "label": tr("Batteria"), "role": "drums"}]}]
    out += list(groups.values())
    from .instruments import DEFAULT_INSTRUMENTS, list_instrument_names
    known = {i["value"] for g in out for i in g["instruments"]}
    custom = []
    for name in list_instrument_names():
        if name in DEFAULT_INSTRUMENTS or token(name) in known:
            continue
        role = role_of(name)
        if role:
            custom.append({"value": name, "label": name, "role": role})
    if custom:
        out.append({"label": tr("I miei strumenti"), "instruments": custom})
    return out


def role_label(role: str) -> str:
    """Il ruolo in parole, nella lingua dell'interfaccia."""
    return {"chords": tr("accordi"), "pad": tr("tappeto"), "melody": tr("melodia"), "horn": tr("fiati d'insieme"),
            "bass": tr("basso"), "drums": tr("batteria")}[role]


def assign(names: List[str]) -> Tuple[Dict[str, str], List[str]]:
    """({parte: strumento}, strumenti lasciati fuori) per l'elenco scelto. ValueError se uno strumento non si conosce o
    se l'elenco e' vuoto."""
    if not names:
        raise ValueError(tr("la formazione e' vuota: scegli almeno uno strumento"))
    parts: Dict[str, str] = {}
    left_out: List[str] = []
    seen = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        role = role_of(name)
        if role is None:
            raise ValueError(tr("strumento sconosciuto nella formazione: {name}", name=name))
        for part in _PARTS_FOR_ROLE[role]:
            if part not in parts:
                parts[part] = DRUMS if role == "drums" else name
                break
        else:
            left_out.append(name)
    return parts, left_out


def describe(parts: Dict[str, str]) -> str:
    """Gli strumenti della formazione in una riga, nell'ordine delle parti."""
    order = ("comp", "comp2", "pad", "horn", "melody", "bass", "drums")
    return ", ".join(parts[p].replace("_", " ") for p in order if p in parts)
