"""
Prepara mobile/bundle/ per il prototipo SoundText Mobile (fase 0):

- engine.zip: mobile/engine.py, i moduli di core/ che servono al motore
  (quelli che Python carica davvero importando engine.ENGINE_MODULES,
  con PySide6 bloccato) e locales/*.json, da estrarre nel file system di
  Pyodide;
- examples/: gli esempi che la pagina propone;
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

EXAMPLES = [
    "jazz_aaba.st",
    "symphony_d_minor_box.st",
    "bossa_nova.st",
    "boom_bap.st",
]

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
for name in sys.argv[3:]:
    with open(os.path.join(root, "examples", name), encoding="utf-8") as f:
        source = f.read()
    engine.analyze(source, name, transpose=2)
    engine.check_text(source, name)
print(json.dumps(sorted(m for m in sys.modules if m == "core" or m.startswith("core."))))
"""


def engine_core_modules() -> list:
    out = subprocess.run([sys.executable, "-I", "-c", _PROBE, ROOT, HERE, *EXAMPLES],
                         check=True, capture_output=True, text=True, cwd=ROOT)
    return json.loads(out.stdout.strip().splitlines()[-1])


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
    for name in EXAMPLES:
        with open(os.path.join(ROOT, "examples", name), "rb") as src, \
                open(os.path.join(BUNDLE, "examples", name), "wb") as dst:
            dst.write(src.read())
    info = {"core_modules": modules, "examples": EXAMPLES,
            "engine_zip_bytes": os.path.getsize(zpath)}
    with open(os.path.join(BUNDLE, "files.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=1)
    print(f"bundle: {len(modules)} moduli di core/, engine.zip {info['engine_zip_bytes'] // 1024} KB, "
          f"{len(EXAMPLES)} esempi")


if __name__ == "__main__":
    build()
