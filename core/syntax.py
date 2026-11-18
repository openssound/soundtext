"""
Evidenziazione sintattica della notazione, senza Qt: la categoria di ogni
token di una riga (nota, accordo, pausa, richiamo di pattern...) e la voce
di un blocco { ; } in cui cade ogni carattere. La usano l'editor di
SoundText (gui.highlighter, che trasforma le categorie in formati Qt) e
SoundText Mobile (mobile/engine.py, che le manda alla pagina web).

Riusa le regex di classificazione di core.notation: cosi' i colori mostrati
corrispondono sempre a come il parser interpreta il testo. La suddivisione
in token e' invece riga per riga e tollerante (_LEX): un gruppo N(...) o un
blocco di voci { ; } puo' andare a capo, e ogni riga va colorata anche se
da sola non e' un testo completo; dentro gruppi e voci ogni token ha il suo
colore. Lo stato fra le righe (le voci aperte, una pila per i blocchi
annidati, e se un arp= e' attivo) passa da una riga all'altra.
"""

import re
from typing import Iterable, List, Optional, Tuple

from .notation import (
    strip_comments, comment_spans, split_note_value, RE_PATTERN_REF, RE_MIDI_REF, RE_GRID,
    RE_VELOCITY, RE_REST, RE_NOTE, RE_CHORD, RE_PERC, RE_SLIDE,
    RE_TEMPO_SET, RE_RAMP_UP, RE_RAMP_DOWN, RE_CONTROL, RE_SWING, RE_SHIFT, RE_PITCH_MODE,
    RE_KEY_MODE, RE_BAR_ANCHOR, RE_TRANSPOSE, RESET_TOKEN, RE_NAVIGATION, RE_HARMONY, RE_ARP,
    RE_ARPEGGIO_SUFFIX, NotationError,
)
from st_language.transform import is_transform_reference, parse_reference

# Categorie (i colori li sceglie chi disegna): note, chord, chord_arp
# (accordo sotto un arp= attivo: si sente spezzato), perc, state, ref, rest,
# block, repeat, slide, sustain, tempo_ramp, comment, voices, lyric, bar,
# bar_error (avviso: '|' fuori stanghetta, richiamo che non si legge...),
# transform.
CATEGORIES = ("note", "chord", "chord_arp", "perc", "state", "ref", "rest", "block", "repeat", "slide",
              "sustain", "tempo_ramp", "comment", "voices", "lyric", "bar", "bar_error", "transform")

# Quante voci a rotazione per gli sfondi dei blocchi { ; }
VOICE_COLORS = 4

# Token di una riga, per colorarla: testo cantato, blocco [...] (col suo
# eventuale valore di nota), aperture e chiusure di gruppi e voci, la
# stanghetta e i token semplici.
_LEX = re.compile(r"""
    (?P<text>\$"[^"\n]*"?)
  | (?P<midiref>\d*&"[^"\n]*"?(?:[+-]\d+)?)
  | (?P<lyric>"[^"\n]*"?)
  | (?P<block>\d*\[[^\]\n]*\]?(?:'[^\s|"(){};]*)?(?:\$[a-z]+)*(?:\.(?i:arpeggio)(?:\([^()\s]*\)?)?)?[<>]?~?\(?)
  | (?P<group>\d*\(|\))
  | (?P<voices>[{};])
  | (?P<bar>:\|(?:[1-9]\.)?|\|(?::|\||[1-9]\.)?)
  | (?P<transform>\d*%\w+(?:[+-]\d+)*(?:\.\w*(?:\([^()\s]*\)?)?(?:[+-]\d+)?)+)
  | (?P<arpeggio>(?:[^\s|"(){};\[\]:]|:(?!\|))+?\.(?i:arpeggio)(?:\([^()\s]*\)?)?[^\s|"(){};\[\]:]*)
  | (?P<plain>(?:[^\s|"(){};\[\]:]|:(?!\|))+\(?)
""", re.VERBOSE)


