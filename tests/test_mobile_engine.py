"""
Prototipo SoundText Mobile (mobile/, fase 0): il motore che gira in
Pyodide nel browser usa i moduli di core/ senza Qt. Qui si controlla che
nessuno di quelli che usa importi PySide6, nemmeno dentro una funzione
chiamata durante l'analisi, e che motore, trasposizione e mappa per
l'evidenziazione funzionino sugli esempi della fase 0.
"""

import io
import json
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOBILE = os.path.join(ROOT, "mobile")
EXAMPLES = ("jazz_aaba.st", "symphony_d_minor_box.st")

# In un processo nuovo: un finder registra ogni tentativo di importare
# PySide6 (anche quelli in un try/except) e lo fa fallire; poi si importano
# i moduli del motore e si analizzano gli esempi, trasposizione compresa.
_PROBE = r"""
import importlib, importlib.abc, json, os, sys
attempts = []
class NoQt(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name == "PySide6" or name.startswith("PySide6."):
            attempts.append(name)
            raise ImportError("PySide6 non e' disponibile nel motore di SoundText Mobile")
        return None
sys.meta_path.insert(0, NoQt())
root, mobile = sys.argv[1], sys.argv[2]
sys.path.insert(0, root); sys.path.insert(0, mobile)
import engine
for name in engine.ENGINE_MODULES:
    importlib.import_module(name)
for name in sys.argv[3:]:
    with open(os.path.join(root, "examples", name), encoding="utf-8") as f:
        source = f.read()
    engine.analyze(source, name, transpose=3)
    engine.check_text(source, name)
print(json.dumps({"attempts": attempts,
                  "core": sorted(m for m in sys.modules if m == "core" or m.startswith("core.")),
                  "qt_loaded": sorted(m for m in sys.modules if m.startswith("PySide6"))}))
"""


@pytest.fixture(scope="module")
def probe():
    # l'ambiente del processo di test, con la cartella di configurazione
    # isolata (tests/_config_isolation.py)
    out = subprocess.run([sys.executable, "-c", _PROBE, ROOT, MOBILE, *EXAMPLES],
                         capture_output=True, text=True, timeout=180, cwd=ROOT, env=dict(os.environ))
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout.strip().splitlines()[-1])


@pytest.mark.slow
def test_engine_modules_never_import_pyside6(probe):
    assert probe["attempts"] == []
    assert probe["qt_loaded"] == []


@pytest.mark.slow
def test_engine_modules_exclude_known_qt_modules(probe):
    # i due moduli di core/ che usano Qt (vedi il documento di progetto)
    assert "core.audio_decode" not in probe["core"]
    assert "core.autosave" not in probe["core"]
    for name in ("core.project_io", "core.midi_export", "core.model", "core.notation"):
        assert name in probe["core"]


@pytest.mark.slow
def test_bundle_lists_the_modules_actually_used(probe):
    sys.path.insert(0, MOBILE)
    try:
        import build
    finally:
        sys.path.remove(MOBILE)
    assert set(probe["core"]) <= set(build.engine_core_modules())


def _engine(name):
    sys.path.insert(0, MOBILE)
    try:
        import engine
    finally:
        sys.path.remove(MOBILE)
    with open(os.path.join(ROOT, "examples", name), encoding="utf-8") as f:
        text = f.read()
    e = engine.Engine()
    e.load(text, name)
    return e, text


def _notes(data):
    import mido
    out = []
    for track in mido.MidiFile(file=io.BytesIO(data)).tracks:
        tick = 0
        for msg in track:
            tick += msg.time
            if msg.type == "note_on" and msg.velocity:
                out.append((tick, msg.channel, msg.note))
    return sorted(out)


def test_transpose_moves_pitched_notes_only():
    e, _ = _engine("jazz_aaba.st")
    plain, up = _notes(e.midi_bytes(0)), _notes(e.midi_bytes(2))
    assert any(ch == 9 for _, ch, _ in plain)
    # le percussioni (canale 10) restano dove sono, il resto sale di 2
    assert sorted((t, ch, n if ch == 9 else n - 2) for t, ch, n in up) == plain


def test_highlight_spans_reach_the_notes_inside_patterns():
    e, text = _engine("jazz_aaba.st")
    spans = e.highlight_spans()
    tracks = [t.name for t in e.project.tracks if not t.is_audio]
    sax = tracks.index("Tenor Sax")
    sax_notes = [s for s in spans if s[0] == sax and s[5] > 0]
    # il primo chorus: box a beat 16 -> %Head -> %HeadA1, che comincia con "r a*4 c*5"
    first = sorted(sax_notes, key=lambda s: (s[3], -s[5]))
    tokens = [text[s[1]:s[2]] for s in first if s[5] == max(x[5] for x in first)][:3]
    assert tokens == ["r", "a*4", "c*5"]
    deepest = [s for s in first if text[s[1]:s[2]] == "a*4"][0]
    assert deepest[3] == pytest.approx(16.5)


def test_highlight_spans_follow_box_positions():
    e, text = _engine("symphony_d_minor_box.st")
    spans = e.highlight_spans()
    # ogni span sta dentro il testo e non finisce oltre la fine del MIDI
    last_note = max(t for t, _, _ in _notes(e.midi_bytes(0))) / 480
    assert all(0 <= s[1] < s[2] <= len(text) for s in spans)
    assert max(s[3] for s in spans) <= last_note + 1e-6


def _pyside_imports(module_name):
    """Gli import di PySide6 scritti nel sorgente del modulo, anche dentro
    funzioni o try/except (che la prova dinamica vede solo se li esegue)."""
    import ast
    rel = module_name.replace(".", "/") + ("/__init__.py" if module_name == "core" else ".py")
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        tree = ast.parse(f.read())
    found = []
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names = [node.module]
        found += [f"{module_name}:{node.lineno} {n}" for n in names if n.split(".")[0] == "PySide6"]
    return found


