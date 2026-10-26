"""
Strumenti, plugin e profili da scaricare, per la finestra "Scarica e
installa" (gui.download_dialog): l'elenco con lo stato di ogni voce e il
modo di eseguirle.

Il lavoro lo fa scarica_strumenti.py (accanto al programma: lo stesso che si
usa dal terminale), in un processo a parte: la finestra ne legge l'uscita
riga per riga e lo puo' fermare. Il processo e' SoundText stesso avviato con
--scarica-strumenti (vedi main.py), cosi' funziona anche nell'app
impacchettata, dove non c'e' un Python da usare. Profili NAM e casse IR
passano dallo stesso processo (voci "profili-nam" e "casse-ir"), con le
funzioni di core.nam_profiles e core.cab_irs.
"""

import importlib.util
import os
import sys
from dataclasses import dataclass
from typing import List, Optional

from .i18n import tr
from .version import get_app_root

SCRIPT_NAME = "scarica_strumenti.py"
_script = None


def script_path() -> str:
    return os.path.join(get_app_root(), SCRIPT_NAME)


def load_script():
    """Il modulo scarica_strumenti.py del programma (None se manca)."""
    global _script
    if _script is None:
        path = script_path()
        if not os.path.isfile(path):
            return None
        spec = importlib.util.spec_from_file_location("scarica_strumenti", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _script = module
    return _script


def command(items: List[str]) -> List[str]:
    """Il comando del processo che esegue 'items' (vedi main.py)."""
    if getattr(sys, "frozen", False):
        return [sys.executable, "--scarica-strumenti", *items]
    return [sys.executable, "-u", os.path.join(get_app_root(), "main.py"), "--scarica-strumenti", *items]


def _download_nam(kind: str) -> int:
    """profili-nam / casse-ir, con le funzioni del programma e lo stesso
    stile di righe dello script."""
    if kind == "profili-nam":
        from .nam_profiles import download_profiles as download
        label = tr("Profili NAM consigliati")
    else:
        from .cab_irs import download_cabinets as download
        label = tr("Casse IR per gli amplificatori NAM")
    print(f"== {kind}: {label}", flush=True)
    result = download(progress=lambda i, total, name: print(f"   {i}/{total} {name}", flush=True))
    for name, reason in result.get("failed", []):
        print(f"   non riuscito: {name}: {reason}", flush=True)
    print(f"   -> {result['folder']}", flush=True)
    return 1 if result.get("failed") else 0


def run_script(items: List[str]) -> int:
    """Esegue le voci nel processo attuale (main.py --scarica-strumenti)."""
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    status = 0
    rest = []
    for item in items:
        if item in ("profili-nam", "casse-ir"):
            try:
                status = max(status, _download_nam(item))
            except Exception as e:                     # rete, disco...: si continua con le altre
                print(f"ERRORE: {e}", flush=True)
                status = 1
        else:
            rest.append(item)
    if rest:
        script = load_script()
        if script is None:
            print(f"ERRORE: manca {SCRIPT_NAME} accanto al programma", flush=True)
            return 1
        status = max(status, script.main(rest))
    return status


# ---------------------------------------------------------------- l'elenco

@dataclass
class Item:
    key: str                    # l'argomento dello script ("piano", "vst3", "nam-plugin"...)
    category: str
    label: str
    detail: str                 # dimensione, licenza, note
    installed: Optional[bool]   # None: non si sa (si puo' sempre reinstallare)
    needs_build: bool = False   # si compila: servono git, cmake e un compilatore


CATEGORY_SFZ = "sfz"
CATEGORY_SFZ_EXTRA = "sfz_extra"
CATEGORY_AMP = "amp"
CATEGORY_PLUGINS = "plugins"
CATEGORY_ENGINES = "engines"


def category_label(category: str) -> str:
    return {CATEGORY_SFZ: tr("Strumenti campionati (SFZ)"),
            CATEGORY_SFZ_EXTRA: tr("Altri strumenti SFZ (grandi)"),
            CATEGORY_AMP: tr("Amplificatori per chitarra (NAM)"),
            CATEGORY_PLUGINS: tr("Plugin e programmi gratuiti"),
            CATEGORY_ENGINES: tr("Motori")}[category]


def _split(desc: str):
    """("Piano a coda Salamander", "SFZ+FLAC, ~740 MB") da "Piano ... (SFZ+FLAC, ~740 MB)"."""
    if desc.endswith(")") and " (" in desc:
        head, _sep, tail = desc.rpartition(" (")
        return head, tail[:-1]
    return desc, ""


def catalog() -> List[Item]:
    """Tutte le voci, nell'ordine della finestra, con lo stato attuale."""
    script = load_script()
    items: List[Item] = []
    if script is not None:
        sfz = script.DEST / "sfz"
        for groups, category in ((script.GRUPPI, CATEGORY_SFZ), (script.EXTRA, CATEGORY_SFZ_EXTRA)):
            for name, desc, _url, sub in groups:
                label, detail = _split(desc)
                items.append(Item(name, category, label, detail,
                                  (script.DEST / sub / name / ".completo").exists()))
    from .cab_irs import CABINETS, existing_cab_dir
    from .nam_profiles import PROFILES, existing_nam_dir
    nam_dir, cab_dir = existing_nam_dir(), existing_cab_dir()
    items.append(Item("profili-nam", CATEGORY_AMP, tr("Profili NAM consigliati"),
                      tr("{n} amplificatori e pedali, GPL-3.0", n=len(PROFILES)),
                      bool(nam_dir) and all(os.path.exists(os.path.join(nam_dir, p.file)) for p in PROFILES)))
    items.append(Item("casse-ir", CATEGORY_AMP, tr("Casse IR per gli amplificatori NAM"),
                      tr("{n} casse per chitarra, GPL-2.0, < 1 MB", n=len(CABINETS)),
                      bool(cab_dir) and all(os.path.exists(os.path.join(cab_dir, c)) for c in CABINETS)))
    if script is not None:
        version = script.NAM_PLUGIN_VERSION
        stamp = script.user_lv2_dir() / script.NAM_PLUGIN_DIR / "soundtext.versione"
        available = script.SISTEMA in script.NAM_PLUGIN_FILES
        items.append(Item("nam-plugin", CATEGORY_AMP, tr("Motore NAM veloce (plugin Neural Amp Modeler)"),
                          (tr("{version}, GPL-3.0, ~2 MB: profili NAM 4-6 volte più veloci", version=version)
                           if available else tr("non disponibile per questo sistema")),
                          stamp.exists() and stamp.read_text().strip() == version))
        vst3 = ", ".join(n for n, _d, _r, _rel, modelli in script.PLUGIN_VST3 if script.chiave_sistema() in modelli)
        items.append(Item("vst3", CATEGORY_PLUGINS, tr("Plugin VST3 gratuiti"), vst3, None))
        items.append(Item("host", CATEGORY_PLUGINS, tr("7-Zip, sfizz e Surge XT"),
                          tr("i programmi per estrarre e suonare gli strumenti"), None))
        lib = script.user_lib_dir()
        stamp = lib / "sfizioso.commit"
        items.append(Item("libreria", CATEGORY_ENGINES, tr("Motore SFZ interno (libreria sfizz)"),
                          tr("si compila: circa 5 minuti, servono git, cmake e un compilatore"),
                          (lib / script.LIB_FILE).exists() and stamp.exists()
                          and stamp.read_text().strip() == script.SFIZIOSO_COMMIT,
                          needs_build=True))
    return items


def build_tools_problem() -> str:
    """Che cosa manca per compilare (la libreria sfizz), '' se c'e' tutto:
    lo si dice prima di partire invece di fallire dopo minuti."""
    script = load_script()
    if script is None:
        return tr("manca {name} accanto al programma", name=SCRIPT_NAME)
    try:
        script.controlla_strumenti_compilazione()
    except script.Errore as e:
        return str(e)
    except SystemExit:
        return tr("mancano gli strumenti per compilare")
    return ""
