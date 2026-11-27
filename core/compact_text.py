"""Testo generato leggibile (docs, sezione 8.1): lo scrive come lo scriverebbe una persona.

I generatori (core.rhythm_generate) scrivono una riga continua di eventi, senza barre di battuta e senza pattern. Qui
quella riga diventa:

    Pattern %Rock:
      16: 105@ kick r 70@ hihat r 100@ [snare hihat] r 70@ hihat r

    16: %Rock | %Rock | %Rock | %RockFill |

1. una barra | a ogni battuta (dove nessuna nota attraversa la stanghetta: una pausa lunga si divide, una nota no);
2. le battute uguali diventano un pattern con un nome che dice lo stile (%Rock, %Walking); le diverse (fill, finali)
   restano scritte;
3. la velocity si scrive solo quando cambia (e all'inizio di ogni pattern);
4. si ripete la griglia (es. «16:») dove serve.

Il suono non cambia: il testo compatto, con i suoi pattern, da' esattamente gli stessi eventi di quello esteso (lo
verifica tests/test_compact_text.py, per ogni stile e molti semi). Si applica come ultimo passo, quando la parte entra
nel brano: le funzioni che lavorano sul testo dei generatori (rigenerare battute, arrangiare) vogliono il testo esteso.
"""

import re
from collections import Counter
from fractions import Fraction
from typing import Dict, List, Optional, Tuple

_TOKEN = re.compile(r"(\d*)(.+)", re.S)
BARS_PER_LINE = 4


def _camel(name: str) -> str:
    """'walking' -> 'Walking', 'quarter_chords' -> 'QuarterChords': un nome di pattern valido."""
    words = re.split(r"[^A-Za-z0-9]+", name or "")
    out = "".join(w[:1].upper() + w[1:] for w in words if w)
    return out if out and out[0].isalpha() else "Parte"


def _tieable(body: str) -> bool:
    """Una nota, un accordo o un blocco che si puo' dividere alla stanghetta con la legatura: non le pause, gli slide (portano
    le loro durate), gli abbellimenti, le legature di portamento o le note gia' legate o allungate."""
    return body != "r" and not any(ch in body for ch in ">'()~_%") and not body.endswith("!")


def _bars(grid_text: str, items: list, bar_beats: float):
    """[(token, velocita')...] per battuta e il numero di battute; None se la metrica non cade sulla griglia.
    Ritorna (lista di battute, [True se la stanghetta dopo la battuta si puo' scrivere])."""
    m = re.match(r"(\d+)(T?):", grid_text)
    unit = Fraction(4, int(m.group(1))) * (Fraction(2, 3) if m.group(2) else 1)
    bar_units = Fraction(bar_beats).limit_denominator(64) / unit
    if bar_units.denominator != 1 or bar_units <= 0:
        return None
    bar_units = int(bar_units)
    bars: List[list] = []
    closed: List[bool] = []
    for start, end, tok, vel in items:
        mult_s, body = _TOKEN.fullmatch(tok).groups()
        length = int((end - start) / unit)
        k = int(start / unit)
        while True:
            index = k // bar_units
            while len(bars) <= index:
                bars.append([])
                closed.append(True)
            room = (index + 1) * bar_units - k
            if length > room and _tieable(body):
                # una nota che attraversa la stanghetta: si divide con la legatura (c~ | c), la stanghetta resta
                bars[index].append((room, body + "~", vel))
                length -= room
                k += room
                continue
            if length <= room or body != "r":
                bars[index].append((length, body, vel))
                if length > room:                    # una nota che attraversa la stanghetta: li' non si scrive
                    last = (k + length - 1) // bar_units
                    for j in range(index, last):
                        while len(closed) <= j:
                            closed.append(True)
                        closed[j] = False
                    while len(bars) <= last:
                        bars.append([])
                        closed.append(True)
                break
            bars[index].append((room, "r", vel))     # una pausa lunga si divide alla stanghetta
            length -= room
            k += room
    return bars, closed, unit


def _write(tokens: List[Tuple[int, str, Optional[int]]], current: Optional[int]) -> Tuple[str, Optional[int]]:
    """Le battute come testo, con la velocity solo dove cambia a partire da 'current'."""
    out = []
    for length, body, vel in tokens:
        if body != "r" and vel is not None and vel != current:
            out.append(f"{vel}@")
            current = vel
        out.append((str(length) if length > 1 and ">" not in body else "") + body)   # uno slide porta le sue durate nei tratti
    return " ".join(out), current


