"""Gli strumenti definiti in un file .st ("Strumento Nome:") valgono per quel
brano, anche se in locale c'e' gia' uno strumento con lo stesso nome definito
diversamente (per esempio da un altro brano aperto prima)."""

import mido

import st_language as st
from core.instruments import get_instrument, set_session_instruments
from core.midi_export import export_project_to_midi
from core.project_io import parse_project_text, project_to_text


def _song(program, octave):
    return (
        "Tempo: 120 BPM\n\n"
        "Strumento ViolaProva:\n"
        f"  program={program} percussione=no ottava={octave} range=36-96 poly=no voicing=monophonic\n\n"
        "Traccia Voce [ViolaProva]:\n"
        "  4: c d e f |\n"
    )


def _program_and_notes(path):
    programs, notes = [], []
    for track in mido.MidiFile(path).tracks:
        for msg in track:
            if msg.type == "program_change":
                programs.append(msg.program)
            elif msg.type == "note_on" and msg.velocity:
                notes.append(msg.note)
    return programs, notes


def test_second_song_keeps_its_own_instrument_definition(tmp_path):
    first = parse_project_text(_song(48, 3))
    second = parse_project_text(_song(41, 5))
    assert first.get_track("Voce").instrument.gm_program == 48
    assert second.get_track("Voce").instrument.gm_program == 41
    assert second.get_track("Voce").instrument.default_octave == 5

    # L'export dell'app coincide con quello della libreria per tutti e due.
    for text, program in ((_song(48, 3), 48), (_song(41, 5), 41)):
        src = tmp_path / f"song{program}.st"
        src.write_text(text, encoding="utf-8")
        app, lib = tmp_path / f"app{program}.mid", tmp_path / f"lib{program}.mid"
        export_project_to_midi(parse_project_text(text), str(app))
        st.to_midi(st.load_song(str(src)), str(lib))
        assert _program_and_notes(app) == _program_and_notes(lib)
        assert program in _program_and_notes(app)[0]


def test_instrument_definition_survives_save_and_new_tracks():
    project = parse_project_text(_song(41, 5))
    text = project_to_text(project)
    assert "Strumento ViolaProva:" in text and "program=41" in text
    again = parse_project_text(text)
    assert again.get_track("Voce").instrument.gm_program == 41

    # Una traccia aggiunta dopo con lo stesso strumento usa la definizione del brano.
    parse_project_text(_song(48, 3))
    added = again.add_track("Altra", "ViolaProva", "")
    assert added.instrument.gm_program == 41
    again.update_track("Altra", "Altra", "ViolaProva")
    assert again.get_track("Altra").instrument.gm_program == 41


def test_session_instruments_drive_previews():
    parse_project_text(_song(48, 3))
    project = parse_project_text(_song(41, 5))
    try:
        set_session_instruments(project.instruments)
        assert get_instrument("ViolaProva").gm_program == 41
        set_session_instruments(None)
        assert get_instrument("ViolaProva").gm_program == 48   # quello registrato per primo
    finally:
        set_session_instruments(None)
