"""
Valori di nota espliciti (c'8.), blocchi di voci { ; } e testo cantato
"...": parser, controlli, trasposizione, colorazione, esportazione
MusicXML (voci e sillabe) e MIDI (eventi lyrics).
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys
import xml.etree.ElementTree as ET

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core.model import Project
from core.musicxml_export import project_to_musicxml
from core.notation import (
    Pattern, check_bar_lines, compute_token_spans, notation_warnings, parse_track_text,
    split_note_value, tokenize, transpose_tokens, validate_track_text,
)


def _notes(text, patterns=None):
    return [(e.kind, e.letter or e.symbol or e.name, e.start, e.duration, e.voice, e.lyric)
            for e in parse_track_text(text, patterns or {}) if e.kind not in ("rest", "tempo_marker", "repeat")]


# ------------------------------------------------------------------ valori di nota

@pytest.mark.parametrize("token,beats", [
    ("c'1", 4.0), ("c'2", 2.0), ("c'4", 1.0), ("c'8", 0.5), ("c'16", 0.25), ("c'64", 1 / 16),
    ("c'4.", 1.5), ("c'8.", 0.75), ("c'2..", 3.5), ("c'8T", 1 / 3), ("c'4T", 2 / 3), ("c'16Q", 0.2),
])
def test_note_values(token, beats):
    [ev] = parse_track_text(token, {})
    assert ev.duration == pytest.approx(beats)


def test_value_does_not_change_the_grid_and_applies_to_every_kind():
    events = parse_track_text("8: c'4. d [c e g]'2 r'4 C'1 kick'16 e", {})
    assert [(e.kind, e.start, e.duration) for e in events] == [
        ("note", 0.0, 1.5), ("note", 1.5, 0.5), ("block", 2.0, 2.0), ("rest", 4.0, 1.0),
        ("chord", 5.0, 4.0), ("percussion", 9.0, 0.25), ("note", 9.25, 0.5)]


def test_value_with_multiplier_octave_and_articulation():
    events = parse_track_text("2c*5'8! d'8_ e*3!'4", {})
    assert [(e.letter, e.octave, e.duration, e.articulation) for e in events] == [
        ("c", 5, 1.0, "staccato"), ("d", 4, 0.5, "legato"), ("e", 3, 1.0, "staccato")]
    assert split_note_value("2c*5'8.!") == ("2c*5!", "'8.")


@pytest.mark.parametrize("text", ["c'3", "c'0", "c'8x8", "4:'8", "c'", "[c e]'"])
def test_invalid_values(text):
    ok, _ = validate_track_text(text, {})
    assert not ok


def test_values_and_bar_checks():
    assert check_bar_lines("c'4. d'8 e'2 | f'1 |", {}) == []
    [issue] = check_bar_lines("c'4. d'16 e'2 |", {})
    assert issue.message == "battuta 1: manca 1 semicroma"


def test_transpose_keeps_values():
    assert transpose_tokens(tokenize("c'8. C7'2 [c e]'4"), 2, 4) == ["d*4'8.", "D7'2", "[d*4 f#*4]'4"]


# ------------------------------------------------------------------ voci

def test_voices_start_together_and_last_as_the_longest():
    assert _notes("4: { 8: c d e f ; 2g*3 } a") == [
        ("note", "c", 0.0, 0.5, 1, None), ("note", "d", 0.5, 0.5, 1, None),
        ("note", "e", 1.0, 0.5, 1, None), ("note", "f", 1.5, 0.5, 1, None),
        ("note", "g", 0.0, 2.0, 2, None), ("note", "a", 2.0, 1.0, 1, None)]


def test_state_inside_a_voice_stays_there_and_is_inherited():
    events = parse_track_text("8: 100@ { c 4: 30@ d ; e } f", {})
    assert [(e.letter, e.start, e.duration, e.velocity) for e in events] == [
        ("c", 0.0, 0.5, 100), ("d", 0.5, 1.0, 30), ("e", 0.0, 0.5, 100), ("f", 1.5, 0.5, 100)]


def test_voices_on_multiple_lines_with_comments_patterns_and_groups():
    patterns = {"Basso": Pattern("Basso", tokenize("2c*3 2g*2"))}
    text = "4: {\n  2(c d) // melodia\n  ;\n  %Basso\n} e"
    events = _notes(text, patterns)
    assert [(e[1], e[2], e[4]) for e in events] == [
        ("c", 0.0, 1), ("d", 1.0, 1), ("c", 2.0, 1), ("d", 3.0, 1),
        ("c", 0.0, 2), ("g", 2.0, 2), ("e", 4.0, 1)]


def test_nested_voices_and_three_voices():
    events = _notes("{ c ; { d ; e } ; f }")
    assert sorted((e[1], e[4]) for e in events) == [("c", 1), ("d", 2), ("e", 3), ("f", 3)]


def test_voice_errors():
    assert not validate_track_text("{ ; }", {})[0]
    assert not validate_track_text("{ c d", {})[0]
    assert not validate_track_text("c ; d", {})[0]


def test_bar_checks_inside_voices_are_checked_per_voice():
    assert check_bar_lines("4: { c d e f | 4g ; 2c 2d | 4e } |", {}) == []
    issues = check_bar_lines("4: { c d e | ; 2c 2d | } |", {})
    assert [(i.bar, i.message) for i in issues] == [(1, "battuta 1: manca 1 semiminima")]
    assert check_bar_lines("4: { c d e f ; c } c d e |", {}) != []


def test_voice_block_is_one_highlight_span():
    text = "4: { c d ; e } f"
    spans = compute_token_spans(text, {})
    assert [(text[a:b], start, dur) for a, b, start, dur in spans] == [
        ("{ c d ; e }", 0.0, 2.0), ("f", 2.0, 1.0)]


def test_transpose_inside_voices_and_groups():
    assert transpose_tokens(tokenize("{ c ; 2(C d) }"), 2, 4) == ["{ d*4 ; 2(D e*4) }"]


# ------------------------------------------------------------------ testo cantato

def test_lyrics_go_to_the_notes_before_them():
    events = _notes('4: c d e 2f "Ma- ri- a, sei" g a "_ la"')
    assert [e[5] for e in events] == ["Ma-", "ri-", "a,", "sei", "_", "la"]


def test_lyrics_skip_rests_and_drums_and_star_skips_a_note():
    events = parse_track_text('4: c r kick [kick snare] d [c e] "uno * due"', {})
    assert [(e.kind, e.lyric) for e in events if e.kind != "rest"] == [
        ("note", "uno"), ("percussion", None), ("block", None), ("note", None), ("block", "due")]


def test_attached_syllables_and_lyrics_with_spaces_quotes_and_slashes():
    assert [e[5] for e in _notes('c"ciao" d"a" e "tut-ti/e // no"')] == ["ciao", "a", "tut-ti/e"]
    assert tokenize('c "a | b" // x') == ["c", '"a | b"']


def test_lyrics_after_a_voice_block_go_on_the_first_voice():
    events = _notes('4: { c d ; 2e } f "la la la"')
    assert [(e[1], e[5]) for e in events] == [("c", "la"), ("d", "la"), ("e", None), ("f", "la")]


def test_lyrics_repeat_with_groups():
    assert [e[5] for e in _notes('2(c d "la- la")')] == ["la-", "la", "la-", "la"]


def test_too_many_syllables_is_a_warning_on_the_lyric():
    text = 'c d "a b c"'
    ok, _ = validate_track_text(text, {})
    assert ok
    [w] = notation_warnings(text, {})
    assert (text[w.char_start:w.char_end], w.bar) == ('"a b c"', 0)
    assert w.message == "testo cantato: 1 sillaba in piu' delle note"
    assert check_bar_lines(text, {}) == []


def test_unclosed_lyric_is_an_error():
    assert not validate_track_text('c "la la', {})[0]


# ------------------------------------------------------------------ esportazioni

def _measure_notes(xml, part=0):
    root = ET.fromstring(xml.split("\n", 2)[2])
    parts = root.findall("part")
    out = []
    for m in parts[part].findall("measure"):
        out.append([(n.findtext("voice"), n.findtext("type"), n.find("rest") is not None,
                     n.findtext("lyric/text"), n.findtext("lyric/syllabic"), n.findtext("stem"))
                    for n in m.findall("note") if n.find("chord") is None])
    return out


def test_musicxml_voices_and_lyrics():
    p = Project(name="t")
    p.add_track("Voce", "Trumpet", '4: { c*5 d*5 e*5 f*5 ; 2c*4 2g*4 } g*5\'1 "Ma- ri- a, sei qui"')
    measures = _measure_notes(project_to_musicxml(p))
    assert measures[0] == [
        ("1", "quarter", False, "Ma", "begin", "up"), ("1", "quarter", False, "ri", "middle", "up"),
        ("1", "quarter", False, "a,", "end", "up"), ("1", "quarter", False, "sei", "single", "up"),
        ("2", "half", False, None, None, "down"), ("2", "half", False, None, None, "down")]
    # battuta senza seconda voce: una voce sola, gambi automatici
    assert measures[1] == [("1", "whole", False, "qui", "single", None)]


def test_musicxml_melisma_and_backup_durations():
    p = Project(name="t")
    p.add_track("Voce", "Trumpet", '4: { c*5 d*5 e*5 f*5 ; 1c*4 } "la _"')
    xml = project_to_musicxml(p)
    assert "<extend/>" in xml
    assert xml.count("<backup>") == 1


def test_musicxml_note_values():
    p = Project(name="t")
    p.add_track("Voce", "Trumpet", "c*5'4. d*5'8 e*5'2")
    [m] = _measure_notes(project_to_musicxml(p))
    assert [n[1] for n in m] == ["quarter", "eighth", "half"]


def test_midi_lyrics(tmp_path):
    import mido
    from core.midi_export import export_project_to_midi
    p = Project(name="t")
    p.add_track("Voce", "Piano", '4: c d e "Ma- ri- a _"')
    path = str(tmp_path / "l.mid")
    export_project_to_midi(p, path)
    texts = [m.text for t in mido.MidiFile(path).tracks for m in t if m.type == "lyrics"]
    assert texts == ["Ma", "ri", "a "]


def test_project_file_round_trip():
    from core.project_io import parse_project_text, project_to_text
    p = Project(name="t")
    text = "4: { c d ; 2e }  // voci\n\"la la\" f'8. | [c e]'2"
    p.add_track("Piano", "Piano", text)
    assert parse_project_text(project_to_text(p)).tracks[0].text == text


# ------------------------------------------------------------------ editor

def test_highlighter_colours_tokens_inside_groups_voices_and_lyrics():
    from PySide6.QtWidgets import QApplication, QPlainTextEdit
    QApplication.instance() or QApplication([])
    from gui.highlighter import NotationHighlighter, _COLORS
    editor = QPlainTextEdit()
    editor.setPlainText("2(c d) { C'2 ;\n e*3'8. } \"la\" | // x")
    h = NotationHighlighter(editor.document())
    h.rehighlight()

    def colours(block):
        return {(f.start, f.length): f.format.foreground().color().name() for f in block.layout().formats()}

    first = colours(editor.document().firstBlock())
    dark = {k: v[0] for k, v in _COLORS.items()}
    assert first[(0, 2)] == dark["repeat"] and first[(2, 1)] == dark["note"]
    assert first[(7, 1)] == dark["voices"] and first[(9, 3)] == dark["chord"]
    second = colours(editor.document().firstBlock().next())
    assert second[(1, 6)] == dark["note"]                  # riga a meta' di un blocco di voci
    assert second[(10, 4)] == dark["lyric"]


def test_splitting_into_boxes_keeps_trailing_lyrics_and_bar_checks():
    from core.arrangement import split_text_into_box_segments
    segments = split_text_into_box_segments('4: c d e "la la la" | 8r f g "x y"', {}, 4)
    assert segments == [(0.0, '4: c d e "la la la" |'), (11.0, '4: f g "x y"')]


def test_highlighter_gives_each_voice_its_own_background():
    """Ogni voce di un blocco { ; } ha uno sfondo diverso, anche quando il
    blocco va a capo; fuori dal blocco e sui separatori nessuno sfondo."""
    from PySide6.QtWidgets import QApplication, QPlainTextEdit
    QApplication.instance() or QApplication([])
    from PySide6.QtCore import Qt
    from gui.highlighter import NotationHighlighter, _VOICE_BACKGROUNDS
    editor = QPlainTextEdit()
    editor.setPlainText("c { d e ;\n f { g ; a } } b")
    h = NotationHighlighter(editor.document())
    h.rehighlight()

    def background(block, pos):
        for f in reversed(block.layout().formats()):
            if f.start <= pos < f.start + f.length:
                brush = f.format.background()
                return brush.color().name() if brush.style() != Qt.NoBrush else None
        return None

    dark = [d for d, _l in _VOICE_BACKGROUNDS]
    first = editor.document().firstBlock()
    second = first.next()
    assert background(first, 0) is None                 # c, fuori dal blocco
    assert background(first, 2) is None                 # {
    assert background(first, 4) == dark[0]              # d, prima voce
    assert background(first, 8) is None                 # ;
    assert background(second, 1) == dark[1]             # f, seconda voce (a capo)
    assert background(second, 5) == dark[2]             # g, prima voce annidata
    assert background(second, 9) == dark[3]             # a, seconda voce annidata
    assert background(second, 15) is None               # b, dopo il blocco
