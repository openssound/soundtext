"""
Melodia dal testo: dalle parole di una canzone (una riga per frase) una
melodia con una nota per sillaba, gli accenti delle parole sui tempi forti,
e il testo gia' scritto sotto le note ("Ma- ri- a", vedi la guida, 2.13).

- Sillabe: le regole dell'italiano (una consonante va con la vocale dopo;
  doppie e gruppi come "lt", "nd" si dividono; "s" + consonante e consonante
  + l/r restano insieme; i dittonghi con i/u restano insieme). Chi vuole
  dividere diversamente scrive i trattini: "Ma-ri-a".
- Accento: sulla vocale accentata se c'e' (citta', perche'), altrimenti sulla
  penultima sillaba; le parole di una sillaba sono accentate, salvo articoli,
  preposizioni e congiunzioni.
- Ritmo: ogni riga e' una frase di due battute (quattro se le sillabe non ci
  stanno); le sillabe vanno a crome, le accentate cadono sul tempo (se
  serve la sillaba prima si allunga), l'ultima tiene fino alla fine della
  frase.
- Altezze: come le melodie a frasi (core.melody_generate), sulle note degli
  accordi della traccia scelta: note dell'accordo sui tempi forti, della
  scala sui deboli, un arco per frase; le frasi pari chiudono sulla tonica.
"""

import random
import re
import unicodedata
from typing import List, Optional, Tuple

from .i18n import tr

VOWELS = set("aeiouàèéìíòóùúAEIOUÀÈÉÌÍÒÓÙÚyY")
ACCENTED = set("àèéìíòóùúÀÈÉÌÍÒÓÙÚ")
STRONG_VOWELS = set("aeoàèéòóAEOÀÈÉÒÓ")
_KEEP_TOGETHER = {"bl", "br", "cl", "cr", "dr", "fl", "fr", "gl", "gr", "pl", "pr", "tr", "vr",
                  "ch", "gh", "gn", "sc", "qu", "ph", "th", "sh"}
UNSTRESSED = {"il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "di", "a", "da", "in", "con", "su",
              "per", "tra", "fra", "e", "o", "ma", "che", "mi", "ti", "si", "ci", "vi", "ne", "se", "del",
              "dal", "al", "nel", "sul", "col", "non", "the", "a", "an", "of", "to", "and", "in", "my"}

SLOT = 0.5                     # una croma
PHRASE_BARS = 2


def _is_vowel(ch: str) -> bool:
    return ch in VOWELS


def syllabify(word: str) -> List[str]:
    """Le sillabe di una parola (i trattini scritti dividono gia')."""
    if "-" in word.strip("-"):
        return [p for p in word.split("-") if p]
    letters = word
    nuclei = []                                   # (inizio, fine) dei gruppi vocalici
    i = 0
    while i < len(letters):
        if _is_vowel(letters[i]):
            j = i + 1
            while j < len(letters) and _is_vowel(letters[j]):
                # due vocali forti (a, e, o) sono due sillabe: pa-e-se
                if letters[j] in STRONG_VOWELS and letters[j - 1] in STRONG_VOWELS:
                    break
                j += 1
            nuclei.append((i, j))
            i = j
        else:
            i += 1
    if len(nuclei) <= 1:
        return [word]
    cuts = []
    for (_a, end), (start, _b) in zip(nuclei, nuclei[1:]):
        cons = letters[end:start].lower()
        if len(cons) <= 1:
            cuts.append(end)                          # ca-sa, pa-e-se
        elif len(cons) == 2:
            together = cons[0] != cons[1] and (cons in _KEEP_TOGETHER or cons[0] == "s")
            cuts.append(end if together else end + 1)     # las-su', tri-stez-za, can-ta-re
        else:
            if cons[0] == "s" or cons[:2] in _KEEP_TOGETHER:
                cuts.append(end)
            else:
                cuts.append(end + 1)                  # in-stru-men-to
    out, last = [], 0
    for cut in cuts:
        out.append(letters[last:cut])
        last = cut
    out.append(letters[last:])
    return [s for s in out if s]


def stressed_index(word: str, syllables: List[str]) -> Optional[int]:
    """L'indice della sillaba accentata, None per le parole atone."""
    plain = re.sub(r"[^\w]", "", word.lower())
    if len(syllables) == 1:
        return None if plain in UNSTRESSED else 0
    for k in range(len(syllables) - 1, -1, -1):
        if any(ch in ACCENTED for ch in syllables[k]):
            return k
    return len(syllables) - 2


