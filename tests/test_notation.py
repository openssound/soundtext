"""
Test di base per il motore di notazione. Esecuzione:
    python3 -m pytest tests/ -v
oppure semplicemente:
    python3 tests/test_notation.py
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest

from core.notation import NotationError, parse_track_text, validate_track_text, Pattern, tokenize
from core.chords import parse_chord_symbol, voice_chord
from core.instruments import get_instrument


def test_tokenize_brackets_with_multiplier():
    toks = tokenize("2[kick hihat] snare 3r [c*4 e*4 g*4]")
    assert toks == ["2[kick hihat]", "snare", "3r", "[c*4 e*4 g*4]"]


def test_grid_and_velocity_state():
    events = parse_track_text("100@ 8: c e 60@ g a 100@ c", {})
    vels = [e.velocity for e in events]
    assert vels == [100, 100, 60, 60, 100]
    durs = {round(e.duration, 4) for e in events}
    assert durs == {0.5}  # 1/8 di nota = 0.5 beat (quarto)


def test_rest_and_multiplier():
    events = parse_track_text("4: c 3r 2c", {})
    assert [e.kind for e in events] == ["note", "rest", "note"]
    assert events[1].duration == 3.0   # 3 unita' di griglia (nera = 1 beat)
    assert events[2].duration == 2.0


def test_percussion_block():
    events = parse_track_text("8: [kick hihat] hihat", {})
    assert events[0].kind == "block"
    names = sorted(i["name"] for i in events[0].items)
    assert names == ["hihat", "kick"]


def test_pattern_expansion_and_state_persistence():
    patterns = {"Arp": Pattern(name="Arp", tokens=tokenize("16: 90@ c e g e"))}
    events = parse_track_text("%Arp", patterns)
    assert len(events) == 4
    assert all(e.velocity == 90 for e in events)
    assert all(round(e.duration, 4) == 0.25 for e in events)  # 1/16 = 0.25 beat


def test_chord_voicing_guitar_range():
    chord = parse_chord_symbol("Cmaj7")
    instr = get_instrument("Guitar")
    notes = voice_chord(chord, octave=4, instrument=instr)
    assert all(instr.range_low <= n <= instr.range_high for n in notes)
    assert len(notes) == 4  # C E G B


def test_bass_voicing_root_fifth_only():
    chord = parse_chord_symbol("G7")
    instr = get_instrument("Bass")
    notes = voice_chord(chord, octave=2, instrument=instr)
    assert len(notes) == 2  # solo fondamentale + quinta


def test_validation_reports_unknown_percussion():
    ok, msg = validate_track_text("kazoo", {})
    assert not ok and "kazoo" in msg


def test_validation_reports_missing_pattern():
    ok, msg = validate_track_text("%DoesNotExist", {})
    assert not ok and "DoesNotExist" in msg


def test_validation_reports_bad_chord_quality():
    ok, msg = validate_track_text("Cxyz123", {})
    assert not ok


def test_pipe_is_a_bar_check_that_takes_no_time():
    # '|' e' un controllo di battuta: valido, non suona e non sposta il tempo.
    ok, msg = validate_track_text("c | d", {})
    assert ok, msg
    events = parse_track_text("c d|e", {})
    assert [(e.letter, e.start) for e in events] == [("c", 0.0), ("d", 1.0), ("e", 2.0)]


# ---------------------------------------------------------------------- ottava: solo '*'

def test_octave_is_written_only_with_star():
    assert [(e.letter, e.octave) for e in parse_track_text("c*3 e*3", {})] == [("c", 3), ("e", 3)]
    assert parse_track_text("Cmaj7*3", {})[0].octave == 3
    # le vecchie forme con la barra non esistono piu': '/' e' solo il basso
    for old in ("c/3", "Cmaj7/3", "c*4>d/4"):
        with pytest.raises(NotationError):
            parse_track_text(old, {})


def test_transpose_writes_the_octave_with_star():
    from core.notation import transpose_tokens
    assert transpose_tokens(["c*3"], 2, default_octave=4) == ["d*3"]


# ---------------------------------------------------------------------- basso alternativo (accordo 'slash')

def test_chord_slash_bass_parses_and_carries_bass_field():
    ev = parse_track_text("C/E", {})
    assert ev[0].kind == "chord"
    assert ev[0].symbol == "C"
    assert ev[0].bass == "E"


def test_chord_slash_bass_lowest_note_in_export():
    from core.model import Project
    from core.midi_export import export_project_to_midi
    from core import midi_convert
    import tempfile
    import shutil

    tmpdir = tempfile.mkdtemp()
    try:
        p = Project(name="Test")
        p.add_track("Piano1", "Piano", "4: C/E*4")
        path = os.path.join(tmpdir, "slash.mid")
        export_project_to_midi(p, path)
        _, _, channels = midi_convert.analyze_midi(path)
        notes = sorted(n for _, _, n, _ in list(channels.values())[0].notes)
        # E all'ottava 3 (sotto la fondamentale C dell'accordo, ottava 4)
        # deve essere la nota piu' grave suonata: e' il punto dello slash chord.
        assert notes[0] % 12 == 4  # E
        assert notes[0] < min(n for n in notes if n % 12 == 0)  # sotto ogni Do dell'accordo
    finally:
        shutil.rmtree(tmpdir)


def test_chord_slash_bass_survives_transpose():
    from core.notation import transpose_tokens
    assert transpose_tokens(["C/E"], 2, default_octave=4) == ["D/F#"]


def test_chord_octave_and_slash_bass_together():
    ev = parse_track_text("C/E*4", {})
    assert ev[0].bass == "E"
    assert ev[0].octave == 4


# ---------------------------------------------------------------------- nuove qualita' d'accordo

def test_new_extended_and_alias_chord_qualities_valid():
    ok, msg = validate_track_text("E5 G7alt D11 A13 Cmaj13 C° C°7", {})
    assert ok, msg


def test_power_chord_quality_five_is_root_and_fifth_only():
    chord = parse_chord_symbol("E5")
    assert chord.intervals == [0, 7]


def test_diminished_alias_matches_dim_intervals():
    assert parse_chord_symbol("C°").intervals == parse_chord_symbol("Cdim").intervals
    assert parse_chord_symbol("C°7").intervals == parse_chord_symbol("Cdim7").intervals


def test_altered_dominant_alias_matches_7b9_intervals():
    assert parse_chord_symbol("G7alt").intervals == parse_chord_symbol("G7b9").intervals


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
