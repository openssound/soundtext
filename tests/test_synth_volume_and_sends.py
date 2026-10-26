"""
Tracce suonate da uno strumento plugin (SFZ, VST3, LV2): il volume di
traccia e il master sono un guadagno sull'audio, non una scala delle
velocity (che con i campioni scelgono lo strato dinamico), e i cursori
Riverbero e Chorus dell'invio rapido agiscono anche su di loro.

Esecuzione:
    python3 -m pytest tests/test_synth_volume_and_sends.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys
import tempfile

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mido  # noqa: E402

from core import effect_render  # noqa: E402
from core.effects import apply_synth_sends, effects_available  # noqa: E402
from core.midi_export import export_project_to_midi  # noqa: E402
from core.model import Effect, Project  # noqa: E402
from core.tempo_map import build_tempo_beat_map  # noqa: E402

SFZ = "sfz:/strumenti/piano.sfz"
needs_pedalboard = pytest.mark.skipif(not effects_available(), reason="pedalboard non installato")


def _project(volume=100, synth=SFZ, reverb=0, chorus=0, master=100):
    p = Project(name="x", tempo_bpm=120, time_sig="4/4")
    p.master_volume = master
    t = p.add_track("P", "Piano", "4: 60@ c 100@ e 120@ g c*5 |")
    t.synth, t.volume, t.reverb, t.chorus = synth, volume, reverb, chorus
    return p, t


def _velocities_and_cc7(project, track, **kw):
    path = tempfile.mktemp(suffix=".mid")
    try:
        export_project_to_midi(project, path, tracks=[track], **kw)
        msgs = [m for tr in mido.MidiFile(path).tracks for m in tr]
    finally:
        os.remove(path)
    velocities = [m.velocity for m in msgs if m.type == "note_on" and m.velocity > 0]
    cc7 = [m.value for m in msgs if m.type == "control_change" and m.control == 7]
    return velocities, cc7


def test_plugin_track_keeps_the_written_velocities():
    p, t = _project(volume=190, master=150)
    velocities, cc7 = _velocities_and_cc7(p, t, volume_as_gain=True)
    assert velocities == [60, 100, 120, 120]          # non tutte schiacciate a 127
    assert cc7 == [100]                               # il valore neutro dello strumento


def test_soundfont_track_and_plain_export_still_scale_the_velocity():
    p, t = _project(volume=50, synth="")
    assert _velocities_and_cc7(p, t, volume_as_gain=True)[0] == [30, 50, 60, 60]
    p, t = _project(volume=50)
    assert _velocities_and_cc7(p, t)[0] == [30, 50, 60, 60]     # l'export MIDI dell'utente non cambia


def test_stem_request_carries_gain_and_sends():
    p, t = _project(volume=150, master=80, reverb=40, chorus=20)
    request = effect_render.prepare_stem(p, t, build_tempo_beat_map(p))
    try:
        assert request.synth == SFZ
        assert request.gain == pytest.approx(1.2)
        assert (request.reverb_send, request.chorus_send) == (40, 20)
    finally:
        request.cleanup()


def test_no_sends_into_a_simulated_amplifier():
    p, t = _project(reverb=40, chorus=20)
    t.effects = [Effect(kind="nam", params={})]
    request = effect_render.prepare_stem(p, t, build_tempo_beat_map(p))
    try:
        assert (request.reverb_send, request.chorus_send) == (0, 0)
    finally:
        request.cleanup()


def test_volume_is_applied_after_the_effects_chain(monkeypatch):
    tone = np.full((4800, 2), 0.25, dtype=np.float32)
    monkeypatch.setattr(effect_render, "render_synth", lambda request, stop_check=None: tone.copy())
    levels = {}
    for volume in (100, 50):
        p, t = _project(volume=volume)
        request = effect_render.prepare_stem(p, t, build_tempo_beat_map(p))
        try:
            # il volume e' dopo la catena: il suono asciutto non cambia
            assert float(np.abs(effect_render.render_dry(request)).max()) == pytest.approx(0.25)
            levels[volume] = float(np.abs(effect_render.render_stem(request)).max())
        finally:
            request.cleanup()
    assert levels[100] == pytest.approx(0.25)
    assert levels[50] == pytest.approx(0.125)


@needs_pedalboard
def test_synth_sends_add_reverb_and_leave_dry_tracks_alone():
    rate = 48000
    x = np.zeros((rate, 2), dtype=np.float32)
    x[:2400] = 0.5                                     # un colpo di 50 ms, poi silenzio
    assert apply_synth_sends(x, rate, "sala", 0, 0) is x
    assert apply_synth_sends(x, rate, "secco", 50, 50) is x
    wet = apply_synth_sends(x, rate, "sala", 50, 0)
    assert len(wet) >= len(x)
    after = np.abs(wet[4800:rate]).max()               # la coda del riverbero dopo il colpo
    assert after > 1e-3 and np.abs(x[4800:rate]).max() == 0
    chorus = apply_synth_sends(x, rate, "sala", 0, 50)
    assert not np.allclose(chorus[:2400], x[:2400])
