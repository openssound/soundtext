"""
Da traccia audio a notazione, per tutta la traccia invece che per una clip
alla volta:

- convert_audio_track: ogni clip udibile (con i suoi tagli e le sue
  dissolvenze, le clip silenziate no) passa per lo stesso motore di "Importa
  audio" (core.audio_import.convert_audio_to_track_text) con le stesse
  opzioni, e diventa un box alla posizione della clip, con il suo nome;
- extract_chords_from_audio_track: gli accordi della traccia audio come
  core.rhythm_generate.ChordSpan, gli stessi che extract_chords_from_track
  ricava da una traccia di note, cosi' basso, accompagnamento e melodia
  possono seguire una ripresa (vedi AudioChordSource).

L'analisi degli accordi di una clip resta in memoria (chiave: file, tagli,
dissolvenze, tempo e metrica): riaprire un generatore non rianalizza niente.
"""

import os
import tempfile
import threading
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from . import audio_tracks
from .audio_quantize import QuantizeSettings
from .model import AudioClip, Clip, Project, Track


@dataclass
class ConversionOptions:
    """Le scelte del dialogo, uguali per tutte le clip (vedi
    convert_audio_to_track_text per il significato di ciascuna)."""
    mode: str = "melody"            # "melody", "drums" o "chords"
    grid_denominator: int = 16
    ternary: bool = False
    sevenths: bool = False
    voice_source: bool = False
    min_freq_hz: Optional[float] = None
    buf_size: Optional[int] = None
    hop_size: Optional[int] = None
    pitch_confidence_threshold: Optional[float] = None
    min_note_duration_sec: Optional[float] = None
    quantize: Optional[QuantizeSettings] = None   # forza, finestra, swing, pulizia


def _beats_per_bar(time_sig: str) -> float:
    try:
        num, den = (int(x) for x in str(time_sig).split("/"))
        return 4.0 * num / den
    except (ValueError, ZeroDivisionError):
        return 4.0


def audible_clips(track: Track) -> List[AudioClip]:
    """Le clip che suonano (non silenziate, con il file presente), in ordine."""
    return sorted((c for c in track.audio_clips if not c.muted and audio_tracks.clip_play_seconds(c) > 0),
                  key=lambda c: c.start_beat)


def _clip_beat_mapper(project: Project, clip: AudioClip):
    """Con un tempo che cambia nel brano (cambi di tempo per battuta, per
    esempio ricavati dalla ripresa, vedi core.performance_tempo): il beat,
    contato dall'inizio della clip, di un istante della clip. None a tempo
    fisso (basta il BPM)."""
    if not project.tempo_changes:
        return None
    from .tempo_map import beat_at_elapsed_seconds, build_tempo_beat_map, seconds_for_beats
    tempo_map = build_tempo_beat_map(project)
    start = seconds_for_beats(tempo_map, clip.start_beat)
    return lambda t: beat_at_elapsed_seconds(tempo_map, 0.0, start + t) - clip.start_beat


def _convert_clip(project: Project, clip: AudioClip, options: ConversionOptions, default_octave: int,
                  progress: Optional[Callable[[float], None]] = None) -> Optional[str]:
    """Il testo di notazione della parte udibile della clip; None se e' muta."""
    from .audio_import import SilentAudio, convert_audio_to_track_text
    fd, tmp = tempfile.mkstemp(suffix=".wav", prefix="soundtext_clip_")
    os.close(fd)
    try:
        audio_tracks.extract_clip_audio(clip, tmp)
        try:
            text = convert_audio_to_track_text(
                tmp, options.mode == "drums", project.tempo_bpm, options.grid_denominator, options.ternary,
                project.patterns, default_octave, min_freq_hz=options.min_freq_hz,
                voice_source=options.voice_source and options.mode != "chords",
                buf_size=options.buf_size, hop_size=options.hop_size,
                pitch_confidence_threshold=options.pitch_confidence_threshold,
                min_note_duration_sec=options.min_note_duration_sec,
                chords=options.mode == "chords", sevenths=options.mode == "chords" and options.sevenths,
                beats_per_bar=_beats_per_bar(project.time_sig), progress_callback=progress,
                quantize=options.quantize, beats_of_seconds=_clip_beat_mapper(project, clip),
            )
        except SilentAudio:
            return None
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return text if text and text.strip() else None


