"""
Strumenti, plugin e profili da scaricare, per la finestra "Scarica e
installa" (gui.download_dialog): l'elenco con lo stato di ogni voce e il
modo di eseguirle.

Il lavoro lo fa scarica_strumenti.py (accanto al programma: lo stesso che si
usa dal terminale), in un processo a parte: la finestra ne legge l'uscita
riga per riga e lo puo' fermare. Il processo e' SoundText stesso avviato con
--scarica-strumenti (vedi main.py), cosi' funziona anche nell'app
impacchettata, dove non c'e' un Python da usare. Profili NAM, casse IR e
SoundFont passano dallo stesso processo (voci "profili-nam", "casse-ir" e
"sf-..."), con le funzioni di core.nam_profiles, core.cab_irs e
core.soundfont_downloads.

Gli indirizzi da cui si scarica si possono cambiare (Opzioni -> Sorgenti
dei download): sources() li elenca, apply_source_overrides() li applica nel
processo che scarica.
"""

import dataclasses
import importlib.util
import os
import re
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional

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


def _download_soundfont(key: str) -> int:
    from .soundfont_downloads import download, find
    source = find(key)
    print(f"== {key}: SoundFont {source.label} ({source.detail})", flush=True)
    script = load_script()
    download(source, fetch=(lambda url, path: script.scarica_file(url, __import__("pathlib").Path(path)))
             if script is not None else None, log=lambda line: print(line, flush=True))
    return 0


def run_script(items: List[str]) -> int:
    """Esegue le voci nel processo attuale (main.py --scarica-strumenti),
    con gli indirizzi scelti dall'utente (apply_source_overrides)."""
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    from .settings import get_download_sources
    apply_source_overrides(load_script(), get_download_sources())
    status = 0
    rest = []
    for item in items:
        if item in ("profili-nam", "casse-ir") or item.startswith("sf-"):
            try:
                status = max(status, _download_soundfont(item) if item.startswith("sf-") else _download_nam(item))
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
CATEGORY_SOUNDFONTS = "soundfonts"
CATEGORY_AMP = "amp"
CATEGORY_PLUGINS = "plugins"
CATEGORY_ENGINES = "engines"


