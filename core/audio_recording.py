"""
Registrazione di una traccia audio (fase 2) mentre suona il resto del
brano: voce al microfono, chitarra/basso nell'ingresso Hi-Z della scheda
audio, tastiera negli ingressi line.

Come funziona una ripresa:
1. build_backing() prepara la base: il brano renderizzato come in
   riproduzione (core.playback.render_project_mix) dal punto di partenza in
   poi, preceduto da qualche battuta di silenzio per il conteggio; i click
   del conteggio (e, se richiesto, del metronomo per tutta la ripresa) sono
   una ClickSchedule sommata al volo, cosi' si puo' registrare anche oltre
   la fine del brano (o in un brano ancora vuoto) con il click che continua.
2. DuplexRecorder suona la base e registra l'ingresso scelto con UN solo
   stream full-duplex di sounddevice (stesso dispositivo/driver per
   ingresso e uscita), cosi' i due flussi hanno lo stesso clock; se il
   driver non lo consente ripiega su due stream separati.
3. Allineamento: il primo frame della base esce dagli altoparlanti al tempo
   D (outputBufferDacTime), il primo frame registrato e' entrato al tempo A
   (inputBufferAdcTime); chi suona a tempo con cio' che sente produce il
   suono del frame s della base nel frame registrato s + (D - A) * rate.
   Quel ritardo (D - A), il conteggio e la compensazione manuale (ms, per
   dispositivo, per cio' che i driver non dichiarano) diventano il trim
   iniziale della clip: il file resta intero, come tutte le clip
   (vedi core.audio_tracks).
"""

import os
import re
import sys
import threading
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple

import numpy as np

from .audio_tracks import AUDIO_SAMPLE_RATE, resample, unique_audio_path, write_wav
from .model import AudioClip, Project
from .i18n import tr

# Profili d'ingresso: solo suggerimenti (canali predefiniti e cosa impostare
# sulla scheda audio), il segnale registrato e' lo stesso.
INPUT_PROFILES = {
    "voce": ("Voce / microfono", "1",
             "Collega il microfono all'ingresso 1 della scheda audio; se e' un microfono a "
             "condensatore attiva la phantom +48V."),
    "chitarra": ("Chitarra o basso (jack)", "1",
                 "Collega il jack all'ingresso INST/Hi-Z della scheda audio (non LINE): viene "
                 "registrato il suono pulito, senza amplificatore."),
    "tastiera": ("Tastiera (uscita line)", "1+2",
                 "Collega le uscite L/R della tastiera agli ingressi 1 e 2 (impostati su LINE); "
                 "con un solo cavo scegli un ingresso mono."),
}
DEFAULT_PROFILE = "voce"

# Oltre questa durata la ripresa si ferma da sola (memoria: ~1,4 GB in float
# stereo a 48 kHz per 60 minuti).
MAX_RECORD_SECONDS = 30 * 60
CLIP_THRESHOLD = 0.999


def _sounddevice():
    try:
        import sounddevice as sd
        return sd
    except (ImportError, OSError):
        return None


def is_recording_available() -> bool:
    return _sounddevice() is not None


# ---------------------------------------------------------------------------
# Dispositivi e canali d'ingresso
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InputDevice:
    index: int
    name: str
    hostapi: str
    hostapi_index: int
    max_channels: int
    default_samplerate: int
    external: bool = False       # scheda audio collegata al computer (USB...), non quella incorporata

    @property
    def label(self) -> str:
        return f"{self.name} ({self.hostapi})"


# Ingressi "generici" del sistema (alias, mixer software): non sono una
# scelta precisa di chi registra, quindi una scheda esterna ha la precedenza.
_GENERIC_INPUTS = {"default", "sysdefault", "pipewire", "pulse", "jack", "dmix", "dsnoop", "lavrate",
                   "samplerate", "speexrate", "speex", "upmix", "vdownmix", "spdif",
                   "microsoft sound mapper - input", "primary sound capture driver"}
