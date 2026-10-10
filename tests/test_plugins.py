"""
Test per i plugin esterni (core.plugins, core.plugin_worker, core.lv2_host):
processo separato con tempo massimo, plugin LV2 installati (Ardour/ACE,
Guitarix, sfizz con il suo file SFZ: si saltano se mancano), strumento plugin di una traccia, effetto
plugin nella catena, salvataggio nel file .st e finestre della GUI.

I VST3 si provano solo se la variabile SOUNDTEXT_TEST_VST3_DIR indica una
cartella con dei plugin VST3 (per esempio i DISTRHO di dpf-plugins-vst3).

Esecuzione:
    python3 -m pytest tests/test_plugins.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from core import plugins
from core.lv2_host import lv2_available, lv2_plugin_info
from core.model import Effect, Project
from core.plugin_worker import parse_ref
from core.project_io import parse_project_text, project_to_text

A_DELAY = "lv2:urn:ardour:a-delay"
SYNTH = "lv2:https://community.ardour.org/node/7596"      # ACE Reasonable Synth
SFIZZ = "lv2:http://sfztools.github.io/sfizz"
RATE = 48000


def _has_lv2(ref):
    return lv2_available() and lv2_plugin_info(parse_ref(ref)[1]) is not None


needs_delay = pytest.mark.skipif(not _has_lv2(A_DELAY), reason="plugin LV2 ACE Delay non installato")
needs_synth = pytest.mark.skipif(not _has_lv2(SYNTH), reason="plugin LV2 ACE Reasonable Synth non installato")
needs_sfizz = pytest.mark.skipif(not _has_lv2(SFIZZ), reason="plugin LV2 sfizz non installato")
VST3_DIR = os.environ.get("SOUNDTEXT_TEST_VST3_DIR", "")
needs_vst3 = pytest.mark.skipif(not os.path.isdir(VST3_DIR), reason="SOUNDTEXT_TEST_VST3_DIR non impostata")


@pytest.fixture(autouse=True, scope="module")
def _stop_hosts():
    yield
    plugins.shutdown()


def _rms(x):
    return float(np.sqrt(np.mean(np.square(x)))) if len(x) else 0.0


def _tone(seconds=1.0, freq=220.0):
    t = np.arange(int(seconds * RATE)) / RATE
    return np.stack([0.4 * np.sin(2 * np.pi * freq * t)] * 2, axis=1).astype(np.float32)


# ------------------------------------------------------------------ riferimenti

def test_parse_ref_and_display_name():
    assert parse_ref("vst3:/a/b/MVerb.vst3") == ("vst3", "/a/b/MVerb.vst3", None)
    assert parse_ref("vst3:/a/Shell.vst3|Uno") == ("vst3", "/a/Shell.vst3", "Uno")
    assert parse_ref("lv2:urn:ardour:a-delay") == ("lv2", "urn:ardour:a-delay", None)
    assert plugins.display_name("vst3:/x/y/MVerb.vst3") == "MVerb"
    assert plugins.display_name("vst3:/x/Shell.vst3|Uno") == "Uno"
    assert plugins.display_name("") == ""


def test_moved_vst3_is_found_by_file_name(tmp_path, monkeypatch):
    bundle = tmp_path / "Eco.vst3"
    bundle.mkdir()
    monkeypatch.setattr(plugins, "vst3_dirs", lambda: [str(tmp_path)])
    assert plugins.find_vst3_bundles() == [str(bundle)]
    assert plugins.resolve_ref("vst3:/altro/computer/Eco.vst3") == "vst3:" + str(bundle)
    assert plugins.resolve_ref("vst3:/altro/Sconosciuto.vst3") == "vst3:/altro/Sconosciuto.vst3"


def test_vst3_outside_the_plugin_folders_is_not_loaded(tmp_path, monkeypatch):
    """Un .st ricevuto da altri non puo' far caricare un VST3 da un percorso
    qualsiasi: solo dalle cartelle dei plugin (o, per nome, da li')."""
    dirs = tmp_path / "plugins"
    dirs.mkdir()
    (dirs / "Buono.vst3").mkdir()
    other = tmp_path / "scaricati"
    other.mkdir()
    (other / "Strano.vst3").mkdir()
    (other / "Buono.vst3").mkdir()
    monkeypatch.setattr(plugins, "vst3_dirs", lambda: [str(dirs)])
    calls = []
    monkeypatch.setitem(plugins._hosts, "ui", type("H", (), {"call": lambda self, r, t: calls.append(r)})())
    with pytest.raises(plugins.PluginError):
        plugins.describe("vst3:" + str(other / "Strano.vst3"))
    assert calls == []                                   # il processo dei plugin non l'ha mai visto
    # lo stesso nome di un plugin installato si usa da la' (come per un progetto spostato)
    assert plugins.resolve_ref("vst3:" + str(other / "Buono.vst3")) == "vst3:" + str(dirs / "Buono.vst3")
    assert plugins.in_plugin_dirs(str(dirs / "Buono.vst3"))


# ------------------------------------------------------------------ processo separato

def test_hanging_plugin_times_out_and_host_restarts():
    host = plugins._Host("prova")
    try:
        assert host.call(("ping",), 20) == "pong"
        start = time.monotonic()
        with pytest.raises(plugins.PluginError, match="non risponde"):
            host.call(("_sleep", 30), 1.0)
        assert time.monotonic() - start < 10
        assert host.call(("ping",), 20) == "pong"          # un processo nuovo
    finally:
        host.stop()


def test_crashing_plugin_does_not_take_down_the_app():
    host = plugins._Host("prova")
    try:
        with pytest.raises(plugins.PluginError, match="anomalo"):
            host.call(("_crash",), 20)
        assert host.call(("ping",), 20) == "pong"
    finally:
        host.stop()


def test_plugin_that_stopped_responding_is_remembered(monkeypatch):
    calls = []

    def fake(request, timeout):
        calls.append(request)
        raise plugins.PluginError("il plugin non risponde", fatal=True)
    monkeypatch.setattr(plugins._hosts["ui"], "call", fake)
    ref = "vst3:/nessuno/Bloccato.vst3"
    for _ in range(2):
        with pytest.raises(plugins.PluginError):
            plugins.describe(ref)
    assert len(calls) == 1 and plugins.broken_reason(ref) == "il plugin non risponde"
    plugins._broken.pop(ref, None)


def test_errors_of_the_plugin_come_back_as_text():
    with pytest.raises(plugins.PluginError, match="non trovato"):
        plugins.describe("vst3:/percorso/che/non/esiste.vst3")


# ------------------------------------------------------------------ LV2

@needs_delay
def test_scan_lists_lv2_effects_and_instruments():
    found = {i.ref: i for i in plugins.scan_plugins(refresh=True)}
    assert A_DELAY in found and not found[A_DELAY].instrument and found[A_DELAY].usable
    if _has_lv2(SYNTH):
        assert found[SYNTH].instrument


@needs_delay
def test_lv2_effect_describe_and_process():
    info = plugins.describe(A_DELAY)
    assert info.format == "lv2" and info.params
    x = np.concatenate([_tone(0.3), np.zeros((RATE, 2), dtype=np.float32)])
    y = plugins.process_audio(A_DELAY, {}, "", x, RATE)
    assert y.shape == x.shape and np.isfinite(y).all()
    assert _rms(y[int(0.4 * RATE):]) > 1e-4 > _rms(x[int(0.4 * RATE):])      # le ripetizioni del delay


@needs_synth
def test_lv2_instrument_renders_midi_events():
    events = [(0.1, bytes([0x90, 60, 100])), (0.6, bytes([0x80, 60, 0]))]
    y = plugins.render_events(SYNTH, {}, "", events, 1.0, RATE)
    assert y.shape == (RATE, 2)
    assert _rms(y[:int(0.09 * RATE)]) < 1e-4 < _rms(y[int(0.15 * RATE):int(0.55 * RATE)])


@needs_delay
def test_plugin_effect_in_the_chain_and_mix():
    from core.effects import apply_effect_chain
    x = _tone(0.5)
    wet = apply_effect_chain(x, RATE, [Effect("plugin", {"mix": 100, "livello": 0}, plugin=A_DELAY)])
    dry = apply_effect_chain(x, RATE, [Effect("plugin", {"mix": 0, "livello": 0}, plugin=A_DELAY)])
    assert len(wet) > len(x)                                   # coda delle ripetizioni
    np.testing.assert_allclose(dry[:len(x)], x, atol=1e-4)


def test_missing_plugin_lets_the_sound_through():
    from core.effects import apply_effect_chain
    x = _tone(0.2)
    y = apply_effect_chain(x, RATE, [Effect("plugin", {"mix": 100, "livello": 0}, plugin="lv2:urn:non:esiste")],
                           with_tail=False)
    np.testing.assert_allclose(y, x, atol=1e-6)


@needs_synth
def test_track_played_by_a_plugin_instrument():
    from core.effect_render import clear_stem_cache, fx_tracks
    from core.playback import render_project_mix
    clear_stem_cache()
    p = Project(name="prova")
    track = p.add_track("Synth", "Piano", "4: c*4 e*4 g*4 c*5")
    track.synth = SYNTH
    assert fx_tracks(p.tracks) == [track]
    y, rate = render_project_mix(p)
    assert rate == RATE and _rms(y) > 1e-3
    track.pan = 0                                            # tutto a sinistra
    y_left, _ = render_project_mix(p)
    assert _rms(y_left[:, 1]) < 1e-6 < _rms(y_left[:, 0])


def test_broken_instrument_falls_back_to_the_soundfont(monkeypatch):
    from core import effect_render
    from core.effect_render import prepare_stem, render_dry
    from core.tempo_map import build_tempo_beat_map
    p = Project(name="prova")
    track = p.add_track("Synth", "Piano", "4: c*4 e*4")
    track.synth = "lv2:urn:non:esiste"
    request = prepare_stem(p, track, build_tempo_beat_map(p))
    fallback = np.ones((10, 2), dtype=np.float32)
    monkeypatch.setattr("core.playback.render_midi_file_to_samples", lambda *a, **k: (fallback, RATE))
    try:
        np.testing.assert_array_equal(render_dry(request), fallback)
    finally:
        request.cleanup()
        effect_render.clear_stem_cache()


# ------------------------------------------------------------------ file .st

def test_plugins_are_saved_in_the_project_file():
    p = Project(name="prova")
    t = p.add_track("Synth", "Piano", "4: c d e f")
    t.synth, t.synth_params, t.synth_state = SYNTH, {"gain": 0.5}, ""
    t.effects = [Effect("plugin", {"mix": 80, "livello": -3}, True, "", plugin=A_DELAY,
                        plugin_params={"time": 250.0}, plugin_state="QUJD+/=")]
    text = project_to_text(p)
    assert "Plugin Synth:" in text
    q = parse_project_text(text, "prova").get_track("Synth")
    assert (q.synth, q.synth_params) == (SYNTH, {"gain": 0.5})
    e = q.effects[0]
    assert (e.kind, e.params, e.plugin, e.plugin_params, e.plugin_state) == \
        ("plugin", {"mix": 80.0, "livello": -3.0}, A_DELAY, {"time": 250.0}, "QUJD+/=")
    assert project_to_text(parse_project_text(text, "prova")) == text


def test_lv2_files_state_round_trip_and_project_file():
    from core.lv2_host import decode_state, encode_state
    files = {"urn:x:file": "/tmp/Mio \"strumento\" à.sfz"}
    state = encode_state(files)
    assert decode_state(state) == files and not set(state) & set('" ')
    assert encode_state({"urn:x:file": ""}) == "" and decode_state("") == {}
    assert decode_state("non-base64!") == {}
    p = Project(name="prova")
    t = p.add_track("Synth", "Piano", "4: c d e f")
    t.synth, t.synth_state = SFIZZ, state
    q = parse_project_text(project_to_text(p), "prova").get_track("Synth")
    assert decode_state(q.synth_state) == files


# ------------------------------------------------------------------ sfizz LV2 (file SFZ)

def _sfz(tmp_path, sample):
    path = tmp_path / f"{sample.strip('*')}.sfz"
    path.write_text(f"<region> sample={sample}\n")
    return str(path)


@needs_sfizz
def test_lv2_file_property_loads_the_sfz(tmp_path):
    from core.lv2_host import encode_state
    info = plugins.describe(SFIZZ)
    sfz_key = next(f.key for f in info.files if f.key.endswith("sfzfile"))
    events = [(0.0, bytes([0x90, 60, 100])), (0.5, bytes([0x80, 60, 0]))]
    default = plugins.render_events(SFIZZ, {}, "", events, 0.6, RATE)
    state = encode_state({sfz_key: _sfz(tmp_path, "*silence")})
    silent = plugins.render_events(SFIZZ, {}, state, events, 0.6, RATE)
    again = plugins.render_events(SFIZZ, {}, "", events, 0.6, RATE)        # file tolto
    assert _rms(default) > 0.05 and _rms(silent) < 1e-4 and _rms(again) > 0.05
    assert plugins.signature(SFIZZ, {}, state) != plugins.signature(SFIZZ, {}, "")


@needs_sfizz
def test_params_dialog_chooses_the_lv2_file(tmp_path):
    _app()
    from core.lv2_host import decode_state
    from gui.plugin_dialogs import PluginParamsDialog
    changes = []
    dialog = PluginParamsDialog(None, SFIZZ, {}, "", on_change=lambda params, state: changes.append(state))
    sfz_key = next(k for k in dialog.file_rows if k.endswith("sfzfile"))
    path = _sfz(tmp_path, "*sine")
    dialog.file_rows[sfz_key]._emit(path)
    dialog.accept()
    assert decode_state(changes[-1]) == {sfz_key: path}
    dialog = PluginParamsDialog(None, SFIZZ, {}, changes[-1], on_change=lambda params, state: changes.append(state))
    assert dialog.file_rows[sfz_key].path_edit.text() == path
    dialog.reset_defaults()
    assert changes[-1] == "" and dialog.file_rows[sfz_key].path_edit.text() == ""
    dialog.reject()


# ------------------------------------------------------------------ VST3 (opzionali)

@needs_vst3
def test_vst3_effects_from_the_test_folder(monkeypatch):
    monkeypatch.setattr(plugins, "vst3_dirs", lambda: [VST3_DIR])
    effects = [i for i in plugins.scan_plugins(refresh=True) if i.format == "vst3" and i.usable
               and not i.instrument]
    assert effects
    info = plugins.describe(effects[0].ref)
    y = plugins.process_audio(info.ref, {}, info.state, _tone(0.3), RATE)
    assert y.shape == (int(0.3 * RATE), 2) and np.isfinite(y).all()
    if info.params:
        key = info.params[0].key
        assert key in plugins.parameter_texts(info.ref, {key: 1.0}, "")


# ------------------------------------------------------------------ GUI

def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@needs_delay
def test_effects_panel_adds_a_plugin_and_edits_its_parameters():
    _app()
    from gui.main_window import MainWindow
    from gui.plugin_dialogs import PluginParamsDialog
    w = MainWindow()
    w.project.add_track("Chitarra", "Guitar", "4: E A")
    w.refresh_mixer()
    w.open_effects_panel("Chitarra")
    panel = w.effects_panel
    panel.choose_plugin = lambda current="": ""
    panel.add_effect("plugin")                                          # annullato
    assert w.project.get_track("Chitarra").effects == []
    panel.choose_plugin = lambda current="": A_DELAY
    panel.add_effect("plugin")
    effect = w.project.get_track("Chitarra").effects[0]
    card = panel.cards[0]
    assert effect.plugin == A_DELAY
    assert plugins.display_name(A_DELAY) in card.plugin_label.text() and "LV2" in card.plugin_label.text()
    changes = []
    dialog = PluginParamsDialog(w, effect.plugin, effect.plugin_params, effect.plugin_state,
                                on_change=lambda params, state: changes.append(params))
    row = next(iter(dialog.rows.values()))
    other = row.param.maximum if row.param.default != row.param.maximum else row.param.minimum
    row.set_value(other)
    row._emit(other)
    dialog.accept()
    assert changes and changes[-1] == {row.param.key: other}
    dialog = PluginParamsDialog(w, effect.plugin, {row.param.key: other}, "",
                                on_change=lambda params, state: changes.append(params))
    dialog.reject()                                                     # Annulla: si torna a prima
    assert changes[-1] == {row.param.key: other}
    panel.close_panel()


@needs_synth
def test_track_menu_sets_the_plugin_instrument(monkeypatch):
    _app()
    from PySide6.QtWidgets import QDialog
    from gui import plugin_dialogs
    from gui.main_window import MainWindow
    w = MainWindow()
    w.project.add_track("Synth", "Piano", "4: c d e f")
    w.refresh_mixer()
    w._mark_dirty()                                   # la traccia aggiunta e' il punto di partenza

    class FakePicker:
        Accepted = QDialog.Accepted

        def __init__(self, *a, **k):
            pass

        def exec(self):
            return QDialog.Accepted

        def selected_ref(self):
            return SYNTH
    monkeypatch.setattr(plugin_dialogs, "PluginPickerDialog", FakePicker)
    monkeypatch.setattr(plugin_dialogs.PluginParamsDialog, "exec", lambda self: QDialog.Accepted)
    w.choose_track_synth("Synth")
    track = w.project.get_track("Synth")
    assert track.synth == SYNTH
    assert "(plugin)" in w.track_headers["Synth"].instr_label.toolTip() + w.track_headers["Synth"].instr_label.text()
    w.undo()
    assert w.project.get_track("Synth").synth == ""


@needs_vst3
def test_vst3_instrument_from_the_test_folder(monkeypatch):
    monkeypatch.setattr(plugins, "vst3_dirs", lambda: [VST3_DIR])
    synths = [i for i in plugins.scan_plugins(refresh=True) if i.format == "vst3" and i.usable and i.instrument]
    if not synths:
        pytest.skip("nessuno strumento VST3 utilizzabile nella cartella di prova")
    events = [(0.1, bytes([0x90, 60, 100])), (0.6, bytes([0x80, 60, 0]))]
    y = plugins.render_events(synths[0].ref, {}, "", events, 1.0, RATE)
    assert y.shape == (RATE, 2) and _rms(y[int(0.15 * RATE):int(0.55 * RATE)]) > 1e-3


# ------------------------------------------------------------------ ricerca: plugin che non si erano potuti usare

def _fake_scan(monkeypatch, tmp_path, results):
    """scan_plugins con un bundle finto: 'results' sono le descrizioni che
    si danno a ogni caricamento, una per volta."""
    bundle = str(tmp_path / "Surge XT Effects.vst3")
    os.makedirs(bundle)
    calls = []

    def describe(path):
        calls.append(path)
        return [results[min(len(calls), len(results)) - 1]]
    monkeypatch.setattr(plugins, "find_vst3_bundles", lambda dirs=None: [bundle])
    monkeypatch.setattr(plugins, "_describe_bundle", describe)
    monkeypatch.setattr(plugins, "_hosts", {**plugins._hosts, "ui": type("NoLv2", (), {
        "call": staticmethod(lambda request, timeout: [])})()})
    monkeypatch.setattr(plugins, "_scan_cache_path", lambda: str(tmp_path / "cache.json"))
    plugins.forget_scan()
    return calls


def _effect(problem=""):
    return {"ref": "vst3:x", "format": "vst3", "name": "Surge XT Effects", "vendor": "Surge Synth Team",
            "category": "Fx", "instrument": False, "problem": problem}


def test_a_plugin_that_did_not_answer_is_tried_again(monkeypatch, tmp_path):
    calls = _fake_scan(monkeypatch, tmp_path, [_effect("il plugin non risponde"), _effect()])
    assert not plugins.scan_plugins()[0].usable
    plugins.forget_scan()
    assert plugins.scan_plugins()[0].usable           # riprovato da solo alla ricerca dopo
    plugins.forget_scan()
    plugins.scan_plugins()
    assert len(calls) == 2                            # una volta usabile, resta in memoria
    plugins.forget_scan()


def test_search_again_retries_plugins_with_an_error(monkeypatch, tmp_path):
    calls = _fake_scan(monkeypatch, tmp_path, [_effect("errore del plugin"), _effect()])
    assert not plugins.scan_plugins()[0].usable
    plugins.forget_scan()
    assert not plugins.scan_plugins()[0].usable       # un errore normale non si ritenta da solo...
    assert plugins.scan_plugins(refresh=True)[0].usable   # ...ma con «Cerca di nuovo» si'
    assert len(calls) == 2
    plugins.forget_scan()


# ------------------------------------------------------------------ Windows: perche' un VST3 non si carica

def _pe(path, machine):
    """Una finta DLL: intestazione MZ, offset del PE a 0x3C, firma e Machine."""
    data = bytearray(512)
    data[0:2] = b"MZ"
    data[0x3C:0x40] = (0x80).to_bytes(4, "little")
    data[0x80:0x84] = b"PE\0\0"
    data[0x84:0x86] = machine.to_bytes(2, "little")
    with open(path, "wb") as f:
        f.write(bytes(data))


def test_pe_machine_and_bundle_binary(tmp_path):
    from core.plugin_worker import pe_machine, vst3_binary
    bundle = tmp_path / "Surge XT Effects.vst3"
    (bundle / "Contents" / "x86_64-win").mkdir(parents=True)
    dll = bundle / "Contents" / "x86_64-win" / "Surge XT Effects.vst3"
    _pe(dll, 0x8664)
    assert pe_machine(str(dll)) == "x64"
    assert vst3_binary(str(bundle), "AMD64") == (str(dll), ["x86_64-win"])
    assert vst3_binary(str(bundle), "x86")[0] is None


def test_windows_diagnosis_names_the_architecture(tmp_path, monkeypatch):
    import platform
    from core import plugin_worker
    monkeypatch.setattr(platform, "machine", lambda: "AMD64")
    only_arm = tmp_path / "Solo ARM.vst3"
    (only_arm / "Contents" / "arm64-win").mkdir(parents=True)
    _pe(only_arm / "Contents" / "arm64-win" / "Solo ARM.vst3", 0xAA64)
    assert "arm64-win" in plugin_worker.windows_load_diagnosis(str(only_arm))
    old32 = tmp_path / "Vecchio.vst3"
    _pe(old32, 0x014C)                                     # VST3 "a file singolo" a 32 bit
    assert "32 bit" in plugin_worker.windows_load_diagnosis(str(old32))


def test_same_folder_written_twice_gives_each_plugin_once(tmp_path):
    (tmp_path / "Surge Synth Team" / "Surge XT.vst3").mkdir(parents=True)
    (tmp_path / "Surge Synth Team" / "Surge XT Effects.vst3").mkdir(parents=True)
    twice = [str(tmp_path), str(tmp_path) + os.sep, os.path.join(str(tmp_path), "Surge Synth Team", "..")]
    found = plugins.find_vst3_bundles(twice)
    assert [os.path.basename(p) for p in found] == ["Surge XT Effects.vst3", "Surge XT.vst3"]


def test_editor_window_is_moved_where_its_title_bar_is_visible():
    """Windows: l'interfaccia di un plugin che compare con la barra del titolo
    fuori dallo schermo si centra nell'area di lavoro (vedi editor_position)."""
    from core.plugin_worker import editor_position
    work = (0, 0, 1920, 1040)                                    # schermo meno la barra delle applicazioni
    assert editor_position((100, 100, 900, 700), work) is None   # gia' visibile: resta dov'e'
    assert editor_position((-8, -31, 792, 569), work) == (560, 220)   # titolo sopra lo schermo: centrata
    assert editor_position((0, -20, 2400, 1300), work) == (0, 0)      # piu' grande dello schermo: in alto a sinistra
    assert editor_position((1500, 900, 2300, 1500), (1920, 0, 3840, 1080)) == (2480, 240)   # secondo monitor
