"""
Fase 2 di ST-language 2.2: ritornelli |: :| con le caselle |1. |2. ||,
segni sulle note ($accent, $fermata, $tr...), indicazioni di testo
$"rit.": parser, controlli di battuta, evidenziazione, MIDI dell'app e
della libreria, partitura (MusicXML e ABC) e colori dell'editor.
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
    check_bar_lines, compute_token_spans, expand_repeats, parse_track_text, split_note_value, tokenize,
    transpose_tokens, validate_track_text,
)


def _notes(text):
    return [(e.letter, e.start) for e in parse_track_text(text, {}) if e.kind == "note"]


def _marks(text):
    return [(e.name, e.start, e.value) for e in parse_track_text(text, {}) if e.kind == "repeat"]


# ------------------------------------------------------------------ ritornelli

def test_tokens():
    assert tokenize("|: c :| d :|2. e || f|1. g") == ["|:", "c", ":|", "d", ":|2.", "e", "||", "f", "|1.", "g"]
    assert tokenize("4:|c d|2c") == ["4:", "|", "c", "d", "|", "2c"]      # la griglia resta una griglia


def test_simple_repeat_is_played_twice():
    assert [n for n, _ in _notes("4: |: c d e f :| g")] == list("cdefcdefg")
    assert _marks("4: |: c d e f :| g") == [("start", 0, None), ("again", 4, 2), ("end", 8, None)]


def test_repeat_without_start_goes_back_to_the_beginning_or_the_previous_repeat():
    assert [n for n, _ in _notes("c d :| e f :|")] == list("cdcdefef")


def test_endings():
    text = "4: |: c d e f |1. g a b c :| |2. 4g || 4c"
    assert [n for n, _ in _notes(text)] == list("cdefgabccdefgc")
    assert _marks(text) == [("start", 0, None), ("ending", 4, 1), ("again", 8, 2), ("ending", 12, 2),
                            ("end", 16, None)]
    assert check_bar_lines(text, {}) == []
    assert [n for n, _ in _notes("|: c |1. d :|2. e :|3. f")] == list("cdcecf")


def test_repeat_tokens_are_bar_checks():
    [issue] = check_bar_lines("4: |: c d e :| f", {})      # :| dopo 3 quarti
    assert issue.bar == 1


def test_highlight_spans_play_the_repeated_tokens_twice():
    spans = compute_token_spans("|: c d :| e", {})
    c_starts = sorted(b for cs, _ce, b, _d in spans if cs == 3)
    assert c_starts == [0, 2]


@pytest.mark.parametrize("text", ["|: c d", "|: c |: d :| :|", "c |2. d", "|: c |1. d ||",
                                  "|: c |1. d :| e", "c :| :|2. d"])
def test_repeat_errors(text):
    assert not validate_track_text(text, {})[0]


def test_expand_repeats_keeps_the_origins():
    tokens, origins = expand_repeats(["|:", "c", ":|", "d"], [0, 1, 2, 3])
    assert [t for t in tokens if not t.startswith("\x00")] == ["|", "c", "|", "c", "|", "d"]
    assert [o for t, o in zip(tokens, origins) if t == "c"] == [1, 1]


def test_groups_mark_their_repetitions():
    assert _marks("2(c d) e") == [("start", 0, None), ("again", 2, 2), ("end", 4, None)]
    assert _marks("1(c d) 3(e)") == [("start", 2, None), ("again", 3, 2), ("again", 4, 3), ("end", 5, None)]


def test_repeats_inside_voices():
    events = parse_track_text("{ 4: |: c d e f :| ; 8e }", {})
    assert [e.voice for e in events if e.kind == "note"] == [1] * 8 + [2]


# ------------------------------------------------------------------ segni e testi

def test_marks_on_notes_chords_blocks_and_rests():
    events = [e for e in parse_track_text("c$accent C7$fermata [c e]$tr$tenuto r$fermata c'2$turn~ c$mordent", {})
              if e.kind != "repeat"]
    assert [e.decorations for e in events] == [["accent"], ["fermata"], ["tr", "tenuto"], ["fermata"],
                                               ["turn", "mordent"]]
    assert events[-1].duration == 3


def test_marks_stay_with_the_token_when_rewriting():
    assert split_note_value("c'8.$accent<~)") == ("c", "'8.$accent<~)")
    assert transpose_tokens(tokenize("c$tr [c e]$accent C$fermata"), 2, 4) == \
        ["d*4$tr", "[d*4 f#*4]$accent", "D$fermata"]


@pytest.mark.parametrize("text", ["c$wobble", "r$accent", "c$"])
def test_mark_errors(text):
    assert not validate_track_text(text, {})[0]


def test_text_indications():
    events = parse_track_text('$"dolce" c $"rit." d', {})
    assert [(e.kind, e.name, e.start) for e in events] == \
        [("text", "dolce", 0), ("note", None, 0), ("text", "rit.", 1), ("note", None, 1)]
    assert tokenize('c$"a tempo" d') == ["c", '$"a tempo"', "d"]


# ------------------------------------------------------------------ MIDI

def _midi(path):
    import mido
    out = []
    for track in mido.MidiFile(path).tracks:
        now = 0
        for msg in track:
            now += msg.time
            if msg.type == "note_on" and msg.velocity:
                out.append((now, msg.note, msg.velocity))
            elif msg.type == "set_tempo":
                out.append((now, "tempo", round(mido.tempo2bpm(msg.tempo))))
    return out


def _project(text, key="C"):
    p = Project(name="t", tempo_bpm=120)
    p.key = key
    p.add_track("A", "Piano", text)
    return p


def test_app_midi_marks_and_repeats(tmp_path):
    from core.midi_export import export_project_to_midi
    path = str(tmp_path / "a.mid")
    export_project_to_midi(_project("4: c$accent d$mordent e$fermata f |: g :| a$tr"), path)
    msgs = _midi(path)
    notes = [m for m in msgs if m[1] != "tempo"]
    assert notes[0] == (0, 60, 100)                                    # accento: 80 * 1.25
    assert [n for t, n, _v in notes if 480 <= t < 960] == [62, 60, 62]  # mordente: re do re
    assert [(t, b) for t, kind, b in msgs if kind == "tempo"] == [(0, 120), (960, 60), (1440, 120)]
    assert [n for t, n, _v in notes if 1920 <= t < 2880] == [67, 67]    # ritornello
    trill = [n for t, n, _v in notes if t >= 2880]
    assert trill[0] == trill[-1] == 69 and set(trill) == {69, 71}


def test_trill_uses_the_key(tmp_path):
    from core.midi_export import export_project_to_midi
    path = str(tmp_path / "k.mid")
    export_project_to_midi(_project("e$tr", key="D"), path)         # in Re maggiore sopra a mi c'e' fa#
    assert {n for _t, n, _v in _midi(path) if n != "tempo"} == {64, 66}


def test_library_midi_matches_the_app(tmp_path):
    import st_language as st
    from core.midi_export import export_project_to_midi
    text = "4: |: c$tr d$accent e f |1. g$fermata a b c :| |2. 4c$turn || [c e]$marcato d$mordent 2r$fermata"
    app, lib = str(tmp_path / "app.mid"), str(tmp_path / "lib.mid")
    export_project_to_midi(_project(text), app)
    st.to_midi(st.read_song(f"Tempo: 120 BPM\nTonalita: C\n\nTraccia A [Piano]:\n  {text}\n"), lib)
    assert _midi(lib) == _midi(app)


# ------------------------------------------------------------------ partitura

def _xml(text, extra=""):
    import st_language as st
    song = st.read_song(f"Tempo: 100 BPM\n\nTraccia A [Flute]:\n  {text}\n{extra}")
    from st_language.musicxml import project_to_musicxml
    return song, project_to_musicxml(song)


def test_score_prints_repeats_and_endings():
    _song, xml = _xml("4: |: c d e f |1. g a b c :| |2. 4c*5 || d e f g |")
    assert xml.count("<measure ") == 4
    assert re.findall(r'<repeat direction="(\w+)"', xml) == ["forward", "backward"]
    assert re.findall(r'<ending number="(\d)" type="(\w+)"', xml) == \
        [("1", "start"), ("1", "stop"), ("2", "start"), ("2", "discontinue")]


def test_score_prints_bar_aligned_groups_as_repeats_with_times():
    _song, xml = _xml("4: 3(c d e f |) g a b c |")
    assert xml.count("<measure ") == 2 and '<repeat direction="backward" times="3"/>' in xml


def test_score_writes_out_repeats_that_differ_between_tracks_or_bars():
    _song, xml = _xml("4: |: c d e f :|", extra="\nTraccia B [Flute]:\n  4: e e e e | f f f f |\n")
    assert "<repeat" not in xml and xml.count("<measure ") == 4      # 2 battute x 2 parti
    _song, xml = _xml("4: 2(c d) e f |")
    assert "<repeat" not in xml


def test_score_marks_and_texts():
    import verovio
    _song, xml = _xml('4: $"dolce" c$tr d$accent e$fermata f$turn | g$mordent a$marcato b$tenuto r$fermata |')
    for tag in ("<trill-mark/>", "<accent/>", '<fermata type="upright"/>', "<turn/>", "<mordent/>",
                "<strong-accent/>", "<tenuto/>", "<words>dolce</words>"):
        assert tag in xml, tag
    assert verovio.toolkit().loadData(xml)


def test_abc_repeats_marks_and_texts():
    from st_language.abc import project_to_abc
    song, _xml_text = _xml('4: |: $"dolce" c$tr d e f |1. g a b c :| |2. 4c$fermata ||')
    body = project_to_abc(song)
    assert "|:" in body and ":|" in body and "[1 " in body and "[2 " in body
    assert '"^dolce"' in body and "!trill!" in body and "!fermata!" in body


# ------------------------------------------------------------------ editor

def test_highlighter_colours_repeats_marks_and_texts():
    from PySide6.QtWidgets import QApplication, QPlainTextEdit
    QApplication.instance() or QApplication([])
    from gui.highlighter import NotationHighlighter, _COLORS
    editor = QPlainTextEdit()
    editor.setPlainText('|: c$tr $"rit." d :|2. e ||')
    h = NotationHighlighter(editor.document())
    h.rehighlight()
    colours = {(f.start, f.length): f.format.foreground().color().name()
               for f in editor.document().firstBlock().layout().formats()}
    dark = {k: v[0] for k, v in _COLORS.items()}
    assert colours[(0, 2)] == dark["bar"] and colours[(3, 4)] == dark["note"]
    assert colours[(8, 7)] == dark["lyric"]
    assert colours[(18, 4)] == dark["bar"] and colours[(25, 2)] == dark["bar"]
