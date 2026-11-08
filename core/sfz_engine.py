"""
Motore SFZ interno: suona un file .sfz con la libreria del motore sfizz
(il fork sfizioso, oppure sfizz stesso: hanno la stessa interfaccia C,
sfizz.h, e lo stesso nome di file, libsfizz), chiamata con ctypes. Niente
plugin: si carica il file, si mandano le note e si calcolano blocchi di
audio. Gira nel processo dei plugin (core.plugin_worker), cosi' un crash
della libreria non porta giu' SoundText.

La libreria si cerca, in ordine: nella variabile d'ambiente
SOUNDTEXT_SFZ_LIB, nella cartella dell'utente dove la installa
"scarica_strumenti.py libreria" (user_lib_dir), nella cartella lib/ accanto
al programma e fra le librerie del sistema. Senza, sfz_available() e' False.
"""

import ctypes
import ctypes.util
import os
import re
import sys
import threading
from typing import List, Tuple

import numpy as np
from .i18n import tr

# Frame per chiamata a sfizz_render_block: a blocchi grandi il costo fisso
# di ogni chiamata (Python, ctypes, sfizz) pesa meno; gli eventi restano
# precisi al campione. Dal vivo render() riceve i blocchi del dispositivo.
BLOCK = 4096
# Qualita' dell'interpolazione dei campioni nel rendering (freewheeling):
# sfizz usa 10, tre volte piu' lento della qualita' 2 dell'ascolto dal vivo
# per una differenza inudibile (circa -60 dB).
OFFLINE_SAMPLE_QUALITY = 2
_PROCESS_FREEWHEELING = 1
# Nome del file e cartella dell'utente: gli stessi di scarica_strumenti.py
LIB_NAME = {"win32": "sfizz.dll", "darwin": "libsfizz.dylib"}.get(sys.platform, "libsfizz.so")


def user_lib_dir() -> str:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
        return os.path.join(base, "SoundText", "lib")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/SoundText/lib")
    return os.path.expanduser("~/.local/lib/soundtext")


class SfzError(Exception):
    pass


_lib = None
_lib_lock = threading.Lock()


def library_candidates() -> List[str]:
    from .version import get_app_root
    out = []
    env = os.environ.get("SOUNDTEXT_SFZ_LIB", "")
    if env:
        out.append(env)
    out += [os.path.join(user_lib_dir(), LIB_NAME), os.path.join(get_app_root(), "lib", LIB_NAME)]
    system = ctypes.util.find_library("sfizz")
    if system:
        out.append(system)
    return out


def library_found() -> str:
    """Il percorso della libreria che si userebbe, senza caricarla (per
    l'interfaccia: la libreria si carica solo nel processo dei plugin)."""
    for path in library_candidates():
        if os.sep not in path or os.path.exists(path):
            return path
    return ""


def _open_library(path: str):
    """La libreria in 'path' con le firme delle funzioni; None se non va."""
    try:
        lib = ctypes.CDLL(path)
        lib.sfizz_create_synth
    except (OSError, AttributeError):
        return None
    _set_signatures(lib)
    lib.path = path
    return lib


def _load_library():
    global _lib
    with _lib_lock:
        if _lib is not None:
            return _lib or None
        for path in library_candidates():
            if os.sep in path and not os.path.exists(path):
                continue
            lib = _open_library(path)
            if lib is None:
                continue
            _lib = lib
            return lib
        _lib = False
        return None


def _set_signatures(lib):
    """Tipi di argomenti e risultato delle funzioni usate."""
    vp, i = ctypes.c_void_p, ctypes.c_int
    sigs = {
        "sfizz_create_synth": ([], vp), "sfizz_free": ([vp], None),
        "sfizz_load_file": ([vp, ctypes.c_char_p], ctypes.c_bool),
        "sfizz_get_num_regions": ([vp], i),
        "sfizz_set_samples_per_block": ([vp, i], None),
        "sfizz_set_sample_rate": ([vp, ctypes.c_float], None),
        "sfizz_enable_freewheeling": ([vp], None), "sfizz_disable_freewheeling": ([vp], None),
        "sfizz_all_sound_off": ([vp], None),
        "sfizz_send_note_on": ([vp, i, i, i], None), "sfizz_send_note_off": ([vp, i, i, i], None),
        "sfizz_send_cc": ([vp, i, i, i], None), "sfizz_send_program_change": ([vp, i, i], None),
        "sfizz_send_pitch_wheel": ([vp, i, i], None),
        "sfizz_send_channel_aftertouch": ([vp, i, i], None),
        "sfizz_render_block": ([vp, ctypes.POINTER(ctypes.POINTER(ctypes.c_float)), i, i], None),
    }
    if hasattr(lib, "sfizz_set_sample_quality"):        # assente nelle sfizz molto vecchie
        sigs["sfizz_set_sample_quality"] = ([vp, i, i], None)
    for name, (args, res) in sigs.items():
        fn = getattr(lib, name)
        fn.argtypes = args
        fn.restype = res


