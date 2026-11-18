"""
SoundText Mobile, fase 3: gli esercizi quotidiani.

Esercizi brevi da qualche minuto al giorno, per la scuola e per l'abitudine. Ogni esercizio e' deciso da tre
numeri, il tipo, il livello (1-3) e un seme, quindi e' infinito, ripetibile e si puo' passare a un altro
telefono con un link. La correzione e' automatica e non si fida del telefono: exercise_check() rifa' la domanda
dal seme e confronta.

Tipi: intervalli, accordi, giri armonici (riconoscerlo ascoltando), completa la battuta, trova l'errore e
dettato ritmico. La domanda dice cosa si ascolta (note con i tempi in battiti, per il sintetizzatore) e cosa si
risponde: una scelta fra opzioni, una nota da indicare, o i passi di una griglia ritmica.

Solo Python standard (e core.i18n per le etichette): gira in Pyodide con il resto del motore.
"""

import random
from typing import Dict, List, Optional

from core.i18n import tr

KINDS = ("intervals", "chords", "progression", "bar", "error", "rhythm")
LEVELS = (1, 2, 3)

_NOTE_NAMES_SHARP = ("c", "c#", "d", "d#", "e", "f", "f#", "g", "g#", "a", "a#", "b")
_LETTERS_SHARP = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
_LETTERS_FLAT = ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B")
_MAJOR = (0, 2, 4, 5, 7, 9, 11)
_MINOR = (0, 2, 3, 5, 7, 8, 10)
_FLAT_KEYS = {5, 10, 3, 8}                     # Fa, Sib, Mib, Lab maggiori


def _note(t: float, d: float, n: int, ch: int = 0, v: int = 90) -> dict:
    return {"t": round(t, 4), "d": round(d, 4), "n": int(n), "ch": ch, "v": v}


def _name(midi: int) -> str:
    """Una nota MIDI come la scrive ST: c*4 e' il do centrale."""
    return f"{_NOTE_NAMES_SHARP[midi % 12]}*{midi // 12 - 1}"


def _rng(kind: str, level: int, seed: int) -> random.Random:
    return random.Random(f"{kind}/{level}/{int(seed)}")


def _choices(pairs) -> List[dict]:
    return [{"value": value, "label": label} for value, label in pairs]


# ------------------------------------------------------------ intervalli

def _interval_labels() -> Dict[int, str]:
    return {1: tr("seconda minore"), 2: tr("seconda maggiore"), 3: tr("terza minore"), 4: tr("terza maggiore"),
            5: tr("quarta giusta"), 6: tr("tritono"), 7: tr("quinta giusta"), 8: tr("sesta minore"),
            9: tr("sesta maggiore"), 10: tr("settima minore"), 11: tr("settima maggiore"), 12: tr("ottava")}


def _intervals(level: int, rng: random.Random) -> dict:
    pool = (3, 4, 5, 7, 12) if level == 1 else tuple(range(1, 13))
    semitones = rng.choice(pool)
    root = rng.randint(55, 67)
    other = root + semitones
    notes = [_note(0, 1.5, root), _note(1.5, 1.5, other)]
    if level >= 2 and rng.random() < 0.3:                      # dall'alto in basso
        notes = [_note(0, 1.5, other), _note(1.5, 1.5, root)]
    if level == 3 and rng.random() < 0.34:                     # insieme
        notes = [_note(0, 3, root), _note(0, 3, other)]
    labels = _interval_labels()
    return {"prompt": tr("Che intervallo senti?"), "input": "choice", "notes": notes, "bpm": 80,
            "choices": _choices((s, labels[s]) for s in pool), "answer": semitones, "answer_label": labels[semitones]}


# ------------------------------------------------------------ accordi

_CHORD_SHAPES = {"maj": (0, 4, 7), "min": (0, 3, 7), "dim": (0, 3, 6), "aug": (0, 4, 8), "sus4": (0, 5, 7),
                 "7": (0, 4, 7, 10), "maj7": (0, 4, 7, 11), "m7": (0, 3, 7, 10), "m7b5": (0, 3, 6, 10)}


def _chord_labels() -> Dict[str, str]:
    return {"maj": tr("maggiore"), "min": tr("minore"), "dim": tr("diminuito"), "aug": tr("aumentato"),
            "sus4": tr("sospeso (sus4)"), "7": tr("settima di dominante"), "maj7": tr("settima maggiore"),
            "m7": tr("minore con settima"), "m7b5": tr("semidiminuito")}


