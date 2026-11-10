"""
Test per i plugin Audio Unit (AU, solo macOS; vedi core.plugins e
core.plugin_worker): riferimento "au:", ricerca dei bundle .component,
caricamento con pedalboard.AudioUnitPlugin, brani con un AU aperti fuori
da macOS, cache della ricerca, AU che esistono anche in VST3.

Girano su tutti i sistemi con un AudioUnitPlugin finto; l'ultimo test
carica un AU vero ed e' saltato fuori da macOS (o se pedalboard non ha
AudioUnitPlugin).

Esecuzione:
    python3 -m pytest tests/test_plugins_au.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from core import plugin_worker, plugins
from core.model import Effect, Project
from core.plugin_worker import _Worker, is_pedalboard_format, parse_ref
from core.project_io import parse_project_text, project_to_text

RATE = 48000


@pytest.fixture(autouse=True, scope="module")
def _stop_hosts():
    yield
    plugins.shutdown()


def _tone(seconds=0.2, freq=220.0):
    t = np.arange(int(seconds * RATE)) / RATE
    return np.stack([0.4 * np.sin(2 * np.pi * freq * t)] * 2, axis=1).astype(np.float32)


# ------------------------------------------------------------------ un AudioUnitPlugin finto

class _Param:
    def __init__(self, name, value):
        self.name, self.raw_value, self.units = name, value, "dB"
        self.valid_values = None
        self.type = float

    @property
    def string_value(self):
        return f"{self.raw_value:.2f}"


class FakeAU:
    """Come pedalboard.AudioUnitPlugin, quanto basta: un effetto che dimezza
    il segnale, o uno strumento che suona un'onda costante per ogni nota."""
    loaded = []

    def __init__(self, path, plugin_name=None):
        FakeAU.loaded.append((path, plugin_name))
        self.name = plugin_name or os.path.splitext(os.path.basename(path))[0]
        self.manufacturer_name = "Finto"
        self.is_instrument = "Synth" in self.name
        self.category = "Synth" if self.is_instrument else "Effect"
        self.parameters = {"gain": _Param("Gain", 0.5)}
        self.raw_state = b"stato"

    @staticmethod
    def get_plugin_names_for_file(path):
        return ["Uno", "Due"] if "Doppio" in path else [os.path.splitext(os.path.basename(path))[0]]

    def process(self, data, sample_rate=None, duration=None, num_channels=2, buffer_size=None, reset=True):
        if isinstance(data, np.ndarray):                     # effetto: (canali, frame)
            return data * 0.5
        frames = int(round(duration * sample_rate))          # strumento: messaggi MIDI
        level = 0.1 if data else 0.0
        return np.full((num_channels, frames), level, dtype=np.float32)

    def reset(self):
        pass


def _pretend_macos(monkeypatch, value: bool):
    """Come se SoundText girasse (o no) su macOS, senza toccare sys.platform:
    cambiarlo in tutto il processo rompe altre librerie (sysconfig su Linux)."""
    monkeypatch.setattr(plugin_worker, "running_on_macos", lambda: value)


@pytest.fixture
def fake_pedalboard(monkeypatch, tmp_path):
    """pedalboard con AudioUnitPlugin finto, "su macOS"; torna la cartella
    dei bundle."""
    module = types.ModuleType("pedalboard")
    module.AudioUnitPlugin = FakeAU
    monkeypatch.setitem(sys.modules, "pedalboard", module)
    _pretend_macos(monkeypatch, True)
    FakeAU.loaded = []
    folder = tmp_path / "Components"
    folder.mkdir()
    return folder


def _bundle(folder, name):
    path = folder / f"{name}.component"
    (path / "Contents").mkdir(parents=True)
    return str(path)


# ------------------------------------------------------------------ riferimento au:

