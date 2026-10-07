"""
Importazione di partiture MusicXML (.musicxml, .xml, .mxl compresso), come
le esportano MuseScore, Finale, Sibelius, Dorico e SoundText stesso (vedi
core.musicxml_export).

La partitura viene letta in modo esatto (posizioni in frazioni di quarto)
e trasformata in un file MIDI temporaneo, che passa poi dall'importazione
MIDI di sempre (core.midi_import): voci in blocchi { ; }, testo cantato, strumenti
riconosciuti dal programma General MIDI, batteria, dinamiche, cambi di
tempo e di metrica. In piu', rispetto a un MIDI:
  - le tracce prendono il nome delle parti ("Flauto", "Violino I"...) e
    il progetto quello del brano (work-title);
  - gli strumenti traspositori (sax, clarinetto, chitarra scritta
    all'ottava) suonano all'altezza reale (<transpose>);
  - i ritornelli e i finali 1./2. vengono svolti nell'ordine in cui si
    suonano;
  - una battuta in levare iniziale viene completata con una pausa, cosi'
    le stanghette restano al loro posto;
  - le sigle degli accordi (<harmony>) diventano una traccia "Accordi",
    udibile in un lead sheet (melodia + sigle), muta se la partitura ha
    gia' altre parti che suonano l'armonia.

Non si svolgono D.C., D.S. e Coda (si legge la partitura una volta, con i
soli ritornelli); le note di abbellimento (acciaccature) si ignorano.
"""

import os
import re
import tempfile
import zipfile
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

from .chords import parse_chord_symbol
from .import_lyrics import midi_text_bytes
from .notation import DYNAMICS_TO_VELOCITY
from .i18n import tr

TICKS_PER_QUARTER = 960
DEFAULT_TEMPO = 120.0
DEFAULT_VELOCITY = 80
DRUM_CHANNEL = 9
CHORDS_TRACK_NAME = "Accordi"
CHORDS_INSTRUMENT = "Piano"
_MAX_UNROLLED = 20                 # limite di sicurezza: misure svolte <= 20 x quelle scritte

_STEP_SEMITONES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_MAJOR_KEYS = ["Cb", "Gb", "Db", "Ab", "Eb", "Bb", "F", "C", "G", "D", "A", "E", "B", "F#", "C#"]
_MINOR_KEYS = ["Abm", "Ebm", "Bbm", "Fm", "Cm", "Gm", "Dm", "Am", "Em", "Bm", "F#m", "C#m", "G#m", "D#m", "A#m"]

# Valori di <kind> -> suffisso delle sigle di SoundText (core.chords); le
# qualita' che SoundText non ha diventano la piu' vicina.
_KIND_SUFFIX = {
    "major": "", "minor": "m", "augmented": "aug", "diminished": "dim",
    "dominant": "7", "major-seventh": "maj7", "minor-seventh": "m7",
    "diminished-seventh": "dim7", "augmented-seventh": "aug", "half-diminished": "m7b5",
    "major-minor": "mMaj7", "major-sixth": "6", "minor-sixth": "m6",
    "dominant-ninth": "9", "major-ninth": "maj9", "minor-ninth": "m9",
    "dominant-11th": "11", "major-11th": "maj9", "minor-11th": "m9",
    "dominant-13th": "13", "major-13th": "maj13", "minor-13th": "m9",
    "suspended-second": "sus2", "suspended-fourth": "sus4", "power": "5",
}

# Parti senza programma MIDI: strumento dal nome della parte (in varie lingue).
_NAME_PROGRAMS = [
    (("drum", "batteria", "batterie", "bateria", "percuss"), None),
    (("piano", "pianoforte"), 0), (("organ", "organo", "orgue", "órgano"), 19),
    (("bass", "basso", "basse", "bajo"), 33), (("guitar", "chitarra", "guitare", "guitarra"), 24),
    (("violin", "violino", "violon", "violín"), 40), (("viola", "alto vl"), 41),
    (("cello", "violoncell", "violonchelo"), 42), (("contrab", "double bass"), 43),
    (("flute", "flauto", "flûte", "flauta"), 73), (("clarinet", "clarinett", "clarinette"), 71),
    (("oboe", "hautbois"), 68), (("bassoon", "fagott", "basson", "fagot"), 70),
    (("sax",), 65), (("trumpet", "tromba", "trompette", "trompeta"), 56),
    (("trombone", "trombón"), 57), (("horn", "corno", "cor", "trompa"), 60),
    (("tuba",), 58), (("harp", "arpa", "harpe"), 46),
    (("voice", "voce", "voix", "voz", "soprano", "alto", "tenor", "bariton", "choir", "coro", "chœur"), 52),
]


