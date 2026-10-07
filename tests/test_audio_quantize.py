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