@pytest.mark.slow
def test_engine_modules_have_no_pyside6_import_anywhere(probe):
    assert [hit for name in probe["core"] for hit in _pyside_imports(name)] == []


def test_static_check_finds_lazy_qt_imports():
    # la stessa prova sui due moduli di core/ che usano Qt li trova
    assert _pyside_imports("core.audio_decode")
    assert _pyside_imports("core.autosave")


# Nel browser numpy si carica solo dopo l'avvio (mobile/worker.js): l'analisi
# dei brani non deve usarlo. Un numpy finto conta gli attributi letti dopo
# l'import dei moduli (prima, Python < 3.14 valuta le annotazioni del modulo,
# es. Dict[..., np.ndarray] in core/effects.py; Pyodide usa la 3.14, dove
# non si valutano piu' all'import).
_NO_NUMPY_PROBE = r"""
import importlib, json, os, sys, types
used = []
class FakeNumpy(types.ModuleType):
    armed = False
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        if FakeNumpy.armed:
            used.append(name)
        return type(name, (), {})
sys.modules["numpy"] = FakeNumpy("numpy")
root, mobile = sys.argv[1], sys.argv[2]
sys.path.insert(0, root); sys.path.insert(0, mobile)
import build, engine
for name in engine.ENGINE_MODULES:
    importlib.import_module(name)
FakeNumpy.armed = True
for name in build.EXAMPLES:
    with open(build.example_path(name), encoding="utf-8") as f:
        source = f.read()
    engine.analyze(source, name, transpose=-2)
    engine.check_text(source, name)
    e = engine.Engine()
    e.load(source, name)
    e.musicxml()
for kind in engine.GENERATORS:
    engine.generate(source, kind, {"seed": 1, "bars": 4, "performance": True})
print(json.dumps(used))
"""


@pytest.mark.slow
def test_song_analysis_never_uses_numpy():
    out = subprocess.run([sys.executable, "-c", _NO_NUMPY_PROBE, ROOT, MOBILE],
                         capture_output=True, text=True, timeout=180, cwd=ROOT, env=dict(os.environ))
    assert out.returncode == 0, out.stderr
    assert json.loads(out.stdout.strip().splitlines()[-1]) == []


def _check(text):
    sys.path.insert(0, MOBILE)
    try:
        import engine
    finally:
        sys.path.remove(MOBILE)
    return engine, engine.check_text(text)


def test_check_finds_ignored_tracks_errors_and_bar_warnings():
    text = ("ST: 2.6\nTempo: 100 BPM\n\nPiano:\n  4: c d e |\n\nBassoo:\n  4: c d e f |\n\n"
            "Traccia Lead [Violinoo]:\n  4: c d e f |\n\nPattern %A:\n  4: c d zz |\n")
    _, result = _check(text)
    kinds = {w["kind"] for w in result["warnings"]}
    assert kinds == {"bar", "file", "error"}
    first = {w["kind"]: w for w in reversed(result["warnings"])}
    kinds = first
    # la '|' della battuta corta, il blocco "Bassoo:" saltato (lo dice il lettore
    # dei file, da st-language 2.12.2: un avviso solo), il pattern che non si legge
    assert text[kinds["bar"]["start"]] == "|"
    files = [w for w in result["warnings"] if w["kind"] == "file"]
    assert [text[w["start"]:w["end"]] for w in files] == ["Bassoo:", "Traccia Lead [Violinoo]:"]
    assert "Bassoon" in files[0]["message"]
    assert text[kinds["error"]["start"]:kinds["error"]["end"]] == "Pattern %A:"
    assert {b["label"] for b in result["blocks"]} >= {"Piano", "Lead", "%A"}


def _example_names():
    sys.path.insert(0, MOBILE)
    try:
        import build
    finally:
        sys.path.remove(MOBILE)
    return build, build.EXAMPLES


@pytest.mark.slow
def test_check_marks_percussion_blocks():
    """La fila di tasti mostra i pezzi della batteria nelle tracce di percussioni."""
    text = ("ST: 2.6\nTempo: 100 BPM\n\nPiano:\n  4: c d e f |\n\n"
            "Drums:\n  8: kick hihat snare hihat kick hihat snare hihat |\n")
    _, result = _check(text)
    assert {b["label"]: b["percussion"] for b in result["blocks"]} == {"Piano": False, "Drums": True}


def _sung(notes, rate=16000, beat=0.6):
    """Una voce finta: una nota per quarto a 100 BPM, con due armoniche."""
    import numpy as np
    parts = [np.zeros(int(0.3 * rate))]
    for midi in notes:
        f = 440.0 * 2 ** ((midi - 69) / 12)
        n = int((beat - 0.06) * rate)
        t = np.arange(n) / rate
        env = np.minimum(1, np.minimum(t / 0.03, (t[-1] - t) / 0.05))
        parts += [0.3 * env * (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(4 * np.pi * f * t)), np.zeros(int(0.06 * rate))]
    return np.concatenate(parts).astype("<f4").tobytes()


HUM_SONG = "ST: 2.6\nTempo: 100 BPM\nMetrica: 4/4\n\nFlute:\n  4: c d e f |\n\nBass:\n  4: c*2 c*2 |\n"


