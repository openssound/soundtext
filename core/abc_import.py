"""
Importazione di brani in notazione ABC (standard 2.1: .abc), come quelli
delle raccolte di musica tradizionale, di abcjs, EasyABC, abcm2ps e di
SoundText stesso (vedi st_language.abc).

Il brano viene letto in modo esatto (posizioni in frazioni di quarto) nella
stessa forma intermedia dell'import MusicXML (battute di ogni parte, vedi
core.musicxml_import), che poi passa da un MIDI temporaneo e dall'import
MIDI di sempre: voci in blocchi { ; }, testo cantato, strumenti, batteria,
dinamiche, cambi di tempo e di metrica, ritornelli e finali 1./2. svolti,
levare iniziale, sigle degli accordi nella traccia "Accordi".

Si legge il primo brano del file (X:). Ogni voce (V:) e' una parte; le voci
raggruppate sullo stesso pentagramma o con una graffa da %%score/%%staves
(es. le due mani del pianoforte), con lo stesso strumento, diventano una
traccia sola. Lo strumento viene da %%MIDI program (%%MIDI channel 10 per la
batteria, le cui note sono i suoni GM), altrimenti dal nome della voce.
Le chiavi all'ottava (treble-8), transpose= e octave= suonano all'altezza
reale. Le note di abbellimento si ignorano, come le parti (P:) e i salti.
"""

import os
import re
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Dict, List, Optional, Tuple

from .chords import parse_chord_symbol
from .i18n import tr
from .musicxml_import import (_NAME_PROGRAMS, DEFAULT_VELOCITY, MeasureData, NoteEv, PartInfo,
                              assemble_score, project_from_score)
from .notation import DYNAMICS_TO_VELOCITY


class ABCError(ValueError):
    """File ABC illeggibile o senza note: il messaggio e' gia' per l'utente."""


_STEP_SEMITONES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_TONIC_FIFTHS = {"Cb": -7, "Gb": -6, "Db": -5, "Ab": -4, "Eb": -3, "Bb": -2, "F": -1, "C": 0,
                 "G": 1, "D": 2, "A": 3, "E": 4, "B": 5, "F#": 6, "C#": 7, "G#": 8, "D#": 9,
                 "A#": 10, "E#": 11, "B#": 12, "Fb": -8}
_MODE_OFFSET = {"": 0, "maj": 0, "ion": 0, "m": -3, "min": -3, "aeo": -3, "mix": -1, "dor": -2,
                "phr": -4, "lyd": 1, "loc": -5}
_SHARP_ORDER = "FCGDAEB"
_CLEF_NAMES = ("treble", "bass", "alto", "tenor", "perc", "none")
_ACCIDENTALS = {"^^": 2, "^": 1, "=": 0, "_": -1, "__": -2}
# I campi che contano per le note (gli altri, come C: compositore o
# W: parole in fondo, non cambiano cio' che suona).
_MUSIC_FIELDS = ("T", "M", "L", "Q", "K", "V")

_RE_FIELD = re.compile(r"^([A-Za-z]):(.*)$")
_RE_NOTE = re.compile(r"(\^\^|\^|__|_|=)?([A-Ga-g])([',]*)(\d*(?:/+\d*)?)")
_RE_LENGTH = re.compile(r"\d*(?:/+\d*)?")
_RE_INLINE_FIELD = re.compile(r"\[([A-Za-z]):([^\]]*)\]")
_RE_ENDING = re.compile(r"\s*\[?([1-9][0-9,\-]*)")


def _parse_length(text: str) -> Fraction:
    """Il moltiplicatore di durata ('', '2', '3/2', '/2', '/', '//')."""
    if not text:
        return Fraction(1)
    if "/" not in text:
        return Fraction(int(text))
    num, _sep, rest = text.partition("/")
    slashes = 1 + len(rest) - len(rest.lstrip("/"))
    den_text = rest.lstrip("/")
    numerator = int(num) if num else 1
    denominator = int(den_text) if den_text else 2 ** slashes
    return Fraction(numerator, denominator)


def _parse_meter(text: str) -> Optional[Tuple[int, int]]:
    text = text.strip().split("%")[0].strip()
    if text in ("C", ""):
        return (4, 4) if text else None
    if text == "C|":
        return (2, 2)
    m = re.match(r"^\(?([\d+]+)\)?\s*/\s*(\d+)", text)
    if not m:
        return None
    num = sum(int(n) for n in m.group(1).split("+") if n)
    den = int(m.group(2))
    return (num, den) if num > 0 and den > 0 else None