def test_parse_ref_label_and_display_name():
    home = os.path.expanduser("~")
    fmt, path, name = parse_ref("au:~/Library/Audio/Plug-Ins/Components/X.component|Nome")
    assert (fmt, name) == ("au", "Nome")
    assert path == os.path.normpath(os.path.join(home, "Library/Audio/Plug-Ins/Components/X.component"))
    assert parse_ref("au:/L/Eco.component") == ("au", "/L/Eco.component", None)
    assert plugins.display_name("au:/L/TAL-Reverb-4.component") == "TAL-Reverb-4"
    assert plugins.display_name("au:/L/Doppio.component|Due") == "Due"
    assert plugins.PluginInfo(ref="au:/x", format="au", name="x").format_label == "AU"
    assert is_pedalboard_format("au") and is_pedalboard_format("vst3") and not is_pedalboard_format("lv2")


# ------------------------------------------------------------------ ricerca dei bundle

def test_find_au_bundles_only_takes_component_folders(tmp_path, monkeypatch):
    _bundle(tmp_path, "Uno")
    _bundle(tmp_path, "Due")
    (tmp_path / "leggimi.txt").write_text("x")
    (tmp_path / "finto.component").mkdir()
    (tmp_path / "Uno.component" / "Contents" / "Annidato.component").mkdir()     # dentro un bundle no
    (tmp_path / "file.component.txt").write_text("x")
    found = plugins.find_au_bundles([str(tmp_path)])
    assert [os.path.basename(p) for p in found] == ["Due.component", "Uno.component", "finto.component"]
    _pretend_macos(monkeypatch, False)
    assert plugins.default_au_dirs() == [] and plugins.au_dirs() == [] and plugins.find_au_bundles() == []
    _pretend_macos(monkeypatch, True)
    assert "/Library/Audio/Plug-Ins/Components" in plugins.default_au_dirs()


def test_au_from_an_unknown_folder_is_not_loaded(fake_pedalboard, tmp_path, monkeypatch):
    other = tmp_path / "scaricati"
    other.mkdir()
    strano = _bundle(other, "Strano")
    monkeypatch.setattr(plugins, "default_au_dirs", lambda: [str(fake_pedalboard)])
    calls = []
    monkeypatch.setitem(plugins._hosts, "ui", type("H", (), {"call": lambda self, r, t: calls.append(r)})())
    with pytest.raises(plugins.PluginError):
        plugins.describe("au:" + strano)
    assert calls == []
    # lo stesso nome nella cartella dei plugin: un brano spostato da un altro Mac
    buono = _bundle(fake_pedalboard, "Buono")
    assert plugins.resolve_ref("au:/altro/Mac/Buono.component|X") == "au:" + buono + "|X"


# ------------------------------------------------------------------ il processo dei plugin

def test_worker_uses_the_vst3_paths_for_au(fake_pedalboard):
    effect = "au:" + _bundle(fake_pedalboard, "Eco")
    synth = "au:" + _bundle(fake_pedalboard, "Doppio") + "|Synth"
    worker = _Worker()
    d = worker.describe(effect)
    assert (d["format"], d["name"], d["vendor"], d["instrument"]) == ("au", "Eco", "Finto", False)
    assert [p["key"] for p in d["params"]] == ["gain"] and d["state"]
    assert worker.strings(effect, {"gain": 0.25}, "") == {"gain": "0.25"}
    x = _tone()
    np.testing.assert_allclose(worker.process(effect, RATE, {}, "", x), x * 0.5, atol=1e-6)
    y = worker.render(synth, RATE, {}, "", [(0.0, b"\x90\x3c\x64")], 0.1)
    assert y.shape == (int(0.1 * RATE), 2) and float(np.max(y)) > 0
    assert (FakeAU.loaded[-1][1]) == "Synth"                  # il nome dopo "|" arriva a pedalboard
    assert worker.handle(("au_names", str(fake_pedalboard / "Doppio.component"))) == ["Uno", "Due"]


