"""
Host LV2 minimo per l'elaborazione offline, sulla libreria di sistema lilv
(liblilv-0, pacchetto di Debian/Ubuntu 'liblilv-0-0', gia' presente con
Ardour, Carla, Guitarix...). Niente binding Python: lilv si chiama con
ctypes, e le funzioni "inline" del suo header (connect_port, run...)
passano direttamente dal descrittore LV2 del plugin.

Supporta cio' che serve a un plugin di effetti o a uno strumento senza
interfaccia grafica: porte audio, di controllo, CV (collegate a silenzio)
e atom (sequenza MIDI in ingresso per gli strumenti), con le estensioni
urid:map/unmap, options, buf-size e worker (eseguito nello stesso thread
appena finisce il run() che l'ha chiesto: va bene per il rendering offline). Lo stato LV2 (state:interface)
non e' gestito: del plugin si salvano i valori delle porte di controllo e
i file scelti per le sue proprieta' di tipo file (patch:writable con
rdfs:range atom:Path, per esempio il file SFZ di sfizz), che gli arrivano
come messaggio patch:Set.

Solo Linux (e altri sistemi con lilv installato): senza la libreria
lv2_available() e' False e i plugin LV2 semplicemente non compaiono.
"""

import base64
import ctypes
import ctypes.util
import json
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
from struct import pack as struct_pack
from .i18n import tr

LV2_CORE = "http://lv2plug.in/ns/lv2core#"
_URI = {
    "audio": LV2_CORE + "AudioPort", "control": LV2_CORE + "ControlPort", "cv": LV2_CORE + "CVPort",
    "input": LV2_CORE + "InputPort", "output": LV2_CORE + "OutputPort",
    "atom": "http://lv2plug.in/ns/ext/atom#AtomPort",
    "toggled": LV2_CORE + "toggled", "integer": LV2_CORE + "integer",
    "enumeration": LV2_CORE + "enumeration", "logarithmic": "http://lv2plug.in/ns/ext/port-props#logarithmic",
    "not_on_gui": "http://lv2plug.in/ns/ext/port-props#notOnGUI",
    "instrument": LV2_CORE + "InstrumentPlugin",
    "midi_event": "http://lv2plug.in/ns/ext/midi#MidiEvent",
    "supports": "http://lv2plug.in/ns/ext/atom#supports",
    "patch_writable": "http://lv2plug.in/ns/ext/patch#writable",
    "patch_message": "http://lv2plug.in/ns/ext/patch#Message",
    "range": "http://www.w3.org/2000/01/rdf-schema#range",
    "label": "http://www.w3.org/2000/01/rdf-schema#label",
    "atom_path": "http://lv2plug.in/ns/ext/atom#Path",
}
_ATOM_SEQUENCE = "http://lv2plug.in/ns/ext/atom#Sequence"
_ATOM_CHUNK = "http://lv2plug.in/ns/ext/atom#Chunk"
_ATOM_INT = "http://lv2plug.in/ns/ext/atom#Int"
_ATOM_FLOAT = "http://lv2plug.in/ns/ext/atom#Float"
_ATOM_OBJECT = "http://lv2plug.in/ns/ext/atom#Object"
_ATOM_URID = "http://lv2plug.in/ns/ext/atom#URID"
_PATCH_SET = "http://lv2plug.in/ns/ext/patch#Set"
_PATCH_PROPERTY = "http://lv2plug.in/ns/ext/patch#property"
_PATCH_VALUE = "http://lv2plug.in/ns/ext/patch#value"
_URID_MAP = "http://lv2plug.in/ns/ext/urid#map"
_URID_UNMAP = "http://lv2plug.in/ns/ext/urid#unmap"
_OPTIONS = "http://lv2plug.in/ns/ext/options#options"
_BOUNDED = "http://lv2plug.in/ns/ext/buf-size#boundedBlockLength"
_WORKER_SCHEDULE = "http://lv2plug.in/ns/ext/worker#schedule"
_WORKER_INTERFACE = "http://lv2plug.in/ns/ext/worker#interface"
_MAX_BLOCK = "http://lv2plug.in/ns/ext/buf-size#maxBlockLength"
_MIN_BLOCK = "http://lv2plug.in/ns/ext/buf-size#minBlockLength"
_NOMINAL_BLOCK = "http://lv2plug.in/ns/ext/buf-size#nominalBlockLength"
_SAMPLE_RATE = "http://lv2plug.in/ns/ext/parameters#sampleRate"