# Ingressi incorporati o virtuali (Windows/macOS, dove non si sa come e' collegata la scheda)
_BUILTIN_OR_VIRTUAL = re.compile(
    r"realtek|high definition audio|microphone array|intel.*(smart sound|sst)|stereo mix|"
    r"built-in|macbook|imac|mac mini|mac studio|mac pro|blackhole|soundflower|loopback|"
    r"zoom ?audio|teams|virtual|vb-audio|voicemeeter|cable output|aggregate|nvidia|amd high|"
    r"steam streaming|webcam|camera|display audio|hdmi|displayport|bluetooth|airpods|hands-free",
    re.IGNORECASE)


def _is_generic(name: str) -> bool:
    return name.strip().lower() in _GENERIC_INPUTS


def _alsa_card_sysfs(name: str) -> str:
    """Linux: il percorso nel kernel della scheda ALSA ('... (hw:3,0)'), o ''."""
    m = re.search(r"\(hw:(\d+),\d+\)", name)
    return os.path.realpath(f"/sys/class/sound/card{m.group(1)}") if m else ""


def is_external_input(name: str) -> bool:
    """Una scheda audio collegata al computer (interfaccia USB, multieffetto,
    mixer...) invece dell'ingresso incorporato o di un dispositivo virtuale."""
    if _is_generic(name):
        return False
    if sys.platform.startswith("linux"):
        path = _alsa_card_sysfs(name)
        return bool(path) and any(bus in path for bus in ("/usb", "/firewire", "/fw"))
    if "usb" in name.lower():
        return True
    return not _BUILTIN_OR_VIRTUAL.search(name)


# Su Windows lo stesso ingresso compare una volta per driver: WASAPI (e ASIO,
# se presente) hanno latenza molto piu' bassa di MME/DirectSound.
_WINDOWS_HOSTAPI_ORDER = ("ASIO", "Windows WASAPI", "Windows WDM-KS", "Windows DirectSound", "MME")


def list_input_devices() -> List[InputDevice]:
    sd = _sounddevice()
    if sd is None:
        return []
    try:
        hostapis = sd.query_hostapis()
        devices = sd.query_devices()
    except Exception:
        return []
    result = []
    for index, d in enumerate(devices):
        if d.get("max_input_channels", 0) > 0:
            api_index = d.get("hostapi", 0)
            result.append(InputDevice(
                index=index, name=d["name"], hostapi=hostapis[api_index]["name"], hostapi_index=api_index,
                max_channels=int(d["max_input_channels"]),
                default_samplerate=int(d.get("default_samplerate") or AUDIO_SAMPLE_RATE),
                external=is_external_input(d["name"])))
    if sys.platform == "win32":
        def rank(dev):
            return (_WINDOWS_HOSTAPI_ORDER.index(dev.hostapi) if dev.hostapi in _WINDOWS_HOSTAPI_ORDER
                    else len(_WINDOWS_HOSTAPI_ORDER))
        result.sort(key=rank)
    return result


def pick_input_device(devices: Sequence[InputDevice], preferred_label: str = "") -> Optional[InputDevice]:
    """Il dispositivo scelto l'ultima volta (per etichetta) se era un ingresso
    preciso; altrimenti una scheda audio esterna collegata; altrimenti
    l'ingresso scelto l'ultima volta, quello predefinito del sistema o il
    primo dell'elenco."""
    if not devices:
        return None
    preferred = next((dev for dev in devices if preferred_label and dev.label == preferred_label), None)
    if preferred is not None and not _is_generic(preferred.name):
        return preferred
    external = next((dev for dev in devices if dev.external), None)
    if external is not None:
        return external
    if preferred is not None:
        return preferred
    sd = _sounddevice()
    if sd is not None:
        try:
            default_in = sd.default.device[0]
        except Exception:
            default_in = -1
        for dev in devices:
            if dev.index == default_in:
                return dev
    return devices[0]


def output_device_for(device: InputDevice) -> Optional[int]:
    """Uscita predefinita dello stesso driver dell'ingresso: condizione per
    aprire uno stream full-duplex (None = uscita predefinita di sistema)."""
    sd = _sounddevice()
    if sd is None:
        return None
    try:
        out = sd.query_hostapis(device.hostapi_index)["default_output_device"]
    except Exception:
        return None
    return out if out is not None and out >= 0 else None


