"""
Che cosa suona un richiamo di pattern con funzioni (%Tema.invert(e*5).retro)
nel punto del testo in cui e' scritto: lo usano l'anteprima delle note e la
finestra Trasforma (gui.transform_preview, gui.transform_dialog). I calcoli
sono di st_language.transform.expand_reference, a cui qui si danno la griglia,
la velocity e la tonalita' di quel punto; il risultato si ricorda per richiamo
e testo del progetto. Anche il suffisso .arpeggio degli accordi sta qui.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from st_language.transform import Expansion, expand_reference, is_transform_reference

from .i18n import tr
from .model import Project, copy_synth
from .notation import (RE_ARPEGGIO_SUFFIX, RE_CHORD, RE_KEY_MODE, all_token_spans, compute_token_spans,
                       context_prefix_before, parse_track_text, split_note_value)

RE_REFERENCE = re.compile(r"\d*%\w+(?:[+-]\d+)*(?:\.\w+(?:\([^()\s]*\))?(?:[+-]\d+)?)*")
MAX_NOTES_SHOWN = 12        # per ogni passo della catena

_cache: Dict[tuple, Expansion] = {}


@dataclass
class ReferencePoint:
    """Il punto del testo in cui sta un richiamo."""
    prefix: str = ""            # i comandi di griglia e velocity in vigore
    grid: float = 1.0           # in quarti
    velocity: int = 80
    position: float = 0.0       # in quarti, dall'inizio del brano
    key: str = ""               # il key= in vigore


def reference_at(text: str, pos: int, with_functions: bool = True) -> Optional[Tuple[int, int, str]]:
    """(inizio, fine, token) del richiamo che contiene il carattere pos."""
    for m in RE_REFERENCE.finditer(text):
        if m.start() > pos:
            break
        if pos <= m.end() and (is_transform_reference(m.group()) or not with_functions):
            return m.start(), m.end(), m.group()
    return None


def reference_point(text: str, start: int, patterns, instrument, meter=None, origin_beat: float = 0.0) -> ReferencePoint:
    """Griglia, velocity e tonalita' in vigore al carattere 'start' del testo,
    che nel brano comincia a origin_beat. Un testo non valido da' i default."""
    point = ReferencePoint(prefix=context_prefix_before(text, start), position=origin_beat)
    octave = instrument.default_octave
    try:
        probe = parse_track_text(point.prefix + "c", {}, default_octave=octave)[-1]
        point.grid, point.velocity = float(probe.duration), probe.velocity
        spans = compute_token_spans(text, patterns, default_octave=octave, meter=meter, origin_beat=origin_beat)
        point.position = origin_beat + min((span[2] for span in spans if span[0] >= start), default=0.0)
    except Exception:           # si sta scrivendo: l'anteprima resta con i default
        pass
    for cs, ce in all_token_spans(text):
        if cs >= start:
            break
        m = RE_KEY_MODE.match(text[cs:ce])
        if m:
            point.key = m.group(1)
    return point


def expansion(token: str, project: Project, point: ReferencePoint, instrument) -> Expansion:
    """Quello che suona il richiamo. Solleva NotationError come il parser."""
    patterns = tuple((name, tuple(p.tokens)) for name, p in sorted(project.patterns.items()))
    key = (token, patterns, project.time_sig, tuple(project.metrica_changes), project.pickup, project.key,
           tuple(project.key_changes), point.grid, point.velocity, point.position, point.key, instrument.name)
    if key not in _cache:
        if len(_cache) > 200:
            _cache.clear()
        _cache[key] = expand_reference(token, project.patterns, instrument.default_octave, project.meter(),
                                       point.position, point.key, point.grid, point.velocity, instrument)
    return _cache[key]


def _event_text(ev) -> str:
    if ev.kind in ("note", "slide"):
        return f"{ev.letter}*{ev.octave}"
    if ev.kind in ("chord", "harmony"):
        return ev.symbol
    if ev.kind == "block":
        return "[" + " ".join(item.get("symbol") or f"{item.get('letter')}*{item.get('octave')}"
                              for item in ev.items or ()) + "]"
    if ev.kind == "percussion":
        return str(getattr(ev, "name", "") or "x")
    return ""


def stage_lines(token: str, result: Expansion) -> List[Tuple[str, str]]:
    """La catena passo per passo: (passo, note), con il pattern di partenza
    per primo; si trova subito la funzione che produce una nota inattesa."""
    lines = []
    for step, events in result.stages:
        label = tr("Il pattern") if step is None else token[step.start:step.end]
        notes = [text for text in map(_event_text, events) if text]
        shown = " ".join(notes[:MAX_NOTES_SHOWN]) + (" …" if len(notes) > MAX_NOTES_SHOWN else "")
        lines.append((label, shown))
    return lines


def preview_project(project: Project, token: str, point: ReferencePoint, instrument_name: str,
                    synth_track=None) -> Project:
    """Un progetto usa-e-getta che suona solo il richiamo, nel suo contesto."""
    preview = Project(name="preview", tempo_bpm=project.tempo_bpm, time_sig=project.time_sig,
                      metrica_changes=list(project.metrica_changes), key=project.key,
                      key_changes=list(project.key_changes))
    preview.patterns = project.patterns
    preview.instruments = project.instruments
    copy_synth(preview.add_track("Anteprima", instrument_name, point.prefix + token), synth_track)
    return preview


# ------------------------------------------------------------------ .arpeggio sugli accordi

def arpeggiable(tok: str) -> bool:
    """Se al token si puo' dare il suffisso .arpeggio: un accordo o un blocco
    senza $arp, che insieme a .arpeggio e' un errore."""
    if "$arp" in tok:
        return False
    m = RE_ARPEGGIO_SUFFIX.match(tok)
    base = (m.group(1) if m else tok).rstrip("~")
    if base.lstrip("0123456789").startswith("["):
        return True
    return bool(RE_CHORD.match(split_note_value(base)[0]))


def with_arpeggio(tok: str, kind: str, grid: str = "") -> str:
    """Il token con il suffisso .arpeggio(tipo,griglia), al posto di quello
    che ha; '~' va dopo il suffisso."""
    m = RE_ARPEGGIO_SUFFIX.match(tok)
    base, rest = (m.group(1), m.group(3)) if m else (tok, "")
    tie = "~" if base.endswith("~") or rest.endswith("~") else ""
    return f"{base.rstrip('~')}.arpeggio({kind}{',' + grid if grid else ''}){tie}"
