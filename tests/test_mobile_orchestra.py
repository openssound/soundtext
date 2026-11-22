"""Il pacchetto orchestra di SoundText Mobile (mobile/tools/costruisci_sf3.py): da .sfz e campioni sintetici si
ottiene un SoundFont 2 valido, con i programmi General MIDI giusti, sempre lo stesso a parita' di sorgenti."""
import hashlib
import json
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
        [["<region>", f"sample=F_{c}.wav", f"key={c}", "lovel=0", "hivel=127"] for c in (60, 64, 67)], [])
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
    ibag, igen = pdta[b"ibag"], pdta[b"igen"]
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


# ---------------------------------------------------------------------------
# i pacchetti da file di dati (mobile/tools/pacchetti/*.json)
# ---------------------------------------------------------------------------

def _samples(data):
    """[(nome, frequenza)] dall'shdr di un SoundFont 2."""
    i = data.index(b"shdr")
    size = struct.unpack("<I", data[i + 4:i + 8])[0]
    out = []
    for off in range(i + 8, i + 8 + size - 46, 46):
        name = data[off:off + 20].split(b"\0")[0].decode()
        rate = struct.unpack("<I", data[off + 36:off + 40])[0]
        out.append((name, rate))
    return out


def _spec(**entry):
    base = {"programma": 46, "nome": "Piano", "sorgente": "sorgenti", "sfz": "Harp.sfz", "tipo": "pizz"}
    base.update(entry)
    return {"nome": "Prova", "copyright": "CC0", "commento": "prova", "strumenti": [base]}


def test_two_dynamics_make_two_velocity_layers_at_the_chosen_rate(tmp_path):
    tool = _tool()
    sources = {"sorgenti": _library(tmp_path)["vsco"]}
    data, report = tool.build(sources, "sf2", log=lambda *_: None, spec=_spec(dinamiche=[40, 110], frequenza=44100, classe="piano"))
    names = _samples(data)
    assert any(" v0 " in n for n, _r in names) and any(" v76 " in n for n, _r in names)          # due livelli, confine a meta' strada
    assert {r for _n, r in names} == {44100}
    one, _ = tool.build(sources, "sf2", log=lambda *_: None, spec=_spec(dinamiche=[100], frequenza=32000))
    assert {r for _n, r in _samples(one)} == {32000} and len(_samples(one)) < len(names)


def test_defines_in_an_sfz_are_expanded():
    tool = _tool()
    text = "#define $EXT flac\n<region>\nsample=a1.$EXT key=60\n"
    assert tool.parse_sfz(text)[0]["sample"] == "a1.flac"
    assert "#define" not in tool.expand_defines(text)


def test_saturation_makes_the_samples_louder_and_flatter(tmp_path):
    tool = _tool()
    sources = {"sorgenti": _library(tmp_path)["vsco"]}
    clean, _ = tool.build(sources, "sf2", log=lambda *_: None, spec=_spec())
    driven, _ = tool.build(sources, "sf2", log=lambda *_: None, spec=_spec(saturazione=6.0))
    assert clean != driven and len(clean) == len(driven)


def test_the_weight_limit_stops_the_build_and_names_the_heaviest_instruments(tmp_path):
    tool = _tool()
    sources = {"sorgenti": _library(tmp_path)["vsco"]}
    with pytest.raises(SystemExit) as stop:
        tool.build(sources, "sf2", log=lambda *_: None, spec=_spec(), limit_mb=0.001)
    assert "limite" in str(stop.value) and "Piano" in str(stop.value)


def test_the_electric_package_file_lists_valid_general_midi_programs():
    import json
    spec = json.load(open(os.path.join(ROOT, "mobile", "tools", "pacchetti", "elettrico.json"), encoding="utf-8"))
    programs = [e["programma"] for e in spec["strumenti"]]
    assert len(programs) == len(set(programs)) and all(0 <= p <= 127 for p in programs)
    assert {4, 5, 27, 30, 33, 34} <= set(programs)
    assert all(e.get("licenza") for e in spec["strumenti"])                           # ogni strumento dichiara la licenza
    assert all(e.get("sorgente") == "sorgenti" or "sintesi" in e for e in spec["strumenti"]) and spec["limite_mb"] <= 25
    tool = _tool()
    assert all(e["classe"] in tool.CLASSI for e in spec["strumenti"])


