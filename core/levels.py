"""
Livelli del mix: picco nel tempo e punti in cui clippa.

Il mix arriva alla scheda audio a 16 bit (vedi core.playback): oltre il
fondo scala i campioni si tagliano a +-32767, ed e' li' che il suono si
rompe. analyze_int16 misura proprio quel segnale (quello che si sente):
picco ogni BLOCK_SECONDS e clipping dove almeno CLIP_RUN campioni di fila
stanno al fondo scala (un singolo campione al massimo e' un picco pieno,
non una distorsione). peak_dbfs misura un segnale float (rendering di una
traccia, vedi analyze_track_peaks), che puo' anche superare 0 dBFS.
"""

import bisect
import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

BLOCK_SECONDS = 0.02
CLIP_RUN = 3
FULL_SCALE_INT16 = 32766      # |campione| da qui in su e' fondo scala
SILENCE_DBFS = -90.0


@dataclass
class MixLevels:
    block_seconds: float
    peaks: np.ndarray        # picco di ogni blocco, 0..1 del fondo scala
    clipped: np.ndarray      # True dove il blocco clippa

    def peak_between(self, start_seconds: float, end_seconds: float) -> float:
        """Picco (0..1) fra i due istanti (almeno un blocco)."""
        a = max(0, int(start_seconds / self.block_seconds))
        b = max(a + 1, int(math.ceil(end_seconds / self.block_seconds)))
        chunk = self.peaks[a:b]
        return float(chunk.max()) if len(chunk) else 0.0

    def clipped_between(self, start_seconds: float, end_seconds: float) -> bool:
        a = max(0, int(start_seconds / self.block_seconds))
        b = max(a + 1, int(math.ceil(end_seconds / self.block_seconds)))
        return bool(self.clipped[a:b].any())

    def clip_regions(self) -> List[Tuple[float, float]]:
        """[(inizio, fine)] in secondi dei tratti che clippano, uniti."""
        regions = []
        idx = np.flatnonzero(self.clipped)
        for i in idx:
            start, end = i * self.block_seconds, (i + 1) * self.block_seconds
            if regions and start - regions[-1][1] <= self.block_seconds * 1.5:
                regions[-1] = (regions[-1][0], end)
            else:
                regions.append((start, end))
        return regions

    @property
    def max_peak(self) -> float:
        return float(self.peaks.max()) if len(self.peaks) else 0.0


