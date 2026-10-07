"""
Pipeline completa di importazione audio -> notazione testuale: decodifica
(se necessario) -> analisi (melodica o percussiva) -> quantizzazione sulla
griglia scelta -> validazione sintattica. Analogo di midi_import.py per il
percorso audio.
"""

import math
import os
from typing import Callable, Dict, List, Optional

from .audio_decode import decode_audio_file_to_wav
from .audio_quantize import AudioEvent, audio_events_to_validated_text, grid_slot_beats
from .notation import Pattern

# Dinamica: i rilevatori misurano il picco assoluto (una registrazione
# debole darebbe velocity 10, quasi muta). Si porta il colpo/la nota piu'
# forte a VELOCITY_TOP e gli altri in proporzione ai dB (VELOCITY_PER_DB),
# arrotondando a passi di VELOCITY_STEP: le piccole differenze naturali tra
# una nota e l'altra non riempiono il testo di "@".
VELOCITY_TOP = 110
VELOCITY_PER_DB = 1.5
VELOCITY_STEP = 10
VELOCITY_FLOOR = 30


class ConversionCancelled(Exception):
    """Sollevata dal progress_callback per interrompere la conversione."""


def normalize_velocities(events: List[AudioEvent]) -> List[AudioEvent]:
    loudest = max((ev.velocity for ev in events), default=0)
    for ev in events:
        db = 20.0 * math.log10(max(ev.velocity, 1) / max(loudest, 1))
        vel = VELOCITY_TOP + VELOCITY_PER_DB * db
        ev.velocity = int(max(VELOCITY_FLOOR, min(127, VELOCITY_STEP * round(vel / VELOCITY_STEP))))
    return events


def align_to_first_event(events: List[AudioEvent]) -> List[AudioEvent]:
    """Sposta tutto in modo che il primo evento cada sul tempo 0: per le
    registrazioni senza metronomo, dove l'istante in cui si preme Registra
    non e' legato al tempo del brano."""
    if events:
        shift = min(ev.start_sec for ev in events)
        for ev in events:
            ev.start_sec -= shift
            ev.end_sec -= shift
    return events


def convert_audio_to_track_text(source_path: str, is_percussion: bool, tempo_bpm: float,
                                 grid_denominator: int, ternary: bool,
                                 patterns: Dict[str, Pattern], default_octave: int = 4,
                                 midi_dir: Optional[str] = None,
                                 already_wav: bool = False,
                                 min_freq_hz: Optional[float] = None,
                                 voice_source: bool = False,
                                 buf_size: Optional[int] = None,
                                 hop_size: Optional[int] = None,
                                 pitch_confidence_threshold: Optional[float] = None,
                                 min_note_duration_sec: Optional[float] = None,
                                 progress_callback: Optional[Callable[[float], None]] = None,
                                 align_to_first_note: bool = False) -> str:
    """Converte un file audio (o un WAV gia' registrato dal microfono, se
    already_wav=True) nel testo di notazione da inserire nella traccia
    corrente. Solleva RuntimeError se il file non si puo' leggere (vedi
    core.audio_decode), ValueError se (teoricamente mai) il testo generato
    non supera la validazione sintattica.

    already_wav va impostato SOLO per il WAV prodotto da
    core.audio_recorder.MicRecorder.stop() (gia' nel formato normalizzato
    mono/44100Hz/16-bit): un file .wav scelto manualmente dall'utente deve
    comunque passare dalla decodifica, per garantire lo stesso formato
    atteso dai moduli di analisi indipendentemente da come e' stato
    codificato dalla sorgente originale.

    voice_source=True indica che l'audio e' voce/beatbox (non lo strumento
    reale): per la batteria ricalibra la classificazione kick/snare/hihat
    su un timbro vocale invece che su una batteria vera (vedi
    core.audio_percussion). Per la parte melodica non serve un parametro
    dedicato qui: e' il chiamante a passare (o non passare) min_freq_hz in
    base allo strumento di destinazione.

    buf_size, hop_size, pitch_confidence_threshold e min_note_duration_sec
    sono override opzionali dei parametri di core.audio_pitch.detect_melodic_notes
    (lasciati a None si usano i default automatici): permettono di adattare
    il rilevamento del pitch caso per caso su un audio specifico, invece di
    dover modificare le costanti nel codice. Ignorati per la batteria.

    align_to_first_note=True fa partire il testo dalla prima nota (vedi
    align_to_first_event). Per interrompere la conversione, il
    progress_callback puo' sollevare ConversionCancelled."""
    from .audio_pitch import detect_melodic_notes
    from .audio_percussion import detect_percussive_hits

    def _report(frac, lo, hi):
        if progress_callback:
            progress_callback(lo + frac * (hi - lo))

    wav_path = source_path
    cleanup = False
    try:
        if not already_wav:
            wav_path = decode_audio_file_to_wav(source_path)
            cleanup = True
        _report(1.0, 0.0, 0.2)

        if is_percussion:
            slot_s = grid_slot_beats(grid_denominator, ternary) * 60.0 / tempo_bpm
            events = detect_percussive_hits(wav_path, beatbox=voice_source, slot_s=slot_s,
                                             progress_callback=lambda f: _report(f, 0.2, 0.85))
        else:
            events = detect_melodic_notes(wav_path, hop_size=hop_size, buf_size=buf_size,
                                           min_freq_hz=min_freq_hz,
                                           confidence_threshold=pitch_confidence_threshold,
                                           min_note_duration_sec=min_note_duration_sec,
                                           progress_callback=lambda f: _report(f, 0.2, 0.85))

        normalize_velocities(events)
        if align_to_first_note:
            align_to_first_event(events)
        text = audio_events_to_validated_text(
            events, tempo_bpm, grid_denominator, ternary, patterns,
            default_octave=default_octave, midi_dir=midi_dir, monophonic=not is_percussion,
        )
        _report(1.0, 0.85, 1.0)
        return text
    finally:
        if cleanup and wav_path and os.path.exists(wav_path):
            os.remove(wav_path)
