"""
Motore di quantizzazione audio -> notazione testuale (Audio-to-SoundText).

Prende eventi con timestamp assoluti in secondi (prodotti da core.audio_pitch
o core.audio_percussion) e li quantizza sulla griglia ritmica scelta
dall'utente (denominatore + eventuale terzine), producendo una sequenza di
token ST-Syntax sempre valida (vedi validate_track_text in core.notation).

Nessuna dipendenza da decodifica/sounddevice/analisi audio: modulo puro, testabile in
isolamento (vedi tests/test_audio_quantize.py) e riusabile sia dal percorso
file sia dal percorso microfono.
"""

from dataclasses import dataclass, replace
from typing import Dict, List, Optional

from .chords import midi_to_token
from .instruments import PERCUSSION_MAP
from .notation import Pattern, validate_track_text
from .i18n import tr


@dataclass
class AudioEvent:
    """Un evento nota/percussione rilevato nell'audio, con timestamp assoluti
    in secondi (non ancora quantizzati). Per un evento melodico impostare
    midi_pitch; per un evento percussivo impostare perc_name (nome presente
    in core.instruments.PERCUSSION_MAP).

    slide_to_pitch (opzionale, solo eventi melodici): se impostata, l'evento
    viene emesso come portamento/slide (vedi core.notation.RE_SLIDE,
    'c*4>d*4') dalla classe di altezza midi_pitch a slide_to_pitch invece che
    come nota ferma - usato dal bending del dialogo 'Suona con la tastiera'
    (gui.keyboard_play_dialog) per catturare un vero bending in stile
    chitarra, che core.midi_export sa gia' rendere come un pitch bend MIDI
    continuo. Ignorata se l'evento condivide lo slot con altri eventi
    simultanei (es. un accordo): in quel caso resta una nota ferma, dato che
    la grammatica non supporta ancora piu' slide simultanei in un blocco."""
    start_sec: float
    end_sec: float
    velocity: int
    midi_pitch: Optional[int] = None
    perc_name: Optional[str] = None
    slide_to_pitch: Optional[int] = None


@dataclass(frozen=True)
class QuantizeSettings:
    """Quantizzazione regolabile, per chi suona impreciso senza voler
    perdere il suo modo di suonare:
    - strength (0-1): di quanto ogni nota si sposta verso la griglia (1 =
      tutta, come prima); il punto intermedio si arrotonda alla griglia fine
      di FINE_GRID;
    - window (0-1, della meta' di uno slot): si correggono solo le note
      entro quella distanza dalla griglia, le altre (anticipi e ritardi
      voluti) restano dove sono;
    - swing (0.5-0.75): sulle griglie da 1/8 e 1/16 la seconda suddivisione
      di ogni coppia va piu' tardi (0.5 = dritto, 0.66 = shuffle in terzine),
      cosi' un'esecuzione swing non viene raddrizzata;
    - min_note_sec: si scartano le note piu' corte (corde sfiorate);
    - merge_gap_sec: due note uguali di fila separate da meno di cosi'
      diventano una sola (un attacco rilevato due volte).
    I valori predefiniti danno la quantizzazione di sempre."""
    strength: float = 1.0
    window: float = 1.0
    swing: float = 0.5
    min_note_sec: float = 0.0
    merge_gap_sec: float = 0.0

    @property
    def snaps_to_grid(self) -> bool:
        """Vero se le note finiscono esattamente sulla griglia scelta (e il
        testo si scrive su quella griglia, non su quella fine)."""
        return self.strength >= 1.0 and self.window >= 1.0 and abs(self.swing - 0.5) < 1e-9


# Griglia su cui si scrive una quantizzazione parziale o con lo swing (la
# stessa di "Off"): 1/64, o 1/64 in terzine se la griglia scelta e' ternaria.
FINE_GRID = 64
SWING_GRIDS = (8, 16)


def grid_slot_beats(denominator: int, ternary: bool) -> float:
    """Durata in beat di uno slot della griglia N:/NT:. Stessa identica
    formula usata da parse_tokens/compute_token_spans in core/notation.py:
    va riusata cosi' com'e', non riderivata, per garantire che la
    quantizzazione non produca mai uno sfasamento rispetto a come il motore
    di playback interpreta la stessa griglia."""
    beats = 4.0 / denominator
    if ternary:
        beats *= 2.0 / 3.0
    return beats


def grid_token(denominator: int, ternary: bool) -> str:
    return f"{denominator}{'T' if ternary else ''}:"


