"""
Test GUI (offscreen) del dialogo "Registra nella traccia audio"
(gui.audio_record_dialog) con una scheda audio simulata: scelte di
ingresso, misuratore, registrazione/stop/tieni e clip aggiunta alla traccia.

Esecuzione:
    python3 -m pytest tests/test_audio_record_dialog_gui.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys
from types import SimpleNamespace

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from core import settings
from core.audio_recording import Backing, ClickSchedule, InputDevice
from core.audio_tracks import AUDIO_SAMPLE_RATE, read_wav_info
from core.model import AudioClip, Project
from gui.audio_record_dialog import AudioRecordDialog
from gui.main_window import MainWindow

_app = QApplication.instance() or QApplication([])
RATE = AUDIO_SAMPLE_RATE

DEVICES = [InputDevice(3, "Scarlett 2i2", "ALSA", 0, 2, RATE),
           InputDevice(5, "Microfono USB", "ALSA", 0, 1, RATE)]


class FakeDuplex:
    """Ingresso: una sinusoide sul canale 2 (la chitarra), niente sull'1."""

    def __init__(self, callback, rate, in_channels, input_device, output_device):
        self.callback, self.rate, self.in_channels = callback, rate, in_channels
        self.opened_with = (input_device, output_device, in_channels)
        self.now = 10.0

    def start(self):
        pass

    def pump(self, blocks, n=480):
        for _ in range(blocks):
            indata = np.zeros((n, self.in_channels), np.float32)
            indata[:, -1] = 0.25
            outdata = np.zeros((n, 2), np.float32)
            t = SimpleNamespace(outputBufferDacTime=self.now + 0.005, inputBufferAdcTime=self.now - 0.003)
            self.callback(indata, outdata, n, t, None)
            self.now += n / float(self.rate)

    def stop(self):
        pass

    def close(self):
        pass


class FakeMonitorStream:
    def __init__(self, callback, in_channels, device):
        self.callback, self.in_channels, self.device = callback, in_channels, device
        self.stopped = False

    def start(self):
        data = np.zeros((32, self.in_channels), np.float32)
        data[0, :] = 0.5
        self.callback(data, 32, None, None)

    def stop(self):
        self.stopped = True

    def close(self):
        pass


def _backing(project, start_beat, count_in_bars, with_metronome, mute_track=None):
    silent = ClickSchedule([], np.zeros(4, np.float32), np.zeros(4, np.float32), 0.0, RATE)
    count_in = 2.0 * count_in_bars
    return Backing(np.zeros((int(count_in * RATE) + RATE, 2), np.float32), RATE, silent, count_in)


def _dialog(tmp_path, track_profile="", track_channels="", options=(("Inizio del brano", 0.0),)):
    p = Project(tempo_bpm=120)
    t = p.add_audio_track("Chitarra")
    t.input_profile, t.input_channels = track_profile, track_channels
    streams = {}

    def duplex_factory(*args):
        streams["duplex"] = FakeDuplex(*args)
        return streams["duplex"]

    def monitor_factory(*args):
        streams["monitor"] = FakeMonitorStream(*args)
        return streams["monitor"]

    dlg = AudioRecordDialog(None, p, t, list(options), str(tmp_path), stream_factory=duplex_factory,
                            monitor_factory=monitor_factory, backing_builder=_backing,
                            run_in_thread=False, devices=DEVICES)
    return dlg, t, streams


def test_dialog_restores_track_input_and_suggests_channels_by_profile(tmp_path):
    dlg, _t, streams = _dialog(tmp_path, track_profile="tastiera", track_channels="2")
    assert dlg.input_profile() == "tastiera"
    assert dlg.input_channels_spec() == "2"
    assert "Ingressi 1+2 (stereo)" in [dlg.channel_combo.itemText(i) for i in range(dlg.channel_combo.count())]
    dlg.profile_combo.setCurrentIndex(0)          # voce -> ingresso 1
    assert dlg.input_channels_spec() == "1"
    dlg.profile_combo.setCurrentIndex(2)          # tastiera -> 1+2
    assert dlg.input_channels_spec() == "1+2"
    assert "LINE" in dlg.hint_label.text()
    dlg.device_combo.setCurrentIndex(1)           # microfono USB: un solo ingresso
    assert [dlg.channel_combo.itemData(i) for i in range(dlg.channel_combo.count())] == ["1"]
    assert streams["monitor"].device == 5
    dlg.reject()


def test_meter_reads_the_monitor(tmp_path):
    dlg, _t, _streams = _dialog(tmp_path)
    dlg._tick()
    assert dlg.meter_db_label.text() == "-6 dB"
    dlg.reject()