class LineState:
    """Lo stato alla fine di una riga: le voci aperte (indice di voce per
    ogni livello di blocchi annidati) e se un arp= e' attivo."""
    __slots__ = ("stack", "arp")

    def __init__(self, stack: Optional[List[int]] = None, arp: bool = False):
        self.stack = list(stack or [])
        self.arp = arp


def voice_color(stack: List[int]) -> Optional[int]:
    """L'indice (0..VOICE_COLORS-1) dello sfondo della voce piu' interna
    aperta, None fuori dai blocchi: un blocco annidato parte da un altro
    colore di quello che lo contiene."""
    if not stack:
        return None
    return (stack[-1] + 2 * (len(stack) - 1)) % VOICE_COLORS


def classify(tok: str) -> Optional[str]:
    """La categoria di un token semplice (senza valore di nota)."""
    if RE_PATTERN_REF.match(tok) or RE_MIDI_REF.match(tok):
        return "ref"
    if tok in ("SON", "SOFF"):
        return "sustain"
    if RE_TEMPO_SET.match(tok) or RE_RAMP_UP.match(tok) or RE_RAMP_DOWN.match(tok):
        return "tempo_ramp"
    if is_transform_reference(tok):
        return "bar_error"     # scritto a meta': un richiamo valido e' un lessema 'transform'
    if RE_GRID.match(tok) or RE_VELOCITY.match(tok) or RE_ARP.match(tok) or RE_CONTROL.match(tok) \
            or RE_SWING.match(tok) or RE_SHIFT.match(tok) or RE_PITCH_MODE.match(tok) or RE_KEY_MODE.match(tok) \
            or RE_BAR_ANCHOR.match(tok) or RE_TRANSPOSE.match(tok) or tok == RESET_TOKEN:
        return "state"
    if RE_NAVIGATION.match(tok):
        return "repeat"        # $segno, $dc...: struttura, come i ritornelli
    if RE_HARMONY.match(tok):
        return "chord"         # $Am7: sigla senza suono
    if RE_REST.match(tok):
        return "rest"
    if RE_SLIDE.match(tok):
        return "slide"
    if RE_NOTE.match(tok):
        return "note"
    if RE_CHORD.match(tok):
        return "chord"
    if RE_PERC.match(tok):
        return "perc"
    return None


def _call_spans(start: int, call: str) -> List[Tuple[int, int, str]]:
    """'.nome(a,b)': nome e parentesi colore funzione, argomenti i loro."""
    spans = [(start, len(call), "transform")]
    opened = call.find("(")
    if opened < 0:
        return spans
    pos = opened + 1
    for argument in call[pos:].rstrip(")").split(","):
        if argument:
            spans.append((start + pos, len(argument), classify(argument) or "state"))
        pos += len(argument) + 1
    return spans


def _reference_spans(start: int, tok: str) -> List[Tuple[int, int, str]]:
    """Un richiamo con funzioni: il pattern corallo, le funzioni con il
    loro colore, gli argomenti con quelli che hanno gia'. La grammatica e'
    quella della libreria (parse_reference); un richiamo che non si legge
    e' tutto un errore."""
    try:
        steps = parse_reference(tok).steps
    except NotationError:
        return [(start, len(tok), "bar_error")]
    spans = [(start, steps[0].start if steps else len(tok), "ref")]
    for step in steps:
        if step.name == "transpose":
            spans.append((start + step.start, step.end - step.start, "ref"))
        else:
            spans += _call_spans(start + step.start, tok[step.start:step.end])
    return spans


def _arpeggio_spans(start: int, tok: str, kind: str) -> List[Tuple[int, int, str]]:
    """Un accordo o un blocco con .arpeggio(...): prima il suo colore, poi
    il suffisso."""
    m = RE_ARPEGGIO_SUFFIX.match(tok)
    if not m:
        return [(start, len(tok), "block" if kind == "block" else "chord")]
    base = "block" if kind == "block" else (classify(split_note_value(m.group(1))[0]) or "chord")
    suffix_end = len(tok) - len(m.group(3))
    return [(start, len(tok), base)] + _call_spans(start + len(m.group(1)), tok[len(m.group(1)):suffix_end])


