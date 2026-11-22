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

Le percussioni (kit_elettronico, drum_hit): un colpo per ogni nota del set General MIDI (35-81), nello stile delle drum
machine analogiche: cassa e tom sono sinusoidi con una caduta d'intonazione, rullante e battito di mani sono rumore e un
corpo tonale, i piatti sono sei onde quadre inarmoniche. Il rumore viene da un generatore con seme fisso (il nome della
nota): il risultato e' sempre lo stesso.
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


# ---------------------------------------------------------------------------
# percussioni: un colpo per nota General MIDI
# ---------------------------------------------------------------------------

METAL = (2.0, 3.0, 4.16, 5.43, 6.79, 8.21)                   # i rapporti delle sei onde quadre dei piatti di una drum machine


def _noise(n: int, key: int) -> np.ndarray:
    return np.random.default_rng(1000 + key).uniform(-1.0, 1.0, n)


def _highpass(x: np.ndarray, amount: int = 1) -> np.ndarray:
    """Toglie le basse: differenza fra campioni vicini (una volta per 'amount')."""
    for _ in range(amount):
        x = np.concatenate(([0.0], np.diff(x)))
    return x


def _smooth(x: np.ndarray, width: int) -> np.ndarray:
    return np.convolve(x, np.ones(width) / width, mode="same") if width > 1 else x


def _drop_sine(t: np.ndarray, rate: int, f_start: float, f_end: float, glide: float) -> np.ndarray:
    freq = f_end + (f_start - f_end) * np.exp(-t / glide)
    return np.sin(2 * math.pi * np.cumsum(freq) / rate)


def _metal(t: np.ndarray, base: float, rate: int) -> np.ndarray:
    out = np.zeros_like(t)
    for ratio in METAL:
        out += np.sign(np.sin(2 * math.pi * base * ratio * t))
    return out / len(METAL)


# nota -> (famiglia, parametri): tutte le note del set General MIDI da 35 a 81
DRUM_NOTES = {
    35: ("kick", dict(f0=120, f1=52, glide=0.025, decay=0.30, click=0.25)),
    36: ("kick", dict(f0=150, f1=46, glide=0.035, decay=0.50, click=0.2)),
    37: ("rim", dict(f=820, decay=0.035)),
    38: ("snare", dict(f=185, decay=0.20, noise=0.8, hp=1)),
    39: ("clap", dict(decay=0.22)),
    40: ("snare", dict(f=215, decay=0.16, noise=1.0, hp=2)),
    41: ("tom", dict(f0=130, f1=70, decay=0.50)),
    42: ("hat", dict(decay=0.045, base=205)),
    43: ("tom", dict(f0=160, f1=88, decay=0.45)),
    44: ("hat", dict(decay=0.035, base=205)),
    45: ("tom", dict(f0=195, f1=110, decay=0.42)),
    46: ("hat", dict(decay=0.40, base=205)),
    47: ("tom", dict(f0=240, f1=135, decay=0.38)),
    48: ("tom", dict(f0=290, f1=165, decay=0.35)),
    49: ("crash", dict(decay=1.3, base=300)),
    50: ("tom", dict(f0=340, f1=200, decay=0.32)),
    51: ("ride", dict(decay=0.9, base=420)),
    52: ("crash", dict(decay=1.0, base=360)),
    53: ("bell", dict(f=(680, 1010), decay=0.5)),
    54: ("shaker", dict(decay=0.10, width=2, hp=2)),
    55: ("crash", dict(decay=0.55, base=380)),
    56: ("bell", dict(f=(540, 810), decay=0.28)),
    57: ("crash", dict(decay=1.5, base=330)),
    58: ("shaker", dict(decay=0.45, width=3, hp=1)),
    59: ("ride", dict(decay=0.8, base=460)),
    60: ("conga", dict(f0=420, f1=330, decay=0.14)),
    61: ("conga", dict(f0=330, f1=260, decay=0.17)),
    62: ("conga", dict(f0=300, f1=240, decay=0.09)),
    63: ("conga", dict(f0=260, f1=200, decay=0.22)),
    64: ("conga", dict(f0=210, f1=160, decay=0.26)),
    65: ("conga", dict(f0=520, f1=410, decay=0.2)),
    66: ("conga", dict(f0=420, f1=340, decay=0.22)),
    67: ("bell", dict(f=(870, 1305), decay=0.3)),
    68: ("bell", dict(f=(650, 975), decay=0.34)),
    69: ("shaker", dict(decay=0.07, width=1, hp=2)),
    70: ("shaker", dict(decay=0.05, width=1, hp=2)),
    71: ("rim", dict(f=2100, decay=0.18)),
    72: ("rim", dict(f=1700, decay=0.35)),
    73: ("shaker", dict(decay=0.06, width=3, hp=1)),
    74: ("shaker", dict(decay=0.18, width=3, hp=1)),
    75: ("rim", dict(f=2500, decay=0.05)),
    76: ("rim", dict(f=1150, decay=0.06)),
    77: ("rim", dict(f=820, decay=0.07)),
    78: ("conga", dict(f0=900, f1=700, decay=0.12)),
    79: ("conga", dict(f0=700, f1=560, decay=0.2)),
    80: ("bell", dict(f=(2400, 3600), decay=0.12)),
    81: ("bell", dict(f=(2400, 3600), decay=0.7)),
}
# il peso di ogni famiglia sul livello del colpo (dB, prima del ritocco del kit): la cassa e il rullante portano il ritmo,
# i piatti e i suoni piccoli stanno dietro
# (misurati contro il kit di TimGM6mb, a pari colpo: media fra picco e livello medio)
DRUM_LEVEL_DB = {"kick": -4.5, "snare": 0.0, "clap": -2.0, "tom": -2.0, "hat": -4.0, "crash": -5.0, "ride": -9.0, "rim": -3.0,
                 "bell": -8.0, "shaker": -2.0, "conga": -3.0}
