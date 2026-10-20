"""
Il groove di una ripresa: per ogni sedicesimo della battuta, quanto spesso
e quanto forte c'e' un attacco (core.audio_slice), sulle battute del brano
(mappa del tempo compresa, vedi core.performance_tempo). Serve alla
batteria che segue la ripresa (core.rhythm_generate.generate_drum_pattern,
kick_accents): la cassa va sugli accenti forti e ricorrenti.
"""

import bisect
import threading
from typing import Dict, List, Optional

from . import audio_tracks
from .model import Project, Track

SLOTS_PER_QUARTER = 4
_cache: Dict[tuple, Optional[List[float]]] = {}
_lock = threading.Lock()


def _key(project: Project, track: Track) -> tuple:
    from .audio_track_notation import audible_clips
    clips = tuple((audio_tracks._file_key(c.file), c.start_beat, c.trim_start, c.trim_end, c.stretch)
                  for c in audible_clips(track))
    return (clips, project.tempo_bpm, tuple(project.tempo_changes), project.time_sig,
            tuple(project.metrica_changes), float(project.pickup or 0.0))


def groove_of_track(project: Project, track: Track) -> Optional[List[float]]:
    """[peso 0-1 per sedicesimo della battuta] della traccia audio: la
    frequenza (in quante battute c'e' un attacco li') per la forza media.
    None se non ci sono attacchi. In cache finche' clip e tempo non cambiano."""
    key = _key(project, track)
    with _lock:
        if key in _cache:
            return _cache[key]
    result = _compute(project, track)
    with _lock:
        if len(_cache) > 16:
            _cache.clear()
        _cache[key] = result
    return result


def is_cached(project: Project, track: Track) -> bool:
    with _lock:
        return _key(project, track) in _cache


def _compute(project: Project, track: Track) -> Optional[List[float]]:
    from .audio_slice import detect_attack_strengths
    from .audio_track_notation import audible_clips
    from .performance_tempo import bar_starts, clip_samples
    from .tempo_map import beat_at_elapsed_seconds, build_tempo_beat_map, seconds_for_beats
    tempo_map = build_tempo_beat_map(project)
    clips = audible_clips(track)
    end = max(c.start_beat + audio_tracks.clip_duration_beats(c, tempo_map) for c in clips) if clips else 0.0
    starts = bar_starts(project, end + 8.0)               # una volta sola per tutti gli attacchi
    bar_quarters = starts[1] - starts[0] or 4.0
    slots = max(1, int(round(bar_quarters * SLOTS_PER_QUARTER)))
    hits: Dict[int, Dict[int, float]] = {}          # battuta -> {sedicesimo: forza}
    for clip in clips:
        samples, rate = clip_samples(clip)
        start = seconds_for_beats(tempo_map, clip.start_beat)
        for t, strength in detect_attack_strengths(samples, rate, min_gap=0.06):
            beat = beat_at_elapsed_seconds(tempo_map, 0.0, start + t)
            bar = max(0, bisect.bisect_right(starts, beat + 1e-9) - 1)   # la battuta che lo contiene (da 0)
            pos = beat - starts[bar]
            slot = int(round(pos * SLOTS_PER_QUARTER))
            if slot >= slots:
                bar, slot = bar + 1, 0
            row = hits.setdefault(bar, {})
            row[slot] = max(row.get(slot, 0.0), strength)
    if not hits:
        return None
    bars = len(hits)
    weights = [0.0] * slots
    for row in hits.values():
        for slot, strength in row.items():
            weights[slot] += strength / bars
    top = max(weights)
    return [w / top for w in weights] if top > 0 else None
