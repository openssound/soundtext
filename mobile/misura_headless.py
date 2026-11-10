"""
Misura il prototipo in un browser senza finestra (Firefox headless):
serve mobile/ su 127.0.0.1, apre la pagina con ?misura=1 due volte con lo
stesso profilo nuovo (la prima senza cache, la seconda con la cache del
service worker) e stampa le misure che la pagina manda con un POST.

    python3 mobile/misura_headless.py [--browser firefox] [--json misure.json]
"""

import argparse
import functools
import http.server
import json
import os
import shutil
import subprocess
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    results = []
    arrived = threading.Event()

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        Handler.results.append(json.loads(body or b"[]"))
        Handler.arrived.set()
        self.send_response(204)
        self.end_headers()

    def log_message(self, *args):
        pass


def run(browser: str, out_json: str = ""):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=HERE))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}/?misura=1"
    profile = tempfile.mkdtemp(prefix="stmobile-profile-")
    try:
        for label in ("senza cache", "con cache"):
            Handler.arrived.clear()
            proc = subprocess.Popen([browser, "--headless", "--no-remote", "--profile", profile, url],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            ok = Handler.arrived.wait(240)
            proc.terminate()
            proc.wait(30)
            if not ok:
                raise SystemExit(f"nessuna misura dalla pagina ({label})")
            report(label, Handler.results[-1])
    finally:
        server.shutdown()
        shutil.rmtree(profile, ignore_errors=True)
    if out_json:
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(Handler.results, f, indent=1)


def report(label, entries):
    boot = [e for e in entries if e["kind"] == "avvio"][-1]
    print(f"--- {label}: {boot.get('ua', '')}")
    print(f"avvio motore {boot['total_ms']} ms (Pyodide {boot['pyodide_ms']}, numpy {boot['numpy_ms']}, "
          f"wheel {boot['wheels_ms']}, import core/ {boot['engine_import_ms']}); "
          f"caricati {boot['network']['decoded'] / 1048576:.1f} MB; heap wasm "
          f"{boot['heap_bytes'] / 1048576:.0f} MB")
    for e in entries:
        if e["kind"] == "analisi" and e["when"] >= boot["when"]:
            print(f"analisi {e['song']}: {e['worker_total_ms']} ms (lettura {e['parse_ms']}, MIDI {e['midi_ms']}, "
                  f"evidenziazione {e['spans_ms']})")
        if e["kind"] == "memoria" and e["when"] >= boot["when"] and e["when_label"].startswith("fine"):
            print("memoria:", {k: v for k, v in e.items() if k.endswith("bytes")})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--browser", default="firefox")
    ap.add_argument("--json", default="")
    args = ap.parse_args()
    run(args.browser, args.json)
