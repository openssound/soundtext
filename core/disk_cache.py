"""
Cache dei rendering su disco, accanto al progetto (<Progetto>_audio/cache/):
tracce elaborate dagli effetti (NAM, plugin, amplificatori), strumenti
plugin e time-stretch, salvati quando si calcolano e riusati alla
riapertura del progetto, cosi' un computer lento non rifa' tutto a ogni
avvio. La chiave e' la stessa delle cache in memoria (core.effect_render,
core.audio_tracks.stretched), che cambia con le note, le clip, i file e i
parametri: un rendering vecchio non si riusa mai per sbaglio, resta solo
sul disco finche' la cartella non supera MAX_BYTES (si tolgono i meno
usati). La cartella *_audio/ e' gia' esclusa da git.

Un progetto mai salvato non ha cartella: niente cache su disco.

Oltre al limite per progetto c'e' un limite complessivo (global_limit: 5 GB,
o il 10% dello spazio libero se minore) su tutte le cartelle di cache dei
progetti aperti finora, elencate in un registro nella cartella di
configurazione: oltre, si tolgono i file usati meno di recente fra tutti i
progetti (un progetto che non c'e' piu' esce dal registro). Svuota la cache
(menu File) usa clear() e clear_all().

I file si leggono mappati in memoria (np.load con mmap_mode): il sistema
legge solo le parti usate e le libera quando serve. Su Windows un file
mappato non si puo' cancellare finche' e' in uso: prune() e clear() lo
saltano. Il nome dei file porta la versione del formato (FORMAT_VERSION):
i file di un formato vecchio non si leggono e prune() li toglie per primi.
"""

import hashlib
import json
import logging
import os
import shutil
import threading
import time
from typing import Dict, List, Optional, Tuple

import numpy as np

CACHE_DIR_NAME = "cache"
MAX_BYTES = 2 * 1024 ** 3        # per progetto: oltre, si tolgono i file usati meno di recente
MIN_BYTES = 256 * 1024           # le cose piu' piccole si rifanno in un attimo
GLOBAL_MAX_BYTES = 5 * 1024 ** 3  # tutti i progetti insieme
GLOBAL_FREE_SHARE = 0.10         # ...o il 10% dello spazio libero, se minore
FORMAT_VERSION = "v2"
SUFFIX = "." + FORMAT_VERSION + ".npy"
REGISTRY_NAME = "disk_cache_registry.json"

_dir: Optional[str] = None
_lock = threading.Lock()
_writing = set()                 # chiavi in scrittura (un thread per volta)


def set_project(project_path: Optional[str]) -> None:
    """La cartella della cache per il progetto salvato in project_path
    (None = progetto non salvato: nessuna cache su disco)."""
    global _dir
    if project_path:
        from .audio_tracks import audio_dir_for_project
        _dir = os.path.join(audio_dir_for_project(project_path), CACHE_DIR_NAME)
        _register(_dir)
    else:
        _dir = None


def cache_dir() -> Optional[str]:
    return _dir


def _file_for(key: str, directory: str) -> str:
    return os.path.join(directory, hashlib.sha1(key.encode("utf-8")).hexdigest() + SUFFIX)


def _is_cache_file(name: str) -> bool:
    return name.endswith(".npy") and ".tmp." not in name


# ---------------------------------------------------------------------------
# Registro delle cartelle di cache di tutti i progetti
# ---------------------------------------------------------------------------

_registry_lock = threading.Lock()


def _registry_path() -> str:
    from .settings import CONFIG_DIR
    return os.path.join(CONFIG_DIR, REGISTRY_NAME)


def _read_registry() -> Dict[str, dict]:
    try:
        with open(_registry_path(), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_registry(data: Dict[str, dict]) -> None:
    path = _registry_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1)
        os.replace(tmp, path)
    except OSError:
        logging.getLogger(__name__).warning("Registro della cache non scritto: %s", path, exc_info=True)