# ---------------------------------------------------------------------------
# Render riproducibile
# ---------------------------------------------------------------------------
# Le regioni con lorand/hirand (round robin casuale: colpi di batteria, note
# ripetute che non suonano tutte uguali) usano un generatore casuale unico
# per tutta la libreria, che parte sempre dallo stesso seme ma avanza a ogni
# nota: due render dello stesso brano nello stesso processo suonavano diversi,
# e la libreria non ha una funzione per reimpostare il seme. Per il render
# offline si carica percio' una copia privata della libreria, che riparte dal
# seme iniziale, e la si scarica alla fine (circa 0,3 s): lo stesso brano da'
# lo stesso audio, campione per campione. Dal vivo resta l'istanza condivisa.

_copy_counter = 0
_copy_lock = threading.Lock()
# Blocchi piccoli nel render offline: oltre la parte precaricata, sfizz legge
# i campioni in sottofondo e in freewheeling li aspetta solo fra un blocco e
# l'altro; con blocchi da 4096 frame una nota trasposta in alto consumava la
# parte precaricata prima della pausa, e su un computer carico il suono
# cambiava da un render all'altro.
OFFLINE_BLOCK = 256


def _private_library():
    """(libreria, percorso della copia) caricata da una copia nuova; (None,
    None) se non si riesce (si ripiega sulla libreria condivisa)."""
    import shutil
    import tempfile
    global _copy_counter
    shared = _load_library()
    if shared is None:
        return None, None
    base, ext = os.path.splitext(os.path.basename(shared.path))
    with _copy_lock:
        _copy_counter += 1
        name = f"{base}-{os.getpid()}-{_copy_counter}{ext}"
    folder = os.path.join(tempfile.gettempdir(), "soundtext-sfz")
    copy = os.path.join(folder, name)
    try:
        os.makedirs(folder, exist_ok=True)
        shutil.copyfile(shared.path, copy)
    except OSError:
        return None, None
    if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(os.path.dirname(os.path.abspath(shared.path)))   # DLL accanto all'originale
        except OSError:
            pass
    lib = _open_library(copy)
    if lib is None:
        _remove_quietly(copy)
        return None, None
    return lib, copy


def _remove_quietly(path: str):
    try:
        os.remove(path)
    except OSError:
        pass


def _unload(lib, copy: str):
    import _ctypes
    try:
        if sys.platform == "win32":
            _ctypes.FreeLibrary(lib._handle)
        else:
            _ctypes.dlclose(lib._handle)
    except (OSError, AttributeError):
        pass
    _remove_quietly(copy)


def render_reproducible(path: str, samplerate: int, events: List[Tuple[float, bytes]],
                        seconds: float) -> np.ndarray:
    """Come SfzInstance(path, samplerate).render(events, seconds), ma con le
    scelte casuali del file sempre uguali (vedi sopra). Senza una copia
    della libreria si usa quella condivisa: il suono e' lo stesso, solo non
    ripetibile."""
    lib, copy = _private_library()
    if lib is None:
        import logging
        logging.getLogger(__name__).warning("Copia della libreria SFZ non caricata: render non ripetibile")
        inst = SfzInstance(path, samplerate)
        try:
            return inst.render(events, seconds)
        finally:
            inst.close()
    try:
        inst = SfzInstance(path, samplerate, lib=lib, block=OFFLINE_BLOCK)
        try:
            return inst.render(events, seconds)
        finally:
            inst.close()
            del inst
    finally:
        _unload(lib, copy)


def sfz_available() -> bool:
    return _load_library() is not None


def library_path() -> str:
    lib = _load_library()
    return lib.path if lib else ""


_SAMPLE = re.compile(r"\bsample\s*=\s*(\S)")
_INCLUDE = re.compile(r'#include\s+"([^"]+)"')


