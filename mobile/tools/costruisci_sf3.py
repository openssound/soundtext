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


def parse_sfz(text: str) -> list:
    """Le regioni di un .sfz come dizionari di opcode, con quelli di <global>, <master> e <group> sommati (la regione
    vince). Le librerie dell'orchestra non usano #include ne' #define."""
    return _inherit(text)


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
    if "sample" not in r or r.get("trigger", "attack") != "attack":
        return None
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


def thin(picked: list, gap: int) -> list:
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
    high = min(127, max(p["hi"] for p in picked) + 12)                # trasposti, meglio del silenzio
    bounds = []                                                       # i confini a meta' strada fra le note tenute
    for i, p in enumerate(keep):
        lo = low if i == 0 else bounds[-1][1] + 1
        hi = high if i == len(keep) - 1 else (p["center"] + keep[i + 1]["center"]) // 2
        bounds.append((lo, hi))
    return [dict(p, lo=lo, hi=hi) for p, (lo, hi) in zip(keep, bounds)]


# ---------------------------------------------------------------------------
# campioni
# ---------------------------------------------------------------------------

def decode(path: Path) -> np.ndarray:
    """Il campione a 32 kHz mono, int16 -> float32 [-1, 1]."""
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-map_metadata", "-1", "-ac", "1", "-ar", str(RATE), "-f", "s16le", "pipe:1"]
    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0


