"""
Uscita audio su JACK: SoundText come client con le sue porte (nome
"SoundText", porte out_1/out_2), da collegare con qjackctl, Carla, Ardour
o il grafo JACK di PipeWire. Serve la libreria JACK-Client (pip) sopra la
libjack del sistema; senza, o senza un server JACK in ascolto,
jack_available() e' False e l'audio resta su PortAudio.

JackOutputStream ha la stessa forma di sounddevice.OutputStream per le
parti che SoundText usa (callback(outdata, frames, time_info, status),
start/stop/abort/close, latency, time, active): PcmPlayer, ClickPlayer e
l'ascolto dal vivo dei plugin lo aprono con open_output_stream() al posto
del flusso di PortAudio, senza altre differenze.

Il callback di chi suona NON gira nel thread in tempo reale di JACK: un
thread a parte lo chiama in anticipo e riempie un buffer circolare, e il
callback di JACK copia soltanto. Un ridisegno dell'interfaccia che tiene
il GIL per qualche millisecondo non diventa cosi' un xrun per tutto il
grafo JACK. La frequenza di campionamento la decide il server: se e'
diversa da quella dei campioni, il flusso li ricampiona (sinc a finestra).
"""

import logging
import os
import sys
import threading
import time
from types import SimpleNamespace
from typing import Callable, Optional

import numpy as np

from . import settings

try:
    import jack as _jack
except Exception:  # ImportError, o libjack assente (OSError)
    _jack = None

CLIENT_NAME = "SoundText"

# I valori di settings.get_audio_output()
OUTPUT_SYSTEM = "system"
OUTPUT_JACK = "jack"


def jack_supported() -> bool:
    """La libreria JACK-Client e libjack ci sono (non dice se un server
    e' in ascolto: vedi jack_available)."""
    return _jack is not None


def jack_available() -> bool:
    """Un server JACK (jackd, o PipeWire con pipewire-jack) risponde.
    Non ne avvia uno: se non c'e', False."""
    if _jack is None:
        return False
    try:
        client = _jack.Client(CLIENT_NAME + "-probe", no_start_server=True)
    except Exception:
        return False
    try:
        client.close()
    except Exception:
        pass
    return True


def wants_jack() -> bool:
    """L'utente ha scelto JACK come uscita (Suoni > Uscita audio), o lo
    chiede la variabile SOUNDTEXT_AUDIO_OUTPUT=jack (processo dei plugin)."""
    choice = os.environ.get("SOUNDTEXT_AUDIO_OUTPUT") or settings.get_audio_output()
    return choice == OUTPUT_JACK


def use_jack() -> bool:
    """JACK scelto e disponibile adesso."""
    return wants_jack() and jack_available()


