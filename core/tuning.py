"""
Accordatura: l'accordatore del dialogo di registrazione (nota e scarto in
cent di un blocco breve dell'ingresso, vedi gui.audio_record_dialog) e
l'avviso di ripresa scordata (di quanto una ripresa intera e' sopra o sotto
il La 440, corretto poi con AudioClip.transpose).
"""

import math
from typing import Optional, Tuple

import numpy as np

NOTE_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]

TUNER_BLOCK_SECONDS = 0.12     # quanto ingresso guarda l'accordatore a ogni lettura
TUNER_MIN_CONFIDENCE = 0.8     # sotto, l'altezza non e' affidabile (rumore, accordo)
TUNER_MIN_HZ, TUNER_MAX_HZ = 30.0, 2000.0
TUNER_MIN_LEVEL = 0.005        # sotto (-46 dB) e' silenzio

# Una ripresa scordata di almeno tanto (in semitoni: 0,15 = 15 cent) merita
# l'avviso; meno si sente appena.
DETUNE_WARN = 0.15
# Accordo minimo fra i picchi dello spettro (vedi audio_chords.tuning_and_strength):
# sotto, la ripresa non ha un'accordatura chiara (batteria, rumore).
DETUNE_MIN_STRENGTH = 0.35


def note_and_cents(freq_hz: float) -> Tuple[str, int]:
    """("A4", scarto in cent da quella nota, -50..50) di una frequenza."""
    midi = 69 + 12 * math.log2(freq_hz / 440.0)
    nearest = int(round(midi))
    return f"{NOTE_NAMES[nearest % 12]}{nearest // 12 - 1}", int(round((midi - nearest) * 100))


def block_pitch(x: np.ndarray, rate: int) -> Optional[float]:
    """Altezza (Hz) di un blocco breve mono dell'ingresso, None se e'
    silenzio o non e' una nota sola."""
    from .audio_dsp import yin
    x = np.asarray(x, dtype=np.float32).reshape(-1)
    if len(x) < 512 or float(np.max(np.abs(x))) < TUNER_MIN_LEVEL:
        return None
    buf = 4096 if len(x) >= 4096 else 2048 if len(x) >= 2048 else 1024
    _centers, freqs, confs = yin(x, rate, buf, buf // 4)
    ok = (confs >= TUNER_MIN_CONFIDENCE) & (freqs >= TUNER_MIN_HZ) & (freqs <= TUNER_MAX_HZ)
    if ok.sum() < 2:
        return None
    return float(np.median(freqs[ok]))


def samples_tuning(x: np.ndarray, rate: int) -> Optional[float]:
    """Di quanto (semitoni, -0.5..0.5) l'audio mono x e' sopra o sotto il
    La 440; None se non ha un'accordatura chiara."""
    from .audio_chords import FRAME, _spectrogram, tuning_and_strength
    x = np.asarray(x, dtype=np.float32).reshape(-1)
    if len(x) < FRAME or float(np.max(np.abs(x))) < TUNER_MIN_LEVEL:
        return None
    spec = _spectrogram(x)
    offset, strength = tuning_and_strength(spec, np.fft.rfftfreq(FRAME, 1.0 / rate))
    return offset if strength >= DETUNE_MIN_STRENGTH else None


def clip_tuning(clip) -> Optional[float]:
    """samples_tuning della parte suonata di una clip audio, come si sente
    (trasposizione compresa): la correzione e' clip.transpose - risultato."""
    import os
    import tempfile
    from .audio_dsp import read_mono
    from .audio_tracks import extract_clip_audio
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        extract_clip_audio(clip, path)
        x, rate = read_mono(path)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
    return samples_tuning(x, rate)


def detune_to_correct(offset: Optional[float]) -> bool:
    return offset is not None and abs(offset) >= DETUNE_WARN