def _parse_unit(text: str) -> Optional[Fraction]:
    m = re.match(r"^\s*(\d+)\s*/\s*(\d+)", text)
    if not m or int(m.group(2)) == 0:
        return None
    return Fraction(int(m.group(1)), int(m.group(2))) * 4       # in quarti


def _parse_tempo(text: str, unit: Fraction) -> Optional[float]:
    """Q: in battiti al quarto ('1/4=120', '3/8=60', '120', '"Allegro" 1/4=120')."""
    text = re.sub(r'"[^"]*"', " ", text).strip()
    if "=" in text:
        beats, _sep, bpm = text.partition("=")
        total = Fraction(0)
        for b in beats.split():
            m = re.match(r"^(\d+)/(\d+)$", b)
            if m and int(m.group(2)):
                total += Fraction(int(m.group(1)), int(m.group(2)))
        m = re.match(r"^\s*(\d+(?:\.\d+)?)", bpm)
        if not m or total == 0:
            return None
        return float(m.group(1)) * float(total * 4)
    m = re.match(r"^(\d+(?:\.\d+)?)$", text)
    return float(m.group(1)) * float(unit) if m else None


@dataclass
class _Key:
    fifths: int = 0
    minor: bool = False
    alters: Dict[str, int] = field(default_factory=lambda: {s: 0 for s in "ABCDEFG"})


def _key_from_fifths(fifths: int) -> Dict[str, int]:
    alters = {s: 0 for s in "ABCDEFG"}
    order = _SHARP_ORDER if fifths > 0 else _SHARP_ORDER[::-1]
    for step in order[:min(7, abs(fifths))]:
        alters[step] = 1 if fifths > 0 else -1
    return alters


def _parse_params(tokens: List[str]) -> Dict[str, str]:
    """Clef e trasposizione da K:/V: ('clef=bass', 'treble-8', 'transpose=-2', 'octave=1')."""
    params = {}
    for tok in tokens:
        if "=" in tok:
            k, _sep, v = tok.partition("=")
            k = {"t": "transpose", "m": "middle", "nm": "name", "snm": "subname"}.get(k.lower(), k.lower())
            params[k] = v.strip('"')
        elif re.match(r"^(" + "|".join(_CLEF_NAMES) + r")\d?([+-]8)?$", tok):
            params["clef"] = tok
    return params


def _parse_key(text: str) -> Tuple[Optional[_Key], Dict[str, str]]:
    """(tonalita', parametri) di un campo K:; tonalita' None se il campo ha
    solo parametri (es. 'K: clef=bass')."""
    tokens = text.split("%")[0].split()
    params = _parse_params(tokens)
    rest = [t for t in tokens if "=" not in t and not re.match(r"^(" + "|".join(_CLEF_NAMES) + r")", t)]
    if not rest:
        return None, params
    first = rest.pop(0)
    key = _Key()
    if first.lower() == "none":
        return key, params
    if first in ("HP", "Hp"):
        key.fifths = 0 if first == "HP" else 2
        key.alters = _key_from_fifths(key.fifths)
        if first == "Hp":
            key.alters["G"] = 0
        return key, params
    m = re.match(r"^([A-Ga-g])([#b]?)(.*)$", first)
    if not m:
        return None, params
    tonic = m.group(1).upper() + m.group(2)
    mode_text = m.group(3)
    if not mode_text and rest and re.match(r"^[A-Za-z]+$", rest[0]) and rest[0][:3].lower() in _MODE_OFFSET:
        mode_text = rest.pop(0)
    mode = mode_text.lower()
    mode = "m" if mode == "m" else mode[:3]
    offset = _MODE_OFFSET.get(mode, 0)
    fifths = _TONIC_FIFTHS.get(tonic, 0) + offset
    key.fifths = max(-7, min(7, fifths))
    key.minor = mode in ("m", "min", "aeo")
    key.alters = _key_from_fifths(key.fifths)
    explicit = [t for t in rest if re.match(r"^(\^\^|\^|__|_|=)[A-Ga-g]$", t)]
    if "exp" in rest:
        key.alters = {s: 0 for s in "ABCDEFG"}
    for t in explicit:
        key.alters[t[-1].upper()] = _ACCIDENTALS[t[:-1]]
    return key, params


