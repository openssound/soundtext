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

from dataclasses import dataclass
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


def events_to_tokens(events: List[AudioEvent], tempo_bpm: float,
                      grid_denominator: int, ternary: bool = False,
                      monophonic: bool = False) -> List[str]:
    """Quantizza gli eventi (timestamp assoluti in secondi) sulla griglia
    scelta e li converte in una sequenza di token di notazione interna.
    Stesso schema di core.midi_convert.channel_to_tokens (slot interi,
    velocity emessa solo al cambiamento, blocchi [...] per eventi
    simultanei), generalizzato a denominatore/terzine arbitrari e a
    timestamp in secondi (convertiti in beat via tempo_bpm) invece di tick
    MIDI fissi su una griglia di sedicesimi.

    monophonic=True per una linea melodica rilevata dall'audio: vedi
    _monophonic."""
    tokens = [grid_token(grid_denominator, ternary)]
    if not events:
        return tokens

    beats_per_sec = tempo_bpm / 60.0
    slot_beats = grid_slot_beats(grid_denominator, ternary)

    quantized = []
    for ev in events:
        start_beat = ev.start_sec * beats_per_sec
        end_beat = ev.end_sec * beats_per_sec
        qs = max(0, round(start_beat / slot_beats))
        qe = max(qs + 1, round(end_beat / slot_beats))
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
                                    midi_dir: Optional[str] = None, monophonic: bool = False) -> str:
    """Genera il testo finale e lo valida SEMPRE con validate_track_text
    prima di ritornarlo. Solleva ValueError se il risultato non e' valido
    (non dovrebbe mai accadere dato il design difensivo di events_to_tokens,
    ma nessun testo viene mai inserito in una traccia senza passare da qui)."""
    tokens = events_to_tokens(events, tempo_bpm, grid_denominator, ternary, monophonic=monophonic)
    text = " ".join(tokens)
    ok, msg = validate_track_text(text, patterns, default_octave=default_octave, midi_dir=midi_dir)
    if not ok:
        raise ValueError(tr("Conversione audio: token generati non validi ({msg}). Nessuna modifica applicata.", msg=msg))
    return text