def test_hum_writes_the_melody_in_the_octave_of_the_track():
    """«Canta»: do re mi fa cantati all'ottava 3 vanno nell'ottava dello strumento."""
    sys.path.insert(0, MOBILE)
    try:
        import engine
    finally:
        sys.path.remove(MOBILE)
    pcm = _sung((48, 50, 52, 53))
    bass = engine.hum_to_text(HUM_SONG, pcm, 16000, {"track": "Bass", "grid": "8"})
    assert bass["text"].split()[-4:] == ["2c*2", "2d*2", "2e*2", "2f*2"] and bass["notes"] == 4
    flute = engine.hum_to_text(HUM_SONG, pcm, 16000, {"track": "Flute", "grid": "4"})
    assert flute["text"].split()[-4:] == ["c*5", "d*5", "e*5", "f*5"]
    # l'anteprima e' un brano che si apre, con la sola parte cantata
    e = engine.Engine()
    assert [t["name"] for t in e.load(flute["preview"], "Anteprima")["tracks"]] == ["Flute"]


def test_hum_says_when_there_is_nothing_to_recognize():
    sys.path.insert(0, MOBILE)
    try:
        import engine
    finally:
        sys.path.remove(MOBILE)
    silent = engine.hum_to_text(HUM_SONG, b"\x00" * (4 * 32000), 16000, {"track": "Flute"})
    assert "error" in silent and "text" not in silent
    assert "error" in engine.hum_to_text(HUM_SONG, b"\x00" * 400, 16000, {"track": "Flute"})


def test_new_track_adds_an_empty_track_of_each_proposed_instrument():
    """«Nuova traccia»: ogni strumento proposto da' una traccia che il brano riconosce."""
    sys.path.insert(0, MOBILE)
    try:
        import engine
    finally:
        sys.path.remove(MOBILE)
    song = "ST: 2.6\nTempo: 100 BPM\n\nPiano:\n  1: C | F |\n"
    names = engine.track_instruments()
    assert "Guitar" in names and "Flute" in names
    for instrument in names:
        r = engine.new_track(song, instrument)
        assert r["text"].endswith("\n  ")                  # il cursore va sulla prima riga della traccia
        tracks = [b["label"] for b in engine.check_text(r["text"] + "4: c d e f |\n")["blocks"]]
        assert tracks[0] == "Piano" and tracks[-1] == r["name"] and len(tracks) == 2, instrument
    assert engine.new_track(song, "Piano")["name"] == "Piano 2"


def test_every_example_opens_plays_and_has_a_score():
    """Criterio della fase 1: tutti gli esempi di examples/ e
    examples/didattici/ (quelli dell'app, mobile/build.py) si aprono, si
    leggono e suonano, con un avviso solo per le parti che l'app non suona
    (strumenti SFZ o plugin, effetti, tracce audio)."""
    build, names = _example_names()
    assert len(names) >= 17 and "14_trasformazioni.st" in names
    for name in names:
        with open(build.example_path(name), encoding="utf-8") as f:
            text = f.read()
        e, result = _check(text)
        assert result["error"] == "", name
        assert all(w["kind"] == "unsupported" for w in result["warnings"]), (name, result["warnings"])
        assert bool(result["warnings"]) == ("__sfz__" in name), name
        analysis = e.analyze(text, name)
        assert _notes(analysis["midi"]), name
        assert analysis["spans"], name
        assert analysis["engine"].timeline()["length"] > 0, name
        assert "<score-part " in analysis["engine"].musicxml(), name


def test_check_colours_like_the_desktop_editor():
    engine, result = _check("Piano:\n  4: c d %A Am7 r | // fine\n")
    names = engine.syntax_categories()
    text = "Piano:\n  4: c d %A Am7 r | // fine\n"
    colours = {text[s:s + n]: names[c] for s, n, c in zip(*[iter(result["syntax"])] * 3)}
    assert colours["Piano:"] == "header"
    assert colours["4:"] == "state" and colours["c"] == "note" and colours["%A"] == "ref"
    assert colours["Am7"] == "chord" and colours["r"] == "rest" and colours["|"] == "bar"
    assert colours["// fine"] == "comment"


def test_completion_bar_and_transforms_for_the_music_bar():
    sys.path.insert(0, MOBILE)
    try:
        import engine
    finally:
        sys.path.remove(MOBILE)
    text = ("ST: 2.6\nTempo: 100 BPM\nMetrica: 3/4\n\nPattern %Tema:\n  4: c d e |\n\n"
            "Piano:\n  4: %Tema Cma\n\nDrums:\n  4: hi\n")
    engine.check_text(text)
    # come l'editor di SoundText: pattern, qualita' d'accordo, percussioni
    pos = text.index("Cma") + 3
    r = engine.complete(text, pos)
    assert text[r["start"]:r["end"]] == "Cma"
    assert "Cmaj7" in [i["text"] for i in r["items"]]
    r = engine.complete(text[:pos - 3] + "%Te" + text[pos:], pos)
    assert [i["text"] for i in r["items"]] == ["%Tema"]
    pos = text.index("hi") + 2
    assert "hihat" in [i["text"] for i in engine.complete(text, pos)["items"]]
    # la battuta di un battito, in 3/4
    assert engine.bar_bounds(text, 4.5) == [3.0, 6.0]
    assert engine.bar_bounds(text, 0) == [0.0, 3.0]
    calls = [t["call"] for t in engine.transforms()]
    assert any(c.startswith(".retro") for c in calls) and all(c.startswith(".") for c in calls)


