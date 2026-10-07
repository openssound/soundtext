"""
Test della fase 2 degli effetti: catena per traccia con pedalboard
(core.effects), salvataggio nel file .st (blocco "Effetti <traccia>:"),
rendering a stem con cache (core.effect_render), loop di calibrazione
(CalibrationSession, PcmPlayer.queue_loop_update) e pannello Effetti
(gui.effects_panel).

Esecuzione:
    python3 -m pytest tests/test_effects_chain.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys
import types

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from core import audio_stream, effect_render, settings
from core.effects import (
    EFFECT_KINDS, active_effects, apply_effect_chain, chain_signature, clamp_params, default_params,
    effect_params, effects_available, format_value, matching_preset, preset_params, tail_seconds,
)
from core.model import Effect, Project
from core.project_io import parse_project_text, project_to_text

SOUNDFONT = "/usr/share/sounds/sf2/TimGM6mb.sf2"
needs_pedalboard = pytest.mark.skipif(not effects_available(), reason="pedalboard non installato")
needs_soundfont = pytest.mark.skipif(not os.path.exists(SOUNDFONT), reason="SoundFont di prova assente")
RATE = 48000


def _tone(seconds=1.0, freq=440.0):
    t = np.arange(int(seconds * RATE)) / RATE
    mono = (0.3 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    return np.stack([mono, mono], axis=1)


def _project():
    p = Project(name="t")
    p.add_track("Chitarra", "Guitar", "8: c e g e c e g e c e g e c e g e")
    p.add_track("Basso", "Bass", "2: c g c g")
    return p


@pytest.fixture
def soundfont():
    previous = settings.get_soundfont_path() if hasattr(settings, "get_soundfont_path") else None
    settings.set_soundfont_path(SOUNDFONT)
    effect_render.clear_stem_cache()
    yield SOUNDFONT
    effect_render.clear_stem_cache()
    if previous:
        settings.set_soundfont_path(previous)


# ------------------------------------------------------------------ catalogo

def test_catalog_presets_are_within_limits_and_match_themselves():
    for kind, info in EFFECT_KINDS.items():
        assert info["family"] in ("Dinamica", "Tono", "Saturazione", "Spazio", "Plugin")
        for name, values in info["presets"].items():
            params = {p.key: p for p in effect_params(kind)}
            expected = {k: float([c for c, _l in params[k].choices].index(v)) if params[k].choices else float(v)
                        for k, v in values.items()}
            assert {k: clamp_params(kind, values)[k] for k in values} == expected, (kind, name)
            assert matching_preset(kind, preset_params(kind, name)) == name
        for p in effect_params(kind):
            assert p.minimum <= p.default <= p.maximum


def test_clamp_params_fills_defaults_and_drops_unknown_keys():
    params = clamp_params("delay", {"tempo": 99999, "mix": "40", "sconosciuto": 3, "ripetizioni": "x"})
    assert params == {"suddivisione": 0.0, "tempo": 1500.0,
                      "ripetizioni": default_params("delay")["ripetizioni"], "mix": 40.0}
    assert matching_preset("eq", {"bassi": 1}) == ""


def test_format_value_is_italian():
    eq = effect_params("eq")[0]
    comp = {p.key: p for p in effect_params("compressore")}
    assert format_value(eq, 3) == "+3 dB"
    assert format_value(eq, -1.5) == "−1,5 dB"
    assert format_value(comp["rapporto"], 4) == "4:1"


def test_active_effects_and_signature_ignore_switched_off_ones():
    on = Effect("delay", default_params("delay"))
    off = Effect("eq", {"bassi": 6}, enabled=False)
    unknown = Effect("flanger", {})
    assert active_effects([on, off, unknown]) == [on]
    assert chain_signature([on, off]) == chain_signature([on])
    assert chain_signature([on]) != chain_signature([Effect("delay", dict(default_params("delay"), mix=90))])
    assert tail_seconds([]) == 0
    assert 0 < tail_seconds([Effect("riverbero", preset_params("riverbero", "Cattedrale"))]) <= 8


# ------------------------------------------------------------------ elaborazione

@needs_pedalboard
def test_empty_or_switched_off_chain_leaves_the_audio_untouched():
    x = _tone()
    assert np.array_equal(apply_effect_chain(x, RATE, []), x)
    assert np.array_equal(apply_effect_chain(x, RATE, [Effect("eq", {"bassi": 12}, enabled=False)]), x)


@needs_pedalboard
def test_delay_adds_a_tail_and_eq_changes_the_level():
    x = np.zeros((RATE, 2), dtype=np.float32)
    x[:2000] = _tone(2000 / RATE)
    wet = apply_effect_chain(x, RATE, [Effect("delay", {"tempo": 500, "ripetizioni": 50, "mix": 50})])
    assert len(wet) > len(x)                                      # coda delle ripetizioni
    echo = wet[int(0.5 * RATE):int(0.5 * RATE) + 2000]
    assert np.abs(echo).max() > 0.02                              # l'eco a 500 ms
    cut = apply_effect_chain(_tone(freq=100), RATE, [Effect("eq", {"bassi": -12})], with_tail=False)
    assert np.sqrt((cut ** 2).mean()) < 0.5 * np.sqrt((_tone(freq=100) ** 2).mean())


def _rms(a):
    return float(np.sqrt((a[RATE // 10:] ** 2).mean()))


@needs_pedalboard
def test_every_preset_processes_without_errors():
    x = _tone(0.5, 220)
    for kind, info in EFFECT_KINDS.items():
        for name in info["presets"]:
            y = apply_effect_chain(x, RATE, [Effect(kind, preset_params(kind, name))])
            assert np.isfinite(y).all() and len(y) >= len(x), (kind, name)


@needs_pedalboard
def test_filters_cut_below_or_above_the_frequency_and_slope_matters():
    low, high = _tone(freq=40), _tone(freq=4000)
    hp = lambda x, slope: apply_effect_chain(  # noqa: E731
        x, RATE, [Effect("passa_alto", {"frequenza": 80, "pendenza": slope})], with_tail=False)
    lp = apply_effect_chain(high, RATE, [Effect("passa_basso", {"frequenza": 1000, "pendenza": 24})],
                            with_tail=False)
    assert _rms(hp(low, 6)) < 0.5 * _rms(low)
    assert _rms(hp(low, 24)) < 0.5 * _rms(hp(low, 6))              # pendenza piu' ripida, taglio maggiore
    assert _rms(hp(_tone(freq=2000), 12)) > 0.95 * _rms(_tone(freq=2000))   # sopra: intatto
    assert _rms(lp) < 0.01 * _rms(high)


@needs_pedalboard
def test_noise_gate_silences_the_quiet_part():
    x = _tone(freq=220) * 0.003                                     # circa -60 dB
    x[RATE // 2:] *= 100                                            # sussurro, poi suono pieno
    y = apply_effect_chain(x, RATE, [Effect("noise_gate", preset_params("noise_gate", "Voce"))],
                           with_tail=False)
    assert np.abs(y[RATE // 10:RATE // 2 - 2000]).max() < 0.1 * np.abs(x[:RATE // 2]).max()
    assert np.abs(y[RATE // 2 + 4000:]).max() > 0.9 * np.abs(x[RATE // 2:]).max()


@needs_pedalboard
def test_limiter_keeps_peaks_under_the_ceiling_and_raises_the_level():
    x = _tone(freq=220) * 3                                         # picchi a 0,9
    loud = [Effect("limiter", {"guadagno": 12, "tetto": -3, "rilascio": 50})]
    y = apply_effect_chain(x, RATE, loud, with_tail=False)
    assert np.abs(y).max() <= 10 ** (-3 / 20) + 1e-3
    quiet = _tone(freq=220) * 0.1
    assert _rms(apply_effect_chain(quiet, RATE, loud, with_tail=False)) > 2 * _rms(quiet)


@needs_pedalboard
def test_distortion_adds_harmonics_and_mix_blends_the_dry_sound():
    x = _tone(freq=220)
    def third_harmonic(a):
        spectrum = np.abs(np.fft.rfft(a[:RATE, 0]))
        return spectrum[660] / spectrum[220]
    full = apply_effect_chain(x, RATE, [Effect("distorsione", preset_params("distorsione", "Fuzz"))],
                              with_tail=False)
    blend = apply_effect_chain(x, RATE, [Effect("distorsione", dict(preset_params("distorsione", "Fuzz"), mix=20))],
                               with_tail=False)
    assert third_harmonic(x) < 0.01 < third_harmonic(full)
    assert third_harmonic(blend) < third_harmonic(full)


@needs_pedalboard
def test_amp_cabinet_cuts_the_highs_without_latency():
    from core.effects import cabinet_ir
    for cabinet in ("combo_1x12", "2x12", "4x12", "vintage_1x10"):
        ir = cabinet_ir(cabinet, RATE)
        response = np.abs(np.fft.rfft(ir, RATE))
        assert int(np.argmax(np.abs(ir))) < 16                         # fase minima: niente ritardo
        assert response[10000] < 0.1 * response[2000]                  # un altoparlante da chitarra non fa gli acuti
        assert response[40] < 0.5 * response[200]
    impulse = np.zeros((RATE // 4, 2), dtype=np.float32)
    impulse[0] = 0.01
    amp = dict(preset_params("amplificatore", "Pulito brillante"), guadagno=0)
    out = apply_effect_chain(impulse, RATE, [Effect("amplificatore", amp)], with_tail=False)
    assert int(np.argmax(np.abs(out[:, 0]))) < 16


@needs_pedalboard
def test_amp_models_and_gain_add_distortion():
    x = _tone(freq=110)

    def harmonics(params):
        y = apply_effect_chain(x, RATE, [Effect("amplificatore", dict(params, cassa="nessuna"))], with_tail=False)
        spectrum = np.abs(np.fft.rfft(y[:RATE, 0]))
        return spectrum[330] / spectrum[110]
    clean = harmonics(dict(preset_params("amplificatore", "Pulito brillante"), guadagno=0))
    crunch = harmonics(preset_params("amplificatore", "Blues"))
    metal = harmonics(preset_params("amplificatore", "Metal"))
    assert clean < crunch < metal


def test_delay_follows_the_song_tempo():
    from core.effects import DELAY_DIVISIONS, delay_seconds, inactive_params
    free = preset_params("delay", "Eco corto")
    synced = preset_params("delay", "A tempo 1/8 puntato")
    assert delay_seconds(free, 90) == pytest.approx(0.25) and inactive_params("delay", free) == set()
    assert delay_seconds(synced, 120) == pytest.approx(0.375)
    assert delay_seconds(synced, 80) == pytest.approx(0.5625)
    assert inactive_params("delay", synced) == {"tempo"}
    assert DELAY_DIVISIONS["1/4t"] * 60 / 100 == pytest.approx(delay_seconds(
        clamp_params("delay", {"suddivisione": "1/4t"}), 100))
    free_chain, synced_chain = [Effect("delay", free)], [Effect("delay", synced)]
    assert chain_signature(free_chain, 90) == chain_signature(free_chain, 140)   # il BPM conta solo a tempo
    assert chain_signature(synced_chain, 90) != chain_signature(synced_chain, 140)


def test_choice_params_are_saved_by_name():
    p = _project()
    p.get_track("Chitarra").effects = [
        Effect("amplificatore", preset_params("amplificatore", "Metal"), preset="Metal"),
        Effect("delay", preset_params("delay", "A tempo 1/4"), preset="A tempo 1/4"),
    ]
    text = project_to_text(p)
    assert "modello=high_gain cassa=4x12" in text and "suddivisione=1/4 " in text
    back = parse_project_text(text)
    assert back.get_track("Chitarra").effects == p.get_track("Chitarra").effects
    bad = text.replace("modello=high_gain", "modello=valvolare")      # scelta sconosciuta: predefinita
    amp = parse_project_text(bad).get_track("Chitarra").effects[0]
    assert amp.params["modello"] == default_params("amplificatore")["modello"]


def test_new_units_are_formatted():
    assert format_value(effect_params("passa_basso")[0], 8000) == "8 kHz"
    assert format_value(effect_params("passa_alto")[0], 80) == "80 Hz"
    assert format_value(effect_params("noise_gate")[1], 1.5) == "1,5:1"
    assert format_value(effect_params("passa_alto")[1], 12) == "12 dB/ott"
    assert format_value(effect_params("amplificatore")[1], 3) == "4×12 chiusa"


# ------------------------------------------------------------------ salvataggio

def test_effects_block_round_trips_in_the_project_file():
    p = _project()
    p.get_track("Chitarra").effects = [
        Effect("compressore", preset_params("compressore", "Voce"), preset="Voce"),
        Effect("delay", {"tempo": 250, "ripetizioni": 25, "mix": 20}, enabled=False),
    ]
    text = project_to_text(p)
    assert "Effetti Chitarra:" in text and "Effetti Basso:" not in text
    assert 'preset="Voce"' in text and "spento" in text
    back = parse_project_text(text)
    effects = back.get_track("Chitarra").effects
    assert [(e.kind, e.enabled, e.preset) for e in effects] == [
        ("compressore", True, "Voce"), ("delay", False, "")]
    assert effects[1].params == {"suddivisione": 0.0, "tempo": 250.0, "ripetizioni": 25.0, "mix": 20.0}
    assert "suddivisione" not in text                                 # delay libero: file come prima
    assert back.get_track("Basso").effects == []
    assert project_to_text(back) == text


def test_unknown_effects_and_out_of_range_values_are_tolerated():
    p = _project()
    text = project_to_text(p) + "\nEffetti Basso:\n  flanger: velocita=3\n  eq: bassi=40 alti=-2,5\n"
    effects = parse_project_text(text).get_track("Basso").effects
    assert [(e.kind, e.params) for e in effects] == [("eq", {"bassi": 12.0, "medi": 0.0, "alti": -2.5})]


# ------------------------------------------------------------------ loop che cambia al giro successivo

@pytest.mark.skipif(audio_stream._sd is None, reason="sounddevice non installato")
def test_loop_update_is_applied_at_the_next_wrap():
    class _T:
        outputBufferDacTime = 1.0
        currentTime = 0.9
    player = audio_stream.PcmPlayer(np.arange(8, dtype=np.int16).reshape(-1, 1), 1000)
    player._stream = types.SimpleNamespace(latency=0.1, time=1.0)
    player.set_loop((0, 8))
    player.queue_loop_update(np.zeros((3, 1), dtype=np.int16))       # forma sbagliata: ignorato
    out = np.zeros((6, 1), dtype=np.int16)
    player._callback(out, 6, _T(), None)
    player.queue_loop_update(np.full((8, 1), 100, dtype=np.int16))
    out2 = np.zeros((6, 1), dtype=np.int16)
    player._callback(out2, 6, _T(), None)
    assert out[:, 0].tolist() == [0, 1, 2, 3, 4, 5]
    assert out2[:, 0].tolist() == [6, 7, 100, 100, 100, 100]         # il giro in corso finisce com'era


# ------------------------------------------------------------------ stem e cache

@needs_pedalboard
@needs_soundfont
def test_effects_change_the_mix_and_a_knob_does_not_resynthesize(soundfont, monkeypatch):
    from core import playback
    p = _project()
    plain, rate = playback.render_project_mix(p)
    p.get_track("Chitarra").effects = [Effect("delay", preset_params("delay", "Eco lungo"))]
    calls = []
    real = playback.render_midi_file_to_samples

    def counting(*args, **kwargs):
        calls.append(1)
        return real(*args, **kwargs)
    monkeypatch.setattr(playback, "render_midi_file_to_samples", counting)
    wet, rate2 = playback.render_project_mix(p)
    assert rate == rate2 and len(wet) > len(plain)                     # la coda del delay allunga il brano
    assert len(calls) == 2                                             # il resto e la traccia con effetti
    p.get_track("Chitarra").effects[0].params["mix"] = 60
    playback.render_project_mix(p)
    assert len(calls) == 3                                             # solo il resto: l'asciutta e' in cache
    p.get_track("Chitarra").effects[0].enabled = False
    off, _ = playback.render_project_mix(p)
    assert len(off) == len(plain)                                      # di nuovo il percorso di sempre


@needs_pedalboard
@needs_soundfont
def test_muted_track_with_effects_is_not_heard(soundfont):
    from core import playback
    p = _project()
    p.get_track("Chitarra").effects = [Effect("delay", preset_params("delay", "Spaziale"))]
    p.get_track("Chitarra").mute = True
    assert effect_render.fx_tracks(p.audible_tracks()) == []
    only_bass, _ = playback.render_project_mix(p)
    p.get_track("Chitarra").effects = []
    again, _ = playback.render_project_mix(p)
    assert len(only_bass) == len(again)


@needs_pedalboard
@needs_soundfont
def test_calibration_session_mixes_the_window_with_and_without_others(soundfont):
    p = _project()
    track = p.get_track("Chitarra")
    effects = [Effect("riverbero", preset_params("riverbero", "Cattedrale"))]
    session = effect_render.CalibrationSession(p, track, 0.5, 2.5)
    alone = effect_render.CalibrationSession(p, track, 0.5, 2.5, with_others=False)
    try:
        session.prepare()
        alone.prepare()
        assert session.ready and session.frames == 2 * RATE
        dry = session.mix([])
        wet = session.mix(effects)
        assert dry.shape == wet.shape == (2 * RATE, 2)
        assert np.abs(dry - wet).max() > 0.01
        rms = lambda a: float(np.sqrt((a ** 2).mean()))  # noqa: E731
        assert rms(alone.mix([])) < rms(dry)                           # senza il basso
    finally:
        session.cleanup()
        alone.cleanup()


# ------------------------------------------------------------------ pannello

def _window():
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from gui.main_window import MainWindow
    w = MainWindow()
    w.project.add_track("Chitarra", "Guitar", "8: c e g e c e g e")
    w.project.add_audio_track("Voce")
    w.refresh_mixer()
    return w


@needs_pedalboard
def test_panel_builds_the_chain_with_cards():
    w = _window()
    panel = w.effects_panel
    w.open_effects_panel("Chitarra")
    track = w.project.get_track("Chitarra")
    panel.add_effect("eq")
    panel.add_effect("delay")
    assert [e.kind for e in track.effects] == ["eq", "delay"]
    assert [c.effect.kind for c in panel.cards] == ["eq", "delay"]
    assert not panel.cards[0].left_btn.isEnabled() and not panel.cards[1].right_btn.isEnabled()
    assert w.track_headers["Chitarra"].fx_btn.text() == "FX 2"
    header = w.arrangement_view.canvas.header_widgets["Chitarra"]
    assert header.fx_btn.text() == "FX 2" and header.fx_btn.objectName() == "fxBtnOn"

    card = panel.cards[1]
    card.preset_combo.setCurrentText("Slapback")
    assert track.effects[1].params == preset_params("delay", "Slapback") and track.effects[1].preset == "Slapback"
    card.knobs["mix"].dial.setValue(card.knobs["mix"].dial.value() + 10)
    assert track.effects[1].params["mix"] == 35 and card.preset_combo.currentText() == "Personalizzato"
    assert track.effects[1].preset == ""
    card.power_btn.setChecked(False)
    assert not track.effects[1].enabled and w.track_headers["Chitarra"].fx_btn.text() == "FX 1"

    panel.move_effect(panel.cards[1], -1)
    assert [e.kind for e in track.effects] == ["delay", "eq"]
    panel.remove_effect(panel.cards[1])
    assert [e.kind for e in track.effects] == ["delay"]
    assert w.history.can_undo() and w._dirty


@needs_pedalboard
def test_panel_choices_and_synced_delay():
    w = _window()
    w.project.tempo_bpm = 100
    panel = w.effects_panel
    w.open_effects_panel("Chitarra")
    panel.add_effect("amplificatore")
    panel.add_effect("delay")
    track = w.project.get_track("Chitarra")
    amp, delay = panel.cards
    assert amp.preset_combo.currentText() == "Blues"
    amp.knobs["cassa"].combo.setCurrentIndex(3)
    assert track.effects[0].params["cassa"] == 3 and amp.preset_combo.currentText() == "Personalizzato"
    assert delay.knobs["tempo"].isEnabled()
    delay.preset_combo.setCurrentText("A tempo 1/8 puntato")
    assert not delay.knobs["tempo"].isEnabled()
    assert delay.knobs["tempo"].value_label.text() == "450 ms"            # 3/8 di battito a 100 BPM
    delay.knobs["suddivisione"].combo.setCurrentIndex(0)                  # di nuovo libero
    assert delay.knobs["tempo"].isEnabled() and delay.preset_combo.currentText() == "Personalizzato"
    panel.close_panel()


@needs_pedalboard
def test_panel_revert_copy_and_undo():
    w = _window()
    panel = w.effects_panel
    track = w.project.get_track("Chitarra")
    track.effects = [Effect("chorus", preset_params("chorus", "Ampio"), preset="Ampio")]
    w.open_effects_panel("Chitarra")
    panel.add_effect("phaser")
    panel.cards[0].knobs["mix"].dial.setValue(0)
    panel.revert_changes()
    assert [(e.kind, e.params, e.preset) for e in track.effects] == [
        ("chorus", preset_params("chorus", "Ampio"), "Ampio")]
    assert len(panel.cards) == 1

    panel.copy_to("Voce")
    voce = w.project.get_track("Voce")
    assert [e.kind for e in voce.effects] == ["chorus"] and voce.effects[0] is not track.effects[0]
    assert w.track_headers["Voce"].fx_btn.text() == "FX 1"

    panel.add_effect("eq")
    w.undo()                                   # il progetto viene sostituito da una copia
    assert panel.track is w.project.get_track("Chitarra")
    assert [c.effect.kind for c in panel.cards] == [e.kind for e in panel.track.effects]


def test_panel_sets_and_restores_the_loop_markers():
    w = _window()
    w._loop_a_beat, w._loop_b_beat = 4.0, 8.0
    w.loop_action.setEnabled(True)
    w.loop_action.setChecked(False)
    panel = w.effects_panel
    w.open_effects_panel("Chitarra")
    assert panel.loop_spin.value() == 10
    assert w.loop_action.isChecked() and w._loop_a_beat == 0 and w._loop_b_beat == 20   # 10 s a 120 BPM
    panel.loop_spin.setValue(4)
    assert w._loop_b_beat == 8
    assert panel._region == (0.0, 4.0)
    panel.close_panel()
    assert (w._loop_a_beat, w._loop_b_beat, w.loop_action.isChecked()) == (4.0, 8.0, False)
    assert not panel.is_open()


def test_panel_starts_the_loop_from_the_selected_box():
    w = _window()
    track = w.project.get_track("Chitarra")
    from core.model import Clip
    track.text = ""
    clip = Clip(name="A", text="8: c e g e", start_beat=8.0)
    track.clips.append(clip)
    w.refresh_mixer()
    w.arrangement_view.select_box("Chitarra", clip)
    w.open_effects_panel("Chitarra")
    assert w._loop_a_beat == 8.0
    w.effects_panel.close_panel()


def test_panel_closes_when_its_track_disappears():
    w = _window()
    w.open_effects_panel("Voce")
    assert w.effects_panel.sends_card is None                  # traccia audio: niente invio al synth
    w.project.remove_track("Voce")
    w.refresh_mixer()
    assert not w.effects_panel.is_open() and w.effects_panel.isHidden()


@needs_pedalboard
@needs_soundfont
def test_panel_loop_is_ready_and_follows_bypass(soundfont):
    w = _window()
    panel = w.effects_panel
    w.open_effects_panel("Chitarra")
    panel.add_effect("delay")
    panel.cards[0].preset_combo.setCurrentText("Spaziale")
    assert panel.wait_until_ready()
    wet = panel.current_loop_samples()
    panel.bypass_btn.setChecked(True)
    dry = panel.current_loop_samples()
    assert wet.shape == dry.shape and np.abs(wet - dry).max() > 0.01
    assert w.project.get_track("Chitarra").effects[0].enabled     # Prima/Dopo non cambia la traccia
    panel.close_panel()


# ------------------------------------------------------------------ master

def test_master_chain_round_trips_and_does_not_clash_with_a_track_named_master():
    p = _project()
    p.add_track("Master", "Piano", "4: c")
    p.get_track("Master").effects = [Effect("eq", clamp_params("eq", {"bassi": 3}))]
    p.master_effects = [Effect("compressore", preset_params("compressore", "Colla del mix"), preset="Colla del mix"),
                        Effect("limiter", preset_params("limiter", "Più forte"), enabled=False)]
    text = project_to_text(p)
    assert "Catena master:" in text and "Effetti Master:" in text
    back = parse_project_text(text)
    assert back.master_effects == p.master_effects
    assert back.get_track("Master").effects == p.get_track("Master").effects
    assert [t.name for t in back.tracks] == ["Chitarra", "Basso", "Master"]
    assert project_to_text(back) == text
    assert "Catena master" not in project_to_text(_project())             # senza catena: file come prima


@needs_pedalboard
@needs_soundfont
def test_master_chain_is_applied_to_the_full_mix_only(soundfont):
    from core import playback
    p = _project()
    single, _ = playback.render_project_mix(p, tracks=[p.get_track("Basso")])
    p.master_effects = [Effect("eq", {"bassi": -12, "medi": -12, "alti": -12})]
    full, _ = playback.render_project_mix(p)
    single_after, _ = playback.render_project_mix(p, tracks=[p.get_track("Basso")])
    plain, _ = playback.render_project_mix(p, master=False)
    assert _rms(full) < 0.5 * _rms(plain)                                   # -12 dB ovunque
    assert _rms(single_after) == pytest.approx(_rms(single), rel=0.05)     # export di una traccia: senza master


@needs_pedalboard
@needs_soundfont
def test_calibration_loop_of_the_master_and_of_a_track_through_the_master(soundfont):
    p = _project()
    loud = [Effect("limiter", {"guadagno": 12, "tetto": -1, "rilascio": 50})]
    master = effect_render.CalibrationSession(p, None, 2.5, 4.5)
    track_loop = effect_render.CalibrationSession(p, p.get_track("Chitarra"), 2.5, 4.5)
    p.master_effects = loud
    track_through_master = effect_render.CalibrationSession(p, p.get_track("Chitarra"), 2.5, 4.5)
    try:
        for session in (master, track_loop, track_through_master):
            session.prepare()
        assert master.is_master and master.preroll == 2.0
        dry = master.mix([])
        wet = master.mix(loud)
        assert dry.shape == wet.shape == (2 * RATE, 2)
        assert _rms(wet) > 2 * _rms(dry)
        assert np.abs(wet).max() <= 10 ** (-1 / 20) + 1e-3
        assert _rms(track_loop.mix([])) == pytest.approx(_rms(dry), rel=0.05)   # stesso mix, senza master
        assert _rms(track_through_master.mix([])) > 2 * _rms(track_loop.mix([]))
    finally:
        for session in (master, track_loop, track_through_master):
            session.cleanup()


@needs_pedalboard
def test_panel_edits_the_master_chain():
    w = _window()
    panel = w.effects_panel
    assert w.master_fx_btn.text() == "FX"
    w.master_fx_btn.click()
    assert panel.is_master and panel.sends_card is None and panel.with_others_check.isHidden()
    panel.mastering_btn.click()
    assert [(e.kind, e.preset) for e in w.project.master_effects] == [
        ("eq", "Neutro"), ("compressore", "Colla del mix"), ("limiter", "Più forte")]
    assert w.master_fx_btn.text() == "FX 3" and "Limiter" in w.master_fx_btn.toolTip()
    assert w.track_headers["Chitarra"].fx_btn.text() == "FX"                      # le tracce non cambiano
    panel.cards[2].power_btn.setChecked(False)
    assert w.master_fx_btn.text() == "FX 2"
    panel.revert_changes()
    assert w.project.master_effects == [] and w.master_fx_btn.text() == "FX"

    panel.open_for("Chitarra")                                              # da una traccia al master
    panel.add_effect("eq")
    panel.copy_to(None)
    assert [e.kind for e in w.project.master_effects] == ["eq"]
    assert w.project.master_effects[0] is not w.project.get_track("Chitarra").effects[0]
    w.master_fx_btn.click()
    assert panel.is_master and [c.effect.kind for c in panel.cards] == ["eq"]
    w.undo()                                                                # il progetto viene sostituito
    assert panel.is_master and panel.track.effects is w.project.master_effects
    panel.close_panel()
    assert not panel.is_open()


# ------------------------------------------------------------------ amplificatore: sovracampionamento e IR

def _spurious_db(y, f0):
    """Energia non armonica rispetto a quella armonica sotto i 10 kHz (dB)."""
    spectrum = np.abs(np.fft.rfft(y * np.hanning(len(y)))) ** 2
    f = np.fft.rfftfreq(len(y), 1.0 / RATE)
    harmonic = np.zeros_like(f, dtype=bool)
    for k in range(1, int(24000 / f0) + 1):
        harmonic |= np.abs(f - k * f0) < 6
    band = f < 10000
    return 10 * np.log10(spectrum[band & ~harmonic].sum() / spectrum[band & harmonic].sum())


@needs_pedalboard
def test_high_gain_amp_has_no_audible_aliasing_on_high_notes():
    x = _tone(2.0, 1318.5)                                             # Mi acuto
    params = dict(preset_params("amplificatore", "Metal"), cassa="nessuna")
    y = apply_effect_chain(x, RATE, [Effect("amplificatore", clamp_params("amplificatore", params))],
                           with_tail=False)
    assert _spurious_db(y[RATE // 2:RATE // 2 + RATE, 0], 1318.5) < -45    # senza sovracampionamento: -22 dB
    fuzz = apply_effect_chain(x, RATE, [Effect("distorsione", preset_params("distorsione", "Fuzz"))],
                              with_tail=False)
    assert _spurious_db(fuzz[RATE // 2:RATE // 2 + RATE, 0], 1318.5) < -45


@needs_pedalboard
def test_oversampling_adds_no_delay_and_keeps_the_length():
    from core import effects
    frames = effects._OS_BLOCK * 3 + 123                                # piu' pezzi, lunghezza qualsiasi
    t = np.arange(frames) / RATE
    burst = 0.001 * np.sin(2 * np.pi * 1000 * t) * np.hanning(frames)   # in banda, livello basso: tanh ~ lineare
    x = np.stack([burst, -burst], axis=1).astype(np.float32)
    y = effects._oversampled([effects.Saturation(0.0)])(x, RATE)
    assert y.shape == x.shape
    assert np.abs(y - x).max() < 1e-3 * np.abs(x).max() * 10            # stesso segnale, nessun ritardo


def test_polyphase_resamplers_match_direct_filtering():
    from core import effects
    rng = np.random.RandomState(1)
    h = effects._os_filter(4)
    x = rng.randn(20000, 2)
    up = effects._Upsampler(h, 4, 2)
    got = np.concatenate([up.process(x[i:i + 3000]) for i in range(0, len(x), 3000)])
    stuffed = np.zeros((len(x) * 4, 2))
    stuffed[::4] = x
    ref = np.stack([np.convolve(stuffed[:, c], h * 4)[:len(stuffed)] for c in range(2)], axis=1)
    assert np.abs(got - ref).max() < 1e-9
    v = rng.randn(80000, 2)
    down = effects._Downsampler(h, 4, 2)
    got = np.concatenate([down.process(v[i:i + 12000]) for i in range(0, len(v), 12000)])
    ref = np.stack([np.convolve(v[:, c], h)[:len(v)] for c in range(2)], axis=1)[::4]
    assert np.abs(got - ref).max() < 1e-9


@needs_pedalboard
def test_numpy_saturation_matches_pedalboard_distortion():
    import pedalboard
    x = (np.random.RandomState(0).randn(2, 5000) * 0.3).astype(np.float32)
    for drive in (0, 12, 30):
        ref = pedalboard.Distortion(drive_db=drive)(x, RATE)
        assert np.abs(np.tanh(x * 10 ** (drive / 20)) - ref).max() < 1e-5


def _write_ir(path, rate=48000, cabinet="4x12"):
    from core.audio_tracks import write_wav
    from core.effects import cabinet_ir
    ir = cabinet_ir(cabinet, rate) * 0.2
    write_wav(path, np.stack([ir, ir], axis=1), rate, bits=24)


def test_ir_file_is_resampled_and_normalized_like_the_internal_cabinets(tmp_path):
    from core.effects import cabinet_ir, ir_file_problem, load_ir_file
    path = str(tmp_path / "cassa96k.wav")
    _write_ir(path, 96000)
    ir = load_ir_file(path, RATE)
    ref = cabinet_ir("4x12", RATE)
    response = lambda h: 20 * np.log10(np.abs(np.fft.rfft(h, RATE))[[100, 1000, 3000]])  # noqa: E731
    assert np.abs(response(ir) - response(ref)).max() < 1.5                 # stessa curva, stesso livello
    assert ir_file_problem(path) == ""
    assert ir_file_problem("") == "nessun file scelto"
    assert ir_file_problem(str(tmp_path / "manca.wav")) == "file non trovato"
    bad = tmp_path / "rotto.wav"
    bad.write_bytes(b"non e' un wav")
    assert ir_file_problem(str(bad)) == "non e' un WAV leggibile"


@needs_pedalboard
def test_amp_with_ir_file_saves_relative_path_and_falls_back_when_missing(tmp_path):
    from core.effects import chain_signature, uses_ir_file
    (tmp_path / "ir").mkdir()
    path = str(tmp_path / "ir" / "cassa.wav")
    _write_ir(path, cabinet="vintage_1x10")
    p = _project()
    amp = Effect("amplificatore", clamp_params("amplificatore", dict(preset_params("amplificatore", "Blues"),
                                                                     cassa="file")), ir=path)
    p.get_track("Chitarra").effects = [amp]
    assert uses_ir_file(amp)
    text = project_to_text(p, base_dir=str(tmp_path))
    assert 'cassa=file' in text and 'ir="ir/cassa.wav"' in text
    back = parse_project_text(text, base_dir=str(tmp_path))
    assert os.path.samefile(back.get_track("Chitarra").effects[0].ir, path)

    x = _tone(0.5, 220)
    with_file = apply_effect_chain(x, RATE, [amp], with_tail=False)
    internal = Effect("amplificatore", clamp_params("amplificatore", dict(amp.params, cassa="combo_1x12")))
    signature = chain_signature([amp])
    _write_ir(path, cabinet="4x12")                                         # il file cambia su disco
    os.utime(path, (1, 1))
    assert chain_signature([amp]) != signature                              # la cache non lo riusa
    os.remove(path)
    missing = apply_effect_chain(x, RATE, [amp], with_tail=False)           # ripiego: Combo 1x12
    assert np.allclose(missing, apply_effect_chain(x, RATE, [internal], with_tail=False))
    assert not np.allclose(with_file, missing)


@needs_pedalboard
def test_panel_asks_for_the_ir_file_when_choosing_file_cabinet(tmp_path):
    path = str(tmp_path / "Mesa 4x12.wav")
    _write_ir(path)
    w = _window()
    panel = w.effects_panel
    w.open_effects_panel("Chitarra")
    panel.add_effect("amplificatore")
    card = panel.cards[0]
    assert card.ir_row.isHidden()
    answers = [""]
    panel.choose_ir_file = lambda current="": answers.pop(0)
    card.knobs["cassa"].combo.setCurrentIndex(5)                            # File IR…, poi annullato
    assert card.effect.params["cassa"] == 1 and card.knobs["cassa"].combo.currentIndex() == 1
    answers = [path]
    card.knobs["cassa"].combo.setCurrentIndex(5)
    track = w.project.get_track("Chitarra")
    assert track.effects[0].ir == path and track.effects[0].params["cassa"] == 5
    assert not card.ir_row.isHidden() and card.ir_label.text() == "Mesa 4x12.wav"
    os.remove(path)
    card._refresh_ir_row()
    assert "non trovato" in card.ir_label.text()
    panel.close_panel()


# ------------------------------------------------------------------ amplificatore: tone stack e stadio di potenza

def _db_at(ir, freqs):
    spectrum = np.abs(np.fft.rfft(ir, RATE))
    return np.array([20 * np.log10(spectrum[int(f)]) for f in freqs])


def test_tone_stack_matches_the_analog_circuit_and_interacts_like_a_real_amp():
    from core.effects import TONE_STACKS, _tone_stack_analog, tone_stack_ir
    # digitale (bilineare) contro analogico, a meta' corsa
    values = TONE_STACKS["fender"]
    b, a = _tone_stack_analog(0.5, 0.5, np.exp(-0.5 * 3.4), *values)
    analog = lambda f: 20 * np.log10(abs(np.polyval(b[::-1], 2j * np.pi * f) / np.polyval(a[::-1], 2j * np.pi * f)))  # noqa: E731
    ir = tone_stack_ir("fender", 5, 5, 5, RATE)
    digital = _db_at(ir, [100, 700, 2000])
    offset = digital[0] - analog(100)                                   # la normalizzazione e' solo un guadagno
    assert all(abs(digital[i] - offset - analog(f)) < 0.5 for i, f in enumerate([100, 700, 2000]))
    # il classico "scavo" dei medi
    low, mid, high = _db_at(ir, [100, 700, 4000])
    assert mid < low - 5 and mid < high - 3
    # medi a 0 scavano di piu', a 10 riempiono
    assert _db_at(tone_stack_ir("fender", 5, 0, 5, RATE), [700])[0] < mid - 5
    assert _db_at(tone_stack_ir("fender", 5, 10, 5, RATE), [700])[0] > mid + 2
    # le manopole interagiscono: gli alti alzano anche i medi-alti
    assert _db_at(tone_stack_ir("fender", 5, 5, 10, RATE), [1000])[0] > _db_at(ir, [1000])[0] + 1
    # Marshall: scavo meno profondo di Fender
    m_low, m_mid = _db_at(tone_stack_ir("marshall", 5, 5, 5, RATE), [100, 700])
    assert (m_low - m_mid) < (low - mid)
    assert np.abs(ir[-100:]).max() < 1e-3                               # la risposta si esaurisce


@needs_pedalboard
def test_power_stage_adds_warm_harmonics_without_dc():
    x = _tone(2.0, 220)
    third, second = [], []
    for power in (0, 40, 80):
        params = dict(preset_params("amplificatore", "Pulito brillante"), cassa="nessuna", guadagno=6,
                      potenza=power)
        y = apply_effect_chain(x, RATE, [Effect("amplificatore", clamp_params("amplificatore", params))],
                               with_tail=False)[RATE // 2:RATE // 2 + RATE, 0]
        spectrum = np.abs(np.fft.rfft(y * np.hanning(len(y))))
        second.append(spectrum[440] / spectrum[220])
        third.append(spectrum[660] / spectrum[220])
        assert abs(float(y.mean())) < 1e-3                               # niente componente continua
    assert second[0] < 1e-4 < second[1]                                 # armoniche pari solo con il finale
    assert third[0] < third[1] < third[2]
    params = dict(preset_params("amplificatore", "Metal"), cassa="nessuna")
    y = apply_effect_chain(_tone(2.0, 1318.5), RATE, [Effect("amplificatore", clamp_params("amplificatore", params))],
                           with_tail=False)
    assert _spurious_db(y[RATE // 2:RATE // 2 + RATE, 0], 1318.5) < -45


# ------------------------------------------------------------------ export asciutto (re-amping)

@needs_pedalboard
def test_dry_export_leaves_out_effects_sends_pan_and_master(tmp_path):
    from core.audio_tracks import read_wav, write_wav
    from core.model import AudioClip
    from core.playback import dry_track, render_project_mix, render_project_mix_to_wav
    src = str(tmp_path / "chitarra.wav")
    write_wav(src, _tone(1.0, 330), RATE, bits=24)
    p = Project(name="t")
    gtr = p.add_audio_track("Chitarra")
    gtr.audio_clips.append(AudioClip("Ripresa", src, 0.0))
    gtr.effects = [Effect("amplificatore", preset_params("amplificatore", "Metal")),
                   Effect("delay", preset_params("delay", "Eco lungo"))]
    gtr.pan = 20
    p.master_effects = [Effect("limiter", preset_params("limiter", "Molto forte"))]
    wet, _ = render_project_mix(p, tracks=[gtr])
    dry, _ = render_project_mix(p, tracks=[gtr], dry=True)
    plain = dry_track(gtr)
    assert (gtr.pan, len(gtr.effects)) == (20, 2)                       # la traccia del progetto non cambia
    assert (plain.pan, plain.effects, plain.reverb, plain.chorus) == (64, [], 0, 0)
    assert len(wet) > len(dry)                                          # la coda del delay c'e' solo con effetti
    assert np.allclose(dry[:, 0], dry[:, 1])                            # pan al centro
    assert np.abs(dry[:RATE, 0] - _tone(1.0, 330)[:, 0]).max() < 0.02   # il suono registrato, cosi' com'e'
    out = str(tmp_path / "asciutto.wav")
    render_project_mix_to_wav(p, out, tracks=[gtr], dry=True)
    samples, rate = read_wav(out)
    assert rate == RATE and len(samples) == len(dry)


@needs_pedalboard
def test_dry_export_is_offered_in_the_track_menus(monkeypatch):
    w = _window()
    calls = []
    monkeypatch.setattr(w, "export_track_wav", lambda name, dry=False: calls.append((name, dry)))
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QMenu
    import gui.arrangement_view as view_module

    class PickDryExport(QMenu):
        def exec(self, *args):
            return next(a for a in self.actions() if a.text().startswith("Esporta WAV asciutto"))
    monkeypatch.setattr(view_module, "QMenu", PickDryExport)
    for name in ("Chitarra", "Voce"):
        w.arrangement_view.show_track_menu(name, QPoint(0, 0))
    assert calls == [("Chitarra", True), ("Voce", True)]


# ------------------------------------------------------------------ saturazione dipendente dalla frequenza

def _amp_out(x_mono, preset, **overrides):
    params = dict(preset_params("amplificatore", preset), cassa="nessuna", potenza=0, **overrides)
    x = np.stack([x_mono, x_mono], axis=1).astype(np.float32)
    y = apply_effect_chain(x, RATE, [Effect("amplificatore", clamp_params("amplificatore", params))],
                           with_tail=False)
    return y[RATE // 2:RATE // 2 + RATE, 0]


def _thd_db(f0, preset, amp=0.3):
    t = np.arange(RATE * 2) / RATE
    spectrum = np.abs(np.fft.rfft(_amp_out(amp * np.sin(2 * np.pi * f0 * t), preset) * np.hanning(RATE))) ** 2
    fund = spectrum[int(f0) - 2:int(f0) + 3].sum()
    harm = sum(spectrum[int(k * f0) - 2:int(k * f0) + 3].sum() for k in range(2, 11))
    return 10 * np.log10(harm / fund)


@needs_pedalboard
def test_low_notes_distort_less_than_mid_notes_like_a_tube_stage():
    for preset in ("Blues", "Rock classico", "Metal"):
        assert _thd_db(82.41, preset) < _thd_db(329.6, preset) - 8, preset      # Mi2 contro Mi4
    t = np.arange(RATE * 2) / RATE
    f1, f2 = 82.41, 123.47                                              # power chord Mi2 + Si2
    y = _amp_out(0.2 * (np.sin(2 * np.pi * f1 * t) + np.sin(2 * np.pi * f2 * t)), "Rock classico")
    spectrum = np.abs(np.fft.rfft(y * np.hanning(RATE))) ** 2
    f = np.fft.rfftfreq(RATE, 1.0 / RATE)
    harmonic = np.zeros_like(f, dtype=bool)
    for base in (f1, f2):
        for k in range(1, 40):
            harmonic |= np.abs(f - k * base) < 3
    band = (f > 20) & (f < 2000)
    imd = 10 * np.log10(spectrum[band & ~harmonic].sum() / spectrum[band & harmonic].sum())
    assert imd < -18                                                    # senza pre-enfasi: -14 dB


@needs_pedalboard
def test_frequency_dependent_saturation_keeps_the_bass_balance():
    t = np.arange(RATE * 2) / RATE

    def level(f):
        y = _amp_out(0.001 * np.sin(2 * np.pi * f * t), "Rock classico")
        return 20 * np.log10(np.sqrt((y ** 2).mean()))
    assert -7 < level(82) - level(1000) < -3                            # come prima della pre-enfasi (-4,5 dB)


# ------------------------------------------------------------------ spostamento del punto di lavoro (TubeStage)

@needs_pedalboard
def test_tube_stage_is_plain_saturation_when_played_softly_and_chunking_does_not_matter():
    from core import effects
    t = np.arange(RATE) / RATE
    soft = np.stack([0.02 * np.sin(2 * np.pi * 330 * t)] * 2, axis=1).astype(np.float32)
    tube = effects._oversampled([effects.TubeStage(12.0)])(soft, RATE)
    plain = effects._oversampled([effects.Saturation(12.0)])(soft, RATE)
    assert np.array_equal(tube, plain)
    t3 = np.arange(RATE * 3) / RATE
    hits = np.where((t3 % 0.5) < 0.1, 0.6, 0.03) * np.sin(2 * np.pi * 196 * t3)
    x = np.stack([hits, hits], axis=1).astype(np.float32)
    whole = effects._oversampled([effects.TubeStage(20.0, 1.0)])(x, RATE)
    original = effects._OS_BLOCK
    try:
        effects._OS_BLOCK = 8192                                        # pezzi piu' piccoli
        pieces = effects._oversampled([effects.TubeStage(20.0, 1.0)])(x, RATE)
    finally:
        effects._OS_BLOCK = original
    assert np.array_equal(whole, pieces)


def _note_level(y, t, start, end, freq):
    a, b = int(start * RATE), int(end * RATE)
    return 20 * np.log10(np.hypot((y[a:b] * np.sin(2 * np.pi * freq * t[a:b])).mean(),
                                  (y[a:b] * np.cos(2 * np.pi * freq * t[a:b])).mean()))


@needs_pedalboard
def test_hard_hits_make_the_amp_breathe_and_recover():
    t = np.arange(int(RATE * 1.2)) / RATE
    quiet = 0.03 * np.sin(2 * np.pi * 196 * t)
    hit_then_quiet = np.where(t < 0.2, 0.6 * np.sin(2 * np.pi * 196 * t), quiet)

    def run(x, preset):
        params = dict(preset_params("amplificatore", preset), cassa="nessuna", potenza=0)
        y = apply_effect_chain(np.stack([x, x], axis=1).astype(np.float32), RATE,
                               [Effect("amplificatore", clamp_params("amplificatore", params))], with_tail=False)
        return y[:, 0]
    for preset, deepest in (("Blues", -2.0), ("Rock classico", -2.0)):
        after, alone = run(hit_then_quiet, preset), run(quiet, preset)
        dip = _note_level(after, t, 0.21, 0.23, 196) - _note_level(alone, t, 0.21, 0.23, 196)
        later = _note_level(after, t, 0.28, 0.32, 196) - _note_level(alone, t, 0.28, 0.32, 196)
        recovered = _note_level(after, t, 0.8, 1.0, 196) - _note_level(alone, t, 0.8, 1.0, 196)
        assert -8.0 < dip < deepest, (preset, dip)                      # subito dopo il colpo: un po' di fiato in meno
        assert dip < later < 0.0                                         # poi recupera...
        assert abs(recovered) < 0.3                                      # ...fino a tornare com'era
    clean_after, clean_alone = run(hit_then_quiet, "Pulito brillante"), run(quiet, "Pulito brillante")
    assert abs(_note_level(clean_after, t, 0.21, 0.23, 196) - _note_level(clean_alone, t, 0.21, 0.23, 196)) < 0.5


@needs_pedalboard
def test_loud_notes_get_even_harmonics_and_power_chords_no_sub_rumble():
    t = np.arange(RATE * 2) / RATE
    for amp, expect_even in ((0.5, True), (0.005, False)):
        y = _amp_out(amp * np.sin(2 * np.pi * 220 * t), "Rock classico")
        spectrum = np.abs(np.fft.rfft(y * np.hanning(RATE)))
        second = 20 * np.log10(spectrum[440] / spectrum[220])
        assert (second > -30) if expect_even else (second < -60), (amp, second)
    f1, f2 = 82.41, 123.47
    y = _amp_out(0.2 * (np.sin(2 * np.pi * f1 * t) + np.sin(2 * np.pi * f2 * t)), "Rock classico")
    spectrum = np.abs(np.fft.rfft(y * np.hanning(RATE))) ** 2
    f = np.fft.rfftfreq(RATE, 1.0 / RATE)
    harmonic = np.zeros_like(f, dtype=bool)
    for base in (f1, f2):
        for k in range(1, 40):
            harmonic |= np.abs(f - k * base) < 3
    total = spectrum[(f > 20) & (f < 2000) & harmonic].sum()
    sub = spectrum[(f > 20) & (f < 75) & ~harmonic].sum()
    assert 10 * np.log10(sub / total) < -18                             # niente brontolio sotto il power chord
