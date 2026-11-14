"""
Host CLAP minimo per l'elaborazione offline e l'ascolto dal vivo. CLAP
(https://github.com/free-audio/clap) ha un'interfaccia binaria in C puro:
il file .clap e' una libreria che esporta 'clap_entry', e tutto passa da
strutture di puntatori a funzione, chiamate qui con ctypes senza librerie
in mezzo.

Supporta cio' che serve a un effetto o a uno strumento senza la sua
finestra grafica: porte audio (la principale in ingresso e in uscita; le
altre ricevono silenzio), note in MIDI o come eventi CLAP, i parametri
(clap.params, impostati con eventi PARAM_VALUE), la latenza dichiarata
dal plugin (clap.latency), che si compensa, e lo stato interno (clap.state:
save_state/load_state, un blocco di byte che il plugin scrive e rilegge).

L'interfaccia grafica del plugin (clap.gui) si apre dentro una finestra
che le da' chi usa l'istanza (core.clap_gui, con Qt): qui ci sono
open_gui/close_gui e cio' che al plugin serve per farla vivere, cioe' i
timer (clap.timer-support) e i descrittori di file da sorvegliare
(clap.posix-fd-support, su Linux), serviti da idle() e fd_event().

Un riferimento e' 'clap:/percorso/Nome.clap|id.del.plugin': un file .clap
puo' contenere molti plugin (LSP ne ha centinaia), distinti dall'id.
"""

import ctypes
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .i18n import tr

BLOCK = 1024

c_void = ctypes.c_void_p
c_str = ctypes.c_char_p
u32 = ctypes.c_uint32


class _Version(ctypes.Structure):
    _fields_ = [("major", u32), ("minor", u32), ("revision", u32)]


_HOST_VERSION = (1, 2, 0)


class _Entry(ctypes.Structure):
    _fields_ = [("clap_version", _Version),
                ("init", ctypes.CFUNCTYPE(ctypes.c_bool, c_str)),
                ("deinit", ctypes.CFUNCTYPE(None)),
                ("get_factory", ctypes.CFUNCTYPE(c_void, c_str))]


class _Descriptor(ctypes.Structure):
    _fields_ = [("clap_version", _Version), ("id", c_str), ("name", c_str), ("vendor", c_str), ("url", c_str),
                ("manual_url", c_str), ("support_url", c_str), ("version", c_str), ("description", c_str),
                ("features", ctypes.POINTER(c_str))]


class _Host(ctypes.Structure):
    _fields_ = [("clap_version", _Version), ("host_data", c_void), ("name", c_str), ("vendor", c_str),
                ("url", c_str), ("version", c_str),
                ("get_extension", ctypes.CFUNCTYPE(c_void, c_void, c_str)),
                ("request_restart", ctypes.CFUNCTYPE(None, c_void)),
                ("request_process", ctypes.CFUNCTYPE(None, c_void)),
                ("request_callback", ctypes.CFUNCTYPE(None, c_void))]


class _Factory(ctypes.Structure):
    _fields_ = [("get_plugin_count", ctypes.CFUNCTYPE(u32, c_void)),
                ("get_plugin_descriptor", ctypes.CFUNCTYPE(ctypes.POINTER(_Descriptor), c_void, u32)),
                ("create_plugin", ctypes.CFUNCTYPE(c_void, c_void, ctypes.POINTER(_Host), c_str))]


class _AudioBuffer(ctypes.Structure):
    _fields_ = [("data32", ctypes.POINTER(ctypes.POINTER(ctypes.c_float))),
                ("data64", ctypes.POINTER(ctypes.POINTER(ctypes.c_double))),
                ("channel_count", u32), ("latency", u32), ("constant_mask", ctypes.c_uint64)]


class _EventHeader(ctypes.Structure):
    _fields_ = [("size", u32), ("time", u32), ("space_id", ctypes.c_uint16), ("type", ctypes.c_uint16),
                ("flags", u32)]


class _NoteEvent(ctypes.Structure):
    _fields_ = [("header", _EventHeader), ("note_id", ctypes.c_int32), ("port_index", ctypes.c_int16),
                ("channel", ctypes.c_int16), ("key", ctypes.c_int16), ("velocity", ctypes.c_double)]


class _MidiEvent(ctypes.Structure):
    _fields_ = [("header", _EventHeader), ("port_index", ctypes.c_uint16), ("data", ctypes.c_uint8 * 3)]


class _ParamValueEvent(ctypes.Structure):
    _fields_ = [("header", _EventHeader), ("param_id", u32), ("cookie", c_void), ("note_id", ctypes.c_int32),
                ("port_index", ctypes.c_int16), ("channel", ctypes.c_int16), ("key", ctypes.c_int16),
                ("value", ctypes.c_double)]


_EVENT_NOTE_ON, _EVENT_NOTE_OFF, _EVENT_PARAM_VALUE, _EVENT_MIDI = 0, 1, 5, 10


class _InputEvents(ctypes.Structure):
    _fields_ = [("ctx", c_void),
                ("size", ctypes.CFUNCTYPE(u32, c_void)),
                ("get", ctypes.CFUNCTYPE(c_void, c_void, u32))]


class _OutputEvents(ctypes.Structure):
    _fields_ = [("ctx", c_void),
                ("try_push", ctypes.CFUNCTYPE(ctypes.c_bool, c_void, c_void))]


class _Process(ctypes.Structure):
    _fields_ = [("steady_time", ctypes.c_int64), ("frames_count", u32), ("transport", c_void),
                ("audio_inputs", ctypes.POINTER(_AudioBuffer)), ("audio_outputs", ctypes.POINTER(_AudioBuffer)),
                ("audio_inputs_count", u32), ("audio_outputs_count", u32),
                ("in_events", ctypes.POINTER(_InputEvents)), ("out_events", ctypes.POINTER(_OutputEvents))]


