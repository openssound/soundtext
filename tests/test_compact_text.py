"""Testo generato leggibile (core/compact_text.py): barre, pattern, velocity solo dove cambia. Il suono non cambia: per ogni
stile di batteria, basso, accompagnamento, melodia e giro armonico, e per molti semi, il MIDI del testo compatto (con i suoi
pattern) e' identico a quello del testo di oggi."""
import os
import tempfile

import pytest

from core import compact_text as ct
from core import rhythm_generate as rg
from core.midi_export import export_project_to_midi
from core.project_io import parse_project_text

HEAD = "ST: 2.6\nTempo: 100 BPM\nMetrica: {meter}\nTonalita: C\n\n"


def _midi(text: str) -> bytes:
    project = parse_project_text(text, "x")
    fd, path = tempfile.mkstemp(suffix=".mid")
    os.close(fd)
    try:
        export_project_to_midi(project, path)
        with open(path, "rb") as f:
            return f.read()
    finally:
        os.remove(path)


def _song(body: str, instrument: str, patterns: dict, meter="4/4") -> str:
    return HEAD.format(meter=meter) + ct.with_patterns("", patterns).strip("\n") + ("\n\n" if patterns else "") + \
        f"Traccia Parte [{instrument}]:\n" + "\n".join("  " + line for line in body.split("\n")) + "\n"


def _same_sound(raw: str, instrument: str, bar_beats: float, name: str, meter="4/4") -> dict:
    result = ct.compact(raw, bar_beats, name)
    assert _midi(_song(raw, instrument, {}, meter)) == _midi(_song(result["text"], instrument, result["patterns"], meter)), \
        (name, result["text"][:200])
    return result


@pytest.mark.parametrize("meter,bar_beats", [("4/4", 4.0), ("3/4", 3.0), ("6/8", 3.0), ("7/8", 3.5)])
def test_every_drum_style_keeps_its_midi(meter, bar_beats):
    styles = rg.drum_styles_for_meter(meter)
    assert styles
    for style in styles:
        for seed in (1, 2, 3):
            for bars, fill, ending in ((4, 0, False), (8, 4, False), (4, 4, True), (1, 0, False)):
                raw = rg.generate_drum_pattern(style, bars, fill_every=fill, ending=ending, seed=seed, variability=rg.Variability(0.35, 0.35, 0.35),
                                               intensity="normal", phrase_fills=True)
                _same_sound(raw, "Drums", bar_beats, style, meter)


def test_every_bass_and_comping_style_keeps_its_midi():
    chords = rg.extract_chords_from_track("1: Am7 | Dm7 | G7 | Cmaj7 | F | Bm7b5 E7 | Am | Am |", {})
    var = rg.Variability(0.35, 0.35, 0.35)
    for style in rg.BASS_STYLES:
        for seed in (1, 5):
            raw = rg.generate_bass_from_chords(chords, style, octave=2, min_total_beats=32, bar_beats=4.0, seed=seed, variability=var)
            _same_sound(raw, "Bass", 4.0, style)
    for style in rg.COMPING_STYLES:
        for seed in (1, 5):
            raw = rg.generate_melodic_line(chords, style, 4, 48, 84, True, min_total_beats=32, bar_beats=4.0, seed=seed,
                                           variability=var, voice_leading=True)
            _same_sound(raw, "Piano", 4.0, style)


def test_every_progression_style_keeps_its_midi():
    for style, spec in rg.PROGRESSION_STYLES.items():
        key = "Am" if spec["mode"] == "minor" else "C"
        for seed in (1, 2):
            raw = rg.generate_chord_progression(key, style, bars=8, chord_bars=1.0, bar_beats=4.0, seed=seed)
            _same_sound(raw, "Piano", 4.0, style)


def test_repeated_bars_become_one_pattern_and_the_rest_stays_written():
    raw = rg.generate_drum_pattern("rock", 8, fill_every=4, seed=3, phrase_fills=True)
    result = ct.compact(raw, 4.0, "rock")
    assert result["text"].count("|") == 8 and "%Rock" in result["text"]
    assert "Rock" in result["patterns"] and result["patterns"]["Rock"].startswith("16: ")
    assert len(result["text"]) < len(raw) / 2                                      # molto piu' corto
    for line in result["text"].split("\n"):
        assert line.count("|") <= 4                                                # quattro battute per riga


def test_velocity_is_written_only_when_it_changes_and_at_the_start_of_each_pattern():
    result = ct.compact("16: 100@ kick r 100@ snare r 80@ kick r 80@ snare r", 1.0, "x")
    assert result["text"].count("@") == 2 and "100@" in result["text"] and "80@" in result["text"]
    raw = "16: 90@ kick r r r 90@ snare r r r 90@ kick r r r 90@ snare r r r"
    both = ct.compact(raw, 2.0, "uno")
    assert both["text"].count("@") <= 2


def test_a_long_rest_is_split_at_the_barline_but_a_note_that_crosses_it_is_left_whole():
    split = ct.compact("4: c*4 r 3r", 4.0, "x")                                  # la pausa da 3 attraversa la battuta
    assert split["text"].count("|") == 2
    long_note = ct.compact("4: c*4 4c*5 3c*4", 4.0, "x")                          # una nota che attraversa la stanghetta
    assert long_note["text"].count("|") == 1                                      # solo quella finale
    for raw in ("4: c*4 r 3r", "4: c*4 4c*5 3c*4"):
        _same_sound(raw, "Piano", 4.0, "x")


def test_existing_patterns_are_reused_and_a_clash_gets_a_new_name():
    raw = rg.generate_drum_pattern("rock", 4, seed=1, fill_every=0)
    first = ct.compact(raw, 4.0, "rock")
    again = ct.compact(raw, 4.0, "rock", existing=first["patterns"])
    assert again["patterns"] == {} and "%Rock" in again["text"]                    # stesso corpo: si riusa
    clash = ct.compact(raw, 4.0, "rock", existing={"Rock": "16: kick r r r"})
    assert "Rock2" in clash["patterns"] and "%Rock2" in clash["text"]


def test_text_that_is_not_generated_text_is_left_alone():
    for text in ("", "Am F C G", "4: c d e f | g a b c*5 |", "4: tempo=90 c d e f"):
        assert ct.compact(text, 4.0, "x") == {"text": text, "patterns": {}}
    assert ct.compact("4: c*4 d*4", 5.0, "x")["patterns"] == {}                    # una metrica che non cade sulla griglia


def test_a_quick_song_in_compact_text_sounds_exactly_like_the_extended_one_and_is_shorter():
    """«Un brano in 60 secondi»: stesso genere, atmosfera e seme, stesso suono; il testo compatto ha le barre e si legge."""
    from core.quicksong import GENRES, GENRES_DATA, quick_song
    shorter = 0
    for genre in GENRES:
        mood = GENRES_DATA[genre]["moods"][0]
        compact = quick_song({"genre": genre, "mood": mood, "duration": 15, "seed": 4})
        extended = quick_song({"genre": genre, "mood": mood, "duration": 15, "seed": 4, "compact": False})
        assert _midi(compact["text"]) == _midi(extended["text"]), (genre, mood)
        # il preludio di 15 secondi e' una sezione sola col rallentando scritto dentro (tempo=...): non si compatta
        assert compact["text"].count("|") > extended["text"].count("|") or genre == "preludio", genre
        shorter += len(compact["text"]) <= len(extended["text"]) + 200
    assert shorter >= 20
