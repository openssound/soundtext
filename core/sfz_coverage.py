"""
Note che uno strumento SFZ non suona: una traccia suonata dal motore SFZ
interno (Track.synth "sfz:...") resta muta sulle note che nessuna regione
del file copre (fuori dai suoi tasti, o a una dinamica senza campioni).
Con il SoundFont General MIDI si sentono tutte, con un .sfz no: i timpani
di VSCO 2 CE, per esempio, vanno solo dal Do2 al Do4 (MIDI 36-60).

sfz_regions() legge i tasti e le dinamiche delle regioni (con #define,
#include, la gerarchia <global>/<master>/<group>/<region> e note_offset e
octave_offset di <control>); silent_notes() li confronta con le note della
traccia. Il risultato e' prudente: nel dubbio una nota si considera suonata.
"""

import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .i18n import tr

# (tasto piu' basso, piu' alto, dinamica piu' bassa, piu' alta) di una regione
Region = Tuple[int, int, int, int]

_HEADER = re.compile(r"<(\w+)>")
_OPCODE = re.compile(r"(\w+)=")
_NOTE_NAME = re.compile(r"^([a-gA-G])([#b]?)(-?\d+)$")
_SEMITONES = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}
_LEVELS = {"global": 0, "master": 1, "group": 2, "region": 3}
# solo gli opcode che decidono se un tasto suona
_KEYS = ("key", "lokey", "hikey", "lovel", "hivel", "trigger", "pitch_keycenter")

_cache: Dict[str, Tuple[float, Optional[List[Region]]]] = {}


def _note_value(text: str) -> Optional[int]:
    """Un numero MIDI o un nome di nota alla sfizz (c4 = 60, c#4, db4)."""
    text = text.strip()
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    m = _NOTE_NAME.match(text)
    if not m:
        return None
    value = _SEMITONES[m.group(1).lower()] + {"#": 1, "b": -1}.get(m.group(2), 0)
    return value + (int(m.group(3)) + 1) * 12


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def _expand(path: str, defines: Dict[str, str], depth: int = 0) -> str:
    """Il testo del file con #include espansi e #define applicati."""
    if depth > 10:
        return ""
    with open(path, encoding="utf-8", errors="replace") as f:
        text = _strip_comments(f.read())
    out = []
    base = os.path.dirname(path)
    for line in text.splitlines():
        stripped = line.strip()
        m = re.match(r'#define\s+(\$\w+)\s+(.*)$', stripped)
        if m:
            defines[m.group(1)] = m.group(2).strip()
            continue
        for name in sorted(defines, key=len, reverse=True):
            line = line.replace(name, defines[name])
        m = re.match(r'\s*#include\s+"([^"]+)"', line)
        if m:
            included = os.path.join(base, m.group(1).replace("\\", "/"))
            if os.path.isfile(included):
                out.append(_expand(included, defines, depth + 1))
            continue
        out.append(line)
    return "\n".join(out)


def _parse(text: str) -> List[Region]:
    regions: List[Region] = []
    levels: List[Dict[str, str]] = [{}, {}, {}, {}]     # global, master, group, region
    current: Optional[int] = None
    offset = 0                                          # note_offset + 12 * octave_offset
    in_control = False

    def close_region():
        if current != 3:
            return
        values: Dict[str, str] = {}
        for level in levels:
            values.update(level)
        if values.get("trigger", "attack") in ("release", "release_key"):
            return                                      # suonano al rilascio, non all'attacco
        lo, hi = _note_value(values.get("lokey", "0")), _note_value(values.get("hikey", "127"))
        if "key" in values:
            lo = hi = _note_value(values["key"])
        lovel, hivel = _note_value(values.get("lovel", "0")), _note_value(values.get("hivel", "127"))
        if None in (lo, hi, lovel, hivel) or hi < 0 or lo > 127:
            return
        regions.append((lo - offset, hi - offset, max(1, lovel), hivel))

    pos = 0
    for m in _HEADER.finditer(text + "<end>"):
        body = text[pos:m.start()]
        pos = m.end()
        opcodes = {}
        starts = list(_OPCODE.finditer(body))
        for i, op in enumerate(starts):
            end = starts[i + 1].start() if i + 1 < len(starts) else len(body)
            opcodes[op.group(1)] = body[op.end():end].strip().split()[0] if body[op.end():end].strip() else ""
        if in_control:
            note = _note_value(opcodes.get("note_offset", "0")) or 0
            octave = _note_value(opcodes.get("octave_offset", "0")) or 0
            offset = note + 12 * octave
        elif current is not None:
            levels[current].update({k: v for k, v in opcodes.items() if k in _KEYS})
        close_region()
        header = m.group(1)
        in_control = header == "control"
        current = _LEVELS.get(header)
        if current is not None:
            for deeper in range(current, 4):            # un'intestazione nuova azzera quelle sotto
                levels[deeper] = {}
    return regions


