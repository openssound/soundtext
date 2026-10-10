"""
Analisi e conversione di file MIDI in token di notazione interna.

Il modulo analizza il file (canali, note, controller, tempo, metrica,
tonalita'); il resto sta in moduli dedicati, i cui nomi restano importabili
anche da qui per compatibilita':
  - core.midi_to_tokens  quantizzazione delle note in token (channel_to_tokens...)
  - core.midi_bends      riconoscimento dei bending dal pitch bend
  - core.midi_library    libreria midi/ e riferimenti &Nome

Usato da:
  - midi_import.py     (import multitraccia di un intero file MIDI)
  - notation.py         (riferimenti &Nome dentro le tracce, funzionalita' 5)
  - gui/midi_library.py  (visualizzazione/modifica dei MIDI in libreria, funzionalita' 4)

Nota: la grammatica della notazione supporta note melodiche con alterazione
(es. 'c#*4'), quindi la conversione MIDI->testo non e' piu' lossy sulle
altezze cromatiche (a differenza della sola quantizzazione ritmica, che
resta su una griglia di sedicesimi).
"""

import bisect
import logging
import os
from collections import defaultdict
from typing import Dict, List, Optional

import mido

from .instruments import DRUM_MIDI_CHANNEL, all_instruments
from .midi_bends import _collect_pitch_bend_targets
from .midi_library import (  # noqa: F401  (riesportati: vedi la docstring del modulo)
    DEFAULT_MIDI_DIR, USER_MIDI_DIR, AmbiguousMidiRefError, build_midi_index, clear_midi_ref_cache,
    ensure_midi_dir, get_midi_ref_tokens, list_midi_library, render_tokens_to_midi, resolve_midi_ref,
)
from .midi_to_tokens import (  # noqa: F401  (riesportati: vedi la docstring del modulo)
    BEAT_UNITS, DEFAULT_CC_PAN, DEFAULT_CC_VOLUME, GRID_COMMANDS, MAX_IMPORT_VOICES,
    _choose_beat_grid, _dominant_swing_grid, _nearest_percussion, channel_to_tokens,
    channel_to_voices, tempo_marker_drift,
)
from .i18n import tr

# Sensibilita' di pitch bend di default (General MIDI) quando il file non la
# dichiara esplicitamente via RPN 0 (vedi _collect_pitch_bend_targets): +-2
# semitoni e' lo standard a cui i sintetizzatori si affidano in assenza di
# un'indicazione esplicita.
DEFAULT_PITCH_BEND_RANGE_SEMITONES = 2

TEMPO_CHANGE_MIN_FRACTION = 0.02

# Un cambio piu' piccolo (anche 1 BPM) conta se il nuovo tempo resta almeno
# tanti quarti: 84 -> 85 BPM per 100 quarti sono quasi un secondo di scarto.
TEMPO_HOLD_MIN_BEATS = 8

def guess_instrument_name(program: Optional[int], is_percussion: bool) -> str:
    """Funzionalita' 6: riconosce lo strumento piu' vicino (per numero di
    Program Change GM) tra quelli disponibili (predefiniti + personalizzati),
    invece di assegnare sempre 'Piano'."""
    if is_percussion:
        for name, instr in all_instruments().items():
            if instr.is_percussion:
                return name
        return "Drums"

    if program is None:
        return "Piano"

    best_name, best_dist = "Piano", 999
    for name, instr in all_instruments().items():
        if instr.is_percussion:
            continue
        d = abs(instr.gm_program - program)
        if d < best_dist:
            best_name, best_dist = name, d
    return best_name

