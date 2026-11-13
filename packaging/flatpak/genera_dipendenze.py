#!/usr/bin/env python3
"""Scrive python-deps.json: il modulo Flatpak che installa i pacchetti
Python di requirements.txt dalle wheel di PyPI, ognuna con il suo SHA-256
(durante la build Flatpak non c'e' rete: tutto va dichiarato prima).

Va rilanciato quando cambia requirements.txt o la versione di Python del
runtime (PYTHON, sotto: org.freedesktop.Platform 24.08 ha Python 3.12).

    python3 packaging/flatpak/genera_dipendenze.py

Usa "pip install --dry-run --report": non installa niente."""

import json
import os
import subprocess
import sys
import tempfile

PYTHON = "3.12"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PLATFORMS = ["manylinux_2_28_x86_64", "manylinux_2_27_x86_64", "manylinux_2_17_x86_64",
             "manylinux2014_x86_64", "linux_x86_64"]


def main():
    abi = "cp" + PYTHON.replace(".", "")
    with tempfile.TemporaryDirectory() as tmp:
        report = os.path.join(tmp, "report.json")
        command = [sys.executable, "-m", "pip", "install", "--dry-run", "--ignore-installed", "--quiet",
                   "--only-binary=:all:", "--python-version", PYTHON, "--implementation", "cp",
                   "--abi", abi, "--abi", "abi3", "--abi", "none", "--target", os.path.join(tmp, "x"),
                   "-r", os.path.join(ROOT, "requirements.txt"), "--report", report]
        for platform in PLATFORMS:
            command += ["--platform", platform]
        subprocess.run(command, check=True)
        with open(report, encoding="utf-8") as f:
            items = json.load(f)["install"]
    sources, names = [], []
    for item in sorted(items, key=lambda i: i["metadata"]["name"].lower()):
        info = item["download_info"]
        sources.append({"type": "file", "url": info["url"], "sha256": info["archive_info"]["hashes"]["sha256"]})
        names.append(f'{item["metadata"]["name"]}=={item["metadata"]["version"]}')
    module = {
        "name": "python-deps",
        "buildsystem": "simple",
        "build-commands": [
            'pip3 install --verbose --exists-action=i --no-index --find-links="file://${PWD}" '
            '--prefix=${FLATPAK_DEST} --no-build-isolation ' + " ".join(f'"{n}"' for n in names)
        ],
        "sources": sources,
    }
    out = os.path.join(HERE, "python-deps.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(module, f, indent=4)
        f.write("\n")
    print(f"{out}: {len(names)} pacchetti")


if __name__ == "__main__":
    main()
