"""
Riconoscimento degli accordi da un audio (modalita' "Accordi" dell'import
audio, vedi core.audio_import): dal suono di una chitarra, di un pianoforte
o di un brano intero, la sequenza di sigle d'accordo in notazione
("4: 4C | 2Am 2G7 | ...").

Metodo (classico, solo numpy):
  1. cromagramma: per ogni finestra (FRAME/HOP) l'energia di ciascuna delle
     12 note sommando le ottave (FREQ_MIN-FREQ_MAX), dopo aver stimato
     l'accordatura della registrazione e tolto la parte dovuta agli
     armonici (THIRD_HARMONIC, FIFTH_HARMONIC); a parte quella dei bassi
     (BASS_MIN-BASS_MAX), per i rivolti (C/E);
  2. un accordo per passo (un quarto, o un ottavo con le battute che non sono
     un numero intero di quarti): media del cromagramma sul passo, confronto
     (coseno) con i modelli di QUALITIES su 12 fondamentali;
  3. la sequenza piu' probabile con Viterbi: cambiare accordo costa, meno
     sull'inizio della battuta, cosi' gli accordi non "sfarfallano";
  4. la notazione a battute, con le legature dove un accordo continua.
"""

import math
from typing import Callable, List, Optional, Tuple

import numpy as np

NOTE_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
SHARP_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
FLAT_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

# Tonalita' maggiori con i diesis e con i bemolle (fondamentale), per
# scrivere le alterazioni come in partitura: D#dim in Mi, non Ebdim.
_SHARP_KEYS = {7, 2, 9, 4, 11, 6}          # G D A E B F#
_FLAT_KEYS = {5, 10, 3, 8, 1}              # F Bb Eb Ab Db

FRAME = 8192            # campioni per finestra (a 44,1 kHz: 186 ms, abbastanza per i bassi)
HOP = 2048              # passo fra le finestre (46 ms)
FREQ_MIN, FREQ_MAX = 60.0, 2100.0
# Bassi da 65 Hz (Do2): piu' in basso due semitoni distano meno della
# risoluzione della finestra (5,4 Hz) e il Si grave diventava Sib; le note
# piu' gravi si riconoscono dal secondo armonico, un'ottava sopra. Il basso
# e' la nota piu' grave fra quelle forti della banda (BASS_STRONG del
# massimo), non la piu' forte: il Si3 di un G diventava il basso di G/B.
BASS_MIN, BASS_MAX = 65.0, 250.0
BASS_STRONG = 0.5

# qualita' -> (intervalli in semitoni dalla fondamentale, pesi, penalita').
# La penalita' fa preferire la triade quando la settima non si sente
# chiaramente; dim e sus4 sono piu' rari in pratica.
QUALITIES = {
    "": ((0, 4, 7), (1.0, 0.85, 0.8), 0.0),
    "m": ((0, 3, 7), (1.0, 0.85, 0.8), 0.0),
    "7": ((0, 4, 7, 10), (1.0, 0.8, 0.75, 0.65), 0.035),
    "maj7": ((0, 4, 7, 11), (1.0, 0.8, 0.75, 0.65), 0.035),
    "m7": ((0, 3, 7, 10), (1.0, 0.8, 0.75, 0.65), 0.035),
    # piu' cara: senza fondamentale un accordo di settima (B7 senza Si) o
    # una triade maggiore indebolita somiglia al diminuito sulla sua terza
    # (0.10 basta sui casi di prova, i diminuiti veri restano riconosciuti)
    "dim": ((0, 3, 6), (1.0, 0.85, 0.8), 0.12),
    "sus4": ((0, 5, 7), (1.0, 0.85, 0.8), 0.05),
}

