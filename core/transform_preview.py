"""
Che cosa suona un richiamo di pattern con funzioni (%Tema.invert(e*5).retro)
nel punto del testo in cui e' scritto: lo usano l'anteprima delle note e la
finestra Trasforma (gui.transform_preview, gui.transform_dialog). I calcoli
sono di st_language.transform.expand_reference, a cui qui si danno la griglia,
la velocity e la tonalita' di quel punto; il risultato si ricorda per richiamo
e testo del progetto. Qui stanno anche il suffisso .arpeggio degli accordi e
Congela la trasformazione, che scrive per esteso le note di un richiamo.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from st_language import events_to_text
from st_language.midi import resolve_event_notes
from st_language.transform import Expansion, expand_reference, is_transform_reference

from .i18n import tr
from .model import Project, copy_synth
from .notation import (NotationError, RE_ARP, RE_ARPEGGIO_SUFFIX, RE_CHORD, RE_KEY_MODE, all_token_spans,
                       compute_token_spans, context_prefix_before, find_references, parse_track_text,
                       pattern_state_effect, split_note_value, tokenize)

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
    for reference in pattern_references(text):
        if reference.start > pos:
            break
        if pos <= reference.end and (is_transform_reference(reference.token) or not with_functions):
            return reference.start, reference.end, reference.token
    return None


def pattern_references(text: str) -> list:
    """I richiami di pattern del testo, anche dentro gruppi e voci."""
    return [reference for reference in find_references(text) if reference.kind == "pattern"]


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
           tuple(project.key_changes), point.prefix, point.position, point.key, instrument.name)
    if key not in _cache:
        if len(_cache) > 200:
            _cache.clear()
        _cache[key] = expand_reference(token, project.patterns, instrument.default_octave, project.meter(),
                                       point.position, point.key, point.grid, point.velocity, instrument,
                                       prefix=point.prefix)
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


# ------------------------------------------------------------------ Congela la trasformazione

_STATE_DEFAULTS = {"grid": "4:", "velocity": "80@", "swing": "swing=50", "shift": "shift=0", "arp": "arp=off"}


def sounding(text: str, patterns, instrument, meter=None, origin_beat: float = 0.0, midi_dir=None) -> list:
    """Quello che si sente di un testo con lo strumento della traccia: si
    confronta prima e dopo una riscrittura che non deve cambiare il suono."""
    events = parse_track_text(text, patterns, default_octave=instrument.default_octave, midi_dir=midi_dir,
                              meter=meter, origin_beat=origin_beat, instrument=instrument)
    sound = []
    for ev in events:
        moment = (round(ev.start, 6), round(ev.duration, 6))
        if ev.kind in ("note", "chord", "block", "percussion", "slide"):
            notes = tuple(resolve_event_notes(ev, instrument)[0])
            sound.append((moment, ev.kind, ev.velocity, notes, ev.swing, ev.shift, ev.articulation))
        elif ev.kind == "control":
            sound.append((moment, ev.kind, ev.name, ev.value))
        elif ev.kind == "tempo_marker":
            sound.append((moment, ev.kind, ev.bpm))
    return sorted(sound, key=repr)


def preview_notation(token: str, project: Project, point: ReferencePoint, instrument) -> str:
    """Il richiamo in notazione ST, per l'anteprima."""
    return events_to_text(expansion(token, project, point, instrument).events, instrument.default_octave,
                          key=point.key, grid=point.grid, velocity=point.velocity)


def _restored_state(written: str, prefix: str) -> str:
    """I comandi che rimettono lo stato cambiato dal testo scritto."""
    changed = pattern_state_effect(tokenize(written), {})[1]
    before = pattern_state_effect(tokenize(prefix), {})[1]
    return " ".join(before.get(slot, _STATE_DEFAULTS[slot]) for slot in changed
                    if before.get(slot, _STATE_DEFAULTS[slot]) != changed[slot])


def arp_region(text: str, pos: int) -> Optional[Tuple[int, int]]:
    """Il tratto fra arp=tipo e il comando che lo chiude, se pos ci sta dentro."""
    opened = None
    last_end = 0
    for cs, ce in all_token_spans(text):
        if RE_ARP.match(text[cs:ce]):
            closing = text[cs:ce].lower().startswith("arp=off")
            if opened is not None and opened <= pos <= ce and closing:
                return opened, ce
            if opened is not None and opened <= pos < cs:
                return opened, last_end
            opened = None if closing else cs
        last_end = ce
    return (opened, last_end) if opened is not None and pos >= opened else None


def freeze_span(text: str, start: int, end: int, project: Project, instrument, origin_beat: float = 0.0,
                comment: bool = True) -> str:
    """Il testo con [start, end) (un richiamo con funzioni, un accordo con
    .arpeggio, un tratto arp=) scritto per esteso nota per nota, e lo stato
    di prima rimesso dopo. Il suono resta identico: se non puo' solleva
    NotationError e il testo non cambia."""
    meter = project.meter()
    point = reference_point(text, start, project.patterns, instrument, meter, origin_beat)
    head = (f"key={point.key} " if point.key else "") + point.prefix
    events = parse_track_text(head + text[start:end], project.patterns, default_octave=instrument.default_octave,
                              meter=meter, origin_beat=point.position, instrument=instrument)
    written = events_to_text(events, instrument.default_octave, key=point.key, grid=point.grid,
                             velocity=point.velocity)
    after = text[end:]
    restore = _restored_state(written, point.prefix) if after.strip() else ""
    body = written + (" " + restore if restore else "")
    expected = sounding(text, project.patterns, instrument, meter, origin_beat)
    before = text[:start]
    lead = "" if not before.rstrip(" \t") or before.rstrip(" \t").endswith("\n") else "\n"
    note = lead + "// " + tr("da {source}", source=" ".join(text[start:end].split())) + "\n"
    for candidate in ([before + note + body + after] if comment else []) + [before + body + after]:
        try:
            if sounding(candidate, project.patterns, instrument, meter, origin_beat) == expected:
                return candidate
        except NotationError:
            continue
    raise NotationError(tr("Queste note non si possono scrivere per esteso senza cambiare il suono"), text[start:end])


def freeze_all(text: str, project: Project, instrument, origin_beat: float = 0.0,
               comment: bool = True) -> Tuple[str, int, List[str]]:
    """Tutti i richiami con funzioni del testo: (testo, quanti, quelli rimasti)."""
    done, kept = 0, []
    for reference in reversed(pattern_references(text)):
        if not is_transform_reference(reference.token):
            continue
        try:
            text = freeze_span(text, reference.start, reference.end, project, instrument, origin_beat, comment)
            done += 1
        except NotationError:
            kept.append(reference.token)
    return text, done, kept
