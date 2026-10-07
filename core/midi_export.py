"""
Esportazione del progetto (o rendering per il playback) in MIDI standard,
rispettando timeline comune, mixaggio (Solo/Mute/Volume/Pan) e motore di
voicing automatico per strumento (SoundText Engine).
"""

import random
from typing import List, Tuple, Optional, Dict

import mido

from .import_lyrics import midi_text_bytes

from .model import Project, Track, send_percent_to_cc
from .instruments import PERCUSSION_MAP, DRUM_MIDI_CHANNEL, InstrumentProfile
from .chords import parse_chord_symbol, voice_chord, pitch_to_midi, apply_bass_note
from .notation import Event
from st_language.midi import (  # noqa: F401  (note e articolazioni: nella libreria)
    SLIDE_PITCH_BEND_RANGE_SEMITONES, _ARTICULATION_DURATION_FACTOR, _apply_articulation, _resolve_event_notes,
    _assign_channels, midi_ports_needed, MIDI_CHANNELS, control_points, PITCH_BEND, TUNE, tune_controls,
    effective_articulation, sounding_span, shift_ticks, needs_bend_range, decorated_velocity, ornament_spans,
    sounding_events,
)
from st_language.timing import fermata_spans, with_fermatas

TICKS_PER_BEAT = 480


# Umanizzazione (funzionalita' 14): jitter massimo applicato a intensita' 100
# (humanize_amount), scalato linearmente per valori intermedi. Il timing
# jitter non si applica alla batteria (un pattern percussivo e' quasi sempre
# scritto con la griglia voluta: spostarlo suona "impreciso", non "umano"),
# solo la velocity (che invece rende bene anche su un groove "stretto",
# come un batterista vero che non colpisce mai due volte esattamente alla
# stessa intensita').
HUMANIZE_MAX_TIMING_JITTER_TICKS = 30
HUMANIZE_MAX_VELOCITY_JITTER = 15


def channels_used_in_midi_file(path: str) -> set:
    """Insieme dei canali MIDI (0-15) effettivamente usati in path (letto
    da qualunque messaggio con un attributo .channel, esclusi i meta come
    tempo/nome traccia). Usato dal motore di riproduzione (core.playback)
    per sapere quali canali restano sul SoundFont di default quando alcuni
    strumenti hanno un override (vedi filter_midi_file_by_channels)."""
    mid = mido.MidiFile(path)
    return {msg.channel for track in mid.tracks for msg in track if hasattr(msg, "channel")}


def filter_midi_file_by_channels(src_path: str, dest_path: str, channels) -> None:
    """Scrive in dest_path una copia di src_path che mantiene solo i
    messaggi meta (tempo, nome traccia, ecc.) e quelli sui canali in
    `channels`: gli altri canali restano silenziosi, ma il tempo assoluto
    degli eventi mantenuti resta corretto (i delta dei messaggi scartati
    vengono accumulati sul prossimo messaggio mantenuto nella stessa
    traccia, invece di essere semplicemente persi).

    Usato dal motore di riproduzione (core.playback) per renderizzare in
    passate separate i gruppi di canali con SoundFont diversi, poi
    mixate insieme campione per campione: fluidsynth NON isola
    correttamente il preset per canale quando piu' SoundFont sono caricati
    nella stessa istanza di synth — per un messaggio program_change
    'grezzo' come quelli di un file MIDI (a differenza di una selezione
    esplicita via API), la ricerca del preset ignora qualunque
    canale-soundfont assegnato in precedenza e usa sempre il SoundFont
    caricato piu' di recente, per QUALSIASI canale (verificato
    empiricamente: anche un canale mai toccato cambia suono al solo
    caricamento di un secondo SoundFont). L'isolamento vero si ottiene
    quindi solo con un synth dedicato a un SOLO SoundFont per gruppo di
    canali, da cui la necessita' di renderizzare (e poi mixare) in passate
    separate invece che in un unico rendering multi-canale."""
    channels = set(channels)
    mid = mido.MidiFile(src_path)
    out = mido.MidiFile(ticks_per_beat=mid.ticks_per_beat)
    for track in mid.tracks:
        new_track = mido.MidiTrack()
        pending = 0
        for msg in track:
            if not hasattr(msg, "channel") or msg.channel in channels:
                new_track.append(msg.copy(time=msg.time + pending))
                pending = 0
            else:
                pending += msg.time
        out.tracks.append(new_track)
    out.save(dest_path)