def channel_choices(max_channels: int) -> List[Tuple[str, str]]:
    """(etichetta, specifica) degli ingressi selezionabili: ogni ingresso
    mono e le coppie stereo 1+2, 3+4, ... La specifica ("1", "1+2") e'
    quella salvata nel progetto (Track.input_channels)."""
    choices = [(f"Ingresso {i} (mono)", str(i)) for i in range(1, max_channels + 1)]
    choices += [(f"Ingressi {i}+{i + 1} (stereo)", f"{i}+{i + 1}")
                for i in range(1, max_channels, 2)]
    return choices


def parse_channel_spec(spec: str, max_channels: int) -> Tuple[int, ...]:
    """'1' -> (0,), '1+2' -> (0, 1) (indici da 0), limitati ai canali che
    il dispositivo ha davvero; (0,) se la specifica non vale."""
    try:
        chans = tuple(int(p) - 1 for p in str(spec).split("+"))
    except ValueError:
        chans = (0,)
    if not chans or any(c < 0 or c >= max(1, max_channels) for c in chans):
        return (0,)
    return chans


# ---------------------------------------------------------------------------
# Click del conteggio e del metronomo
# ---------------------------------------------------------------------------

def _click_samples(name: str, rate: int) -> Tuple[np.ndarray, np.ndarray]:
    from . import metronome_sounds
    from .audio_tracks import read_wav
    accent_path, normal_path = metronome_sounds.ensure_click_sound_files(name)
    out = []
    for path in (accent_path, normal_path):
        samples, src_rate = read_wav(path)
        out.append(resample(samples, src_rate, rate)[:, 0].copy())
    return out[0], out[1]


class ClickSchedule:
    """Click (tempo in secondi dall'inizio della base, accento) sommati al
    volo all'uscita: nessun buffer lungo quanto la ripresa."""

    def __init__(self, times: List[Tuple[float, bool]], accent: np.ndarray, normal: np.ndarray,
                 volume: float, rate: int):
        self.rate = rate
        self.volume = volume
        self._accent = accent.astype(np.float32)
        self._normal = normal.astype(np.float32)
        self._events = [(int(round(t * rate)), acc) for t, acc in sorted(times)]
        self._starts = np.array([f for f, _ in self._events], dtype=np.int64)

    def __len__(self):
        return len(self._events)

    def at_rate(self, rate: int) -> "ClickSchedule":
        """La stessa sequenza di click per uno stream a un'altra frequenza."""
        times = [(frame / float(self.rate), acc) for frame, acc in self._events]
        return ClickSchedule(times, resample(self._accent[:, None], self.rate, rate)[:, 0],
                             resample(self._normal[:, None], self.rate, rate)[:, 0], self.volume, rate)

    def add_into(self, out: np.ndarray, start_frame: int) -> None:
        """Somma a out (frame, canali) i click che cadono nei suoi frame,
        dove out[0] e' il frame start_frame della base."""
        if not self._events or self.volume <= 0:
            return
        n = len(out)
        longest = max(len(self._accent), len(self._normal))
        lo = np.searchsorted(self._starts, start_frame - longest, side="left")
        hi = np.searchsorted(self._starts, start_frame + n, side="left")
        for frame, accent in self._events[lo:hi]:
            sample = self._accent if accent else self._normal
            a = max(frame, start_frame)
            b = min(frame + len(sample), start_frame + n)
            if b > a:
                out[a - start_frame:b - start_frame] += (
                    sample[a - frame:b - frame] * self.volume)[:, None]


