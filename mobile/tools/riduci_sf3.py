#!/usr/bin/env python3
"""Riduce un SoundFont SF3 a un sottoinsieme di strumenti: la «base» di SoundText Mobile, ricavata da MuseScore General (MIT).

MuseScore General (38 MB, 310 preset) suona molto meglio di TimGM6mb (6 MB), ma caricarlo tutto costa nell'app piu' di 8 secondi.
Questo script tiene solo i programmi General MIDI che SoundText usa davvero (e alcuni kit di batteria), senza ricodificare i
campioni (restano i byte Ogg Vorbis dell'originale), li risistema in un SF3 nuovo con gli indici rimappati e, se serve, ritocca
il volume di ogni programma. La base si carica SOTTO i pacchetti e SOPRA TimGM6mb, che resta come riserva per i programmi
che non contiene (i pianoforti, per esempio: quello buono e' nel pacchetto acustico).

    python mobile/tools/riduci_sf3.py --in MuseScore_General.sf3 --out soundtext-base.sf3
    python mobile/tools/riduci_sf3.py --in MuseScore_General.sf3 --out base.sf3 --elenco programmi.json   # un altro elenco

Il file di dati (mobile/tools/pacchetti/base.json) dice quali programmi (banco 0) e quali kit (banco 128) tenere e, per ogni
programma, il ritocco in dB; il risultato e' sempre lo stesso a parita' di sorgente.
"""

import argparse
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from costruisci_sf3 import chunk, lst, name20, zstr   # noqa: E402

DATI = Path(__file__).resolve().parent / "pacchetti" / "base.json"


def _chunks(data: bytes, start: int, end: int, out: dict) -> None:
    pos = start
    while pos < end:
        tag = data[pos:pos + 4]
        size = struct.unpack("<I", data[pos + 4:pos + 8])[0]
        if tag == b"LIST":
            sub: dict = {}
            _chunks(data, pos + 12, pos + 8 + size, sub)
            out[data[pos + 8:pos + 12]] = sub
        else:
            out[tag] = (pos + 8, size)
        pos += 8 + size + (size & 1)