class _Plugin(ctypes.Structure):
    _fields_ = [("desc", ctypes.POINTER(_Descriptor)), ("plugin_data", c_void),
                ("init", ctypes.CFUNCTYPE(ctypes.c_bool, c_void)),
                ("destroy", ctypes.CFUNCTYPE(None, c_void)),
                ("activate", ctypes.CFUNCTYPE(ctypes.c_bool, c_void, ctypes.c_double, u32, u32)),
                ("deactivate", ctypes.CFUNCTYPE(None, c_void)),
                ("start_processing", ctypes.CFUNCTYPE(ctypes.c_bool, c_void)),
                ("stop_processing", ctypes.CFUNCTYPE(None, c_void)),
                ("reset", ctypes.CFUNCTYPE(None, c_void)),
                ("process", ctypes.CFUNCTYPE(ctypes.c_int32, c_void, ctypes.POINTER(_Process))),
                ("get_extension", ctypes.CFUNCTYPE(c_void, c_void, c_str)),
                ("on_main_thread", ctypes.CFUNCTYPE(None, c_void))]


# --- estensioni del plugin ---------------------------------------------------

class _ParamInfo(ctypes.Structure):
    _fields_ = [("id", u32), ("flags", u32), ("cookie", c_void), ("name", ctypes.c_char * 256),
                ("module", ctypes.c_char * 1024), ("min_value", ctypes.c_double),
                ("max_value", ctypes.c_double), ("default_value", ctypes.c_double)]


_PARAM_IS_STEPPED, _PARAM_IS_HIDDEN, _PARAM_IS_READONLY, _PARAM_IS_BYPASS = 1 << 0, 1 << 2, 1 << 3, 1 << 4
_PARAM_IS_ENUM = 1 << 16


class _PluginParams(ctypes.Structure):
    _fields_ = [("count", ctypes.CFUNCTYPE(u32, c_void)),
                ("get_info", ctypes.CFUNCTYPE(ctypes.c_bool, c_void, u32, ctypes.POINTER(_ParamInfo))),
                ("get_value", ctypes.CFUNCTYPE(ctypes.c_bool, c_void, u32, ctypes.POINTER(ctypes.c_double))),
                ("value_to_text", ctypes.CFUNCTYPE(ctypes.c_bool, c_void, u32, ctypes.c_double,
                                                   ctypes.c_char_p, u32)),
                ("text_to_value", ctypes.CFUNCTYPE(ctypes.c_bool, c_void, u32, c_str,
                                                   ctypes.POINTER(ctypes.c_double))),
                ("flush", ctypes.CFUNCTYPE(None, c_void, ctypes.POINTER(_InputEvents),
                                           ctypes.POINTER(_OutputEvents)))]


class _AudioPortInfo(ctypes.Structure):
    _fields_ = [("id", u32), ("name", ctypes.c_char * 256), ("flags", u32), ("channel_count", u32),
                ("port_type", c_str), ("in_place_pair", u32)]


class _PluginAudioPorts(ctypes.Structure):
    _fields_ = [("count", ctypes.CFUNCTYPE(u32, c_void, ctypes.c_bool)),
                ("get", ctypes.CFUNCTYPE(ctypes.c_bool, c_void, u32, ctypes.c_bool,
                                         ctypes.POINTER(_AudioPortInfo)))]


class _NotePortInfo(ctypes.Structure):
    _fields_ = [("id", u32), ("supported_dialects", u32), ("preferred_dialect", u32),
                ("name", ctypes.c_char * 256)]


_DIALECT_CLAP, _DIALECT_MIDI = 1, 2


class _PluginNotePorts(ctypes.Structure):
    _fields_ = [("count", ctypes.CFUNCTYPE(u32, c_void, ctypes.c_bool)),
                ("get", ctypes.CFUNCTYPE(ctypes.c_bool, c_void, u32, ctypes.c_bool,
                                         ctypes.POINTER(_NotePortInfo)))]


class _PluginLatency(ctypes.Structure):
    _fields_ = [("get", ctypes.CFUNCTYPE(u32, c_void))]


class _Stream(ctypes.Structure):
    """clap_istream / clap_ostream: read(stream, buffer, size) o
    write(stream, buffer, size), che restituiscono i byte letti o scritti
    (0 a fine dati, -1 per un errore)."""


_Stream._fields_ = [("ctx", c_void),
                    ("transfer", ctypes.CFUNCTYPE(ctypes.c_int64, ctypes.POINTER(_Stream), c_void, ctypes.c_uint64))]


class _PluginState(ctypes.Structure):
    _fields_ = [("save", ctypes.CFUNCTYPE(ctypes.c_bool, c_void, ctypes.POINTER(_Stream))),
                ("load", ctypes.CFUNCTYPE(ctypes.c_bool, c_void, ctypes.POINTER(_Stream)))]


class _Window(ctypes.Structure):
    """clap_window: l'api ("x11", "win32", "cocoa") e la finestra che fa da
    genitore (id X11, HWND o NSView*: in tutti i casi sta in un puntatore)."""
    _fields_ = [("api", c_str), ("handle", c_void)]


