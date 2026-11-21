"""Esecuzione piu' umana (docs, 8.3): il micro-tempo di ogni stile scritto nel testo con «shift=N» (millisecondi: positivo =
dopo, negativo = prima), che sposta il suono e non il ritmo scritto. Per esempio il rullante un po' indietro nel funk e nel
soul, la cassa avanti nel punk. «amount» (0-1) scala tutto: 0 lascia il testo com'e', la griglia esatta."""

import re
from typing import Dict

# millisecondi per suono di batteria, per stile (i nomi di core.rhythm_generate.DRUM_STYLES)
DRUM_SHIFT: Dict[str, Dict[str, int]] = {
    "funk": {"snare": 14, "clap": 14},
    "soul": {"snare": 16, "clap": 16},
    "hiphop": {"snare": 18, "clap": 18},
    "halftime": {"snare": 10},
    "reggae": {"snare": 8, "rim": 8},
    "disco": {"snare": 4},
    "punk": {"kick": -6, "snare": -3},
    "rocknroll": {"kick": -4},
    "metal": {"kick": -4},
    "rock": {"kick": -3, "snare": 4},
}

_TOKEN = re.compile(r"\[[^\]]*\]\S*|\S+")
_NAME = re.compile(r"^\d*([a-z][a-z0-9_]*)(?:\*\d+)?$")


def _shift_of(token: str, table: Dict[str, int]) -> int:
    """I millisecondi del suono che il token suona (0 se non e' un suono con micro-tempo)."""
    if token.startswith("["):
        members = re.findall(r"[a-z][a-z0-9_]*", token[1:token.index("]")])
        return next((table[m] for m in members if m in table), 0)
    found = _NAME.match(token)
    return table.get(found.group(1), 0) if found else 0


def humanize_drums(text: str, style: str, amount: float = 1.0) -> str:
    """Il testo di una batteria con «shift=N» prima dei suoni dello stile; il micro-tempo torna a 0 alla fine del testo
    (un pattern richiamato non lo lascia acceso)."""
    table = DRUM_SHIFT.get(style or "")
    if not table or amount <= 0 or "shift=" in text:
        return text
    scaled = {name: int(round(ms * amount)) for name, ms in table.items()}
    out, current = [], 0
    for token in _TOKEN.findall(text):
        if token.endswith(":") or token == "|" or re.fullmatch(r"\d*r", token) or re.fullmatch(r"\d+@", token) or token.startswith("%"):
            if token.startswith("%") and current:
                out.append("shift=0")
                current = 0
            out.append(token)
            continue
        want = _shift_of(token, scaled)
        if want != current:
            out.append(f"shift={want}")
            current = want
        out.append(token)
    if current:
        out.append("shift=0")
    return " ".join(out).replace(" |", " |")


# millisecondi per parte melodica (basso e accompagnamento) e genere: la parte intera suona un po' dopo (+) o prima (-)
PART_SHIFT: Dict[str, Dict[str, int]] = {
    "bass": {"soul": 8, "reggae": 6, "funk": -5, "rock": -3, "punk": -4, "metal": -3},
    "comp": {"reggae": 10, "soul": 6, "funk": 4},
}


def humanize_part(text: str, part: str, genre: str, amount: float = 1.0) -> str:
    """Basso o accompagnamento di un genere: «shift=N» davanti a tutto il testo e «shift=0» alla fine, anche attraverso i
    pattern richiamati (la parte intera spostata di pochi millisecondi, come un musicista dietro o davanti al tempo)."""
    ms = int(round(PART_SHIFT.get(part, {}).get(genre, 0) * amount))
    if not ms or "shift=" in text:
        return text
    return f"shift={ms} {text.strip()} shift=0"
