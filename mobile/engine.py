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
                current = {"header": stripped, "start": pos + len(line), "end": pos + len(line)}
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
            path = "/tmp/_soundtext_mobile.mid"
            export_project_to_midi(self.project, path)
            with open(path, "rb") as f:
                self._midi = f.read()
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
