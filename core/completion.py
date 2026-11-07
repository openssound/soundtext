"""
Motore di suggerimenti per l'autocompletamento dei token nell'editor
(gui.voicing_picker.NotationEditor). Logica pura di testo, senza
dipendenze da Qt: dato il frammento di token gia' digitato (dall'inizio
della "parola" corrente fino al cursore), ritorna la lista dei token
COMPLETI pertinenti, per velocizzare la digitazione delle notazioni piu'
lunghe o meno immediate da ricordare a memoria (qualita' d'accordo, stili
di voicing, nomi di percussioni/dinamiche, riferimenti %pattern e &midi,
funzioni sui pattern e tipi di arpeggio).

Le note singole (es. 'c', 'g#*4') non generano suggerimenti propri: sono
gia' brevi quanto un suggerimento. La lettera minuscola sola resta pero'
un prefisso valido per i nomi di percussione che iniziano allo stesso modo
(es. 'c' -> 'crash'), gestito da _LOWERCASE_TOKEN_RE piu' sotto.
"""

import re
from typing import Callable, Dict, List, Optional, Tuple

from st_language.transform import list_transforms, parse_reference

from .i18n import current_language
from .instruments import PERCUSSION_MAP, InstrumentProfile
from .notation import DECORATIONS, DYNAMICS_TO_VELOCITY, NotationError, Pattern
from .chords import CHORD_QUALITIES, applicable_voicings

# Delimitatori di token nell'editor: spazio e le parentesi che aprono un
# blocco [...] o un gruppo (...). '/' e '.' NON sono delimitatori perche'
# fanno parte del token stesso (ottava, suffisso di voicing).
_WORD_BOUNDARY_CHARS = set(" \t\n[]()")

_STATE_WORDS = ["SON", "SOFF", "r", "arp="]
_DYNAMIC_WORDS = [f"{name}@" for name in DYNAMICS_TO_VELOCITY]
# Percussioni escluse: pertinenti solo su una traccia percussiva (vedi
# completions_for_word) - senza questa distinzione, digitando 'c' su una
# traccia di piano si vedrebbe suggerito 'crash' insieme alle note.
_NON_PERCUSSION_LOWERCASE_WORDS = sorted(set(_DYNAMIC_WORDS) | set(_STATE_WORDS))
_LOWERCASE_WORDS = sorted(set(PERCUSSION_MAP) | set(_NON_PERCUSSION_LOWERCASE_WORDS))

_CHORD_TOKEN_RE = re.compile(r"^(\d*)([A-G])([#b♭]?)([A-Za-z0-9#]*)$")
_VOICING_SUFFIX_RE = re.compile(r"^(\d*[A-G][#b♭]?[A-Za-z0-9#]*)\.([A-Za-z0-9]*)$")
_VOICED_CHORD_RE = re.compile(r"^(\d*[A-G][#b♭]?[A-Za-z0-9#]*\.[A-Za-z0-9]+)\.([A-Za-z0-9]*)$")
# Un richiamo con funzioni fino al cursore, e gli argomenti di .arpeggio(: le
# parentesi delimitano le parole, ma qui fanno parte del token.
_TRANSFORM_WORD_RE = re.compile(r"\d*%\w+(?:[+-]\d+)*(?:\.\w*(?:\([^()\s]*\)?)?(?:[+-]\d+)?)+$")
_ARPEGGIO_ARGUMENT_RE = re.compile(r"\.arpeggio\([^()\s]*$", re.IGNORECASE)
_ARPEGGIO_KINDS = ("up", "down", "updown", "alberti")
_ITALIAN_KINDS = {"up": "su", "down": "giu", "updown": "sugiu"}
_LOWERCASE_TOKEN_RE = re.compile(r"^(\d*)([a-z_][a-zA-Z_0-9]*)$")
# Segni di navigazione (da soli: $segno, $dc...) e segni sulle note (c$arp)
_NAVIGATION_WORDS = ["segno", "coda", "tocoda", "fine", "dc", "ds"]


