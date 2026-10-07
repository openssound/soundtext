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
import sys
import threading
from typing import List, Tuple

import numpy as np
from .i18n import tr

BLOCK = 512
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


def _load_library():
    global _lib
    with _lib_lock:
        if _lib is not None:
            return _lib or None
        for path in library_candidates():
            if os.sep in path and not os.path.exists(path):
                continue
            try:
                lib = ctypes.CDLL(path)
                lib.sfizz_create_synth
            except (OSError, AttributeError):
                continue
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
            for name, (args, res) in sigs.items():
                fn = getattr(lib, name)
                fn.argtypes = args
                fn.restype = res
            lib.path = path
            _lib = lib
            return lib
        _lib = False
        return None


def sfz_available() -> bool:
    return _load_library() is not None


def library_path() -> str:
    lib = _load_library()
    return lib.path if lib else ""


class SfzInstance:
    """Un file .sfz caricato a una frequenza di campionamento, pronto a
    suonare eventi MIDI (render). Non e' thread-safe."""

    def __init__(self, path: str, samplerate: int):
        lib = _load_library()
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
        lib.sfizz_set_samples_per_block(self._synth, BLOCK)
        # offline: i campioni si caricano tutti subito, niente streaming
        lib.sfizz_enable_freewheeling(self._synth)
        if not lib.sfizz_load_file(self._synth, os.fsencode(path)):
            self.close()
            raise SfzError(tr("il file SFZ non si puo' caricare: {path}", path=path))
        self.regions = lib.sfizz_get_num_regions(self._synth)
        self._left = np.zeros(BLOCK, dtype=np.float32)
        self._right = np.zeros(BLOCK, dtype=np.float32)
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
        for start in range(0, n, BLOCK):
            frames = min(BLOCK, n - start)
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
