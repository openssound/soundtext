"""
Gli effetti Audio Unit di Apple, che ogni Mac ha gratis (riverberi, delay,
equalizzatori, dinamica...), come plugin "au:" normali.

Apple li registra tutti insieme nel bundle di sistema
/System/Library/Components/CoreAudio.component, con 49 componenti, molti
dei quali non sono plugin audio (lettori di file, uscite, mixer):
pedalboard, chiedendone i nomi, entra in un ciclo che alloca memoria senza
fine. Per questo SoundText scrive per ciascun effetto utile un bundle
"ponte" nella sua cartella delle impostazioni: un .component con il solo
Contents/Info.plist, che dichiara un unico componente (tipo, sottotipo,
produttore copiati da quello di Apple). Caricandolo, macOS da' a pedalboard
l'effetto di sistema gia' registrato: niente codice copiato, niente
binario.

Da li' in poi sono AU come gli altri (core.plugins): stessa ricerca, cache,
processo separato e riferimento au:percorso nel file; su un altro Mac il
plugin si ritrova per nome del bundle, che non cambia.
"""

import os
import plistlib
from typing import Dict, List, Optional, Tuple

from .i18n import tr

APPLE_BUNDLE = "/System/Library/Components/CoreAudio.component"
FOLDER_NAME = "Apple AU"

# (tipo, sottotipo) degli effetti e strumenti Apple che servono per fare
# musica, nell'ordine in cui si scrivono. Fuori: AUNetSend, AURogerBeep,
# AURoundTripAAC, i convertitori (aufc), uscite e mixer.
COMPONENTS: List[Tuple[str, str]] = [
    ("aufx", "rvb2"), ("aufx", "mrev"), ("aufx", "dely"),
    ("aufx", "nbeq"), ("aufx", "pmeq"), ("aufx", "greq"),
    ("aufx", "lpas"), ("aufx", "hpas"), ("aufx", "bpas"), ("aufx", "lshf"), ("aufx", "hshf"), ("aufx", "filt"),
    ("aufx", "dcmp"), ("aufx", "mcmp"), ("aufx", "lmtr"),
    ("aufx", "dist"), ("aufx", "tmpt"),
    ("aumu", "dls "),
]


def friendly_names() -> Dict[str, str]:
    """Nome del bundle ponte (quello di Apple, es. AUMatrixReverb) -> nome
    da mostrare nella lingua dell'interfaccia."""
    return {
        "AUReverb2": tr("Riverbero (Apple)"),
        "AUMatrixReverb": tr("Riverbero a matrice (Apple)"),
        "AUDelay": tr("Delay (Apple)"),
        "AUNBandEQ": tr("Equalizzatore a bande (Apple)"),
        "AUParametricEQ": tr("EQ parametrico (Apple)"),
        "AUGraphicEQ": tr("EQ grafico (Apple)"),
        "AULowpass": tr("Filtro passa-basso (Apple)"),
        "AUHipass": tr("Filtro passa-alto (Apple)"),
        "AUBandpass": tr("Filtro passa-banda (Apple)"),
        "AULowShelfFilter": tr("Shelving bassi (Apple)"),
        "AUHighShelfFilter": tr("Shelving acuti (Apple)"),
        "AUFilter": tr("Filtro multiplo (Apple)"),
        "AUDynamicsProcessor": tr("Dinamica (Apple)"),
        "AUMultibandCompressor": tr("Compressore multibanda (Apple)"),
        "AUPeakLimiter": tr("Limiter (Apple)"),
        "AUDistortion": tr("Distorsione (Apple)"),
        "AUPitch": tr("Pitch (Apple)"),
        "DLSMusicDevice": tr("Sintetizzatore General MIDI (Apple)"),
    }


def proxy_folder() -> str:
    from .settings import CONFIG_DIR
    return os.path.join(CONFIG_DIR, FOLDER_NAME)


def is_proxy(path: str) -> bool:
    """Se il bundle e' uno dei ponti verso un effetto Apple."""
    return os.path.basename(os.path.dirname(os.path.normpath(path))) == FOLDER_NAME


def friendly_name(path: str) -> Optional[str]:
    """Il nome da mostrare di un bundle ponte, o None se non lo e'."""
    if not is_proxy(path):
        return None
    base = os.path.splitext(os.path.basename(os.path.normpath(path)))[0]
    return friendly_names().get(base)


def _apple_components(bundle: str) -> Dict[Tuple[str, str], dict]:
    try:
        with open(os.path.join(bundle, "Contents", "Info.plist"), "rb") as f:
            info = plistlib.load(f)
    except (OSError, ValueError, plistlib.InvalidFileException):
        return {}
    return {(str(c.get("type")), str(c.get("subtype"))): c for c in info.get("AudioComponents") or []
            if isinstance(c, dict) and c.get("manufacturer") == "appl" and c.get("name")}


def _proxy_plist(component: dict) -> bytes:
    sub = str(component["subtype"]).strip()
    return plistlib.dumps({
        "CFBundlePackageType": "BNDL",
        "CFBundleIdentifier": f"local.soundtext.apple-au.{component['type']}.{sub}",
        "CFBundleName": str(component["name"]).split(":", 1)[-1].strip(),
        "AudioComponents": [component],
    }, sort_keys=True)


def ensure_proxies(folder: Optional[str] = None, apple_bundle: Optional[str] = None) -> List[str]:
    """Scrive (o aggiorna) i bundle ponte e torna i loro percorsi. Un bundle
    gia' giusto non si riscrive: la data non cambia e la ricerca dei plugin
    non lo ricarica. Vuoto se il bundle di Apple non si legge (non macOS)."""
    folder = folder or proxy_folder()
    components = _apple_components(apple_bundle or APPLE_BUNDLE)
    out = []
    for key in COMPONENTS:
        component = components.get(key)
        if component is None:
            continue
        name = str(component["name"]).split(":", 1)[-1].strip()
        contents = os.path.join(folder, name + ".component", "Contents")
        path = os.path.join(contents, "Info.plist")
        data = _proxy_plist(component)
        try:
            with open(path, "rb") as f:
                same = f.read() == data
        except OSError:
            same = False
        if not same:
            try:
                os.makedirs(contents, exist_ok=True)
                with open(path, "wb") as f:
                    f.write(data)
            except OSError:
                continue
        out.append(os.path.dirname(contents))
    return out


_ready: Optional[str] = None


def ready_folder() -> Optional[str]:
    """La cartella dei bundle ponte, scritti una volta per sessione; None
    se non ce n'e' nessuno (bundle di Apple non leggibile)."""
    global _ready
    folder = proxy_folder()
    if _ready != folder:
        if not ensure_proxies(folder):
            return None
        _ready = folder
    return folder