def prepare(audio: np.ndarray, kind: str, offset_frames: int = 0) -> tuple:
    """(campione, inizio anello, fine anello) o (campione, None, None). Accorcia, toglie il silenzio iniziale,
    chiude con una dissolvenza; i suoni tenuti hanno un anello con il raccordo."""
    cfg = KINDS[kind]
    audio = audio[offset_frames:] if offset_frames else audio
    peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
    if peak <= 0:
        return audio[:RATE // 10], None, None
    start = int(np.argmax(np.abs(audio) > peak * 0.02))                 # via il silenzio prima dell'attacco
    audio = audio[max(0, start - 16):]
    n = min(len(audio), int(cfg["seconds"] * RATE))
    audio = audio[:n].copy()
    if kind == "tenuto" and n > int(1.4 * RATE):
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
    fade = min(int(0.35 * RATE), n // 3)
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

    def add_sample(self, name, pcm, loop_a, loop_b, key, cents):
        self.samples.append((name, pcm, loop_a, loop_b, key, cents))
        return len(self.samples) - 1

    def add_instrument(self, name, zones):
        self.instruments.append((name, zones))
        return len(self.instruments) - 1

    def add_preset(self, name, program, instrument):
        self.presets.append((name, program, instrument))

    def to_bytes(self, info: dict, compressed: list | None = None) -> bytes:
        smpl = bytearray()
        shdr = bytearray()
        for i, (name, pcm, la, lb, key, cents) in enumerate(self.samples):
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
            shdr += name20(name) + struct.pack("<IIIIIBbHH", start, end, loop_a, loop_b, RATE, key, cents, 0, stype)
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
        for i, (name, program, instrument) in enumerate(self.presets):
            phdr += name20(name) + struct.pack("<HHHIII", program, 0, i, 0, 0, 0)
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


def vorbis(pcm: np.ndarray) -> bytes:
    cmd = ["ffmpeg", "-v", "error", "-f", "s16le", "-ar", str(RATE), "-ac", "1", "-i", "pipe:0", "-map_metadata", "-1",
           "-fflags", "+bitexact", "-flags:a", "+bitexact", "-c:a", "libvorbis", "-q:a", "3", "-f", "ogg", "pipe:1"]
    return subprocess.run(cmd, input=pcm.tobytes(), check=True, capture_output=True).stdout


# ---------------------------------------------------------------------------
# la costruzione
# ---------------------------------------------------------------------------

def build(sources: dict, fmt: str = "sf2", log=print, instruments: list | None = None) -> tuple:
    sf = SoundFont()
    report = []
    cache: dict = {}
    for program, name, source, sfz_name, kind, velocity in sorted(instruments or INSTRUMENTS):
        sfz_path = sources[source] / sfz_name
        text = sfz_path.read_text(encoding="utf-8", errors="replace")
        folder = sfz_path.parent / control_path(text)
        layers = thin(pick_layers(parse_sfz(text), velocity), KINDS[kind]["gap"])
        if not layers:
            raise SystemExit(f"nessun campione in {sfz_path}")
        cfg = KINDS[kind]
        prepared = []
        for layer in layers:
            key = (str(folder), layer["sample"], kind, layer["offset"])
            if key not in cache:
                wav = (folder / layer["sample"]) if (folder / layer["sample"]).exists() else sfz_path.parent / layer["sample"]
                audio = decode(wav)
                if layer["end"]:
                    audio = audio[: int(layer["end"] * RATE / 44100)]
                cache[key] = prepare(audio, kind, int(layer["offset"] * RATE / 44100))
            prepared.append(cache[key])
        # il volume: lo stesso RMS per tutti gli strumenti, misurato sul primo secondo dei campioni di mezzo
        rms = []
        for pcm, _a, _b in prepared:
            seg = pcm[: RATE]
            rms.append(float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0)
        level = float(np.median(rms)) or 1e-3
        scale = TARGET_RMS / level * 10 ** (GAIN_DB.get(program, 0) / 20)
        # (niente tetto sul picco: il limitatore dolce qui sotto schiaccia i picchi oltre 0,5, cosi' arpa e timpani,
        # che hanno picchi alti sul volume medio, arrivano al livello degli altri strumenti)
        zones = []
        for layer, (pcm, la, lb) in zip(layers, prepared):
            data = np.round(soft_limit(pcm * scale) * 32767.0).astype("<i2")
            cents = int(round(layer["tune"]))
            sid = sf.add_sample(f"{name[:12]} {layer['center']}", data, la, lb, layer["center"], max(-99, min(99, cents)))
            zone = [(43, (layer["lo"], layer["hi"])), (44, (0, 127)),
                    (34, timecents(cfg["attack"])), (38, timecents(cfg["release"]))]
            if la is not None:
                zone.append((54, 1))
            zone += [(53, sid)]
            zones.append(zone)
        inst = sf.add_instrument(name, zones)
        sf.add_preset(name, program, inst)
        seconds = sum(len(p) for p, _a, _b in prepared) / RATE
        report.append({"program": program, "name": name, "samples": len(layers), "seconds": round(seconds, 1)})
        log(f"  {program:3d} {name:20s} {len(layers):3d} campioni, {seconds:5.1f} s")
    info = {"name": "SoundText Orchestra", "copyright": "CC0 1.0: VSCO 2 CE e VCSL (Versilian Studios)",
            "comment": "Pacchetto orchestra di SoundText Mobile, costruito da mobile/tools/costruisci_sf3.py"}
    if fmt == "sf3":
        compressed = [vorbis(pcm) for _n, pcm, *_rest in sf.samples]
        return sf.to_bytes(info, compressed), report
    return sf.to_bytes(info), report


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--vsco", type=Path, required=True, help="cartella delle sorgenti VSCO 2 CE")
    p.add_argument("--vcsl", type=Path, required=True, help="cartella delle sorgenti VCSL")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--format", choices=("sf2", "sf3"), default="sf2")
    args = p.parse_args()
    data, report = build({"vsco": args.vsco, "vcsl": args.vcsl}, args.format)
    args.out.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    print(f"{args.out}: {len(data) / 1e6:.1f} MB, SHA-256 {digest}")
    args.out.with_suffix(args.out.suffix + ".json").write_text(
        json.dumps({"sha256": digest, "bytes": len(data), "instruments": report}, indent=1) + "\n")


if __name__ == "__main__":
    sys.exit(main())
