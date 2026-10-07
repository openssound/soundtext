"""
Test dei profili NAM (core.nam e l'effetto "Profilo NAM").

tests/data/nam_reference.json contiene piccoli profili WaveNet casuali e le
uscite calcolate dal motore ufficiale NeuralAmpModelerCore (C++,
tools/render) per lo stesso ingresso: il calcolo con numpy deve coincidere.
- A1 (classici): Tanh, gated, Fasttanh/ReLU, LeakyReLU con kernel 5 e
  Hardtanh;
- A2: contenitore con due misure (SlimmableContainer, kernel diversi per
  strato, testa con kernel 16), le altre novita' (bottleneck, head1x1 a
  gruppi, convoluzione depthwise, gating blended/gated, FiLM, testa con
  dilatazione tra due gruppi di strati, testa finale, PReLU, SiLU,
  LeakyHardtanh, Hardswish, Softsign) e una rete di condizionamento
  (condition_dsp);
- LSTM: uno e due strati e un contenitore la cui misura completa e' un LSTM
  (con gli stati iniziali del file e il prewarm di mezzo secondo).

Esecuzione:
    python3 -m pytest tests/test_nam.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import json
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from core import nam
from core.effects import apply_effect_chain, chain_signature, clamp_params, effects_available
from core.model import Effect, Project
from core.project_io import parse_project_text, project_to_text

REFERENCE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "nam_reference.json")
RATE = 48000
needs_pedalboard = pytest.mark.skipif(not effects_available(), reason="pedalboard non installato")


def _reference():
    with open(REFERENCE) as f:
        return json.load(f)


def _write(tmp_path, name, data):
    path = str(tmp_path / name)
    with open(path, "w") as f:
        json.dump(data, f)
    return path


@pytest.mark.parametrize("case", ["tanh", "gated", "fasttanh_relu", "leaky_k5",
                                  "a2_container", "a2_features", "a2_condition_dsp",
                                  "lstm_1", "lstm_2x", "lstm_container"])
def test_numpy_inference_matches_the_official_engine(tmp_path, case, monkeypatch):
    ref = _reference()
    x = np.array(ref["input"], dtype=np.float32)
    expected = np.array(ref["models"][case]["expected"])
    model = nam.load_nam(_write(tmp_path, case + ".nam", ref["models"][case]["nam"]))
    y = nam.process(model, x)
    assert len(y) == len(x)
    assert np.abs(y - expected).max() < 1e-5 * max(1.0, np.abs(expected).max())
    monkeypatch.setattr(nam, "_BLOCK", 700)                             # a blocchi piccoli: uguale
    monkeypatch.setattr(nam, "_LSTM_CHUNK", 0.004)                      # LSTM a 16 tratti paralleli: uguale
    assert np.abs(nam.process(model, x) - expected).max() < 1e-5
    assert model.generation == ("A2" if case.startswith("a2") else "LSTM" if case.startswith("lstm") else "A1")


def test_lstm_chunks_converge_to_the_sequential_result(tmp_path, monkeypatch):
    # Una rete che ricorda a lungo (porta "forget" quasi sempre aperta): i
    # tratti in parallelo richiedono piu' giri, ma il risultato e' lo stesso.
    data = json.loads(json.dumps(_reference()["models"]["lstm_1"]["nam"]))
    weights, hidden = data["weights"], 6
    for i in range(hidden, 2 * hidden):
        weights[4 * hidden * (1 + hidden) + i] = 6.0                   # bias della porta "forget"
    model = nam.load_nam(_write(tmp_path, "memoria.nam", data))
    x = np.array(_reference()["input"], dtype=np.float32)
    sequential = nam.process(model, x)                                  # 3000 campioni: un tratto solo
    runs = []
    original = nam._lstm_run
    monkeypatch.setattr(nam, "_lstm_run", lambda *a: runs.append(1) or original(*a))
    monkeypatch.setattr(nam, "_LSTM_CHUNK", 0.002)                      # 32 tratti da 96 campioni
    assert np.abs(nam.process(model, x) - sequential).max() < 1e-5
    assert len(runs) > 2


def test_a2_container_uses_the_full_size_model(tmp_path):
    ref = _reference()
    container = ref["models"]["a2_container"]["nam"]
    x = np.array(ref["input"], dtype=np.float32)
    model = nam.load_nam(_write(tmp_path, "a2.nam", container))
    full = nam.load_nam(_write(tmp_path, "piena.nam", container["config"]["submodels"][-1]["model"]))
    small = nam.load_nam(_write(tmp_path, "ridotta.nam", container["config"]["submodels"][0]["model"]))
    assert np.array_equal(nam.process(model, x), nam.process(full, x))
    assert not np.allclose(nam.process(model, x), nam.process(small, x))
    assert model.name == "A2 di prova" and model.loudness == -21.0          # metadati del contenitore


def test_metadata_name_and_description(tmp_path):
    data = _reference()["models"]["tanh"]["nam"]
    data = dict(data, metadata={"name": "Plexi", "gear_make": "Marshall", "gear_model": "1959SLP",
                                "gear_type": "amp", "modeled_by": "Sergio", "loudness": -14.0})
    model = nam.load_nam(_write(tmp_path, "plexi.nam", data))
    assert model.name == "Plexi"
    assert model.description == "Marshall 1959SLP (amplificatore) — di Sergio"
    assert model.loudness == -14.0
    anonymous = nam.load_nam(_write(tmp_path, "Senza nome.nam", dict(data, metadata={})))
    assert anonymous.name == "Senza nome" and anonymous.description == "" and anonymous.loudness is None


def test_unsupported_or_broken_files_are_explained(tmp_path):
    base = _reference()["models"]["tanh"]["nam"]
    lstm = {"architecture": "LSTM", "config": {"num_layers": 1, "input_size": 1, "hidden_size": 8}, "weights": [0.1] * 30}
    other = {"architecture": "Transformer", "config": {}, "weights": []}
    future = json.loads(json.dumps(base))
    future["config"]["layers"][0]["nuova_funzione"] = {"active": True}
    unknown_act = json.loads(json.dumps(base))
    unknown_act["config"]["layers"][0]["activation"] = "Mish"
    short = dict(base, weights=base["weights"][:-5])
    long = dict(base, weights=base["weights"] + [0.1])
    broken = str(tmp_path / "rotto.nam")
    with open(broken, "w") as f:
        f.write("{ non e' json")
    assert "pesi" in nam.nam_problem(_write(tmp_path, "lstm.nam", lstm))
    assert "Transformer" in nam.nam_problem(_write(tmp_path, "altro.nam", other))
    assert "nuova_funzione" in nam.nam_problem(_write(tmp_path, "futuro.nam", future))
    assert "Mish" in nam.nam_problem(_write(tmp_path, "mish.nam", unknown_act))
    assert "pesi" in nam.nam_problem(_write(tmp_path, "corto.nam", short))
    assert "pesi" in nam.nam_problem(_write(tmp_path, "lungo.nam", long))
    assert "leggibile" in nam.nam_problem(broken)
    assert nam.nam_problem(str(tmp_path / "manca.nam")) == "file non trovato"
    assert nam.nam_problem("") == "nessun profilo scelto"
    assert nam.nam_problem(_write(tmp_path, "ok.nam", base)) == ""


@needs_pedalboard
def test_nam_effect_in_the_chain(tmp_path):
    ref = _reference()
    path = _write(tmp_path, "profilo.nam", ref["models"]["tanh"]["nam"])       # loudness -12,5 dB
    x = np.array(ref["input"], dtype=np.float32)
    stereo = np.stack([x, 0.5 * x], axis=1)
    effect = Effect("nam", clamp_params("nam", {}), nam=path)
    y = apply_effect_chain(stereo, RATE, [effect], with_tail=False)
    mono = nam.process(nam.load_nam(path), stereo.mean(axis=1))
    normalization = 10 ** ((-18.0 - (-12.5)) / 20)                          # verso -18 dB, come il plugin
    assert np.allclose(y[:, 0], y[:, 1])
    assert np.abs(y[:, 0] - mono * normalization).max() < 1e-4
    louder = apply_effect_chain(stereo, RATE, [Effect("nam", clamp_params("nam", {"livello": 6}), nam=path)],
                                with_tail=False)
    assert np.abs(louder[:, 0] - y[:, 0] * 10 ** (6 / 20)).max() < 1e-4
    missing = Effect("nam", clamp_params("nam", {}), nam=str(tmp_path / "manca.nam"))
    assert np.allclose(apply_effect_chain(stereo, RATE, [missing], with_tail=False), stereo, atol=1e-6)


@needs_pedalboard
def test_nam_model_at_another_sample_rate_is_resampled(tmp_path):
    data = dict(_reference()["models"]["tanh"]["nam"], sample_rate=44100)
    path = _write(tmp_path, "44k.nam", data)
    t = np.arange(RATE) / RATE
    x = np.stack([0.3 * np.sin(2 * np.pi * 220 * t)] * 2, axis=1).astype(np.float32)
    y = apply_effect_chain(x, RATE, [Effect("nam", clamp_params("nam", {}), nam=path)], with_tail=False)
    assert y.shape == x.shape and np.isfinite(y).all() and np.abs(y).max() > 0


def test_nam_profile_path_is_saved_relative_and_changes_the_cache_key(tmp_path):
    (tmp_path / "profili").mkdir()
    path = _write(tmp_path / "profili", "Plexi.nam", _reference()["models"]["tanh"]["nam"])
    p = Project(name="t")
    track = p.add_track("Chitarra", "Guitar", "4: c e g")
    effect = Effect("nam", clamp_params("nam", {"ingresso": 3}), nam=path)
    track.effects = [effect]
    text = project_to_text(p, base_dir=str(tmp_path))
    assert 'nam="profili/Plexi.nam"' in text and "ingresso=3" in text
    back = parse_project_text(text, base_dir=str(tmp_path)).get_track("Chitarra").effects[0]
    assert os.path.samefile(back.nam, path) and back.params == effect.params
    before = chain_signature([effect])
    os.utime(path, (1, 1))
    assert chain_signature([effect]) != before


@needs_pedalboard
def test_panel_asks_for_a_profile_when_adding_the_effect(tmp_path):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from gui.main_window import MainWindow
    data = dict(_reference()["models"]["tanh"]["nam"],
                metadata={"name": "Plexi", "gear_make": "Marshall", "gear_type": "amp"})
    path = _write(tmp_path, "plexi.nam", data)
    w = MainWindow()
    w.project.add_track("Chitarra", "Guitar", "8: c e g e")
    w.refresh_mixer()
    w.open_effects_panel("Chitarra")
    panel = w.effects_panel
    answers = [""]
    panel.choose_nam_file = lambda current="": answers.pop(0)
    panel.add_effect("nam")                                             # annullato: nessun effetto
    assert w.project.get_track("Chitarra").effects == []
    answers = [path]
    panel.add_effect("nam")
    effect = w.project.get_track("Chitarra").effects[0]
    card = panel.cards[0]
    assert effect.kind == "nam" and effect.nam == path
    assert card.nam_label.text() == "Plexi" and "Marshall" in card.nam_info.text()
    assert w.track_headers["Chitarra"].fx_btn.text() == "FX 1"
    assert "formato" not in card.nam_info.text()
    effect.nam = _write(tmp_path, "a2.nam", _reference()["models"]["a2_container"]["nam"])
    card._refresh_nam_row()
    assert card.nam_label.text() == "A2 di prova" and card.nam_info.text() == "formato A2"
    effect.nam = path
    os.remove(path)
    card._refresh_nam_row()
    assert "non trovato" in card.nam_label.text()
    panel.close_panel()


def test_loudness_is_measured_when_the_profile_does_not_declare_it(tmp_path):
    from core.audio_tracks import read_wav
    from core.effects import _nam_normalization_db
    data = dict(_reference()["models"]["tanh"]["nam"], metadata={})
    path = _write(tmp_path, "vecchio.nam", data)
    model = nam.load_nam(path)
    assert model.loudness is None
    x = read_wav(nam.LOUDNESS_INPUT)[0][:, 0]
    y = nam.process(model, x).astype(np.float64)
    expected = 20 * np.log10(np.sqrt(np.mean(y * y)))                   # come l'addestramento di NAM
    assert abs(nam.reference_loudness(model) - expected) < 1e-9
    assert abs(_nam_normalization_db(path) - (-18.0 - expected)) < 1e-6
    declared = nam.load_nam(_write(tmp_path, "nuovo.nam", _reference()["models"]["tanh"]["nam"]))
    assert nam.reference_loudness(declared) == -12.5                    # dichiarata: si usa quella


class _FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self.body


def test_recommended_profiles_download(tmp_path):
    from core import nam_profiles
    body = json.dumps(dict(_reference()["models"]["tanh"]["nam"], metadata={"loudness": -20.0})).encode()
    urls = []

    def opener(url, timeout):
        urls.append(url)
        if "TS9" in url:
            raise OSError("rete assente")
        return _FakeResponse(body)

    steps = []
    result = nam_profiles.download_profiles(str(tmp_path), lambda i, n, name: steps.append(i), opener=opener)
    total = len(nam_profiles.PROFILES)
    assert 10 <= total <= 12 and len(result["downloaded"]) == total - 1
    assert result["failed"] == [("Ibanez TS9 Tube Screamer.nam", "rete assente")]
    assert all(u.startswith(nam_profiles.RAW_BASE) and " " not in u for u in urls)
    assert steps == list(range(total + 1))
    assert not [f for f in os.listdir(tmp_path) if f.endswith(".part")]
    model = nam.load_nam(str(tmp_path / "Fender Twin Reverb - pulito.nam"))
    assert model.name == "Fender Twin Reverb - pulito" and model.loudness == -20.0     # metadati aggiunti
    assert model.description == "Fender Twin Reverb (amplificatore) — di Tim R"
    assert "GPL" in (tmp_path / "LEGGIMI.txt").read_text(encoding="utf-8")
    urls.clear()
    again = nam_profiles.download_profiles(str(tmp_path), opener=opener)   # riscarica solo quello mancante
    assert len(again["present"]) == total - 1 and len(urls) == 1
    stopped = nam_profiles.download_profiles(str(tmp_path / "altra"), opener=opener, should_stop=lambda: True)
    assert stopped["downloaded"] == [] and stopped["failed"] == []


def test_download_command_in_the_menu(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QApplication, QMessageBox
    app = QApplication.instance() or QApplication([])
    from core import nam_profiles
    from gui.command_palette import collect_commands
    from gui.main_window import MainWindow
    calls, shown = [], []

    def fake_download(folder, progress=None, should_stop=None):
        calls.append(folder)
        progress(0, 1, "uno")
        return {"folder": folder, "downloaded": ["uno.nam"], "present": [], "failed": []}

    monkeypatch.setattr(nam_profiles, "download_profiles", fake_download)
    monkeypatch.setattr(nam_profiles, "ensure_nam_dir", lambda: str(tmp_path))
    monkeypatch.setattr(QMessageBox, "information", lambda *a: shown.append(a[2]))
    w = MainWindow()
    labels = [c.action.text() for c in collect_commands(w.menuBar())]   # sottomenu compresi
    assert "Scarica profili NAM consigliati..." in labels
    w.download_nam_profiles(ask=False)
    w._nam_download_worker.wait()
    for _ in range(50):
        app.processEvents()
        if shown:
            break
    assert calls == [str(tmp_path)] and shown and "Scaricati: 1" in shown[0]


def _wav_bytes(samples, rate=44100):
    import io
    import wave
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((np.asarray(samples) * 32767).astype("<i2").tobytes())
    return buf.getvalue()


def test_cabinet_irs_download(tmp_path):
    from core import cab_irs
    ir = _wav_bytes(np.exp(-np.arange(2000) / 200.0) * np.cos(np.arange(2000) * 0.3))
    urls = []

    def opener(url, timeout):
        urls.append(url)
        if url.endswith("/LICENSE"):
            return _FakeResponse(b"GNU GPL v2 or later")
        if "Mesa" in url:
            raise OSError("rete assente")
        if "Splawn%20Nitro" in url:
            return _FakeResponse(b"<html>not found</html>")          # non e' un WAV
        return _FakeResponse(ir)

    steps = []
    result = cab_irs.download_cabinets(str(tmp_path), lambda i, n, name: steps.append(i), opener=opener)
    total = len(cab_irs.CABINETS)
    assert len(result["downloaded"]) == total - 2
    assert [name for name, _ in result["failed"]] == ["Mesa Boogie Mark V.wav", "Splawn Nitro.wav"]
    assert all(u.startswith(cab_irs.RAW_BASE) and " " not in u for u in urls)
    assert steps == list(range(total + 1))
    assert not [f for f in os.listdir(tmp_path) if f.endswith(".part")]
    assert (tmp_path / "LICENSE.txt").read_bytes() == b"GNU GPL v2 or later"
    assert "GPL" in (tmp_path / "LEGGIMI.txt").read_text(encoding="utf-8")
    from core.effects import load_ir_file
    assert load_ir_file(str(tmp_path / "EVH 5150 III.wav"), 48000) is not None
    urls.clear()
    again = cab_irs.download_cabinets(str(tmp_path), opener=opener)   # riscarica solo quelle mancanti
    assert len(again["present"]) == total - 2 and len(urls) == 2
    stopped = cab_irs.download_cabinets(str(tmp_path / "altra"), opener=opener, should_stop=lambda: True)
    assert stopped["downloaded"] == [] and stopped["failed"] == []


def test_cabinet_download_command_in_the_menu(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QApplication, QMessageBox
    app = QApplication.instance() or QApplication([])
    from core import cab_irs
    from gui.command_palette import collect_commands
    from gui.main_window import MainWindow
    calls, shown = [], []

    def fake_download(folder, progress=None, should_stop=None):
        calls.append(folder)
        progress(0, 1, "uno")
        return {"folder": folder, "downloaded": ["uno.wav"], "present": [], "failed": []}

    monkeypatch.setattr(cab_irs, "download_cabinets", fake_download)
    monkeypatch.setattr(cab_irs, "ensure_cab_dir", lambda: str(tmp_path))
    monkeypatch.setattr(QMessageBox, "information", lambda *a: shown.append(a[2]))
    w = MainWindow()
    labels = [c.action.text() for c in collect_commands(w.menuBar())]   # sottomenu compresi
    assert "Scarica casse IR per gli amplificatori NAM..." in labels
    w.download_cab_irs(ask=False)
    w._cab_download_worker.wait()
    for _ in range(50):
        app.processEvents()
        if shown:
            break
    assert calls == [str(tmp_path)] and shown and "Scaricati: 1" in shown[0] and "File IR" in shown[0]