class ChannelData:
    def __init__(self, channel: int):
        self.channel = channel
        self.notes = []       # (start_tick, end_tick, note, velocity)
        self.program = None   # ultimo Program Change ricevuto
        # Tutti i Program Change del canale: [(tick, programma), ...] in
        # ordine di arrivo (vedi split_by_program).
        self.program_changes = []
        # Bending rilevati (vedi _collect_pitch_bend_targets): (start_tick,
        # note) -> (peak_fraction, [nota MIDI di arrivo, ...]) - una tappa
        # per un bend-and-hold, due per un bend-and-release - solo per le
        # note di self.notes il cui pitch bend supera la soglia di un
        # bending deliberato. Chiave composta invece di allineare per
        # indice: piu' robusta se in futuro self.notes viene riordinata o
        # filtrata prima di channel_to_tokens.
        self.bends = {}
        # Solo per i bend-and-release: (start_tick, note) -> (frazione della
        # nota in cui il wheel INIZIA a rilasciare dopo la tenuta sul picco,
        # frazione in cui ha finito di rilasciare e resta sul valore finale).
        # Separato da bends per non cambiare la forma delle sue tuple.
        self.bend_release = {}
        # (start_tick, note) -> frazione della nota in cui il bend INIZIA
        # (wheel fermo prima); assente = parte subito dall'attacco.
        self.bend_onset = {}
        # (start_tick, note) -> [(frazione, nota MIDI), ...]: percorso a tappe
        # dei bend a due direzioni (su E giu' rispetto alla nota scritta), che
        # il modello a un solo picco non puo' rappresentare.
        self.bend_paths = {}
        # Pedale del sustain (CC64): [(tick, acceso), ...] in ordine di
        # arrivo (acceso = valore >= 64, soglia standard MIDI); vedi
        # channel_to_tokens per la conversione in token SON/SOFF.
        self.sustain = []
        # Volume (CC7) ed espressione (CC11): [(tick, valore), ...]; vedi
        # _dynamics_scale per come diventano velocity delle note.
        self.volume_cc = []
        self.expression_cc = []
        # Pan (CC10): [(tick, valore 0-127, 64=centro), ...]; il primo
        # valore del canale (il "pan" di base scelto per lo strumento
        # nell'arrangiamento originale, tipicamente impostato una sola
        # volta a inizio brano) diventa il pan della traccia importata -
        # vedi import_midi_file in core.midi_import.
        self.pan_cc = []
        # Invio al riverbero (CC91) e al chorus (CC93): come il pan, conta il
        # primo valore (diventa il riverbero/chorus della traccia importata).
        self.reverb_cc = []
        self.chorus_cc = []
        # Testo cantato (eventi "lyrics", o "text" nei file karaoke):
        # [(tick, sillaba in forma ST)], vedi core.import_lyrics.
        self.lyrics = []

    @property
    def is_percussion(self):
        return self.channel == DRUM_MIDI_CHANNEL

    @property
    def note_count(self):
        return len(self.notes)

