"""
Congela in audio: una traccia pesante da calcolare (note col SoundFont o
con uno strumento plugin, effetti, NAM) diventa una clip audio, renderizzata
una volta sola come si sente in Solo (volume, pan ed effetti compresi, senza
il master). La clip va in una traccia audio nuova accanto all'originale;
l'originale resta nel brano, silenziata e segnata come congelata
(Track.frozen), e Scongela la fa tornare com'era togliendo la traccia audio.
Il file WAV resta nella cartella audio del progetto.
"""

from typing import Optional

from .i18n import tr
from .model import AudioClip, Project, Track

TAIL_PAD_SECONDS = 0.05


def frozen_name(project: Project, track: Track) -> str:
    base = tr("{name} (congelata)", name=track.name)
    name, n = base, 2
    while project.find_track(name) is not None:
        name, n = f"{base} {n}", n + 1
    return name


def render_frozen_audio(project: Project, track: Track, dest_dir: str, stop_check=None) -> str:
    """Il WAV (48 kHz, 24 bit) della traccia come si sente in Solo, dall'inizio
    del brano, in dest_dir; ne ritorna il percorso. Si puo' chiamare da un
    thread di sottofondo. Solleva RuntimeError se non c'e' niente da suonare
    o se annullato."""
    from .audio_tracks import unique_audio_path, write_wav
    from .playback import render_project_mix
    import os
    import numpy as np
    mixed, rate = render_project_mix(project, stop_check, tracks=[track])
    # un po' di silenzio in coda: la microdissolvenza di fine clip
    # (audio_tracks.MICRO_FADE_SECONDS) cade li', non sull'ultimo suono
    mixed = np.concatenate([mixed, np.zeros((int(TAIL_PAD_SECONDS * rate), mixed.shape[1]), np.float32)])
    os.makedirs(dest_dir, exist_ok=True)
    path = unique_audio_path(dest_dir, tr("{name} congelata", name=track.name))
    write_wav(path, mixed, rate, bits=24)
    return path


def apply_freeze(project: Project, track: Track, wav_path: str) -> Track:
    """Mette nel brano la traccia audio con il WAV congelato (subito dopo
    l'originale) e congela l'originale. Ritorna la traccia audio."""
    audio = project.add_audio_track(frozen_name(project, track))
    project.tracks.remove(audio)
    project.tracks.insert(project.tracks.index(track) + 1, audio)
    audio.audio_clips.append(AudioClip(name=track.name, file=wav_path, start_beat=0.0))
    audio.solo = track.solo
    track.frozen = audio.name
    track.mute, track.solo = True, False
    return audio


def unfreeze(project: Project, track: Track) -> Optional[str]:
    """Scongela: toglie la traccia audio congelata e la traccia torna a
    suonare. Ritorna il nome della traccia tolta (None se non c'era piu')."""
    audio = project.find_track(track.frozen)
    removed = None
    if audio is not None and audio.is_audio:
        track.solo = audio.solo
        project.remove_track(audio.name)      # remove_track sblocca anche l'originale
        removed = audio.name
    track.frozen, track.mute = "", False
    return removed


def is_frozen(project: Project, track: Track) -> bool:
    return bool(track.frozen) and project.find_track(track.frozen) is not None