def _track_port(track) -> Optional[int]:
    """Porta MIDI di una traccia (meta "midi_port"), None se non ne ha."""
    for msg in track:
        if msg.type == "midi_port":
            return msg.port
    return None


def midi_file_ports(path: str) -> set:
    """Porte MIDI usate dalle tracce con messaggi di canale di path (0 se
    una traccia non dichiara la porta)."""
    mid = mido.MidiFile(path)
    return {_track_port(t) or 0 for t in mid.tracks if any(hasattr(m, "channel") for m in t)}


def filter_midi_file_by_port(src_path: str, dest_path: str, port: int) -> None:
    """Copia di src_path con le sole tracce della porta `port` (piu' quelle
    senza messaggi di canale: tempo, metrica, testi), senza il meta
    "midi_port". Il player di FluidSynth ignora le porte (un canale della
    porta 1 suonerebbe sullo stesso canale della porta 0): core.playback
    renderizza quindi ogni porta in una passata separata e poi le mixa."""
    mid = mido.MidiFile(src_path)
    out = mido.MidiFile(ticks_per_beat=mid.ticks_per_beat)
    for track in mid.tracks:
        has_channels = any(hasattr(m, "channel") for m in track)
        if has_channels and (_track_port(track) or 0) != port:
            continue
        new_track = mido.MidiTrack()
        pending = 0
        for msg in track:
            if msg.type == "midi_port":
                pending += msg.time
                continue
            new_track.append(msg.copy(time=msg.time + pending))
            pending = 0
        out.tracks.append(new_track)
    out.save(dest_path)


def channel_instrument_map(project: Project, only_audible: bool = True,
                            tracks: Optional[List[Track]] = None) -> Dict[int, str]:
    """Slot MIDI (porta * 16 + canale) -> nome strumento, con la stessa selezione di tracce e lo
    stesso algoritmo di assegnazione canali usati da export_project_to_midi
    (vedi _assign_channels). Usato dal motore di riproduzione (core.playback)
    per instradare ogni canale sul SoundFont giusto quando uno strumento ha
    un override (vedi core.settings.get_instrument_soundfont): deve restare
    IDENTICO a export_project_to_midi, altrimenti canale e strumento
    andrebbero fuori sincrono tra il file MIDI renderizzato e la mappa."""
    if tracks is None:
        tracks = project.audible_tracks() if only_audible else project.tracks
    tracks = [t for t in tracks if not t.is_audio]
    channels = _assign_channels(tracks)
    return {channels[t.name]: t.instrument_name for t in tracks}


def _shift_beat_map(beat_map: List[Tuple[float, object]], offset_beats: float) -> List[Tuple[float, object]]:
    """Riporta una mappa (beat, valore) sulla timeline di un export che parte
    da offset_beats (vedi export_project_to_midi): il valore attivo
    all'offset diventa quello iniziale (beat 0) e i cambi successivi
    vengono traslati indietro come le note. Senza questo, riprendendo da
    una pausa il brano ripartirebbe col tempo della battuta 1 e i cambi
    arriverebbero in ritardo di offset_beats."""
    if offset_beats <= 0 or not beat_map:
        return beat_map
    from .tempo_map import value_at_beat
    shifted = [(0.0, value_at_beat(beat_map, offset_beats))]
    shifted += [(b - offset_beats, v) for b, v in beat_map if b > offset_beats]
    return shifted


def _note_messages(note_spans: List[Tuple[int, int, int, int]], channel: int
                    ) -> List[Tuple[int, int, mido.Message]]:
    """Messaggi note_on/note_off (tick, priorita', messaggio) per le note
    (attacco, fine, nota, velocity) di una traccia. Due note della STESSA
    altezza sullo stesso canale non possono sovrapporsi: il note_off della
    prima, se arrivasse dopo l'attacco della seconda (legato, o jitter
    dell'umanizzazione), spegnerebbe la seconda quasi subito. La prima
    viene quindi chiusa all'attacco della seconda; due attacchi identici
    diventano una sola nota, lunga quanto la piu' lunga."""
    by_note: Dict[int, List[List[int]]] = {}
    for on, off, note, velocity in sorted(note_spans):
        spans = by_note.setdefault(note, [])
        if spans and spans[-1][0] == on:
            spans[-1][1] = max(spans[-1][1], off)
            continue
        if spans and spans[-1][1] > on:
            spans[-1][1] = on
        spans.append([on, off, velocity])
    out = []
    for note, spans in by_note.items():
        for on, off, velocity in spans:
            out.append((on, 2, mido.Message("note_on", note=note, velocity=velocity, channel=channel, time=0)))
            out.append((off, 0, mido.Message("note_off", note=note, velocity=0, channel=channel, time=0)))
    return out