def line_spans(text: str, state: Optional[LineState] = None,
               errors: Iterable[int] = ()) -> Tuple[List[Tuple[int, int, str]], List[Optional[int]], LineState]:
    """Colori di una riga di notazione.

    'state': lo stato alla fine della riga precedente (None all'inizio).
    'errors': posizioni (nella riga) dei token con un avviso, vedi
    core.notation.notation_warnings: in rosso.

    Ritorna (formati, sfondi, stato a fine riga). I formati sono
    (inizio, lunghezza, categoria) da applicare nell'ordine (uno successivo
    vince sui caratteri gia' colorati); gli sfondi sono, per ogni carattere,
    l'indice di voce (vedi voice_color) o None."""
    previous = state or LineState()
    errors = frozenset(errors)
    stripped = strip_comments(text)
    lexemes = list(_LEX.finditer(stripped))

    # Sfondo di ogni carattere: quello della voce aperta in quel punto.
    stack = list(previous.stack)
    backgrounds: List[Optional[int]] = [None] * len(text)
    pos = 0
    for m in lexemes:
        background = voice_color(stack)
        for i in range(pos, m.start()):
            backgrounds[i] = background
        tok = m.group()
        if m.lastgroup == "voices":
            if tok == "{":
                stack.append(0)
            elif tok == ";" and stack:
                stack[-1] += 1
            elif tok == "}" and stack:
                stack.pop()
        else:
            for i in range(m.start(), m.end()):
                backgrounds[i] = background
        pos = m.end()
    background = voice_color(stack)
    for i in range(pos, len(text)):
        backgrounds[i] = background
    arp = previous.arp
    arp_after = arp
    for m in lexemes:
        if RE_ARP.match(m.group()):
            arp_after = not m.group().lower().startswith("arp=off")

    spans: List[Tuple[int, int, str]] = []
    for start, end in comment_spans(text):
        spans.append((start, end - start, "comment"))
    # ')' chiude un gruppo N(...) o una legatura di portamento c( ... f):
    # vale il gruppo aperto per ultimo sulla riga (se non ce n'e', la
    # legatura aperta sulla riga, altrimenti un gruppo di una riga prima).
    opened = []
    for m in lexemes:
        kind, tok = m.lastgroup, m.group()
        if kind == "group" and tok != ")":
            opened.append("group")
        elif kind in ("plain", "block") and tok.endswith("("):
            opened.append("slur")
        elif tok == ")" and opened and opened.pop() == "slur":
            kind = "slur_close"
        if kind == "plain" and RE_ARP.match(tok):
            arp = not tok.lower().startswith("arp=off")
        if kind == "transform":
            if m.start() in errors:
                spans.append((m.start(), len(tok), "bar_error"))
            else:
                spans += _reference_spans(m.start(), tok)
            continue
        if kind == "arpeggio" or (kind == "block" and ".arpeggio" in tok.lower()):
            spans += _arpeggio_spans(m.start(), tok, kind)
            continue
        if kind == "slur_close":
            category = "note"
        elif kind == "bar":
            category = "bar_error" if m.start() in errors else "bar"
        elif kind in ("lyric", "text"):
            category = "lyric"
        elif kind == "block":
            category = "block"
        elif kind == "group":
            category = "repeat"
        elif kind == "voices":
            category = "voices"
        else:
            category = classify(split_note_value(tok)[0])
        if kind != "bar" and m.start() in errors:
            category = "bar_error"     # avviso sul testo cantato o su un blocco di voci
        if category == "chord" and arp:
            category = "chord_arp"
        if category:
            spans.append((m.start(), len(tok), category))
    return spans, backgrounds, LineState(stack, arp_after)
