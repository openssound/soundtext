"""
"Rimuovi i silenzi" di una clip audio: dove il livello resta sotto una
soglia abbastanza a lungo la clip si divide e il pezzo vuoto sparisce. Ogni
pezzo che resta comincia un po' prima del suo attacco (pre_roll) e finisce
un po' dopo che il suono e' sceso sotto la soglia (TAIL), con una
dissolvenza breve ai tagli. Il file non cambia e i pezzi restano dove
suonavano: il risultato sono clip normali, come per la quantizzazione
dell'audio (core.audio_slice).
"""

import dataclasses
from typing import List, Optional, Tuple

import numpy as np

from . import audio_tracks
from .model import AudioClip, Project

THRESHOLD_DB = -45.0
MIN_SILENCE = 0.3           # secondi: un silenzio piu' corto resta nella clip
PRE_ROLL = 0.05             # secondi lasciati prima di ogni attacco
TAIL = 0.05                 # secondi lasciati dopo la fine del suono
EDGE_FADE = 0.01            # dissolvenza ai tagli
LEVEL_HOP = 0.01            # secondi per ogni valore del livello


def clip_levels_db(clip: AudioClip) -> Tuple[np.ndarray, float]:
    """Il livello RMS (dBFS) della parte che suona della clip, un valore
    ogni LEVEL_HOP secondi del brano, e la durata in secondi della parte."""
    from .beat_track import _mono
    from .performance_tempo import clip_samples
    samples, rate = clip_samples(clip)
    mono = _mono(samples).astype(np.float64)
    hop = max(1, int(round(LEVEL_HOP * rate)))
    count = len(mono) // hop
    if count == 0:
        return np.full(0, -120.0), len(mono) / rate
    frames = mono[:count * hop].reshape(count, hop)
    rms = np.sqrt(np.mean(frames * frames, axis=1))
    return 20.0 * np.log10(np.maximum(rms, 1e-6)), len(mono) / rate


def sound_regions(levels_db: np.ndarray, total: float, threshold_db: float = THRESHOLD_DB,
                  min_silence: float = MIN_SILENCE, pre_roll: float = PRE_ROLL,
                  hop: float = LEVEL_HOP) -> List[Tuple[float, float]]:
    """Le parti da tenere, [(inizio, fine)] in secondi dall'inizio della
    clip: tutto tranne i silenzi lunghi almeno min_silence; vuota se la
    clip e' tutta sotto la soglia."""
    loud = np.asarray(levels_db) > threshold_db
    if not loud.any():
        return []
    regions: List[Tuple[float, float]] = []
    start: Optional[int] = None
    quiet_since: Optional[int] = None
    for i, is_loud in enumerate(loud):
        if is_loud:
            if start is None:
                start = i
            quiet_since = None
        elif start is not None:
            if quiet_since is None:
                quiet_since = i
            if (i + 1 - quiet_since) * hop >= min_silence:
                regions.append((start, quiet_since))
                start, quiet_since = None, None
    if start is not None:
        regions.append((start, quiet_since if quiet_since is not None else len(loud)))
    # il primo silenzio e l'ultimo si tolgono solo se abbastanza lunghi
    if regions[0][0] * hop < min_silence:
        regions[0] = (0, regions[0][1])
    if total - regions[-1][1] * hop < min_silence:
        regions[-1] = (regions[-1][0], None)
    kept: List[Tuple[float, float]] = []
    for a, b in regions:
        a = 0.0 if a == 0 else max(0.0, a * hop - pre_roll)
        b = total if b is None else min(total, b * hop + TAIL)
        if kept and a <= kept[-1][1]:
            kept[-1] = (kept[-1][0], b)
        else:
            kept.append((a, b))
    return [(a, b) for a, b in kept if b - a >= audio_tracks.MIN_CLIP_SECONDS]


def remove_silences(project: Project, clip: AudioClip, regions: List[Tuple[float, float]]) -> List[AudioClip]:
    """I pezzi della clip che restano (vedi sound_regions), ciascuno nel
    punto del brano in cui suonava; la clip com'e' se non c'e' niente da
    togliere o se e' tutta silenzio."""
    from .tempo_map import beat_at_elapsed_seconds, build_tempo_beat_map, seconds_for_beats
    play = audio_tracks.clip_play_seconds(clip)
    if not regions or (len(regions) == 1 and regions[0][0] <= 0.0 and regions[0][1] >= play - 1e-6):
        return [clip]
    tempo_map = build_tempo_beat_map(project)
    clip_s = seconds_for_beats(tempo_map, clip.start_beat)
    stretch = audio_tracks._stretch(clip)
    total = audio_tracks.clip_file_seconds(clip)
    pieces = []
    for a, b in regions:
        piece = dataclasses.replace(clip)
        piece.trim_start = round(clip.trim_start + a / stretch, 6)
        piece.trim_end = round(max(0.0, total - (clip.trim_start + b / stretch)), 6)
        piece.fade_in = clip.fade_in if a <= 0.0 else EDGE_FADE
        piece.fade_out = clip.fade_out if b >= play - 1e-6 else EDGE_FADE
        piece.start_beat = round(beat_at_elapsed_seconds(tempo_map, 0.0, clip_s + a), 6)
        pieces.append(piece)
    return pieces
