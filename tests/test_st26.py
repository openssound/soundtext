"""ST-language 2.6 (consolidamento): reset:, &"nome" fra virgolette,
intestazione 'ST:' e parole chiave inglesi, battuta in levare."""

import pytest

from st_language import notation
from st_language.notation import NotationError, parse_track_text, tokenize


def _notes(text, patterns=None, **kwargs):
    return [(e.start, e.duration, e.letter, e.octave, e.velocity)
            for e in parse_track_text(text, patterns or {}, **kwargs) if e.kind == "note"]


# ------------------------------------------------------------------ reset:

def test_reset_restores_the_initial_state():
    text = "8: 100@ rel: key=G transpose=2 swing=60 shift=20 c f reset: c f"
    events = [e for e in parse_track_text(text, {}) if e.kind == "note"]
    after = events[2:]
    plain = [e for e in parse_track_text("c f", {}) if e.kind == "note"]
    assert [(e.letter, e.octave, e.velocity, e.duration) for e in after] == \
           [(e.letter, e.octave, e.velocity, e.duration) for e in plain]
    assert all(e.swing is None and not e.shift for e in after)


def test_reset_keeps_automations_and_the_pattern_transposition():
    events = parse_track_text("vol=40 reset: c", {})
    assert [e.value for e in events if e.kind == "control"] == [40]
    patterns = {"P": notation.Pattern("P", tokenize("transpose=5 reset: c"))}
    assert _notes("%P+2", patterns)[0][2:4] == ("d", 4)   # il +2 del richiamo resta


def test_reset_inside_a_velocity_ramp_is_an_error():
    with pytest.raises(NotationError):
        parse_track_text("60@ >> c reset: d 90@", {})
    with pytest.raises(NotationError):
        parse_track_text("reset: >> c", {})


# ------------------------------------------------------------------ &"nome"

@pytest.fixture
def library():
    files = {"riff": "4: c", "take": "4: e", "take-2": "4: g", "solo-3": "4: a", "bass line": "4: d"}

    def resolver(name, midi_dir):
        if name not in files:
            raise FileNotFoundError(name)
        return tokenize(files[name])

    previous = notation._midi_ref_resolver
    notation.set_midi_ref_resolver(resolver)
    yield files
    notation.set_midi_ref_resolver(previous)


def test_quoted_name_then_transposition(library):
    assert _notes('&"take"-2')[0][2:4] == ("d", 4)
    assert _notes('&"take-2"')[0][2:4] == ("g", 4)         # il file 'take-2', senza dubbi
    assert _notes('&"take-2"+2')[0][2:4] == ("a", 4)
    assert _notes('2&"bass line"+1')[0][2:4] == ("d#", 4)  # spazi nel nome
    assert len(_notes('2&"riff"')) == 2


def test_bare_reference_is_an_error_with_the_fix(library):
    with pytest.raises(NotationError) as info:
        parse_track_text("4: c &riff+2", {})
    assert '&"riff"+2' in str(info.value)
    with pytest.raises(NotationError, match="nessuno"):
        parse_track_text('&"nessuno"', {})


def test_old_references_are_upgraded_when_reading_files(library):
    from st_language.notation import upgrade_midi_refs
    from core.project_io import parse_project_text
    old = "4: c &riff 2&riff+7 &take-2 &solo-3 (&riff) { &take ; d } \"rock &roll\" // &riff"
    assert upgrade_midi_refs(old) == ('4: c &"riff" 2&"riff"+7 &"take-2" &"solo-3" (&"riff") '
                                     '{ &"take" ; d } "rock &roll" // &"riff"')
    # 2.5: '&take-2' era il file 'take-2' (che esiste), '&riff-1' riff trasposto
    assert upgrade_midi_refs("&take-2 &riff-1") == '&"take-2" &"riff"-1'
    assert upgrade_midi_refs('&"riff"-1 c') == '&"riff"-1 c'           # gia' nuovo: invariato
    project = parse_project_text("Tempo: 90 BPM\n\nPattern %A:\n  &riff+2\n\nPiano:\n  %A &take\n")
    assert project.get_track("Piano").text == '%A &"take"'
    assert project.patterns["A"].tokens == ['&"riff"+2']


# ------------------------------------------------------------------ ST: e parole chiave inglesi

