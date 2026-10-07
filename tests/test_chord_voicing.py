"""
Test dei suffissi di voicing esplicito sugli accordi compatti
(Cmaj7.drop2, C7.cagEd, C.power, ...). Esecuzione:
    python3 -m pytest tests/test_chord_voicing.py -v
oppure:
    python3 tests/test_chord_voicing.py
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.notation import validate_track_text, transpose_tokens
from core.chords import (
    parse_chord_symbol, voice_chord, midi_note, GUITAR_VOICING_PATTERNS,
    applicable_voicings, recognize_chord, GENERAL_VOICINGS, GUITAR_VOICINGS, KEYBOARD_VOICINGS,
)
from core.instruments import get_instrument


def test_voicing_suffix_valid_syntax():
    ok, msg = validate_track_text("Cmaj7.drop2 C7.cagEd C.power Am7.open F.barre", {})
    assert ok, msg


def test_unknown_voicing_style_is_invalid():
    ok, msg = validate_track_text("Cmaj7.pippo", {})
    assert not ok


def test_new_chord_qualities_valid():
    ok, msg = validate_track_text("C7#9.hendrix Cadd9 Cm7b5 CmMaj7 C7sus4 C7b9", {})
    assert ok, msg


def test_guitar_table_lookup_used_when_present():
    guitar = get_instrument("Guitar")
    chord = parse_chord_symbol("Cmaj7")
    notes = voice_chord(chord, guitar.default_octave, guitar, voicing_override="drop2")
    base = midi_note(0, guitar.default_octave)
    expected = sorted(base + off for off in GUITAR_VOICING_PATTERNS["maj7"]["drop2"])
    assert notes == expected


def test_guitar_generic_fallback_when_not_in_table():
    guitar = get_instrument("Guitar")
    chord = parse_chord_symbol("Csus2")
    assert "drop3" not in GUITAR_VOICING_PATTERNS.get("sus2", {})
    notes = voice_chord(chord, guitar.default_octave, guitar, voicing_override="drop3")
    assert len(notes) >= 1  # algoritmo generico eseguito senza sollevare errori


def test_fallback_on_non_guitar_instrument():
    piano = get_instrument("Piano")
    chord = parse_chord_symbol("Cmaj7")
    barre = voice_chord(chord, piano.default_octave, piano, voicing_override="barre")
    close = voice_chord(chord, piano.default_octave, piano, voicing_override="close")
    assert barre == close


def test_inversions_put_correct_tone_in_bass():
    piano = get_instrument("Piano")
    chord = parse_chord_symbol("C")  # intervalli [0, 4, 7]: fondamentale/terza/quinta
    inv1 = voice_chord(chord, piano.default_octave, piano, voicing_override="inv1")
    inv2 = voice_chord(chord, piano.default_octave, piano, voicing_override="inv2")
    assert min(inv1) % 12 == 4   # terza al basso
    assert min(inv2) % 12 == 7   # quinta al basso


def test_inversion_clamped_when_not_enough_tones():
    piano = get_instrument("Piano")
    chord = parse_chord_symbol("C")  # triade: nessuna settima disponibile
    inv3 = voice_chord(chord, piano.default_octave, piano, voicing_override="inv3")
    assert min(inv3) % 12 == 7   # ricade sull'inversione piu' alta disponibile (inv2)


def test_transpose_preserves_voicing_suffix():
    result = transpose_tokens(["Cmaj7.drop2"], 2, default_octave=4)
    assert result == ["Dmaj7.drop2"]


def test_voicing_overrides_default_instrument_style():
    guitar = get_instrument("Guitar")
    chord = parse_chord_symbol("Cmaj7")
    default_notes = voice_chord(chord, guitar.default_octave, guitar)
    forced_notes = voice_chord(chord, guitar.default_octave, guitar, voicing_override="drop2")
    assert default_notes != forced_notes


def test_applicable_voicings_guitar_excludes_keyboard():
    styles = set(applicable_voicings(get_instrument("Guitar")))
    assert GENERAL_VOICINGS <= styles
    assert GUITAR_VOICINGS <= styles
    assert not (KEYBOARD_VOICINGS & styles)


def test_applicable_voicings_piano_excludes_guitar():
    styles = set(applicable_voicings(get_instrument("Piano")))
    assert GENERAL_VOICINGS <= styles
    assert KEYBOARD_VOICINGS <= styles
    assert not (GUITAR_VOICINGS & styles)


def test_applicable_voicings_other_family_general_only():
    styles = set(applicable_voicings(get_instrument("Bass")))
    assert styles == GENERAL_VOICINGS


def test_recognize_chord_maj7():
    assert recognize_chord([60, 64, 67, 71]) == (0, "maj7", 4)


def test_recognize_chord_bare_fifth_recognized_as_power_chord():
    """Da quando '5' e' una qualita' vera (power chord: solo fondamentale+
    quinta), una semplice quinta non e' piu' ambigua: e' quella qualita'."""
    assert recognize_chord([60, 67]) == (0, "5", 4)


def test_recognize_chord_bare_second_still_not_recognized():
    """Un intervallo che non corrisponde a nessuna qualita' nota (es. una
    semplice seconda maggiore) resta correttamente non riconosciuto."""
    assert recognize_chord([60, 62]) is None


def test_recognize_chord_octave_doubling_keeps_lowest_anchor():
    root_pc, quality, anchor_octave = recognize_chord([48, 52, 55, 60])
    assert (root_pc, quality) == (0, "maj")
    assert anchor_octave == 3


def test_recognize_chord_single_note_not_recognized():
    assert recognize_chord([60]) is None


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
