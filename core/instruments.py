"""
Profili strumento e mappa percussioni.
Ogni strumento definisce come il motore di voicing e l'export MIDI
devono interpretare accordi astratti e note.

Oltre ai 5 strumenti di base dell'MVP, l'utente puo' definire strumenti
personalizzati (funzionalita' 1): vengono salvati in
~/.config/soundtext/instruments.json su Linux (%APPDATA%/SoundText/ su
Windows, ~/Library/Application Support/SoundText/ su macOS) e uniti a
quelli predefiniti.
"""

import json
import os
from dataclasses import asdict
from typing import Optional, Dict, List
from .i18n import tr


# Strumenti e percussioni della notazione: definiti nella libreria
# st_language (usabile anche senza SoundText), qui riesportati.
from st_language.instruments import (  # noqa: F401
    PERCUSSION_MAP, DRUM_MIDI_CHANNEL, GM_FAMILIES, GM_FAMILY_DEFAULTS, GM_DRUM_KITS,
    gm_instrument_catalog, gm_family_for_program, InstrumentProfile, DEFAULT_INSTRUMENTS,
    INSTRUMENT_TYPE_ALIASES, PERCUSSION_TYPE_ALIASES, resolve_instrument_type,
    suggest_instrument, unknown_instrument_message, unrecognized_header_message,
)


from .settings import CONFIG_DIR, write_json_atomic  # cartella di configurazione (vedi li' SOUNDTEXT_CONFIG_DIR)
CUSTOM_INSTRUMENTS_FILE = os.path.join(CONFIG_DIR, "instruments.json")

_custom_cache: Optional[Dict[str, InstrumentProfile]] = None