def build_click_schedule(project: Project, start_beat: float, count_in_bars: int, with_metronome: bool,
                         rate: int = AUDIO_SAMPLE_RATE, sound: Optional[str] = None,
                         volume: Optional[float] = None,
                         max_seconds: float = MAX_RECORD_SECONDS) -> Tuple[ClickSchedule, float]:
    """Click del conteggio (count_in_bars battute al tempo e con la metrica
    in vigore a start_beat) e, con with_metronome, del metronomo da
    start_beat in poi. Ritorna (schedule, durata del conteggio in secondi)."""
    from . import settings
    from .tempo_map import (build_metrica_beat_map, build_tempo_beat_map, click_grid_position,
                            seconds_for_beats, value_at_beat)

    tempo_map = build_tempo_beat_map(project)
    metrica_map = build_metrica_beat_map(project)
    bpm = max(1, value_at_beat(tempo_map, start_beat) or project.tempo_bpm)
    sig = value_at_beat(metrica_map, start_beat) or project.time_sig or "4/4"
    try:
        num, den = (max(1, int(x)) for x in sig.split("/"))
    except ValueError:
        num, den = 4, 4
    click_seconds = (4.0 / den) * 60.0 / bpm
    times = [(k * click_seconds, k % num == 0) for k in range(max(0, count_in_bars) * num)]
    count_in_seconds = max(0, count_in_bars) * num * click_seconds

    if with_metronome:
        origin = seconds_for_beats(tempo_map, start_beat)
        beat = start_beat
        while True:
            beat, accent = click_grid_position(metrica_map, beat)
            t = count_in_seconds + seconds_for_beats(tempo_map, beat) - origin
            if t > max_seconds:
                break
            times.append((t, accent))
            beat += 1e-6

    accent, normal = _click_samples(sound or settings.get_metronome_sound(), rate)
    if volume is None:
        volume = settings.get_metronome_volume() / 100.0
    return ClickSchedule(times, accent, normal, volume, rate), count_in_seconds


@dataclass
class Backing:
    samples: np.ndarray        # float32 (frame, 2): conteggio (silenzio) + brano dal punto di partenza
    rate: int
    clicks: ClickSchedule
    count_in_seconds: float
    midi_skipped: bool = False  # le tracce con note non si sono potute renderizzare


def build_backing(project: Project, start_beat: float, count_in_bars: int = 1, with_metronome: bool = True,
                  mute_track: Optional[str] = None, stop_check=None) -> Backing:
    """Prepara la base per registrare da start_beat (vedi modulo). Se le
    tracce con note non si possono renderizzare (manca il SoundFont) la base
    contiene solo le tracce audio e midi_skipped e' True: si registra
    comunque, sul metronomo. mute_track esclude una traccia dalla base (non
    serve riascoltare cio' che si sta per sostituire)."""
    import copy
    from .playback import render_project_mix
    from .tempo_map import build_tempo_beat_map, seconds_for_beats

    source = project
    if mute_track:
        source = copy.deepcopy(project)
        for t in source.tracks:
            if t.name == mute_track:
                t.mute, t.solo = True, False
    midi_skipped = False
    try:
        song, rate = render_project_mix(source, stop_check=stop_check, allow_empty=True)
    except RuntimeError:
        if stop_check and stop_check():
            raise
        song, rate = render_project_mix(source, stop_check=stop_check, include_midi=False, allow_empty=True)
        midi_skipped = any(not t.is_audio and t.text.strip() for t in source.audible_tracks())
    if rate != AUDIO_SAMPLE_RATE:
        song, rate = resample(song, rate, AUDIO_SAMPLE_RATE), AUDIO_SAMPLE_RATE

    start_seconds = seconds_for_beats(build_tempo_beat_map(project), start_beat)
    part = song[int(round(start_seconds * rate)):]
    clicks, count_in_seconds = build_click_schedule(project, start_beat, count_in_bars, with_metronome, rate)
    lead = np.zeros((int(round(count_in_seconds * rate)), 2), dtype=np.float32)
    return Backing(np.concatenate([lead, part.astype(np.float32)]), rate, clicks, count_in_seconds,
                   midi_skipped)


# ---------------------------------------------------------------------------
# Registrazione
# ---------------------------------------------------------------------------

@dataclass
class Take:
    samples: np.ndarray        # float32 (frame, canali) registrati
    rate: int
    alignment_seconds: float   # ritardo dell'ingresso rispetto all'uscita (vedi modulo)
    peak: float                # picco assoluto (1.0 = fondo scala)

    @property
    def seconds(self) -> float:
        return len(self.samples) / float(self.rate) if self.rate else 0.0

    @property
    def clipped(self) -> bool:
        return self.peak >= CLIP_THRESHOLD


