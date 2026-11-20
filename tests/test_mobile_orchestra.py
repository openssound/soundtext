"""Il pacchetto orchestra di SoundText Mobile (mobile/tools/costruisci_sf3.py): da .sfz e campioni sintetici si
ottiene un SoundFont 2 valido, con i programmi General MIDI giusti, sempre lo stesso a parita' di sorgenti."""
import hashlib
import importlib.util
import os
import shutil
import struct
import wave

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="serve ffmpeg")


def _tool():
    spec = importlib.util.spec_from_file_location("costruisci_sf3", os.path.join(ROOT, "mobile", "tools", "costruisci_sf3.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _wav(path, hz, seconds=2.0, rate=44100):
    t = np.arange(int(seconds * rate)) / rate
    data = (0.5 * np.sin(2 * np.pi * hz * t) * np.exp(-t * 0.4) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(data.tobytes())


def _library(tmp_path):
    """Una libreria finta: Flute.sfz con note ogni due semitoni (alternanze e due dinamiche), Harp.sfz."""
    src = tmp_path / "vsco"
    (src / "Strings" / "Harp").mkdir(parents=True)
    lines = ["<control>", "default_path=Strings\\Harp\\", "<global>", "ampeg_attack=0.001", "<group>"]
    for center in range(48, 73, 2):
        hz = 440 * 2 ** ((center - 69) / 12)
        for name, lo, hi in (("p", 0, 80), ("f", 81, 127)):
            _wav(src / "Strings" / "Harp" / f"H_{center}_{name}.wav", hz)
            lines += ["<region>", f"sample=H_{center}_{name}.wav", f"lokey={center}", f"hikey={center + 1}",
                      f"pitch_keycenter={center}", f"lovel={lo}", f"hivel={hi}"]
        _wav(src / "Strings" / "Harp" / f"H_{center}_rr.wav", hz)
        lines += ["<region>", f"sample=H_{center}_rr.wav", f"lokey={center}", f"hikey={center + 1}", f"pitch_keycenter={center}",
                  "lovel=81", "hivel=127", "seq_length=2", "seq_position=2"]
    (src / "Harp.sfz").write_text("\n".join(lines) + "\n")
    flute = ["<global>", "ampeg_release=0.3"] + sum(
        [["<region>", f"sample=F_{c}.wav", f"key={c}", f"lovel=0", "hivel=127"] for c in (60, 64, 67)], [])
    for c in (60, 64, 67):
        _wav(src / f"F_{c}.wav", 440 * 2 ** ((c - 69) / 12), seconds=4.0)
    (src / "Flute.sfz").write_text("\n".join(flute) + "\n")
    return {"vsco": src, "vcsl": src}


INSTRUMENTS = [(46, "Orchestral Harp", "vsco", "Harp.sfz", "pizz", 100), (73, "Flute", "vsco", "Flute.sfz", "tenuto", 100)]


def _riff(data):
    assert data[:4] == b"RIFF" and data[8:12] == b"sfbk"
    assert struct.unpack("<I", data[4:8])[0] == len(data) - 8
    out, at = {}, 12
    while at < len(data):
        tag, size = data[at:at + 4], struct.unpack("<I", data[at + 4:at + 8])[0]
        body = data[at + 8:at + 8 + size]
        if tag == b"LIST":
            at2, inner = 4, {}
            while at2 < len(body):
                t2, s2 = body[at2:at2 + 4], struct.unpack("<I", body[at2 + 4:at2 + 8])[0]
                inner[t2] = body[at2 + 8:at2 + 8 + s2]
                at2 += 8 + s2 + (s2 % 2)
            out[body[:4]] = inner
        at += 8 + size + (size % 2)
    return out


def test_a_valid_soundfont_with_the_right_programs(tmp_path):
    tool = _tool()
    data, report = tool.build(_library(tmp_path), instruments=INSTRUMENTS, log=lambda *_: None)
    sections = _riff(data)
    pdta = sections[b"pdta"]
    presets = pdta[b"phdr"]
    assert len(presets) // 38 == 3                                          # due programmi e il terminatore
    assert [struct.unpack("<H", presets[i * 38 + 20:i * 38 + 22])[0] for i in range(2)] == [46, 73]
    assert struct.unpack("<H", presets[20:22])[0] == 46 and presets[:15] == b"Orchestral Harp"
    shdr = pdta[b"shdr"]
    n = len(shdr) // 46 - 1
    smpl = sections[b"sdta"][b"smpl"]
    for i in range(n):
        start, end, ls, le, rate, key = struct.unpack("<IIIIIB", shdr[i * 46 + 20:i * 46 + 41])
        assert rate == 32000 and end > start and end * 2 + 92 <= len(smpl)
        assert ls == le or start <= ls < le <= end                          # l'anello sta dentro il campione
    # arpa: una dinamica e una sola alternanza, una nota ogni tre semitoni circa: molto meno dei 39 file
    harp = next(r for r in report if r["program"] == 46)
    assert 4 <= harp["samples"] <= 9, harp
    assert next(r for r in report if r["program"] == 73)["samples"] == 3
    # le zone coprono la tastiera senza buchi
    inst, ibag, igen = pdta[b"inst"], pdta[b"ibag"], pdta[b"igen"]
    zones = len(ibag) // 4 - 1
    ranges = []
    for z in range(zones):
        first = struct.unpack("<H", ibag[z * 4:z * 4 + 2])[0]
        lo, hi = struct.unpack("<BB", igen[first * 4 + 2:first * 4 + 4])
        assert struct.unpack("<H", igen[first * 4:first * 4 + 2])[0] == 43       # keyRange per primo
        ranges.append((lo, hi))
    flute_zones = ranges[-3:]
    assert flute_zones[0][0] == 48 and flute_zones[-1][1] == 79          # la tessitura reale piu' un'ottava per parte
    assert all(a[1] + 1 == b[0] for a, b in zip(flute_zones, flute_zones[1:]))


def test_the_flute_loops_and_the_harp_decays(tmp_path):
    tool = _tool()
    data, _ = tool.build(_library(tmp_path), instruments=INSTRUMENTS, log=lambda *_: None)
    shdr = _riff(data)[b"pdta"][b"shdr"]
    loops = []
    for i in range(len(shdr) // 46 - 1):
        start, end, ls, le = struct.unpack("<IIII", shdr[i * 46 + 20:i * 46 + 36])
        loops.append(le > ls)
    assert not any(loops[:-3]) and all(loops[-3:])


def test_same_sources_give_the_same_file(tmp_path):
    tool = _tool()
    lib = _library(tmp_path)
    one, _ = tool.build(lib, instruments=INSTRUMENTS, log=lambda *_: None)
    two, _ = tool.build(lib, instruments=INSTRUMENTS, log=lambda *_: None)
    assert hashlib.sha256(one).hexdigest() == hashlib.sha256(two).hexdigest()


def test_sf3_is_the_compressed_version(tmp_path):
    tool = _tool()
    lib = _library(tmp_path)
    plain, _ = tool.build(lib, instruments=INSTRUMENTS, log=lambda *_: None)
    packed, _ = tool.build(lib, fmt="sf3", instruments=INSTRUMENTS, log=lambda *_: None)
    assert len(packed) < len(plain) * 0.6
    assert b"OggS" in _riff(packed)[b"sdta"][b"smpl"][:8]


def test_sfz_opcodes_inherit_and_notes_have_names():
    tool = _tool()
    regions = tool.parse_sfz("<control>\ndefault_path=X\\\n<global>\nvolume=3\n<group>\nlovel=0 hivel=60\n<region>\nsample=a b.wav key=c4\n"
                             "<group>\nlovel=61 hivel=127\n<region>\nsample=c.wav lokey=c#4 hikey=e4 pitch_keycenter=d4\n")
    assert regions[0]["sample"] == "a b.wav" and regions[0]["volume"] == "3" and regions[0]["hivel"] == "60"
    assert regions[1]["lovel"] == "61"
    assert tool.note_number("c4") == 60 and tool.note_number("c#4") == 61 and tool.note_number("bb3") == 58
    info = tool.region_info(regions[1])
    assert (info["lo"], info["hi"], info["center"]) == (61, 64, 62)
