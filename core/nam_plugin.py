"""
Motore NAM veloce: i profili NAM calcolati dal plugin LV2 Neural Amp
Modeler (motore in C++, GPL-3.0) quando e' installato (Suoni -> Scarica e
installa..., voce "nam-plugin"), invece che dalla rete in numpy di
core.nam.

Il segnale si divide in pezzi, uno per processo dei plugin (core.plugins,
canali nam0, nam1...), e ogni pezzo parte dal campo ricettivo dell'audio che
lo precede: il risultato e' quello del calcolo in un colpo solo (misurato:
0,15-0,3% di differenza dalla rete in numpy, la tanh veloce del C++), e
4-6 volte piu' in fretta. Se il plugin manca o non risponde si torna alla
rete in numpy (process() torna None).

Il plugin porta da solo i profili che dichiarano la loudness a -18 dB:
process() toglie quel guadagno, perche' la normalizzazione la fa gia'
core.effects (anche per i profili senza loudness dichiarata).
"""

import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

import numpy as np

URI = "http://github.com/mikeoliphant/neural-amp-modeler-lv2"
REF = "lv2:" + URI
MODEL_PROPERTY = URI + "#model"
BUNDLE = "neural_amp_modeler.lv2"
# La loudness a cui il plugin porta i profili che la dichiarano
PLUGIN_TARGET_LOUDNESS_DB = -18.0
# Sotto questa durata un pezzo solo (avviare un processo costa piu' del guadagno)
MIN_SEGMENT_SECONDS = 4.0

log = logging.getLogger(__name__)
_disabled_reason = ""


def lv2_dirs() -> List[str]:
    """Le cartelle in cui lilv cerca i plugin LV2 (LV2_PATH, altrimenti
    quelle predefinite del sistema)."""
    env = os.environ.get("LV2_PATH")
    if env:
        return [d for d in env.split(os.pathsep) if d]
    home = os.path.expanduser("~")
    if sys.platform == "win32":
        return [os.path.join(os.environ.get("APPDATA", ""), "LV2"),
                os.path.join(os.environ.get("COMMONPROGRAMFILES", ""), "LV2")]
    if sys.platform == "darwin":
        return [os.path.join(home, "Library", "Audio", "Plug-Ins", "LV2"), "/Library/Audio/Plug-Ins/LV2"]
    return [os.path.join(home, ".lv2"), "/usr/local/lib/lv2", "/usr/lib/lv2"]


def bundle_path() -> str:
    """La cartella del plugin, se e' installato; '' altrimenti."""
    for folder in lv2_dirs():
        path = os.path.join(folder, BUNDLE)
        if os.path.isfile(os.path.join(path, "manifest.ttl")):
            return path
    return ""


def available() -> bool:
    return bool(bundle_path()) and not _disabled_reason


def process(path: str, x: np.ndarray, rate: int, receptive_field: int,
            loudness: Optional[float] = None) -> Optional[np.ndarray]:
    """Il segnale mono x attraverso il profilo 'path' col plugin, stessa
    lunghezza e stesso livello della rete in numpy (loudness: quella
    dichiarata nel profilo, che il plugin normalizza); None se non si puo'
    (plugin assente o in errore): allora calcola core.nam."""
    global _disabled_reason
    if not available() or len(x) == 0:
        return None
    from . import plugins
    from .lv2_host import encode_state
    state = encode_state({MODEL_PROPERTY: os.path.abspath(path)})
    lead = int(receptive_field) + 64
    segments = max(1, min(plugins.NAM_HOSTS, int(len(x) / (MIN_SEGMENT_SECONDS * rate))))
    bounds = np.linspace(0, len(x), segments + 1).astype(int)

    def one(i):
        start, end = int(bounds[i]), int(bounds[i + 1])
        before = x[max(0, start - lead):start]
        piece = np.concatenate([np.zeros(lead - len(before), dtype=np.float32), before, x[start:end]])
        y = plugins.process_audio_on(f"nam{i}", REF, {}, state, np.stack([piece, piece], axis=1), rate)
        return y[lead:lead + (end - start), 0]

    try:
        if segments == 1:
            parts = [one(0)]
        else:
            with ThreadPoolExecutor(max_workers=segments) as pool:
                parts = list(pool.map(one, range(segments)))
    except plugins.PluginError as e:
        # non lo si riprova a ogni traccia: per questa sessione si calcola in numpy
        _disabled_reason = str(e)
        log.warning("Motore NAM veloce non usato (%s): calcolo in numpy", e)
        return None
    y = np.concatenate(parts).astype(np.float32)
    if loudness is not None:
        y *= np.float32(10.0 ** (-(PLUGIN_TARGET_LOUDNESS_DB - loudness) / 20.0))
    if len(y) != len(x) or not np.all(np.isfinite(y)):
        log.warning("Motore NAM veloce: uscita non valida, calcolo in numpy")
        return None
    return y
