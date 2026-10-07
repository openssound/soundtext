"""
Testo cantato negli import: dagli eventi "lyrics" di un file MIDI (anche
karaoke .kar) e dalle sillabe di una partitura MusicXML (che passa dal
MIDI, vedi core.musicxml_import.write_midi) al testo fra virgolette di ST
(sezione 2.13 della guida).

Le sillabe vengono agganciate alla nota della prima voce che attacca nello
stesso punto (dopo la quantizzazione), e scritte una riga di testo per
battuta, dopo le sue note: "Ma- ri- a". Una nota senza sillaba in una
battuta che ne ha diventa '*'; prima della prima battuta cantata dopo un
tratto strumentale va un testo vuoto "" (chiude le note precedenti senza
dar loro sillabe).
"""

import bisect
import re
from fractions import Fraction
from typing import List, Optional, Sequence, Tuple

from .notation import _sings, bar_starts, parse_tokens

# Distanza massima (in quarti) fra la sillaba e l'attacco della nota.
LYRIC_SNAP_BEATS = Fraction(1, 4)

_LINE_MARKS = re.compile(r"[/\\\r\n]")


def midi_text(text: str) -> str:
    """Il testo di un evento MIDI: mido lo legge come latin-1; se in realta'
    erano byte UTF-8 (come li scrive SoundText per i caratteri fuori dal
    latin-1) lo si ricostruisce."""
    try:
        decoded = text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text
    return decoded


def midi_text_bytes(text: str) -> str:
    """Il testo da scrivere in un evento MIDI: latin-1 se basta, altrimenti
    i byte UTF-8 (vedi midi_text, che li rilegge)."""
    try:
        text.encode("latin-1")
        return text
    except UnicodeEncodeError:
        return text.encode("utf-8").decode("latin-1")


def syllables(events: Sequence[Tuple[int, str]]) -> List[Tuple[int, str]]:
    """Eventi (tick, testo) -> (tick, sillaba) nella forma di ST: 'Ma-' se
    la parola continua nella sillaba dopo. Una sillaba continua se finisce
    con '-', oppure se non finisce con uno spazio e la successiva non
    comincia con uno spazio (convenzione dei file karaoke: le parole
    nuove cominciano con uno spazio; quella dell'export di SoundText: la
    fine di parola ha uno spazio dopo). '/' e '\\' (a capo del karaoke)
    sono ignorati."""
    cleaned = []
    for tick, raw in sorted(events, key=lambda e: e[0]):
        raw = _LINE_MARKS.sub(" ", midi_text(raw))
        if raw.strip():
            cleaned.append((tick, raw))
    out = []
    for i, (tick, raw) in enumerate(cleaned):
        nxt = cleaned[i + 1][1] if i + 1 < len(cleaned) else " "
        word = raw.strip()
        if word.endswith("-") and len(word) > 1:
            continues, word = True, word[:-1].strip()
        else:
            continues = not raw[-1].isspace() and not nxt[0].isspace()
        word = re.sub(r"\s+", "‿", word).replace('"', "'")
        if word in ("_", "*"):
            word = word + "‿"
        out.append((tick, word + ("-" if continues else "")))
    return out


def _sings_token(tok: str) -> bool:
    try:
        events = parse_tokens([tok])
    except Exception:
        return False
    return bool(events) and _sings(events[0])


def add_lyrics(tokens: Sequence[str], lyrics: Sequence[Tuple[Fraction, str]],
               time_sig: str = "4/4", metrica_changes=()) -> List[str]:
    """I token della voce con il testo cantato: lyrics = [(quarto, sillaba)]."""
    from .voice_merge import timed_tokens
    tokens = list(tokens)
    if not lyrics:
        return tokens
    timed = timed_tokens(tokens)
    notes = [i for i, (tok, a, b) in enumerate(timed) if b > a and _sings_token(tok)]
    if not notes:
        return tokens
    sung = {}
    for beat, syllable in sorted(lyrics):
        best = min(notes, key=lambda i: abs(timed[i][1] - beat))
        if abs(timed[best][1] - beat) <= LYRIC_SNAP_BEATS and best not in sung:
            sung[best] = syllable

    end = timed[notes[-1]][2]
    lines = []
    for line in bar_starts(time_sig, metrica_changes):
        lines.append(line)
        if line > end:
            break

    def bar_of(i):
        start = timed[i][1]
        return max(k for k, line in enumerate(lines) if line <= start)

    by_bar = {}
    for i in notes:
        by_bar.setdefault(bar_of(i), []).append(i)
    inserts: List[Tuple[int, str]] = []          # (indice dopo cui inserire, token)
    pending = 0                                  # note senza sillaba ancora in attesa
    for bar in sorted(by_bar):
        bar_notes = by_bar[bar]
        if not any(i in sung for i in bar_notes):
            pending += len(bar_notes)
            continue
        if pending:
            inserts.append((bar_notes[0], '""'))
            pending = 0
        words = [sung.get(i, "*") for i in bar_notes]
        while words and words[-1] == "*":
            words.pop()
        inserts.append((bar_notes[-1] + 1, '"' + " ".join(words) + '"'))
    for index, token in sorted(inserts, key=lambda x: x[0], reverse=True):
        tokens.insert(index, token)
    return tokens


def beats_from_ticks(lyrics: Sequence[Tuple[int, str]], ticks_per_beat: int) -> List[Tuple[Fraction, str]]:
    return [(Fraction(tick, ticks_per_beat), syllable) for tick, syllable in lyrics]


def nearest_channel(ticks: Sequence[int], onsets_by_channel, ticks_per_beat: int) -> Optional[int]:
    """Il canale le cui note attaccano dove cadono piu' sillabe (per i
    testi in una traccia MIDI senza note, come nei file karaoke)."""
    tol = ticks_per_beat // 8
    best, best_hits = None, 0
    for channel, onsets in onsets_by_channel.items():
        ordered = sorted(onsets)
        hits = 0
        for t in ticks:
            j = bisect.bisect_left(ordered, t - tol)
            if j < len(ordered) and ordered[j] <= t + tol:
                hits += 1
        if hits > best_hits:
            best, best_hits = channel, hits
    return best
