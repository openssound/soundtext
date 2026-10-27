"""
SoundFont gratuiti per "Scarica e installa" (core.downloads): solo con
licenze che permettono di scaricarli e usarli liberamente, anche per musica
commerciale. Vanno nella cartella dei SoundFont di SoundText (la stessa da
cui partono Opzioni -> SoundFont e la scelta per strumento), ciascuno con il
file della sua licenza accanto.
"""

import os
import shutil
import tarfile
import tempfile
import urllib.request
from dataclasses import dataclass
from typing import Callable, List, Optional

from .project_io import DEFAULT_SOUNDFONTS_DIR, USER_SOUNDFONTS_DIR, ensure_soundfonts_dir


@dataclass
class SoundFontSource:
    key: str                    # voce di "Scarica e installa"
    label: str
    detail: str                 # licenza e dimensione
    url: str                    # il .sf2/.sf3, o un archivio .tar.* che lo contiene
    file: str                   # nome del SoundFont nella cartella
    license_url: str = ""       # file di licenza da scaricare accanto
    license_text: str = ""      # oppure: la nota di licenza da scrivere accanto


SOUNDFONTS: List[SoundFontSource] = [
    SoundFontSource(
        "sf-musescore", "MuseScore General",
        "MIT, ~38 MB: General MIDI completo, l'evoluzione del FluidR3 di SoundText",
        "https://ftp.osuosl.org/pub/musescore/soundfont/MuseScore_General/MuseScore_General.sf3",
        "MuseScore_General.sf3",
        license_url="https://ftp.osuosl.org/pub/musescore/soundfont/MuseScore_General/MuseScore_General_License.md"),
    SoundFontSource(
        "sf-timgm6mb", "TimGM6mb",
        "GPL-2.0, ~6 MB: General MIDI completo e leggero, per computer poco potenti",
        "https://deb.debian.org/debian/pool/main/t/timgm6mb-soundfont/timgm6mb-soundfont_1.3.orig.tar.gz",
        "TimGM6mb.sf2",
        license_text="TimGM6mb.sf2\n"
                     "Copyright 2004 Tim Brechbill <https://www.timbrechbill.com>\n"
                     "          2010 David Bolton <davidkbolton@gmail.com>\n\n"
                     "Licenza: GNU General Public License versione 2 (https://www.gnu.org/licenses/gpl-2.0.html).\n"
                     "Fonte: pacchetto Debian timgm6mb-soundfont, dal repository di MuseScore.\n"),
    SoundFontSource(
        "sf-freepats-drums", "FreePats GM, percussioni",
        "GPL-3.0 con eccezione per l'uso musicale, ~15 MB: kit di batteria General MIDI (43 suoni su 47)",
        "https://freepats.zenvoid.org/SoundSets/GM-PercussionSet/FreePatsGM-Percussion-SF2-20200822.tar.xz",
        "FreePatsGM-Percussion-20200822.sf2"),
]


def find(key: str) -> Optional[SoundFontSource]:
    return next((s for s in SOUNDFONTS if s.key == key), None)


def installed_path(source: SoundFontSource) -> str:
    """Dove si trova il SoundFont, se e' gia' stato scaricato ('' altrimenti)."""
    for folder in (USER_SOUNDFONTS_DIR, DEFAULT_SOUNDFONTS_DIR):
        path = os.path.join(folder, source.file)
        if os.path.isfile(path):
            return path
    return ""


def _license_name(source: SoundFontSource) -> str:
    return os.path.splitext(source.file)[0] + "-LICENSE" + (".md" if source.license_url.endswith(".md") else ".txt")


def download(source: SoundFontSource, fetch: Callable[[str, str], None] = None,
             log: Callable[[str], None] = print) -> str:
    """Scarica il SoundFont (fetch(url, percorso): di solito scarica_file di
    scarica_strumenti, che riprende i download interrotti) e ne mette accanto
    la licenza. Ritorna il percorso del SoundFont."""
    fetch = fetch or _plain_fetch
    folder = ensure_soundfonts_dir()
    target = os.path.join(folder, source.file)
    with tempfile.TemporaryDirectory(prefix="soundfont-") as tmp:
        name = source.url.rsplit("/", 1)[-1]
        archive = os.path.join(tmp, name)
        fetch(source.url, archive)
        if name.endswith(source.file):
            shutil.move(archive, target + ".part")
        else:
            _extract_member(archive, source.file, target + ".part", folder)
        os.replace(target + ".part", target)
        if source.license_url:
            fetch(source.license_url, os.path.join(tmp, "license"))
            shutil.copyfile(os.path.join(tmp, "license"), os.path.join(folder, _license_name(source)))
    if source.license_text:
        with open(os.path.join(folder, _license_name(source)), "w", encoding="utf-8") as f:
            f.write(source.license_text)
    log(f"   -> {target}")
    return target


def _extract_member(archive: str, file: str, target: str, folder: str):
    """Dall'archivio .tar.* il SoundFont 'file' (in target) e i testi di
    licenza che ha accanto (in folder, con il nome del SoundFont davanti)."""
    with tarfile.open(archive) as tar:
        members = [m for m in tar.getmembers() if m.isfile()]
        soundfont = next((m for m in members if os.path.basename(m.name) == file), None)
        if soundfont is None:
            raise RuntimeError(f"nell'archivio manca {file}")
        with tar.extractfile(soundfont) as src, open(target, "wb") as dst:
            shutil.copyfileobj(src, dst)
        stem = os.path.splitext(file)[0]
        for m in members:
            base = os.path.basename(m.name)
            if os.path.dirname(m.name) == os.path.dirname(soundfont.name) and base.lower().endswith(".txt"):
                with tar.extractfile(m) as src, open(os.path.join(folder, f"{stem}-{base}"), "wb") as dst:
                    shutil.copyfileobj(src, dst)


def _plain_fetch(url: str, path: str):
    request = urllib.request.Request(url, headers={"User-Agent": "SoundText"})
    with urllib.request.urlopen(request, timeout=60) as response, open(path, "wb") as f:
        shutil.copyfileobj(response, f)