def test_player_mute_solo_and_metronome():
    """Lettore completo (tappa 4): le tracce in mute perdono le note, il
    resto del brano resta dov'e'; il metronomo batte ogni battito, piu'
    forte sul primo della battuta; la linea del tempo arriva alla fine."""
    import mido
    e, _ = _engine("jazz_aaba.st")
    timeline = e.timeline()
    plain = _notes(e.midi_bytes(0))
    assert timeline["bars"][:3] == [0.0, 4.0, 8.0]
    assert max(t for t, _, _ in plain) / 480 < timeline["length"]
    assert timeline["bars"][-1] < timeline["length"]

    def by_track(data):
        out = {}
        for track in mido.MidiFile(file=io.BytesIO(data)).tracks:
            out[track.name] = sum(1 for m in track if m.type == "note_on" and m.velocity)
        return out

    counts = by_track(e.midi_bytes(0))
    muted = by_track(e.midi_bytes(0, ["Piano", "Drums"]))
    assert muted["Piano"] == muted["Drums"] == 0
    assert muted["Bass"] == counts["Bass"] > 0
    # le note che restano non si spostano nel tempo
    kept = [n for n in _notes(e.midi_bytes(0, ["Piano"])) if n[1] != 9]
    assert set(kept) <= set(plain)

    clicks = [m for track in mido.MidiFile(file=io.BytesIO(e.midi_bytes(0, (), True))).tracks
              if track.name == "Metronomo" for m in track if m.type == "note_on"]
    assert len(clicks) == int(timeline["length"])
    assert sum(1 for m in clicks if m.note == 76) == len(timeline["bars"])
    # trasposizione, mute e metronomo insieme
    both = e.midi_bytes(2, ["Piano"], True)
    assert by_track(both)["Piano"] == 0 and "Metronomo" in by_track(both)


def test_score_musicxml_all_tracks_or_some():
    """Partitura (tappa 5): il MusicXML ha una parte per traccia udibile,
    oppure solo per le tracce scelte."""
    e, _ = _engine("jazz_aaba.st")
    full = e.musicxml()
    assert full.count("<score-part ") == 5
    one = e.musicxml(["Bass"])
    assert one.count("<score-part ") == 1 and "<part-name>Bass</part-name>" in one
    assert e.musicxml(["Piano", "Bass"]).count("<score-part ") == 2


SECTIONS_SONG = ("ST: 2.6\nTempo: 100 BPM\nMetrica: 4/4\n\n// accordi\nPiano:\n  1: C | F | G7 | C |\n\n"
                 "Bass:\n  4: c*2 e*2 g*2 e*2 | f*2 a*2 c*3 a*2 | g*2 b*2 d*3 b*2 | 4c*2 |\n\n"
                 "Mixer Piano:\n  volume: 90 pan: 0 mute: no solo: no\n")


def test_structure_builds_a_song_in_sections():
    """Struttura (fase 2): dal testo semplice a un brano a sezioni senza
    scrivere intestazioni; il resto del file resta com'e' e SoundText lo
    legge con i box giusti."""
    sys.path.insert(0, MOBILE)
    try:
        import engine
    finally:
        sys.path.remove(MOBILE)
    from core.project_io import parse_project_text

    def boxes(text):
        return {t.name: [(c.name, c.start_beat) for c in t.clips] for t in parse_project_text(text, "x").tracks}

    text = engine.box_edit(SECTIONS_SONG, "make_boxes", {"name": "Strofa"})["text"]
    assert boxes(text) == {"Piano": [("Strofa", 0.0)], "Bass": [("Strofa", 0.0)]}
    assert "// accordi\n" in text and text.endswith("Mixer Piano:\n  volume: 90 pan: 0 mute: no solo: no\n")
    info = engine.structure(text)
    assert [(s["bar"], s["name"]) for s in info["sections"]] == [(1, "Strofa")]
    assert [b["bars"] for t in info["tracks"] for b in t["boxes"]] == [4, 4]

    text = engine.box_edit(text, "section_duplicate", {"beat": 0})["text"]
    text = engine.box_edit(text, "section_rename", {"beat": 16, "name": "Ritornello"})["text"]
    text = engine.box_edit(text, "section_duplicate", {"beat": 0})["text"]
    assert boxes(text)["Bass"] == [("Strofa", 0.0), ("Ritornello", 16.0), ("Strofa", 32.0)]
    info = engine.structure(text)
    assert [(s["bar"], s["name"]) for s in info["sections"]] == [(1, "Strofa"), (5, "Ritornello"), (9, "Strofa")]
    # la copia suona come l'originale, spostata di 8 battute
    plain = engine.analyze(SECTIONS_SONG, "x")["midi"]
    full = engine.analyze(text, "x")["midi"]
    first = sorted(n for n in _notes(plain))
    assert [n for n in _notes(full) if n[0] >= 32 * 480] == [(t + 32 * 480, ch, note) for t, ch, note in first]

    piano = [b for b in engine._box_blocks(text) if b["track"] == "Piano"]
    moved = engine.box_edit(text, "move", {"hstart": piano[2]["hstart"], "bar": 13})["text"]
    assert boxes(moved)["Piano"][-1] == ("Strofa", 48.0)
    with pytest.raises(ValueError, match="sovrappone"):
        engine.box_edit(text, "move", {"hstart": piano[1]["hstart"], "bar": 2})
    gone = engine.box_edit(text, "section_delete", {"beat": 16})["text"]
    assert boxes(gone)["Piano"] == [("Strofa", 0.0), ("Strofa", 32.0)]
    renamed = engine.box_edit(text, "rename", {"hstart": piano[0]["hstart"], "name": "Intro"})["text"]
    assert boxes(renamed)["Piano"][0] == ("Intro", 0.0)