def sfz_regions(path: str) -> Optional[List[Region]]:
    """Tasti e dinamiche delle regioni del .sfz, None se non si legge."""
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return None
    cached = _cache.get(path)
    if cached is not None and cached[0] == mtime:
        return cached[1]
    try:
        regions = _parse(_expand(path, {}))
    except (OSError, ValueError, RecursionError):
        regions = None
    _cache[path] = (mtime, regions)
    return regions


def sounds(regions: List[Region], note: int, velocity: int) -> bool:
    return any(lo <= note <= hi and lovel <= velocity <= hivel for lo, hi, lovel, hivel in regions)


def track_notes(project, track) -> List[Tuple[int, int]]:
    """(nota MIDI, dinamica) di ogni nota che la traccia suona, come le
    calcola l'export MIDI (accordi con il loro voicing, slide dalla nota di
    partenza), senza tempi ne' controlli."""
    from st_language.midi import _resolve_event_notes, decorated_velocity, sounding_events
    from .chords import pitch_to_midi
    instrument = track.instrument
    out = []
    for ev in sounding_events(track.parsed_events(project.patterns, meter=project.meter())):
        if ev.kind in ("control", "sustain", "tempo_marker"):
            continue
        if ev.kind == "slide":
            out.append((pitch_to_midi(ev.letter, ev.octave), max(1, min(127, ev.velocity))))
            continue
        notes, velocity = _resolve_event_notes(ev, instrument)
        velocity = max(1, min(127, decorated_velocity(ev, velocity)))
        out += [(n, velocity) for n in notes if 0 <= n <= 127]
    return out


@dataclass
class SilentNotes:
    file_name: str
    silent: int               # quante note restano mute
    total: int                # su quante
    low: int                  # la piu' bassa e la piu' alta fra le mute (MIDI)
    high: int
    covered_low: int          # i tasti che il file suona (MIDI)
    covered_high: int

    def message(self) -> str:
        from .chords import midi_to_token
        span = midi_to_token(self.low) if self.low == self.high else \
            f"{midi_to_token(self.low)}–{midi_to_token(self.high)}"
        values = dict(silent=self.silent, total=self.total, span=span, file=self.file_name,
                      low=midi_to_token(self.covered_low), high=midi_to_token(self.covered_high))
        if self.silent == 1:
            return tr("1 nota su {total} resta muta ({span}): «{file}» suona solo da {low} a {high}", **values)
        return tr("{silent} note su {total} restano mute ({span}): «{file}» suona solo da {low} a {high}", **values)


def sfz_path(track) -> str:
    """Il file .sfz che suona la traccia, '' se non e' il motore SFZ interno."""
    if track.is_audio or not track.synth or not track.synth.startswith("sfz:") or track.frozen:
        return ""
    from .plugin_worker import parse_ref
    return parse_ref(track.synth)[1]


_track_cache: Dict[tuple, Optional[SilentNotes]] = {}


def silent_notes_cached(project, track) -> Optional[SilentNotes]:
    """Come silent_notes, ricordando il risultato finche' non cambiano il
    testo della traccia, il suo strumento, i pattern o il file .sfz: lo
    chiedono le testate a ogni aggiornamento e l'editor a ogni tasto."""
    path = sfz_path(track)
    if not path:
        return None
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return None
    patterns = tuple((name, " ".join(map(str, pattern.tokens))) for name, pattern in sorted(project.patterns.items()))
    key = (track.text, track.synth, track.instrument_name, path, mtime, hash(patterns), project.time_sig,
           tuple(project.metrica_changes), project.pickup)
    if key not in _track_cache:
        if len(_track_cache) > 200:
            _track_cache.clear()
        _track_cache[key] = silent_notes(project, track)
    return _track_cache[key]


def silent_notes(project, track) -> Optional[SilentNotes]:
    """Le note della traccia che il suo .sfz non suona, None se le suona
    tutte (o la traccia non usa il motore SFZ interno, o il file non si legge)."""
    path = sfz_path(track)
    regions = sfz_regions(path) if path else None
    if not regions:
        return None
    try:
        notes = track_notes(project, track)
    except Exception:                                   # testo con errori: lo dice gia' l'editor
        return None
    mute = [n for n, v in notes if not sounds(regions, n, v)]
    if not mute:
        return None
    return SilentNotes(os.path.basename(path), len(mute), len(notes), min(mute), max(mute),
                       max(0, min(lo for lo, _h, _l, _v in regions)),
                       min(127, max(hi for _l, hi, _lv, _hv in regions)))
