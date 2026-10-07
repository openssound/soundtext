"""
Tracce audio (fase 1): file audio registrati altrove (voce, chitarra o
tastiera collegate alla scheda audio) posizionati nel brano come clip
(core.model.AudioClip) e mixati sopra al rendering MIDI in riproduzione ed
esportazione.

I file non vengono mai modificati: spostare, rinominare o cambiare il gain
di una clip cambia solo i suoi parametri nel progetto. All'importazione ogni
file viene convertito una volta sola in WAV a AUDIO_SAMPLE_RATE (la stessa
frequenza dei rendering di fluidsynth, vedi core.playback), cosi' il mix non
deve ricampionare niente a ogni ascolto.

Dove stanno i file:
- progetto gia' salvato: nella cartella '<NomeProgetto>_audio/' accanto al
  file .st (vedi audio_dir_for_project);
- progetto mai salvato: in una cartella temporanea (staging_audio_dir), da
  cui il primo salvataggio li copia nella cartella del progetto
  (consolidate_project_audio, chiamata da core.project_io.save_project_file).
In memoria AudioClip.file e' sempre un percorso assoluto; nel file .st e'
relativo alla cartella del progetto (vedi core.project_io).

Il tempo del brano non stira l'audio: una clip e' ancorata al beat in cui
inizia (convertito in secondi con la mappa del tempo) e dura quanto il file.
"""

import contextlib
import math
import os
import shutil
import struct
import tempfile
import threading
import wave
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from .model import AudioClip, Project, Track
from .i18n import tr

AUDIO_SAMPLE_RATE = 48000
AUDIO_DIR_SUFFIX = "_audio"
# Estensioni proposte dal dialogo di importazione: .wav lo legge SoundText,
# le altre il decodificatore di Qt Multimedia (o ffmpeg, vedi
# core.audio_decode).
AUDIO_FILE_EXTENSIONS = (".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aif", ".aiff")

_WAVE_FORMAT_PCM = 1
_WAVE_FORMAT_IEEE_FLOAT = 3
_WAVE_FORMAT_EXTENSIBLE = 0xFFFE