DRUM_NOTE_DB = {46: 1.0}                                    # l'hi-hat aperto un po' sopra il chiuso


def drum_hit(note: int, rate: int = 32000) -> tuple:
    """(famiglia, colpo in float32 con picco 0,9) della nota General MIDI 'note' (35-81)."""
    family, p = DRUM_NOTES[note]
    seconds = {"kick": 1.0, "tom": 0.9, "crash": 2.2, "ride": 1.6, "hat": 0.7, "bell": 1.0, "shaker": 0.7}.get(family, 0.6)
    seconds = min(seconds, max(0.15, p["decay"] * 5))
    n = int(seconds * rate)
    t = np.arange(n) / rate
    noise = _noise(n, note)
    if family == "kick":
        body = _drop_sine(t, rate, p["f0"], p["f1"], p["glide"])
        out = np.tanh(1.6 * body) * np.exp(-t / p["decay"]) + p["click"] * _smooth(noise, 3) * np.exp(-t / 0.004)
    elif family == "tom":
        out = (_drop_sine(t, rate, p["f0"] * 1.5, p["f1"], 0.04) * np.exp(-t / p["decay"]) +
               0.12 * _highpass(noise) * np.exp(-t / 0.01))
    elif family == "snare":
        tone = _drop_sine(t, rate, p["f"] * 1.4, p["f"], 0.015) * np.exp(-t / (p["decay"] * 0.5))
        rattle = _highpass(_smooth(noise, 2), p["hp"]) * np.exp(-t / p["decay"])
        out = 0.7 * tone + p["noise"] * rattle / max(1e-6, np.max(np.abs(rattle)))
    elif family == "clap":
        env = np.zeros(n)
        for k, gap in enumerate((0.0, 0.011, 0.022)):
            s = int(gap * rate)
            env[s:] += np.exp(-t[: n - s] / 0.005) * (0.9 - 0.1 * k)
        env += 0.5 * np.exp(-np.maximum(0, t - 0.03) / p["decay"]) * (t > 0.03)
        out = _smooth(_highpass(noise), 2) * env
    elif family == "hat":
        out = _highpass(_metal(t, p["base"], rate), 1) * np.exp(-t / p["decay"]) + 0.25 * _highpass(noise) * np.exp(-t / (p["decay"] * 0.7))
    elif family == "crash":
        out = (_highpass(_metal(t, p["base"], rate), 1) * 0.7 + 0.5 * _highpass(noise)) * np.exp(-t / p["decay"]) * (1.0 - 0.3 * np.exp(-t / 0.01))
    elif family == "ride":
        out = (_highpass(_metal(t, p["base"], rate), 1) * 0.6 * np.exp(-t / p["decay"]) +
               0.6 * np.sin(2 * math.pi * 5200 * t) * np.exp(-t / 0.06))
    elif family == "rim":
        out = np.sin(2 * math.pi * p["f"] * t) * np.exp(-t / p["decay"]) + 0.3 * _highpass(noise) * np.exp(-t / 0.004)
    elif family == "bell":
        a, b = p["f"]
        out = (np.sign(np.sin(2 * math.pi * a * t)) + np.sign(np.sin(2 * math.pi * b * t))) * 0.5 * np.exp(-t / p["decay"])
        out = _smooth(out, 3)
    elif family == "shaker":
        out = _smooth(_highpass(noise, p["hp"]), p["width"]) * np.exp(-t / p["decay"]) * np.minimum(1.0, t / 0.004)
    elif family == "conga":
        out = (_drop_sine(t, rate, p["f0"] * 1.15, p["f1"], 0.02) * np.exp(-t / p["decay"]) +
               0.2 * _smooth(noise, 3) * np.exp(-t / 0.006))
    else:
        raise ValueError(family)
    out = out * np.minimum(1.0, t / 0.0008)                    # niente scatto all'inizio
    out[-int(0.02 * rate):] *= np.linspace(1.0, 0.0, int(0.02 * rate))
    peak = float(np.max(np.abs(out))) or 1.0
    return family, (out / peak * 0.9).astype(np.float32)