ENGLISH = """ST: 2.6
Tempo: 100 BPM
Meter: 3/4
Key: G
Pickup: 1

Instrument Viola2:
  program=41 percussion=no octave=3 range=48-84 poly=no voicing=monophonic

Track Melodia [Viola2]:
  4: d | g a b |

Mixer Melodia:
  volume: 90 mute: yes
"""


def test_english_keywords_are_read_by_library_and_app():
    import st_language as st
    from core.project_io import parse_project_text
    song = st.read_song(ENGLISH)
    project = parse_project_text(ENGLISH)
    for x in (song, project):
        assert (x.time_sig, x.key, x.pickup, x.st_version) == ("3/4", "G", 1.0, (2, 6))
    assert song.instrument("Viola2").gm_program == 41 and song.instrument("Viola2").default_octave == 3
    track = project.get_track("Melodia")
    assert track.instrument.default_octave == 3 and track.mute and track.volume == 90


def test_saved_file_declares_the_version_and_the_pickup():
    from core.project_io import parse_project_text, project_to_text
    text = project_to_text(parse_project_text(ENGLISH))
    lines = text.splitlines()
    assert lines[0] == "ST: %d.%d" % __import__("st_language").stfile.LANGUAGE_VERSION
    assert "Levare: 1" in lines and "Metrica: 3/4" in lines and "Strumento Viola2:" in text
    again = parse_project_text(text)
    assert again.pickup == 1.0 and again.get_track("Melodia").instrument.gm_program == 41


def test_newer_version_warns_in_the_library():
    import warnings
    import st_language as st
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        st.read_song("ST: 3.0\nTempo: 90 BPM\n")
    assert caught


def test_old_instrument_form_without_program_is_not_an_instrument():
    import st_language as st
    song = st.read_song("Instrument MioSax:\n  type: tenor_sax\n")
    assert "MioSax" not in song.instruments


# ------------------------------------------------------------------ levare

def test_pickup_moves_bar_one():
    from st_language.notation import Meter, check_bar_lines
    meter = Meter("3/4", (), 1)
    assert [meter.start_of(b) for b in (1, 2, 3)] == [1, 4, 7]
    assert check_bar_lines("4: g | c e g | c 2r |", {}, "3/4", pickup=1) == []
    issues = check_bar_lines("4: g a | c e g |", {}, "3/4", pickup=1)
    assert [i.bar for i in issues] == [0]               # il levare e' la battuta 0
    events = parse_track_text("4: g bar=2 c", {}, meter=meter)
    assert [e.start for e in events if e.kind == "note"] == [0, 4]


def test_pickup_in_tempo_and_metrica_maps_and_metronome():
    import st_language as st
    from st_language.timing import build_metrica_beat_map, build_tempo_beat_map, click_grid_position
    song = st.read_song("Levare: 1\nMetrica: 3/4\nTempo: 1: 100, 2: 80\n\nPiano:\n  4: g | c e g | c 2r |\n")
    assert build_tempo_beat_map(song) == [(0.0, 100), (4.0, 80)]
    clicks = [click_grid_position(build_metrica_beat_map(song), b) for b in (0, 1, 2, 4)]
    assert [accent for _beat, accent in clicks] == [False, True, False, True]


def test_pickup_in_score_exports(tmp_path):
    import re
    import mido
    import st_language as st
    from st_language.musicxml import project_to_musicxml
    song = st.read_song("Levare: 1\nMetrica: 3/4\n\nPiano:\n  4: g | c e g | c 2r |\n")
    measures = re.findall(r"<measure[^>]*>", project_to_musicxml(song))
    assert measures[0] == '<measure number="0" implicit="yes">' and measures[1] == '<measure number="1">'
    path = tmp_path / "p.mid"
    st.to_midi(song, str(path))
    signatures = [(m.time, m.numerator) for t in mido.MidiFile(str(path)).tracks for m in t
                  if m.type == "time_signature"]
    assert signatures == [(0, 3)]


def test_pickup_field_in_the_main_window():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from core.project_io import parse_project_text
    from gui.main_window import MainWindow
    w = MainWindow()
    w.pickup_spin.setValue(1.5)
    assert w.project.pickup == 1.5
    w._replace_project(parse_project_text("Levare: 1\nMetrica: 3/4\n"))
    assert w.pickup_spin.value() == 1.0
    assert w.arrangement_view.canvas.meter_args == ("3/4", [], 1.0)
    w._dirty = False
    w.close()