class DuplexRecorder:
    """Suona backing (+ click) e registra i canali 'channels' (indici da 0)
    dell'ingresso 'input_device'. start()/stop() sono leggere e si chiamano
    dal thread della GUI; il lavoro vero gira nel callback di PortAudio.

    stream_factory(callback, rate, in_channels, input_device, output_device)
    sostituisce l'apertura dello stream sounddevice (test senza scheda
    audio): deve ritornare un oggetto con start(), stop(), close() che
    chiami callback(indata, outdata, frames, time_info, status)."""

    def __init__(self, backing: Backing, input_device: Optional[int], channels: Sequence[int],
                 output_device: Optional[int] = None, stream_factory: Optional[Callable] = None,
                 fallback_rate: Optional[int] = None):
        self.backing = backing
        self.fallback_rate = fallback_rate
        self.input_device = input_device
        self.channels = tuple(channels) or (0,)
        self.output_device = output_device
        self._factory = stream_factory
        self._streams = []
        self._chunks: List[np.ndarray] = []
        self._pos = 0
        self._recorded = 0
        self._lock = threading.Lock()
        self._first_dac: Optional[float] = None
        self._first_adc: Optional[float] = None
        self._latency_estimate = 0.0
        self._peak = 0.0
        self._peak_since_read = 0.0
        self.rate = backing.rate
        self.error: Optional[str] = None
        self._running = False

    # ----------------------------------------------------------- stato

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def elapsed_seconds(self) -> float:
        """Secondi di base gia' mandati all'uscita (conteggio compreso)."""
        return self._pos / float(self.rate)

    def read_peak(self) -> float:
        """Picco dell'ingresso dall'ultima lettura (per il misuratore)."""
        with self._lock:
            peak, self._peak_since_read = self._peak_since_read, 0.0
        return peak

    # ----------------------------------------------------------- callback

    def _output_block(self, outdata, frames: int, time_info):
        if self._first_dac is None:
            dac = getattr(time_info, "outputBufferDacTime", 0.0) or 0.0
            if dac > 0:
                self._first_dac = dac
        samples = self.backing.samples
        block = np.zeros((frames, 2), dtype=np.float32)
        end = min(len(samples), self._pos + frames)
        if end > self._pos:
            block[:end - self._pos] = samples[self._pos:end]
        self.backing.clicks.add_into(block, self._pos)
        np.clip(block, -1.0, 1.0, out=block)
        if outdata.shape[1] == 1:
            outdata[:, 0] = block.mean(axis=1)
        else:
            outdata[:, :2] = block
            outdata[:, 2:] = 0
        self._pos += frames

    def _input_block(self, indata, time_info):
        if self._first_adc is None:
            adc = getattr(time_info, "inputBufferAdcTime", 0.0) or 0.0
            if adc > 0:
                self._first_adc = adc
        if self._recorded >= MAX_RECORD_SECONDS * self.rate:
            return
        chunk = np.array(indata[:, list(self.channels)], dtype=np.float32, copy=True)
        peak = float(np.max(np.abs(chunk))) if len(chunk) else 0.0
        with self._lock:
            self._chunks.append(chunk)
            self._peak = max(self._peak, peak)
            self._peak_since_read = max(self._peak_since_read, peak)
        self._recorded += len(chunk)

    def _use_rate(self, rate: int):
        b = self.backing
        self.backing = Backing(resample(b.samples, b.rate, rate), rate, b.clicks.at_rate(rate),
                               b.count_in_seconds, b.midi_skipped)
        self.rate = rate

    def _duplex_callback(self, indata, outdata, frames, time_info, status):
        self._output_block(outdata, frames, time_info)
        self._input_block(indata, time_info)

    # ----------------------------------------------------------- avvio/arresto

    def _open_with_sounddevice(self):
        sd = _sounddevice()
        if sd is None:
            raise RuntimeError(tr("Registrazione non disponibile: serve la libreria di sistema "
                               "PortAudio (libportaudio2) e il pacchetto sounddevice."))
        in_channels = max(self.channels) + 1
        # Uno stream full-duplex solo se ingresso e uscita sono la stessa scheda
        # (stesso clock): fra due schede diverse (es. multieffetto USB in
        # ingresso, casse del computer in uscita) ALSA lo apre ma si inceppa.
        if self.input_device == self.output_device:
            try:
                stream = sd.Stream(samplerate=self.rate, device=(self.input_device, self.output_device),
                                   channels=(in_channels, 2), dtype="float32", latency="low",
                                   callback=self._duplex_callback)
                self._latency_estimate = float(sum(stream.latency))
                return [stream]
            except Exception:
                pass   # driver senza full-duplex su questa coppia: due stream separati

        def out_cb(outdata, frames, time_info, status):
            self._output_block(outdata, frames, time_info)

        def in_cb(indata, frames, time_info, status):
            self._input_block(indata, time_info)

        out_stream = sd.OutputStream(samplerate=self.rate, device=self.output_device, channels=2,
                                     dtype="float32", latency="low", callback=out_cb)
        in_stream = sd.InputStream(samplerate=self.rate, device=self.input_device, channels=in_channels,
                                   dtype="float32", latency="low", callback=in_cb)
        self._latency_estimate = float(out_stream.latency + in_stream.latency)
        return [in_stream, out_stream]

    def start(self):
        if self._running:
            return
        if self._factory is not None:
            self._streams = [self._factory(self._duplex_callback, self.rate, max(self.channels) + 1,
                                           self.input_device, self.output_device)]
        else:
            sd = _sounddevice()
            if (sd is not None and self.fallback_rate and self.fallback_rate != self.rate
                    and not _input_rate_supported(sd, self.input_device, max(self.channels) + 1, self.rate)):
                self._use_rate(self.fallback_rate)
            try:
                self._streams = self._open_with_sounddevice()
            except Exception:
                # Scheda che non lavora a 48 kHz: si registra alla sua
                # frequenza (la ripresa viene poi convertita, vedi save_take).
                if not self.fallback_rate or self.fallback_rate == self.rate:
                    raise
                self._use_rate(self.fallback_rate)
                self._streams = self._open_with_sounddevice()
        self._running = True
        for s in self._streams:
            s.start()

    def stop(self) -> Take:
        for s in self._streams:
            try:
                s.stop()
                s.close()
            except Exception:
                pass
        self._streams = []
        self._running = False
        with self._lock:
            chunks, self._chunks = self._chunks, []
        samples = (np.concatenate(chunks, axis=0) if chunks
                   else np.zeros((0, len(self.channels)), dtype=np.float32))
        if self._first_dac is not None and self._first_adc is not None:
            alignment = self._first_dac - self._first_adc
        else:
            alignment = self._latency_estimate
        return Take(samples, self.rate, max(0.0, alignment), self._peak)


