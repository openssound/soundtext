#!/usr/bin/env python3
"""
Strumento diagnostico per calibrare l'analisi audio (pitch detection per le
tracce melodiche, classificazione kick/snare/hihat per la batteria) su
registrazioni reali, invece di indovinare le soglie alla cieca.

Per ogni nota/colpo rilevato stampa i dati grezzi usati dalla
classificazione (frequenza, bande di energia, ecc.): incolla l'output di
questo script quando segnali un problema di riconoscimento, cosi' la
calibrazione puo' basarsi su numeri reali invece che su ipotesi.

Uso:
    python3 diagnose_audio.py --melodic registrazione.wav
    python3 diagnose_audio.py --percussion registrazione.wav
    python3 diagnose_audio.py --percussion --wav-only file_gia_wav.wav

Se il file non e' gia' un .wav mono/44100Hz/16-bit (es. un .mp3/.m4a, o un
.wav non normalizzato), viene decodificato (core.audio_decode: Qt Multimedia, o ffmpeg);
con --wav-only si salta la decodifica (solo per un .wav gia'
nel formato corretto).
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _resolve_wav(path: str, wav_only: bool) -> str:
    if wav_only:
        return path
    from core.audio_decode import decode_audio_file_to_wav
    print(f"Decodifica '{path}' in WAV normalizzato (mono/44100Hz/16-bit)...", file=sys.stderr)
    return decode_audio_file_to_wav(path)


def diagnose_melodic(path: str, wav_only: bool, confidence_threshold, min_note_duration_ms):
    from core.audio_pitch import detect_melodic_notes, PITCH_CONFIDENCE_THRESHOLD
    from core.chords import midi_to_token

    wav_path = _resolve_wav(path, wav_only)
    min_note_duration_sec = None if min_note_duration_ms is None else min_note_duration_ms / 1000.0
    used_threshold = confidence_threshold if confidence_threshold is not None else PITCH_CONFIDENCE_THRESHOLD
    print(f"Soglia di confidenza usata: {used_threshold}")
    events = detect_melodic_notes(
        wav_path, confidence_threshold=confidence_threshold, min_note_duration_sec=min_note_duration_sec,
    )

    print(f"{'inizio(s)':>10}  {'fine(s)':>8}  {'durata(ms)':>10}  {'MIDI':>4}  {'nota':>6}  {'velocity':>8}")
    for ev in events:
        dur_ms = (ev.end_sec - ev.start_sec) * 1000
        note_name = midi_to_token(ev.midi_pitch)
        print(f"{ev.start_sec:10.3f}  {ev.end_sec:8.3f}  {dur_ms:10.1f}  {ev.midi_pitch:4d}  {note_name:>6}  {ev.velocity:8d}")
    print(f"\nTotale note rilevate: {len(events)}")
    if events:
        durations = [ev.end_sec - ev.start_sec for ev in events]
        print(f"Durata media nota: {1000 * sum(durations) / len(durations):.1f} ms "
              f"(min {1000 * min(durations):.1f} ms, max {1000 * max(durations):.1f} ms)")
        print("Se vedi tante note brevissime consecutive sulla stessa zona di altezza: probabile "
              "instabilita' di intonazione (vibrato/oscillazione) che frammenta una nota sola in tante.")
    else:
        print("Nessuna nota rilevata: ogni segmento tra un onset e il successivo non ha frame con "
              "confidenza >= alla soglia sopra. Prova ad abbassarla con --confidence-threshold "
              "per vedere se il problema e' la soglia o se davvero non c'e' pitch rilevabile nel segnale.")


def diagnose_percussion(path: str, wav_only: bool):
    import numpy as np

    from core.audio_percussion import (
        detect_onset_samples, estimate_noise_floor, suppress_duplicate_onsets,
        _read_window, _classify_band, compute_band_ratios,
        SKIP_SAMPLES, CLASSIFY_WINDOW_SAMPLES, DEFAULT_HOP_SIZE, LOW_FREQ_HZ,
        BEATBOX_LOW_FREQ_HZ, KICK_LOW_RATIO, BEATBOX_KICK_LOW_RATIO,
    )

    wav_path = _resolve_wav(path, wav_only)
    onset_samples_raw, samplerate = detect_onset_samples(wav_path)
    noise_spectrum = estimate_noise_floor(wav_path, onset_samples_raw, samplerate)
    onset_samples = suppress_duplicate_onsets(wav_path, onset_samples_raw, samplerate)

    print(f"Soglie attuali — normale: banda bassa <{LOW_FREQ_HZ}Hz, soglia kick {KICK_LOW_RATIO}; "
          f"beatbox: banda bassa <{BEATBOX_LOW_FREQ_HZ}Hz, soglia kick {BEATBOX_KICK_LOW_RATIO}")
    if noise_spectrum is not None:
        peak_bin = int(np.argmax(noise_spectrum))
        peak_freq = peak_bin * samplerate / CLASSIFY_WINDOW_SAMPLES
        print(f"Rumore di fondo stimato dai tratti di silenzio pre-colpo: picco a {peak_freq:.1f}Hz "
              "(sottratto da ogni colpo prima della classificazione).")
    else:
        print("Rumore di fondo non stimabile (nessun tratto di silenzio pre-colpo sufficiente): "
              "classificazione senza sottrazione del rumore.")
    print(f"Onset grezzi: {len(onset_samples_raw)} — dopo soppressione doppioni "
          f"(picco massimo entro finestra): {len(onset_samples)}.")
    print()
    print(f"{'inizio(s)':>10}  {'low':>6}  {'mid':>6}  {'high':>6}  {'normale':>9}  {'beatbox':>9}  {'velocity':>8}")

    counts = {"normale": {}, "beatbox": {}}
    for onset_sample in onset_samples:
        window = _read_window(wav_path, onset_sample + SKIP_SAMPLES, CLASSIFY_WINDOW_SAMPLES, DEFAULT_HOP_SIZE)
        low, mid, high = compute_band_ratios(window, samplerate, noise_spectrum=noise_spectrum)
        name_normal, velocity = _classify_band(window, samplerate, beatbox=False, noise_spectrum=noise_spectrum)
        name_beatbox, _ = _classify_band(window, samplerate, beatbox=True, noise_spectrum=noise_spectrum)
        counts["normale"][name_normal] = counts["normale"].get(name_normal, 0) + 1
        counts["beatbox"][name_beatbox] = counts["beatbox"].get(name_beatbox, 0) + 1
        start_sec = onset_sample / float(samplerate)
        print(f"{start_sec:10.3f}  {low:6.3f}  {mid:6.3f}  {high:6.3f}  {name_normal:>9}  {name_beatbox:>9}  {velocity:8d}")

    print(f"\nTotale colpi rilevati: {len(onset_samples)}")
    print(f"Conteggio (modalita' normale): {counts['normale']}")
    print(f"Conteggio (modalita' beatbox): {counts['beatbox']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--melodic", action="store_true", help="analizza come traccia melodica (pitch detection)")
    mode.add_argument("--percussion", action="store_true", help="analizza come traccia percussiva (kick/snare/hihat)")
    parser.add_argument("--wav-only", action="store_true",
                         help="salta la decodifica (solo per un .wav gia' mono/44100Hz/16-bit)")
    parser.add_argument("--confidence-threshold", type=float, default=None,
                         help="soglia di confidenza (0-1, solo --melodic); default automatico")
    parser.add_argument("--min-note-duration-ms", type=float, default=None,
                         help="durata minima di una nota in ms; default automatico (30ms)")
    parser.add_argument("file", help="file audio da analizzare (.wav/.mp3/.m4a)")
    args = parser.parse_args()

    if args.melodic:
        diagnose_melodic(args.file, args.wav_only, args.confidence_threshold, args.min_note_duration_ms)
    else:
        diagnose_percussion(args.file, args.wav_only)


if __name__ == "__main__":
    main()