def test_without_audiounitplugin_the_message_says_macos_only(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "pedalboard", types.ModuleType("pedalboard"))
    with pytest.raises(RuntimeError, match="solo su macOS"):
        _Worker().describe("au:" + _bundle(tmp_path, "Eco"))


def test_au_bundle_with_several_plugins_gets_one_ref_each(fake_pedalboard, monkeypatch):
    bundle = _bundle(fake_pedalboard, "Doppio")
    worker = _Worker()
    monkeypatch.setitem(plugins._hosts, "ui", type("H", (), {"call": lambda self, r, t: worker.handle(r)})())
    infos = plugins._describe_au_bundle(bundle)
    assert [(d["ref"], d["name"], d["format"]) for d in infos] == \
        [("au:" + bundle + "|Uno", "Uno", "au"), ("au:" + bundle + "|Due", "Due", "au")]
    single = _bundle(fake_pedalboard, "Eco")
    assert [d["ref"] for d in plugins._describe_au_bundle(single)] == ["au:" + single]


# ------------------------------------------------------------------ brani aperti fuori da macOS

def test_song_with_an_au_opened_elsewhere_plays_without_it(monkeypatch):
    from core.effects import apply_effect_chain
    _pretend_macos(monkeypatch, False)
    ref = "au:/Library/Audio/Plug-Ins/Components/TAL-Reverb-4.component"
    assert "Audio Unit" in plugins.broken_reason(ref)
    with pytest.raises(plugins.PluginError, match="Audio Unit"):
        plugins.describe(ref)
    x = _tone()
    y = apply_effect_chain(x, RATE, [Effect("plugin", {"mix": 100, "livello": 0}, plugin=ref)], with_tail=False)
    np.testing.assert_allclose(y, x, atol=1e-6)
    # il riferimento, i parametri e lo stato restano nel file
    p = Project(name="prova")
    t = p.add_track("Chitarra", "Piano", "4: c d e f")
    t.effects = [Effect("plugin", {"mix": 80, "livello": 0}, True, "", plugin=ref,
                        plugin_params={"gain": 0.25}, plugin_state="QUJD")]
    text = project_to_text(p)
    e = parse_project_text(text, "prova").get_track("Chitarra").effects[0]
    assert (e.plugin, e.plugin_params, e.plugin_state) == (ref, {"gain": 0.25}, "QUJD")
    assert project_to_text(parse_project_text(text, "prova")) == text


# ------------------------------------------------------------------ cache della ricerca

def test_scan_caches_au_and_does_not_load_them_again(fake_pedalboard, monkeypatch, tmp_path):
    bundle = _bundle(fake_pedalboard, "Eco")
    calls = []

    def describe(path):
        calls.append(path)
        return [{"ref": "au:" + path, "format": "au", "name": "Eco", "vendor": "Finto", "category": "Effect",
                 "instrument": False, "problem": ""}]
    monkeypatch.setattr(plugins, "find_vst3_bundles", lambda dirs=None: [])
    monkeypatch.setattr(plugins, "find_au_bundles", lambda dirs=None: [bundle])
    monkeypatch.setattr(plugins, "_describe_au_bundle", describe)
    monkeypatch.setattr(plugins, "_describe_bundle", lambda b: pytest.fail("un AU non e' un VST3"))
    monkeypatch.setattr(plugins, "_hosts", {**plugins._hosts, "ui": type("NoLv2", (), {
        "call": staticmethod(lambda request, timeout: [])})()})
    monkeypatch.setattr(plugins, "_scan_cache_path", lambda: str(tmp_path / "cache.json"))
    plugins.forget_scan()
    try:
        found = plugins.scan_plugins()
        assert [(i.format, i.format_label, i.name) for i in found] == [("au", "AU", "Eco")]
        plugins.forget_scan()
        assert plugins.quick_scan() == (found, 0)               # gia' in cache: niente da caricare
        plugins.scan_plugins()
        assert calls == [bundle]
    finally:
        plugins.forget_scan()


