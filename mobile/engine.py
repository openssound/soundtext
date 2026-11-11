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
import re
import time
from typing import Dict, List, Optional, Tuple

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
        self.text = text
        self.timings = {"parse_s": time.perf_counter() - t0}
        tracks = [{"name": t.name, "instrument": t.instrument_name,
                   "percussion": bool(t.instrument.is_percussion)}
                  for t in self.project.tracks if not t.is_audio]
        return {"name": name, "tracks": tracks, "bpm": self.project.tempo_bpm}

    # ------------------------------------------------------------ MIDI

    def midi_bytes(self, transpose: int = 0) -> bytes:
        """Il brano in MIDI, con le note non percussive trasposte di
        'transpose' semitoni.

        La trasposizione si fa sulle note del MIDI e non con transpose=N
        davanti al testo delle tracce: i box degli esempi cominciano con
        reset: e hanno un loro transpose= (es. il sax di jazz_aaba.st,
        un'ottava sotto), che annullerebbero quello aggiunto. Le percussioni
        stanno sempre sul canale 10 (st_language.midi._assign_channels) e
        non si toccano. L'esportazione si fa una volta sola per brano."""
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
        if not transpose:
            return self._midi
        import mido
        from st_language.instruments import DRUM_MIDI_CHANNEL
        t0 = time.perf_counter()
        mid = mido.MidiFile(file=io.BytesIO(self._midi))
        for track in mid.tracks:
            for i, msg in enumerate(track):
                if msg.type in ("note_on", "note_off", "polytouch") and msg.channel != DRUM_MIDI_CHANNEL:
                    track[i] = msg.copy(note=min(127, max(0, msg.note + int(transpose))))
        out = io.BytesIO()
        mid.save(file=out)
        self.timings["transpose_s"] = time.perf_counter() - t0
        return out.getvalue()

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
                warn(hstart, hend, "ignored", f"Il box è della traccia «{track_name}», che nel brano non c'è.")
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
            message = f"«{header}» viene ignorato: «{instrument}» non è uno strumento noto."
            suggestion = suggest_instrument(instrument)
            if suggestion:
                message += f" Forse intendevi «{suggestion}»?"
            warn(hstart, hend, "ignored", message)

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
        out.append({"call": f".{name}({','.join(args)})" if args else f".{name}", "help": t["help"]})
    return out


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
