"""
Motore del prototipo SoundText Mobile (fase 0): gira in Pyodide, nel Web
Worker della PWA (mobile/app/worker.js), e anche in Python normale per le
misure di confronto e i test (python mobile/engine.py esempio.st).

Riusa i moduli di core/ senza Qt: legge il brano con
core.project_io.parse_project_text, lo esporta in MIDI con
core.midi_export.export_project_to_midi (lo stesso file che suona
SoundText) e calcola con compute_token_spans di st-language la mappa
eventi -> token del testo, come l'evidenziazione di SoundText
(gui.play_highlight), ma sul testo intero del file .st: i box e le
tracce puntano ai pattern, e dentro un riferimento %Nome si scende nel
corpo del pattern, cosi' si vede la nota che suona e non solo il box.
"""

import io
import math
import re
import time
from typing import Dict, Iterable, List, Optional, Tuple

# I moduli di core/ usati dall'app: tests/test_mobile_engine.py controlla
# che nessuno importi PySide6, nemmeno indirettamente.
ENGINE_MODULES = (
    "core.project_io",
    "core.midi_export",
    "core.notation",
    "core.model",
    "core.instruments",
    "core.syntax",
    "core.completion",
    "core.musicxml_export",
    "core.rhythm_generate",
    "core.performance_style",
    "core.dictation",
    "core.generate_labels",
)

RE_PATTERN_HDR = re.compile(r"^Pattern\s+%([\w.\-]+)\s*:\s*$")
RE_BOX_HDR = re.compile(r'^Box\s+(.+?)\s+"[^"]*"\s*\|\s*([0-9.]+)\s*:\s*$')
RE_PATTERN_REF = re.compile(r"^%([\w\-]+)$")
MAX_DEPTH = 8


def _blank_comments(body: str) -> str:
    """Il corpo con i commenti // sostituiti da spazi: stesse posizioni dei
    caratteri, nessun token in piu'."""
    return re.sub(r"//[^\n]*", lambda m: " " * len(m.group(0)), body)


def file_blocks(text: str) -> List[dict]:
    """I blocchi del file con il corpo indentato: intestazione (riga non
    indentata che finisce con ':') e posizione del corpo nel testo."""
    blocks = []
    pos = 0
    current = None
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if line[:1] not in (" ", "\t") and stripped and not stripped.startswith("//"):
            current = None
            if stripped.endswith(":"):
                current = {"header": stripped, "hstart": pos, "start": pos + len(line), "end": pos + len(line)}
                blocks.append(current)
        elif current is not None and stripped:
            current["end"] = pos + len(line.rstrip("\r\n"))
        pos += len(line)
    return blocks


