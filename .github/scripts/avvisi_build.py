#!/usr/bin/env python3
"""
Il file licenses/COMPONENTI.txt di una build di SoundText: le versioni
esatte di cio' che contiene (l'interprete Python e ogni pacchetto Python
installato nell'ambiente da cui PyInstaller l'ha costruita, piu' le righe
passate come argomenti, per esempio la versione di FluidSynth) e i testi di
licenza che quei pacchetti portano con se'. Le versioni dicono quali
sorgenti corrispondono a quella build (GPL e LGPL); i testi accompagnano i
binari, come chiedono le licenze BSD, MIT e Apache.

Uso (con il Python della build, dopo PyInstaller):
    python .github/scripts/avvisi_build.py USCITA [RIGA_IN_PIU ...]

Lo chiamano build-release.yml e gli script build-*-portable.
"""

import platform
import re
import sys
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Strumenti per costruire la build, non contenuti nel programma
STRUMENTI_DI_BUILD = {"pip", "setuptools", "wheel", "packaging", "pyinstaller", "pyinstaller-hooks-contrib",
                      "altgraph", "pefile", "pywin32-ctypes", "macholib"}
FILE_DI_LICENZA = re.compile(r"(?i)^(licen[cs]e|copying|notice|authors)")


def _versione_soundtext() -> str:
    m = re.search(r'APP_VERSION = "([^"]+)"', (ROOT / "core" / "version.py").read_text(encoding="utf-8"))
    return m.group(1) if m else "?"


def _licenza(dist) -> str:
    meta = dist.metadata
    for campo in ("License-Expression", "License"):
        valore = (meta.get(campo) or "").strip()
        if valore and len(valore) < 80 and "\n" not in valore:
            return valore
    classificatori = [c.rsplit(" :: ", 1)[-1] for c in meta.get_all("Classifier") or [] if c.startswith("License ::")]
    return ", ".join(classificatori) or "vedi i testi qui sotto"


def _testi_di_licenza(dist) -> list:
    """I file di licenza nella cartella .dist-info del pacchetto."""
    out = []
    for file in dist.files or []:
        parti = file.parts
        if not parti or not parti[0].endswith(".dist-info"):
            continue
        if FILE_DI_LICENZA.match(file.name) or "licenses" in parti[1:-1]:
            percorso = Path(dist.locate_file(file))
            if percorso.is_file():
                out.append((str(file), percorso.read_text(encoding="utf-8", errors="replace").strip()))
    return out


def _licenza_python() -> str:
    """La licenza dell'interprete: su Windows LICENSE.txt contiene anche il
    software che Python include (OpenSSL, libffi, SQLite, zlib...)."""
    base = Path(sys.base_prefix)
    for percorso in (base / "LICENSE.txt",
                     base / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "LICENSE.txt"):
        if percorso.is_file():
            return percorso.read_text(encoding="utf-8", errors="replace").strip()
    return "(LICENSE.txt dell'interprete non trovato: vedi licenses/Python-PSF.txt)"


def main(argv) -> int:
    if not argv:
        print(__doc__)
        return 2
    uscita, extra = Path(argv[0]), argv[1:]
    sep = "=" * 72
    pacchetti = sorted((d for d in metadata.distributions()
                        if d.metadata["Name"] and d.metadata["Name"].lower() not in STRUMENTI_DI_BUILD),
                       key=lambda d: d.metadata["Name"].lower())
    righe = [f"SoundText {_versione_soundtext()}: componenti di questa build",
             f"Sistema di build: {platform.system()} {platform.machine()}", "",
             "I sorgenti di SoundText sono su https://github.com/openssound/soundtext (al tag della",
             "versione); quelli di ogni componente sui siti dei progetti, alle versioni qui sotto.",
             "Le licenze di ciascuno sono riassunte in THIRD_PARTY_NOTICES.md.", "",
             f"Python {platform.python_version()} ({platform.python_implementation()})"]
    righe += [f"{d.metadata['Name']} {d.version} - {_licenza(d)}" for d in pacchetti]
    righe += extra
    parti = ["\n".join(righe) + "\n"]
    parti.append(f"{sep}\nPython {platform.python_version()} - LICENSE.txt dell'interprete\n{sep}\n\n"
                 f"{_licenza_python()}\n")
    for d in pacchetti:
        for nome, testo in _testi_di_licenza(d):
            parti.append(f"{sep}\n{d.metadata['Name']} {d.version} - {nome}\n{sep}\n\n{testo}\n")
    uscita.parent.mkdir(parents=True, exist_ok=True)
    uscita.write_text("\n".join(parti), encoding="utf-8")
    print(f"{uscita}: Python e {len(pacchetti)} pacchetti")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
