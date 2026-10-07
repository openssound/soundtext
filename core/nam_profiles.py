"""
Profili NAM consigliati: una dozzina di catture di amplificatori e pedali
famosi da scaricare con un comando (Strumenti → Scarica profili NAM
consigliati..., oppure python scarica_profili_nam.py).

I file vengono dalla raccolta della comunita' di Neural Amp Modeler su
GitHub (https://github.com/pelennor2170/NAM_models, licenza GNU GPL v3),
fissata a una revisione precisa: i file scaricati sono sempre gli stessi.
Finiscono nella cartella profili_nam/ accanto all'app (o in
~/SoundText/profili_nam se li' non si puo' scrivere), che non e'
versionata: ognuno li scarica sul proprio computer.

I file originali non hanno descrizioni: al download si aggiungono nome,
marca, modello, tipo e autore nei metadati (la licenza GPL lo consente),
cosi' nel pannello Effetti la card mostra che cosa si sta usando.
"""

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable, List, Optional

from .version import USER_DATA_ROOT, get_app_root, pick_writable_dir

SOURCE_REPO = "https://github.com/pelennor2170/NAM_models"
SOURCE_REVISION = "944ca6718581c60cc5365586d2f378d740e181f3"
RAW_BASE = f"https://raw.githubusercontent.com/pelennor2170/NAM_models/{SOURCE_REVISION}/"

DEFAULT_NAM_DIR = os.path.join(get_app_root(), "profili_nam")
USER_NAM_DIR = os.path.join(USER_DATA_ROOT, "profili_nam")


def ensure_nam_dir() -> str:
    return pick_writable_dir(DEFAULT_NAM_DIR, USER_NAM_DIR)


def existing_nam_dir() -> str:
    """La cartella dei profili se esiste gia' (per i dialoghi), altrimenti ''."""
    for path in (DEFAULT_NAM_DIR, USER_NAM_DIR):
        if os.path.isdir(path):
            return path
    return ""


@dataclass(frozen=True)
class Profile:
    file: str            # nome del file salvato
    source: str          # nome del file nella raccolta
    name: str
    gear_make: str
    gear_model: str
    gear_type: str       # "amp", "amp_cab" o "pedal"
    modeled_by: str
    use: str             # a che cosa serve (per il README e la guida)


PROFILES: List[Profile] = [
    Profile("Fender Twin Reverb - pulito.nam", "Tim R Fender TwinVerb Norm Bright.nam",
            "Fender Twin Reverb - pulito", "Fender", "Twin Reverb", "amp", "Tim R",
            "il pulito americano brillante: funk, pop, arpeggi"),
    Profile("Vox AC15 - Top Boost.nam", "Phillipe P VOXAC15-TopBoost.nam",
            "Vox AC15 - Top Boost", "Vox", "AC15", "amp", "Phillipe P",
            "il suono \"chime\" britannico, pulito che si sporca col tocco"),
    Profile("Bugera 333 - crunch con cassa.nam", "Phillipe P Bug333-Crunch-NoDrive-Cab-ESR0,005.nam",
            "Bugera 333 - crunch con cassa", "Bugera", "333", "amp_cab", "Phillipe P",
            "crunch rock gia' completo di cassa: si usa senza IR"),
    Profile("Marshall JCM2000 - crunch.nam", "Tim R JCM2000 Crunch.nam",
            "Marshall JCM2000 - crunch", "Marshall", "JCM2000 DSL", "amp", "Tim R",
            "il crunch Marshall: rock classico, blues rock"),
    Profile("Marshall JCM900 - lead.nam", "Tim R JCM90050WDualVerbChBG12.nam",
            "Marshall JCM900 - lead", "Marshall", "JCM900 Dual Reverb", "amp", "Tim R",
            "hard rock e assoli anni '90"),
    Profile("Mesa Boogie Mark IV - lead.nam", "Roman A LT_MESA_MARKIV_1.nam",
            "Mesa Boogie Mark IV - lead", "Mesa/Boogie", "Mark IV", "amp", "Roman A",
            "lead e ritmiche metal compatte"),
    Profile("Peavey 5150 - high gain.nam", "Helga B 5150 BlockLetter - NoBoost.nam",
            "Peavey 5150 - high gain", "Peavey", "5150 (block letter)", "amp", "Helga B",
            "il classico del metal"),
    Profile("Ibanez TS9 Tube Screamer.nam", "Tim R TS9.nam",
            "Ibanez TS9 Tube Screamer", "Ibanez", "TS9 Tube Screamer", "pedal", "Tim R",
            "il pedale overdrive piu' diffuso: davanti a un amplificatore"),
    Profile("Klon Centaur (clone).nam", "Keith B klone_g6_t6_o5.nam",
            "Klon Centaur (clone)", "Klon", "Centaur (clone)", "pedal", "Keith B",
            "overdrive trasparente: spinge l'amplificatore senza cambiarne il carattere"),
    Profile("Boss HM-2 - svedese.nam", "Peter N HM-2_SWEDE_Std_ESR-0.0034.nam",
            "Boss HM-2 - svedese", "Boss", "HM-2 Heavy Metal", "pedal", "Peter N",
            "il pedale del death metal svedese"),
    Profile("Tech 21 dUg DP3X - basso.nam", "Jason Z Tech21 dUg DP3X bass preamp pedal all dimed no shift.nam",
            "Tech 21 dUg DP3X - basso", "Tech 21", "dUg Pinnick DP3X", "pedal", "Jason Z",
            "preamplificatore distorto per basso"),
]