def _input_rate_supported(sd, device: Optional[int], channels: int, rate: int) -> bool:
    """Chiede alla scheda se accetta la frequenza, senza aprirla: un tentativo
    a vuoto fa stampare a PortAudio (ALSA) tre righe di errore nel terminale."""
    check = getattr(sd, "check_input_settings", None)
    if check is None:
        return True
    try:
        check(device=device, samplerate=rate, channels=channels, dtype="float32")
        return True
    except Exception:
        return False


class InputMonitor:
    """Legge l'ingresso senza registrare, per il misuratore di livello del
    dialogo di registrazione (prova del gain prima di premere Registra).
    Una scheda che non lavora a 48 kHz si legge alla sua frequenza
    (fallback_rate), come in DuplexRecorder."""

    def __init__(self, input_device: Optional[int], channels: Sequence[int],
                 stream_factory: Optional[Callable] = None, fallback_rate: Optional[int] = None):
        self.input_device = input_device
        self.channels = tuple(channels) or (0,)
        self._factory = stream_factory
        self.fallback_rate = fallback_rate
        self._stream = None
        self._peak = 0.0
        self._lock = threading.Lock()

    def _callback(self, indata, frames, time_info, status):
        peak = float(np.max(np.abs(indata[:, list(self.channels)]))) if frames else 0.0
        with self._lock:
            self._peak = max(self._peak, peak)

    def start(self):
        in_channels = max(self.channels) + 1
        if self._factory is not None:
            self._stream = self._factory(self._callback, in_channels, self.input_device)
        else:
            sd = _sounddevice()
            if sd is None:
                raise RuntimeError(tr("PortAudio/sounddevice non disponibili."))
            rates = [AUDIO_SAMPLE_RATE]
            if self.fallback_rate and self.fallback_rate != AUDIO_SAMPLE_RATE:
                if _input_rate_supported(sd, self.input_device, in_channels, AUDIO_SAMPLE_RATE):
                    rates.append(self.fallback_rate)
                else:
                    rates = [self.fallback_rate]
            for i, rate in enumerate(rates):
                try:
                    self._stream = sd.InputStream(samplerate=rate, device=self.input_device, channels=in_channels,
                                                  dtype="float32", callback=self._callback)
                    break
                except Exception:
                    if i == len(rates) - 1:
                        raise
        self._stream.start()

    def read_peak(self) -> float:
        with self._lock:
            peak, self._peak = self._peak, 0.0
        return peak

    def stop(self):
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None


