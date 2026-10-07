"""
Riproduzione di audio gia' renderizzato (PCM in memoria) con sounddevice,
invece di passare il WAV a un player esterno (pw-play/paplay/afplay...).

Tenere i campioni in memoria e scriverli noi nel driver audio permette cio'
che un player esterno non consente: partire da un punto qualsiasi senza
rifare il rendering (pausa/ripresa e salto istantanei, vedi la cache in
core.playback), ripetere in loop una sezione A-B senza interruzioni e
conoscere la posizione ESATTA di cio' che si sta ascoltando (dal clock del
driver, non da un cronometro avviato "circa" quando e' partito il processo
esterno), cosi' barra di avanzamento, evidenziazione e metronomo restano
agganciati all'audio reale.

Non e' sintesi in tempo reale: i campioni sono gia' pronti, il callback si
limita a copiarli (niente crepitii da underrun dovuti a una sintesi lenta,
lo stesso motivo per cui il rendering resta offline, vedi core.playback).
"""

import logging
import threading
from typing import Optional, Tuple

import numpy as np

try:
    import sounddevice as _sd
except Exception:  # ImportError, o PortAudio assente (OSError)
    _sd = None


def is_available() -> bool:
    """True se sounddevice/PortAudio sono utilizzabili e c'e' un dispositivo
    di uscita: altrimenti core.playback ripiega sul player esterno."""
    if _sd is None:
        return False
    try:
        _sd.query_devices(kind="output")
    except Exception:
        logging.getLogger(__name__).info("Nessun dispositivo audio di uscita per sounddevice", exc_info=True)
        return False
    return True


class PcmPlayer:
    """Riproduce 'samples' (array int16 di forma (frame, canali)) a
    'samplerate'. Una istanza = una riproduzione: start() una sola volta,
    poi stop() o fine naturale (wait() ritorna)."""

    def __init__(self, samples: np.ndarray, samplerate: int):
        if samples.ndim == 1:
            samples = samples.reshape(-1, 1)
        self._samples = samples
        self._samplerate = samplerate
        self._pos = 0                      # prossimo frame da scrivere nel driver
        self._loop: Optional[Tuple[int, int]] = None
        # (tempo del driver in cui suonera' il primo frame dell'ultimo
        # blocco scritto, frame corrispondente): serve a position_frames()
        # per sapere cosa si sta ASCOLTANDO adesso, non cosa e' stato scritto
        # (tra le due c'e' la latenza del driver).
        self._last_block: Optional[Tuple[float, int]] = None
        self._lock = threading.Lock()
        self._done = threading.Event()
        self._stream = None
        # Nuovo contenuto per la sezione in loop, applicato al prossimo giro
        # (vedi queue_loop_update): cosi' il cambio non arriva a meta' giro.
        self._pending_loop = None

    @property
    def samplerate(self) -> int:
        return self._samplerate

    @property
    def total_frames(self) -> int:
        return len(self._samples)

    def set_loop(self, loop: Optional[Tuple[int, int]]):
        """(frame_inizio, frame_fine) della sezione da ripetere, o None per
        suonare fino in fondo. Ignorato se la sezione e' vuota."""
        with self._lock:
            if loop is not None:
                a, b = max(0, int(loop[0])), min(self.total_frames, int(loop[1]))
                loop = (a, b) if b > a else None
            self._loop = loop

    def queue_loop_update(self, samples: np.ndarray):
        """Sostituisce il contenuto della sezione in loop dal prossimo giro
        (campioni int16 della stessa forma della sezione; altrimenti senza
        effetto). Serve al loop di calibrazione del pannello Effetti."""
        with self._lock:
            loop = self._loop or (0, self.total_frames)
            if samples.shape == self._samples[loop[0]:loop[1]].shape:
                self._pending_loop = np.ascontiguousarray(samples, dtype=self._samples.dtype)

    def start(self, start_frame: int = 0):
        self._pos = max(0, min(self.total_frames, int(start_frame)))
        self._stream = _sd.OutputStream(
            samplerate=self._samplerate, channels=self._samples.shape[1], dtype="int16",
            # 'high': buffer ampio, nessuna fretta di riempirlo (i campioni
            # sono gia' pronti): massima robustezza contro i crepitii.
            latency="high", callback=self._callback, finished_callback=self._done.set,
        )
        self._stream.start()

    def _callback(self, outdata, frames, time_info, _status):
        with self._lock:
            dac_time = time_info.outputBufferDacTime or (time_info.currentTime + self._stream.latency)
            self._last_block = (dac_time, self._pos)
            written = 0
            while written < frames:
                end = self.total_frames
                if self._loop is not None and self._pos < self._loop[1]:
                    end = self._loop[1]
                chunk = min(frames - written, end - self._pos)
                if chunk > 0:
                    outdata[written:written + chunk] = self._samples[self._pos:self._pos + chunk]
                    written += chunk
                    self._pos += chunk
                if self._pos >= end:
                    if self._loop is not None and end == self._loop[1]:
                        self._pos = self._loop[0]
                        if self._pending_loop is not None:
                            self._samples[self._loop[0]:self._loop[1]] = self._pending_loop
                            self._pending_loop = None
                        continue
                    outdata[written:] = 0
                    raise _sd.CallbackStop

    def position_frames(self) -> int:
        """Frame che si sta ascoltando in questo istante (compensata la
        latenza del driver, e riportata dentro la sezione in loop se il
        blocco corrente l'ha gia' riavvolta)."""
        with self._lock:
            if self._last_block is None or self._stream is None:
                return self._pos
            dac_time, frame = self._last_block
            loop = self._loop
        try:
            elapsed = self._stream.time - dac_time
        except Exception:  # stream gia' chiuso
            return frame
        pos = frame + int(round(elapsed * self._samplerate))
        if loop is not None and frame < loop[1] and pos >= loop[1]:
            pos = loop[0] + (pos - loop[1]) % (loop[1] - loop[0])
        return max(0, min(self.total_frames, pos))

    def wait(self):
        self._done.wait()

    def stop(self):
        stream = self._stream
        if stream is not None:
            try:
                stream.abort()
                stream.close()
            except Exception:
                pass
        self._done.set()

    def is_active(self) -> bool:
        return self._stream is not None and not self._done.is_set()


def load_wav_samples(path: str) -> Tuple[np.ndarray, int]:
    """(campioni int16 (frame, canali), samplerate) di un WAV 16 bit."""
    import contextlib
    import wave

    with contextlib.closing(wave.open(path, "rb")) as w:
        channels, rate = w.getnchannels(), w.getframerate()
        raw = w.readframes(w.getnframes())
    return np.frombuffer(raw, dtype=np.int16).reshape(-1, channels).copy(), rate
