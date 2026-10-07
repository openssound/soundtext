"""
Ingresso da tastiera MIDI esterna (USB o interfaccia MIDI), per il dialogo
"Suona con la tastiera" (gui.keyboard_play_dialog).

Usa mido con il backend python-rtmidi (ALSA/JACK su Linux, CoreMIDI su
macOS, Windows MM su Windows). Nessuna dipendenza da Qt: i messaggi
arrivano nel thread di rtmidi con l'istante di arrivo (time.time(), preso
subito, cosi' il ritardo con cui la GUI li elabora non sposta le note
registrate) e vengono passati a una callback; e' il chiamante a riportarli
nel thread della GUI (vedi gui.midi_keyboard).
"""

import time
from typing import Callable, List, Optional, Tuple
from .i18n import tr

# Messaggi usati: note_on/note_off, pedale del sustain (control_change 64) e
# leva del pitch bend (pitchwheel). Il resto (clock, aftertouch, sysex...)
# si scarta subito nel thread di rtmidi.
SUSTAIN_CC = 64
HANDLED_TYPES = ("note_on", "note_off", "control_change", "pitchwheel")


def midi_input_problem() -> str:
    """'' se si possono usare tastiere MIDI, altrimenti il motivo."""
    try:
        import mido
        import rtmidi  # noqa: F401  (backend di mido)
    except ImportError:
        return tr("manca il pacchetto Python 'python-rtmidi' (pip install python-rtmidi)")
    try:
        mido.get_input_names()
    except Exception as e:                      # es. Linux senza sequencer ALSA
        return tr("il sistema MIDI non risponde ({__name__}: {e})", __name__=e.__class__.__name__, e=e)
    return ""


def list_input_ports() -> List[str]:
    """Nomi delle porte MIDI d'ingresso (tastiere collegate); [] se nessuna o
    se il sistema MIDI non e' disponibile."""
    try:
        import mido
        return list(dict.fromkeys(mido.get_input_names()))
    except Exception:
        return []


class MidiInput:
    """Una porta MIDI d'ingresso aperta. callback(istante, messaggio) viene
    chiamata nel thread di rtmidi per ogni messaggio utile."""

    def __init__(self, port_name: str, callback: Callable[[float, object], None]):
        import mido
        self.port_name = port_name
        self._callback = callback
        self._port = mido.open_input(port_name, callback=self._on_message)

    def _on_message(self, message):
        if message.type in HANDLED_TYPES:
            self._callback(time.time(), message)

    def close(self):
        if self._port is not None:
            try:
                self._port.close()
            except Exception:
                pass
            self._port = None

    @property
    def is_open(self) -> bool:
        return self._port is not None


def open_input(port_name: str, callback: Callable[[float, object], None]) -> Tuple[Optional[MidiInput], str]:
    """(porta aperta, '') oppure (None, motivo)."""
    try:
        return MidiInput(port_name, callback), ""
    except Exception as e:
        return None, f"{e.__class__.__name__}: {e}"


def pitchwheel_semitones(pitch: int, bend_range: float = 2.0) -> float:
    """Valore della leva (-8192..8191) in semitoni, con l'escursione
    standard di +/- 2 semitoni."""
    return bend_range * pitch / (8192.0 if pitch < 0 else 8191.0)