class Completion(str):
    """Un suggerimento (il testo da inserire) con quello che l'elenco mostra
    al suo posto e la parte da lasciare selezionata dopo averlo inserito."""

    def __new__(cls, text: str, label: str = "", select: Optional[Tuple[int, int]] = None):
        item = super().__new__(cls, text)
        item.label = label or text
        item.select = select
        return item


def _italian() -> bool:
    return current_language() == "it"


def arpeggio_kinds() -> List[str]:
    """I tipi di arpeggio nella lingua dell'interfaccia."""
    return [_ITALIAN_KINDS.get(k, k) if _italian() else k for k in _ARPEGGIO_KINDS]


def arp_is_active(text_before: str) -> bool:
    """Se un arp= e' in vigore alla fine del testo."""
    written = re.findall(r"(?:^|\s)arp=(\S+)", text_before)
    return bool(written) and written[-1].partition(",")[0].lower() != "off"


def _function_call(base: str, transform: dict) -> Completion:
    """base.nome: con le parentesi e il primo argomento selezionato, se ne ha."""
    name = transform["alias"] if _italian() else transform["name"]
    arguments = [a["name"] for a in transform["arguments"] if a["required"]] \
        or [a["name"] for a in transform["arguments"]][:1]
    call = f".{name}({','.join(arguments)})" if arguments else f".{name}"
    text = base + call
    select = None
    if arguments:
        start = len(base) + len(name) + 2
        select = (start, start + len(arguments[0]))
    return Completion(text, f"{call}  —  {transform['help']}", select)


def _transform_completions(word: str) -> List[str]:
    """Dopo %Nome. e dopo ogni funzione: le funzioni, senza quelle che non
    si applicano a piu' voci se la catena ne ha gia' create."""
    m = re.match(r"^(.*)\.(\w*)$", word)
    if not m:
        return []
    base, prefix = m.groups()
    try:
        steps = {step.name for step in parse_reference(base).steps}
    except NotationError:
        return []
    transforms = list_transforms()
    voices = any(t["makes_voices"] and t["name"] in steps for t in transforms)
    prefix = prefix.lower()
    return [_function_call(base, t) for t in transforms
            if not (voices and t["single_voice"])
            and prefix not in (t["name"], t["alias"])
            and (t["name"].startswith(prefix) or t["alias"].startswith(prefix))]


def _arpeggio_call(base: str) -> Completion:
    kind = arpeggio_kinds()[0]
    start = len(base) + len(".arpeggio(")
    return Completion(f"{base}.arpeggio({kind})", select=(start, start + len(kind)))


def _arpeggio_arguments(word: str, active: bool) -> List[str]:
    head, _, prefix = word.rpartition("(")
    if "," in prefix:                     # la griglia si scrive a mano
        return []
    kinds = arpeggio_kinds() + (["off"] if active else [])
    return [f"{head}({k})" for k in kinds if k.startswith(prefix) and k != prefix]


def current_word_bounds(text: str, pos: int) -> Tuple[int, int]:
    """Ritorna (char_start, pos): l'estensione del token in digitazione che
    precede il cursore, fino al piu' vicino delimitatore. E' l'intervallo
    da sostituire quando si accetta un suggerimento."""
    start = pos
    while start > 0 and text[start - 1] not in _WORD_BOUNDARY_CHARS:
        start -= 1
    line_start = pos
    while line_start > 0 and text[line_start - 1] not in " \t\n":
        line_start -= 1
    chunk = text[line_start:pos]
    m = _TRANSFORM_WORD_RE.search(chunk) or _ARPEGGIO_ARGUMENT_RE.search(chunk)
    if m:
        return line_start + m.start(), pos
    return start, pos