def _build_global_tempo_map(project: Project, tracks: List[Track], events_by_track: Dict[str, List[Event]],
                             start_offset_beats: float = 0.0) -> List[Tuple[int, int]]:
    """Mappa di tempo (tick, bpm) ordinata, derivata da core.tempo_map.
    build_tempo_beat_map (beat -> bpm, vedi la' per le due sorgenti di cambi
    combinate) convertendo i beat in tick MIDI."""
    from .tempo_map import build_tempo_beat_map

    beat_map = build_tempo_beat_map(project, tracks=tracks, events_by_track=events_by_track)
    beat_map = with_fermatas(beat_map, fermata_spans(events_by_track))
    beat_map = _shift_beat_map(beat_map, start_offset_beats)
    return [(round(beat * TICKS_PER_BEAT), bpm) for beat, bpm in beat_map]


def _control_messages(cc: int, value: int, channel: int) -> List[mido.Message]:
    """I messaggi di un punto di automazione (vedi control_points): un
    control change, il pitch bend per bend=, l'RPN 1 per tune=."""
    if cc == PITCH_BEND:
        return [mido.Message("pitchwheel", pitch=value - 8192, channel=channel, time=0)]
    if cc == TUNE:
        return [mido.Message("control_change", control=c, value=v, channel=channel, time=0)
                for c, v in tune_controls(value)]
    return [mido.Message("control_change", control=cc, value=value, channel=channel, time=0)]


