#!/usr/bin/env python3
"""Il pacchetto orchestra di SoundText Mobile: un SoundFont leggero costruito dalle librerie CC0 che SoundText
scarica gia' sul computer (VSCO 2 CE e VCSL, di Versilian Studios).

Per ogni strumento d'orchestra (archi, legni, ottoni, arpa, timpani, vibrafono...) legge il file .sfz, tiene pochi
campioni (una dinamica, una nota ogni tre circa), li porta a 32 kHz mono, li accorcia (con un anello per i suoni
tenuti) e li mette nel programma General MIDI corrispondente, cosi' i brani esistenti lo usano senza modifiche.
Gli altri programmi restano a TimGM6mb: il pacchetto si carica come SoundFont predefinito sopra di lui.

Il formato di uscita e' SF2 (non compresso) o, con --format sf3, SF3 (campioni Ogg Vorbis, 5-10 volte piu' leggero): il
FluidSynth in WebAssembly dell'app e' compilato con libsndfile e legge entrambi. L'app usa l'SF3.
Il risultato e' sempre lo stesso a parità di sorgenti (stesso SHA-256): niente date, ordine fisso, ffmpeg senza
metadati.

    python mobile/tools/costruisci_sf3.py --vsco CARTELLA/vsco --vcsl CARTELLA/vcsl --out orchestra.sf2
    python mobile/tools/costruisci_sf3.py --pacchetto elettrico --sorgenti ~/Strumenti/sfz --out elettrico.sf3 --format sf3

Le sorgenti si scaricano con scarica_strumenti.py (voci vsco-* e vcsl-*), o con scarica_orchestra() di quel file.
Servono ffmpeg e numpy.
"""

import argparse
import hashlib
import json
import math
import re
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sintesi   # noqa: E402  (i suoni generati: organo, fisarmonica, suoni elettronici)

RATE = 32000
NOTE_NAMES = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}

# programma General MIDI -> (nome, sorgente, file .sfz, tipo, dinamica)
#   tipo: "tenuto" (anello sulla coda), "pizz" (si spegne da solo), "colpo" (percussione che risuona)
INSTRUMENTS = [
    (6, "Harpsichord", "vcsl", "Chordophones/Zithers/Harpsichord, French.sfz", "pizz", 100),
    (9, "Glockenspiel", "vsco", "Glockenspiel.sfz", "colpo", 100),
    (11, "Vibraphone", "vcsl", "Idiophones/Struck Idiophones/Vibraphone - Soft Mallets.sfz", "colpo", 100),
    (12, "Marimba", "vsco", "Marimba.sfz", "colpo", 100),
    (13, "Xylophone", "vsco", "Xylophone.sfz", "colpo", 100),
    (14, "Tubular Bells", "vsco", "TubularBells.sfz", "colpo", 100),
    (40, "Violin", "vsco", "SViolinVib.sfz", "tenuto", 100),
    (41, "Viola", "vsco", "ViolaEnsSusVib.sfz", "tenuto", 100),
    (42, "Cello", "vsco", "CelloEnsSusVib.sfz", "tenuto", 100),
    (43, "Contrabass", "vsco", "ContrabassSusVB.sfz", "tenuto", 100),
    (44, "Tremolo Strings", "vsco", "ViolinEnsTrem.sfz", "tenuto", 100),
    (45, "Pizzicato Strings", "vsco", "ViolinEnsPizz.sfz", "pizz", 100),
    (46, "Orchestral Harp", "vsco", "Harp.sfz", "pizz", 100),
    (47, "Timpani", "vsco", "Timpani.sfz", "colpo", 100),
    (48, "String Ensemble 1", "vsco", "ViolinEnsSusVib.sfz", "tenuto", 100),
    (49, "String Ensemble 2", "vsco", "ViolaEnsSusVib.sfz", "tenuto", 100),
    (56, "Trumpet", "vsco", "TrumpetSusVib.sfz", "tenuto", 100),
    (57, "Trombone", "vsco", "TromboneSus.sfz", "tenuto", 100),
    (58, "Tuba", "vsco", "TubaSus.sfz", "tenuto", 100),
    (59, "Muted Trumpet", "vsco", "TrumpetStraightMuteSus.sfz", "tenuto", 100),
    (60, "French Horn", "vsco", "FHornSus.sfz", "tenuto", 100),
    (61, "Brass Section", "vsco", "FHornSus.sfz", "tenuto", 100),
    (68, "Oboe", "vsco", "OboeSusVib.sfz", "tenuto", 100),
    (70, "Bassoon", "vsco", "BassoonSus.sfz", "tenuto", 100),
    (71, "Clarinet", "vsco", "ClarinetSus.sfz", "tenuto", 100),
    (72, "Piccolo", "vsco", "PiccoloSus.sfz", "tenuto", 100),
    (73, "Flute", "vsco", "FluteSusVib.sfz", "tenuto", 100),
]