def completions_for_word(
    word: str,
    *,
    patterns: Optional[Dict[str, Pattern]] = None,
    instrument: Optional[InstrumentProfile] = None,
    midi_ref_names: Optional[Callable[[], List[str]]] = None,
    text_before: str = "",
) -> List[str]:
    """Ritorna i token completi pertinenti al frammento 'word' gia'
    digitato, secondo la categoria sintattica cui appartiene:
      %parziale    -> nomi di pattern definiti nel progetto che iniziano cosi'
      %Nome.       -> funzioni sui pattern, nella lingua dell'interfaccia
      .arpeggio(   -> tipi di arpeggio (e off, se c'e' un arp= attivo); come arp=
      &parziale    -> riferimenti alla libreria MIDI che iniziano cosi' (&"nome")
      Cmaj7.dr     -> stili di voicing applicabili allo strumento della traccia
      C7, Dm...    -> qualita' d'accordo che iniziano col suffisso digitato
      hi, mf...    -> percussioni/dinamiche/comandi di stato che iniziano cosi'
    'midi_ref_names', se fornita, viene invocata solo quando serve (evita di
    scandire la libreria MIDI su disco ad ogni tasto premuto). 'text_before':
    il testo prima della parola, per sapere se c'e' un arp= attivo e se la
    parola segue un blocco [...]."""
    if not word:
        return []

    if word.startswith("arp="):
        prefix = word[4:]
        return [f"arp={k}" for k in arpeggio_kinds() + ["off"] if k.startswith(prefix) and k != prefix]

    if _ARPEGGIO_ARGUMENT_RE.search(word):
        return _arpeggio_arguments(word, arp_is_active(text_before))

    if _TRANSFORM_WORD_RE.fullmatch(word):
        return _transform_completions(word)

    if word.startswith(".") and text_before.endswith("]"):
        return [_arpeggio_call("")] if "arpeggio".startswith(word[1:].lower()) else []

    if word.startswith("%"):
        names = sorted(patterns) if patterns else []
        prefix = word[1:]
        return [f"%{n}" for n in names if n.startswith(prefix) and n != prefix]

    if word.startswith("&"):
        # il nome del file va sempre fra virgolette: &"Blues/riff"
        names = midi_ref_names() if midi_ref_names else []
        prefix = word[1:].lstrip('"')
        return [f'&"{n}"' for n in sorted(names) if n.startswith(prefix) and f'&"{n}"' != word]

    if "$" in word and not word.startswith('$"'):
        before, _, after = word.rpartition("$")
        if after[:1].isupper():
            # sigla senza suono: $Am7 (le qualita' come per gli accordi)
            m = _CHORD_TOKEN_RE.match(after)
            if not m or m.group(1):
                return []
            _mult, letter, accidental, suffix = m.groups()
            return [f"{before}${letter}{accidental}{q}" for q in CHORD_QUALITIES
                    if q and q.startswith(suffix) and q != suffix]
        names = DECORATIONS if before else _NAVIGATION_WORDS
        return [f"{before}${n}" for n in names if n.startswith(after) and n != after]

    m = _VOICING_SUFFIX_RE.match(word)
    if m:
        root, style_prefix = m.groups()
        styles = applicable_voicings(instrument) if instrument else []
        found = [f"{root}.{s}" for s in styles if s.startswith(style_prefix) and s != style_prefix]
        if style_prefix and "arpeggio".startswith(style_prefix.lower()) or not style_prefix:
            found.append(_arpeggio_call(root))
        return found

    m = _VOICED_CHORD_RE.match(word)
    if m:
        return [_arpeggio_call(m.group(1))] if "arpeggio".startswith(m.group(2).lower()) else []

    m = _CHORD_TOKEN_RE.match(word)
    if m:
        mult, letter, accidental, suffix = m.groups()
        return [
            f"{mult}{letter}{accidental}{quality}"
            for quality in CHORD_QUALITIES
            if quality and quality.startswith(suffix) and quality != suffix
        ]

    m = _LOWERCASE_TOKEN_RE.match(word)
    if m:
        mult, rest = m.groups()
        # Senza uno strumento noto si resta permissivi (comportamento
        # originale): il filtro si applica solo quando si sa per certo che
        # la traccia non e' percussiva.
        words = (
            _LOWERCASE_WORDS if instrument is None or instrument.is_percussion
            else _NON_PERCUSSION_LOWERCASE_WORDS
        )
        return [f"{mult}{w}" for w in words if w.startswith(rest) and w != rest]

    return []