def test_record_stop_keep_creates_an_aligned_clip(tmp_path):
    settings.set_input_latency_ms("Scarlett 2i2 (ALSA)", 0.0)
    dlg, track, streams = _dialog(tmp_path, track_profile="chitarra", track_channels="2",
                                  options=(("Punto scelto (battuta 3)", 8.0), ("Inizio del brano", 0.0)))
    dlg.count_in_spin.setValue(1)
    dlg.latency_spin.setValue(7)
    assert dlg.keep_btn.isEnabled() is False
    dlg.start_recording()
    duplex = streams["duplex"]
    assert duplex.opened_with[0] == 3 and duplex.in_channels == 2
    assert not dlg.record_btn.isEnabled() and dlg.stop_btn.isEnabled()
    duplex.pump(100)                               # 1 s: ancora nel conteggio di 2 s
    dlg._tick()
    assert dlg.status_label.text().startswith("Conteggio")
    duplex.pump(300)                               # 4 s in tutto
    dlg._tick()
    assert "REC" in dlg.status_label.text()
    dlg.stop_recording()
    assert "Ripresa di 00:02" in dlg.status_label.text()
    assert dlg.keep_btn.isEnabled()
    dlg.keep_take()
    assert dlg.result() == QDialog.Accepted

    clip = dlg.result_clip()
    assert clip.start_beat == 8.0
    assert clip.trim_start == pytest.approx(2.0 + 0.008 + 0.007)   # conteggio + driver + manuale
    info = read_wav_info(clip.file)
    assert os.path.dirname(clip.file) == str(tmp_path)
    assert info.channels == 1 and info.seconds == pytest.approx(4.0)
    assert settings.get_audio_input_device() == "Scarlett 2i2 (ALSA)"
    assert settings.get_input_latency_ms("Scarlett 2i2 (ALSA)") == 7


def test_stop_during_count_in_keeps_nothing(tmp_path):
    dlg, _t, streams = _dialog(tmp_path)
    dlg.count_in_spin.setValue(1)
    dlg.start_recording()
    streams["duplex"].pump(50)
    dlg.stop_recording()
    assert not dlg.keep_btn.isEnabled()
    assert "troppo corta" in dlg.status_label.text()
    dlg.reject()


def test_no_devices_disables_recording(tmp_path):
    p = Project()
    t = p.add_audio_track("Voce")
    dlg = AudioRecordDialog(None, p, t, [("Inizio del brano", 0.0)], str(tmp_path), devices=[])
    assert not dlg.record_btn.isEnabled()
    assert "Nessun ingresso" in dlg.status_label.text()
    dlg.reject()


def test_main_window_adds_the_take_and_asks_about_overlaps(tmp_path, monkeypatch):
    w = MainWindow()
    w.show()
    track = w.project.add_audio_track("Voce")
    old = str(tmp_path / "old.wav")
    from core.audio_tracks import write_wav
    write_wav(old, np.zeros((RATE * 4, 1), np.float32), RATE, bits=16)
    track.audio_clips.append(AudioClip("Vecchia", old, 0.0))
    w.history.reset(w.project)
    w.refresh_mixer()

    new = str(tmp_path / "new.wav")
    write_wav(new, np.zeros((RATE * 2, 1), np.float32), RATE, bits=16)
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))
    w._add_recorded_clip(track, AudioClip("Ripresa 2", new, 2.0), "voce", "1")
    assert [c.name for c in track.audio_clips] == ["Ripresa 2"]
    assert (track.input_profile, track.input_channels) == ("voce", "1")
    w.undo()
    assert [c.name for c in w.project.get_track("Voce").audio_clips] == ["Vecchia"]


def test_record_button_on_strip_and_start_options(tmp_path, monkeypatch):
    w = MainWindow()
    w.show()
    w.project.add_audio_track("Voce")
    w.project.add_track("Piano", "Piano", "")
    w.refresh_mixer()
    assert w.track_headers["Voce"].record_btn is not None
    assert w.track_headers["Piano"].record_btn is None

    import core.audio_recording as rec
    monkeypatch.setattr(rec, "is_recording_available", lambda: True)
    captured = {}

    class DummyDialog:
        def __init__(self, track, options, target_dir):
            captured.update(track=track.name, options=options, target_dir=target_dir)

        def exec(self):
            return QDialog.Rejected

    monkeypatch.setattr(w, "_make_record_dialog", lambda *a: DummyDialog(*a))
    w._playback_paused_beat = 16.0
    w.track_headers["Voce"].record_btn.click()
    assert captured["track"] == "Voce"
    assert captured["options"] == [("Posizione corrente (battuta 5)", 16.0), ("Inizio del brano", 0.0)]
    w.record_into_audio_track("Voce", start_beat=6.0)
    assert captured["options"][0] == ("Punto scelto (battuta 2)", 6.0)


