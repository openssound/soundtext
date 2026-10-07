"""
Genera i file WAV usati dal click del metronomo: un suono 'accento' (primo
movimento di ogni battuta) e uno 'normale' (gli altri) per ciascun preset,
sintetizzati con la sola libreria standard (nessuna dipendenza aggiuntiva) e
salvati in cache su disco cosi' da generarli una sola volta per macchina.
"""

import math
import os
import random
import struct
import wave

from .settings import CONFIG_DIR

SOUND_DIR = os.path.join(CONFIG_DIR, "metronome")

# nome preset -> (frequenza click accento Hz, frequenza click normale Hz,
#                 forma d'onda, decadimento 1/s, durata ms)
SOUND_PRESETS = {
    "Click": (1600, 1100, "sine", 45.0, 35),
    "Beep": (1400, 950, "square", 45.0, 35),
    "Legno": (1800, 900, "noise", 45.0, 35),
    "Blocco di legno": (1500, 1000, "woodblock", 70.0, 70),
    "Claves": (2600, 2000, "sine", 120.0, 60),
    "Campanaccio": (800, 540, "cowbell", 20.0, 130),
    "Triangolo": (2200, 1700, "bell", 14.0, 280),
    "Hi-hat": (9000, 7000, "hihat", 80.0, 60),
}

DEFAULT_SOUND = "Click"
SAMPLE_RATE = 44100


def _wave_value(waveform: str, freq: float, t: float, prev_noise: list) -> float:
    if waveform == "square":
        return 1.0 if (t * freq) % 1.0 < 0.5 else -1.0
    if waveform == "noise":
        return random.uniform(-1.0, 1.0)
    if waveform == "hihat":
        # rumore filtrato passa-alto (differenza fra campioni successivi)
        x = random.uniform(-1.0, 1.0)
        out = (x - prev_noise[0]) * 0.5
        prev_noise[0] = x
        return out
    if waveform == "woodblock":
        return 0.8 * math.sin(2 * math.pi * freq * t) + 0.35 * math.sin(2 * math.pi * freq * 2.3 * t)
    if waveform == "cowbell":
        # due onde quadre quasi in quinta, come nel campanaccio classico
        p1 = 1.0 if (t * freq) % 1.0 < 0.5 else -1.0
        p2 = 1.0 if (t * freq * 1.48) % 1.0 < 0.5 else -1.0
        return 0.5 * (p1 + p2)
    if waveform == "bell":
        # parziali inarmoniche, come un triangolo metallico
        return (0.6 * math.sin(2 * math.pi * freq * t)
                + 0.3 * math.sin(2 * math.pi * freq * 2.76 * t)
                + 0.2 * math.sin(2 * math.pi * freq * 5.4 * t))
    return math.sin(2 * math.pi * freq * t)  # sine


def _synth_click(freq: float, waveform: str, duration_ms: int = 35, decay: float = 45.0) -> bytes:
    """Un breve impulso con inviluppo a decadimento rapido (tipico di un
    click percussivo), nella forma d'onda richiesta."""
    n = int(SAMPLE_RATE * duration_ms / 1000)
    samples = []
    prev_noise = [0.0]
    for i in range(n):
        t = i / SAMPLE_RATE
        envelope = math.exp(-t * decay)
        raw = _wave_value(waveform, freq, t, prev_noise)
        value = max(-1.0, min(1.0, raw * envelope))
        samples.append(int(value * 32767))
    return struct.pack("<%dh" % n, *samples)


def _write_wav(path: str, pcm_data: bytes):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm_data)


def ensure_click_sound_files(name: str):
    """Ritorna (percorso_click_accento, percorso_click_normale) per il
    preset `name` (uno di SOUND_PRESETS, altrimenti DEFAULT_SOUND),
    generandoli su disco alla prima richiesta."""
    if name not in SOUND_PRESETS:
        name = DEFAULT_SOUND
    os.makedirs(SOUND_DIR, exist_ok=True)
    accent_path = os.path.join(SOUND_DIR, f"{name}_accent.wav")
    normal_path = os.path.join(SOUND_DIR, f"{name}_normal.wav")
    freq_accent, freq_normal, waveform, decay, duration_ms = SOUND_PRESETS[name]
    if not os.path.exists(accent_path):
        _write_wav(accent_path, _synth_click(freq_accent, waveform, duration_ms, decay))
    if not os.path.exists(normal_path):
        _write_wav(normal_path, _synth_click(freq_normal, waveform, duration_ms, decay))
    return accent_path, normal_path