def _chords(level: int, rng: random.Random) -> dict:
    pool = {1: ("maj", "min"), 2: ("maj", "min", "dim", "aug", "sus4"),
            3: ("maj", "min", "dim", "aug", "7", "maj7", "m7", "m7b5")}[level]
    quality = rng.choice(pool)
    root = rng.randint(48, 58)
    pitches = [root + i for i in _CHORD_SHAPES[quality]]
    notes = [_note(0, 3, n) for n in pitches]
    if level >= 2 and rng.random() < 0.5:                      # arpeggiato: le note entrano una dopo l'altra e restano
        notes = [_note(i * 0.5, 3.0 - i * 0.5, n) for i, n in enumerate(pitches)]
    labels = _chord_labels()
    return {"prompt": tr("Che accordo senti?"), "input": "choice", "notes": notes, "bpm": 80,
            "choices": _choices((q, labels[q]) for q in pool), "answer": quality, "answer_label": labels[quality]}


# ------------------------------------------------------------ giri armonici

# (scostamento dalla tonica, qualita') per accordo; i numeri romani sono l'etichetta della risposta
_MAJOR_LOOPS = {
    "I – V – vi – IV": ((0, ""), (7, ""), (9, "m"), (5, "")),
    "I – IV – V – I": ((0, ""), (5, ""), (7, ""), (0, "")),
    "I – vi – IV – V": ((0, ""), (9, "m"), (5, ""), (7, "")),
    "I – IV – I – V": ((0, ""), (5, ""), (0, ""), (7, "")),
    "ii – V – I – I": ((2, "m"), (7, ""), (0, ""), (0, "")),
    "I – iii – IV – V": ((0, ""), (4, "m"), (5, ""), (7, "")),
    "vi – IV – I – V": ((9, "m"), (5, ""), (0, ""), (7, "")),
    "I – vi – ii – V": ((0, ""), (9, "m"), (2, "m"), (7, "")),
}
_MINOR_LOOPS = {
    "i – VI – III – VII": ((0, "m"), (8, ""), (3, ""), (10, "")),
    "i – iv – V – i": ((0, "m"), (5, "m"), (7, ""), (0, "m")),
    "i – VII – VI – VII": ((0, "m"), (10, ""), (8, ""), (10, "")),
    "i – iv – VII – III": ((0, "m"), (5, "m"), (10, ""), (3, "")),
    "i – VI – iv – V": ((0, "m"), (8, ""), (5, "m"), (7, "")),
}
_LOOP_POOLS = {1: (_MAJOR_LOOPS, ("I – V – vi – IV", "I – IV – V – I", "I – vi – IV – V", "I – IV – I – V")),
               2: (_MAJOR_LOOPS, tuple(_MAJOR_LOOPS)),
               3: (None, None)}


def _progression(level: int, rng: random.Random) -> dict:
    if level == 3:
        loops, names = (_MINOR_LOOPS, tuple(_MINOR_LOOPS)) if rng.random() < 0.5 else (_MAJOR_LOOPS, tuple(_MAJOR_LOOPS))
    else:
        loops, names = _LOOP_POOLS[level]
    minor = loops is _MINOR_LOOPS
    tonic = rng.randint(48, 54)
    answer = rng.choice(names)
    options = [answer] + rng.sample([n for n in names if n != answer], 3)
    rng.shuffle(options)
    notes = []
    for i, (offset, quality) in enumerate(loops[answer]):
        root = tonic + offset
        shape = (0, 3, 7) if quality == "m" else (0, 4, 7)
        notes += [_note(i * 2, 2, root - 12, v=80)] + [_note(i * 2, 2, root + s, v=85) for s in shape]
    return {"prompt": tr("Quale giro armonico senti?"), "input": "choice", "notes": notes, "bpm": 84,
            "choices": _choices((n, n) for n in options), "answer": answer, "answer_label": answer,
            "context": tr("in tonalità minore") if minor else tr("in tonalità maggiore")}


# ------------------------------------------------------------ completa la battuta

# durate in sedicesimi
def _value_labels() -> Dict[int, str]:
    return {1: tr("semicroma"), 2: tr("croma"), 3: tr("croma col punto"), 4: tr("semiminima"), 6: tr("semiminima col punto"),
            8: tr("minima"), 12: tr("minima col punto"), 16: tr("semibreve")}


