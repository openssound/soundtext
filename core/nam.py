"""
Profili NAM (Neural Amp Modeler, https://www.neuralampmodeler.com): modelli
neurali "catturati" da amplificatori e pedali veri, file .nam (JSON con
l'architettura della rete e i suoi pesi).

Qui si calcolano con numpy, senza PyTorch. L'architettura e' la WaveNet,
una pila di convoluzioni causali dilatate, facile da calcolare su tutto un
brano a blocchi, in entrambe le generazioni dei profili:
- A1 ("classica": standard / lite / feather / nano), la gran parte di quelli
  pubblicati, per esempio su Tone3000;
- A2, la piu' recente: bottleneck, kernel diversi per strato, gating
  "gated" o "blended", modulazioni FiLM, convoluzioni a gruppi, 1x1 verso
  la testa, testa convolutiva finale, rete di condizionamento
  (condition_dsp), reti "slimmable" e contenitori con piu' misure dello
  stesso modello (SlimmableContainer): qui si usa sempre la misura piena,
  la qualita' massima, come fa il plugin se non gli si chiede di
  risparmiare CPU.
Il calcolo segue quello del motore ufficiale NeuralAmpModelerCore (C++):
ordine dei pesi, strati, "testa" e head_scale (verificato confrontando le
uscite).

Anche i profili LSTM (la prima generazione di NAM, reti ricorrenti) si
possono usare: vedi _process_lstm per come si calcolano in fretta.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import numpy as np

from .version import get_app_root
from .i18n import tr

DEFAULT_SAMPLE_RATE = 48000
_BLOCK = 65536                     # campioni d'uscita per blocco

_FILM_KEYS = ("conv_pre_film", "conv_post_film", "input_mixin_pre_film", "input_mixin_post_film",
              "activation_pre_film", "activation_post_film", "layer1x1_post_film", "head1x1_post_film")
_LAYER_KEYS = {"input_size", "condition_size", "head_size", "head_bias", "head", "channels", "bottleneck",
               "kernel_size", "kernel_sizes", "dilations", "activation", "gated", "gating_mode",
               "secondary_activation", "groups_input", "groups_input_mixin", "head1x1", "layer1x1",
               "slimmable", *_FILM_KEYS}


class NamError(Exception):
    """File .nam non leggibile o di un formato non supportato."""


# ------------------------------------------------------------ attivazioni

def _fast_tanh(x: np.ndarray) -> np.ndarray:
    # la stessa approssimazione del motore NAM ("Fasttanh")
    ax = np.abs(x)
    x2 = x * x
    return (x * (2.45550750702956 + 2.45550750702956 * ax + (0.893229853513558 + 0.821226666969744 * ax) * x2)
            / (2.44506634652299 + (2.44506634652299 + x2) * np.abs(x + 0.814642734961073 * x * ax)))


def _sigmoid(x: np.ndarray) -> np.ndarray:
    with np.errstate(over="ignore"):
        return 1.0 / (1.0 + np.exp(-x))


def _leaky(slope: float):
    if 0.0 <= slope <= 1.0:
        return lambda x: np.maximum(x, x * np.float32(slope))
    return lambda x: np.where(x > 0, x, x * np.float32(slope))


def _prelu(slopes: List[float]):
    slopes = np.asarray(slopes, dtype=np.float32)

    def apply(x):
        # come il C++: pendenza del canale (riga) modulo il numero di pendenze
        s = slopes[np.arange(x.shape[0]) % len(slopes)][:, None]
        return np.where(x > 0, x, x * s)
    return apply


def _leaky_hardtanh(lo: float, hi: float, lo_slope: float, hi_slope: float):
    lo, hi, lo_slope, hi_slope = (np.float32(v) for v in (lo, hi, lo_slope, hi_slope))

    def apply(x):
        return np.where(x < lo, (x - lo) * lo_slope + lo, np.where(x > hi, (x - hi) * hi_slope + hi, x))
    return apply


def _activation(spec) -> Callable[[np.ndarray], np.ndarray]:
    """La funzione di attivazione dal nome (o da {"type": nome, ...})."""
    params = {}
    if isinstance(spec, dict):
        params = spec
        spec = spec.get("type")
    name = str(spec)
    if name == "Tanh":
        return np.tanh
    if name == "Fasttanh":
        return _fast_tanh
    if name == "ReLU":
        return lambda x: np.maximum(x, np.float32(0.0))
    if name == "Hardtanh":                                  # il motore usa sempre [-1, 1]
        return lambda x: np.clip(x, np.float32(-1.0), np.float32(1.0))
    if name == "Sigmoid":
        return _sigmoid
    if name == "LeakyReLU":
        return _leaky(float(params.get("negative_slope", 0.01)))
    if name == "PReLU":
        if "negative_slopes" in params:
            return _prelu([float(v) for v in params["negative_slopes"]])
        return _prelu([float(params.get("negative_slope", 0.01))])
    if name == "SiLU":
        return lambda x: x * _sigmoid(x)
    if name == "Hardswish":
        return lambda x: x * np.clip(x + np.float32(3.0), np.float32(0.0), np.float32(6.0)) * np.float32(1.0 / 6.0)
    if name in ("LeakyHardtanh", "LeakyHardTanh"):
        return _leaky_hardtanh(float(params.get("min_val", -1.0)), float(params.get("max_val", 1.0)),
                               float(params.get("min_slope", 0.01)), float(params.get("max_slope", 0.01)))
    if name == "Softsign":
        return lambda x: x / (np.float32(1.0) + np.abs(x))
    raise NamError(tr("attivazione '{name}' non supportata", name=name))


# ------------------------------------------------------------ struttura

@dataclass
class _FiLM:
    """Modulazione FiLM: scala (e spostamento) per canale calcolati dal
    segnale di condizionamento con una 1x1."""
    weight: np.ndarray          # (dim o 2*dim, cond)
    bias: np.ndarray            # (dim o 2*dim, 1)
    dim: int
    shift: bool

    def __call__(self, x: np.ndarray, cond: np.ndarray) -> np.ndarray:
        ss = self.weight @ cond + self.bias
        if self.shift:
            return x * ss[:self.dim] + ss[self.dim:]
        return x * ss


@dataclass
class _Layer:
    # Pesi nel layout (uscita, ingresso): la rete lavora su matrici canali x
    # tempo, il layout per cui numpy moltiplica piu' in fretta.
    dilation: int
    conv: np.ndarray            # (K, z, C): tap k -> campione t - (K-1-k)*d
    conv_bias: np.ndarray       # (z, 1)
    mixin: np.ndarray           # (z, cond)
    gating: str                 # "none", "gated" o "blended"
    activation: Callable
    secondary: Optional[Callable]
    bottleneck: int
    layer1x1: Optional[tuple]   # (C, B), (C, 1)
    head1x1: Optional[tuple]    # (H, B), (H, 1)
    films: Dict[str, _FiLM]

    @property
    def receptive_field(self) -> int:
        return (self.conv.shape[0] - 1) * self.dilation


@dataclass
class _LayerArray:
    input_size: int
    channels: int
    head_in: int                # canali verso la testa (bottleneck o uscite di head1x1)
    rechannel: np.ndarray       # (C, in)
    layers: List[_Layer]
    head: np.ndarray            # (Kh, head_size, head_in)
    head_bias: Optional[np.ndarray]   # (head_size, 1)
    head_dilation: int

    @property
    def head_size(self) -> int:
        return self.head.shape[1]

    @property
    def receptive_field(self) -> int:
        return sum(layer.receptive_field for layer in self.layers) + (self.head.shape[0] - 1) * self.head_dilation


@dataclass
class _WaveNet:
    arrays: List[_LayerArray]
    head_scale: float
    post_head: List[tuple]      # testa finale: (attivazione, pesi (K, out, in), bias)
    condition: Optional["_WaveNet"]

    @property
    def in_channels(self) -> int:
        return self.arrays[0].input_size

    @property
    def out_channels(self) -> int:
        return self.post_head[-1][1].shape[1] if self.post_head else self.arrays[-1].head_size

    @property
    def receptive_field(self) -> int:
        rf = sum(a.receptive_field for a in self.arrays)
        rf += sum(w.shape[0] - 1 for _, w, _ in self.post_head)
        if self.condition is not None:
            rf += self.condition.receptive_field
        return rf


@dataclass
class _LSTMLayer:
    # Porte riordinate come i, f, o, g (il file le ha i, f, g, o): le tre
    # sigmoidi sono righe contigue.
    w: np.ndarray               # (4H, ingresso + H)
    b: np.ndarray               # (4H, 1)
    h0: np.ndarray              # (H,) stato iniziale (fa parte dei pesi)
    c0: np.ndarray              # (H,)


@dataclass
class _LSTM:
    in_channels: int
    layers: List[_LSTMLayer]
    head: np.ndarray            # (out, H)
    head_bias: np.ndarray       # (out, 1)
    prewarm: int                # campioni di silenzio prima di suonare, come il C++
    start: Optional[tuple] = None   # stati dopo il prewarm (calcolati una volta)

    @property
    def out_channels(self) -> int:
        return self.head.shape[0]

    @property
    def receptive_field(self) -> int:
        return 0


@dataclass
class NamModel:
    """Un profilo NAM pronto da calcolare (vedi process)."""
    path: str
    sample_rate: int
    net: object                 # _WaveNet o _LSTM
    metadata: Dict = field(default_factory=dict)
    generation: str = "A1"      # "A1", "A2" o "LSTM"
    measured_loudness: Optional[float] = field(default=None, repr=False)

    @property
    def receptive_field(self) -> int:
        return self.net.receptive_field

    @property
    def name(self) -> str:
        name = (self.metadata or {}).get("name")
        return str(name) if name else os.path.splitext(os.path.basename(self.path))[0]

    @property
    def description(self) -> str:
        """Descrizione per il pannello: marca, modello e tipo, se il file li dice."""
        meta = self.metadata or {}
        parts = [str(meta[k]) for k in ("gear_make", "gear_model") if meta.get(k)]
        kind = {"amp": "amplificatore", "pedal": "pedale", "amp_cab": "amplificatore con cassa",
                "pedal_amp": "pedale e amplificatore", "amp_pedal_cab": "pedale, amplificatore e cassa",
                "preamp": "preamplificatore", "studio": "catena da studio"}.get(meta.get("gear_type"), "")
        text = " ".join(parts)
        if kind:
            text = f"{text} ({kind})" if text else kind
        if meta.get("modeled_by"):
            text += f" — di {meta['modeled_by']}" if text else f"di {meta['modeled_by']}"
        return text

    @property
    def loudness(self) -> Optional[float]:
        value = (self.metadata or {}).get("loudness")
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None


# ------------------------------------------------------------ lettura

class _Weights:
    """I pesi del file, letti in ordine come fa set_weights_ nel C++."""

    def __init__(self, values):
        self.values = np.asarray(values if values is not None else [], dtype=np.float64)
        self.pos = 0

    def take(self, count: int) -> np.ndarray:
        if self.pos + count > len(self.values):
            raise NamError(tr("pesi mancanti nel file"))
        chunk = self.values[self.pos:self.pos + count]
        self.pos += count
        return chunk

    def conv1x1(self, cin: int, cout: int, bias: bool, groups: int = 1):
        """Conv1x1 (a gruppi: matrice a blocchi sulla diagonale)."""
        _check_groups(cin, cout, groups)
        op, ip = cout // groups, cin // groups
        w = np.zeros((cout, cin))
        for g in range(groups):
            w[g * op:(g + 1) * op, g * ip:(g + 1) * ip] = self.take(op * ip).reshape(op, ip)
        b = _f32(self.take(cout).reshape(cout, 1)) if bias else None
        return _f32(w), b

    def conv1d(self, cin: int, cout: int, k: int, bias: bool, groups: int = 1):
        """Conv1D: per gruppo, uscita i, ingresso j, tap k."""
        _check_groups(cin, cout, groups)
        op, ip = cout // groups, cin // groups
        w = np.zeros((k, cout, cin))
        for g in range(groups):
            w[:, g * op:(g + 1) * op, g * ip:(g + 1) * ip] = self.take(op * ip * k).reshape(op, ip, k).transpose(2, 0, 1)
        b = _f32(self.take(cout).reshape(cout, 1)) if bias else None
        return _f32(w), b


def _f32(a: np.ndarray) -> np.ndarray:
    return np.ascontiguousarray(a, dtype=np.float32)


def _check_groups(cin: int, cout: int, groups: int):
    if groups < 1 or cin % groups or cout % groups:
        raise NamError(tr("gruppi delle convoluzioni incoerenti"))


def _per_layer(value, count: int, what: str) -> list:
    if isinstance(value, list):
        if len(value) != count:
            raise NamError(tr("'{what}': {0} valori per {count} strati", len(value), what=what, count=count))
        return list(value)
    return [value] * count


def _film_params(spec: dict, key: str):
    """(attivo, shift, gruppi) di una FiLM, come parse_film_params nel C++."""
    value = spec.get(key)
    if value is None or value is False:
        return False, False, 1
    if not isinstance(value, dict):
        value = {}
    return bool(value.get("active", True)), bool(value.get("shift", True)), int(value.get("groups", 1))


def _parse_array(spec: dict, weights: _Weights, index: int) -> _LayerArray:
    extra = set(spec) - _LAYER_KEYS
    if extra:
        raise NamError(tr("formato NAM piu' recente non ancora supportato: ") + ", ".join(sorted(extra)))
    slim = spec.get("slimmable")
    if isinstance(slim, dict) and slim.get("method", "") not in ("", "slice_channels_uniform"):
        raise NamError(tr("metodo slimmable '{0}' non supportato", slim.get('method')))
    size_in, cond = int(spec["input_size"]), int(spec["condition_size"])
    channels = int(spec["channels"])
    bottleneck = int(spec.get("bottleneck", channels))
    groups_in, groups_mix = int(spec.get("groups_input", 1)), int(spec.get("groups_input_mixin", 1))
    l1 = spec.get("layer1x1") or {"active": True, "groups": 1}
    l1_active, l1_groups = bool(l1.get("active", True)), int(l1.get("groups", 1))
    h1 = spec.get("head1x1") or {"active": False}
    h1_active = bool(h1.get("active", False))
    h1_out, h1_groups = int(h1.get("out_channels", channels)), int(h1.get("groups", 1))
    if not l1_active and bottleneck != channels:
        raise NamError(tr("senza layer1x1 il bottleneck deve essere uguale ai canali"))

    head_spec = spec.get("head")
    if isinstance(head_spec, dict):
        head_size, head_k = int(head_spec["out_channels"]), int(head_spec["kernel_size"])
        head_dilation, head_bias = int(head_spec.get("head_dilation", 1)), bool(head_spec["bias"])
    elif "head_size" in spec:
        head_size, head_k, head_dilation, head_bias = int(spec["head_size"]), 1, 1, bool(spec["head_bias"])
    else:
        raise NamError(tr("strati {0}: manca la testa", index + 1))
    if head_k < 1:
        raise NamError(tr("kernel della testa non valido"))

    dilations = [int(d) for d in spec["dilations"]]
    n = len(dilations)
    if "kernel_size" in spec and "kernel_sizes" in spec:
        raise NamError(tr("kernel_size e kernel_sizes insieme"))
    if "kernel_sizes" in spec:
        kernels = [int(k) for k in _per_layer(spec["kernel_sizes"], n, "kernel_sizes")]
    else:
        kernels = [int(spec["kernel_size"])] * n
    activations = [_activation(a) for a in _per_layer(spec["activation"], n, "activation")]

    if "gating_mode" in spec:
        modes = [str(m) for m in _per_layer(spec["gating_mode"], n, "gating_mode")]
        secondaries = _per_layer(spec.get("secondary_activation", "Sigmoid"), n, "secondary_activation")
        secondaries = ["Sigmoid" if s is None and m != "none" else s for s, m in zip(secondaries, modes)]
    else:
        modes = ["gated" if spec.get("gated", False) else "none"] * n
        secondaries = ["Sigmoid"] * n
    for m in modes:
        if m not in ("none", "gated", "blended"):
            raise NamError(tr("gating_mode '{m}' non valido", m=m))

    films = {key: _film_params(spec, key) for key in _FILM_KEYS}
    if films["layer1x1_post_film"][0] and not l1_active:
        raise NamError(tr("layer1x1_post_film senza layer1x1"))
    if films["head1x1_post_film"][0] and not h1_active:
        raise NamError(tr("head1x1_post_film senza head1x1"))

    rechannel, _ = weights.conv1x1(size_in, channels, False)
    layers = []
    for d, k, act, mode, sec in zip(dilations, kernels, activations, modes, secondaries):
        z = 2 * bottleneck if mode != "none" else bottleneck
        conv, conv_bias = weights.conv1d(channels, z, k, True, groups_in)
        mixin, _ = weights.conv1x1(cond, z, False, groups_mix)
        layer1x1 = weights.conv1x1(bottleneck, channels, True, l1_groups) if l1_active else None
        head1x1 = weights.conv1x1(bottleneck, h1_out, True, h1_groups) if h1_active else None
        dims = {"conv_pre_film": channels, "conv_post_film": z, "input_mixin_pre_film": cond,
                "input_mixin_post_film": z, "activation_pre_film": z, "activation_post_film": bottleneck,
                "layer1x1_post_film": channels, "head1x1_post_film": h1_out}
        layer_films = {}
        for key in _FILM_KEYS:
            active, shift, groups = films[key]
            if active:
                w, b = weights.conv1x1(cond, (2 if shift else 1) * dims[key], True, groups)
                layer_films[key] = _FiLM(w, b, dims[key], shift)
        layers.append(_Layer(d, conv, conv_bias, mixin, mode, act,
                             _activation(sec) if mode != "none" else None,
                             bottleneck, layer1x1, head1x1, layer_films))
    head_in = h1_out if h1_active else bottleneck
    head, head_b = weights.conv1d(head_in, head_size, head_k, head_bias)
    return _LayerArray(size_in, channels, head_in, rechannel, layers, head, head_b, head_dilation)


def _parse_wavenet(data: dict) -> _WaveNet:
    architecture = data.get("architecture")
    if architecture != "WaveNet":
        raise NamError(tr("architettura '{architecture}' non supportata (solo WaveNet e LSTM)", architecture=architecture))
    config = data.get("config") or {}
    condition = None
    if config.get("condition_dsp") is not None:
        condition = _parse_dsp(config["condition_dsp"])
        if not isinstance(condition, _WaveNet):
            raise NamError(tr("rete di condizionamento LSTM non supportata"))
    weights = _Weights(data.get("weights"))
    arrays = [_parse_array(spec, weights, i) for i, spec in enumerate(config.get("layers") or [])]
    if not arrays:
        raise NamError(tr("nessuno strato nel file"))
    in_channels = int(config.get("in_channels", 1))
    cond_channels = condition.out_channels if condition is not None else in_channels
    if arrays[0].input_size != in_channels:
        raise NamError(tr("dimensioni degli strati incoerenti"))
    for prev, nxt in zip(arrays, arrays[1:]):
        # la testa e le uscite di un gruppo di strati entrano nel successivo
        if prev.head_size != nxt.head_in or prev.channels != nxt.input_size:
            raise NamError(tr("dimensioni degli strati incoerenti"))
    for array in arrays:
        if any(layer.mixin.shape[1] != cond_channels for layer in array.layers):
            raise NamError(tr("dimensioni del condizionamento incoerenti"))
    post_head = []
    head = config.get("head")
    if head is not None:
        cin = arrays[-1].head_size
        kernels = [int(k) for k in head["kernel_sizes"]]
        if not kernels or min(kernels) < 1:
            raise NamError(tr("testa finale non valida"))
        act = _activation(head["activation"])
        for i, k in enumerate(kernels):
            cout = int(head["out_channels"]) if i == len(kernels) - 1 else int(head["channels"])
            w, b = weights.conv1d(cin, cout, k, True)
            post_head.append((act, w, b))
            cin = cout
    head_scale = float(weights.take(1)[0])
    if weights.pos != len(weights.values):
        raise NamError(tr("numero di pesi sbagliato ({0} invece di {pos})", len(weights.values), pos=weights.pos))
    return _WaveNet(arrays, head_scale, post_head, condition)


def _parse_lstm(data: dict) -> _LSTM:
    config = data.get("config") or {}
    layers_n, size_in = int(config["num_layers"]), int(config["input_size"])
    hidden = int(config["hidden_size"])
    in_ch, out_ch = int(config.get("in_channels", 1)), int(config.get("out_channels", 1))
    if layers_n < 1 or hidden < 1 or size_in != in_ch:
        raise NamError(tr("LSTM non valido"))
    weights = _Weights(data.get("weights"))
    order = np.concatenate([np.arange(0, 2 * hidden), np.arange(3 * hidden, 4 * hidden),
                            np.arange(2 * hidden, 3 * hidden)])          # i, f, g, o -> i, f, o, g
    layers = []
    for i in range(layers_n):
        cin = size_in if i == 0 else hidden
        w = weights.take(4 * hidden * (cin + hidden)).reshape(4 * hidden, cin + hidden)[order]
        b = weights.take(4 * hidden).reshape(4 * hidden, 1)[order]
        h0, c0 = weights.take(hidden), weights.take(hidden)
        layers.append(_LSTMLayer(_f32(w), _f32(b), _f32(h0), _f32(c0)))
    head = _f32(weights.take(out_ch * hidden).reshape(out_ch, hidden))
    head_bias = _f32(weights.take(out_ch).reshape(out_ch, 1))
    if weights.pos != len(weights.values):
        raise NamError(tr("numero di pesi sbagliato ({0} invece di {pos})", len(weights.values), pos=weights.pos))
    rate = data.get("sample_rate") or DEFAULT_SAMPLE_RATE
    return _LSTM(in_ch, layers, head, head_bias, max(1, int(0.5 * float(rate))))


def _parse_dsp(data: dict):
    if not isinstance(data, dict):
        raise NamError(tr("non e' un file .nam"))
    if data.get("architecture") == "SlimmableContainer":
        # piu' misure dello stesso modello: la piena (l'ultima) e' la migliore
        submodels = (data.get("config") or {}).get("submodels") or []
        if not submodels:
            raise NamError(tr("contenitore senza modelli"))
        limits = [float(s["max_value"]) for s in submodels]
        if any(b <= a for a, b in zip(limits, limits[1:])) or limits[-1] < 1.0:
            raise NamError(tr("contenitore non valido"))
        return _parse_dsp(submodels[-1]["model"])
    if data.get("architecture") == "LSTM":
        return _parse_lstm(data)
    return _parse_wavenet(data)


def _is_a2(data) -> bool:
    """Il file usa le novita' dell'architettura A2?"""
    if isinstance(data, dict):
        if data.get("architecture") == "SlimmableContainer":
            return True
        layers = (data.get("config") or {}).get("layers") or []
        classic = {"input_size", "condition_size", "head_size", "channels", "kernel_size", "dilations",
                   "activation", "gated", "head_bias"}
        if any(set(spec) - classic for spec in layers if isinstance(spec, dict)):
            return True
        config = data.get("config") or {}
        return config.get("head") is not None or config.get("condition_dsp") is not None
    return False


def _parse(data: dict, path: str) -> NamModel:
    net = _parse_dsp(data)
    if net.in_channels != 1 or net.out_channels != 1:
        raise NamError(tr("il profilo deve avere un ingresso e un'uscita mono"))
    rate = data.get("sample_rate") or DEFAULT_SAMPLE_RATE
    generation = "LSTM" if isinstance(net, _LSTM) else "A2" if _is_a2(data) else "A1"
    return NamModel(path, int(float(rate)), net, data.get("metadata") or {}, generation)


_cache: Dict[tuple, NamModel] = {}


def load_nam(path: str) -> NamModel:
    """Il profilo del file (in cache finche' il file non cambia). Solleva
    NamError se il file manca, non e' valido o non e' supportato."""
    try:
        stat = os.stat(path)
    except OSError:
        raise NamError(tr("file non trovato"))
    key = (os.path.abspath(path), stat.st_mtime, stat.st_size)
    if key not in _cache:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as e:
            raise NamError(tr("non e' un file .nam leggibile ({__name__})", __name__=e.__class__.__name__))
        if not isinstance(data, dict):
            raise NamError(tr("non e' un file .nam"))
        try:
            _cache[key] = _parse(data, path)
        except (KeyError, TypeError, ValueError, AttributeError, IndexError) as e:
            raise NamError(tr("file .nam non valido ({e})", e=e))
    return _cache[key]


LOUDNESS_INPUT = os.path.join(get_app_root(), "assets", "nam_loudness_input.wav")


def reference_loudness(model: NamModel) -> Optional[float]:
    """La "loudness" del profilo in dB: quella dichiarata nel file o, per i
    profili che non la dichiarano (i piu' vecchi), misurata come fa
    l'addestramento di NAM: livello RMS dell'uscita per il segnale di
    riferimento assets/nam_loudness_input.wav (calcolata una volta)."""
    if model.loudness is not None:
        return model.loudness
    if model.measured_loudness is None:
        try:
            from .audio_tracks import read_wav
            x = read_wav(LOUDNESS_INPUT)[0].mean(axis=1)
        except Exception:                                   # file mancante: niente misura
            return None
        y = process(model, x).astype(np.float64)
        rms = float(np.sqrt(np.mean(y * y)))
        model.measured_loudness = 20.0 * np.log10(max(rms, 1e-9))
    return model.measured_loudness


def nam_problem(path: str) -> str:
    """'' se il profilo si puo' usare, altrimenti il motivo (per il pannello)."""
    if not path:
        return tr("nessun profilo scelto")
    try:
        load_nam(path)
    except NamError as e:
        return str(e)
    return ""


# ------------------------------------------------------------ calcolo
# Tutto "valido" e allineato alla fine: ogni convoluzione accorcia il tempo
# del suo campo ricettivo, e i segnali che si sommano si allineano
# sull'ultimo campione.

def _conv(x: np.ndarray, w: np.ndarray, dilation: int, bias: Optional[np.ndarray]) -> np.ndarray:
    k = w.shape[0]
    t = x.shape[1] - (k - 1) * dilation
    y = w[0] @ x[:, 0:t]
    for i in range(1, k):
        y += w[i] @ x[:, i * dilation:i * dilation + t]
    if bias is not None:
        y += bias
    return y


def _tail(x: np.ndarray, n: int) -> np.ndarray:
    return x[:, x.shape[1] - n:]


def _run_layer(layer: _Layer, h: np.ndarray, cond: np.ndarray):
    films = layer.films
    x = h
    if "conv_pre_film" in films:
        x = films["conv_pre_film"](h, _tail(cond, h.shape[1]))
    z = _conv(x, layer.conv, layer.dilation, layer.conv_bias)
    t = z.shape[1]
    c = _tail(cond, t)
    if "conv_post_film" in films:
        z = films["conv_post_film"](z, c)
    mix = films["input_mixin_pre_film"](c, c) if "input_mixin_pre_film" in films else c
    m = layer.mixin @ mix
    if "input_mixin_post_film" in films:
        m = films["input_mixin_post_film"](m, c)
    z = z + m
    if "activation_pre_film" in films:
        z = films["activation_pre_film"](z, c)
    b = layer.bottleneck
    if layer.gating == "none":
        a = layer.activation(z)
    elif layer.gating == "gated":
        a = layer.activation(z[:b]) * layer.secondary(z[b:])
    else:                                   # "blended": tra attivato e non attivato
        alpha = layer.secondary(z[b:])
        a = alpha * layer.activation(z[:b]) + (np.float32(1.0) - alpha) * z[:b]
    if "activation_post_film" in films:
        a = films["activation_post_film"](a, c)
    if layer.layer1x1 is not None:
        r = layer.layer1x1[0] @ a + layer.layer1x1[1]
        if "layer1x1_post_film" in films:
            r = films["layer1x1_post_film"](r, c)
        h = _tail(h, t) + r
    else:
        h = _tail(h, t)
    if layer.head1x1 is not None:
        a = layer.head1x1[0] @ a + layer.head1x1[1]
        if "head1x1_post_film" in films:
            a = films["head1x1_post_film"](a, c)
    return h, a


def _run(net: _WaveNet, x: np.ndarray) -> np.ndarray:
    """Uscita della rete (canali x tempo) per l'ingresso x (canali x tempo,
    con davanti il campo ricettivo): piu' corta, allineata alla fine."""
    cond = x
    if net.condition is not None:
        cond = _run(net.condition, x)
        x = _tail(x, cond.shape[1])
    layer_in, head_in = x, None
    for array in net.arrays:
        h = array.rechannel @ layer_in
        head = head_in
        for layer in array.layers:
            h, contrib = _run_layer(layer, h, cond)
            if head is None:
                head = contrib
            else:
                n = min(head.shape[1], contrib.shape[1])
                head = _tail(head, n) + _tail(contrib, n)
        layer_in, head_in = h, _conv(head, array.head, array.head_dilation, array.head_bias)
    y = np.float32(net.head_scale) * head_in
    for act, w, b in net.post_head:
        y = _conv(act(y), w, 1, b)
    return y


# ------------------------------------------------------------ LSTM
# Una rete ricorrente va calcolata un campione dopo l'altro: in Python, un
# campione alla volta, un brano intero richiederebbe minuti. Il segnale si
# divide allora in tratti (_LSTM_CHUNK secondi) calcolati tutti insieme,
# ogni passo una moltiplicazione di matrici con una colonna per tratto.
# Ogni tratto deve partire dallo stato in cui finisce il precedente: al
# primo giro non lo si conosce ancora (si parte dallo stato iniziale), al
# giro dopo ogni tratto riparte dallo stato finale del precedente, e cosi'
# via finche' gli stati ai confini non cambiano piu': allora il risultato
# e' quello del calcolo campione per campione. Le reti dei profili
# "dimenticano" in fretta, quindi bastano di solito due giri; in ogni caso
# il tratto k e' esatto dopo k giri, quindi il ciclo termina sempre.

_LSTM_CHUNK = 0.25
_LSTM_TOL = 1e-6


def _lstm_run(net: _LSTM, x: np.ndarray, h: List[np.ndarray], c: List[np.ndarray], want_out: bool):
    """x: (passi, colonne). h, c: stati per strato (H, colonne), aggiornati.
    Restituisce l'uscita (passi, colonne) se richiesta."""
    steps, cols = x.shape
    hidden = net.layers[0].h0.shape[0]
    xh, z, g, tc = [], None, None, None
    for i, layer in enumerate(net.layers):
        buf = np.empty((layer.w.shape[1], cols), dtype=np.float32)
        buf[layer.w.shape[1] - hidden:] = h[i]
        xh.append(buf)
    z = np.empty((4 * hidden, cols), dtype=np.float32)
    tc = np.empty((hidden, cols), dtype=np.float32)
    out = np.empty((steps, cols), dtype=np.float32) if want_out else None
    head = net.head[0]
    last = len(net.layers) - 1
    with np.errstate(over="ignore"):
        for t in range(steps):
            xh[0][0] = x[t]
            for i, layer in enumerate(net.layers):
                buf = xh[i]
                np.matmul(layer.w, buf, out=z)
                z += layer.b
                sg = z[:3 * hidden]                     # i, f, o: sigmoidi
                np.negative(sg, out=sg)
                np.exp(sg, out=sg)
                sg += 1.0
                np.reciprocal(sg, out=sg)
                g = z[3 * hidden:]
                np.tanh(g, out=g)
                ci = c[i]
                ci *= z[hidden:2 * hidden]
                g *= z[:hidden]
                ci += g
                np.tanh(ci, out=tc)
                hi = buf[buf.shape[0] - hidden:]
                np.multiply(z[2 * hidden:3 * hidden], tc, out=hi)
                if i < last:
                    xh[i + 1][:hidden] = hi
            if want_out:
                np.matmul(head, xh[last][xh[last].shape[0] - hidden:], out=out[t])
    for i in range(len(net.layers)):
        h[i] = xh[i][xh[i].shape[0] - hidden:].copy()
    if want_out:
        out += net.head_bias[0, 0]
    return out


def _lstm_start(net: _LSTM) -> tuple:
    """Gli stati dopo il prewarm (silenzio a partire dagli stati iniziali
    del file). Si ferma prima se lo stato non cambia piu': da li' in poi
    resterebbe identico."""
    if net.start is None:
        h = [layer.h0[:, None].copy() for layer in net.layers]
        c = [layer.c0[:, None].copy() for layer in net.layers]
        done = 0
        while done < net.prewarm:
            n = min(256, net.prewarm - done)
            _lstm_run(net, np.zeros((n - 1, 1), dtype=np.float32), h, c, False)
            before = [a.copy() for a in h + c]
            _lstm_run(net, np.zeros((1, 1), dtype=np.float32), h, c, False)
            done += n
            if all(np.array_equal(a, b) for a, b in zip(before, h + c)):
                break
        net.start = ([a[:, 0] for a in h], [a[:, 0] for a in c])
    return net.start


def _process_lstm(net: _LSTM, x: np.ndarray, rate: int) -> np.ndarray:
    h0, c0 = _lstm_start(net)
    n = len(x)
    chunk = max(1, int(_LSTM_CHUNK * rate))
    cols = max(1, -(-n // chunk))
    if cols < 3:                                    # corto: campione per campione
        h = [a[:, None].copy() for a in h0]
        c = [a[:, None].copy() for a in c0]
        return _lstm_run(net, x[:, None], h, c, True)[:, 0]
    padded = np.zeros(cols * chunk, dtype=np.float32)
    padded[:n] = x
    steps = np.ascontiguousarray(padded.reshape(cols, chunk).T)

    def run(h_init, c_init, want_out):
        h = [a.copy() for a in h_init]
        c = [a.copy() for a in c_init]
        out = _lstm_run(net, steps, h, c, want_out)
        return out, h, c

    h_init = [np.repeat(a[:, None], cols, axis=1) for a in h0]
    c_init = [np.repeat(a[:, None], cols, axis=1) for a in c0]
    _, h_end, c_end = run(h_init, c_init, False)
    for _ in range(cols):
        for a, b, start in zip(h_init + c_init, h_end + c_end, h0 + c0):
            a[:, 0] = start                        # il primo tratto parte dal prewarm
            a[:, 1:] = b[:, :-1]                   # gli altri dalla fine del precedente
        out, h_new, c_new = run(h_init, c_init, True)
        change = max(float(np.abs(a - b).max()) for a, b in zip(h_new + c_new, h_end + c_end))
        scale = max(1.0, max(float(np.abs(a).max()) for a in c_new))
        h_end, c_end = h_new, c_new
        if change <= _LSTM_TOL * scale:
            break
    return out.T.reshape(-1)[:n]


def process(model: NamModel, x: np.ndarray) -> np.ndarray:
    """Il segnale mono x (float, alla frequenza del modello) attraverso il
    profilo, a blocchi: stessa lunghezza, partendo da silenzio."""
    x = np.asarray(x, dtype=np.float32)
    if isinstance(model.net, _LSTM):
        return _process_lstm(model.net, x, model.sample_rate)
    rf = model.receptive_field
    padded = np.concatenate([np.zeros(rf, dtype=np.float32), x])
    out = np.empty(len(x), dtype=np.float32)
    for start in range(0, len(x), _BLOCK):
        end = min(len(x), start + _BLOCK)
        y = _run(model.net, padded[None, start:end + rf])[0]
        out[start:end] = y[len(y) - (end - start):]
    return out
