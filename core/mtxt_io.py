"""
Import ed export MTXT (vedi st_language.mtxt).

L'export parte dallo stesso MIDI dell'export dell'app (volume del mixer e
master, umanizzazione, porte oltre le 15 tracce), convertito in righe MTXT.
L'import scrive il testo MTXT come MIDI e lo importa come un MIDI
(quantizzazione, voci, accordi: vedi core.midi_import), con i nomi dei
canali MTXT come nomi delle tracce.
"""

import os
import tempfile
from typing import Dict, List, Tuple

import mido

from st_language.mtxt import midi_tracks_to_mtxt, mtxt_to_midi_tracks
from st_language.midi import write_smf

from .midi_export import export_project_to_midi
from .model import Project


def _midi_file_tracks(path: str) -> List[List[Tuple[int, int, bytes]]]:
    """Le tracce di un file MIDI come [(tick assoluto, ordine, byte)]."""
    mid = mido.MidiFile(path)
    scale = 480 / mid.ticks_per_beat
    tracks = []
    for track in mid.tracks:
        now, events = 0, []
        for order, msg in enumerate(track):
            now += msg.time
            if msg.type == "end_of_track":
                continue
            events.append((round(now * scale), order, bytes(msg.bytes())))
        tracks.append(events)
    return tracks


def project_to_mtxt(project: Project, only_audible: bool = True) -> str:
    handle = tempfile.NamedTemporaryFile(suffix=".mid", delete=False)
    handle.close()
    try:
        export_project_to_midi(project, handle.name, only_audible=only_audible)
        return midi_tracks_to_mtxt(_midi_file_tracks(handle.name), project.key or None)
    finally:
        os.remove(handle.name)


def export_project_to_mtxt(project: Project, path: str, only_audible: bool = True) -> str:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(project_to_mtxt(project, only_audible))
    return path


def import_mtxt_file(path: str, project_name: str = None, recognize_chords: bool = False,
                     min_bend_semitones: float = None) -> Project:
    """Un nuovo progetto da un file MTXT. Solleva ValueError (st_language.
    mtxt.MtxtError) se il file non e' valido."""
    from .midi_import import import_midi_file
    with open(path, encoding="utf-8") as f:
        tracks = mtxt_to_midi_tracks(f.read())
    title = next((m[3:].decode("utf-8", "replace") for _t, _o, m in tracks[0] if m[:2] == b"\xff\x03"), "")
    names: Dict[int, str] = {}
    for events in tracks[1:]:
        name = next((m[3:].decode("utf-8", "replace") for _t, _o, m in events if m[:2] == b"\xff\x03"), None)
        port = next((m[3] for _t, _o, m in events if m[:2] == b"\xff\x21"), 0)
        channel = next((m[0] & 0x0F for _t, _o, m in events if m[0] < 0xF0), None)
        if name and channel is not None:
            names[port * 16 + channel] = name
    handle = tempfile.NamedTemporaryFile(suffix=".mid", delete=False)
    handle.close()
    try:
        write_smf(handle.name, tracks)
        default_name = title if title and title != "MTXT" else os.path.splitext(os.path.basename(path))[0]
        return import_midi_file(handle.name, project_name=project_name or default_name, recognize_chords=recognize_chords, min_bend_semitones=min_bend_semitones,
            channel_names=names)
    finally:
        os.remove(handle.name)