BLOCK = 512
ATOM_CAPACITY = 65536


# ---------------------------------------------------------------------------
# lilv via ctypes
# ---------------------------------------------------------------------------

_lib = None
_lib_lock = threading.Lock()


def _load_library():
    global _lib
    with _lib_lock:
        if _lib is not None:
            return _lib or None
        name = ctypes.util.find_library("lilv-0") or "liblilv-0.so.0"
        try:
            lib = ctypes.CDLL(name)
        except OSError:
            _lib = False
            return None
        vp, cp, u32, f = ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32, ctypes.c_float
        sigs = {
            "lilv_world_new": ([], vp), "lilv_world_load_all": ([vp], None),
            "lilv_world_get_all_plugins": ([vp], vp),
            "lilv_plugins_begin": ([vp], vp), "lilv_plugins_is_end": ([vp, vp], ctypes.c_bool),
            "lilv_plugins_get": ([vp, vp], vp), "lilv_plugins_next": ([vp, vp], vp),
            "lilv_plugins_get_by_uri": ([vp, vp], vp),
            "lilv_new_uri": ([vp, cp], vp), "lilv_node_free": ([vp], None),
            "lilv_node_as_string": ([vp], cp), "lilv_node_as_float": ([vp], f),
            "lilv_plugin_get_uri": ([vp], vp), "lilv_plugin_get_name": ([vp], vp),
            "lilv_plugin_get_author_name": ([vp], vp),
            "lilv_plugin_get_class": ([vp], vp), "lilv_plugin_class_get_label": ([vp], vp),
            "lilv_plugin_class_get_uri": ([vp], vp),
            "lilv_plugin_get_num_ports": ([vp], u32), "lilv_plugin_get_port_by_index": ([vp, u32], vp),
            "lilv_plugin_get_port_ranges_float": ([vp, vp, vp, vp], None),
            "lilv_plugin_get_required_features": ([vp], vp),
            "lilv_plugin_get_value": ([vp, vp], vp),
            "lilv_world_ask": ([vp, vp, vp, vp], ctypes.c_bool),
            "lilv_world_get": ([vp, vp, vp, vp], vp),
            "lilv_nodes_begin": ([vp], vp), "lilv_nodes_is_end": ([vp, vp], ctypes.c_bool),
            "lilv_nodes_get": ([vp, vp], vp), "lilv_nodes_next": ([vp, vp], vp),
            "lilv_nodes_free": ([vp], None),
            "lilv_port_is_a": ([vp, vp, vp], ctypes.c_bool),
            "lilv_port_has_property": ([vp, vp, vp], ctypes.c_bool),
            "lilv_port_supports_event": ([vp, vp, vp], ctypes.c_bool),
            "lilv_port_get_symbol": ([vp, vp], vp), "lilv_port_get_name": ([vp, vp], vp),
            "lilv_port_get_scale_points": ([vp, vp], vp),
            "lilv_scale_points_begin": ([vp], vp), "lilv_scale_points_is_end": ([vp, vp], ctypes.c_bool),
            "lilv_scale_points_get": ([vp, vp], vp), "lilv_scale_points_next": ([vp, vp], vp),
            "lilv_scale_points_free": ([vp], None),
            "lilv_scale_point_get_label": ([vp], vp), "lilv_scale_point_get_value": ([vp], vp),
            "lilv_plugin_instantiate": ([vp, ctypes.c_double, vp], vp),
            "lilv_instance_free": ([vp], None),
        }
        for fname, (args, res) in sigs.items():
            fn = getattr(lib, fname)
            fn.argtypes = args
            fn.restype = res
        _lib = lib
        return lib


def lv2_available() -> bool:
    return _load_library() is not None


class _LV2Descriptor(ctypes.Structure):
    pass


_HANDLE = ctypes.c_void_p
_LV2Descriptor._fields_ = [
    ("URI", ctypes.c_char_p),
    ("instantiate", ctypes.c_void_p),
    ("connect_port", ctypes.CFUNCTYPE(None, _HANDLE, ctypes.c_uint32, ctypes.c_void_p)),
    ("activate", ctypes.CFUNCTYPE(None, _HANDLE)),
    ("run", ctypes.CFUNCTYPE(None, _HANDLE, ctypes.c_uint32)),
    ("deactivate", ctypes.CFUNCTYPE(None, _HANDLE)),
    ("cleanup", ctypes.c_void_p),
    ("extension_data", ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_char_p)),
]