# Gli armonici ingannano: il terzo armonico di una nota cade una quinta
# sopra (piu' un'ottava), il quinto una terza maggiore sopra. Su una
# chitarra, C (x32010, il Mi in cima) diventava Em (Mi Sol Si) e D diventava
# F#m. Dal cromagramma si toglie quindi a ogni nota una parte di quella una
# quinta sotto e di quella una terza maggiore sotto: tarato su pianoforte,
# chitarre pulita, classica e distorta, con e senza basso e batteria
# (accordi giusti dall'85% al 98% dei tempi; 0.8 e oltre peggiora).
THIRD_HARMONIC = 0.7
FIFTH_HARMONIC = 0.15

# Le settime restano le piu' incerte (una settima vera e una nota
# rinforzata da un armonico si somigliano): si cercano solo se richiesto
# (sevenths=True). Con la compensazione degli armonici le triadi restano
# triadi; delle settime vere se ne perde circa una su quattro.
SEVENTH_QUALITIES = ("7", "maj7", "m7")


def _harmonic_compensation() -> np.ndarray:
    mix = np.eye(12, dtype=np.float32)
    for p in range(12):
        mix[(p - 7) % 12, p] -= THIRD_HARMONIC
        mix[(p - 4) % 12, p] -= FIFTH_HARMONIC
    return mix

CHANGE_COST = 0.16          # cambiare accordo a meta' battuta
CHANGE_COST_BAR = 0.06      # cambiarlo sull'inizio della battuta
CHANGE_COST_HALF = 0.11     # sulla meta' della battuta (4/4: terzo quarto)
SILENCE_DB = -40.0          # passi piu' deboli di cosi' (rispetto al piu' forte): pausa
NO_CHORD_SCORE = 0.55       # sotto questa somiglianza con ogni accordo: pausa
BASS_BONUS = 0.06           # il basso suona la fondamentale
SLASH_MIN_SHARE = 0.35      # quota dell'energia dei bassi perche' un rivolto si scriva
SLASH_MIN_STEPS = 0.7       # ...in almeno questa parte dei passi dell'accordo
TAIL_RATIO = 0.1            # coda prima di una pausa sotto -10 dB dell'accordo: pausa


def _chord_templates(sevenths: bool = False):
    names, vectors, penalties, members = [], [], [], []
    for root in range(12):
        for quality, (intervals, weights, penalty) in QUALITIES.items():
            if quality in SEVENTH_QUALITIES and not sevenths:
                continue
            v = np.zeros(12)
            for iv, w in zip(intervals, weights):
                v[(root + iv) % 12] = w
            names.append((root, quality))
            vectors.append(v / np.linalg.norm(v))
            penalties.append(penalty)
            members.append({(root + iv) % 12 for iv in intervals})
    return names, np.array(vectors), np.array(penalties), members


def _mono(path: str) -> Tuple[np.ndarray, int]:
    from .audio_tracks import read_wav
    x, rate = read_wav(path)
    if x.ndim == 2:
        x = x.mean(axis=1)
    return x.astype(np.float32), rate