class _PluginGui(ctypes.Structure):
    _fields_ = [("is_api_supported", ctypes.CFUNCTYPE(ctypes.c_bool, c_void, c_str, ctypes.c_bool)),
                ("get_preferred_api", ctypes.CFUNCTYPE(ctypes.c_bool, c_void, ctypes.POINTER(c_str),
                                                       ctypes.POINTER(ctypes.c_bool))),
                ("create", ctypes.CFUNCTYPE(ctypes.c_bool, c_void, c_str, ctypes.c_bool)),
                ("destroy", ctypes.CFUNCTYPE(None, c_void)),
                ("set_scale", ctypes.CFUNCTYPE(ctypes.c_bool, c_void, ctypes.c_double)),
                ("get_size", ctypes.CFUNCTYPE(ctypes.c_bool, c_void, ctypes.POINTER(u32), ctypes.POINTER(u32))),
                ("can_resize", ctypes.CFUNCTYPE(ctypes.c_bool, c_void)),
                ("get_resize_hints", ctypes.CFUNCTYPE(ctypes.c_bool, c_void, c_void)),
                ("adjust_size", ctypes.CFUNCTYPE(ctypes.c_bool, c_void, ctypes.POINTER(u32), ctypes.POINTER(u32))),
                ("set_size", ctypes.CFUNCTYPE(ctypes.c_bool, c_void, u32, u32)),
                ("set_parent", ctypes.CFUNCTYPE(ctypes.c_bool, c_void, ctypes.POINTER(_Window))),
                ("set_transient", ctypes.CFUNCTYPE(ctypes.c_bool, c_void, ctypes.POINTER(_Window))),
                ("suggest_title", ctypes.CFUNCTYPE(None, c_void, c_str)),
                ("show", ctypes.CFUNCTYPE(ctypes.c_bool, c_void)),
                ("hide", ctypes.CFUNCTYPE(ctypes.c_bool, c_void))]


class _PluginTimer(ctypes.Structure):
    _fields_ = [("on_timer", ctypes.CFUNCTYPE(None, c_void, u32))]


class _PluginPosixFd(ctypes.Structure):
    _fields_ = [("on_fd", ctypes.CFUNCTYPE(None, c_void, ctypes.c_int, u32))]


FD_READ, FD_WRITE, FD_ERROR = 1, 2, 4


# --- estensioni dell'host ----------------------------------------------------

class _HostThreadCheck(ctypes.Structure):
    _fields_ = [("is_main_thread", ctypes.CFUNCTYPE(ctypes.c_bool, c_void)),
                ("is_audio_thread", ctypes.CFUNCTYPE(ctypes.c_bool, c_void))]


class _HostLog(ctypes.Structure):
    _fields_ = [("log", ctypes.CFUNCTYPE(None, c_void, ctypes.c_int32, c_str))]


class _HostParams(ctypes.Structure):
    _fields_ = [("rescan", ctypes.CFUNCTYPE(None, c_void, u32)),
                ("clear", ctypes.CFUNCTYPE(None, c_void, u32, u32)),
                ("request_flush", ctypes.CFUNCTYPE(None, c_void))]


class _HostNotify(ctypes.Structure):      # clap.state (mark_dirty) e clap.latency (changed): una funzione senza argomenti
    _fields_ = [("notify", ctypes.CFUNCTYPE(None, c_void))]


class _HostAudioPorts(ctypes.Structure):
    _fields_ = [("is_rescan_flag_supported", ctypes.CFUNCTYPE(ctypes.c_bool, c_void, u32)),
                ("rescan", ctypes.CFUNCTYPE(None, c_void, u32))]


class _HostNotePorts(ctypes.Structure):
    _fields_ = [("supported_dialects", ctypes.CFUNCTYPE(u32, c_void)),
                ("rescan", ctypes.CFUNCTYPE(None, c_void, u32))]


class _HostGui(ctypes.Structure):
    _fields_ = [("resize_hints_changed", ctypes.CFUNCTYPE(None, c_void)),
                ("request_resize", ctypes.CFUNCTYPE(ctypes.c_bool, c_void, u32, u32)),
                ("request_show", ctypes.CFUNCTYPE(ctypes.c_bool, c_void)),
                ("request_hide", ctypes.CFUNCTYPE(ctypes.c_bool, c_void)),
                ("closed", ctypes.CFUNCTYPE(None, c_void, ctypes.c_bool))]


class _HostTimer(ctypes.Structure):
    _fields_ = [("register_timer", ctypes.CFUNCTYPE(ctypes.c_bool, c_void, u32, ctypes.POINTER(u32))),
                ("unregister_timer", ctypes.CFUNCTYPE(ctypes.c_bool, c_void, u32))]


class _HostPosixFd(ctypes.Structure):
    _fields_ = [("register_fd", ctypes.CFUNCTYPE(ctypes.c_bool, c_void, ctypes.c_int, u32)),
                ("modify_fd", ctypes.CFUNCTYPE(ctypes.c_bool, c_void, ctypes.c_int, u32)),
                ("unregister_fd", ctypes.CFUNCTYPE(ctypes.c_bool, c_void, ctypes.c_int))]


class ClapError(Exception):
    pass


def gui_api() -> Optional[bytes]:
    """L'api delle finestre di questo sistema per clap.gui, o None se non
    c'e' modo di aprirne (Linux senza X11: CLAP non ha un'api per Wayland,
    dove si passa da XWayland)."""
    if sys.platform == "win32":
        return b"win32"
    if sys.platform == "darwin":
        return b"cocoa"
    return b"x11" if os.environ.get("DISPLAY") else None


def _text(value) -> str:
    if not value:
        return ""
    return (value if isinstance(value, bytes) else bytes(value)).split(b"\0")[0].decode("utf-8", "replace")


# ---------------------------------------------------------------------------
# I file .clap
# ---------------------------------------------------------------------------

def parse_clap_ref(target: str) -> Tuple[str, str]:
    """'/percorso/Nome.clap|id' -> (percorso, id). Senza id: il primo plugin."""
    path, _, plugin_id = target.partition("|")
    return os.path.expanduser(path), plugin_id


def clap_binary(path: str) -> str:
    """Il file da caricare: su macOS un .clap e' un bundle (cartella)."""
    if os.path.isdir(path):
        folder = os.path.join(path, "Contents", "MacOS")
        try:
            names = sorted(os.listdir(folder))
        except OSError:
            names = []
        if names:
            return os.path.join(folder, names[0])
    return path


