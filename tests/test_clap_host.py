"""Host CLAP (core.clap_host): un piccolo file .clap scritto in C per i
test (tests/data/clap_test_plugin.c) si compila qui e si carica davvero:
elenco dei plugin, parametri, elaborazione con la latenza compensata, uno
strumento suonato da eventi MIDI, e il percorso completo attraverso il
processo dei plugin (core.plugins). Senza un compilatore C i test si saltano."""

import os
import shutil
import subprocess
import sys

import numpy as np
import pytest

from core import clap_host, plugins

RATE = 48000
SOURCE = os.path.join(os.path.dirname(__file__), "data", "clap_test_plugin.c")


@pytest.fixture(scope="module")
def clap_file(tmp_path_factory):
    compiler = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if compiler is None or sys.platform == "win32":
        pytest.skip("serve un compilatore C per costruire il plugin di prova")
    folder = tmp_path_factory.mktemp("clap")
    path = str(folder / "soundtext-test.clap")
    done = subprocess.run([compiler, "-shared", "-fPIC", "-O1", "-o", path, SOURCE, "-lm"],
                          capture_output=True, text=True)
    if done.returncode != 0:
        pytest.skip("il plugin di prova non si compila: " + done.stderr[-300:])
    return path


def _sine(seconds=0.5, freq=440.0):
    wave = (0.5 * np.sin(2 * np.pi * freq * np.arange(int(RATE * seconds)) / RATE)).astype(np.float32)
    return np.stack([wave, wave], axis=1)


def test_lists_the_plugins_of_a_file(clap_file):
    infos = clap_host.list_clap_plugins(clap_file)
    assert [(i.id, i.name, i.instrument) for i in infos] == [
        ("test.soundtext.gain", "Test Gain", False), ("test.soundtext.sine", "Test Sine", True),
        ("test.soundtext.notes", "Test Notes", False)]
    assert infos[0].vendor == "SoundText tests" and infos[0].category == "Utility"
    assert infos[0].ref == f"clap:{clap_file}|test.soundtext.gain"
    assert infos[0].problem == "" and infos[1].problem == ""
    assert infos[2].problem                       # ne' effetto ne' strumento: non utilizzabile


def test_finds_clap_files_in_folders(clap_file, tmp_path):
    nested = tmp_path / "vendor"
    nested.mkdir()
    shutil.copy(clap_file, nested / "Other.clap")
    (tmp_path / "notes.txt").write_text("x")
    assert clap_host.find_clap_files([str(tmp_path), "/non/esiste"]) == [str(nested / "Other.clap")]


def test_parameters(clap_file):
    inst = clap_host.ClapInstance(clap_file + "|test.soundtext.gain", RATE)
    gain, mode = inst.params
    assert (gain.key, gain.name, gain.minimum, gain.maximum, gain.default) == ("100", "Gain", 0.0, 2.0, 1.0)
    assert not gain.integer and not gain.toggled and gain.choices == []
    assert mode.key == "200" and mode.integer and mode.choices == [(0.0, "Normal"), (1.0, "Invert")]
    inst.close()


def test_effect_with_latency_compensated(clap_file):
    inst = clap_host.ClapInstance(clap_file + "|test.soundtext.gain", RATE)
    assert inst.latency == 32
    x = _sine()
    inst.set_values({})
    assert np.allclose(inst.process(x), x, atol=1e-6)            # guadagno 1, e nessun ritardo
    inst.set_values({"100": 0.5})
    inst.reset()
    assert np.allclose(inst.process(x), 0.5 * x, atol=1e-6)
    inst.set_values({"100": 0.5, "200": 1.0})
    inst.reset()
    assert np.allclose(inst.process(x), -0.5 * x, atol=1e-6)
    inst.set_values({})                                           # i non nominati tornano al predefinito
    inst.reset()
    assert np.allclose(inst.process(x), x, atol=1e-6)
    inst.set_values({"100": 99.0, "boh": 1.0})                    # fuori scala: limitato; sconosciuto: ignorato
    inst.reset()
    assert np.allclose(inst.process(x), 2.0 * x, atol=1e-6)
    inst.close()


