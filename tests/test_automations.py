"""
Automazioni (vol=, expr=, pan=, mod=, rev=, cho=), curve delle rampe
(>>exp, >>log, >>s) e forcelle sulle note (c<, c>): parser, errori,
trasposizione, esportazione MIDI dell'app e della libreria (control
change, anche partendo a meta' brano), forcelle in MusicXML, colori.
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core.model import Project
from core.notation import (
    RAMP_CURVES, parse_track_text, split_note_value, tokenize, transpose_tokens, validate_track_text,
)


def _controls(text):
    return [(e.name, e.start, e.duration, e.start_value, e.value, e.curve)
            for e in parse_track_text(text, {}) if e.kind == "control"]


# ------------------------------------------------------------------ parser

def test_set_values_take_no_time():
    events = parse_track_text("vol=90 c pan=-0.5 rev=40.4 d", {})
    assert [e.kind for e in events] == ["control", "note", "control", "control", "note"]
    assert _controls("vol=90 c pan=-0.5 rev=40.4 d") == [
        ("vol", 0.0, 0.0, None, 90, None), ("pan", 1.0, 0.0, None, -0.5, None),
        ("rev", 1.0, 0.0, None, 40, None)]
    assert [e.start for e in events if e.kind == "note"] == [0.0, 1.0]


def test_ramp_goes_from_the_opening_to_the_closing_value():
    assert _controls("vol=40 >>exp c d e vol=100 f") == [
        ("vol", 0.0, 0.0, None, 40, None), ("vol", 0.0, 3.0, 40, 100, "exp")]
    # '<<' e' uguale a '>>'; la curva di default e' lineare
    assert _controls("pan=1 << 2c pan=-1")[1] == ("pan", 0.0, 2.0, 1.0, -1.0, "lin")


def test_ramps_of_different_names_overlap_and_ignore_velocity_and_tempo():
    controls = _controls("vol=50 >> pan=0 >> 100@ c tempo=90 d pan=1 e vol=120")
    assert ("pan", 0.0, 2.0, 0.0, 1.0, "lin") in controls
    assert ("vol", 0.0, 3.0, 50, 120, "lin") in controls


def test_closing_without_moving_is_a_plain_change():
    assert _controls("mod=10 >> mod=90 c") == [("mod", 0.0, 0.0, None, 10, None),
                                              ("mod", 0.0, 0.0, None, 90, None)]


def test_curves():
    assert [RAMP_CURVES[c](0.5) for c in ("lin", "exp", "log", "s")] == [0.5, 0.25, 0.75, 0.5]
    for shape in RAMP_CURVES.values():
        assert shape(0) == 0 and shape(1) == 1
    velocities = [e.velocity for e in parse_track_text("20@ >>exp c d e f 100@", {})]
    assert velocities == [20, 29, 56, 100]


def test_velocity_ramp_does_not_count_automations():
    notes = [e.velocity for e in parse_track_text("20@ >> c vol=50 d< e 100@", {}) if e.kind == "note"]
    assert notes == [20, 60, 100]


def test_hairpins_use_the_current_expression():
    assert _controls("2c< d>") == [
        ("expr", 0.0, 2.0, 64, 127, "lin"), ("expr", 2.0, 0.0, None, 127, None),
        ("expr", 2.0, 1.0, 127, 64, "lin"), ("expr", 3.0, 0.0, None, 127, None)]
    assert _controls("expr=100 c'2<")[1:] == [("expr", 0.0, 2.0, 50, 100, "lin"),
                                             ("expr", 2.0, 0.0, None, 100, None)]


@pytest.mark.parametrize("text", ["c<", "c'8.<", "2C7!>", "[c e g]<", "2[c e]'2>", "c*4>d*4<", "kick<"])
def test_hairpin_on_every_sounding_token(text):
    assert validate_track_text(text, {}) == (True, "")
    assert [c[0] for c in _controls(text)] == ["expr", "expr"]


def test_split_note_value_keeps_the_hairpin_with_the_value():
    assert split_note_value("c'2<") == ("c", "'2<")
    assert split_note_value("c!'8>") == ("c!", "'8>")
    assert split_note_value("2c*4<") == ("2c*4", "<")
    assert split_note_value(">>") == (">>", "") and split_note_value("<<exp") == ("<<exp", "")


def test_transpose_keeps_hairpins():
    assert transpose_tokens(tokenize("c< C7'2> [c e]<"), 2, 4) == ["d*4<", "D7'2>", "[d*4 f#*4]<"]


def test_automations_belong_to_the_whole_track_across_voices():
    # vol=20 dentro la prima voce vale anche dopo il blocco; la forcella
    # dopo il blocco parte dall'expr scritto nella seconda voce
    controls = _controls("{ c vol=20 ; d expr=80 } e<")
    assert controls[-2:] == [("expr", 1.0, 1.0, 40, 80, "lin"), ("expr", 2.0, 0.0, None, 80, None)]
    assert _controls("vol=30 { vol=30 >> c vol=90 ; d }") [-1] == ("vol", 0.0, 1.0, 30, 90, "lin")


@pytest.mark.parametrize("text", [
    "vol=128 c", "expr=-1 c", "pan=1.5 c", "pan=-2 c",
    "vol=40 >> c d",                       # rampa mai chiusa
    "{ vol=40 >> c ; d } vol=90",          # chiusa fuori dalla voce: non vale
    "c r<",                                # forcella su una pausa
    "expr=40 >> c< expr=120",              # forcella dentro una rampa di expr
    "p@ >>quad c f@",                      # curva sconosciuta
    "4: >> c",                             # rampa dopo un comando di griglia
])
def test_errors(text):
    assert not validate_track_text(text, {})[0]


def test_old_texts_are_unchanged():
    text = "8: p@ >> c d e f ff@ tempo=120 << 2g tempo=90 c*4>d*4 SON [c e g] SOFF"
    assert all(e.kind != "control" for e in parse_track_text(text, {}))


# ------------------------------------------------------------------ MIDI

def _ccs(path):
    import mido
    out = []
    for track in mido.MidiFile(path).tracks:
        now = 0
        for msg in track:
            now += msg.time
            if msg.type == "control_change" and msg.control in (1, 7, 10, 11, 91, 93):
                out.append((now, msg.control, msg.value))
    return out


def _project(text, volume=100):
    p = Project(name="t")
    p.add_track("A", "Piano", text)
    p.tracks[0].volume = volume
    return p


def test_app_midi_writes_control_changes(tmp_path):
    from core.midi_export import export_project_to_midi
    path = str(tmp_path / "a.mid")
    export_project_to_midi(_project("4: pan=-1 c pan=0 d pan=1 e mod=50 rev=60 cho=70 f"), path)
    ccs = _ccs(path)
    assert [(t, v) for t, c, v in ccs if c == 10][-3:] == [(0, 1), (480, 64), (960, 127)]
    assert (1440, 1, 50) in ccs and (1440, 91, 60) in ccs and (1440, 93, 70) in ccs


def test_ramp_is_a_series_of_values_along_the_curve(tmp_path):
    from core.midi_export import export_project_to_midi
    path = str(tmp_path / "r.mid")
    export_project_to_midi(_project("4: vol=0 >>exp 4c vol=100"), path)
    values = [(t, v) for t, c, v in _ccs(path) if c == 7][1:]     # il primo e' quello del mixer
    assert values[0] == (0, 0) and values[-1] == (1920, 100)
    assert all(a[1] <= b[1] and a[0] <= b[0] for a, b in zip(values, values[1:]))
    middle = min(values, key=lambda tv: abs(tv[0] - 960))
    assert 20 <= middle[1] <= 30                                  # exp: a meta' circa un quarto
    assert len(values) <= 130          # al piu' 128 punti, piu' il valore scritto prima di '>>'


def test_vol_follows_the_mixer_volume(tmp_path):
    from core.midi_export import export_project_to_midi
    path = str(tmp_path / "v.mid")
    export_project_to_midi(_project("vol=100 c vol=60 d", volume=50), path)
    assert [v for _t, c, v in _ccs(path) if c == 7] == [50, 50, 30]


def test_hairpin_is_expression_during_the_note(tmp_path):
    from core.midi_export import export_project_to_midi
    path = str(tmp_path / "h.mid")
    export_project_to_midi(_project("4: 2c< d"), path)
    expr = [(t, v) for t, c, v in _ccs(path) if c == 11]
    assert expr[0] == (0, 64) and expr[-1] == (960, 127)
    assert all(a[1] <= b[1] for a, b in zip(expr, expr[1:])) and len(expr) > 10


def test_starting_mid_song_applies_the_values_written_before(tmp_path):
    from core.midi_export import export_project_to_midi
    path = str(tmp_path / "o.mid")
    export_project_to_midi(_project("4: vol=40 c pan=-1 >> d e pan=1 f expr=90 g"), path,
                           start_offset_beats=3.5)
    ccs = _ccs(path)
    at_start = {c: v for t, c, v in ccs if t == 0}
    assert at_start[7] == 40 and at_start[10] == 127
    assert (240, 11, 90) in ccs


def test_library_midi_matches_the_app(tmp_path):
    import st_language as st
    from core.midi_export import export_project_to_midi
    text = "4: vol=30 >>s c d vol=110 pan=-0.5 >>log e f pan=0.5 2g< expr=100 a> mod=40 b"
    app, lib = str(tmp_path / "app.mid"), str(tmp_path / "lib.mid")
    export_project_to_midi(_project(text), app)
    song = st.read_song(f"Tempo: 120 BPM\n\nTraccia A [Piano]:\n  {text}\n")
    st.to_midi(song, lib)
    assert _ccs(lib) == _ccs(app)


# ------------------------------------------------------------------ partitura e editor

def test_musicxml_wedges_for_volume_expression_and_hairpins():
    from core.musicxml_export import project_to_musicxml
    xml = project_to_musicxml(_project("4: vol=40 >> c d vol=90 e f> | 2g< pan=-1 >> 2a pan=1"))
    assert xml.count('<wedge type="crescendo"') == 2
    assert xml.count('<wedge type="diminuendo"') == 1
    assert xml.count('<wedge type="stop"') == 3          # il pan non e' una forcella


def test_musicxml_wedge_ending_with_the_piece_is_closed():
    from core.musicxml_export import project_to_musicxml
    xml = project_to_musicxml(_project("4: c d e f<"))
    assert xml.index('<wedge type="stop"') < xml.rindex("</measure>")
    assert xml.index('<wedge type="crescendo"') < xml.index('<wedge type="stop"')


def test_highlighter_colours_automations_and_hairpins():
    from PySide6.QtWidgets import QApplication, QPlainTextEdit
    QApplication.instance() or QApplication([])
    from gui.highlighter import NotationHighlighter, _COLORS
    editor = QPlainTextEdit()
    editor.setPlainText("vol=40 >>exp 2c< [c e]> pan=-0.5")
    h = NotationHighlighter(editor.document())
    h.rehighlight()
    colours = {(f.start, f.length): f.format.foreground().color().name()
               for f in editor.document().firstBlock().layout().formats()}
    dark = {k: v[0] for k, v in _COLORS.items()}
    assert colours[(0, 6)] == dark["state"] and colours[(7, 5)] == dark["tempo_ramp"]
    assert colours[(13, 3)] == dark["note"] and colours[(17, 6)] == dark["block"]
    assert colours[(24, 8)] == dark["state"]
