#!/usr/bin/env python3
"""Propone (o scrive) i riferimenti fissi dei plugin gratuiti di scarica_strumenti.py: per ogni repository delle tabelle
PLUGIN_VST3, PLUGIN_LV2 e PLUGIN_CLAP, e per Surge XT e sfizz, il tag della release e lo SHA-256 di ogni file che
SoundText scarica (i nomi che corrispondono ai modelli per sistema). Gli SHA-256 li danno le API di GitHub (campo
"digest" di ogni file): non si scarica nessun programma.

    python tools/aggiorna_pin_plugin.py            # stampa le righe nuove e quello che cambia
    python tools/aggiorna_pin_plugin.py --scrivi   # le scrive in scarica_strumenti.py (fra PIN_INIZIO e PIN_FINE)

L'aggiornamento e' una scelta: si guarda la differenza, si prova, si fa un commit. Con GITHUB_TOKEN nell'ambiente le API
concedono piu' richieste.
"""

import argparse
import importlib.util
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scarica_strumenti.py"
INIZIO, FINE = "# --- PIN_INIZIO (scritto da tools/aggiorna_pin_plugin.py) ---", "# --- PIN_FINE ---"
G_INIZIO, G_FINE = "# --- PIN_GIT_INIZIO (scritto da tools/aggiorna_pin_plugin.py) ---", "# --- PIN_GIT_FINE ---"


def carica_script():
    spec = importlib.util.spec_from_file_location("scarica_strumenti", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["scarica_strumenti"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


def richiesta(url):
    headers = {"User-Agent": "SoundText-pin", "Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as resp:
        return json.load(resp)


def repository(s) -> dict:
    """{repo: (release da cercare, [modelli])} da tutte le tabelle."""
    out = {}
    for tabella in (s.PLUGIN_VST3, s.PLUGIN_LV2, s.PLUGIN_CLAP):
        for _nome, _desc, repo, release, modelli in tabella:
            voce = out.setdefault(repo, [release, set()])
            voce[1].update(modelli.values())
    # Surge XT e sfizz: i modelli sono scritti dentro host_windows_macos
    out.setdefault(s.SURGE_REPO, ["latest", set()])[1].update(
        [r"surge-xt-win64-[\d.]+-pluginsonly\.zip", r"surge-xt-macos-[\d.]+-pluginsonly\.zip",
         r"surge-xt-portable-content-[\d.]+\.tar\.gz"])
    out.setdefault(s.SFIZZ_UI_REPO, ["latest", set()])[1].update([r"sfizz-[\d.]+-win64\.exe", r"sfizz-[\d.]+-macos\.pkg"])
    return out


def raccogli(repos: dict, log=print, senza=None) -> tuple:
    """({repo: {"tag", "sha256": {file: sha}}}, [avvisi]); 'senza' raccoglie (repo, file, url) dei file senza SHA-256
    nelle API (valore vuoto nel risultato)."""
    pin, avvisi = {}, []
    senza = senza if senza is not None else []
    for repo, (release, modelli) in sorted(repos.items()):
        if release not in ("latest",):
            avvisi.append(f"{repo}: la release «{release}» e' un tag mobile, non si fissa per tag (solo gli SHA-256 dei file)")
        api = f"https://api.github.com/repos/{repo}/releases/" + ("latest" if release == "latest" else f"tags/{release}")
        try:
            dati = richiesta(api)
        except Exception as e:                                  # noqa: BLE001
            avvisi.append(f"{repo}: {e}")
            continue
        sha = {}
        for asset in dati.get("assets", []):
            if any(re.fullmatch(m, asset["name"]) for m in modelli):
                digest = asset.get("digest") or ""
                if digest.startswith("sha256:"):
                    sha[asset["name"]] = digest[7:]
                else:                                           # le release vecchie non hanno il "digest"
                    sha[asset["name"]] = ""
                    senza.append((repo, asset["name"], asset["browser_download_url"]))
                    avvisi.append(f"{repo}: {asset['name']} non ha uno SHA-256 nelle API (si fissa con --calcola)")
        if sha:
            pin[repo] = {"tag": dati.get("tag_name", release), "sha256": sha}
        log(f"{repo}: {dati.get('tag_name', release)}, {len(sha)} file")
    return pin, avvisi


def testo(pin: dict) -> str:
    righe = [INIZIO, "PIN_PLUGIN = {"]
    for repo in sorted(pin):
        righe.append(f'    "{repo}": {{"tag": "{pin[repo]["tag"]}", "sha256": {{')
        for nome in sorted(pin[repo]["sha256"]):
            righe.append(f'        "{nome}": "{pin[repo]["sha256"][nome]}",')
        righe.append("    }},")
    righe += ["}", FINE]
    return "\n".join(righe)


def commit_git(s) -> dict:
    """{url: commit} del ramo principale di ogni repository .git delle tabelle (git ls-remote: niente si scarica)."""
    import subprocess
    out = {}
    for tabella in (s.GRUPPI, s.EXTRA, s.EXTRA_GRUPPI):
        for voce in tabella:
            url = voce[2] if len(voce) > 2 else ""
            if isinstance(url, str) and url.endswith(".git") and url not in out:
                r = subprocess.run(["git", "ls-remote", url, "HEAD"], capture_output=True, text=True, timeout=120)
                if r.returncode == 0 and r.stdout.strip():
                    out[url] = r.stdout.split()[0]
                else:
                    print("avviso:", url, "non risponde a git ls-remote")
    return out


def testo_git(git: dict) -> str:
    righe = [G_INIZIO, "PIN_GIT = {"] + [f'    "{url}": "{git[url]}",' for url in sorted(git)] + ["}", G_FINE]
    return "\n".join(righe)


def scrivi(pin: dict, git: dict):
    s = SCRIPT.read_text(encoding="utf-8")
    for ini, fin, nuovo in ((INIZIO, FINE, testo(pin)), (G_INIZIO, G_FINE, testo_git(git))):
        if ini not in s or fin not in s:
            raise SystemExit("mancano i marcatori dei riferimenti fissi in scarica_strumenti.py")
        a, b = s.index(ini), s.index(fin) + len(fin)
        s = s[:a] + nuovo + s[b:]
    SCRIPT.write_text(s, encoding="utf-8")


def calcola(s, pin: dict, senza: list):
    """Scarica (senza eseguire niente) i file che non hanno lo SHA-256 nelle API e ne calcola lo SHA-256. Scarica
    programmi di terzi: si usa solo dopo aver deciso di farlo."""
    import tempfile
    for repo, nome, url in senza:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / nome
            s._scarica_file(url, dest, silenzioso=True)
            pin[repo]["sha256"][nome] = s._sha256_file(dest)
        print(f"{repo}: {nome} -> {pin[repo]['sha256'][nome][:12]}...")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--scrivi", action="store_true")
    p.add_argument("--calcola", action="store_true", help="scarica i file senza SHA-256 nelle API e lo calcola")
    args = p.parse_args()
    script = carica_script()
    senza = []
    pin, avvisi = raccogli(repository(script), senza=senza)
    if args.calcola:
        calcola(script, pin, senza)
        avvisi = [a for a in avvisi if "con --calcola" not in a]
    for a in avvisi:
        print("avviso:", a)
    git = commit_git(script)
    if args.scrivi:
        scrivi(pin, git)
        print("scritto in", SCRIPT)
    else:
        print(testo(pin))
        print(testo_git(git))


if __name__ == "__main__":
    main()
