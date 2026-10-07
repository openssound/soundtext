"""
Casse consigliate per i profili NAM di sola testata: una ventina di
risposte all'impulso (IR) di casse per chitarra da scaricare con un comando
(Strumenti → Scarica casse IR per gli amplificatori NAM...).

I file sono il pacchetto "BestPlugins Mega Pack 2" di David Fau Casquel
(2013), che l'autore ha rilasciato con licenza GNU GPL v2 o successiva per
il repository di Guitarix (https://github.com/brummer10/guitarix,
trunk/IR/BestPlugins_Amps), fissato a una revisione precisa: i file
scaricati sono sempre gli stessi. Ogni file prende il nome
dell'amplificatore di cui riproduce la cassa. Finiscono nella sottocartella
casse/ dei profili NAM (vedi core.nam_profiles), che non e' versionata:
ognuno li scarica sul proprio computer, insieme al testo della licenza.
"""

import os
import urllib.parse
import urllib.request
from typing import Callable, List, Optional

from .nam_profiles import DEFAULT_NAM_DIR, USER_NAM_DIR
from .version import pick_writable_dir

SOURCE_REPO = "https://github.com/brummer10/guitarix"
SOURCE_REVISION = "a4c561ad9d411748589287c3834f1b921726f3fa"
SOURCE_DIR = "trunk/IR/BestPlugins_Amps/"
RAW_BASE = f"https://raw.githubusercontent.com/brummer10/guitarix/{SOURCE_REVISION}/{SOURCE_DIR}"

DEFAULT_CAB_DIR = os.path.join(DEFAULT_NAM_DIR, "casse")
USER_CAB_DIR = os.path.join(USER_NAM_DIR, "casse")

CABINETS: List[str] = [
    "Blackat Leon S7.wav",
    "Cicognani Imperivm Luxury.wav",
    "DV Mark Triple 6.wav",
    "EVH 5150 III.wav",
    "Engl Retro Tube.wav",
    "Engl Special Edition.wav",
    "Fortin Natas.wav",
    "Kaos Sludge 15.wav",
    "Krank Krankenstein.wav",
    "Laney ironheart.wav",
    "MakosampCustomHatred.wav",
    "Marshall JMP 2203  Jose Arredondo mod.wav",
    "Marshall MG 15.wav",
    "Mesa Boogie Mark V.wav",
    "Peavey Vypyr 15.wav",
    "Randall Satan.wav",
    "Randall thrasher.wav",
    "Splawn Nitro.wav",
    "Splawn Quick Rod.wav",
    "Taurus Stomphead.wav",
]


def ensure_cab_dir() -> str:
    return pick_writable_dir(DEFAULT_CAB_DIR, USER_CAB_DIR)


def existing_cab_dir() -> str:
    """La cartella delle casse se esiste gia' (per i dialoghi), altrimenti ''."""
    for path in (DEFAULT_CAB_DIR, USER_CAB_DIR):
        if os.path.isdir(path):
            return path
    return ""


def _readme(folder: str) -> None:
    lines = ["Casse (IR) consigliate da SoundText per i profili NAM di sola testata", "",
             "Pacchetto \"BestPlugins Mega Pack 2\" di David Fau Casquel (2013),",
             "licenza GNU GPL v2 o successiva (testo in LICENSE.txt),",
             f"dal repository di Guitarix: {SOURCE_REPO} (revisione {SOURCE_REVISION[:7]},",
             f"cartella {SOURCE_DIR}).", "",
             "Ogni file prende il nome dell'amplificatore di cui riproduce la cassa.",
             "Si usano nella card Profilo NAM (o Amplificatore): Cassa -> File IR...", ""]
    lines += [f"- {name}" for name in CABINETS]
    with open(os.path.join(folder, "LEGGIMI.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _fetch(opener: Callable, name: str) -> bytes:
    with opener(RAW_BASE + urllib.parse.quote(name), timeout=60) as response:
        return response.read()


def download_cabinets(folder: Optional[str] = None,
                      progress: Optional[Callable[[int, int, str], None]] = None,
                      should_stop: Optional[Callable[[], bool]] = None,
                      opener: Callable = urllib.request.urlopen) -> dict:
    """Scarica le casse che mancano in folder (predefinita: ensure_cab_dir()),
    piu' il testo della licenza. progress(i, totale, nome) prima di ogni file.
    Restituisce {"folder", "downloaded", "present", "failed": [(file, motivo)]}."""
    from .effects import ir_file_problem
    folder = folder or ensure_cab_dir()
    os.makedirs(folder, exist_ok=True)
    result = {"folder": folder, "downloaded": [], "present": [], "failed": []}
    for i, name in enumerate(CABINETS):
        if should_stop is not None and should_stop():
            break
        if progress is not None:
            progress(i, len(CABINETS), name)
        path = os.path.join(folder, name)
        if not ir_file_problem(path):
            result["present"].append(name)
            continue
        tmp = path + ".part"
        try:
            with open(tmp, "wb") as f:
                f.write(_fetch(opener, name))
            problem = ir_file_problem(tmp)
            if problem:
                raise ValueError(problem)
            os.replace(tmp, path)
            result["downloaded"].append(name)
        except Exception as e:                      # rete, file rovinato...: si prosegue
            if os.path.exists(tmp):
                os.remove(tmp)
            result["failed"].append((name, str(e) or e.__class__.__name__))
    if progress is not None:
        progress(len(CABINETS), len(CABINETS), "")
    license_path = os.path.join(folder, "LICENSE.txt")
    if not os.path.exists(license_path):
        try:
            text = _fetch(opener, "LICENSE")
            with open(license_path, "wb") as f:
                f.write(text)
        except Exception:
            pass                                    # il LEGGIMI indica comunque la licenza
    _readme(folder)
    return result
