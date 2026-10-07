"""
Analisi audio per l'importazione (core.audio_pitch, core.audio_percussion),
in numpy: lettura dei WAV, rilevamento degli attacchi e stima dell'altezza.
Sostituisce aubio, che era la dipendenza piu' difficile da installare (in
particolare su macOS con Apple Silicon, dove spesso andava compilata).

Algoritmi pubblicati, riscritti da zero:
- attacchi: "spectral flux" logaritmico su un banco di filtri a
  semitoni, con il massimo sulle bande vicine del frame precedente per non
  scambiare il vibrato per un nuovo attacco (SuperFlux: S. Boeck,
  G. Widmer, "Maximum filter vibrato suppression for onset detection",
  DAFx 2013), e scelta dei picchi con soglia adattiva;
- altezza: YIN (A. de Cheveigne', H. Kawahara, "YIN, a fundamental
  frequency estimator for speech and music", JASA 2002), con la funzione
  differenza calcolata via FFT, soglia assoluta e interpolazione
  parabolica; la confidenza e' 1 meno il valore della funzione normalizzata
  nel minimo scelto (1 = periodicita' perfetta).
"""

from typing import Callable, List, Optional, Tuple

import numpy as np

# --- attacchi ---------------------------------------------------------------
ONSET_FRAME = 2048          # finestra dell'analisi spettrale (46 ms a 44.1 kHz)
ONSET_HOP = 256             # passo: 5.8 ms, per collocare bene gli attacchi
ONSET_FMIN, ONSET_FMAX = 30.0, 16000.0
ONSET_BANDS_PER_OCTAVE = 24
ONSET_LAG = 2               # frame di distanza nel confronto (SuperFlux: mu)
ONSET_MAX_BANDS = 3         # massimo sulle bande vicine (soppressione vibrato)
# Scelta dei picchi (in secondi): un picco deve essere il massimo in
# [-PRE_MAX, +POST_MAX] e superare la media in [-PRE_AVG, +POST_AVG] di
# DELTA volte la scala della funzione; due attacchi distano almeno COMBINE.
PRE_MAX, POST_MAX = 0.03, 0.03
PRE_AVG, POST_AVG = 0.10, 0.07
COMBINE = 0.03
MELODIC_DELTA = 0.35
PERCUSSIVE_DELTA = 0.25
SILENCE_DB = -60.0          # frame piu' deboli di cosi' (rispetto al picco) non danno attacchi
OFFSET_GUARD = 0.05         # secondi di livello confrontati prima e dopo un picco...
OFFSET_RATIO = 0.5          # ...dopo deve restare almeno a questa frazione di prima

# --- altezza ----------------------------------------------------------------
YIN_THRESHOLD = 0.15
OCTAVE_MARGIN = 0.1         # vedi yin: preferenza per il periodo piu' corto
YIN_MAX_HZ = 4200.0
_CHUNK_FRAMES = 256         # frame calcolati insieme (memoria contenuta)


def read_mono(path: str) -> Tuple[np.ndarray, int]:
    """Campioni float32 in [-1, 1] (media dei canali) e frequenza."""
    from .audio_tracks import read_wav
    data, rate = read_wav(path)
    data = np.asarray(data, dtype=np.float32)
    if data.ndim == 2:
        data = data.mean(axis=1)
    return np.ascontiguousarray(data, dtype=np.float32), int(rate)