def _register(directory: str) -> None:
    """Annota (o aggiorna) la cartella nel registro, con dimensione e ultimo uso."""
    directory = os.path.abspath(directory)
    with _registry_lock:
        data = _read_registry()
        data[directory] = {"size": dir_size(directory), "used": time.time()}
        _write_registry(data)


def registered_dirs() -> List[str]:
    """Le cartelle di cache note che esistono ancora (le altre escono dal registro)."""
    with _registry_lock:
        data = _read_registry()
        alive = {d: v for d, v in data.items() if os.path.isdir(d) or os.path.isdir(os.path.dirname(d))}
        if len(alive) != len(data):
            _write_registry(alive)
    return [d for d in alive if os.path.isdir(d)]


def dir_size(directory: Optional[str]) -> int:
    """I byte occupati dalla cartella di cache (0 se non c'e')."""
    total = 0
    if directory and os.path.isdir(directory):
        for name in os.listdir(directory):
            if _is_cache_file(name):
                try:
                    total += os.stat(os.path.join(directory, name)).st_size
                except OSError:
                    pass
    return total


def total_size() -> int:
    """I byte occupati dalle cache di tutti i progetti."""
    dirs = set(registered_dirs())
    if _dir:
        dirs.add(os.path.abspath(_dir))
    return sum(dir_size(d) for d in dirs)


def global_limit(directory: Optional[str] = None) -> int:
    """Il limite complessivo: GLOBAL_MAX_BYTES o, se minore, il 10% dello
    spazio libero sul disco della cache (contando anche la cache stessa,
    che si puo' liberare)."""
    limit = GLOBAL_MAX_BYTES
    probe = directory or _dir
    while probe and not os.path.isdir(probe):
        parent = os.path.dirname(probe)
        probe = parent if parent != probe else None
    if probe:
        try:
            free = shutil.disk_usage(probe).free + total_size()
            limit = min(limit, int(free * GLOBAL_FREE_SHARE))
        except OSError:
            pass
    return max(MIN_BYTES, limit)


def load(key: str) -> Optional[np.ndarray]:
    """Il rendering salvato per 'key', o None."""
    directory = _dir
    if directory is None:
        return None
    path = _file_for(key, directory)
    try:
        # mappato: il sistema legge solo le parti usate (sola lettura)
        data = np.load(path, mmap_mode="r", allow_pickle=False)
    except (OSError, ValueError):
        return None
    try:
        os.utime(path)           # usato adesso: e' fra gli ultimi a sparire
    except OSError:
        pass
    return data


def store(key: str, data: np.ndarray, wait: bool = False) -> None:
    """Salva il rendering (in sottofondo, salvo 'wait'): un file scritto a
    meta' non si legge mai, perche' prende il suo nome solo alla fine."""
    directory = _dir
    if directory is None or data is None or data.nbytes < MIN_BYTES:
        return
    path = _file_for(key, directory)
    with _lock:
        if path in _writing or os.path.exists(path):
            return
        _writing.add(path)

    def write():
        try:
            os.makedirs(directory, exist_ok=True)
            tmp = path + ".tmp.npy"
            np.save(tmp, np.ascontiguousarray(data), allow_pickle=False)
            os.replace(tmp, path)
            prune(directory)
            _maybe_prune_global(directory)
        except OSError:
            logging.getLogger(__name__).warning("Cache su disco non scritta: %s", path, exc_info=True)
        finally:
            with _lock:
                _writing.discard(path)

    if wait:
        write()
    else:
        threading.Thread(target=write, daemon=True, name="disk-cache").start()


def prune(directory: Optional[str] = None, max_bytes: int = MAX_BYTES) -> int:
    """Toglie i file usati meno di recente finche' la cartella sta in
    max_bytes; ritorna quanti ne ha tolti."""
    directory = directory or _dir
    if not directory or not os.path.isdir(directory):
        return 0
    return _remove_oldest(_cache_files(directory), max_bytes)