def category_label(category: str) -> str:
    return {CATEGORY_SFZ: tr("Strumenti campionati (SFZ)"),
            CATEGORY_SFZ_EXTRA: tr("Altri strumenti SFZ (grandi)"),
            CATEGORY_SOUNDFONTS: tr("SoundFont General MIDI"),
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
    from .soundfont_downloads import SOUNDFONTS, installed_path
    for source in SOUNDFONTS:
        items.append(Item(source.key, CATEGORY_SOUNDFONTS, tr(source.label), tr(source.detail),
                          bool(installed_path(source))))
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
        lv2 = ", ".join(n for n, _d, _r, _rel, modelli in script.PLUGIN_LV2 if script.chiave_sistema() in modelli)
        items.append(Item("lv2", CATEGORY_PLUGINS, tr("Plugin LV2 gratuiti"),
                          lv2 if script.SISTEMA == "linux" and lv2 else tr("solo Linux"), None))
        lib = script.user_lib_dir()
        stamp = lib / "sfizioso.commit"
        items.append(Item("libreria", CATEGORY_ENGINES, tr("Motore SFZ interno (libreria sfizz)"),
                          tr("si compila: circa 5 minuti, servono git, cmake e un compilatore"),
                          (lib / script.LIB_FILE).exists() and stamp.exists()
                          and stamp.read_text().strip() == script.SFIZIOSO_COMMIT,
                          needs_build=True))
    return items


def lv2_unavailable() -> bool:
    """La voce "lv2" non vale per questo sistema (i plugin LV2 si usano solo su Linux)."""
    script = load_script()
    return script is None or script.SISTEMA != "linux"


def lilv_missing() -> bool:
    """Manca la libreria lilv, senza la quale SoundText non usa i plugin LV2."""
    script = load_script()
    return script is not None and script.SISTEMA == "linux" and not script.lilv_presente()


def missing_build_tools() -> List[str]:
    """Che cosa manca per compilare la libreria sfizz (nomi da mostrare)."""
    script = load_script()
    if script is None:
        return []
    return [name for name, _command in script.strumenti_compilazione_mancanti()]


def build_tools_install_problem() -> str:
    """Perche' gli strumenti mancanti non si possono installare da qui ('' se si puo')."""
    script = load_script()
    return script.motivo_installazione_impossibile() if script is not None else ""


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


# ---------------------------------------------------------------- sorgenti

@dataclass
class Source:
    key: str            # "sfz:piano", "vst3:Dexed", "libreria", "sf:sf-musescore"...
    section: str        # il gruppo in cui mostrarla
    label: str
    default: str        # l'indirizzo originale
    kind: str = "url"   # "url" (http/https) o "github" (https://github.com/proprietario/progetto)


GITHUB = "https://github.com/"


def _fresh_script():
    """Lo script appena letto dal disco, con gli indirizzi originali."""
    path = script_path()
    if not os.path.isfile(path):
        return None
    spec = importlib.util.spec_from_file_location("scarica_strumenti_originale", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sources() -> List[Source]:
    """Tutti gli indirizzi da cui "Scarica e installa" scarica, con
    l'originale di ciascuno."""
    from . import cab_irs, nam_profiles
    from .soundfont_downloads import SOUNDFONTS
    out: List[Source] = []
    script = _fresh_script()
    if script is not None:
        for groups, section in ((script.GRUPPI, CATEGORY_SFZ), (script.EXTRA, CATEGORY_SFZ_EXTRA)):
            out += [Source(f"sfz:{name}", category_label(section), _split(desc)[0], url)
                    for name, desc, url, _sub in groups]
    out += [Source(f"sf:{s.key}", category_label(CATEGORY_SOUNDFONTS), tr(s.label), s.url) for s in SOUNDFONTS]
    out += [Source("profili-nam", category_label(CATEGORY_AMP), tr("Profili NAM consigliati"), nam_profiles.RAW_BASE),
            Source("casse-ir", category_label(CATEGORY_AMP), tr("Casse IR per gli amplificatori NAM"), cab_irs.RAW_BASE)]
    if script is not None:
        plugins = category_label(CATEGORY_PLUGINS)
        out.append(Source("nam-plugin", category_label(CATEGORY_AMP),
                          tr("Motore NAM veloce (plugin Neural Amp Modeler)"), script.NAM_PLUGIN_BASE))
        out += [Source(f"vst3:{name}", plugins, f"VST3: {name}", GITHUB + repo, "github")
                for name, _d, repo, _rel, _m in script.PLUGIN_VST3]
        out += [Source(f"lv2:{name}", plugins, f"LV2: {name}", GITHUB + repo, "github")
                for name, _d, repo, _rel, _m in script.PLUGIN_LV2]
        out += [Source("surge", plugins, tr("Surge XT (Windows e macOS)"), GITHUB + script.SURGE_REPO, "github"),
                Source("surge-linux", plugins, tr("Surge XT Nightly (Linux)"), GITHUB + script.SURGE_NIGHTLY_REPO,
                       "github"),
                Source("sfizz-ui", plugins, tr("sfizz (Windows e macOS)"), GITHUB + script.SFIZZ_UI_REPO, "github"),
                Source("sfizz-deb", plugins, tr("sfizz (Linux, pacchetti .deb)"), script.SFIZZ_DEB_BASE),
                Source("libreria", category_label(CATEGORY_ENGINES), tr("Motore SFZ interno (libreria sfizz)"),
                       script.SFIZIOSO_URL)]
    return out


def check_source(source: Source, value: str) -> str:
    """'' se 'value' va bene per la sorgente, altrimenti il motivo."""
    value = value.strip()
    if source.kind == "github":
        if not re.fullmatch(r"https://github\.com/[\w.-]+/[\w.-]+/?", value):
            return tr("serve l'indirizzo di un progetto GitHub: https://github.com/proprietario/progetto")
        return ""
    if not re.match(r"https?://\S+$", value):
        return tr("serve un indirizzo che cominci con https:// (o http://), senza spazi")
    return ""


def _repo(value: str) -> str:
    return value.strip().rstrip("/")[len(GITHUB):]


def apply_source_overrides(script, overrides: Dict[str, str]):
    """Applica gli indirizzi cambiati dall'utente allo script (e ai moduli
    di profili NAM, casse IR e SoundFont), nel processo che scarica."""
    if not overrides:
        return
    from . import cab_irs, nam_profiles, soundfont_downloads
    if "profili-nam" in overrides:
        nam_profiles.RAW_BASE = overrides["profili-nam"].rstrip("/") + "/"
    if "casse-ir" in overrides:
        cab_irs.RAW_BASE = overrides["casse-ir"].rstrip("/") + "/"
    soundfont_downloads.SOUNDFONTS[:] = [
        dataclasses.replace(s, url=overrides[f"sf:{s.key}"]) if f"sf:{s.key}" in overrides else s
        for s in soundfont_downloads.SOUNDFONTS]
    if script is None:
        return
    for groups in (script.GRUPPI, script.EXTRA):
        groups[:] = [(n, d, overrides.get(f"sfz:{n}", u), sub) for n, d, u, sub in groups]
    for prefix, plugins in (("vst3", script.PLUGIN_VST3), ("lv2", script.PLUGIN_LV2)):
        plugins[:] = [(n, d, _repo(overrides[f"{prefix}:{n}"]) if f"{prefix}:{n}" in overrides else r, rel, m)
                      for n, d, r, rel, m in plugins]
    for key, attribute in (("surge", "SURGE_REPO"), ("surge-linux", "SURGE_NIGHTLY_REPO"),
                           ("sfizz-ui", "SFIZZ_UI_REPO")):
        if key in overrides:
            setattr(script, attribute, _repo(overrides[key]))
    if "sfizz-deb" in overrides:
        script.SFIZZ_DEB_BASE = overrides["sfizz-deb"]
    if "libreria" in overrides:
        script.SFIZIOSO_URL = overrides["libreria"]
    if "nam-plugin" in overrides:
        script.NAM_PLUGIN_BASE = overrides["nam-plugin"].rstrip("/") + "/"
