"""I suoni generati dei pacchetti di SoundText Mobile (organo, fisarmonica, suoni elettronici): sintesi additiva con numpy,
senza numeri casuali, quindi sempre gli stessi a parita' di parametri. Non ci sono licenze da controllare.

Ogni suono e' una somma di armoniche, ciascuna con il suo inviluppo nel tempo: il «filtro» (che si chiude, si apre, risuona)
e' il modo in cui le armoniche alte si spengono o crescono, senza filtri veri. render() da' una nota intera (attacco, parte
tenuta, coda) che lo script dei pacchetti accorcia e mette in anello come un campione qualunque.

Tipi (campo «tipo» del file di dati del pacchetto):
  organo        registri a barre (campo «registri»: ampiezze di 16', 5 1/3', 8', 4', 2 2/3', 2', 1 3/5', 1 1/3', 1'), click opzionale
  fisarmonica   tre ance leggermente scordate («musette»)
  basso_saw     dente di sega e quadra con filtro risonante che si chiude veloce (basso analogico)
  basso_808     sinusoide con salita d'intonazione all'attacco e leggera saturazione
  lead_pwm      onda quadra con modulazione di larghezza d'impulso
  lead_saw      tre denti di sega leggermente scordati
  pad           denti di sega scordati con filtro lento («apertura»: da quanto parte il filtro, «chiusura» a dove arriva)
"""

import math

import numpy as np

DRAWBARS = (0.5, 1.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0)          # i rapporti con la fondamentale (16', 5 1/3', 8', 4'...)


def hz(midi: int) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12.0)


def _envelope(t: np.ndarray, attack: float, decay: float = 0.0, sustain: float = 1.0, release_at: float | None = None,
              release: float = 0.3) -> np.ndarray:
    """Inviluppo ADSR (decay in secondi verso 'sustain'; con 'release_at' la nota si spegne in 'release' secondi)."""
    env = np.minimum(1.0, t / max(attack, 1e-4))
    if decay > 0:
        env = env * (sustain + (1.0 - sustain) * np.exp(-np.maximum(0.0, t - attack) / decay))
    if release_at is not None:
        env = env * np.clip(1.0 - (t - release_at) / release, 0.0, 1.0)
    return env


def _lowpass_gain(freqs: np.ndarray, cutoff: np.ndarray, resonance: float = 0.0, order: float = 2.0) -> np.ndarray:
    """Il guadagno di un passa-basso a frequenza di taglio 'cutoff' (che puo' variare nel tempo), con un picco di
    risonanza 'resonance' (0 = nessuno) intorno al taglio, valutato sulle armoniche 'freqs'."""
    ratio = freqs / np.maximum(cutoff, 20.0)
    gain = 1.0 / np.sqrt(1.0 + ratio ** (2 * order))
    if resonance > 0:
        gain = gain * (1.0 + resonance * np.exp(-((np.log2(np.maximum(ratio, 1e-6))) ** 2) / 0.04))
    return gain


def _harmonics(f0: float, rate: int, limit: float = 0.45) -> np.ndarray:
    """I numeri delle armoniche che stanno sotto la frequenza di Nyquist (con un po' di margine)."""
    return np.arange(1, max(1, int(limit * rate / f0)) + 1)