# lunghezza massima del campione (secondi), ogni quanti semitoni se ne tiene uno, rilascio (secondi), RMS di arrivo
KINDS = {
    "tenuto": {"seconds": 3.0, "gap": 3, "release": 0.45, "attack": 0.03},
    "pizz": {"seconds": 2.5, "gap": 3, "release": 0.6, "attack": 0.001},
    "colpo": {"seconds": 3.0, "gap": 3, "release": 0.8, "attack": 0.001},
}
TARGET_RMS = 0.2
# Ritocco del volume di ogni programma, in dB, misurato contro TimGM6mb con le stesse note e la stessa dinamica
# (renderizzando con FluidSynth una scala per strumento): il pacchetto suona alla pari con gli altri strumenti GM.
# Il tetto e' +9 dB: un campione non puo' superare il fondo scala.
GAIN_DB = {6: -6.5, 9: -9.5, 11: 10.5, 12: -9.5, 13: -14, 14: 2.5, 40: -1, 41: 3.5, 42: 5, 43: -5.5, 44: 2, 45: -1, 46: 0.5, 47: 1, 48: 0, 49: -3, 56: 3, 57: -4.5, 58: -3, 59: 2.5, 60: 1, 61: 8, 68: 5, 70: 2.5, 71: 1, 72: 5, 73: 11}


# ---------------------------------------------------------------------------
# SFZ
# ---------------------------------------------------------------------------

def note_number(value: str) -> int:
    value = value.strip().lower()
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    m = re.fullmatch(r"([a-g])([#b]?)(-?\d+)", value)
    if not m:
        raise ValueError(f"nota non valida: {value}")
    return NOTE_NAMES[m.group(1)] + (1 if m.group(2) == "#" else -1 if m.group(2) == "b" else 0) + 12 * (int(m.group(3)) + 1)


def preprocess(text: str, folder: Path | None = None, defines: dict | None = None, depth: int = 0) -> str:
    """I #define («#define $EXT flac») e i #include («#include "file.sfz"») di un .sfz: $NOME sostituito nel testo e nei percorsi
    dei #include, e ogni #include sostituito dal contenuto del file (relativo alla cartella di chi lo cita, barre rovesciate
    dei percorsi Windows comprese). Senza 'folder' si risolvono solo i #define."""
    defs = dict(defines or {})
    defs.update(re.findall(r"^\s*#define\s+(\$\w+)\s+(\S+)", text, re.M))
    text = re.sub(r"^\s*#define\b.*$", "", text, flags=re.M)
    for name in sorted(defs, key=len, reverse=True):
        text = text.replace(name, defs[name])
    if folder is None or depth > 6:
        return text

    def include(match):
        target = folder / match.group(1).replace("\\", "/")
        if not target.exists():
            return ""
        return preprocess(target.read_text(encoding="utf-8", errors="replace"), target.parent, defs, depth + 1)
    return re.sub(r'^\s*#include\s+"([^"]+)"', include, text, flags=re.M)


def expand_defines(text: str) -> str:
    return preprocess(text)


def parse_sfz(text: str, folder: Path | None = None) -> list:
    """Le regioni di un .sfz come dizionari di opcode, con quelli di <global>, <master> e <group> sommati (la regione
    vince). Si capiscono i #define e, se si da' la cartella del file, i #include."""
    return _inherit(preprocess(text, folder))


def _inherit(text: str) -> list:
    scopes = {"global": {}, "master": {}, "group": {}}
    current = None
    regions = []
    for line in text.splitlines():
        line = line.split("//")[0].strip()
        if not line:
            continue
        for part in re.split(r"(?=<\w+>)", line):
            part = part.strip()
            if not part:
                continue
            m = re.match(r"<(\w+)>(.*)$", part)
            if m:
                header, part = m.group(1), m.group(2).strip()
                if header == "control":
                    current = {}
                elif header in ("global", "master", "group"):
                    order = ["global", "master", "group"]
                    for inner in order[order.index(header):]:
                        scopes[inner] = {}
                    current = scopes[header]
                elif header == "region":
                    merged = {}
                    for scope in ("global", "master", "group"):
                        merged.update(scopes[scope])
                    current = {"__base": merged}
                    regions.append(current)
                else:
                    current = {}
            if not part or current is None:
                continue
            for item in re.split(r"\s+(?=\w+=)", part):
                if "=" in item:
                    key, value = item.split("=", 1)
                    current[key.strip()] = value.strip()
    final = []
    for r in regions:
        base = r.pop("__base")
        merged = dict(base)
        merged.update(r)
        final.append(merged)
    return final


def control_path(text: str) -> str:
    m = re.search(r"default_path\s*=\s*([^\n\r]*)", text.split("<region>")[0])
    return m.group(1).split("//")[0].strip().replace("\\", "/") if m else ""