def _spectrogram(x: np.ndarray, progress: Optional[Callable[[float], None]] = None):
    window = np.hanning(FRAME).astype(np.float32)
    n = max(1, 1 + (len(x) - FRAME) // HOP) if len(x) >= FRAME else 1
    if len(x) < FRAME:
        x = np.pad(x, (0, FRAME - len(x)))
    spec = np.empty((n, FRAME // 2 + 1), np.float32)
    for i in range(n):
        frame = x[i * HOP:i * HOP + FRAME]
        spec[i] = np.abs(np.fft.rfft(frame * window))
        if progress and i % 200 == 0:
            progress(i / n)
    return spec


def _estimate_tuning(spec: np.ndarray, freqs: np.ndarray) -> float:
    """Scostamento dell'accordatura dal La 440, in semitoni (-0.5..0.5):
    media circolare della parte frazionaria della nota dei picchi forti."""
    band = (freqs >= FREQ_MIN) & (freqs <= FREQ_MAX)
    avg = spec[:, band].mean(axis=0)
    f = freqs[band]
    peaks = np.flatnonzero((avg[1:-1] > avg[:-2]) & (avg[1:-1] > avg[2:])) + 1
    if len(peaks) == 0:
        return 0.0
    strongest = peaks[np.argsort(avg[peaks])[-60:]]
    # posizione del picco piu' precisa con l'interpolazione parabolica
    a, b, c = avg[strongest - 1], avg[strongest], avg[strongest + 1]
    shift = 0.5 * (a - c) / np.where(a - 2 * b + c == 0, -1e-9, a - 2 * b + c)
    step = f[1] - f[0]
    pitch = 69 + 12 * np.log2((f[strongest] + shift * step) / 440.0)
    angles = 2 * np.pi * (pitch - np.round(pitch))
    weights = avg[strongest]
    mean = math.atan2(float((weights * np.sin(angles)).sum()), float((weights * np.cos(angles)).sum()))
    return mean / (2 * np.pi)


def _semitone_matrix(freqs: np.ndarray, lo: float, hi: float, tuning: float):
    """(matrice (bin, note), nota MIDI della prima colonna): ogni bin della
    banda alla sua nota, senza piegare le ottave (per trovare la piu' grave)."""
    band = (freqs >= lo) & (freqs <= hi)
    pitch = 69 + 12 * np.log2(np.where(band, freqs, 1.0) / 440.0) - tuning
    nearest = np.round(pitch).astype(int)
    first = int(nearest[band].min()) if band.any() else 0
    count = int(nearest[band].max()) - first + 1 if band.any() else 1
    m = np.zeros((len(freqs), count), np.float32)
    weight = np.clip(1.0 - 2.0 * np.abs(pitch - nearest), 0.0, 1.0)
    idx = np.flatnonzero(band)
    m[idx, nearest[idx] - first] = weight[idx]
    return m, first


def _chroma_matrix(freqs: np.ndarray, lo: float, hi: float, tuning: float) -> np.ndarray:
    """Matrice (bin, 12): ogni bin della banda alla sua nota, col peso che
    cala allontanandosi dal centro della nota (meno sbavature fra semitoni)."""
    m = np.zeros((len(freqs), 12), np.float32)
    band = (freqs >= lo) & (freqs <= hi)
    pitch = 69 + 12 * np.log2(np.where(band, freqs, 1.0) / 440.0) - tuning
    nearest = np.round(pitch)
    distance = np.abs(pitch - nearest)
    weight = np.clip(1.0 - 2.0 * distance, 0.0, 1.0)
    idx = np.flatnonzero(band)
    m[idx, (nearest[idx].astype(int)) % 12] = weight[idx]
    return m


def detect_chords(wav_path: str, tempo_bpm: float, beats_per_bar: float,
                  align_to_first: bool = False, sevenths: bool = False,
                  progress_callback: Optional[Callable[[float], None]] = None):
    """[(fondamentale, qualita', basso o None, passi)] con la durata del
    passo (in quarti) e l'inizio in secondi del primo passo. Fondamentale
    None = pausa. Vedi il docstring del modulo."""
    x, rate = _mono(wav_path)
    spec = _spectrogram(x, (lambda f: progress_callback(0.7 * f)) if progress_callback else None)
    freqs = np.fft.rfftfreq(FRAME, 1.0 / rate)
    tuning = _estimate_tuning(spec, freqs)
    compressed = np.log1p(spec * 10.0)
    chroma = np.maximum(compressed @ _chroma_matrix(freqs, FREQ_MIN, FREQ_MAX, tuning) @ _harmonic_compensation(), 0.0)
    # i bassi sull'energia lineare: compressa, la nota del basso spariva fra
    # gli armonici (il 16-28% dell'energia invece del 50%)
    bass_matrix, bass_first = _semitone_matrix(freqs, BASS_MIN, BASS_MAX, tuning)
    bass = spec @ bass_matrix
    energy = (spec ** 2).sum(axis=1)
    frame_times = (np.arange(len(spec)) * HOP + FRAME / 2) / rate

    step_q = 1.0 if abs(beats_per_bar - round(beats_per_bar)) < 1e-9 else 0.5
    step_s = step_q * 60.0 / tempo_bpm
    loud = energy > energy.max() * 10 ** (SILENCE_DB / 10) if energy.max() > 0 else np.zeros(len(energy), bool)
    start_s = 0.0
    if align_to_first and loud.any():
        start_s = max(0.0, float(frame_times[np.flatnonzero(loud)[0]]) - FRAME / 2 / rate)
    total = max(1, int(math.ceil((len(x) / rate - start_s) / step_s)))

    names, templates, penalties, members = _chord_templates(sevenths)
    n_chords = len(names)
    scores = np.full((total, n_chords + 1), -1.0)
    bass_root = [None] * total
    step_energy = np.zeros(total)
    loud_share = np.zeros(total)
    selections = []
    for s in range(total):
        sel = (frame_times >= start_s + s * step_s) & (frame_times < start_s + (s + 1) * step_s)
        selections.append(sel)
        if sel.any():
            step_energy[s] = float(energy[sel].mean())
            loud_share[s] = float(loud[sel].mean())
    for s in range(total):
        sel = selections[s]
        # Un passo quasi muto subito prima di uno forte e' l'attacco che
        # "sbava" indietro (la finestra e' lunga 186 ms): pausa. Alla fine di
        # un accordo invece il suono che si spegne resta accordo.
        bleed = loud_share[s] < 0.5 and s + 1 < total and loud_share[s + 1] >= 0.5
        if loud_share[s] == 0 or bleed:
            scores[s, n_chords] = 1.0                       # silenzio: pausa
            continue
        c = chroma[sel].mean(axis=0)
        norm = np.linalg.norm(c)
        if norm == 0:
            scores[s, n_chords] = 1.0
            continue
        sim = templates @ (c / norm) - penalties
        b = bass[sel].mean(axis=0)
        if b.sum() > 0:
            lowest = int(np.flatnonzero(b >= BASS_STRONG * b.max())[0])
            low = (bass_first + lowest) % 12
            folded = np.bincount((bass_first + np.arange(len(b))) % 12, weights=b, minlength=12)
            bass_root[s] = (low, float(folded[low] / b.sum()))
            sim = sim + BASS_BONUS * np.array([1.0 if root == low else 0.0 for root, _q in names])
        scores[s, :n_chords] = sim
        scores[s, n_chords] = NO_CHORD_SCORE
    if progress_callback:
        progress_callback(0.85)

    # Viterbi: massimizza somiglianza meno il costo dei cambi
    steps_per_bar = beats_per_bar / step_q
    best = scores[0].copy()
    back = np.zeros((total, n_chords + 1), np.int32)
    for s in range(1, total):
        pos = (s % steps_per_bar) if steps_per_bar > 0 else 1
        if abs(pos) < 1e-9:
            cost = CHANGE_COST_BAR
        elif abs(pos - steps_per_bar / 2) < 1e-9:
            cost = CHANGE_COST_HALF
        else:
            cost = CHANGE_COST
        leader = int(np.argmax(best))
        stay = best
        switch = best[leader] - cost
        take_switch = switch > stay
        back[s] = np.where(take_switch, leader, np.arange(n_chords + 1))
        best = np.where(take_switch, switch, stay) + scores[s]
    path = [int(np.argmax(best))]
    for s in range(total - 1, 0, -1):
        path.append(int(back[s][path[-1]]))
    path.reverse()

    # sequenze dello stesso accordo: [stato, primo passo, ultimo passo]
    runs = []
    for s, state in enumerate(path):
        if runs and runs[-1][0] == state:
            runs[-1][2] = s
        else:
            runs.append([state, s, s])
    # La coda di un accordo prima di una pausa (o della fine) che suona molto
    # piu' debole del resto e' il riverbero o il rilascio: diventa pausa.
    for i, (state, first, last) in enumerate(runs):
        if state == n_chords or (i + 1 < len(runs) and runs[i + 1][0] != n_chords):
            continue
        typical = float(np.median(step_energy[first:last + 1]))
        while last > first and step_energy[last] < TAIL_RATIO * typical:
            last -= 1
        if last < runs[i][2]:
            runs[i][2] = last
    out = []
    pos = 0
    for state, first, last in runs:
        if first > pos:                                   # coda tolta: pausa
            out.append((None, "", None, first - pos))
        # Il rivolto si decide battuta per battuta (C | C/E e' lo stesso
        # accordo con il basso che si muove): in ogni pezzo il basso deve
        # stare su quella nota dell'accordo quasi sempre (SLASH_MIN_STEPS),
        # per non spezzare un accordo in C, C/E, C.
        bar_steps = max(1, int(round(steps_per_bar)))
        piece_start = first
        while piece_start <= last:
            piece_end = min(last, (piece_start // bar_steps + 1) * bar_steps - 1)
            length = piece_end - piece_start + 1
            if state == n_chords:
                chord = (None, "", None)
            else:
                root, quality = names[state]
                lows = [bass_root[s][0] for s in range(piece_start, piece_end + 1)
                        if bass_root[s] is not None and bass_root[s][1] >= SLASH_MIN_SHARE]
                slash = None
                if lows:
                    low = max(set(lows), key=lows.count)
                    if low != root and low in members[state] and lows.count(low) >= SLASH_MIN_STEPS * length:
                        slash = low
                chord = (root, quality, slash)
            if out and out[-1][:3] == chord:
                out[-1] = chord + (out[-1][3] + length,)
            else:
                out.append(chord + (length,))
            piece_start = piece_end + 1
        pos = last + 1
    if progress_callback:
        progress_callback(1.0)
    return out, step_q, start_s


def note_names_for(chords) -> List[str]:
    """I nomi delle note secondo la tonalita' maggiore (o relativa minore)
    in cui suonano piu' a lungo gli accordi trovati: per ognuna delle 12, il
    tempo degli accordi che le appartengono (triadi sui gradi I-VII)."""
    best_key, best = 0, -1.0
    for key in range(12):
        diatonic = {(key, ""), ((key + 2) % 12, "m"), ((key + 4) % 12, "m"), ((key + 5) % 12, ""),
                    ((key + 7) % 12, ""), ((key + 9) % 12, "m"), ((key + 11) % 12, "dim")}
        score = sum(length for root, quality, _bass, length in chords
                    if root is not None and (root, quality.replace("maj7", "").replace("m7", "m")
                                             .replace("7", "")) in diatonic)
        if score > best:
            best_key, best = key, score
    if best_key in _SHARP_KEYS:
        return SHARP_NAMES
    if best_key in _FLAT_KEYS:
        return FLAT_NAMES
    return NOTE_NAMES


def chord_name(root: Optional[int], quality: str, bass: Optional[int], names=NOTE_NAMES) -> str:
    if root is None:
        return "r"
    return names[root] + quality + (f"/{names[bass]}" if bass is not None else "")


def chords_to_text(chords, step_q: float, beats_per_bar: float) -> str:
    """Le sigle a battute: "4: 4C | 2Am 2G7 | 4F~ | 2F 2r". Un accordo che
    passa la stanghetta continua con la legatura (le pause no)."""
    grid = "4:" if step_q == 1.0 else "8:"
    steps_per_bar = int(round(beats_per_bar / step_q))
    names = note_names_for(chords)
    bars: List[List[str]] = [[]]
    used = 0
    for root, quality, bass, length in chords:
        name = chord_name(root, quality, bass, names)
        remaining = length
        while remaining > 0:
            room = steps_per_bar - used
            take = min(room, remaining)
            remaining -= take
            tie = "~" if remaining > 0 and root is not None else ""
            bars[-1].append(f"{take if take > 1 else ''}{name}{tie}")
            used += take
            if used == steps_per_bar:
                bars.append([])
                used = 0
    # niente pause in coda, ne' battute vuote
    while bars and (not bars[-1] or all(t.lstrip("0123456789") == "r" for t in bars[-1])):
        bars.pop()
    if not bars:
        return ""
    return grid + " " + " | ".join(" ".join(tokens) for tokens in bars)
