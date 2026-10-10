"""
Importazione da file MIDI standard con conversione automatica nella
notazione testuale interna (vedi sezione 2 delle specifiche).

Ogni canale MIDI diventa una traccia; lo strumento viene riconosciuto
guardando l'ultimo Program Change ricevuto su quel canale. Se nessuno
strumento disponibile (predefinito o personalizzato) ha esattamente quel
Program Change GM, ne viene registrato automaticamente uno nuovo (invece
di limitarsi al piu' vicino approssimato), cosi' la traccia importata usa
sempre lo strumento corretto. Un canale che cambia strumento a meta'
brano (Program Change fra le note) diventa una traccia per strumento. Il canale 10 (percussioni) viene sempre
riconosciuto come Drums. Le note sovrapposte di un canale diventano voci
della stessa traccia (blocchi { ; }), il testo cantato (eventi lyrics,
anche dei file karaoke) testo fra virgolette sulla prima voce.
"""

import bisect
import logging
import math

from .model import Project, cc_to_send_percent
from . import midi_convert
from .instruments import resolve_or_create_instrument_by_program
from .key_detect import detect_key
from .import_lyrics import add_lyrics, beats_from_ticks
from .voice_merge import merged_text
from .midi_to_tokens import _dynamics_scale
from .i18n import tr


def import_midi_file(path: str, project_name: str = "Import MIDI",
                      recognize_chords: bool = False,
                      min_bend_semitones: float = None,
                      channel_names=None) -> Project:
    """channel_names (canale -> nome, porta * 16 + canale oltre i 16
    canali): i nomi delle tracce al posto di quello dello strumento
    (l'import MusicXML e MTXT vi passano i nomi delle parti)."""
    tempo_bpm, tpb, channels = midi_convert.analyze_midi(path, min_bend_semitones=min_bend_semitones)
    key = midi_convert.detect_key_signature(path) or ""
    project = Project(name=project_name, tempo_bpm=tempo_bpm, key=key)

    tempo_changes, time_sigs = midi_convert.detect_tempo_and_meter(path)
    time_sig, metrica_changes = midi_convert.meter_to_project_fields(time_sigs, tpb)
    if time_sig:
        project.time_sig = time_sig
        project.metrica_changes = metrica_changes

    # Un canale che cambia strumento a meta' brano diventa una traccia per
    # strumento (vedi midi_convert.split_by_program).
    # channel_num e' lo slot porta * 16 + canale (vedi midi_convert.analyze_midi).
    numbered = [(channel_num, part) for channel_num in sorted(channels)
                for part in midi_convert.split_by_program(channels[channel_num])
                if part.note_count]
    parts = [part for _num, part in numbered]

    # Il tempo e' globale in ST: i marcatori tempo=N vanno in UNA sola traccia,
    # scelta fra quelle con note come quella su cui slittano di meno (la
    # batteria, di solito: colpi brevi, nessuna nota lunga a "coprirli").
    tempo_carrier = None
    if tempo_changes and parts:
        tempo_carrier = min(range(len(parts)), key=lambda i: midi_convert.tempo_marker_drift(
            parts[i], tpb, tempo_changes))

    used_names = set()
    for part_index, (channel_num, ch) in enumerate(numbered):
        instrument_name = resolve_or_create_instrument_by_program(ch.program, ch.is_percussion)
        # Le note sovrapposte (nota tenuta sotto una melodia, accordo che
        # continua sotto una voce) vanno in voci separate, unite poi nella
        # stessa traccia con i blocchi { ; } dove suonano insieme (vedi
        # core.voice_merge); il testo cantato va sulla prima voce.
        voices = midi_convert.channel_to_voices(
            ch, tpb, recognize_chords=recognize_chords,
            tempo_changes=tempo_changes if part_index == tempo_carrier else None)
        text = _channel_text(ch, voices, tpb, project.time_sig, project.metrica_changes)

        # Volume (CC7) e pan (CC10) di base del canale: senza questo, ogni
        # traccia importata partiva sempre da volume/pan predefiniti
        # (100/centro), perdendo il bilanciamento del mix originale tra gli
        # strumenti (uno piu' in secondo piano, uno spostato a
        # sinistra/destra...) - vedi core.midi_convert DEFAULT_CC_VOLUME/
        # DEFAULT_CC_PAN. Le variazioni di CC7/CC11 NEL TEMPO restano gestite
        # a parte da _dynamics_scale come velocity delle note, relative al
        # livello piu' alto del canale: il volume di base e' quindi il CC7 piu'
        # alto in vigore sulle note, non il primo ricevuto (la batteria di
        # Dancin' Fool parte da CC7 0 e sale a 100: diventava muta).
        volume = (track_volume_from_cc(_base_cc_volume(ch)) if ch.volume_cc
                  else midi_convert.DEFAULT_CC_VOLUME)
        pan = ch.pan_cc[0][1] if ch.pan_cc else midi_convert.DEFAULT_CC_PAN
        reverb = cc_to_send_percent(ch.reverb_cc[0][1]) if ch.reverb_cc else 0
        chorus = cc_to_send_percent(ch.chorus_cc[0][1]) if ch.chorus_cc else 0

        name = (channel_names or {}).get(channel_num) or instrument_name
        i = 1
        candidate = name
        while candidate in used_names:
            i += 1
            candidate = f"{name} {i}"
        used_names.add(candidate)
        track = project.add_track(candidate, instrument_name, text)
        track.volume = volume
        track.pan = pan
        track.reverb, track.chorus = reverb, chorus

    if not project.tracks:
        project.add_track("Piano", "Piano", "")

    # "Do maggiore" nel meta key signature e' il valore predefinito di molti
    # sequencer: un file che lo dichiara non e' distinguibile da uno che non
    # dichiara nulla. In entrambi i casi la tonalita' si stima dalle note
    # (come "Analizza tonalita'"), cosi' un'analisi successiva non la cambia.
    if key in ("", "C"):
        try:
            detected = detect_key(project)
        except Exception:
            # la stima e' solo un miglioramento: si tiene il valore del file
            logging.getLogger(__name__).warning("Stima della tonalita' fallita", exc_info=True)
            detected = None
        if detected:
            project.key = detected

    return project


