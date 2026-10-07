"""Trasposizione: transpose=N e %Nome+N (ST-language 2.5)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _config_isolation  # noqa: E402,F401

import pytest  # noqa: E402

from st_language.notation import (  # noqa: E402
    Pattern, compute_token_spans, parse_track_text, tokenize, validate_track_text,
)


def pitches(text, patterns=None, kinds=("note",)):
    return [(e.letter, e.octave) for e in parse_track_text(text, patterns or {}) if e.kind in kinds]


def pats(**bodies):
    return {name: Pattern(name=name, tokens=tokenize(body)) for name, body in bodies.items()}


def test_transpose_command_moves_the_following_notes():
    assert pitches("c d transpose=2 c d transpose=0 c") == [
        ("c", 4), ("d", 4), ("d", 4), ("e", 4), ("c", 4)]
    assert pitches("transpose=-1 c e") == [("b", 3), ("d#", 4)]
    assert pitches("transpose=12 c*4 transpose=-12 c*4") == [("c", 5), ("c", 3)]


def test_pattern_reference_with_semitones_and_multiplier():
    p = pats(T="4: c e g")
    assert pitches("%T %T+7 %T-5", p) == [
        ("c", 4), ("e", 4), ("g", 4), ("g", 4), ("b", 4), ("d", 5), ("g", 3), ("b", 3), ("d", 4)]
    assert pitches("2%T+2", p) == [("d", 4), ("f#", 4), ("a", 4)] * 2
    assert pitches("%T+0", p) == pitches("%T", p)


def test_transposition_is_inherited_and_added_by_patterns():
    p = pats(T="4: c e g", U="%T+2 c")
    assert pitches("transpose=3 %T", p)[0] == ("d#", 4)
    # transpose=3 piu' %T+4: sette semitoni in tutto
    assert pitches("transpose=3 %T+4", p)[:3] == [("g", 4), ("b", 4), ("d", 5)]
    # un pattern dentro un pattern trasposto si somma
    assert pitches("%U+1", p) == [("d#", 4), ("g", 4), ("a#", 4), ("c#", 4)]


def test_transpose_inside_a_pattern_stays_in_the_pattern():
    p = pats(A="transpose=5 c d", B="c")
    assert pitches("%A %B", p) == [("f", 4), ("g", 4), ("c", 4)]
    # il comando dentro il pattern vale rispetto alla chiamata
    assert pitches("%A+2", p) == [("g", 4), ("a", 4)]


def test_transpose_before_and_after_a_pattern_call_only_at_that_level():
    p = pats(B="c")
    assert pitches("transpose=2 %B %B+1 transpose=0 %B", p) == [("d", 4), ("d#", 4), ("c", 4)]


def test_key_signature_is_followed_when_transposing():
    # key=G (fa diesis): +2 va in La, che ha il sol diesis
    assert pitches("key=G f g transpose=2 f g") == [("f#", 4), ("g", 4), ("g#", 4), ("a", 4)]
    # key=Eb: +2 va in Fa, che ha il si bemolle
    assert pitches("key=Eb e a transpose=2 e a b") == [
        ("eb", 4), ("ab", 4), ("f", 4), ("bb", 4), ("c", 5)]
    # verso il basso: re minore (si bemolle) -3 semitoni va in si minore (fa diesis)
    assert pitches("key=Dm b a transpose=-3 b a") == [("bb", 4), ("a", 4), ("g", 4), ("f#", 4)]


def test_without_a_key_flats_stay_flats():
    assert pitches("eb db*5 transpose=2 eb db*5") == [("eb", 4), ("db", 5), ("f", 4), ("eb", 5)]
    assert pitches("c transpose=1 c") == [("c", 4), ("c#", 4)]


def test_relative_octaves_follow_the_written_notes():
    # rel: ragiona sulle note scritte; la trasposizione e' applicata dopo
    assert pitches("rel: g a b transpose=2 g a b") == [
        ("g", 3), ("a", 3), ("b", 3), ("a", 3), ("b", 3), ("c#", 4)]


def test_chords_and_slash_bass():
    ev = parse_track_text("C7 transpose=5 C7/E transpose=12 Cm/Eb*3", {})
    assert [(e.symbol, e.bass, e.octave) for e in ev] == [("C7", None, 4), ("F7", "A", 4), ("Cm", "Eb", 4)]
    ev = parse_track_text("transpose=-7 Cm7/Bb Db/F", {})
    assert [(e.symbol, e.bass, e.octave) for e in ev] == [("Fm7", "Eb", 3), ("Gb", "Bb", 3)]
    # una fondamentale che scavalca il Do cambia ottava
    ev = parse_track_text("B transpose=1 B", {})
    assert [(e.symbol, e.octave) for e in ev] == [("B", 4), ("C", 5)]


def test_slides_blocks_and_voices():
    ev = parse_track_text("transpose=3 c>e*5 [c e g]", {})
    assert (ev[0].letter, ev[0].octave, ev[0].slide_points) == ("d#", 4, [("g", 5)])
    assert [(i["letter"], i["octave"]) for i in ev[1].items] == [("d#", 4), ("g", 4), ("a#", 4)]
    ev = parse_track_text("{ c d ; e } transpose=2 { c d ; e }", {})
    assert [(e.letter, e.voice) for e in ev if e.kind == "note"] == [
        ("c", 1), ("d", 1), ("e", 2), ("d", 1), ("e", 1), ("f#", 2)]


def test_percussion_and_rests_are_not_transposed():
    ev = parse_track_text("transpose=5 kick r snare c", {})
    assert [(e.kind, e.name) for e in ev if e.kind == "percussion"] == [("percussion", "kick"), ("percussion", "snare")]
    assert [e.letter for e in ev if e.kind == "note"] == ["f"]


def test_midi_references_follow_transpose():
    # il testo espanso di un &"Nome" e' fatto di note come le altre
    from st_language import notation
    previous = notation._midi_ref_resolver
    notation.set_midi_ref_resolver(lambda name, midi_dir: tokenize("4: c e g"))
    try:
        assert pitches('transpose=2 &"Riff"') == [("d", 4), ("f#", 4), ("a", 4)]
    finally:
        notation.set_midi_ref_resolver(previous)


def test_midi_reference_with_semitones():
    """&"Nome"+N e &"Nome"-N: come %Nome+N; il nome sta fra le virgolette,
    quindi puo' contenere '-' senza ambiguita'."""
    from st_language import notation
    previous = notation._midi_ref_resolver
    files = {"Riff": "4: c e g", "Blues/bass-line": "4: a*2 c*3", "Bass-2": "4: d e"}

    def resolver(name, midi_dir):
        if name in files:
            return tokenize(files[name])
        raise FileNotFoundError(name)

    notation.set_midi_ref_resolver(resolver)
    try:
        assert pitches('&"Riff"+7') == [("g", 4), ("b", 4), ("d", 5)]
        assert pitches('&"Riff"-5') == [("g", 3), ("b", 3), ("d", 4)]
        assert pitches('2&"Riff"-12') == [("c", 3), ("e", 3), ("g", 3)] * 2
        assert pitches('transpose=2 &"Riff"+3') == [("f", 4), ("a", 4), ("c", 5)]
        assert pitches('&"Blues/bass-line"') == [("a", 2), ("c", 3)]
        assert pitches('&"Blues/bass-line"+2') == [("b", 2), ("d", 3)]
        assert pitches('&"Blues/bass-line"-3') == [("f#", 2), ("a", 2)]
        # il file che si chiama 'Bass-2'
        assert pitches('&"Bass-2"') == [("d", 4), ("e", 4)]
        assert pitches('&"Bass-2"+3') == [("f", 4), ("g", 4)]
        # una trasposizione dopo il riferimento non cambia le note dopo
        assert pitches('&"Riff"+7 c') [-1] == ("c", 4)
        for bad in ('&"Nope"-2', '&"Nope"+2', '&"Riff"+99', '&"Riff"-99', "&Riff"):
            assert not validate_track_text(bad, {})[0], bad
    finally:
        notation.set_midi_ref_resolver(previous)


def test_midi_reference_with_semitones_from_the_library(tmp_path):
    from core.midi_library import render_tokens_to_midi, clear_midi_ref_cache
    (tmp_path / "Bass").mkdir()
    render_tokens_to_midi("4: c*4 e*4 g*4", "Piano", 120, str(tmp_path / "Bass" / "Riff.mid"))
    clear_midi_ref_cache()
    plain = [(e.letter, e.octave) for e in parse_track_text('&"Riff"', {}, midi_dir=str(tmp_path)) if e.kind == "note"]
    up = [(e.letter, e.octave) for e in parse_track_text('&"Riff"+2', {}, midi_dir=str(tmp_path)) if e.kind == "note"]
    down = [(e.letter, e.octave) for e in parse_track_text('&"Bass/Riff"-12', {}, midi_dir=str(tmp_path)) if e.kind == "note"]
    assert plain == [("c", 4), ("e", 4), ("g", 4)]
    assert up == [("d", 4), ("f#", 4), ("a", 4)]
    assert down == [("c", 3), ("e", 3), ("g", 3)]


def test_errors():
    p = pats(T="c")
    for bad in ("transpose=61 c", "transpose=-61 c", "transpose=1.5 c", "%T+61", "%T-99", "transpose= c"):
        ok, _ = validate_track_text(bad, p)
        assert not ok, bad
    # fuori dal MIDI dopo la trasposizione
    assert not validate_track_text("c*9 transpose=12 c*5 transpose=60 c*8", p)[0]
    assert not validate_track_text("transpose=-60 c*0", p)[0]
    # '%T/3' resta un token non valido
    assert not validate_track_text("%T/3", p)[0]
    assert validate_track_text("%T+7 transpose=-12 c", p)[0]


def test_transposed_pattern_in_spans_and_midi(tmp_path):
    p = pats(T="4: c e g")
    spans = compute_token_spans("%T %T+7", p)
    assert len(spans) == 2 and spans[1][2] == 3.0
    import st_language as st
    f = tmp_path / "a.st"
    f.write_text("Pattern %T:\n  4: c*4 e*4 g*4\n\nPiano:\n  %T+12 transpose=-12 %T\n", encoding="utf-8")
    song = st.load_song(str(f))
    out = tmp_path / "a.mid"
    st.to_midi(song, str(out))
    import mido
    notes = [m.note for t in mido.MidiFile(str(out)).tracks for m in t if m.type == "note_on" and m.velocity]
    assert notes == [72, 76, 79, 48, 52, 55]


def test_extraction_keeps_transpose_commands_out_of_patterns():
    from core.reorganize import extract_patterns_from_tokens
    toks = tokenize("4: c d e f transpose=2 c d e f transpose=0 c d e f")
    new, found = extract_patterns_from_tokens(toks, [], min_window=4, min_repeats=2)
    for body in found.values():
        assert not any(t.startswith("transpose=") for t in body)
    # e il risultato suona come prima
    before = [(e.letter, e.octave, e.start) for e in parse_track_text(" ".join(toks), {}) if e.kind == "note"]
    from core.model import Project
    from core.reorganize import extract_patterns_for_project
    proj = Project(name="t")
    proj.add_track("P", "Piano", " ".join(toks))
    extract_patterns_for_project(proj, min_window=4, min_repeats=2)
    after = [(e.letter, e.octave, e.start) for e in parse_track_text(proj.tracks[0].text, proj.patterns) if e.kind == "note"]
    assert before == after


def test_a_pattern_called_in_a_transposed_region_is_extracted_with_the_same_sound():
    from core.model import Project
    from core.reorganize import extract_patterns_for_project
    text = "4: c d e f g a transpose=2 c d e f g a transpose=0 c d e f g a"
    proj = Project(name="t")
    proj.add_track("P", "Piano", text)
    before = [(e.letter, e.octave, e.start) for e in parse_track_text(text, {}) if e.kind == "note"]
    extract_patterns_for_project(proj, min_window=4, min_repeats=2)
    after = [(e.letter, e.octave, e.start) for e in parse_track_text(proj.tracks[0].text, proj.patterns) if e.kind == "note"]
    assert before == after