class _Library:
    """Un file .clap caricato e inizializzato (una volta sola per percorso)."""

    def __init__(self, path: str):
        self.path = path
        try:
            self.lib = ctypes.CDLL(clap_binary(path))
        except OSError as e:
            raise ClapError(tr("il file CLAP non si carica: {error}", error=str(e)))
        try:
            self.entry = _Entry.in_dll(self.lib, "clap_entry")
        except ValueError:
            raise ClapError(tr("non e' un plugin CLAP (manca clap_entry)"))
        if not self.entry.init(os.fsencode(path)):
            raise ClapError(tr("il plugin CLAP rifiuta di inizializzarsi"))
        factory = self.entry.get_factory(b"clap.plugin-factory")
        if not factory:
            raise ClapError(tr("il file CLAP non contiene plugin"))
        self.factory_ptr = factory
        self.factory = ctypes.cast(factory, ctypes.POINTER(_Factory)).contents

    def descriptors(self) -> List[_Descriptor]:
        out = []
        for i in range(self.factory.get_plugin_count(self.factory_ptr)):
            desc = self.factory.get_plugin_descriptor(self.factory_ptr, i)
            if desc:
                out.append(desc.contents)
        return out


_libraries: Dict[str, _Library] = {}


def _library(path: str) -> _Library:
    key = os.path.realpath(path)
    if key not in _libraries:
        _libraries[key] = _Library(path)
    return _libraries[key]


@dataclass
class ClapParam:
    id: int
    name: str
    minimum: float
    maximum: float
    default: float
    toggled: bool = False
    integer: bool = False
    choices: List[Tuple[float, str]] = field(default_factory=list)

    @property
    def key(self) -> str:
        return str(self.id)


@dataclass
class ClapPluginInfo:
    path: str
    id: str
    name: str
    vendor: str
    category: str
    instrument: bool
    problem: str = ""

    @property
    def ref(self) -> str:
        return f"clap:{self.path}|{self.id}"


def _features(desc: _Descriptor) -> List[str]:
    out, i = [], 0
    while desc.features and desc.features[i]:
        out.append(_text(desc.features[i]))
        i += 1
    return out


_CATEGORY_FEATURES = ("instrument", "audio-effect", "note-effect", "note-detector", "analyzer")


def _info(path: str, desc: _Descriptor) -> ClapPluginInfo:
    features = _features(desc)
    instrument = "instrument" in features
    details = [f for f in features if f not in _CATEGORY_FEATURES and f not in ("stereo", "mono", "surround", "ambisonic")]
    problem = ""
    if not instrument and "audio-effect" not in features:
        problem = tr("non e' un effetto audio ne' uno strumento")
    return ClapPluginInfo(path=path, id=_text(desc.id), name=_text(desc.name) or _text(desc.id),
                          vendor=_text(desc.vendor), category=", ".join(details[:2]).title(),
                          instrument=instrument, problem=problem)


def list_clap_plugins(path: str) -> List[ClapPluginInfo]:
    """I plugin di un file .clap, senza crearne nessuno."""
    return [_info(path, d) for d in _library(path).descriptors()]