class SincResampler:
    """Ricampiona a blocchi da 'source_rate' a 'target_rate' con un sinc a
    finestra (TAPS campioni, PHASES fasi precalcolate). 'pull(frames)'
    deve dare 'frames' campioni float32 (frame, canali) della sorgente."""

    TAPS = 32
    PHASES = 512

    def __init__(self, source_rate: float, target_rate: float, channels: int, pull: Callable[[int], np.ndarray]):
        self.step = float(source_rate) / float(target_rate)       # frame sorgente per frame di uscita
        self.channels = channels
        self._pull = pull
        half = self.TAPS // 2
        cutoff = min(1.0, 1.0 / self.step)                         # sotto Nyquist della frequenza piu' bassa
        offsets = np.arange(-half + 1, half + 1)[None, :] - (np.arange(self.PHASES) / self.PHASES)[:, None]
        window = np.kaiser(self.TAPS * self.PHASES + 1, 8.6)
        positions = ((offsets + half) * self.PHASES).round().astype(int).clip(0, self.TAPS * self.PHASES)
        table = cutoff * np.sinc(cutoff * offsets) * window[positions]
        self._table = (table / table.sum(axis=1, keepdims=True)).astype(np.float32)
        # campioni sorgente gia' letti e non ancora consumati: _buffer[0] e'
        # il frame sorgente numero _base; _phase la posizione (frazionaria)
        # del prossimo frame di uscita, in frame sorgente.
        self._buffer = np.zeros((half - 1, channels), dtype=np.float32)   # silenzio prima dell'inizio
        self._base = -(half - 1)
        self._phase = 0.0

    @property
    def delay_source_frames(self) -> float:
        """Di quanti frame sorgente il primo campione non ancora uscito
        precede l'ultimo letto con pull (per il calcolo della posizione)."""
        return self._base + len(self._buffer) - self._phase

    def read(self, frames: int) -> np.ndarray:
        """'frames' campioni di uscita, float32 (frame, canali)."""
        half = self.TAPS // 2
        positions = self._phase + self.step * np.arange(frames)
        whole = np.floor(positions).astype(np.int64)
        last_needed = int(whole[-1]) + half                         # ultimo frame sorgente che serve
        missing = last_needed + 1 - (self._base + len(self._buffer))
        if missing > 0:
            block = np.asarray(self._pull(missing), dtype=np.float32).reshape(-1, self.channels)
            if len(block) < missing:                                 # sorgente finita: silenzio
                block = np.concatenate([block, np.zeros((missing - len(block), self.channels), np.float32)])
            self._buffer = np.concatenate([self._buffer, block])
        phases = ((positions - whole) * self.PHASES).astype(np.int64).clip(0, self.PHASES - 1)
        first = whole - (half - 1) - self._base                      # indice nel buffer del primo dei TAPS
        index = first[:, None] + np.arange(self.TAPS)[None, :]
        out = np.einsum("ftc,ft->fc", self._buffer[index], self._table[phases])
        self._phase += self.step * frames
        keep_from = int(np.floor(self._phase)) - (half - 1) - self._base
        if keep_from > 0:
            self._buffer = self._buffer[keep_from:]
            self._base += keep_from
        return out.astype(np.float32, copy=False)


def _is_stop(error: BaseException) -> bool:
    """sounddevice.CallbackStop / CallbackAbort, senza dipendere da
    sounddevice (che puo' mancare quando c'e' solo JACK)."""
    return type(error).__name__ in ("CallbackStop", "CallbackAbort")


