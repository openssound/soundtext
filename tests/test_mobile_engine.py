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
    text = ("ST: 2.6\nTempo: 100 BPM\n\nPiano:\n  4: c d e |\n\nBasso:\n  4: c d e f |\n\n"
            "Traccia Lead [Violinoo]:\n  4: c d e f |\n\nPattern %A:\n  4: c d zz |\n")
    _, result = _check(text)
    kinds = {w["kind"]: w for w in result["warnings"]}
    assert set(kinds) == {"bar", "ignored", "file", "error"}
    # la '|' della battuta corta, il blocco "Basso:" saltato, il pattern che non si legge
    assert text[kinds["bar"]["start"]] == "|"
    assert text[kinds["ignored"]["start"]:kinds["ignored"]["end"]] == "Basso:"
    assert "basso" in kinds["ignored"]["message"]
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
