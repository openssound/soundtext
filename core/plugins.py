"""
Plugin audio esterni: VST3 (tutte le piattaforme, con pedalboard) e LV2
(Linux, con la libreria di sistema lilv, vedi core.lv2_host).

Un plugin si usa in due modi:
  - come effetto nella catena di una traccia o del master (Effect di tipo
    "plugin", vedi core.effects);
  - come strumento di una traccia di testo al posto del SoundFont
    (Track.synth, vedi core.effect_render).

Il plugin si indica con un riferimento testuale ("ref"), lo stesso che
si salva nel file .st:
    vst3:/usr/lib/vst3/MVerb.vst3        (vst3:percorso[|nome] se il file ne contiene piu' d'uno)
    lv2:urn:ardour:a-delay                (lv2:URI del plugin)
I parametri si salvano come {chiave: valore}: per LV2 il valore della
porta di controllo, per VST3 il valore normalizzato 0-1 del parametro.
Dei VST3 si salva anche lo stato interno (base64), che conserva quello
che i parametri non dicono (es. le impostazioni fatte nell'interfaccia
grafica del plugin).

Tutto il lavoro vero lo fa un processo separato (core.plugin_worker):
un plugin che si blocca o va in crash non porta giu' SoundText. Ogni
richiesta ha un tempo massimo; se scade, il processo viene chiuso e al
bisogno riavviato, e il plugin viene segnato come "non risponde" fino al
riavvio dell'app.
"""

import base64
import hashlib
import json
import logging
import os
import pickle
import queue
import re
import struct
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

from .plugin_worker import parse_ref
from .i18n import tr

log = logging.getLogger(__name__)

# Caricare un plugin grande puo' richiedere decine di secondi (Surge XT:
# circa 20 fra caricamento ed elenco dei suoi 600 parametri): il tempo
# massimo deve starci largo, anche se un plugin bloccato si scopre piu' tardi.
DESCRIBE_TIMEOUT = 60.0
UI_TIMEOUT = 15.0
EDITOR_TIMEOUT = 24 * 3600.0


class PluginError(Exception):
    """Errore di un plugin. 'fatal' se il plugin si e' bloccato o ha fatto
    cadere il processo: da allora non lo si usa piu' (vedi _call)."""

    def __init__(self, message: str, fatal: bool = False):
        super().__init__(message)
        self.fatal = fatal


# ---------------------------------------------------------------------------
# Il processo separato
# ---------------------------------------------------------------------------

