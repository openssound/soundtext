"""ST-language 2.7 dentro SoundText: titolo e autori, tonalita' per battuta e
strumenti traspositori letti e riscritti nel file .st, note di abbellimento
e arpeggio nell'export MIDI, autocompletamento dei nuovi token."""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

SONG = """ST: 2.7
Titolo: Prova
Autore: A. Autore
Parole: P. Paroliere
Tempo: 100 BPM
Metrica: 4/4
Tonalita: 1: C, 3: G

Strumento TrombaSib:
  program=56 percussione=no ottava=4 range=54-82 poly=no voicing=monophonic trasposizione=-2

Traccia Tromba [TrombaSib]:
  4: $segno $C7 d'g c e f g | a b c*5 d*5 $tocoda | f# g a b $ds $coda | c*5 C$arp 2r |
  "la la la la" "2: lo lo lo lo"
"""


def test_song_headers_and_transposition_survive_a_save():
    from core.project_io import parse_project_text, project_to_text
    project = parse_project_text(SONG)
    assert (project.title, project.composer, project.lyricist) == ("Prova", "A. Autore", "P. Paroliere")
    assert project.key == "C" and project.key_changes == [(1, "C"), (3, "G")]
    assert project.get_track("Tromba").instrument.transposition == -2
    text = project_to_text(project)
    for line in ("Titolo: Prova", "Autore: A. Autore", "Parole: P. Paroliere", "Tonalita: 1: C, 3: G",
                 "trasposizione=-2"):
        assert line in text, line
    again = parse_project_text(text)
    assert (again.title, again.key_changes) == ("Prova", [(1, "C"), (3, "G")])


def test_changing_the_key_field_changes_bar_one_of_the_list():
    from core.project_io import parse_project_text, project_to_text
    project = parse_project_text(SONG)
    project.key = "D"
    assert "Tonalita: 1: D, 3: G" in project_to_text(project)


def test_score_has_title_and_transposed_part():
    from core.musicxml_export import project_to_musicxml
    from core.project_io import parse_project_text
    xml = project_to_musicxml(parse_project_text(SONG))
    assert "<work-title>Prova</work-title>" in xml and "<chromatic>-2</chromatic>" in xml
    assert '<grace slash="yes"/>' in xml and '<lyric number="2">' in xml and "<segno/>" in xml


def test_midi_export_plays_the_grace_note_before_the_note(tmp_path):
    import mido
    from core.midi_export import export_project_to_midi
    from core.project_io import parse_project_text
    project = parse_project_text("Tempo: 120 BPM\n\nPiano:\n  d'g c C$arp\n")
    path = str(tmp_path / "g.mid")
    export_project_to_midi(project, path)
    ons = []
    for track in mido.MidiFile(path).tracks:
        now = 0
        for msg in track:
            now += msg.time
            if msg.type == "note_on" and msg.velocity:
                ons.append((now, msg.note))
    ons.sort()
    assert ons[:2] == [(0, 62), (60, 60)]               # Re di abbellimento, poi il Do
    arpeggio = [t for t, _n in ons[2:]]
    assert arpeggio == sorted(arpeggio) and len(set(arpeggio)) == len(arpeggio)   # note una dopo l'altra


def test_completion_of_navigation_marks_and_chord_symbols():
    from core.completion import completions_for_word
    assert completions_for_word("$se") == ["$segno"]
    assert "c$staccatissimo" in completions_for_word("c$st")
    assert "$Am7" in completions_for_word("$Am")
    assert "C69" in completions_for_word("C6")
