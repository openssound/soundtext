"""
Test per la fila qualita' accordo (Z X C V B N M , . /) e i tasti esecutivi
(L-Alt sustain, L-Ctrl inversione, Tab commuta Piano/Forte) del dialogo
"Suona con la tastiera" (gui.keyboard_play_dialog.KeyboardPlayDialog), che
hanno sostituito il vecchio sistema di modificatori Maiusc/Ctrl/Alt.

Esecuzione:
    python3 -m pytest tests/test_keyboard_quality_row.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from core.model import Project
from gui.keyboard_play_dialog import KeyboardPlayDialog

_app = QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _linux_tables(monkeypatch):
    """Questi test usano i codici di Linux (evdev + 8): le tavole sono quelle
    di Linux su qualunque sistema giri la suite (le altre sono provate a
    parte, vedi test_keyboard_scancodes.py)."""
    from gui import keyboard_scancodes
    monkeypatch.setattr(keyboard_scancodes, "_PLATFORM", "linux")
    monkeypatch.setattr(keyboard_scancodes, "_scancode_table_cache", None)


class _FakeKeyEvent:
    def __init__(self, key, native_scan_code=0):
        self._key = key
        self._native_scan_code = native_scan_code

    def key(self):
        return self._key

    def nativeScanCode(self):
        # 0 non e' mai una voce valida nella tavola scancode Linux (vedi
        # gui.keyboard_scancodes: i codici evdev partono da 2, +8 = 10 come
        # minimo): canonical_key() ricade quindi sempre su key() qui, a meno
        # che un test non passi esplicitamente un native_scan_code reale.
        return self._native_scan_code


def _wait_until(condition, timeout_s):
    """Fa girare gli eventi Qt finche' condition() e' vera o scade il tempo."""
    t0 = time.time()
    while not condition() and time.time() - t0 < timeout_s:
        _app.processEvents()
        time.sleep(0.01)


def _make_dialog():
    p = Project(name="Test")
    p.add_track("Piano1", "Piano", "")
    dlg = KeyboardPlayDialog(None, project=p, instrument_name="Piano", context_label="test")
    dlg._instrument_active = lambda: True  # bypassa il grab tastiera reale
    return dlg


def _press(dlg, key):
    dlg._on_surface_key_press(_FakeKeyEvent(key))


def _release(dlg, key):
    dlg._on_surface_key_release(_FakeKeyEvent(key))


def test_single_note_without_quality_key():
    dlg = _make_dialog()
    _press(dlg, Qt.Key_Q)
    notes = dlg._active_notes[Qt.Key_Q]["midi_notes"]
    assert len(notes) == 1
    _release(dlg, Qt.Key_Q)
    assert Qt.Key_Q not in dlg._active_notes


def test_major_chord_with_z():
    dlg = _make_dialog()
    _press(dlg, Qt.Key_Z)
    _press(dlg, Qt.Key_Q)
    base = dlg._active_notes[Qt.Key_Q]["midi_notes"]
    assert sorted(n - min(base) for n in base) == [0, 4, 7]
    _release(dlg, Qt.Key_Q)
    _release(dlg, Qt.Key_Z)


def test_minor7_chord_with_v():
    dlg = _make_dialog()
    _press(dlg, Qt.Key_V)
    _press(dlg, Qt.Key_Q)
    base = dlg._active_notes[Qt.Key_Q]["midi_notes"]
    assert sorted(n - min(base) for n in base) == [0, 3, 7, 10]
    _release(dlg, Qt.Key_Q)
    _release(dlg, Qt.Key_V)


def test_power_chord_includes_octave_double():
    dlg = _make_dialog()
    _press(dlg, Qt.Key_Period)
    _press(dlg, Qt.Key_Q)
    base = dlg._active_notes[Qt.Key_Q]["midi_notes"]
    assert sorted(n - min(base) for n in base) == [0, 7, 12]
    _release(dlg, Qt.Key_Q)
    _release(dlg, Qt.Key_Period)


def test_bass_double_with_slash():
    dlg = _make_dialog()
    _press(dlg, Qt.Key_Slash)
    _press(dlg, Qt.Key_Q)
    notes = sorted(dlg._active_notes[Qt.Key_Q]["midi_notes"])
    assert len(notes) == 2
    assert notes[1] - notes[0] == 12
    _release(dlg, Qt.Key_Q)
    _release(dlg, Qt.Key_Slash)


def test_quality_key_released_before_note_has_no_effect():
    # Il tasto qualita' va tenuto PRIMA/insieme alla nota: se viene
    # rilasciato prima ancora di premere la nota, quest'ultima resta singola.
    dlg = _make_dialog()
    _press(dlg, Qt.Key_Z)
    _release(dlg, Qt.Key_Z)
    _press(dlg, Qt.Key_Q)
    assert len(dlg._active_notes[Qt.Key_Q]["midi_notes"]) == 1
    _release(dlg, Qt.Key_Q)


def test_inversion_moves_root_up_an_octave():
    dlg = _make_dialog()
    _press(dlg, Qt.Key_Z)  # accordo maggiore
    _press(dlg, Qt.Key_Q)
    without_inversion = sorted(dlg._active_notes[Qt.Key_Q]["midi_notes"])
    _release(dlg, Qt.Key_Q)
    _release(dlg, Qt.Key_Z)

    _press(dlg, Qt.Key_Control)  # inversione
    _press(dlg, Qt.Key_Z)
    _press(dlg, Qt.Key_Q)
    with_inversion = sorted(dlg._active_notes[Qt.Key_Q]["midi_notes"])
    _release(dlg, Qt.Key_Q)
    _release(dlg, Qt.Key_Z)
    _release(dlg, Qt.Key_Control)

    root = without_inversion[0]
    assert root not in with_inversion
    assert (root + 12) in with_inversion
    assert sorted(with_inversion) == sorted(without_inversion[1:] + [root + 12])


def test_inversion_only_applies_to_chords_not_single_notes():
    dlg = _make_dialog()
    _press(dlg, Qt.Key_Control)
    _press(dlg, Qt.Key_Q)
    notes = dlg._active_notes[Qt.Key_Q]["midi_notes"]
    assert len(notes) == 1  # nessun accordo attivo: l'inversione non ha nulla su cui agire
    _release(dlg, Qt.Key_Q)
    _release(dlg, Qt.Key_Control)


def test_velocity_toggle_with_tab():
    dlg = _make_dialog()
    assert dlg._velocity_low is False  # stato di partenza: Forte

    _press(dlg, Qt.Key_Q)
    assert dlg._active_notes[Qt.Key_Q]["velocity"] == 110
    _release(dlg, Qt.Key_Q)

    _press(dlg, Qt.Key_Tab)
    _press(dlg, Qt.Key_Q)
    assert dlg._active_notes[Qt.Key_Q]["velocity"] == 60
    _release(dlg, Qt.Key_Q)

    _press(dlg, Qt.Key_Tab)  # torna a Forte
    _press(dlg, Qt.Key_Q)
    assert dlg._active_notes[Qt.Key_Q]["velocity"] == 110
    _release(dlg, Qt.Key_Q)


def test_sustain_keeps_note_open_until_capslock_released():
    dlg = _make_dialog()
    dlg._recording = True
    dlg._record_start_wall = time.time()

    _press(dlg, Qt.Key_CapsLock)
    _press(dlg, Qt.Key_Q)
    time.sleep(0.05)
    _release(dlg, Qt.Key_Q)

    assert Qt.Key_Q not in dlg._active_notes
    assert len(dlg._sustained_notes) == 1
    assert len(dlg._captured_events) == 0  # non ancora chiuso: il sustain e' ancora attivo

    time.sleep(0.05)
    _release(dlg, Qt.Key_CapsLock)

    assert len(dlg._sustained_notes) == 0
    assert len(dlg._captured_events) == 1
    ev = dlg._captured_events[0]
    assert ev.end_sec - ev.start_sec >= 0.09  # copre l'intero periodo, non solo fino al release della nota


def test_sustain_inactive_releases_note_normally():
    dlg = _make_dialog()
    dlg._recording = True
    dlg._record_start_wall = time.time()

    _press(dlg, Qt.Key_Q)
    _release(dlg, Qt.Key_Q)

    assert len(dlg._sustained_notes) == 0
    assert len(dlg._captured_events) == 1


def test_bend_on_single_note_is_a_real_slide_not_a_pitch_shift():
    # Su una nota singola il bending e' "vero" (slide + rampa dal vivo, vedi
    # BEND_SEMITONES): midi_notes resta la nota NATURALE (suonata subito, non
    # spostata), lo scarto va invece in slide_to_pitch, catturato come
    # portamento nella notazione registrata (vedi core.audio_quantize).
    dlg = _make_dialog()
    _press(dlg, Qt.Key_Q)
    natural = dlg._active_notes[Qt.Key_Q]["midi_notes"][0]
    _release(dlg, Qt.Key_Q)

    from gui.keyboard_play_dialog import BEND_SEMITONES

    _press(dlg, Qt.Key_Shift)
    _press(dlg, Qt.Key_Q)
    info = dlg._active_notes[Qt.Key_Q]
    assert info["midi_notes"] == [natural]
    assert info.get("live_bend") is True
    assert info["slide_to_pitch"] == natural + BEND_SEMITONES
    _release(dlg, Qt.Key_Q)
    _release(dlg, Qt.Key_Shift)


def test_bend_single_note_captured_as_slide_token():
    dlg = _make_dialog()
    dlg._recording = True
    dlg._record_start_wall = time.time()

    _press(dlg, Qt.Key_Shift)
    _press(dlg, Qt.Key_Q)
    time.sleep(0.02)
    _release(dlg, Qt.Key_Q)
    _release(dlg, Qt.Key_Shift)

    assert len(dlg._captured_events) == 1
    ev = dlg._captured_events[0]
    from gui.keyboard_play_dialog import BEND_SEMITONES
    assert ev.slide_to_pitch == ev.midi_pitch + BEND_SEMITONES

    from core.audio_quantize import events_to_tokens
    tokens = events_to_tokens(dlg._captured_events, tempo_bpm=120, grid_denominator=16, ternary=False)
    joined = " ".join(tokens)
    assert ">" in joined  # sintassi di slide (core.notation.RE_SLIDE), es. 'c*4>d*4'


def test_bend_live_ramp_reaches_target_and_resets_on_release():
    dlg = _make_dialog()

    class _FakeLiveSynth:
        def __init__(self):
            self.bend_values = []
            self.notes_on = []
            self.notes_off = []

        def note_on(self, channel, pitch, velocity=100):
            self.notes_on.append(pitch)

        def note_off(self, channel, pitch):
            self.notes_off.append(pitch)

        def pitch_bend(self, channel, semitones):
            self.bend_values.append(semitones)

    dlg._live_synth = _FakeLiveSynth()

    from gui.keyboard_play_dialog import BEND_SEMITONES, BEND_RAMP_UP_MS, BEND_RAMP_DOWN_MS

    _press(dlg, Qt.Key_Shift)
    _press(dlg, Qt.Key_Q)
    assert dlg._live_bend_key == Qt.Key_Q
    assert dlg._live_synth.notes_on == [dlg._active_notes[Qt.Key_Q]["midi_notes"][0]]
    assert dlg._live_synth.bend_values[0] == 0.0  # la rampa parte da zero, non un salto secco

    # Lascia scorrere il vero QTimer fino al termine della rampa di salita
    # (su una macchina lenta i passi da 15 ms arrivano in ritardo: si aspetta
    # l'arrivo, con un limite largo, invece di un tempo fisso).
    _wait_until(lambda: dlg._live_synth.bend_values[-1] == float(BEND_SEMITONES),
                BEND_RAMP_UP_MS / 1000.0 + 3.0)
    assert dlg._live_synth.bend_values[-1] == float(BEND_SEMITONES)  # arrivata al bersaglio

    _release(dlg, Qt.Key_Q)
    _release(dlg, Qt.Key_Shift)

    _wait_until(lambda: dlg._live_synth.bend_values[-1] == 0.0 and dlg._live_synth.notes_off,
                BEND_RAMP_DOWN_MS / 1000.0 + 3.0)
    assert dlg._live_synth.bend_values[-1] == 0.0  # tornata a zero: non lascia il canale stonato
    assert dlg._live_synth.notes_off == dlg._live_synth.notes_on  # la nota e' stata fermata alla fine


def test_bend_applies_to_whole_chord():
    dlg = _make_dialog()
    _press(dlg, Qt.Key_Shift)
    _press(dlg, Qt.Key_Z)  # maggiore
    _press(dlg, Qt.Key_Q)
    bent = sorted(dlg._active_notes[Qt.Key_Q]["midi_notes"])
    _release(dlg, Qt.Key_Q)
    _release(dlg, Qt.Key_Z)
    _release(dlg, Qt.Key_Shift)

    from gui.keyboard_play_dialog import BEND_SEMITONES
    assert sorted(n - bent[0] for n in bent) == [0, 4, 7]  # struttura maggiore invariata
    unbent_root = bent[0] - BEND_SEMITONES
    # radice alzata esattamente di BEND_SEMITONES rispetto a quella "naturale" del tasto Q
    dlg2 = _make_dialog()
    _press(dlg2, Qt.Key_Q)
    natural_root = dlg2._active_notes[Qt.Key_Q]["midi_notes"][0]
    _release(dlg2, Qt.Key_Q)
    assert unbent_root == natural_root


def test_strum_staggers_note_onsets_but_shares_release():
    dlg = _make_dialog()
    dlg._recording = True
    dlg._record_start_wall = time.time()

    _press(dlg, Qt.Key_Alt)  # strumming
    _press(dlg, Qt.Key_Z)    # accordo maggiore (3 note)
    _press(dlg, Qt.Key_Q)
    time.sleep(0.1)
    _release(dlg, Qt.Key_Q)
    _release(dlg, Qt.Key_Z)
    _release(dlg, Qt.Key_Alt)

    assert len(dlg._captured_events) == 3
    starts = sorted(ev.start_sec for ev in dlg._captured_events)
    ends = {round(ev.end_sec, 3) for ev in dlg._captured_events}
    assert len(ends) == 1  # tutte le note finiscono insieme (rilascio del tasto fisico)
    assert starts[1] > starts[0]  # onset scaglionati, non simultanei
    assert starts[2] > starts[1]


def test_strum_inactive_plays_chord_as_single_block():
    dlg = _make_dialog()
    dlg._recording = True
    dlg._record_start_wall = time.time()

    _press(dlg, Qt.Key_Z)
    _press(dlg, Qt.Key_Q)
    _release(dlg, Qt.Key_Q)
    _release(dlg, Qt.Key_Z)

    assert len(dlg._captured_events) == 3
    starts = {round(ev.start_sec, 3) for ev in dlg._captured_events}
    assert len(starts) == 1  # tutte simultanee


def test_arpeggiator_cycles_through_pool_and_captures_events():
    dlg = _make_dialog()
    dlg._recording = True
    dlg._record_start_wall = time.time()
    dlg.project.tempo_bpm = 480  # passo breve (1/16 a 480bpm = 31.25ms) per un test veloce

    _press(dlg, Qt.Key_Space)   # pool ancora vuoto qui: il tick immediato di _start_arpeggiator non cattura nulla
    _press(dlg, Qt.Key_Z)   # accordo maggiore: pool di 3 note
    _press(dlg, Qt.Key_Q)
    assert dlg._active_notes[Qt.Key_Q].get("via_arpeggiator") is True
    assert len(dlg._captured_events) == 0

    # Simula il passare di alcuni intervalli del timer chiamando il tick a mano
    # (piu' affidabile in test headless che affidarsi al QTimer reale, che nel
    # normale funzionamento continuerebbe a scattare da solo da qui in poi).
    for _ in range(6):
        dlg._on_arpeggio_tick()
    assert len(dlg._captured_events) == 6

    pitches_used = {ev.midi_pitch for ev in dlg._captured_events}
    assert len(pitches_used) == 3  # ha effettivamente ciclato su tutte e 3 le note dell'accordo

    _release(dlg, Qt.Key_Q)
    _release(dlg, Qt.Key_Z)
    _release(dlg, Qt.Key_Space)
    assert dlg._arpeggiator_active is False


def test_note_pressed_before_arpeggiator_is_unaffected():
    dlg = _make_dialog()
    dlg._recording = True
    dlg._record_start_wall = time.time()

    _press(dlg, Qt.Key_Q)  # nota gia' in corso, PRIMA dello spazio
    _press(dlg, Qt.Key_Space)
    assert dlg._active_notes[Qt.Key_Q].get("via_arpeggiator") is not True
    _release(dlg, Qt.Key_Space)
    _release(dlg, Qt.Key_Q)
    assert len(dlg._captured_events) == 1  # un singolo evento normale, non arpeggiato


if __name__ == "__main__":
    import inspect
    here = sys.modules[__name__]
    tests = [f for name, f in inspect.getmembers(here) if name.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        passed += 1
        print(f"OK  {t.__name__}")
    print(f"\n{passed}/{len(tests)} test superati.")