def test_structure_of_the_examples():
    sys.path.insert(0, MOBILE)
    try:
        import engine
    finally:
        sys.path.remove(MOBILE)
    with open(os.path.join(ROOT, "examples", "jazz_aaba.st"), encoding="utf-8") as f:
        text = f.read()
    info = engine.structure(text)
    assert [s["name"] for s in info["sections"]] == ["Intro", "Intro", "Chorus 1", "Chorus 2", "Chorus 3", "Coda"]
    piano = next(t for t in info["tracks"] if t["name"] == "Piano")
    assert [(b["name"], b["bar"], b["bars"]) for b in piano["boxes"]][:2] == [("Intro", 1, 4), ("Chorus 1", 5, 32)]
    assert all(text[b["start"]:].startswith("  ") for b in piano["boxes"])     # il corpo del box nel testo


@pytest.mark.parametrize("token", ["%Tema.retro", "%Tema.invert(e*4).augment(2)", "%Tema.thirds", "2%Tema.step(1)"])
def test_transform_preview_sounds_like_the_song_after_replacing(token):
    """Trasforma (fase 2): l'anteprima suona proprio quello che suona il
    brano dopo «Sostituisci», nello stesso punto; «Scrivi le note» non
    cambia il suono."""
    import base64
    import re
    import mido
    sys.path.insert(0, MOBILE)
    try:
        import engine
    finally:
        sys.path.remove(MOBILE)
    with open(os.path.join(ROOT, "examples", "didattici", "14_trasformazioni.st"), encoding="utf-8") as f:
        text = f.read()
    first = next(m for m in re.finditer(r"%Tema\b", text) if not text[:m.start()].endswith("Pattern "))
    pos = first.start() + 1
    preview = engine.transform_preview(text, pos, token)
    assert preview["error"] == "", preview["error"]
    assert preview["stages"][0][0] and len(preview["stages"]) >= 2

    def notes(data, track=None, start=0):
        out = []
        for tr in mido.MidiFile(file=io.BytesIO(data)).tracks:
            if track and tr.name != track:
                continue
            tick = 0
            for msg in tr:
                tick += msg.time
                if msg.type == "note_on" and msg.velocity:
                    out.append((tick - start, msg.note, msg.velocity))
        return sorted(out)

    heard = notes(base64.b64decode(preview["midi_after"]))
    applied = engine.transform_apply(text, pos, preview["token"])["text"]
    offset = round(preview["position"] * 480)
    song = [n for n in notes(engine.analyze(applied, "x")["midi"], track="Melodia", start=offset)
            if 0 <= n[0] < (heard[-1][0] + 1 if heard else 0)]
    assert song == heard
    frozen = engine.transform_apply(text, pos, preview["token"], freeze=True)["text"]
    assert notes(engine.analyze(frozen, "x")["midi"]) == notes(engine.analyze(applied, "x")["midi"])
    added = [line for line in frozen.split("\n") if line not in text.split("\n")]
    assert added and all(line.startswith("  ") for line in added)   # il rientro del file resta


def test_dictate_knows_the_patterns_of_the_song():
    """La dettatura nel motore (fase 2): i pattern del brano si riconoscono
    per nome, la lingua e' quella data o quella dell'interfaccia."""
    sys.path.insert(0, MOBILE)
    try:
        import engine
    finally:
        sys.path.remove(MOBILE)
    with open(os.path.join(ROOT, "examples", "didattici", "14_trasformazioni.st"), encoding="utf-8") as f:
        source = f.read()
    result = engine.dictate(source, "motivo retrogrado, giro, la minore", "it")
    assert result["text"] == "%Motivo.retro %Giro Am"
    assert engine.dictate(source, "Motivo inverted", "en")["text"] == "%Motivo.invert"
    assert engine.dictate("non si legge {", "do re mi")["text"] == "c d e"


def test_dictate_track_adds_an_empty_track_ready_to_dictate():
    """«nuova traccia basso» (fase 2, tappa 6): la traccia in fondo al brano,
    con la riga rientrata dove continua la dettatura; il brano resta valido."""
    sys.path.insert(0, MOBILE)
    try:
        import engine
    finally:
        sys.path.remove(MOBILE)
    from core.project_io import parse_project_text
    source = "ST: 2.6\nTempo: 100 BPM\n\nPiano:\n  1: C | F |\n"
    r = engine.dictate_track(source, "basso", "it")
    assert r["name"] == "Bass"
    assert r["text"] == source + "\nBass:\n  "
    dictated = r["text"] + engine.dictate(r["text"], "quarti do mi sol mi", "it")["text"] + "\n"
    assert [t.name for t in parse_project_text(dictated, "x").tracks] == ["Piano", "Bass"]
    again = engine.dictate_track(dictated, "bass", "en")
    assert again["name"] == "Bass 2"
    # da st-language 2.12.2 anche gli strumenti fuori dal catalogo hanno la forma breve
    violin = engine.dictate_track(source, "violino", "it")
    assert violin["text"].endswith("\nViolin:\n  ")
    track = parse_project_text(violin["text"] + "4: c d e f\n", "x").tracks[1]
    assert track.name == violin["name"] and track.instrument.resolved and track.instrument.gm_program == 40
    strings = engine.dictate_track(source, "strings", "en")
    assert parse_project_text(strings["text"] + "1: c\n", "x").tracks[1].instrument.gm_program == 48
    assert engine.dictate_track(source, "pippo", "it") is None


def test_short_headers_and_odd_meters_of_st_language_2122():
    """st-language 2.12.2: «Flute:» e «Basso:» sono tracce, e una metrica che
    il MIDI non sa scrivere (4/6) non ferma l'analisi."""
    engine, result = _check("ST: 2.6\nTempo: 100 BPM\n\nBasso:\n  4: c d e f |\n\nFlute:\n  4: c d e f |\n")
    assert result["warnings"] == []
    assert {b["label"] for b in result["blocks"]} == {"Basso", "Flute"}
    song = engine.analyze("ST: 2.6\nTempo: 100 BPM\nMetrica: 4/6\n\nFlute:\n  4: c d e f\n", "x")
    assert [t["instrument"] for t in song["info"]["tracks"]] == ["Flute"]