class MusicXMLError(ValueError):
    pass


# --------------------------------------------------------------- lettura

def _strip_namespace(root):
    for el in root.iter():
        if isinstance(el.tag, str) and "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    return root


def read_musicxml_root(path: str):
    """L'elemento radice della partitura (anche dentro un .mxl)."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            target = None
            if "META-INF/container.xml" in names:
                container = _strip_namespace(ET.fromstring(z.read("META-INF/container.xml")))
                rootfile = container.find(".//rootfile")
                if rootfile is not None:
                    target = rootfile.get("full-path")
            if target is None:
                target = next((n for n in names if n.lower().endswith((".musicxml", ".xml"))
                               and not n.startswith("META-INF/")), None)
            if target is None or target not in names:
                raise MusicXMLError(tr("Il file .mxl non contiene una partitura MusicXML."))
            data = z.read(target)
    else:
        with open(path, "rb") as f:
            data = f.read()
    try:
        root = _strip_namespace(ET.fromstring(data))
    except ET.ParseError as e:
        raise MusicXMLError(tr("Il file non è un MusicXML valido: {e}", e=e))
    if root.tag == "score-timewise":
        root = _timewise_to_partwise(root)
    if root.tag != "score-partwise":
        raise MusicXMLError(tr("Il file non è una partitura MusicXML."))
    return root


def _timewise_to_partwise(root):
    out = ET.Element("score-partwise")
    for child in root:
        if child.tag != "measure":
            out.append(child)
    parts: Dict[str, ET.Element] = {}
    for measure in root.findall("measure"):
        for part in measure.findall("part"):
            pid = part.get("id")
            if pid not in parts:
                parts[pid] = ET.SubElement(out, "part", id=pid)
            m = ET.SubElement(parts[pid], "measure", dict(measure.attrib))
            m.extend(list(part))
    return out


def _text(el, path, default=None):
    found = el.find(path) if el is not None else None
    return found.text.strip() if found is not None and found.text and found.text.strip() else default


def _int(el, path, default=None):
    value = _text(el, path)
    try:
        return int(float(value)) if value is not None else default
    except ValueError:
        return default


def _float(value, default=None):
    try:
        return float(value) if value is not None else default
    except ValueError:
        return default


# --------------------------------------------------------------- struttura

@dataclass
class PartInfo:
    pid: str
    name: str
    program: Optional[int] = None          # 0-127
    is_drums: bool = False
    unpitched: Dict[str, int] = field(default_factory=dict)   # id strumento -> nota MIDI
    volume: Optional[int] = None           # 0-127
    pan: Optional[int] = None              # 0-127


@dataclass
class NoteEv:
    start: Fraction                        # quarti dall'inizio della battuta
    duration: Fraction
    midi: int
    velocity: int
    tie_start: bool
    tie_stop: bool
    staff: str
    lyrics: Dict[str, str] = field(default_factory=dict)   # strofa -> sillaba ("Ma-" se continua)


@dataclass
class MeasureData:
    length: Fraction = Fraction(0)
    notes: List[NoteEv] = field(default_factory=list)
    harmonies: List[Tuple[Fraction, Optional[str]]] = field(default_factory=list)   # None = N.C.
    tempos: List[Tuple[Fraction, float]] = field(default_factory=list)
    time_sig: Optional[Tuple[int, int]] = None
    key: Optional[Tuple[int, str]] = None
    implicit: bool = False
    forward_repeat: bool = False
    backward_repeat: int = 0               # volte totali (0 = nessun ritornello)
    endings: Optional[List[int]] = None    # un finale (1., 2.) comincia qui
    ending_stop: bool = False              # ...e finisce qui
    # salti: D.C. / D.S. a fine battuta, segno, Fine, "al Coda" e Coda
    segno: bool = False
    coda: bool = False
    to_coda: bool = False
    fine: bool = False
    da_capo: bool = False
    dal_segno: bool = False


def _part_infos(root) -> Dict[str, PartInfo]:
    infos = {}
    for sp in root.findall("part-list/score-part"):
        pid = sp.get("id")
        name = _text(sp, "part-name") or _text(sp, "part-abbreviation") or pid
        info = PartInfo(pid=pid, name=name)
        for mi in sp.findall("midi-instrument"):
            program = _int(mi, "midi-program")
            if program is not None and info.program is None:
                info.program = max(0, min(127, program - 1))
            if _int(mi, "midi-channel") == 10:
                info.is_drums = True
            unpitched = _int(mi, "midi-unpitched")
            if unpitched is not None:
                info.unpitched[mi.get("id")] = max(0, min(127, unpitched - 1))
                info.is_drums = True
            volume = _float(_text(mi, "volume"))
            if volume is not None and info.volume is None:
                info.volume = max(0, min(127, round(volume / 100 * 127)))
            pan = _float(_text(mi, "pan"))
            if pan is not None and info.pan is None:
                info.pan = max(0, min(127, round((pan + 90) / 180 * 127)))
        if info.program is None and not info.is_drums:
            lower = name.lower()
            for words, program in _NAME_PROGRAMS:
                if any(w in lower for w in words):
                    if program is None:
                        info.is_drums = True
                    else:
                        info.program = program
                    break
        infos[pid] = info
    return infos


def _harmony_symbol(h) -> Optional[str]:
    """La sigla in notazione SoundText ('Am7', 'C/E'), None per N.C. o se
    non si riesce a rappresentare."""
    kind_el = h.find("kind")
    kind = kind_el.text.strip() if kind_el is not None and kind_el.text else "major"
    if kind == "none":
        return None
    step = _text(h, "root/root-step")
    if not step:
        return None
    alter = _int(h, "root/root-alter", 0)
    root = step.upper() + ("#" * alter if alter > 0 else "b" * -alter)
    text = kind_el.get("text") if kind_el is not None else None
    base = suffix = _KIND_SUFFIX.get(kind, "")
    degrees = [(_int(d, "degree-value"), _int(d, "degree-alter", 0), _text(d, "degree-type"))
               for d in h.findall("degree")]
    if kind == "dominant" and (9, -1, "add") in degrees or (9, -1, "alter") in degrees:
        suffix = "7b9"
    elif kind == "dominant" and ((9, 1, "add") in degrees or (9, 1, "alter") in degrees):
        suffix = "7#9"
    elif kind == "major" and (9, 0, "add") in degrees:
        suffix = "add9"
    elif kind == "suspended-fourth" and (7, 0, "add") in degrees:
        suffix = "7sus4"
    # le alterazioni scritte come <degree> valgono piu' del testo mostrato
    # (che spesso le omette o le scrive in forme come "7(b9)")
    candidates = [suffix] if suffix != base else []
    if text is not None:
        candidates.append(text.strip())
    candidates.append(base)
    symbol = None
    for cand in candidates:
        try:
            parse_chord_symbol(root + cand)
            symbol = root + cand
            break
        except ValueError:
            continue
    if symbol is None:
        return None
    bass_step = _text(h, "bass/bass-step")
    if bass_step:
        bass_alter = _int(h, "bass/bass-alter", 0)
        symbol += "/" + bass_step.upper() + ("#" * bass_alter if bass_alter > 0 else "b" * -bass_alter)
    return symbol


_RE_DA_CAPO = re.compile(r"^\s*(d\.?\s*c\.?(\s|$|al)|da\s+capo)", re.I)
_RE_DAL_SEGNO = re.compile(r"^\s*(d\.?\s*s\.?(\s|$|al)|dal\s+segno)", re.I)
_RE_FINE = re.compile(r"^\s*fine\.?\s*$", re.I)
_RE_TO_CODA = re.compile(r"^\s*(to|al|alla|à\s+la|a\s+la)\s+coda", re.I)


def _read_jumps(sound, md: MeasureData):
    """Gli attributi di <sound> che dicono come si suona la partitura."""
    if sound.get("dacapo") == "yes":
        md.da_capo = True
    if sound.get("dalsegno"):
        md.dal_segno = True
    if sound.get("segno"):
        md.segno = True
    if sound.get("fine"):
        md.fine = True
    if sound.get("tocoda"):
        md.to_coda = True
    if sound.get("coda"):
        md.coda = True


def _read_jump_marks(direction, md: MeasureData):
    """Gli stessi salti scritti solo come testo o simbolo (non tutti i
    programmi scrivono anche gli attributi di <sound>)."""
    for words in direction.findall("direction-type/words"):
        text = (words.text or "").strip()
        if _RE_DA_CAPO.match(text):
            md.da_capo = True
        elif _RE_DAL_SEGNO.match(text):
            md.dal_segno = True
        elif _RE_TO_CODA.match(text):
            md.to_coda = True
        elif _RE_FINE.match(text):
            md.fine = True
    if direction.find("direction-type/segno") is not None:
        md.segno = True
    if direction.find("direction-type/coda") is not None and not md.to_coda:
        md.coda = True


def _lyrics(note) -> Dict[str, str]:
    """Le sillabe di una nota, per strofa: 'Ma-' se la parola continua
    (syllabic begin/middle); le elisioni (due sillabe sulla stessa nota)
    unite con '‿'."""
    out = {}
    for n, lyric in enumerate(note.findall("lyric"), 1):
        texts = [(t.text or "").strip() for t in lyric.findall("text")]
        text = "‿".join(t for t in texts if t)
        if not text:
            continue
        syllabic = [(s.text or "").strip() for s in lyric.findall("syllabic")]
        if syllabic and syllabic[-1] in ("begin", "middle"):
            text += "-"
        out.setdefault(lyric.get("number") or str(n), text)
    return out


def _parse_part(part, info: PartInfo) -> List[MeasureData]:
    measures = []
    divisions = 1
    transpose = 0
    velocity = DEFAULT_VELOCITY
    for m in part.findall("measure"):
        md = MeasureData(implicit=m.get("implicit") == "yes")
        cursor = 0                          # in divisioni
        last_start = 0
        max_cursor = 0
        for el in m:
            tag = el.tag
            if tag == "attributes":
                divisions = _int(el, "divisions", divisions) or divisions
                if el.find("time") is not None:
                    beats, beat_type = _text(el, "time/beats"), _int(el, "time/beat-type")
                    try:
                        num = sum(int(b) for b in beats.split("+")) if beats else None
                    except ValueError:
                        num = None
                    if num and beat_type:
                        md.time_sig = (num, beat_type)
                if el.find("key/fifths") is not None:
                    md.key = (_int(el, "key/fifths", 0), _text(el, "key/mode", "major"))
                if el.find("transpose") is not None:
                    transpose = _int(el, "transpose/chromatic", 0) + 12 * _int(el, "transpose/octave-change", 0)
            elif tag == "backup":
                cursor = max(0, cursor - (_int(el, "duration", 0) or 0))
            elif tag == "forward":
                cursor += _int(el, "duration", 0) or 0
                max_cursor = max(max_cursor, cursor)
            elif tag == "direction":
                offset = _int(el, "offset", 0) or 0
                at = Fraction(cursor + offset, divisions)
                for dyn in el.findall("direction-type/dynamics"):
                    for mark in dyn:
                        if mark.tag in DYNAMICS_TO_VELOCITY:
                            velocity = DYNAMICS_TO_VELOCITY[mark.tag]
                tempo = _float(el.find("sound").get("tempo")) if el.find("sound") is not None else None
                if tempo is None:
                    metro = el.find("direction-type/metronome")
                    per_minute = _float(_text(metro, "per-minute")) if metro is not None else None
                    if per_minute:
                        unit = {"whole": 4, "half": 2, "quarter": 1, "eighth": 0.5, "16th": 0.25}.get(
                            _text(metro, "beat-unit", "quarter"), 1)
                        if metro.find("beat-unit-dot") is not None:
                            unit *= 1.5
                        tempo = per_minute * unit
                if tempo:
                    md.tempos.append((at, tempo))
                sound = el.find("sound")
                if sound is not None:
                    _read_jumps(sound, md)
                _read_jump_marks(el, md)
                if sound is not None and sound.get("dynamics"):
                    velocity = max(1, min(127, round(_float(sound.get("dynamics"), 100) * 0.9)))
            elif tag == "sound":
                if el.get("tempo"):
                    md.tempos.append((Fraction(cursor, divisions), _float(el.get("tempo"), DEFAULT_TEMPO)))
                _read_jumps(el, md)
            elif tag == "harmony":
                offset = _int(el, "offset", 0) or 0
                md.harmonies.append((Fraction(cursor + offset, divisions), _harmony_symbol(el)))
            elif tag == "barline":
                if el.find("segno") is not None:
                    md.segno = True
                if el.find("coda") is not None:
                    md.coda = True
                repeat = el.find("repeat")
                if repeat is not None:
                    if repeat.get("direction") == "forward":
                        md.forward_repeat = True
                    elif repeat.get("direction") == "backward":
                        md.backward_repeat = max(2, int(_float(repeat.get("times"), 2)))
                ending = el.find("ending")
                if ending is not None and ending.get("type") in ("stop", "discontinue"):
                    md.ending_stop = True
                if ending is not None and ending.get("type") == "start":
                    numbers = []
                    for chunk in (ending.get("number") or "").replace(" ", "").split(","):
                        if "-" in chunk:
                            a, _, b = chunk.partition("-")
                            if a.isdigit() and b.isdigit():
                                numbers.extend(range(int(a), int(b) + 1))
                        elif chunk.isdigit():
                            numbers.append(int(chunk))
                    md.endings = numbers or [1]
            elif tag == "note":
                duration = _int(el, "duration", 0) or 0
                if el.find("grace") is not None or el.find("cue") is not None:
                    continue
                if el.find("chord") is not None:
                    start = last_start
                else:
                    start = cursor
                    cursor += duration
                    last_start = start
                max_cursor = max(max_cursor, start + duration)
                if el.find("rest") is not None or duration <= 0:
                    continue
                midi = None
                if el.find("pitch") is not None:
                    step = _text(el, "pitch/step", "C")
                    octave = _int(el, "pitch/octave", 4)
                    alter = round(_float(_text(el, "pitch/alter"), 0))
                    midi = 12 * (octave + 1) + _STEP_SEMITONES.get(step.upper(), 0) + alter + transpose
                elif el.find("unpitched") is not None:
                    inst = el.find("instrument")
                    midi = info.unpitched.get(inst.get("id")) if inst is not None else None
                    if midi is None:
                        midi = next(iter(info.unpitched.values()), 38)
                if midi is None or not 0 <= midi <= 127:
                    continue
                note_velocity = velocity
                if el.get("dynamics"):
                    note_velocity = max(1, min(127, round(_float(el.get("dynamics"), 100) * 0.9)))
                ties = {t.get("type") for t in el.findall("tie")} | {t.get("type") for t in el.findall("notations/tied")}
                md.notes.append(NoteEv(Fraction(start, divisions), Fraction(duration, divisions), midi,
                                       note_velocity, "start" in ties, "stop" in ties,
                                       _text(el, "staff", "1"), _lyrics(el)))
        md.length = Fraction(max(max_cursor, cursor), divisions)
        measures.append(md)
    return measures


def _play_order(measures: List[MeasureData]) -> List[int]:
    """Indici delle battute nell'ordine in cui si suonano: ritornelli e
    finali 1./2. svolti, poi D.C./D.S. (una volta ciascuno) fino a Fine o
    con il salto alla Coda. Dopo un D.C./D.S. i ritornelli non si
    ripetono e dei finali si suona l'ultimo, come d'uso."""
    order: List[int] = []
    n = len(measures)
    i, section_start, pass_no = 0, 0, 1
    repeats_done: Dict[int, int] = {}
    ending: Optional[List[int]] = None      # numeri del finale in corso
    ending_is_last = False
    jumped = False                           # arrivati qui tornando indietro
    after_jump = False                       # dopo un D.C./D.S.
    jumps_taken = set()
    limit = max(1, n) * _MAX_UNROLLED

    def more_endings_follow(j):
        return j + 1 < n and measures[j + 1].endings is not None

    def ending_region_end(j):
        while j < n - 1 and not (measures[j].ending_stop or measures[j].backward_repeat):
            if j > 0 and measures[j + 1].endings is not None:
                break
            j += 1
        return j

    while i < n and len(order) < limit:
        m = measures[i]
        if m.forward_repeat and not jumped:
            section_start, pass_no = i, 1
        jumped = False
        if m.endings is not None:
            ending = m.endings
            ending_is_last = not more_endings_follow(ending_region_end(i))
        if ending is None:
            play = True
        elif after_jump:
            play = ending_is_last
        else:
            play = pass_no in ending
        if play:
            order.append(i)
        if play and m.backward_repeat and not after_jump:
            done = repeats_done.get(i, 1)
            if done < m.backward_repeat:
                repeats_done[i] = done + 1
                pass_no = done + 1
                i, jumped, ending = section_start, True, None
                continue
            repeats_done.pop(i, None)
            section_start = i + 1
            if not more_endings_follow(i):
                pass_no = 1
        if ending is not None and (m.ending_stop or m.backward_repeat):
            ending = None
            if play and not m.backward_repeat and not more_endings_follow(i):
                pass_no = 1                  # ultimo finale suonato: il ritornello e' chiuso
        if play:
            if after_jump and m.fine:
                break
            if after_jump and m.to_coda:
                target = next((j for j in range(i + 1, n) if measures[j].coda), None)
                if target is not None:
                    i, ending = target, None
                    continue
            if (m.da_capo or m.dal_segno) and i not in jumps_taken:
                jumps_taken.add(i)
                if m.da_capo:
                    target = 0
                else:
                    segni = [j for j in range(n) if measures[j].segno]
                    before = [j for j in segni if j <= i]
                    target = before[-1] if before else (segni[0] if segni else 0)
                after_jump, ending, pass_no = True, None, 1
                i, jumped = target, True
                continue
        i += 1
    return order


# --------------------------------------------------------------- partitura -> MIDI

@dataclass
class ScoreData:
    title: str
    parts: List[PartInfo]
    notes: Dict[str, List[Tuple[Fraction, Fraction, int, int]]]      # pid -> (inizio, fine, nota, velocity)
    harmonies: List[Tuple[Fraction, Optional[str]]]
    tempos: List[Tuple[Fraction, float]]
    time_sigs: List[Tuple[Fraction, int, int]]
    key: Optional[str]
    end: Fraction
    lyrics: Dict[str, List[Tuple[Fraction, str]]] = field(default_factory=dict)   # pid -> (inizio, sillaba)


def parse_score(path: str) -> ScoreData:
    root = read_musicxml_root(path)
    infos = _part_infos(root)
    parts_xml = root.findall("part")
    if not parts_xml:
        raise MusicXMLError(tr("La partitura non contiene parti."))
    parsed: Dict[str, List[MeasureData]] = {}
    for part in parts_xml:
        pid = part.get("id")
        info = infos.setdefault(pid, PartInfo(pid=pid, name=pid))
        parsed[pid] = _parse_part(part, info)
    title = (_text(root, "work/work-title") or _text(root, "movement-title") or "").strip()
    return assemble_score(title, [infos[p.get("id")] for p in parts_xml], parsed)


def assemble_score(title: str, parts: List[PartInfo], parsed: Dict[str, List[MeasureData]]) -> ScoreData:
    """La partitura in tempo assoluto dalle battute lette di ogni parte
    (la prima dichiara metrica, ritornelli e salti): usata anche
    dall'import ABC (core.abc_import)."""
    infos = {p.pid: p for p in parts}
    first = parsed[parts[0].pid]
    n = max(len(ms) for ms in parsed.values())
    # metrica di ogni battuta (dalla prima parte, che la dichiara)
    sigs, current = [], (4, 4)
    for i in range(n):
        if i < len(first) and first[i].time_sig:
            current = first[i].time_sig
        sigs.append(current)
    # durata di ogni battuta: quella della metrica se almeno una parte la
    # riempie esattamente (una parte che "sborda", es. due pause intere in
    # un 4/4, e' un errore di scrittura); altrimenti la piu' lunga (battuta
    # irregolare voluta, o tutta in levare)
    lengths = []
    for i in range(n):
        nominal = Fraction(4 * sigs[i][0], sigs[i][1])
        written = [ms[i].length for ms in parsed.values() if i < len(ms) and ms[i].length > 0]
        if not written:
            lengths.append(nominal)
        elif nominal in written:
            lengths.append(nominal)
        else:
            lengths.append(max(written))
    order = _play_order(first + [MeasureData() for _ in range(n - len(first))])

    # levare: la prima battuta incompleta si allunga in testa con una pausa
    nominal0 = Fraction(4 * sigs[0][0], sigs[0][1]) if n else Fraction(0)
    pickup = nominal0 - lengths[0] if n and lengths[0] < nominal0 else Fraction(0)

    starts: List[Tuple[int, Fraction]] = []
    t = Fraction(0)
    for k, i in enumerate(order):
        offset = pickup if k == 0 else Fraction(0)
        starts.append((i, t + offset))
        t += lengths[i] + offset
    end = t

    notes: Dict[str, list] = {}
    lyrics: Dict[str, list] = {}
    harmonies: Dict[Fraction, Optional[str]] = {}
    tempos: Dict[Fraction, float] = {}
    for pid, measures in parsed.items():
        open_ties: Dict[Tuple[int, str], list] = {}
        out = []
        part_lyrics = []
        visits: Dict[int, int] = {}
        for i, m_start in starts:
            if i >= len(measures):
                continue
            md = measures[i]
            # a ogni ripetizione della battuta la strofa successiva, se c'e'
            visits[i] = visits.get(i, 0) + 1
            verse = str(visits[i])
            for ev in sorted(md.notes, key=lambda e: e.start):
                if ev.lyrics and not ev.tie_stop:
                    part_lyrics.append((m_start + ev.start,
                                        ev.lyrics.get(verse) or ev.lyrics.get("1") or next(iter(ev.lyrics.values()))))
                start, stop = m_start + ev.start, m_start + ev.start + ev.duration
                key = (ev.midi, ev.staff)
                tied = open_ties.get(key)
                # una legatura aperta assorbe la nota uguale che comincia dove
                # finisce, anche se questa non dichiara la fine della legatura
                # (file scritti in modo approssimativo, ma il senso e' quello)
                if tied is not None and abs(tied[1] - start) <= Fraction(1, TICKS_PER_QUARTER):
                    tied[1] = max(tied[1], stop)
                    if not ev.tie_start:
                        open_ties.pop(key, None)
                    continue
                note = [start, stop, ev.midi, ev.velocity]
                out.append(note)
                if ev.tie_start:
                    open_ties[key] = note
                else:
                    open_ties.pop(key, None)
            for at, symbol in md.harmonies:
                harmonies.setdefault(m_start + at, symbol)
            for at, bpm in md.tempos:
                # il tempo scritto in testa alla battuta in levare vale dall'inizio
                abs_at = Fraction(0) if (i, m_start) == starts[0] and at == 0 else m_start + at
                tempos.setdefault(abs_at, bpm)
        notes[pid] = [tuple(n) for n in out]
        lyrics[pid] = sorted(dict(part_lyrics).items())

    time_sigs, last = [], None
    for k, (i, m_start) in enumerate(starts):
        sig = sigs[i]
        if sig != last:
            time_sigs.append((Fraction(0) if k == 0 else m_start, sig[0], sig[1]))
            last = sig
    key = None
    for pid in parsed:
        if infos[pid].is_drums:
            continue
        found = next((md.key for md in parsed[pid] if md.key), None)
        if found:
            fifths, mode = found
            fifths = max(-7, min(7, fifths))
            key = (_MINOR_KEYS if (mode or "").lower() == "minor" else _MAJOR_KEYS)[fifths + 7]
            break
    return ScoreData(
        title=title, parts=list(parts), notes=notes,
        harmonies=sorted(harmonies.items(), key=lambda kv: kv[0]),
        tempos=sorted(tempos.items(), key=lambda kv: kv[0]), time_sigs=time_sigs, key=key, end=end,
        lyrics=lyrics)