class _LilvInstance(ctypes.Structure):
    _fields_ = [("lv2_descriptor", ctypes.POINTER(_LV2Descriptor)), ("lv2_handle", _HANDLE),
                ("pimpl", ctypes.c_void_p)]


class _LV2Feature(ctypes.Structure):
    _fields_ = [("URI", ctypes.c_char_p), ("data", ctypes.c_void_p)]


_MAP_FN = ctypes.CFUNCTYPE(ctypes.c_uint32, ctypes.c_void_p, ctypes.c_char_p)
_UNMAP_FN = ctypes.CFUNCTYPE(ctypes.c_char_p, ctypes.c_void_p, ctypes.c_uint32)


class _LV2URIDMap(ctypes.Structure):
    _fields_ = [("handle", ctypes.c_void_p), ("map", _MAP_FN)]


class _LV2URIDUnmap(ctypes.Structure):
    _fields_ = [("handle", ctypes.c_void_p), ("unmap", _UNMAP_FN)]


class _LV2Option(ctypes.Structure):
    _fields_ = [("context", ctypes.c_uint32), ("subject", ctypes.c_uint32), ("key", ctypes.c_uint32),
                ("size", ctypes.c_uint32), ("type", ctypes.c_uint32), ("value", ctypes.c_void_p)]


_RESPOND_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p)
_SCHEDULE_FN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p)


class _LV2WorkerSchedule(ctypes.Structure):
    _fields_ = [("handle", ctypes.c_void_p), ("schedule_work", _SCHEDULE_FN)]


class _LV2WorkerInterface(ctypes.Structure):
    _fields_ = [("work", ctypes.CFUNCTYPE(ctypes.c_int, _HANDLE, _RESPOND_FN, ctypes.c_void_p,
                                          ctypes.c_uint32, ctypes.c_void_p)),
                ("work_response", ctypes.CFUNCTYPE(ctypes.c_int, _HANDLE, ctypes.c_uint32, ctypes.c_void_p)),
                ("end_run", ctypes.CFUNCTYPE(ctypes.c_int, _HANDLE))]


class _URIDs:
    """urid:map condiviso da tutti i plugin del processo."""

    def __init__(self):
        self._ids: Dict[bytes, int] = {}
        self._uris: Dict[int, bytes] = {}
        self._lock = threading.Lock()
        self._map_cb = _MAP_FN(lambda _h, uri: self.map(uri))
        self._unmap_cb = _UNMAP_FN(lambda _h, urid: self._uris.get(urid))
        self.map_struct = _LV2URIDMap(None, self._map_cb)
        self.unmap_struct = _LV2URIDUnmap(None, self._unmap_cb)

    def map(self, uri) -> int:
        if isinstance(uri, str):
            uri = uri.encode()
        with self._lock:
            if uri not in self._ids:
                self._ids[uri] = len(self._ids) + 1
                self._uris[self._ids[uri]] = uri
            return self._ids[uri]


_world = None
_urids: Optional[_URIDs] = None
_nodes: Dict[str, int] = {}


def _get_world():
    global _world, _urids
    lib = _load_library()
    if lib is None:
        return None, None
    with _lib_lock:
        if _world is None:
            _world = lib.lilv_world_new()
            lib.lilv_world_load_all(_world)
            _urids = _URIDs()
            for key, uri in _URI.items():
                _nodes[key] = lib.lilv_new_uri(_world, uri.encode())
    return lib, _world


def _node_str(lib, node, free: bool = False) -> str:
    if not node:
        return ""
    text = (lib.lilv_node_as_string(node) or b"").decode("utf-8", "replace")
    if free:
        lib.lilv_node_free(node)
    return text


@dataclass
class LV2Param:
    index: int
    symbol: str
    name: str
    minimum: float
    maximum: float
    default: float
    toggled: bool = False
    integer: bool = False
    logarithmic: bool = False
    choices: List[Tuple[float, str]] = field(default_factory=list)


@dataclass
class LV2FileParam:
    uri: str
    label: str


@dataclass
class LV2PluginInfo:
    uri: str
    name: str
    author: str
    category: str
    instrument: bool
    audio_in: int
    audio_out: int
    params: List[LV2Param]
    supported: bool           # tutte le feature richieste sono fornite da questo host
    problem: str = ""
    files: List[LV2FileParam] = field(default_factory=list)


