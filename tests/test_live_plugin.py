"""
Test dello strumento plugin suonato dal vivo nel dialogo "Suona con la
tastiera": il motore a blocchi del processo dei plugin
(core.plugin_worker._Live), core.playback.LivePluginSynth e la scelta, nel
dialogo, fra lo strumento della traccia e il SoundFont.

Esecuzione:
    python3 -m pytest tests/test_live_plugin.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

import gui.keyboard_play_dialog as kpd
from core.instruments import DRUM_MIDI_CHANNEL
from core.model import Project
from core.playback import LivePluginSynth
from core.plugin_worker import _Live
from core.sfz_engine import SfzInstance, sfz_available
from gui.keyboard_play_dialog import KeyboardPlayDialog, LIVE_MELODIC_CHANNEL

_app = QApplication.instance() or QApplication([])

RATE = 48000
needs_lib = pytest.mark.skipif(not sfz_available(), reason="libreria SFZ (sfizioso o sfizz) non trovata")


def _rms(x):
    return float(np.sqrt(np.mean(np.square(x)))) if len(x) else 0.0


def _sine_sfz(tmp_path):
    path = tmp_path / "sine.sfz"
    path.write_text("<region> sample=*sine\n")
    return str(path)


# --------------------------------------------------------------- motore a blocchi

@needs_lib
def test_live_engine_plays_the_notes_as_they_arrive(tmp_path):
    inst = SfzInstance(_sine_sfz(tmp_path), RATE)
    inst.set_realtime()
    live = _Live(inst, "sfz", RATE)
    assert _rms(live.render(256)) < 1e-6
    live.pending.append(bytes([0x90, 69, 100]))
    block = live.render(256)
    assert block.shape == (256, 2) and block.dtype == np.float32
    assert _rms(np.concatenate([live.render(256) for _ in range(20)])) > 0.05
    assert not live.pending
    live.pending.append(bytes([0x80, 69, 0]))
    tail = [live.render(256) for _ in range(200)]
    assert _rms(tail[-1]) < 1e-5
    inst.close()


@needs_lib
def test_live_engine_pans_like_the_rendering(tmp_path):
    inst = SfzInstance(_sine_sfz(tmp_path), RATE)
    live = _Live(inst, "sfz", RATE, pan=0)       # tutto a sinistra
    live.pending.append(bytes([0x90, 69, 100]))
    y = np.concatenate([live.render(256) for _ in range(10)])
    assert _rms(y[:, 0]) > 0.05 and _rms(y[:, 1]) < 1e-6
    inst.close()


# --------------------------------------------------------------- LivePluginSynth

def test_live_plugin_synth_is_none_when_the_instrument_does_not_open(tmp_path):
    assert LivePluginSynth.create("sfz:" + str(tmp_path / "manca.sfz"), {}, "") is None


def test_live_plugin_synth_sends_midi_messages(monkeypatch):
    sent = []
    monkeypatch.setattr("core.plugins.live_start",
                        lambda *a, **k: {"hostapi": "Prova", "latency_ms": 20, "session": 7})
    monkeypatch.setattr("core.plugins.live_send", lambda session, data: sent.append((session, data)) or True)
    stopped = []
    monkeypatch.setattr("core.plugins.live_stop", stopped.append)
    synth = LivePluginSynth.create("sfz:/x.sfz", {}, "")
    assert "Prova" in synth.description() and "20 ms" in synth.description()
    synth.set_program(0, 33)
    synth.note_on(0, 60, 90)
    synth.note_off(9, 36)
    synth.pitch_bend(0, 1.0)          # un semitono su +-2: leva a 3/4
    synth.pitch_bend(0, 0.0)
    assert sent == [(7, bytes([0xC0, 33])), (7, bytes([0x90, 60, 90])), (7, bytes([0x89, 36, 0])),
                    (7, bytes([0xE0, 0, 96])), (7, bytes([0xE0, 0, 64]))]
    synth.close()
    synth.note_on(0, 60)              # dopo la chiusura non manda piu' niente
    assert stopped == [7] and len(sent) == 5


def test_live_plugin_synth_goes_quiet_when_the_process_is_gone(monkeypatch):
    monkeypatch.setattr("core.plugins.live_start",
                        lambda *a, **k: {"hostapi": "Prova", "latency_ms": 20, "session": 1})
    calls = []
    monkeypatch.setattr("core.plugins.live_send", lambda session, data: calls.append(data) and False)
    synth = LivePluginSynth.create("sfz:/x.sfz", {}, "")
    synth.note_on(0, 60)
    synth.note_on(0, 62)
    assert len(calls) == 1


def test_new_live_session_silences_the_old_one(monkeypatch):
    import core.plugins as plugins
    monkeypatch.setattr(plugins, "_live_session", 3)
    assert plugins.live_send(2, bytes([0x90, 60, 100])) is False


# --------------------------------------------------------------- il dialogo

class _FakeSynth:
    def __init__(self, name="plugin"):
        self.name = name
        self.calls = []
        self.closed = False

    def description(self):
        return f"Audio: prova ({self.name})"

    def set_program(self, channel, program):
        self.calls.append(("program", channel, program))

    def note_on(self, channel, pitch, velocity=100):
        self.calls.append(("on", channel, pitch))

    def note_off(self, channel, pitch):
        self.calls.append(("off", channel, pitch))

    def pitch_bend(self, channel, semitones):
        pass

    def all_notes_off(self):
        pass

    def close(self):
        self.closed = True


def _dialog(monkeypatch, instrument="Piano", synth="sfz:/strumento.sfz", plugin_result="fake"):
    created = []

    def create(ref, params, state, pan=64):
        created.append((ref, pan))
        return _FakeSynth() if plugin_result == "fake" else None

    monkeypatch.setattr(kpd.LivePluginSynth, "create", staticmethod(create))
    monkeypatch.setattr(kpd.LiveSynth, "create", staticmethod(lambda: _FakeSynth("soundfont")))
    p = Project(name="Test")
    t = p.add_track("T1", instrument, "16: c*4")
    t.synth = synth
    t.pan = 30
    dlg = KeyboardPlayDialog(None, project=p, instrument_name=instrument, context_label="T1",
                             current_track_name="T1")
    return dlg, created


def test_dialog_plays_the_keys_with_the_track_plugin(monkeypatch):
    dlg, created = _dialog(monkeypatch)
    dlg._ensure_live_synth()
    assert dlg._live_synth.name == "plugin"
    assert created == [("sfz:/strumento.sfz", 30)]
    assert dlg._live_synth.calls[0] == ("program", LIVE_MELODIC_CHANNEL, dlg.instr.gm_program)
    assert "plugin" in dlg.latency_info_label.text()
    synth = dlg._live_synth
    dlg.reject()
    assert synth.closed


def test_dialog_drum_track_with_plugin_uses_the_drum_channel(monkeypatch):
    dlg, _created = _dialog(monkeypatch, instrument="Drums")
    dlg._ensure_live_synth()
    assert dlg._live_synth.calls[0][:2] == ("program", DRUM_MIDI_CHANNEL)
    dlg.reject()


def test_dialog_falls_back_to_the_soundfont(monkeypatch):
    dlg, _created = _dialog(monkeypatch, plugin_result=None)
    dlg._ensure_live_synth()
    assert dlg._live_synth.name == "soundfont"
    assert "SoundFont" in dlg.surface_label.text()
    dlg.reject()


def test_dialog_without_plugin_uses_the_soundfont(monkeypatch):
    dlg, created = _dialog(monkeypatch, synth="")
    dlg._ensure_live_synth()
    assert dlg._live_synth.name == "soundfont" and created == []
    dlg.reject()


def test_latency_change_reopens_the_plugin(monkeypatch):
    dlg, created = _dialog(monkeypatch)
    dlg._ensure_live_synth()
    first = dlg._live_synth
    dlg._on_latency_changed()
    assert first.closed and dlg._live_synth is None
    dlg._ensure_live_synth()
    assert dlg._live_synth is not first and len(created) == 2
    dlg.reject()


def test_plugin_loaded_after_close_is_closed(monkeypatch):
    import threading
    gate = threading.Event()
    loaded = []

    def slow_create(ref, params, state, pan=64):
        gate.wait(5)
        synth = _FakeSynth()
        loaded.append(synth)
        return synth

    dlg, _created = _dialog(monkeypatch)
    loader = dlg._plugin_loader
    loader.join(5)                        # quello del costruttore (veloce)
    dlg._close_live_synth()               # chiude quello gia' pronto
    monkeypatch.setattr(kpd.LivePluginSynth, "create", staticmethod(slow_create))
    dlg._start_plugin_loader()
    loader = dlg._plugin_loader
    dlg.reject()                          # chiuso mentre lo strumento si apre
    gate.set()
    loader.join(5)
    assert loaded and loaded[0].closed
