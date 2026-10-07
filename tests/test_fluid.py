"""
Collegamento diretto alla libreria FluidSynth (core.fluid), al posto di
pyfluidsynth: impostazioni secondo il tipo, SoundFont, campioni, guadagno
che resiste al reset, riverbero, lettore MIDI, e il pitch bend dal vivo
(prima un bending di un tono suonava di mezzo tono).
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from core import fluid

pytestmark = pytest.mark.skipif(not fluid.available(), reason="libreria FluidSynth non installata")

SF = "/usr/share/sounds/sf2/TimGM6mb.sf2"
needs_sf = pytest.mark.skipif(not os.path.exists(SF), reason="SoundFont di prova non installato")
RATE = 44100


@pytest.fixture
def synth():
    s = fluid.Synth(gain=0.5, samplerate=RATE)
    yield s
    s.delete()


def _pitch(samples):
    from core.audio_dsp import yin
    _, freqs, conf = yin(samples, RATE, 2048, 512)
    return float(np.median(freqs[conf > 0.8]))


def _play(synth, sfid, key=69, frames=RATE // 2, program=73):
    synth.program_select(0, sfid, 0, program)            # flauto: altezza stabile
    synth.noteon(0, key, 100)
    x = synth.get_samples(frames).reshape(-1, 2)[:, 0].astype(np.float32) / 32768
    synth.noteoff(0, key)
    synth.get_samples(RATE // 4)
    return x


def test_version_is_2_or_newer():
    assert fluid.version()[0] >= 2
    assert fluid.load_error() == ""


def test_settings_follow_their_type(synth):
    assert synth.get_setting("synth.gain") == 0.5
    assert synth.get_setting("synth.sample-rate") == RATE              # numerica, passata come intero
    assert synth.setting("synth.reverb.active", True)                 # intera
    assert synth.get_setting("synth.reverb.active") == 1
    assert isinstance(synth.get_setting("audio.driver"), str)
    assert not synth.setting("non.esiste", 1)
    assert synth.get_setting("non.esiste") is None


def test_invalid_soundfont_gives_minus_one(synth, tmp_path):
    assert synth.sfload(str(tmp_path / "manca.sf2")) == -1


@needs_sf
def test_samples_and_pitch(synth):
    sfid = synth.sfload(SF)
    assert sfid >= 0
    synth.system_reset()
    silent = synth.get_samples(1000)
    assert silent.dtype == np.int16 and silent.shape == (2000,)
    assert np.abs(silent).max() <= 1                                   # solo il dither
    x = _play(synth, sfid)
    assert np.abs(x).max() > 0.01
    assert abs(12 * np.log2(_pitch(x[5000:]) / 440.0)) < 0.1


@needs_sf
def test_pitch_bend_covers_two_semitones(synth):
    sfid = synth.sfload(SF)
    synth.system_reset()
    for value, semitones in ((4096, 1.0), (8191, 2.0), (-8192, -2.0)):
        synth.pitch_bend(0, value)
        x = _play(synth, sfid)
        assert abs(12 * np.log2(_pitch(x[5000:]) / 440.0) - semitones) < 0.1


def test_live_synth_bends_by_the_requested_semitones():
    from core.playback import LiveSynth

    class Recorder:
        def __init__(self):
            self.values = []

        def pitch_bend(self, channel, value):
            self.values.append(value)

    live = LiveSynth()
    live._synth = Recorder()
    live.pitch_bend(0, 2.0)
    live.pitch_bend(0, 1.0)
    live.pitch_bend(0, -2.0)
    assert live._synth.values == [8192, 4096, -8192]
    live._synth = None


@needs_sf
def test_gain_survives_system_reset(synth):
    sfid = synth.sfload(SF)
    synth.system_reset()
    loud = np.abs(_play(synth, sfid)).max()
    synth.set_gain(0.125)
    synth.system_reset()
    assert abs(synth.get_gain() - 0.125) < 1e-6
    quiet = np.abs(_play(synth, sfid)).max()
    assert 0.15 < quiet / loud < 0.35                                  # 0.125 / 0.5


def test_reverb_settings(synth):
    synth.set_reverb(0.7, 0.3, 0.8, 0.6)
    assert synth.get_setting("synth.reverb.room-size") == 0.7
    assert synth.get_setting("synth.reverb.level") == 0.6


@needs_sf
def test_midi_player_renders_a_file(synth, tmp_path):
    import mido
    mid = mido.MidiFile()
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track += [mido.Message("program_change", program=73, time=0),
              mido.Message("note_on", note=72, velocity=100, time=0),
              mido.Message("note_off", note=72, velocity=0, time=240)]
    path = str(tmp_path / "nota.mid")
    mid.save(path)
    synth.sfload(SF)
    synth.system_reset()
    player = fluid.Player(synth)
    try:
        assert player.add(path)
        assert not player.add(str(tmp_path / "manca.mid"))
        player.play()
        chunks = []
        while player.playing() and len(chunks) < 200:
            chunks.append(synth.get_samples(4410))
    finally:
        player.delete()
    x = np.concatenate(chunks).reshape(-1, 2)[:, 0].astype(np.float32) / 32768
    assert 2 <= len(chunks) < 200
    assert abs(12 * np.log2(_pitch(x[2000:12000]) / _hz(72))) < 0.1


def _hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)