def analyze_midi(path: str, ticks_per_beat_override: Optional[int] = None,
                 min_bend_semitones: Optional[float] = None):
    """Analizza un file MIDI e ritorna (tempo_bpm, ticks_per_beat, {channel: ChannelData}).

    min_bend_semitones abbassa la soglia con cui un pitch bend e' riconosciuto
    come slide (vedi _collect_pitch_bend_targets): utile per la slide guitar,
    i cui bend brevi restano appena sopra il semitono. None = soglia di sempre.

    Usa clip=True: alcuni file MIDI "in the wild" (esportati da DAW o
    convertitori non perfettamente conformi) contengono byte dato fuori dal
    range MIDI valido (0-127), che altrimenti farebbero sollevare a mido un
    ValueError ("data byte must be in range 0..127") anche se il file e'
    perfettamente riproducibile in un player normale. Con clip=True mido
    satura questi valori nel range valido invece di rifiutare il file."""
    try:
        mid = mido.MidiFile(path, clip=True)
    except Exception as e:
        raise ValueError(
            tr("Impossibile leggere il file MIDI '{0}': {e}", os.path.basename(path), e=e)
        ) from e
    tpb = ticks_per_beat_override or mid.ticks_per_beat
    tempo = 500000  # default 120 BPM in microsecondi/quarto
    first_tempo_tick = None

    channels: Dict[int, ChannelData] = {}
    active = {}
    # Per il rilevamento dei bending (vedi _collect_pitch_bend_targets, in
    # fondo): timeline grezza dei messaggi pitchwheel per canale, e ampiezza
    # del pitch bend dichiarata via RPN 0 (Pitch Bend Sensitivity) - se mai
    # dichiarata, altrimenti si assume il default General MIDI.
    pitchwheel_events: Dict[int, List[tuple]] = defaultdict(list)
    pitch_bend_range: Dict[int, float] = {}
    rpn_selected: Dict[int, tuple] = {}  # channel -> (MSB, LSB) dell'ultimo RPN selezionato (CC101/100)
    lyric_events: Dict[int, list] = defaultdict(list)     # traccia -> [(tick, testo)]
    text_events: Dict[int, list] = defaultdict(list)
    track_channels: Dict[int, set] = defaultdict(set)     # traccia -> canali con note
    onsets: Dict[int, list] = defaultdict(list)           # canale -> tick d'attacco

    for track_index, track in enumerate(mid.tracks):
        abs_tick = 0
        port = 0
        for msg in track:
            abs_tick += msg.time
            # Oltre 16 canali un file usa piu' porte MIDI (meta "midi_port",
            # vedi st_language.midi._assign_channels): il canale 1 della porta
            # 1 e' un'altra parte rispetto al canale 1 della porta 0. Le chiavi
            # sono quindi "slot" = porta * 16 + canale (uguali al canale con
            # una sola porta).
            if msg.type == "midi_port":
                port = msg.port
            slot = port * 16 + msg.channel if hasattr(msg, "channel") else None
            if msg.type == "lyrics":
                lyric_events[track_index].append((abs_tick, msg.text))
            elif msg.type == "text" and not msg.text.startswith("@"):
                text_events[track_index].append((abs_tick, msg.text))
            if msg.type == "set_tempo":
                # Un file puo' contenere piu' cambi di tempo (es. accelerando/
                # rallentando, o cambi di tempo per battuta): il tempo "del
                # brano" da riportare e' quello iniziale (al tick piu' basso),
                # non l'ultimo incontrato durante la scansione.
                if first_tempo_tick is None or abs_tick < first_tempo_tick:
                    first_tempo_tick = abs_tick
                    tempo = msg.tempo
            elif msg.type == "program_change":
                ch = channels.setdefault(slot, ChannelData(msg.channel))
                ch.program = msg.program
                ch.program_changes.append((abs_tick, msg.program))
            elif msg.type == "note_on" and msg.velocity > 0:
                active[(slot, msg.note)] = (abs_tick, msg.velocity)
                track_channels[track_index].add(slot)
                onsets[slot].append(abs_tick)
            elif msg.type in ("note_off",) or (msg.type == "note_on" and msg.velocity == 0):
                key = (slot, msg.note)
                if key in active:
                    start_tick, vel = active.pop(key)
                    ch = channels.setdefault(slot, ChannelData(msg.channel))
                    ch.notes.append((start_tick, abs_tick, msg.note, vel))
            elif msg.type == "pitchwheel":
                pitchwheel_events[slot].append((abs_tick, msg.pitch))
            elif msg.type == "control_change" and msg.control == 64:
                channels.setdefault(slot, ChannelData(msg.channel)).sustain.append(
                    (abs_tick, msg.value >= 64))
            elif msg.type == "control_change" and msg.control in (7, 10, 11, 91, 93):
                ch = channels.setdefault(slot, ChannelData(msg.channel))
                dest = {7: ch.volume_cc, 10: ch.pan_cc, 11: ch.expression_cc,
                        91: ch.reverb_cc, 93: ch.chorus_cc}[msg.control]
                dest.append((abs_tick, msg.value))
            elif msg.type == "control_change" and msg.control in (100, 101):
                # RPN MSB/LSB (CC101/100): selezionano QUALE parametro le
                # prossime CC6/CC38 (Data Entry) andranno a impostare. Ordine
                # d'arrivo non garantito, quindi si aggiornano indipendentemente
                # e si controlla la coppia risultante solo alla CC6 (sotto).
                msb, lsb = rpn_selected.get(slot, (None, None))
                rpn_selected[slot] = ((msg.value, lsb) if msg.control == 101
                                    else (msb, msg.value))
            elif msg.type == "control_change" and msg.control == 6:
                # Data Entry MSB: se l'RPN correntemente selezionato e' 0,0
                # (Pitch Bend Sensitivity), il suo valore sono i semitoni di
                # ampiezza del pitch bend su questo canale (il centesimi via
                # CC38/Data Entry LSB si ignora: precisione che non serve qui,
                # dato che il bersaglio va comunque arrotondato al semitono).
                if rpn_selected.get(slot) == (0, 0):
                    pitch_bend_range[slot] = msg.value

    _assign_lyrics(channels, lyric_events, text_events, track_channels, onsets, tpb)

    for ch_num, ch in channels.items():
        _collect_pitch_bend_targets(
            ch, pitchwheel_events.get(ch_num, []),
            pitch_bend_range.get(ch_num, DEFAULT_PITCH_BEND_RANGE_SEMITONES), tpb,
            min_bend_semitones,
        )

    return round(mido.tempo2bpm(tempo)), tpb, channels