def _worker_command() -> List[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--plugin-worker"]
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return [sys.executable, os.path.join(root, "core", "plugin_worker.py")]


def _worker_log_path() -> str:
    from .settings import CONFIG_DIR
    os.makedirs(CONFIG_DIR, exist_ok=True)
    return os.path.join(CONFIG_DIR, "plugin_host.log")


class _Host:
    """Un processo host con la sua coda di risposte. Una richiesta alla
    volta (lock); chi aspetta oltre il tempo massimo fa chiudere il
    processo."""

    def __init__(self, name: str):
        self.name = name
        self._proc: Optional[subprocess.Popen] = None
        self._replies: "queue.Queue" = queue.Queue()
        self._lock = threading.Lock()

    def _start(self):
        env = dict(os.environ)
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env["PYTHONPATH"] = root + os.pathsep + env.get("PYTHONPATH", "")
        try:
            err = open(_worker_log_path(), "ab")
        except OSError:
            err = subprocess.DEVNULL
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = 0x08000000    # CREATE_NO_WINDOW
        self._proc = subprocess.Popen(_worker_command(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                      stderr=err, env=env, **kwargs)
        if err is not subprocess.DEVNULL:
            err.close()
        self._replies = queue.Queue()
        threading.Thread(target=self._reader, args=(self._proc, self._replies), daemon=True).start()

    @staticmethod
    def _reader(proc, replies):
        stream = proc.stdout
        try:
            while True:
                head = stream.read(8)
                if len(head) < 8:
                    break
                size = struct.unpack("<Q", head)[0]
                data = stream.read(size)
                if len(data) < size:
                    break
                replies.put(pickle.loads(data))
        except Exception:
            pass
        replies.put(("died", None))

    def stop(self):
        proc, self._proc = self._proc, None
        if proc is not None:
            try:
                proc.kill()
                proc.wait(timeout=5)
            except Exception:
                pass

    def call(self, request: tuple, timeout: float):
        with self._lock:
            if self._proc is None or self._proc.poll() is not None:
                self._start()
            data = pickle.dumps(request, protocol=pickle.HIGHEST_PROTOCOL)
            try:
                self._proc.stdin.write(struct.pack("<Q", len(data)) + data)
                self._proc.stdin.flush()
            except OSError:
                self.stop()
                raise PluginError(tr("il processo dei plugin si e' chiuso"))
            try:
                status, value = self._replies.get(timeout=timeout)
            except queue.Empty:
                self.stop()
                raise PluginError(tr("il plugin non risponde"), fatal=True)
            if status == "died":
                self.stop()
                raise PluginError(tr("il plugin si e' chiuso in modo anomalo"), fatal=True)
            if status == "error":
                raise PluginError(value)
            return value

    def send(self, request: tuple) -> bool:
        """Manda una richiesta che non ha risposta ("live_midi"). False se
        il processo non c'e' piu'."""
        with self._lock:
            if self._proc is None or self._proc.poll() is not None:
                return False
            data = pickle.dumps(request, protocol=pickle.HIGHEST_PROTOCOL)
            try:
                self._proc.stdin.write(struct.pack("<Q", len(data)) + data)
                self._proc.stdin.flush()
            except (OSError, ValueError):
                return False
            return True


# Tre processi: uno per il rendering (lavori lunghi, in sottofondo), uno
# per l'interfaccia (descrizioni, testi dei parametri, finestra del plugin),
# cosi' un rendering in corso non blocca le finestre, e uno per lo
# strumento suonato dal vivo (live_start), che tiene aperta l'uscita audio.
_hosts = {"render": _Host("render"), "ui": _Host("ui"), "live": _Host("live")}
_broken: Dict[str, str] = {}     # ref -> motivo (plugin che si sono bloccati)


def shutdown():
    for host in _hosts.values():
        host.stop()


def broken_reason(ref: str) -> str:
    """Perche' il plugin non si usa (si e' bloccato o chiuso), o ''."""
    return _broken.get(ref, "")


def _call(channel: str, ref: Optional[str], request: tuple, timeout: float):
    if ref and ref in _broken:
        raise PluginError(_broken[ref])
    if ref:
        _check_allowed(ref)
    try:
        return _hosts[channel].call(request, timeout)
    except PluginError as e:
        if ref and e.fatal:
            _broken[ref] = str(e)
        raise


# ---------------------------------------------------------------------------
# Dove sono i plugin e cosa sono
# ---------------------------------------------------------------------------

def default_vst3_dirs() -> List[str]:
    if sys.platform == "win32":
        base = os.environ.get("COMMONPROGRAMFILES", r"C:\Program Files\Common Files")
        dirs = [os.path.join(base, "VST3"),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Common", "VST3")]
    elif sys.platform == "darwin":
        dirs = ["/Library/Audio/Plug-Ins/VST3", os.path.expanduser("~/Library/Audio/Plug-Ins/VST3")]
    else:
        dirs = [os.path.expanduser("~/.vst3"), "/usr/lib/vst3", "/usr/local/lib/vst3",
                "/usr/lib/x86_64-linux-gnu/vst3", "/usr/lib64/vst3"]
    dirs += [d for d in os.environ.get("VST3_PATH", "").split(os.pathsep) if d]
    return dirs


def vst3_dirs() -> List[str]:
    """Le cartelle in cui cercare i VST3: quelle standard del sistema e
    quelle aggiunte in Opzioni."""
    from .settings import get_plugin_dirs
    out = []
    for d in default_vst3_dirs() + get_plugin_dirs():
        if d and d not in out:
            out.append(d)
    return out


def find_vst3_bundles(dirs: Optional[List[str]] = None) -> List[str]:
    found = []
    for d in dirs if dirs is not None else vst3_dirs():
        if not os.path.isdir(d):
            continue
        for root, subdirs, _files in os.walk(d):
            for sub in list(subdirs):
                if sub.lower().endswith(".vst3"):
                    found.append(os.path.join(root, sub))
                    subdirs.remove(sub)          # dentro un bundle non si cerca
        for name in os.listdir(d):               # VST3 "a file singolo" (Windows)
            path = os.path.join(d, name)
            if name.lower().endswith(".vst3") and os.path.isfile(path):
                found.append(path)
    return sorted(set(found))


@dataclass
class PluginParam:
    key: str
    label: str
    minimum: float
    maximum: float
    default: float
    raw: bool = False          # VST3: valore normalizzato 0-1
    text: str = ""             # come lo scrive il plugin (VST3)
    units: str = ""
    toggled: bool = False
    integer: bool = False
    logarithmic: bool = False
    choices: List[Tuple[float, str]] = field(default_factory=list)


@dataclass
class PluginFile:
    key: str                   # LV2: URI della proprieta'
    label: str


@dataclass
class PluginInfo:
    ref: str
    format: str                # "vst3" / "lv2" / "sfz" (motore interno)
    name: str
    vendor: str = ""
    category: str = ""
    instrument: bool = False
    problem: str = ""          # se non si puo' usare: perche'
    params: List[PluginParam] = field(default_factory=list)
    state: str = ""            # stato iniziale (VST3)
    files: List[PluginFile] = field(default_factory=list)   # LV2: proprieta' da impostare con un file

    @property
    def usable(self) -> bool:
        return not self.problem

    @property
    def format_label(self) -> str:
        return {"vst3": "VST3", "lv2": "LV2", "sfz": "SFZ"}.get(self.format, self.format.upper())


def _info_from_dict(d: dict) -> PluginInfo:
    params = [PluginParam(**{**p, "choices": [tuple(c) for c in p.get("choices", [])]}) for p in d.get("params", [])]
    return PluginInfo(ref=d["ref"], format=d["format"], name=d["name"], vendor=d.get("vendor", ""),
                      category=d.get("category", ""), instrument=bool(d.get("instrument")),
                      problem=d.get("problem", ""), params=params, state=d.get("state", ""),
                      files=[PluginFile(**f) for f in d.get("files", [])])


def _scan_cache_path() -> str:
    from .settings import CONFIG_DIR
    return os.path.join(CONFIG_DIR, "plugins_cache.json")


def _load_scan_cache() -> dict:
    try:
        with open(_scan_cache_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_scan_cache(cache: dict):
    try:
        os.makedirs(os.path.dirname(_scan_cache_path()), exist_ok=True)
        with open(_scan_cache_path(), "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=1, ensure_ascii=False)
    except OSError:
        pass


def _bundle_stamp(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


# pedalboard da' al plugin solo l'uscita stereo principale: questi plugin
# scrivono anche sulle altre e vanno in crash al caricamento.
MULTI_OUTPUT_ALTERNATIVES = {"sfizz-multi": "sfizz"}

_scan_lock = threading.Lock()
_scan_result: Optional[List[PluginInfo]] = None


def _describe_bundle(bundle: str) -> List[dict]:
    """Descrizione (senza parametri e stato) di ogni plugin di un bundle
    VST3. Un bundle puo' contenerne piu' d'uno (es. sfizz e sfizz-multi):
    pedalboard lo dice nell'errore, e ognuno si descrive col suo nome."""
    def one(ref: str) -> dict:
        d = _call("ui", None, ("describe", ref), DESCRIBE_TIMEOUT)
        return {k: v for k, v in d.items() if k not in ("params", "state")}

    ref = "vst3:" + bundle
    try:
        return [one(ref)]
    except PluginError as e:
        names = re.findall(r'"([^"]+)"', str(e).split("following values", 1)[-1]) if "contains" in str(e) else []
        if not names:
            return [{"ref": ref, "format": "vst3", "name": os.path.splitext(os.path.basename(bundle))[0],
                     "problem": str(e)}]
    out = []
    for name in names:
        try:
            out.append(one(f"{ref}|{name}"))
        except PluginError as e:
            out.append({"ref": f"{ref}|{name}", "format": "vst3", "name": name, "problem": str(e)})
    return out


def scan_plugins(refresh: bool = False, progress: Optional[Callable[[str], None]] = None) -> List[PluginInfo]:
    """Tutti i plugin trovati, VST3 e LV2, ordinati per nome. I VST3 vanno
    caricati una volta per sapere cosa sono (effetto o strumento): il
    risultato si ricorda (plugins_cache.json nella cartella delle
    impostazioni) finche' il file del plugin non cambia. 'refresh' rifa'
    la ricerca da capo (ma non ricarica i VST3 gia' noti e invariati)."""
    global _scan_result
    with _scan_lock:
        if _scan_result is not None and not refresh:
            return list(_scan_result)
        out: List[PluginInfo] = []
        try:
            out += [_info_from_dict(d) for d in _call("ui", None, ("list_lv2",), DESCRIBE_TIMEOUT)]
        except PluginError as e:
            log.warning("Elenco dei plugin LV2 non disponibile: %s", e)
        cache = _load_scan_cache()
        new_cache = {}
        for bundle in find_vst3_bundles():
            stamp = _bundle_stamp(bundle)
            entry = cache.get(bundle)
            if not entry or entry.get("mtime") != stamp:
                if progress:
                    progress(os.path.basename(bundle))
                entry = {"mtime": stamp, "infos": _describe_bundle(bundle)}
            new_cache[bundle] = entry
            for d in entry.get("infos") or [entry["info"]]:
                info = _info_from_dict(d)
                if info.problem and info.name in MULTI_OUTPUT_ALTERNATIVES:
                    info.problem = tr("plugin a uscite multiple, il motore VST3 di SoundText non lo supporta: "
                                      "usa {alt}", alt=MULTI_OUTPUT_ALTERNATIVES[info.name])
                out.append(info)
        if new_cache != cache:
            _save_scan_cache(new_cache)
        out.sort(key=lambda i: (i.name.lower(), i.format))
        _scan_result = out
        return list(out)


def forget_scan():
    """La prossima scan_plugins() rifa' la ricerca (cartelle cambiate)."""
    global _scan_result
    with _scan_lock:
        _scan_result = None


_describe_cache: Dict[str, PluginInfo] = {}


def in_plugin_dirs(path: str) -> bool:
    """Se il plugin sta in una delle cartelle dei plugin (quelle del sistema
    o quelle aggiunte da Suoni → Cartelle dei plugin VST3, vedi vst3_dirs)."""
    real = os.path.realpath(path)
    for d in vst3_dirs():
        base = os.path.realpath(d)
        try:
            if os.path.commonpath([real, base]) == base:
                return True
        except ValueError:            # dischi diversi su Windows
            continue
    return False


def _check_allowed(ref: str) -> None:
    """Un VST3 e' codice che gira sul computer: si carica solo dalle
    cartelle dei plugin, mai da un percorso qualsiasi scritto in un file
    .st ricevuto da altri. Un percorso che non esiste non si carica
    comunque (lo dira' il processo dei plugin)."""
    fmt, path, _name = parse_ref(ref)
    if fmt == "vst3" and os.path.exists(path) and not in_plugin_dirs(path):
        raise PluginError(tr("Il plugin '{path}' non e' in una cartella dei plugin: per usarlo aggiungi "
                             "la sua cartella in Suoni → Cartelle dei plugin VST3", path=path))


def resolve_ref(ref: str) -> str:
    """Il riferimento come va usato su questa macchina: un VST3 che non c'e'
    piu' nel percorso salvato (progetto aperto su un altro computer) si
    cerca per nome del file nelle cartelle dei plugin."""
    fmt, path, name = parse_ref(ref)
    if fmt != "vst3" or (os.path.exists(path) and in_plugin_dirs(path)):
        return ref
    base = os.path.basename(path.rstrip("/\\")).lower()
    for bundle in find_vst3_bundles():
        if os.path.basename(bundle).lower() == base:
            return "vst3:" + bundle + (f"|{name}" if name else "")
    return ref


def describe(ref: str) -> PluginInfo:
    """Nome, tipo e parametri del plugin. Solleva PluginError se non si
    puo' caricare."""
    ref = resolve_ref(ref)
    if ref not in _describe_cache:
        _describe_cache[ref] = _info_from_dict(_call("ui", ref, ("describe", ref), DESCRIBE_TIMEOUT))
    return _describe_cache[ref]


def is_described(ref: str) -> bool:
    """La descrizione del plugin e' gia' pronta (describe() non aspetta)."""
    return resolve_ref(ref) in _describe_cache


def display_name(ref: str) -> str:
    """Nome da mostrare, senza caricare il plugin se non serve."""
    if not ref:
        return ""
    for info in (_scan_result or []):
        if info.ref == ref:
            return info.name
    if ref in _describe_cache:
        return _describe_cache[ref].name
    fmt, target, name = parse_ref(ref)
    if name:
        return name
    if fmt in ("vst3", "sfz"):
        return os.path.splitext(os.path.basename(target.rstrip("/\\")))[0]
    return target.rstrip("/#").rsplit("/", 1)[-1].rsplit("#", 1)[-1].rsplit(":", 1)[-1]


def parameter_texts(ref: str, params: dict, state: str) -> Dict[str, str]:
    """Come il plugin scrive i valori dei parametri (VST3; vuoto per LV2)."""
    ref = resolve_ref(ref)
    return _call("ui", ref, ("strings", ref, dict(params or {}), state or ""), UI_TIMEOUT)


def open_editor(ref: str, params: dict, state: str) -> Tuple[Dict[str, float], str]:
    """Apre l'interfaccia grafica del plugin (VST3) e aspetta che venga
    chiusa: torna (parametri, stato) come li ha lasciati l'utente."""
    ref = resolve_ref(ref)
    result = _call("ui", ref, ("editor", ref, dict(params or {}), state or ""), EDITOR_TIMEOUT)
    return result["params"], result["state"]


def signature(ref: str, params: dict, state: str) -> tuple:
    """Parte delle chiavi di cache che dipende dal plugin e dalla sua
    configurazione (e dal file del plugin, se cambia su disco)."""
    ref = resolve_ref(ref)
    fmt, target, _name = parse_ref(ref)
    if fmt in ("vst3", "sfz"):
        stamp = _bundle_stamp(target)
    else:       # LV2: i file scelti (es. l'SFZ di sfizz) se cambiano su disco
        from .lv2_host import decode_state
        stamp = max([_bundle_stamp(f) for f in decode_state(state).values()], default=0.0)
    return (ref, stamp, tuple(sorted((k, float(v)) for k, v in (params or {}).items())),
            hashlib.sha1((state or "").encode()).hexdigest() if state else "")


def _timeout_for(seconds: float) -> float:
    return DESCRIBE_TIMEOUT + 4.0 * max(0.0, seconds)


def process_audio(ref: str, params: dict, state: str, samples: np.ndarray, rate: int) -> np.ndarray:
    """Effetto: samples float32 (frame, 2) -> (frame, 2)."""
    ref = resolve_ref(ref)
    x = np.ascontiguousarray(samples[:, :2], dtype=np.float32)
    y = _call("render", ref, ("process", ref, int(rate), dict(params or {}), state or "", x),
              _timeout_for(len(x) / float(rate)))
    return np.ascontiguousarray(y, dtype=np.float32)


def render_events(ref: str, params: dict, state: str, events: List[Tuple[float, bytes]], seconds: float,
                  rate: int) -> np.ndarray:
    """Strumento: eventi MIDI (secondi, byte) -> float32 (frame, 2)."""
    ref = resolve_ref(ref)
    y = _call("render", ref, ("render", ref, int(rate), dict(params or {}), state or "",
                              [(float(t), bytes(d)) for t, d in events], float(seconds)),
              _timeout_for(seconds))
    return np.ascontiguousarray(y, dtype=np.float32)


_live_lock = threading.Lock()
_live_session = 0      # la sessione dal vivo aperta per ultima (live_start)


def live_start(ref: str, params: dict, state: str, blocksize: int, pan: int = 64, rate: int = 48000) -> dict:
    """Apre lo strumento per suonarlo dal vivo, nel suo processo, con
    l'uscita audio aperta li' (blocchi di 'blocksize' frame): da allora
    live_send() lo fa suonare. Un solo strumento dal vivo alla volta: quello
    di prima si chiude. Torna {"hostapi": ..., "latency_ms": ..., "session": n};
    solleva PluginError se il plugin o l'uscita audio non si aprono."""
    global _live_session
    ref = resolve_ref(ref)
    with _live_lock:
        _hosts["live"].stop()
        _live_session += 1
        info = dict(_call("live", ref, ("live_start", ref, int(rate), dict(params or {}), state or "",
                                        int(blocksize), int(pan)), DESCRIBE_TIMEOUT))
        info["session"] = _live_session
        return info


def live_send(session: int, data: bytes) -> bool:
    """Un messaggio MIDI allo strumento dal vivo della sessione 'session'.
    False se non suona piu' (chiuso, sostituito da un altro o caduto)."""
    if session != _live_session:
        return False
    return _hosts["live"].send(("live_midi", bytes(data)))


def live_stop(session: int):
    """Chiude lo strumento dal vivo, se e' ancora quello di 'session'."""
    with _live_lock:
        if session == _live_session:
            _hosts["live"].stop()


def midi_file_events(path: str) -> Tuple[List[Tuple[float, bytes]], float]:
    """Gli eventi di un file MIDI con il tempo in secondi (cambi di tempo
    compresi) e la durata totale in secondi."""
    import mido
    events = []
    t = 0.0
    for msg in mido.MidiFile(path):
        t += msg.time
        if not msg.is_meta and msg.type not in ("sysex",):
            events.append((t, bytes(msg.bytes())))
    return events, t


def encode_state(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")