def test_calibrate_measures_and_saves_the_latency(tmp_path, monkeypatch):
    from test_audio_recording import LoopbackStream
    streams = {}

    def loopback_factory(callback, rate, in_channels, input_device, output_device):
        streams["loop"] = LoopbackStream(callback, rate, in_channels, hidden_delay=0.009)
        return streams["loop"]

    p = Project()
    t = p.add_audio_track("Chitarra")
    dlg = AudioRecordDialog(None, p, t, [("Inizio del brano", 0.0)], str(tmp_path),
                            stream_factory=loopback_factory,
                            monitor_factory=lambda *a: FakeMonitorStream(*a),
                            backing_builder=_backing, run_in_thread=False, devices=DEVICES)
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: QMessageBox.Ok))
    dlg.calibrate_latency()
    assert not dlg.record_btn.isEnabled() and "Calibrazione" in dlg.status_label.text()
    streams["loop"].pump(int(5.2 * RATE / 256))
    dlg._tick()
    assert dlg.latency_spin.value() == pytest.approx(9.0, abs=0.2)
    assert settings.get_input_latency_ms("Scarlett 2i2 (ALSA)") == pytest.approx(9.0, abs=0.2)
    assert dlg.record_btn.isEnabled()
    assert "Latenza misurata" in dlg.status_label.text()
    dlg.reject()


def test_calibrate_failure_is_reported(tmp_path, monkeypatch):
    dlg, _t, streams = _dialog(tmp_path)            # FakeDuplex: segnale costante, niente click
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: QMessageBox.Ok))
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: warnings.append(a[1])))
    before = dlg.latency_spin.value()
    dlg.calibrate_latency()
    streams["duplex"].pump(500)
    dlg._tick()
    assert warnings == ["Calibrazione non riuscita"]
    assert dlg.latency_spin.value() == before
    dlg.reject()


def test_microphone_warning_follows_input_and_click(tmp_path):
    from dataclasses import replace
    dlg, _t, _streams = _dialog(tmp_path)
    shown = lambda: dlg.mic_warning.isVisibleTo(dlg)          # noqa: E731
    dlg.metronome_check.setChecked(True)
    assert shown()                                              # DEVICES: nessuna scheda esterna
    dlg.metronome_check.setChecked(False)
    dlg.count_in_spin.setValue(0)
    assert not shown()                                          # niente click: niente avviso
    dlg.count_in_spin.setValue(1)
    assert shown()
    dlg._devices[dlg.device_combo.currentIndex()] = replace(dlg.selected_device(), external=True)
    dlg._update_hint()
    assert not shown()                                          # scheda esterna: il click non entra
    dlg.reject()


def test_listen_to_the_take_before_keeping_it(tmp_path):
    played = []

    class FakeOut:
        def __init__(self, callback, rate, device):
            self.callback, self.rate = callback, rate
            played.append(self)

        def start(self):
            pass

        def stop(self):
            pass

        def close(self):
            pass
    dlg, _track, streams = _dialog(tmp_path)
    dlg._player_factory = FakeOut
    assert not dlg.play_btn.isEnabled()
    dlg.start_recording()
    streams["duplex"].pump(400)                                 # 2 s di conteggio + 2 s di ripresa
    dlg.stop_recording()
    status = dlg.status_label.text()
    assert dlg.play_btn.isEnabled() and dlg.with_backing_check.isChecked()
    dlg.toggle_listen()
    assert dlg.listening and dlg.play_btn.text() == "■ Ferma" and not dlg.with_backing_check.isEnabled()
    out = np.zeros((RATE, 2), np.float32)
    played[0].callback(out, RATE, None, None)                   # 1 s: si sente la chitarra (0,25)
    assert np.allclose(out[RATE // 10:], 0.25, atol=0.02)
    dlg._tick()
    assert "Ascolto" in dlg.status_label.text()
    dlg.toggle_listen()                                         # Ferma
    assert not dlg.listening and dlg.play_btn.text() == "▶ Ascolta" and dlg.status_label.text() == status
    dlg.toggle_listen()
    for _ in range(3):
        played[-1].callback(out, RATE, None, None)              # fino alla fine
    dlg._tick()
    assert not dlg.listening and dlg.status_label.text() == status
    dlg.toggle_listen()
    dlg.keep_take()                                             # Tieni: l'ascolto si ferma
    assert dlg._player is None and dlg.result() == QDialog.Accepted
