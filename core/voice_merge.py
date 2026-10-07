"""
Voci di un canale importato (core.midi_to_tokens.channel_to_voices) unite
in UN solo testo di traccia: dove suona solo la prima voce il testo resta
quello di sempre, dove suonano anche le altre diventa un blocco di voci
{ voce1 ; voce2 } (sezione 2.12 della guida), che parte e finisce su punti
in cui nessuna nota viene tagliata (sulle stanghette, quando si puo').

Lavora sui token gia' prodotti, misurando con il parser stesso
(_parse_tokens_exact con 'ranges') dove inizia e finisce ciascuno: cosi'
il testo unito suona esattamente come le voci separate.
"""

from fractions import Fraction
from typing import List, Optional, Sequence, Tuple

from .notation import (RE_GRID, RE_REST, RE_VELOCITY, _parse_tokens_exact, bar_starts, is_lyric,
                       tokenize)

# Due tratti a piu' voci separati da meno di tanto (in quarti) diventano un
# blocco solo: meglio un blocco lungo che tanti blocchi spezzettati.
MERGE_GAP_BEATS = Fraction(4)

# Valori di nota con cui si scrivono le pause d'attesa all'inizio di una
# voce (vedi _rest_tokens), dal piu' lungo: griglie binarie e tuplet.
_REST_VALUES = sorted([
    (Fraction(4), "'1"), (Fraction(2), "'2"), (Fraction(1), "'4"), (Fraction(1, 2), "'8"),
    (Fraction(1, 4), "'16"), (Fraction(1, 8), "'32"), (Fraction(1, 16), "'64"),
    (Fraction(2, 3), "'4T"), (Fraction(1, 3), "'8T"), (Fraction(1, 6), "'16T"), (Fraction(1, 12), "'32T"),
    (Fraction(1, 5), "'16Q"), (Fraction(1, 10), "'32Q"), (Fraction(1, 7), "'16S"), (Fraction(1, 14), "'32S"),
], key=lambda v: -v[0])

Timed = Tuple[str, Fraction, Fraction]      # (token, inizio, fine) in quarti


def timed_tokens(tokens: Sequence[str]) -> List[Timed]:
    """Ogni token con il suo intervallo, misurato dal parser."""
    ranges: List[Tuple[Fraction, Fraction]] = []
    _parse_tokens_exact(list(tokens), lenient=True, ranges=ranges)
    return [(tok, a, b) for tok, (a, b) in zip(tokens, ranges)]


def _rest_tokens(duration: Fraction) -> Optional[List[str]]:
    """Una pausa di 'duration' quarti scritta con valori di nota
    (2r'1 r'8...), indipendente dalla griglia; None se non si puo'."""
    out = []
    left = duration
    for value, suffix in _REST_VALUES:
        count = left // value
        if count:
            out.append(f"{count if count > 1 else ''}r{suffix}")
            left -= count * value
    return out if left == 0 else None


def _rest_tokens_any(duration: Fraction) -> List[str]:
    """Come _rest_tokens, ma sempre possibile: se i valori di nota non
    bastano, una griglia apposta dentro un blocco (cosi' non cambia quella
    del resto della traccia)."""
    tokens = _rest_tokens(duration)
    if tokens is not None:
        return tokens
    return ["{ " + f"{4 * duration.denominator}: {duration.numerator}r" + " }"]


def _sounding(tok: str, a: Fraction, b: Fraction) -> bool:
    return b > a and not RE_REST.match(tok)


def _state_prefix(timed: List[Timed], before_index: int) -> List[str]:
    """Ultima griglia e ultima velocity dei token prima di before_index."""
    grid = velocity = None
    for tok, _a, _b in timed[:before_index]:
        if RE_GRID.match(tok):
            grid = tok
        elif RE_VELOCITY.match(tok):
            velocity = tok
    return [t for t in (grid, velocity) if t]


def _regions(main: List[Timed], others: List[List[Timed]], bar_lines: List[Fraction]
             ) -> List[Tuple[Fraction, Fraction]]:
    """Tratti [a, b) in cui suonano le voci oltre la prima, allargati fino a
    punti in cui nessuna nota viene tagliata."""
    busy = sorted((a, b) for timed in others for tok, a, b in timed if _sounding(tok, a, b))
    if not busy:
        return []

    def blocking(t: Fraction, at_start: bool) -> Optional[Tuple[Fraction, Fraction]]:
        """Il primo token che attraversa t (e quindi impedisce di tagliare li')."""
        for tok, a, b in main:
            if a < t < b:
                return a, b
        for timed in others:
            for tok, a, b in timed:
                if a < t < b and (_sounding(tok, a, b) or (at_start and _rest_tokens(b - t) is None)):
                    return a, b
        return None

    def widen(a: Fraction, b: Fraction) -> Tuple[Fraction, Fraction]:
        while True:
            hit = blocking(a, True)
            if hit is None:
                break
            a = hit[0]
        while True:
            hit = blocking(b, False)
            if hit is None:
                break
            b = hit[1]
        # sulle stanghette, se li' si puo' tagliare e non si allarga troppo
        bar_a = max((t for t in bar_lines if t <= a), default=None)
        if bar_a is not None and a - bar_a < MERGE_GAP_BEATS and blocking(bar_a, True) is None:
            a = bar_a
        bar_b = min((t for t in bar_lines if t >= b), default=None)
        if bar_b is not None and bar_b - b < MERGE_GAP_BEATS and blocking(bar_b, False) is None:
            b = bar_b
        return a, b

    regions: List[Tuple[Fraction, Fraction]] = []
    for a, b in busy:
        if regions and a - regions[-1][1] < MERGE_GAP_BEATS:
            regions[-1] = (regions[-1][0], max(regions[-1][1], b))
        else:
            regions.append((a, b))
    while True:
        widened = []
        for a, b in (widen(a, b) for a, b in regions):
            if widened and a <= widened[-1][1]:
                widened[-1] = (widened[-1][0], max(widened[-1][1], b))
            else:
                widened.append((a, b))
        if widened == regions:
            return regions
        regions = widened


