"""
Beat tracking: il battito di una ripresa suonata libera, senza click, per
ricavarne la mappa del tempo del brano (un cambio di tempo per battuta,
come quelli che l'import MIDI gia' crea: Project.tempo_changes).

Metodo (classico, solo numpy, come in Ellis 2007):
  1. inviluppo degli attacchi: per ogni finestra (FRAME/HOP) l'aumento
     dell'energia, banda per banda in scala logaritmica (spectral flux);
  2. tempo medio: autocorrelazione dell'inviluppo fra MIN_BPM e MAX_BPM,
     pesata verso i tempi piu' comuni (attorno a PRIOR_BPM);
  3. battiti: programmazione dinamica che sceglie gli istanti con gli
     attacchi piu' forti, con una penalita' per gli intervalli lontani dal
     periodo medio (cosi' segue chi accelera e rallenta, ma non salta);
  4. battute: il primo battito della ripresa e' l'inizio di una battuta;
     ogni battuta ha il suo tempo in BPM interi, scelti compensando gli
     arrotondamenti delle precedenti, cosi' i battiti non si allontanano
     da quelli suonati.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

FRAME = 2048
HOP = 512
MIN_BPM, MAX_BPM = 50.0, 200.0
PRIOR_BPM = 110.0          # i tempi piu' probabili stanno attorno a questo (un'ottava di tolleranza)
TIGHTNESS = 60.0           # quanto costa un intervallo lontano dal periodo medio
ONSET_THRESHOLD = 0.15     # frazione del massimo dell'inviluppo da cui la musica "c'e'"


def _mono(samples: np.ndarray) -> np.ndarray:
    x = np.asarray(samples, dtype=np.float32)
    return x.mean(axis=1) if x.ndim == 2 else x


def onset_envelope(samples: np.ndarray, rate: int) -> Tuple[np.ndarray, float]:
    """(inviluppo degli attacchi, frame al secondo): quanto cresce l'energia
    in ogni finestra, normalizzato (media 0 lontano dagli attacchi)."""
    x = _mono(samples)
    if len(x) < FRAME:
        x = np.concatenate([x, np.zeros(FRAME - len(x), np.float32)])
    n = 1 + (len(x) - FRAME) // HOP
    window = np.hanning(FRAME).astype(np.float32)
    frames = np.lib.stride_tricks.as_strided(x, shape=(n, FRAME), strides=(x.strides[0] * HOP, x.strides[0]))
    spec = np.abs(np.fft.rfft(frames * window, axis=1))
    # 40 bande logaritmiche fra 30 Hz e 8 kHz
    freqs = np.fft.rfftfreq(FRAME, 1.0 / rate)
    edges = np.geomspace(30.0, min(8000.0, rate / 2 - 1), 41)
    band = np.digitize(freqs, edges) - 1
    bands = np.zeros((n, 40), np.float32)
    for b in range(40):
        mask = band == b
        if mask.any():
            bands[:, b] = spec[:, mask].sum(axis=1)
    log = np.log1p(100.0 * bands)
    flux = np.maximum(0.0, np.diff(log, axis=0, prepend=log[:1])).sum(axis=1)
    # via l'andamento lento (crescendo, rumore): restano gli attacchi
    k = max(1, min(len(flux), int(round(0.5 * rate / HOP))))   # piu' corta del segnale: "same" non lo allunga
    smooth = np.convolve(flux, np.ones(k) / k, mode="same")
    env = np.maximum(0.0, flux - smooth)
    std = env.std()
    return (env / std if std > 0 else env), rate / float(HOP)


def estimate_period(env: np.ndarray, fps: float) -> float:
    """Il periodo medio del battito, in frame (vedi modulo, punto 2)."""
    lo = int(round(fps * 60.0 / MAX_BPM))
    hi = min(len(env) - 1, int(round(fps * 60.0 / MIN_BPM)))
    if hi <= lo:
        return fps * 60.0 / PRIOR_BPM
    centered = env - env.mean()
    ac = np.correlate(centered, centered, mode="full")[len(env) - 1:]
    lags = np.arange(lo, hi + 1)
    bpm = 60.0 * fps / lags
    weight = np.exp(-0.5 * (np.log2(bpm / PRIOR_BPM) / 1.0) ** 2)
    best = lags[int(np.argmax(ac[lo:hi + 1] * weight))]
    # interpolazione parabolica del picco, per un periodo non intero
    if lo < best < hi:
        a, b, c = ac[best - 1], ac[best], ac[best + 1]
        denom = a - 2 * b + c
        if denom < 0:
            return best + 0.5 * (a - c) / denom
    return float(best)


def track_beats(env: np.ndarray, period: float, tightness: float = TIGHTNESS) -> np.ndarray:
    """Gli istanti (in frame) dei battiti, con la programmazione dinamica."""
    n = len(env)
    if n == 0:
        return np.zeros(0, int)
    score = env.astype(np.float64).copy()
    back = np.full(n, -1, int)
    lo, hi = max(1, int(round(period / 2))), max(2, int(round(2 * period)))
    offsets = np.arange(lo, hi + 1)
    penalty = -tightness * np.log(offsets / period) ** 2
    for t in range(lo, n):
        prev = t - offsets
        ok = prev >= 0
        if not ok.any():
            continue
        cand = score[prev[ok]] + penalty[ok]
        i = int(np.argmax(cand))
        if cand[i] > 0:
            score[t] = env[t] + cand[i]
            back[t] = prev[ok][i]
    # l'ultimo battito: il punteggio migliore nell'ultimo periodo
    tail = max(0, n - int(round(period)))
    t = tail + int(np.argmax(score[tail:]))
    beats = [t]
    while back[t] >= 0:
        t = back[t]
        beats.append(t)
    return np.array(beats[::-1])


@dataclass
class BeatAnalysis:
    beats: List[float]                    # secondi dei battiti, dal primo attacco all'ultimo
    beats_per_bar: int                    # battiti per battuta (quarti, o semiminime puntate in 6/8)
    beat_quarters: float                  # quarti per battito (1, o 1.5 nei tempi composti)
    bar_tempos: List[int] = field(default_factory=list)   # BPM (in quarti) di ogni battuta

    @property
    def first_beat(self) -> float:
        return self.beats[0] if self.beats else 0.0

    @property
    def bars(self) -> int:
        return len(self.bar_tempos)

    @property
    def mean_bpm(self) -> float:
        if len(self.beats) < 2:
            return 0.0
        period = (self.beats[-1] - self.beats[0]) / (len(self.beats) - 1)
        return 60.0 * self.beat_quarters / period


def meter_beats(time_sig: str) -> Tuple[int, float]:
    """(battiti per battuta, quarti per battito) della metrica: nei tempi
    composti (6/8, 9/8, 12/8) il battito e' la semiminima puntata."""
    try:
        num, den = (int(x) for x in str(time_sig).split("/"))
    except ValueError:
        num, den = 4, 4
    if den == 8 and num % 3 == 0 and num > 3:
        return num // 3, 1.5
    quarters_per_bar = 4.0 * num / max(1, den)
    unit = 4.0 / max(1, den) if den > 4 else 1.0
    return max(1, int(round(quarters_per_bar / unit))), unit


