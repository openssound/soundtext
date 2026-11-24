"""Il controllo armonico (core/harmony_check.py): dove la melodia stona con basso e accompagnamento, e la soglia che i generatori
di «Un brano in 60 secondi» devono rispettare in ogni genere e atmosfera."""

import collections

import pytest

from core import harmony_check as hc
from core import quicksong as q
from core import song_generate as E
from core.project_io import parse_project_text

HEADER = "ST: 2.6\nTempo: 100 BPM\nMetrica: 4/4\nTonalita: C\n\n"


def _song(melody, chord="4: 4C", bass="4: 4c*2"):
    text = E.add_track(HEADER, "Piano", chord, compact=False)["text"]
    text = E.add_track(text, "Bass", bass, compact=False)["text"]
    return E.add_track(text, "Flute", melody, compact=False)["text"]


def test_a_melody_note_a_semitone_above_the_chord_is_a_clash():
    clashes = hc.check_text(_song("4: 4f*4"), ["Flute"])
    assert [c.kind for c in clashes] == ["minor_second"] and clashes[0].other_track == "Piano"
    assert "battuta 1, quarto 1" in str(clashes[0])


def test_a_chord_tone_is_not_a_clash():
    assert hc.check_text(_song("4: 4e*4"), ["Flute"]) == []
    assert hc.check_text(_song("4: 2g*4 2e*4"), ["Flute"]) == []


def test_the_tritone_against_the_bass_is_a_clash():
    kinds = {c.kind for c in hc.check_text(_song("4: 4f#*4"), ["Flute"])}
    assert "tritone" in kinds


def test_short_notes_off_the_beat_do_not_count():
    assert hc.check_text(_song("4: r 2f*4 2e*4 r", chord="4: 4C"), ["Flute"]) != []        # il fa dura un quarto: pesa
    assert hc.check_text(_song("4: e*4 r r r r r r r"), ["Flute"]) == []                  # (nessuna nota fuori posto)
    weak = hc.check_text(_song("8: r f*4 r e*4 r e*4 r e*4"), ["Flute"])                   # un ottavo in levare: passaggio, non scontro
    assert weak == []


def test_the_command_line_reports_the_clashes(tmp_path, capsys):
    path = tmp_path / "brano.st"
    path.write_text(_song("4: 4f*4"), encoding="utf-8")
    assert hc.main([str(path)]) == 1
    assert "seconda minore" in capsys.readouterr().out
    path.write_text(_song("4: 4e*4"), encoding="utf-8")
    assert hc.main([str(path)]) == 0


def _sweep(duration=30):
    rows = []
    for genre in q.GENRES_DATA:
        for mood in q.GENRES_DATA[genre]["moods"]:
            song = q.quick_song({"genre": genre, "mood": mood, "seed": 5, "duration": duration, "variety": 0})
            project = parse_project_text(song["text"], "Brano")
            melody = [song["choices"]["instruments"]["melody"]]
            clashes = hc.check_project(project, melody_tracks=melody)
            rows.append((genre, mood, clashes, hc.weighty_notes(project, melody) or 1))
    return rows


@pytest.fixture(scope="module")
def sweep():
    return _sweep()


def test_every_genre_and_mood_stays_under_the_clash_threshold(sweep):
    """Le combinazioni di genere e atmosfera con il seme fisso: gli scontri sono pochi. Le soglie sono sopra i valori di oggi (circa il 2,3 %
    delle note che pesano nel totale, il 6,5 % nel genere peggiore, il 37 % nella combinazione peggiore, l'orchestrale misteriosa con poche
    note): scendono se i generatori migliorano e il test fallisce se peggiorano."""
    assert len(sweep) >= 250
    total = sum(len(c) for _g, _m, c, _n in sweep)
    weighty = sum(n for _g, _m, _c, n in sweep)
    assert total / weighty <= 0.035, f"{total} scontri su {weighty} note"
    tritones = sum(1 for _g, _m, clashes, _n in sweep for c in clashes if c.kind == "tritone")
    assert tritones / weighty <= 0.01, f"{tritones} tritoni col basso"
    worst = [(len(c) / n, g, m) for g, m, c, n in sweep if len(c) / n > 0.5]
    assert not worst, worst
    per_genre = collections.defaultdict(lambda: [0, 0])
    for genre, _m, clashes, n in sweep:
        per_genre[genre][0] += len(clashes)
        per_genre[genre][1] += n
    bad = {g: round(a / b, 3) for g, (a, b) in per_genre.items() if a / b > 0.1}
    assert not bad, bad


def test_the_colour_of_the_atmosphere_does_not_add_clashes_the_plain_one_lacks(sweep):
    """L'accompagnamento colorato (settime, tensione) non deve far stonare la melodia piu' di quello a triadi."""
    by = collections.defaultdict(lambda: [0, 0])
    for _g, mood, clashes, n in sweep:
        how = q._MOOD_COLOR.get(mood, {}).get("chords") or "plain"
        by[how][0] += len(clashes)
        by[how][1] += n
    plain = by["plain"][0] / by["plain"][1]
    for how in ("tension", "seventh"):
        assert by[how][0] / by[how][1] <= plain + 0.03, (how, by[how], by["plain"])