_SUPPORTED_FEATURES = {_URID_MAP, _URID_UNMAP, _OPTIONS, _BOUNDED, _WORKER_SCHEDULE,
                       "http://lv2plug.in/ns/lv2core#isLive", "http://lv2plug.in/ns/lv2core#hardRTCapable",
                       "http://lv2plug.in/ns/ext/buf-size#powerOf2BlockLength",
                       "http://lv2plug.in/ns/ext/buf-size#fixedBlockLength"}


def _plugin_info(lib, plugin) -> LV2PluginInfo:
    n = _nodes
    uri = _node_str(lib, lib.lilv_plugin_get_uri(plugin))
    name = _node_str(lib, lib.lilv_plugin_get_name(plugin), free=True) or uri
    author = _node_str(lib, lib.lilv_plugin_get_author_name(plugin), free=True)
    klass = lib.lilv_plugin_get_class(plugin)
    category = _node_str(lib, lib.lilv_plugin_class_get_label(klass)) if klass else ""
    class_uri = _node_str(lib, lib.lilv_plugin_class_get_uri(klass)) if klass else ""
    count = lib.lilv_plugin_get_num_ports(plugin)
    mins = (ctypes.c_float * count)()
    maxs = (ctypes.c_float * count)()
    defs = (ctypes.c_float * count)()
    lib.lilv_plugin_get_port_ranges_float(plugin, mins, maxs, defs)
    params: List[LV2Param] = []
    audio_in = audio_out = 0
    midi_in = False
    for i in range(count):
        port = lib.lilv_plugin_get_port_by_index(plugin, i)
        is_input = lib.lilv_port_is_a(plugin, port, n["input"])
        if lib.lilv_port_is_a(plugin, port, n["audio"]):
            if is_input:
                audio_in += 1
            else:
                audio_out += 1
        elif lib.lilv_port_is_a(plugin, port, n["atom"]) and is_input:
            if lib.lilv_port_supports_event(plugin, port, n["midi_event"]):
                midi_in = True
        elif lib.lilv_port_is_a(plugin, port, n["control"]) and is_input:
            if lib.lilv_port_has_property(plugin, port, n["not_on_gui"]):
                continue
            lo, hi, default = mins[i], maxs[i], defs[i]
            if lo != lo:          # NaN: senza limiti dichiarati
                lo = 0.0
            if hi != hi:
                hi = 1.0
            if default != default:
                default = lo
            choices = []
            points = lib.lilv_port_get_scale_points(plugin, port)
            if points:
                it = lib.lilv_scale_points_begin(points)
                while not lib.lilv_scale_points_is_end(points, it):
                    sp = lib.lilv_scale_points_get(points, it)
                    choices.append((float(lib.lilv_node_as_float(lib.lilv_scale_point_get_value(sp))),
                                    _node_str(lib, lib.lilv_scale_point_get_label(sp))))
                    it = lib.lilv_scale_points_next(points, it)
                lib.lilv_scale_points_free(points)
            enumeration = lib.lilv_port_has_property(plugin, port, n["enumeration"])
            params.append(LV2Param(
                i, _node_str(lib, lib.lilv_port_get_symbol(plugin, port)),
                _node_str(lib, lib.lilv_port_get_name(plugin, port), free=True),
                float(min(lo, hi)), float(max(lo, hi)), float(default),
                toggled=bool(lib.lilv_port_has_property(plugin, port, n["toggled"])),
                integer=bool(lib.lilv_port_has_property(plugin, port, n["integer"])),
                logarithmic=bool(lib.lilv_port_has_property(plugin, port, n["logarithmic"])),
                choices=sorted(choices) if (enumeration and choices) else []))
    required = []
    nodes = lib.lilv_plugin_get_required_features(plugin)
    if nodes:
        it = lib.lilv_nodes_begin(nodes)
        while not lib.lilv_nodes_is_end(nodes, it):
            required.append(_node_str(lib, lib.lilv_nodes_get(nodes, it)))
            it = lib.lilv_nodes_next(nodes, it)
        lib.lilv_nodes_free(nodes)
    files = _file_params(lib, plugin)
    missing = [r for r in required if r not in _SUPPORTED_FEATURES]
    instrument = (class_uri == _URI["instrument"] or (midi_in and audio_in == 0)) and audio_out > 0
    problem = ""
    if missing:
        problem = "richiede funzioni non supportate: " + ", ".join(r.rsplit("#", 1)[-1] for r in missing)
    elif audio_out == 0:
        problem = "nessuna uscita audio"
    elif instrument and not midi_in:
        problem = "nessun ingresso MIDI"
    elif not instrument and audio_in == 0:
        problem = "nessun ingresso audio"
    return LV2PluginInfo(uri, name, author, category, instrument, audio_in, audio_out, params,
                         supported=not problem, problem=problem, files=files)