def _frames(x: np.ndarray, size: int, hop: int) -> np.ndarray:
    """Frame centrati: il frame i copre [i*hop - size/2, i*hop + size/2)."""
    padded = np.concatenate([np.zeros(size // 2, np.float32), x, np.zeros(size // 2 + hop, np.float32)])
    n = 1 + len(x) // hop
    return np.lib.stride_tricks.sliding_window_view(padded, size)[::hop][:n]


def _log_filterbank(n_fft: int, rate: int) -> np.ndarray:
    """Filtri triangolari a quarti di tono tra ONSET_FMIN e ONSET_FMAX
    (matrice bin x bande), normalizzati ad area unitaria."""
    freqs = np.fft.rfftfreq(n_fft, 1.0 / rate)
    fmax = min(ONSET_FMAX, rate / 2.0)
    n_bands = int(np.log2(fmax / ONSET_FMIN) * ONSET_BANDS_PER_OCTAVE)
    centers = ONSET_FMIN * 2.0 ** (np.arange(n_bands + 2) / ONSET_BANDS_PER_OCTAVE)
    bins = np.unique(np.clip(np.searchsorted(freqs, centers), 1, len(freqs) - 1))
    fb = np.zeros((len(freqs), max(1, len(bins) - 2)), dtype=np.float32)
    for b in range(len(bins) - 2):
        lo, mid, hi = bins[b], bins[b + 1], bins[b + 2]
        fb[lo:mid + 1, b] = np.linspace(0.0, 1.0, mid - lo + 1)
        fb[mid:hi + 1, b] = np.linspace(1.0, 0.0, hi - mid + 1)
        fb[:, b] /= max(fb[:, b].sum(), 1e-9)
    return fb


def onset_strength(x: np.ndarray, rate: int,
                   progress: Optional[Callable[[float], None]] = None) -> Tuple[np.ndarray, np.ndarray]:
    """Funzione di rilevamento (SuperFlux) e livello (RMS) per frame; il
    frame i e' centrato sul campione i * ONSET_HOP."""
    window = np.hanning(ONSET_FRAME).astype(np.float32)
    fb = _log_filterbank(ONSET_FRAME, rate)
    frames = _frames(x, ONSET_FRAME, ONSET_HOP)
    n = len(frames)
    spec = np.empty((n, fb.shape[1]), dtype=np.float32)
    rms = np.empty(n, dtype=np.float32)
    step = 2048
    for s in range(0, n, step):
        block = frames[s:s + step]
        mag = np.abs(np.fft.rfft(block * window, axis=1)).astype(np.float32)
        spec[s:s + step] = np.log1p(mag @ fb * 10.0)
        rms[s:s + step] = np.sqrt(np.mean(block * block, axis=1))
        if progress:
            progress(min(1.0, (s + step) / max(n, 1)))
    # massimo sulle bande vicine del frame di confronto
    ref = spec.copy()
    for k in range(1, ONSET_MAX_BANDS // 2 + 1):
        ref[:, k:] = np.maximum(ref[:, k:], spec[:, :-k])
        ref[:, :-k] = np.maximum(ref[:, :-k], spec[:, k:])
    odf = np.zeros(n, dtype=np.float32)
    odf[ONSET_LAG:] = np.maximum(spec[ONSET_LAG:] - ref[:-ONSET_LAG], 0.0).sum(axis=1)
    # prima dell'inizio del file c'e' silenzio: un suono che parte subito e'
    # un attacco anche senza frame precedenti con cui confrontarlo
    odf[:ONSET_LAG] = spec[:ONSET_LAG].sum(axis=1)
    return odf, rms


def pick_peaks(odf: np.ndarray, rms: np.ndarray, rate: int, delta: float) -> List[int]:
    """Indici dei frame di attacco (vedi PRE_MAX/.../COMBINE)."""
    n = len(odf)
    if n == 0:
        return []
    fps = rate / ONSET_HOP
    pre_max, post_max = max(1, int(PRE_MAX * fps)), max(1, int(POST_MAX * fps))
    pre_avg, post_avg = max(1, int(PRE_AVG * fps)), max(1, int(POST_AVG * fps))
    combine = max(1, int(COMBINE * fps))
    padded = np.concatenate([np.zeros(pre_max), odf, np.zeros(post_max)])
    local_max = np.lib.stride_tricks.sliding_window_view(padded, pre_max + post_max + 1).max(axis=1)
    csum = np.concatenate([[0.0], np.cumsum(np.concatenate([np.zeros(pre_avg), odf, np.zeros(post_avg)]))])
    width = pre_avg + post_avg + 1
    mean = (csum[width:] - csum[:-width]) / width
    scale = _odf_scale(odf)
    loud = rms > float(rms.max()) * 10 ** (SILENCE_DB / 20.0)
    # un attacco non e' seguito da un calo del livello: la fine brusca di un
    # suono (uno scatto, un taglio) allarga lo spettro ma non e' una nota
    k = max(1, int(OFFSET_GUARD * fps))
    rcs = np.concatenate([[0.0], np.cumsum(rms.astype(np.float64))])
    idx = np.arange(n)
    before = (rcs[idx] - rcs[np.maximum(idx - k, 0)]) / np.maximum(idx - np.maximum(idx - k, 0), 1)
    after = (rcs[np.minimum(idx + k, n)] - rcs[idx]) / np.maximum(np.minimum(idx + k, n) - idx, 1)
    rising = after >= OFFSET_RATIO * before
    candidates = np.nonzero((odf >= local_max) & (odf > 0) & (odf >= mean + delta * scale) & loud
                            & rising)[0]
    peaks: List[int] = []
    for i in candidates:
        if peaks and i - peaks[-1] < combine:
            if odf[i] > odf[peaks[-1]]:
                peaks[-1] = int(i)
            continue
        peaks.append(int(i))
    return peaks


def refine_onset(x: np.ndarray, sample: int, rate: int) -> Tuple[int, bool]:
    """Sposta un attacco all'inizio della salita del livello, se nei
    dintorni c'e' una salita netta (un colpo, una nota pizzicata); se il
    livello non cambia (legato cantato) lo lascia dov'e'. Ritorna anche se
    la salita c'era."""
    block = 64
    # il picco del flusso arriva anche mezzo frame prima dell'attacco vero
    # (la finestra lo "vede" appena ci entra dal bordo): si cerca soprattutto avanti
    lo = sample - ONSET_FRAME // 4
    hi = min(len(x), sample + ONSET_FRAME // 2 + ONSET_FRAME // 4)
    seg = np.abs(x[max(0, lo):hi])
    if lo < 0:              # prima dell'inizio del file c'e' silenzio
        seg = np.concatenate([np.zeros(-lo, dtype=seg.dtype), seg])
    if len(seg) < 4 * block:
        return sample, False
    env = seg[:len(seg) // block * block].reshape(-1, block).max(axis=1)
    top = int(np.argmax(env))
    if top == 0:
        return sample, False
    first = int(np.nonzero(env[:top + 1] >= 0.5 * env[top])[0][0])
    # risale fino a dove il livello era ancora quello di prima (con le note
    # gravi i blocchi oscillano: un minimo locale non e' ancora l'inizio)
    floor = float(env[:top].min())
    base = floor + 0.1 * (float(env[top]) - floor)
    while first > 0 and env[first - 1] > base:
        first -= 1
    # salita netta solo se prima il livello era ben piu' basso (il tremolo e
    # le oscillazioni di una nota tenuta non lo sono)
    if first == 0 or float(env[:first].max()) >= 0.5 * float(env[top]):
        return sample, False
    return max(0, lo + first * block), True


def detect_onsets(x: np.ndarray, rate: int, percussive: bool = False,
                  progress: Optional[Callable[[float], None]] = None,
                  with_strength: bool = False):
    """Posizioni (campioni) degli attacchi, in ordine; con with_strength
    anche la forza di ciascuno (picco della funzione di rilevamento diviso
    per la sua scala, vedi pick_peaks): lista di (campione, forza)."""
    odf, rms = onset_strength(x, rate, progress)
    peaks = pick_peaks(odf, rms, rate, PERCUSSIVE_DELTA if percussive else MELODIC_DELTA)
    scale = _odf_scale(odf)
    found = {}
    w = max(1, int(OFFSET_GUARD * rate))
    for p in peaks:
        if p * ONSET_HOP + ONSET_FRAME // 2 > len(x):
            continue        # la finestra esce dal file: il taglio finale non e' un attacco
        pos, rose = refine_onset(x, p * ONSET_HOP, rate)
        # dopo un attacco il suono c'e' ancora; dopo un taglio no. Senza una
        # salita del livello (legato, o un taglio che la finestra ha visto
        # arrivare) si guarda oltre la finestra del frame
        after = pos if rose else p * ONSET_HOP + ONSET_FRAME // 2
        if _rms(x[after:after + w]) < OFFSET_RATIO * _rms(x[max(0, pos - w):pos]):
            continue
        found[pos] = max(found.get(pos, 0.0), float(odf[p]) / scale if scale > 0 else 0.0)
    ordered = sorted(found.items())
    return ordered if with_strength else [pos for pos, _ in ordered]


def _rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(x, dtype=np.float64)))) if len(x) else 0.0


def _odf_scale(odf: np.ndarray) -> float:
    """Scala della funzione di rilevamento: la media del quarto piu' alto
    dei valori non nulli (il rumore di fondo non conta, un brano forte o
    debole si comporta uguale)."""
    active = odf[odf > 0]
    return float(np.mean(np.sort(active)[-max(1, len(active) // 4):])) if len(active) else 0.0


def yin(x: np.ndarray, rate: int, buf_size: int, hop_size: int,
        threshold: float = YIN_THRESHOLD,
        progress: Optional[Callable[[float], None]] = None) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Stima YIN per frame centrati su i * hop_size: (centri in campioni,
    frequenze in Hz (0 = nessuna), confidenze 0-1)."""
    w = buf_size // 2                       # finestra d'integrazione
    tau_max = buf_size - w
    tau_min = max(2, int(rate / YIN_MAX_HZ))
    frames = _frames(x, buf_size, hop_size)
    n = len(frames)
    n_fft = 1 << int(np.ceil(np.log2(2 * buf_size)))
    freqs = np.zeros(n, dtype=np.float32)
    conf = np.zeros(n, dtype=np.float32)
    taus = np.arange(tau_max, dtype=np.float64)
    for s in range(0, n, _CHUNK_FRAMES):
        f = frames[s:s + _CHUNK_FRAMES].astype(np.float64)
        # d(tau) = e0 + e_tau - 2 r(tau)
        a = np.fft.rfft(f[:, :w], n_fft, axis=1)
        b = np.fft.rfft(f, n_fft, axis=1)
        r = np.fft.irfft(np.conj(a) * b, n_fft, axis=1)[:, :tau_max]
        sq = np.concatenate([np.zeros((len(f), 1)), np.cumsum(f * f, axis=1)], axis=1)
        e0 = sq[:, w:w + 1]
        e_tau = sq[:, w:w + tau_max] - sq[:, :tau_max]
        d = np.maximum(e0 + e_tau - 2.0 * r, 0.0)
        d[:, 0] = 0.0
        # funzione differenza normalizzata (media cumulativa)
        cum = np.cumsum(d[:, 1:], axis=1)
        dn = np.ones_like(d)
        dn[:, 1:] = d[:, 1:] * taus[1:] / np.maximum(cum, 1e-12)
        dn[:, :tau_min] = 1.0
        # primo minimo locale sotto soglia; se nessuno ci arriva, il primo
        # minimo locale quasi profondo quanto il minimo assoluto (il minimo
        # assoluto da solo cade spesso al doppio del periodo: errore d'ottava)
        inner = dn[:, 1:-1]
        local = (inner < dn[:, :-2]) & (inner <= dn[:, 2:])
        below = local & (inner < threshold)
        has = below.any(axis=1)
        gmin = inner.min(axis=1, keepdims=True)
        near = local & (inner <= gmin + OCTAVE_MARGIN)
        fallback = np.where(near.any(axis=1), np.argmax(near, axis=1), np.argmin(inner, axis=1))
        first = np.where(has, np.argmax(below, axis=1), fallback) + 1
        rows = np.arange(len(f))
        y0, y1, y2 = dn[rows, first - 1], dn[rows, first], dn[rows, np.minimum(first + 1, tau_max - 1)]
        denom = y0 - 2.0 * y1 + y2
        shift = np.where(np.abs(denom) > 1e-12, 0.5 * (y0 - y2) / np.where(denom == 0, 1, denom), 0.0)
        tau = first + np.clip(shift, -1.0, 1.0)
        silent = e0[:, 0] <= 1e-10
        freqs[s:s + len(f)] = np.where(silent, 0.0, rate / np.maximum(tau, 1.0))
        conf[s:s + len(f)] = np.where(silent, 0.0, np.clip(1.0 - y1, 0.0, 1.0))
        if progress:
            progress(min(1.0, (s + len(f)) / max(n, 1)))
    centers = np.arange(n, dtype=np.int64) * hop_size
    return centers, freqs, conf
