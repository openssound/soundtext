"""
Test per il motore di suggerimenti di autocompletamento (core/completion.py).
Esecuzione:
    python3 -m pytest tests/ -v
oppure semplicemente:
    python3 tests/test_completion.py
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.completion import completions_for_word, current_word_bounds
from core.notation import Pattern
from core.instruments import get_instrument


def test_current_word_bounds_stops_at_space_and_brackets():
    assert current_word_bounds("8: c e", 6) == (5, 6)           # "c e" -> parola "e"
    assert current_word_bounds("[c*4 e*4", 8) == (5, 8)         # dentro un blocco, "e*4"
    assert current_word_bounds("4(2C7", 5) == (2, 5)            # non oltrepassa la parentesi tonda


def test_no_completions_for_empty_word():
    assert completions_for_word("") == []


def test_chord_quality_completions():
    result = completions_for_word("C")
    assert "Cmaj7" in result
    assert "Cm" in result
    assert "C7" in result
    assert "C" not in result  # non ripropone il prefisso gia' digitato


def test_chord_quality_completions_keep_multiplier_and_accidental():
    result = completions_for_word("2C#m")
    assert "2C#m7" in result
    assert all(r.startswith("2C#m") for r in result)


def test_percussion_and_dynamics_completions():
    drums = get_instrument("Drums")
    result = completions_for_word("hi", instrument=drums)
    assert "hihat" in result
    assert "hihat_open" in result

    result = completions_for_word("m")
    assert "mf@" in result
    assert "mp@" in result


def test_percussion_completions_excluded_for_non_percussive_instrument():
    # Su una traccia non percussiva (es. Piano), 'c' non deve suggerire
    # 'crash': e' una nota (c*4...), non un colpo di batteria.
    piano = get_instrument("Piano")
    result = completions_for_word("c", instrument=piano)
    assert "crash" not in result

    drums = get_instrument("Drums")
    result = completions_for_word("c", instrument=drums)
    assert "crash" in result

    # Senza strumento noto si resta permissivi (comportamento originale).
    result = completions_for_word("c")
    assert "crash" in result


def test_pattern_reference_completions():
    patterns = {"Riff": Pattern(name="Riff", tokens=[]), "Ride": Pattern(name="Ride", tokens=[])}
    result = completions_for_word("%Ri", patterns=patterns)
    assert set(result) == {"%Riff", "%Ride"}


def test_midi_reference_completions_are_lazy():
    calls = []

    def provider():
        calls.append(1)
        return ["Blues/bass_line", "Guitar/intro"]

    assert completions_for_word("C", midi_ref_names=provider) != []
    assert calls == []  # non invocata per un token non-&

    result = completions_for_word("&Blu", midi_ref_names=provider)
    assert result == ['&"Blues/bass_line"']          # il nome va sempre fra virgolette
    assert calls == [1]
    assert completions_for_word('&"Gu', midi_ref_names=provider) == ['&"Guitar/intro"']


def test_voicing_suffix_completions_use_applicable_voicings():
    guitar = get_instrument("Guitar")
    result = completions_for_word("Cmaj7.dr", instrument=guitar)
    assert "Cmaj7.drop2" in result

    piano = get_instrument("Piano")
    result = completions_for_word("Cmaj7.dr", instrument=piano)
    assert "Cmaj7.drop2" not in result  # 'drop2' non e' pertinente per la tastiera


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