def _records(data: bytes, loc: tuple, fmt: str) -> list:
    off, size = loc
    n = struct.calcsize(fmt)
    return [struct.unpack(fmt, data[off + i * n:off + (i + 1) * n]) for i in range(size // n)]


class SoundFont:
    """Un SoundFont letto: preset, strumenti, campioni (con i loro byte)."""

    def __init__(self, path: Path):
        self.data = path.read_bytes()
        if self.data[:4] != b"RIFF" or self.data[8:12] != b"sfbk":
            raise SystemExit(f"{path}: non e' un SoundFont")
        tree: dict = {}
        _chunks(self.data, 12, len(self.data), tree)
        pdta, info, sdta = tree[b"pdta"], tree[b"INFO"], tree[b"sdta"]
        self.info = info
        self.compressed = struct.unpack("<HH", self.data[info[b"ifil"][0]:info[b"ifil"][0] + 4])[0] >= 3
        if not self.compressed:
            raise SystemExit("serve un SF3 (campioni Ogg Vorbis): la riduzione non ricodifica i campioni")
        self.smpl_at = sdta[b"smpl"][0]
        self.phdr = _records(self.data, pdta[b"phdr"], "<20sHHHIII")
        self.pbag = _records(self.data, pdta[b"pbag"], "<HH")
        self.pmod = _records(self.data, pdta[b"pmod"], "<10s")
        self.pgen = _records(self.data, pdta[b"pgen"], "<H2s")
        self.inst = _records(self.data, pdta[b"inst"], "<20sH")
        self.ibag = _records(self.data, pdta[b"ibag"], "<HH")
        self.imod = _records(self.data, pdta[b"imod"], "<10s")
        self.igen = _records(self.data, pdta[b"igen"], "<H2s")
        self.shdr = _records(self.data, pdta[b"shdr"], "<20sIIIIIBbHH")

    def preset_index(self, bank: int, program: int):
        for i, h in enumerate(self.phdr[:-1]):
            if h[2] == bank and h[1] == program:
                return i
        return None

    def zones(self, bags, gens, mods, first_bag, last_bag):
        """[(generatori, modulatori)] delle zone da first_bag a last_bag (esclusa)."""
        zones = []
        for b in range(first_bag, last_bag):
            g0, g1 = bags[b][0], bags[b + 1][0]
            m0, m1 = bags[b][1], bags[b + 1][1]
            zones.append(([(op, amount) for op, amount in gens[g0:g1]], [m[0] for m in mods[m0:m1]]))
        return zones


def reduce_soundfont(src: SoundFont, wanted: list, gains: dict, name: str, comment: str) -> bytes:
    """wanted: [(banco, programma)]; gains: {"banco/programma": dB}."""
    presets = []                     # (nome, programma, banco, zone)
    for bank, program in wanted:
        i = src.preset_index(bank, program)
        if i is None:
            raise SystemExit(f"nel SoundFont non c'e' il preset {bank}/{program}")
        h = src.phdr[i]
        presets.append((h[0], h[1], h[2], src.zones(src.pbag, src.pgen, src.pmod, h[3], src.phdr[i + 1][3]), (bank, program)))

    inst_map: dict = {}              # strumento vecchio -> nuovo
    smp_map: dict = {}               # campione vecchio -> nuovo
    inst_out = []                    # (nome, zone)

    def take_sample(old: int) -> int:
        if old not in smp_map:
            smp_map[old] = len(smp_map)
            link = src.shdr[old][8]
            if src.shdr[old][9] & (2 | 4 | 8) and link and link < len(src.shdr) - 1:   # stereo: l'altro canale viene con lui
                take_sample(link)
        return smp_map[old]

    def take_instrument(old: int) -> int:
        if old in inst_map:
            return inst_map[old]
        zones = []
        for gens, mods in src.zones(src.ibag, src.igen, src.imod, src.inst[old][1], src.inst[old + 1][1]):
            new_gens = []
            for op, amount in gens:
                if op == 53:
                    amount = struct.pack("<H", take_sample(struct.unpack("<H", amount)[0]))
                new_gens.append((op, amount))
            zones.append((new_gens, mods))
        inst_map[old] = len(inst_out)
        inst_out.append((src.inst[old][0], zones))
        return inst_map[old]

    new_presets = []
    for pname, program, bank, zones, key in presets:
        db = float(gains.get(f"{key[0]}/{key[1]}", gains.get("tutti", 0.0)))
        cb = int(round(db * -25))              # FluidSynth applica l'attenuazione con un fattore 0,4: 25 cB per dB (e non 10) ottengono quello voluto
        new_zones = []
        has_global = bool(zones) and not any(op == 41 for op, _a in zones[0][0])     # la prima zona senza strumento vale per tutte
        for n_zone, (gens, mods) in enumerate(zones):
            new_gens = []
            for op, amount in gens:
                if op == 41:
                    amount = struct.pack("<H", take_instrument(struct.unpack("<H", amount)[0]))
                new_gens.append((op, amount))
            is_global = has_global and n_zone == 0
            if cb and (is_global or any(op == 41 for op, _a in new_gens)):
                # Un generatore di una zona del preset si somma a quello dello strumento, e quello della zona sostituisce quello della
                # zona globale: il ritocco di volume va sommato a ogni attenuazione gia' scritta e, se manca, messo dove vale per tutti
                # (nella zona globale se c'e', se no in ogni zona).
                at = [k for k, (op, _a) in enumerate(new_gens) if op == 48]
                if at:
                    new_gens[at[0]] = (48, struct.pack("<h", struct.unpack("<h", new_gens[at[0]][1])[0] + cb))
                elif is_global:
                    new_gens.append((48, struct.pack("<h", cb)))
                elif not has_global:
                    new_gens.insert(len(new_gens) - 1, (48, struct.pack("<h", cb)))
            new_zones.append((new_gens, mods))
        new_presets.append((pname, program, bank, new_zones))

    # i campioni nell'ordine nuovo
    order = sorted(smp_map, key=lambda old: smp_map[old])
    smpl = bytearray()
    shdr = bytearray()
    for old in order:
        n, start, end, loop_a, loop_b, rate, pitch, corr, link, typ = src.shdr[old]
        blob = src.data[src.smpl_at + start:src.smpl_at + end]
        s0 = len(smpl)
        smpl += blob
        new_link = smp_map.get(link, 0) if (typ & (2 | 4 | 8) and link) else 0
        shdr += struct.pack("<20sIIIIIBbHH", n, s0, len(smpl), loop_a, loop_b, rate, pitch, corr, new_link, typ)
    shdr += name20("EOS") + struct.pack("<IIIIIBbHH", 0, 0, 0, 0, 0, 0, 0, 0, 0)

    def write_zones(entries, bag_b, gen_b, mod_b, head, tail_name):
        """Scrive i bag/gen/mod di un elenco [(nome, parametri..., zone)]; ritorna anche la testata."""
        bag_i = gen_i = mod_i = 0
        for entry_head, zones in entries:
            head += entry_head(bag_i)
            for gens, mods in zones:
                bag_b += struct.pack("<HH", gen_i, mod_i)
                bag_i += 1
                for op, amount in gens:
                    gen_b += struct.pack("<H", op) + amount
                    gen_i += 1
                for m in mods:
                    mod_b += m
                    mod_i += 1
        bag_b += struct.pack("<HH", gen_i, mod_i)
        gen_b += struct.pack("<H", 0) + b"\0\0"
        mod_b += bytes(10)
        return bag_i

    pbag, pgen, pmod, phdr = bytearray(), bytearray(), bytearray(), bytearray()
    entries = [(lambda bag_i, p=p: name20(p[0].rstrip(b"\0").decode("ascii", "replace")) + struct.pack("<HHHIII", p[1], p[2], bag_i, 0, 0, 0), p[3])
               for p in new_presets]
    n_bags = write_zones(entries, pbag, pgen, pmod, phdr, "EOP")
    phdr += name20("EOP") + struct.pack("<HHHIII", 0, 0, n_bags, 0, 0, 0)

    ibag, igen, imod, inst = bytearray(), bytearray(), bytearray(), bytearray()
    entries = [(lambda bag_i, n=n: name20(n.rstrip(b"\0").decode("ascii", "replace")) + struct.pack("<H", bag_i), z) for n, z in inst_out]
    n_ibags = write_zones(entries, ibag, igen, imod, inst, "EOI")
    inst += name20("EOI") + struct.pack("<H", n_ibags)

    copyright = src.data[src.info[b"ICOP"][0]:src.info[b"ICOP"][0] + src.info[b"ICOP"][1]].split(b"\0")[0].decode("ascii", "replace")
    info = [chunk(b"ifil", struct.pack("<HH", 3, 1)), chunk(b"isng", b"EMU8000\0"), chunk(b"INAM", zstr(name)),
            chunk(b"ICOP", zstr(copyright)), chunk(b"ICMT", zstr(comment))]
    pdta = lst(b"pdta", chunk(b"phdr", bytes(phdr)), chunk(b"pbag", bytes(pbag)), chunk(b"pmod", bytes(pmod)), chunk(b"pgen", bytes(pgen)),
               chunk(b"inst", bytes(inst)), chunk(b"ibag", bytes(ibag)), chunk(b"imod", bytes(imod)), chunk(b"igen", bytes(igen)),
               chunk(b"shdr", bytes(shdr)))
    body = b"sfbk" + lst(b"INFO", *info) + lst(b"sdta", chunk(b"smpl", bytes(smpl))) + pdta
    return chunk(b"RIFF", body)


def wanted_from(spec: dict) -> list:
    return [(0, p) for p in spec["programmi"]] + [(128, k) for k in spec.get("batterie", [])]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--in", dest="source", type=Path, required=True, help="MuseScore_General.sf3")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--elenco", type=Path, default=DATI, help="il file di dati (default: mobile/tools/pacchetti/base.json)")
    args = ap.parse_args()
    spec = json.loads(args.elenco.read_text(encoding="utf-8"))
    src = SoundFont(args.source)
    data = reduce_soundfont(src, wanted_from(spec), spec.get("guadagni_db", {}), spec["nome"], spec["commento"])
    limit = spec.get("limite_mb")
    if limit and len(data) > limit * 1e6:
        raise SystemExit(f"la base pesa {len(data) / 1e6:.1f} MB, oltre il limite di {limit} MB")
    args.out.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    print(f"{args.out}: {len(data) / 1e6:.1f} MB, SHA-256 {digest}")
    args.out.with_suffix(args.out.suffix + ".json").write_text(json.dumps(
        {"name": spec["nome"], "title": spec.get("titolo", spec["nome"]), "sha256": digest, "bytes": len(data),
         "source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(), "programs": spec["programmi"], "kits": spec.get("batterie", [])},
        indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    sys.exit(main())