def analyze_int16(samples: np.ndarray, rate: int) -> MixLevels:
    """Livelli di un mix int16 (frame, canali)."""
    block = max(1, int(round(rate * BLOCK_SECONDS)))
    if samples.ndim == 1:
        samples = samples[:, None]
    n = len(samples)
    n_blocks = (n + block - 1) // block
    if n == 0:
        return MixLevels(block / rate, np.zeros(0, np.float32), np.zeros(0, bool))
    # Senza convertire tutto il mix (decine di milioni di campioni): massimo
    # e minimo per blocco direttamente sugli int16, poi il picco.
    whole = (n // block) * block
    hi = samples[:whole].reshape(-1, block, samples.shape[1]).max(axis=(1, 2)).astype(np.int32)
    lo = samples[:whole].reshape(-1, block, samples.shape[1]).min(axis=(1, 2)).astype(np.int32)
    if whole < n:
        hi = np.append(hi, int(samples[whole:].max()))
        lo = np.append(lo, int(samples[whole:].min()))
    peaks = np.maximum(hi, -lo).astype(np.float32) / 32767.0
    clipped = np.zeros(n_blocks, bool)
    loud = np.flatnonzero(peaks * 32767.0 >= FULL_SCALE_INT16)
    for i in loud:          # solo i blocchi che arrivano al fondo scala
        chunk = samples[max(0, i * block - CLIP_RUN):(i + 1) * block]
        full = (np.abs(chunk.astype(np.int32)) >= FULL_SCALE_INT16).any(axis=1)
        run = full[:len(full) - CLIP_RUN + 1].copy()
        for k in range(1, CLIP_RUN):
            run &= full[k:len(full) - CLIP_RUN + 1 + k]
        clipped[i] = bool(run.any())
    return MixLevels(block / rate, np.minimum(peaks, 1.0), clipped)


def peak_dbfs(samples: np.ndarray) -> float:
    """Picco di un segnale float in dBFS (0 = fondo scala; puo' superarlo)."""
    if samples is None or len(samples) == 0:
        return SILENCE_DBFS
    peak = float(np.max(np.abs(samples)))
    return 20 * math.log10(peak) if peak > 1e-9 else SILENCE_DBFS


def to_dbfs(level: float) -> float:
    return 20 * math.log10(level) if level > 1e-9 else SILENCE_DBFS


def bars_for_seconds(project, tempo_map, seconds_list: List[float]) -> List[int]:
    """Numeri di battuta (come nei controlli di battuta, il levare e' la 0)
    in cui cadono gli istanti dati, senza ripetizioni e in ordine."""
    from .tempo_map import beat_at_elapsed_seconds
    meter = project.meter()
    beats = [beat_at_elapsed_seconds(tempo_map, 0.0, s) for s in seconds_list]
    if not beats:
        return []
    pickup = float(getattr(project, "pickup", 0) or 0)
    starts = [0.0] if pickup > 0 else []
    first_bar = 0 if pickup > 0 else 1
    bar = 1
    while True:
        starts.append(float(meter.start_of(bar)))
        if starts[-1] > max(beats):
            break
        bar += 1
    out = []
    for b in beats:
        n = first_bar + bisect.bisect_right(starts, b + 1e-9) - 1
        if not out or out[-1] != n:
            out.append(n)
    return sorted(set(out))


def format_bars(bars: List[int], limit: int = 12) -> str:
    """'3, 5-7, 12' (intervalli uniti), al massimo 'limit' voci."""
    parts = []
    for b in bars:
        if parts and isinstance(parts[-1], list) and b == parts[-1][1] + 1:
            parts[-1][1] = b
        else:
            parts.append([b, b])
    text = [f"{a}" if a == b else f"{a}-{b}" for a, b in parts]
    return ", ".join(text[:limit]) + (" ..." if len(text) > limit else "")


@dataclass
class TrackPeak:
    peak_db: float            # picco della traccia suonata da sola (dBFS)
    clip_bars: List[int]      # battute in cui clippa anche da sola


@dataclass
class LevelReport:
    tracks: "dict"            # nome traccia -> TrackPeak
    master_peak_db: float
    master_clip_bars: List[int]
    master_clip_seconds: float


def _float_clip_seconds(samples: np.ndarray, rate: int) -> List[float]:
    """Inizi (secondi) dei tratti di un segnale float che arrivano al fondo
    scala per CLIP_RUN campioni di fila (sintesi a 16 bit: oltre si taglia)."""
    if len(samples) == 0:
        return []
    levels = analyze_int16((np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16), rate)
    return [start for start, _end in levels.clip_regions()]


def analyze_project_levels(project, stop_check=None, progress_callback=None) -> LevelReport:
    """Picco di ogni traccia udibile suonata da sola (stessi suoni, guadagno
    e catena di effetti della riproduzione, senza il master) e del mix
    completo, con le battute in cui clippano. Una sintesi per traccia piu'
    una per il mix: richiede tempo, si lancia su richiesta (Analizza livelli)."""
    from .playback import render_project_mix
    from .tempo_map import build_tempo_beat_map
    stop_check = stop_check or (lambda: False)
    tracks = [t for t in project.audible_tracks() if t.is_audio or t.text.strip()]
    tempo_map = build_tempo_beat_map(project)
    steps = len(tracks) + 1
    results = {}
    for i, track in enumerate(tracks):
        if progress_callback:
            progress_callback(i / steps)
        mixed, rate = render_project_mix(project, stop_check, tracks=[track], allow_empty=True, master=False)
        bars = bars_for_seconds(project, tempo_map, _float_clip_seconds(mixed, rate))
        results[track.name] = TrackPeak(peak_dbfs(mixed), bars)
    if progress_callback:
        progress_callback(len(tracks) / steps)
    mixed, rate = render_project_mix(project, stop_check, allow_empty=True)
    levels = analyze_int16((np.clip(mixed, -1.0, 1.0) * 32767).astype(np.int16), rate)
    starts = [start for start, _end in levels.clip_regions()]
    if progress_callback:
        progress_callback(1.0)
    return LevelReport(results, peak_dbfs(mixed), bars_for_seconds(project, tempo_map, starts),
                       float(levels.clipped.sum() * levels.block_seconds))


def block_peaks(channels_first: np.ndarray, rate: int) -> np.ndarray:
    """Picco (float, puo' superare 1) di ogni blocco da BLOCK_SECONDS di un
    segnale (canali, frame)."""
    block = max(1, int(round(rate * BLOCK_SECONDS)))
    mag = np.abs(channels_first).max(axis=0) if channels_first.ndim == 2 else np.abs(channels_first)
    n = len(mag)
    whole = (n // block) * block
    peaks = mag[:whole].reshape(-1, block).max(axis=1) if whole else np.zeros(0, np.float32)
    if whole < n:
        peaks = np.append(peaks, mag[whole:].max())
    return peaks.astype(np.float32)


def merge_peaks(target: dict, key, peaks: np.ndarray, offset_blocks: int = 0):
    """target[key] = massimo blocco per blocco fra quello che c'era e peaks
    (spostati di offset_blocks), allungando dove serve."""
    if offset_blocks > 0:
        peaks = np.concatenate([np.zeros(offset_blocks, np.float32), peaks])
    elif offset_blocks < 0:
        peaks = peaks[-offset_blocks:]
    old = target.get(key)
    if old is None:
        target[key] = peaks
        return
    if len(old) < len(peaks):
        old = np.concatenate([old, np.zeros(len(peaks) - len(old), np.float32)])
    old[:len(peaks)] = np.maximum(old[:len(peaks)], peaks)
    target[key] = old


@dataclass
class TrackLevels:
    """Picco nel tempo di ogni traccia del rendering che si sta ascoltando
    (vedi core.playback): float per blocchi da BLOCK_SECONDS, oltre 1 se la
    traccia da sola supera il fondo scala. Le tracce MIDI sono misurate
    asciutte (riverbero e chorus del synth sono in comune); piu' tracce di
    batteria condividono il canale 10, e quindi il livello."""
    block_seconds: float
    peaks: dict              # nome traccia -> np.ndarray

    def level(self, track_name: str, start_seconds: float, end_seconds: float) -> Optional[float]:
        arr = self.peaks.get(track_name)
        if arr is None:
            return None
        a = max(0, int(start_seconds / self.block_seconds))
        b = max(a + 1, int(math.ceil(end_seconds / self.block_seconds)))
        chunk = arr[a:b]
        return float(chunk.max()) if len(chunk) else 0.0
