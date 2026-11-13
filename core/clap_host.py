"""
Host CLAP minimo per l'elaborazione offline e l'ascolto dal vivo. CLAP
(https://github.com/free-audio/clap) ha un'interfaccia binaria in C puro:
il file .clap e' una libreria che esporta 'clap_entry', e tutto passa da
strutture di puntatori a funzione, chiamate qui con ctypes senza librerie
in mezzo.

Supporta cio' che serve a un effetto o a uno strumento senza la sua
finestra grafica: porte audio (la principale in ingresso e in uscita; le
altre ricevono silenzio), note in MIDI o come eventi CLAP, i parametri
(clap.params, impostati con eventi PARAM_VALUE) e la latenza dichiarata
dal plugin (clap.latency), che si compensa. L'interfaccia grafica del
plugin (clap.gui) e lo stato (clap.state) non sono gestiti: del plugin si
salvano i valori dei parametri.

Un riferimento e' 'clap:/percorso/Nome.clap|id.del.plugin': un file .clap
puo' contenere molti plugin (LSP ne ha centinaia), distinti dall'id.
"""

import ctypes
import logging
import os
import sys
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


class ClapError(Exception):
    pass


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
        self._touched = False                  # un valore diverso dal predefinito e' stato mandato
        self._needs_main_thread = False
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
        extensions = {b"clap.thread-check": thread_check, b"clap.log": host_log, b"clap.params": host_params,
                      b"clap.state": notify, b"clap.latency": notify, b"clap.audio-ports": audio_ports,
                      b"clap.note-ports": note_ports}

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
                self._pending_values = {p.id: self._values.get(p.key, p.default) for p in self.params}

    def close(self):
        if self._plugin is not None:
            try:
                self._deactivate()
                self._plugin.destroy(self._pointer)
            finally:
                self._plugin = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    # -- parametri -------------------------------------------------------------
    def set_values(self, values: Dict[str, float]):
        """Valori dei parametri (chiave = id del parametro): arrivano al
        plugin come eventi all'inizio del prossimo blocco. Quelli non
        nominati tornano al valore predefinito."""
        known = {p.key: p for p in self.params}
        wanted = {key: p.default for key, p in known.items()}
        for key, value in (values or {}).items():
            if str(key) in known:
                p = known[str(key)]
                wanted[str(key)] = min(p.maximum, max(p.minimum, float(value)))
        for key, value in wanted.items():
            if self._values.get(key, known[key].default) != value:
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
        if self._needs_main_thread:
            self._needs_main_thread = False
            self._plugin.on_main_thread(self._pointer)

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
