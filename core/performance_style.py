"""
Esecuzione per strumento: un testo generato (accompagnamento, basso) che
suona come lo suonerebbe un musicista, invece di accordi tutti simultanei e
note tutte uguali.

- Chitarra: strumming. Ogni accordo diventa un blocco di voci
  ("{c*3 ; shift=10 e*3 ; ...}") che partono a pochi millisecondi una
  dall'altra: in giu' (dal basso all'acuto) sui tempi, in su (dall'acuto al
  basso, piu' piano) in levare.
- Pianoforte: pedale di risonanza (SON/SOFF), cambiato a ogni accordo nuovo.
- Basso: note fantasma (stoppate, piano) nella pausa prima di un attacco
  sul tempo, e qualche slide verso la nota dell'accordo successivo.

Lavora sugli eventi del testo e lo riscrive sulla sua griglia: se il testo
non ha una griglia sola, o contiene altro (sigle d'accordo, voci), resta
com'e'.
"""

import random
import re
from typing import List, Optional

STRUM_MS = 12                  # fra una corda e l'altra
UP_STROKE_VELOCITY = -14       # le pennate in su sono piu' leggere
GHOST_VELOCITY = 38
SLIDE_PROBABILITY = 0.3
SLIDE_MAX_SEMITONES = 5

STYLES = ("guitar", "piano", "bass")


def style_for(instrument) -> Optional[str]:
    """Lo stile d'esecuzione di uno strumento, o None."""
    from .instruments import gm_family_for_program
    if instrument is None or instrument.is_percussion:
        return None
    family = gm_family_for_program(instrument.gm_program)
    return {"Chitarre": "guitar", "Pianoforti": "piano", "Bassi": "bass"}.get(family)


def _grid(text: str):
    m = re.match(r"\s*(\d+)(T?):", text)
    if not m:
        return None, None
    unit = 4.0 / int(m.group(1))
    return (unit * 2.0 / 3.0 if m.group(2) else unit), m.group(0).strip()


def _pitch(letter: str, octave: int) -> int:
    from .chords import pitch_to_midi
    return pitch_to_midi(letter, octave)


def _token(letter, octave) -> str:
    return f"{letter}*{octave}"


def perform(text: str, style: str, seed: Optional[int] = None, patterns=None) -> str:
    """Il testo con l'esecuzione dello strumento 'style' (vedi STYLES)."""
    from .notation import parse_track_text
    unit, header = _grid(text)
    if unit is None or style not in STYLES:
        return text
    try:
        events = parse_track_text(text, patterns or {})
    except Exception:
        return text
    items = []
    for ev in events:
        mult = ev.duration / unit
        if abs(mult - round(mult)) > 1e-6 or round(mult) < 1:
            return text
        if ev.kind == "note" and ev.letter:
            items.append({"kind": "note", "start": ev.start, "mult": int(round(mult)), "velocity": ev.velocity,
                          "notes": [(ev.letter, ev.octave)], "articulation": ev.articulation})
        elif ev.kind == "block" and ev.items and all(it.get("kind") == "note" for it in ev.items):
            items.append({"kind": "block", "start": ev.start, "mult": int(round(mult)), "velocity": ev.velocity,
                          "notes": [(it["letter"], it["octave"]) for it in ev.items], "articulation": None})
        elif ev.kind == "rest":
            items.append({"kind": "rest", "start": ev.start, "mult": int(round(mult)), "velocity": ev.velocity})
        else:
            return text                       # sigle, slide, voci, controlli: non si tocca
    rng = random.Random(seed)
    if style == "bass":
        items = _bass(items, unit, rng)
    return _write(items, header, unit, style)


def _bass(items: List[dict], unit: float, rng: random.Random) -> List[dict]:
    out: List[dict] = []
    for i, item in enumerate(items):
        nxt = items[i + 1] if i + 1 < len(items) else None
        # nota fantasma: l'ultima unita' di una pausa prima di una nota sul tempo
        if (item["kind"] == "rest" and nxt is not None and nxt["kind"] == "note"
                and abs(nxt["start"] - round(nxt["start"])) < 1e-6 and item["mult"] >= 2):
            out.append(dict(item, mult=item["mult"] - 1))
            letter, octave = nxt["notes"][0]
            out.append({"kind": "note", "start": nxt["start"] - unit, "mult": 1, "velocity": GHOST_VELOCITY,
                        "notes": [(letter, octave)], "articulation": "mute"})
            continue
        # slide verso la nota dopo, se e' vicina e questa e' lunga
        if (item["kind"] == "note" and nxt is not None and nxt["kind"] == "note" and item["mult"] >= 2
                and item["notes"] != nxt["notes"]
                and abs(_pitch(*item["notes"][0]) - _pitch(*nxt["notes"][0])) <= SLIDE_MAX_SEMITONES
                and rng.random() < SLIDE_PROBABILITY):
            out.append(dict(item, mult=item["mult"] - 1))
            out.append({"kind": "slide", "start": item["start"] + (item["mult"] - 1) * unit, "mult": 1,
                        "velocity": item["velocity"], "notes": [item["notes"][0], nxt["notes"][0]]})
            continue
        out.append(item)
    return out


def _write(items: List[dict], header: str, unit: float, style: str) -> str:
    tokens = [header]
    velocity = None
    pedal = False
    for item in items:
        prefix = str(item["mult"]) if item["mult"] > 1 else ""
        if item["kind"] == "rest":
            tokens.append(prefix + "r")
            continue
        v = item["velocity"]
        on_beat = abs(item["start"] - round(item["start"])) < 1e-6
        if style == "guitar" and item["kind"] == "block" and not on_beat:
            v = max(1, v + UP_STROKE_VELOCITY)
        if v != velocity:
            tokens.append(f"{v}@")
            velocity = v
        if style == "piano" and item["kind"] == "block":
            # pedale cambiato a ogni accordo: si alza e si riabbassa sull'attacco
            tokens.append("SOFF SON" if pedal else "SON")
            pedal = True
        if item["kind"] == "slide":
            (a, ao), (b, bo) = item["notes"]
            tokens.append(f"{prefix}{_token(a, ao)}>{_token(b, bo)}")
        elif item["kind"] == "note":
            mark = "x" if item.get("articulation") == "mute" else ""
            tokens.append(prefix + _token(*item["notes"][0]) + mark)
        elif style == "guitar" and len(item["notes"]) > 1:
            notes = sorted(item["notes"], key=lambda n: _pitch(*n))
            if not on_beat:
                notes.reverse()                        # pennata in su
            voices = [f"{prefix}{_token(*n)}" if k == 0 else f"shift={k * STRUM_MS} {prefix}{_token(*n)}"
                      for k, n in enumerate(notes)]
            tokens.append("{" + " ; ".join(voices) + "}")
        else:
            tokens.append(prefix + "[" + " ".join(_token(*n) for n in item["notes"]) + "]")
    if pedal:
        tokens.append("SOFF")
    return " ".join(tokens)