def _assign_channels(parts: List[PartInfo], notes) -> Dict[str, int]:
    """Un canale MIDI per parte (la batteria sul 10); oltre 15 parti
    melodiche, le parti con lo stesso strumento condividono un canale."""
    channels: Dict[str, int] = {}
    free = [c for c in range(16) if c != DRUM_CHANNEL]
    by_program: Dict[Optional[int], int] = {}
    for p in parts:
        if not notes.get(p.pid):
            continue
        if p.is_drums:
            channels[p.pid] = DRUM_CHANNEL
        elif free:
            channels[p.pid] = free.pop(0)
            by_program.setdefault(p.program, channels[p.pid])
        else:
            channels[p.pid] = by_program.get(p.program, list(by_program.values())[len(channels) % len(by_program)])
    return channels


def write_midi(score: ScoreData, path: str) -> Dict[int, str]:
    """Scrive la partitura come MIDI e ritorna canale -> nome della parte."""
    import mido

    def tick(t: Fraction) -> int:
        return int(round(t * TICKS_PER_QUARTER))

    mid = mido.MidiFile(type=1, ticks_per_beat=TICKS_PER_QUARTER)
    events = []
    tempos = list(score.tempos)
    if not tempos or tempos[0][0] > 0:
        tempos.insert(0, (Fraction(0), DEFAULT_TEMPO))
    for at, bpm in tempos:
        events.append((tick(at), 0, mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm), time=0)))
    for at, num, den in score.time_sigs:
        events.append((tick(at), 1, mido.MetaMessage("time_signature", numerator=num, denominator=den, time=0)))
    if score.key:
        events.append((0, 2, mido.MetaMessage("key_signature", key=score.key, time=0)))
    events.append((tick(score.end), 3, mido.MetaMessage("end_of_track", time=0)))
    mid.tracks.append(_to_track(events, end_marker=True))

    channels = _assign_channels(score.parts, score.notes)
    names: Dict[int, str] = {}
    for p in score.parts:
        ch = channels.get(p.pid)
        if ch is None:
            continue
        names.setdefault(ch, p.name)
        events = []
        if ch != DRUM_CHANNEL:
            events.append((0, 0, mido.Message("program_change", channel=ch, program=p.program or 0, time=0)))
        if p.volume is not None:
            events.append((0, 1, mido.Message("control_change", channel=ch, control=7, value=p.volume, time=0)))
        if p.pan is not None:
            events.append((0, 1, mido.Message("control_change", channel=ch, control=10, value=p.pan, time=0)))
        for at, syllable in score.lyrics.get(p.pid, []):
            # convenzione letta da core.import_lyrics.syllables: 'Ma-' continua, 'a ' chiude la parola
            text = syllable if syllable.endswith("-") else syllable + " "
            events.append((tick(at), 1, mido.MetaMessage("lyrics", text=midi_text_bytes(text), time=0)))
        # Una nota che riattacca mentre la stessa altezza suona ancora (due
        # voci all'unisono, un accordo tenuto sotto una melodia) chiude la
        # precedente: nel MIDI la seconda accensione la farebbe sparire.
        spans = sorted((tick(start), tick(stop), note, velocity)
                       for start, stop, note, velocity in score.notes[p.pid])
        sounding: Dict[int, list] = {}
        notes = []
        for a, b, note, velocity in spans:
            previous = sounding.get(note)
            if previous is not None and previous[1] > a:
                previous[1] = a
            current = [a, b, note, velocity]
            notes.append(current)
            sounding[note] = current
        for a, b, note, velocity in notes:
            if b <= a:
                continue
            events.append((b, 2, mido.Message("note_off", channel=ch, note=note, velocity=0, time=0)))
            events.append((a, 3, mido.Message("note_on", channel=ch, note=note, velocity=velocity, time=0)))
        mid.tracks.append(_to_track(events))
    mid.save(path)
    return names