def lyric_lines(text: str) -> List[List[Tuple[str, bool, bool]]]:
    """Per ogni riga non vuota: [(sillaba, accentata?, ultima della parola?)]."""
    lines = []
    for raw in text.splitlines():
        words = re.findall(r"[\w'’\-àèéìíòóùúÀÈÉÌÍÒÓÙÚ]+", unicodedata.normalize("NFC", raw))
        line = []
        for word in words:
            word = word.replace("’", "'")
            parts = []
            for piece in re.split(r"(?<=')", word):        # l'amore -> l' + amore
                if piece:
                    parts.append(piece)
            for piece in parts:
                sylls = syllabify(piece)
                stress = stressed_index(piece, sylls)
                for k, syl in enumerate(sylls):
                    line.append((syl, k == stress, k == len(sylls) - 1))
        if line:
            lines.append(line)
    return lines


def phrase_rhythm(line, bar_beats: float) -> Tuple[List[Tuple[float, float]], float]:
    """[(attacco, durata)] di una riga e la lunghezza della frase (beat)."""
    bars = PHRASE_BARS
    while True:
        phrase_beats = bars * bar_beats
        onsets, t = [], 0.0
        for syl, stressed, _end in line:
            on_beat = abs(t - round(t)) < 1e-6
            if stressed and not on_beat:
                t = round(t + SLOT, 6)                # la sillaba prima si allunga
            onsets.append(t)
            t = round(t + SLOT, 6)
        if t <= phrase_beats - SLOT + 1e-6 or bars >= 8:
            break
        bars *= 2
    rhythm = []
    for k, onset in enumerate(onsets):
        end = onsets[k + 1] if k + 1 < len(onsets) else min(phrase_beats, max(onset + 2.0, phrase_beats - SLOT))
        rhythm.append((onset, round(end - onset, 6)))
    return rhythm, phrase_beats


def lyrics_to_melody(lyrics: str, chords, key: Optional[str], octave: int, range_low: int, range_high: int,
                     bar_beats: float = 4.0, seed: Optional[int] = None) -> str:
    """Il testo di notazione della melodia, con le sillabe fra virgolette
    dopo ogni frase. Solleva ValueError senza parole o senza accordi."""
    from .chords import midi_note
    from .melody_generate import (MAJOR_SCALE, MINOR_SCALE, _arch, _Harmony, _realize, estimate_key)
    from .rhythm_generate import _expand_chords_to_cover, _note_token, parse_key
    lines = lyric_lines(lyrics)
    if not lines:
        raise ValueError(tr("Scrivi le parole: una riga per frase."))
    if not chords:
        raise ValueError(tr("Nessun accordo da seguire: la traccia sorgente non ne contiene."))
    phrases = [phrase_rhythm(line, bar_beats) for line in lines]
    total = sum(beats for _r, beats in phrases)
    chords = _expand_chords_to_cover(chords, total)
    if key and key.strip():
        tonic, mode, _flats = parse_key(key)
    else:
        tonic, mode = estimate_key(chords)
    scale = [(tonic + s) % 12 for s in (MAJOR_SCALE if mode == "major" else MINOR_SCALE)]
    center = midi_note(tonic, octave)
    while center > range_high - 7 and center - 12 >= range_low:
        center -= 12
    while center < range_low + 5 and center + 12 <= range_high:
        center += 12
    low, high = max(range_low, center - 7), min(range_high, center + 12)
    if high - low < 12:
        low, high = range_low, range_high
    harmony = _Harmony(chords, scale, low, high)
    rng = random.Random(seed if seed is not None else 0)
    compound = abs(bar_beats - round(bar_beats)) > 1e-6
    tokens = ["8:"]
    start = 0.0
    prev = prev2 = None
    for p, ((rhythm, beats), line) in enumerate(zip(phrases, lines)):
        ending = "closed" if p % 2 == 1 or p == len(lines) - 1 else "open"
        targets = _arch(rhythm, beats, center, 5, ending)
        pitches = _realize(rhythm, start, harmony, bar_beats, compound, targets, ending, tonic,
                           prev, prev2, rng, 0.2)
        t = 0.0
        for (onset, duration), pitch in zip(rhythm, pitches):
            if onset > t + 1e-6:
                rest = int(round((onset - t) / SLOT))
                tokens.append(f"{rest}r" if rest > 1 else "r")
            mult = max(1, int(round(duration / SLOT)))
            tokens.append((f"{mult}" if mult > 1 else "") + _note_token(pitch % 12, pitch // 12 - 1))
            t = onset + mult * SLOT
        if t < beats - 1e-6:
            rest = int(round((beats - t) / SLOT))
            tokens.append(f"{rest}r" if rest > 1 else "r")
        words = " ".join(syl.replace('"', "'") + ("" if end else "-") for syl, _s, end in line)
        tokens.append(f'"{words}"')
        if pitches:
            prev2, prev = (pitches[-2] if len(pitches) > 1 else prev), pitches[-1]
        start += beats
    return " ".join(tokens)