def bar_tempos(beats: List[float], beats_per_bar: int, beat_quarters: float) -> List[int]:
    """Un tempo intero per battuta completa (piu' l'ultima incompleta se ha
    almeno due battiti), scelto perche' la fine della battuta resti il piu'
    vicino possibile al battito suonato: l'errore di arrotondamento di una
    battuta si recupera nella successiva."""
    out: List[int] = []
    if len(beats) < 2:
        return out
    t_grid = beats[0]                    # dove la mappa a BPM interi mette l'inizio della battuta
    i = 0
    while i + 1 < len(beats):
        j = min(i + beats_per_bar, len(beats) - 1)
        count = j - i
        if count < beats_per_bar and count < 2:
            break
        target = beats[j]                # fine (vera) di questi 'count' battiti
        exact = 60.0 * beat_quarters * count / max(1e-6, target - t_grid)
        bpm = int(round(exact))
        bpm = max(20, min(400, bpm))
        out.append(bpm)
        t_grid += 60.0 * beat_quarters * count / bpm
        i = j
        if count < beats_per_bar:
            break
    return out


def _attack_time(samples: np.ndarray, rate: int, approx: float) -> float:
    """Il punto in cui comincia davvero l'attacco vicino ad 'approx': la
    finestra dell'inviluppo lo colloca con una decina di millisecondi
    d'anticipo o di ritardo, che per allineare la clip alla battuta contano."""
    a, b = max(0, int((approx - 0.04) * rate)), min(len(samples), int((approx + 0.06) * rate))
    if b - a < 16:
        return approx
    part = np.abs(_mono(samples[a:b]))            # solo la finestra, non tutto il segnale
    k = max(1, int(0.002 * rate))                       # inviluppo su 2 ms
    env = np.convolve(part, np.ones(k) / k, mode="same")
    peak = env.max()
    if peak <= 0:
        return approx
    rise = np.flatnonzero(env >= 0.3 * peak)
    return (a + int(rise[0])) / float(rate)