def _to_track(events, end_marker=False):
    import mido
    track = mido.MidiTrack()
    now = 0
    for at, _order, msg in sorted(events, key=lambda e: (e[0], e[1])):
        if msg.type == "end_of_track":
            continue
        track.append(msg.copy(time=at - now))
        now = at
    if end_marker:
        end = max((e[0] for e in events), default=0)
        track.append(mido.MetaMessage("end_of_track", time=max(0, end - now)))
    return track


# --------------------------------------------------------------- progetto

def _chords_text(harmonies, end: Fraction) -> str:
    """Testo della traccia delle sigle: ogni sigla dura fino alla successiva
    (N.C. = pausa), sulla griglia piu' larga che le contiene tutte."""
    times = [t for t, _ in harmonies] + [end]
    grid = 16
    for g in (1, 2, 4, 8, 16):
        if all((t * g / 4).denominator == 1 for t in times):
            grid = g
            break
    unit = Fraction(4, grid)
    tokens = [f"{grid}:"]
    first = harmonies[0][0]
    if first > 0:
        tokens.append(f"{max(1, round(first / unit))}r")
    for (t, symbol), nxt in zip(harmonies, [h[0] for h in harmonies[1:]] + [end]):
        units = max(1, round((nxt - t) / unit))
        tokens.append(f"{units}{symbol}" if symbol else f"{units}r")
    return " ".join(tokens)