def _transpose_from(params: Dict[str, str]) -> Optional[int]:
    """Semitoni fra scrittura e suono dati da clef (+8/-8), transpose= e
    octave=; None se il campo non ne parla."""
    found = False
    semis = 0
    clef = params.get("clef", "")
    if clef:
        found = True
        semis += 12 if clef.endswith("+8") else -12 if clef.endswith("-8") else 0
    for name, factor in (("transpose", 1), ("octave", 12)):
        value = params.get(name)
        if value is not None and re.match(r"^[+-]?\d+$", value):
            found = True
            semis += int(value) * factor
    return semis if found else None


def _abc_chord_symbol(text: str) -> Optional[str]:
    """Una sigla ABC ('Am7', 'G/B', 'F#m7b5', 'Bbmaj7', 'C+') in notazione
    SoundText; None per N.C. o se non si riesce a rappresentare."""
    text = text.strip()
    if not text or text.upper().replace(".", "") in ("NC", "N C"):
        return None
    m = re.match(r"^([A-G][#b♭]?)([^/]*)(?:/([A-G][#b♭]?))?", text)
    if not m:
        return None
    root, suffix, bass = m.group(1).replace("♭", "b"), m.group(2), m.group(3)
    normal = (suffix.replace("(", "").replace(")", "").replace("°", "dim").replace("ø", "m7b5")
              .replace("min", "m").replace("Maj", "maj").replace("M7", "maj7").replace("-", "m"))
    if normal.startswith("+"):
        normal = "aug" + normal[1:]
    candidates = [suffix, normal, "m" if normal.startswith("m") and not normal.startswith("maj") else ""]
    for cand in candidates:
        try:
            parse_chord_symbol(root + cand)
        except ValueError:
            continue
        return root + cand + ("/" + bass.replace("♭", "b") if bass else "")
    return None


class _Voice:
    def __init__(self, vid: str, tune: "_Tune"):
        self.vid = vid
        self.name = ""
        self.program: Optional[int] = None
        self.drums = False
        self.transpose = tune.transpose
        self.unit = tune.unit
        self.meter = tune.meter
        self.key = tune.key
        self.velocity = DEFAULT_VELOCITY
        self.measures: List[MeasureData] = []
        self.md = MeasureData(time_sig=tune.meter, key=(tune.key.fifths, "minor" if tune.key.minor else "major"))
        self.time = Fraction(0)
        self.bar_max = Fraction(0)
        self.bar_alters: Dict[object, int] = {}
        self.pending_ties: Dict[Tuple[str, int], int] = {}
        self.tuplet: Optional[List] = None          # [fattore, note rimaste]
        self.broken_next = Fraction(1)
        self.last_element: List[NoteEv] = []
        self.last_duration = Fraction(0)
        self.ending_active = False
        self.lyric_notes: List[Tuple[int, NoteEv]] = []
        self.aligned_upto = 0
        self.last_lyric_slice: Tuple[int, int] = (0, 0)
        self.verse = 1


class _Tune:
    def __init__(self):
        self.title = ""
        self.meter: Optional[Tuple[int, int]] = (4, 4)
        self.unit: Optional[Fraction] = None
        self.key = _Key()
        self.transpose = 0
        self.tempo: Optional[float] = None
        self.voices: Dict[str, _Voice] = {}
        self.voice_params: Dict[str, Dict[str, str]] = {}
        self.order: List[str] = []           # voci nell'ordine in cui compaiono
        self.declared: List[str] = []        # ...e in cui sono dichiarate in testa
        self.in_body = False
        self.groups: List[List[str]] = []
        self.propagate = "pitch"
        self.pending_program: Optional[int] = None
        self.pending_drums = False
        self.header_voice: Optional[str] = None      # ultima V: in testa (vi vanno i %%MIDI)
        self.voice_midi: Dict[str, Dict[str, object]] = {}
        self.current: Optional[_Voice] = None
        self.previous_was_lyrics = False

    # ----------------------------------------------------------------- voci

    def voice(self, vid: str) -> _Voice:
        if vid not in self.voices:
            if self.unit is None:
                self.unit = self.default_unit()
            v = _Voice(vid, self)
            params = self.voice_params.get(vid, {})
            self.apply_voice_params(v, params)
            if not self.voices:
                v.program = self.pending_program
                v.drums = self.pending_drums
            midi = self.voice_midi.get(vid, {})
            if "program" in midi:
                v.program = midi["program"]
            if midi.get("drums"):
                v.drums = True
            self.voices[vid] = v
            self.order.append(vid)
        return self.voices[vid]

    def apply_voice_params(self, v: _Voice, params: Dict[str, str]):
        if params.get("name"):
            v.name = params["name"]
        transpose = _transpose_from(params)
        if transpose is not None:
            v.transpose = transpose
        if params.get("clef", "").startswith("perc"):
            v.drums = True

    def default_unit(self) -> Fraction:
        if self.meter and Fraction(self.meter[0], self.meter[1]) < Fraction(3, 4):
            return Fraction(1, 16) * 4
        return Fraction(1, 8) * 4

    def cur(self) -> _Voice:
        if self.current is None:
            self.current = self.voice(self.order[0] if self.order else "1")
        return self.current