def convert_audio_track(project: Project, track: Track, options: ConversionOptions, default_octave: int,
                        progress_callback: Optional[Callable[[float], None]] = None
                        ) -> Tuple[List[Clip], List[str]]:
    """([box, uno per clip udibile, alla posizione della clip e con il suo
    nome], [nomi delle clip mute, saltate]). Il progress_callback puo'
    sollevare core.audio_import.ConversionCancelled per interrompere."""
    clips = audible_clips(track)
    boxes, silent = [], []
    for i, clip in enumerate(clips):
        def progress(frac, i=i):
            if progress_callback:
                progress_callback((i + max(0.0, min(1.0, frac))) / len(clips))
        text = _convert_clip(project, clip, options, default_octave, progress)
        if text is None:
            silent.append(clip.name)
        else:
            boxes.append(Clip(name=clip.name, text=text, start_beat=clip.start_beat))
    if progress_callback:
        progress_callback(1.0)
    return boxes, silent


# ---------------------------------------------------------------------------
# Accordi di una traccia audio
# ---------------------------------------------------------------------------

_chords_cache: Dict[tuple, Optional[str]] = {}
_chords_lock = threading.Lock()
_CHORDS_CACHE_MAX = 64


def _chord_key(project: Project, clip: AudioClip) -> Optional[tuple]:
    file_key = audio_tracks._file_key(clip.file)
    if file_key is None:
        return None
    return (file_key, round(clip.trim_start, 6), round(clip.trim_end, 6), round(clip.fade_in, 6),
            round(clip.fade_out, 6), clip.fade_shape, project.tempo_bpm, project.time_sig)


def clip_chord_text(project: Project, clip: AudioClip) -> Optional[str]:
    """Gli accordi della clip in notazione ("4: 4C | 2Am 2G"), con l'inizio
    della clip a 0; None se la clip e' muta o il file manca. In cache."""
    key = _chord_key(project, clip)
    if key is None:
        return None
    with _chords_lock:
        if key in _chords_cache:
            return _chords_cache[key]
    text = _convert_clip(project, clip, ConversionOptions(mode="chords"), 4)
    with _chords_lock:
        while len(_chords_cache) >= _CHORDS_CACHE_MAX:
            _chords_cache.pop(next(iter(_chords_cache)))
        _chords_cache[key] = text
    return text


def chords_are_cached(project: Project, track: Track) -> bool:
    """Vero se gli accordi di tutte le clip udibili sono gia' in memoria
    (estrarli non costa niente: il dialogo non deve avvisare dell'attesa)."""
    with _chords_lock:
        return all(_chord_key(project, c) in _chords_cache for c in audible_clips(track))


def extract_chords_from_audio_track(project: Project, track: Track) -> list:
    """Gli accordi della traccia audio come [ChordSpan] (vedi
    core.rhythm_generate.extract_chords_from_track), ciascuno spostato alla
    posizione della sua clip; dove non ci sono clip, nessun accordo."""
    from .rhythm_generate import extract_chords_from_track
    spans = []
    for clip in audible_clips(track):
        text = clip_chord_text(project, clip)
        if not text:
            continue
        for span in extract_chords_from_track(text, project.patterns):
            spans.append(span._replace(start_beat=span.start_beat + clip.start_beat))
    spans.sort(key=lambda s: s.start_beat)
    return spans


def audio_track_chord_text(project: Project, track: Track) -> str:
    """Gli accordi di tutte le clip uno dopo l'altro (per stimarne la
    tonalita', vedi core.key_detect.detect_key_of_text): le posizioni non
    contano."""
    texts = [clip_chord_text(project, c) for c in audible_clips(track)]
    return " ".join(t for t in texts if t)


class AudioChordSource:
    """Una traccia audio come sorgente di accordi per i generatori (basso,
    accompagnamento, melodia), accanto alle tracce di note che invece
    passano il loro testo: l'analisi si fa solo quando serve."""

    def __init__(self, project: Project, track: Track):
        self.project = project
        self.track = track

    @property
    def name(self) -> str:
        return self.track.name

    def is_ready(self) -> bool:
        return chords_are_cached(self.project, self.track)

    def chords(self) -> list:
        return extract_chords_from_audio_track(self.project, self.track)

    def text(self) -> str:
        return audio_track_chord_text(self.project, self.track)


def audio_tracks_with_clips(project: Project, exclude_track_name: Optional[str] = None) -> List[Track]:
    """Le tracce audio con almeno una clip udibile: possono dare accordi."""
    return [t for t in project.tracks
            if t.is_audio and t.name != exclude_track_name and audible_clips(t)]
