"""
Conversione delle tracce a testo libero in box (vista Struttura brano): lo
stesso taglio usato dopo un import (vedi core.arrangement.
split_text_into_box_segments: un box nuovo dove una pausa supera
GAP_SPLIT_THRESHOLD_BEATS, allineato all'inizio della battuta).

convert_project_to_boxes controlla anche, traccia per traccia, che il brano
suoni ESATTAMENTE come prima (stessi messaggi MIDI agli stessi tick): una
traccia che cambierebbe anche di poco resta com'era.
"""

import os
import tempfile
from typing import List, Tuple

import mido

from .arrangement import flatten_clips_to_text, split_text_into_box_segments
from .model import Clip, Project, Track


def split_track_into_boxes(project: Project, track: Track) -> None:
    """Racchiude il testo di 'track' in uno o piu' box (track.clips) e
    rigenera track.text dai box. Una traccia vuota resta senza box."""
    if not track.text.strip():
        return
    meter = project.meter()
    octave = track.instrument.default_octave
    segments = split_text_into_box_segments(track.text, project.patterns, octave, meter=meter)
    if len(segments) <= 1:
        # Il segmento non ha le pause iniziali: il box comincia dove
        # comincia lui, non a 0 (altrimenti una parte che entra a meta'
        # brano suonerebbe dall'inizio).
        track.clips = [Clip(name=track.name, text=(segments[0][1] if segments else track.text),
                            start_beat=(segments[0][0] if segments else 0.0))]
    else:
        track.clips = [Clip(name=f"{track.name} {i + 1}", text=seg_text, start_beat=start_beat)
                       for i, (start_beat, seg_text) in enumerate(segments)]
    track.text = flatten_clips_to_text(track.clips, project.patterns, octave, meter=meter)


def _midi_signature(project: Project, track: Track):
    """I messaggi MIDI (tick assoluto, messaggio) della sola traccia, senza
    ordine fra quelli allo stesso tick: cio' che si sente."""
    from .midi_export import export_project_to_midi
    fd, path = tempfile.mkstemp(suffix=".mid", prefix="soundtext_boxes_")
    os.close(fd)
    try:
        export_project_to_midi(project, path, only_audible=False, tracks=[track])
        events = []
        for i, mtrack in enumerate(mido.MidiFile(path).tracks):
            tick = 0
            for msg in mtrack:
                tick += msg.time
                if msg.type != "end_of_track":
                    events.append((i, tick, str(msg.copy(time=0))))
        return sorted(events)
    finally:
        os.remove(path)


def convertible_tracks(project: Project) -> List[Track]:
    """Le tracce di notazione con del testo ma ancora senza box."""
    return [t for t in project.tracks if not t.is_audio and not t.clips and t.text.strip()]


def convert_project_to_boxes(project: Project) -> Tuple[List[str], List[str]]:
    """Converte in box ogni traccia di convertible_tracks. Ritorna (tracce
    convertite, tracce lasciate com'erano perche' avrebbero suonato
    diverse o la conversione non e' riuscita)."""
    converted, kept = [], []
    for track in convertible_tracks(project):
        text = track.text
        try:
            before = _midi_signature(project, track)
        except Exception:
            kept.append(track.name)
            continue
        # Prima divisa dove ci sono pause lunghe; se cosi' cambierebbe (es. un
        # vol=/ccN= o una rampa nella pausa fra due box), un box solo con
        # tutto il testo.
        for convert in (split_track_into_boxes, _single_box):
            try:
                convert(project, track)
                if _midi_signature(project, track) == before:
                    converted.append(track.name)
                    break
            except Exception:
                pass
            track.text, track.clips = text, []
        else:
            kept.append(track.name)
    return converted, kept


def _single_box(project: Project, track: Track) -> None:
    """Tutto il testo della traccia in un box solo, dall'inizio del brano."""
    track.clips = [Clip(name=track.name, text=track.text.strip(), start_beat=0.0)]
    track.text = flatten_clips_to_text(track.clips, project.patterns, track.instrument.default_octave,
                                       meter=project.meter())