def region_info(r: dict) -> dict | None:
    """key range, keycenter, velocita' di una regione; None se non e' una nota da tenere."""
    if "sample" not in r or r.get("trigger", "attack") != "attack" or r["sample"].startswith("*"):
        return None                                                  # (i campioni «*noise», «*sine»: oscillatori dell'SFZ, non file)
    if float(r.get("lorand", 0) or 0) > 0:
        return None                                                  # le altre alternanze
    seq = int(float(r.get("seq_position", 1)))
    if seq > 1:
        return None
    if "key" in r:
        lo = hi = center = note_number(r["key"])
    else:
        lo, hi = note_number(r.get("lokey", "0")), note_number(r.get("hikey", "127"))
        center = note_number(r["pitch_keycenter"]) if "pitch_keycenter" in r else lo
    if "pitch_keycenter" in r:
        center = note_number(r["pitch_keycenter"])
    return {"sample": r["sample"].replace("\\", "/"), "lo": lo, "hi": hi, "center": center,
            "lovel": int(float(r.get("lovel", 0))), "hivel": int(float(r.get("hivel", 127))),
            "tune": float(r.get("tune", 0) or 0), "offset": int(float(r.get("offset", 0) or 0)),
            "end": int(float(r["end"])) if "end" in r else None}


def find_sample(folder: Path, sfz_path: Path, sample: str) -> Path:
    """Il file di un campione: nella cartella di default_path, accanto all'.sfz, o (come nelle librerie Karoryfer, con gli
    .sfz in Programs/) in ../Samples/."""
    for candidate in (folder / sample, sfz_path.parent / sample, sfz_path.parent.parent / "Samples" / sample):
        if candidate.exists():
            return candidate
    return folder / sample


def synth_layers(spec: dict, rate: int, cfg: dict, kind: str = "tenuto") -> tuple:
    """I campioni di un suono generato (mobile/tools/sintesi.py): uno ogni 'passo' semitoni nell'estensione, con gli stessi
    confini a meta' strada e lo stesso anello dei campioni veri. Ritorna (regioni, campioni preparati)."""
    low, high = spec.get("estensione", [28, 100])
    step = int(spec.get("passo", 3))
    centers = list(range(low, high + 1, step))
    if centers[-1] != high:
        centers.append(high)
    layers, prepared = [], []
    for i, center in enumerate(centers):
        lo = max(0, center - 12) if i == 0 else (centers[i - 1] + center) // 2 + 1
        hi = min(127, center + 12) if i == len(centers) - 1 else (center + centers[i + 1]) // 2
        audio = sintesi.render(spec["tipo"], spec.get("parametri", {}), center, rate, float(cfg["seconds"]) + 0.5)
        layers.append({"sample": f"{spec['tipo']}{center}", "lo": lo, "hi": hi, "center": center, "lovel": 0, "hivel": 127,
                       "tune": 0.0, "offset": 0, "end": None})
        prepared.append(prepare(audio, kind, 0, rate, cfg))
    return layers, prepared


def pick_layers(regions: list, velocity: int) -> list:
    """Una regione per ogni nota di riferimento: quella la cui dinamica contiene 'velocity' (o la piu' vicina)."""
    by_center: dict = {}
    for r in regions:
        info = region_info(r)
        if info:
            by_center.setdefault(info["center"], []).append(info)
    picked = []
    for center in sorted(by_center):
        layers = by_center[center]
        inside = [l for l in layers if l["lovel"] <= velocity <= l["hivel"]]
        best = inside[0] if inside else min(layers, key=lambda l: min(abs(l["lovel"] - velocity), abs(l["hivel"] - velocity)))
        picked.append(best)
    return picked


def thin(picked: list, gap: int, extra: int = 12) -> list:
    """Una nota ogni 'gap' semitoni circa; i campioni tenuti coprono i tasti vicini. Il primo e l'ultimo restano."""
    if not picked:
        return []
    keep = [picked[0]]
    for p in picked[1:-1]:
        if p["center"] - keep[-1]["center"] >= gap:
            keep.append(p)
    if len(picked) > 1 and picked[-1]["center"] - keep[-1]["center"] >= 1:
        keep.append(picked[-1])
    low = max(0, min(p["lo"] for p in picked) - 12)                  # fuori dalla tessitura reale: un'ottava di campioni
    high = min(127, max(p["hi"] for p in picked) + extra)             # trasposti, meglio del silenzio
    bounds = []                                                       # i confini a meta' strada fra le note tenute
    for i, p in enumerate(keep):
        lo = low if i == 0 else bounds[-1][1] + 1
        hi = high if i == len(keep) - 1 else (p["center"] + keep[i + 1]["center"]) // 2
        bounds.append((lo, hi))
    return [dict(p, lo=lo, hi=hi) for p, (lo, hi) in zip(keep, bounds)]