def test_a_synthesized_instrument_builds_the_same_every_time_and_covers_the_range(tmp_path):
    tool = _tool()
    spec = {"nome": "Prova", "copyright": "x", "commento": "x", "strumenti": [
        {"programma": 16, "nome": "Organ", "tipo": "tenuto", "classe": "organo", "frequenza": 32000,
         "sintesi": {"tipo": "organo", "parametri": {"registri": [8, 8, 8, 0, 0, 0, 0, 0, 0]}, "estensione": [48, 72], "passo": 6}},
        {"programma": 39, "nome": "808", "tipo": "colpo", "classe": "organo", "frequenza": 32000,
         "sintesi": {"tipo": "basso_808", "parametri": {}, "estensione": [30, 42], "passo": 6}}]}
    one, report = tool.build({}, "sf2", log=lambda *_: None, spec=spec)
    two, _ = tool.build({}, "sf2", log=lambda *_: None, spec=spec)
    assert one == two and report[0]["source"] == "sintesi" and report[0]["samples"] == 5
    assert len(_samples(one)) == 5 + 3                                       # 48,54,60,66,72 e 30,36,42


def test_synthesis_gives_the_right_pitch_and_is_not_silent():
    import importlib.util
    spec = importlib.util.spec_from_file_location("sintesi", os.path.join(ROOT, "mobile", "tools", "sintesi.py"))
    sintesi = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sintesi)
    for kind in ("organo", "fisarmonica", "basso_saw", "basso_808", "lead_pwm", "lead_saw", "pad"):
        note = sintesi.render(kind, {}, 57, 32000, 1.0)                       # il la 220 Hz
        assert len(note) == 32000 and 0.2 < float(np.max(np.abs(note))) <= 0.9, kind
        window = note[8000:24000] * np.hanning(16000)
        spectrum = np.abs(np.fft.rfft(window, 1 << 16))
        freqs = np.fft.rfftfreq(1 << 16, 1 / 32000)
        strong = freqs[np.argmax(spectrum * (freqs < 2000))]
        assert min(abs(strong / 220.0 - k) for k in (1, 2, 3, 4, 5, 6, 7, 8)) < 0.03, (kind, strong)      # una fondamentale o una sua armonica
    assert (sintesi.render("organo", {}, 60, 32000, 1.0) == sintesi.render("organo", {}, 60, 32000, 1.0)).all()
    with pytest.raises(ValueError):
        sintesi.render("flauto_magico", {}, 60)


def test_the_four_packages_are_listed_with_licenses():
    import json
    for name, limit in (("acustico", 25), ("elettrico", 25), ("elettronico", 10)):
        spec = json.load(open(os.path.join(ROOT, "mobile", "tools", "pacchetti", f"{name}.json"), encoding="utf-8"))
        programs = [e["programma"] for e in spec["strumenti"]]
        assert len(programs) == len(set(programs)) and spec["limite_mb"] == limit, name
        assert all(e.get("licenza") and ("sfz" in e or "sintesi" in e) for e in spec["strumenti"]), name


def test_normalized_samples_sit_at_full_scale_and_the_level_is_an_attenuation(tmp_path):
    """Il FluidSynth in WebAssembly porta i campioni SF3 al fondo scala: il volume voluto sta nell'attenuazione della zona."""
    tool = _tool()
    sources = {"sorgenti": _library(tmp_path)["vsco"]}
    quiet = _spec(guadagno_db=-18)
    quiet["normalizza"] = True
    data, _ = tool.build(sources, "sf2", log=lambda *_: None, spec=quiet)
    i = data.index(b"smpl")
    size = struct.unpack("<I", data[i + 4:i + 8])[0]
    pcm = np.frombuffer(data[i + 8:i + 8 + size], dtype="<i2")
    assert abs(int(np.max(np.abs(pcm))) - 0.98 * 32767) < 600                           # al fondo scala, nonostante i -18 dB
    j = data.index(b"igen")
    igen = data[j + 8:j + 8 + struct.unpack("<I", data[j + 4:j + 8])[0]]
    ops = [struct.unpack("<HH", igen[k:k + 4])[0] for k in range(0, len(igen), 4)]
    assert 48 in ops                                                                    # initialAttenuation
    plain, _ = tool.build(sources, "sf2", log=lambda *_: None, spec=_spec(guadagno_db=-18))
    k = plain.index(b"igen")
    assert 48 not in [struct.unpack("<HH", plain[k + 8 + m:k + 12 + m])[0] for m in range(0, 40, 4)]   # senza: il livello sta nei campioni