def _cache_files(directory: str) -> List[Tuple[bool, float, int, str]]:
    """(formato attuale?, ultimo uso, byte, percorso) dei file della cartella."""
    files = []
    try:
        names = os.listdir(directory)
    except OSError:
        return files
    for name in names:
        if not _is_cache_file(name):
            continue
        path = os.path.join(directory, name)
        try:
            st = os.stat(path)
        except OSError:
            continue
        files.append((name.endswith(SUFFIX), st.st_mtime, st.st_size, path))
    return files


def _remove_oldest(files, max_bytes: int, protected: frozenset = frozenset()) -> int:
    """Toglie i file di un formato vecchio e poi i meno usati di recente
    finche' il totale sta in max_bytes; quelli in 'protected' (il progetto
    aperto) si contano ma non si toccano. Un file che non si puo' togliere
    (mappato su Windows) si salta e si conta come tolto: altrimenti, per
    compensare, si cancellerebbero tutti i file piu' recenti."""
    total = sum(size for _cur, _t, size, _p in files)
    removed = 0
    for current, _mtime, size, path in sorted(files):     # i vecchi formati (False) prima
        if current and total <= max_bytes:
            break
        if path in protected:
            continue
        try:
            os.remove(path)
            removed += 1
        except OSError:
            pass                 # in uso: tornera' candidato la prossima volta
        total -= size
    return removed


GLOBAL_PRUNE_INTERVAL = 60.0      # secondi fra due controlli del limite complessivo
_last_global_prune = 0.0


def _maybe_prune_global(directory: str) -> None:
    """prune_global al piu' una volta al minuto: scorre le cache di tutti i
    progetti, e un render ne scrive anche centinaia di file."""
    global _last_global_prune
    now = time.monotonic()
    with _lock:
        if now - _last_global_prune < GLOBAL_PRUNE_INTERVAL and _last_global_prune:
            return
        _last_global_prune = now
    prune_global(directory)


def prune_global(directory: Optional[str] = None, max_bytes: Optional[int] = None) -> int:
    """Come prune, ma su tutte le cartelle di cache del registro insieme:
    si tolgono i file meno usati di recente fra tutti i progetti."""
    dirs = set(registered_dirs())
    for d in (directory, _dir):
        if d:
            dirs.add(os.path.abspath(d))
    files = [f for d in dirs for f in _cache_files(d)]
    # il progetto aperto non si tocca (lo limita gia' prune, a MAX_BYTES): con
    # un limite piccolo (poco spazio libero) si cancellavano i render appena
    # scritti del brano che si sta ascoltando, e la cache non serviva piu'
    protected = frozenset(p for _c, _t, _s, p in _cache_files(os.path.abspath(_dir))) if _dir else frozenset()
    removed = _remove_oldest(files, global_limit(directory) if max_bytes is None else max_bytes, protected)
    if directory:
        _register(directory)
    return removed


def _clear_dir(directory: Optional[str]) -> int:
    """Toglie i file di cache della cartella; ritorna i byte liberati."""
    freed = 0
    for _cur, _t, size, path in (_cache_files(directory) if directory else []):
        try:
            os.remove(path)
            freed += size
        except OSError:
            pass                 # in uso (Windows): resta
    return freed


def clear() -> int:
    """Svuota la cache su disco del progetto corrente; i byte liberati."""
    freed = _clear_dir(_dir)
    if _dir:
        _register(_dir)
    return freed


def clear_all() -> int:
    """Svuota le cache su disco di tutti i progetti del registro."""
    dirs = set(registered_dirs())
    if _dir:
        dirs.add(os.path.abspath(_dir))
    freed = sum(_clear_dir(d) for d in dirs)
    with _registry_lock:
        data = _read_registry()
        for d in data:
            data[d]["size"] = dir_size(d)
        _write_registry(data)
    return freed


def wait_writes(timeout: float = 30.0) -> bool:
    """Aspetta che le scritture in sottofondo siano finite (chiusura del
    programma, test); False se non lo sono entro timeout secondi."""
    import time
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with _lock:
            if not _writing:
                return True
        time.sleep(0.01)
    return False
