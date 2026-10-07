"""
Riconoscimento delle note dall'audio (dialogo "Converti audio in
SoundText"): casi verificati durante la revisione del codice.

- Note ripetute (la stessa nota suonata piu' volte, tipica del basso):
  restano note distinte, sia staccate sia legate; una nota tenuta con
  vibrato e tremolo resta invece una nota sola.
- Le note staccate lasciano le pause, e l'ultima non si allunga fino alla
  fine del file.
- Una registrazione debole non da' velocity quasi mute.
- In modalita' percussiva gli hihat in crome tra cassa e rullante (e due
  casse di fila) non spariscono.
- Due note di una melodia che cadono nello stesso slot non diventano un
  accordo.
- Il dialogo: Annulla interrompe davvero la conversione e lascia il dialogo
  utilizzabile, la chiusura ferma la registrazione ed elimina i WAV
  temporanei, il metronomo riparte con la registrazione, metriche non
  valide non finiscono nel progetto.
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys
import wave

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from core.audio_import import align_to_first_event, convert_audio_to_track_text, normalize_velocities
from core.audio_percussion import drop_tail_retriggers, duplicate_window_s
from core.audio_quantize import AudioEvent, events_to_tokens

R = 44100


def _hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def _tone(freq, dur, amp=0.5, sound=None):
    n, s = int(dur * R), int((sound or dur) * R)
    t = np.arange(s) / R
    env = np.minimum(1, t / 0.005) * np.exp(-t * 3) * np.minimum(1, (s / R - t) / 0.01)
    y = sum(amp / k * np.sin(2 * np.pi * freq * k * t) for k in range(1, 6)) * env
    return np.concatenate([y, np.zeros(n - s)])


def _write(tmp_path, name, x):
    path = str(tmp_path / name)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(R)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    return path


def _convert(path, percussion=False, grid=16, min_freq=None):
    return convert_audio_to_track_text(path, percussion, 120, grid, False, {}, 3, already_wav=True,
                                       min_freq_hz=min_freq)


# ------------------------------------------------------------ audio sintetico

def test_repeated_notes_and_rests(tmp_path):
    x = np.concatenate([_tone(_hz(40), 0.25, sound=0.2) for _ in range(4)]      # 4 crome di Mi1 staccate
                       + [_tone(_hz(45), 0.5, sound=0.45) for _ in range(2)]    # 2 semiminime di La1
                       + [np.zeros(R), _tone(_hz(40), 1.0)])                    # pausa, minima
    text = _convert(_write(tmp_path, "basso.wav", x), min_freq=41.2)
    assert text == "16: 110@ 2e*2 2e*2 2e*2 2e*2 4a*2 4a*2 8r 8e*2"


def test_repeated_notes_without_gap_stay_separate(tmp_path):
    x = np.concatenate([_tone(_hz(45), 0.5) for _ in range(4)])                # ripizzicate, senza pausa
    assert _convert(_write(tmp_path, "legate.wav", x), min_freq=41.2) == "16: 110@ 4a*2 4a*2 4a*2 4a*2"


def test_staccato_melody_leaves_rests(tmp_path):
    x = np.concatenate([_tone(_hz(m), 0.5, sound=0.25) for m in (60, 62, 64)] + [np.zeros(R // 2)])
    assert _convert(_write(tmp_path, "staccato.wav", x)) == "16: 110@ 2c*4 2r 2d*4 2r 2e*4"


def test_held_note_with_vibrato_and_tremolo_is_one_note(tmp_path):
    t = np.arange(2 * R) / R
    f = _hz(57) * 2 ** (0.6 / 12 * np.sin(2 * np.pi * 6 * t))
    amp = 0.4 * (1 + 0.3 * np.sin(2 * np.pi * 6 * t)) * np.minimum(1, t / 0.02)
    x = sum(amp / k * np.sin(2 * np.pi * k * np.cumsum(f) / R) for k in range(1, 5))
    assert _convert(_write(tmp_path, "vibrato.wav", x)) == "16: 110@ 16a*3"


def test_quiet_recording_is_not_almost_mute(tmp_path):
    x = 0.1 * np.concatenate([_tone(_hz(60), 0.5), _tone(_hz(64), 0.5)])        # picco al 10%
    assert _convert(_write(tmp_path, "debole.wav", x)) == "16: 110@ 4c*4 4e*4"


def test_drums_in_eighths_keep_the_hihats(tmp_path):
    rng = np.random.RandomState(1)
    t = np.arange(int(0.25 * R)) / R

    def kick():
        return 0.9 * np.sin(2 * np.pi * np.cumsum(50 + 100 * np.exp(-t * 30)) / R) * np.exp(-t * 12)

    def snare():
        return (0.5 * rng.randn(len(t)) + 0.4 * np.sin(2 * np.pi * 190 * t)) * np.exp(-t * 20)

    def hat():
        return 0.3 * np.diff(np.concatenate([[0], rng.randn(len(t))])) * np.exp(-t * 60)

    x = np.concatenate([f() for f in [kick, hat, snare, hat, kick, kick, snare, hat]])
    text = _convert(_write(tmp_path, "batteria.wav", x), percussion=True, grid=8)
    assert text.startswith("8: ")
    hits, velocity = [], None
    for token in text[3:].split():
        if token.endswith("@"):
            velocity = int(token[:-1])
        else:
            hits.append((token, velocity))
    assert [name for name, _ in hits] == ["kick", "hihat", "snare", "hihat", "kick", "kick", "snare", "hihat"]
    # gli hihat hanno picchi alti quanto la cassa ma molta meno energia
    assert max(v for name, v in hits if name == "hihat") < min(v for name, v in hits if name == "kick")


# ------------------------------------------------------------ passi singoli

def test_velocities_are_normalized_to_the_loudest():
    events = [AudioEvent(0, 1, 13, 60), AudioEvent(1, 2, 6, 62), AudioEvent(2, 3, 12, 64)]
    assert [e.velocity for e in normalize_velocities(events)] == [110, 100, 110]   # -6.7 dB -> 100


def test_align_to_first_event():
    events = align_to_first_event([AudioEvent(1.5, 2.0, 100, 60), AudioEvent(2.0, 2.5, 100, 62)])
    assert [(e.start_sec, e.end_sec) for e in events] == [(0.0, 0.5), (0.5, 1.0)]


def test_melodic_notes_in_the_same_slot_do_not_become_a_chord():
    # a 120 BPM uno slot da 1/16 dura 0.125 s: le prime due note cadono nello stesso slot
    events = [AudioEvent(0.0, 0.05, 100, 60), AudioEvent(0.05, 0.5, 100, 62), AudioEvent(0.5, 1.0, 100, 64)]
    assert events_to_tokens(events, 120, 16, monophonic=True) == ["16:", "100@", "4d*4", "4e*4"]
    assert "[c*4 d*4]" in " ".join(events_to_tokens(events, 120, 16))              # polifonico: accordo
    overlapping = [AudioEvent(0.0, 0.6, 100, 60), AudioEvent(0.25, 0.5, 100, 62)]
    assert events_to_tokens(overlapping, 120, 16, monophonic=True) == ["16:", "100@", "2c*4", "2d*4"]


def test_percussion_duplicate_window_follows_the_grid():
    assert duplicate_window_s(None) == 0.28                                      # valore storico
    assert duplicate_window_s(0.125) == pytest.approx(0.075)                     # 1/16 a 120 BPM
    assert duplicate_window_s(0.5) == 0.28 and duplicate_window_s(0.01) == 0.04
    hits = [AudioEvent(0.0, 0.0, 100, perc_name="kick"), AudioEvent(0.1, 0.1, 20, perc_name="kick"),
            AudioEvent(0.12, 0.12, 20, perc_name="hihat"), AudioEvent(0.25, 0.25, 90, perc_name="kick")]
    kept = drop_tail_retriggers(hits)
    assert [(e.perc_name, e.start_sec) for e in kept] == [("kick", 0.0), ("hihat", 0.12), ("kick", 0.25)]


# ------------------------------------------------------------ dialogo

@pytest.fixture
def dialog(monkeypatch):
    from PySide6.QtWidgets import QApplication, QMessageBox
    QApplication.instance() or QApplication([])
    from core.model import Project
    import gui.audio_import_dialog as mod
    errors = []
    monkeypatch.setattr(QMessageBox, "critical", lambda *a: errors.append(a[2]))
    monkeypatch.setattr(mod, "can_decode_compressed_audio", lambda: True)
    dlg = mod.AudioImportDialog(None, Project(name="t"), "Guitar", "traccia 'Chitarra'")
    dlg.errors = errors
    yield dlg, mod
    dlg.close()


def _wait(dlg, until):
    from PySide6.QtWidgets import QApplication
    for _ in range(500):
        QApplication.processEvents()
        if until():
            return True
        if dlg._worker is not None:
            dlg._worker.wait(10)
    return until()


def test_cancel_stops_the_conversion_and_keeps_the_dialog_usable(dialog, monkeypatch):
    dlg, mod = dialog
    import threading
    started = threading.Event()

    def slow_convert(*args, progress_callback=None, **kwargs):
        started.set()
        import time
        while True:                                            # gira finche' non si annulla
            progress_callback(0.5)
            time.sleep(0.005)

    monkeypatch.setattr(mod, "convert_audio_to_track_text", slow_convert)
    dlg._set_source("/tmp/qualunque.wav")
    dlg._on_convert_clicked()
    assert started.wait(5)
    dlg._progress_dlg.canceled.emit()                          # pulsante Annulla (o Esc)
    assert _wait(dlg, lambda: dlg._worker is None)
    assert dlg.convert_btn.isEnabled() and dlg.errors == []                   # nessun errore mostrato


def test_closing_stops_the_recording_and_removes_temporary_files(dialog, tmp_path):
    dlg, _ = dialog
    old = tmp_path / "vecchia.wav"
    old.write_bytes(b"x")
    new = tmp_path / "nuova.wav"

    class FakeRecorder:
        is_recording = True

        def stop(self):
            self.is_recording = False
            new.write_bytes(b"x")
            return str(new)

    dlg.recorder = FakeRecorder()
    dlg._mic_files.append(str(old))
    dlg.reject()
    assert not dlg.recorder.is_recording
    assert not old.exists() and not new.exists()


def test_metronome_restarts_with_the_recording(dialog, monkeypatch):
    dlg, mod = dialog
    restarts, calls = [], []

    class FakeRecorder:
        is_recording = False
        elapsed_seconds = 0.0

        def start(self):
            self.is_recording = True

        def stop(self):
            self.is_recording = False
            return "/tmp/soundtext_mic_prova.wav"

    monkeypatch.setattr(dlg, "_restart_metronome", lambda: restarts.append(1))
    monkeypatch.setattr(mod, "convert_audio_to_track_text", lambda *a, **k: calls.append(k) or "16: c")
    dlg.recorder = FakeRecorder()
    for metronome in (True, False):
        dlg.metronome_checkbox.blockSignals(True)
        dlg.metronome_checkbox.setChecked(metronome)
        dlg.metronome_checkbox.blockSignals(False)
        dlg._toggle_recording()
        dlg._toggle_recording()
        dlg._on_convert_clicked()
        assert _wait(dlg, lambda: dlg._worker is None)
    assert restarts == [1]                                     # solo con il metronomo acceso
    assert [c["align_to_first_note"] for c in calls] == [False, True]


def test_invalid_time_signatures_do_not_reach_the_project(dialog):
    dlg, _ = dialog
    for text in ("4/0", "0/4", "7/3"):
        dlg._on_metrica_changed(text)
        assert dlg.project.time_sig == "4/4"
    dlg._on_metrica_changed("6/8")
    assert dlg.project.time_sig == "6/8"