# ---------------------------------------------------------------------------
# Salvataggio della ripresa
# ---------------------------------------------------------------------------

def save_take(take: Take, dest_dir: str, base_name: str) -> str:
    """Scrive la ripresa (a AUDIO_SAMPLE_RATE, 24 bit) in dest_dir e ne
    ritorna il percorso."""
    path = unique_audio_path(dest_dir, base_name)
    samples = take.samples
    if take.rate != AUDIO_SAMPLE_RATE:
        samples = resample(samples, take.rate, AUDIO_SAMPLE_RATE)
    write_wav(path, samples, AUDIO_SAMPLE_RATE, bits=24)
    return path


def recorded_clip(name: str, path: str, start_beat: float, count_in_seconds: float,
                  alignment_seconds: float, manual_latency_ms: float) -> AudioClip:
    """Clip della ripresa, posizionata a start_beat: il conteggio e il
    ritardo dell'ingresso (misurato + compensazione manuale) diventano il
    trim iniziale, cosi' cio' che si e' suonato a tempo cade sul beat."""
    trim = count_in_seconds + alignment_seconds + manual_latency_ms / 1000.0
    return AudioClip(name=name, file=path, start_beat=start_beat, trim_start=max(0.0, round(trim, 4)))


def take_preview(take: Take, backing: Backing, manual_latency_ms: float,
                 with_backing: bool = True) -> np.ndarray:
    """La ripresa come suonera' nella traccia (stesso trim di recorded_clip),
    float32 (frame, 2) alla frequenza della base, dall'inizio del brano; con
    with_backing mescolata alla base (senza conteggio ne' metronomo)."""
    rate = backing.rate
    x = np.asarray(take.samples, dtype=np.float32)
    x = np.repeat(x[:, :1], 2, axis=1) if x.shape[1] == 1 else x[:, :2]
    x = resample(x, take.rate, rate)
    trim = take.alignment_seconds + manual_latency_ms / 1000.0 + backing.count_in_seconds
    x = x[max(0, int(round(trim * rate))):]
    if with_backing:
        start = int(round(backing.count_in_seconds * rate))
        base = backing.samples[start:start + len(x)]
        x = x.copy()
        x[:len(base)] += base
    return np.clip(x, -1.0, 1.0)