# ------------------------------------------------------------------ AU che esistono anche in VST3

def test_vst3_comes_first_and_au_twins_are_recognised():
    def info(fmt, name, vendor="Surge Synth Team", problem=""):
        return plugins.PluginInfo(ref=f"{fmt}:/{name}.{fmt}", format=fmt, name=name, vendor=vendor, problem=problem)
    infos = [info("au", "Surge XT"), info("vst3", "Surge XT"), info("au", "Solo AU"),
             info("au", "TAL-Reverb-4", "TAL"), info("vst3", "TAL-Reverb-4", "Altro"),
             info("au", "Rotto"), info("vst3", "Rotto", problem="non si carica")]
    assert plugins.vst3_twins(infos) == {"au:/Surge XT.au"}
    order = sorted(infos, key=lambda i: (i.name.lower(), plugins._FORMAT_ORDER.get(i.format, 9), i.format))
    assert [i.format for i in order if i.name == "Surge XT"] == ["vst3", "au"]


# ------------------------------------------------------------------ un AU vero (solo macOS)

# sfizz in versione AU (gratuito, sfztools.github.io/sfizz): uno strumento
# che senza file .sfz suona un'onda sinusoidale. Gli effetti Apple di
# sistema (CoreAudio.component) non si usano: pedalboard si blocca
# chiedendone i nomi.
SFIZZ_AU = "/Library/Audio/Plug-Ins/Components/sfizz.component"


def _real_au_available() -> bool:
    if sys.platform != "darwin" or not os.path.isdir(SFIZZ_AU):
        return False
    try:
        import pedalboard
    except ImportError:
        return False
    return hasattr(pedalboard, "AudioUnitPlugin")


@pytest.mark.skipif(not _real_au_available(), reason="serve macOS con sfizz.component installato")
def test_real_au_instrument_through_the_plugin_process():
    ref = "au:" + SFIZZ_AU
    info = plugins.describe(ref)
    assert (info.format, info.format_label, info.instrument, info.usable) == ("au", "AU", True, True)
    assert info.params and info.state
    y = plugins.render_events(ref, {}, "", [(0.0, bytes([0x90, 60, 100])), (0.5, bytes([0x80, 60, 0]))], 1.0, RATE)
    assert y.shape == (RATE, 2) and float(np.sqrt(np.mean(y ** 2))) > 1e-3
    assert plugins.parameter_texts(ref, {}, "")


# ------------------------------------------------------------------ effetti Apple (bundle ponte, core.apple_au)

def _fake_apple_bundle(tmp_path):
    """Un CoreAudio.component finto: due componenti utili, uno escluso e uno
    che non e' un plugin audio."""
    import plistlib
    contents = tmp_path / "CoreAudio.component" / "Contents"
    contents.mkdir(parents=True)
    comps = [{"type": "afil", "subtype": "MooV", "manufacturer": "appl", "name": "QTAudioFileComponent"},
             {"type": "aufx", "subtype": "mrev", "manufacturer": "appl", "name": "Apple: AUMatrixReverb",
              "factoryFunction": "AUMatrixReverbFactory", "version": 67072},
             {"type": "aufx", "subtype": "nsnd", "manufacturer": "appl", "name": "Apple: AUNetSend"},
             {"type": "aumu", "subtype": "dls ", "manufacturer": "appl", "name": "Apple: DLSMusicDevice"}]
    (contents / "Info.plist").write_bytes(plistlib.dumps({"AudioComponents": comps}))
    return str(tmp_path / "CoreAudio.component")


