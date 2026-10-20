"""
Riprese multiple di una clip audio (AudioClip.takes) e comping.

Una clip con piu' riprese suona sempre la sua ripresa attiva, che e' quella
in AudioClip.file: tutto il resto del programma (mix, forma d'onda, tagli,
divisione) non deve sapere che ce ne sono altre. Le riprese sono allineate
nel tempo dal loro 'delta' rispetto all'attiva (vedi core.model.AudioTake),
che non cambia tagliando, dividendo o spostando il contenuto della clip:
cambia solo scegliendo un'altra ripresa (set_active_take).

Il comping (comp_clip) divide la clip nei tratti scelti, ciascuno con la sua
ripresa attiva, e mette una dissolvenza incrociata di COMP_CROSSFADE secondi
in ogni punto di cambio. Ogni tratto tiene tutte le riprese: lo si puo'
rifare.
"""

import dataclasses
from typing import List, Optional, Sequence, Tuple

from . import audio_tracks
from .model import AudioClip, AudioTake

COMP_CROSSFADE = 0.010


def has_takes(clip: AudioClip) -> bool:
    return len(clip.takes) > 1


def _ensure_takes(clip: AudioClip) -> None:
    """Una clip senza riprese diventa la ripresa 1 di se stessa."""
    if not clip.takes:
        clip.takes = [AudioTake(clip.name, clip.file, 0.0)]
        clip.active_take = 0


def add_take(clip: AudioClip, name: str, file: str, file_seconds_at_clip_start: float,
             make_active: bool = True) -> int:
    """Aggiunge una ripresa: file_seconds_at_clip_start e' il punto del suo
    file che suona all'inizio (attuale) della clip. Ritorna il suo indice."""
    _ensure_takes(clip)
    delta = file_seconds_at_clip_start - clip.trim_start
    clip.takes = clip.takes + [AudioTake(name, file, round(delta, 6))]
    index = len(clip.takes) - 1
    if make_active:
        set_active_take(clip, index)
    return index


def set_active_take(clip: AudioClip, index: int) -> None:
    """Fa suonare la ripresa 'index' nello stesso tratto di tempo: stessi
    inizio e durata della clip, se il file della ripresa li copre."""
    if not clip.takes or not 0 <= index < len(clip.takes) or index == clip.active_take:
        return
    take = clip.takes[index]
    play = audio_tracks.clip_play_seconds(clip)
    trim_start = clip.trim_start + take.delta
    clip.file = take.file
    clip.trim_start = round(max(0.0, trim_start), 6)
    total = audio_tracks.clip_file_seconds(clip)
    if total > 0:
        clip.trim_end = round(max(0.0, total - clip.trim_start - play / audio_tracks._stretch(clip)), 6)
    clip.takes = [dataclasses.replace(t, delta=round(t.delta - take.delta, 6)) for t in clip.takes]
    clip.active_take = index


def keep_only_active_take(clip: AudioClip) -> None:
    clip.takes = []
    clip.active_take = 0


def next_take_name(clip: AudioClip, base: str = "Ripresa") -> str:
    names = {t.name for t in clip.takes} | {clip.name}
    n = max(2, len(clip.takes) + 1)
    while f"{base} {n}" in names:
        n += 1
    return f"{base} {n}"


def comp_clip(clip: AudioClip, segments: Sequence[Tuple[float, float, int]], tempo_map,
              crossfade: float = COMP_CROSSFADE) -> List[AudioClip]:
    """Le clip del comping: segments [(inizio, fine, ripresa)] in beat, in
    ordine e contigui, dentro la clip. Ogni tratto e' una copia della clip
    con quella ripresa attiva, tagliata al tratto; nei punti di cambio i due
    tratti si sovrappongono di 'crossfade' secondi, con le dissolvenze.
    Due tratti vicini con la stessa ripresa diventano uno solo."""
    from .tempo_map import beat_at_elapsed_seconds, seconds_for_beats
    merged: List[List] = []
    for start, end, take in segments:
        if end - start <= 1e-9:
            continue
        if merged and merged[-1][2] == take and abs(merged[-1][1] - start) < 1e-9:
            merged[-1][1] = end
        else:
            merged.append([start, end, take])
    clip_start_s = seconds_for_beats(tempo_map, clip.start_beat)
    half = crossfade / 2
    out = []
    for i, (start, end, take) in enumerate(merged):
        part = dataclasses.replace(clip)
        set_active_take(part, take)
        play = audio_tracks.clip_play_seconds(part)
        a = seconds_for_beats(tempo_map, start) - clip_start_s
        b = seconds_for_beats(tempo_map, end) - clip_start_s
        first, last = i == 0, i == len(merged) - 1
        stretch = audio_tracks._stretch(part)    # a, b e play in secondi del brano, i tagli del file
        if not first:
            a -= min(half, part.trim_start * stretch + a)   # entra prima, dove la ripresa ha audio
        if not last:
            b = min(play, b + half)
        a, b = max(0.0, a), min(play, b)
        if b - a < audio_tracks.MIN_CLIP_SECONDS:
            continue
        part.trim_start = round(part.trim_start + a / stretch, 6)
        part.trim_end = round(part.trim_end + (play - b) / stretch, 6)
        part.start_beat = round(beat_at_elapsed_seconds(tempo_map, 0.0, clip_start_s + a), 6)
        part.fade_in = clip.fade_in if first else crossfade
        part.fade_out = clip.fade_out if last else crossfade
        if len(merged) > 1:
            part.fade_shape = "equal"        # niente calo di volume a meta' dell'incrocio
        out.append(part)
    return out


