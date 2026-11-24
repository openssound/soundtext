"""Gli accordi dei testi generati, in notazione ridotta.

I generatori scrivono ogni accordo come un blocco di note, «[c*4 e*4 g*4]». Dove un simbolo (maiuscolo: «C», «Am7», «G7*3») suona
esattamente le stesse note sullo stesso strumento, il testo lo scrive cosi': si legge e si modifica piu' facilmente, e il suono e'
identico. Dove il simbolo suonerebbe altro (un rivolto, una fondamentale raddoppiata, una nota estranea) il blocco resta com'e'.
"""
import re
from typing import Dict, Optional, Tuple

from .chords import CHORD_QUALITIES, pc_to_letter, recognize_chord

# un blocco di note con il suo moltiplicatore di durata, non dentro un altro token: «2[c*4 e*4 g*4]»
_GROUP = re.compile(r"(?<![\w\]\[])(\d*)\[([^\[\]]+)\]")


def _notes_of(token: str, instrument) -> Optional[Tuple[int, ...]]:
    """Le note MIDI (ordinate) che un token di un accordo suona sullo strumento; None se non si legge o non e' un solo accordo."""
    from st_language.midi import resolve_event_notes
    from .notation import parse_track_text
    try:
        events = parse_track_text("4: " + token, {}, default_octave=instrument.default_octave)
        if len(events) != 1:
            return None
        notes, _velocity = resolve_event_notes(events[0], instrument)
    except Exception:
        return None
    return tuple(sorted(notes)) if notes else None


def symbol_for(inner: str, instrument, cache: Optional[Dict] = None) -> Optional[str]:
    """Il simbolo (senza moltiplicatore) che suona le stesse note del blocco «[inner]», o None se non c'e'."""
    if cache is not None and (inner, id(instrument)) in cache:
        return cache[(inner, id(instrument))]
    found = None
    notes = _notes_of(f"[{inner}]", instrument)
    recognized = recognize_chord(list(notes)) if notes and len(notes) >= 3 else None
    if recognized is not None:
        root_pc, quality, anchor = recognized
        chord_pcs = {(root_pc + iv) % 12 for iv in CHORD_QUALITIES[quality]}
        if {n % 12 for n in notes} == chord_pcs and len(notes) == len(chord_pcs) and min(notes) % 12 == root_pc:
            name = pc_to_letter(root_pc).upper() + ("" if quality == "maj" else quality)
            for candidate in (name, f"{name}*{anchor}"):                 # l'ottava solo se serve a restare nel registro del blocco
                if _notes_of(candidate, instrument) == notes:
                    found = candidate
                    break
    if cache is not None:
        cache[(inner, id(instrument))] = found
    return found


def chords_as_symbols(text: str, instrument) -> str:
    """Il testo con i blocchi di note che un simbolo suona uguale scritti come simbolo («2[c*4 e*4 g*4]» -> «2C»)."""
    if "[" not in text:
        return text
    cache: Dict = {}

    def swap(match):
        symbol = symbol_for(match.group(2), instrument, cache)
        return f"{match.group(1)}{symbol}" if symbol else match.group(0)
    return _GROUP.sub(swap, text)


# ------------------------------------------------------------ gli accordi della progressione

_QUALITY_OF = {(4, None): "", (3, None): "m", (4, 10): "7", (4, 11): "maj7", (3, 10): "m7", (3, 11): "mMaj7"}
_LETTER_PC = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}
_TOKEN = re.compile(r"(\d+)@|(\d*)(\[[^\]]*\]|\S+)")
_NOTE = re.compile(r"([a-g])([#b]?)\*(\d+)")


def span_symbol(span) -> Optional[str]:
    """Il simbolo (maiuscolo) di un accordo della progressione («C», «Am7», «G7»), o None se non si sa scrivere (sospeso, rivoltato...)."""
    quality = _QUALITY_OF.get((span.third, span.seventh))
    if quality is None or not span.has_fifth or span.bass_pc is not None:
        return None
    return pc_to_letter(span.root_pc).upper() + quality


def _group_pcs(inner: str) -> Optional[set]:
    found = _NOTE.findall(inner)
    if not found or len(" ".join(f"{a}{b}*{c}" for a, b, c in found).split()) != len(inner.split()):
        return None
    return {(_LETTER_PC[l] + (1 if acc == "#" else -1 if acc == "b" else 0)) % 12 for l, acc, _o in found}


def progression_symbols(text: str, chords) -> str:
    """Il testo di un accompagnamento con ogni blocco che suona l'accordo della progressione (con la fondamentale e la terza) scritto come
    il simbolo di quell'accordo: «2[c*4 f*4 a*4]» sul Fa diventa «2F». Il simbolo lo suona il motore col voicing dello strumento: i rivolti
    e la fondamentale raddoppiata si perdono, l'armonia no. I blocchi che non sono l'accordo intero (la sola terza e quinta, una
    settima senza fondamentale) restano com'erano. Un testo che non ha una griglia sola (voci, cambi di griglia) resta com'e'."""
    if "[" not in text or not chords:
        return text
    head = re.match(r"\s*(\d+)(T?):\s*", text)
    if not head:
        return text
    unit = 4.0 / int(head.group(1)) * (2.0 / 3.0 if head.group(2) else 1.0)
    body = text[head.end():]
    t, out = 0.0, []
    for tok in _TOKEN.finditer(body):
        if tok.group(1):                                              # la velocity: non occupa tempo
            continue
        mult, core = tok.group(2), tok.group(3)
        if core.endswith(":") or core.endswith("@") or core.startswith("{") or "=" in core:
            return text
        if core.startswith("["):
            span = next((s for s in chords if s.start_beat - 1e-6 <= t < s.start_beat + s.duration_beats - 1e-6), None)
            symbol = span_symbol(span) if span is not None else None
            pcs = _group_pcs(core[1:-1])
            if symbol and pcs and len(pcs) >= 3:
                tones = {span.root_pc, (span.root_pc + span.third) % 12}
                if tones <= pcs and pcs <= tones | {(span.root_pc + 7) % 12} | ({(span.root_pc + span.seventh) % 12} if span.seventh else set()):
                    out.append((tok.start(2) if mult else tok.start(3), tok.end(3), (mult or "") + symbol))
        t += unit * (int(mult) if mult else 1)
    pieces, cursor = [], 0
    for start, end, replacement in out:
        pieces.append(body[cursor:start])
        pieces.append(replacement)
        cursor = end
    pieces.append(body[cursor:])
    return text[:head.end()] + "".join(pieces)
