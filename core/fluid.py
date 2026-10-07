"""
Collegamento diretto (ctypes) alla libreria FluidSynth, al posto del
pacchetto pyfluidsynth: solo le funzioni che servono a SoundText
(core.playback), con la ricerca della libreria adatta a come l'app e'
installata e i controlli sui tipi delle impostazioni.

Serve FluidSynth 2.x (libfluidsynth.so.3 / libfluidsynth-3.dll /
libfluidsynth.dylib). La libreria si cerca, nell'ordine:
- accanto all'app (build portable Windows: DLL affiancate a SoundText.exe;
  build Linux: cartella lib/);
- con i nomi di sistema (ctypes.util.find_library, poi il caricamento
  diretto per nome, che rispetta LD_LIBRARY_PATH);
- nelle cartelle di Homebrew su macOS (su Apple Silicon find_library non
  le vede) e in C:\\tools\\fluidsynth\\bin su Windows (Chocolatey).
Se non c'e', available() e' False e load_error() dice perche': SoundText
ripiega sul programma 'fluidsynth' da riga di comando, se c'e'.
"""

import ctypes
import ctypes.util
import glob
import os
import sys
from ctypes import POINTER, byref, c_char_p, c_double, c_float, c_int, c_void_p
from typing import List, Optional

import numpy as np

FLUID_OK = 0
FLUID_FAILED = -1
FLUID_PLAYER_PLAYING = 1
# tipi delle impostazioni (fluid_settings_get_type)
_NUM_TYPE, _INT_TYPE, _STR_TYPE = 0, 1, 2

_lib = None
_load_error = ""
_version = (0, 0, 0)


def _candidates() -> List[str]:
    names: List[str] = []
    try:
        from .version import get_app_root
        root = get_app_root()
    except Exception:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if sys.platform == "win32":
        for folder in (root, os.path.join(root, "fluidsynth"), r"C:\tools\fluidsynth\bin"):
            names += sorted(glob.glob(os.path.join(folder, "libfluidsynth*.dll")))
            names += sorted(glob.glob(os.path.join(folder, "fluidsynth*.dll")))
    elif sys.platform == "darwin":
        names += sorted(glob.glob(os.path.join(root, "lib", "libfluidsynth*.dylib")))
    else:
        names += sorted(glob.glob(os.path.join(root, "lib", "libfluidsynth.so*")))
    for base in ("fluidsynth", "libfluidsynth-3", "fluidsynth-3", "libfluidsynth"):
        found = ctypes.util.find_library(base)
        if found:
            names.append(found)
    if sys.platform == "darwin":
        prefixes = [os.environ.get("HOMEBREW_PREFIX", ""), "/opt/homebrew", "/usr/local", "/opt/local"]
        names += [os.path.join(p, "lib", "libfluidsynth.dylib") for p in prefixes if p]
    elif sys.platform != "win32":
        names += ["libfluidsynth.so.3", "libfluidsynth.so"]
    seen, unique = set(), []
    for name in names:
        if name not in seen:
            seen.add(name)
            unique.append(name)
    return unique


