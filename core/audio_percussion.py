"""
Rilevamento di colpi percussivi (transient/onset detection) da un file WAV,
usato per le tracce percussive (beatboxing/batteria) nella funzionalita' di
importazione audio.

Usa core.audio_dsp.detect_onsets per individuare i transienti (primo
passaggio, solo posizioni), poi classifica ciascun colpo con un
classificatore per bande di energia FFT (energia media per bin, non
sommata: vedi _classify_band) su una finestra presa ESATTAMENTE a partire
dal campione dell'attacco (secondo passaggio): frequenze basse dominanti
-> kick; altrimenti energia in banda media (150-1000Hz, il "corpo" del
fusto) maggiore o uguale a quella in banda alta (rumore di cordiera/
shimmer) -> snare; energia alta superiore -> hihat.

Nota di progetto: la classificazione automatica si limita volutamente a
kick/snare/hihat (non tenta di distinguere tom1/tom2/floor/crash/ride/
hihat_open dal solo spettro del transiente, inaffidabile senza un modello
dedicato). Il testo generato resta comunque editabile a mano come
qualunque altro token della traccia.

Parametro beatbox=True: ricalibra le soglie per una sorgente voce/beatbox
invece di una batteria vera (vedi BEATBOX_LOW_FREQ_HZ/BEATBOX_KICK_LOW_RATIO)
— il tratto vocale umano non puo' fisicamente produrre una risonanza grave
quanto quella di un fusto di batteria.
"""

from typing import Callable, List, Optional

from .audio_quantize import AudioEvent

DEFAULT_HOP_SIZE = 512
DEFAULT_ONSET_BUF_SIZE = 1024

# Finestra di classificazione: letta A PARTIRE dal campione esatto
# dell'attacco (mai da un buffer "storico" scorrevole, che finirebbe per
# catturare soprattutto il silenzio/la coda del suono precedente invece
# del corpo del nuovo colpo — causa piu' probabile di una classificazione
# sistematicamente sbilanciata su hihat). Si scarta un breve intervallo
# iniziale (il click transiente, largamente rumore a banda larga per
# qualunque tipo di colpo, poco discriminante) per analizzare il "corpo"
# del suono subito dopo, dove le differenze spettrali tra
# cassa/rullante/hihat sono molto piu' marcate.
SKIP_SAMPLES = 300               # ~7ms a 44100Hz
CLASSIFY_WINDOW_SAMPLES = 4096    # ~93ms a 44100Hz

# Finestra di soppressione dei doppioni: il rilevamento puo' scattare piu'
# volte per un singolo colpo reale (coda di risonanza/decadimento scambiata
# per un nuovo attacco) — alzare solo minioi non basta, perche' minioi tiene
# il PRIMO onset del gruppo anche se e' proprio quello spurio (es. un colpo
# debole prima dell'attacco vero), scartando invece l'onset corretto se
# arriva subito dopo. Qui invece si raggruppano gli onset entro questa
# finestra dal primo del gruppo e si tiene quello di AMPIEZZA MASSIMA
# (verificato su una registrazione reale: gli onset spuri hanno quasi
# sempre ampiezza di picco molto piu' bassa del colpo vero vicino). Valore
# tarato sotto il piu' piccolo intervallo reale fra due colpi osservato in
# quella registrazione (~350ms): piu' alto rischierebbe di fondere due
# colpi veri ravvicinati (es. rullimenti/pattern veloci).
DUPLICATE_ONSET_WINDOW_S = 0.28
# ...ma 0.28 s e' piu' di una croma a 120 BPM: con un valore fisso gli hihat
# tra cassa e rullante (e ogni figura in crome o sedicesimi) sparivano
# sempre. Quando si conosce la griglia scelta (tempo e suddivisione, vedi
# core.audio_import) la finestra scende a questa frazione dello slot, mai
# sotto MIN_DUPLICATE_WINDOW_S; i doppioni oltre la finestra li toglie
# TAIL_RETRIGGER_RATIO.
DUPLICATE_SLOT_FRACTION = 0.6
MIN_DUPLICATE_WINDOW_S = 0.04
# Un colpo entro DUPLICATE_ONSET_WINDOW_S dal precedente, dello STESSO tipo
# e con meno di questa frazione della sua velocity, e' la coda di risonanza
# del colpo prima che fa riscattare l'onset, non un colpo nuovo (un hihat
# dopo una cassa, di tipo diverso, resta).
TAIL_RETRIGGER_RATIO = 0.3
PEAK_WINDOW_SAMPLES = 2048
# Durata su cui si misura il livello di un colpo per la velocity (vedi
# hit_velocity): circa quella in cui l'orecchio integra un suono breve.
LOUDNESS_WINDOW_S = 0.05

