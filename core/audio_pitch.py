"""
Rilevamento di note melodiche (pitch + attacco/rilascio + dinamica) da un
file WAV, usato per le tracce melodiche/armoniche (voce, strumento) nella
funzionalita' di importazione audio.

Segmentazione sugli attacchi (core.audio_dsp.detect_onsets: colpi, note
pizzicate, sillabe, anche in registro grave) piu' i cambi d'altezza senza
attacco (legato cantato o suonato, vedi _pitch_change_onsets), e stima
del pitch con YIN (core.audio_dsp.yin) sui campioni di ogni segmento.
Tutto in numpy, senza librerie di analisi audio esterne.

Per ogni intervallo tra un onset e il successivo, il pitch della nota e'
la MEDIANA delle stime frame-per-frame con confidenza sufficiente (vedi
PITCH_CONFIDENCE_THRESHOLD): piu' robusta a vibrato/instabilita' di
intonazione tipica di una voce non professionale rispetto a una singola
stima istantanea. Segmenti senza stime sufficientemente confidenti
(silenzio, respiro, consonante non intonata) non generano una nota.

Pensato anche per la voce di chi canta senza riferimento: gli attacchi
lenti si riportano all'inizio della salita del livello (vedi
_backtrack_onsets), le altezze si arrotondano al semitono dopo aver tolto
l'accordatura dell'intera esecuzione (tutta calante o crescente, vedi
estimate_tuning), e i pezzi di una nota tenuta che il vibrato fa cadere su
semitoni vicini tornano una nota sola (vedi MERGE_SEMITONES).

Ogni stima di pitch e' attribuita al CENTRO della sua finestra di analisi
(che si estende all'indietro di buf_size campioni dalla fine dell'hop
appena letto), non all'inizio dell'hop: con le finestre ampie usate per i
bassi (8192 campioni) la differenza e' di quasi 100 ms, abbastanza da
attribuire a una nota breve le stime della nota precedente.

La nota finisce dove il suono si spegne (livello sotto NOTE_END_DB rispetto
al picco della nota), non per forza all'attacco successivo: cosi' le note
staccate lasciano le pause, e l'ultima nota non si allunga fino alla fine
del file. Due segmenti consecutivi con la stessa altezza si uniscono solo
se il secondo non e' un nuovo attacco (falso onset a meta' di una nota
tenuta, es. per vibrato): note ripetute (la stessa nota suonata piu' volte,
tipica dei bassi) restano note distinte.
"""

import math
from typing import Callable, List, Optional

from .audio_quantize import AudioEvent

DEFAULT_HOP_SIZE = 512
DEFAULT_BUF_SIZE = 2048

# Filtra le note piu' brevi di questa soglia: quasi sempre artefatti (onset
# spuri ravvicinati, es. per vibrato marcato) piuttosto che note davvero
# suonate/cantate.
MIN_NOTE_DURATION_SEC = 0.03

# Confidenza minima (0-1, vedi core.audio_dsp.yin) perche' una stima di
# frequenza sia considerata attendibile, sotto la quale il frame e'
# probabilmente silenzio/rumore/consonante non intonata, non una nota.
PITCH_CONFIDENCE_THRESHOLD = 0.6

