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
import time
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
        # Per il log di un flusso che si chiude da solo prima della fine
        # (vedi _on_finished): fermato da stop(), arrivato in fondo, o il
        # primo avviso del driver (underrun...) visto nel callback.
        self._stopping = False
        self._reached_end = False
        self._driver_status = None
        # Dopo un underflow (il driver e' rimasto un attimo senza dati) lo
        # stream ALSA/PipeWire di PortAudio puo' restare muto pur andando
        # avanti: il thread di guardia (vedi _watch) lo riapre dal punto che
        # si sta ascoltando. _generation scarta la fine dello stream vecchio.
        self._wake = threading.Event()
        self._underflow = False
        self._generation = 0
        self._recoveries = 0

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
        self._open_stream()
        threading.Thread(target=self._watch, daemon=True).start()

    def _open_stream(self):
        generation = self._generation
        self._stream = _sd.OutputStream(
            samplerate=self._samplerate, channels=self._samples.shape[1], dtype="int16",
            # 'high': buffer ampio, nessuna fretta di riempirlo (i campioni
            # sono gia' pronti): massima robustezza contro i crepitii.
            latency="high", callback=self._callback,
            finished_callback=lambda: self._on_finished(generation),
        )
        self._stream.start()

    MAX_RECOVERIES = 20
    MIN_RECOVERY_INTERVAL = 0.5

    def _watch(self):
        """Riapre lo stream dopo un underflow (vedi __init__), al massimo
        una volta ogni MIN_RECOVERY_INTERVAL secondi."""
        last = 0.0
        while True:
            self._wake.wait()
            self._wake.clear()
            if self._done.is_set() or self._stopping:
                return
            if not self._underflow or self._recoveries >= self.MAX_RECOVERIES:
                continue
            time.sleep(max(0.0, last + self.MIN_RECOVERY_INTERVAL - time.monotonic()))
            last = time.monotonic()
            self._underflow = False
            self._recover()

    def _recover(self):
        frame = self.position_frames()
        old = self._stream
        self._generation += 1
        try:
            old.abort()
            old.close()
        except Exception:
            pass
        if self._stopping or self._done.is_set():
            return
        with self._lock:
            self._pos = frame
            self._last_block = None
        self._recoveries += 1
        logging.getLogger(__name__).info("Stream audio riaperto dopo un underflow a %.1f s",
                                         frame / float(self._samplerate))
        try:
            self._open_stream()
        except Exception:
            logging.getLogger(__name__).warning("Stream audio non riapribile", exc_info=True)
            self._done.set()
            return
        if self._stopping:
            self.stop()

    def _on_finished(self, generation: int = 0):
        """Fine del flusso: se non l'ha chiesta stop() e non si era arrivati
        in fondo, il driver l'ha chiuso a meta' (la barra di avanzamento
        prosegue allora col cronometro, ma non si sente piu' niente)."""
        if generation != self._generation:
            return                     # lo stream sostituito da _recover
        if not self._stopping and not self._reached_end:
            logging.getLogger(__name__).warning(
                "Flusso audio chiuso a meta' riproduzione: frame %d di %d (%.1f s), "
                "ultimo avviso del driver: %s", self._pos, self.total_frames,
                self._pos / float(self._samplerate), self._driver_status or "nessuno")
        self._done.set()
        self._wake.set()

    def _callback(self, outdata, frames, time_info, status):
        if status and self._driver_status is None:
            self._driver_status = f"{status} a {self._pos / float(self._samplerate):.1f} s"
            logging.getLogger(__name__).info("Avviso del driver audio: %s", self._driver_status)
        if getattr(status, "output_underflow", False):
            self._underflow = True
            self._wake.set()
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
                    self._reached_end = True
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
        self._stopping = True
        stream = self._stream
        if stream is not None:
            try:
                stream.abort()
                stream.close()
            except Exception:
                pass
        self._done.set()
        self._wake.set()

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


class ClickPlayer:
    """Suoni brevi (i click del metronomo) con sounddevice: un flusso di
    uscita in cui ogni suono viene mixato appena arriva. Si apre al primo
    suono e si chiude dopo IDLE_SECONDS di silenzio; il suono successivo ne
    apre uno nuovo, sul dispositivo audio di quel momento. Prima i click
    passavano da QSoundEffect, che su Windows poteva restare muto fino al
    riavvio (l'uscita audio di Qt bloccata, per esempio dopo un cambio o una
    sospensione del dispositivo), pur dicendo di suonare."""

    IDLE_SECONDS = 4.0

    def __init__(self, samplerate: int = 48000):
        self.samplerate = samplerate
        self._lock = threading.Lock()
        self._voices = []          # [array float32 mono, posizione]
        self._stream = None
        self._last_sound = 0.0

    def play(self, samples: np.ndarray, volume: float = 1.0) -> bool:
        """Suona 'samples' (float, mono, a self.samplerate). False se il
        flusso non si apre (chi chiama ripiega su altro). Aprire e chiudere
        il flusso avviene fuori dal lock: stop() aspetta la fine del
        callback, che a sua volta prende il lock."""
        import time
        if _sd is None:
            return False
        now = time.monotonic()
        with self._lock:
            old = None
            if self._stream is not None and (not self._stream.active
                                             or now - self._last_sound > self.IDLE_SECONDS):
                old, self._stream, self._voices = self._stream, None, []
            need_stream = self._stream is None
        if old is not None:
            _stop_quietly(old)
        if need_stream:
            try:
                stream = _sd.OutputStream(samplerate=self.samplerate, channels=2, dtype="float32",
                                          latency="low", callback=self._callback)
                stream.start()
            except Exception:
                logging.getLogger(__name__).warning("Flusso audio dei click non apribile", exc_info=True)
                return False
            with self._lock:
                if self._stream is None:
                    self._stream = stream
                    stream = None
            if stream is not None:                 # un altro thread l'ha gia' aperto
                _stop_quietly(stream)
        with self._lock:
            self._voices.append([np.asarray(samples, dtype=np.float32) * float(volume), 0])
            self._last_sound = now
        return True

    def _callback(self, outdata, frames, _time_info, _status):
        outdata.fill(0)
        with self._lock:
            alive = []
            for voice in self._voices:
                samples, pos = voice
                part = samples[pos:pos + frames]
                outdata[:len(part), 0] += part
                outdata[:len(part), 1] += part
                voice[1] = pos + len(part)
                if voice[1] < len(samples):
                    alive.append(voice)
            self._voices = alive
        np.clip(outdata, -1.0, 1.0, out=outdata)

    def close(self):
        with self._lock:
            stream, self._stream, self._voices = self._stream, None, []
        if stream is not None:
            _stop_quietly(stream)


def _stop_quietly(stream):
    try:
        stream.stop()
        stream.close()
    except Exception:
        pass