def _declare(lib):
    def fn(name, restype, *argtypes):
        f = getattr(lib, name)
        f.restype = restype
        f.argtypes = list(argtypes)

    fn("fluid_version", None, POINTER(c_int), POINTER(c_int), POINTER(c_int))
    fn("new_fluid_settings", c_void_p)
    fn("delete_fluid_settings", None, c_void_p)
    fn("fluid_settings_get_type", c_int, c_void_p, c_char_p)
    fn("fluid_settings_setnum", c_int, c_void_p, c_char_p, c_double)
    fn("fluid_settings_setint", c_int, c_void_p, c_char_p, c_int)
    fn("fluid_settings_setstr", c_int, c_void_p, c_char_p, c_char_p)
    fn("fluid_settings_getnum", c_int, c_void_p, c_char_p, POINTER(c_double))
    fn("fluid_settings_getint", c_int, c_void_p, c_char_p, POINTER(c_int))
    fn("fluid_settings_copystr", c_int, c_void_p, c_char_p, c_char_p, c_int)
    fn("new_fluid_synth", c_void_p, c_void_p)
    fn("delete_fluid_synth", None, c_void_p)
    fn("fluid_synth_sfload", c_int, c_void_p, c_char_p, c_int)
    fn("fluid_synth_program_select", c_int, c_void_p, c_int, c_int, c_int, c_int)
    fn("fluid_synth_noteon", c_int, c_void_p, c_int, c_int, c_int)
    fn("fluid_synth_noteoff", c_int, c_void_p, c_int, c_int)
    fn("fluid_synth_cc", c_int, c_void_p, c_int, c_int, c_int)
    fn("fluid_synth_pitch_bend", c_int, c_void_p, c_int, c_int)
    fn("fluid_synth_all_notes_off", c_int, c_void_p, c_int)
    fn("fluid_synth_system_reset", c_int, c_void_p)
    fn("fluid_synth_set_gain", None, c_void_p, c_float)
    fn("fluid_synth_get_gain", c_float, c_void_p)
    fn("fluid_synth_write_s16", c_int, c_void_p, c_int, c_void_p, c_int, c_int, c_void_p, c_int, c_int)
    fn("new_fluid_audio_driver", c_void_p, c_void_p, c_void_p)
    fn("delete_fluid_audio_driver", None, c_void_p)
    fn("new_fluid_player", c_void_p, c_void_p)
    fn("delete_fluid_player", None, c_void_p)
    fn("fluid_player_add", c_int, c_void_p, c_char_p)
    fn("fluid_player_play", c_int, c_void_p)
    fn("fluid_player_stop", c_int, c_void_p)
    fn("fluid_player_seek", c_int, c_void_p, c_int)
    fn("fluid_player_get_status", c_int, c_void_p)
    # riverbero: per gruppo di effetti da FluidSynth 2.2, prima tutto insieme
    for name in ("roomsize", "damp", "width", "level"):
        if hasattr(lib, f"fluid_synth_set_reverb_group_{name}"):
            fn(f"fluid_synth_set_reverb_group_{name}", c_int, c_void_p, c_int, c_double)
    if hasattr(lib, "fluid_synth_set_reverb"):
        fn("fluid_synth_set_reverb", c_int, c_void_p, c_double, c_double, c_double, c_double)


def _load():
    global _lib, _load_error, _version
    if _lib is not None or _load_error:
        return _lib
    if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
        # le DLL da cui dipende FluidSynth (glib, libsndfile...) stanno accanto
        for folder in {os.path.dirname(p) for p in _candidates() if os.path.isabs(p)}:
            if os.path.isdir(folder):
                try:
                    os.add_dll_directory(folder)
                except OSError:
                    pass
    tried = []
    for name in _candidates():
        try:
            lib = ctypes.CDLL(name)
        except OSError as exc:
            tried.append(f"{name}: {exc}")
            continue
        if not hasattr(lib, "new_fluid_synth"):
            continue
        major, minor, micro = c_int(), c_int(), c_int()
        lib.fluid_version(byref(major), byref(minor), byref(micro))
        if major.value < 2:
            tried.append(f"{name}: FluidSynth {major.value}.{minor.value} (serve la 2.x)")
            continue
        try:
            _declare(lib)
        except AttributeError as exc:
            tried.append(f"{name}: {exc}")
            continue
        _lib, _version = lib, (major.value, minor.value, micro.value)
        return _lib
    _load_error = "; ".join(tried[-3:]) or "libreria FluidSynth non trovata"
    return None


def available() -> bool:
    return _load() is not None


def load_error() -> str:
    _load()
    return _load_error


def version() -> tuple:
    _load()
    return _version