def _file_params(lib, plugin) -> List[LV2FileParam]:
    """Le proprieta' del plugin che si impostano con un file."""
    n = _nodes
    out = []
    nodes = lib.lilv_plugin_get_value(plugin, n["patch_writable"])
    if not nodes:
        return out
    it = lib.lilv_nodes_begin(nodes)
    while not lib.lilv_nodes_is_end(nodes, it):
        prop = lib.lilv_nodes_get(nodes, it)
        if lib.lilv_world_ask(_world, prop, n["range"], n["atom_path"]):
            uri = _node_str(lib, prop)
            label = _node_str(lib, lib.lilv_world_get(_world, prop, n["label"], None), free=True)
            out.append(LV2FileParam(uri, label or uri.rsplit(":", 1)[-1].rsplit("#", 1)[-1]))
        it = lib.lilv_nodes_next(nodes, it)
    lib.lilv_nodes_free(nodes)
    return out


def encode_state(files: Dict[str, str]) -> str:
    """Stato LV2 come lo salva il progetto (base64, niente virgolette):
    i file scelti, proprieta' -> percorso."""
    files = {k: v for k, v in files.items() if v}
    return base64.b64encode(json.dumps({"files": files}).encode()).decode("ascii") if files else ""


def decode_state(state: str) -> Dict[str, str]:
    if not state:
        return {}
    try:
        files = json.loads(base64.b64decode(state)).get("files", {})
    except (ValueError, AttributeError):
        return {}
    return {str(k): str(v) for k, v in files.items() if v} if isinstance(files, dict) else {}


_info_cache: Optional[Dict[str, LV2PluginInfo]] = None


def list_lv2_plugins() -> List[LV2PluginInfo]:
    """Tutti i plugin LV2 installati (anche quelli che questo host non puo'
    caricare: supported=False con il motivo in 'problem')."""
    global _info_cache
    lib, world = _get_world()
    if lib is None:
        return []
    if _info_cache is None:
        plugins = lib.lilv_world_get_all_plugins(world)
        out = {}
        it = lib.lilv_plugins_begin(plugins)
        while not lib.lilv_plugins_is_end(plugins, it):
            info = _plugin_info(lib, lib.lilv_plugins_get(plugins, it))
            out[info.uri] = info
            it = lib.lilv_plugins_next(plugins, it)
        _info_cache = out
    return sorted(_info_cache.values(), key=lambda i: i.name.lower())


def lv2_plugin_info(uri: str) -> Optional[LV2PluginInfo]:
    list_lv2_plugins()
    return (_info_cache or {}).get(uri)


# ---------------------------------------------------------------------------
# Un'istanza pronta a elaborare
# ---------------------------------------------------------------------------

class LV2Error(Exception):
    pass