def split_by_program(channel: ChannelData) -> List[ChannelData]:
    """Un canale che cambia strumento a meta' brano (Program Change fra le
    note: Layla, il riff dell'intro in chitarra overdrive e poi pianoforte
    sullo stesso canale) diviso in un ChannelData per strumento, con le sole
    note suonate con quel programma (quello dell'ultimo Program Change
    all'attacco; prima del primo, il primo). Tutte le parti tornate dallo
    stesso strumento finiscono nella stessa. Un canale con un solo strumento
    (o la batteria, dove il programma sceglie il kit) torna intatto."""
    changes = sorted(channel.program_changes, key=lambda c: c[0])
    if channel.is_percussion or len({p for _t, p in changes}) < 2:
        return [channel]
    ticks = [t for t, _p in changes]

    def program_at(tick):
        i = bisect.bisect_right(ticks, tick)
        return changes[i - 1][1] if i else changes[0][1]

    groups: Dict[int, list] = {}
    for note in sorted(channel.notes, key=lambda n: n[0]):
        groups.setdefault(program_at(note[0]), []).append(note)
    if len(groups) < 2:
        channel.program = next(iter(groups), channel.program)
        return [channel]

    parts = []
    for program, notes in groups.items():         # in ordine di prima nota
        part = ChannelData(channel.channel)
        part.program = program
        part.program_changes = [c for c in changes if c[1] == program]
        part.notes = notes
        keys = {(start, n) for start, _end, n, _vel in notes}
        for attr in ("bends", "bend_release", "bend_onset", "bend_paths"):
            setattr(part, attr, {k: v for k, v in getattr(channel, attr).items() if k in keys})
        first = notes[0][0]
        for attr in ("volume_cc", "pan_cc", "expression_cc", "reverb_cc", "chorus_cc"):
            # dal valore in vigore alla prima nota della parte: e' quello che
            # diventa il livello iniziale della traccia (vedi midi_import)
            events = sorted(getattr(channel, attr), key=lambda e: e[0])
            before = [e for e in events if e[0] <= first]
            setattr(part, attr, before[-1:] + [e for e in events if e[0] > first])
        part.sustain = list(channel.sustain)
        part.lyrics = [ly for ly in channel.lyrics if program_at(ly[0]) == program]
        parts.append(part)
    return parts


# Un file karaoke senza eventi "lyrics" scrive il testo come eventi "text":
# si usano solo se una traccia ne ha almeno tanti (altrimenti sono note,
# titoli o crediti).
MIN_KARAOKE_TEXT_EVENTS = 8


def _assign_lyrics(channels, lyric_events, text_events, track_channels, onsets, tpb) -> None:
    """Il testo cantato di ogni traccia MIDI va al canale delle sue note; da
    una traccia senza note (karaoke) al canale le cui note attaccano dove
    cadono le sillabe."""
    from .import_lyrics import nearest_channel, syllables
    sources = lyric_events
    if not any(lyric_events.values()):
        sources = {t: ev for t, ev in text_events.items() if len(ev) >= MIN_KARAOKE_TEXT_EVENTS}
    melodic = {c: o for c, o in onsets.items() if c != DRUM_MIDI_CHANNEL}
    for track_index, events in sources.items():
        own = [c for c in track_channels.get(track_index, ()) if c != DRUM_MIDI_CHANNEL]
        channel = own[0] if len(own) == 1 else nearest_channel(
            [t for t, _ in events], {c: melodic[c] for c in (own or melodic)}, tpb)
        if channel is None or channel not in channels:
            continue
        channels[channel].lyrics.extend(syllables(events))
    for ch in channels.values():
        ch.lyrics.sort(key=lambda e: e[0])


def detect_key_signature(path: str) -> Optional[str]:
    """Cerca il primo evento meta 'key_signature' nel file MIDI e ritorna la
    tonalita' nella stessa notazione di Project.key (es. 'C', 'Am', 'F#'):
    mido usa gia' questa identica convenzione per msg.key, quindi nessuna
    conversione e' necessaria. Ritorna None se il file non ne dichiara una
    (la maggior parte dei file "in the wild" non lo fa).

    Funzione separata da analyze_midi (che non tocca) per non cambiarne la
    firma di ritorno, usata in molti punti del codice e nei test."""
    try:
        mid = mido.MidiFile(path, clip=True)
    except Exception:
        logging.getLogger(__name__).info("Tonalita' non leggibile da %s", path, exc_info=True)
        return None
    best_tick = None
    best_key = None
    for track in mid.tracks:
        abs_tick = 0
        for msg in track:
            abs_tick += msg.time
            if msg.type == "key_signature":
                if best_tick is None or abs_tick < best_tick:
                    best_tick = abs_tick
                    best_key = msg.key
    return best_key