def default_clap_dirs() -> List[str]:
    if sys.platform == "win32":
        base = os.environ.get("COMMONPROGRAMFILES", r"C:\Program Files\Common Files")
        dirs = [os.path.join(base, "CLAP"),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Common", "CLAP")]
    elif sys.platform == "darwin":
        dirs = ["/Library/Audio/Plug-Ins/CLAP", os.path.expanduser("~/Library/Audio/Plug-Ins/CLAP")]
    else:
        dirs = [os.path.expanduser("~/.clap"), "/usr/lib/clap", "/usr/local/lib/clap",
                "/usr/lib/x86_64-linux-gnu/clap", "/usr/lib64/clap"]
    dirs += [d for d in os.environ.get("CLAP_PATH", "").split(os.pathsep) if d]
    return dirs


def find_clap_files(dirs: List[str]) -> List[str]:
    """I file (o bundle) .clap nelle cartelle date, sottocartelle comprese."""
    found, seen = [], set()
    for base in dirs:
        if not os.path.isdir(base):
            continue
        for root, folders, files in os.walk(base):
            for name in sorted(folders + files):
                if name.lower().endswith(".clap"):
                    path = os.path.join(root, name)
                    real = os.path.realpath(path)
                    if real not in seen:
                        seen.add(real)
                        found.append(path)
            folders[:] = [f for f in folders if not f.lower().endswith(".clap")]
    return found


# ---------------------------------------------------------------------------
# Un plugin in funzione
# ---------------------------------------------------------------------------

class _Port:
    """Una porta audio: i buffer dei canali e la struttura che li indica."""

    def __init__(self, channels: int):
        self.channels = max(1, int(channels))
        self.data = np.zeros((self.channels, BLOCK), dtype=np.float32)
        self.pointers = (ctypes.POINTER(ctypes.c_float) * self.channels)(
            *[self.data[c].ctypes.data_as(ctypes.POINTER(ctypes.c_float)) for c in range(self.channels)])


class ClapInstance:
    """Un plugin CLAP attivo a 'samplerate'. Stessa forma di
    core.lv2_host.LV2Instance: process(), render(), reset(), close()."""

    def __init__(self, target: str, samplerate: int):
        self.samplerate = int(samplerate)
        self._plugin = None
        self._active = False
        self._pending_values: Dict[int, float] = {}
        self._values: Dict[str, float] = {}
        self._baseline: Dict[str, float] = {}  # valori dello stato caricato (load_state), al posto dei predefiniti
        self._touched = False                  # un valore diverso dal predefinito e' stato mandato
        self._needs_main_thread = False
        self._timers: Dict[int, List[float]] = {}   # id -> [periodo in secondi, prossima scadenza]
        self._next_timer = 1
        self.fds: Dict[int, int] = {}          # descrittore -> FD_READ | FD_WRITE | FD_ERROR
        self.fds_version = 0                   # cambia a ogni modifica di fds
        self._gui = None                       # clap.gui del plugin, mentre l'interfaccia e' aperta
        self.gui_listener = None               # chi tiene la finestra: request_resize(w, h), closed()
        self._keep = []                        # callback e strutture che il plugin puo' richiamare
        path, plugin_id = parse_clap_ref(target)
        if not os.path.exists(path):
            raise ClapError(tr("plugin non trovato: {path}", path=path))
        self._library = _library(path)
        descriptors = self._library.descriptors()
        chosen = next((d for d in descriptors if _text(d.id) == plugin_id), None) if plugin_id else \
            (descriptors[0] if descriptors else None)
        if chosen is None:
            raise ClapError(tr("plugin CLAP non trovato nel file: {id}", id=plugin_id or path))
        self.info = _info(path, chosen)
        self._build_host()
        pointer = self._library.factory.create_plugin(self._library.factory_ptr, ctypes.byref(self._host),
                                                      chosen.id)
        if not pointer:
            raise ClapError(tr("il plugin CLAP non si crea"))
        self._pointer = pointer
        self._plugin = ctypes.cast(pointer, ctypes.POINTER(_Plugin)).contents
        if not self._plugin.init(pointer):
            self._plugin.destroy(pointer)
            self._plugin = None
            raise ClapError(tr("il plugin CLAP rifiuta di inizializzarsi"))
        self._read_ports()
        self.params = self._read_params()
        self._activate()

    # -- l'host visto dal plugin ---------------------------------------------
    def _build_host(self):
        log = logging.getLogger(__name__)
        yes = _HostThreadCheck._fields_[0][1](lambda _h: True)

        def log_message(_host, severity, message):
            log.log(logging.DEBUG if severity < 2 else logging.INFO, "CLAP %s: %s", self.info.name, _text(message))

        def nothing(*_args):
            return None

        def request_callback(_host):
            self._needs_main_thread = True

        thread_check = _HostThreadCheck(yes, yes)
        host_log = _HostLog(_HostLog._fields_[0][1](log_message))
        host_params = _HostParams(_HostParams._fields_[0][1](nothing), _HostParams._fields_[1][1](nothing),
                                  _HostParams._fields_[2][1](nothing))
        notify = _HostNotify(_HostNotify._fields_[0][1](nothing))
        audio_ports = _HostAudioPorts(_HostAudioPorts._fields_[0][1](lambda _h, _f: False),
                                      _HostAudioPorts._fields_[1][1](nothing))
        note_ports = _HostNotePorts(_HostNotePorts._fields_[0][1](lambda _h: _DIALECT_CLAP | _DIALECT_MIDI),
                                    _HostNotePorts._fields_[1][1](nothing))

        def register_timer(_host, period_ms, timer_id):
            period = max(1, int(period_ms)) / 1000.0
            self._timers[self._next_timer] = [period, time.monotonic() + period]
            timer_id[0] = self._next_timer
            self._next_timer += 1
            return True

        def unregister_timer(_host, timer_id):
            return self._timers.pop(int(timer_id), None) is not None

        def set_fd(_host, fd, flags):
            self.fds[int(fd)] = int(flags)
            self.fds_version += 1
            return True

        def modify_fd(_host, fd, flags):
            if int(fd) not in self.fds:
                return False
            return set_fd(_host, fd, flags)

        def unregister_fd(_host, fd):
            self.fds_version += 1
            return self.fds.pop(int(fd), None) is not None

        def request_resize(_host, width, height):
            listener = self.gui_listener
            return bool(listener is not None and listener.request_resize(int(width), int(height)))

        def gui_closed(_host, _was_destroyed):
            if self.gui_listener is not None:
                self.gui_listener.closed()

        gui_open = lambda _h: self._gui is not None     # noqa: E731
        fields = _HostGui._fields_
        host_gui = _HostGui(fields[0][1](nothing), fields[1][1](request_resize), fields[2][1](gui_open),
                            fields[3][1](gui_open), fields[4][1](gui_closed))
        host_timer = _HostTimer(_HostTimer._fields_[0][1](register_timer),
                                _HostTimer._fields_[1][1](unregister_timer))
        host_fd = _HostPosixFd(_HostPosixFd._fields_[0][1](set_fd), _HostPosixFd._fields_[1][1](modify_fd),
                               _HostPosixFd._fields_[2][1](unregister_fd))
        extensions = {b"clap.thread-check": thread_check, b"clap.log": host_log, b"clap.params": host_params,
                      b"clap.state": notify, b"clap.latency": notify, b"clap.audio-ports": audio_ports,
                      b"clap.note-ports": note_ports, b"clap.gui": host_gui, b"clap.timer-support": host_timer}
        if sys.platform != "win32":
            extensions[b"clap.posix-fd-support"] = host_fd

        def get_extension(_host, name):
            ext = extensions.get(name)
            return ctypes.addressof(ext) if ext is not None else None

        callbacks = (_Host._fields_[6][1](get_extension), _Host._fields_[7][1](nothing),
                     _Host._fields_[8][1](nothing), _Host._fields_[9][1](request_callback))
        self._host = _Host(_Version(*_HOST_VERSION), None, b"SoundText", b"openssound",
                           b"https://github.com/openssound/soundtext", b"1", *callbacks)
        self._keep += [extensions, callbacks, yes]

    def _extension(self, name: bytes, struct):
        pointer = self._plugin.get_extension(self._pointer, name)
        return ctypes.cast(pointer, ctypes.POINTER(struct)).contents if pointer else None

    # -- porte e parametri -----------------------------------------------------
    def _read_ports(self):
        ports = self._extension(b"clap.audio-ports", _PluginAudioPorts)
        self._in_ports: List[_Port] = []
        self._out_ports: List[_Port] = []
        if ports is not None:
            for is_input, target in ((True, self._in_ports), (False, self._out_ports)):
                for i in range(ports.count(self._pointer, is_input)):
                    info = _AudioPortInfo()
                    if ports.get(self._pointer, i, is_input, ctypes.byref(info)):
                        target.append(_Port(info.channel_count))
        self._in_buffers = (_AudioBuffer * max(1, len(self._in_ports)))()
        self._out_buffers = (_AudioBuffer * max(1, len(self._out_ports)))()
        for buffers, group in ((self._in_buffers, self._in_ports), (self._out_buffers, self._out_ports)):
            for buffer, port in zip(buffers, group):
                buffer.data32 = ctypes.cast(port.pointers, ctypes.POINTER(ctypes.POINTER(ctypes.c_float)))
                buffer.channel_count = port.channels
        self._midi_dialect = None
        notes = self._extension(b"clap.note-ports", _PluginNotePorts)
        if notes is not None and notes.count(self._pointer, True) > 0:
            info = _NotePortInfo()
            if notes.get(self._pointer, 0, True, ctypes.byref(info)):
                self._midi_dialect = _DIALECT_MIDI if info.supported_dialects & _DIALECT_MIDI else _DIALECT_CLAP

    def _read_params(self) -> List[ClapParam]:
        self._params_ext = self._extension(b"clap.params", _PluginParams)
        out = []
        modules: Dict[int, str] = {}
        if self._params_ext is None:
            return out
        ext = self._params_ext
        for i in range(ext.count(self._pointer)):
            info = _ParamInfo()
            if not ext.get_info(self._pointer, i, ctypes.byref(info)):
                continue
            if info.flags & (_PARAM_IS_HIDDEN | _PARAM_IS_READONLY | _PARAM_IS_BYPASS):
                continue
            low, high = float(info.min_value), float(info.max_value)
            if not high > low:
                continue
            stepped = bool(info.flags & _PARAM_IS_STEPPED)
            choices = []
            if stepped and info.flags & _PARAM_IS_ENUM and high - low <= 64:
                text = ctypes.create_string_buffer(256)
                for step in range(int(round(low)), int(round(high)) + 1):
                    if ext.value_to_text(self._pointer, info.id, float(step), text, 256):
                        choices.append((float(step), _text(text.value)))
            name = _text(info.name)
            modules[int(info.id)] = _text(info.module).strip("/").split("/")[-1]
            out.append(ClapParam(id=int(info.id), name=name,
                                 minimum=low, maximum=high,
                                 default=min(high, max(low, float(info.default_value))),
                                 toggled=stepped and low == 0.0 and high == 1.0 and not choices,
                                 integer=stepped, choices=choices))
        # il gruppo ("Osc 1: Pitch") solo dove serve a distinguere due nomi uguali
        counts: Dict[str, int] = {}
        for p in out:
            counts[p.name] = counts.get(p.name, 0) + 1
        for p in out:
            if counts[p.name] > 1 and modules.get(p.id):
                p.name = f"{modules[p.id]}: {p.name}"
        return out

    # -- vita del plugin -------------------------------------------------------
    def _activate(self):
        if not self._plugin.activate(self._pointer, float(self.samplerate), 1, BLOCK):
            raise ClapError(tr("il plugin CLAP non si attiva"))
        self._active = True
        self._plugin.start_processing(self._pointer)
        latency = self._extension(b"clap.latency", _PluginLatency)
        self.latency = int(latency.get(self._pointer)) if latency is not None else 0
        self._steady = 0

    def _deactivate(self):
        if self._active:
            self._plugin.stop_processing(self._pointer)
            self._plugin.deactivate(self._pointer)
            self._active = False

    def reset(self):
        """Stato di elaborazione da capo (code dei riverberi, voci, filtri):
        il plugin si disattiva e si riattiva. Il solo reset() di CLAP non
        basta a tutti (ZamVerb teneva la coda del riverbero, e lo stesso
        audio usciva diverso da una volta all'altra)."""
        if self._active:
            self._plugin.reset(self._pointer)
            self._deactivate()
            self._activate()
            # i valori vanno ridetti tutti: riattivato, il plugin tiene quelli
            # di prima, anche quando nel frattempo sono tornati al predefinito
            if self._touched:
                self._pending_values = {p.id: self._values.get(p.key, self._start_value(p)) for p in self.params}

    def close(self):
        if self._plugin is not None:
            try:
                self.close_gui()
                self._deactivate()
                self._plugin.destroy(self._pointer)
            finally:
                self._plugin = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    # -- stato -----------------------------------------------------------------
    def save_state(self) -> bytes:
        """Lo stato interno del plugin (clap.state), b"" se non ne ha."""
        ext = self._extension(b"clap.state", _PluginState)
        if ext is None:
            return b""
        chunks = []

        def write(_stream, buffer, size):
            chunks.append(ctypes.string_at(buffer, size))
            return size

        stream = _Stream(None, _Stream._fields_[1][1](write))
        if not ext.save(self._pointer, ctypes.byref(stream)):
            raise ClapError(tr("il plugin CLAP non salva il suo stato"))
        return b"".join(chunks)

    def load_state(self, data: bytes):
        """Rimette lo stato salvato da save_state. I valori dei parametri che
        ne risultano diventano quelli di partenza: set_values riporta li' (e
        non al predefinito) i parametri che non nomina."""
        ext = self._extension(b"clap.state", _PluginState)
        if ext is None:
            raise ClapError(tr("il plugin CLAP non ha uno stato da caricare"))
        data = bytes(data)
        position = [0]

        def read(_stream, buffer, size):
            chunk = data[position[0]:position[0] + size]
            ctypes.memmove(buffer, chunk, len(chunk))
            position[0] += len(chunk)
            return len(chunk)

        stream = _Stream(None, _Stream._fields_[1][1](read))
        if not ext.load(self._pointer, ctypes.byref(stream)):
            raise ClapError(tr("il plugin CLAP rifiuta lo stato salvato"))
        self._pending_values = {}
        if self._active:
            # alcuni plugin (Surge XT) applicano lo stato al blocco audio che
            # segue: prima di rileggere i valori se ne elabora uno di silenzio
            self._feed(None, BLOCK)
            self._run(BLOCK, [])
        self._baseline = self.read_values()
        self._values = dict(self._baseline)

    def _start_value(self, param: "ClapParam") -> float:
        return self._baseline.get(param.key, param.default)

    # -- parametri -------------------------------------------------------------
    def set_values(self, values: Dict[str, float]):
        """Valori dei parametri (chiave = id del parametro): arrivano al
        plugin come eventi all'inizio del prossimo blocco. Quelli non
        nominati tornano al valore predefinito (o a quello dello stato
        caricato con load_state)."""
        known = {p.key: p for p in self.params}
        wanted = {key: self._start_value(p) for key, p in known.items()}
        for key, value in (values or {}).items():
            if str(key) in known:
                p = known[str(key)]
                wanted[str(key)] = min(p.maximum, max(p.minimum, float(value)))
        for key, value in wanted.items():
            if self._values.get(key, self._start_value(known[key])) != value:
                self._pending_values[known[key].id] = value
                self._touched = True
        self._values = wanted

    # -- elaborazione ----------------------------------------------------------
    def _events(self, midi: List[Tuple[int, bytes]]):
        """La lista degli eventi di un blocco: prima i parametri (al frame
        0), poi le note in ordine di tempo."""
        events = []
        for param_id, value in self._pending_values.items():
            event = _ParamValueEvent()
            event.header = _EventHeader(ctypes.sizeof(_ParamValueEvent), 0, 0, _EVENT_PARAM_VALUE, 0)
            event.param_id, event.note_id, event.port_index, event.channel, event.key = param_id, -1, -1, -1, -1
            event.value = value
            events.append(event)
        self._pending_values = {}
        for time, data in sorted(midi, key=lambda e: e[0]):
            if self._midi_dialect is None or not data:
                continue
            status = data[0] & 0xF0
            if self._midi_dialect == _DIALECT_MIDI:
                event = _MidiEvent()
                event.header = _EventHeader(ctypes.sizeof(_MidiEvent), int(time), 0, _EVENT_MIDI, 0)
                event.port_index = 0
                for i in range(3):
                    event.data[i] = data[i] if i < len(data) else 0
                events.append(event)
            elif status in (0x80, 0x90) and len(data) >= 3:
                on = status == 0x90 and data[2] > 0
                event = _NoteEvent()
                event.header = _EventHeader(ctypes.sizeof(_NoteEvent), int(time), 0,
                                            _EVENT_NOTE_ON if on else _EVENT_NOTE_OFF, 0)
                event.note_id, event.port_index, event.channel, event.key = -1, 0, data[0] & 0x0F, data[1]
                event.velocity = data[2] / 127.0
                events.append(event)
        return events

    def _run(self, frames: int, midi: List[Tuple[int, bytes]]):
        events = self._events(midi)
        size = _InputEvents._fields_[1][1](lambda _ctx: len(events))
        get = _InputEvents._fields_[2][1](lambda _ctx, i: ctypes.addressof(events[i]) if i < len(events) else None)
        push = _OutputEvents._fields_[1][1](lambda _ctx, _event: True)
        in_events, out_events = _InputEvents(None, size, get), _OutputEvents(None, push)
        for port in self._out_ports:
            port.data[:, :frames] = 0
        process = _Process()
        process.steady_time = self._steady
        process.frames_count = frames
        process.transport = None
        process.audio_inputs = self._in_buffers if self._in_ports else None
        process.audio_outputs = self._out_buffers if self._out_ports else None
        process.audio_inputs_count = len(self._in_ports)
        process.audio_outputs_count = len(self._out_ports)
        process.in_events = ctypes.pointer(in_events)
        process.out_events = ctypes.pointer(out_events)
        status = self._plugin.process(self._pointer, ctypes.byref(process))
        self._steady += frames
        if status == 0:
            raise ClapError(tr("il plugin CLAP ha dato un errore durante l'elaborazione"))
        self.idle()

    def idle(self):
        """Quello che il plugin chiede al thread principale: la chiamata che
        ha prenotato (request_callback) e i timer scaduti. La chiama ogni
        blocco di audio e, a interfaccia aperta, chi tiene la finestra."""
        if self._needs_main_thread:
            self._needs_main_thread = False
            self._plugin.on_main_thread(self._pointer)
        if self._timers:
            ext = self._extension(b"clap.timer-support", _PluginTimer)
            now = time.monotonic()
            for timer_id, timer in list(self._timers.items()):
                if timer[1] <= now and timer_id in self._timers:
                    timer[1] = now + timer[0]
                    if ext is not None:
                        ext.on_timer(self._pointer, timer_id)

    def fd_event(self, fd: int, flags: int):
        """Il descrittore fd (vedi fds) e' pronto: lo si dice al plugin."""
        ext = self._extension(b"clap.posix-fd-support", _PluginPosixFd)
        if ext is not None and fd in self.fds:
            ext.on_fd(self._pointer, int(fd), int(flags))

    # -- interfaccia grafica ---------------------------------------------------
    def has_gui(self) -> bool:
        """Il plugin ha un'interfaccia che si puo' aprire dentro una nostra finestra."""
        api = gui_api()
        ext = self._extension(b"clap.gui", _PluginGui)
        return bool(api and ext is not None and ext.is_api_supported(self._pointer, api, False))

    def gui_size(self) -> Tuple[int, int]:
        width, height = u32(0), u32(0)
        if self._gui is None or not self._gui.get_size(self._pointer, ctypes.byref(width), ctypes.byref(height)):
            return 0, 0
        return int(width.value), int(height.value)

    def gui_resizable(self) -> bool:
        return bool(self._gui is not None and self._gui.can_resize(self._pointer))

    def gui_resize(self, width: int, height: int) -> Tuple[int, int]:
        """Chiede al plugin di disegnarsi in width x height (pixel): torna
        la misura che ha accettato."""
        if self._gui is None:
            return 0, 0
        w, h = u32(max(1, int(width))), u32(max(1, int(height)))
        self._gui.adjust_size(self._pointer, ctypes.byref(w), ctypes.byref(h))
        self._gui.set_size(self._pointer, w.value, h.value)
        return int(w.value), int(h.value)

    def open_gui(self, parent: int, scale: float, listener) -> Tuple[int, int]:
        """Crea l'interfaccia del plugin dentro la finestra 'parent' (id X11,
        HWND o NSView*) e la mostra: torna la sua misura in pixel. 'scale'
        e' il fattore dello schermo (non su macOS, dove le misure sono gia'
        logiche); 'listener' riceve request_resize(w, h) e closed()."""
        api = gui_api()
        ext = self._extension(b"clap.gui", _PluginGui)
        if not api or ext is None or not ext.is_api_supported(self._pointer, api, False):
            raise ClapError(tr("questo plugin CLAP non ha un'interfaccia che si possa aprire qui"))
        if self._gui is not None:
            raise ClapError(tr("l'interfaccia del plugin e' gia' aperta"))
        if not ext.create(self._pointer, api, False):
            raise ClapError(tr("il plugin CLAP non crea la sua interfaccia"))
        self._gui, self.gui_listener = ext, listener
        if api != b"cocoa":
            ext.set_scale(self._pointer, float(scale))
        window = _Window(api, parent)
        self._keep.append(window)
        if not ext.set_parent(self._pointer, ctypes.byref(window)):
            self.close_gui()
            raise ClapError(tr("il plugin CLAP non entra nella finestra"))
        ext.show(self._pointer)
        return self.gui_size()

    def close_gui(self):
        if self._gui is not None:
            ext, self._gui, self.gui_listener = self._gui, None, None
            ext.hide(self._pointer)
            ext.destroy(self._pointer)

    def read_values(self) -> Dict[str, float]:
        """I valori che i parametri hanno adesso nel plugin."""
        out: Dict[str, float] = {}
        if self._params_ext is not None:
            value = ctypes.c_double()
            for p in self.params:
                if self._params_ext.get_value(self._pointer, p.id, ctypes.byref(value)):
                    out[p.key] = min(p.maximum, max(p.minimum, float(value.value)))
        return out

    def adopt_values(self, as_baseline: bool) -> Dict[str, float]:
        """Dopo che il plugin ha cambiato i suoi valori da solo (dalla sua
        interfaccia): li si rilegge e diventano quelli che l'host sa di aver
        impostato; con as_baseline anche quelli di partenza, come dopo
        load_state (lo stato appena salvato li contiene)."""
        values = self.read_values()
        self._values = dict(values)
        self._pending_values = {}
        if as_baseline:
            self._baseline = dict(values)
        return values

    def _output(self, frames: int) -> np.ndarray:
        out = np.zeros((frames, 2), dtype=np.float32)
        if self._out_ports:
            data = self._out_ports[0].data
            out[:, 0] = data[0, :frames]
            out[:, 1] = data[1 if len(data) > 1 else 0, :frames]
        return out

    def _feed(self, block: Optional[np.ndarray], frames: int):
        for index, port in enumerate(self._in_ports):
            if index == 0 and block is not None:
                if port.channels >= 2:
                    port.data[0, :frames], port.data[1, :frames] = block[:, 0], block[:, 1]
                    port.data[2:, :frames] = 0
                else:
                    port.data[0, :frames] = block.mean(axis=1)
            else:
                port.data[:, :frames] = 0          # ingressi in piu' (sidechain): silenzio

    def process(self, samples: np.ndarray) -> np.ndarray:
        """Effetto: samples float32 (frame, 2) -> (frame, 2), compensata la
        latenza che il plugin dichiara."""
        n = len(samples)
        total = n + self.latency
        padded = np.zeros((total, 2), dtype=np.float32)
        padded[:n] = samples
        out = np.zeros((total, 2), dtype=np.float32)
        for start in range(0, total, BLOCK):
            frames = min(BLOCK, total - start)
            self._feed(padded[start:start + frames], frames)
            self._run(frames, [])
            out[start:start + frames] = self._output(frames)
        if not np.isfinite(out).all():
            raise ClapError(tr("il plugin CLAP ha prodotto valori non validi (NaN)"))
        return out[self.latency:]

    def render(self, events: List[Tuple[float, bytes]], seconds: float) -> np.ndarray:
        """Strumento: eventi (secondi, byte MIDI) ordinati -> (frame, 2)."""
        n = int(round(seconds * self.samplerate))
        out = np.zeros((n, 2), dtype=np.float32)
        pending = sorted(((int(round(t * self.samplerate)), bytes(data)) for t, data in events),
                         key=lambda e: e[0])
        i = 0
        for start in range(0, n, BLOCK):
            frames = min(BLOCK, n - start)
            block_events = []
            while i < len(pending) and pending[i][0] < start + frames:
                block_events.append((max(0, pending[i][0] - start), pending[i][1]))
                i += 1
            self._feed(None, frames)
            self._run(frames, block_events)
            out[start:start + frames] = self._output(frames)
        return out
