"""
Riduzione del rumore di fondo (effetto "Riduzione rumore", vedi
core.effects): toglie il fruscio costante (ventola, amplificatore, preamp)
imparandolo dal tratto piu' silenzioso della traccia, con la sottrazione
spettrale classica:

1. STFT (finestra di Hann, FRAME campioni, passo HOP);
2. profilo del rumore: la media dello spettro nei PROFILE_SECONDS piu'
   silenziosi (ma non muti: fra una clip e l'altra il silenzio digitale non
   dice niente del rumore);
3. per ogni bin un guadagno 1 - soglia*rumore/ampiezza, mai sotto
   -'riduzione' dB, levigato nel tempo (meno "rumore musicale");
4. ricostruzione per sovrapposizione e somma.

Solo numpy, a blocchi (una traccia lunga non occupa troppa memoria).
"""

import numpy as np

FRAME = 2048
HOP = FRAME // 4
PROFILE_SECONDS = 0.5
DIGITAL_SILENCE = 1e-5         # RMS sotto il quale un tratto e' silenzio digitale, non rumore
SMOOTHING = 0.6                # quanto il guadagno di un bin segue quello del frame prima
_BLOCK_FRAMES = 1024


def _window() -> np.ndarray:
    return np.hanning(FRAME + 1)[:-1].astype(np.float32)


def _frames_rms(x: np.ndarray) -> np.ndarray:
    n = max(0, 1 + (len(x) - FRAME) // HOP)
    if n == 0:
        return np.zeros(0)
    idx = np.arange(FRAME)[None, :] + HOP * np.arange(n)[:, None]
    return np.sqrt(np.mean(np.square(x[idx], dtype=np.float64), axis=1))


def noise_profile(x: np.ndarray, rate: int):
    """Lo spettro medio (ampiezza per bin) del tratto piu' silenzioso di x
    (mono), o None se non c'e' un tratto di rumore abbastanza lungo."""
    rms = _frames_rms(x)
    count = max(2, int(PROFILE_SECONDS * rate / HOP))
    if len(rms) < count:
        return None
    candidates = np.flatnonzero(rms > DIGITAL_SILENCE)
    if len(candidates) < count:
        return None
    # la finestra di 'count' frame consecutivi (non muti) con l'energia minore
    alive = rms > DIGITAL_SILENCE
    energy = np.where(alive, rms, np.inf)
    sums = np.convolve(energy, np.ones(count), mode="valid")
    start = int(np.argmin(sums))
    if not np.isfinite(sums[start]):
        return None
    window = _window()
    idx = np.arange(FRAME)[None, :] + HOP * (start + np.arange(count))[:, None]
    spec = np.abs(np.fft.rfft(x[idx] * window, axis=1))
    return spec.mean(axis=0)


def reduce_noise(samples: np.ndarray, rate: int, reduction_db: float = 12.0, threshold_db: float = 6.0,
                 profile=None) -> np.ndarray:
    """samples (frame, canali) con il rumore di fondo attenuato fino a
    'reduction_db'; 'threshold_db' sopra il profilo un bin si considera
    suono e resta. Il profilo si impara dal tratto piu' silenzioso della
    media dei canali (o si passa gia' fatto). Se non c'e' un tratto di
    rumore, torna samples com'e'."""
    x = np.asarray(samples, dtype=np.float32)
    if x.ndim == 1:
        x = x[:, None]
    if len(x) < FRAME * 2 or reduction_db <= 0:
        return samples
    if profile is None:
        profile = noise_profile(x.mean(axis=1), rate)
    if profile is None:
        return samples
    floor = 10.0 ** (-reduction_db / 20.0)
    over = 10.0 ** (threshold_db / 20.0) * profile
    window = _window()
    pad = FRAME
    total = len(x) + 2 * pad + HOP + FRAME
    out = np.zeros((total, x.shape[1]), dtype=np.float32)
    norm = np.zeros(total, dtype=np.float32)
    for ch in range(x.shape[1]):
        sig = np.concatenate([np.zeros(pad, np.float32), x[:, ch], np.zeros(pad + HOP, np.float32)])
        n = 1 + (len(sig) - FRAME) // HOP
        prev_gain = np.ones(len(profile), dtype=np.float32)
        for first in range(0, n, _BLOCK_FRAMES):
            count = min(_BLOCK_FRAMES, n - first)
            idx = np.arange(FRAME)[None, :] + HOP * (first + np.arange(count))[:, None]
            spec = np.fft.rfft(sig[idx] * window, axis=1)
            mag = np.abs(spec)
            gain = np.clip(1.0 - over[None, :] / np.maximum(mag, 1e-12), floor, 1.0).astype(np.float32)
            for i in range(count):                    # levigato nel tempo
                gain[i] = SMOOTHING * prev_gain + (1 - SMOOTHING) * gain[i]
                prev_gain = gain[i]
            frames = np.fft.irfft(spec * gain, n=FRAME, axis=1).astype(np.float32) * window
            for i in range(count):
                pos = (first + i) * HOP
                out[pos:pos + FRAME, ch] += frames[i]
                if ch == 0:
                    norm[pos:pos + FRAME] += window * window
    norm = np.maximum(norm, 1e-6)
    y = out / norm[:, None]
    return np.ascontiguousarray(y[pad:pad + len(x)], dtype=np.float32)