# Fine della nota: primo hop, dopo il picco, in cui il livello scende di
# questi dB sotto il picco della nota (e resta sotto fino al segmento dopo).
NOTE_END_DB = -30.0
# Livello minimo assoluto rispetto al picco dell'intero file: sotto, e'
# silenzio/rumore di fondo anche se la nota era debole.
SILENCE_DB = -50.0
# Un segmento con la stessa altezza del precedente e' un NUOVO attacco (nota
# ripetuta) se tra i due c'e' una pausa, o se il picco dell'attacco supera di
# questo fattore il livello di poco prima del picco (vedi REATTACK_BEFORE):
# un attacco vero (plettro, corda ripizzicata, nuova sillaba) sale in pochi
# ms, il tremolo/vibrato di una nota tenuta in decine di ms, quindi poco
# prima del suo picco il livello e' gia' quasi quello del picco.
REATTACK_RATIO = 1.5
# ...oppure se l'attacco spettrale e' netto (forza, vedi
# core.audio_dsp.detect_onsets): una corda ripizzicata mentre suona ancora
# alza poco il volume ma cambia lo spettro. Il vibrato, soppresso dal
# rilevatore, resta sotto (misurato: note ripetute vere 2.9-6.9, falsi
# attacchi dentro note tenute di flauto, sax e coro 0.5-2.5; sul corpus
# di prova col SoundFont GM).
STRONG_ONSET = 3.0
# Due segmenti consecutivi, il secondo senza un nuovo attacco, sono la
# stessa nota se le loro altezze (frazionarie, accordatura tolta) distano
# meno di questi semitoni: il vibrato di chi canta (fino a +/-60 cent) fa
# cadere le mediane di pezzi della stessa nota ai due lati del confine fra
# due semitoni. Un passo legato vero di un semitono resta separato.
MERGE_SEMITONES = 0.75
# L'altezza "dopo" il confine si misura come media delle stime nei
# MERGE_CONTEXT_S secondi che seguono (senza oltrepassare il prossimo
# attacco vero): almeno un ciclo intero di vibrato (5-6 Hz), cosi' la media
# cade sul centro della nota anche quando il pezzo dopo il confine e' breve
# e ne contiene solo mezzo ciclo.
MERGE_CONTEXT_S = 0.2
# Stime fuori da questo intervallo (Hz) sono rumore/sibilanti o errori
# d'ottava: nessuno strumento ha fondamentali utili fuori da qui (il Do piu'
# acuto del pianoforte e' ~4186 Hz).
MIN_PITCH_HZ = 20.0
MAX_PITCH_HZ = 4200.0
# Il livello (per fine nota, nuovi attacchi e dinamica) si misura su una
# griglia propria, fine, indipendente dall'hop del pitch: con le finestre
# dei bassi (hop 2048 = 46 ms) un hop a cavallo di un onset conterrebbe gia'
# l'attacco della nota dopo.
LEVEL_HOP = 256
# Il picco dell'attacco si cerca in [onset - 10 ms, onset + 50 ms]; il
# livello "prima" in [picco - 45 ms, picco - 15 ms] (almeno un periodo anche
# per le note piu' gravi, ~24 ms per un Mi1).
REATTACK_SEARCH = (0.010, 0.050)
REATTACK_BEFORE = (0.045, 0.015)
# Attacchi lenti (arco, fiati, voce, coro): il rilevatore trova il punto in
# cui lo spettro e' gia' cambiato, quando il suono e' gia' cresciuto, anche
# 100-150 ms dopo l'inizio della nota. Si risale l'inviluppo del livello
# (smussato su BACKTRACK_SMOOTH blocchi) finche' scende, fino a
# BACKTRACK_MAX secondi prima e mai oltre l'attacco precedente: e' l'inizio
# della salita (come l'onset backtracking di librosa).
BACKTRACK_MAX = 0.15
BACKTRACK_SMOOTH = 3


