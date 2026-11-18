"""
Benchmark di SoundText: le stesse misure prima e dopo ogni modifica che
tocca memoria o prestazioni (vedi le note di rilascio interne).

    python tools/benchmark.py            # tabella
    python tools/benchmark.py --json out.json
    python tools/benchmark.py --quick    # senza i render (secondi invece di minuti)

Misure:
- apertura e analisi di examples/symphony_d_minor_box.st;
- validazione (validate_track_text + notation_warnings) di una traccia di
  500 battute;
- render completo (core.playback.render_project_mix) di jazz_aaba.st e di
  un esempio con effetti, ciascuno in un sottoprocesso separato (le cache di
  un render non falsano il successivo) con tempo, picco di RAM del processo
  e dimensione del mix; il primo render e' anche il "primo della sessione"
  (SoundFont non ancora caricato);
- dimensione della cache su disco dopo i render (in una cartella temporanea).

Plugin LV2, profili NAM e SFZ mancanti vengono saltati con un avviso, come
nel programma: il benchmark lo dice. Non e' incluso negli installer.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

EXAMPLES = os.path.join(ROOT, "examples")
OPEN_EXAMPLE = "symphony_d_minor_box.st"
RENDER_EXAMPLES = ["jazz_aaba.st",
                   "hardrock_4_electric_storm__sfz__plugin-ts9-areverb__nam-twin-jcm900-mesa4-5150.st"]


def _isolated_config():
    """Configurazione in una cartella temporanea (come i test)."""
    if "SOUNDTEXT_CONFIG_DIR" not in os.environ:
        os.environ["SOUNDTEXT_CONFIG_DIR"] = tempfile.mkdtemp(prefix="soundtext-bench-config-")


def measure_open() -> dict:
    from core.project_io import load_project_file
    path = os.path.join(EXAMPLES, OPEN_EXAMPLE)
    start = time.perf_counter()
    project = load_project_file(path)
    return {"name": "Apertura " + OPEN_EXAMPLE, "seconds": time.perf_counter() - start,
            "detail": f"{len(project.tracks)} tracce"}


def long_track_text(bars: int = 500) -> str:
    bar = "c d e f g a b c"
    return "8: " + " | ".join(bar for _ in range(bars)) + " |"


def measure_validation(bars: int = 500) -> dict:
    from core.model import Project
    from core.notation import notation_warnings, validate_track_text
    project = Project()
    text = long_track_text(bars)
    start = time.perf_counter()
    ok, _msg = validate_track_text(text, project.patterns)
    middle = time.perf_counter()
    notation_warnings(text, project.patterns, project.time_sig, project.metrica_changes,
                      pickup=project.pickup, key=project.key, key_changes=project.key_changes)
    end = time.perf_counter()
    return {"name": f"Validazione di {bars} battute", "seconds": end - start,
            "detail": f"sintassi {1000 * (middle - start):.0f} ms, avvisi {1000 * (end - middle):.0f} ms"
                      + ("" if ok else " (testo non valido!)")}


def _render_child(example: str, cache_dir: str) -> dict:
    """Nel sottoprocesso: un render completo, con picco di RAM."""
    import logging
    logging.basicConfig(level=logging.WARNING, format="  avviso: %(message)s", stream=sys.stderr)
    from core import disk_cache
    from core.memory import peak_rss_mb
    from core.playback import render_project_mix
    from core.project_io import load_project_file
    project = load_project_file(os.path.join(EXAMPLES, example))
    disk_cache.set_project(os.path.join(cache_dir, os.path.splitext(example)[0] + ".st"))
    start = time.perf_counter()
    mixed, rate = render_project_mix(project)
    seconds = time.perf_counter() - start
    disk_cache.wait_writes(60.0)
    return {"seconds": seconds, "peak_mb": peak_rss_mb(), "mix_mb": mixed.nbytes / 1024 ** 2,
            "duration": len(mixed) / float(rate),
            "cache_mb": disk_cache.dir_size(disk_cache.cache_dir()) / 1024 ** 2}


def measure_render(example: str, cache_dir: str) -> dict:
    proc = subprocess.run([sys.executable, os.path.abspath(__file__), "--child", example, cache_dir],
                          capture_output=True, text=True, env=os.environ.copy())
    if proc.stderr.strip():
        sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        return {"name": "Render " + example, "error": proc.stderr.strip().splitlines()[-1:] or ["?"]}
    result = json.loads(proc.stdout.strip().splitlines()[-1])
    peak = result["peak_mb"]
    return {"name": "Render " + example, "seconds": result["seconds"], "peak_mb": peak,
            "detail": f"{result['duration'] / 60:.0f}:{result['duration'] % 60:02.0f} di brano, mix "
                      f"{result['mix_mb']:.0f} MB, picco {peak:.0f} MB "
                      f"(x {peak / max(1.0, result['mix_mb']):.0f}), cache {result['cache_mb']:.0f} MB"}


def print_table(rows):
    width = max(len(r["name"]) for r in rows)
    for r in rows:
        if "error" in r:
            print(f"{r['name']:<{width}}  ERRORE: {r['error'][0]}")
        else:
            print(f"{r['name']:<{width}}  {r['seconds']:7.2f} s  {r.get('detail', '')}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", metavar="FILE", help="salva i risultati in un file JSON")
    parser.add_argument("--quick", action="store_true", help="salta i render")
    parser.add_argument("--child", nargs=2, help=argparse.SUPPRESS)
    args = parser.parse_args()
    _isolated_config()
    if args.child:
        print(json.dumps(_render_child(*args.child)))
        return
    from core.version import APP_VERSION
    rows = [measure_open(), measure_validation()]
    if not args.quick:
        with tempfile.TemporaryDirectory(prefix="soundtext-bench-cache-") as cache_dir:
            for example in RENDER_EXAMPLES:
                rows.append(measure_render(example, cache_dir))
    print(f"SoundText {APP_VERSION}, Python {sys.version.split()[0]}, {sys.platform}")
    print_table(rows)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"version": APP_VERSION, "python": sys.version.split()[0], "platform": sys.platform,
                       "results": rows}, f, indent=1)


if __name__ == "__main__":
    main()
