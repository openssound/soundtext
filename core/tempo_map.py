"""
La mappa di tempo e metrica: e' st_language.timing (sta nella libreria
st_language perche' si possa usare anche senza SoundText, vedi
st_language/README.md), con gli stessi nomi, cosi' il resto del programma
continua a importarla da qui.

Una differenza: in SoundText il tempo e' del brano. I cambi 'tempo=' e le
corone ($fermata) valgono per tutte le tracce da qualunque traccia siano
scritti, anche se quella traccia e' in mute o se si suona (o si esporta)
una traccia sola: build_tempo_beat_map e song_fermata_spans li cercano
sempre in tutto il brano. Prima ogni traccia renderizzata da sola restava
al tempo iniziale, fuori tempo rispetto alle altre.
"""

from typing import List, Optional, Tuple

from . import _st  # noqa: F401  (traduzioni e libreria MIDI per la notazione)
from st_language import timing as _library

globals().update({k: v for k, v in vars(_library).items() if not k.startswith("__")})


def _tracks_with(project, marker: str) -> list:
    """Le tracce (anche in mute) che possono contenere 'marker' nel testo,
    anche dentro un pattern: leggere le note di tutte le tracce a ogni
    calcolo costerebbe decimi di secondo, e quasi mai ce ne sono."""
    in_patterns = any(marker in tok for pat in project.patterns.values() for tok in pat.tokens)
    return [t for t in project.tracks
            if not getattr(t, "is_audio", False) and (marker in t.text or (in_patterns and "%" in t.text))]


def _events(project, tracks, events_by_track, midi_dir) -> dict:
    """Gli eventi delle tracce, riusando quelli gia' letti dal chiamante."""
    known = events_by_track or {}
    return {t.name: (known[t.name] if t.name in known
                     else t.parsed_events(project.patterns, midi_dir=midi_dir, meter=project.meter()))
            for t in tracks}


def build_tempo_beat_map(project, tracks=None, midi_dir: Optional[str] = None,
                         events_by_track=None) -> List[Tuple[float, int]]:
    """Come st_language.timing.build_tempo_beat_map, ma i marcatori
    'tempo=' vengono da tutte le tracce del brano, anche in mute: 'tracks'
    (le tracce che si stanno suonando) non restringe il tempo, che e' del
    brano; events_by_track evita di rileggere quelle gia' lette."""
    sources = _tracks_with(project, "tempo=")
    return _library.build_tempo_beat_map(project, tracks=sources,
                                         events_by_track=_events(project, sources, events_by_track, midi_dir))


def song_fermata_spans(project, events_by_track=None,
                       midi_dir: Optional[str] = None) -> List[Tuple[float, float]]:
    """Le corone di tutto il brano (vedi fermata_spans): una corona in una
    traccia rallenta tutte le tracce, anche se quella traccia e' in mute."""
    sources = _tracks_with(project, "fermata")
    return _library.fermata_spans(_events(project, sources, events_by_track, midi_dir))


def song_tempo_beat_map_heard(project, events_by_track=None,
                              midi_dir: Optional[str] = None) -> List[Tuple[float, int]]:
    """La mappa del tempo come suona: con le corone del brano."""
    return _library.with_fermatas(build_tempo_beat_map(project, midi_dir=midi_dir, events_by_track=events_by_track),
                                  song_fermata_spans(project, events_by_track, midi_dir))