def test_instrument_from_midi_events(clap_file):
    inst = clap_host.ClapInstance(clap_file + "|test.soundtext.sine", RATE)
    assert inst.info.instrument and inst.params == []
    events = [(0.1, bytes([0x90, 69, 100])), (0.4, bytes([0x80, 69, 0]))]
    y = inst.render(events, 0.6)
    assert y.shape == (int(0.6 * RATE), 2)
    assert np.all(y[:int(0.1 * RATE) - 1] == 0) and np.all(y[int(0.4 * RATE) + 1:] == 0)
    note = y[int(0.1 * RATE):int(0.4 * RATE), 0]
    spectrum = np.abs(np.fft.rfft(note * np.hanning(len(note))))
    assert abs(np.argmax(spectrum) * RATE / len(note) - 440.0) < 4.0
    assert np.max(np.abs(note)) == pytest.approx(0.25, abs=0.01)
    inst.reset()
    assert np.array_equal(inst.render(events, 0.6), y)             # stesso brano, stesso suono
    inst.close()


def test_missing_file_and_missing_plugin(clap_file, tmp_path):
    with pytest.raises(clap_host.ClapError):
        clap_host.ClapInstance(str(tmp_path / "niente.clap"), RATE)
    with pytest.raises(clap_host.ClapError):
        clap_host.ClapInstance(clap_file + "|non.esiste", RATE)
    bogus = tmp_path / "bogus.clap"
    bogus.write_bytes(b"non e' una libreria")
    with pytest.raises(clap_host.ClapError):
        clap_host.list_clap_plugins(str(bogus))


def test_through_the_plugin_process(clap_file, monkeypatch):
    """Ricerca, descrizione, effetto e strumento come li usa SoundText."""
    folder = os.path.dirname(clap_file)
    monkeypatch.setattr(clap_host, "default_clap_dirs", lambda: [folder])
    monkeypatch.setattr(plugins, "find_vst3_bundles", lambda dirs=None: [])
    monkeypatch.setattr(plugins, "find_au_bundles", lambda dirs=None: [])
    plugins.forget_scan()
    try:
        found = {i.name: i for i in plugins.scan_plugins(refresh=True) if i.format == "clap"}
        assert set(found) == {"Test Gain", "Test Sine", "Test Notes"}
        gain, sine = found["Test Gain"], found["Test Sine"]
        assert gain.format_label == "CLAP" and gain.usable and not gain.instrument
        assert sine.instrument and not found["Test Notes"].usable
        described = plugins.describe(gain.ref)
        assert [(p.key, p.label) for p in described.params] == [("100", "Gain"), ("200", "Mode")]
        assert described.params[1].choices == [(0.0, "Normal"), (1.0, "Invert")]
        x = _sine(0.25)
        assert np.allclose(plugins.process_audio(gain.ref, {"100": 0.25}, "", x, RATE), 0.25 * x, atol=1e-6)
        assert np.allclose(plugins.process_audio(gain.ref, {}, "", x, RATE), x, atol=1e-6)
        y = plugins.render_events(sine.ref, {}, "", [(0.0, bytes([0x90, 60, 90])), (0.2, bytes([0x80, 60, 0]))],
                                  0.3, RATE)
        assert y.shape == (int(0.3 * RATE), 2) and np.max(np.abs(y)) == pytest.approx(0.25, abs=0.01)
        assert plugins.display_name(gain.ref) == "Test Gain"
        assert plugins.signature(gain.ref, {"100": 0.5}, "")[1] > 0
    finally:
        plugins.forget_scan()


def test_clap_outside_the_plugin_folders_is_refused(clap_file, monkeypatch):
    """Un .clap e' codice: si carica solo dalle cartelle dei plugin."""
    monkeypatch.setattr(clap_host, "default_clap_dirs", lambda: ["/non/esiste"])
    monkeypatch.setattr(plugins, "plugin_dirs", lambda: ["/non/esiste"])
    with pytest.raises(plugins.PluginError):
        plugins.process_audio(f"clap:{clap_file}|test.soundtext.gain", {}, "", _sine(0.1), RATE)