LOW_FREQ_HZ = 150
HIGH_FREQ_HZ = 1000

# Sopra questa quota di energia in banda bassa, il colpo e' una cassa: ben
# separato da qualunque altro colpo (verificato su spettri sintetici
# realistici: cassa ~0.9-0.99, rullante/hihat sempre sotto 0.1). Sotto
# questa soglia, si distingue rullante da hihat confrontando media/alta:
# un rullante ha corpo del fusto in banda media (150-1000Hz) comparabile o
# superiore al rumore di cordiera in banda alta; un hihat e' quasi tutto
# concentrato in banda alta (shimmer metallico), con la media trascurabile.
KICK_LOW_RATIO = 0.45

# Calibrazione alternativa per sorgente voce/beatbox. PRIMO TENTATIVO (banda
# bassa allargata a 250Hz + soglia 0.30) rivelatosi TROPPO aggressivo nella
# prova reale: il fondamentale della voce (~85-255Hz per la maggior parte
# delle persone) ricade quasi sempre sotto 250Hz per QUALUNQUE suono
# vocalizzato, non solo per un "boom" di kick, quindi finiva per classificare
# come kick anche snare/hihat imitati con la bocca. Corretto in modo molto
# piu' prudente: banda bassa INVARIATA (150Hz, come per una batteria vera —
# allargarla e' proprio cio' che causava il problema), solo la soglia
# abbassata leggermente. Resta comunque una stima non validata su
# registrazioni reali: vedi diagnose_audio.py per calibrare sui tuoi dati.
BEATBOX_LOW_FREQ_HZ = LOW_FREQ_HZ
BEATBOX_KICK_LOW_RATIO = 0.38


_audio_cache = {}


def _load(wav_path: str):
    """Campioni e frequenza del file (letto una volta sola, finche' non
    cambia: le finestre dei colpi si ritagliano dall'array in memoria)."""
    import os
    from .audio_dsp import read_mono
    st = os.stat(wav_path)
    key = (os.path.abspath(wav_path), st.st_mtime, st.st_size)
    if key not in _audio_cache:
        _audio_cache.clear()
        _audio_cache[key] = read_mono(wav_path)
    return _audio_cache[key]


def _read_window(wav_path: str, start_sample: int, n_samples: int, hop_size: int = 0):
    """n_samples campioni a partire da start_sample (meno, a fine file).
    hop_size non serve piu' (resta per compatibilita' con diagnose_audio.py)."""
    x, _rate = _load(wav_path)
    start = max(0, int(start_sample))
    return x[start:start + n_samples]


