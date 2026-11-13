#!/usr/bin/env python3
"""Scrive python-deps.json: il modulo Flatpak che installa i pacchetti
Python di requirements.txt dalle wheel di PyPI, ognuna con il suo SHA-256
(durante la build Flatpak non c'e' rete: tutto va dichiarato prima).

Va rilanciato quando cambia requirements.txt o la versione di Python del
runtime (PYTHON, sotto: org.freedesktop.Platform 25.08 ha Python 3.13).

    python3 packaging/flatpak/genera_dipendenze.py

Usa "pip install --dry-run --report": non installa niente.

python-rtmidi resta fuori: su PyPI non ha wheel per Python 3.13, quindi il
manifest lo compila dai sorgenti in un modulo a parte."""

import json
import os
import subprocess
import sys
import tempfile

PYTHON = "3.13"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
# pacchetti senza wheel adatta: li compila il manifest
FROM_SOURCE = ("python-rtmidi",)
PLATFORMS = ["manylinux_2_28_x86_64", "manylinux_2_27_x86_64", "manylinux_2_17_x86_64",
             "manylinux2014_x86_64", "linux_x86_64"]


def _for_target(lines):
    """Le righe di requirements.txt che valgono per il Python del runtime.
    pip valuta i marcatori (python_version...) con l'interprete che lo
    lancia, non con --python-version: qui si valutano a mano e si tolgono."""
    from packaging.requirements import Requirement
    target = {"python_version": PYTHON, "python_full_version": PYTHON + ".0",
              "sys_platform": "linux", "platform_system": "Linux", "os_name": "posix",
              "platform_machine": "x86_64", "implementation_name": "cpython",
              "platform_python_implementation": "CPython"}
    out = []
    for line in lines:
        text = line.split("#", 1)[0].strip()
        if not text:
            continue
        req = Requirement(text)
        if req.name.lower() in FROM_SOURCE:
            continue
        if req.marker is not None and not req.marker.evaluate(target):
            continue
        out.append(f"{req.name}{req.specifier}\n")
    return out


def main():
    abi = "cp" + PYTHON.replace(".", "")
    with tempfile.TemporaryDirectory() as tmp:
        report = os.path.join(tmp, "report.json")
        requirements = os.path.join(tmp, "requirements.txt")
        with open(os.path.join(ROOT, "requirements.txt"), encoding="utf-8") as f:
            lines = _for_target(f)
        with open(requirements, "w", encoding="utf-8") as f:
            f.writelines(lines)
        command = [sys.executable, "-m", "pip", "install", "--dry-run", "--ignore-installed", "--quiet",
                   "--only-binary=:all:", "--python-version", PYTHON, "--implementation", "cp",
                   "--abi", abi, "--abi", "abi3", "--abi", "none", "--target", os.path.join(tmp, "x"),
                   "-r", requirements, "--report", report]
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