def _split_tunes(text: str) -> List[List[str]]:
    tunes, current = [], None
    for line in text.splitlines():
        if re.match(r"^X:", line):
            current = []
            tunes.append(current)
        if current is not None:
            current.append(line)
    if not tunes:                      # un frammento senza X: e' un brano solo
        tunes = [text.splitlines()]
    return tunes


def _parse_score_groups(text: str) -> List[List[List[str]]]:
    """I gruppi di %%score/%%staves: [strumento [pentagramma [voci]]]. Le
    voci fra ( ) stanno sullo stesso pentagramma, i pentagrammi fra { }
    sono quelli di uno strumento (le due mani del pianoforte)."""
    groups: List[List[List[str]]] = []
    brace: Optional[List[List[str]]] = None
    staff: Optional[List[str]] = None
    for tok in re.findall(r"[(){}\[\]|*]|[^\s(){}\[\]|*]+", text):
        if tok == "{":
            brace = []
        elif tok == "}":
            if brace:
                groups.append(brace)
            brace = None
        elif tok == "(":
            staff = []
        elif tok == ")":
            if staff:
                if brace is not None:
                    brace.append(staff)
                else:
                    groups.append([staff])
            staff = None
        elif tok in ("[", "]", "|", "*"):
            continue
        elif staff is not None:
            staff.append(tok)
        elif brace is not None:
            brace.append([tok])
        else:
            groups.append([[tok]])
    return groups


def _midi_directive(tune: _Tune, text: str):
    """%%MIDI program N (o program canale N) e %%MIDI channel 10 (batteria):
    per la voce corrente, per l'ultima V: dichiarata in testa, o per la
    prima voce se il brano non ne dichiara."""
    parts = text.split()
    if len(parts) < 2:
        return
    numbers = [int(p) for p in parts[1:] if p.isdigit()]
    if not numbers:
        return
    if parts[0] == "program":
        setting = ("program", max(0, min(127, numbers[-1])))
    elif parts[0] == "channel" and numbers[0] == 10:
        setting = ("drums", True)
    else:
        return
    if tune.current is not None:
        setattr(tune.current, *setting)
    elif tune.header_voice is not None:
        tune.voice_midi.setdefault(tune.header_voice, {})[setting[0]] = setting[1]
    elif setting[0] == "program":
        tune.pending_program = setting[1]
    else:
        tune.pending_drums = True


# --------------------------------------------------------------- corpo del brano

def _close_measure(v: _Voice, bar: str, ending: Optional[List[int]]):
    """Una stanghetta: chiude la battuta (se ha qualcosa) con i ritornelli."""
    v.bar_max = max(v.bar_max, v.time)
    closed = None
    if v.md.notes or v.bar_max > 0 or v.md.length > 0:
        v.md.length = max(v.md.length, v.bar_max)
        v.measures.append(v.md)
        closed = v.md
        v.md = MeasureData()
    target = closed or (v.measures[-1] if v.measures else None)
    leading = len(bar) - len(bar.lstrip(":"))
    trailing = len(bar) - len(bar.rstrip(":"))
    if bar.strip(":") == "" and len(bar) >= 2:       # '::' = fine e inizio di un ritornello
        leading = trailing = 1
    if leading and target is not None:
        target.backward_repeat = leading + 1
    stops = leading or "||" in bar or "]" in bar or "[|" in bar or ending is not None
    if v.ending_active and stops and target is not None:
        target.ending_stop = True
        v.ending_active = False
    if trailing:
        v.md.forward_repeat = True
    if ending is not None:
        v.md.endings = ending
        v.ending_active = True
    v.time = Fraction(0)
    v.bar_max = Fraction(0)
    v.bar_alters = {}


