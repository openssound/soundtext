"""
La mappa del tempo del brano ricavata da una ripresa suonata libera (vedi
core.beat_track): il brano segue il tempo dell'esecuzione, battuta per
battuta, e la clip si sposta perche' il suo primo battito cada sull'inizio
della battuta scelta. Le note scritte dopo (generatori, conversione della
ripresa in notazione) seguono la stessa mappa.
"""

from typing import Optional, Tuple

import numpy as np

from . import audio_tracks
from .beat_track import BeatAnalysis, analyze_beats, tempo_changes_for
from .model import AudioClip, Project


def bar_start_beat(project: Project, bar: int) -> float:
    """Il beat (quarti) in cui comincia la battuta 'bar' (da 1)."""
    from .tempo_map import compute_bar_beat_offsets
    offsets = compute_bar_beat_offsets(list(project.tempo_changes) + [(max(1, bar), 0)], project.metrica_changes,
                                       project.time_sig, float(project.pickup or 0.0))
    return offsets.get(max(1, bar), 0.0)


def bar_at_beat(project: Project, beat: float) -> int:
    """La battuta (da 1) che comincia piu' vicino a 'beat'."""
    bar = 1
    while bar_start_beat(project, bar + 1) <= beat:
        bar += 1
    nxt = bar_start_beat(project, bar + 1)
    return bar + 1 if nxt - beat < beat - bar_start_beat(project, bar) else bar


def time_sig_at_bar(project: Project, bar: int) -> str:
    sig = project.time_sig or "4/4"
    for b, value in sorted(project.metrica_changes):
        if b <= bar:
            sig = value
    return sig


def clip_samples(clip: AudioClip) -> Tuple[np.ndarray, int]:
    """La parte che suona della clip (senza dissolvenze)."""
    samples, rate = audio_tracks.read_wav(clip.file)
    first = int(round(max(0.0, clip.trim_start) * rate))
    last = len(samples) - int(round(max(0.0, clip.trim_end) * rate))
    return samples[first:max(first, last)], rate


def analyze_clip(project: Project, clip: AudioClip, first_bar: Optional[int] = None) -> BeatAnalysis:
    bar = first_bar or suggested_first_bar(project, clip, None)
    samples, rate = clip_samples(clip)
    return analyze_beats(samples, rate, time_sig_at_bar(project, bar))


def suggested_first_bar(project: Project, clip: AudioClip, analysis: Optional[BeatAnalysis]) -> int:
    """La battuta piu' vicina al punto in cui oggi cade il primo battito."""
    from .tempo_map import beat_at_elapsed_seconds, build_tempo_beat_map, seconds_for_beats
    tempo_map = build_tempo_beat_map(project)
    first = analysis.first_beat if analysis is not None else 0.0
    beat = beat_at_elapsed_seconds(tempo_map, 0.0, seconds_for_beats(tempo_map, clip.start_beat) + first)
    return bar_at_beat(project, beat)


def apply_performance_tempo(project: Project, clip: AudioClip, analysis: BeatAnalysis, first_bar: int) -> int:
    """Il brano prende il tempo della ripresa dalla battuta first_bar per
    tante battute quante ne ha l'analisi; dopo torna il tempo che c'era. La
    clip si sposta perche' il primo battito cada sull'inizio di first_bar.
    Ritorna quante battute hanno avuto il loro tempo."""
    from .tempo_map import beat_at_elapsed_seconds, build_tempo_beat_map, seconds_for_beats, value_at_beat
    if not analysis.bar_tempos:
        return 0
    before = build_tempo_beat_map(project)
    after_bar = first_bar + analysis.bars
    tempo_after = value_at_beat(before, bar_start_beat(project, after_bar)) or project.tempo_bpm
    if not project.tempo_changes:
        project.tempo_changes = [(1, project.tempo_bpm)]
    project.tempo_changes = tempo_changes_for(analysis, first_bar, project.tempo_changes, tempo_after)
    project.tempo_bpm = next((v for b, v in project.tempo_changes if b == 1), project.tempo_bpm)
    if [b for b, _v in project.tempo_changes] == [1]:
        project.tempo_changes = []              # un tempo solo: niente lista
    tempo_map = build_tempo_beat_map(project)
    start_s = seconds_for_beats(tempo_map, bar_start_beat(project, first_bar)) - analysis.first_beat
    if start_s < 0:
        clip.trim_start = round(clip.trim_start - start_s, 6)    # la parte prima dell'inizio del brano
        start_s = 0.0
    clip.start_beat = round(beat_at_elapsed_seconds(tempo_map, 0.0, start_s), 6)
    return analysis.bars