def import_musicxml_file(path: str, project_name: Optional[str] = None,
                         recognize_chords: bool = False, min_bend_semitones: float = None):
    """Il progetto (core.model.Project) della partitura in path."""
    score = parse_score(path)
    if not any(score.notes.values()) and not any(s for _t, s in score.harmonies):
        raise MusicXMLError(tr("La partitura non contiene note."))
    return project_from_score(score, path, project_name, recognize_chords, min_bend_semitones)


def project_from_score(score: ScoreData, path: str, project_name: Optional[str] = None,
                       recognize_chords: bool = False, min_bend_semitones: float = None):
    """Il progetto di una partitura gia' letta (MusicXML o ABC): passa da un
    MIDI temporaneo e dall'import MIDI, poi aggiunge la traccia delle sigle."""
    from .midi_import import import_midi_file
    from .notation import validate_track_text

    name = score.title or project_name or os.path.splitext(os.path.basename(path))[0]
    fd, tmp = tempfile.mkstemp(suffix=".mid", prefix="soundtext_musicxml_")
    os.close(fd)
    try:
        channel_names = write_midi(score, tmp)
        project = import_midi_file(tmp, project_name=name, recognize_chords=recognize_chords,
                                   min_bend_semitones=min_bend_semitones, channel_names=channel_names)
    finally:
        os.remove(tmp)
    project.name = name

    chords = [(t, s) for t, s in score.harmonies]
    while chords and chords[0][1] is None:
        chords.pop(0)
    if chords:
        text = _chords_text(chords, score.end)
        ok, _error = validate_track_text(text, project.patterns)
        if not ok:
            text = ""
        if text:
            had_notes = any(t.text.strip() for t in project.tracks)
            if not had_notes:
                project.tracks = []
            names = {t.name for t in project.tracks}
            track_name = CHORDS_TRACK_NAME
            n = 2
            while track_name in names:
                track_name = f"{CHORDS_TRACK_NAME} {n}"
                n += 1
            track = project.add_track(track_name, CHORDS_INSTRUMENT, text)
            pitched_parts = [p for p in score.parts if not p.is_drums and score.notes.get(p.pid)]
            # lead sheet (una melodia e le sigle): gli accordi si sentono;
            # con altre parti che suonano gia' l'armonia restano muti
            track.mute = len(pitched_parts) > 1
    return project