def render(kind: str, params: dict, midi: int, rate: int = 44100, seconds: float = 3.0) -> np.ndarray:
    """Una nota (mono, float32, circa [-1, 1]) del suono 'kind' con i parametri 'params', alla nota MIDI 'midi'."""
    f0 = hz(midi)
    t = np.arange(int(seconds * rate)) / rate
    out = np.zeros_like(t)
    if kind == "organo":
        bars = params.get("registri", [0, 0, 8, 0, 4, 0, 0, 0, 2])
        click = float(params.get("click", 0.0))
        for ratio, amount in zip(DRAWBARS, bars):
            if amount <= 0 or f0 * ratio > 0.45 * rate:
                continue
            out += (amount / 8.0) * np.sin(2 * math.pi * f0 * ratio * t)
        out *= _envelope(t, 0.006 + 0.01 * (1 - click), release_at=None)
        if click:
            out += click * 0.6 * np.sin(2 * math.pi * f0 * 8 * t) * np.exp(-t / 0.03)       # il «click» d'attacco
        out *= 0.35
    elif kind == "fisarmonica":
        n = _harmonics(f0, rate)
        amplitude = 1.0 / n ** float(params.get("pendenza", 0.9))
        shades = np.where(n % 2 == 0, 0.55, 1.0)                    # ance: le armoniche pari un po' piu' deboli
        dark = float(params.get("scuro", 0.0))                       # 0..1: la variante scura per il registro basso
        tone = amplitude * shades / (1.0 + dark * (n / 4.0) ** 2)
        for cents in params.get("voci", [-6.0, 0.0, 6.0]):
            ratio = 2 ** (cents / 1200.0)
            for k, a in zip(n, tone):
                out += (a / 3.0) * np.sin(2 * math.pi * f0 * ratio * k * t)
        out *= _envelope(t, 0.06) * (1.0 + 0.03 * np.sin(2 * math.pi * 5.5 * t))           # il mantice: attacco morbido e respiro
        out *= 0.5
    elif kind in ("basso_saw", "pad", "lead_saw"):
        detune = params.get("scordatura", [0.0] if kind == "basso_saw" else [-9.0, 0.0, 9.0])
        n = _harmonics(f0, rate)
        env = _envelope(t, params.get("attacco", 0.005 if kind == "basso_saw" else 0.4 if kind == "pad" else 0.01),
                        decay=params.get("decadimento", 0.0), sustain=params.get("sostegno", 1.0))
        if kind == "basso_saw":
            cutoff = f0 * (params.get("taglio_fine", 2.5) + params.get("taglio_inizio", 14.0) * np.exp(-t / params.get("tempo_filtro", 0.14)))
            env = _envelope(t, 0.004, decay=params.get("decadimento", 0.9), sustain=params.get("sostegno", 0.25))
        elif kind == "pad":
            opening = params.get("apertura", 3.0)
            closing = params.get("chiusura", 14.0)
            cutoff = f0 * (opening + (closing - opening) * (1.0 - np.exp(-t / params.get("tempo_filtro", 1.2))))
        else:
            cutoff = np.full_like(t, f0 * params.get("taglio", 12.0))
        for cents in detune:
            ratio = 2 ** (cents / 1200.0)
            for k in n:
                freq = f0 * ratio * k
                if freq > 0.45 * rate:
                    break
                gain = _lowpass_gain(np.full_like(t, freq), cutoff, params.get("risonanza", 0.0))
                out += (1.0 / k) * gain * np.sin(2 * math.pi * freq * t)
        if kind == "basso_saw" and params.get("quadra", 0.4):
            for k in n[::2]:
                freq = f0 * k
                if freq > 0.45 * rate:
                    break
                gain = _lowpass_gain(np.full_like(t, freq), cutoff, params.get("risonanza", 0.0))
                out += params.get("quadra", 0.4) * (1.0 / k) * gain * np.sin(2 * math.pi * f0 * k * t + 0.5)
        out *= env / max(1, len(detune)) * 0.5
    elif kind == "lead_pwm":
        n = _harmonics(f0, rate)
        duty = 0.5 + params.get("profondita", 0.18) * np.sin(2 * math.pi * params.get("velocita", 0.7) * t)
        for k in n:
            freq = f0 * k
            if freq > 0.45 * rate:
                break
            out += (2.0 / (math.pi * k)) * np.sin(math.pi * k * duty) * np.sin(2 * math.pi * freq * t - math.pi * k * duty)
        out *= _envelope(t, 0.008) * 0.45
    elif kind == "basso_808":
        drop = params.get("salita", 1.2)
        glide = params.get("tempo_salita", 0.05)
        freq = f0 * (1.0 + drop * np.exp(-t / glide))
        phase = 2 * math.pi * np.cumsum(freq) / rate
        body = np.sin(phase)
        out = np.tanh(params.get("saturazione", 1.8) * body) / np.tanh(params.get("saturazione", 1.8))
        out *= _envelope(t, 0.002, decay=params.get("decadimento", 1.4), sustain=0.0) * 0.9
    else:
        raise ValueError(f"suono sintetico sconosciuto: {kind}")
    peak = float(np.max(np.abs(out))) or 1.0
    return (out / peak * 0.9).astype(np.float32)