def _load_custom_instruments() -> Dict[str, InstrumentProfile]:
    global _custom_cache
    if _custom_cache is not None:
        return _custom_cache
    result = {}
    if os.path.exists(CUSTOM_INSTRUMENTS_FILE):
        try:
            with open(CUSTOM_INSTRUMENTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for name, d in data.items():
                result[name] = InstrumentProfile(**d)
        except (json.JSONDecodeError, TypeError, OSError):
            result = {}
    _custom_cache = result
    return result


def _save_custom_instruments():
    write_json_atomic(CUSTOM_INSTRUMENTS_FILE, {name: asdict(p) for name, p in _custom_cache.items()})


def all_instruments() -> Dict[str, InstrumentProfile]:
    """Unione degli strumenti predefiniti e di quelli personalizzati
    dall'utente, con l'eventuale kit percussioni scelto per uno strumento a
    percussioni (vedi Gestione strumenti, core.settings.get_drum_kit_override)
    applicato sopra al suo gm_program - unico campo che si puo' cambiare
    anche per uno strumento predefinito come 'Drums', tutti gli altri
    restano fissi per i predefiniti."""
    merged = dict(DEFAULT_INSTRUMENTS)
    merged.update(_opened_instruments)
    merged.update(_load_custom_instruments())
    from .settings import get_all_drum_kit_overrides
    overrides = get_all_drum_kit_overrides()
    for name, program in overrides.items():
        instr = merged.get(name)
        if instr is not None and instr.is_percussion and instr.gm_program != program:
            merged[name] = InstrumentProfile(**{**instr.__dict__, "gm_program": program})
    return merged


# Ordine con cui raggruppare gli strumenti (non i singoli suoni GM) nelle
# liste della GUI (Gestione strumenti, scelta strumento per una traccia,
# ...), cosi' che strumenti simili restino vicini (fiati vicino ad altri
# fiati, corde vicino ad altre corde, tastiere vicino ad altre tastiere,
# ...) invece di seguire l'ordine di creazione. Le percussioni (canale 10,
# non hanno una famiglia GM) vanno per ultime, in un gruppo a parte.
_INSTRUMENT_GROUP_ORDER = [family for family, _start, _names in GM_FAMILIES] + ["Percussioni"]


def _instrument_group(profile: InstrumentProfile) -> str:
    return "Percussioni" if profile.is_percussion else gm_family_for_program(profile.gm_program)


def sorted_instrument_names(names=None) -> List[str]:
    """Nomi strumento ordinati per famiglia (vedi _INSTRUMENT_GROUP_ORDER),
    poi alfabeticamente all'interno della stessa famiglia: usato per
    popolare le liste della GUI mantenendo vicini gli strumenti simili,
    invece del semplice ordine di creazione (predefiniti, poi personalizzati
    nell'ordine in cui sono stati aggiunti)."""
    catalog = all_instruments()
    if names is None:
        names = catalog.keys()

    def _key(name):
        group = _instrument_group(catalog[name])
        rank = _INSTRUMENT_GROUP_ORDER.index(group) if group in _INSTRUMENT_GROUP_ORDER \
            else len(_INSTRUMENT_GROUP_ORDER)
        return (rank, name.lower())

    return sorted(names, key=_key)


def list_instrument_names():
    return sorted_instrument_names()


# Strumenti arrivati aprendo un brano (definiti nel file, o nominati in
# un'intestazione e riconosciuti dalla libreria): valgono fino alla chiusura
# del programma e non si scrivono in instruments.json. Aprire un brano non
# deve cambiare la configurazione dell'utente; alla prossima apertura dello
# stesso brano tornano da soli. Quelli salvati dall'utente (Gestione
# strumenti, import MIDI confermato) vincono su questi.
_opened_instruments: Dict[str, InstrumentProfile] = {}


def add_custom_instrument(profile: InstrumentProfile):
    if profile.name in DEFAULT_INSTRUMENTS:
        raise ValueError(tr("'{name}' e' gia' uno strumento predefinito: scegli un altro nome.", name=profile.name))
    _load_custom_instruments()
    _custom_cache[profile.name] = profile
    _save_custom_instruments()


def remove_custom_instrument(name: str):
    _load_custom_instruments()
    if name in DEFAULT_INSTRUMENTS:
        raise ValueError(tr("'{name}' e' uno strumento predefinito e non puo' essere rimosso.", name=name))
    _opened_instruments.pop(name, None)
    if name in _custom_cache:
        del _custom_cache[name]
        _save_custom_instruments()


def is_custom_instrument(name: str) -> bool:
    return name not in DEFAULT_INSTRUMENTS


def replace_custom_instrument(profile: InstrumentProfile):
    """Sostituisce (o aggiunge) lo strumento personalizzato con quel nome."""
    _load_custom_instruments()
    _custom_cache[profile.name] = profile
    _save_custom_instruments()


def ensure_instrument_available(profile: InstrumentProfile) -> bool:
    """Rende disponibile, per questa sessione, uno strumento personalizzato
    che non lo e' gia' (funzionalita': caricamento automatico degli strumenti
    incorporati in un file .st). Non lo salva in instruments.json (vedi
    _opened_instruments). Non sovrascrive mai:
      - uno strumento predefinito con lo stesso nome (i predefiniti vincono sempre);
      - uno strumento personalizzato gia' presente in locale (non tocca eventuali
        modifiche manuali dell'utente).
    Ritorna True se lo strumento e' stato effettivamente registrato ora."""
    if profile.name in DEFAULT_INSTRUMENTS or not profile.resolved:
        return False
    _load_custom_instruments()
    if profile.name in _custom_cache or profile.name in _opened_instruments:
        return False
    _opened_instruments[profile.name] = profile
    return True


def resolve_or_create_instrument_by_program(program: Optional[int], is_percussion: bool) -> str:
    """Come una ricerca per Program Change GM, ma se nessuno strumento
    esistente (predefinito o personalizzato) ha esattamente quel programma,
    ne crea e registra automaticamente uno nuovo (nome derivato dal nome
    ufficiale General MIDI, parametri suggeriti per famiglia — stessa
    logica di resolve_instrument_type), cosi' l'import MIDI riflette
    fedelmente lo strumento della traccia originale invece di limitarsi al
    piu' vicino gia' disponibile. Ritorna il nome dello strumento (nuovo o
    esistente). Usata solo per un'importazione MIDI effettivamente
    confermata dall'utente, mai per semplici anteprime/suggerimenti."""
    if is_percussion:
        for name, instr in all_instruments().items():
            if instr.is_percussion:
                return name
        return "Drums"

    if program is None:
        return "Piano"

    for name, instr in all_instruments().items():
        if not instr.is_percussion and instr.gm_program == program:
            return name

    gm_name = next((n for p, n, _fam in gm_instrument_catalog() if p == program), f"GM{program}")
    base_name = "".join(ch for ch in gm_name if ch.isalnum()) or f"GM{program}"
    existing = all_instruments()
    name = base_name
    i = 1
    while name in existing:
        i += 1
        name = f"{base_name}{i}"

    family = gm_family_for_program(program)
    defaults = GM_FAMILY_DEFAULTS.get(family, {})
    profile = InstrumentProfile(
        name=name, gm_program=program, is_percussion=False,
        default_octave=defaults.get("default_octave", 4),
        range_low=defaults.get("range_low", 40),
        range_high=defaults.get("range_high", 88),
        polyphonic=defaults.get("polyphonic", True),
        voicing_style=defaults.get("voicing_style", "spread"),
    )
    add_custom_instrument(profile)
    return name


# Strumenti definiti nel brano aperto nella finestra principale (vedi
# core.model.Project.instruments): le anteprime costruiscono progetti
# provvisori con il solo nome dello strumento, e cosi' suonano comunque come
# il brano invece che come lo strumento omonimo registrato in locale.
_session_instruments: Dict[str, InstrumentProfile] = {}


def set_session_instruments(instruments: Optional[Dict[str, InstrumentProfile]]):
    """Gli strumenti del brano aperto (Project.instruments), o None/{}."""
    global _session_instruments
    _session_instruments = dict(instruments or {})


# Strumenti nominati da un brano che la libreria non riconosce (resolved
# falso, dalla 2.11 di st-language): suonano come pianoforte solo per questa
# sessione e non vanno in instruments.json, cosi' l'avviso torna a ogni
# apertura invece di sparire dopo la prima (vedi core.project_io).
_unresolved_instruments: Dict[str, InstrumentProfile] = {}


def register_unresolved_instrument(profile: InstrumentProfile):
    _unresolved_instruments[profile.name] = profile


def instrument_suggestion(name: str) -> Optional[str]:
    """Il nome con cui correggere lo strumento sconosciuto 'name': quello
    noto piu' simile (suggest_instrument), scritto come uno strumento gia'
    disponibile se ce n'e' uno uguale a meno delle maiuscole, altrimenti con
    l'iniziale maiuscola come le intestazioni di traccia. None se non c'e'."""
    suggestion = suggest_instrument(name)
    if not suggestion:
        return None
    for known in all_instruments():
        if known.lower() == suggestion.lower():
            return known
    return suggestion[:1].upper() + suggestion[1:]


def make_instrument_available(name: str) -> bool:
    """Rende 'name' usabile come strumento di una traccia, come la lettura
    di "Traccia Nome [Strumento]:": se non e' gia' disponibile e la libreria
    lo riconosce lo registra, altrimenti lo fa suonare come pianoforte per
    la sola sessione. Ritorna False se il nome non si riconosce."""
    if name in all_instruments():
        return True
    profile = resolve_instrument_type(name, name)
    if profile.resolved:
        ensure_instrument_available(profile)
        return True
    register_unresolved_instrument(profile)
    return False


# Il profilo con cui le versioni prima della 2.11 di st-language salvavano
# in instruments.json un nome che non riconoscevano (il pianoforte), e il
# programma del fagotto, dove finivano nomi come 'Basso'.
_LEGACY_FALLBACK = dict(gm_program=0, is_percussion=False, default_octave=4, range_low=21,
                        range_high=108, polyphonic=True, voicing_style="spread", transposition=0)
_LEGACY_BASSOON_PROGRAM = 70


def legacy_instrument_fix(profile: InstrumentProfile) -> Optional[InstrumentProfile]:
    """Se 'profile' e' un ripiego delle versioni vecchie (il pianoforte del
    nome sconosciuto, o il fagotto) e la libreria ora riconosce il suo nome
    come un altro strumento, il profilo nuovo; altrimenti None."""
    if profile.is_percussion:
        return None
    fresh = resolve_instrument_type(profile.name, profile.name)
    if not fresh.resolved:
        return None
    if all(getattr(profile, key) == value for key, value in _LEGACY_FALLBACK.items()):
        changed = fresh.is_percussion or fresh.gm_program != 0
    elif profile.gm_program == _LEGACY_BASSOON_PROGRAM:
        changed = fresh.is_percussion or fresh.gm_program != _LEGACY_BASSOON_PROGRAM
    else:
        return None
    return fresh if changed else None


def pending_instrument_fixes(declined=()) -> List[InstrumentProfile]:
    """Gli strumenti personalizzati salvati come ripiego da correggere (vedi
    legacy_instrument_fix), tranne quelli in 'declined': i profili nuovi."""
    fixes = []
    for name, profile in _load_custom_instruments().items():
        if name in declined or name in DEFAULT_INSTRUMENTS:
            continue
        fresh = legacy_instrument_fix(profile)
        if fresh is not None:
            fixes.append(fresh)
    return fixes


def get_instrument(name: str) -> InstrumentProfile:
    if name in _session_instruments:
        return InstrumentProfile(**_session_instruments[name].__dict__)
    catalog = all_instruments()
    if name not in catalog and name in _unresolved_instruments:
        return InstrumentProfile(**_unresolved_instruments[name].__dict__)
    if name not in catalog:
        raise ValueError(
            tr("Strumento sconosciuto: '{name}'. Disponibili: {0}", ', '.join(catalog), name=name)
        )
    # Restituisce una copia indipendente (dataclass e' mutabile)
    src = catalog[name]
    return InstrumentProfile(**src.__dict__)