def test_strip_comments_keeps_the_song_but_not_the_comments():
    """Per il QR code: tolti i commenti il brano e' lo stesso (la stessa musica), e un // dentro un testo cantato non e' un commento."""
    import glob

    _engine("jazz_aaba.st")                               # mette il motore fra i moduli importabili
    e = sys.modules["engine"]
    assert e.strip_comments("// titolo\n\nST: 2.6\nTempo: 90 BPM // veloce\n\n\n\nPiano:\n  1: C | // via\n") == \
        "ST: 2.6\nTempo: 90 BPM\n\nPiano:\n  1: C |\n"
    assert e.strip_comments("Testo: \"a // b\" // fine\n") == "Testo: \"a // b\"\n"
    files = sorted(glob.glob(os.path.join(ROOT, "examples", "*.st")) + glob.glob(os.path.join(ROOT, "examples", "didattici", "*.st")))
    assert len(files) >= 10
    for path in files:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        short = e.strip_comments(text)
        assert len(short) <= len(text) + 1, path
        # la stessa musica: gli stessi byte MIDI, con e senza commenti
        full, bare = e.Engine(), e.Engine()
        full.load(text, "Brano")
        bare.load(short, "Brano")
        assert bare.midi_bytes(0) == full.midi_bytes(0), path


def _quick():
    _engine("jazz_aaba.st")                               # mette il motore fra i moduli importabili
    if MOBILE not in sys.path:                            # e quicksong, che il motore importa quando serve
        sys.path.insert(0, MOBILE)
    return sys.modules["engine"]


def test_quick_song_opens_in_the_structure_view():
    """Il brano scritto a box si legge anche dalla vista Struttura."""
    e = _quick()
    r = e.quick_song({"genre": "lofi", "mood": "tesa", "duration": 60, "seed": 4})
    structure = e.structure(r["text"])
    assert structure["tracks"], structure


def test_chord_chart_reads_written_chords_and_chords_made_of_notes():
    """La clip video mostra gli accordi: sigle scritte nel brano, oppure ricavate dai blocchi di note."""
    e = _quick()
    with open(os.path.join(ROOT, "examples", "jazz_aaba.st"), encoding="utf-8") as f:
        chart = e.chord_chart(f.read())
    assert chart and all(len(c) == 3 and c[1] > 0 and isinstance(c[2], str) for c in chart)
    assert [c[0] for c in chart] == sorted(c[0] for c in chart)
    made = e.quick_song({"genre": "pop", "mood": "malinconica", "duration": 30, "seed": 2, "key": "Am"})
    chart = e.chord_chart(made["text"])
    labels = [c[2] for c in chart]
    assert labels and {"Am", "G", "F", "E"} & set(labels), labels          # il giro di La minore
    assert e.chord_chart("ST: 2.6\nTempo: 100 BPM\nMetrica: 4/4\n\nDrums:\n  4: kick snare kick snare |\n") == []


def test_bank_select_sends_a_pitched_track_to_its_soundfont():
    """Un SoundFont per traccia: il banco della traccia (CC 0) apre i suoni del suo SoundFont; le
    percussioni restano sul predefinito, e senza banchi il MIDI e' quello di sempre."""
    import io

    import mido
    _engine("jazz_aaba.st")
    e = sys.modules["engine"]
    with open(os.path.join(ROOT, "examples", "jazz_aaba.st"), encoding="utf-8") as f:
        engine = e.Engine()
        engine.load(f.read(), "jazz")

    def banks_of(data):
        out = {}
        for track in mido.MidiFile(file=io.BytesIO(data)).tracks:
            for msg in track:
                if msg.type == "control_change" and msg.control == 0:
                    out.setdefault(track.name, set()).add((msg.channel, msg.value))
        return out

    assert engine.midi_bytes(0) == engine.midi_bytes(0, banks={}) == engine.midi_bytes(0, banks={"Piano": 0})
    base_banks = banks_of(engine.midi_bytes(0))                      # la batteria ha gia' il suo banco (GS)
    assert all(ch == 9 for pairs in base_banks.values() for ch, _v in pairs)
    named = {t.name for t in mido.MidiFile(file=io.BytesIO(engine.midi_bytes(0))).tracks}
    piano = next(n for n in named if n.lower().startswith("piano"))
    drums = next(n for n in named if n.lower().startswith("drums"))
    result = banks_of(engine.midi_bytes(0, banks={piano: 3, drums: 4}))
    assert result[piano] and all(value == 3 and channel != 9 for channel, value in result[piano])
    assert result.get(drums) == base_banks.get(drums)                # le percussioni non cambiano banco
    # con la trasposizione e il mute il resto continua a funzionare
    mixed = engine.midi_bytes(2, muted=[piano], banks={piano: 3})
    assert mixed != engine.midi_bytes(0)