def placeholder_only(path: str) -> bool:
    """True se il file .sfz (con i suoi #include) usa solo i generatori
    interni (sample=*sine, *saw, *noise...) e nessun campione: e' il caso
    dei segnaposto "//dummy" del Discord SFZ GM Bank, che suonano come una
    sinusoide. Un file senza alcun sample= o illeggibile da' False."""
    base = os.path.dirname(os.path.abspath(path))
    seen, pending, first = set(), [os.path.abspath(path)], []
    while pending:
        name = pending.pop()
        if name in seen or len(seen) > 200:
            continue
        seen.add(name)
        try:
            with open(name, encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
        text = "\n".join(line.split("//", 1)[0] for line in text.splitlines())
        first += _SAMPLE.findall(text)
        if any(c != "*" for c in first):
            return False
        pending += [os.path.join(base, inc) for inc in _INCLUDE.findall(text)]
    return bool(first)


class SfzInstance:
    """Un file .sfz caricato a una frequenza di campionamento, pronto a
    suonare eventi MIDI (render). Non e' thread-safe."""

    def __init__(self, path: str, samplerate: int, lib=None, block: int = BLOCK):
        lib = lib or _load_library()
        self.block = int(block)
        if lib is None:
            raise SfzError(tr("libreria SFZ (sfizioso o sfizz) non trovata"))
        if not os.path.isfile(path):
            raise SfzError(tr("file SFZ non trovato: {path}", path=path))
        self._lib = lib
        self.samplerate = int(samplerate)
        self._synth = lib.sfizz_create_synth()
        if not self._synth:
            raise SfzError(tr("impossibile creare il motore SFZ"))
        lib.sfizz_set_sample_rate(self._synth, float(self.samplerate))
        lib.sfizz_set_samples_per_block(self._synth, self.block)
        # offline: i campioni si caricano tutti subito, niente streaming
        lib.sfizz_enable_freewheeling(self._synth)
        if hasattr(lib, "sfizz_set_sample_quality"):
            lib.sfizz_set_sample_quality(self._synth, _PROCESS_FREEWHEELING, OFFLINE_SAMPLE_QUALITY)
        if not lib.sfizz_load_file(self._synth, os.fsencode(path)):
            self.close()
            raise SfzError(tr("il file SFZ non si puo' caricare: {path}", path=path))
        self.regions = lib.sfizz_get_num_regions(self._synth)
        self._left = np.zeros(self.block, dtype=np.float32)
        self._right = np.zeros(self.block, dtype=np.float32)
        ptr = ctypes.POINTER(ctypes.c_float)
        self._channels = (ptr * 2)(self._left.ctypes.data_as(ptr), self._right.ctypes.data_as(ptr))

    def _send(self, delay: int, data: bytes):
        if not data:
            return
        lib, s = self._lib, self._synth
        status = data[0] & 0xF0
        a = data[1] if len(data) > 1 else 0
        b = data[2] if len(data) > 2 else 0
        if status == 0x90 and b > 0:
            lib.sfizz_send_note_on(s, delay, a, b)
        elif status in (0x80, 0x90):
            lib.sfizz_send_note_off(s, delay, a, b)
        elif status == 0xB0:
            lib.sfizz_send_cc(s, delay, a, b)
        elif status == 0xE0:
            lib.sfizz_send_pitch_wheel(s, delay, ((b << 7) | a) - 8192)
        elif status == 0xD0:
            lib.sfizz_send_channel_aftertouch(s, delay, a)
        elif status == 0xC0:
            lib.sfizz_send_program_change(s, delay, a)

    def render(self, events: List[Tuple[float, bytes]], seconds: float) -> np.ndarray:
        """Eventi (secondi, byte MIDI) ordinati -> float32 (frame, 2)."""
        n = int(round(seconds * self.samplerate))
        out = np.zeros((n, 2), dtype=np.float32)
        pending = [(int(round(t * self.samplerate)), data) for t, data in events]
        i = 0
        for start in range(0, n, self.block):
            frames = min(self.block, n - start)
            while i < len(pending) and pending[i][0] < start + frames:
                self._send(max(0, pending[i][0] - start), pending[i][1])
                i += 1
            self._lib.sfizz_render_block(self._synth, self._channels, 2, frames)
            out[start:start + frames, 0] = self._left[:frames]
            out[start:start + frames, 1] = self._right[:frames]
        return out

    def set_realtime(self):
        """Per suonare dal vivo (core.plugin_worker, "live_start"): il resto
        dei campioni si legge in sottofondo, non dentro render(), che deve
        stare nei tempi del dispositivo audio."""
        self._lib.sfizz_disable_freewheeling(self._synth)

    def reset(self):
        self._lib.sfizz_all_sound_off(self._synth)

    def close(self):
        if getattr(self, "_synth", None):
            self._lib.sfizz_free(self._synth)
            self._synth = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
