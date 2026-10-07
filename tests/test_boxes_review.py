"""Box della vista Struttura brano: un box illeggibile non blocca l'apertura
del brano, bar=N dentro un box che non comincia da 0, transpose= che non
passa al box dopo; pattern richiamati dai box (rinomina e controllo prima
di eliminarli)."""

import st_language as st
from core.model import Clip, Project
from core.notation import validate_track_text
from core.project_io import parse_project_text, project_to_text


def _boxes(*boxes, time_sig="4/4"):
    text = f"Tempo: 120 BPM\nMetrica: {time_sig}\n\nTraccia Voce [Piano]:\n\n"
    for name, beat, body in boxes:
        text += f'Box Voce "{name}" |{beat}:\n  {body}\n\n'
    return text


def _notes(project):
    track = project.get_track("Voce")
    return [(e.start, (e.letter, e.octave)) for e in track.parsed_events(project.patterns, meter=project.meter())
            if e.kind == "note"]


def test_unreadable_box_does_not_block_opening_the_song():
    project = parse_project_text(_boxes(("A", 0, "4: c d e f |"), ("B", 4, '&"FileCheNonEsiste"')))
    track = project.get_track("Voce")
    assert [c.name for c in track.clips] == ["A", "B"]
    ok, _msg = validate_track_text(track.text, project.patterns)
    assert not ok                     # l'errore resta, sulla traccia
    # e il brano si salva e si riapre uguale
    again = parse_project_text(project_to_text(project))
    assert [c.text.strip() for c in again.get_track("Voce").clips] == ["4: c d e f |", '&"FileCheNonEsiste"']


def test_bar_anchor_inside_a_box_that_starts_later():
    # B comincia al beat 8 (battuta 3): bar=5 porta la d al beat 16.
    # C, al beat 20, deve suonare al beat 20.
    project = parse_project_text(_boxes(("A", 0, "4: c d e f |"), ("B", 8, "4: c bar=5 d"), ("C", 20, "4: e")))
    starts = [start for start, _notes in _notes(project)]
    assert starts == [0, 1, 2, 3, 8, 16, 20]


def test_bar_anchor_in_a_box_follows_the_meter():
    # In 3/4 la battuta 4 comincia al beat 9.
    project = parse_project_text(_boxes(("A", 3, "4: c bar=4 d"), ("B", 12, "4: e"), time_sig="3/4"))
    assert [start for start, _n in _notes(project)] == [3, 9, 12]


def test_library_reads_the_same_boxes(tmp_path):
    text = _boxes(("A", 0, "4: c d e f |"), ("B", 8, "4: c bar=5 d"), ("C", 20, "4: e"))
    song = st.read_song(text)
    part = song.get_track("Voce")
    starts = [e.start for e in part.parsed_events(song.patterns, meter=song.meter()) if e.kind == "note"]
    assert starts == [0, 1, 2, 3, 8, 16, 20]


def test_transpose_does_not_leak_into_the_next_box():
    plain = parse_project_text(_boxes(("A", 0, "4: c"), ("B", 1, "4: c")))
    moved = parse_project_text(_boxes(("A", 0, "transpose=2 4: c"), ("B", 1, "4: c")))
    (_, first), (_, second) = _notes(moved)
    assert first == ("d", 4)
    assert second == _notes(plain)[1][1] == ("c", 4)


def test_rename_pattern_updates_boxes_and_the_song_reopens():
    text = ("Tempo: 120 BPM\n\nPattern %Giro:\n  4: c d e f |\n\nTraccia Voce [Piano]:\n\n"
            'Box Voce "A" |0:\n  2%Giro\n\nBox Voce "B" |8:\n  %Giro+2 %GiroLungo\n\n'
            "Pattern %GiroLungo:\n  4: g |\n")
    project = parse_project_text(text)
    project.rename_pattern("Giro", "Strofa")
    clips = project.get_track("Voce").clips
    assert clips[0].text.strip() == "2%Strofa"
    assert clips[1].text.strip() == "%Strofa+2 %GiroLungo"
    again = parse_project_text(project_to_text(project))
    assert len(_notes(again)) == 8 + 4 + 1


def test_pattern_usages_lists_tracks_boxes_and_patterns():
    project = Project()
    project.add_pattern("Giro", "4: c d e f |")
    project.add_pattern("Doppio", "2%Giro")
    project.add_pattern("Altro", "4: g |")
    project.add_track("Basso", "Bass", "%Giro %Altro")
    voce = project.add_track("Voce", "Piano", "")
    voce.clips = [Clip(name="Intro", text="4: c"), Clip(name="Strofa", text="%Giro+2", start_beat=4)]
    places = project.pattern_usages("Giro")
    assert len(places) == 3
    assert any("Basso" in p for p in places)
    assert any("Strofa" in p and "Voce" in p for p in places)
    assert any("Doppio" in p for p in places)
    assert project.pattern_usages("Doppio") == []
    assert len(project.pattern_usages("Altro")) == 1