def _monophonic(quantized: list) -> list:
    """Per una linea melodica (una nota alla volta, come la produce
    core.audio_pitch): due note che dopo la quantizzazione si sovrappongono
    diventerebbero un accordo inesistente (partenza nello stesso slot) o la
    seconda sparirebbe (partenza dentro la prima). La nota precedente si
    accorcia fino all'inizio della successiva; se partono nello stesso slot
    resta quella piu' lunga nell'audio."""
    out = []
    for qs, qe, ev in sorted(quantized, key=lambda q: (q[0], q[2].start_sec)):
        if out and qs < out[-1][1]:
            pqs, pqe, pev = out[-1]
            if qs > pqs:
                out[-1] = (pqs, qs, pev)
            else:
                if (ev.end_sec - ev.start_sec) > (pev.end_sec - pev.start_sec):
                    out[-1] = (qs, qe, ev)
                continue
        out.append((qs, qe, ev))
    return out


def _same_sound(a: AudioEvent, b: AudioEvent) -> bool:
    return (a.midi_pitch, a.perc_name, a.slide_to_pitch) == (b.midi_pitch, b.perc_name, b.slide_to_pitch)


def clean_events(events: List[AudioEvent], min_note_sec: float = 0.0,
                 merge_gap_sec: float = 0.0) -> List[AudioEvent]:
    """La pulizia di QuantizeSettings: via le note piu' corte di
    min_note_sec, poi una nota uguale alla precedente (stessa altezza o
    stesso colpo) che parte entro merge_gap_sec dalla sua fine la allunga
    invece di ripetersi. Gli eventi originali non cambiano."""
    kept = [e for e in events if e.end_sec - e.start_sec >= min_note_sec] if min_note_sec > 0 else list(events)
    if merge_gap_sec <= 0:
        return kept
    out: List[AudioEvent] = []
    last_of: Dict[tuple, int] = {}       # suono -> indice in out della sua ultima nota
    for ev in sorted(kept, key=lambda e: e.start_sec):
        key = (ev.midi_pitch, ev.perc_name, ev.slide_to_pitch)
        i = last_of.get(key)
        if i is not None and _same_sound(out[i], ev) and ev.start_sec - out[i].end_sec <= merge_gap_sec:
            out[i] = replace(out[i], end_sec=max(out[i].end_sec, ev.end_sec))
            continue
        last_of[key] = len(out)
        out.append(ev)
    return out


def _swung(position: float, slot_beats: float, swing: float) -> float:
    """Posizione (in beat) del punto di griglia 'position' (multiplo di
    slot_beats) con lo swing: i punti dispari di ogni coppia vanno avanti."""
    k = round(position / slot_beats)
    return k * slot_beats + ((2 * swing - 1) * slot_beats if k % 2 else 0.0)


def _quantized_beats(start: float, end: float, slot_beats: float, settings: QuantizeSettings) -> tuple:
    """(inizio, fine) in beat dopo la quantizzazione regolabile, non ancora
    arrotondati alla griglia fine: l'inizio va verso il punto di griglia
    piu' vicino (con lo swing) se e' entro la finestra, la durata resta."""
    base = round(start / slot_beats)
    targets = [_swung((base + d) * slot_beats, slot_beats, settings.swing) for d in (-1, 0, 1)]
    target = min(targets, key=lambda t: abs(t - start))
    if abs(target - start) > settings.window * slot_beats / 2 + 1e-9:
        return start, end
    shift = settings.strength * (target - start)
    return start + shift, end + shift