class TakePlayer:
    """Suona un audio (frame, 2) sull'uscita, fermabile in ogni momento."""

    def __init__(self, samples: np.ndarray, rate: int, output_device: Optional[int] = None,
                 stream_factory: Optional[Callable] = None):
        self.samples = samples
        self.rate = rate
        self.output_device = output_device
        self._factory = stream_factory
        self._pos = 0
        self._stream = None

    @property
    def playing(self) -> bool:
        return self._stream is not None and self._pos < len(self.samples)

    @property
    def seconds(self) -> float:
        return self._pos / float(self.rate)

    def _callback(self, outdata, frames, time_info, status):
        chunk = self.samples[self._pos:self._pos + frames]
        outdata[:len(chunk)] = chunk
        outdata[len(chunk):] = 0
        self._pos += frames

    def start(self):
        if self._factory is not None:
            self._stream = self._factory(self._callback, self.rate, self.output_device)
        else:
            sd = _sounddevice()
            if sd is None:
                raise RuntimeError(tr("PortAudio/sounddevice non disponibili."))
            self._stream = sd.OutputStream(samplerate=self.rate, device=self.output_device, channels=2,
                                           dtype="float32", callback=self._callback)
        self._stream.start()

    def stop(self):
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None


# ---------------------------------------------------------------------------
# Calibrazione automatica della latenza
# ---------------------------------------------------------------------------

CALIBRATION_CLICKS = 8
CALIBRATION_INTERVAL = 0.5
CALIBRATION_LEAD = 0.5
CALIBRATION_MAX_SPREAD = 0.005   # misure dei click che differiscono piu' di 5 ms: non attendibili


def build_calibration_backing(rate: int = AUDIO_SAMPLE_RATE) -> Tuple[Backing, List[float]]:
    """Base per la calibrazione: CALIBRATION_CLICKS click secchi (2 kHz,
    5 ms) a intervalli regolari. Ritorna (base, istanti dei click in s)."""
    times = [CALIBRATION_LEAD + k * CALIBRATION_INTERVAL for k in range(CALIBRATION_CLICKS)]
    samples = np.zeros((int((times[-1] + 0.6) * rate), 2), dtype=np.float32)
    n = int(0.005 * rate)
    t = np.arange(n) / rate
    click = (0.8 * np.sin(2 * np.pi * 2000 * t) * np.exp(-t * 600)).astype(np.float32)
    for when in times:
        start = int(round(when * rate))
        samples[start:start + n] += click[:, None]
    silent = ClickSchedule([], np.zeros(1, np.float32), np.zeros(1, np.float32), 0.0, rate)
    return Backing(samples, rate, silent, 0.0), times


def measure_latency_ms(take: Take, click_times: Sequence[float]) -> float:
    """Ritardo residuo (ms) dei click registrati rispetto a quando sono
    usciti, oltre a quello gia' compensato dai tempi del driver
    (take.alignment_seconds): e' il valore da mettere nella compensazione
    manuale. Solleva RuntimeError se i click non si sentono abbastanza o le
    misure non sono coerenti (cavo scollegato, volume troppo basso, rumore)."""
    rate = take.rate
    mono = np.abs(take.samples).max(axis=1) if len(take.samples) else np.zeros(0, np.float32)
    aligned = mono[int(round(take.alignment_seconds * rate)):]
    noise = float(np.median(aligned)) if len(aligned) else 0.0
    residuals = []
    for t in click_times:
        a = max(0, int((t - 0.1) * rate))
        window = aligned[a:int((t + 0.3) * rate)]
        if len(window) == 0:
            continue
        peak = float(window.max())
        if peak < max(10 * noise, 0.01):
            continue
        onset = int(np.argmax(window >= 0.3 * peak))
        residuals.append((a + onset) / rate - t)
    if len(residuals) < len(click_times) // 2 + 1:
        raise RuntimeError(
            tr("Click non rilevati nella registrazione: collega un'uscita della scheda audio a un "
            "ingresso con un cavo (o avvicina il microfono alle casse) e alza un po' il volume."))
    if max(residuals) - min(residuals) > CALIBRATION_MAX_SPREAD:
        raise RuntimeError(
            tr("Misure non coerenti (troppo rumore o eco): riprova in un ambiente piu' silenzioso "
            "o con un cavo fra uscita e ingresso."))
    return round(float(np.median(residuals)) * 1000.0, 1)


def level_to_db(peak: float) -> float:
    return 20.0 * float(np.log10(max(peak, 1e-6)))