def export_project_to_midi(project: Project, path: str, only_audible: bool = True,
                            tracks: Optional[List[Track]] = None, midi_dir: Optional[str] = None,
                            start_offset_beats: float = 0.0,
                            humanize: bool = False, humanize_amount: int = 50):
    """Esporta il progetto (o un sottoinsieme esplicito di tracce, funzionalita' 3)
    in un file MIDI standard multitraccia.

    start_offset_beats permette di 'saltare' l'inizio del brano (usato per
    riavviare la riproduzione dalla posizione corrente quando l'utente
    modifica Mute/Solo/Volume durante l'esecuzione, funzionalita' 5): gli
    eventi che iniziano prima dell'offset vengono scartati (semplificazione:
    una nota gia' in corso al punto di taglio non viene troncata a meta',
    semplicemente non riparte), gli altri vengono traslati indietro
    dell'offset.

    humanize/humanize_amount (funzionalita' 14, 0-100) aggiungono un piccolo
    scostamento casuale a timing e velocity delle note (non alla batteria,
    che riceve solo il jitter di velocity: vedi commento su
    HUMANIZE_MAX_TIMING_JITTER_TICKS), diverso ad ogni chiamata (nessun seed
    fisso: e' proprio l'incoerenza fra un ascolto e l'altro a suonare
    'umana'). Non tocca eventi di tipo slide/sustain/tempo_marker/rest, ne'
    la timeline logica (il cursore/le durate 'di griglia' restano quelli
    nominali, cambia solo il tick MIDI effettivo scritto nel file)."""
    mid = mido.MidiFile(ticks_per_beat=TICKS_PER_BEAT)

    if tracks is None:
        tracks = project.audible_tracks() if only_audible else project.tracks
    # Le tracce audio non hanno note: le loro clip si aggiungono al rendering
    # (core.playback / core.audio_tracks), nel MIDI non c'e' niente da scrivere.
    tracks = [t for t in tracks if not t.is_audio]
    channels = _assign_channels(tracks)
    ports = midi_ports_needed(channels)

    events_by_track = {
        track.name: track.parsed_events(project.patterns, midi_dir=midi_dir, meter=project.meter())
        for track in tracks
    }

    tempo_track = mido.MidiTrack()
    mid.tracks.append(tempo_track)
    tempo_track.append(mido.MetaMessage("track_name", name=project.name, time=0))
    tempo_map = _build_global_tempo_map(project, tracks, events_by_track, start_offset_beats)
    # Metrica (time_signature): scritta accanto ai cambi di tempo cosi' un
    # export -> import riconosce la metrica del progetto (vedi
    # core.midi_convert.detect_tempo_and_meter). A pari tick precede il tempo.
    from .tempo_map import build_metrica_beat_map, RE_METRICA_VALUE
    tempo_track_events = []
    for beat, sig in _shift_beat_map(build_metrica_beat_map(project), start_offset_beats):
        m = RE_METRICA_VALUE.match(sig or "")
        if m:
            tempo_track_events.append((max(0, round(beat * TICKS_PER_BEAT)), 0, mido.MetaMessage(
                "time_signature", numerator=int(m.group(1)), denominator=int(m.group(2)))))
    for tick, bpm in tempo_map:
        tempo_track_events.append((tick, 1, mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm))))
    last_tempo_tick = 0
    for tick, _order, msg in sorted(tempo_track_events, key=lambda e: (e[0], e[1])):
        msg.time = max(0, tick - last_tempo_tick)
        tempo_track.append(msg)
        last_tempo_tick = max(last_tempo_tick, tick)

    master_factor = max(0, min(200, project.master_volume)) / 100.0

    for track in tracks:
        instrument = track.instrument
        events = events_by_track[track.name]

        midi_track = mido.MidiTrack()
        mid.tracks.append(midi_track)
        midi_track.append(mido.MetaMessage("track_name", name=track.name, time=0))

        port, channel = divmod(channels[track.name], MIDI_CHANNELS)
        if ports:
            # Oltre 15 tracce melodiche: porta MIDI della traccia (vedi
            # st_language.midi._assign_channels e il rendering per porta in
            # core.playback).
            midi_track.append(mido.MetaMessage("midi_port", port=port, time=0))
        if instrument.is_percussion:
            # Bank Select (CC0=120) seleziona il set di drum kit GM2 sul
            # canale percussioni; il Program Change che segue sceglie il
            # kit specifico (vedi GM_DRUM_KITS in core/instruments.py).
            midi_track.append(mido.Message("control_change", control=0, value=120,
                                            channel=channel, time=0))
            midi_track.append(mido.Message("program_change", program=instrument.gm_program,
                                            channel=channel, time=0))
        else:
            midi_track.append(mido.Message("program_change", program=instrument.gm_program,
                                            channel=channel, time=0))
        # Il volume di traccia (0-200, 100 = guadagno originale) scala direttamente
        # la velocity di ogni nota: e' l'unico meccanismo che garantisce un effetto
        # sempre udibile su qualunque synth, a differenza del solo Channel Volume
        # (CC7), la cui curva di risposta e' spesso debole o poco lineare.
        # CC7 viene comunque inviato (clampato 0-127) per i lettori che lo usano.
        # Il volume master (project.master_volume) scala ulteriormente questo
        # fattore, applicandosi uniformemente a tutte le tracce.
        volume_factor = (track.volume / 100.0) * master_factor
        midi_track.append(mido.Message("control_change", control=7,
                                        value=max(0, min(127, round(track.volume * master_factor))),
                                        channel=channel, time=0))
        midi_track.append(mido.Message("control_change", control=10, value=track.pan,
                                        channel=channel, time=0))
        # Invio al riverbero (CC91) e al chorus (CC93) del synth: scritti solo
        # se impostati, cosi' i progetti che non li usano esportano lo stesso
        # file di prima (il synth parte comunque da 0).
        if track.reverb:
            midi_track.append(mido.Message("control_change", control=91, channel=channel, time=0,
                                            value=send_percent_to_cc(track.reverb)))
        if track.chorus:
            midi_track.append(mido.Message("control_change", control=93, channel=channel, time=0,
                                            value=send_percent_to_cc(track.chorus)))

        if needs_bend_range([e for e in events if e.start >= start_offset_beats or e.kind == "control"]):
            # RPN: imposta l'ampiezza del pitch bend su questo canale, cosi'
            # che uno slide di piu' semitoni sia riprodotto correttamente.
            midi_track.append(mido.Message("control_change", control=101, value=0, channel=channel, time=0))
            midi_track.append(mido.Message("control_change", control=100, value=0, channel=channel, time=0))
            midi_track.append(mido.Message("control_change", control=6,
                                            value=SLIDE_PITCH_BEND_RANGE_SEMITONES, channel=channel, time=0))
            midi_track.append(mido.Message("control_change", control=38, value=0, channel=channel, time=0))
            midi_track.append(mido.Message("control_change", control=101, value=127, channel=channel, time=0))
            midi_track.append(mido.Message("control_change", control=100, value=127, channel=channel, time=0))

        # Costruisce la lista di messaggi MIDI assoluti: (tick, priorita', messaggio)
        # priorita': 0=note_off, 1=control_change/pitchwheel, 2=note_on
        # (a parita' di tick, gli off precedono gli altri per evitare sovrapposizioni)
        raw: List[Tuple[int, int, mido.Message]] = []
        note_spans: List[Tuple[int, int, int, int]] = []  # (attacco, fine, nota, velocity), vedi _note_messages
        sustain_open = False
        last_event_end_tick = 0
        # Automazioni (vol=, expr=, pan=...): i valori scritti prima del
        # punto di partenza valgono comunque, si applica l'ultimo al tick 0.
        controls_before: Dict[int, Tuple[float, int]] = {}
        volume_scale = track.volume * master_factor / 100.0

        # le note di abbellimento (d'g) suonano subito prima della loro nota
        for ev in sounding_events(events):
            if ev.kind == "control":
                for beat, cc, value in control_points(ev, volume_scale):
                    if beat < start_offset_beats:
                        if cc not in controls_before or beat >= controls_before[cc][0]:
                            controls_before[cc] = (beat, value)
                        continue
                    tick = round((beat - start_offset_beats) * TICKS_PER_BEAT)
                    raw.extend((tick, 1, msg) for msg in _control_messages(cc, value, channel))
                continue
            if ev.start < start_offset_beats:
                continue

            sound_start, sound_end = sounding_span(ev)
            start_tick = max(0, round((sound_start - start_offset_beats) * TICKS_PER_BEAT))
            end_tick = round((sound_end - start_offset_beats) * TICKS_PER_BEAT)
            moved = shift_ticks(ev, tempo_map, start_tick)      # micro-timing (shift=N ms)
            start_tick, end_tick = max(0, start_tick + moved), max(0, end_tick + moved)
            last_event_end_tick = max(last_event_end_tick, end_tick)

            if ev.lyric and ev.lyric != "_":
                # Testo cantato come evento "lyrics" (karaoke): una sillaba
                # per nota, lo spazio dopo l'ultima sillaba di ogni parola.
                text = ev.lyric[:-1] if ev.lyric.endswith("-") and len(ev.lyric) > 1 else ev.lyric + " "
                raw.append((start_tick, 1, mido.MetaMessage("lyrics", text=midi_text_bytes(text), time=0)))

            if ev.kind == "sustain":
                value = 127 if ev.name == "on" else 0
                sustain_open = (ev.name == "on")
                raw.append((start_tick, 1, mido.Message("control_change", control=64, value=value,
                                                          channel=channel, time=0)))
                continue

            if ev.kind == "tempo_marker":
                continue  # gia' gestito globalmente in _build_global_tempo_map

            if ev.kind == "slide":
                if volume_factor <= 0:
                    # Volume di traccia e/o master a zero: nessun suono, non solo
                    # "molto basso" (senza questo controllo la velocity veniva
                    # comunque forzata ad almeno 1 dal clamp sotto, restando
                    # udibile su soundfont la cui risposta non e' lineare a
                    # velocity minime).
                    continue
                start_note = pitch_to_midi(ev.letter, ev.octave)
                # Tutte le tappe della catena (partenza inclusa), come note MIDI:
                # un classico slide a due punti ha una sola tappa in ev.slide_points
                # (un solo segmento sotto), una catena bend-and-release
                # (c*4>d*4>c*4) ne ha due o piu' (piu' segmenti in sequenza). Un
                # segmento extra ripete l'ultima tappa: ev.slide_segment_durations
                # ha sempre una voce in piu' delle rampe (l'ultima e' l'attesa
                # sull'altezza finale, vedi core.notation._slide_segment_durations),
                # rappresentata come una rampa "ferma" verso se stessa.
                waypoint_notes = [start_note] + [
                    pitch_to_midi(letter, octave) for letter, octave in ev.slide_points
                ]
                waypoint_notes.append(waypoint_notes[-1])
                velocity = max(1, min(127, round(ev.velocity * volume_factor)))

                note_spans.append((start_tick, end_tick, start_note, velocity))
                num_segments = len(ev.slide_segment_durations)
                total_duration = sum(ev.slide_segment_durations)
                cumulative = [0.0]
                for seg_dur in ev.slide_segment_durations:
                    cumulative.append(cumulative[-1] + seg_dur)
                segment_ticks = [
                    start_tick + round((end_tick - start_tick) * (c / total_duration if total_duration > 0 else 0))
                    for c in cumulative
                ]
                for seg in range(num_segments):
                    seg_start_tick, seg_end_tick = segment_ticks[seg], segment_ticks[seg + 1]
                    offset_start = waypoint_notes[seg] - start_note
                    offset_end = waypoint_notes[seg + 1] - start_note
                    steps = max(2, min(16, seg_end_tick - seg_start_tick))
                    for i in range(steps + 1):
                        frac = i / steps
                        tick = seg_start_tick + round((seg_end_tick - seg_start_tick) * frac)
                        offset = offset_start + (offset_end - offset_start) * frac
                        bend = round((offset / SLIDE_PITCH_BEND_RANGE_SEMITONES) * 8192)
                        bend = max(-8192, min(8191, bend))
                        raw.append((tick, 1, mido.Message("pitchwheel", pitch=bend, channel=channel, time=0)))
                raw.append((end_tick, 1, mido.Message("pitchwheel", pitch=0, channel=channel, time=0)))
                continue

            notes, velocity = _resolve_event_notes(ev, instrument)
            # Il parser rifiuta gia' le note singole fuori range, ma il
            # voicing di un accordo a un'ottava estrema puo' comunque
            # sforare: mido solleverebbe ValueError e l'intero export fallirebbe.
            notes = [n for n in notes if 0 <= n <= 127]
            if not notes or volume_factor <= 0:
                # volume_factor <= 0: volume di traccia e/o master a zero, vedi
                # il commento identico nel ramo "slide" qui sopra.
                continue
            velocity = decorated_velocity(ev, round(velocity * volume_factor))
            audible_end_tick = _apply_articulation(start_tick, end_tick, effective_articulation(ev))

            note_start_tick = start_tick
            note_end_tick = audible_end_tick
            if humanize and not instrument.is_percussion:
                timing_jitter = HUMANIZE_MAX_TIMING_JITTER_TICKS * (humanize_amount / 100.0)
                tick_shift = round(random.uniform(-timing_jitter, timing_jitter))
                note_start_tick = max(0, start_tick + tick_shift)
                note_end_tick = max(note_start_tick + 1, audible_end_tick + tick_shift)

            for n in notes:
                note_velocity = velocity
                if humanize:
                    velocity_jitter = HUMANIZE_MAX_VELOCITY_JITTER * (humanize_amount / 100.0)
                    note_velocity = max(1, min(127, velocity + round(random.uniform(-velocity_jitter, velocity_jitter))))
                for a, b, pitch in ornament_spans(ev, n, note_start_tick, note_end_tick, project.key, notes):
                    note_spans.append((a, b, pitch, note_velocity))

        # Rete di sicurezza: se il pedale sustain e' ancora attivo alla fine
        # del brano, lo si rilascia esplicitamente per evitare code sonore
        # infinite dovute a un SOFF mancante.
        if sustain_open:
            raw.append((last_event_end_tick, 1, mido.Message("control_change", control=64, value=0,
                                                               channel=channel, time=0)))

        raw[:0] = [(0, 1, msg) for cc, (_beat, value) in controls_before.items()
                   for msg in _control_messages(cc, value, channel)]
        raw.extend(_note_messages(note_spans, channel))
        raw.sort(key=lambda item: (item[0], item[1]))
        last_tick = 0
        for tick, _priority, msg in raw:
            delta = max(0, tick - last_tick)
            last_tick = tick
            midi_track.append(msg.copy(time=delta))

    mid.save(path)
    return path


def compute_project_duration_beats(project: Project, only_audible: bool = True,
                                     midi_dir: Optional[str] = None) -> float:
    """Durata totale del progetto in beat (quarti), calcolata come il
    massimo, tra le tracce udibili, di (ultimo evento.start + durata),
    comprese le clip delle tracce audio. Usata per la barra di avanzamento
    della riproduzione."""
    from .audio_tracks import audio_tracks_end_beat
    tracks = project.audible_tracks() if only_audible else project.tracks
    max_beats = 0.0
    for track in tracks:
        events = track.parsed_events(project.patterns, midi_dir=midi_dir, meter=project.meter())
        if events:
            track_end = max(e.start + e.duration for e in events)
            max_beats = max(max_beats, track_end)
    return max(max_beats, audio_tracks_end_beat(project, tracks))


def export_single_track_to_midi(project: Project, track_name: str, path: str,
                                  midi_dir: Optional[str] = None):
    """Esporta una sola traccia (funzionalita' 3), ignorando Solo/Mute."""
    track = project.get_track(track_name)
    return export_project_to_midi(project, path, tracks=[track], midi_dir=midi_dir)