def test_apple_proxies_declare_one_component_each(tmp_path):
    import plistlib
    from core import apple_au
    folder = str(tmp_path / apple_au.FOLDER_NAME)
    made = apple_au.ensure_proxies(folder, _fake_apple_bundle(tmp_path))
    assert sorted(os.path.basename(p) for p in made) == ["AUMatrixReverb.component", "DLSMusicDevice.component"]
    reverb = os.path.join(folder, "AUMatrixReverb.component")
    plist = plistlib.load(open(os.path.join(reverb, "Contents", "Info.plist"), "rb"))
    assert [(c["type"], c["subtype"], c["manufacturer"]) for c in plist["AudioComponents"]] == \
        [("aufx", "mrev", "appl")]
    assert not os.path.exists(os.path.join(reverb, "Contents", "MacOS"))       # niente codice copiato
    # gia' giusti: non si riscrivono, la ricerca dei plugin non li ricarica
    stamp = os.path.getmtime(os.path.join(reverb, "Contents", "Info.plist"))
    os.utime(os.path.join(reverb, "Contents", "Info.plist"), (stamp - 100, stamp - 100))
    apple_au.ensure_proxies(folder, _fake_apple_bundle(tmp_path / "di nuovo"))
    assert os.path.getmtime(os.path.join(reverb, "Contents", "Info.plist")) == stamp - 100
    # nomi chiari solo per i ponti
    assert apple_au.friendly_name(reverb) == "Riverbero a matrice (Apple)"
    assert apple_au.friendly_name(str(tmp_path / "AUMatrixReverb.component")) is None
    info = plugins._info_from_dict({"ref": "au:" + reverb, "format": "au", "name": "AUMatrixReverb"})
    assert (info.name, info.format_label) == ("Riverbero a matrice (Apple)", "AU")
    assert plugins.display_name("au:" + os.path.join(folder, "DLSMusicDevice.component")) == \
        "Sintetizzatore General MIDI (Apple)"
    # un altro Mac: il ponte si ritrova per nome nella sua cartella
    assert apple_au.ensure_proxies(str(tmp_path / "x"), str(tmp_path / "manca.component")) == []


def test_apple_folder_is_a_plugin_folder_only_on_macos(tmp_path, monkeypatch):
    from core import apple_au
    monkeypatch.setattr(apple_au, "APPLE_BUNDLE", _fake_apple_bundle(tmp_path))
    monkeypatch.setattr(apple_au, "_ready", None)
    _pretend_macos(monkeypatch, True)
    folder = apple_au.proxy_folder()
    assert folder in plugins.default_au_dirs()
    assert plugins.in_plugin_dirs(os.path.join(folder, "AUMatrixReverb.component"))
    _pretend_macos(monkeypatch, False)
    assert plugins.default_au_dirs() == []


def _apple_effects_available() -> bool:
    from core import apple_au
    if sys.platform != "darwin" or not os.path.isdir(apple_au.APPLE_BUNDLE):
        return False
    try:
        import pedalboard
    except ImportError:
        return False
    return hasattr(pedalboard, "AudioUnitPlugin")


@pytest.mark.skipif(not _apple_effects_available(), reason="serve macOS con pedalboard.AudioUnitPlugin")
def test_real_apple_reverb_and_synth_through_the_plugin_process():
    from core import apple_au
    folder = apple_au.ready_folder()
    reverb = "au:" + os.path.join(folder, "AUMatrixReverb.component")
    info = plugins.describe(reverb)
    assert (info.name, info.vendor, info.instrument, info.usable) == ("Riverbero a matrice (Apple)", "Apple", False, True)
    x = np.zeros((RATE, 2), dtype=np.float32)
    x[0] = 0.8                                              # un impulso: il riverbero lo allunga
    y = plugins.process_audio(reverb, {}, "", x, RATE)
    assert float(np.sqrt(np.mean(y[RATE // 4:] ** 2))) > 1e-5
    synth = "au:" + os.path.join(folder, "DLSMusicDevice.component")
    assert plugins.describe(synth).instrument
    z = plugins.render_events(synth, {}, "", [(0.0, bytes([0x90, 60, 100]))], 0.5, RATE)
    assert float(np.sqrt(np.mean(z ** 2))) > 1e-3
