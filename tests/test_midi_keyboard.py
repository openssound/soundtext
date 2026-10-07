"""
Tastiera MIDI esterna nel dialogo "Suona con la tastiera" (core.midi_input,
gui.midi_keyboard). Senza hardware: le porte sono finte, i messaggi sono
veri messaggi mido passati al dialogo con l'istante di arrivo.

Esecuzione:
    python3 -m pytest tests/test_midi_keyboard.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mido
import pytest
from PySide6.QtWidgets import QApplication

from core import midi_input
from core import settings as app_settings
from core.model import Project

_app = QApplication.instance() or QApplication([])
T0 = 1000.0


class _FakePort:
    def __init__(self, name, callback):
        self.port_name = name
        self.callback = callback
        self.closed = False

    def close(self):
        self.closed = True


class _FakeLiveSynth:
    def __init__(self):
        self.on, self.off, self.bends = [], [], []

    def note_on(self, channel, pitch, velocity=100):
        self.on.append((channel, pitch, velocity))

    def note_off(self, channel, pitch):
        self.off.append((channel, pitch))

    def pitch_bend(self, channel, semitones):
        self.bends.append(semitones)

    def close(self):
        pass


@pytest.fixture
def ports(monkeypatch):
    import gui.midi_keyboard as mk
    state = {"ports": ["Tastiera USB", "Pad"], "problem": "", "opened": []}

    def fake_open(name, callback):
        port = _FakePort(name, callback)
        state["opened"].append(port)
        return port, ""

    monkeypatch.setattr(mk, "midi_input_problem", lambda: state["problem"])
    monkeypatch.setattr(mk, "list_input_ports", lambda: list(state["ports"]))
    monkeypatch.setattr(mk, "open_input", fake_open)
    return state


def _dialog(instrument="Piano"):
    from gui.keyboard_play_dialog import KeyboardPlayDialog
    p = Project(name="Test", tempo_bpm=120)
    p.add_track("T", instrument, "")
    dlg = KeyboardPlayDialog(None, project=p, instrument_name=instrument, context_label="test")
    dlg._live_synth = _FakeLiveSynth()
    dlg.grid_combo.setCurrentIndex(dlg.grid_combo.findData(16))
    dlg.ternary_check.setChecked(False)
    return dlg


def _record(dlg, messages):
    """Registra i messaggi (secondi dall'inizio, messaggio) e genera l'anteprima."""
    dlg._recording = True
    dlg._record_start_wall = T0
    for at, message in messages:
        dlg._on_midi_message(T0 + at, message)
    dlg._recording = False
    dlg._generate_preview_from_events()
    return dlg.preview_edit.toPlainText()


def _on(note, velocity=100):
    return mido.Message("note_on", note=note, velocity=velocity)


def _off(note):
    return mido.Message("note_off", note=note)


# ------------------------------------------------------------ core

def test_pitchwheel_semitones():
    assert midi_input.pitchwheel_semitones(0) == 0.0
    assert midi_input.pitchwheel_semitones(8191) == 2.0
    assert midi_input.pitchwheel_semitones(-8192) == -2.0
    assert midi_input.pitchwheel_semitones(4096) == pytest.approx(1.0, abs=1e-3)


def test_input_forwards_only_useful_messages_with_arrival_time(monkeypatch):
    opened = {}

    def fake_open_input(name, callback):
        opened["callback"] = callback
        return _FakePort(name, callback)

    monkeypatch.setattr(mido, "open_input", fake_open_input)
    received = []
    port, problem = midi_input.open_input("Tastiera", lambda t, m: received.append((t, m.type)))
    assert problem == "" and port.is_open
    for message in (_on(60), mido.Message("clock"), mido.Message("aftertouch", value=3),
                    mido.Message("control_change", control=64, value=127), mido.Message("pitchwheel", pitch=100),
                    _off(60)):
        opened["callback"](message)
    assert [kind for _, kind in received] == ["note_on", "control_change", "pitchwheel", "note_off"]
    assert all(isinstance(t, float) for t, _ in received)
    port.close()
    assert not port.is_open


def test_unavailable_midi_system_is_explained(monkeypatch):
    def broken():
        raise RuntimeError("MidiInAlsa::initialize: error creating ALSA sequencer client object.")

    monkeypatch.setattr(mido, "get_input_names", broken)
    assert "non risponde" in midi_input.midi_input_problem()
    assert midi_input.list_input_ports() == []


def test_port_that_cannot_be_opened(monkeypatch):
    def refuse(name, callback):
        raise OSError("porta occupata da un altro programma")

    monkeypatch.setattr(mido, "open_input", refuse)
    port, problem = midi_input.open_input("Tastiera", lambda t, m: None)
    assert port is None and "occupata" in problem


# ------------------------------------------------------------ dialogo

def test_first_port_is_opened_and_remembered(ports):
    dlg = _dialog()
    assert dlg.midi_combo.isEnabled() and dlg.midi_combo.count() == 3        # Nessuna + 2 porte
    assert dlg._midi_input.port_name == "Tastiera USB"
    assert app_settings.get_midi_input_port() == "Tastiera USB"
    dlg.midi_combo.setCurrentIndex(dlg.midi_combo.findData("Pad"))
    assert ports["opened"][0].closed and dlg._midi_input.port_name == "Pad"
    dlg.reject()
    assert ports["opened"][-1].closed and dlg._midi_input is None
    again = _dialog()
    assert again._midi_input.port_name == "Pad"                              # l'ultima usata
    again.reject()


def test_no_ports_and_unavailable_system(ports):
    ports["ports"] = []
    dlg = _dialog()
    assert not dlg.midi_combo.isEnabled() and dlg._midi_input is None
    assert "Nessuna tastiera" in dlg.midi_status_label.text()
    ports["ports"] = ["Tastiera USB"]
    dlg._refresh_midi_ports()                                                # collegata dopo: ⟳
    assert dlg._midi_input.port_name == "Tastiera USB"
    ports["problem"] = "manca il pacchetto Python 'python-rtmidi'"
    dlg._refresh_midi_ports()
    assert dlg._midi_input is None and "python-rtmidi" in dlg.midi_status_label.text()
    dlg.reject()


def test_notes_chords_velocity_sustain_and_bend_are_recorded(ports):
    dlg = _dialog()
    text = _record(dlg, [
        (0.0, _on(60, 100)), (0.5, _off(60)),                                 # do, semiminima
        (0.5, _on(64, 60)), (0.5, _on(67, 60)), (1.0, _off(64)), (1.0, _off(67)),   # accordo piano
        (1.0, _on(62, 100)), (1.1, mido.Message("control_change", control=64, value=127)),
        (1.2, _off(62)), (1.5, mido.Message("control_change", control=64, value=0)),  # tenuta dal pedale
        (1.5, _on(69, 100)), (1.6, mido.Message("pitchwheel", pitch=8191)), (2.0, _off(69)),  # leva: slide
        (2.0, mido.Message("pitchwheel", pitch=0)),
    ])
    assert text == "16: 100@ 4c*4 60@ 4[e*4 g*4] 100@ 4d*4 4a*4>b*4"
    synth = dlg._live_synth
    assert (0, 60, 100) in synth.on and (0, 64, 60) in synth.on                  # suono dal vivo con velocity
    assert synth.bends[:1] == [2.0]
    dlg.reject()


def test_small_bend_does_not_become_a_slide(ports):
    dlg = _dialog()
    text = _record(dlg, [(0.0, _on(60)), (0.1, mido.Message("pitchwheel", pitch=2000)), (0.5, _off(60))])
    assert text == "16: 100@ 4c*4"                                               # meno di un semitono
    dlg.reject()


def test_repeated_note_on_without_note_off(ports):
    dlg = _dialog()
    text = _record(dlg, [(0.0, _on(60)), (0.25, _on(60, 80)), (0.5, _off(60))])
    assert text == "16: 100@ 2c*4 80@ 2c*4"
    dlg.reject()


def test_drums_follow_the_general_midi_map(ports):
    dlg = _dialog("Drums")
    text = _record(dlg, [(0.0, _on(36, 110)), (0.25, _on(42, 70)), (0.5, _on(38, 110)),
                         (0.6, _on(61, 100)),                                    # fuori mappa: ignorata
                         (0.1, _off(36)), (0.35, _off(42)), (0.6, _off(38))])
    assert text == "16: 110@ kick r 70@ hihat r 110@ snare"
    dlg.reject()


def test_messages_from_the_rtmidi_thread_reach_the_dialog(ports):
    import threading
    import time
    dlg = _dialog()
    dlg._playing_live = True                                                  # "Suona"
    callback = ports["opened"][0].callback                                    # quella data a open_input
    thread = threading.Thread(target=lambda: callback(time.time(), _on(64, 90)))
    thread.start()
    thread.join()
    assert dlg._active_notes == {}                                            # non ancora: e' accodato
    for _ in range(20):
        _app.processEvents()
    assert list(dlg._active_notes) == [("midi", 64)] and (0, 64, 90) in dlg._live_synth.on
    dlg.reject()


def test_notes_are_ignored_until_record_or_play(ports):
    dlg = _dialog()
    dlg._on_midi_message(T0, _on(60))
    assert dlg._active_notes == {} and dlg._live_synth.on == []
    assert "Registra" in dlg.midi_status_label.text()
    dlg.reject()