def compute_band_ratios(window, samplerate: int, low_freq_hz: float = LOW_FREQ_HZ,
                         high_freq_hz: float = HIGH_FREQ_HZ, noise_spectrum=None):
    """Energia media per bin (non sommata, vedi nota sotto) in banda bassa/
    media/alta, come frazioni che sommano a 1.0. Estratta a parte (invece di
    restare privata dentro _classify_band) cosi' diagnose_audio.py puo'
    mostrare gli stessi numeri usati dalla classificazione, per calibrare le
    soglie su dati reali invece che a occhio.

    noise_spectrum, se passato (vedi estimate_noise_floor), viene sottratto
    dallo spettro del colpo prima di calcolare le bande: su una registrazione
    reale con un ronzio stazionario (alimentatore/USB/massa) anche debole, il
    ronzio si concentra su pochissimi bin e ne gonfia la media quanto o piu'
    di un vero fondamentale di cassa, rendendo kick/rullante/hihat
    indistinguibili by banda bassa da soli (verificato: un tono fisso
    presente identico persino nel silenzio prima del primo colpo dominava la
    banda bassa di OGNI colpo, incluso l'hihat)."""
    import numpy as np

    if len(window) == 0:
        return 0.0, 0.0, 0.0

    # Rimozione della componente continua (offset DC): non sottrarla fa
    # trapelare qualunque bias di ampiezza medio non nullo del segnale
    # direttamente nel bin 0/vicino-0, gonfiando artificialmente la banda
    # bassa indipendentemente dal contenuto reale del colpo (verificato: bin
    # 0-20Hz con media 613 col DC incluso, 0.0002 senza).
    w = (window.astype(np.float64) - window.mean()) * np.hanning(len(window))
    spectrum = np.abs(np.fft.rfft(w))
    if noise_spectrum is not None and len(noise_spectrum) == len(spectrum):
        # Sottrazione parziale (fattore 0.5, non il rumore intero) con
        # pavimento al 30% del valore originale, non azzeramento secco: su
        # un colpo debole, l'energia propria in banda bassa puo' essere
        # comparabile o inferiore al rumore stimato in quella stessa banda
        # (dove il rumore e' piu' forte) — sottrarre tutto il rumore e
        # azzerare quasi del tutto quei bin sbilancia artificialmente il
        # rapporto verso media/alta (dove il rumore e' quasi nullo, quindi
        # sopravvive quasi intatta), facendo scambiare colpi deboli per
        # rullante a prescindere dal loro vero timbro (verificato: cassa
        # debole con energia bassa comparabile al rumore, scambiata per
        # rullante). Valori scelti su misurazioni reali (vedi
        # diagnose_audio.py su registrazioni isolate kick/snare/hihat):
        # miglior compromesso fra pulizia della cassa e correzione di
        # rullante/hihat fra le combinazioni provate.
        spectrum = np.maximum(spectrum - 0.5 * noise_spectrum, 0.3 * spectrum)
    freqs = np.fft.rfftfreq(len(w), d=1.0 / samplerate)

    # Media (non somma) per bin: la banda alta copre migliaia di bin contro
    # una decina della banda bassa (risoluzione dell'FFT lineare in Hz), una
    # somma grezza sbilancerebbe sistematicamente la classificazione verso
    # "alta energia" per qualunque contenuto a banda larga (rumore/colpo
    # reale), indipendentemente dal reale bilanciamento percettivo tra le
    # bande — causa concreta di una vecchia versione che classificava quasi
    # tutto come hihat.
    low_bins = spectrum[freqs < low_freq_hz]
    mid_bins = spectrum[(freqs >= low_freq_hz) & (freqs < high_freq_hz)]
    high_bins = spectrum[freqs >= high_freq_hz]
    low = low_bins.mean() if len(low_bins) else 0.0
    mid = mid_bins.mean() if len(mid_bins) else 0.0
    high = high_bins.mean() if len(high_bins) else 0.0
    total = low + mid + high + 1e-9
    return low / total, mid / total, high / total


def hit_velocity(window, samplerate: int) -> int:
    """Velocity del colpo dal livello efficace dei primi LOUDNESS_WINDOW_S
    (come un'onda sinusoidale di pari energia: RMS * radice di 2), non dal
    picco: un hihat ha picchi alti quanto una cassa ma molta meno energia,
    e all'orecchio e' piu' debole."""
    import numpy as np

    head = np.asarray(window[:max(1, int(LOUDNESS_WINDOW_S * samplerate))], dtype=np.float64)
    if len(head) == 0:
        return 60
    level = float(np.sqrt(np.mean(head * head)) * np.sqrt(2.0))
    return max(1, min(127, int(round(level * 127))))