class Synth:
    """Un sintetizzatore FluidSynth con le sue impostazioni. Le chiavi
    extra (es. {"synth.reverb.active": 1}) sono impostazioni di FluidSynth
    applicate prima della creazione."""

    def __init__(self, gain: float = 0.2, samplerate: int = 44100, channels: int = 256, **settings):
        lib = _load()
        if lib is None:
            raise RuntimeError(_load_error)
        self._lib = lib
        self.settings = lib.new_fluid_settings()
        self.setting("synth.gain", gain)
        self.setting("synth.sample-rate", samplerate)
        self.setting("synth.midi-channels", channels)
        for key, value in settings.items():
            self.setting(key, value)
        self.synth = lib.new_fluid_synth(self.settings)
        if not self.synth:
            lib.delete_fluid_settings(self.settings)
            self.settings = None
            raise RuntimeError("new_fluid_synth fallita")
        self.audio_driver = None

    # ------------------------------------------------------------ impostazioni

    def setting(self, key: str, value) -> bool:
        """Imposta secondo il tipo dichiarato da FluidSynth (un intero passato
        a un'impostazione numerica non va perso, come con pyfluidsynth)."""
        name = key.encode()
        kind = self._lib.fluid_settings_get_type(self.settings, name)
        if kind == _NUM_TYPE:
            result = self._lib.fluid_settings_setnum(self.settings, name, float(value))
        elif kind == _INT_TYPE:
            result = self._lib.fluid_settings_setint(self.settings, name, int(value))
        elif kind == _STR_TYPE:
            result = self._lib.fluid_settings_setstr(self.settings, name, str(value).encode())
        else:
            return False
        return result == FLUID_OK

    def get_setting(self, key: str):
        name = key.encode()
        kind = self._lib.fluid_settings_get_type(self.settings, name)
        if kind == _NUM_TYPE:
            num = c_double()
            if self._lib.fluid_settings_getnum(self.settings, name, byref(num)) == FLUID_OK:
                return round(num.value, 6)
        elif kind == _INT_TYPE:
            val = c_int()
            if self._lib.fluid_settings_getint(self.settings, name, byref(val)) == FLUID_OK:
                return val.value
        elif kind == _STR_TYPE:
            buf = ctypes.create_string_buffer(256)
            if self._lib.fluid_settings_copystr(self.settings, name, buf, len(buf)) == FLUID_OK:
                return buf.value.decode(errors="replace")
        return None

    # ------------------------------------------------------------ suono

    def sfload(self, path: str, reset_presets: bool = False) -> int:
        """Id del SoundFont caricato, -1 se il file non e' valido.
        reset_presets riassegna subito i preset ai canali (come faceva
        pyfluidsynth, di norma no: ci pensa system_reset)."""
        return self._lib.fluid_synth_sfload(self.synth, os.fsencode(path), 1 if reset_presets else 0)

    def program_select(self, channel: int, sfid: int, bank: int, preset: int) -> int:
        return self._lib.fluid_synth_program_select(self.synth, channel, sfid, bank, preset)

    def noteon(self, channel: int, key: int, velocity: int) -> int:
        return self._lib.fluid_synth_noteon(self.synth, channel, max(0, min(127, key)), max(0, min(127, velocity)))

    def noteoff(self, channel: int, key: int) -> int:
        return self._lib.fluid_synth_noteoff(self.synth, channel, max(0, min(127, key)))

    def cc(self, channel: int, control: int, value: int) -> int:
        return self._lib.fluid_synth_cc(self.synth, channel, control, max(0, min(127, value)))

    def pitch_bend(self, channel: int, value: int) -> int:
        """value da -8192 a 8191 (0 = nessuna variazione)."""
        return self._lib.fluid_synth_pitch_bend(self.synth, channel, max(0, min(16383, value + 8192)))

    def all_notes_off(self, channel: int = -1) -> int:
        """Rilascia le note del canale (-1: di tutti i canali)."""
        return self._lib.fluid_synth_all_notes_off(self.synth, channel)

    def system_reset(self) -> int:
        return self._lib.fluid_synth_system_reset(self.synth)

    def set_gain(self, value: float):
        """Guadagno di un synth gia' creato: a differenza dell'impostazione
        'synth.gain' resta valido anche dopo system_reset()."""
        self._lib.fluid_synth_set_gain(self.synth, float(value))

    def get_gain(self) -> float:
        return float(self._lib.fluid_synth_get_gain(self.synth))

    def set_reverb(self, roomsize: float, damping: float, width: float, level: float):
        lib = self._lib
        if hasattr(lib, "fluid_synth_set_reverb_group_roomsize"):
            lib.fluid_synth_set_reverb_group_roomsize(self.synth, -1, roomsize)
            lib.fluid_synth_set_reverb_group_damp(self.synth, -1, damping)
            lib.fluid_synth_set_reverb_group_width(self.synth, -1, width)
            lib.fluid_synth_set_reverb_group_level(self.synth, -1, level)
        else:
            lib.fluid_synth_set_reverb(self.synth, roomsize, damping, width, level)
        # le impostazioni restano allineate (e sono quelle che si rileggono)
        self.setting("synth.reverb.room-size", roomsize)
        self.setting("synth.reverb.damp", damping)
        self.setting("synth.reverb.width", width)
        self.setting("synth.reverb.level", level)

    def get_samples(self, frames: int) -> np.ndarray:
        """frames campioni stereo a 16 bit, alternati (sinistro, destro)."""
        buf = np.empty(2 * frames, dtype=np.int16)
        ptr = c_void_p(buf.ctypes.data)
        self._lib.fluid_synth_write_s16(self.synth, frames, ptr, 0, 2, ptr, 1, 2)
        return buf

    # ------------------------------------------------------------ uscita audio

    def start_audio(self, driver: Optional[str] = None) -> bool:
        """Apre il driver audio in tempo reale (thread di FluidSynth); False
        se non si apre. Nessun driver MIDI: gli ingressi MIDI li gestisce
        SoundText (core.midi_input)."""
        if self.audio_driver:
            self._lib.delete_fluid_audio_driver(self.audio_driver)
            self.audio_driver = None
        if driver:
            self.setting("audio.driver", driver)
        self.audio_driver = self._lib.new_fluid_audio_driver(self.settings, self.synth) or None
        return self.audio_driver is not None

    def delete(self):
        if self.audio_driver:
            self._lib.delete_fluid_audio_driver(self.audio_driver)
            self.audio_driver = None
        if self.synth:
            self._lib.delete_fluid_synth(self.synth)
            self.synth = None
        if self.settings:
            self._lib.delete_fluid_settings(self.settings)
            self.settings = None


class Player:
    """Lettore di file MIDI collegato a un Synth (rendering offline con
    Synth.get_samples)."""

    def __init__(self, synth: Synth):
        self._lib = synth._lib
        self._player = self._lib.new_fluid_player(synth.synth)
        if not self._player:
            raise RuntimeError("new_fluid_player fallita")

    def add(self, midi_path: str) -> bool:
        """False se il file non c'e' (fluid_player_add lo accetterebbe
        comunque, fallendo solo durante la lettura)."""
        if not os.path.isfile(midi_path):
            return False
        return self._lib.fluid_player_add(self._player, os.fsencode(midi_path)) == FLUID_OK

    def play(self):
        self._lib.fluid_player_play(self._player)

    def playing(self) -> bool:
        return self._lib.fluid_player_get_status(self._player) == FLUID_PLAYER_PLAYING

    def delete(self):
        if self._player:
            self._lib.fluid_player_stop(self._player)
            self._lib.fluid_player_seek(self._player, 0)
            self._lib.delete_fluid_player(self._player)
            self._player = None
