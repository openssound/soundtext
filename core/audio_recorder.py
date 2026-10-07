"""
Registrazione da microfono (funzionalita' "Registra da microfono" del
dialogo di importazione audio). Usa 'sounddevice' (binding Python di
PortAudio, richiede la libreria di sistema libportaudio2).

La cattura audio gira nel proprio thread nativo gestito da sounddevice, non
in un QThread dedicato: start()/stop() sono chiamate leggere e non
bloccanti, invocabili direttamente dal thread della GUI. Solo la successiva
pipeline di decodifica+analisi (potenzialmente lenta) va eseguita in
background (vedi gui/reorganize_worker.py), non la registrazione in se'.
"""

import os
import tempfile
import time
import wave
from typing import Optional
from .i18n import tr

SAMPLE_RATE = 44100


def is_sounddevice_available() -> bool:
    """True se sounddevice e' importabile E la libreria di sistema
    libportaudio2 e' presente (il pacchetto pip puo' essere installato ma
    fallire all'import con OSError se la libreria di sistema manca)."""
    try:
        import sounddevice  # noqa: F401
        return True
    except (ImportError, OSError):
        return False


class MicRecorder:
    """Registrazione da microfono con avvio/arresto manuale (pulsante
    Start/Stop nella GUI)."""

    def __init__(self, samplerate: int = SAMPLE_RATE):
        self.samplerate = samplerate
        self._stream = None
        self._chunks = []
        self._start_time: Optional[float] = None

    @property
    def is_recording(self) -> bool:
        return self._stream is not None

    @property
    def elapsed_seconds(self) -> float:
        return time.monotonic() - self._start_time if self._start_time else 0.0

    def _callback(self, indata, frames, time_info, status):
        self._chunks.append(indata.copy())

    def start(self):
        import sounddevice as sd

        if self.is_recording:
            return
        self._chunks = []
        self._start_time = time.monotonic()
        self._stream = sd.InputStream(
            samplerate=self.samplerate, channels=1, dtype="int16",
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> str:
        """Ferma la registrazione e scrive un WAV temporaneo mono a
        44100 Hz / 16-bit (stesso formato normalizzato prodotto da
        core.audio_decode.decode_audio_file_to_wav), ritornandone il
        percorso. Il chiamante e' responsabile di eliminarlo dopo l'uso."""
        import numpy as np

        if not self.is_recording:
            raise RuntimeError(tr("Nessuna registrazione in corso."))
        self._stream.stop()
        self._stream.close()
        self._stream = None
        self._start_time = None

        if self._chunks:
            data = np.concatenate(self._chunks, axis=0)
        else:
            data = np.zeros((0, 1), dtype="int16")
        self._chunks = []

        fd, path = tempfile.mkstemp(suffix=".wav", prefix="soundtext_mic_")
        os.close(fd)
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.samplerate)
            wf.writeframes(data.tobytes())
        return path