def test_effects_plan_keeps_what_the_app_can_do_and_lists_the_rest():
    """Gli effetti che l'app sente: la catena master (Web Audio) e il riverbero di traccia (invio di FluidSynth);
    il resto si elenca come non udibile."""
    _engine("jazz_aaba.st")
    e = sys.modules["engine"]
    with open(os.path.join(ROOT, "examples", "jazz_1_evening_swing__sfz__plugin-areverb__nam-twin.st"), encoding="utf-8") as f:
        text = f.read()
    engine = e.Engine()
    engine.load(text, "jazz")
    plan = engine.effects_plan()
    assert [m["kind"] for m in plan["master"]] == ["compressore", "limiter"]           # il plugin del master non si sente
    assert plan["master"][0]["params"]["soglia"] == -14 and plan["master"][1]["params"]["tetto"] == -1
    assert plan["sends"]["Piano"]["91"] > 0 and "Guitar" in plan["sends"]
    assert plan["reverb"] and 0 < plan["reverb"]["room"] < 1 and plan["reverb"]["level"] > 0
    assert {"nam", "plugin"} <= set(plan["ignored"]) and "riverbero" not in plan["ignored"]
    assert {"compressore", "eq"} <= set(plan["ignored"])                               # per traccia non si possono fare
    # il MIDI porta gli invii al riverbero sui canali della traccia (non su quelli delle percussioni)
    import io

    import mido
    midi = mido.MidiFile(file=io.BytesIO(engine.midi_bytes(0, sends=plan["sends"])))
    sent = {t.name: {m.value for m in t if m.type == "control_change" and m.control == 91} for t in midi.tracks}
    assert plan["sends"]["Piano"]["91"] in sent["Piano"]
    assert engine.midi_bytes(0) != engine.midi_bytes(0, sends=plan["sends"])
    # senza effetti: niente da fare, e il MIDI resta quello di sempre
    plain = e.Engine()
    plain.load("ST: 2.6\nTempo: 100 BPM\nMetrica: 4/4\n\nPiano:\n  4: c d e f |\n", "p")
    assert plain.effects_plan() == {"master": [], "reverb": None, "sends": {}, "ignored": []}
    assert plain.midi_bytes(0, sends={}) == plain.midi_bytes(0)


def test_unheard_effects_warning_lists_only_the_kinds_the_app_cannot_do():
    e = _quick()
    with open(os.path.join(ROOT, "examples", "jazz_1_evening_swing__sfz__plugin-areverb__nam-twin.st"), encoding="utf-8") as f:
        warnings = [w["message"] for w in e.check_text(f.read(), "jazz")["warnings"] if w["kind"] == "unsupported"]
    effects = [m for m in warnings if m.startswith("Effetti che nell'app non si sentono")]
    assert len(effects) == 1 and "nam" in effects[0] and "plugin" in effects[0] and "riverbero" not in effects[0]


def test_pad_chords_cover_the_key_and_every_symbol_is_valid_st():
    """Nove pad per tonalita': accordi della scala piu' due colori, con settima, sospeso e rivolto che ST sa leggere."""
    e = _quick()
    from core.chords import parse_chord_symbol
    from core.project_io import parse_project_text
    from core.rhythm_generate import extract_chords_from_track
    for key, labels, first in (("C", ["I", "ii", "iii", "IV", "V", "vi", "vii°", "V/V", "iv"], "C"),
                               ("Am", ["i", "ii°", "III", "iv", "V", "VI", "VII", "v", "♭II"], "Am"),
                               ("Bb", None, "Bb"), ("Ebm", None, "Ebm"), ("F#", None, "F#")):
        info = e.pad_info(key)
        assert len(info["chords"]) == 9 and info["chords"][0]["symbol"] == first, key
        if labels:
            assert [c["label"] for c in info["chords"]] == labels
        for chord in info["chords"]:
            for symbol in (chord["symbol"], chord["seventh"]["symbol"], chord["sus"]["symbol"]):
                parse_chord_symbol(symbol)                                     # nessun simbolo non valido
            assert all(24 <= n <= 90 for n in chord["notes"]) and chord["notes"] == sorted(chord["notes"])
            block = chord["inversion"]["text"]                                  # il rivolto e' un blocco di note ST
            project = parse_project_text(f"ST: 2.6\nTempo: 100 BPM\nMetrica: 4/4\n\nPiano:\n  4: 4{block}\n", "x")
            assert extract_chords_from_track(project.tracks[0].text, project.patterns, midi_dir=None)
    flat = [c["symbol"] for c in e.pad_info("Bb")["chords"]]
    sharp = [c["symbol"] for c in e.pad_info("E")["chords"]]
    assert "Eb" in flat and "G#m" in sharp and not any("#" in s for s in flat)
    assert e.pad_info("Am")["chords"][8]["symbol"] == "Bb"                      # ♭II con il bemolle anche in La minore
    assert [d["name"] for d in e.pad_info("C")["drums"]] == ["kick", "snare", "hihat", "hihat_open", "tom_hi", "tom2", "crash", "ride"]


def test_pad_chords_text_quantizes_taps_to_bars_or_half_bars():
    e = _quick()
    from core.project_io import parse_project_text
    from core.rhythm_generate import extract_chords_from_track
    taps = [{"beat": 0.1, "text": "Am"}, {"beat": 4.3, "text": "F"}, {"beat": 7.8, "text": "C"}, {"beat": 12.2, "text": "G7"}]
    r = e.pad_chords_text(taps, {"total_beats": 16.4, "grid": "bar"})
    assert r["text"] == "4: 4Am 4F 4C 4G7" and r["bars"] == 4 and r["chords"] == 4
    project = parse_project_text(f"ST: 2.6\nTempo: 100 BPM\nMetrica: 4/4\n\nPiano:\n  {r['text']}\n", "x")
    chords = extract_chords_from_track(project.tracks[0].text, project.patterns, midi_dir=None)
    assert [(c.start_beat, c.duration_beats, c.root_pc) for c in chords] == [(0, 4, 9), (4, 4, 5), (8, 4, 0), (12, 4, 7)]
    assert e.pad_chords_text([{"beat": 0, "text": "Am"}, {"beat": 2.2, "text": "G"}], {"grid": "half"})["text"] == "4: 2Am 2G"
    # due tocchi nello stesso passo: vale l'ultimo; l'ultimo accordo arriva alla fine della registrazione
    assert e.pad_chords_text([{"beat": 0.1, "text": "C"}, {"beat": 0.3, "text": "F"}], {"total_beats": 8})["text"] == "4: 8F"
    # chi comincia dopo la battuta uno trova prima una pausa; una meta' battuta non intera passa al battito
    assert e.pad_chords_text([{"beat": 4.2, "text": "Am"}], {"grid": "bar"})["text"].startswith("4: 4r 4Am")
    assert e.pad_chords_text([{"beat": 0, "text": "Am"}, {"beat": 1.6, "text": "G"}], {"bar_beats": 3, "grid": "half"})["text"] == "4: 2Am 1G"
    for bad in ([], [{"beat": 0, "text": "C"}]):
        if not bad:
            with pytest.raises(ValueError):
                e.pad_chords_text(bad)
    with pytest.raises(ValueError):
        e.pad_chords_text([{"beat": 0, "text": "C"}], {"grid": "mai"})