def analyze_beats(samples: np.ndarray, rate: int, time_sig: str = "4/4") -> BeatAnalysis:
    """Il battito della ripresa (vedi modulo). I battiti prima del primo
    attacco e dopo l'ultimo (silenzio in testa e in coda) non contano."""
    env, fps = onset_envelope(samples, rate)
    beats_per_bar, beat_quarters = meter_beats(time_sig)
    if not env.any():
        return BeatAnalysis([], beats_per_bar, beat_quarters)
    period = estimate_period(env, fps)
    frames = track_beats(env, period)
    loud = np.flatnonzero(env > ONSET_THRESHOLD * env.max())
    first, last = loud[0] - period / 4, loud[-1] + period / 4
    frames = frames[(frames >= first) & (frames <= last)]
    # un battito un po' prima dell'attacco vero: lo si sposta sul picco vicino
    refined = []
    for f in frames:
        a, b = max(0, int(f - 2)), min(len(env), int(f + 3))
        refined.append(a + int(np.argmax(env[a:b])))
    beats = [_attack_time(samples, rate, (f * HOP + FRAME / 2) / rate) for f in refined]
    analysis = BeatAnalysis(beats, beats_per_bar, beat_quarters)
    analysis.bar_tempos = bar_tempos(beats, beats_per_bar, beat_quarters)
    return analysis


def tempo_changes_for(analysis: BeatAnalysis, first_bar: int, existing: List[tuple],
                      tempo_after: Optional[int]) -> List[tuple]:
    """I cambi di tempo del brano con le battute della ripresa a partire da
    first_bar (al posto di quelli che c'erano in quelle battute) e, alla
    battuta dopo, il tempo che c'era prima (tempo_after), cosi' il resto del
    brano non cambia."""
    n = analysis.bars
    if n == 0:
        return list(existing)
    kept = [(b, v) for b, v in existing if not first_bar <= b <= first_bar + n]
    new = []
    for k, bpm in enumerate(analysis.bar_tempos):
        if not new or new[-1][1] != bpm:
            new.append((first_bar + k, bpm))
    if tempo_after is not None and analysis.bar_tempos[-1] != tempo_after:
        new.append((first_bar + n, tempo_after))
    return sorted(kept + new)


def tempo_spread(analysis: BeatAnalysis) -> Tuple[int, int]:
    if not analysis.bar_tempos:
        return 0, 0
    return min(analysis.bar_tempos), max(analysis.bar_tempos)
