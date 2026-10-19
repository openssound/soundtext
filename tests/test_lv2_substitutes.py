import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)

from core import effects
from core.effects import LV2_SUBSTITUTES, chain_signature, plugin_substitute, tail_seconds
from core.model import Effect

TS9 = "lv2:http://guitarix.sourceforge.net/plugins/gxts9#ts9sim"


def _unusable(monkeypatch):
    monkeypatch.setattr(effects, "_lv2_usable", lambda uri: False)


def test_missing_lv2_plugin_plays_its_builtin_substitute(monkeypatch):
    _unusable(monkeypatch)
    sub = plugin_substitute(Effect(kind="plugin", plugin=TS9))
    assert (sub.kind, sub.preset) == ("distorsione", "Overdrive")
    assert sub.params == effects.preset_params("distorsione", "Overdrive")
    reverb = plugin_substitute(Effect(kind="plugin", plugin="lv2:urn:ardour:a-reverb"))
    assert reverb.kind == "riverbero" and tail_seconds([Effect(kind="plugin", plugin="lv2:urn:ardour:a-reverb")]) \
        == tail_seconds([reverb])


def test_no_substitute_for_usable_unknown_or_non_lv2_plugins(monkeypatch):
    monkeypatch.setattr(effects, "_lv2_usable", lambda uri: True)
    assert plugin_substitute(Effect(kind="plugin", plugin=TS9)) is None          # il plugin c'e'
    _unusable(monkeypatch)
    assert plugin_substitute(Effect(kind="plugin", plugin="lv2:urn:sconosciuto")) is None
    assert plugin_substitute(Effect(kind="plugin", plugin="vst3:C:/x.vst3")) is None
    assert plugin_substitute(Effect(kind="riverbero")) is None


def test_every_substitute_is_a_real_preset():
    for kind, preset in LV2_SUBSTITUTES.values():
        assert preset in effects.EFFECT_KINDS[kind]["presets"]


def test_substitution_changes_the_cache_key(monkeypatch):
    chain = [Effect(kind="plugin", plugin=TS9)]
    monkeypatch.setattr(effects, "_lv2_usable", lambda uri: True)
    with_plugin = chain_signature(chain)
    _unusable(monkeypatch)
    assert chain_signature(chain) != with_plugin


def test_fx_summary_says_what_plays_instead(monkeypatch):
    _unusable(monkeypatch)
    from gui.effects_panel import fx_summary
    from core.model import Project
    project = Project(name="p")
    track = project.add_track("Chitarra", "Piano", "c")
    track.effects = [Effect(kind="plugin", plugin=TS9)]
    text = fx_summary(track)
    assert "Overdrive" in text and "non disponibile" in text


def test_missing_lv2_instrument_falls_back_to_the_soundfont(monkeypatch):
    """AVL Drums (x42) su Windows: la traccia suona con la sua batteria
    General MIDI invece di restare muta."""
    _unusable(monkeypatch)
    import core.effect_render as er
    from core.model import Project
    from core.tempo_map import build_tempo_beat_map
    project = Project(name="p")
    track = project.add_track("Batteria", "Drums", "kick snare kick snare")
    track.synth = "lv2:http://gareus.org/oss/lv2/avldrums#RedZeppelin"
    assert effects.lv2_instrument_missing(track.synth)
    assert not effects.lv2_instrument_missing("vst3:C:/x.vst3")
    request = er.prepare_stem(project, track, build_tempo_beat_map(project))
    try:
        assert request.synth == "" and request.dry_key.startswith("midi")     # strada del SoundFont
    finally:
        request.cleanup()
    assert er.plugin_uses(project) == []                                      # niente precaricamento