def test_pad_drums_text_makes_a_groove_that_suona():
    e = _quick()
    from core.project_io import parse_project_text
    hits = [{"beat": 0, "name": "kick"}, {"beat": 0.02, "name": "hihat"}, {"beat": 1.0, "name": "snare"}, {"beat": 2.52, "name": "hihat"},
            {"beat": 3.9, "name": "kick"}, {"beat": 5, "name": "crash"}]
    r = e.pad_drums_text(hits, {"bars": 2})
    assert r["text"] == "16: [kick hihat] 3r snare 5r hihat 5r |\nkick 3r crash 11r |" and r["hits"] == 6 and r["bars"] == 2
    project = parse_project_text(f"ST: 2.6\nTempo: 100 BPM\nMetrica: 4/4\n\nDrums:\n  {r['text']}\n", "x")
    events = project.tracks[0].parsed_events(project.patterns, midi_dir=None, meter="4/4")
    played = sorted((round(ev.start, 3), it["name"]) for ev in events if ev.kind == "block" for it in ev.items) + \
        sorted((round(ev.start, 3), ev.name) for ev in events if ev.kind == "percussion")
    assert (0.0, "kick") in played and (0.0, "hihat") in played and (1.0, "snare") in played and (5.0, "crash") in played
    # un giro di una battuta: i colpi dopo la fine tornano all'inizio
    assert e.pad_drums_text([{"beat": 4.0, "name": "kick"}], {"bars": 1})["text"] == "16: kick 15r |"
    with pytest.raises(ValueError):
        e.pad_drums_text([])
    with pytest.raises(ValueError):
        e.pad_drums_text([{"beat": 0, "name": "cabasa"}])


def test_add_pattern_goes_before_the_first_track_and_is_valid():
    e = _quick()
    from core.project_io import parse_project_text
    text = ("// idea\n\nST: 2.6\nTempo: 100 BPM\nMetrica: 4/4\n\nPattern %Rest:\n  4: 4r |\n\nPiano:\n  1: C | F |\n\nBass:\n  4: c d |\n")
    out = e.add_pattern(text, "Groove", "16: kick 3r snare 3r |")
    assert out["name"] == "Groove" and out["text"].index("Pattern %Groove:") < out["text"].index("Piano:")
    project = parse_project_text(out["text"], "x")
    assert "Groove" in project.patterns or "%Groove" in project.patterns
    assert [t.name for t in project.tracks] == ["Piano", "Bass"]                      # le tracce non cambiano
    assert e.add_pattern(out["text"], "Groove", "16: snare 15r |")["name"] == "Groove2"      # nome gia' preso
    assert e.add_pattern("ST: 2.6\nTempo: 100 BPM\nMetrica: 4/4\n", "G", "4: c |")["text"].endswith("  4: c |\n\n")


def test_track_notes_gives_the_melody_of_a_track_in_beats():
    """«Suona con la base»: le note di una traccia, una voce sola, in battiti; niente per le percussioni."""
    e = _quick()
    made = e.quick_song({"genre": "pop", "mood": "allegra", "duration": 30, "seed": 3})
    tracks = [m.group(1) for m in re.finditer(r'^Box (\S+) "', made["text"], re.M)]
    melody = next(n for n in tracks if e.track_notes(made["text"], n))
    notes = e.track_notes(made["text"], melody)
    assert len(notes) > 8 and all(0 <= n[2] < 128 and n[1] > 0 for n in notes)
    assert all(a[0] + a[1] <= b[0] + 1e-9 for a, b in zip(notes, notes[1:]))         # una voce, senza sovrapposizioni
    assert e.track_notes(made["text"], "Non c'e'") == []
    drums = [n for n in tracks if "rum" in n or "Drum" in n]
    assert all(e.track_notes(made["text"], n) == [] for n in drums)


def test_visual_notes_gives_every_track_with_its_notes_in_beats():
    """Le forme e i colori della clip: le note di tutte le tracce, con la dinamica; le percussioni segnate."""
    e = _quick()
    made = e.quick_song({"genre": "rock", "mood": "tesa", "duration": 30, "seed": 2})
    data = e.visual_notes(made["text"])
    assert data["bpm"] > 0 and len(data["tracks"]) >= 3
    assert any(t["percussion"] for t in data["tracks"]) and any(not t["percussion"] for t in data["tracks"])
    for track in data["tracks"]:
        assert track["notes"] == sorted(track["notes"])
        assert all(n[1] > 0 and 0 <= n[2] < 128 and 0 < n[3] <= 127 for n in track["notes"])