def compact(text: str, bar_beats: float, name: str = "", existing: Optional[Dict[str, str]] = None,
            per_line: int = BARS_PER_LINE, make_patterns: bool = True) -> dict:
    """{"text": il testo compatto, "patterns": {nome: corpo}} per un testo scritto dai generatori. Un testo che non e' di
    quella forma (modificato a mano) o una metrica che non cade sulla griglia resta com'e', senza pattern.

    existing: i pattern gia' nel brano {nome: corpo}: uno uguale si riusa, uno con lo stesso nome e un corpo diverso
    fa prendere un nome nuovo (Rock2)."""
    from .rhythm_generate import _generated_timeline
    existing = existing or {}
    try:
        grid, items = _generated_timeline(text)
        # solo testo davvero generato: una stanghetta, un marcatore tempo=, un richiamo o un gruppo scritti a mano restano com'e'
        if any(re.search(r"[|=%&$(){}~]", _TOKEN.fullmatch(tok).group(2)) for _s, _e, tok, _v in items):
            return {"text": text, "patterns": {}}
        built = _bars(grid, items, bar_beats) if items else None
    except (ValueError, AttributeError, KeyError):
        built = None
    if built is None:
        return {"text": text, "patterns": {}}
    bars, closed, _unit = built
    # chiave di una battuta: la velocity con cui comincia e i suoi token
    def key(index):
        tokens = bars[index]
        first = next((v for _l, b, v in tokens if b != "r" and v is not None), None)
        return (first, tuple(tokens))
    # una battuta legata alla successiva (o che continua la precedente) resta scritta: la legatura non passa dentro un pattern
    def tied(index):
        ends = bool(bars[index]) and bars[index][-1][1].endswith("~")
        return ends or (index > 0 and bool(bars[index - 1]) and bars[index - 1][-1][1].endswith("~"))
    # una battuta di sole pause resta scritta («8r»): un pattern che non suona niente non serve a chi legge
    def silent(index):
        return all(b == "r" for _l, b, _v in bars[index])
    counts = Counter(key(i) for i in range(len(bars)) if bars[i] and not tied(i) and not silent(i))
    # senza pattern ('make_patterns' falso: lo sfumato, dove ogni battuta ha la sua velocity) restano solo barre e righe
    repeated = [k for k, n in counts.most_common() if n >= 2 and len(k[1]) >= 1] if make_patterns else []
    base = _camel(name)
    patterns: Dict[str, str] = {}
    names: Dict[tuple, str] = {}
    for rank, k in enumerate(repeated):
        body, _cur = _write(list(k[1]), None)
        body = f"{grid} {body}"
        label = base + ("" if rank == 0 else chr(ord("A") + rank) if rank < 26 else str(rank))
        final, n = label, 2
        while final in existing and existing[final] != body or final in patterns:
            final, n = f"{label}{n}", n + 1
        names[k] = final
        if final not in existing:
            patterns[final] = body
    pieces: List[str] = []
    current: Optional[int] = None
    unknown = False                               # dopo un richiamo di pattern la velocity in vigore non si da' per nota
    for i, tokens in enumerate(bars):
        if not tokens:
            pieces.append("")
            continue
        k = key(i)
        if k in names and not tied(i):
            pieces.append("%" + names[k])
            unknown = True
        else:
            body, current_after = _write(tokens, None if unknown else current)
            pieces.append(body)
            current = current_after
            unknown = False
    # le stanghette (dove si possono scrivere) e le righe
    lines, line, count = [], [], 0
    for i, piece in enumerate(pieces):
        line.append(piece)
        count += 1
        last = i == len(pieces) - 1
        sep = " |" if closed[i] or last else ""
        line[-1] = line[-1] + sep
        if count % per_line == 0 and not last:
            lines.append(" ".join(line))
            line = []
    if line:
        lines.append(" ".join(line))
    text_out = grid + " " + lines[0]
    if len(lines) > 1:
        text_out += "\n" + "\n".join(lines[1:])
    return {"text": text_out, "patterns": patterns}


def with_patterns(text: str, patterns: Dict[str, str]) -> str:
    """Il testo di un file con i blocchi «Pattern %Nome:» in testa a 'text' (per scriverlo in un file .st)."""
    blocks = [f"Pattern %{n}:\n  {b}" for n, b in patterns.items()]
    return "\n\n".join(blocks + [text]) if blocks else text


def compact_for_project(project, text: str, name: str = "", per_line: int = BARS_PER_LINE) -> dict:
    """Come compact(), con la metrica e i pattern del progetto: un pattern gia' nel progetto con lo stesso corpo si riusa;
    con un corpo diverso, il nuovo prende un altro nome. Il progetto non cambia."""
    from .rhythm_generate import project_bar_beats
    existing = {n: " ".join(p.tokens) for n, p in project.patterns.items()}
    return compact(text, project_bar_beats(project), name, existing=existing, per_line=per_line)


def compact_into_project(project, text: str, name: str = "", per_line: int = BARS_PER_LINE) -> str:
    """Compatta 'text' (scritto da un generatore) e mette i pattern che ne escono nel progetto: ritorna il testo compatto."""
    made = compact_for_project(project, text, name, per_line)
    for pname, body in made["patterns"].items():
        project.add_pattern(pname, body)
    return made["text"]