class LV2Instance:
    """Un plugin LV2 istanziato a una frequenza di campionamento. process()
    elabora un effetto, render() suona uno strumento da eventi MIDI. Non e'
    thread-safe: un'istanza per thread (vedi core.plugins)."""

    def __init__(self, uri: str, samplerate: int):
        lib, world = _get_world()
        if lib is None:
            raise LV2Error(tr("libreria lilv non disponibile"))
        info = lv2_plugin_info(uri)
        if info is None:
            raise LV2Error(tr("plugin LV2 non trovato: {uri}", uri=uri))
        if not info.supported:
            raise LV2Error(f"{info.name}: {info.problem}")
        self.info = info
        self.samplerate = int(samplerate)
        self._lib = lib
        uri_node = lib.lilv_new_uri(world, uri.encode())
        plugin = lib.lilv_plugins_get_by_uri(lib.lilv_world_get_all_plugins(world), uri_node)
        lib.lilv_node_free(uri_node)
        if not plugin:
            raise LV2Error(tr("plugin LV2 non trovato: {uri}", uri=uri))
        self._plugin = plugin
        self._keep = []
        self._pending_work: List[bytes] = []
        self._pending_responses: List[bytes] = []
        self._features = self._build_features()
        inst = lib.lilv_plugin_instantiate(plugin, float(self.samplerate), self._features)
        if not inst:
            raise LV2Error(tr("{name}: impossibile creare il plugin", name=info.name))
        self._inst_ptr = inst
        self._inst = ctypes.cast(inst, ctypes.POINTER(_LilvInstance)).contents
        self._desc = self._inst.lv2_descriptor.contents
        self._handle = self._inst.lv2_handle
        self._worker = None
        if self._desc.extension_data:
            ptr = self._desc.extension_data(_WORKER_INTERFACE.encode())
            if ptr:
                self._worker = ctypes.cast(ptr, ctypes.POINTER(_LV2WorkerInterface)).contents
        self._connect_ports()
        self.values = {p.symbol: p.default for p in info.params}
        self.files: Dict[str, str] = {}
        if self._desc.activate:
            self._desc.activate(self._handle)

    # -- feature ---------------------------------------------------------
    def _build_features(self):
        urids = _urids
        max_block = ctypes.c_int32(BLOCK)
        min_block = ctypes.c_int32(1)
        rate = ctypes.c_float(self.samplerate)
        t_int, t_float = urids.map(_ATOM_INT), urids.map(_ATOM_FLOAT)
        options = (_LV2Option * 5)(
            _LV2Option(0, 0, urids.map(_MAX_BLOCK), 4, t_int, ctypes.cast(ctypes.pointer(max_block), ctypes.c_void_p)),
            _LV2Option(0, 0, urids.map(_MIN_BLOCK), 4, t_int, ctypes.cast(ctypes.pointer(min_block), ctypes.c_void_p)),
            _LV2Option(0, 0, urids.map(_NOMINAL_BLOCK), 4, t_int,
                       ctypes.cast(ctypes.pointer(max_block), ctypes.c_void_p)),
            _LV2Option(0, 0, urids.map(_SAMPLE_RATE), 4, t_float, ctypes.cast(ctypes.pointer(rate), ctypes.c_void_p)),
            _LV2Option(0, 0, 0, 0, 0, None))

        def schedule(_handle, size, data):
            # il lavoro si fa dopo il run() in corso (vedi _run): dentro
            # run() il plugin puo' tenere un lock che serve anche a work()
            if self._worker is None:
                return 1
            self._pending_work.append(ctypes.string_at(data, size))
            return 0

        def respond(_handle, size, data):
            self._pending_responses.append(ctypes.string_at(data, size))
            return 0
        self._respond_cb = _RESPOND_FN(respond)
        self._schedule_cb = _SCHEDULE_FN(schedule)
        schedule_struct = _LV2WorkerSchedule(None, self._schedule_cb)
        feats = [(_URID_MAP, ctypes.pointer(urids.map_struct)), (_URID_UNMAP, ctypes.pointer(urids.unmap_struct)),
                 (_OPTIONS, options), (_BOUNDED, None), (_WORKER_SCHEDULE, ctypes.pointer(schedule_struct))]
        structs = [_LV2Feature(uri.encode(), ctypes.cast(data, ctypes.c_void_p) if data is not None else None)
                   for uri, data in feats]
        arr = (ctypes.POINTER(_LV2Feature) * (len(structs) + 1))(*[ctypes.pointer(s) for s in structs], None)
        self._keep += [max_block, min_block, rate, options, schedule_struct, structs, arr]
        return ctypes.cast(arr, ctypes.c_void_p)

    # -- porte -----------------------------------------------------------
    def _connect_ports(self):
        lib, plugin, n = self._lib, self._plugin, _nodes
        count = lib.lilv_plugin_get_num_ports(plugin)
        mins = (ctypes.c_float * count)()
        maxs = (ctypes.c_float * count)()
        defs = (ctypes.c_float * count)()
        lib.lilv_plugin_get_port_ranges_float(plugin, mins, maxs, defs)
        self._audio_in: List[np.ndarray] = []
        self._audio_out: List[np.ndarray] = []
        self._controls: Dict[int, ctypes.c_float] = {}
        self._midi_in: Optional[ctypes.Array] = None
        self._atom_out: List[ctypes.Array] = []
        self._patch_in: Optional[ctypes.Array] = None
        seq_type = _urids.map(_ATOM_SEQUENCE)
        self._chunk_type = _urids.map(_ATOM_CHUNK)
        self._seq_type = seq_type
        self._midi_type = _urids.map(_URI["midi_event"])
        for i in range(count):
            port = lib.lilv_plugin_get_port_by_index(plugin, i)
            is_input = lib.lilv_port_is_a(plugin, port, n["input"])
            if lib.lilv_port_is_a(plugin, port, n["audio"]) or lib.lilv_port_is_a(plugin, port, n["cv"]):
                buf = np.zeros(BLOCK, dtype=np.float32)
                if lib.lilv_port_is_a(plugin, port, n["audio"]):
                    (self._audio_in if is_input else self._audio_out).append(buf)
                self._keep.append(buf)
                self._desc.connect_port(self._handle, i, buf.ctypes.data_as(ctypes.c_void_p))
            elif lib.lilv_port_is_a(plugin, port, n["control"]):
                default = defs[i]
                value = ctypes.c_float(default if default == default else (mins[i] if mins[i] == mins[i] else 0.0))
                self._controls[i] = value
                self._desc.connect_port(self._handle, i, ctypes.cast(ctypes.pointer(value), ctypes.c_void_p))
            elif lib.lilv_port_is_a(plugin, port, n["atom"]):
                buf = (ctypes.c_uint8 * ATOM_CAPACITY)()
                self._keep.append(buf)
                if is_input:
                    if self._midi_in is None and lib.lilv_port_supports_event(plugin, port, n["midi_event"]):
                        self._midi_in = buf
                    if self._patch_in is None and lib.lilv_port_supports_event(plugin, port, n["patch_message"]):
                        self._patch_in = buf
                    self._clear_sequence(buf)
                    self._atom_in_bufs = getattr(self, "_atom_in_bufs", []) + [buf]
                else:
                    self._atom_out.append(buf)
                self._desc.connect_port(self._handle, i, ctypes.cast(buf, ctypes.c_void_p))
            else:
                buf = np.zeros(BLOCK, dtype=np.float32)
                self._keep.append(buf)
                self._desc.connect_port(self._handle, i, buf.ctypes.data_as(ctypes.c_void_p))
        self._by_symbol = {p.symbol: p.index for p in self.info.params}

    def _clear_sequence(self, buf):
        # LV2_Atom_Sequence vuota: size (del body) 8, type Sequence, unit 0, pad 0
        header = np.frombuffer(buf, dtype=np.uint32, count=4)
        header[:] = (8, self._seq_type, 0, 0)

    def _prepare_outputs(self):
        for buf in self._atom_out:
            header = np.frombuffer(buf, dtype=np.uint32, count=2)
            header[:] = (ATOM_CAPACITY - 8, self._chunk_type)

    def _write_midi(self, events: List[Tuple[int, bytes]]):
        """Scrive nella sequenza MIDI in ingresso gli eventi (frame nel
        blocco, byte MIDI)."""
        buf = self._midi_in
        raw = np.frombuffer(buf, dtype=np.uint8)
        offset = 16
        for frame, data in events:
            size = len(data)
            need = 16 + ((size + 7) & ~7)
            if offset + need > ATOM_CAPACITY:
                break
            np.frombuffer(buf, dtype=np.int64, count=1, offset=offset)[0] = frame
            np.frombuffer(buf, dtype=np.uint32, count=2, offset=offset + 8)[:] = (size, self._midi_type)
            raw[offset + 16:offset + 16 + size] = np.frombuffer(data, dtype=np.uint8)
            offset += need
        np.frombuffer(buf, dtype=np.uint32, count=4)[:] = (offset - 8, self._seq_type, 0, 0)

    # -- parametri -------------------------------------------------------
    def set_values(self, values: Dict[str, float]):
        for symbol, value in values.items():
            index = self._by_symbol.get(symbol)
            if index is not None:
                self._controls[index].value = float(value)
                self.values[symbol] = float(value)

    def set_files(self, files: Dict[str, str]):
        """Manda al plugin i file scelti (proprieta' -> percorso) che sono
        cambiati, e lo fa girare a vuoto finche' li ha caricati."""
        changed = {k: v for k, v in files.items() if self.files.get(k) != v}
        if not changed:
            return
        buf = self._patch_in or self._midi_in or next(iter(getattr(self, "_atom_in_bufs", [])), None)
        if buf is None:
            return
        offset = 16
        for prop, path in changed.items():
            event = self._patch_set(prop, path)
            if offset + len(event) > ATOM_CAPACITY:
                break
            np.frombuffer(buf, dtype=np.uint8)[offset:offset + len(event)] = np.frombuffer(event, dtype=np.uint8)
            offset += len(event)
        np.frombuffer(buf, dtype=np.uint32, count=4)[:] = (offset - 8, self._seq_type, 0, 0)
        for ins in self._audio_in:
            ins[:] = 0
        for _ in range(2):        # il secondo giro consegna le risposte del worker
            self._run(BLOCK)
        self.files.update(changed)

    def _patch_set(self, prop: str, path: str) -> bytes:
        """Evento (frame 0) con un oggetto patch:Set property=prop value=path."""
        m = _urids.map

        def atom(type_uri, body: bytes) -> bytes:
            return struct_pack("<II", len(body), m(type_uri)) + body

        def pad(data: bytes) -> bytes:
            return data + b"\0" * (-len(data) % 8)

        props = b""
        for key, value in ((_PATCH_PROPERTY, atom(_ATOM_URID, struct_pack("<I", m(prop)))),
                           (_PATCH_VALUE, atom(_URI["atom_path"], path.encode("utf-8") + b"\0"))):
            props += pad(struct_pack("<II", m(key), 0) + value)
        obj = atom(_ATOM_OBJECT, struct_pack("<II", 0, m(_PATCH_SET)) + props)
        return pad(struct_pack("<q", 0) + obj)

    # -- elaborazione ----------------------------------------------------
    def _run(self, frames: int):
        self._prepare_outputs()
        self._desc.run(self._handle, frames)
        while self._worker is not None and self._pending_work:
            body = self._pending_work.pop(0)
            data = ctypes.create_string_buffer(body, len(body))
            self._worker.work(self._handle, self._respond_cb, None, len(body), data)
        if self._worker is not None and self._pending_responses:
            responses, self._pending_responses = self._pending_responses, []
            for body in responses:
                data = ctypes.create_string_buffer(body, len(body))
                self._worker.work_response(self._handle, len(body), data)
        if self._worker is not None and self._worker.end_run:
            self._worker.end_run(self._handle)
        for buf in getattr(self, "_atom_in_bufs", []):
            self._clear_sequence(buf)

    def _outputs(self, frames: int) -> np.ndarray:
        outs = self._audio_out
        if len(outs) >= 2:
            return np.stack([outs[0][:frames], outs[1][:frames]], axis=1)
        return np.repeat(outs[0][:frames, None], 2, axis=1)

    def process(self, samples: np.ndarray) -> np.ndarray:
        """Effetto: samples float32 (frame, 2) -> (frame, 2)."""
        n = len(samples)
        out = np.zeros((n, 2), dtype=np.float32)
        ins = self._audio_in
        for start in range(0, n, BLOCK):
            frames = min(BLOCK, n - start)
            block = samples[start:start + frames]
            if len(ins) >= 2:
                ins[0][:frames] = block[:, 0]
                ins[1][:frames] = block[:, 1]
                for extra in ins[2:]:
                    extra[:frames] = 0
            elif ins:
                ins[0][:frames] = block.mean(axis=1)
            self._run(frames)
            out[start:start + frames] = self._outputs(frames)
        if len(ins) == 1 and len(self._audio_out) == 1:
            pass     # mono -> mono: gia' duplicato su due canali
        return out

    def render(self, events: List[Tuple[float, bytes]], seconds: float) -> np.ndarray:
        """Strumento: eventi (secondi, byte MIDI) ordinati -> (frame, 2)."""
        n = int(round(seconds * self.samplerate))
        out = np.zeros((n, 2), dtype=np.float32)
        pending = [(int(round(t * self.samplerate)), data) for t, data in events]
        i = 0
        for start in range(0, n, BLOCK):
            frames = min(BLOCK, n - start)
            block_events = []
            while i < len(pending) and pending[i][0] < start + frames:
                block_events.append((max(0, pending[i][0] - start), pending[i][1]))
                i += 1
            if self._midi_in is not None:
                self._write_midi(block_events)
            self._run(frames)
            out[start:start + frames] = self._outputs(frames)
        return out

    def reset(self):
        if self._desc.deactivate:
            self._desc.deactivate(self._handle)
        if self._desc.activate:
            self._desc.activate(self._handle)

    def close(self):
        if getattr(self, "_inst_ptr", None):
            if self._desc.deactivate:
                self._desc.deactivate(self._handle)
            self._lib.lilv_instance_free(self._inst_ptr)
            self._inst_ptr = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
