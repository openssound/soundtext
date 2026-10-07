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
)


from .settings import CONFIG_DIR  # cartella di configurazione (vedi li' SOUNDTEXT_CONFIG_DIR)
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
    os.makedirs(CONFIG_DIR, exist_ok=True)
    data = {name: asdict(p) for name, p in _custom_cache.items()}
    with open(CUSTOM_INSTRUMENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def all_instruments() -> Dict[str, InstrumentProfile]:
    """Unione degli strumenti predefiniti e di quelli personalizzati
    dall'utente, con l'eventuale kit percussioni scelto per uno strumento a
    percussioni (vedi Gestione strumenti, core.settings.get_drum_kit_override)
    applicato sopra al suo gm_program - unico campo che si puo' cambiare
    anche per uno strumento predefinito come 'Drums', tutti gli altri
    restano fissi per i predefiniti."""
    merged = dict(DEFAULT_INSTRUMENTS)
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
    if name in _custom_cache:
        del _custom_cache[name]
        _save_custom_instruments()


def is_custom_instrument(name: str) -> bool:
    return name not in DEFAULT_INSTRUMENTS


def ensure_instrument_available(profile: InstrumentProfile) -> bool:
    """Registra automaticamente uno strumento personalizzato se non e' gia'
    disponibile (funzionalita': caricamento automatico degli strumenti
    incorporati in un file .st). Non sovrascrive mai:
      - uno strumento predefinito con lo stesso nome (i predefiniti vincono sempre);
      - uno strumento personalizzato gia' presente in locale (non tocca eventuali
        modifiche manuali dell'utente).
    Ritorna True se lo strumento e' stato effettivamente registrato ora."""
    if profile.name in DEFAULT_INSTRUMENTS:
        return False
    _load_custom_instruments()
    if profile.name in _custom_cache:
        return False
    _custom_cache[profile.name] = profile
    _save_custom_instruments()
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


def get_instrument(name: str) -> InstrumentProfile:
    if name in _session_instruments:
        return InstrumentProfile(**_session_instruments[name].__dict__)
    catalog = all_instruments()
    if name not in catalog:
        raise ValueError(
            tr("Strumento sconosciuto: '{name}'. Disponibili: {0}", ', '.join(catalog), name=name)
        )
    # Restituisce una copia indipendente (dataclass e' mutabile)
    src = catalog[name]
    return InstrumentProfile(**src.__dict__)