def _classify_band(window, samplerate: int, beatbox: bool = False, noise_spectrum=None):
    import numpy as np

    if len(window) == 0:
        return "snare", 60

    low_freq_hz = BEATBOX_LOW_FREQ_HZ if beatbox else LOW_FREQ_HZ
    kick_low_ratio = BEATBOX_KICK_LOW_RATIO if beatbox else KICK_LOW_RATIO

    low_ratio, mid_ratio, high_ratio = compute_band_ratios(
        window, samplerate, low_freq_hz, HIGH_FREQ_HZ, noise_spectrum=noise_spectrum)

    velocity = hit_velocity(window, samplerate)

    if low_ratio > kick_low_ratio:
        return "kick", velocity
    return ("snare", velocity) if mid_ratio >= high_ratio else ("hihat", velocity)


def estimate_noise_floor(wav_path: str, onset_samples, samplerate: int,
                          hop_size: int = DEFAULT_HOP_SIZE):
    """Stima lo spettro di un rumore di fondo stazionario (ronzio di
    alimentatore/USB/massa, ecc.) sempre presente nella registrazione,
    misurando lo spettro subito PRIMA di ogni colpo (quando il colpo
    precedente si e' gia' esaurito) e prendendone la mediana per bin: un
    ronzio stazionario appare pressoche' identico in ogni finestra
    pre-colpo, mentre la coda del colpo precedente contamina solo una
    minoranza di quelle finestre (quelle troppo vicine al colpo prima), che
    la mediana scarta come outlier. Ritorna None se non ci sono abbastanza
    campioni di silenzio pre-colpo da misurare (es. il primo colpo e' troppo
    vicino all'inizio del file)."""
    import numpy as np

    spectra = []
    for onset_sample in onset_samples:
        start = onset_sample - CLASSIFY_WINDOW_SAMPLES
        if start < 0:
            continue
        window = _read_window(wav_path, start, CLASSIFY_WINDOW_SAMPLES, hop_size)
        if len(window) < CLASSIFY_WINDOW_SAMPLES:
            continue
        w = (window.astype(np.float64) - window.mean()) * np.hanning(len(window))
        spectra.append(np.abs(np.fft.rfft(w)))

    if not spectra:
        return None
    return np.median(np.array(spectra), axis=0)


def suppress_duplicate_onsets(wav_path: str, onset_samples, samplerate: int,
                               hop_size: int = DEFAULT_HOP_SIZE,
                               window_s: float = DUPLICATE_ONSET_WINDOW_S):
    """Raggruppa gli onset entro window_s dal primo di ciascun gruppo e
    tiene solo quello di ampiezza di picco massima (vedi nota su
    DUPLICATE_ONSET_WINDOW_S): riduce i doppioni causati dalla coda di
    risonanza di un colpo scambiata per un nuovo attacco, mantenendo quello
    vero anche quando non e' il primo a scattare nel gruppo."""
    import numpy as np

    if not onset_samples:
        return list(onset_samples)

    peaks = []
    for onset_sample in onset_samples:
        window = _read_window(wav_path, onset_sample, PEAK_WINDOW_SAMPLES, hop_size)
        peaks.append(float(np.max(np.abs(window))) if len(window) else 0.0)

    window_samples = window_s * samplerate
    kept = []
    i = 0
    n = len(onset_samples)
    while i < n:
        j = i
        cluster_start = onset_samples[i]
        while j + 1 < n and (onset_samples[j + 1] - cluster_start) < window_samples:
            j += 1
        best = max(range(i, j + 1), key=lambda k: peaks[k])
        kept.append(onset_samples[best])
        i = j + 1
    return kept


