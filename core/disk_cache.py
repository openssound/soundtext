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
"""

import hashlib
import logging
import os
import threading
from typing import Optional

import numpy as np

CACHE_DIR_NAME = "cache"
MAX_BYTES = 2 * 1024 ** 3        # oltre, si tolgono i file usati meno di recente
MIN_BYTES = 256 * 1024           # le cose piu' piccole si rifanno in un attimo

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
    else:
        _dir = None


def cache_dir() -> Optional[str]:
    return _dir


def _file_for(key: str, directory: str) -> str:
    return os.path.join(directory, hashlib.sha1(key.encode("utf-8")).hexdigest() + ".npy")


def load(key: str) -> Optional[np.ndarray]:
    """Il rendering salvato per 'key', o None."""
    directory = _dir
    if directory is None:
        return None
    path = _file_for(key, directory)
    try:
        data = np.load(path, allow_pickle=False)
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
    files = []
    for name in os.listdir(directory):
        if not name.endswith(".npy") or ".tmp." in name:
            continue
        try:
            st = os.stat(os.path.join(directory, name))
        except OSError:
            continue
        files.append((st.st_mtime, st.st_size, name))
    total = sum(size for _t, size, _n in files)
    removed = 0
    for _mtime, size, name in sorted(files):
        if total <= max_bytes:
            break
        try:
            os.remove(os.path.join(directory, name))
            total -= size
            removed += 1
        except OSError:
            pass
    return removed


def clear() -> None:
    """Svuota la cache su disco del progetto corrente."""
    directory = _dir
    if directory and os.path.isdir(directory):
        for name in os.listdir(directory):
            if name.endswith(".npy"):
                try:
                    os.remove(os.path.join(directory, name))
                except OSError:
                    pass


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
