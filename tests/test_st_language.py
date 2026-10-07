"""
La libreria st_language (repository openssound/st-language) dentro SoundText:
il lettore dei file .st e l'esportazione MIDI della libreria danno gli stessi
risultati dell'applicazione, e i due condividono lo stesso motore. I test
della libreria da sola (conformita', CLI, pacchetto) stanno nel suo repository.
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest

import st_language as st
from st_language import song as st_song

EXAMPLES = sorted(glob.glob(os.path.join(ROOT, "examples", "*.st")))


# ------------------------------------------------------------------ uguale a SoundText

@pytest.mark.parametrize("path", EXAMPLES, ids=os.path.basename)
def test_song_reader_matches_soundtext(path):
    from core.project_io import load_project_file
    project = load_project_file(path)
    song = st.load_song(path)
    assert (song.tempo_bpm, song.time_sig, song.key) == (project.tempo_bpm, project.time_sig, project.key)
    assert song.tempo_changes == project.tempo_changes and song.metrica_changes == project.metrica_changes
    assert {n: p.tokens for n, p in song.patterns.items()} == {n: p.tokens for n, p in project.patterns.items()}
    assert [(t.name, t.instrument_name, t.text, t.mute, t.solo) for t in song.tracks] == \
           [(t.name, t.instrument_name, t.text, t.mute, t.solo) for t in project.tracks]


@pytest.mark.parametrize("path", EXAMPLES, ids=os.path.basename)
def test_midi_export_has_the_same_notes_as_soundtext(path, tmp_path):
    import mido
    from core.midi_export import export_project_to_midi
    from core.project_io import load_project_file
    app, lib = str(tmp_path / "app.mid"), str(tmp_path / "lib.mid")
    export_project_to_midi(load_project_file(path), app)
    st.to_midi(st.load_song(path), lib)

    def notes(file):
        out = []
        for track in mido.MidiFile(file).tracks:
            now = 0
            for msg in track:
                now += msg.time
                if msg.type == "note_on" and msg.velocity:
                    out.append((msg.channel, msg.note, now))
        return sorted(out)
    assert notes(lib) == notes(app)




def test_soundtext_and_library_share_one_engine():
    import core.chords
    import core.musicxml_export
    import core.notation
    import core.tempo_map
    import st_language.chords
    import st_language.musicxml
    import st_language.notation
    import st_language.timing
    assert core.notation is st_language.notation and core.chords is st_language.chords
    assert core.tempo_map is st_language.timing and core.musicxml_export is st_language.musicxml
    from core.instruments import InstrumentProfile
    assert InstrumentProfile is st_language.instruments.InstrumentProfile
    assert st_song.flatten_clips_to_text.__module__ == "st_language.song"
