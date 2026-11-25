"""
Bemolli e diesis scritti con i simboli (♭ ♯) e percussioni con le
abbreviazioni (bd, hh, sn): la sostituzione mentre si scrive, i comandi che
riscrivono un testo e lo stile del testo che il programma genera.

La logica sta qui, senza interfaccia, perche' la usano l'editor del
computer, i generatori e i comandi; la riscrittura vera e' della libreria
st_language (normalize_track_text, PERCUSSION_ALIASES).
"""

import re
from typing import Optional, Tuple

from st_language import normalize_track_text
from st_language.notation import comment_spans

from . import settings
from .instruments import PERCUSSION_ALIASES, PERCUSSION_MAP, percussion_short_name

# Quello che chiude un token mentre si scrive; il token e' quello che precede.
CLOSERS = frozenset(" \t\n|])}")
# Dove comincia un token: dopo questi caratteri (le parentesi e i blocchi che
# si aprono, lo spazio, la stanghetta, il punto e virgola delle voci).
_TOKEN_START = frozenset(" \t\n[({|;")


def symbols_enabled() -> bool:
    return settings.get_accidental_symbols()


def accidentals_style() -> Optional[str]:
    """'symbols' se l'opzione e' accesa, altrimenti None: da passare a
    accidentals= delle funzioni della libreria che scrivono testo (None =
    come le scrive la libreria, con b e #)."""
    return "symbols" if settings.get_accidental_symbols() else None


def styled(text: str) -> str:
    """Il testo che il programma ha generato, con le alterazioni nello stile
    scelto nelle impostazioni (e, se acceso, le percussioni abbreviate)."""
    if not text:
        return text
    if settings.get_percussion_abbreviations():
        text = abbreviate_percussion(text)
    if settings.get_accidental_symbols():
        try:
            text = normalize_track_text(text, "symbols")
        except Exception:                  # testo che la libreria non legge: com'e'
            pass
    return text


def styled_notes(text: str) -> str:
    """Come styled, ma solo le alterazioni: per il testo che arriva da un
    file importato (MIDI, ABC, MusicXML), dove le percussioni non cambiano."""
    if not text or not settings.get_accidental_symbols():
        return text
    try:
        return normalize_track_text(text, "symbols")
    except Exception:
        return text


def _in_comment_or_lyrics(text: str, start: int) -> bool:
    for begin, end in comment_spans(text):
        if begin <= start < end:
            return True
    quotes = 0
    pos = 0
    for begin, end in comment_spans(text):
        if begin >= start:
            break
        quotes += text.count('"', pos, min(begin, start))
        pos = end
    if pos < start:
        quotes += text.count('"', pos, start)
    return quotes % 2 == 1


def closed_token_replacement(text: str, end: int) -> Optional[Tuple[int, int, str]]:
    """Il token che finisce a 'end' (dove c'e' il carattere che l'ha chiuso)
    riscritto con i simboli: (inizio, fine, testo nuovo), o None se non c'e'
    niente da cambiare. Non si tocca un commento, un testo cantato, un
    richiamo %Nome o &file, le abbreviazioni delle percussioni, ne' una
    parola che non e' una nota, un accordo o una tonalita'."""
    start = end
    while start > 0 and text[start - 1] not in _TOKEN_START:
        start -= 1
    token = text[start:end]
    if not token or "b" not in token and "#" not in token:
        return None
    if _in_comment_or_lyrics(text, start):
        return None
    try:
        new = normalize_track_text(token, "symbols")
    except Exception:
        return None
    if new == token:
        return None
    return start, end, new


def convert_accidentals(text: str, style: str) -> str:
    """Il testo di una traccia, di un pattern o di un box con bemolli e
    diesis scritti 'symbols' (♭ ♯) o 'ascii' (b #)."""
    return normalize_track_text(text, style)




def abbreviate_percussion(text: str) -> str:
    """Il testo con i nomi lunghi delle percussioni scritti con la prima
    abbreviazione ('kick' -> 'bd'). Commenti e testi cantati restano."""
    return _rewrite_percussion(text, lambda name: percussion_short_name(name) if name in PERCUSSION_MAP else name)


def expand_percussion(text: str) -> str:
    """Il testo con le abbreviazioni delle percussioni scritte per intero
    ('bd' -> 'kick')."""
    return _rewrite_percussion(text, lambda name: PERCUSSION_ALIASES.get(name, name))


def _rewrite_percussion(text: str, convert) -> str:
    from st_language.notation import _tokenize_spans_raw
    from st_language.accidentals import _plain_tokens  # noqa: F401  (solo per coerenza dei token)
    out, pos = [], 0
    try:
        spans = _tokenize_spans_raw(text)
    except Exception:
        return text

    def one(tok: str) -> str:
        if tok[:1] in ('"', "%", "&") or tok.startswith('$"'):
            return tok
        if tok[:1] == "{":
            from st_language.notation import split_voices
            return "{" + ";".join(_rewrite_percussion(v, convert) for v in split_voices(tok[1:-1])) + "}"
        m = re.match(r"^(\d*)\((.*)\)$", tok, re.DOTALL)
        if m:
            return f"{m.group(1)}(" + _rewrite_percussion(m.group(2), convert) + ")"
        m = re.match(r"^(\d*)\[(.*)\](.*)$", tok, re.DOTALL)
        if m:
            return f"{m.group(1)}[" + _rewrite_percussion(m.group(2), convert) + "]" + m.group(3)
        m = re.match(r"^(\d*)([a-z][a-z0-9_]*)(['$<>~()].*)?$", tok, re.DOTALL)
        if m and (m.group(2) in PERCUSSION_MAP or m.group(2) in PERCUSSION_ALIASES):
            return m.group(1) + convert(m.group(2)) + (m.group(3) or "")
        return tok

    for tok, start, end in spans:
        out.append(text[pos:start])
        out.append(one(tok))
        pos = end
    out.append(text[pos:])
    return "".join(out)


def rewrite_project_texts(project, rewrite) -> int:
    """'rewrite' (testo -> testo) applicata al testo di tutte le tracce, di
    tutti i box e dei pattern del progetto. Ritorna quanti testi sono
    cambiati. Il suono non cambia, se 'rewrite' non lo cambia."""
    from .arrangement import flatten_clips_to_text
    from .notation import tokenize
    changed = 0
    for pattern in project.patterns.values():
        old = " ".join(pattern.tokens)
        new = rewrite(old)
        if new != old:
            pattern.tokens = tokenize(new)
            changed += 1
    for track in project.tracks:
        if track.is_audio:
            continue
        if track.clips:
            moved = False
            for clip in track.clips:
                new = rewrite(clip.text)
                if new != clip.text:
                    clip.text = new
                    moved = True
                    changed += 1
            if moved:
                track.text = flatten_clips_to_text(track.clips, project.patterns, track.instrument.default_octave,
                                                   meter=project.meter())
        else:
            new = rewrite(track.text)
            if new != track.text:
                track.text = new
                changed += 1
    return changed