class Engine:
    def __init__(self):
        self.project = None
        self.text = ""
        self.timings: Dict[str, float] = {}

    # ------------------------------------------------------------ lettura

    def load(self, text: str, name: str = "Brano") -> dict:
        from core.project_io import parse_project_text
        t0 = time.perf_counter()
        self.project = parse_project_text(text, name)
        self._midi = None
        self._length = None
        self.text = text
        self.timings = {"parse_s": time.perf_counter() - t0}
        tracks = [{"name": t.name, "instrument": t.instrument_name,
                   "percussion": bool(t.instrument.is_percussion)}
                  for t in self.project.tracks if not t.is_audio]
        return {"name": name, "tracks": tracks, "bpm": self.project.tempo_bpm}

    # ------------------------------------------------------------ MIDI

    def _base_midi(self) -> bytes:
        """Il MIDI del brano com'e' scritto. L'esportazione si fa una volta
        sola per brano."""
        if getattr(self, "_midi", None) is None:
            from core.midi_export import export_project_to_midi
            t0 = time.perf_counter()
            # un file temporaneo del sistema (/tmp non esiste su Windows)
            import os
            import tempfile
            fd, path = tempfile.mkstemp(suffix=".mid")
            os.close(fd)
            try:
                export_project_to_midi(self.project, path)
                with open(path, "rb") as f:
                    self._midi = f.read()
            finally:
                os.remove(path)
            self.timings["midi_s"] = time.perf_counter() - t0
        return self._midi

    def midi_bytes(self, transpose: int = 0, muted: Iterable[str] = (), metronome: bool = False) -> bytes:
        """Il brano in MIDI, come lo suona il lettore dell'app.

        'transpose': le note non percussive si spostano di tanti semitoni.
        La trasposizione si fa sulle note del MIDI e non con transpose=N
        davanti al testo delle tracce: i box degli esempi cominciano con
        reset: e hanno un loro transpose= (es. il sax di jazz_aaba.st,
        un'ottava sotto), che annullerebbero quello aggiunto. Le percussioni
        stanno sempre sul canale 10 (st_language.midi._assign_channels) e
        non si toccano.

        'muted': i nomi delle tracce da non sentire (mute, o le altre quando
        una e' in solo): le loro note spariscono, il resto della traccia
        (strumento, controlli) resta, cosi' riattivarla a meta' suona giusto.

        'metronome': un click sul canale 10 a ogni battito, piu' forte
        sul primo della battuta (con la metrica del brano)."""
        base = self._base_midi()
        muted = set(muted)
        if not transpose and not muted and not metronome:
            return base
        import mido
        from st_language.instruments import DRUM_MIDI_CHANNEL
        t0 = time.perf_counter()
        mid = mido.MidiFile(file=io.BytesIO(base))
        for track in mid.tracks:
            silent = track.name in muted
            kept = []
            carry = 0
            for msg in track:
                if msg.type in ("note_on", "note_off", "polytouch"):
                    if silent:
                        carry += msg.time
                        continue
                    if transpose and msg.channel != DRUM_MIDI_CHANNEL:
                        msg = msg.copy(note=min(127, max(0, msg.note + int(transpose))))
                if carry:
                    msg = msg.copy(time=msg.time + carry)
                    carry = 0
                kept.append(msg)
            track[:] = kept
        if metronome:
            mid.tracks.append(self._metronome_track(mid))
        out = io.BytesIO()
        mid.save(file=out)
        self.timings["render_s"] = time.perf_counter() - t0
        return out.getvalue()

    def _metronome_track(self, mid):
        import mido
        from st_language.instruments import DRUM_MIDI_CHANNEL
        tpb = mid.ticks_per_beat
        end = self.length_beats()
        bars = set(self.bar_list())
        track = mido.MidiTrack([mido.MetaMessage("track_name", name="Metronomo", time=0)])
        clicks = sorted({float(b) for b in range(int(math.ceil(end)))} | {b for b in bars if b < end})
        last = 0
        for beat in clicks:
            tick = round(beat * tpb)
            accent = beat in bars
            note = 76 if accent else 77        # Hi / Low Wood Block (GM)
            track.append(mido.Message("note_on", channel=DRUM_MIDI_CHANNEL, note=note,
                                      velocity=110 if accent else 75, time=tick - last))
            track.append(mido.Message("note_off", channel=DRUM_MIDI_CHANNEL, note=note,
                                      velocity=0, time=tpb // 8))
            last = tick + tpb // 8
        return track

    # ------------------------------------------------------------ partitura

    def musicxml(self, track_names: Optional[Iterable[str]] = None) -> str:
        """La partitura in MusicXML (st_language.musicxml, la stessa della
        vista Partitura di SoundText): le tracce udibili, oppure solo
        quelle nominate, nell'ordine del file. La impagina verovio nella
        pagina (mobile/score-worker.js)."""
        from core.musicxml_export import project_to_musicxml
        t0 = time.perf_counter()
        tracks = [t for t in self.project.audible_tracks() if not t.is_audio]
        if track_names is not None:
            wanted = set(track_names)
            tracks = [t for t in self.project.tracks if t.name in wanted and not t.is_audio]
        xml = project_to_musicxml(self.project, tracks=tracks)
        self.timings["musicxml_s"] = time.perf_counter() - t0
        return xml

    # ------------------------------------------------------------ linea del tempo

    def length_beats(self) -> float:
        """Dove finisce il brano, in battiti: l'ultimo evento del MIDI."""
        if getattr(self, "_length", None) is None:
            import mido
            mid = mido.MidiFile(file=io.BytesIO(self._base_midi()))
            ticks = max((sum(m.time for m in t) for t in mid.tracks), default=0)
            self._length = ticks / mid.ticks_per_beat
        return self._length

    def bar_list(self) -> List[float]:
        """L'inizio di ogni battuta fino alla fine del brano, in battiti,
        con la metrica del brano (cambi e levare compresi)."""
        from st_language.notation import bar_starts
        end = self.length_beats()
        out = []
        for start in bar_starts(self.project.time_sig, self.project.metrica_changes, self.project.pickup):
            start = float(start)
            if start >= end - 1e-9 and out:
                break
            out.append(start)
            if len(out) > 100000:
                break
        return out

    def timeline(self) -> dict:
        """Lunghezza e battute, per la barra di avanzamento e il loop A-B."""
        return {"length": self.length_beats(), "bars": self.bar_list()}

    # ------------------------------------------------------------ evidenziazione

    def highlight_spans(self) -> List[Tuple[int, int, int, float, float, int]]:
        """(traccia, char_start, char_end, beat_start, beat_durata, livello)
        nel testo del file: livello 0 per i token di un box o di una traccia,
        poi +1 per ogni pattern in cui si scende. Uno span che ha figli
        (un %Nome) resta, con un livello minore dei figli."""
        from core.notation import compute_token_spans
        t0 = time.perf_counter()
        project = self.project
        text = self.text
        blocks = file_blocks(text)
        pattern_body = {}
        for b in blocks:
            m = RE_PATTERN_HDR.match(b["header"])
            if m:
                pattern_body[m.group(1)] = (b["start"], b["end"])
        tracks = [t for t in project.tracks if not t.is_audio]
        index = {t.name: i for i, t in enumerate(tracks)}
        meter = project.meter()
        cache: Dict[tuple, list] = {}

        def spans_of(start: int, end: int, octave: int, origin: float = 0.0):
            key = (start, end, octave, origin)
            if key not in cache:
                body = _blank_comments(text[start:end])
                try:
                    cache[key] = compute_token_spans(body, project.patterns, default_octave=octave,
                                                     meter=meter, origin_beat=origin)
                except Exception:
                    cache[key] = []
            return cache[key]

        out = []

        def walk(track_i: int, start: int, end: int, octave: int, base: float, depth: int,
                 origin: float = 0.0, limit: Optional[float] = None):
            for cs, ce, b0, dur in spans_of(start, end, octave, origin):
                if limit is not None and b0 >= limit:
                    break
                out.append((track_i, start + cs, start + ce, base + b0, dur, depth))
                m = RE_PATTERN_REF.match(text[start + cs:start + ce])
                if m and m.group(1) in pattern_body and depth < MAX_DEPTH:
                    ps, pe = pattern_body[m.group(1)]
                    walk(track_i, ps, pe, octave, base + b0, depth + 1, limit=dur)

        for b in blocks:
            header = b["header"]
            if b["end"] <= b["start"] or RE_PATTERN_HDR.match(header):
                continue
            m = RE_BOX_HDR.match(header)
            if m:
                name, beat = m.group(1), float(m.group(2))
            else:
                name, beat = self._track_of_header(header, index), 0.0
            if name not in index:
                continue
            track = tracks[index[name]]
            walk(index[name], b["start"], b["end"], track.instrument.default_octave, beat, 0, origin=beat)
        out.sort(key=lambda s: (s[0], s[3], s[5]))
        self.timings["spans_s"] = time.perf_counter() - t0
        return out

    @staticmethod
    def _track_of_header(header: str, index: Dict[str, int]) -> Optional[str]:
        """Il nome della traccia di un'intestazione "Traccia Nome [Strumento]:"
        o della forma breve "Nome:"."""
        head = header[:-1].strip()
        for prefix in ("Traccia ", "Track "):
            if head.startswith(prefix):
                head = head[len(prefix):]
        head = re.sub(r"\s*\[[^\]]*\]$", "", head).strip()
        return head if head in index else None


# ------------------------------------------------------------ controlli del testo

# Intestazioni che hanno la forma corta "Nome:" ma non sono tracce
_OTHER_HEADER_NAMES = ("RE_AMBIENTE", "RE_AUDIO_HDR", "RE_COMPOSER", "RE_CONVERSION_HDR", "RE_EFFECTS_HDR",
                       "RE_INSTRUMENT_HDR", "RE_KEY_LIST_HDR", "RE_LYRICIST", "RE_MASTER", "RE_MASTER_CHAIN_HDR",
                       "RE_METRICA_LIST_HDR", "RE_MIXER_HDR", "RE_SYNTH_HDR", "RE_TEMPO_LIST_HDR", "RE_TITLE")

# Categorie dei colori: quelle di core.syntax piu' "header" (intestazioni e
# righe di impostazioni del file, fuori dalla notazione).
def _names(names: List[str], most: int = 4) -> str:
    return ", ".join(names[:most]) + (", …" if len(names) > most else "")


def _unsupported_warnings(text: str, project, warn, tr) -> None:
    """Un avviso per ogni genere di parte che l'app non suona, sul primo
    blocco che la scrive: strumenti SFZ o plugin (suonano col SoundFont
    General MIDI), effetti e catena master, tracce audio. Il file le
    conserva com'erano (l'app modifica solo il testo cambiato)."""
    import st_language.stfile as stfile
    first = {}
    for b in file_blocks(text):
        header = b["header"]
        if stfile.RE_SYNTH_HDR.match(header):
            kind = "synth"
        elif stfile.RE_EFFECTS_HDR.match(header) or stfile.RE_MASTER_CHAIN_HDR.match(header):
            kind = "effects"
        elif stfile.RE_AUDIO_HDR.match(header):
            kind = "audio"
        else:
            continue
        first.setdefault(kind, (b["hstart"], b["hstart"] + len(header)))
    synth = [t.name for t in project.tracks if t.synth and not t.is_audio]
    effects = [t.name for t in project.tracks if t.effects]
    audio = [t.name for t in project.tracks if t.is_audio]
    if synth:
        start, end = first.get("synth", (0, 0))
        warn(start, end, "unsupported",
             tr("Strumenti SFZ o plugin ({tracks}): nell'app suonano con il SoundFont General MIDI.",
                tracks=_names(synth)))
    if effects or project.master_effects:
        start, end = first.get("effects", (0, 0))
        warn(start, end, "unsupported",
             tr("Effetti e catena master non si sentono nell'app; il file li conserva come sono."))
    if audio:
        start, end = first.get("audio", (0, 0))
        warn(start, end, "unsupported",
             tr("Tracce audio ({tracks}): nell'app non suonano; il file le conserva come sono.",
                tracks=_names(audio)))


def syntax_categories() -> list:
    from core.syntax import CATEGORIES
    return list(CATEGORIES) + ["header"]


def check_text(text: str, name: str = "Brano") -> dict:
    """I controlli del testo per l'editor, sul file intero:

    - syntax: colori, terne piatte (inizio, lunghezza, categoria) con la
      categoria come indice di syntax_categories(); la notazione si colora
      con core.syntax (come l'editor di SoundText), il resto del file solo
      nei commenti e nelle intestazioni;
    - voices: sfondi delle voci { ; }, terne (inizio, lunghezza, voce);
    - warnings: avvisi {start, end, kind, message}: "error" (il testo di un
      box, di una traccia o di un pattern non si legge), "bar", "anchor",
      "lyric"... (core.notation.notation_warnings, come SoundText),
      "ignored" (blocco "Nome:" di uno strumento sconosciuto, che il
      lettore dei file salta senza dirlo), "file" (Project.file_warnings);
    - blocks: tracce, box e pattern per il menu "Vai a" {start, label, kind}.
    Le posizioni sono indici di carattere nel testo."""
    import st_language.stfile as stfile
    from core.i18n import tr
    from core.notation import comment_spans, notation_warnings, validate_track_text
    from core.project_io import parse_project_text
    from core.syntax import LineState, line_spans
    from st_language.instruments import suggest_instrument

    categories = {c: i for i, c in enumerate(syntax_categories())}
    out = {"syntax": [], "voices": [], "warnings": [], "blocks": [], "error": ""}
    try:
        project = parse_project_text(text, name)
    except Exception as e:                     # il file intero non si legge
        project = None
        out["error"] = str(e)
    _last_check.update(text=text, project=project)
    patterns = project.patterns if project else {}
    tracks = [t for t in project.tracks if not t.is_audio] if project else []
    index = {t.name: i for i, t in enumerate(tracks)}
    meter = project.meter() if project else None
    other_headers = [getattr(stfile, n) for n in _OTHER_HEADER_NAMES if hasattr(stfile, n)]

    def warn(start, end, kind, message):
        out["warnings"].append({"start": start, "end": end, "kind": kind, "message": message})

    # che cos'e' ogni blocco
    notation = []           # (blocco, traccia o None, ottava, battito d'inizio, avvisi di battuta?)
    for b in file_blocks(text):
        header, hstart = b["header"], b["hstart"]
        hend = hstart + len(header)
        m = RE_PATTERN_HDR.match(header)
        if m:
            notation.append((b, None, 4, 0.0, False))
            out["blocks"].append({"start": hstart, "label": "%" + m.group(1), "kind": "pattern"})
            continue
        m = RE_BOX_HDR.match(header)
        if m:
            track_name = m.group(1)
            title = re.search(r'"([^"]*)"', header)
            track = tracks[index[track_name]] if track_name in index else None
            notation.append((b, track, track.instrument.default_octave if track else 4, float(m.group(2)),
                             track is not None))
            out["blocks"].append({"start": hstart, "label": f"{track_name} · {title.group(1) if title else ''}",
                                  "kind": "box"})
            if track is None and project:
                warn(hstart, hend, "ignored",
                     tr("Il box è della traccia «{track}», che nel brano non c'è.", track=track_name))
            continue
        if any(rx.match(header) for rx in other_headers):
            continue
        track_name = Engine._track_of_header(header, index)
        if track_name is not None:
            track = tracks[index[track_name]]
            notation.append((b, track, track.instrument.default_octave, 0.0, True))
            out["blocks"].append({"start": hstart, "label": track_name, "kind": "track"})
        elif project and stfile.RE_TRACK_HDR.match(header) and not stfile.RE_TRACK_HDR_EXPLICIT.match(header):
            # "Basso:": una traccia di uno strumento che non si conosce
            instrument = stfile.RE_TRACK_HDR.match(header).group(1)
            message = tr("«{header}» viene ignorato: «{instrument}» non è uno strumento noto.",
                         header=header, instrument=instrument)
            suggestion = suggest_instrument(instrument)
            if suggestion:
                message += " " + tr("Forse intendevi «{suggestion}»?", suggestion=suggestion)
            # da st-language 2.12.2 lo dice gia' il lettore dei file (avviso "file", qui sotto)
            if text.count("\n", 0, hstart) + 1 not in {line for line, _m in project.file_warnings}:
                warn(hstart, hend, "ignored", message)

    # parti del file che l'app non suona (restano nel file come sono)
    if project:
        _unsupported_warnings(text, project, warn, tr)

    # avvisi del lettore dei file (strumenti sconosciuti nelle intestazioni esplicite...)
    if project:
        line_starts = [0] + [i + 1 for i, ch in enumerate(text) if ch == "\n"]
        for line, message in project.file_warnings:
            if 1 <= line <= len(line_starts):
                start = line_starts[line - 1]
                end = text.find("\n", start)
                warn(start, end if end >= 0 else len(text), "file", message)

    # notazione: errori, avvisi e colori
    bodies = []
    for b, track, octave, beat, bar_checks in notation:
        start, end = b["start"], b["end"]
        if end <= start:
            continue
        bodies.append((start, end))
        body = _blank_comments(text[start:end])
        if not body.strip():
            continue
        errors = set()
        ok, msg = validate_track_text(body, patterns, default_octave=octave, meter=meter)
        if not ok:
            warn(b["hstart"], b["hstart"] + len(b["header"]), "error", msg)
        elif bar_checks and project:
            for issue in notation_warnings(body, patterns, project.time_sig, project.metrica_changes,
                                           start_beat=beat, default_octave=octave, pickup=project.pickup,
                                           key=project.key, key_changes=project.key_changes):
                warn(start + issue.char_start, start + issue.char_end, issue.kind, issue.message)
                errors.add(start + issue.char_start)
        state = LineState()
        pos = start
        for line in text[start:end].split("\n"):
            line_errors = [e - pos for e in errors if pos <= e < pos + len(line)]
            spans, voices, state = line_spans(line, state, line_errors)
            for s0, length, category in spans:
                out["syntax"] += [pos + s0, length, categories[category]]
            run = None
            for i, v in enumerate(voices + [None]):
                if run is not None and (v != run[1]):
                    out["voices"] += [pos + run[0], i - run[0], run[1]]
                    run = None
                if v is not None and run is None:
                    run = (i, v)
            pos += len(line) + 1

    # fuori dalla notazione: commenti e intestazioni
    bodies.sort()
    pos = 0
    body_i = 0
    for line in text.split("\n"):
        while body_i < len(bodies) and bodies[body_i][1] < pos:
            body_i += 1
        inside = body_i < len(bodies) and bodies[body_i][0] <= pos <= bodies[body_i][1]
        if not inside:
            comments = comment_spans(line)
            for s0, e0 in comments:
                out["syntax"] += [pos + s0, e0 - s0, categories["comment"]]
            code_end = comments[0][0] if comments else len(line)
            code = line[:code_end].rstrip()
            if code and line[:1] not in (" ", "\t"):
                out["syntax"] += [pos, len(code), categories["header"]]
        pos += len(line) + 1
    out["warnings"].sort(key=lambda w: w["start"])
    return out


# Il brano dell'ultimo controllo: il completamento, che si chiede a ogni
# tasto, usa i suoi pattern e strumenti invece di rileggere il file.
_last_check = {"text": None, "project": None}


def _project_for(text: str):
    from core.project_io import parse_project_text
    if _last_check["project"] is None or _last_check["text"] is None:
        try:
            _last_check.update(text=text, project=parse_project_text(text, "Brano"))
        except Exception:
            return None
    return _last_check["project"]


def _instrument_at(text: str, pos: int, project):
    """Lo strumento del blocco (box o traccia) in cui sta 'pos', None in un
    pattern o fuori dalla notazione."""
    if project is None:
        return None
    tracks = {t.name: t for t in project.tracks if not t.is_audio}
    for b in file_blocks(text):
        if b["hstart"] <= pos <= b["end"]:
            m = RE_BOX_HDR.match(b["header"])
            name = m.group(1) if m else Engine._track_of_header(b["header"], {n: 0 for n in tracks})
            return tracks[name].instrument if name in tracks else None
    return None


def complete(text: str, pos: int) -> dict:
    """I suggerimenti per la parola che finisce in 'pos', come l'editor di
    SoundText (core.completion): {start, end, items: [{text, label}]}; la
    parola da sostituire e' text[start:end]."""
    from core.completion import completions_for_word, current_word_bounds
    start, end = current_word_bounds(text, pos)
    word = text[start:end]
    project = _project_for(text)
    try:
        items = completions_for_word(word, patterns=project.patterns if project else {},
                                     instrument=_instrument_at(text, pos, project), text_before=text[:start])
    except Exception:
        items = []
    return {"start": start, "end": end,
            "items": [{"text": str(c), "label": getattr(c, "label", str(c))} for c in items[:20]]}


def transforms() -> list:
    """Le funzioni sui pattern per la barra musicale: nome nella lingua
    dell'interfaccia, argomenti e spiegazione."""
    from core.completion import _italian
    from st_language.transform import list_transforms
    italian = _italian()
    out = []
    for t in list_transforms():
        args = [a["name"] for a in t["arguments"] if a["required"]] or [a["name"] for a in t["arguments"]][:1]
        name = t["alias"] if italian else t["name"]
        # pronta da aggiungere a un richiamo: gli argomenti obbligatori con
        # il loro valore iniziale (Trasforma nell'app)
        values = [str(a["default"]).strip("'") if a["default"] is not None else a["name"]
                  for a in t["arguments"] if a["required"]]
        values = [v if not v.startswith("2") or a["type"] != "note_value" else "'" + v
                  for v, a in zip(values, [a for a in t["arguments"] if a["required"]])]
        out.append({"call": f".{name}({','.join(args)})" if args else f".{name}", "help": t["help"],
                    "ready": f".{name}({','.join(values)})" if values else f".{name}"})
    return out


# ------------------------------------------------------------ trasforma (fase 2)
#
# La finestra Trasforma di SoundText (gui/transform_dialog.py) nell'app: il
# richiamo di pattern sotto il cursore, la catena di funzioni passo per
# passo, le note che suona nel suo punto del brano (core.transform_preview,
# come l'anteprima del computer), il MIDI e il MusicXML di prima e di dopo
# per ascoltarli e vederli, e la sostituzione nel testo (anche scritta nota
# per nota, «Congela la trasformazione»).

def _notation_block_at(text: str, pos: int, project):
    """(blocco, strumento, battito d'inizio) del box, della traccia o del
    pattern che contiene 'pos'; None fuori dalla notazione."""
    from core.instruments import get_instrument
    index = {t.name: i for i, t in enumerate(project.tracks)}
    for b in file_blocks(text):
        if not (b["start"] <= pos <= max(b["end"], b["start"])):
            continue
        m = RE_BOX_LINE.match(b["header"])
        if m and m.group(1) in index:
            return b, project.tracks[index[m.group(1)]].instrument, float(m.group(3))
        if RE_PATTERN_HDR.match(b["header"]):
            return b, get_instrument("Piano"), 0.0
        name = Engine._track_of_header(b["header"], index)
        if name is not None:
            return b, project.tracks[index[name]].instrument, 0.0
    return None


def _project_midi(project) -> bytes:
    import os
    import tempfile
    from core.midi_export import export_project_to_midi
    fd, path = tempfile.mkstemp(suffix=".mid")
    os.close(fd)
    try:
        export_project_to_midi(project, path, only_audible=False)
        with open(path, "rb") as f:
            return f.read()
    finally:
        os.remove(path)


def transform_at(text: str, pos: int) -> Optional[dict]:
    """Il richiamo di pattern sotto il cursore: {start, end, token,
    pattern}, oppure None."""
    from core.project_io import parse_project_text
    from core.transform_preview import reference_at
    from st_language.transform import parse_reference
    try:
        project = parse_project_text(text, "Brano")
    except Exception:
        return None
    found = _notation_block_at(text, pos, project)
    if found is None:
        return None
    block = found[0]
    body = text[block["start"]:block["end"]]
    ref = reference_at(body, pos - block["start"], with_functions=False)
    if ref is None:
        return None
    start, end, token = ref
    try:
        pattern = parse_reference(token).pattern
    except Exception:
        return None
    return {"start": block["start"] + start, "end": block["start"] + end, "token": token, "pattern": pattern}


def transform_preview(text: str, pos: int, token: str) -> dict:
    """L'anteprima di 'token' al posto del richiamo sotto il cursore:
    {token (scritto nella lingua dell'interfaccia), stages: [[passo, note]],
    notation, warnings, error, midi_before, midi_after (base64), xml_before,
    xml_after}. Con un richiamo non valido c'e' solo 'error'."""
    import base64
    from core.i18n import current_language
    from core.musicxml_export import project_to_musicxml
    from core.project_io import parse_project_text
    from core.transform_preview import expansion, preview_notation, preview_project, reference_point, stage_lines
    from st_language.notation import NotationError
    from st_language.transform import format_reference, parse_reference
    ref = transform_at(text, pos)
    if ref is None:
        from core.i18n import tr
        return {"error": tr("Metti il cursore su un richiamo di pattern (%Nome).")}
    project = parse_project_text(text, "Brano")
    block, instrument, origin = _notation_block_at(text, pos, project)
    body = text[block["start"]:block["end"]]
    point = reference_point(body, ref["start"] - block["start"], project.patterns, instrument, project.meter(), origin)
    out = {"start": ref["start"], "end": ref["end"], "pattern": ref["pattern"], "position": point.position}
    try:
        written = format_reference(parse_reference(token.strip()), italian=current_language() == "it")
        result = expansion(written, project, point, instrument)
        out.update(token=written, stages=[list(x) for x in stage_lines(written, result)],
                   notation=preview_notation(written, project, point, instrument),
                   warnings=list(result.warnings), error="")
    except (NotationError, ValueError, KeyError) as e:
        return {**out, "error": str(e)}
    for which, tok in (("before", "%" + ref["pattern"]), ("after", out["token"])):
        preview = preview_project(project, tok, point, instrument.name)
        out["midi_" + which] = base64.b64encode(_project_midi(preview)).decode("ascii")
        out["xml_" + which] = project_to_musicxml(preview, tracks=preview.tracks)
    return out


def transform_apply(text: str, pos: int, token: str, freeze: bool = False) -> dict:
    """Il brano con 'token' al posto del richiamo sotto il cursore e, con
    freeze, scritto nota per nota (core.transform_preview.freeze_span, che
    rifiuta se il suono cambierebbe): {text, start, end}."""
    from core.project_io import parse_project_text
    from core.transform_preview import freeze_span
    ref = transform_at(text, pos)
    if ref is None:
        from core.i18n import tr
        raise ValueError(tr("Metti il cursore su un richiamo di pattern (%Nome)."))
    new = text[:ref["start"]] + token + text[ref["end"]:]
    end = ref["start"] + len(token)
    if freeze:
        project = parse_project_text(new, "Brano")
        block, instrument, origin = _notation_block_at(new, ref["start"], project)
        body = new[block["start"]:block["end"]]
        # freeze_span lavora sul testo della traccia, senza il rientro del file
        plain, offset = _dedent(body, [ref["start"] - block["start"], end - block["start"]])
        frozen = _indent(freeze_span(plain, offset[0], offset[1], project, instrument, origin))
        new = new[:block["start"]] + frozen + new[block["end"]:]
        end = block["end"] + len(frozen) - len(body)
    return {"text": new, "start": ref["start"], "end": end}


# ------------------------------------------------------------ dettatura (fase 2)

def dictate(text: str, phrase: str, lang: Optional[str] = None, mode: str = "auto") -> dict:
    """La frase riconosciuta dalla dettatura -> testo ST, pezzi e comandi
    (core.dictation.interpret), nella lingua data o in quella
    dell'interfaccia; i pattern del brano si riconoscono per nome («Tema
    invertito»)."""
    from core.dictation import interpret
    from core.i18n import current_language
    from core.project_io import parse_project_text
    try:
        patterns = list(parse_project_text(text, "Brano").patterns)
    except Exception:                                  # il file non si legge: niente pattern
        patterns = []
    return interpret(phrase, lang or current_language(), mode, patterns)


def dictate_track(text: str, spoken: str, lang: Optional[str] = None) -> Optional[dict]:
    """«nuova traccia basso»: il brano con una traccia nuova in fondo, vuota,
    pronta per dettare: {text, name}. None se lo strumento non si conosce."""
    from core.dictation import instrument_name
    from core.i18n import current_language
    instrument = instrument_name(spoken, lang or current_language())
    if not instrument:
        return None
    # il nome della traccia: lo strumento, o la parola detta («Violino»)
    name = None if _has_short_header(instrument) else (spoken.strip().split() or [instrument])[-1].capitalize()
    r = add_track(text, instrument, "", name)
    return {"text": r["text"].rstrip("\n") + "\n  ", "name": r["name"]}


def dictation_words(text: str, lang: Optional[str] = None) -> list:
    """La grammatica del riconoscimento locale (core.dictation.grammar): le
    parole e le frasi della dettatura, con i nomi dei pattern del brano."""
    from core.dictation import grammar
    from core.i18n import current_language
    from core.project_io import parse_project_text
    try:
        patterns = list(parse_project_text(text, "Brano").patterns)
    except Exception:
        patterns = []
    return grammar(lang or current_language(), patterns)


def _dedent(body: str, positions: List[int]) -> Tuple[str, List[int]]:
    """Il corpo di un blocco senza il rientro di ogni riga (due spazi o un
    tab), con le posizioni date riportate nel testo senza rientro."""
    out, mapped, pos, removed = [], list(positions), 0, 0
    for line in body.split("\n"):
        cut = 2 if line.startswith("  ") else 1 if line.startswith("\t") else 0
        for i, p in enumerate(positions):
            if p >= pos + cut:
                mapped[i] = p - removed - cut
        removed += cut
        out.append(line[cut:])
        pos += len(line) + 1
    return "\n".join(out), mapped


def _indent(text: str) -> str:
    return "\n".join("  " + line if line.strip() else "" for line in text.split("\n"))


def bar_bounds(text: str, beat: float) -> list:
    """[inizio, fine] in battiti della battuta che contiene 'beat', con la
    metrica del brano (cambi e levare compresi)."""
    from st_language.notation import bar_starts
    project = _project_for(text)
    if project is None:
        return [0.0, 4.0]
    previous = 0.0
    if project.pickup:
        previous = 0.0
    for start in bar_starts(project.time_sig, project.metrica_changes, project.pickup):
        start = float(start)
        if start > beat + 1e-9:
            return [previous, start]
        previous = start
    return [previous, previous + 4.0]


# ------------------------------------------------------------ generatori (fase 2)
#
# Giro armonico, batteria, basso e accompagnamento, con i generatori di
# SoundText (core.rhythm_generate, core.performance_style). I parametri e i
# valori predefiniti sono quelli delle finestre «Genera ...» di SoundText
# (gui/rhythm_generate_dialog.py), che qui non si possono importare perche'
# usano Qt: tests/test_mobile_engine.py pilota quelle finestre e controlla
# che con gli stessi parametri e lo stesso seme il testo sia identico.

GENERATORS = ("progression", "drums", "bass", "comping")
DEFAULT_VARIABILITY = 0.35          # il cursore Variabilita' delle finestre: 35%


def _bar_beats(project) -> float:
    from core.rhythm_generate import project_bar_beats
    return project_bar_beats(project)


def _variation(options: dict) -> dict:
    """Variabilita' (una sola, per ritmo, note e dinamica come con le quote
    al 100%) e seme; senza seme se ne sceglie uno, che si restituisce."""
    import random
    from core.rhythm_generate import Variability
    value = float(options.get("variability", DEFAULT_VARIABILITY))
    seed = options.get("seed")
    if seed is None:
        seed = random.randrange(2 ** 31)
    return {"variability": Variability(value, value, value), "seed": int(seed)}


def _chords_of(project, source: Optional[str], exclude: Optional[str]):
    """Gli accordi da seguire: quelli della traccia 'source', altrimenti
    della prima traccia di note che ne ha (diversa da quella di
    destinazione). (accordi, nome della traccia)."""
    from core.rhythm_generate import extract_chords_from_track
    from core.i18n import tr
    candidates = [t for t in project.tracks if not t.is_audio and t.name != exclude]
    if source:
        candidates = [t for t in candidates if t.name == source]
        if not candidates:
            raise ValueError(tr("La traccia '{name}' non c'è.", name=source))
    for track in candidates:
        chords = extract_chords_from_track(track.text, project.patterns, midi_dir=None)
        if chords:
            return chords, track
    if source:
        raise ValueError(
            tr("La traccia '{source_name}' non contiene accordi da seguire: servono accordi scritti come simbolo (es. Cmaj7) o blocchi [...] di almeno due note; note singole (melodie, arpeggi) non bastano.", source_name=source))
    raise ValueError(tr("Nel brano non c'è ancora una traccia con degli accordi da seguire."))


def _instrument(project, name: str):
    from core.instruments import get_instrument
    for track in project.tracks:
        if track.instrument_name == name and not track.is_audio:
            return track.instrument
    return get_instrument(name)


def _performed(text: str, instrument, options: dict, seed: int, project) -> str:
    """«Esecuzione dello strumento» (pennate, pedale, note fantasma)."""
    if not options.get("performance"):
        return text
    from core.performance_style import perform, style_for
    style = style_for(instrument)
    return perform(text, style, seed=seed, patterns=project.patterns) if style else text


def generate(text: str, kind: str, options: Optional[dict] = None) -> dict:
    """Il testo di una parte generata per il brano 'text': {text, seed}.

    kind: "progression" (giro armonico), "drums", "bass", "comping"
    (accompagnamento). options, tutte facoltative (i valori predefiniti
    delle finestre di SoundText):
    - comuni: seed, variability (0-1, 0.35), bars, intensity ("light",
      "normal", "full", "build"), track (la traccia di destinazione, che
      non fa da sorgente di accordi);
    - progression: key, style, chord_bars (0.5, 1, 2), ending;
    - drums: style, fill_every (4), phrase_fills (si'), ending (no),
      section_fills (si' se le altre tracce hanno dei box);
    - bass: source (traccia degli accordi), style, octave (2),
      variation_every (4), kick_track, performance, instrument ("Bass");
    - comping: source, style, instrument ("Piano"), octave, variation_every
      (4), voice_leading (si'), leave_space (si'), performance.
    ValueError con un messaggio leggibile se non si puo' generare."""
    from core.project_io import parse_project_text
    from core import rhythm_generate as rg
    options = dict(options or {})
    project = parse_project_text(text, "Brano")
    bar_beats = _bar_beats(project)
    variation = _variation(options)
    seed = variation["seed"]
    intensity = options.get("intensity", "normal")
    track_name = options.get("track")
    destination = project.find_track(track_name) if track_name else None
    start_beat = float(options.get("start_beat", rg.track_end_beat(project, destination)))

    if kind == "progression":
        key = options.get("key") or (project.key or "").strip() or "C"
        mode = rg.parse_key(key)[1]
        style = options.get("style") or next(n for n, spec in rg.PROGRESSION_STYLES.items() if spec["mode"] == mode)
        out = rg.generate_chord_progression(key, style, bars=int(options.get("bars", 0)),
                                            chord_bars=float(options.get("chord_bars", 1.0)), bar_beats=bar_beats,
                                            ending=bool(options.get("ending", False)), **variation)
    elif kind == "drums":
        styles = rg.drum_styles_for_meter(project.time_sig)
        style = options.get("style") or (styles[0] if styles else "rock")
        bars = int(options.get("bars", 8))
        sections = rg.section_end_bars(project, start_beat, 256, bar_beats, exclude_track_name=track_name)
        use_sections = options.get("section_fills", bool(sections))
        section_bars = rg.section_end_bars(project, start_beat, bars, bar_beats,
                                           exclude_track_name=track_name) if use_sections else []
        out = rg.generate_drum_pattern(style, bars=bars, fill_every=int(options.get("fill_every", 4)),
                                       intensity=intensity, phrase_fills=bool(options.get("phrase_fills", True)),
                                       ending=bool(options.get("ending", False)), kick_accents=None,
                                       section_fill_bars=section_bars, **variation)
    elif kind == "bass":
        chords, _source = _chords_of(project, options.get("source"), track_name)
        instrument = _instrument(project, options.get("instrument", "Bass"))
        kick = None
        if options.get("kick_track"):
            kick = rg.kick_beats_of_track(project, project.get_track(options["kick_track"]), start_beat) or None
        out = rg.generate_bass_from_chords(
            chords, options.get("style") or rg.BASS_STYLES[0], octave=int(options.get("octave", 2)),
            variation_every=int(options.get("variation_every", 4)),
            min_total_beats=int(options.get("bars", 4)) * bar_beats, bar_beats=bar_beats,
            intensity=intensity, kick_beats=kick, **variation)
        out = _performed(out, instrument, options, seed, project)
    elif kind == "comping":
        chords, _source = _chords_of(project, options.get("source"), track_name)
        instrument = _instrument(project, options.get("instrument", "Piano"))
        low, high = instrument.range_low, instrument.range_high
        if options.get("leave_space", True):
            low, high = rg.fit_register(low, high, True,
                                        rg.part_registers(project, exclude_track_name=track_name))
        out = rg.generate_melodic_line(
            chords, options.get("style") or rg.COMPING_STYLES[0],
            octave=int(options.get("octave", instrument.default_octave)),
            range_low=low, range_high=high, polyphonic=True,
            variation_every=int(options.get("variation_every", 4)),
            min_total_beats=int(options.get("bars", 4)) * bar_beats, bar_beats=bar_beats,
            intensity=intensity, voice_leading=bool(options.get("voice_leading", True)),
            key=None, meter=project.time_sig, repeats=(), **variation)
        out = _performed(out, instrument, options, seed, project)
    else:
        raise ValueError(f"generatore sconosciuto: {kind}")
    return {"text": out, "seed": seed}


def _choice_labels() -> dict:
    """Le etichette degli stili, delle intensita' e delle durate degli
    accordi, nella lingua dell'interfaccia: le stesse delle finestre
    «Genera ...» di SoundText (core/generate_labels.py)."""
    from core.generate_labels import generator_labels
    return generator_labels()


# Strumenti proposti per ogni generatore (quelli che esistono nel motore)
_GENERATOR_INSTRUMENTS = {
    "progression": ("Piano", "Rhodes", "Guitar", "Hammond", "Strings"),
    "drums": ("Drums",),
    "bass": ("Bass", "FretlessBass", "DoubleBass", "SlapBass1", "SynthBass1"),
    "comping": ("Piano", "Rhodes", "Wurli", "Guitar", "Nylon", "Clean", "Hammond", "Strings", "Pad"),
}


def generator_choices(text: str = "") -> dict:
    """Quello che serve alla schermata Crea per il brano 'text': per ogni
    generatore gli stili [{value, label}] (la batteria solo per la metrica
    del brano, i giri con il loro modo), gli strumenti; intensita', durate
    degli accordi, tonalita'; la tonalita' del brano, le tracce che possono
    fare da sorgente di accordi o da cassa e le battute gia' scritte."""
    from core import rhythm_generate as rg
    from core.instruments import get_instrument
    from core.project_io import parse_project_text
    try:
        project = parse_project_text(text, "Brano") if text.strip() else None
    except Exception:
        project = None
    meter = project.time_sig if project else "4/4"
    labels = _choice_labels()
    drums = set(rg.drum_styles_for_meter(meter))
    instruments = {}
    for kind, names in _GENERATOR_INSTRUMENTS.items():
        available = []
        for name in names:
            try:
                get_instrument(name)
            except ValueError:
                continue
            available.append(name)
        instruments[kind] = available
    sources, kicks = [], []
    bars = 0
    if project:
        for track in project.tracks:
            if track.is_audio or not track.text.strip():
                continue
            try:
                if rg.extract_chords_from_track(track.text, project.patterns, midi_dir=None):
                    sources.append(track.name)
                if track.instrument.is_percussion:
                    kicks.append(track.name)
            except Exception:
                continue
        try:
            bars = round(rg.tracks_duration_beats(project) / _bar_beats(project))
        except Exception:
            bars = 0
    item = lambda pairs: [{"value": v, "label": label} for v, label in pairs]
    return {
        "progression": [{"value": v, "label": label, "mode": rg.PROGRESSION_STYLES[v]["mode"]}
                        for v, label in labels["progression"]],
        "drums": [{"value": v, "label": label} for v, label in labels["drums"] if v in drums],
        "bass": item(labels["bass"]),
        "comping": item(labels["comping"]),
        "intensities": item(labels["intensity"]),
        "chord_durations": item(labels["chord_duration"]),
        "keys": ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B",
                 "Cm", "C#m", "Dm", "Ebm", "Em", "Fm", "F#m", "Gm", "G#m", "Am", "Bbm", "Bm"],
        "instruments": instruments,
        "key": ((project.key or "").strip() if project else "") or "C",
        "sources": sources,
        "kick_tracks": kicks,
        "bars": bars,
    }


def _has_short_header(instrument: str) -> bool:
    """«Bass:» vale per gli strumenti del catalogo e, da st-language 2.12.2,
    per i nomi General MIDI scritti per intero («Flute:», «Violin:»); gli
    altri si scrivono «Traccia Nome [Strumento]:»."""
    from core.instruments import all_instruments
    from st_language.instruments import is_instrument_name
    return instrument in all_instruments() or is_instrument_name(instrument)


def add_track(text: str, instrument: str, body: str, name: Optional[str] = None) -> dict:
    """Il brano con una traccia nuova in fondo: {text, name, start}.

    Il nome e' quello dato o quello dello strumento, con un numero se c'e'
    gia' una traccia che si chiama cosi'. L'intestazione e' la forma breve
    «Bass:» quando il nome e' lo strumento, altrimenti
    «Traccia Nome [Strumento]:». Il resto del file non cambia."""
    from core.project_io import parse_project_text
    try:
        taken = {t.name for t in parse_project_text(text, "Brano").tracks}
    except Exception:
        taken = set()
    base = (name or instrument).strip()
    candidate, n = base, 2
    while candidate in taken:
        candidate, n = f"{base} {n}", n + 1
    if candidate == instrument and re.match(r"^[A-Za-z]\w*$", candidate) and _has_short_header(instrument):
        header = f"{candidate}:"
    else:
        header = f"Traccia {candidate} [{instrument}]:"
    lines = "\n".join("  " + line if line.strip() else "" for line in body.strip().split("\n"))
    head = text.rstrip("\n")
    new = (head + "\n\n" if head else "") + header + "\n" + lines + "\n"
    return {"text": new, "name": candidate, "start": len(head) + (2 if head else 0)}


# ------------------------------------------------------------ struttura (fase 2)
#
# La schermata Struttura: le sezioni del brano (core.arrangement.song_sections,
# come il righello della vista Struttura di SoundText) e i box di ogni
# traccia, con la loro posizione nel testo. Le modifiche (sposta, rinomina,
# duplica, elimina un box o una sezione, dividi in box) cambiano solo le
# intestazioni «Box Traccia "Nome" |battito:» e i blocchi dei box: il resto
# del file resta com'e', come per ogni modifica dell'app.

RE_BOX_LINE = re.compile(r'^Box\s+(.+?)\s+"(.*)"\s*\|\s*([0-9.]+)\s*:\s*$')


def _format_beat(beat: float) -> str:
    """core.project_io._format_beat"""
    beat = round(float(beat), 6)
    return str(int(beat)) if beat == int(beat) else str(beat)


def _box_header(track: str, name: str, beat: float) -> str:
    return f'Box {track} "{name.replace(chr(34), chr(39)).strip()}" |{_format_beat(beat)}:'


def _box_blocks(text: str) -> List[dict]:
    """I blocchi dei box del file: track, name, beat, hstart, end (fine
    dell'ultima riga del corpo), header."""
    out = []
    for b in file_blocks(text):
        m = RE_BOX_LINE.match(b["header"])
        if m:
            out.append({"track": m.group(1), "name": m.group(2), "beat": float(m.group(3)),
                        "hstart": b["hstart"], "hend": b["hstart"] + len(b["header"]),
                        "start": b["start"], "end": max(b["end"], b["hstart"] + len(b["header"]))})
    return out


def _bars_until(project, end_beat: float) -> List[float]:
    from st_language.notation import bar_starts
    bars = []
    for start in bar_starts(project.time_sig, project.metrica_changes, project.pickup):
        start = float(start)
        bars.append(start)
        if start > end_beat + 1e-9 or len(bars) > 100000:
            break
    return bars


def _bar_number(bars: List[float], beat: float) -> int:
    import bisect
    return max(1, bisect.bisect_right(bars, beat + 1e-9))


def structure(text: str) -> dict:
    """Sezioni e box del brano, per la schermata Struttura.

    {tracks: [{name, instrument, plain, boxes: [{name, beat, length, bar,
    bars, hstart, start}]}], sections: [{beat, bar, name}], bars: inizio
    di ogni battuta, end}. Una traccia senza box ('plain') ha un solo box
    finto, il suo testo, con hstart -1."""
    from core.arrangement import song_sections
    from core.project_io import parse_project_text
    from st_language.song import clip_duration_beats
    project = parse_project_text(text, "Brano")
    meter = project.meter()
    blocks = _box_blocks(text)
    used = set()
    tracks, end = [], 0.0
    for track in project.tracks:
        if track.is_audio:
            continue
        octave = track.instrument.default_octave
        boxes = []
        for clip in sorted(track.clips, key=lambda c: c.start_beat):
            length = clip_duration_beats(clip.text, project.patterns, octave, clip.start_beat, meter)
            block = next((b for i, b in enumerate(blocks) if i not in used and b["track"] == track.name
                          and abs(b["beat"] - clip.start_beat) < 1e-6), None)
            if block is not None:
                used.add(blocks.index(block))
            boxes.append({"name": clip.name, "beat": clip.start_beat, "length": length,
                          "hstart": block["hstart"] if block else -1, "start": block["start"] if block else -1})
            end = max(end, clip.start_beat + length)
        plain = not track.clips
        if plain and track.text.strip():
            try:
                events = track.parsed_events(project.patterns, midi_dir=None, meter=meter)
                length = max((e.start + e.duration for e in events), default=0.0)
            except Exception:
                length = 0.0
            boxes.append({"name": "", "beat": 0.0, "length": length, "hstart": -1, "start": -1})
            end = max(end, length)
        tracks.append({"name": track.name, "instrument": track.instrument_name, "plain": plain, "boxes": boxes})
    bars = _bars_until(project, end)
    for t in tracks:
        for b in t["boxes"]:
            b["bar"] = _bar_number(bars, b["beat"])
            b["bars"] = max(1, _bar_number(bars, b["beat"] + max(b["length"], 1e-6) - 1e-6) - b["bar"] + 1)
    sections = [{"beat": beat, "name": name} for beat, name in song_sections(project)]
    if not sections or sections[0]["beat"] > 1e-9:
        # l'inizio del brano e' sempre una sezione: col nome di un box che
        # comincia li', se c'e'
        first = next((b["name"] for t in tracks if not t["plain"] for b in t["boxes"] if b["beat"] < 1e-9), "")
        sections.insert(0, {"beat": 0.0, "name": first})
    for sec in sections:
        sec["bar"] = _bar_number(bars, sec["beat"])
    return {"tracks": tracks, "sections": sections, "bars": bars, "end": end}


def _check_overlaps(text: str) -> None:
    """ValueError se due box della stessa traccia si sovrappongono."""
    from core.i18n import tr
    info = structure(text)
    for track in info["tracks"]:
        boxes = sorted((b for b in track["boxes"] if b["hstart"] >= 0), key=lambda b: b["beat"])
        for a, b in zip(boxes, boxes[1:]):
            if a["beat"] + a["length"] > b["beat"] + 1e-6:
                raise ValueError(tr("Nella traccia «{track}» il box «{a}» si sovrappone a «{b}».",
                                    track=track["name"], a=a["name"], b=b["name"]))


def _insert_after_track_boxes(text: str, track: str, block: str) -> Tuple[str, int]:
    """Il testo con 'block' dopo l'ultimo box della traccia (o in fondo)."""
    boxes = [b for b in _box_blocks(text) if b["track"] == track]
    at = max(b["end"] for b in boxes) if boxes else len(text.rstrip("\n"))
    insert = "\n\n" + block
    return text[:at] + insert + text[at:], at + 2


def _song_end_bar_beat(text: str) -> float:
    """L'inizio della battuta dopo la fine del brano (dove si accoda una
    sezione duplicata)."""
    info = structure(text)
    bars = info["bars"]
    end = info["end"]
    return next((b for b in bars if b >= end - 1e-6), bars[-1] if bars else 0.0)


def box_edit(text: str, op: str, args: dict) -> dict:
    """Una modifica della struttura: {text, focus} (focus: dove portare il
    cursore, o -1). op e args:
    - "move" {hstart, bar}: il box comincia alla battuta 'bar';
    - "rename" {hstart, name};
    - "duplicate" {hstart}: una copia subito dopo l'ultimo box della sua
      traccia, alla fine del brano;
    - "delete" {hstart};
    - "section_duplicate" {beat}: tutti i box che cominciano nella sezione,
      copiati in fondo al brano con le stesse distanze;
    - "section_rename" {beat, name}: i box che cominciano nella sezione;
    - "section_delete" {beat};
    - "make_boxes" {name}: il testo di ogni traccia senza box diventa un box
      'name' che comincia alla battuta 1.
    ValueError con un messaggio leggibile (box che si sovrappongono...)."""
    from core.i18n import tr
    blocks = _box_blocks(text)
    by_start = {b["hstart"]: b for b in blocks}

    def box(hstart):
        b = by_start.get(int(hstart))
        if b is None:
            raise ValueError(tr("Il box non c'è più: il testo è cambiato."))
        return b

    def section_boxes(beat):
        info = structure(text)
        starts = [s["beat"] for s in info["sections"]]
        beat = float(beat)
        later = [s for s in starts if s > beat + 1e-9]
        until = min(later) if later else float("inf")
        return [b for b in blocks if beat - 1e-9 <= b["beat"] < until - 1e-9], beat, until

    focus = -1
    if op == "move":
        b = box(args["hstart"])
        bars = structure(text)["bars"]
        n = max(1, int(args["bar"]))
        while len(bars) < n:
            bars.append(bars[-1] + (bars[-1] - bars[-2] if len(bars) > 1 else 4.0))
        header = _box_header(b["track"], b["name"], bars[n - 1])
        new = text[:b["hstart"]] + header + text[b["hend"]:]
        focus = b["hstart"]
    elif op == "rename":
        b = box(args["hstart"])
        name = str(args["name"]).strip()
        if not name:
            raise ValueError(tr("Il nome non può essere vuoto."))
        new = text[:b["hstart"]] + _box_header(b["track"], name, b["beat"]) + text[b["hend"]:]
        focus = b["hstart"]
    elif op == "duplicate":
        b = box(args["hstart"])
        beat = _song_end_bar_beat(text)
        body = text[b["hend"]:b["end"]]
        new, focus = _insert_after_track_boxes(text, b["track"], _box_header(b["track"], b["name"], beat) + body)
    elif op == "delete":
        b = box(args["hstart"])
        end = b["end"]
        while end < len(text) and text[end] == "\n" and end + 1 <= len(text):
            end += 1
            if end < len(text) and text[end] != "\n":
                break
        new = text[:b["hstart"]] + text[end:]
        new = new if new.endswith("\n") or not text.endswith("\n") else new
    elif op in ("section_duplicate", "section_rename", "section_delete"):
        chosen, beat, _until = section_boxes(args["beat"])
        if not chosen:
            raise ValueError(tr("Nella sezione non ci sono box."))
        new = text
        if op == "section_duplicate":
            base = _song_end_bar_beat(text)
            copies = [(b["track"], _box_header(b["track"], b["name"], base + b["beat"] - beat)
                       + text[b["hend"]:b["end"]]) for b in chosen]
            for track, block in copies:
                new, at = _insert_after_track_boxes(new, track, block)
                focus = at if focus < 0 else focus
        elif op == "section_rename":
            name = str(args["name"]).strip()
            if not name:
                raise ValueError(tr("Il nome non può essere vuoto."))
            for b in sorted(chosen, key=lambda b: -b["hstart"]):
                new = new[:b["hstart"]] + _box_header(b["track"], name, b["beat"]) + new[b["hend"]:]
        else:
            for b in sorted(chosen, key=lambda b: -b["hstart"]):
                new = box_edit(new, "delete", {"hstart": b["hstart"]})["text"]
    elif op == "make_boxes":
        name = str(args.get("name") or "A").strip()
        from core.project_io import parse_project_text
        project = parse_project_text(text, "Brano")
        index = {t.name: i for i, t in enumerate(project.tracks)}
        boxed = {b["track"] for b in blocks}
        new = text
        changed = False
        for b in reversed(file_blocks(text)):
            track = Engine._track_of_header(b["header"], index)
            if track is None or track in boxed or b["end"] <= b["start"]:
                continue
            if project.tracks[index[track]].is_audio or not text[b["start"]:b["end"]].strip():
                continue
            body = text[b["start"]:b["end"]]
            block = _box_header(track, name, 0) + "\n" + body
            new = new[:b["start"]] + "\n" + block + new[b["end"]:]
            changed = True
        if not changed:
            raise ValueError(tr("Tutte le tracce sono già divise in box."))
    else:
        raise ValueError(f"modifica sconosciuta: {op}")
    _check_overlaps(new)
    return {"text": new, "focus": focus}


def flat_spans(spans) -> list:
    """Gli span in una lista piatta di numeri, per un Float64Array in JS."""
    flat = []
    for s in spans:
        flat.extend(s)
    return flat


def analyze(text: str, name: str = "Brano", transpose: int = 0) -> dict:
    """Lettura, MIDI ed evidenziazione con i tempi di ciascuna fase."""
    engine = Engine()
    info = engine.load(text, name)
    midi = engine.midi_bytes(transpose)
    spans = engine.highlight_spans()
    return {"engine": engine, "info": info, "midi": midi, "spans": spans, "timings": dict(engine.timings)}


if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for path in sys.argv[1:]:
        with open(path, encoding="utf-8") as f:
            source = f.read()
        t0 = time.perf_counter()
        result = analyze(source, os.path.basename(path))
        total = time.perf_counter() - t0
        timings = ", ".join(f"{k} {v:.3f}" for k, v in result["timings"].items())
        print(f"{os.path.basename(path)}: totale {total:.3f} s ({timings}); "
              f"{len(result['info']['tracks'])} tracce, MIDI {len(result['midi'])} byte, "
              f"{len(result['spans'])} span")
