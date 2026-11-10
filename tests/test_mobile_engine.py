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
        engine.analyze(f.read(), name, transpose=3)
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
    with open(os.path.join(root, "examples", name), encoding="utf-8") as f:
        engine.analyze(f.read(), name, transpose=-2)
print(json.dumps(used))
"""


@pytest.mark.slow
def test_song_analysis_never_uses_numpy():
    out = subprocess.run([sys.executable, "-c", _NO_NUMPY_PROBE, ROOT, MOBILE],
                         capture_output=True, text=True, timeout=180, cwd=ROOT, env=dict(os.environ))
    assert out.returncode == 0, out.stderr
    assert json.loads(out.stdout.strip().splitlines()[-1]) == []