def test_the_complete_package_merges_the_four_with_one_instrument_per_program():
    tool = _tool()
    spec = tool.completo_spec()
    programs = [e["programma"] for e in spec["strumenti"]]
    assert len(programs) == len(set(programs)) and spec["normalizza"] and spec["limite_mb"] == 25
    from_orchestra = {e["programma"] for e in tool.orchestra_spec()["strumenti"]}
    first = {e["programma"]: e["pacchetto"] for e in spec["strumenti"]}
    assert all(first[p] == "orchestra" for p in from_orchestra)                       # vale il primo: l'orchestra tiene violino, tromba, clarinetto
    assert {"orchestra", "acustico", "elettrico", "elettronico"} == set(first.values())
    # il ritocco di volume del pacchetto passa agli strumenti
    import json
    acoustic = json.load(open(os.path.join(ROOT, "mobile", "tools", "pacchetti", "acustico.json"), encoding="utf-8"))
    piano = next(e for e in acoustic["strumenti"] if e["programma"] == 0)
    merged = next(e for e in spec["strumenti"] if e["programma"] == 0)
    assert merged["guadagno_db"] == pytest.approx(piano["guadagno_db"] + acoustic.get("guadagno_pacchetto_db", 0))


def test_the_programs_listed_in_the_app_match_the_package_files():
    """mobile/app/fonts.js sa quali programmi General MIDI copre ogni pacchetto (per la scelta automatica): lo stesso elenco dei file di dati."""
    import json
    import re
    source = open(os.path.join(ROOT, "mobile", "app", "fonts.js"), encoding="utf-8").read()
    in_app = {m.group(1): json.loads(m.group(2)) for m in re.finditer(r'\{ id: "(\w+)", programs: (\[[\d,]*\])', source)}
    tool = _tool()
    expected = {"orchestra": {e["programma"] for e in tool.orchestra_spec()["strumenti"]}}
    for name in ("acustico", "elettrico", "elettronico"):
        expected[name] = {e["programma"] for e in json.load(open(os.path.join(ROOT, "mobile", "tools", "pacchetti", f"{name}.json"), encoding="utf-8"))["strumenti"]}
    expected["completo"] = set().union(*expected.values())
    assert {k: set(v) for k, v in in_app.items()} == expected


def test_every_genre_has_a_preferred_pack_and_only_known_ones():
    import re
    source = open(os.path.join(ROOT, "mobile", "app", "fonts.js"), encoding="utf-8").read()
    block = re.search(r"const PACK_FOR_GENRE = \{(.*?)\n\};", source, re.S).group(1)
    genre_pack = dict(re.findall(r"(\w+): \"(\w+)\"", block))
    from core import quicksong
    assert set(genre_pack) == set(quicksong.GENRES_DATA)
    assert set(genre_pack.values()) <= {"orchestra", "acustico", "elettrico", "elettronico"}


def _drum_notes_used_by_the_rhythm_generator():
    import re
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(ROOT), "st-language"))
    from st_language.instruments import PERCUSSION_MAP
    source = open(os.path.join(ROOT, "core", "rhythm_generate.py"), encoding="utf-8").read()
    return {PERCUSSION_MAP[name] for name in set(re.findall(r'\("(\w+)", *\d+\)', source)) if name in PERCUSSION_MAP}


def test_the_electronic_kit_is_a_bank_128_preset_with_one_deterministic_hit_per_general_midi_note():
    tool = _tool()
    sintesi = tool.sintesi
    assert set(sintesi.DRUM_NOTES) == set(range(35, 82))
    for note in (36, 38, 42, 46, 49, 54):
        family, hit = sintesi.drum_hit(note)
        again = sintesi.drum_hit(note)[1]
        assert np.array_equal(hit, again) and 0.85 < float(np.max(np.abs(hit))) <= 0.9 and family in sintesi.DRUM_LEVEL_DB
        assert np.all(np.isfinite(hit)) and len(hit) > 3000
    spec = {"nome": "Prova", "copyright": "x", "commento": "x", "strumenti": [],
            "kit": [{"nome": "Electronic Kit", "programma": 0, "banco": 128, "frequenza": 32000}]}
    one, report = tool.build({}, "sf3", log=lambda *_: None, spec=spec)
    two, _ = tool.build({}, "sf3", log=lambda *_: None, spec=spec)
    assert one == two and report[0]["bank"] == 128 and report[0]["samples"] == len(sintesi.DRUM_NOTES)
    i = one.index(b"phdr")
    program, bank = struct.unpack("<HH", one[i + 8 + 20:i + 8 + 24])
    assert (program, bank) == (0, 128)                                                  # banco 128, programma 0: la batteria
    j = one.index(b"igen")
    igen = one[j + 8:j + 8 + struct.unpack("<I", one[j + 4:j + 8])[0]]
    keyranges = {struct.unpack("<HBB", igen[k:k + 4])[1:] for k in range(0, len(igen), 4) if struct.unpack("<H", igen[k:k + 2])[0] == 43}
    assert keyranges == {(n, n) for n in sintesi.DRUM_NOTES}                           # una zona per nota, senza trasposizione


