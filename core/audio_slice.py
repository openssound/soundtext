"""
Quantizzazione dell'audio: la clip si taglia poco prima di ogni attacco
(colpo, nota) e ogni pezzo si sposta verso la griglia, con la stessa forza,
finestra e swing della quantizzazione delle note (core.audio_quantize.
QuantizeSettings). Il file non cambia: il risultato sono clip normali, una
per pezzo; dove un pezzo spostato finisce sopra il successivo si accorcia
fino a li', con una dissolvenza incrociata breve.
"""

import dataclasses
from typing import List, Optional

import numpy as np

from . import audio_tracks
from .audio_quantize import QuantizeSettings, _quantized_beats
from .beat_track import _attack_time, onset_envelope
from .model import AudioClip, Project

PRE_ATTACK = 0.005          # il taglio cade poco prima dell'attacco
SLICE_CROSSFADE = 0.010
ATTACK_THRESHOLD = 0.2      # frazione del picco dell'inviluppo sopra cui c'e' un attacco


def detect_attacks(samples: np.ndarray, rate: int, min_gap: float = 0.08,
                   threshold: float = ATTACK_THRESHOLD) -> List[float]:
    """Gli istanti (secondi) degli attacchi: i picchi dell'inviluppo degli
    attacchi sopra la soglia, distanti almeno min_gap, rifiniti sul segnale."""
    env, fps = onset_envelope(samples, rate)
    if not env.any():
        return []
    level = threshold * env.max()
    gap = max(1, int(round(min_gap * fps)))
    peaks = [i for i in range(1, len(env) - 1)
             if env[i] >= level and env[i] >= env[i - 1] and env[i] > env[i + 1]]
    chosen: List[int] = []
    for i in sorted(peaks, key=lambda k: -env[k]):         # i piu' forti prima
        if all(abs(i - j) >= gap for j in chosen):
            chosen.append(i)
    from .beat_track import FRAME, HOP
    times = sorted(_attack_time(samples, rate, (i * HOP + FRAME / 2) / rate) for i in chosen)
    out: List[float] = []
    for t in times:                                         # due picchi dello stesso attacco
        if not out or t - out[-1] >= min_gap / 2:
            out.append(t)
    return out


def clip_attacks(clip: AudioClip, min_gap: float = 0.08) -> List[float]:
    """Gli attacchi della clip, in secondi del brano dall'inizio della clip."""
    from .performance_tempo import clip_samples
    samples, rate = clip_samples(clip)
    return detect_attacks(samples, rate, min_gap)


def quantize_clip(project: Project, clip: AudioClip, grid_beats: float, settings: Optional[QuantizeSettings] = None,
                  attacks: Optional[List[float]] = None) -> List[AudioClip]:
    """I pezzi della clip quantizzata (vedi modulo). grid_beats: la
    suddivisione in beat (0.25 = sedicesimi). Senza attacchi, la clip com'e'."""
    from .tempo_map import beat_at_elapsed_seconds, build_tempo_beat_map, seconds_for_beats
    settings = settings or QuantizeSettings()
    tempo_map = build_tempo_beat_map(project)
    if attacks is None:
        min_gap = max(0.03, 0.5 * seconds_for_beats(tempo_map, grid_beats))
        attacks = clip_attacks(clip, min(0.15, min_gap))
    play = audio_tracks.clip_play_seconds(clip)
    attacks = [t for t in attacks if PRE_ATTACK < t < play - audio_tracks.MIN_CLIP_SECONDS]
    if not attacks:
        return [clip]
    stretch = audio_tracks._stretch(clip)
    clip_s = seconds_for_beats(tempo_map, clip.start_beat)
    cuts = [0.0] + [t - PRE_ATTACK for t in attacks] + [play]
    # dove va ogni pezzo: il suo attacco verso la griglia
    starts = [clip_s]                                       # il pezzo prima del primo attacco resta
    for t in attacks:
        beat = beat_at_elapsed_seconds(tempo_map, 0.0, clip_s + t)
        new_beat, _ = _quantized_beats(beat, beat, grid_beats, settings)
        starts.append(seconds_for_beats(tempo_map, max(0.0, new_beat)) - PRE_ATTACK)
    total = audio_tracks.clip_file_seconds(clip)
    pieces = []
    for k in range(len(cuts) - 1):
        a, b = cuts[k], cuts[k + 1]
        start = starts[k]
        end = start + (b - a)
        last = k == len(cuts) - 2
        if not last:
            end = min(end, starts[k + 1] + SLICE_CROSSFADE)  # non sopra il pezzo dopo
        if end - start < audio_tracks.MIN_CLIP_SECONDS:
            continue          # due attacchi sullo stesso punto della griglia: resta il secondo
        if pieces and start < pieces[-1][0]:
            continue          # spostato prima del pezzo precedente
        piece = dataclasses.replace(clip)
        piece.trim_start = round(clip.trim_start + a / stretch, 6)
        piece.trim_end = round(max(0.0, total - (clip.trim_start + (a + (end - start)) / stretch)), 6)
        piece.fade_in = clip.fade_in if k == 0 else 0.0     # all'attacco basta la microdissolvenza
        piece.fade_out = clip.fade_out if last else SLICE_CROSSFADE
        if start < 0:
            piece.trim_start = round(piece.trim_start - start / stretch, 6)
            start = 0.0
        piece.start_beat = round(beat_at_elapsed_seconds(tempo_map, 0.0, start), 6)
        pieces.append((start, piece))
    return [p for _s, p in pieces]
