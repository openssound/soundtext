"""
Prepara mobile/bundle/ per il prototipo SoundText Mobile (fase 0):

- engine.zip: mobile/engine.py, i moduli di core/ che servono al motore
  (quelli che Python carica davvero importando engine.ENGINE_MODULES,
  con PySide6 bloccato) e locales/*.json, da estrarre nel file system di
  Pyodide;
- examples/: gli esempi che la pagina propone;
- locales/<lingua>.json: le traduzioni dell'interfaccia dell'app, prese dai
  cataloghi di SoundText (locales/, vedi mobile/i18n.js) e ridotte alle sue
  voci;
- files.json: l'elenco, per la pagina e per il service worker.

Da lanciare dopo ogni modifica a core/ o a engine.py:
    venv/bin/python mobile/build.py
"""

import json
import os
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUNDLE = os.path.join(HERE, "bundle")

# Tutti gli esempi di examples/ e examples/didattici/ (criterio della fase 1:
# si aprono, si leggono e suonano), prima i brani e poi i didattici.
def _example_files() -> list:
    out = []
    for folder in ("examples", os.path.join("examples", "didattici")):
        out += sorted(f for f in os.listdir(os.path.join(ROOT, folder)) if f.endswith(".st"))
    return out


EXAMPLES = _example_files()
EXAMPLE_DIRS = ("examples", os.path.join("examples", "didattici"))


def example_path(name: str) -> str:
    for folder in EXAMPLE_DIRS:
        path = os.path.join(ROOT, folder, name)
        if os.path.exists(path):
            return path
    raise FileNotFoundError(name)

# Moduli caricati dal motore mentre analizza ed esporta gli esempi (alcuni
# moduli di core/ ne importano altri solo dentro le funzioni), con PySide6
# che fallisce all'import: tests/test_mobile_engine.py fa la stessa prova.
_PROBE = r"""
import importlib, json, os, sys
sys.modules["PySide6"] = None
root, here = sys.argv[1], sys.argv[2]
sys.path.insert(0, root); sys.path.insert(0, here)
import engine
for name in engine.ENGINE_MODULES:
    importlib.import_module(name)
for path in sys.argv[3:]:
    name = os.path.basename(path)
    with open(path, encoding="utf-8") as f:
        source = f.read()
    engine.analyze(source, name, transpose=2)
    engine.check_text(source, name)
    e = engine.Engine()
    e.load(source, name)
    e.musicxml()
# i generatori (fase 2), su un brano con degli accordi
with open(os.path.join(root, "examples", "jazz_aaba.st"), encoding="utf-8") as f:
    source = f.read()
for kind in engine.GENERATORS:
    engine.generate(source, kind, {"seed": 1, "bars": 4, "performance": True})
engine.generator_choices(source)
# la struttura (fase 2): box e sezioni
engine.structure(source)
song = engine.add_track("ST: 2.6\nTempo: 100 BPM\n", "Piano", "1: C | F |")["text"]
engine.box_edit(engine.box_edit(song, "make_boxes", {"name": "A"})["text"], "section_duplicate", {"beat": 0})
# trasforma (fase 2)
with open(os.path.join(root, "examples", "didattici", "14_trasformazioni.st"), encoding="utf-8") as f:
    source = f.read()
at = source.index("  %Tema") + 3
engine.transform_preview(source, at, "%Tema.retro.invert(e*4)")
engine.transform_apply(source, at, "%Tema.retro", True)
# dettatura (fase 2)
engine.dictate(source, "ottavi do re mi fa ripeti due volte, la minore, Tema invertito, tempo novanta", "it")
engine.dictate_track(source, "basso", "it")
# canta (fase 2): mezzo secondo di una nota tenuta
import math, struct
pcm = struct.pack("<8000f", *(0.3 * math.sin(2 * math.pi * 220 * i / 16000) for i in range(8000)))
engine.hum_to_text(source, pcm, 16000, {"track": "Piano"})
print(json.dumps(sorted(m for m in sys.modules if m == "core" or m.startswith("core."))))
"""


def engine_core_modules() -> list:
    out = subprocess.run([sys.executable, "-I", "-c", _PROBE, ROOT, HERE, *map(example_path, EXAMPLES)],
                         check=True, capture_output=True, text=True, cwd=ROOT)
    return json.loads(out.stdout.strip().splitlines()[-1])


def app_catalogs() -> list:
    """bundle/locales/<lingua>.json: le voci dei cataloghi di SoundText che
    usa l'interfaccia dell'app (locales/extract.py, mobile_strings)."""
    sys.path.insert(0, os.path.join(ROOT, "locales"))
    try:
        from extract import mobile_strings
    finally:
        sys.path.pop(0)
    wanted = mobile_strings()
    out_dir = os.path.join(BUNDLE, "locales")
    os.makedirs(out_dir, exist_ok=True)
    languages = []
    for fname in sorted(os.listdir(os.path.join(ROOT, "locales"))):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(ROOT, "locales", fname), encoding="utf-8") as f:
            catalog = json.load(f)
        subset = {k: catalog[k] for k in sorted(wanted) if catalog.get(k)}
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8") as f:
            json.dump(subset, f, ensure_ascii=False, indent=0)
        languages.append(fname[:-5])
    return languages


def build():
    modules = engine_core_modules()
    os.makedirs(os.path.join(BUNDLE, "examples"), exist_ok=True)
    zpath = os.path.join(BUNDLE, "engine.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(HERE, "engine.py"), "engine.py")
        for name in modules:
            rel = name.replace(".", "/") + ("/__init__.py" if name == "core" else ".py")
            z.write(os.path.join(ROOT, rel), rel)
        locales = os.path.join(ROOT, "locales")
        for fname in sorted(os.listdir(locales)):
            if fname.endswith(".json"):
                z.write(os.path.join(locales, fname), "locales/" + fname)
    languages = app_catalogs()
    for name in EXAMPLES:
        with open(example_path(name), "rb") as src, \
                open(os.path.join(BUNDLE, "examples", name), "wb") as dst:
            dst.write(src.read())
    # le lingue della dettatura: i modelli di Vosk scaricati da scarica_vendor.sh
    vosk = os.path.join(HERE, "vendor", "vosk")
    voice = sorted(f[:-7] for f in os.listdir(vosk) if f.endswith(".tar.gz")) if os.path.isdir(vosk) else []
    # le wheel che il motore carica (st-language, mido): l'elenco di scarica_vendor.sh
    wheels_json = os.path.join(HERE, "vendor", "wheels", "wheels.json")
    wheels = json.load(open(wheels_json, encoding="utf-8")) if os.path.exists(wheels_json) else None
    info = {"core_modules": modules, "examples": EXAMPLES, "languages": languages, "voice": voice,
            "wheels": wheels,
            "engine_zip_bytes": os.path.getsize(zpath)}
    with open(os.path.join(BUNDLE, "files.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=1)
    print(f"bundle: {len(modules)} moduli di core/, engine.zip {info['engine_zip_bytes'] // 1024} KB, "
          f"{len(EXAMPLES)} esempi")


if __name__ == "__main__":
    build()