def _parse_endings(text: str) -> List[int]:
    numbers = []
    for part in text.split(","):
        if "-" in part:
            a, _sep, b = part.partition("-")
            if a.isdigit() and b.isdigit():
                numbers += list(range(int(a), int(b) + 1))
        elif part.isdigit():
            numbers.append(int(part))
    return numbers or [1]


def _add_element(v: _Voice, notes: List[Tuple[int, Fraction, bool, bool]], base: Fraction):
    """Una nota, un accordo o una pausa (notes vuota) di durata base
    (tuplet e ritmo puntato applicati qui)."""
    factor = v.broken_next
    v.broken_next = Fraction(1)
    if v.tuplet:
        factor *= v.tuplet[0]
        v.tuplet[1] -= 1
        if v.tuplet[1] <= 0:
            v.tuplet = None
    duration = base * factor
    events = []
    for midi, length, tie, tie_stop in notes:
        ev = NoteEv(start=v.time, duration=length * factor, midi=midi, velocity=v.velocity,
                    tie_start=tie, tie_stop=tie_stop, staff=v.vid)
        v.md.notes.append(ev)
        events.append(ev)
    if events:
        v.lyric_notes.append((len(v.measures), events[0]))
    v.last_element = events
    v.last_duration = duration
    v.time += duration
    v.bar_max = max(v.bar_max, v.time)


def _broken(v: _Voice, symbol: str):
    """'>' / '<' (anche ripetuti) fra due elementi: il primo si allunga,
    il secondo si accorcia, o viceversa."""
    n = len(symbol)
    short = Fraction(1, 2 ** n)
    long = 2 - short
    first, second = (long, short) if symbol[0] == ">" else (short, long)
    delta = v.last_duration * (first - 1)
    for ev in v.last_element:
        ev.duration *= first
    v.time += delta
    v.bar_max = max(v.bar_max, v.time)
    v.broken_next = second


def _note_pitch(v: _Voice, tune: _Tune, accidental: Optional[str], letter: str, marks: str) -> int:
    step = letter.upper()
    octave = (5 if letter.islower() else 4) + marks.count("'") - marks.count(",")
    key = step if tune.propagate == "pitch" else (step, octave)
    if accidental is not None:
        alter = _ACCIDENTALS[accidental]
        if tune.propagate != "not":
            v.bar_alters[key] = alter
    elif (step, octave) in v.pending_ties:
        return v.pending_ties[(step, octave)]
    else:
        alter = v.bar_alters.get(key, v.key.alters[step])
    midi = 12 * (octave + 1) + _STEP_SEMITONES[step] + alter
    if not v.drums:
        midi += v.transpose
    return max(0, min(127, midi))


def _apply_field(tune: _Tune, name: str, value: str, inline: bool = False):
    """Un campo (in testa al brano, su una riga a se' o [X:...] nel corpo)."""
    v = tune.current
    if name == "T" and not tune.title:
        tune.title = value.strip()
    elif name == "M":
        meter = _parse_meter(value)
        if v is None:
            tune.meter = meter
        else:
            v.meter = meter
            if meter:
                v.md.time_sig = meter
    elif name == "L":
        unit = _parse_unit(value)
        if unit:
            if v is None:
                tune.unit = unit
            else:
                v.unit = unit
    elif name == "Q":
        unit = (v.unit if v else tune.unit) or tune.default_unit()
        bpm = _parse_tempo(value, unit)
        if bpm:
            if v is None:
                tune.tempo = bpm
            else:
                v.md.tempos.append((v.time, bpm))
    elif name == "K":
        key, params = _parse_key(value)
        target = v if v is not None else None
        if target is None:
            if key is not None:
                tune.key = key
            transpose = _transpose_from(params)
            if transpose is not None:
                tune.transpose = transpose
        else:
            if key is not None:
                target.key = key
                target.md.key = (key.fifths, "minor" if key.minor else "major")
            tune.apply_voice_params(target, params)
    elif name == "V":
        tokens = value.split("%")[0].split()
        if not tokens:
            return
        vid = tokens[0]
        params = _parse_params(re.findall(r'\S+="[^"]*"|\S+', value[value.find(vid) + len(vid):]))
        tune.voice_params.setdefault(vid, {}).update(params)
        if vid not in tune.declared:
            tune.declared.append(vid)
        if not tune.in_body and not inline:
            tune.header_voice = vid
        if vid in tune.voices:
            tune.apply_voice_params(tune.voices[vid], params)
        if tune.in_body or inline:
            tune.current = tune.voice(vid)