class JackOutputStream:
    """Un flusso di uscita verso JACK con la forma di
    sounddevice.OutputStream (vedi il commento del modulo)."""

    BLOCK = 1024                 # frame JACK preparati per volta dal thread che riempie

    def __init__(self, samplerate: int, channels: int = 2, dtype: str = "float32", latency=None,
                 callback: Optional[Callable] = None, finished_callback: Optional[Callable] = None,
                 blocksize: int = 0, client_name: str = CLIENT_NAME, autoconnect: bool = True,
                 jack_module=None, **_ignored):
        jack = jack_module or _jack
        if jack is None:
            raise RuntimeError("JACK-Client non disponibile")
        self._jack = jack
        self.samplerate = int(samplerate)
        self.channels = int(channels)
        self.dtype = np.dtype(dtype)
        self._callback = callback
        self._finished_callback = finished_callback
        self._autoconnect = autoconnect
        self._client = jack.Client(client_name, no_start_server=True)
        self.jack_rate = int(self._client.samplerate)
        self._ports = [self._client.outports.register(f"out_{i + 1}") for i in range(max(2, self.channels))]
        # Quanto audio tenere pronto: "low" e i flussi dal vivo poco (un
        # paio di periodi di JACK), la riproduzione di campioni gia' pronti
        # di piu' (vedi audio_stream.OUTPUT_LATENCY_SECONDS).
        period = int(self._client.blocksize)
        if isinstance(latency, (int, float)):
            ahead = int(float(latency) * self.jack_rate)
        elif latency == "low":
            ahead = 2 * period
        else:
            ahead = int(0.1 * self.jack_rate)
        self._block = max(64, min(self.BLOCK, int(blocksize * self.jack_rate / self.samplerate) or self.BLOCK))
        if latency == "low" or (isinstance(latency, (int, float)) and latency < 0.05):
            self._block = max(64, min(self._block, period))
        self._ahead = max(ahead, 2 * period, self._block)
        self._ring = jack.RingBuffer((self._ahead + 2 * self._block + period) * len(self._ports) * 4)
        self._written = 0            # frame JACK scritti nel buffer circolare
        self._consumed = 0           # frame JACK letti dal callback di JACK
        self._mark = (0, 0)          # (last_frame_time, _consumed) all'ultimo callback di JACK
        self._source_finished = False
        self._aborted = False
        self._active = False
        self._closed = False
        self._thread = None
        self._wake = threading.Event()
        self._resampler = None
        if self.jack_rate != self.samplerate:
            self._resampler = SincResampler(self.samplerate, self.jack_rate, self.channels, self._pull_source)
        self._block_time = None      # time_info del blocco che il callback sta scrivendo
        self._client.set_process_callback(self._process)
        self._client.set_shutdown_callback(self._on_shutdown)

    # ---------------------------------------------------------------- stato

    @property
    def active(self) -> bool:
        return self._active

    @property
    def latency(self) -> float:
        """Secondi fra un campione scritto dal callback e il suo ascolto."""
        return (self._ahead + self._port_latency()) / float(self.jack_rate)

    @property
    def time(self) -> float:
        """L'orologio del server, in secondi: lo stesso di
        time_info.outputBufferDacTime."""
        return self._client.frame_time / float(self.jack_rate)

    @property
    def device(self) -> str:
        return "JACK"

    def _port_latency(self) -> int:
        try:
            return int(self._ports[0].get_latency_range(self._jack.PLAYBACK)[1])
        except Exception:
            return 0

    # ------------------------------------------------------------ controllo

    def start(self):
        self._client.activate()
        self._active = True
        self._mark = (self._client.frame_time, 0)     # finche' JACK non chiama _process
        if self._autoconnect:
            self._connect_to_playback()
        self._thread = threading.Thread(target=self._fill, daemon=True, name="jack-fill")
        self._thread.start()

    def _connect_to_playback(self):
        """out_1/out_2 sulle prime due uscite fisiche (gli altoparlanti)."""
        try:
            targets = self._client.get_ports(is_physical=True, is_input=True, is_audio=True)
        except Exception:
            targets = []
        for port, target in zip(self._ports, targets[:2]):
            try:
                self._client.connect(port, target)
            except Exception:
                logging.getLogger(__name__).info("Porta JACK non collegata: %s", target, exc_info=True)

    def stop(self):
        """Ferma dopo aver suonato cio' che e' gia' nel buffer."""
        self._source_finished = True
        self._wake.set()
        deadline = time.monotonic() + self._ahead / float(self.jack_rate) + 0.5
        while self._active and self._consumed < self._written and time.monotonic() < deadline:
            time.sleep(0.005)
        self.abort()

    def abort(self):
        """Ferma subito, scartando il buffer."""
        self._aborted = True
        self._wake.set()
        was_active, self._active = self._active, False
        if was_active:
            try:
                self._client.deactivate()
            except Exception:
                pass

    def close(self):
        if self._closed:
            return
        self.abort()
        self._closed = True
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1.0)
        try:
            self._client.close()
        except Exception:
            pass

    def _on_shutdown(self, *_args):
        """Il server JACK e' stato chiuso: il flusso finisce."""
        self._aborted = True
        self._active = False
        self._wake.set()

    # ------------------------------------------------------- thread di JACK

    def _process(self, frames: int):
        """Callback in tempo reale: copia dal buffer circolare, niente altro."""
        count = len(self._ports)
        wanted = frames * count * 4
        data = self._ring.read(min(wanted, self._ring.read_space))
        got = len(data) // (count * 4)
        if got:
            block = np.frombuffer(data, dtype=np.float32, count=got * count).reshape(got, count)
            for i, port in enumerate(self._ports):
                out = port.get_array()
                out[:got] = block[:, i]
                out[got:] = 0
        else:
            for port in self._ports:
                port.get_array().fill(0)
        self._mark = (self._client.last_frame_time, self._consumed)
        self._consumed += got
        self._wake.set()

    # --------------------------------------------------- thread che riempie

    def _pull_source(self, frames: int) -> np.ndarray:
        """'frames' campioni dal callback di chi suona, float32
        (frame, canali). Finito il materiale (CallbackStop), silenzio."""
        if self._source_finished or frames <= 0:
            return np.zeros((max(0, frames), self.channels), dtype=np.float32)
        out = np.zeros((frames, self.channels), dtype=self.dtype)
        status = SimpleNamespace(output_underflow=False)
        try:
            self._callback(out, frames, self._block_time, status)
        except Exception as error:
            if not _is_stop(error):
                logging.getLogger(__name__).warning("Errore nel callback audio (JACK)", exc_info=True)
            self._source_finished = True
        if self.dtype.kind == "i":
            return out.astype(np.float32) / float(np.iinfo(self.dtype).max + 1)
        return out.astype(np.float32, copy=False)

    def _fill(self):
        count = len(self._ports)
        while not self._aborted:
            room = self._ahead - (self._written - self._consumed)
            if room < self._block or self._ring.write_space < self._block * count * 4:
                self._wake.wait(0.02)
                self._wake.clear()
                continue
            if self._source_finished:
                if self._consumed >= self._written:
                    break                                   # suonato tutto
                self._wake.wait(0.02)
                self._wake.clear()
                continue
            # Quando si ascoltera' il primo frame di questo blocco, sull'
            # orologio del server: l'ultimo callback di JACK e' partito al
            # frame 'at' avendo gia' letto 'consumed' frame.
            at, consumed = self._mark
            dac_frame = at + (self._written - consumed) + self._port_latency()
            if self._resampler is not None:
                dac_frame += self._resampler.delay_source_frames / self._resampler.step
            self._block_time = SimpleNamespace(
                outputBufferDacTime=dac_frame / float(self.jack_rate), currentTime=self.time)
            block = (self._resampler.read(self._block) if self._resampler is not None
                     else self._pull_source(self._block))
            wide = np.zeros((self._block, count), dtype=np.float32)
            wide[:, :self.channels] = block
            if self.channels == 1:
                wide[:, 1] = block[:, 0]                    # mono su tutte e due le porte
            self._ring.write(wide.tobytes())
            self._written += self._block
        if not self._aborted:
            self.abort()
        if self._finished_callback is not None:
            try:
                self._finished_callback()
            except Exception:
                logging.getLogger(__name__).warning("Errore alla fine del flusso JACK", exc_info=True)


def open_output_stream(sd=None, **kwargs):
    """Un flusso di uscita: JackOutputStream se l'utente ha scelto JACK e
    il server risponde, altrimenti OutputStream di 'sd' (il modulo
    sounddevice di chi chiama; senza, quello importato qui). Gli argomenti
    sono quelli di sounddevice.OutputStream."""
    if use_jack():
        try:
            return JackOutputStream(**kwargs)
        except Exception:
            logging.getLogger(__name__).warning("JACK non apribile: si ripiega su PortAudio", exc_info=True)
    if sd is None:
        import sounddevice as sd
    kwargs.pop("client_name", None)
    return sd.OutputStream(**kwargs)


def fluidsynth_jack_driver() -> Optional[str]:
    """'jack' se la tastiera dal vivo (FluidSynth) deve uscire su JACK."""
    return "jack" if sys.platform.startswith("linux") and use_jack() else None
