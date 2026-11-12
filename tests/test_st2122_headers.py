"""st-language 2.12.2: l'intestazione corta vale per ogni strumento scritto
per intero ("Flute:", "Violin 2:", "Flauto:"), una riga "Nome:" che non e'
uno strumento da' un avviso invece di sparire in silenzio, e l'export MIDI
non si ferma con una metrica dal denominatore che non e' una potenza di 2."""

import mido
import pytest

from core import instruments, settings
from core.midi_export import export_project_to_midi
import st_language
from core.project_io import parse_project_text, project_to_text


@pytest.fixture(autouse=True)
def _clean_instruments():
    """Ogni test parte senza strumenti personalizzati."""
    def reset():
        for name in list(instruments._load_custom_instruments()):
            instruments.remove_custom_instrument(name)
        instruments._unresolved_instruments.clear()
        settings._load()
    reset()
    yield
    reset()


def test_gm_name_opens_a_track():
    project = parse_project_text("Bass:\n  4: c d e f |\n\nFlute:\n  4: c d e f |\n")
    assert [t.name for t in project.tracks] == ["Bass", "Flute"]
    assert project.file_warnings == []
    flute = project.get_track("Flute")
    assert instruments.get_instrument(flute.instrument_name).gm_program == 73


@pytest.mark.parametrize("header, name", [("Flute:", "Flute"), ("Violin 2:", "Violin 2"), ("Flauto:", "Flauto")])
def test_full_names_and_aliases_open_a_track_without_warnings(header, name):
    project = parse_project_text(f"{header}\n  4: c d e f |\n")
    assert [t.name for t in project.tracks] == [name]
    assert project.file_warnings == []


def test_misspelled_header_warns_and_makes_no_track():
    project = parse_project_text("Bass:\n  4: c d e f |\n\nPianoo:\n  4: c d e f |\n")
    assert [t.name for t in project.tracks] == ["Bass"]
    assert len(project.file_warnings) == 1
    line, message = project.file_warnings[0]
    assert line == 4
    assert "Pianoo" in message and "piano" in message.lower().replace("pianoo", "")


def test_section_label_after_a_blank_line_warns():
    project = parse_project_text("Piano:\n  4: c d e f |\n\nVerse:\n  4: c d e f |\n")
    assert [t.name for t in project.tracks] == ["Piano"]
    assert len(project.file_warnings) == 1 and "Verse" in project.file_warnings[0][1]


def test_unknown_header_without_a_body_is_silent():
    project = parse_project_text("Piano:\n  4: c d e f |\n\nVerse:\n")
    assert project.file_warnings == []


def test_header_inside_a_body_stays_in_the_body():
    project = parse_project_text("Piano:\n  4: c d |\n  Pianoo:\n  4: e f |\n")
    assert project.file_warnings == []
    assert "Pianoo:" in project.get_track("Piano").text
    ok, _error = st_language.validate(project.get_track("Piano").text)
    assert not ok


def test_flute_track_round_trip():
    text = project_to_text(parse_project_text("Flute:\n  4: c d e f |\n"))
    assert "\nFlute:\n" in "\n" + text
    again = parse_project_text(text)
    assert [t.name for t in again.tracks] == ["Flute"]
    assert again.file_warnings == []
    assert project_to_text(again) == text


@pytest.mark.parametrize("metrica, written", [
    ("3/4", (3, 4)), ("3/3", (4, 4)), ("6/12", (8, 16)), ("4/6", (5, 8)), ("4/0", None)])
def test_midi_export_with_any_time_signature(tmp_path, metrica, written):
    project = parse_project_text(f"Tempo: 100 BPM\nMetrica: {metrica}\n\nPiano:\n  4: c d e f\n")
    path = tmp_path / "out.mid"
    export_project_to_midi(project, str(path))
    found = [(m.numerator, m.denominator) for m in mido.MidiFile(str(path)).tracks[0] if m.type == "time_signature"]
    assert found == ([written] if written else [])
