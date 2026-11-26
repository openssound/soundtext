"""«Leggi» (core/speech_text.py, engine.speak_at): la frase che dice la battuta sotto il cursore, nelle quattro lingue,
con note, pause, alterazioni, accordi e durate."""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOBILE = os.path.join(ROOT, "mobile")
from core import speech_text as speech  # noqa: E402


def test_notes_rests_accidentals_and_durations_in_four_languages():
    items = [("r", 0.5), ("c*5", 0.5), ("f#*4", 1.0), ("bb*4", 2.0), ("e*5", 1.5)]
    it = speech.phrase(items, "it", 3, "Piano")
    assert it == "Battuta 3, Piano. pausa croma, do croma, fa diesis semiminima, si bemolle minima, mi semiminima puntata."
    en = speech.phrase(items, "en", 3, "Piano")
    assert en == "Bar 3, Piano. rest eighth note, C eighth note, F sharp quarter note, B flat half note, E dotted quarter note."
    fr = speech.phrase(items, "fr", 3, "Piano")
    assert fr == "Mesure 3, Piano. silence croche, do croche, fa dièse noire, si bémol blanche, mi noire pointée."
    es = speech.phrase(items, "es", 3, "Piano")
    assert es == "Compás 3, Piano. silencio corchea, do corchea, fa sostenido negra, si bemol blanca, mi negra con puntillo."


@pytest.mark.parametrize("lang,expected", [
    ("it", "accordo la minore settima semibreve"), ("en", "chord A minor seventh whole note"),
    ("fr", "accord la mineur septième ronde"), ("es", "acorde la menor séptima redonda")])
def test_chords_with_their_quality(lang, expected):
    assert speech.token_words("Am7!", 4.0, lang) == expected


def test_chord_with_bass_and_voicing_suffix_and_multiplier():
    assert speech.token_words("2Cmaj7.drop2!", 2.0, "it") == "accordo do maggiore settima minima"
    assert speech.token_words("G/B", 4.0, "en") == "chord G over B whole note"


def test_patterns_percussion_and_groups():
    assert speech.token_words("%HeadA1", None, "it") == "pattern HeadA1"
    assert speech.token_words("hihat_open", 0.5, "en") == "hihat open eighth note"
    assert speech.token_words("[kick hihat]", 1.0, "fr") == "kick hihat noire"


def test_durations_that_are_not_a_figure_are_said_in_beats():
    assert speech.duration_words(0.75 * 2, "it") == "semiminima puntata"
    assert speech.duration_words(2.5, "en") == "2.5 beats"
    assert speech.duration_words(2.5, "it") == "2,5 battiti"


def test_nothing_to_read():
    assert speech.phrase([], "it") == "Qui non c'è nulla da leggere."
    assert speech.phrase([("???", 1.0)], "en") == "There is nothing to read here."


def test_unknown_language_falls_back_to_english():
    assert speech.phrase([("c*5", 1.0)], "de") == "C quarter note."


def _engine():
    sys.path.insert(0, ROOT)
    sys.path.insert(0, MOBILE)
    import engine
    return engine


def test_speak_at_reads_the_bar_under_the_cursor():
    e = _engine()
    text = open(os.path.join(ROOT, "examples", "jazz_aaba.st"), encoding="utf-8").read()
    pos = text.index("r c*5 e*5 a*5 g*5 f#*5 a*5 d*5 |") + 8
    r = e.speak_at(text, pos, "it")
    assert r["bar"] == 1 and r["track"] == "Piano"
    assert r["text"].startswith("Battuta 1, Piano. pausa croma, do croma, mi croma, la croma, sol croma, fa diesis croma")
    assert e.speak_at(text, pos, "en")["text"].startswith("Bar 1, Piano. rest eighth note, C eighth note, E eighth")


def test_speak_at_a_comment_or_header_has_nothing_to_read():
    e = _engine()
    text = open(os.path.join(ROOT, "examples", "jazz_aaba.st"), encoding="utf-8").read()
    assert e.speak_at(text, 1200, "it")["text"] == "Qui non c'è nulla da leggere."


def test_speak_at_reads_chords_of_a_chord_track():
    e = _engine()
    made = e.quick_song({"genre": "pop", "mood": "calma", "duration": 30, "seed": 3, "variety": 0, "ensemble": "piano", "chords": "Am F C G"})
    # la prima nota dell'intro (il pop attacca col suo accompagnamento, a ottavi)
    pos = made["text"].index("a*4", made["text"].index('Box Piano "Intro"')) + 1
    r = e.speak_at(made["text"], pos, "it")
    assert r["bar"] == 1 and r["track"] == "Piano" and r["text"].startswith("Battuta 1, Piano. la croma, pausa croma,")