def _parse_music(tune: _Tune, line: str):
    v = tune.cur()
    i, n = 0, len(line)
    while i < n:
        c = line[i]
        if c in " \t`$":
            i += 1
        elif c == "%":
            break
        elif c == "\\" and i == n - 1:
            break
        elif c == '"':
            j = line.find('"', i + 1)
            j = n if j < 0 else j
            text = line[i + 1:j]
            if text and text[0] not in "^_<>@":
                symbol = _abc_chord_symbol(text)
                v.md.harmonies.append((v.time, symbol))
            i = j + 1
        elif c in "!+":
            j = line.find(c, i + 1)
            if j < 0:
                i += 1
                continue
            deco = line[i + 1:j]
            if deco in DYNAMICS_TO_VELOCITY:
                v.velocity = DYNAMICS_TO_VELOCITY[deco]
            i = j + 1
        elif c == "{":
            j = line.find("}", i)
            i = n if j < 0 else j + 1
        elif c == "[" and _RE_INLINE_FIELD.match(line, i):
            m = _RE_INLINE_FIELD.match(line, i)
            _apply_field(tune, m.group(1), m.group(2), inline=True)
            v = tune.cur()
            i = m.end()
        elif c == "[" and i + 1 < n and line[i + 1].isdigit():
            m = _RE_ENDING.match(line, i)
            _close_measure(v, "", _parse_endings(m.group(1)))
            i = m.end()
        elif c in "|:" or (c == "[" and i + 1 < n and line[i + 1] == "|"):
            j = i
            while j < n and (line[j] in "|:]" or (line[j] == "[" and j + 1 < n and line[j + 1] == "|")):
                j += 1
            bar = line[i:j]
            ending = None
            m = re.match(r"([1-9][0-9,\-]*)", line[j:]) if "|" in bar else None
            if m:
                ending = _parse_endings(m.group(1))
                j += m.end()
            elif j < n and line[j] == "[" and j + 1 < n and line[j + 1].isdigit():
                m = _RE_ENDING.match(line, j)
                ending = _parse_endings(m.group(1))
                j = m.end()
            _close_measure(v, bar, ending)
            i = j
        elif c == "&":
            v.time = Fraction(0)          # sovrapposizione di voce: si torna a inizio battuta
            i += 1
        elif c == "(":
            m = re.match(r"\((\d)(?::(\d*))?(?::(\d*))?", line[i:])
            if m:
                p = int(m.group(1))
                compound = bool(v.meter and v.meter[1] == 8 and v.meter[0] % 3 == 0 and v.meter[0] > 3)
                default_q = {2: 3, 3: 2, 4: 3, 6: 2, 8: 3}.get(p, 3 if compound else 2)
                q = int(m.group(2)) if m.group(2) else default_q
                r = int(m.group(3)) if m.group(3) else p
                v.tuplet = [Fraction(q, p), r]
                i += m.end()
            else:
                i += 1
        elif c in "<>":
            j = i
            while j < n and line[j] == c:
                j += 1
            _broken(v, line[i:j])
            i = j
        elif c in "zxZX":
            m = _RE_LENGTH.match(line, i + 1)
            if c in "ZX":
                bars = int(m.group(0)) if m.group(0).isdigit() else 1
                nominal = Fraction(4 * v.meter[0], v.meter[1]) if v.meter else Fraction(4)
                for _ in range(bars - 1):
                    v.time = nominal
                    _close_measure(v, "|", None)
                v.time = nominal
                v.bar_max = nominal
            else:
                _add_element(v, [], v.unit * _parse_length(m.group(0)))
            i = m.end()
        elif c == "[":
            j = line.find("]", i)
            if j < 0:
                i += 1
                continue
            inner = line[i + 1:j]
            m_len = _RE_LENGTH.match(line, j + 1)
            outer = _parse_length(m_len.group(0))
            k = m_len.end()
            tie_all = k < n and line[k] == "-"
            if tie_all:
                k += 1
            notes = []
            first_length = None
            for nm in re.finditer(r"(\^\^|\^|__|_|=)?([A-Ga-g])([',]*)(\d*(?:/+\d*)?)(-?)", inner):
                length = v.unit * _parse_length(nm.group(4)) * outer
                if first_length is None:
                    first_length = length
                notes.append(_note_from(v, tune, nm, length, tie_all or bool(nm.group(5))))
            if notes:
                _add_element(v, notes, first_length)
            i = k
        elif c in "^_=" or c.upper() in _STEP_SEMITONES:
            m = _RE_NOTE.match(line, i)
            if not m:
                i += 1
                continue
            k = m.end()
            tie = k < n and line[k] == "-"
            if tie:
                k += 1
            length = v.unit * _parse_length(m.group(4))
            _add_element(v, [_note_from(v, tune, m, length, tie)], length)
            i = k
        else:
            i += 1          # decorazioni brevi (~ . H T u v...), legature di portamento ), y