def take_waveform(clip: AudioClip, index: int, buckets: int):
    """La forma d'onda della ripresa 'index' nel tratto della clip (per la
    finestra del comping)."""
    probe = dataclasses.replace(clip)
    set_active_take(probe, index)
    probe.fade_in = probe.fade_out = 0.0
    return audio_tracks.waveform_peaks(probe, buckets)


def all_files(clip: AudioClip) -> List[str]:
    """I file usati dalla clip: quello attivo e quelli delle riprese."""
    files = [clip.file] + [t.file for t in clip.takes]
    seen, out = set(), []
    for f in files:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def replace_file(clip: AudioClip, old: str, new: str) -> None:
    """Sostituisce un file (consolidamento nella cartella del progetto,
    Ritrova file) nella clip e nelle sue riprese."""
    if clip.file == old:
        clip.file = new
    if any(t.file == old for t in clip.takes):
        clip.takes = [dataclasses.replace(t, file=new) if t.file == old else t for t in clip.takes]


def find_take_target(clips: Sequence[AudioClip], start_beat: float, end_beat: float,
                     length_of) -> Optional[AudioClip]:
    """La clip su cui una nuova ripresa (start_beat-end_beat) va come
    alternativa: quella con cui si sovrappone di piu', se la sovrapposizione
    copre almeno meta' di una delle due."""
    best, best_overlap = None, 0.0
    for c in clips:
        c_end = c.start_beat + length_of(c)
        overlap = min(end_beat, c_end) - max(start_beat, c.start_beat)
        if overlap > best_overlap:
            best, best_overlap = c, overlap
    if best is None:
        return None
    shortest = min(end_beat - start_beat, length_of(best))
    return best if shortest > 0 and best_overlap >= 0.5 * shortest else None


def add_recording_as_take(track_clips: List[AudioClip], recording: AudioClip, tempo_map) -> Optional[AudioClip]:
    """Mette una nuova ripresa (anche con piu' giri, vedi
    core.audio_recording.loop_clip) come alternativa della clip della
    traccia su cui cade (find_take_target): se la ripresa ne copre solo un
    tratto (punch-in) la clip si divide ai bordi della ripresa e solo quel
    tratto riceve le nuove riprese, attive. Modifica track_clips (nuove
    clip della divisione); ritorna la clip che ha ricevuto le riprese, o
    None se non c'e' una clip su cui metterla (la ripresa va aggiunta a
    parte)."""
    from .tempo_map import seconds_for_beats

    def length_of(c):
        return audio_tracks.clip_duration_beats(c, tempo_map)

    rec_start = recording.start_beat
    rec_end = rec_start + length_of(recording)
    target = find_take_target(track_clips, rec_start, rec_end, length_of)
    if target is None:
        return None
    if rec_start > target.start_beat:
        second = audio_tracks.split_clip(target, rec_start, tempo_map)
        if second is not None:
            track_clips.append(second)
            target = second
    if rec_end < target.start_beat + length_of(target):
        after = audio_tracks.split_clip(target, rec_end, tempo_map)
        if after is not None:
            track_clips.append(after)
    # il punto di ciascuna nuova ripresa che suona all'inizio di target
    shift = seconds_for_beats(tempo_map, target.start_beat) - seconds_for_beats(tempo_map, rec_start)
    takes = recording.takes or [AudioTake(recording.name, recording.file, 0.0)]
    active = recording.active_take if recording.takes else 0
    first_new = None
    for i, take in enumerate(takes):
        name = take.name if take.name not in {t.name for t in target.takes} | {target.name} \
            else next_take_name(target)
        index = add_take(target, name, take.file, recording.trim_start + take.delta + shift, make_active=False)
        if i == active:
            first_new = index
    set_active_take(target, first_new)
    # i bordi della ripresa (le dissolvenze brevi del punch-in) valgono per il tratto
    if recording.fade_in and abs(target.start_beat - rec_start) < 1e-6:
        target.fade_in = max(target.fade_in, recording.fade_in)
    if recording.fade_out and abs(target.start_beat + length_of(target) - rec_end) < 1e-3:
        target.fade_out = max(target.fade_out, recording.fade_out)
    return target


def assign_range(segments: Sequence[Tuple[float, float, int]], start: float, end: float,
                 take: int) -> List[Tuple[float, float, int]]:
    """Il comping dopo aver scelto 'take' per il tratto start-end (in beat):
    segments [(inizio, fine, ripresa)] contigui; i tratti vicini con la
    stessa ripresa si uniscono."""
    if end < start:
        start, end = end, start
    lo, hi = segments[0][0], segments[-1][1]
    start, end = max(lo, start), min(hi, end)
    if end - start <= 1e-9:
        return list(segments)
    out: List[List] = []
    for a, b, t in segments:
        for piece in ((a, min(b, start), t), (max(a, end), b, t)):
            if piece[1] - piece[0] > 1e-9:
                out.append(list(piece))
    out.append([start, end, take])
    out.sort()
    merged: List[List] = []
    for a, b, t in out:
        if merged and merged[-1][2] == t and abs(merged[-1][1] - a) < 1e-9:
            merged[-1][1] = b
        else:
            merged.append([a, b, t])
    return [tuple(m) for m in merged]