def _inside(tok: str, a: Fraction, b: Fraction, start: Fraction, end: Fraction) -> bool:
    if b > a:
        return start <= a and b <= end
    if is_lyric(tok):        # il testo cantato va con le note che lo precedono
        return start < a <= end
    return start <= a < end


def _before(tok: str, a: Fraction, b: Fraction, start: Fraction) -> bool:
    if b > a:
        return b <= start
    return a <= start if is_lyric(tok) else a < start


def merge_voices(voices: Sequence[Sequence[str]], time_sig: str = "4/4", metrica_changes=()) -> List[str]:
    """I token di una sola traccia: la prima voce, con un blocco { ; } dove
    suonano anche le altre. Con una voce sola, i suoi token invariati."""
    voices = [list(v) for v in voices if v]
    if len(voices) <= 1:
        return voices[0] if voices else []
    main = timed_tokens(voices[0])
    others = [timed_tokens(v) for v in voices[1:]]
    end = max([b for t in [main] + others for _tok, _a, b in t] + [Fraction(0)])
    bar_lines = []
    for line in bar_starts(time_sig, metrica_changes):
        if line > end:
            break
        bar_lines.append(line)
    regions = _regions(main, others, bar_lines)

    out: List[str] = []
    pos = 0                                   # indice del prossimo token della prima voce
    cursor = Fraction(0)                      # dove si trova il testo scritto finora

    def fill_to(t: Fraction) -> None:
        """Pausa fino a t (la prima voce puo' essere gia' finita, o
        finire prima del blocco successivo)."""
        nonlocal cursor
        if t > cursor:
            out.extend(_rest_tokens_any(t - cursor))
            cursor = t

    def emit_main(i: int) -> None:
        nonlocal cursor
        tok, a, b = main[i]
        if b > a:
            fill_to(a)
            cursor = max(cursor, b)
        out.append(tok)

    for start, stop in regions:
        while pos < len(main) and _before(*main[pos], start):
            emit_main(pos)
            pos += 1
        block_main = []
        block_end = start
        while pos < len(main) and _inside(*main[pos], start, stop):
            block_main.append(main[pos][0])
            block_end = max(block_end, main[pos][2])
            pos += 1
        parts = [block_main]
        for timed in others:
            inside = [i for i, (tok, a, b) in enumerate(timed) if _inside(tok, a, b, start, stop)]
            if not any(_sounding(*timed[i]) for i in inside):
                continue
            first = min((timed[i][1] for i in inside if timed[i][2] > timed[i][1]), default=start)
            rest = _rest_tokens_any(first - start) if first > start else []
            parts.append(_state_prefix(timed, inside[0]) + rest + [timed[i][0] for i in inside])
            block_end = max([block_end] + [timed[i][2] for i in inside])
        fill_to(start)
        if len(parts) == 1:
            out.extend(block_main)
        else:
            out.append("{ " + " ; ".join(" ".join(p) for p in parts) + " }")
            # dopo il blocco torna lo stato di prima: si riscrive quello della prima voce
            if any(RE_GRID.match(t) or RE_VELOCITY.match(t) for t in block_main):
                out.extend(_state_prefix(main, pos))
        cursor = max(cursor, block_end)
    for i in range(pos, len(main)):
        emit_main(i)
    return out


def merged_text(voices: Sequence[Sequence[str]], time_sig: str = "4/4", metrica_changes=()) -> str:
    """merge_voices come testo: i blocchi di voci su righe a se'."""
    lines: List[str] = []
    current: List[str] = []
    for tok in merge_voices(voices, time_sig, metrica_changes):
        if tok.startswith("{"):
            if current:
                lines.append(" ".join(current))
                current = []
            lines.append(tok)
        else:
            current.append(tok)
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines)


def check_round_trip(voices: Sequence[Sequence[str]], text: str) -> bool:
    """Per i test: il testo unito ha le stesse note (altezza, inizio,
    durata) delle voci separate."""
    from .notation import parse_tokens

    def notes(events):
        out = []
        for ev in events:
            if ev.kind in ("rest", "tempo_marker", "sustain", "control", "repeat", "text"):
                continue
            out.append((ev.kind, ev.letter, ev.octave, ev.symbol, ev.name,
                        tuple(sorted(str(i) for i in (ev.items or []))),
                        round(ev.start, 6), round(ev.duration, 6), ev.velocity))
        return sorted(out)
    separate = []
    for v in voices:
        separate += parse_tokens(list(v))
    return notes(separate) == notes(parse_tokens(tokenize(text)))
