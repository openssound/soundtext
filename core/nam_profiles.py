"""
Profili NAM consigliati: una trentina di catture di amplificatori e pedali
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
    # -- amplificatori puliti e crunch
    Profile("Bugera 333 - pulito con cassa.nam", "Phillipe P Bug333-Clean-Cab-ESR0,007.nam",
            "Bugera 333 - pulito con cassa", "Bugera", "333", "amp_cab", "Phillipe P",
            "pulito gia' completo di cassa: si usa senza IR"),
    Profile("Marshall JVM - pulito con cassa.nam", "Phillipe P JVM-CL-GR-NoDrive-Cab-ESR0,007.nam",
            "Marshall JVM - pulito con cassa", "Marshall", "JVM (canale Clean)", "amp_cab", "Phillipe P",
            "il pulito del Marshall JVM, gia' con la cassa"),
    Profile("Marshall JVM - distorto con cassa.nam", "Phillipe P JVM-OD2-RD-NoDrive-Cab-ESR0,006.nam",
            "Marshall JVM - distorto con cassa", "Marshall", "JVM (canale OD2)", "amp_cab", "Phillipe P",
            "il canale distorto del Marshall JVM, gia' con la cassa"),
    Profile("Marshall JCM2000 - pulito.nam", "Tim R JCM2000 Clean.nam",
            "Marshall JCM2000 - pulito", "Marshall", "JCM2000 DSL", "amp", "Tim R",
            "il pulito Marshall, che completa il crunch e il lead"),
    Profile("Fender Twin Reverb - vibrato.nam", "Tim R Fender TwinVerb Vibrato Bright.nam",
            "Fender Twin Reverb - vibrato", "Fender", "Twin Reverb (canale Vibrato)", "amp", "Tim R",
            "l'altro canale del Twin, piu' caldo"),
    Profile("Magnatone Super 59 - pulito.nam", "Tim R Magnatone Super 59 Mkii Ch1 Norm.nam",
            "Magnatone Super 59 - pulito", "Magnatone", "Super 59 Mk II", "amp", "Tim R",
            "pulito boutique, ottimo per blues e country"),
    Profile("Magnatone Super 59 - spinto.nam", "Tim R Magnatone Super 59 Mkii Pushed.nam",
            "Magnatone Super 59 - spinto", "Magnatone", "Super 59 Mk II", "amp", "Tim R",
            "lo stesso Magnatone, spinto fino al crunch"),
    Profile("Friedman Dirty Shirley Mini - pulito.nam", "Sascha S DirtyShirleyMini_Clean_B1_M6_T7_MV10_G4.nam",
            "Friedman Dirty Shirley Mini - pulito", "Friedman", "Dirty Shirley Mini", "amp", "Sascha S",
            "il pulito del Friedman Dirty Shirley"),
    Profile("Friedman Dirty Shirley Mini - crunch.nam", "Sascha S DirtyShirleyMini_crunch_G6.nam",
            "Friedman Dirty Shirley Mini - crunch", "Friedman", "Dirty Shirley Mini", "amp", "Sascha S",
            "il crunch rock \"moderno-classico\""),
    Profile("Orange Rockerverb (modello Axe-FX).nam", "Tom C Axe FX 2 Orange Rockerverb.nam",
            "Orange Rockerverb (modello Axe-FX)", "Orange", "Rockerverb (modello Axe-FX II)", "amp", "Tom C",
            "il suono Orange (cattura del modello Axe-FX, non dell'amplificatore vero)"),
    Profile("Sovtek MIG50.nam", "Mikhail K Sovtek MIG50.nam",
            "Sovtek MIG50", "Sovtek", "MIG-50", "amp", "Mikhail K",
            "grezzo e pieno: stoner e doom"),
    # -- high gain
    Profile("Peavey 6505+ - high gain.nam", "Helga B 6505+ Red ch - NoBoost.nam",
            "Peavey 6505+ - high gain", "Peavey", "6505+ (canale rosso)", "amp", "Helga B",
            "il successore del 5150"),
    Profile("Splawn Pro Mod - high gain.nam", "Tim R Splawn Pro Mod 2nd Gear - G12.nam",
            "Splawn Pro Mod - high gain", "Splawn", "Pro Mod (seconda marcia)", "amp", "Tim R",
            "hard rock e metal anni '80"),
    Profile("Engl Savage (modello Axe-FX).nam", "Tom C Axe FX 2 Engl Savage.nam",
            "Engl Savage (modello Axe-FX)", "Engl", "Savage (modello Axe-FX II)", "amp", "Tom C",
            "metal europeo (cattura del modello Axe-FX)"),
    Profile("Meshuggah - djent.nam", "Roman A YERASOV_MESHUGGAH.nam",
            "Meshuggah - djent", "Yerasov", "Meshuggah", "amp", "Roman A",
            "djent e metal moderno"),
    # -- pedali ("Feather": i piu' leggeri da calcolare)
    Profile("Maxon OD808.nam", "Phillipe P Maxon-OD808-Feather-ESR0,001.nam",
            "Maxon OD808", "Maxon", "OD808 Overdrive", "pedal", "Phillipe P",
            "l'originale del Tube Screamer"),
    Profile("Boss SD-1.nam", "Phillipe P BOSS-SD1-Feather-ESR0,001.nam",
            "Boss SD-1", "Boss", "SD-1 Super OverDrive", "pedal", "Phillipe P",
            "l'overdrive Boss classico"),
    Profile("MXR M77.nam", "Phillipe P MXR-M77-Feather-ESR0,001.nam",
            "MXR M77", "MXR", "M77 Custom Badass Modified O.D.", "pedal", "Phillipe P",
            "boost e overdrive davanti agli high gain"),
    Profile("Horizon Precision Drive.nam", "Phillipe P Precision-Drive-Feather-ESR0,001.nam",
            "Horizon Precision Drive", "Horizon Devices", "Precision Drive", "pedal", "Phillipe P",
            "il boost \"stretto\" del metal moderno"),
    Profile("Boss DS-1.nam", "Keith B DS1_g6_t5.nam",
            "Boss DS-1", "Boss", "DS-1 Distortion", "pedal", "Keith B",
            "la distorsione piu' diffusa"),
    Profile("Boss OS-2.nam", "Helga B Boss OS-2.nam",
            "Boss OS-2", "Boss", "OS-2 OverDrive/Distortion", "pedal", "Helga B",
            "overdrive e distorsione insieme"),
    Profile("Fortin Grind.nam", "Tudor N Fortin Grind Mini Knob @ 5 ESR_0.0012_lite.nam",
            "Fortin Grind", "Fortin", "Grind", "pedal", "Tudor N",
            "boost per il metal"),
    Profile("EarthQuaker Plumes (clone).nam", "Keith B PlumesClone_maxG_t5_switch3.nam",
            "EarthQuaker Plumes (clone)", "EarthQuaker Devices", "Plumes (clone)", "pedal", "Keith B",
            "overdrive moderno, alternativa al Tube Screamer"),
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
    lines += ["", "Gli amplificatori senza cassa vanno usati con una cassa: SoundText gliene",
              "mette una interna da solo, oppure nella card del Profilo NAM scegli",
              "Cassa -> File IR... Quelli \"con cassa\" e i pedali no."]
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
