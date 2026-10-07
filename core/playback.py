"""
Playback dell'ensemble (o di una singola traccia) tenendo conto del
mixaggio corrente (Solo/Mute/Volume/Pan). Il rendering vero e proprio
avviene esportando un MIDI temporaneo e delegando la sintesi audio a un
synth di sistema disponibile.

Con fluidsynth + SoundFont, il rendering avviene OFFLINE in un file WAV
temporaneo (invece che in tempo reale sul driver audio): evita crepitii/
dropout dovuti a underrun del driver audio (frequenti con PulseAudio/
PipeWire in tempo reale) e da un risultato piu' pulito e riproducibile.
Il WAV viene poi riprodotto con il miglior player audio disponibile.

Se e' disponibile la libreria FluidSynth (collegata direttamente, vedi
core.fluid), il rendering offline usa un'unica istanza di Synth PERSISTENTE per tutta la vita
dell'app (vedi _PersistentSynth), con il SoundFont caricato in memoria una
sola volta: il costo di caricamento del SoundFont (anche centinaia di ms
per un GM da decine di MB) non viene piu' pagato ad ogni play(), solo la
prima volta. Il rendering resta comunque offline su file (file renderer
interno di fluidsynth, non l'output audio in tempo reale): stessa
strategia anti-crepitio di prima, senza pero' lo spawn di un nuovo
processo e il ricaricamento del SoundFont ad ogni riproduzione.

Se la libreria non e' disponibile (o il rendering con il synth
persistente fallisce), si ripiega sul binario CLI fluidsynth (uno spawn +
un caricamento SoundFont per riproduzione), poi su timidity o wildmidi (in
tempo reale) o, in mancanza di tutto, sul player MIDI predefinito del
sistema (xdg-open su Linux, open su macOS, os.startfile su Windows).
"""

import contextlib
import ctypes
import copy
import hashlib
import logging
from ctypes import wintypes
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import wave
from typing import Dict, List, Optional

from . import audio_stream
from .effects import DEFAULT_REVERB_ROOM, apply_reverb, reverb_cli_options
from .model import Project, Track
from .midi_export import export_project_to_midi
from .i18n import tr

from . import fluid as _fluid

# La libreria FluidSynth (vedi core.fluid): se non c'e', il rendering usa il
# programma 'fluidsynth' da riga di comando e non c'e' il suono dal vivo.
_FLUID_AVAILABLE = _fluid.available()


try:
    import winsound as _winsound  # disponibile solo su Windows
except ImportError:
    _winsound = None

# Sentinella usata al posto di un comando esterno quando, su Windows, non
# e' installato nessun player CLI (pw-play/paplay/ffplay/mpv non esistono
# di serie su Windows): si ripiega sul modulo 'winsound' della stdlib, che
# non richiede alcuna dipendenza aggiuntiva.
log = logging.getLogger(__name__)

_WINSOUND_MARKER = ["__winsound__"]

# Campioni per chiamata a Synth.get_samples() nel rendering offline
# (_PersistentSynth._render_group): 100ms a 48kHz, vedi il commento li' per
# il perche'.
_RENDER_CHUNK_FRAMES = 4800
# Escursione della leva del pitch bend del synth dal vivo (default di
# FluidSynth, mai cambiato via RPN): vedi LiveSynth.pitch_bend.
LIVE_BEND_RANGE_SEMITONES = 2.0


class _SHELLEXECUTEINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("fMask", ctypes.c_ulong),
        ("hwnd", wintypes.HWND),
        ("lpVerb", wintypes.LPCWSTR),
        ("lpFile", wintypes.LPCWSTR),
        ("lpParameters", wintypes.LPCWSTR),
        ("lpDirectory", wintypes.LPCWSTR),
        ("nShow", ctypes.c_int),
        ("hInstApp", wintypes.HINSTANCE),
        ("lpIDList", ctypes.c_void_p),
        ("lpClass", wintypes.LPCWSTR),
        ("hKeyClass", wintypes.HKEY),
        ("dwHotKey", wintypes.DWORD),
        ("hIcon", wintypes.HANDLE),
        ("hProcess", wintypes.HANDLE),
    ]


_SEE_MASK_NOCLOSEPROCESS = 0x00000040
_SW_SHOWNORMAL = 1
_INFINITE = 0xFFFFFFFF


def _win_launch_default_app(path: str):
    """Apre path con l'app associata, come farebbe os.startfile(), ma
    passando per ShellExecuteEx con SEE_MASK_NOCLOSEPROCESS per ottenere un
    handle di processo tracciabile. os.startfile() e' fire-and-forget e non
    lascia alcun riferimento su cui stop() possa agire: senza questo, su
    Windows senza fluidsynth/timidity/wildmidi installati (o
    senza un SoundFont trovato), il pulsante Stop non fermerebbe nulla —
    l'app MIDI predefinita del sistema resterebbe un processo completamente
    slegato da SoundText. Ritorna None se ShellExecuteEx fallisce (il
    chiamante ripiega allora su os.startfile, non interrompibile)."""
    info = _SHELLEXECUTEINFO()
    info.cbSize = ctypes.sizeof(_SHELLEXECUTEINFO)
    info.fMask = _SEE_MASK_NOCLOSEPROCESS
    info.hwnd = None
    info.lpVerb = "open"
    info.lpFile = path
    info.lpParameters = None
    info.lpDirectory = None
    info.nShow = _SW_SHOWNORMAL
    info.hInstApp = None
    shell32 = ctypes.windll.shell32
    if not shell32.ShellExecuteExW(ctypes.byref(info)):
        return None
    return info.hProcess or None


def _win_wait_process(handle) -> None:
    """Blocca finche' il processo non termina, da solo o perche' stop() ha
    chiamato TerminateProcess: stesso pattern di Popen.wait() gia' usato per
    gli altri backend di riproduzione, per restare coerenti col resto del
    modulo."""
    ctypes.windll.kernel32.WaitForSingleObject(handle, _INFINITE)


def _win_terminate_process(handle) -> None:
    kernel32 = ctypes.windll.kernel32
    kernel32.TerminateProcess(handle, 0)
    kernel32.CloseHandle(handle)


_STDERR_FD = 2
_stderr_lock = threading.Lock()
_stderr_depth = 0
_stderr_saved_fd: Optional[int] = None


@contextlib.contextmanager
def _suppress_native_stderr():
    """Silenzia temporaneamente lo stderr a livello di file descriptor (non
    solo sys.stderr, che non basterebbe: questi messaggi li stampa
    direttamente la libreria C, non Python). Copre il probing dei driver
    audio disponibili (ALSA/SDL3/...) che libfluidsynth esegue alla
    creazione del Synth e al caricamento del SoundFont: innocuo — non
    apriamo mai un driver audio in tempo reale, solo il file renderer
    offline — ma altrimenti finisce nel terminale dell'app ad ogni avvio
    sembrando un errore.

    Agisce sempre sul descrittore 2, quello in cui scrive la libreria C,
    e non su sys.stderr.fileno(): chi ha sostituito sys.stderr (pytest
    con la sua cattura) avrebbe altrimenti il proprio file rediretto su
    /dev/null. Il descrittore 2 è condiviso da tutto il processo e i
    render girano anche in thread diversi: un contatore protetto da lock
    fa sì che lo stderr venga salvato al primo ingresso e ripristinato
    solo all'ultima uscita, invece che da ciascun thread con una copia
    magari già silenziata."""
    global _stderr_depth, _stderr_saved_fd
    with _stderr_lock:
        if _stderr_depth == 0:
            try:
                saved_fd = os.dup(_STDERR_FD)
            except OSError:          # nessuno stderr (es. pythonw su Windows)
                saved_fd = None
            if saved_fd is not None:
                devnull_fd = os.open(os.devnull, os.O_WRONLY)
                try:
                    if sys.stderr is not None:
                        sys.stderr.flush()
                    os.dup2(devnull_fd, _STDERR_FD)
                finally:
                    os.close(devnull_fd)
            _stderr_saved_fd = saved_fd
        _stderr_depth += 1
    try:
        yield
    finally:
        with _stderr_lock:
            _stderr_depth -= 1
            if _stderr_depth == 0 and _stderr_saved_fd is not None:
                os.dup2(_stderr_saved_fd, _STDERR_FD)
                os.close(_stderr_saved_fd)
                _stderr_saved_fd = None


def _mix_wav_files(paths: List[str], out_path: str) -> None:
    """Mixa (somma campione per campione, con clipping) i WAV mono/stereo
    16-bit in paths in un unico file out_path: ricombina le passate di
    rendering separate per SoundFont diverso (vedi
    _PersistentSynth._render_multi). I file sorgente possono avere
    lunghezze leggermente diverse (code di rilascio diverse tra SoundFont
    diversi): il piu' corto viene esteso con silenzio invece di troncare
    il piu' lungo, per non perdere la coda del piu' lungo."""
    import numpy as np

    arrays = []
    params = None
    max_len = 0
    for path in paths:
        with contextlib.closing(wave.open(path, "rb")) as w:
            if params is None:
                params = (w.getnchannels(), w.getsampwidth(), w.getframerate())
            raw = w.readframes(w.getnframes())
        arr = np.frombuffer(raw, dtype=np.int16).astype(np.int32)
        arrays.append(arr)
        max_len = max(max_len, len(arr))

    mix = np.zeros(max_len, dtype=np.int32)
    for arr in arrays:
        mix[:len(arr)] += arr
    mix = np.clip(mix, -32768, 32767).astype(np.int16)

    nchannels, sampwidth, framerate = params
    with contextlib.closing(wave.open(out_path, "wb")) as w:
        w.setnchannels(nchannels)
        w.setsampwidth(sampwidth)
        w.setframerate(framerate)
        w.writeframes(mix.tobytes())