def _fill_bar(units: int, pool, rng: random.Random) -> Optional[List[int]]:
    for _ in range(60):
        out, left = [], units
        while left:
            options = [v for v in pool if v <= left]
            if not options:
                break
            value = rng.choice(options)
            out.append(value)
            left -= value
        if not left and 3 <= len(out) <= 8:
            return out
    return None


def _bar(level: int, rng: random.Random) -> dict:
    meters = {1: (("4/4", 16),), 2: (("4/4", 16), ("3/4", 12)), 3: (("4/4", 16), ("3/4", 12), ("6/8", 12))}[level]
    pool = {1: (2, 4, 8), 2: (2, 3, 4, 6, 8), 3: (1, 2, 3, 4, 6, 8, 12)}[level]
    meter, units = rng.choice(meters)
    values = None
    while values is None:
        values = _fill_bar(units, pool, rng)
    rests = [level == 3 and rng.random() < 0.2 for _ in values]
    missing = rng.randrange(len(values))
    names = _value_labels()
    items = [{"label": names[v], "rest": r, "missing": i == missing} for i, (v, r) in enumerate(zip(values, rests))]
    pitches = [60, 62, 64, 65, 67, 69, 71, 72]
    notes, at = [], 0
    for i, (v, r) in enumerate(zip(values, rests)):
        if not r:
            notes.append(_note(at / 4, v / 4, pitches[i % len(pitches)]))
        at += v
    tokens = [f"{v}r" if r else f"{v}{_name(pitches[i % len(pitches)])}" for i, (v, r) in enumerate(zip(values, rests))]
    prompt = tr("Che durata ha la pausa che manca?") if rests[missing] else tr("Che durata ha la nota che manca?")
    return {"prompt": prompt, "input": "choice", "meter": meter, "items": items,
            "notes": notes, "bpm": 80, "context": tr("Metrica {meter}", meter=meter),
            "choices": _choices((v, names[v]) for v in pool), "answer": values[missing], "answer_label": names[values[missing]],
            "st": {"meter": meter, "text": "16: " + " ".join(tokens) + " |"}}


# ------------------------------------------------------------ trova l'errore