def _note_from(v: _Voice, tune: _Tune, m, length: Fraction, tie: bool):
    accidental, letter, marks = m.group(1), m.group(2), m.group(3)
    step = letter.upper()
    octave = (5 if letter.islower() else 4) + marks.count("'") - marks.count(",")
    tie_stop = accidental is None and (step, octave) in v.pending_ties
    midi = _note_pitch(v, tune, accidental, letter, marks)
    v.pending_ties.pop((step, octave), None)
    if tie:
        v.pending_ties[(step, octave)] = midi
    return midi, length, tie, tie_stop


def _lyrics(tune: _Tune, text: str):
    """Una riga w: sulle note della voce corrente dopo la riga w: precedente."""
    v = tune.cur()
    if tune.previous_was_lyrics:
        v.verse += 1
        start, end = v.last_lyric_slice
    else:
        v.verse = 1
        start, end = v.aligned_upto, len(v.lyric_notes)
        v.last_lyric_slice = (start, end)
        v.aligned_upto = end
    notes = v.lyric_notes[start:end]
    tokens: List[Tuple[str, str]] = []          # (tipo, sillaba)
    syllable = ""
    i = 0
    while i < len(text):
        c = text[i]
        if c == "\\" and i + 1 < len(text) and text[i + 1] == "-":
            syllable += "-"
            i += 2
            continue
        if c in " \t":
            if syllable:
                tokens.append(("syl", syllable))
                syllable = ""
        elif c == "-":
            if syllable:
                tokens.append(("syl", syllable + "-"))
                syllable = ""
        elif c in "_*":
            if syllable:
                tokens.append(("syl", syllable))
                syllable = ""
            tokens.append(("skip", ""))
        elif c == "|":
            if syllable:
                tokens.append(("syl", syllable))
                syllable = ""
            tokens.append(("bar", ""))
        elif c == "~":
            syllable += " "
        else:
            syllable += c
        i += 1
    if syllable:
        tokens.append(("syl", syllable))
    k = 0
    for kind, syl in tokens:
        if kind == "bar":
            # alla battuta dopo quella dell'ultima nota con una sillaba
            if 0 < k < len(notes):
                bar = notes[k - 1][0]
                while k < len(notes) and notes[k][0] == bar:
                    k += 1
            continue
        if k >= len(notes):
            break
        if kind == "syl":
            notes[k][1].lyrics[str(v.verse)] = syl.strip()
        k += 1


