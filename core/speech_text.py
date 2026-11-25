"""«Leggi» (core/speech_text.py, per il telefono e per il computer): la frase che dice a voce la battuta (o il pattern, o la riga) sotto il cursore, in parole: «Battuta 3,
Piano. Do croma, Re croma, Mi minima, accordo La minore semibreve». E' il contrario della dettatura
(core.dictation): quella scrive la musica da una frase, questa la dice. Le parole sono nelle quattro lingue
dell'interfaccia; l'app (app/speak.js) legge la frase con la sintesi vocale, o la mette in una regione aria-live
se c'e' uno screen reader.
"""
import re
from typing import List, Optional

from st_language.instruments import PERCUSSION_ALIASES

LANGUAGES = ("it", "en", "fr", "es")

NOTES = {
    "it": ["do", "re", "mi", "fa", "sol", "la", "si"],
    "en": ["C", "D", "E", "F", "G", "A", "B"],
    "fr": ["do", "ré", "mi", "fa", "sol", "la", "si"],
    "es": ["do", "re", "mi", "fa", "sol", "la", "si"],
}
LETTERS = "cdefgab"
SHARP = {"it": "diesis", "en": "sharp", "fr": "dièse", "es": "sostenido"}
FLAT = {"it": "bemolle", "en": "flat", "fr": "bémol", "es": "bemol"}

# durata in battiti (quarti): nome per ogni lingua
DURATIONS = [
    (4.0, {"it": "semibreve", "en": "whole note", "fr": "ronde", "es": "redonda"}),
    (2.0, {"it": "minima", "en": "half note", "fr": "blanche", "es": "blanca"}),
    (1.0, {"it": "semiminima", "en": "quarter note", "fr": "noire", "es": "negra"}),
    (0.5, {"it": "croma", "en": "eighth note", "fr": "croche", "es": "corchea"}),
    (0.25, {"it": "semicroma", "en": "sixteenth note", "fr": "double croche", "es": "semicorchea"}),
    (0.125, {"it": "biscroma", "en": "thirty-second note", "fr": "triple croche", "es": "fusa"}),
]
DOTTED = {"it": "puntata", "en": "dotted", "fr": "pointée", "es": "con puntillo"}
BEATS = {"it": "{n} battiti", "en": "{n} beats", "fr": "{n} temps", "es": "{n} tiempos"}
REST = {"it": "pausa", "en": "rest", "fr": "silence", "es": "silencio"}
CHORD = {"it": "accordo", "en": "chord", "fr": "accord", "es": "acorde"}
PATTERN = {"it": "pattern", "en": "pattern", "fr": "motif", "es": "patrón"}
BAR = {"it": "Battuta {n}", "en": "Bar {n}", "fr": "Mesure {n}", "es": "Compás {n}"}
NOTHING = {"it": "Qui non c'è nulla da leggere.", "en": "There is nothing to read here.",
           "fr": "Il n'y a rien à lire ici.", "es": "Aquí no hay nada que leer."}

# la qualita' dell'accordo, nel modo in cui si scrive (dopo la radice)
QUALITIES = {
    "": {"it": "", "en": "", "fr": "", "es": ""},
    "m": {"it": "minore", "en": "minor", "fr": "mineur", "es": "menor"},
    "7": {"it": "settima", "en": "seventh", "fr": "septième", "es": "séptima"},
    "maj7": {"it": "maggiore settima", "en": "major seventh", "fr": "septième majeure", "es": "séptima mayor"},
    "m7": {"it": "minore settima", "en": "minor seventh", "fr": "mineur septième", "es": "menor séptima"},
    "6": {"it": "sesta", "en": "sixth", "fr": "sixte", "es": "sexta"},
    "m6": {"it": "minore sesta", "en": "minor sixth", "fr": "mineur sixte", "es": "menor sexta"},
    "9": {"it": "nona", "en": "ninth", "fr": "neuvième", "es": "novena"},
    "maj9": {"it": "maggiore nona", "en": "major ninth", "fr": "neuvième majeure", "es": "novena mayor"},
    "m9": {"it": "minore nona", "en": "minor ninth", "fr": "mineur neuvième", "es": "menor novena"},
    "11": {"it": "undicesima", "en": "eleventh", "fr": "onzième", "es": "oncena"},
    "13": {"it": "tredicesima", "en": "thirteenth", "fr": "treizième", "es": "trecena"},
    "dim": {"it": "diminuito", "en": "diminished", "fr": "diminué", "es": "disminuido"},
    "dim7": {"it": "diminuito settima", "en": "diminished seventh", "fr": "diminué septième", "es": "disminuido séptima"},
    "m7b5": {"it": "semidiminuito", "en": "half diminished", "fr": "semi-diminué", "es": "semidisminuido"},
    "aug": {"it": "aumentato", "en": "augmented", "fr": "augmenté", "es": "aumentado"},
    "sus4": {"it": "sospeso quarta", "en": "suspended fourth", "fr": "suspendu quarte", "es": "suspendido cuarta"},
    "sus2": {"it": "sospeso seconda", "en": "suspended second", "fr": "suspendu seconde", "es": "suspendido segunda"},
    "sus": {"it": "sospeso", "en": "suspended", "fr": "suspendu", "es": "suspendido"},
    "5": {"it": "quinta", "en": "fifth", "fr": "quinte", "es": "quinta"},
    "add9": {"it": "con nona aggiunta", "en": "add nine", "fr": "avec neuvième ajoutée", "es": "con novena añadida"},
}

