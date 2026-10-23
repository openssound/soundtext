"""
Test del motore di quantizzazione audio -> notazione (Audio-to-SoundText).
Nessuna dipendenza da ffmpeg/sounddevice: usa solo core.audio_quantize
e core.notation, quindi eseguibile senza hardware audio o librerie di
analisi installate. Esecuzione:
    python3 -m pytest tests/test_audio_quantize.py -v
oppure:
    python3 tests/test_audio_quantize.py
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.audio_quantize import (
    AudioEvent, events_to_tokens, audio_events_to_validated_text, grid_slot_beats,
)
from core.notation import validate_track_text

ALL_GRIDS = [(4, False), (8, False), (8, True), (16, False), (16, True), (32, False), (64, False)]


def _melodic_events():
    # c*4 (quarto di nota) @100, vuoto, e*4 (ottavo) @90
    return [
        AudioEvent(start_sec=0.0, end_sec=0.5, velocity=100, midi_pitch=60),
        AudioEvent(start_sec=1.0, end_sec=1.25, velocity=90, midi_pitch=64),
    ]


def test_grid_slot_beats_matches_notation_formula():
    assert grid_slot_beats(16, False) == 0.25
    assert abs(grid_slot_beats(16, True) - (0.25 * 2 / 3)) < 1e-9
    assert grid_slot_beats(8, False) == 0.5
    assert abs(grid_slot_beats(8, True) - (0.5 * 2 / 3)) < 1e-9
    assert grid_slot_beats(4, False) == 1.0


def test_events_to_tokens_starts_with_grid_command():
    for denom, ternary in ALL_GRIDS:
        tokens = events_to_tokens(_melodic_events(), tempo_bpm=120,
                                   grid_denominator=denom, ternary=ternary)
        expected_prefix = f"{denom}{'T' if ternary else ''}:"
        assert tokens[0] == expected_prefix


def test_events_to_tokens_produces_valid_syntax_for_all_grids():
    for denom, ternary in ALL_GRIDS:
        text = " ".join(events_to_tokens(_melodic_events(), 120, denom, ternary))
        ok, msg = validate_track_text(text, {})
        assert ok, f"grid={denom} ternary={ternary}: {msg}\n{text}"


def test_empty_events_still_valid():
    tokens = events_to_tokens([], 120, 16, False)
    assert tokens == ["16:"]
    ok, msg = validate_track_text(" ".join(tokens), {})
    assert ok, msg


def test_percussion_events_simultaneous_block():
    events = [
        AudioEvent(start_sec=0.0, end_sec=0.0, velocity=100, perc_name="kick"),
        AudioEvent(start_sec=0.0, end_sec=0.0, velocity=100, perc_name="hihat"),
        AudioEvent(start_sec=0.5, end_sec=0.5, velocity=80, perc_name="snare"),
    ]
    text = " ".join(events_to_tokens(events, 120, 16, False))
    ok, msg = validate_track_text(text, {})
    assert ok, msg
    assert "[" in text and "]" in text


def test_gap_becomes_rest_token():
    tokens = events_to_tokens(_melodic_events(), 120, 16, False)
    rest_tokens = [t for t in tokens if t == "r" or (t[:-1].isdigit() and t.endswith("r"))]
    assert rest_tokens, tokens


def test_velocity_emitted_only_on_change():
    events = [
        AudioEvent(start_sec=0.0, end_sec=0.25, velocity=100, midi_pitch=60),
        AudioEvent(start_sec=0.25, end_sec=0.5, velocity=100, midi_pitch=62),
        AudioEvent(start_sec=0.5, end_sec=0.75, velocity=60, midi_pitch=64),
    ]
    tokens = events_to_tokens(events, 120, 16, False)
    velocity_tokens = [t for t in tokens if t.endswith("@")]
    assert velocity_tokens == ["100@", "60@"]


def test_velocity_clamped_to_valid_range():
    events = [AudioEvent(start_sec=0.0, end_sec=0.25, velocity=999, midi_pitch=60)]
    text = " ".join(events_to_tokens(events, 120, 16, False))
    ok, msg = validate_track_text(text, {})
    assert ok, msg
    assert "127@" in text


def test_ternary_only_applies_where_selected():
    tokens = events_to_tokens(_melodic_events(), 120, 16, True)
    assert tokens[0] == "16T:"


def test_audio_events_to_validated_text_returns_valid_text():
    text = audio_events_to_validated_text(_melodic_events(), 120, 16, False, {})
    ok, msg = validate_track_text(text, {})
    assert ok, msg


def test_audio_events_to_validated_text_empty_events():
    text = audio_events_to_validated_text([], 120, 16, False, {})
    assert text == "16:"


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


# --------------------------------------------------------------- quantizzazione regolabile

from core.audio_quantize import AudioEvent as _Ev, QuantizeSettings, clean_events, events_to_tokens as _tokens
from core.notation import parse_track_text


def _starts(tokens, default_octave=4):
    """Gli inizi (in beat) delle note del testo generato."""
    return [round(e.start, 4) for e in parse_track_text(" ".join(tokens), {}, default_octave=default_octave)
            if e.kind in ("note", "block", "perc")]


def test_default_settings_give_the_same_result_as_before():
    events = _melodic_events()
    assert _tokens(events, 120, 16, settings=QuantizeSettings()) == _tokens(events, 120, 16)


def test_strength_moves_notes_part_of_the_way_on_the_fine_grid():
    # a 120 BPM 1 beat = 0,5 s: la seconda nota e' 0,25 beat in ritardo sul 2
    events = [_Ev(0.0, 0.4, 100, 60), _Ev(0.625, 0.9, 100, 62)]
    assert _starts(_tokens(events, 120, 4)) == [0.0, 1.0]
    half = _tokens(events, 120, 4, settings=QuantizeSettings(strength=0.5))
    assert half[0] == "64:" and _starts(half) == [0.0, 1.125]
    none = _tokens(events, 120, 4, settings=QuantizeSettings(strength=0.0))
    assert _starts(none) == [0.0, 1.25]


def test_window_leaves_the_far_notes_alone():
    events = [_Ev(0.03, 0.2, 100, 60), _Ev(0.6, 0.8, 100, 62)]      # 0,06 e 0,2 beat dalla griglia di 1/4
    narrow = _tokens(events, 120, 4, settings=QuantizeSettings(window=0.25))   # entro 1/8 di beat
    assert _starts(narrow) == [0.0, 1.1875]                          # la seconda resta (arrotondata a 1/64)


def test_swing_moves_the_second_eighth_of_each_pair():
    events = [_Ev(i * 0.25, i * 0.25 + 0.2, 100, 60 + i) for i in range(4)]   # ottavi dritti
    swung = _tokens(events, 120, 8, settings=QuantizeSettings(swing=0.66))
    assert _starts(swung) == [0.0, 0.6875, 1.0, 1.6875]                # 0,66 arrotondato a 1/64
    triplets = _tokens(events, 120, 8, ternary=True, settings=QuantizeSettings(swing=0.66))
    assert triplets == _tokens(events, 120, 8, ternary=True)          # sulle terzine lo swing non vale


def test_cleanup_drops_short_notes_and_merges_repeated_ones():
    events = [_Ev(0.0, 0.2, 100, 60), _Ev(0.21, 0.4, 90, 60), _Ev(0.5, 0.52, 100, 64), _Ev(0.6, 0.9, 100, 62)]
    cleaned = clean_events(events, min_note_sec=0.04, merge_gap_sec=0.03)
    assert [(e.start_sec, e.end_sec, e.midi_pitch) for e in cleaned] == [(0.0, 0.4, 60), (0.6, 0.9, 62)]
    assert events[0].end_sec == 0.2                                   # gli originali non cambiano
    kept = clean_events(events, merge_gap_sec=0.005)                   # pausa piu' lunga: restano due
    assert [e.midi_pitch for e in kept] == [60, 60, 64, 62]


def test_adjusted_text_is_always_valid():
    events = _melodic_events()
    for s in (QuantizeSettings(strength=0.3), QuantizeSettings(window=0.5, swing=0.6),
              QuantizeSettings(min_note_sec=0.05, merge_gap_sec=0.05)):
        for grid, ternary in ((16, False), (8, True), (4, False)):
            text = " ".join(_tokens(events, 97, grid, ternary=ternary, settings=s, monophonic=True))
            assert validate_track_text(text, {})[0], (s, grid, ternary, text)


def test_a_note_starting_while_the_previous_still_sounds_is_kept():
    # legato: la prima nota finisce dopo l'inizio della seconda (1/16 a 120 BPM = 0,125 s)
    events = [_Ev(0.0, 0.45, 100, 60), _Ev(0.25, 0.5, 100, 62)]
    tokens = _tokens(events, 120, 16)
    assert _starts(tokens) == [0.0, 0.5]
    assert tokens[2:] == ["2c*4", "2d*4"]                         # la prima si accorcia fino alla seconda
