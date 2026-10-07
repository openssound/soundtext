"""
Fase 3 di ST-language 2.3: ottave relative (rel: con *+ e *-) e alterazioni
dalla tonalita' (key=, bequadro n): parser, pattern indipendenti dal modo,
ritornelli e voci, trasposizione e riscrittura in modo relativo che non
cambiano le note, box, pulsante dell'editor e colori.
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core.chords import pitch_to_midi
from core.notation import (
    Pattern, PitchRewriter, key_signature_alters, parse_track_text, relative_text, rewrite_tokens, tokenize,
    transpose_tokens, validate_track_text,
)


def _pitches(text, patterns=None, octave=4):
    out = []
    for e in parse_track_text(text, patterns or {}, default_octave=octave):
        if e.kind == "note":
            out.append(pitch_to_midi(e.letter, e.octave))
        elif e.kind == "block":
            out.append(tuple(pitch_to_midi(i["letter"], i["octave"]) for i in e.items if i["kind"] == "note"))
        elif e.kind == "slide":
            out.append(("slide", pitch_to_midi(e.letter, e.octave),
                        *(pitch_to_midi(l, o) for l, o in e.slide_points)))
    return out


def _names(text, **kw):
    return [(e.letter, e.octave) for e in parse_track_text(text, {}, **kw) if e.kind == "note"]


# ------------------------------------------------------------------ ottave relative

def test_nearest_octave_counting_letters():
    assert _names("rel: c d e f g a b c") == [("c", 4), ("d", 4), ("e", 4), ("f", 4), ("g", 4), ("a", 4),
                                              ("b", 4), ("c", 5)]
    assert _names("rel: c g") == [("c", 4), ("g", 3)]                 # una quinta sopra = una quarta sotto
    assert _names("rel: c f b e") == [("c", 4), ("f", 4), ("b", 4), ("e", 5)]
    assert _names("rel: g c*+ c*- c*--") == [("g", 3), ("c", 5), ("c", 4), ("c", 2)]
    assert _names("rel: g c*++ c*--") == [("g", 3), ("c", 6), ("c", 4)]
    assert _names("rel: c*6 d abs: e") == [("c", 6), ("d", 6), ("e", 4)]
    assert _names("rel: g b", default_octave=2) == [("g", 1), ("b", 1)]


def test_blocks_slides_chords_and_voices():
    assert _pitches("rel: [e g c] a") == [(64, 67, 72), 69]           # dopo il blocco: vicino alla sua prima nota
    assert _pitches("rel: c>e>g c") == [("slide", 60, 64, 67), 72]
    assert _names("rel: c C7*2 d") == [("c", 4), ("d", 4)]            # gli accordi non contano
    assert _names("rel: e { g a ; c b*- } f") == [("e", 4), ("g", 4), ("a", 4), ("c", 4), ("b", 2), ("f", 4)]


def test_every_pass_of_a_repeat_has_the_same_pitches():
    assert _pitches("rel: |: c e g :| c") == [60, 64, 67, 60, 64, 67, 72]
    assert _pitches("rel: 3(c g)") == [60, 55] * 3
    assert _pitches("rel: |: c d |1. e f :| |2. a b || c") == [60, 62, 64, 65, 60, 62, 57, 59, 60]


def test_patterns_are_read_with_absolute_octaves_and_no_key():
    patterns = {"R": Pattern("R", tokenize("c e f"))}
    events = [(e.letter, e.octave) for e in parse_track_text("rel: key=G g*- %R f", patterns) if e.kind == "note"]
    assert events == [("g", 2), ("c", 4), ("e", 4), ("f", 4), ("f#", 2)]


@pytest.mark.parametrize("text", ["c*+", "d*-", "c*4*+", "rel: c*9 a*+"])
def test_relative_errors(text):
    assert not validate_track_text(text, {})[0]


# ------------------------------------------------------------------ tonalita'

def test_key_signatures():
    assert key_signature_alters("G") == {"f": "#"}
    assert key_signature_alters("F") == {"b": "b"}
    assert key_signature_alters("Am") == {} and key_signature_alters("Em") == {"f": "#"}
    assert key_signature_alters("Cb") == {letter: "b" for letter in "beadgcf"}
    assert key_signature_alters("F#m") == {"f": "#", "c": "#", "g": "#"}


def test_notes_take_the_key_accidentals():
    assert [n for n, _ in _names("key=G f fn f♮ f# fb key=off f")] == ["f#", "f", "f", "f#", "fb", "f"]
    assert [n for n, _ in _names("key=Bb b e a key=Ebm a c")] == ["bb", "eb", "a", "ab", "cb"]
    events = parse_track_text("key=D [f a] f>g C", {})
    assert events[0].items[0]["letter"] == "f#" and events[1].letter == "f#" and events[2].symbol == "C"


@pytest.mark.parametrize("text", ["key=H c", "key=G# c", "key=Fbm c", "key=c c"])
def test_key_errors(text):
    assert not validate_track_text(text, {})[0]


# ------------------------------------------------------------------ riscrittura

TEXTS = [
    "c*4 d e*5 f# g*3 bb a*2 c*6",
    "8: c*4 e*4 g*4 [c*4 e*4 g*4] c*5>d*5 b*3 2r c#*7 |: d*4 e*4 |1. f*4 :| |2. g*2 || f*4",
    "{ c*5 d*5 ; e*3 g*3 } a*4 2(b*4 c*5) d*2 C7 kick",
    "key=G f g a b c d e f",
    "rel: c e g c*+ b*- a g",
    "key=Bb rel: b e f bn a g*- f*+ [d f a]",
]


@pytest.mark.parametrize("text", TEXTS)
@pytest.mark.parametrize("key", [None, "G", "Eb", "Am", "C#m"])
def test_relative_rewrite_keeps_the_notes(text, key):
    assert _pitches(relative_text(text, 4, key)) == _pitches(text)


@pytest.mark.parametrize("text", TEXTS)
@pytest.mark.parametrize("semitones", [-7, -1, 1, 2, 6, 12])
def test_transposition_moves_every_note(text, semitones):
    def shift(p):
        if isinstance(p, int):
            return p + semitones
        return tuple(x + semitones if isinstance(x, int) else x for x in p)
    moved = " ".join(transpose_tokens(tokenize(text), semitones, 4))
    assert _pitches(moved) == [shift(p) for p in _pitches(text)]


def test_rewrites_read_well():
    assert relative_text("c*4 d*4 e*4 f#*4 g*4 c*5 // fine", 4, "G") == "rel: key=G c d e f g c // fine"
    assert " ".join(transpose_tokens(tokenize("key=G rel: g a b c d e f g"), 2, 4)) == \
        "key=A rel: a b c d e f g a"
    assert " ".join(transpose_tokens(tokenize("key=F rel: f a c*+ bn"), -2, 4)) == "key=Eb rel: e g b*+ an"


def test_box_rewrite_keeps_layout():
    text = "key=G rel: g a b // riga\nc d"
    assert rewrite_tokens(text, PitchRewriter(5, 4)) == "key=C rel: c d e // riga\nf g"


def test_boxes_reset_the_pitch_state():
    from core.arrangement import flatten_clips_to_text
    from core.model import Clip
    clips = [Clip(name="A", text="rel: key=G c d", start_beat=0.0), Clip(name="B", text="f", start_beat=2.0)]
    text = flatten_clips_to_text(clips, {}, 4)
    assert text.count("reset:") == 2
    assert _names(text)[-1] == ("f", 4)
    plain = [Clip(name="A", text="c d", start_beat=0.0)]
    assert flatten_clips_to_text(plain, {}, 4) == "reset: c d"


# ------------------------------------------------------------------ interfaccia

def test_editor_button_rewrites_the_track(monkeypatch):
    from PySide6.QtWidgets import QApplication, QMessageBox
    QApplication.instance() or QApplication([])
    from gui.main_window import MainWindow
    w = MainWindow()
    w.project.key = "D"
    w.project.add_track("Piano", "Piano", "4: d*4 e*4 f#*4 g*4 | a*4 b*4 c#*5 d*5 |")
    w.refresh_mixer()
    w.select_track("Piano")
    before = _pitches(w.project.tracks[0].text)
    w.rewrite_relative()
    text = w.project.tracks[0].text
    assert text == "rel: key=D 4: d e f g | a b c d |"
    assert _pitches(text) == before
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Discard)
    w.close()


def test_highlighter_colours_pitch_commands():
    from PySide6.QtWidgets import QApplication, QPlainTextEdit
    QApplication.instance() or QApplication([])
    from gui.highlighter import NotationHighlighter, _COLORS
    editor = QPlainTextEdit()
    editor.setPlainText("rel: key=G c*+ fn d*-")
    h = NotationHighlighter(editor.document())
    h.rehighlight()
    colours = {(f.start, f.length): f.format.foreground().color().name()
               for f in editor.document().firstBlock().layout().formats()}
    dark = {k: v[0] for k, v in _COLORS.items()}
    assert colours[(0, 4)] == dark["state"] and colours[(5, 5)] == dark["state"]
    assert colours[(11, 3)] == dark["note"] and colours[(15, 2)] == dark["note"] and colours[(18, 3)] == dark["note"]