_NOTE = re.compile(r"^(\d+)?([a-g])([#♯b♭])?(?:\*(-?\d+))?(?![A-Za-z_#♯])")
_CHORD = re.compile(r"^(\d+)?([A-G])([#♯b♭])?([^/!.'<>~\s]*)(?:/([A-G])([#♯b♭])?)?")
_REST = re.compile(r"^(\d+)?r$")


def _lang(lang: Optional[str]) -> str:
    lang = (lang or "it")[:2].lower()
    return lang if lang in LANGUAGES else "en"


def duration_words(beats: float, lang: str) -> str:
    """La durata in parole: la figura (anche puntata), altrimenti i battiti."""
    for value, names in DURATIONS:
        if abs(beats - value) < 1e-6:
            return names[lang]
        if abs(beats - value * 1.5) < 1e-6:
            return f"{names[lang]} {DOTTED[lang]}" if lang in ("it", "es", "fr") and lang != "en" else f"{DOTTED[lang]} {names[lang]}"
    shown = f"{beats:g}".replace(".", ",") if lang in ("it", "fr", "es") else f"{beats:g}"
    return BEATS[lang].format(n=shown)


def _pitch_name(letter: str, accidental: str, lang: str) -> str:
    name = NOTES[lang][LETTERS.index(letter.lower())]
    if lang == "en":
        name = letter.upper()
    if accidental in ("#", "♯"):
        return f"{name} {SHARP[lang]}"
    if accidental in ("b", "♭"):
        return f"{name} {FLAT[lang]}"
    return name


def _quality_words(quality: str, lang: str) -> str:
    quality = quality.replace("min", "m").replace("M", "maj") if quality not in QUALITIES else quality
    if quality in QUALITIES:
        return QUALITIES[quality][lang]
    return " ".join(quality)                                          # una sigla rara: si sillaba


def _percussion_words(token: str) -> str:
    """Il nome di una percussione in parole: un'abbreviazione (bd, hh, sn) si
    legge col nome intero (kick, hihat, snare)."""
    mult = re.match(r"^\d+", token)
    name = token[mult.end():] if mult else token
    return (mult.group() if mult else "") + PERCUSSION_ALIASES.get(name, name).replace("_", " ")


def token_words(token: str, beats: Optional[float], lang: str) -> Optional[str]:
    """Un token della notazione in parole, con la durata se si conosce; None se non si sa leggere."""
    lang = _lang(lang)
    tail = f" {duration_words(beats, lang)}" if beats else ""
    if token.startswith("%"):
        return f"{PATTERN[lang]} {token[1:]}"
    if token.startswith("["):
        inner = [w for w in re.findall(r"[^\s\[\]]+", token)]
        return " ".join(_percussion_words(w) for w in inner) + tail
    if _REST.match(token):
        return REST[lang] + tail
    m = _NOTE.match(token)
    if m:
        return _pitch_name(m.group(2), m.group(3) or "", lang) + tail
    m = _CHORD.match(token)
    if m:
        quality = _quality_words(m.group(4), lang)
        words = f"{CHORD[lang]} {_pitch_name(m.group(2), m.group(3) or '', lang)}" + (f" {quality}" if quality else "")
        if m.group(5):
            words += {"it": " con basso ", "en": " over ", "fr": " avec basse ", "es": " con bajo "}[lang] + _pitch_name(m.group(5), m.group(6) or "", lang)
        return words + tail
    if re.match(r"^\w+$", token):
        return _percussion_words(token) + tail                        # una percussione: kick, snare...
    return None


def phrase(items: List[tuple], lang: str, bar: Optional[int] = None, track: Optional[str] = None) -> str:
    """(token, durata o None) -> la frase."""
    lang = _lang(lang)
    words = [w for w in (token_words(t, d, lang) for t, d in items) if w]
    if not words:
        return NOTHING[lang]
    head = ""
    if bar is not None:
        head = BAR[lang].format(n=bar) + (f", {track}" if track else "") + ". "
    return head + ", ".join(words) + "."
