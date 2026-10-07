"""
Lettura di file audio di ogni formato (.wav/.mp3/.m4a/.flac/.ogg/...) per
l'importazione audio -> notazione (decode_audio_file_to_wav, che produce un
WAV temporaneo uniforme: mono, 44100 Hz, PCM 16-bit, cosi' che i moduli di
analisi ricevano sempre lo stesso formato) e per le tracce audio
(core.audio_tracks.import_audio_file).

Chi decodifica, nell'ordine:
- i WAV li legge SoundText stesso (core.audio_tracks.read_wav);
- gli altri formati il decodificatore di Qt Multimedia (QAudioDecoder):
  PySide6 lo include gia', con la sua copia di FFmpeg, quindi non serve
  installare niente; rispetta anche i silenzi aggiunti dal codificatore
  (ritardo e riempimento degli mp3 con l'intestazione LAME, "edit list"
  degli m4a), come ffmpeg;
- se Qt non c'e' o non ce la fa (un PySide6 di sistema senza il plugin
  FFmpeg, un formato raro), il programma 'ffmpeg', se installato.
Il ricampionamento e' quello di qualita' di core.audio_tracks.resample_hq.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from typing import List, Optional, Tuple

import numpy as np

from .i18n import tr

TARGET_SAMPLE_RATE = 44100
# Se il decodificatore di Qt non produce niente per cosi' tanto, si arrende
# (un file che lo blocca non deve bloccare anche l'app).
QT_STALL_TIMEOUT_MS = 30000

_qt_available: Optional[bool] = None


def is_ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


_app = None


def _qt_app():
    """L'applicazione Qt, creata se manca (script da riga di comando e
    test): QtMultimedia ne ha bisogno. Se c'e' uno schermo si crea una
    QApplication, che serve anche all'interfaccia se arriva dopo (una
    QCoreApplication non si puo' piu' sostituire)."""
    global _app
    from PySide6.QtCore import QCoreApplication
    app = QCoreApplication.instance()
    if app is None:
        has_screen = (sys.platform in ("win32", "darwin") or os.environ.get("QT_QPA_PLATFORM")
                      or os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
        if has_screen:
            from PySide6.QtWidgets import QApplication
            app = QApplication([])
        else:
            app = QCoreApplication([])
        _app = app
    return app


def is_qt_decoder_available() -> bool:
    """Il decodificatore di Qt Multimedia c'e' e sa leggere qualche formato
    (il plugin FFmpeg e' incluso in PySide6 installato con pip; un PySide6
    di sistema potrebbe non averlo)."""
    global _qt_available
    if _qt_available is None:
        try:
            _qt_app()
            from PySide6.QtMultimedia import QAudioDecoder, QMediaFormat  # noqa: F401
            codecs = QMediaFormat().supportedAudioCodecs(QMediaFormat.ConversionMode.Decode)
            _qt_available = bool(codecs)
        except Exception:
            _qt_available = False
    return _qt_available


def can_decode_compressed_audio() -> bool:
    """Si possono leggere mp3/m4a/flac/ogg (con Qt o con ffmpeg)."""
    return is_qt_decoder_available() or is_ffmpeg_available()


def decoder_description() -> str:
    """Chi decodifica i formati compressi, per la finestra Informazioni."""
    if is_qt_decoder_available():
        return tr("Qt Multimedia (FFmpeg incluso)")
    if is_ffmpeg_available():
        return "ffmpeg"
    return ""


def _decode_with_qt(path: str) -> Tuple[np.ndarray, int]:
    from PySide6.QtCore import QEventLoop, QTimer, QUrl
    from PySide6.QtMultimedia import QAudioDecoder, QAudioFormat

    _qt_app()
    decoder = QAudioDecoder()
    # Il formato d'uscita e' quello del file (Qt ignora una richiesta senza
    # frequenza): si convertono tutti i formati di campione possibili.
    sample = QAudioFormat.SampleFormat
    formats = {sample.Float: (np.float32, 0.0, 1.0), sample.Int16: (np.int16, 0.0, 32768.0),
               sample.Int32: (np.int32, 0.0, 2147483648.0), sample.UInt8: (np.uint8, 128.0, 128.0)}
    loop = QEventLoop()
    chunks: List[np.ndarray] = []
    state = {"done": False, "error": "", "rate": 0, "channels": 0, "fresh": False}

    def read_buffers():
        while decoder.bufferAvailable():
            buf = decoder.read()
            if not buf.isValid():
                continue
            fmt = buf.format()
            state["rate"], state["channels"] = fmt.sampleRate(), fmt.channelCount()
            state["fresh"] = True
            kind = formats.get(fmt.sampleFormat())
            if kind is None:
                state["error"] = tr("formato dei campioni non gestito")
                continue
            dtype, offset, scale = kind
            data = np.frombuffer(bytes(buf.constData()), dtype=dtype).astype(np.float32)
            chunks.append((data - offset) / scale if scale != 1.0 or offset else data)

    def finish():
        state["done"] = True
        loop.quit()

    def failed(*_args):
        state["error"] = decoder.errorString() or tr("errore sconosciuto")
        finish()

    def watchdog():
        if not state["fresh"]:
            state["error"] = tr("la decodifica non procede")
            finish()
        state["fresh"] = False

    decoder.bufferReady.connect(read_buffers)
    decoder.finished.connect(finish)
    decoder.error.connect(failed)
    timer = QTimer()
    timer.setInterval(QT_STALL_TIMEOUT_MS)
    timer.timeout.connect(watchdog)
    decoder.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
    decoder.start()
    # un file che non si apre da' l'errore gia' dentro start(), prima del ciclo
    if not state["done"]:
        timer.start()
        loop.exec()
    timer.stop()
    decoder.stop()
    read_buffers()
    if state["error"]:
        raise RuntimeError(state["error"])
    if not chunks or state["channels"] <= 0 or state["rate"] <= 0:
        raise RuntimeError(tr("nessun audio nel file"))
    samples = np.concatenate(chunks)
    channels = state["channels"]
    samples = samples[:len(samples) // channels * channels].reshape(-1, channels)
    return samples, int(state["rate"])


def _decode_with_ffmpeg(path: str) -> Tuple[np.ndarray, int]:
    from .audio_tracks import read_wav

    fd, tmp = tempfile.mkstemp(suffix=".wav", prefix="soundtext_decode_")
    os.close(fd)
    try:
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", path, "-vn", "-c:a", "pcm_f32le", tmp]
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.decode(errors="replace")[-300:].strip() or "ffmpeg")
        return read_wav(tmp)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def read_audio(path: str) -> Tuple[np.ndarray, int]:
    """Campioni float32 di forma (frame, canali) e frequenza di un file
    audio di qualunque formato leggibile (vedi il commento del modulo).
    Solleva RuntimeError con un messaggio leggibile se non si puo'."""
    from .audio_tracks import read_wav

    if not os.path.isfile(path):
        raise RuntimeError(tr("File audio non trovato: '{input_path}'", input_path=path))
    if os.path.splitext(path)[1].lower() in (".wav", ".wave"):
        try:
            return read_wav(path)
        except (ValueError, OSError, EOFError):
            pass            # WAV compresso o insolito: ci provano i decodificatori
    problems = []
    if is_qt_decoder_available():
        try:
            return _decode_with_qt(path)
        except RuntimeError as exc:
            problems.append(str(exc))
    if is_ffmpeg_available():
        try:
            return _decode_with_ffmpeg(path)
        except RuntimeError as exc:
            problems.append(str(exc))
    name = os.path.basename(path)
    if not problems:
        raise RuntimeError(tr(
            "Non posso leggere '{0}': manca un decodificatore audio. Il PySide6 in uso non ha "
            "il decodificatore di Qt Multimedia: installa PySide6 con pip (lo include) oppure "
            "ffmpeg, o converti prima il file in WAV.", name))
    raise RuntimeError(tr("Non riesco a leggere '{0}': {1}", name, problems[-1]))


def decode_audio_file_to_wav(input_path: str) -> str:
    """Decodifica un file audio qualunque (mp3/m4a/wav/...) in un WAV
    temporaneo mono a 44100 Hz / 16-bit PCM. Il chiamante e' responsabile di
    eliminare il file ritornato dopo l'uso. Solleva RuntimeError se il file
    non si puo' leggere."""
    from .audio_tracks import resample_hq, write_wav

    samples, rate = read_audio(input_path)
    mono = samples.mean(axis=1, keepdims=True, dtype=np.float32)
    mono = resample_hq(mono, rate, TARGET_SAMPLE_RATE)
    fd, out_path = tempfile.mkstemp(suffix=".wav", prefix="soundtext_audio_")
    os.close(fd)
    try:
        write_wav(out_path, mono, TARGET_SAMPLE_RATE, bits=16)
    except Exception:
        os.remove(out_path)
        raise
    return out_path
