"""
Lingue dell'interfaccia: italiano (la lingua in cui e' scritto il
programma), inglese, francese e spagnolo.

I testi si scrivono nel codice in italiano, dentro tr():

    tr("Esporta MIDI...")
    tr("MIDI esportato: {path}", path=path)

tr() cerca il testo nel catalogo della lingua scelta (locales/<lingua>.json,
un dizionario {testo italiano: traduzione}) e, se c'e', usa la traduzione;
altrimenti resta l'italiano. I segnaposto {nome} si riempiono dopo la
traduzione, quindi una traduzione puo' spostarli dove serve alla sua
grammatica.

La lingua si sceglie in Opzioni -> Lingua e vale dal prossimo avvio: i
testi si traducono quando le finestre vengono create. Senza una scelta si
usa quella del sistema, se e' fra le quattro, altrimenti l'inglese. La
variabile d'ambiente SOUNDTEXT_LANGUAGE ha la precedenza (i test la
fissano all'italiano).

Non si traducono le parole del file .st (Tempo:, Traccia, Effetti...), i
nomi salvati nei progetti (preset, tipi di effetto) ne' la grammatica della
notazione: sono il formato dei file, uguale in tutte le lingue.
"""

import json
import locale
import os
from typing import Dict, Optional

LANGUAGES = {"it": "Italiano", "en": "English", "fr": "Français", "es": "Español"}
SOURCE_LANGUAGE = "it"
DEFAULT_FALLBACK = "en"

_language: Optional[str] = None
_catalog: Dict[str, str] = {}


def locales_dir() -> str:
    from .version import get_app_root
    return os.path.join(get_app_root(), "locales")


def system_language() -> str:
    """La lingua del sistema, se e' fra quelle disponibili, altrimenti
    l'inglese."""
    candidates = [os.environ.get(v, "") for v in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG")]
    try:
        candidates.append(locale.getlocale()[0] or "")
    except (ValueError, TypeError):
        pass
    for value in candidates:
        for part in value.split(":"):
            code = part.strip().lower()[:2]
            if code in LANGUAGES:
                return code
    return DEFAULT_FALLBACK


def configured_language() -> str:
    """La lingua da usare: variabile d'ambiente, poi Opzioni, poi sistema."""
    env = os.environ.get("SOUNDTEXT_LANGUAGE", "").strip().lower()
    if env in LANGUAGES:
        return env
    from .settings import get_language
    chosen = get_language()
    return chosen if chosen in LANGUAGES else system_language()


def load_catalog(language: str) -> Dict[str, str]:
    if language == SOURCE_LANGUAGE:
        return {}
    path = os.path.join(locales_dir(), f"{language}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in data.items() if isinstance(v, str) and v}


def set_language(language: str):
    """Attiva una lingua per questo processo (non la salva: vedi
    core.settings.set_language)."""
    global _language, _catalog
    _language = language if language in LANGUAGES else SOURCE_LANGUAGE
    _catalog = load_catalog(_language)


def current_language() -> str:
    if _language is None:
        set_language(configured_language())
    return _language


def tr(text: str, *args, **kwargs) -> str:
    """Il testo nella lingua dell'interfaccia, con i segnaposto riempiti."""
    if _language is None:
        current_language()
    out = _catalog.get(text, text)
    if args or kwargs:
        try:
            return out.format(*args, **kwargs)
        except (IndexError, KeyError, ValueError):
            return text.format(*args, **kwargs)
    return out


def localized_doc(path: str) -> str:
    """La versione tradotta di un documento (docs/HELP.md -> docs/HELP.en.md),
    se esiste, altrimenti l'originale italiano."""
    language = current_language()
    if language == SOURCE_LANGUAGE:
        return path
    base, ext = os.path.splitext(path)
    translated = f"{base}.{language}{ext}"
    return translated if os.path.exists(translated) else path