def events_to_tokens(events: List[AudioEvent], tempo_bpm: float,
                      grid_denominator: int, ternary: bool = False,
                      monophonic: bool = False,
                      settings: Optional[QuantizeSettings] = None) -> List[str]:
    """Quantizza gli eventi (timestamp assoluti in secondi) sulla griglia
    scelta e li converte in una sequenza di token di notazione interna.
    Stesso schema di core.midi_convert.channel_to_tokens (slot interi,
    velocity emessa solo al cambiamento, blocchi [...] per eventi
    simultanei), generalizzato a denominatore/terzine arbitrari e a
    timestamp in secondi (convertiti in beat via tempo_bpm) invece di tick
    MIDI fissi su una griglia di sedicesimi.

    monophonic=True per una linea melodica rilevata dall'audio: vedi
    _monophonic. settings: la quantizzazione regolabile (QuantizeSettings);
    se non porta le note esattamente sulla griglia, il testo si scrive sulla
    griglia fine (FINE_GRID)."""
    settings = settings or QuantizeSettings()
    swing_allowed = grid_denominator in SWING_GRIDS and not ternary
    if not swing_allowed:
        settings = replace(settings, swing=0.5)
    events = clean_events(events, settings.min_note_sec, settings.merge_gap_sec)
    slot_beats = grid_slot_beats(grid_denominator, ternary)
    if settings.snaps_to_grid:
        out_denominator, out_slot = grid_denominator, slot_beats
    else:
        out_denominator, out_slot = FINE_GRID, grid_slot_beats(FINE_GRID, ternary)
    tokens = [grid_token(out_denominator, ternary)]
    if not events:
        return tokens

    beats_per_sec = tempo_bpm / 60.0

    quantized = []
    for ev in events:
        start_beat = ev.start_sec * beats_per_sec
        end_beat = ev.end_sec * beats_per_sec
        if not settings.snaps_to_grid:
            start_beat, end_beat = _quantized_beats(start_beat, end_beat, slot_beats, settings)
        qs = max(0, round(start_beat / out_slot))
        qe = max(qs + 1, round(end_beat / out_slot))
        quantized.append((qs, qe, ev))
    if monophonic:
        quantized = _monophonic(quantized)

    max_slot = max(qe for _, qe, _ in quantized)
    slots: List[list] = [[] for _ in range(max_slot)]
    for qs, qe, ev in quantized:
        if qs < max_slot:
            slots[qs].append((ev, qe - qs))

    slot = 0
    last_velocity = None
    while slot < max_slot:
        here = slots[slot]
        if not here:
            run = 0
            while slot < max_slot and not slots[slot]:
                run += 1
                slot += 1
            tokens.append(f"{run}r" if run > 1 else "r")
            continue

        vel = max(1, min(127, here[0][0].velocity))
        if vel != last_velocity:
            tokens.append(f"{vel}@")
            last_velocity = vel

        dur_slots = max(d for _, d in here)
        # Una nota che parte mentre questa suona ancora (legato, o spostata
        # dallo swing) sparirebbe: questa si accorcia fino a li'.
        next_start = next((k for k in range(slot + 1, min(slot + dur_slots, max_slot)) if slots[k]), None)
        if next_start is not None:
            dur_slots = next_start - slot
        mult = f"{dur_slots}" if dur_slots > 1 else ""

        if here[0][0].perc_name is not None:
            names = sorted({ev.perc_name for ev, _ in here if ev.perc_name in PERCUSSION_MAP})
            body = names[0] if len(names) == 1 else "[" + " ".join(names) + "]"
        elif (len(here) == 1 and here[0][0].midi_pitch is not None
              and here[0][0].slide_to_pitch is not None):
            # Portamento/slide (bending): unico evento nello slot, vedi
            # AudioEvent.slide_to_pitch - se condivide lo slot con altri
            # eventi simultanei ricade sul ramo sotto (nota ferma), la
            # grammatica non supporta ancora slide dentro un blocco [...].
            ev = here[0][0]
            body = f"{midi_to_token(ev.midi_pitch)}>{midi_to_token(ev.slide_to_pitch)}"
        else:
            pitches = sorted({midi_to_token(ev.midi_pitch) for ev, _ in here if ev.midi_pitch is not None})
            body = pitches[0] if len(pitches) == 1 else "[" + " ".join(pitches) + "]"

        tokens.append(mult + body)
        slot += dur_slots

    return tokens


def audio_events_to_validated_text(events: List[AudioEvent], tempo_bpm: float,
                                    grid_denominator: int, ternary: bool,
                                    patterns: Dict[str, Pattern], default_octave: int = 4,
                                    midi_dir: Optional[str] = None, monophonic: bool = False,
                                    settings: Optional[QuantizeSettings] = None) -> str:
    """Genera il testo finale e lo valida SEMPRE con validate_track_text
    prima di ritornarlo. Solleva ValueError se il risultato non e' valido
    (non dovrebbe mai accadere dato il design difensivo di events_to_tokens,
    ma nessun testo viene mai inserito in una traccia senza passare da qui)."""
    tokens = events_to_tokens(events, tempo_bpm, grid_denominator, ternary, monophonic=monophonic,
                              settings=settings)
    text = " ".join(tokens)
    ok, msg = validate_track_text(text, patterns, default_octave=default_octave, midi_dir=midi_dir)
    if not ok:
        raise ValueError(tr("Conversione audio: token generati non validi ({msg}). Nessuna modifica applicata.", msg=msg))
    return text
