"""Ancora di battuta 'bar=N' (ST-language 2.5)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _config_isolation  # noqa: E402,F401

from fractions import Fraction  # noqa: E402

import pytest  # noqa: E402

import st_language as st  # noqa: E402
from st_language.notation import (  # noqa: E402
    Meter, NotationError, Pattern, compute_token_spans, notation_warnings, parse_track_text, tokenize,
    validate_track_text,
)
from core.model import Project  # noqa: E402


def notes(events):
    return [(e.letter, e.start) for e in events if e.kind == "note"]


def test_anchor_pads_with_silence_up_to_the_bar():
    ev = parse_track_text("4: c d e f bar=3 g", {})
    assert notes(ev) == [("c", 0.0), ("d", 1.0), ("e", 2.0), ("f", 3.0), ("g", 8.0)]
    rest = [e for e in ev if e.kind == "rest"]
    assert [(r.start, r.duration) for r in rest] == [(4.0, 4.0)]


def test_anchor_on_the_exact_position_adds_nothing():
    ev = parse_track_text("4: c d e f bar=2 g", {})
    assert not [e for e in ev if e.kind == "rest"]
    assert notes(ev)[-1] == ("g", 4.0)


def test_anchor_at_the_start_and_bar_one():
    assert notes(parse_track_text("bar=3 4: c", {})) == [("c", 8.0)]
    assert notes(parse_track_text("4: bar=1 c", {})) == [("c", 0.0)]


def test_anchor_follows_the_time_signature_and_its_changes():
    three = Meter("3/4")
    assert notes(parse_track_text("4: bar=3 c", {}, meter=three)) == [("c", 6.0)]
    changing = Meter("4/4", [(1, "4/4"), (3, "3/4")])      # battute 1-2 in 4/4, poi 3/4
    assert notes(parse_track_text("4: bar=4 c", {}, meter=changing)) == [("c", 11.0)]


def test_anchor_inside_a_pattern_and_a_voice_block():
    pats = {"A": Pattern(name="A", tokens=tokenize("4: c d"))}
    assert notes(parse_track_text("%A bar=2 %A", pats))[-2:] == [("c", 4.0), ("d", 5.0)]
    ev = parse_track_text("4: c { d e ; bar=2 f }", {})
    # il cursore e' a 1: la voce di destra cade alla battuta 2 (beat 4) e non alla 2 del blocco
    assert ("f", 4.0) in notes(ev)


def test_anchor_does_not_cross_a_tie():
    with pytest.raises(NotationError):
        parse_track_text("4: c~ bar=2 c", {})


def test_invalid_bar_numbers():
    for bad in ("bar=0", "bar=100000"):
        ok, _ = validate_track_text(f"4: c {bad} d", {})
        assert not ok
    assert validate_track_text("4: c bar=2 d", {})[0]


def test_late_track_warns_but_still_plays():
    text = "4: c d e f g a b c bar=2 d"
    assert notes(parse_track_text(text, {}))[-1] == ("d", 8.0)          # resta dov'e'
    issues = notation_warnings(text, {})
    assert len(issues) == 1 and issues[0].bar == 2
    assert text[issues[0].char_start:issues[0].char_end] == "bar=2"
    # ... e anche per un pattern ripetuto: un solo avviso per token
    pats = {"B": Pattern(name="B", tokens=tokenize("4: c d e f bar=2 g"))}
    assert len(notation_warnings("%B %B", pats)) == 1


def test_anchor_in_range_gives_no_warning():
    assert notation_warnings("4: c d e f bar=2 g bar=4 a", {}) == []


def test_token_spans_cover_the_silence():
    spans = compute_token_spans("4: c bar=2 d", {})
    anchor = [s for s in spans if s[2] == 1.0][0]
    assert anchor[3] == 3.0


def test_song_and_project_know_their_meter(tmp_path):
    f = tmp_path / "a.st"
    f.write_text("Metrica: 3/4\n\nPiano:\n  4: bar=2 c\n", encoding="utf-8")
    song = st.load_song(str(f))
    assert [e.start for e in song.tracks[0].parsed_events(song.patterns, meter=song.meter()) if e.kind == "note"] == [3.0]
    midi = tmp_path / "a.mid"
    st.to_midi(song, str(midi))
    import mido
    mid = mido.MidiFile(str(midi))
    ticks = [m.time for t in mid.tracks for m in t if m.type == "note_on"]
    assert ticks and sum(ticks) == pytest.approx(3 * mid.ticks_per_beat)


def test_project_meter_and_midi_export(tmp_path):
    from core.midi_export import export_project_to_midi
    p = Project(name="t", time_sig="3/4")
    p.add_track("P", "Piano", "4: bar=2 c")
    assert p.meter().start_of(2) == Fraction(3)
    out = tmp_path / "p.mid"
    export_project_to_midi(p, str(out))
    import mido
    mid = mido.MidiFile(str(out))
    ticks = [m.time for t in mid.tracks for m in t if m.type == "note_on"]
    assert sum(ticks) == pytest.approx(3 * mid.ticks_per_beat)


def test_extraction_leaves_anchors_where_they_are():
    from core.reorganize import extract_patterns_from_tokens
    toks = tokenize("4: c d e f bar=2 c d e f bar=2 c d e f bar=2 c d e f")
    new, pats = extract_patterns_from_tokens(toks, [], min_window=4, min_repeats=2)
    for body in pats.values():
        assert not any(t.startswith("bar=") for t in body)