def _error(level: int, rng: random.Random) -> dict:
    tonic = rng.choice((0, 2, 4, 5, 7, 9, 10))
    flats = tonic in _FLAT_KEYS
    spelling = _LETTERS_FLAT if flats else _LETTERS_SHARP
    length = {1: 5, 2: 6, 3: 8}[level]
    leap = {1: 1, 2: 2, 3: 3}[level]
    degree = rng.randint(2, 4)
    degrees = [degree]
    while len(degrees) < length:
        step = rng.choice([s for s in range(-leap, leap + 1) if s != 0])
        nxt = max(0, min(9, degrees[-1] + step))
        degrees.append(nxt if nxt != degrees[-1] else degrees[-1] + 1)
    pitches = [60 + tonic + _MAJOR[d % 7] + 12 * (d // 7) for d in degrees]
    wrong = rng.randrange(1, length - 1)
    scale_pcs = {(tonic + s) % 12 for s in _MAJOR}
    options = [p for p in (pitches[wrong] - 1, pitches[wrong] + 1) if p % 12 not in scale_pcs]
    shifted = rng.choice(options)
    played = list(pitches)
    played[wrong] = shifted
    notes = [_note(i * 1.0, 0.9, p) for i, p in enumerate(played)]
    return {"prompt": tr("Una nota non è della tonalità: quale?"), "input": "pick", "notes": notes, "bpm": 90,
            "items": [spelling[p % 12] for p in played], "answer": wrong, "answer_label": spelling[shifted % 12],
            "context": tr("Tonalità: {key} maggiore", key=spelling[tonic]),
            "info": {"tonic": tonic, "wrong": wrong, "original": pitches[wrong], "scale": sorted(scale_pcs)}}


# ------------------------------------------------------------ dettato ritmico

def _rhythm(level: int, rng: random.Random) -> dict:
    per_bar = 8 if level == 1 else 16                          # passi per battuta: crome o semicrome
    bars = 2 if level == 3 else 1
    steps = per_bar * bars
    hits = rng.randint(3, 5) if level == 1 else rng.randint(4, 7) if level == 2 else rng.randint(6, 10)
    chosen = {0}
    while len(chosen) < hits:
        chosen.add(rng.randrange(steps))
    if level == 3:                                             # almeno una sincope: un colpo fuori dai battiti
        off = [s for s in range(steps) if s % 4 != 0]
        chosen.add(rng.choice(off))
    active = sorted(chosen)
    unit = 0.5 if level == 1 else 0.25                         # un passo in battiti
    notes = [_note(i, 0.4, 42, ch=9, v=70) for i in range(4)]       # il conteggio: quattro colpi di charleston
    notes += [_note(4 + s * unit, 0.3, 75, ch=9, v=105) for s in active]       # claves
    return {"prompt": tr("Scrivi il ritmo che senti: tocca i passi dove c'è un colpo."), "input": "grid",
            "grid": {"per_bar": per_bar, "bars": bars, "beats_per_bar": 4}, "notes": notes, "bpm": 80,
            "context": tr("Prima il conteggio di quattro battiti"), "answer": active,
            "answer_label": " ".join(str(s + 1) for s in active)}


_MAKERS = {"intervals": _intervals, "chords": _chords, "progression": _progression, "bar": _bar, "error": _error,
           "rhythm": _rhythm}


def exercise_kinds() -> list:
    """I tipi di esercizio, con l'etichetta nella lingua dell'interfaccia e come si risponde."""
    labels = {"intervals": tr("Intervalli"), "chords": tr("Accordi"), "progression": tr("Giri armonici"),
              "bar": tr("Completa la battuta"), "error": tr("Trova l'errore"), "rhythm": tr("Dettato ritmico")}
    hints = {"intervals": tr("Ascolta due note e di' che intervallo c'è."),
             "chords": tr("Ascolta un accordo e di' di che tipo è."),
             "progression": tr("Ascolta quattro accordi e riconosci il giro."),
             "bar": tr("In una battuta manca una durata: trovala."),
             "error": tr("Una melodia ha una nota fuori tonalità: indicala."),
             "rhythm": tr("Ascolta un ritmo e scrivilo su una griglia.")}
    return [{"kind": k, "label": labels[k], "hint": hints[k], "levels": len(LEVELS)} for k in KINDS]


def _checked(kind: str, level: int):
    if kind not in _MAKERS:
        raise ValueError(f"tipo di esercizio sconosciuto: {kind}")
    if int(level) not in LEVELS:
        raise ValueError(f"livello sconosciuto: {level}")
    return _MAKERS[kind]


def exercise(kind: str, level: int, seed: int) -> dict:
    """La domanda: {kind, level, seed, prompt, input ('choice', 'pick' o 'grid'), notes, bpm, choices o items o
    grid, e a seconda del tipo context, items (la battuta), meter}. Senza la risposta."""
    maker = _checked(kind, level)
    full = maker(int(level), _rng(kind, int(level), seed))
    hidden = ("answer", "answer_label", "info", "st")
    out = {k: v for k, v in full.items() if k not in hidden}
    if kind == "bar":
        out["notes"] = []                       # sentire la battuta (o il vuoto) direbbe la durata che manca
    out.update(kind=kind, level=int(level), seed=int(seed))
    return out


def exercise_check(kind: str, level: int, seed: int, answer) -> dict:
    """La correzione: {correct, answer_label, notes}. 'answer' e' il valore scelto (intero o testo), l'indice
    della nota, o la lista dei passi della griglia. 'notes' (per tipi che lo chiedono) e' da riascoltare dopo:
    la battuta completa, la melodia giusta."""
    maker = _checked(kind, level)
    full = maker(int(level), _rng(kind, int(level), seed))
    expected = full["answer"]
    if full["input"] == "grid":
        try:
            correct = sorted({int(s) for s in answer}) == list(expected)
        except (TypeError, ValueError):
            correct = False
    else:
        correct = answer == expected or str(answer) == str(expected)
    out = {"correct": bool(correct), "answer_label": full["answer_label"], "answer": expected}
    if kind == "bar":
        out["notes"] = full["notes"]            # la battuta completa, da ascoltare dopo la risposta
    if kind == "error":
        info = full["info"]
        fixed = list(full["notes"])
        wrong = info["wrong"]
        fixed[wrong] = dict(fixed[wrong], n=info["original"])          # la nota giusta, da riascoltare
        out["notes"] = fixed
    return out