def _backtrack_onsets(onsets: List[int], block_rms, rate: int) -> List[int]:
    """Ogni attacco spostato all'inizio della salita del livello che lo
    precede (vedi BACKTRACK_MAX). block_rms: livello per blocchi di
    LEVEL_HOP campioni."""
    import numpy as np
    if not len(block_rms):
        return list(onsets)
    kernel = np.ones(BACKTRACK_SMOOTH) / BACKTRACK_SMOOTH
    env = np.convolve(block_rms, kernel, mode="same")
    limit = int(BACKTRACK_MAX * rate / LEVEL_HOP)
    out, prev_block = [], 0
    for pos in onsets:
        k = min(len(env) - 1, pos // LEVEL_HOP)
        stop = max(prev_block + 1, k - limit, 0)
        while k > stop and env[k - 1] < env[k]:
            k -= 1
        new = min(pos, k * LEVEL_HOP)
        out.append(new)
        prev_block = pos // LEVEL_HOP
    return out


def _buf_size_for_min_freq(min_freq_hz: Optional[float]) -> int:
    """Sceglie una finestra di analisi piu' ampia per le frequenze piu'
    gravi: con la finestra di default (2048 campioni, ~46ms a 44100Hz) una
    nota di basso (es. Mi1 ~41Hz, periodo ~24ms) e' coperta da poco piu' di
    un solo periodo, poco affidabile per una stima di pitch precisa. NON
    risolve da sola il rilevamento dell'attacco (demandato a
    core.audio_dsp.detect_onsets, indipendente da questa finestra)."""
    if min_freq_hz is None:
        return DEFAULT_BUF_SIZE
    if min_freq_hz < 50:      # sotto circa Sol1: bassi a 4/5 corde sulle corde piu' gravi
        return 8192
    if min_freq_hz < 100:     # fino a circa La2
        return 4096
    return DEFAULT_BUF_SIZE


def _hz_to_midi(freq_hz: float, tuning: float = 0.0) -> int:
    """Nota MIDI piu' vicina a freq_hz, con l'accordatura 'tuning' (in
    semitoni, vedi estimate_tuning) tolta prima di arrotondare."""
    return max(0, min(127, int(round(69 + 12 * math.log2(freq_hz / 440.0) - tuning))))


# Sotto questo scarto (semitoni) l'accordatura si considera giusta: non vale
# la pena spostare note di strumenti gia' accordati per pochi cent di rumore.
TUNING_MIN = 0.05
# Con poche note "tutto calante di 40 cent" e "intonato ma impreciso" si
# equivalgono: l'accordatura si stima solo da almeno tante note.
TUNING_MIN_NOTES = 6


def estimate_tuning(freqs, weights=None) -> float:
    """Di quanto (in semitoni, fra -0.5 e 0.5) l'intera esecuzione e' sopra
    o sotto l'accordatura a 440 Hz: media circolare (pesata) dello scarto
    dal semitono piu' vicino delle altezze delle note. Chi canta senza
    riferimento e' spesso tutto calante o crescente di qualche decina di
    cent: arrotondando ogni nota al semitono piu' vicino, quelle vicine al
    confine finirebbero sulla nota sbagliata.

    Vanno date le altezze (mediane) delle NOTE, non le stime istantanee: un
    vibrato ampio (+/-60 cent) sparge le stime su quasi un semitono intero e
    la loro media circolare si annulla, o si ribalta."""
    import numpy as np
    pairs = [(v, 1.0 if weights is None else w) for v, w in zip(freqs, weights or freqs) if v > 0]
    if len(pairs) < TUNING_MIN_NOTES:
        return 0.0
    f = np.asarray([v for v, _ in pairs], dtype=np.float64)
    w = np.asarray([w for _, w in pairs], dtype=np.float64)
    m = 69 + 12 * np.log2(f / 440.0)
    z = np.sum(w * np.exp(2j * np.pi * m)) / np.sum(w)
    if abs(z) < 0.2:          # scarti sparsi in tutte le direzioni: nessuna accordatura chiara
        return 0.0
    offset = float(np.angle(z) / (2 * np.pi))
    return offset if abs(offset) >= TUNING_MIN else 0.0


PITCH_CHANGE_WINDOW_S = 0.12    # durata delle due finestre confrontate (piu' del mezzo periodo del vibrato)
PITCH_CHANGE_MIN_GAP_S = 0.06   # un cambio cosi' vicino a un attacco gia' trovato e' lo stesso


def _pitch_change_onsets(centers, freqs, confs, threshold: float, rate: int, hop: int,
                         buf_size: int, existing) -> List[int]:
    """Attacchi dove l'altezza stabile cambia di almeno un semitono: la
    mediana delle stime nella finestra prima e in quella dopo differiscono,
    ed entrambe le finestre sono intonate (tutte le stime confidenti). Un
    cambio che segue di meno di due finestre di analisi un attacco gia'
    trovato e' quell'attacco visto in ritardo (la finestra conteneva ancora
    la nota prima, o la nota prima risuona ancora, come le corde di una
    chitarra), non una nota nuova."""
    import numpy as np
    k = max(2, int(round(PITCH_CHANGE_WINDOW_S * rate / hop)))
    ok = (confs >= threshold) & (freqs >= MIN_PITCH_HZ) & (freqs <= MAX_PITCH_HZ)
    midi = np.where(ok, 69.0 + 12.0 * np.log2(np.maximum(freqs, 1e-6) / 440.0), np.nan)
    marks = []
    for i in range(k, len(midi) - k + 1):
        before, after = midi[i - k:i], midi[i:i + k]
        if np.isnan(before).any() or np.isnan(after).any():
            continue
        diff = abs(float(np.median(after)) - float(np.median(before)))
        if diff >= 0.8:
            marks.append((i, diff))
    out: List[int] = []
    last_i = -10 ** 9
    for i, diff in marks:
        if i - last_i < k:                       # stessa transizione: tiene la piu' netta
            if diff > out_diff:
                out[-1], out_diff = int(centers[i]), diff
            last_i = i
            continue
        out.append(int(centers[i]))
        out_diff = diff
        last_i = i
    after_gap = PITCH_CHANGE_MIN_GAP_S * rate
    before_gap = max(after_gap, 2 * buf_size)     # la nota prima puo' ancora risuonare
    known = sorted(existing)
    import bisect
    kept = []
    for pos in out:
        j = bisect.bisect_left(known, pos)
        prev_ok = j == 0 or pos - known[j - 1] >= before_gap
        next_ok = j >= len(known) or known[j] - pos >= after_gap
        if prev_ok and next_ok:
            kept.append(pos)
    return kept


def detect_melodic_notes(wav_path: str, hop_size: Optional[int] = None,
                          buf_size: Optional[int] = None, min_freq_hz: Optional[float] = None,
                          progress_callback: Optional[Callable[[float], None]] = None,
                          confidence_threshold: Optional[float] = None,
                          min_note_duration_sec: Optional[float] = None,
                          ) -> List[AudioEvent]:
    """confidence_threshold e min_note_duration_sec sono override opzionali
    di PITCH_CONFIDENCE_THRESHOLD/MIN_NOTE_DURATION_SEC (vedi costanti
    sopra): lasciati a None si usano i default, permettendo pero' al
    chiamante (dialogo di importazione audio) di adattarli caso per caso su
    un audio specifico."""
    import bisect
    import numpy as np
    from .audio_dsp import detect_onsets, read_mono, yin

    if buf_size is None:
        buf_size = _buf_size_for_min_freq(min_freq_hz)
    if hop_size is None:
        hop_size = buf_size // 4
    if confidence_threshold is None:
        confidence_threshold = PITCH_CONFIDENCE_THRESHOLD

    def stage(lo, hi):
        return (lambda f: progress_callback(lo + (hi - lo) * f)) if progress_callback else None

    x, samplerate = read_mono(wav_path)
    total_read = len(x)
    # Attacchi dal contenuto spettrale (colpi, note pizzicate, sillabe)...
    found = detect_onsets(x, samplerate, progress=stage(0.0, 0.4), with_strength=True)
    n_blocks = -(-len(x) // LEVEL_HOP)
    padded = np.concatenate([x, np.zeros(n_blocks * LEVEL_HOP - len(x), np.float32)]).reshape(n_blocks, LEVEL_HOP)
    block_rms = np.sqrt(np.mean(np.square(padded, dtype=np.float64), axis=1)) if n_blocks else np.zeros(0)
    moved = _backtrack_onsets([pos for pos, _ in found], block_rms, samplerate)
    found = [(new, strength) for new, (_pos, strength) in zip(moved, found)]
    strong = {pos for pos, strength in found if strength >= STRONG_ONSET}
    onset_samples = [0] + [pos for pos, _ in found]
    # ...e stime di altezza al centro di ogni finestra di analisi.
    centers, freqs, confs = yin(x, samplerate, buf_size, hop_size, progress=stage(0.4, 1.0))
    pitch_frames = list(zip(centers.tolist(), freqs.tolist(), confs.tolist()))
    # ...piu' i cambi d'altezza senza attacco (legato cantato o suonato).
    changes = _pitch_change_onsets(centers, freqs, confs, confidence_threshold, samplerate,
                                   hop_size, buf_size, onset_samples)
    # anche un cambio d'altezza si vede tardi (la finestra deve contenere
    # soprattutto la nota nuova): se prima c'e' una valle del livello, la
    # nota comincia li'
    known = sorted(onset_samples)
    for pos in changes:
        j = bisect.bisect_left(known, pos)
        prev = known[j - 1] if j else 0
        onset_samples.append(max(prev + LEVEL_HOP, _backtrack_onsets([pos], block_rms, samplerate)[0])
                             if pos - prev > LEVEL_HOP else pos)
    block_peaks = np.abs(padded).max(axis=1) if n_blocks else np.zeros(0)
    peak_frames = [(k * LEVEL_HOP, float(v)) for k, v in enumerate(block_peaks)]

    onset_samples.append(total_read)
    onset_samples = sorted(set(onset_samples))
    # sotto la nota piu' grave dello strumento (con un margine di un tono)
    # una stima e' un errore d'ottava o rumore, non una nota suonabile
    low_hz = max(MIN_PITCH_HZ, min_freq_hz * 2 ** (-2 / 12)) if min_freq_hz else MIN_PITCH_HZ

    pitch_pos = [f[0] for f in pitch_frames]
    peak_pos = [p[0] for p in peak_frames]
    peaks = [p[1] for p in peak_frames]
    file_peak = max(peaks) if peaks else 0.0
    silence = file_peak * 10 ** (SILENCE_DB / 20.0)

    def level(start: int, end: int) -> float:
        a, b = bisect.bisect_left(peak_pos, max(0, start)), bisect.bisect_left(peak_pos, max(0, end))
        return max(peaks[a:b]) if b > a else 0.0

    raw = []   # (evento, nuovo attacco?)
    for i in range(len(onset_samples) - 1):
        seg_start, seg_end = onset_samples[i], onset_samples[i + 1]
        lo, hi = bisect.bisect_left(pitch_pos, seg_start), bisect.bisect_left(pitch_pos, seg_end)
        confident = [f for f in pitch_frames[lo:hi]
                     if f[2] >= confidence_threshold and low_hz <= f[1] <= MAX_PITCH_HZ]
        # le stime la cui finestra comincia prima dell'attacco "sentono" ancora
        # la nota precedente: se ne restano abbastanza, si usano solo le altre
        inside = [f for f in confident if f[0] - buf_size // 2 >= seg_start]
        if len(inside) >= 2:
            confident = inside
        if not confident:
            continue  # segmento silenzioso/non intonato (respiro, consonante...): nessuna nota
        freqs = sorted(f[1] for f in confident)
        median_freq = freqs[len(freqs) // 2]
        seg_freqs = freqs
        seg_frames = [(f[0], f[1]) for f in confident]      # in ordine di tempo
        a, b = bisect.bisect_left(peak_pos, seg_start), bisect.bisect_left(peak_pos, seg_end)
        seg_peaks = peaks[a:b]
        peak = max(seg_peaks) if seg_peaks else 0.0
        if peak <= silence:
            continue
        # Fine della nota: dopo il picco, l'ultimo hop ancora sopra la soglia.
        gate = max(peak * 10 ** (NOTE_END_DB / 20.0), silence)
        top = a + seg_peaks.index(peak)
        last = top
        # solo i blocchi tutti dentro il segmento: quello a cavallo del
        # prossimo attacco contiene gia' la nota successiva
        inside_end = bisect.bisect_right(peak_pos, seg_end - LEVEL_HOP)
        for k in range(top, inside_end):
            if peaks[k] >= gate:
                last = k
        if last + 1 >= inside_end:
            end_sample = seg_end        # suona fino al prossimo attacco
        else:
            end_sample = min(seg_end, peak_pos[last + 1])
        c, d = (bisect.bisect_left(peak_pos, max(0, seg_start - int(REATTACK_SEARCH[0] * samplerate))),
                bisect.bisect_left(peak_pos, seg_start + int(REATTACK_SEARCH[1] * samplerate)))
        if d > c:
            top_attack = max(range(c, d), key=lambda k: peaks[k])
            t_attack = peak_pos[top_attack]
            before = level(t_attack - int(REATTACK_BEFORE[0] * samplerate),
                           t_attack - int(REATTACK_BEFORE[1] * samplerate))
            reattack = peaks[top_attack] > REATTACK_RATIO * before
        else:
            reattack = True
        reattack = reattack or seg_start in strong
        raw.append((AudioEvent(
            start_sec=seg_start / samplerate, end_sec=end_sample / samplerate,
            velocity=max(1, min(127, int(round(peak * 127)))),
            midi_pitch=0,
        ), reattack, seg_freqs, seg_frames))

    # Accordatura dall'altezza delle note (pesate per numero di stime), poi
    # la nota di ciascun segmento
    tuning = estimate_tuning([r[2][len(r[2]) // 2] for r in raw], [len(r[2]) for r in raw])
    for ev, _reattack, seg_freqs, _frames in raw:
        ev.midi_pitch = _hz_to_midi(seg_freqs[len(seg_freqs) // 2], tuning)

    # Unisce note consecutive sulla stessa altezza (o quasi: vedi
    # MERGE_SEMITONES) solo se il secondo segmento non e' un nuovo attacco
    # (falso onset a meta' di una nota tenuta, es. per vibrato marcato):
    # musicalmente e' la stessa nota. Una nota ripetuta (pausa in mezzo o
    # nuovo attacco) resta distinta.
    def semitones(freqs):
        f = sorted(freqs)[len(freqs) // 2]
        return 69 + 12 * math.log2(f / 440.0) - tuning

    def pitch_after(i):
        """Altezza media (semitoni) nei MERGE_CONTEXT_S secondi dall'inizio
        del segmento i, fino al prossimo attacco vero."""
        start = raw[i][0].start_sec * samplerate
        limit = start + MERGE_CONTEXT_S * samplerate
        values = []
        for j in range(i, len(raw)):
            if j > i and (raw[j][1] or raw[j][0].start_sec * samplerate >= limit):
                break
            values += [69 + 12 * math.log2(f / 440.0) - tuning for t, f in raw[j][3] if t < limit]
        return sum(values) / len(values) if values else None

    merged: List[AudioEvent] = []
    merged_freqs: List[list] = []
    for i, (ev, reattack, seg_freqs, _frames) in enumerate(raw):
        prev = merged[-1] if merged else None
        after = pitch_after(i) if prev is not None and not reattack else None
        if (prev is not None and not reattack and abs(prev.end_sec - ev.start_sec) < 1e-9
                and (prev.midi_pitch == ev.midi_pitch
                     or (after is not None and abs(semitones(merged_freqs[-1]) - after) < MERGE_SEMITONES))):
            prev.end_sec = ev.end_sec
            prev.velocity = max(prev.velocity, ev.velocity)
            merged_freqs[-1] = merged_freqs[-1] + seg_freqs
            # l'altezza della nota intera, su tutte le sue stime
            prev.midi_pitch = _hz_to_midi(sorted(merged_freqs[-1])[len(merged_freqs[-1]) // 2], tuning)
        else:
            merged.append(ev)
            merged_freqs.append(list(seg_freqs))

    min_duration = MIN_NOTE_DURATION_SEC if min_note_duration_sec is None else min_note_duration_sec
    return [ev for ev in merged if (ev.end_sec - ev.start_sec) >= min_duration]