def test_the_electronic_package_file_has_the_kit_and_it_covers_what_the_rhythm_generator_plays():
    spec = json.loads(open(os.path.join(ROOT, "mobile", "tools", "pacchetti", "elettronico.json"), encoding="utf-8").read())
    kits = spec["kit"]
    assert [(k["programma"], k["banco"]) for k in kits] == [(0, 128)]
    sintesi = _tool().sintesi
    assert _drum_notes_used_by_the_rhythm_generator() <= set(sintesi.DRUM_NOTES)
    complete = _tool().completo_spec()
    assert "kit" not in complete                                    # nel pacchetto completo le percussioni restano quelle di TimGM6mb


def _reducer():
    spec = importlib.util.spec_from_file_location("riduci_sf3", os.path.join(ROOT, "mobile", "tools", "riduci_sf3.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _synthetic_sf3(tool, tmp_path):
    """Un SF3 di prova con tre programmi e una batteria, fatto con i suoni sintetici (al posto di MuseScore General)."""
    spec = {"nome": "Prova", "copyright": "x", "commento": "x", "strumenti": [
        {"programma": p, "nome": f"Synth {p}", "tipo": "tenuto", "classe": "organo", "frequenza": 32000,
         "sintesi": {"tipo": "organo", "parametri": {"registri": [8, 8, 8, 0, 0, 0, 0, 0, 0]}, "estensione": [48, 72], "passo": 12}}
        for p in (16, 17, 18)], "kit": [{"nome": "Kit", "programma": 0, "banco": 128, "frequenza": 32000}]}
    data, _ = tool.build({}, "sf3", log=lambda *_: None, spec=spec)
    path = tmp_path / "sorgente.sf3"
    path.write_bytes(data)
    return path


def test_the_reducer_keeps_only_the_wanted_presets_and_their_samples_and_applies_the_gain(tmp_path):
    tool, reducer = _tool(), _reducer()
    source = reducer.SoundFont(_synthetic_sf3(tool, tmp_path))
    everything = reducer.reduce_soundfont(source, [(0, 16), (0, 17), (0, 18), (128, 0)], {}, "Base", "prova")
    part = reducer.reduce_soundfont(source, [(0, 17), (128, 0)], {"0/17": 6.0}, "Base", "prova")
    assert len(part) < len(everything) and part[:4] == b"RIFF"
    out = tmp_path / "ridotto.sf3"
    out.write_bytes(part)
    reduced = reducer.SoundFont(out)
    assert [(h[2], h[1]) for h in reduced.phdr[:-1]] == [(0, 17), (128, 0)]
    assert len(reduced.shdr) - 1 == 3 + len(tool.sintesi.DRUM_NOTES)                       # 3 note dell'organo + i colpi del kit
    assert reducer.reduce_soundfont(source, [(0, 17), (128, 0)], {"0/17": 6.0}, "Base", "prova") == part      # sempre lo stesso
    # +6 dB: l'attenuazione del preset scende di 6 dB / 0,4 = 15 dB = 150 centesimi di bel (cB, in 25 cB per dB)
    gens = [(op, struct.unpack("<h", amount)[0]) for op, amount in reduced.pgen]
    assert (48, -150) in gens
    # niente ritocco: nessun generatore in piu'
    flat = reducer.reduce_soundfont(source, [(0, 17)], {}, "Base", "prova")
    assert all(op != 48 for op, _a in reducer.SoundFont(_write(tmp_path, "piatto.sf3", flat)).pgen)
    # un preset che non c'e' si dice a voce alta
    with pytest.raises(SystemExit):
        reducer.reduce_soundfont(source, [(0, 99)], {}, "Base", "prova")


def _write(tmp_path, name, data):
    path = tmp_path / name
    path.write_bytes(data)
    return path


def test_the_base_file_lists_valid_programs_and_kits_and_a_gain_per_program():
    spec = json.loads(open(os.path.join(ROOT, "mobile", "tools", "pacchetti", "base.json"), encoding="utf-8").read())
    assert len(spec["programmi"]) == len(set(spec["programmi"])) and all(0 <= p <= 127 for p in spec["programmi"])
    assert not {0, 1, 2, 3} & set(spec["programmi"])                       # i pianoforti restano a TimGM6mb e al pacchetto acustico
    assert 128 not in spec["batterie"] and 0 in spec["batterie"] and spec["limite_mb"] <= 20
    assert all(abs(v) <= 12 for v in spec["guadagni_db"].values())
    assert {f"0/{p}" for p in spec["programmi"]} <= set(spec["guadagni_db"])
