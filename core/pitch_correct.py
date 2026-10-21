"""
Correzione dell'intonazione di una clip (AudioClip.pitch_correct): ogni
nota cantata o suonata si avvicina alla nota della scala piu' vicina, di
tanto quanto dice la forza (100% = esattamente sulla nota). Nota per nota,
non istante per istante: il vibrato e le inflessioni dentro la nota
restano, si sposta solo il suo centro.

1. altezza ogni HOP campioni (YIN, core.audio_dsp.yin);
2. le note: tratti di stime confidenti che restano entro mezzo semitono
   dalla loro mediana per almeno MIN_NOTE_SECONDS;
3. per ogni nota lo scarto fra la mediana e la nota della scala piu' vicina
   (tonalita' del brano, o stimata dalle note), per la forza;
4. una curva di trasposizione per campione, con rampe di RAMP_SECONDS fra
   una nota e l'altra, passata al time-stretch (pedalboard, vedi
   core.audio_tracks.stretched), che la applica senza cambiare la durata.
"""

from typing import List, Optional, Tuple

import numpy as np

BUF = 2048
HOP = 256
CONFIDENCE = 0.8
MIN_NOTE_SECONDS = 0.06
RAMP_SECONDS = 0.03
MIN_HZ, MAX_HZ = 60.0, 1500.0

MAJOR = (0, 2, 4, 5, 7, 9, 11)
MINOR = (0, 2, 3, 5, 7, 8, 10)


def detect_notes(x: np.ndarray, rate: int) -> List[Tuple[int, int, float]]:
    """[(primo campione, ultimo campione, altezza mediana in semitoni MIDI)]
    delle note di x (mono)."""
    from .audio_dsp import yin
    if len(x) < BUF:
        return []
    centers, freqs, confs = yin(np.ascontiguousarray(x, dtype=np.float32), rate, BUF, HOP)
    ok = (confs >= CONFIDENCE) & (freqs >= MIN_HZ) & (freqs <= MAX_HZ)
    midi = np.where(ok, 69.0 + 12.0 * np.log2(np.maximum(freqs, 1e-6) / 440.0), np.nan)
    notes = []
    min_frames = max(2, int(MIN_NOTE_SECONDS * rate / HOP))
    i = 0
    while i < len(midi):
        if np.isnan(midi[i]):
            i += 1
            continue
        j = i + 1
        while j < len(midi) and not np.isnan(midi[j]) and abs(midi[j] - np.median(midi[i:j])) < 0.5:
            j += 1
        if j - i >= min_frames:
            first = max(0, int(centers[i]) - HOP // 2)
            last = min(len(x), int(centers[j - 1]) + HOP // 2)
            notes.append((first, last, float(np.median(midi[i:j]))))
        i = j
    return notes


def _scale(key: Optional[str], notes) -> List[int]:
    from .rhythm_generate import parse_key
    if key and key.strip():
        tonic, mode, _flats = parse_key(key)
    else:
        from .harmonize import melody_key
        guess = melody_key([(a, b - a, int(round(m))) for a, b, m in notes]) if notes else "C"
        tonic, mode, _flats = parse_key(guess)
    return sorted((tonic + s) % 12 for s in (MAJOR if mode == "major" else MINOR))


def _nearest_in_scale(midi: float, scale: List[int]) -> float:
    base = int(np.floor(midi))
    candidates = [n for n in range(base - 2, base + 3) if n % 12 in scale]
    return float(min(candidates, key=lambda n: abs(n - midi)))


def correction_curve(x: np.ndarray, rate: int, strength: float, key: Optional[str] = None) -> np.ndarray:
    """Semitoni di trasposizione per campione (float64, lunga quanto x mono)
    che portano ogni nota verso la scala, per 'strength' (0-1)."""
    curve = np.zeros(len(x), dtype=np.float64)
    notes = detect_notes(x, rate)
    if not notes or strength <= 0:
        return curve
    scale = _scale(key, notes)
    ramp = max(1, int(RAMP_SECONDS * rate))
    shifts = [(a, b, (_nearest_in_scale(m, scale) - m) * min(1.0, strength)) for a, b, m in notes]
    prev_end, prev_value = 0, shifts[0][2]
    for a, b, value in shifts:
        # fra una nota e l'altra la correzione resta, poi cambia con una rampa
        curve[prev_end:a] = prev_value
        r = min(ramp, max(1, b - a) // 2)
        curve[a:a + r] = np.linspace(prev_value, value, r)
        curve[a + r:b] = value
        prev_end, prev_value = b, value
    curve[prev_end:] = prev_value
    return curve
