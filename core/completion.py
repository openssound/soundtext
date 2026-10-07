"""
Motore di suggerimenti per l'autocompletamento dei token nell'editor
(gui.voicing_picker.NotationEditor). Logica pura di testo, senza
dipendenze da Qt: dato il frammento di token gia' digitato (dall'inizio
della "parola" corrente fino al cursore), ritorna la lista dei token
COMPLETI pertinenti, per velocizzare la digitazione delle notazioni piu'
lunghe o meno immediate da ricordare a memoria (qualita' d'accordo, stili
di voicing, nomi di percussioni/dinamiche, riferimenti %pattern e &midi).

Le note singole (es. 'c', 'g#*4') non generano suggerimenti propri: sono
gia' brevi quanto un suggerimento. La lettera minuscola sola resta pero'
un prefisso valido per i nomi di percussione che iniziano allo stesso modo
(es. 'c' -> 'crash'), gestito da _LOWERCASE_TOKEN_RE piu' sotto.
"""

import re
from typing import Callable, Dict, List, Optional, Tuple

from .instruments import PERCUSSION_MAP, InstrumentProfile
from .notation import DECORATIONS, DYNAMICS_TO_VELOCITY, Pattern
from .chords import CHORD_QUALITIES, applicable_voicings

# Delimitatori di token nell'editor: spazio e le parentesi che aprono un
# blocco [...] o un gruppo (...). '/' e '.' NON sono delimitatori perche'
# fanno parte del token stesso (ottava, suffisso di voicing).
_WORD_BOUNDARY_CHARS = set(" \t\n[]()")

_STATE_WORDS = ["SON", "SOFF", "r"]
_DYNAMIC_WORDS = [f"{name}@" for name in DYNAMICS_TO_VELOCITY]
# Percussioni escluse: pertinenti solo su una traccia percussiva (vedi
# completions_for_word) - senza questa distinzione, digitando 'c' su una
# traccia di piano si vedrebbe suggerito 'crash' insieme alle note.
_NON_PERCUSSION_LOWERCASE_WORDS = sorted(set(_DYNAMIC_WORDS) | set(_STATE_WORDS))
_LOWERCASE_WORDS = sorted(set(PERCUSSION_MAP) | set(_NON_PERCUSSION_LOWERCASE_WORDS))

_CHORD_TOKEN_RE = re.compile(r"^(\d*)([A-G])([#b♭]?)([A-Za-z0-9#]*)$")
_VOICING_SUFFIX_RE = re.compile(r"^(\d*[A-G][#b♭]?[A-Za-z0-9#]*)\.([A-Za-z0-9]*)$")
_LOWERCASE_TOKEN_RE = re.compile(r"^(\d*)([a-z_][a-zA-Z_0-9]*)$")
# Segni di navigazione (da soli: $segno, $dc...) e segni sulle note (c$arp)
_NAVIGATION_WORDS = ["segno", "coda", "tocoda", "fine", "dc", "ds"]


def current_word_bounds(text: str, pos: int) -> Tuple[int, int]:
    """Ritorna (char_start, pos): l'estensione del token in digitazione che
    precede il cursore, fino al piu' vicino delimitatore. E' l'intervallo
    da sostituire quando si accetta un suggerimento."""
    start = pos
    while start > 0 and text[start - 1] not in _WORD_BOUNDARY_CHARS:
        start -= 1
    return start, pos


def completions_for_word(
    word: str,
    *,
    patterns: Optional[Dict[str, Pattern]] = None,
    instrument: Optional[InstrumentProfile] = None,
    midi_ref_names: Optional[Callable[[], List[str]]] = None,
) -> List[str]:
    """Ritorna i token completi pertinenti al frammento 'word' gia'
    digitato, secondo la categoria sintattica cui appartiene:
      %parziale    -> nomi di pattern definiti nel progetto che iniziano cosi'
      &parziale    -> riferimenti alla libreria MIDI che iniziano cosi' (&"nome")
      Cmaj7.dr     -> stili di voicing applicabili allo strumento della traccia
      C7, Dm...    -> qualita' d'accordo che iniziano col suffisso digitato
      hi, mf...    -> percussioni/dinamiche/comandi di stato che iniziano cosi'
    'midi_ref_names', se fornita, viene invocata solo quando serve (evita di
    scandire la libreria MIDI su disco ad ogni tasto premuto)."""
    if not word:
        return []

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
        return [f"{root}.{s}" for s in styles if s.startswith(style_prefix) and s != style_prefix]

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
