"""Micro-tempo per stile (docs, 8.3): lo scrive core.humanize_text con shift=N, e sposta il suono, non il ritmo."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _config_isolation  # noqa: F401,E402

from core.humanize_text import humanize_drums  # noqa: E402

TEXT = "16: 105@ kick r 70@ hihat r 100@ [snare hihat] 3r | kick r snare r |"


def test_amount_zero_and_unknown_styles_leave_the_text_alone():
    assert humanize_drums(TEXT, "funk", 0) == TEXT
    assert humanize_drums(TEXT, "bossa") == TEXT
    assert humanize_drums("kick shift=5 snare", "funk") == "kick shift=5 snare"          # gia' scritto a mano


def test_funk_pushes_the_snare_back_and_always_resets():
    out = humanize_drums(TEXT, "funk")
    assert "shift=14 [snare hihat]" in out and "shift=14 snare" in out
    assert out.split()[-1] == "shift=0"
    assert humanize_drums(TEXT, "funk", 0.5).count("shift=7") == 2           # il cursore scala


def test_punk_pulls_the_kick_forward():
    assert "shift=-6 kick" in humanize_drums(TEXT, "punk")


def test_the_sound_moves_but_the_written_rhythm_does_not():
    from core.model import Project
    project = Project(name="t", tempo_bpm=100)
    project.add_track("Drums", "Drums", humanize_drums(TEXT, "funk"))
    plain = Project(name="t", tempo_bpm=100)
    plain.add_track("Drums", "Drums", TEXT)
    got = [(e.name, e.start, e.shift) for e in project.tracks[0].parsed_events({}, meter=project.meter()) if e.kind != "rest"]
    base = [(e.name, e.start) for e in plain.tracks[0].parsed_events({}, meter=plain.meter()) if e.kind != "rest"]
    assert [(n, s) for n, s, _ in got] == base
    assert any(shift == 14 for _n, _s, shift in got)


def test_bass_and_comping_of_a_genre_are_shifted_as_a_whole():
    from core.humanize_text import humanize_part
    assert humanize_part("8: c d e", "bass", "soul") == "shift=8 8: c d e shift=0"
    assert humanize_part("8: c d e", "bass", "soul", 0.5).startswith("shift=4 ")
    assert humanize_part("8: c d e", "bass", "soul", 0) == "8: c d e"
    assert humanize_part("8: c d e", "bass", "bossa") == "8: c d e"


def test_quick_song_shifts_the_bass_of_soul_through_patterns_too():
    from core.project_io import parse_project_text
    from core.quicksong import quick_song
    song = quick_song({"genre": "soul", "mood": "romantica", "duration": 30, "seed": 1})
    project = parse_project_text(song["text"], "x")
    bass = project.get_track("Bass")
    shifts = {e.shift for e in bass.parsed_events(project.patterns, meter=project.meter()) if e.kind == "note"}
    assert shifts == {8}
    exact = quick_song({"genre": "soul", "mood": "romantica", "duration": 30, "seed": 1, "human": 0})
    assert "shift=" not in exact["text"]
