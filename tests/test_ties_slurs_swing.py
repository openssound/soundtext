"""
Fase 1 di ST-language 2.1: legature di valore (c~ c), legature di
portamento (c( d e f)), swing (swing=N, swing16=N), automazioni ccN= e
bend=: parser, errori, trasposizione, MIDI dell'app e della libreria,
MusicXML/ABC e colori dell'editor.
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import re
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core.model import Project
from core.notation import (
    NotationError, check_bar_lines, parse_track_text, split_note_value, swing_time, tokenize,
    transpose_tokens, validate_track_text,
)


def _sounding(text):
    return [e for e in parse_track_text(text, {}) if e.kind not in ("rest", "control", "repeat")]


# ------------------------------------------------------------------ legature di valore

def test_tie_makes_one_event_across_the_bar_line():
    events = _sounding("4: c d 2f~ | 2f g a |")
    assert [(e.letter, e.start, e.duration) for e in events] == \
        [("c", 0, 1), ("d", 1, 1), ("f", 2, 4), ("g", 6, 1), ("a", 7, 1)]
    assert check_bar_lines("4: c d 2f~ | 2f g a |", {}) == []


def test_tie_on_chords_blocks_values_and_enharmonics():
    assert [(e.kind, e.duration) for e in _sounding("C7~ C7 [c e]~ [e c] c'2~ c'8 c#~ db")] == \
        [("chord", 2), ("block", 2), ("note", 2.5), ("note", 2)]
    assert [e.duration for e in _sounding("c~ c~ c")] == [3]


def test_tied_note_keeps_its_velocity_and_takes_the_last_articulation():
    [note] = _sounding("90@ c~ 40@ c!")
    assert note.velocity == 90 and note.articulation == "staccato"


def test_lyrics_skip_the_tied_continuation():
    assert [(e.letter, e.lyric) for e in _sounding('c~ c d "la- la"')] == [("c", "la-"), ("d", "la")]


@pytest.mark.parametrize("text", ["c~ d", "c~ r", "c~", "kick~ kick", "r~ r", "c*4>d*4~ d",
                                  "c~ { c ; e }"])
def test_tie_errors(text):
    assert not validate_track_text(text, {})[0]


# ------------------------------------------------------------------ legature di portamento

def test_slur_marks_and_legato_inside():
    events = _sounding("c( d e f) g")
    assert [e.slur for e in events] == ["start", "continue", "continue", "stop", None]
    assert all(e.articulation is None for e in events)     # il legato e' solo nel suono


def test_slur_with_rests_ties_blocks_and_groups():
    assert [e.slur for e in _sounding("[c e]( d~ d r e)")] == ["start", "continue", "stop"]
    assert [e.slur for e in _sounding("2(c( d) e)")] == ["start", "stop", None] * 2


@pytest.mark.parametrize("text", ["c( d", "c d)", "c( d( e) f)", "c() d", "r( c d)", "c( { d ; e } f)",
                                  "kick( c)"])
def test_slur_errors(text):
    assert not validate_track_text(text, {})[0]


def test_marks_stay_with_the_token_when_rewriting():
    assert split_note_value("c'2<~(") == ("c", "'2<~(")
    assert split_note_value("2c*4~") == ("2c*4", "~")
    assert transpose_tokens(tokenize("c~ c C7'2( [c e]~ d)"), 2, 4) == \
        ["d*4~", "d*4", "D7'2(", "[d*4 f#*4]~", "e*4)"]


def test_tokenizer_keeps_slurs_out_of_groups():
    assert tokenize("c( d e f) 2(g a)") == ["c(", "d", "e", "f)", "2(g a)"]
    assert tokenize("[c e]( [d f])") == ["[c e](", "[d f])"]


# ------------------------------------------------------------------ swing

def test_swing_keeps_the_written_rhythm_and_records_the_feel():
    events = _sounding("swing=66 8: c d swing16=60 16: e f swing=50 8: g")
    assert [(e.start, e.duration) for e in events] == [(0, 0.5), (0.5, 0.5), (1, 0.25), (1.25, 0.25), (1.5, 0.5)]
    assert [e.swing for e in events] == [(1.0, 0.66)] * 2 + [(0.5, 0.6)] * 2 + [None]


def test_swing_time():
    assert swing_time(0.5, (1.0, 0.66)) == pytest.approx(0.66)
    assert swing_time(1.0, (1.0, 0.66)) == pytest.approx(1.0)
    assert swing_time(1.25, (0.5, 0.6)) == pytest.approx(1.3)
    assert swing_time(0.75, None) == 0.75


def test_swing_errors_and_voices():
    for text in ("swing=40 c", "swing=90 c", "swing16=81 c"):
        assert not validate_track_text(text, {})[0]
    assert {e.swing for e in _sounding("swing=62 { 8: c d ; 4e }")} == {(1.0, 0.62)}


# ------------------------------------------------------------------ ccN= e bend=

def test_cc_and_bend_automations():
    events = [e for e in parse_track_text("cc74=20 >> 2c cc74=100 bend=-1.5 c", {}) if e.kind == "control"]
    assert [(e.name, e.value, e.start_value) for e in events] == \
        [("cc74", 20, None), ("cc74", 100, 20), ("bend", -1.5, None)]
    for text in ("cc120=1", "cc74=128", "bend=25"):
        assert not validate_track_text(text, {})[0]


# ------------------------------------------------------------------ MIDI

def _midi(path, kinds=("note_on", "note_off", "pitchwheel", "control_change")):
    import mido
    out = []
    for track in mido.MidiFile(path).tracks:
        now = 0
        for msg in track:
            now += msg.time
            if msg.type in kinds:
                out.append((now, msg))
    return out


def _project(text):
    p = Project(name="t")
    p.add_track("A", "Piano", text)
    return p


def test_app_midi_swing_legato_cc_and_bend(tmp_path):
    from core.midi_export import export_project_to_midi
    path = str(tmp_path / "a.mid")
    export_project_to_midi(_project("swing=66 8: c( d e f) cc74=40 g bend=2 a"), path)
    msgs = _midi(path)
    ons = [t for t, m in msgs if m.type == "note_on" and m.velocity]
    assert ons[:4] == [0, 317, 480, 797]                    # seconde crome spostate dallo swing
    off_c = next(t for t, m in msgs if m.type in ("note_off", "note_on") and m.note == 60 and not m.velocity)
    assert off_c > 317                                       # c legata alla d (legato)
    assert any(m.type == "control_change" and m.control == 74 and m.value == 40 for _, m in msgs)
    assert any(m.type == "pitchwheel" and m.pitch == 683 for _, m in msgs)   # 2 semitoni su 24
    assert any(m.type == "control_change" and m.control == 101 and m.value == 0 for _, m in msgs)  # RPN


def test_library_midi_matches_the_app(tmp_path):
    import st_language as st
    from core.midi_export import export_project_to_midi
    text = "swing=60 8: c( d~ d e) [c e]~ [c e] swing16=55 16: f g a b cc11=90 >> 4c cc11=30 bend=-1 c"
    app, lib = str(tmp_path / "app.mid"), str(tmp_path / "lib.mid")
    export_project_to_midi(_project(text), app)
    st.to_midi(st.read_song(f"Tempo: 120 BPM\n\nTraccia A [Piano]:\n  {text}\n"), lib)

    def notes(path):
        return [(t, m.type, getattr(m, "note", None), getattr(m, "pitch", None)) for t, m in _midi(path)
                if m.type != "control_change"]
    assert notes(lib) == notes(app)


# ------------------------------------------------------------------ partitura ed editor

def test_musicxml_slurs_ties_and_swing_marking():
    from core.musicxml_export import project_to_musicxml
    xml = project_to_musicxml(_project("4: c( d e 2f~ | 2f) swing=62 8: g a b c 2d"))
    assert xml.count('<slur type="start"') == 1 and xml.count('<slur type="stop"') == 1
    assert xml.index('<slur type="stop"') > xml.index('<tied type="stop"/>')
    assert re.findall(r"<words>([^<]*)</words>", xml) == ["Swing"]


def test_abc_slurs():
    import st_language as st
    from st_language.abc import project_to_abc
    song = st.read_song("Tempo: 120 BPM\n\nTraccia A [Flute]:\n  4: c( d e f) g\n")
    body = project_to_abc(song)
    assert "(" in body and ")" in body.split("(", 1)[1]


def test_highlighter_colours_ties_slurs_and_swing():
    from PySide6.QtWidgets import QApplication, QPlainTextEdit
    QApplication.instance() or QApplication([])
    from gui.highlighter import NotationHighlighter, _COLORS
    editor = QPlainTextEdit()
    editor.setPlainText("swing=62 c( d~ d) 2(e f)")
    h = NotationHighlighter(editor.document())
    h.rehighlight()
    colours = {(f.start, f.length): f.format.foreground().color().name()
               for f in editor.document().firstBlock().layout().formats()}
    dark = {k: v[0] for k, v in _COLORS.items()}
    assert colours[(0, 8)] == dark["state"]
    assert colours[(9, 2)] == dark["note"] and colours[(12, 2)] == dark["note"]
    assert colours[(15, 2)] == dark["note"]               # "d)": la ')' della legatura come la nota
    assert colours[(18, 2)] == dark["repeat"] and colours[(23, 1)] == dark["repeat"]