def detect_tempo_and_meter(path: str):
    """Ritorna (tempo_changes, time_sigs) del file MIDI:
      - tempo_changes: [(tick, bpm), ...] dei soli cambi di tempo DOPO quello
        iniziale (quello iniziale e' gia' il tempo restituito da
        analyze_midi), con BPM arrotondato e scartando i cambi che non
        modificano il valore arrotondato;
      - time_sigs: [(tick, numeratore, denominatore), ...] ordinati, con un
        solo evento per tick (l'ultimo).
    Come analyze_midi, legge il file con clip=True."""
    try:
        mid = mido.MidiFile(path, clip=True)
    except Exception as e:
        raise ValueError(
            tr("Impossibile leggere il file MIDI '{0}': {e}", os.path.basename(path), e=e)
        ) from e

    tempos: Dict[int, int] = {}
    sigs: Dict[int, tuple] = {}
    for track in mid.tracks:
        abs_tick = 0
        for msg in track:
            abs_tick += msg.time
            if msg.type == "set_tempo":
                tempos[abs_tick] = round(mido.tempo2bpm(msg.tempo))
            elif msg.type == "time_signature":
                sigs[abs_tick] = (msg.numerator, msg.denominator)

    # Un cambio conta solo se si discosta dall'ULTIMO valore tenuto di almeno
    # TEMPO_CHANGE_MIN_FRACTION (e di 2 BPM): le oscillazioni di 1 BPM di un
    # tempo "registrato" non sono cambi di tempo e riempirebbero il testo di
    # marcatori. Un accelerando graduale emette comunque un marcatore ogni
    # volta che il tempo si e' spostato abbastanza. Un cambio piu' piccolo
    # conta se il tempo poi resta fermo almeno TEMPO_HOLD_MIN_BEATS quarti
    # (la fine di un accelerando, una sezione un po' piu' veloce).
    tempo_changes = []
    kept = None
    ordered = sorted(tempos.items())
    hold_ticks = TEMPO_HOLD_MIN_BEATS * mid.ticks_per_beat
    for i, (tick, bpm) in enumerate(ordered):
        held = (ordered[i + 1][0] if i + 1 < len(ordered) else float("inf")) - tick
        if kept is None:
            kept = bpm
        elif (abs(bpm - kept) >= max(2, round(kept * TEMPO_CHANGE_MIN_FRACTION))
              or (bpm != kept and held >= hold_ticks)):
            tempo_changes.append((tick, bpm))
            kept = bpm

    time_sigs = [(tick, n, d) for tick, (n, d) in sorted(sigs.items())]
    return tempo_changes, time_sigs

def meter_to_project_fields(time_sigs: List[tuple], ticks_per_beat: int):
    """Converte gli eventi time_signature (tick, num, den) nei campi del
    progetto: (time_sig iniziale "N/D", metrica_changes [(battuta, "N/D"), ...]).
    metrica_changes e' vuota se la metrica non cambia mai. Il numero di
    battuta di ogni cambio si ricava dalla lunghezza (in tick) della battuta
    nella metrica precedente, arrotondando al piu' vicino (un cambio non
    allineato alla battuta e' raro, e la metrica di ST cambia solo a inizio
    battuta)."""
    if not time_sigs:
        return None, []
    first_sig = f"{time_sigs[0][1]}/{time_sigs[0][2]}"
    changes = [(1, first_sig)]
    prev_tick, prev_num, prev_den = time_sigs[0]
    bar = 1
    for tick, num, den in time_sigs[1:]:
        bar_ticks = ticks_per_beat * 4 * prev_num / prev_den
        bar += round((tick - prev_tick) / bar_ticks)
        sig = f"{num}/{den}"
        if bar == changes[-1][0]:
            changes[-1] = (bar, sig)
        elif sig != changes[-1][1]:
            changes.append((bar, sig))
        prev_tick, prev_num, prev_den = tick, num, den
    if len(changes) == 1:
        return changes[0][1], []
    return changes[0][1], changes

def pick_primary_channel(channels: Dict[int, "ChannelData"]) -> Optional["ChannelData"]:
    """Sceglie il canale con piu' note (preferendo quelli non percussivi a parita')."""
    candidates = [c for c in channels.values() if c.note_count > 0]
    if not candidates:
        return None
    candidates.sort(key=lambda c: (c.note_count, not c.is_percussion), reverse=True)
    return candidates[0]