# ---------------------------------------------------------------------------
# campioni
# ---------------------------------------------------------------------------

def decode(path: Path, rate: int = RATE) -> np.ndarray:
    """Il campione alla frequenza 'rate' (32 kHz di solito) in mono, int16 -> float32 [-1, 1]."""
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-map_metadata", "-1", "-ac", "1", "-ar", str(rate), "-f", "s16le", "pipe:1"]
    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0


def prepare(audio: np.ndarray, kind: str, offset_frames: int = 0, rate: int = RATE, cfg: dict | None = None) -> tuple:
    """(campione, inizio anello, fine anello) o (campione, None, None). Accorcia, toglie il silenzio iniziale,
    chiude con una dissolvenza; i suoni tenuti hanno un anello con il raccordo."""
    cfg = cfg or KINDS[kind]
    audio = audio[offset_frames:] if offset_frames else audio
    peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
    if peak <= 0:
        return audio[:rate // 10], None, None
    start = int(np.argmax(np.abs(audio) > peak * 0.02))                 # via il silenzio prima dell'attacco
    audio = audio[max(0, start - 16):]
    n = min(len(audio), int(cfg["seconds"] * rate))
    audio = audio[:n].copy()
    if kind == "tenuto" and n > int(1.4 * rate):
        a = int(0.45 * n)
        window = 512
        best, best_cost = int(0.93 * n), None
        target = audio[a:a + window]
        for end in range(int(0.85 * n), n - window - 1, 8):
            cost = float(np.sum((audio[end:end + window] - target) ** 2))
            if best_cost is None or cost < best_cost:
                best, best_cost = end, cost
        b = best
        fade = min(2400, a // 2, b - a)
        w = np.linspace(0.0, 1.0, fade, dtype=np.float32)
        audio[b - fade:b] = audio[b - fade:b] * (1 - w) + audio[a - fade:a] * w
        return audio[:b + window], a, b
    fade = min(int(0.35 * rate), n // 3)
    audio[n - fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)
    return audio, None, None


def soft_limit(x: np.ndarray, knee: float = 0.5) -> np.ndarray:
    """Uguale fino a 'knee', poi i picchi si schiacciano dolcemente verso 1 (tanh)."""
    a = np.abs(x)
    over = a > knee
    out = x.copy()
    out[over] = np.sign(x[over]) * (knee + (1 - knee) * np.tanh((a[over] - knee) / (1 - knee)))
    return out


# ---------------------------------------------------------------------------
# SoundFont 2
# ---------------------------------------------------------------------------

def chunk(tag: bytes, data: bytes) -> bytes:
    pad = b"\0" if len(data) % 2 else b""
    return tag + struct.pack("<I", len(data)) + data + pad


def lst(kind: bytes, *chunks: bytes) -> bytes:
    body = kind + b"".join(chunks)
    return chunk(b"LIST", body)


def zstr(text: str) -> bytes:
    """Una stringa dell'INFO: terminata da zero e di lunghezza pari (lo vuole la specifica, e FluidSynth lo controlla)."""
    data = text.encode("ascii", "replace") + b"\0"
    return data + (b"\0" if len(data) % 2 else b"")


def name20(s: str) -> bytes:
    return s.encode("ascii", "replace")[:19].ljust(20, b"\0")


def timecents(seconds: float) -> int:
    return int(round(1200 * math.log2(max(seconds, 0.001))))


def gen(op: int, amount) -> bytes:
    if isinstance(amount, tuple):
        return struct.pack("<HBB", op, amount[0], amount[1])
    return struct.pack("<Hh", op, int(amount))


class SoundFont:
    def __init__(self):
        self.samples = []          # (nome, int16, loop_a, loop_b, nota di origine, correzione in cent)
        self.instruments = []      # (nome, [zone: lista di (op, valore)])
        self.presets = []          # (nome, programma, indice dello strumento)

    def add_sample(self, name, pcm, loop_a, loop_b, key, cents, rate=RATE):
        self.samples.append((name, pcm, loop_a, loop_b, key, cents, rate))
        return len(self.samples) - 1

    def add_instrument(self, name, zones):
        self.instruments.append((name, zones))
        return len(self.instruments) - 1

    def add_preset(self, name, program, instrument, bank=0):
        self.presets.append((name, program, instrument, bank))

    def to_bytes(self, info: dict, compressed: list | None = None) -> bytes:
        smpl = bytearray()
        shdr = bytearray()
        for i, (name, pcm, la, lb, key, cents, rate) in enumerate(self.samples):
            if compressed is not None:                                    # SF3: i byte di Ogg Vorbis
                blob = compressed[i]
                start = len(smpl)
                smpl += blob
                end = len(smpl)
                loop_a, loop_b = (la or 0), (lb or 0)                     # nell'SF3 i cicli sono relativi al campione
                stype = 1 | 0x10
            else:
                start = len(smpl) // 2
                smpl += pcm.tobytes()
                end = len(smpl) // 2
                smpl += bytes(46 * 2)
                loop_a, loop_b = start + (la or 0), start + (lb or 0)
                stype = 1
            shdr += name20(name) + struct.pack("<IIIIIBbHH", start, end, loop_a, loop_b, rate, key, cents, 0, stype)
        shdr += name20("EOS") + struct.pack("<IIIIIBbHH", 0, 0, 0, 0, 0, 0, 0, 0, 0)

        igen, ibag, inst = bytearray(), bytearray(), bytearray()
        gen_index = 0
        bag_index = 0
        for name, zones in self.instruments:
            inst += name20(name) + struct.pack("<H", bag_index)
            for zone in zones:
                ibag += struct.pack("<HH", gen_index, 0)
                bag_index += 1
                for op, value in zone:
                    igen += gen(op, value)
                    gen_index += 1
        inst += name20("EOI") + struct.pack("<H", bag_index)
        ibag += struct.pack("<HH", gen_index, 0)
        igen += gen(0, 0)
        imod = bytes(10)

        pgen, pbag, phdr = bytearray(), bytearray(), bytearray()
        for i, (name, program, instrument, bank) in enumerate(self.presets):
            phdr += name20(name) + struct.pack("<HHHIII", program, bank, i, 0, 0, 0)
            pbag += struct.pack("<HH", i, 0)
            pgen += gen(41, instrument)
        phdr += name20("EOP") + struct.pack("<HHHIII", 0, 0, len(self.presets), 0, 0, 0)
        pbag += struct.pack("<HH", len(self.presets), 0)
        pgen += gen(0, 0)
        pmod = bytes(10)

        major = 3 if compressed is not None else 2
        info_chunks = [
            chunk(b"ifil", struct.pack("<HH", major, 1)),
            chunk(b"isng", b"EMU8000\0"),
            chunk(b"INAM", zstr(info["name"])),
            chunk(b"ICOP", zstr(info["copyright"])),
            chunk(b"ICMT", zstr(info["comment"])),
        ]
        pdta = lst(b"pdta", chunk(b"phdr", bytes(phdr)), chunk(b"pbag", bytes(pbag)), chunk(b"pmod", pmod),
                   chunk(b"pgen", bytes(pgen)), chunk(b"inst", bytes(inst)), chunk(b"ibag", bytes(ibag)),
                   chunk(b"imod", imod), chunk(b"igen", bytes(igen)), chunk(b"shdr", bytes(shdr)))
        body = b"sfbk" + lst(b"INFO", *info_chunks) + lst(b"sdta", chunk(b"smpl", bytes(smpl))) + pdta
        return chunk(b"RIFF", body)


def vorbis(pcm: np.ndarray, rate: int = RATE) -> bytes:
    cmd = ["ffmpeg", "-v", "error", "-f", "s16le", "-ar", str(rate), "-ac", "1", "-i", "pipe:0", "-map_metadata", "-1",
           "-fflags", "+bitexact", "-flags:a", "+bitexact", "-c:a", "libvorbis", "-q:a", "3", "-f", "ogg", "pipe:1"]
    return subprocess.run(cmd, input=pcm.tobytes(), check=True, capture_output=True).stdout


# ---------------------------------------------------------------------------
# i pacchetti: l'elenco degli strumenti sta in un file di dati (mobile/tools/pacchetti/NOME.json)
# ---------------------------------------------------------------------------

PACCHETTI = Path(__file__).resolve().parent / "pacchetti"

# La qualita' per classe di strumento (docs, sezione 2): frequenza, dinamiche (velocity dei livelli) e ogni quanti semitoni si
# tiene un campione. Un file di dati puo' cambiare ognuna di queste voci per uno strumento.
CLASSI = {
    "piano": {"frequenza": 44100, "dinamiche": [60, 110], "gap": 3},
    "corde": {"frequenza": 44100, "dinamiche": [60, 110], "gap": 4},
    "fiato": {"frequenza": 32000, "dinamiche": [100], "gap": 3},
    "organo": {"frequenza": 32000, "dinamiche": [100], "gap": 3},
}


def orchestra_spec(instruments: list | None = None) -> dict:
    """Il pacchetto orchestra, dalla tabella INSTRUMENTS (stessa qualita' di sempre: 32 kHz, una dinamica, una nota ogni tre)."""
    instruments = INSTRUMENTS if instruments is None else instruments
    return {"nome": "SoundText Orchestra", "copyright": "CC0 1.0: VSCO 2 CE e VCSL (Versilian Studios)",
            "commento": "Pacchetto orchestra di SoundText Mobile, costruito da mobile/tools/costruisci_sf3.py",
            "strumenti": [{"programma": p, "nome": n, "sorgente": src, "sfz": f, "tipo": k, "dinamiche": [v],
                           "frequenza": RATE, "gap": KINDS[k]["gap"], "guadagno_db": GAIN_DB.get(p, 0), "licenza": "CC0"}
                          for p, n, src, f, k, v in instruments]}


def completo_spec() -> dict:
    """Tutti gli strumenti in un solo SoundFont: l'orchestra e gli altri tre pacchetti, un solo strumento per programma (vale il
    primo, nell'ordine orchestra, acustico, elettrico, elettronico). Il ritocco di volume di ogni pacchetto passa agli strumenti."""
    entries, seen, titles = [], set(), []
    for name in ("orchestra", "acustico", "elettrico", "elettronico"):
        spec = orchestra_spec() if name == "orchestra" else json.loads((PACCHETTI / f"{name}.json").read_text(encoding="utf-8"))
        titles.append(spec["nome"].replace("SoundText ", ""))
        for entry in spec["strumenti"]:
            if entry["programma"] in seen:
                continue
            seen.add(entry["programma"])
            entries.append({**entry, "guadagno_db": entry.get("guadagno_db", 0) + spec.get("guadagno_pacchetto_db", 0), "pacchetto": name})
    return {"nome": "SoundText Completo", "titolo": "Tutti gli strumenti", "limite_mb": 25, "normalizza": True,
            "copyright": "CC0 1.0, pubblico dominio, CC BY 3.0 (Greg Sullivan, Wurlitzer EP200) e suoni generati",
            "commento": "Orchestra, acustico, elettrico ed elettronico di SoundText Mobile in un solo SoundFont, costruito da "
                        "mobile/tools/costruisci_sf3.py", "strumenti": entries}


def carica_pacchetto(nome: str) -> dict:
    if nome == "orchestra":
        return orchestra_spec()
    if nome == "completo":
        return completo_spec()
    return json.loads((PACCHETTI / f"{nome}.json").read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _velocity_bounds(velocities: list) -> list:
    """(lovel, hivel) di ogni livello: i confini a meta' strada fra le dinamiche scelte."""
    vs = sorted(velocities)
    cuts = [(a + b) // 2 for a, b in zip(vs, vs[1:])]
    lows = [0] + [c + 1 for c in cuts]
    highs = cuts + [127]
    return list(zip(lows, highs))


def add_kit(sf: "SoundFont", kit: dict, spec: dict, fmt: str, report: list, log=print) -> None:
    """Un kit di percussioni (banco 128): un campione per ogni nota General MIDI, suonato senza trasposizione. Il volume di
    ogni colpo e' il suo peso (sintesi.DRUM_LEVEL_DB) piu' il ritocco del kit, scritto come attenuazione come per gli strumenti.
    FluidSynth applica l'attenuazione dei campioni (generatore 48) con un fattore 0,4: per ottenere i dB voluti la si scrive 2,5 volte
    piu' grande (500 invece di 200 per il logaritmo)."""
    rate = int(kit.get("frequenza", RATE))
    zones, total, count = [], 0, 0
    for note in sorted(sintesi.DRUM_NOTES):
        family, hit = sintesi.drum_hit(note, rate)
        db = sintesi.DRUM_LEVEL_DB[family] + sintesi.DRUM_NOTE_DB.get(note, 0) + kit.get("guadagno_db", 0) + spec.get("guadagno_pacchetto_db", 0)
        scaled = hit * (10 ** (db / 20))
        peak = float(np.max(np.abs(scaled))) or 1.0
        boost = 0.98 / peak
        attenuation = max(0, min(1440, int(round(500 * math.log10(boost))))) if spec.get("normalizza", fmt == "sf3") else 0
        data = np.round((scaled * boost if attenuation else scaled) * 32767.0).astype("<i2")
        sid = sf.add_sample(f"{kit['nome'][:10]} {note}", data, None, None, note, 0, rate)
        zone = [(43, (note, note)), (34, timecents(0.001)), (38, timecents(0.08))]
        if attenuation:
            zone.append((48, attenuation))
        zone += [(56, 0), (58, note), (53, sid)]               # scaleTuning 0 e nota d'origine: il colpo non si trasporta
        zones.append(zone)
        total += len(data)
        count += 1
    inst = sf.add_instrument(kit["nome"], zones)
    sf.add_preset(kit["nome"], kit.get("programma", 0), inst, kit.get("banco", 128))
    report.append({"program": kit.get("programma", 0), "bank": kit.get("banco", 128), "name": kit["nome"], "samples": count,
                   "seconds": round(total / rate, 1), "pcm_bytes": total * 2, "license": "suono generato", "source": "sintesi",
                   "source_sha256": hashlib.sha256(Path(sintesi.__file__).read_bytes()).hexdigest()})
    log(f"  kit {kit['nome']:16s} {count:3d} colpi, {total / rate:5.1f} s")


def build(sources: dict, fmt: str = "sf2", log=print, spec: dict | None = None, limit_mb: float | None = None,
          instruments: list | None = None) -> tuple:
    """(byte del SoundFont, rapporto). 'sources' dice dove sta ogni sorgente (la chiave 'sorgente' di ogni strumento)."""
    spec = spec or orchestra_spec(instruments)
    sf = SoundFont()
    report = []
    cache: dict = {}
    sizes = {}
    for entry in sorted(spec["strumenti"], key=lambda e: (e["programma"], e["nome"])):
        program, name, source, kind = entry["programma"], entry["nome"], entry.get("sorgente", "sintesi"), entry["tipo"]
        sfz_name = entry.get("sfz", "")
        cls = {**CLASSI.get(entry.get("classe", ""), {}), **{k: entry[k] for k in ("frequenza", "dinamiche", "gap") if k in entry}}
        rate, velocities, gap = cls.get("frequenza", RATE), cls.get("dinamiche", [100]), cls.get("gap", KINDS[kind]["gap"])
        if "sintesi" in entry:
            sfz_path, sfz_name, regions, folder, source = None, entry["sintesi"]["tipo"], [], None, "sintesi"
        else:
            sfz_path = sources[source] / sfz_name
        text = sfz_path.read_text(encoding="utf-8", errors="replace") if sfz_path else ""
        if sfz_path:
            folder = sfz_path.parent / control_path(preprocess(text, sfz_path.parent))
            regions = parse_sfz(text, sfz_path.parent)
        cfg = {**KINDS[kind], **entry.get("parametri", {})}             # es. {"seconds": 0.5, "release": 0.15} per una chitarra stoppata
        bounds = _velocity_bounds(velocities)
        per_layer = []                       # per ogni dinamica: [(regione, campione preparato)]
        used = set()
        for vel in sorted(velocities):
            if "sintesi" in entry:
                layers, prepared = synth_layers(entry["sintesi"], rate, cfg, kind)
                if entry.get("saturazione"):
                    drive = float(entry["saturazione"])
                    prepared = [((np.tanh(drive * pcm) / np.tanh(drive)).astype(np.float32), a, b) for pcm, a, b in prepared]
                per_layer.append((layers, prepared))
                continue
            layers = thin(pick_layers(regions, vel), gap, int(entry.get("estendi_alto", 12)))
            if not layers:
                raise SystemExit(f"nessun campione in {sfz_path}")
            prepared = []
            for layer in layers:
                key = (str(folder), layer["sample"], kind, layer["offset"], rate, tuple(sorted(cfg.items())))
                if key not in cache:
                    wav = find_sample(folder, sfz_path, layer["sample"])
                    audio = decode(wav, rate)
                    if layer["end"]:
                        audio = audio[: int(layer["end"] * rate / 44100)]
                    cache[key] = prepare(audio, kind, int(layer["offset"] * rate / 44100), rate, cfg)
                    used.add(str(wav))
                pcm, loop_a, loop_b = cache[key]
                if entry.get("saturazione"):                              # chitarra pulita -> saturata (docs, sezione 4)
                    drive = float(entry["saturazione"])
                    pcm = (np.tanh(drive * pcm) / np.tanh(drive)).astype(np.float32)
                prepared.append((pcm, loop_a, loop_b))
            per_layer.append((layers, prepared))
        # il volume: lo stesso RMS per tutti gli strumenti, misurato sul primo secondo dei campioni di mezzo (di tutte le dinamiche)
        rms = []
        for _layers, prepared in per_layer:
            for pcm, _a, _b in prepared:
                seg = pcm[: rate]
                rms.append(float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0)
        level = float(np.median(rms)) or 1e-3
        scale = TARGET_RMS / level * 10 ** ((entry.get("guadagno_db", 0) + spec.get("guadagno_pacchetto_db", 0)) / 20)
        # (niente tetto sul picco: il limitatore dolce qui sotto schiaccia i picchi oltre 0,5, cosi' arpa e timpani,
        # che hanno picchi alti sul volume medio, arrivano al livello degli altri strumenti)
        zones, total = [], 0
        for (layers, prepared), (vlo, vhi) in zip(per_layer, bounds):
            for layer, (pcm, la, lb) in zip(layers, prepared):
                limited = soft_limit(pcm * scale)
                attenuation = 0
                if spec.get("normalizza", fmt == "sf3"):
                    # Il motore dell'app (FluidSynth in WebAssembly con libsndfile) porta ogni campione compresso (SF3) al fondo
                    # scala quando lo decomprime, qualunque livello gli si sia dato: il volume voluto si scrive allora come
                    # attenuazione della zona (generatore 48), e il campione sta gia' al fondo scala. Vale uguale in un motore
                    # che non normalizza.
                    peak = float(np.max(np.abs(limited))) or 1.0
                    boost = 0.98 / peak
                    limited = limited * boost
                    attenuation = max(0, min(1440, int(round(200 * math.log10(boost)))))
                data = np.round(limited * 32767.0).astype("<i2")
                cents = int(round(layer["tune"]))
                label = f"{name[:9]} v{vlo} {layer['center']}" if len(per_layer) > 1 else f"{name[:12]} {layer['center']}"
                sid = sf.add_sample(label, data, la, lb, layer["center"], max(-99, min(99, cents)), rate)
                zone = [(43, (layer["lo"], layer["hi"])), (44, (vlo, vhi)),
                        (34, timecents(cfg["attack"])), (38, timecents(cfg["release"]))]
                if attenuation:
                    zone.append((48, attenuation))
                if la is not None:
                    zone.append((54, 1))
                zone += [(53, sid)]
                zones.append(zone)
                total += len(pcm)
        inst = sf.add_instrument(name, zones)
        sf.add_preset(name, program, inst)
        seconds = total / rate
        n_samples = sum(len(layers) for layers, _p in per_layer)
        sizes[name] = total * 2 / (1 if fmt == "sf2" else 6)             # SF3: circa un sesto del PCM
        report.append({"program": program, "name": name, "samples": n_samples, "seconds": round(seconds, 1), "pcm_bytes": total * 2,
                       **({"license": entry["licenza"]} if "licenza" in entry else {}),
                       **({"attribution": entry["attribuzione"]} if "attribuzione" in entry else {}),
                       **({"source_sha256": _sha256_file(sfz_path), "source": f"{source}/{sfz_name}"} if sfz_path else
                          {"source": "sintesi", "source_sha256": hashlib.sha256(
                              (Path(sintesi.__file__).read_bytes() + json.dumps(entry["sintesi"], sort_keys=True).encode())).hexdigest()})})
        log(f"  {program:3d} {name:20s} {n_samples:3d} campioni, {seconds:5.1f} s")
    for kit in spec.get("kit", []):
        add_kit(sf, kit, spec, fmt, report, log)
    info = {"name": spec["nome"], "copyright": spec["copyright"], "comment": spec["commento"]}
    if fmt == "sf3":
        compressed = [vorbis(smp[1], smp[6]) for smp in sf.samples]
        data = sf.to_bytes(info, compressed)
    else:
        data = sf.to_bytes(info)
    if limit_mb and len(data) > limit_mb * 1e6:
        heaviest = sorted(sizes.items(), key=lambda kv: -kv[1])[:5]
        raise SystemExit(f"il pacchetto pesa {len(data) / 1e6:.1f} MB, oltre il limite di {limit_mb} MB; i piu' pesanti: " +
                         ", ".join(f"{n} (~{b / 1e6:.1f} MB)" for n, b in heaviest))
    return data, report


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--pacchetto", default="orchestra", help="orchestra, o il nome di un file di mobile/tools/pacchetti/")
    p.add_argument("--vsco", type=Path, help="cartella delle sorgenti VSCO 2 CE (pacchetto orchestra)")
    p.add_argument("--vcsl", type=Path, help="cartella delle sorgenti VCSL (pacchetto orchestra)")
    p.add_argument("--sorgenti", type=Path, help="la cartella di scarica_strumenti.py (una sottocartella per libreria)")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--format", choices=("sf2", "sf3"), default="sf2")
    p.add_argument("--limite-mb", type=float, help="si ferma se il pacchetto pesa di piu' (default: quello del file di dati)")
    args = p.parse_args()
    spec = carica_pacchetto(args.pacchetto)
    sources = {k: v for k, v in (("vsco", args.vsco), ("vcsl", args.vcsl), ("sorgenti", args.sorgenti)) if v}
    needed = {e["sorgente"] for e in spec["strumenti"] if "sorgente" in e}
    if args.pacchetto == "completo":
        needed = needed | {"vsco", "vcsl"}
    if needed - set(sources):
        raise SystemExit("mancano le cartelle delle sorgenti: " + ", ".join("--" + n for n in sorted(needed - set(sources))))
    data, report = build(sources, args.format, spec=spec, limit_mb=args.limite_mb or spec.get("limite_mb"))
    args.out.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    print(f"{args.out}: {len(data) / 1e6:.1f} MB, SHA-256 {digest}")
    args.out.with_suffix(args.out.suffix + ".json").write_text(
        json.dumps({"name": spec["nome"], "title": spec.get("titolo", spec["nome"]), "sha256": digest, "bytes": len(data),
                    "pcm_bytes": sum(r.get("pcm_bytes", 0) for r in report),
                    "instruments": report}, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    sys.exit(main())