def detect_onset_samples(wav_path: str, hop_size: int = DEFAULT_HOP_SIZE,
                          onset_buf_size: int = DEFAULT_ONSET_BUF_SIZE,
                          progress_callback: Optional[Callable[[float], None]] = None):
    """Primo passaggio: solo posizioni (in campioni) degli onset rilevati
    (vedi core.audio_dsp.detect_onsets). Estratta a parte cosi'
    diagnose_audio.py puo' ispezionare ogni colpo senza duplicare la logica
    di rilevamento. hop_size e onset_buf_size non servono piu' (restano per
    compatibilita')."""
    from .audio_dsp import detect_onsets
    x, samplerate = _load(wav_path)
    progress = (lambda f: progress_callback(0.5 * f)) if progress_callback else None
    return detect_onsets(x, samplerate, percussive=True, progress=progress), samplerate


def duplicate_window_s(slot_s: Optional[float]) -> float:
    """Finestra di soppressione dei doppioni per una griglia con slot di
    slot_s secondi (None: griglia sconosciuta, il valore storico fisso)."""
    if slot_s is None:
        return DUPLICATE_ONSET_WINDOW_S
    return min(DUPLICATE_ONSET_WINDOW_S, max(MIN_DUPLICATE_WINDOW_S, DUPLICATE_SLOT_FRACTION * slot_s))


def drop_tail_retriggers(events: List[AudioEvent]) -> List[AudioEvent]:
    """Toglie i colpi che sono la coda del colpo precedente dello stesso tipo
    (vedi TAIL_RETRIGGER_RATIO)."""
    kept: List[AudioEvent] = []
    for ev in events:
        prev = kept[-1] if kept else None
        if (prev is not None and ev.perc_name == prev.perc_name
                and ev.start_sec - prev.start_sec < DUPLICATE_ONSET_WINDOW_S
                and ev.velocity < TAIL_RETRIGGER_RATIO * prev.velocity):
            continue
        kept.append(ev)
    return kept


def detect_percussive_hits(wav_path: str, hop_size: int = DEFAULT_HOP_SIZE,
                            onset_buf_size: int = DEFAULT_ONSET_BUF_SIZE,
                            beatbox: bool = False,
                            progress_callback: Optional[Callable[[float], None]] = None,
                            slot_s: Optional[float] = None,
                            ) -> List[AudioEvent]:
    """slot_s: durata in secondi di uno slot della griglia di quantizzazione
    scelta, per non fondere colpi veri piu' vicini dei 0.28 s storici (vedi
    duplicate_window_s)."""
    onset_samples, samplerate = detect_onset_samples(
        wav_path, hop_size, onset_buf_size, progress_callback=progress_callback,
    )
    noise_spectrum = estimate_noise_floor(wav_path, onset_samples, samplerate, hop_size)
    onset_samples = suppress_duplicate_onsets(wav_path, onset_samples, samplerate, hop_size,
                                              window_s=duplicate_window_s(slot_s))

    # Secondo passaggio: per ogni onset, classificazione sulla finestra
    # letta esattamente a partire da quel campione (vedi _read_window).
    events: List[AudioEvent] = []
    n = len(onset_samples)
    for i, onset_sample in enumerate(onset_samples):
        window = _read_window(wav_path, onset_sample + SKIP_SAMPLES, CLASSIFY_WINDOW_SAMPLES, hop_size)
        name, velocity = _classify_band(window, samplerate, beatbox=beatbox, noise_spectrum=noise_spectrum)
        start_sec = onset_sample / float(samplerate)
        events.append(AudioEvent(start_sec=start_sec, end_sec=start_sec, velocity=velocity, perc_name=name))
        if progress_callback and n:
            progress_callback(0.5 + 0.5 * (i + 1) / n)

    return drop_tail_retriggers(events) if slot_s is not None else events