def _with_metadata(data: dict, profile: Profile) -> dict:
    meta = dict(data.get("metadata") or {})
    for key in ("name", "gear_make", "gear_model", "gear_type", "modeled_by"):
        if not meta.get(key):
            meta[key] = getattr(profile, key)
    data["metadata"] = meta
    return data


def _readme(folder: str) -> None:
    lines = ["Profili NAM consigliati da SoundText", "",
             f"Provenienza: {SOURCE_REPO} (revisione {SOURCE_REVISION[:7]}),",
             "catture fatte dalla comunita' di Neural Amp Modeler, licenza GNU GPL v3.",
             "Ai file sono stati aggiunti nei metadati nome, marca, modello, tipo e autore.", ""]
    for p in PROFILES:
        lines.append(f"- {p.file}: {p.use} (cattura di {p.modeled_by}; originale: {p.source})")
    lines += ["", "Gli amplificatori senza cassa vanno usati con una cassa: nella card del",
              "Profilo NAM scegli Cassa -> File IR... Quelli \"con cassa\" e i pedali no."]
    with open(os.path.join(folder, "LEGGIMI.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def download_profiles(folder: Optional[str] = None,
                      progress: Optional[Callable[[int, int, str], None]] = None,
                      should_stop: Optional[Callable[[], bool]] = None,
                      opener: Callable = urllib.request.urlopen) -> dict:
    """Scarica i profili consigliati che mancano in folder (predefinita:
    ensure_nam_dir()). progress(i, totale, nome) prima di ogni file.
    Restituisce {"folder", "downloaded", "present", "failed": [(file, motivo)]}."""
    from .nam import nam_problem
    folder = folder or ensure_nam_dir()
    os.makedirs(folder, exist_ok=True)
    result = {"folder": folder, "downloaded": [], "present": [], "failed": []}
    for i, profile in enumerate(PROFILES):
        if should_stop is not None and should_stop():
            break
        if progress is not None:
            progress(i, len(PROFILES), profile.name)
        path = os.path.join(folder, profile.file)
        if os.path.exists(path) and not nam_problem(path):
            result["present"].append(profile.file)
            continue
        url = RAW_BASE + urllib.parse.quote(profile.source)
        tmp = path + ".part"
        try:
            with opener(url, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(_with_metadata(data, profile), f, separators=(",", ":"))
            problem = nam_problem(tmp)
            if problem:
                raise ValueError(problem)
            os.replace(tmp, path)
            result["downloaded"].append(profile.file)
        except Exception as e:                      # rete, file rovinato...: si prosegue
            if os.path.exists(tmp):
                os.remove(tmp)
            result["failed"].append((profile.file, str(e) or e.__class__.__name__))
    if progress is not None:
        progress(len(PROFILES), len(PROFILES), "")
    _readme(folder)
    return result