# ---------------------------------------------------------------------------
# Lettura/scrittura WAV
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WavInfo:
    format_tag: int      # _WAVE_FORMAT_PCM o _WAVE_FORMAT_IEEE_FLOAT
    channels: int
    samplerate: int
    bits: int
    data_offset: int
    data_size: int

    @property
    def frames(self) -> int:
        block = self.channels * (self.bits // 8)
        return self.data_size // block if block else 0

    @property
    def seconds(self) -> float:
        return self.frames / float(self.samplerate) if self.samplerate else 0.0


def read_wav_info(path: str) -> WavInfo:
    """Legge solo l'intestazione di un WAV (PCM intero 8/16/24/32 bit o
    float 32/64 bit, anche WAVE_FORMAT_EXTENSIBLE): il modulo 'wave' della
    stdlib non legge i WAV in virgola mobile, che molti programmi di
    registrazione producono di default. Solleva ValueError se il file non e'
    un WAV supportato."""
    with open(path, "rb") as f:
        header = f.read(12)
        if len(header) < 12 or header[:4] != b"RIFF" or header[8:12] != b"WAVE":
            raise ValueError(tr("'{0}' non e' un file WAV", os.path.basename(path)))
        fmt = None
        while True:
            chunk = f.read(8)
            if len(chunk) < 8:
                break
            chunk_id, size = chunk[:4], struct.unpack("<I", chunk[4:])[0]
            if chunk_id == b"fmt ":
                body = f.read(size)
                format_tag, channels, samplerate = struct.unpack("<HHI", body[:8])
                bits = struct.unpack("<H", body[14:16])[0]
                if format_tag == _WAVE_FORMAT_EXTENSIBLE and len(body) >= 26:
                    format_tag = struct.unpack("<H", body[24:26])[0]
                fmt = (format_tag, channels, samplerate, bits)
                if size % 2:
                    f.read(1)
            elif chunk_id == b"data":
                if fmt is None:
                    break
                offset = f.tell()
                # Alcuni registratori lasciano 0 o 0xFFFFFFFF se interrotti:
                # si usa allora la dimensione reale del file.
                real = os.path.getsize(path) - offset
                data_size = real if size in (0, 0xFFFFFFFF) or size > real else size
                format_tag, channels, samplerate, bits = fmt
                supported = ((format_tag == _WAVE_FORMAT_PCM and bits in (8, 16, 24, 32))
                             or (format_tag == _WAVE_FORMAT_IEEE_FLOAT and bits in (32, 64)))
                if not supported or channels < 1 or samplerate < 1:
                    raise ValueError(
                        tr("Formato WAV non supportato in '{0}' (codifica {format_tag}, {bits} bit)", os.path.basename(path), format_tag=format_tag, bits=bits))
                return WavInfo(format_tag, channels, samplerate, bits, offset, data_size)
            else:
                f.seek(size + (size % 2), os.SEEK_CUR)
    raise ValueError(tr("'{0}': WAV senza dati audio leggibili", os.path.basename(path)))


def read_wav(path: str) -> Tuple[np.ndarray, int]:
    """Campioni float32 in [-1, 1] di forma (frame, canali) e frequenza."""
    info = read_wav_info(path)
    with open(path, "rb") as f:
        f.seek(info.data_offset)
        raw = f.read(info.frames * info.channels * (info.bits // 8))
    if info.format_tag == _WAVE_FORMAT_IEEE_FLOAT:
        data = np.frombuffer(raw, dtype="<f4" if info.bits == 32 else "<f8").astype(np.float32)
    elif info.bits == 8:
        data = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif info.bits == 16:
        data = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    elif info.bits == 24:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        ints = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        ints = np.where(ints & 0x800000, ints - 0x1000000, ints)
        data = ints.astype(np.float32) / 8388608.0
    else:
        data = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
    return data.reshape(-1, info.channels), info.samplerate


def write_wav(path: str, samples: np.ndarray, samplerate: int, bits: int = 24) -> None:
    """Scrive samples (float, forma (frame, canali), [-1, 1]; oltre viene
    limitato) come WAV PCM a 16 o 24 bit."""
    if samples.ndim == 1:
        samples = samples.reshape(-1, 1)
    clipped = np.clip(samples, -1.0, 1.0)
    if bits == 16:
        raw = np.round(clipped * 32767.0).astype("<i2").tobytes()
    elif bits == 24:
        ints = np.round(clipped * 8388607.0).astype("<i4")
        raw = ints.view(np.uint8).reshape(-1, 4)[:, :3].tobytes()
    else:
        raise ValueError(tr("bits deve essere 16 o 24"))
    with contextlib.closing(wave.open(path, "wb")) as w:
        w.setnchannels(samples.shape[1])
        w.setsampwidth(bits // 8)
        w.setframerate(samplerate)
        w.writeframes(raw)


def resample(samples: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    """Ricampionamento per interpolazione lineare (quando serve al volo,
    es. la base di una registrazione): veloce ma perde qualcosa sugli
    acuti; per l'importazione dei file c'e' resample_hq."""
    if src_rate == dst_rate or len(samples) == 0:
        return samples
    n_out = int(round(len(samples) * dst_rate / float(src_rate)))
    src_t = np.arange(len(samples), dtype=np.float64)
    dst_t = np.arange(n_out, dtype=np.float64) * (src_rate / float(dst_rate))
    return np.stack([np.interp(dst_t, src_t, samples[:, c]) for c in range(samples.shape[1])],
                    axis=1).astype(np.float32)


# Ricampionamento di qualita' per l'importazione dei file: nel dominio della
# frequenza, a blocchi sovrapposti. Banda passante fino a _HQ_PASS della
# Nyquist piu' bassa, poi discesa a coseno fino alla Nyquist (niente
# aliasing, niente "squillo" di un taglio netto).
_HQ_PASS = 0.90
_HQ_BLOCK = 1 << 16          # campioni d'ingresso per blocco (circa)
_HQ_MARGIN = 2048            # sovrapposizione per lato, scartata


def resample_hq(samples: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    """Ricampiona samples (forma (frame, canali) o (frame,)) senza le
    perdite sugli acuti dell'interpolazione lineare di resample(): per
    l'importazione, che avviene una volta sola."""
    src_rate, dst_rate = int(src_rate), int(dst_rate)
    if src_rate == dst_rate or len(samples) == 0:
        return samples
    x = np.asarray(samples, dtype=np.float32)
    flat = x.ndim == 1
    if flat:
        x = x[:, None]
    g = math.gcd(src_rate, dst_rate)
    up, down = dst_rate // g, src_rate // g
    # blocchi e margini multipli di down: ogni blocco da' un numero intero di uscite
    block = down * max(1, -(-_HQ_BLOCK // down))
    margin = down * max(1, -(-_HQ_MARGIN // down))
    n_in = block + 2 * margin
    n_out_block = n_in // down * up
    keep_from, keep = margin // down * up, block // down * up
    bins_in, bins_out = n_in // 2 + 1, n_out_block // 2 + 1
    shared = min(bins_in, bins_out)
    nyq_bin = shared - 1
    f = np.arange(shared) / max(nyq_bin, 1)
    taper = np.where(f <= _HQ_PASS, 1.0, 0.5 * (1 + np.cos(np.pi * (f - _HQ_PASS) / (1 - _HQ_PASS))))
    taper *= n_out_block / n_in
    n_out = int(round(len(x) * dst_rate / src_rate))
    padded = np.concatenate([np.zeros((margin, x.shape[1]), np.float32), x,
                             np.zeros((block + margin, x.shape[1]), np.float32)])
    out = np.empty((n_out, x.shape[1]), dtype=np.float32)
    spec = np.zeros((bins_out, x.shape[1]), dtype=np.complex128)
    pos = 0
    for start in range(0, len(x), block):
        seg = padded[start:start + n_in]
        spec[:shared] = np.fft.rfft(seg, axis=0)[:shared] * taper[:, None]
        y = np.fft.irfft(spec, n_out_block, axis=0)[keep_from:keep_from + keep]
        take = min(len(y), n_out - pos)
        out[pos:pos + take] = y[:take]
        pos += take
        if pos >= n_out:
            break
    return out[:, 0] if flat else out


# ---------------------------------------------------------------------------
# Cartelle e importazione dei file
# ---------------------------------------------------------------------------

def audio_dir_for_project(project_path: str) -> str:
    """'<cartella>/<NomeProgetto>_audio' per il progetto salvato in project_path."""
    stem = os.path.splitext(os.path.basename(project_path))[0]
    return os.path.join(os.path.dirname(os.path.abspath(project_path)), stem + AUDIO_DIR_SUFFIX)


def staging_audio_dir() -> str:
    """Dove finiscono i file importati in un progetto non ancora salvato."""
    path = os.path.join(tempfile.gettempdir(), "soundtext_audio_non_salvato")
    os.makedirs(path, exist_ok=True)
    return path


def target_audio_dir(project_path: Optional[str]) -> str:
    """Cartella in cui importare un nuovo file audio per il progetto
    salvato in project_path (None = mai salvato), creata se serve."""
    path = audio_dir_for_project(project_path) if project_path else staging_audio_dir()
    os.makedirs(path, exist_ok=True)
    return path


def _safe_stem(name: str) -> str:
    stem = "".join(ch if ch.isalnum() or ch in " _-." else "_" for ch in name).strip(" .")
    return stem or "audio"


def unique_audio_path(directory: str, base_name: str, ext: str = ".wav") -> str:
    """Percorso libero in directory: base_name.wav, poi base_name_2.wav, ..."""
    stem = _safe_stem(base_name)
    candidate = os.path.join(directory, stem + ext)
    n = 2
    while os.path.exists(candidate):
        candidate = os.path.join(directory, f"{stem}_{n}{ext}")
        n += 1
    return candidate


def import_audio_file(src_path: str, dest_dir: str) -> str:
    """Copia/converte src_path in un WAV a AUDIO_SAMPLE_RATE dentro
    dest_dir e ritorna il nuovo percorso (assoluto). Un WAV PCM gia' a
    48 kHz viene copiato cosi' com'e'; gli altri file (WAV a un'altra
    frequenza, mp3/m4a/flac/ogg/aiff, vedi core.audio_decode) vengono
    ricampionati (resample_hq) e salvati a 24 bit. Solleva RuntimeError con
    un messaggio leggibile se il file non si puo' importare."""
    from .audio_decode import read_audio

    if not os.path.isfile(src_path):
        raise RuntimeError(tr("File audio non trovato: '{src_path}'", src_path=src_path))
    os.makedirs(dest_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(src_path))[0]
    out_path = unique_audio_path(dest_dir, stem)
    if os.path.splitext(src_path)[1].lower() == ".wav":
        try:
            info = read_wav_info(src_path)
        except ValueError:
            info = None   # WAV insolito (es. compresso): ci pensa read_audio
        if info is not None and info.samplerate == AUDIO_SAMPLE_RATE and info.format_tag == _WAVE_FORMAT_PCM \
                and info.bits in (16, 24):
            shutil.copyfile(src_path, out_path)
            return out_path
    samples, rate = read_audio(src_path)
    write_wav(out_path, resample_hq(samples, rate, AUDIO_SAMPLE_RATE), AUDIO_SAMPLE_RATE, bits=24)
    return out_path


def consolidate_project_audio(project: Project, project_path: str) -> int:
    """Porta nella cartella audio del progetto (audio_dir_for_project) i
    file delle clip che stanno altrove (cartella temporanea di un progetto
    mai salvato, cartella di un altro progetto dopo 'Salva con nome'),
    copiandoli e aggiornando AudioClip.file. I file mancanti restano
    com'erano. Ritorna quanti file sono stati copiati."""
    audio_dir = audio_dir_for_project(project_path)
    copied: Dict[str, str] = {}
    for track in project.tracks:
        for clip in track.audio_clips:
            src = os.path.abspath(clip.file)
            if os.path.dirname(src) == audio_dir or not os.path.isfile(src):
                continue
            if src not in copied:
                os.makedirs(audio_dir, exist_ok=True)
                dest = os.path.join(audio_dir, os.path.basename(src))
                if os.path.exists(dest) and not _same_file_content(src, dest):
                    stem, ext = os.path.splitext(os.path.basename(src))
                    dest = unique_audio_path(audio_dir, stem, ext)
                if not os.path.exists(dest):
                    shutil.copyfile(src, dest)
                copied[src] = dest
            clip.file = copied[src]
    return len(copied)


def _same_file_content(a: str, b: str) -> bool:
    try:
        if os.path.getsize(a) != os.path.getsize(b):
            return False
        with open(a, "rb") as fa, open(b, "rb") as fb:
            while True:
                ca, cb = fa.read(1 << 20), fb.read(1 << 20)
                if ca != cb:
                    return False
                if not ca:
                    return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Durata e posizione delle clip
# ---------------------------------------------------------------------------

_info_cache: Dict[tuple, Optional[WavInfo]] = {}
_info_lock = threading.Lock()


def _file_key(path: str) -> Optional[tuple]:
    try:
        st = os.stat(path)
    except OSError:
        return None
    return (os.path.abspath(path), st.st_size, st.st_mtime_ns)


def cached_wav_info(path: str) -> Optional[WavInfo]:
    """read_wav_info con cache (per percorso, dimensione e data di
    modifica): la vista Struttura brano la chiede a ogni ridisegno. None se
    il file manca o non e' leggibile."""
    key = _file_key(path)
    if key is None:
        return None
    with _info_lock:
        if key in _info_cache:
            return _info_cache[key]
    try:
        info = read_wav_info(path)
    except (ValueError, OSError, struct.error):
        info = None
    with _info_lock:
        _info_cache[key] = info
    return info


MISSING_CLIP_BEATS = 4.0


def clip_is_missing(clip: AudioClip) -> bool:
    return cached_wav_info(clip.file) is None


def clip_play_seconds(clip: AudioClip) -> float:
    """Secondi effettivamente riprodotti (file meno i tagli); 0 se manca."""
    info = cached_wav_info(clip.file)
    if info is None:
        return 0.0
    return max(0.0, info.seconds - max(0.0, clip.trim_start) - max(0.0, clip.trim_end))


def clip_duration_beats(clip: AudioClip, tempo_map) -> float:
    """Durata in beat della clip nella posizione in cui si trova (con cambi
    di tempo la stessa clip occupa piu' o meno beat a seconda di dove sta).
    Una clip con il file mancante vale MISSING_CLIP_BEATS, cosi' resta
    visibile (e cliccabile per ritrovare il file) nella vista Struttura brano."""
    from .tempo_map import beat_at_elapsed_seconds, seconds_for_beats
    seconds = clip_play_seconds(clip)
    if seconds <= 0:
        return MISSING_CLIP_BEATS
    start_s = seconds_for_beats(tempo_map, clip.start_beat)
    return beat_at_elapsed_seconds(tempo_map, 0.0, start_s + seconds) - clip.start_beat


def audio_tracks_end_beat(project: Project, tracks: List[Track], tempo_map=None) -> float:
    """Beat in cui finisce l'ultima clip audio (con il file presente: una
    mancante non suona) delle tracce indicate."""
    clips = [c for t in tracks if t.is_audio for c in t.audio_clips if clip_play_seconds(c) > 0]
    if not clips:
        return 0.0
    if tempo_map is None:
        from .tempo_map import build_tempo_beat_map
        tempo_map = build_tempo_beat_map(project, tracks=tracks)
    return max(c.start_beat + clip_duration_beats(c, tempo_map) for c in clips)


# ---------------------------------------------------------------------------
# Taglio e divisione delle clip (vista Struttura brano)
# ---------------------------------------------------------------------------

MIN_CLIP_SECONDS = 0.05


def clip_file_seconds(clip: AudioClip) -> float:
    info = cached_wav_info(clip.file)
    return info.seconds if info else 0.0


def trim_clip_start_to_beat(clip: AudioClip, new_start_beat: float, tempo_map) -> None:
    """Sposta l'inizio della clip a new_start_beat lasciando l'audio dov'e'
    nel tempo (si scopre o si nasconde l'inizio del file, come trascinando
    il bordo sinistro in un DAW). Trascinando a sinistra si puo' tornare
    fino all'inizio del file: per una ripresa, anche dentro il conteggio
    (note d'attacco suonate in anticipo)."""
    from .tempo_map import beat_at_elapsed_seconds, seconds_for_beats
    total = clip_file_seconds(clip)
    if total <= 0:
        return
    old_s = seconds_for_beats(tempo_map, clip.start_beat)
    new_s = seconds_for_beats(tempo_map, max(0.0, new_start_beat))
    trim = clip.trim_start + (new_s - old_s)
    trim = max(0.0, min(trim, total - max(0.0, clip.trim_end) - MIN_CLIP_SECONDS))
    clip.start_beat = round(beat_at_elapsed_seconds(tempo_map, 0.0, old_s + trim - clip.trim_start), 6)
    clip.trim_start = round(trim, 6)


def trim_clip_end_to_beat(clip: AudioClip, new_end_beat: float, tempo_map) -> None:
    """Fa finire la clip a new_end_beat (al massimo alla fine del file)."""
    from .tempo_map import seconds_for_beats
    total = clip_file_seconds(clip)
    if total <= 0:
        return
    play = seconds_for_beats(tempo_map, new_end_beat) - seconds_for_beats(tempo_map, clip.start_beat)
    play = max(MIN_CLIP_SECONDS, min(play, total - clip.trim_start))
    clip.trim_end = round(max(0.0, total - clip.trim_start - play), 6)


def split_clip(clip: AudioClip, at_beat: float, tempo_map) -> Optional[AudioClip]:
    """Divide la clip a at_beat: clip diventa la prima parte e viene
    ritornata la seconda (stesso file, tagli diversi). None se at_beat non
    cade dentro la clip."""
    from .tempo_map import seconds_for_beats
    total = clip_file_seconds(clip)
    offset = seconds_for_beats(tempo_map, at_beat) - seconds_for_beats(tempo_map, clip.start_beat)
    if total <= 0 or offset < MIN_CLIP_SECONDS or offset > clip_play_seconds(clip) - MIN_CLIP_SECONDS:
        return None
    second = AudioClip(name=f"{clip.name} (2)", file=clip.file, start_beat=round(at_beat, 6),
                       trim_start=round(clip.trim_start + offset, 6), trim_end=clip.trim_end,
                       gain_db=clip.gain_db)
    clip.trim_end = round(max(0.0, total - clip.trim_start - offset), 6)
    return second


def extract_clip_audio(clip: AudioClip, out_path: str) -> None:
    """Scrive in out_path solo la parte riprodotta della clip (per
    convertirla in notazione, vedi gui.audio_import_dialog)."""
    samples, rate = read_wav(clip.file)
    first = int(round(max(0.0, clip.trim_start) * rate))
    last = len(samples) - int(round(max(0.0, clip.trim_end) * rate))
    write_wav(out_path, samples[first:max(first, last)], rate, bits=16)


# ---------------------------------------------------------------------------
# Forma d'onda (per la vista Struttura brano)
# ---------------------------------------------------------------------------

_PEAK_BLOCK_FRAMES = 256
_peaks_cache: Dict[tuple, np.ndarray] = {}
_PEAKS_CACHE_MAX = 32


def waveform_peaks(clip: AudioClip, buckets: int) -> Optional[np.ndarray]:
    """buckets valori in [0, 1] (picco del valore assoluto, tutti i canali)
    della parte riprodotta della clip, per disegnarne la forma d'onda. I
    picchi dell'intero file sono calcolati una volta per file e tenuti in
    memoria. None se il file manca."""
    key = _file_key(clip.file)
    if key is None or buckets < 1:
        return None
    peaks = _peaks_cache.get(key)
    if peaks is None:
        try:
            samples, _rate = read_wav(clip.file)
        except (ValueError, OSError):
            return None
        mono = np.abs(samples).max(axis=1) if len(samples) else np.zeros(0, dtype=np.float32)
        pad = (-len(mono)) % _PEAK_BLOCK_FRAMES
        if pad:
            mono = np.concatenate([mono, np.zeros(pad, dtype=np.float32)])
        peaks = mono.reshape(-1, _PEAK_BLOCK_FRAMES).max(axis=1) if len(mono) else mono
        while len(_peaks_cache) >= _PEAKS_CACHE_MAX:
            _peaks_cache.pop(next(iter(_peaks_cache)))
        _peaks_cache[key] = peaks
    info = cached_wav_info(clip.file)
    if info is None or len(peaks) == 0:
        return np.zeros(buckets, dtype=np.float32)
    first = int(max(0.0, clip.trim_start) * info.samplerate) // _PEAK_BLOCK_FRAMES
    last = max(first + 1, int(math.ceil((info.seconds - max(0.0, clip.trim_end)) * info.samplerate
                                        / _PEAK_BLOCK_FRAMES)))
    part = peaks[first:last]
    if len(part) == 0:
        return np.zeros(buckets, dtype=np.float32)
    edges = np.linspace(0, len(part), buckets + 1).astype(int)
    out = np.zeros(buckets, dtype=np.float32)
    for i in range(buckets):
        a, b = edges[i], max(edges[i + 1], edges[i] + 1)
        out[i] = part[a:min(b, len(part))].max() if a < len(part) else 0.0
    return np.clip(out, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Mix
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AudioLayer:
    """Una clip pronta da mixare: dove (in secondi dall'inizio del
    rendering), quale parte del file e con che guadagno/pan."""
    path: str
    start_seconds: float
    trim_start: float
    trim_end: float
    gain: float          # lineare, gia' comprensivo di gain clip, volume traccia e master
    pan: int             # 0-127, 64 = centro


def db_to_gain(db: float) -> float:
    return 10.0 ** (db / 20.0)


def build_audio_layers(project: Project, tracks: List[Track], tempo_map,
                       offset_seconds: float = 0.0) -> List[AudioLayer]:
    """Clip udibili delle tracce audio fra 'tracks' (gia' filtrate per
    Solo/Mute dal chiamante), convertite in AudioLayer. offset_seconds
    sposta tutto indietro (riproduzione che parte a meta' brano senza
    streaming, vedi core.playback): la parte che cadrebbe prima di 0 viene
    tagliata. Le clip con il file mancante vengono saltate."""
    from .tempo_map import seconds_for_beats
    master = max(0, min(200, project.master_volume)) / 100.0
    layers = []
    for track in tracks:
        if not track.is_audio:
            continue
        track_gain = max(0, min(200, track.volume)) / 100.0 * master
        for clip in track.audio_clips:
            if clip_play_seconds(clip) <= 0:
                continue
            start = seconds_for_beats(tempo_map, clip.start_beat) - offset_seconds
            trim_start = max(0.0, clip.trim_start)
            if start < 0:
                trim_start -= start
                start = 0.0
            layers.append(AudioLayer(
                path=os.path.abspath(clip.file), start_seconds=start, trim_start=trim_start,
                trim_end=max(0.0, clip.trim_end), gain=db_to_gain(clip.gain_db) * track_gain,
                pan=track.pan,
            ))
    return layers


def layers_signature(layers: List[AudioLayer]) -> str:
    """Parte della chiave della cache di rendering (core.playback) che
    dipende dall'audio: include dimensione e data dei file, cosi' un file
    sostituito sul disco non riusa un mix vecchio."""
    return repr([(layer, _file_key(layer.path)) for layer in layers])


def _pan_gains(pan: int) -> Tuple[float, float]:
    """Bilanciamento: al centro entrambi i canali restano a 1 (nessun calo
    di volume rispetto a prima di aggiungere il pan), spostandosi si
    attenua solo il lato opposto."""
    p = max(-1.0, min(1.0, (pan - 64) / 63.0))
    return 1.0 - max(0.0, p), 1.0 + min(0.0, p)


def mix_layers(base: np.ndarray, samplerate: int, layers: List[AudioLayer], stems=()) -> np.ndarray:
    """Somma le clip a base (float, forma (frame, 2)) e ritorna il mix
    (piu' lungo di base se una clip finisce dopo). Nessun limite applicato
    qui: lo fa chi scrive il risultato su disco o nel driver.

    'stems' sono tracce gia' renderizzate ed elaborate (catena di effetti,
    vedi core.effect_render): [(campioni (frame, 2) a 'samplerate', inizio
    in secondi)], un inizio negativo ne taglia la parte iniziale."""
    mix = base.astype(np.float32, copy=True)
    for samples, start_seconds in stems:
        offset = int(round(start_seconds * samplerate))
        part = samples[max(0, -offset):]
        offset = max(0, offset)
        end = offset + len(part)
        if len(part) == 0:
            continue
        if end > len(mix):
            mix = np.concatenate([mix, np.zeros((end - len(mix), 2), dtype=np.float32)])
        mix[offset:end] += part[:, :2]
    for layer in layers:
        try:
            samples, rate = read_wav(layer.path)
        except (ValueError, OSError):
            continue
        if rate != samplerate:
            samples = resample(samples, rate, samplerate)
        first = int(round(layer.trim_start * samplerate))
        last = len(samples) - int(round(layer.trim_end * samplerate))
        part = samples[first:last]
        if len(part) == 0:
            continue
        if part.shape[1] == 1:
            stereo = np.repeat(part, 2, axis=1)
        else:
            stereo = part[:, :2]
        left, right = _pan_gains(layer.pan)
        stereo = stereo * np.array([left * layer.gain, right * layer.gain], dtype=np.float32)
        offset = int(round(layer.start_seconds * samplerate))
        end = offset + len(stereo)
        if end > len(mix):
            mix = np.concatenate([mix, np.zeros((end - len(mix), 2), dtype=np.float32)])
        mix[offset:end] += stereo
    return mix


def _to_stereo(samples: np.ndarray) -> np.ndarray:
    if samples.shape[1] == 2:
        return samples
    if samples.shape[1] == 1:
        return np.repeat(samples, 2, axis=1)
    return samples[:, :2]


def mix_layers_into_wav(wav_path: str, layers: List[AudioLayer], out_path: Optional[str] = None,
                        bits: int = 16, stems=(), post=None) -> None:
    """Mixa le clip nel WAV renderizzato wav_path (anche vuoto: un brano
    di sole tracce audio produce un rendering MIDI senza campioni) e scrive
    il risultato in out_path (default: sopra a wav_path) a 'bits' bit. Un
    file mancante o illeggibile vale come silenzio. post(campioni, rate),
    se data, elabora il mix prima di scriverlo (catena del master)."""
    try:
        base, rate = read_wav(wav_path)
        base = _to_stereo(base)
    except (ValueError, OSError):
        base, rate = np.zeros((0, 2), dtype=np.float32), AUDIO_SAMPLE_RATE
    mixed = mix_layers(base, rate, layers, stems=stems)
    if post is not None:
        mixed = post(mixed, rate)
    write_wav(out_path or wav_path, mixed, rate, bits=bits)