def _base_cc_volume(ch) -> int:
    """Il CC7 di base del canale, coerente con _dynamics_scale: se le sue
    variazioni diventano velocity (relative al livello piu' alto), il CC7 piu'
    alto in vigore all'attacco delle note; se sono troppo piccole per
    diventarlo, quello tipico (la mediana). Il primo ricevuto se non ci sono
    note."""
    events = sorted(ch.volume_cc, key=lambda e: e[0])
    ticks = [t for t, _ in events]
    levels = []
    for start, *_rest in ch.notes:
        i = bisect.bisect_right(ticks, start)
        levels.append(events[i - 1][1] if i else midi_convert.DEFAULT_CC_VOLUME)
    if not levels:
        return events[0][1]
    if _dynamics_scale(ch) is not None:
        return max(levels)
    return sorted(levels)[len(levels) // 2]


def track_volume_from_cc(cc_volume: int) -> int:
    """Il volume di traccia che, all'export, suona come il CC7 del file.
    L'export applica il volume di traccia due volte, come CC7 e come fattore
    sulla velocity (vedi core.midi_export), e nei synth GM entrambi agiscono
    circa col quadrato: v^2 * (v/100)^2 = cc^2 da' v = sqrt(100 * cc). Col
    CC7 del file messo tale e quale il mix si allargava: 120 suonava come 144,
    70 come 49."""
    return round(math.sqrt(100 * max(0, cc_volume)))


def import_midi_channel_into_track(path: str, channel: int = None,
                                    recognize_chords: bool = False,
                                    min_bend_semitones: float = None):
    """Import a singola traccia (funzionalita' 3): ritorna (tokens_text,
    instrument_name_suggerito) per il canale indicato, o per il canale
    primario se channel e' None."""
    tempo_bpm, tpb, channels = midi_convert.analyze_midi(path, min_bend_semitones=min_bend_semitones)
    if channel is not None:
        ch = channels.get(channel)
        if ch is None or ch.note_count == 0:
            raise ValueError(tr("Il canale {channel} non contiene note.", channel=channel))
    else:
        ch = midi_convert.pick_primary_channel(channels)
        if ch is None:
            raise ValueError(tr("Il file MIDI non contiene note."))
    instrument_name = resolve_or_create_instrument_by_program(ch.program, ch.is_percussion)
    voices = midi_convert.channel_to_voices(ch, tpb, recognize_chords=recognize_chords)
    _tempo_changes, time_sigs = midi_convert.detect_tempo_and_meter(path)
    time_sig, metrica_changes = midi_convert.meter_to_project_fields(time_sigs, tpb)
    return _channel_text(ch, voices, tpb, time_sig or "4/4", metrica_changes or []), instrument_name


def _channel_text(ch, voices, tpb, time_sig, metrica_changes) -> str:
    """Il testo della traccia di un canale: le voci unite (blocchi { ; }
    dove suonano insieme) e il testo cantato sulla prima voce."""
    voices = [list(v) for v in voices]
    if ch.lyrics and voices and not ch.is_percussion:
        voices[0] = add_lyrics(voices[0], beats_from_ticks(ch.lyrics, tpb), time_sig, metrica_changes)
    return merged_text(voices, time_sig, metrica_changes)


def list_midi_channels(path: str):
    """Ritorna [(channel, n_note, instrument_guess), ...] per la scelta in GUI."""
    tempo_bpm, tpb, channels = midi_convert.analyze_midi(path)
    result = []
    for ch_num in sorted(channels.keys()):
        ch = channels[ch_num]
        if ch.note_count == 0:
            continue
        guess = midi_convert.guess_instrument_name(ch.program, ch.is_percussion)
        result.append((ch_num, ch.note_count, guess))
    return result