class _PersistentSynth:
    """Wrapper attorno alle istanze fluidsynth.Synth condivise da tutti i
    PlaybackEngine dell'app (vedi modulo). Create pigramente al primo
    utilizzo, cosi' l'avvio dell'app non paga ne' il caricamento del
    SoundFont ne' il probing dei driver audio che fluidsynth esegue alla
    costruzione del Synth se l'utente non riproduce mai nulla.

    Quando non e' richiesto nessun override per-strumento, c'e' un solo
    synth condiviso (self._synth) con un solo SoundFont caricato, come
    nella versione originale. Quando invece uno o piu' strumenti hanno un
    SoundFont assegnato (core.settings.get_instrument_soundfont), il
    rendering NON puo' avvenire in un unico passaggio multi-canale: caricare
    piu' SoundFont nella STESSA istanza di synth e instradare i canali con
    fluid_synth_sfont_select NON isola correttamente il preset per canale
    per gli eventi program_change 'grezzi' di un file MIDI (a differenza di
    una selezione esplicita via API) — la ricerca del preset ignora
    qualunque assegnazione canale-soundfont precedente e usa sempre il
    SoundFont caricato piu' di recente, per QUALSIASI canale (verificato
    empiricamente: perfino un canale mai toccato dall'override cambia
    suono al solo caricamento di un secondo SoundFont nella stessa
    istanza). Si renderizza percio' un gruppo di canali alla volta, ognuno
    con un synth dedicato a un SOLO SoundFont (self._override_synths), e si
    mixano poi i WAV risultanti (vedi _mix_wav_files).

    Un solo render alla volta: il lock serializza le chiamate concorrenti
    da PlaybackEngine diversi (es. anteprima libreria MIDI + transport
    principale). Ogni render dura tipicamente poche decine di ms (molto
    piu' veloce del tempo reale) quindi la serializzazione non introduce
    latenza percepibile, anche sommando le passate multiple del percorso
    con override.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._synth = None
        self._font_ids: Dict[str, int] = {}
        # Un synth DEDICATO per ciascun SoundFont usato come override
        # per-strumento (un solo font ciascuno): vedi la docstring della
        # classe per il perche' non basta instradare i canali in un unico
        # synth condiviso con piu' font caricati.
        self._override_synths: Dict[str, object] = {}

    def _new_synth(self):
        from .settings import get_playback_gain
        with _suppress_native_stderr():
            return _fluid.Synth(
                gain=get_playback_gain(), samplerate=48000,
                **{"synth.reverb.active": 1, "synth.chorus.active": 1},
            )

    def set_gain(self, value: float):
        """Aggiorna il gain di tutti i synth gia' creati (condiviso +
        eventuali override per-strumento) usando fluid_synth_set_gain()
        (Synth.set_gain), l'unico modo verificato che sopravvive al
        system_reset() fatto da _render_group prima di ogni render (cambiare
        l'impostazione 'synth.gain' aggiorna il valore letto, ma il render
        dopo il reset torna in silenzio al gain di creazione):
        effettivo dal prossimo render senza riavviare l'app. Richiamato da
        Playback -> Volume di sintesi (gain)... dopo aver salvato il nuovo
        default con core.settings.set_playback_gain."""
        with self._lock:
            if self._synth is not None:
                self._synth.set_gain(value)
            for synth in self._override_synths.values():
                synth.set_gain(value)

    def _ensure_font_loaded(self, soundfont: str) -> int:
        """Carica soundfont sul synth condiviso self._synth (usato quando
        non ci sono override attivi, o per il gruppo di canali 'di
        default' del rendering multi-passata)."""
        if self._synth is None:
            self._synth = self._new_synth()
        sfid = self._font_ids.get(soundfont)
        if sfid is not None:
            return sfid
        # sfload ritorna -1 (senza sollevare eccezioni) se il file non e' un
        # SoundFont valido/leggibile: non lo si mette in cache in quel caso,
        # altrimenti un fallimento verrebbe scambiato per un caricamento
        # riuscito e il rendering proseguirebbe silenziosamente senza preset
        # (nessun suono) invece di far ripiegare il chiamante sul CLI
        # fluidsynth.
        with _suppress_native_stderr():
            sfid = self._synth.sfload(soundfont)
        if sfid == -1:
            raise RuntimeError(tr("SoundFont non valido: {soundfont}", soundfont=soundfont))
        self._font_ids[soundfont] = sfid
        return sfid

    def _ensure_override_synth(self, soundfont: str):
        """Synth dedicato con un SOLO SoundFont caricato (soundfont), pagato
        una sola volta e poi riusato — mai scaricato, stesso principio del
        synth condiviso di default."""
        synth = self._override_synths.get(soundfont)
        if synth is not None:
            return synth
        synth = self._new_synth()
        with _suppress_native_stderr():
            sfid = synth.sfload(soundfont)
        if sfid == -1:
            raise RuntimeError(tr("SoundFont non valido: {soundfont}", soundfont=soundfont))
        self._override_synths[soundfont] = synth
        return synth

    @staticmethod
    def _render_group(synth, midi_path: str, wav_path: str, stop_check, reverb_room: Optional[str] = None) -> bool:
        """Renderizza midi_path su wav_path con synth (un solo SoundFont
        caricato): funzione di basso livello condivisa dal rendering
        semplice e da ciascuna passata del rendering multi-SoundFont."""
        # synth e' persistente e riusato per OGNI rendering (mai ricreato, vedi
        # la docstring di _PersistentSynth): se il rendering precedente su
        # questa stessa istanza era stato interrotto a meta' (stop_check(), es.
        # un riavvio rapido causato dal trascinamento di uno slider volume/pan),
        # le note gia' innescate a quel punto restano "attive" nel synth —
        # fluid_player_stop() ferma la lettura del file MIDI ma non spegne le
        # voci gia' avviate. Senza un reset esplicito qui, quelle note
        # residue si mescolerebbero nel PROSSIMO rendering (lo stesso synth
        # continua a produrre audio anche per loro), facendo sentire un
        # volume diverso a seconda di QUANTI rendering parziali sono stati
        # abbandonati prima di questo — tipicamente di piu' trascinando lo
        # slider con il mouse che raggiungendo lo stesso valore con le
        # frecce, da cui la differenza percepita a parita' di valore finale.
        synth.system_reset()
        # L'ambiente del riverbero (vedi core.effects) va reimpostato a ogni
        # render: il synth e' condiviso, e un brano con un'altra sala non
        # deve lasciarla a chi suona dopo (anteprima della libreria MIDI...).
        apply_reverb(synth, reverb_room or DEFAULT_REVERB_ROOM)
        try:
            player = _fluid.Player(synth)
        except RuntimeError:
            return False
        if not player.add(midi_path):
            player.delete()
            return False
        player.play()
        # synth.get_samples(n) chiede a fluidsynth n campioni in UNA sola
        # chiamata C (fluid_synth_write_s16, che internamente cicla sui blocchi
        # DSP interni da 64 campioni), invece del new_fluid_file_renderer()
        # precedente il cui fluid_file_renderer_process_block() va richiamato
        # dal lato Python una volta per ogni blocco da 64 campioni: per un
        # brano di qualche minuto sono centinaia di migliaia di chiamate
        # Python (bytecode + marshalling ctypes) in piu', che si sommano
        # all'attesa prima che l'audio parta (play/mute/solo/volume/pan
        # riavviano sempre un render completo, vedi _on_mixer_changed).
        # _RENDER_CHUNK_FRAMES (100ms a 48kHz) resta comunque abbastanza
        # piccolo da non introdurre un ritardo percepibile nel rispondere a
        # stop_check() (interruzione di un render in corso).
        ok = True
        try:
            with contextlib.closing(wave.open(wav_path, "wb")) as w:
                w.setnchannels(2)
                w.setsampwidth(2)
                w.setframerate(48000)
                while player.playing():
                    if stop_check():
                        ok = False
                        break
                    w.writeframes(synth.get_samples(_RENDER_CHUNK_FRAMES).tobytes())
        finally:
            player.delete()
        return ok

    def _render_multi(self, midi_path: str, wav_path: str, soundfont: str,
                       stop_check, channel_overrides: Dict[int, str],
                       reverb_room: Optional[str] = None) -> bool:
        """Rendering in passate separate (una per SoundFont coinvolto, vedi
        la docstring della classe), poi mixate in wav_path. Ritorna False
        (fallback CLI, come render_to_wav) se una passata fallisce o
        stop_check() scatta durante una di esse."""
        from .midi_export import channels_used_in_midi_file, filter_midi_file_by_channels

        all_channels = channels_used_in_midi_file(midi_path)
        override_groups: Dict[str, set] = {}
        for chan, path in channel_overrides.items():
            if chan in all_channels:
                override_groups.setdefault(path, set()).add(chan)
        default_channels = all_channels - set(channel_overrides.keys())

        tmp_wavs = []
        try:
            groups = []
            if default_channels:
                self._ensure_font_loaded(soundfont)
                groups.append((self._synth, default_channels))
            for path, chans in override_groups.items():
                try:
                    synth = self._ensure_override_synth(path)
                except RuntimeError:
                    log.warning("SoundFont per strumento non caricabile: %s", path, exc_info=True)
                    # Override non piu' raggiungibile (file spostato/cancellato
                    # dopo averlo assegnato allo strumento): questi canali
                    # restano silenziosi in questo rendering, invece di far
                    # fallire l'intera riproduzione per un solo strumento.
                    continue
                groups.append((synth, chans))

            for synth, chans in groups:
                tmp_midi = tempfile.NamedTemporaryFile(suffix=".mid", delete=False).name
                tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
                try:
                    filter_midi_file_by_channels(midi_path, tmp_midi, chans)
                    ok = self._render_group(synth, tmp_midi, tmp_wav, stop_check, reverb_room)
                finally:
                    os.remove(tmp_midi)
                if not ok:
                    # Passata interrotta (stop_check) o fallita: il suo WAV
                    # parziale non serve al mix, va ripulito subito qui,
                    # altrimenti il "finally" esterno (che ripulisce solo
                    # tmp_wavs) non lo vedrebbe mai.
                    os.remove(tmp_wav)
                    return False
                tmp_wavs.append(tmp_wav)

            if not tmp_wavs:
                return False
            _mix_wav_files(tmp_wavs, wav_path)
            return True
        finally:
            for w in tmp_wavs:
                if os.path.exists(w):
                    os.remove(w)

    def _render_port(self, midi_path: str, wav_path: str, soundfont: str, stop_check,
                     channel_overrides: Optional[Dict[int, str]], reverb_room: Optional[str]) -> bool:
        """Rendering di un file con una sola porta MIDI (16 canali)."""
        if not channel_overrides:
            self._ensure_font_loaded(soundfont)
            return self._render_group(self._synth, midi_path, wav_path, stop_check, reverb_room)
        return self._render_multi(midi_path, wav_path, soundfont, stop_check, channel_overrides, reverb_room)

    def _render_ports(self, midi_path: str, wav_path: str, soundfont: str, stop_check,
                      channel_overrides: Optional[Dict[int, str]], reverb_room: Optional[str],
                      ports: List[int]) -> bool:
        """Piu' di 15 tracce melodiche: il file usa piu' porte MIDI (vedi
        st_language.midi._assign_channels), ma il player di FluidSynth le
        ignora e suonerebbe la porta 1 sugli stessi canali della porta 0.
        Si renderizza quindi una porta per passata (con gli override dei
        suoi slot, porta * 16 + canale) e si mixano le passate."""
        from .midi_export import filter_midi_file_by_port

        tmp_wavs = []
        try:
            for port in ports:
                overrides = {slot % 16: path for slot, path in (channel_overrides or {}).items()
                             if slot // 16 == port}
                tmp_midi = tempfile.NamedTemporaryFile(suffix=".mid", delete=False).name
                tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
                tmp_wavs.append(tmp_wav)
                try:
                    filter_midi_file_by_port(midi_path, tmp_midi, port)
                    ok = self._render_port(tmp_midi, tmp_wav, soundfont, stop_check, overrides or None,
                                           reverb_room)
                finally:
                    os.remove(tmp_midi)
                if not ok:
                    return False
            _mix_wav_files(tmp_wavs, wav_path)
            return True
        finally:
            for w in tmp_wavs:
                if os.path.exists(w):
                    os.remove(w)

    def render_to_wav(self, midi_path: str, wav_path: str, soundfont: str,
                       stop_check, channel_overrides: Optional[Dict[int, str]] = None,
                       reverb_room: Optional[str] = None) -> bool:
        """Renderizza midi_path su wav_path. Ritorna False se interrotto
        (stop_check() torna True) o se il rendering fallisce per qualunque
        motivo: in entrambi i casi il chiamante ripiega sul percorso
        CLI/subprocess esistente (che non supporta channel_overrides, vedi
        PlaybackEngine.play_file).

        channel_overrides mappa canale MIDI -> percorso SoundFont per gli
        strumenti con un override (vedi core.settings.get_instrument_soundfont
        e core.midi_export.channel_instrument_map): se vuoto/None, rendering
        singolo come per un SoundFont unico; altrimenti rendering in passate
        multiple poi mixate (vedi _render_multi e la docstring della classe
        per il perche')."""
        with self._lock:
            try:
                from .midi_export import midi_file_ports
                ports = midi_file_ports(midi_path)
                if len(ports) > 1:
                    return self._render_ports(midi_path, wav_path, soundfont, stop_check, channel_overrides,
                                              reverb_room, sorted(ports))
                return self._render_port(midi_path, wav_path, soundfont, stop_check, channel_overrides,
                                         reverb_room)
            except Exception:
                # Qualunque errore col binding persistente (SoundFont
                # incompatibile, sintomi di libreria, ecc.) non deve far
                # cadere la riproduzione: si ripiega sul CLI subprocess.
                log.warning("Rendering con la libreria FluidSynth fallito (%s): si ripiega sul CLI",
                            soundfont, exc_info=True)
                return False


_shared_synth = _PersistentSynth() if _FLUID_AVAILABLE else None


def set_shared_synth_gain(value: float):
    """Applica value al synth condiviso gia' creato (se esiste): il
    chiamante (gui.playback_gain_dialog) salva prima il nuovo default con
    core.settings.set_playback_gain, poi richiama questa funzione perche'
    il cambiamento sia udibile dalla riproduzione successiva senza dover
    riavviare l'app. No-op se _shared_synth e' None (libreria FluidSynth
    non disponibile) o se non e' ancora stato creato nessun synth (il prossimo
    creato leggera' comunque il nuovo default da _new_synth)."""
    if _shared_synth is not None:
        _shared_synth.set_gain(value)


def _find_soundfont() -> Optional[str]:
    from .settings import get_soundfont_path

    # 1) percorso configurato esplicitamente dall'utente (menu Playback -> SoundFont)
    configured = get_soundfont_path()
    if configured and os.path.exists(configured):
        return configured

    # 2) variabile d'ambiente (utile per esecuzioni scriptate/headless)
    env_path = os.environ.get("SOUNDTEXT_SOUNDFONT")
    if env_path and os.path.exists(env_path):
        return env_path

    # 3) SoundFont incluso a fianco dell'eseguibile (build portable Windows,
    # install.sh/install-macos.sh): cartella soundfonts/ nella radice
    # dell'app, vedi DEFAULT_SOUNDFONTS_DIR in project_io.py.
    from .version import get_app_root
    candidates = [
        os.path.join(get_app_root(), "soundfonts", "FluidR3_GM.sf2"),
    ]

    # 4) percorsi comuni delle principali distribuzioni Linux, piu' un paio
    # di posizioni idiomatiche su Windows e macOS (nessun SoundFont e'
    # distribuito di serie su nessuno dei tre sistemi operativi: l'utente
    # lo scarica e lo mette li').
    candidates += [
        os.path.expanduser("~/.local/share/soundfonts/FluidR3_GM.sf2"),
        os.path.expanduser("~/.soundfonts/FluidR3_GM.sf2"),
        "/usr/share/sounds/sf2/FluidR3_GM.sf2",       # Debian/Ubuntu/Fedora (fluid-soundfont-gm)
        "/usr/share/soundfonts/FluidR3_GM.sf2",         # Arch/CachyOS (AUR soundfont-fluid)
        "/usr/share/sounds/sf2/default.sf2",
        "/usr/share/soundfonts/default.sf2",
    ]
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        candidates += [
            os.path.join(appdata, "SoundText", "soundfonts", "FluidR3_GM.sf2"),
            os.path.join(appdata, "FluidSynth", "FluidR3_GM.sf2"),
        ]
    elif sys.platform == "darwin":
        candidates += [
            os.path.expanduser("~/Library/Audio/Sounds/Banks/FluidR3_GM.sf2"),
            os.path.expanduser("~/Library/Application Support/SoundText/soundfonts/FluidR3_GM.sf2"),
            "/Library/Audio/Sounds/Banks/FluidR3_GM.sf2",
            "/opt/homebrew/share/soundfonts/FluidR3_GM.sf2",  # Homebrew su Apple Silicon
            "/usr/local/share/soundfonts/FluidR3_GM.sf2",     # Homebrew su Intel
        ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def render_midi_file_to_samples(midi_path: str, channel_overrides=None, reverb_room: Optional[str] = None,
                                stop_check=None):
    """Sintesi offline di un file MIDI con lo stesso SoundFont e gain della
    riproduzione: (campioni float32 (frame, 2), frequenza). Solleva
    RuntimeError se annullata (stop_check) o se non c'e' modo di
    renderizzare (fluidsynth/SoundFont assenti)."""
    import numpy as np
    from .audio_tracks import AUDIO_SAMPLE_RATE, read_wav

    stop_check = stop_check or (lambda: False)
    wav_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    try:
        soundfont = _find_soundfont()
        fluidsynth_bin = shutil.which("fluidsynth")
        rendered = False
        if _shared_synth and soundfont:
            rendered = _shared_synth.render_to_wav(midi_path, wav_path, soundfont, stop_check,
                                                   channel_overrides=channel_overrides, reverb_room=reverb_room)
        if not rendered and fluidsynth_bin and soundfont and not stop_check():
            from .settings import get_playback_gain
            gain = get_playback_gain()
            result = subprocess.run(
                [fluidsynth_bin, "-ni", "-r", "48000", "-g", str(gain),
                 "-o", "synth.reverb.active=1", "-o", "synth.chorus.active=1",
                 *reverb_cli_options(reverb_room or DEFAULT_REVERB_ROOM),
                 "-o", f"synth.gain={gain}", "-F", wav_path, soundfont, midi_path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            rendered = result.returncode == 0 and os.path.exists(wav_path)
        if stop_check():
            raise RuntimeError(tr("Operazione annullata."))
        if not rendered:
            raise RuntimeError(
                tr("Impossibile renderizzare le tracce MIDI: servono fluidsynth e un SoundFont "
                "(menu Playback → Scegli SoundFont)."))
        try:
            samples, rate = read_wav(wav_path)
        except ValueError:
            return np.zeros((0, 2), dtype=np.float32), AUDIO_SAMPLE_RATE   # rendering vuoto: silenzio
        if samples.shape[1] == 1:
            samples = np.repeat(samples, 2, axis=1)
        return samples[:, :2], rate
    finally:
        if os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except OSError:
                pass


def dry_track(track: Track) -> Track:
    """Copia della traccia "asciutta", per il re-amping con un simulatore di
    amplificatore esterno: senza catena di effetti, senza invio al
    riverbero/chorus del synth, pan al centro (il volume resta)."""
    dry = copy.copy(track)
    dry.effects = []
    dry.reverb = 0
    dry.chorus = 0
    dry.pan = 64
    return dry


def render_project_mix(project: Project, stop_check=None, include_midi: bool = True,
                       allow_empty: bool = False, tracks: Optional[List[Track]] = None,
                       master: Optional[bool] = None, dry: bool = False):
    """Rendering del brano come si sente (tracce udibili): tracce MIDI con
    lo stesso SoundFont e gain della riproduzione, piu' le clip delle
    tracce audio e le tracce con una catena di effetti (renderizzate a
    parte, vedi core.effect_render). Ritorna (campioni float32 (frame, 2),
    frequenza).

    include_midi=False salta le tracce con note (base di sole tracce audio,
    quando manca un SoundFont). Solleva RuntimeError se ci sono note da
    suonare ma nessun modo di renderizzarle (fluidsynth/SoundFont assenti),
    se l'operazione e' stata annullata (stop_check) o, salvo allow_empty,
    se non c'e' niente da suonare.

    tracks limita il rendering a quelle tracce, ignorando Solo/Mute (come
    se fossero le sole in Solo).

    master: applica la catena del master (Project.master_effects); per
    default si' per il brano intero, no per l'export di singole tracce.
    dry: tracce asciutte (vedi dry_track), senza master."""
    import numpy as np
    from .audio_tracks import AUDIO_SAMPLE_RATE, build_audio_layers, mix_layers
    from .effect_render import fx_tracks, prepare_stem, render_stem
    from .tempo_map import build_tempo_beat_map

    stop_check = stop_check or (lambda: False)
    if master is None:
        master = tracks is None and not dry
    if tracks is None:
        tracks = project.audible_tracks()
    if dry:
        tracks = [dry_track(t) for t in tracks]
    if not include_midi:
        tracks = [t for t in tracks if t.is_audio]
    tempo_map = build_tempo_beat_map(project, tracks=tracks)
    fx = fx_tracks([t for t in tracks if t.is_audio or t.text.strip()])
    fx_ids = {id(t) for t in fx}
    plain = [t for t in tracks if id(t) not in fx_ids]
    midi_tracks = [t for t in plain if not t.is_audio and t.text.strip()]
    layers = build_audio_layers(project, plain, tempo_map)
    if not midi_tracks and not layers and not fx and not allow_empty:
        raise RuntimeError(tr("Niente da esportare: nessuna traccia udibile con note o clip audio."))

    base, rate = np.zeros((0, 2), dtype=np.float32), AUDIO_SAMPLE_RATE
    if midi_tracks:
        midi_path = tempfile.NamedTemporaryFile(suffix=".mid", delete=False).name
        try:
            export_project_to_midi(project, midi_path, tracks=midi_tracks)
            base, rate = render_midi_file_to_samples(
                midi_path, _resolve_channel_soundfont_overrides(project, True, tracks=midi_tracks),
                project.reverb_room, stop_check)
        finally:
            if os.path.exists(midi_path):
                try:
                    os.remove(midi_path)
                except OSError:
                    pass
    stems = []
    for track in fx:
        request = prepare_stem(project, track, tempo_map)
        try:
            samples = render_stem(request, stop_check)
        finally:
            request.cleanup()
        if samples is not None:
            stems.append((samples, 0.0))
    mixed = mix_layers(base[:, :2], rate, layers, stems=stems)
    if master:
        from .effect_render import apply_master, master_chain
        mixed = apply_master(mixed, rate, master_chain(project), project.tempo_bpm)
    return mixed, rate


def render_project_mix_to_wav(project: Project, out_path: str, stop_check=None,
                              tracks: Optional[List[Track]] = None, dry: bool = False) -> None:
    """Esporta in out_path (WAV 48 kHz, 24 bit, stereo) il mix delle tracce
    udibili, o solo di tracks, eventualmente asciutte (vedi
    render_project_mix, di cui solleva gli stessi errori)."""
    from .audio_tracks import write_wav
    mixed, rate = render_project_mix(project, stop_check, tracks=tracks, dry=dry)
    write_wav(out_path, mixed, rate, bits=24)


def get_active_soundfont_info():
    """Ritorna (percorso_o_None, e'_configurato_manualmente) per mostrare
    all'utente quale SoundFont verra' usato in riproduzione."""
    from .settings import get_soundfont_path
    configured = get_soundfont_path()
    if configured and os.path.exists(configured):
        return configured, True
    return _find_soundfont(), False


def _preferred_live_audio_driver() -> Optional[str]:
    """Nome del driver audio da chiedere esplicitamente a fluidsynth per
    LiveSynth (audio in tempo reale), invece di lasciargli scegliere il
    default della piattaforma (None = default di fluidsynth).

    Linux: il default e' 'alsa' grezzo, collegato direttamente
    all'hardware: senza un server audio di mezzo a fare da cuscinetto, e'
    molto piu' sensibile a xrun/crepitii. Si forza percio' 'pulseaudio',
    che funziona sia con PulseAudio sia con il layer di compatibilita' di
    PipeWire (pipewire-pulse) e gestisce un buffering piu' robusto lato
    server, isolato dai tempi di risposta di QUESTO processo.

    Windows: il default di fluidsynth e' 'dsound' (DirectSound), che da
    Windows Vista in poi e' solo un'emulazione sopra WASAPI e aggiunge un
    buffer proprio, non controllato da audio.period-size/periods: tasti
    sensibilmente in ritardo anche con un buffer piccolo. Si chiede quindi
    direttamente 'wasapi' (modalita' condivisa), con ripiego sul default
    in LiveSynth.create se non si apre.

    macOS: il default 'coreaudio' va gia' bene."""
    if sys.platform.startswith("linux"):
        return "pulseaudio"
    if sys.platform == "win32":
        return "wasapi"
    return None


def _fallback_live_audio_driver() -> Optional[str]:
    """Driver di ripiego se quello di _preferred_live_audio_driver non si
    apre (es. nessun server PulseAudio/PipeWire, o WASAPI non disponibile):
    il default storico di fluidsynth sulla piattaforma."""
    if sys.platform.startswith("linux"):
        return "alsa"
    if sys.platform == "win32":
        return "dsound"
    return None


# WASAPI in modalita' condivisa (quella usata da fluidsynth di default)
# IGNORA audio.period-size: usa come period il periodo del dispositivo di
# Windows (di solito 10ms) e come buffer periods * quel periodo, e a ogni
# giro riempie TUTTO il buffer libero - quindi il ritardo tasto->suono e'
# sempre l'intero buffer. L'unica leva e' percio' il numero di periods:
# livello "Bassa"/"Media"/"Alta" del dialogo -> 2/3/4 periods (~20/30/40ms).
# Il crepitio osservato in passato con periods=2 o 3 era con DirectSound
# (il driver di default di allora), non con WASAPI.
_WASAPI_SHARED_PERIODS = {256: 2, 512: 3, 1024: 4}
_WASAPI_DEVICE_PERIOD_MS = 10


def _live_buffer_settings(driver: Optional[str], level: int) -> tuple:
    """(audio.period-size, audio.periods) per il driver e il livello di
    latenza scelto (uno di core.settings.LIVE_PERIOD_SIZE_CHOICES)."""
    if driver == "wasapi":
        return level, _WASAPI_SHARED_PERIODS.get(level, 4)
    return level, 4


def _live_buffer_ms(driver: Optional[str], period_size: int, periods: int) -> int:
    """Durata stimata del buffer: per WASAPI condiviso dipende dal periodo
    del dispositivo, non leggibile dalle impostazioni di FluidSynth (si assume il tipico 10ms)."""
    if driver == "wasapi":
        return periods * _WASAPI_DEVICE_PERIOD_MS
    return round(periods * period_size / 48000 * 1000)


def _raise_windows_timer_resolution() -> bool:
    """Porta a 1ms la risoluzione del timer di Windows finche' il synth in
    tempo reale e' aperto (vedi LiveSynth.close): il thread audio di
    fluidsynth WASAPI dorme meta' buffer fra un riempimento e l'altro, e
    con la risoluzione predefinita (~15,6ms) quell'attesa si allunga fino a
    svuotare un buffer piccolo (crepitio). E' cio' che fanno i programmi
    audio su Windows. True se la chiamata e' riuscita."""
    try:
        import ctypes
        return ctypes.windll.winmm.timeBeginPeriod(1) == 0
    except Exception:
        return False


def _restore_windows_timer_resolution():
    try:
        import ctypes
        ctypes.windll.winmm.timeEndPeriod(1)
    except Exception:
        pass


class LiveSynth:
    """Synth fluidsynth in tempo REALE (apre un driver audio vero e proprio
    con .start(), a differenza di _PersistentSynth/_shared_synth qui sopra,
    che renderizzano sempre offline su file per evitare crepitii da
    underrun — vedi la docstring del modulo): usato SOLO per il feedback
    sonoro immediato dei tasti premuti nel dialogo "Suona con la tastiera"
    (gui.keyboard_play_dialog), dove l'obiettivo e' sentire la nota
    nell'istante in cui si preme il tasto, cosa che il percorso offline
    (esporta MIDI -> renderizza WAV -> avvia player) non puo' garantire con
    una latenza utilizzabile.

    Istanza NON condivisa (a differenza di _shared_synth): ogni dialogo che
    ne ha bisogno crea la propria con create() e la chiude con close()
    quando non serve piu', cosi' il driver audio in tempo reale resta
    aperto solo per la durata effettiva dell'uso, non per tutta la vita
    dell'app."""

    def __init__(self):
        self._synth = None
        self._sfid = None
        self._program_by_channel = {}
        # Driver audio effettivamente aperto e latenza del buffer (ms), per
        # la diagnostica mostrata nel dialogo (vedi description()).
        self.driver_name = None
        self.buffer_ms = None
        self._timer_resolution_raised = False

    @classmethod
    def create(cls) -> Optional["LiveSynth"]:
        """None se la libreria FluidSynth non c'e' o non e' stato trovato
        nessun SoundFont, o se l'apertura del driver audio fallisce per
        qualunque motivo: il chiamante deve limitarsi in quel caso a non
        offrire il feedback sonoro, senza sollevare errori."""
        if not _FLUID_AVAILABLE:
            return None
        soundfont = _find_soundfont()
        if not soundfont:
            return None
        from .settings import get_playback_gain, get_live_period_size
        self = cls()
        try:
            with _suppress_native_stderr():
                self._synth = _fluid.Synth(gain=get_playback_gain(), samplerate=48000)
                # Il default di fluidsynth per il driver audio in tempo reale
                # e' un buffer minuscolo (period-size=64, periods=16: circa
                # 21ms totali a 48kHz): troppo poco per questo processo,
                # produce crepitii. Il livello scelto dall'utente nel dialogo
                # (vedi core.settings.get_live_period_size) e'
                # un compromesso tra reattivita' dei tasti e rischio di
                # crepitii, che dipende dall'hardware e non e' verificabile
                # in ambienti offscreen/CI. Come si traduce in buffer dipende
                # dal driver, vedi _live_buffer_settings.
                level = get_live_period_size()
                driver = _preferred_live_audio_driver()
                period_size, periods = _live_buffer_settings(driver, level)
                self._synth.setting('audio.period-size', period_size)
                self._synth.setting('audio.periods', periods)
                if driver == "wasapi":
                    self._timer_resolution_raised = _raise_windows_timer_resolution()
                self._synth.start_audio(driver)
                fallback = _fallback_live_audio_driver()
                if not self._synth.audio_driver and fallback is not None:
                    # driver non disponibile: si riprova con quello di ripiego
                    log.warning("Driver audio %r non disponibile, provo %r", driver, fallback)
                    period_size, periods = _live_buffer_settings(fallback, level)
                    self._synth.setting('audio.period-size', period_size)
                    self._synth.setting('audio.periods', periods)
                    self._synth.start_audio(fallback)
                if not self._synth.audio_driver:
                    raise RuntimeError(tr("impossibile aprire un driver audio in tempo reale"))
                self.driver_name = self._synth.get_setting('audio.driver')
                self.buffer_ms = _live_buffer_ms(self.driver_name, period_size, periods)
                log.info("Synth in tempo reale: driver %s, buffer ~%d ms", self.driver_name, self.buffer_ms)
                self._sfid = self._synth.sfload(soundfont)
                if self._sfid != -1:
                    # Un Synth appena creato non ha i canali inizializzati
                    # secondo la convenzione General MIDI: senza questo
                    # reset (che li stabilisce, incluso il canale 10 come
                    # percussioni) noteon() sul canale percussioni non
                    # produce alcuna voce/suono finche' non si seleziona
                    # ESPLICITAMENTE un preset con program_select — cosa che
                    # qui non facciamo mai per le percussioni (ne' lo fa
                    # l'esportazione MIDI, vedi core.midi_export), esattamente
                    # come _PersistentSynth._render_group fa per lo stesso
                    # motivo prima di ogni rendering offline.
                    self._synth.system_reset()
                    # la stessa sala della riproduzione: le versioni recenti
                    # di FluidSynth hanno un riverbero predefinito diverso
                    apply_reverb(self._synth, DEFAULT_REVERB_ROOM)
            if self._sfid == -1:
                self.close()
                return None
        except Exception:
            log.warning("Synth in tempo reale non disponibile", exc_info=True)
            self.close()
            return None
        return self

    def description(self) -> str:
        """Riga di diagnostica per l'utente: driver audio aperto davvero
        (es. 'dsound' invece di 'wasapi' se quest'ultimo non si e' aperto)
        e latenza del buffer lato app."""
        return f"Audio: {self.driver_name}, buffer ~{self.buffer_ms} ms"

    def set_program(self, channel: int, gm_program: int):
        if self._synth is None or self._program_by_channel.get(channel) == gm_program:
            return
        self._synth.program_select(channel, self._sfid, 0, gm_program)
        self._program_by_channel[channel] = gm_program

    def note_on(self, channel: int, midi_pitch: int, velocity: int = 100):
        if self._synth is None:
            return
        self._synth.noteon(channel, max(0, min(127, midi_pitch)), max(1, min(127, velocity)))

    def note_off(self, channel: int, midi_pitch: int):
        if self._synth is None:
            return
        self._synth.noteoff(channel, max(0, min(127, midi_pitch)))

    def pitch_bend(self, channel: int, semitones: float):
        """Applica un pitch bend al canale, in semitoni (positivo = verso
        l'alto): usato per il bending dal vivo del dialogo 'Suona con la
        tastiera' e le tastiere MIDI). La leva (-8192..8191) copre
        l'escursione di default di FluidSynth, +-2 semitoni: 4096 unita' per
        semitono (misurato; con le 2048 indicate da pyfluidsynth il bending
        di un tono dal vivo suonava di mezzo tono)."""
        if self._synth is None:
            return
        self._synth.pitch_bend(channel, int(round(semitones / LIVE_BEND_RANGE_SEMITONES * 8192)))

    def all_notes_off(self):
        if self._synth is not None:
            self._synth.all_notes_off()

    def close(self):
        if self._synth is not None:
            try:
                self._synth.delete()
            except Exception:
                pass
            self._synth = None
        if self._timer_resolution_raised:
            _restore_windows_timer_resolution()
            self._timer_resolution_raised = False


class LivePluginSynth:
    """Come LiveSynth (stessi metodi), ma i tasti li suona lo strumento
    plugin della traccia (Track.synth: SFZ interno, LV2 o VST3) invece del
    SoundFont. Lo strumento e l'uscita audio stanno nel processo dei plugin
    dal vivo (core.plugins.live_start): da qui partono solo i messaggi
    MIDI, e se il plugin va in crash SoundText resta in piedi (i tasti
    tacciono; al Registra/Suona successivo si riprova)."""

    def __init__(self, ref: str):
        self.ref = ref
        self.driver_name = None
        self.buffer_ms = None
        self._session = None

    @classmethod
    def create(cls, ref: str, params: dict, state: str, pan: int = 64) -> Optional["LivePluginSynth"]:
        """None se lo strumento o l'uscita audio non si aprono (il motivo va
        nel log): il chiamante ripiega su LiveSynth."""
        from .plugins import PluginError, live_start
        from .settings import get_live_period_size
        self = cls(ref)
        try:
            info = live_start(ref, params, state, get_live_period_size(), pan)
        except PluginError as e:
            log.warning("Strumento %s non suonabile dal vivo: %s", ref, e)
            return None
        self.driver_name = info.get("hostapi") or "?"
        self.buffer_ms = int(info.get("latency_ms") or 0)
        self._session = info["session"]
        log.info("Strumento %s dal vivo: %s, buffer ~%d ms", ref, self.driver_name, self.buffer_ms)
        return self

    def description(self) -> str:
        from .plugins import display_name
        return f"Audio: {self.driver_name}, buffer ~{self.buffer_ms} ms ({display_name(self.ref)})"

    def _send(self, *data: int):
        if self._session is None:
            return
        from .plugins import live_send
        if not live_send(self._session, bytes(data)):
            log.warning("Lo strumento %s dal vivo non suona piu'", self.ref)
            self._session = None

    def set_program(self, channel: int, gm_program: int):
        # come l'esportazione MIDI, che il program change lo manda anche ai plugin
        self._send(0xC0 | (channel & 0x0F), max(0, min(127, gm_program)))

    def note_on(self, channel: int, midi_pitch: int, velocity: int = 100):
        self._send(0x90 | (channel & 0x0F), max(0, min(127, midi_pitch)), max(1, min(127, velocity)))

    def note_off(self, channel: int, midi_pitch: int):
        self._send(0x80 | (channel & 0x0F), max(0, min(127, midi_pitch)), 0)

    def pitch_bend(self, channel: int, semitones: float):
        """Come LiveSynth.pitch_bend: leva su +-2 semitoni (l'escursione di
        default anche di sfizz e della maggior parte degli strumenti)."""
        value = max(-8192, min(8191, int(round(semitones / LIVE_BEND_RANGE_SEMITONES * 8192)))) + 8192
        self._send(0xE0 | (channel & 0x0F), value & 0x7F, value >> 7)

    def all_notes_off(self):
        for channel in range(16):
            self._send(0xB0 | channel, 123, 0)

    def close(self):
        if self._session is not None:
            from .plugins import live_stop
            live_stop(self._session)
            self._session = None


def _resolve_channel_soundfont_overrides(project: Project, only_audible: bool,
                                        tracks: Optional[List[Track]] = None) -> Optional[Dict[int, str]]:
    """Canale MIDI -> percorso SoundFont per gli strumenti che ne hanno uno
    assegnato esplicitamente (Gestione strumenti -> SoundFont per questo
    strumento), da passare a PlaybackEngine.play_file(). Un canale il cui
    strumento non ha un override semplicemente non compare nel dict
    risultante, e resta sul SoundFont predefinito (vedi
    _PersistentSynth.render_to_wav)."""
    from .settings import get_instrument_soundfont
    from .midi_export import channel_instrument_map
    overrides = {}
    for channel, instrument_name in channel_instrument_map(project, only_audible=only_audible, tracks=tracks).items():
        path = get_instrument_soundfont(instrument_name)
        if path and os.path.exists(path):
            overrides[channel] = path
    return overrides or None


# Rendering gia' fatti (chiave -> (campioni, samplerate)), per non rifare la
# sintesi di tutto il brano a ogni pausa/ripresa/salto: la chiave dipende
# da tutto cio' che cambia il suono (vedi PlaybackEngine.play). Pochi
# elementi: un brano di qualche minuto occupa decine di MB in memoria.
_RENDER_CACHE: "Dict[str, tuple]" = {}
_RENDER_CACHE_MAX = 3
_render_cache_lock = threading.Lock()


def _cache_get(key: Optional[str]):
    if key is None:
        return None
    with _render_cache_lock:
        entry = _RENDER_CACHE.pop(key, None)
        if entry is not None:
            _RENDER_CACHE[key] = entry  # piu' recente in fondo
        return entry


def _cache_put(key: Optional[str], entry: tuple):
    if key is None:
        return
    with _render_cache_lock:
        _RENDER_CACHE.pop(key, None)
        _RENDER_CACHE[key] = entry
        while len(_RENDER_CACHE) > _RENDER_CACHE_MAX:
            _RENDER_CACHE.pop(next(iter(_RENDER_CACHE)))


_stream_available = None


def streaming_available() -> bool:
    """True se la riproduzione passa da core.audio_stream (partenza da un
    punto qualsiasi, loop, posizione esatta): serve la libreria FluidSynth per il
    rendering, un SoundFont e un dispositivo audio per sounddevice.
    Altrimenti si usa il percorso storico (player esterno), che riparte
    sempre dall'inizio del MIDI esportato e non supporta il loop."""
    global _stream_available
    if _stream_available is None:
        _stream_available = audio_stream.is_available()
    return bool(_stream_available and _shared_synth and _find_soundfont())


def _wav_duration_seconds(path: str) -> float:
    try:
        with contextlib.closing(wave.open(path, "rb")) as w:
            rate = w.getframerate()
            return w.getnframes() / float(rate) if rate else 0.0
    except (wave.Error, OSError):
        return 0.0


def _find_audio_player():
    """Miglior comando disponibile per riprodurre un file WAV.

    Su Linux: PipeWire nativo > PulseAudio/PipeWire-pulse > ALSA > player
    generici. Su macOS 'afplay' e' presente di serie su ogni sistema (fa
    parte di macOS stesso, nessuna installazione richiesta) e viene quindi
    preferito. Su Windows nessuno di questi tool e' installato di serie: si
    usano ffplay/mpv se presenti, altrimenti si ripiega sul modulo
    'winsound' della stdlib (sempre disponibile, nessuna dipendenza
    aggiuntiva richiesta)."""
    if sys.platform == "win32":
        for cmd in ("ffplay", "mpv"):
            if shutil.which(cmd):
                if cmd == "ffplay":
                    return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]
                return ["mpv", "--no-video", "--really-quiet"]
        return _WINSOUND_MARKER if _winsound else None

    if sys.platform == "darwin":
        for cmd in ("afplay", "ffplay", "mpv"):
            if shutil.which(cmd):
                if cmd == "ffplay":
                    return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]
                if cmd == "mpv":
                    return ["mpv", "--no-video", "--really-quiet"]
                return [cmd]
        return None

    for cmd in ("pw-play", "paplay", "aplay", "ffplay", "mpv"):
        if shutil.which(cmd):
            if cmd == "ffplay":
                return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]
            if cmd == "mpv":
                return ["mpv", "--no-video", "--really-quiet"]
            return [cmd]
    return None


def _system_opener() -> Optional[str]:
    """Comando per aprire un file MIDI con l'applicazione predefinita del
    sistema, usato come ultima risorsa quando non c'e' alcun synth
    disponibile: 'xdg-open' su Linux, 'open' su macOS (entrambi presenti di
    serie). Su Windows non esiste un equivalente a riga di comando: si usa
    invece os.startfile direttamente nel chiamante."""
    if sys.platform == "win32":
        return None
    cmd = "open" if sys.platform == "darwin" else "xdg-open"
    return cmd if shutil.which(cmd) else None


def describe_playback_engine() -> str:
    """Descrizione leggibile del motore/soundfont che verra' usato, per
    mostrare trasparenza all'utente (utile per diagnosticare problemi di
    qualita' audio)."""
    if _shared_synth or shutil.which("fluidsynth"):
        soundfont, is_manual = get_active_soundfont_info()
        if soundfont:
            origin = tr("impostato manualmente") if is_manual else tr("rilevato automaticamente")
            player = _find_audio_player()
            if player is None:
                player_name = tr("nessun player WAV trovato")
            elif player == _WINSOUND_MARKER:
                player_name = "winsound (Windows)"
            else:
                player_name = player[0]
            motore = tr("fluidsynth persistente (libreria)") if _shared_synth else "fluidsynth (CLI)"
            return tr("{motore} + {soundfont} ({origin}), rendering offline, playback con {player_name}", motore=motore, soundfont=soundfont, origin=origin, player_name=player_name)
        return tr("fluidsynth trovato ma nessun SoundFont disponibile: verra' usato un fallback")
    if shutil.which("timidity"):
        return tr("timidity (fallback: fluidsynth non trovato, qualita' tipicamente inferiore)")
    if shutil.which("wildmidi"):
        return tr("wildmidi (fallback: fluidsynth non trovato, qualita' tipicamente inferiore)")
    if _system_opener() or (sys.platform == "win32" and hasattr(os, "startfile")):
        return tr("player MIDI predefinito del sistema (nessun synth dedicato trovato)")
    return tr("nessun motore di riproduzione trovato")


class PlaybackEngine:
    def __init__(self):
        self._proc = None
        self._thread = None
        self._render_tmp = None
        # Token di generazione incrementato ad ogni stop()/play_file(): un
        # thread di rendering/riproduzione in corso confronta il token
        # catturato al proprio avvio con quello corrente e si interrompe se
        # non coincidono piu'. Sostituisce un precedente flag booleano
        # (_stop_requested) che soffriva di una race quando play_file()
        # veniva richiamato molto ravvicinato (es. trascinando uno slider
        # volume/pan): stop() lo metteva a True, ma il play_file() successivo
        # lo azzerava subito a False PRIMA che il thread vecchio, ancora in
        # esecuzione, riuscisse a leggerlo — "annullando" involontariamente
        # la richiesta di stop e lasciandolo proseguire fino in fondo con
        # impostazioni ormai superate (volume sbagliato, note doppie). Un
        # token che cresce sempre e non viene mai resettato non puo' soffrire
        # di questa race: una volta superato, un thread vecchio resta
        # per sempre "non piu' valido".
        self._play_token = 0
        # Serializza "controllo del token + avvio del processo" (vedi
        # _spawn in play_file) con stop(): senza, uno stop() arrivato fra il
        # controllo del token e il Popen lasciava partire comunque l'audio
        # del thread vecchio, fuori dal controllo di Stop.
        self._proc_lock = threading.Lock()
        self._rendering = False
        self._using_winsound = False
        self._win_proc_handle = None
        self._pcm_player = None   # audio_stream.PcmPlayer in corso, se in streaming

    def position_seconds(self) -> Optional[float]:
        """Secondi (dall'inizio del brano) di cio' che si sta ascoltando
        adesso, letti dal clock del driver audio: None se la riproduzione
        non passa da core.audio_stream (il chiamante usa allora il proprio
        cronometro, vedi on_audio_started)."""
        player = self._pcm_player
        if player is None or not player.is_active():
            return None
        return player.position_frames() / float(player.samplerate)

    def set_loop_seconds(self, loop: Optional[tuple]):
        """Cambia al volo la sezione in loop (inizio, fine) in secondi, o la
        toglie con None, senza interrompere la riproduzione in corso. No-op
        se non si e' in streaming."""
        player = self._pcm_player
        if player is not None:
            player.set_loop(None if loop is None else
                            (loop[0] * player.samplerate, loop[1] * player.samplerate))

    def is_playing(self) -> bool:
        # self._proc copre i backend a subprocess (CLI fluidsynth/timidity/
        # wildmidi/player WAV esterno); self._using_winsound e
        # self._win_proc_handle coprono invece i due fallback che NON girano
        # come subprocess tracciato in self._proc (vedi play_file): senza
        # includerli qui, is_playing() risultava False mentre l'audio era
        # ancora effettivamente in corso su Windows senza un player CLI
        # installato (winsound) o senza alcun synth (player MIDI di sistema).
        player = self._pcm_player
        return (self._rendering or self._using_winsound
                or (player is not None and player.is_active())
                or self._win_proc_handle is not None
                or (self._proc is not None and self._proc.poll() is None))

    def play(self, project: Project, on_finished=None, only_audible: bool = True,
             start_offset_beats: float = 0.0, on_audio_started=None,
             humanize: bool = False, humanize_amount: int = 50,
             loop_beats: Optional[tuple] = None):
        """Riproduce il progetto da start_offset_beats.

        In streaming (vedi streaming_available) si esporta e renderizza
        SEMPRE l'intero brano, una volta sola per ogni suo stato diverso
        (cache: pausa/ripresa, salto e cambio del loop sono istantanei, solo
        una modifica che cambia il suono richiede un nuovo rendering), e si
        comincia ad ascoltarlo dal punto richiesto. loop_beats (inizio, fine)
        ripete quella sezione finche' non si ferma la riproduzione; ignorato
        fuori dallo streaming."""
        from .audio_tracks import build_audio_layers, layers_signature
        from .effect_render import fx_tracks, master_chain, master_signature, prepare_stem
        from .tempo_map import build_tempo_beat_map, seconds_for_beats

        tracks = project.audible_tracks() if only_audible else project.tracks
        # Catena del master (solo per il brano cosi' come si sente).
        master = master_chain(project) if only_audible else []
        tempo_map = build_tempo_beat_map(project, tracks=tracks)
        # Le tracce con una catena di effetti si renderizzano a parte (vedi
        # core.effect_render) e si sommano al resto come "stem".
        fx = fx_tracks([t for t in tracks if t.is_audio or t.text.strip()])
        fx_ids = {id(t) for t in fx}
        plain = [t for t in tracks if id(t) not in fx_ids]
        midi_subset = plain if fx else None
        channel_overrides = _resolve_channel_soundfont_overrides(project, only_audible, tracks=midi_subset)
        stems = [prepare_stem(project, t, tempo_map) for t in fx]
        midi_tmp = tempfile.NamedTemporaryFile(suffix=".mid", delete=False)
        midi_tmp.close()
        if not streaming_available():
            export_project_to_midi(project, midi_tmp.name, only_audible=only_audible, tracks=midi_subset,
                                    start_offset_beats=start_offset_beats,
                                    humanize=humanize, humanize_amount=humanize_amount)
            # Il MIDI parte gia' da start_offset_beats: le clip audio (e le
            # tracce con effetti) vanno spostate indietro dello stesso tanto.
            offset_seconds = seconds_for_beats(tempo_map, start_offset_beats)
            audio_layers = build_audio_layers(project, plain, tempo_map, offset_seconds=offset_seconds)
            return self.play_file(midi_tmp.name, on_finished=on_finished, delete_after=True,
                                   on_audio_started=on_audio_started, channel_overrides=channel_overrides,
                                   audio_layers=audio_layers, reverb_room=project.reverb_room,
                                   stems=stems, stems_offset=offset_seconds,
                                   master_effects=master, master_bpm=project.tempo_bpm)

        from .settings import get_playback_gain

        # Chiave della cache: il MIDI SENZA umanizzazione (che e' casuale a
        # ogni export) descrive esattamente il contenuto musicale; si
        # aggiungono le impostazioni di umanizzazione e cio' che cambia il
        # suono senza stare nel MIDI (SoundFont, override, gain).
        export_project_to_midi(project, midi_tmp.name, only_audible=only_audible, tracks=midi_subset)
        with open(midi_tmp.name, "rb") as f:
            digest = hashlib.sha1(f.read())
        digest.update(repr((humanize, humanize_amount if humanize else None, _find_soundfont(),
                            sorted((channel_overrides or {}).items()), get_playback_gain(),
                            project.reverb_room)).encode())
        audio_layers = build_audio_layers(project, plain, tempo_map)
        if audio_layers:
            digest.update(layers_signature(audio_layers).encode())
        for stem in stems:
            digest.update(stem.wet_key.encode())
        if humanize:
            export_project_to_midi(project, midi_tmp.name, only_audible=only_audible, tracks=midi_subset,
                                    humanize=True, humanize_amount=humanize_amount)

        start_seconds = seconds_for_beats(tempo_map, start_offset_beats)
        loop_seconds = None
        if loop_beats is not None:
            loop_seconds = (seconds_for_beats(tempo_map, loop_beats[0]),
                            seconds_for_beats(tempo_map, loop_beats[1]))
            if start_seconds >= loop_seconds[1]:
                start_seconds = loop_seconds[0]  # oltre la fine del loop: si riparte dal suo inizio
        # Due chiavi: il mix prima del master e il risultato finale. Cambiando
        # solo il master si rielabora il mix gia' pronto, senza risintetizzare.
        pre_master_key = digest.hexdigest()
        cache_key = pre_master_key + ("|master" + master_signature(project) if master else "")
        return self.play_file(midi_tmp.name, on_finished=on_finished, delete_after=True,
                               on_audio_started=on_audio_started, channel_overrides=channel_overrides,
                               start_seconds=start_seconds, loop_seconds=loop_seconds,
                               cache_key=cache_key, audio_layers=audio_layers,
                               reverb_room=project.reverb_room, stems=stems,
                               master_effects=master, master_bpm=project.tempo_bpm,
                               pre_master_key=pre_master_key if master else None)

    def play_file(self, midi_path: str, on_finished=None, delete_after: bool = False,
                  on_audio_started=None, channel_overrides: Optional[Dict[int, str]] = None,
                  start_seconds: float = 0.0, loop_seconds: Optional[tuple] = None,
                  cache_key: Optional[str] = None, audio_layers=None,
                  reverb_room: Optional[str] = None, stems=None, stems_offset: float = 0.0,
                  master_effects=None, master_bpm: float = 120.0, pre_master_key: Optional[str] = None):
        """Riproduce direttamente un file MIDI gia' pronto su disco (usato
        anche per l'anteprima di pattern e file della libreria MIDI).

        channel_overrides mappa canale MIDI -> percorso SoundFont per gli
        strumenti con un override (vedi core.settings.get_instrument_soundfont),
        gia' risolto dal chiamante (play(), che ha accesso al Project e quindi
        sa quale strumento suona su ciascun canale): chi chiama play_file()
        direttamente con un MIDI "grezzo" (anteprima libreria/pattern, senza
        un Project associato) non puo' fornirlo, e la riproduzione usa allora
        un unico SoundFont per tutti i canali come prima. Effettivo solo sul
        motore fluidsynth persistente (libreria): la CLI fluidsynth e gli
        altri fallback non supportano l'instradamento per canale, quindi
        ignorano questo parametro e usano comunque un solo SoundFont.

        on_audio_started, se fornito, viene chiamato (dal thread di
        riproduzione) esattamente nel momento in cui il processo audio viene
        avviato, cioe' quando il suono comincia DAVVERO — non quando play()
        e' stato chiamato. E' fondamentale per sincronizzare correttamente
        una barra di avanzamento o un'evidenziazione a tempo con l'audio
        reale: l'esportazione MIDI e il rendering offline (che possono
        richiedere anche centinaia di millisecondi) avvengono PRIMA che
        l'audio inizi, quindi calcolare il tempo trascorso da 'play()' invece
        che dall'inizio reale del suono produce una desincronizzazione
        sistematica (tutto risulta "in anticipo" rispetto a cio' che si
        sente).

        start_seconds/loop_seconds/cache_key valgono solo in streaming (vedi
        play e streaming_available): punto di partenza, sezione in loop e
        chiave con cui riusare/memorizzare il rendering di midi_path.

        audio_layers (core.audio_tracks.AudioLayer) sono le clip delle
        tracce audio da mixare sopra al rendering prima di ascoltarlo: vale
        per i percorsi che renderizzano un WAV (fluidsynth), non per i
        player MIDI esterni. Lo stesso per master_effects, la catena del
        master applicata al mix finale; in streaming il mix prima del
        master resta in cache sotto pre_master_key."""
        self.stop()
        with self._proc_lock:
            self._play_token += 1
            my_token = self._play_token

        fluidsynth_bin = shutil.which("fluidsynth")
        soundfont = _find_soundfont() if (fluidsynth_bin or _shared_synth) else None

        def _spawn(cmd, **kwargs):
            """Avvia cmd come self._proc, ma solo se questa riproduzione non
            e' stata nel frattempo fermata o sostituita (None altrimenti):
            controllo e avvio sono atomici rispetto a stop()."""
            with self._proc_lock:
                if self._play_token != my_token:
                    return None
                proc = subprocess.Popen(cmd, **kwargs)
                self._proc = proc
                return proc

        def _start(cmd, **kwargs):
            proc = _spawn(cmd, **kwargs)
            if proc is not None and on_audio_started:
                on_audio_started()
            return proc

        def _run(cmd, **kwargs):
            proc = _start(cmd, **kwargs)
            if proc is not None:
                proc.wait()

        def _stream_samples(entry) -> bool:
            """Riproduce (bloccante) campioni gia' renderizzati con
            core.audio_stream. False se lo stream non si apre (si ripiega
            allora sul player esterno)."""
            samples, rate = entry
            player = audio_stream.PcmPlayer(samples, rate)
            player.set_loop(None if loop_seconds is None else
                            (loop_seconds[0] * rate, loop_seconds[1] * rate))
            with self._proc_lock:
                if self._play_token != my_token:
                    return True
                try:
                    player.start(start_seconds * rate)
                except Exception:
                    log.warning("Stream audio non avviabile: si usa il player esterno", exc_info=True)
                    return False
                self._pcm_player = player
            if on_audio_started:
                on_audio_started()
            player.wait()
            return True

        def _add_audio_layers(wav_path):
            """Mixa le clip audio e le tracce con effetti (renderizzate ed
            elaborate ora, o prese dalla cache: vedi core.effect_render) nel
            WAV appena renderizzato (anche vuoto, per un brano di sole
            tracce audio)."""
            if not (audio_layers or stems) or not os.path.exists(wav_path):
                return
            try:
                from .audio_tracks import mix_layers_into_wav
                from .effect_render import render_stem
                stem_samples = []
                for stem in stems or []:
                    samples = render_stem(stem, lambda: self._play_token != my_token)
                    if samples is not None:
                        stem_samples.append((samples, -stems_offset))
                if self._play_token != my_token:
                    return
                mix_layers_into_wav(wav_path, audio_layers or [], stems=stem_samples)
            except RuntimeError:
                return   # interrotta
            except Exception:
                log.warning("Mix delle tracce audio non riuscito", exc_info=True)

        def _with_master(entry):
            """Il mix (int16) con la catena del master; il mix di partenza
            resta in cache per i ritocchi successivi del solo master."""
            if not master_effects:
                return entry
            from .effect_render import apply_master_int16
            _cache_put(pre_master_key, entry)
            try:
                return apply_master_int16(entry, master_effects, master_bpm)
            except Exception:
                log.warning("Catena del master non applicata", exc_info=True)
                return entry

        def _play_rendered(wav_path) -> bool:
            """Riproduce un WAV appena renderizzato: in streaming se
            possibile (memorizzandolo in cache), altrimenti col player
            esterno. False se non c'e' modo di riprodurlo."""
            if audio_stream.is_available():
                try:
                    entry = audio_stream.load_wav_samples(wav_path)
                except Exception:
                    log.warning("WAV renderizzato non leggibile: %s", wav_path, exc_info=True)
                    entry = None
                if entry is not None:
                    entry = _with_master(entry)
                    if self._play_token != my_token:
                        return True
                    _cache_put(cache_key, entry)
                    if _stream_samples(entry):
                        return True
            player_cmd = _find_audio_player()
            if player_cmd:
                if master_effects:
                    try:
                        from .audio_tracks import mix_layers_into_wav
                        from .effect_render import apply_master
                        mix_layers_into_wav(wav_path, [], post=lambda x, rate: apply_master(
                            x, rate, master_effects, master_bpm))
                    except Exception:
                        log.warning("Catena del master non applicata", exc_info=True)
                _play_wav(player_cmd, wav_path)
                return True
            return False

        def _play_wav(player_cmd, wav_path):
            """Riproduce wav_path in modo bloccante. Gestisce anche il caso
            speciale 'winsound' (Windows senza player CLI installato): non e'
            un subprocess, quindi non passa da _start/self._proc, ma da
            self._using_winsound (usato da stop() per interromperlo)."""
            if player_cmd == _WINSOUND_MARKER:
                with self._proc_lock:
                    if self._play_token != my_token:
                        return
                    self._using_winsound = True
                if on_audio_started:
                    on_audio_started()
                try:
                    # SND_ASYNC e' essenziale: senza, PlaySound() e' sincrona
                    # e blocca il thread chiamante fino alla fine naturale
                    # del WAV. winmm serializza le chiamate PlaySound dello
                    # stesso processo, quindi il PlaySound(None, SND_PURGE)
                    # di stop() (chiamato dal thread GUI) resterebbe A SUA
                    # VOLTA bloccato finche' quella sincrona non termina da
                    # sola — cioe' per l'intera durata del brano: il
                    # pulsante Stop (e con esso l'intera GUI, che gira sullo
                    # stesso thread) resterebbe congelato fino alla fine del
                    # brano. Con SND_ASYNC la
                    # chiamata torna subito e l'attesa del completamento (per
                    # sapere quando il brano e' finito da solo) si fa qui con
                    # un semplice polling sul token di generazione, che stop()
                    # puo' interrompere in qualunque momento.
                    _winsound.PlaySound(wav_path, _winsound.SND_FILENAME | _winsound.SND_ASYNC)
                    deadline = time.monotonic() + _wav_duration_seconds(wav_path)
                    while time.monotonic() < deadline and self._play_token == my_token:
                        time.sleep(0.05)
                finally:
                    _winsound.PlaySound(None, _winsound.SND_PURGE)
                    self._using_winsound = False
                return
            _run(player_cmd + [wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        def run():
            wav_path = None
            try:
                cached = _cache_get(cache_key)
                if cached is None and master_effects:
                    # Cambiato solo il master: si rielabora il mix gia' pronto.
                    before = _cache_get(pre_master_key)
                    if before is not None:
                        cached = _with_master(before)
                        _cache_put(cache_key, cached)
                if cached is not None and _stream_samples(cached):
                    return
                if _shared_synth and soundfont:
                    wav_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
                    self._render_tmp = wav_path
                    self._rendering = True
                    try:
                        rendered = _shared_synth.render_to_wav(
                            midi_path, wav_path, soundfont,
                            lambda: self._play_token != my_token,
                            channel_overrides=channel_overrides, reverb_room=reverb_room)
                    finally:
                        self._rendering = False
                    if self._play_token != my_token:
                        return
                    if rendered:
                        _add_audio_layers(wav_path)
                    if rendered and os.path.exists(wav_path) and os.path.getsize(wav_path) > 44:
                        if _play_rendered(wav_path):
                            return
                    # sintesi persistente non disponibile/fallita: ripiega sul
                    # binario CLI (se presente) o oltre, come prima

                if fluidsynth_bin and soundfont:
                    from .settings import get_playback_gain
                    gain = get_playback_gain()
                    wav_path = wav_path or tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
                    self._render_tmp = wav_path
                    render_cmd = [
                        fluidsynth_bin, "-ni",
                        "-r", "48000",             # sample rate
                        "-g", str(gain),             # gain (default fluidsynth e' spesso 0.2, molto basso)
                        "-o", "synth.reverb.active=1",
                        "-o", "synth.chorus.active=1",
                        *reverb_cli_options(reverb_room or DEFAULT_REVERB_ROOM),
                        "-o", f"synth.gain={gain}",
                        "-F", wav_path,
                        soundfont, midi_path,
                    ]
                    # Popen (non subprocess.run) e assegnato a self._proc: per
                    # un brano lungo/complesso il rendering offline puo'
                    # richiedere diversi secondi, e senza un riferimento
                    # interrompibile stop() non avrebbe alcun processo su cui
                    # agire finche' il rendering non termina da solo.
                    render_proc = _spawn(render_cmd, stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL)
                    if render_proc is None:
                        return
                    returncode = render_proc.wait()
                    if self._play_token != my_token:
                        return
                    if returncode == 0:
                        _add_audio_layers(wav_path)
                    if returncode == 0 and os.path.exists(wav_path) and os.path.getsize(wav_path) > 44:
                        if _play_rendered(wav_path):
                            return
                    if self._play_token != my_token:
                        return
                    # rendering offline fallito: ripiega sulla riproduzione fluidsynth in tempo reale
                    _run([fluidsynth_bin, "-ni", "-g", str(gain), soundfont, midi_path],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return

                if shutil.which("timidity"):
                    _run(["timidity", midi_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return
                if shutil.which("wildmidi"):
                    _run(["wildmidi", midi_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return
                opener = _system_opener()
                if opener:
                    _run([opener, midi_path])
                    return
                if sys.platform == "win32":
                    handle = _win_launch_default_app(midi_path)
                    if handle:
                        self._win_proc_handle = handle
                        if self._play_token != my_token:
                            _win_terminate_process(handle)
                            self._win_proc_handle = None
                            return
                        if on_audio_started:
                            on_audio_started()
                        _win_wait_process(handle)
                        if self._win_proc_handle is not None:
                            # Terminato da solo (non tramite stop(), che
                            # azzera il riferimento prima di chiudere
                            # l'handle): va comunque chiuso qui.
                            ctypes.windll.kernel32.CloseHandle(handle)
                            self._win_proc_handle = None
                        return
                    if hasattr(os, "startfile"):
                        # ShellExecuteEx non disponibile per qualche motivo:
                        # ultima spiaggia, non interrompibile.
                        os.startfile(midi_path)
            finally:
                if wav_path and os.path.exists(wav_path):
                    try:
                        os.remove(wav_path)
                    except OSError:
                        pass
                if delete_after and os.path.exists(midi_path):
                    try:
                        os.remove(midi_path)
                    except OSError:
                        pass
                for stem in stems or []:
                    stem.cleanup()
                if on_finished:
                    on_finished(self.backend_available())

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
        return self.backend_available()

    def play_loop_buffer(self, samples, samplerate: int, on_audio_started=None) -> bool:
        """Suona in loop, finche' non si chiama stop(), i campioni gia' pronti
        'samples' (float32 (frame, 2)): il loop di calibrazione del pannello
        Effetti (vedi core.effect_render.CalibrationSession). False se lo
        streaming audio non e' disponibile."""
        import numpy as np
        self.stop()
        if not audio_stream.is_available() or len(samples) == 0:
            return False
        pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
        player = audio_stream.PcmPlayer(pcm, samplerate)
        player.set_loop((0, len(pcm)))
        with self._proc_lock:
            try:
                player.start(0)
            except Exception:
                log.warning("Stream audio non avviabile per il loop di calibrazione", exc_info=True)
                return False
            self._pcm_player = player
        if on_audio_started:
            on_audio_started()
        return True

    def update_loop_buffer(self, samples) -> bool:
        """Nuovo contenuto per il loop di play_loop_buffer, dal prossimo giro."""
        import numpy as np
        player = self._pcm_player
        if player is None:
            return False
        player.queue_loop_update((np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16))
        return True

    def stop(self):
        with self._proc_lock:
            self._play_token += 1
            if self._proc and self._proc.poll() is None:
                self._proc.terminate()
            self._proc = None
            player, self._pcm_player = self._pcm_player, None
        if player is not None:
            player.stop()
        if self._using_winsound and _winsound:
            # PlaySound(None, SND_PURGE) interrompe la riproduzione in corso
            # avviata da winsound: e' l'unico modo di fermarla, dato che (a
            # differenza dei player CLI) non gira come subprocess tracciabile
            # in self._proc.
            _winsound.PlaySound(None, _winsound.SND_PURGE)
        if self._win_proc_handle:
            # Azzerato PRIMA di terminare/chiudere l'handle: il thread di
            # run() (bloccato in _win_wait_process) lo rilegge dopo lo
            # sblocco e vede None, cosi' non prova a sua volta a chiudere lo
            # stesso handle (CloseHandle doppio su Windows e' undefined
            # behavior).
            handle = self._win_proc_handle
            self._win_proc_handle = None
            _win_terminate_process(handle)

    def backend_available(self) -> bool:
        if (_shared_synth or shutil.which("fluidsynth")) and _find_soundfont():
            return True
        if shutil.which("timidity") or shutil.which("wildmidi"):
            return True
        if _system_opener():
            return True
        return sys.platform == "win32" and hasattr(os, "startfile")