def parse_abc(text: str):
    """Il primo brano ABC del testo come partitura (core.musicxml_import.ScoreData)."""
    lines = _split_tunes(text)[0]
    tune = _Tune()
    for raw in lines:
        line = raw.rstrip("\r\n")
        if line.startswith("%%"):
            directive = line[2:].strip()
            if directive.startswith("MIDI "):
                _midi_directive(tune, directive[5:])
            elif directive.startswith(("score", "staves")):
                tune.groups = _parse_score_groups(directive.split(None, 1)[1] if " " in directive else "")
            elif directive.startswith("propagate-accidentals"):
                parts = directive.split()
                if len(parts) > 1 and parts[1] in ("not", "octave", "pitch"):
                    tune.propagate = parts[1]
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith("%"):
            continue
        field_m = _RE_FIELD.match(stripped)
        if field_m:
            name, value = field_m.group(1), field_m.group(2)
            if name == "w":
                if tune.in_body:
                    _lyrics(tune, value.strip())
                    tune.previous_was_lyrics = True
                continue
            tune.previous_was_lyrics = False
            if name in _MUSIC_FIELDS:
                _apply_field(tune, name, value.split("%")[0])
                if name == "K":
                    tune.in_body = True
            continue
        if not tune.in_body:
            continue
        tune.previous_was_lyrics = False
        _parse_music(tune, line)

    for v in tune.voices.values():
        if v.md.notes or max(v.bar_max, v.time) > 0:
            _close_measure(v, "|]", None)
        elif v.ending_active and v.measures:
            v.measures[-1].ending_stop = True
    order = [vid for vid in tune.declared if vid in tune.voices] + \
        [vid for vid in tune.order if vid not in tune.declared]
    voices = [tune.voices[vid] for vid in order if tune.voices[vid].measures]
    if not voices or not any(md.notes for v in voices for md in v.measures):
        raise ABCError(tr("Il file ABC non contiene note."))
    if tune.tempo and voices[0].measures:
        voices[0].measures[0].tempos.insert(0, (Fraction(0), tune.tempo))

    parts, parsed = _merge_voices(tune, voices)
    return assemble_score(tune.title, parts, parsed)


def _program_for(v: _Voice) -> Tuple[Optional[int], bool]:
    if v.drums:
        return None, True
    if v.program is not None:
        return v.program, False
    lower = v.name.lower()
    for words, program in _NAME_PROGRAMS:
        if any(w in lower for w in words):
            return program, program is None
    return None, False


def _merge_voices(tune: _Tune, voices: List[_Voice]):
    """Le parti: le voci dello stesso pentagramma di %%score diventano una
    (lo strumento e' quello della prima, se le altre non ne dichiarano
    uno); i pentagrammi di una graffa anche, se sono di pianoforte o organo
    (come li scrive l'export). Le altre voci restano parti separate."""
    from .instruments import gm_family_for_program

    by_id = {v.vid: v for v in voices}
    owner: Dict[str, str] = {}
    for brace in tune.groups:
        heads = []
        for staff in brace:
            present = [vid for vid in staff if vid in by_id]
            if not present:
                continue
            head = by_id[present[0]]
            for vid in present[1:]:
                other = by_id[vid]
                if _program_for(other) == (None, False):
                    other.program, other.drums = _program_for(head)
                if _program_for(other) == _program_for(head):
                    owner[vid] = head.vid
            heads.append(head)
        if len(heads) > 1:
            program, drums = _program_for(heads[0])
            keyboard = not drums and (program is None or gm_family_for_program(program) in ("Pianoforti", "Organi"))
            for head in heads[1:]:
                if keyboard and _program_for(head) in ((program, drums), (None, False)):
                    for vid, own in list(owner.items()):
                        if own == head.vid:
                            owner[vid] = heads[0].vid
                    owner[head.vid] = heads[0].vid
    parts: List[PartInfo] = []
    parsed: Dict[str, List[MeasureData]] = {}
    for v in voices:
        head = owner.get(v.vid, v.vid)
        if head != v.vid and head in parsed:
            base = parsed[head]
            for i, md in enumerate(v.measures):
                if i < len(base):
                    base[i].notes.extend(md.notes)
                    base[i].harmonies.extend(md.harmonies)
                    base[i].tempos.extend(md.tempos)
                    base[i].length = max(base[i].length, md.length)
                else:
                    base.append(md)
            continue
        program, drums = _program_for(v)
        parts.append(PartInfo(pid=v.vid, name=v.name, program=program, is_drums=drums))
        parsed[v.vid] = v.measures
    return parts, parsed


def import_abc_file(path: str, project_name: Optional[str] = None,
                    recognize_chords: bool = False, min_bend_semitones: float = None):
    """Il progetto (core.model.Project) del primo brano del file ABC in path."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except UnicodeDecodeError:
        with open(path, encoding="latin-1") as f:
            text = f.read()
    except OSError as e:
        raise ABCError(tr("Impossibile leggere il file ABC '{0}': {e}", os.path.basename(path), e=e)) from e
    score = parse_abc(text)
    return project_from_score(score, path, project_name, recognize_chords, min_bend_semitones)
