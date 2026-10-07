"""
Controlli di battuta '|' e commenti '//' nella notazione: la '|' non suona
e non sposta il tempo, ma se non cade su una stanghetta (metrica del
progetto e suoi cambi) viene segnalata come avviso con quanto manca o
avanza; i commenti si ignorano e sopravvivono a salvataggio, box,
trasposizione e congelamento degli accordi.
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core.arrangement import flatten_clips_to_text
from core.model import Clip, Project
from core.notation import (
    Pattern, check_bar_lines, compute_token_spans, describe_duration, parse_track_text,
    rewrite_tokens, tokenize, tokenize_spans, transpose_tokens, validate_track_text,
)
from core.project_io import parse_project_text, project_to_text
from fractions import Fraction


def _messages(text, *args, **kwargs):
    return [(i.bar, i.message) for i in check_bar_lines(text, {}, *args, **kwargs)]


# ------------------------------------------------------------------ commenti

def test_comments_are_ignored_until_end_of_line():
    text = "4: c d // e f g a  [non | conta]\ne f // altro\n"
    assert tokenize(text) == ["4:", "c", "d", "e", "f"]
    ok, msg = validate_track_text(text, {})
    assert ok, msg
    assert [e.letter for e in parse_track_text(text, {})] == ["c", "d", "e", "f"]


def test_single_slash_is_not_a_comment():
    assert tokenize("c*4 &Blues/bass // nota") == ["c*4", "&Blues/bass"]


def test_comment_inside_a_multiline_group_or_block():
    text = "4: 2(c d // ripetuto\n e f)"
    assert [e.letter for e in parse_track_text(text, {}) if e.kind == "note"] == list("cdef") * 2


def test_token_positions_skip_comments():
    text = "c // d\nd"
    assert tokenize_spans(text) == [("c", 0, 1), ("d", 7, 8)]
    spans = compute_token_spans(text, {})
    assert [(cs, ce, start) for cs, ce, start, _ in spans] == [(0, 1, 0.0), (7, 8, 1.0)]


# ------------------------------------------------------------------ controlli di battuta

def test_bar_check_is_its_own_token_even_when_attached():
    assert tokenize("4: c d e f| g a|b") == ["4:", "c", "d", "e", "f", "|", "g", "a", "|", "b"]
    assert [e.start for e in parse_track_text("c | d|e", {})] == [0.0, 1.0, 2.0]


def test_bar_check_inside_a_simultaneous_block_is_an_error():
    ok, _ = validate_track_text("[c | e]", {})
    assert not ok


def test_correct_bar_checks_give_no_warning():
    assert _messages("4: c d e f | g a b c | 2c 2e |") == []
    assert _messages("8: c d e f g a b c | 2: c c |") == []
    assert _messages("8T: c d e f g a 2: c | 1: c |") == []


def test_missing_and_extra_beats():
    assert _messages("4: c d e | f g a b |") == [(1, "battuta 1: manca 1 semiminima")]
    assert _messages("4: c | d e f g |") == [(1, "battuta 1: mancano 3 semiminime")]
    assert _messages("4: c d | e f g a |") == [(1, "battuta 1: manca 1 minima")]
    assert _messages("8: c d e f g a b c d | e") == [(1, "battuta 1: 1 croma di troppo")]


def test_one_error_does_not_cascade_but_a_second_one_is_reported():
    assert _messages("4: c d e | f g a b | c d e f |") == [(1, "battuta 1: manca 1 semiminima")]
    assert _messages("4: c d e | f g a | c d e f |") == [
        (1, "battuta 1: manca 1 semiminima"), (2, "battuta 2: manca 1 semiminima")]
    assert _messages("4: c d e f g | a b c |") == [
        (1, "battuta 1: 1 semiminima di troppo"), (2, "battuta 2: manca 1 semiminima")]


def test_time_signature_and_its_changes():
    assert _messages("4: c d e | f g a |", "3/4") == []
    assert _messages("4: c d e f | f g a |", "3/4") == [(1, "battuta 1: 1 semiminima di troppo")]
    changes = [(1, "4/4"), (2, "3/4"), (3, "5/4")]
    assert _messages("4: c d e f | g a b | c d e f g | a b c d e |", "4/4", changes) == []
    assert _messages("4: c d e f | g a b | c d e f g | a b c d |", "4/4", changes) == [
        (4, "battuta 4: manca 1 semiminima")]
    # Cambi che non partono dalla battuta 1: prima vale il 4/4.
    assert _messages("4: c d e f | g a b |", "3/4", [(2, "3/4")]) == []


def test_box_starting_mid_bar():
    assert _messages("4: c d | e f g a |", start_beat=2.0) == []
    assert _messages("4: c d | e f g a |", start_beat=3.0) == [(1, "battuta 1: 1 semiminima di troppo")]


def test_bar_checks_inside_patterns_and_groups_are_reported_on_the_reference():
    patterns = {"Riff": Pattern("Riff", tokenize("4: c d e |"))}
    text = "4: c d e f | %Riff"
    issues = check_bar_lines(text, patterns)
    assert [(i.char_start, i.char_end, i.message) for i in issues] == [
        (13, 18, "battuta 2: manca 1 semiminima")]
    assert _messages("4: 2(c d e f |)") == []
    assert len(check_bar_lines("4: 3(c d e |)", {})) == 1      # un avviso per token


def test_issue_points_at_the_bar_character():
    text = "4: c d e |"
    [issue] = check_bar_lines(text, {})
    assert text[issue.char_start:issue.char_end] == "|"


@pytest.mark.parametrize("beats,expected", [
    (Fraction(4), "1 semibreve"), (Fraction(3), "3 semiminime"), (Fraction(3, 2), "3 crome"),
    (Fraction(1, 3), "1 croma di terzina"), (Fraction(2, 3), "1 semiminima di terzina"),
    (Fraction(1, 4), "1 semicroma"), (Fraction(1, 5), "0.2 quarti"),
])
def test_describe_duration(beats, expected):
    assert describe_duration(beats)[1] == expected


def test_invalid_text_gives_no_bar_issues_and_does_not_raise():
    assert check_bar_lines("4: [c d", {}) == []


# ------------------------------------------------------------------ salvataggio e riscritture

def test_project_file_keeps_lines_and_comments():
    p = Project(name="x")
    p.add_track("Piano", "Piano", "4: c d e f |  // strofa\n\ng a b c |\n   // fine")
    bass = p.add_track("Basso", "Bass", "")
    bass.clips = [Clip(name="A", text="4: c*2 // box\n\ne*2", start_beat=0.0),
                  Clip(name="B", text="4: g*2", start_beat=4.0)]
    q = parse_project_text(project_to_text(p))
    assert q.tracks[0].text == "4: c d e f |  // strofa\ng a b c |\n// fine"
    assert [(c.name, c.text) for c in q.tracks[1].clips] == [
        ("A", "4: c*2 // box\ne*2"), ("B", "4: g*2")]


def test_old_single_line_files_load_as_before():
    text = "Tempo: 120 BPM\nMetrica: 4/4\n\nPiano:\n  4: c d\n  e f\n"
    assert parse_project_text(text).tracks[0].text == "4: c d\ne f"
    assert tokenize(parse_project_text(text).tracks[0].text) == ["4:", "c", "d", "e", "f"]


def test_comment_at_the_end_of_a_box_does_not_swallow_the_next_box():
    clips = [Clip(name="A", text="4: c d // fine A", start_beat=0.0),
             Clip(name="B", text="4: e f", start_beat=2.0)]
    flat = flatten_clips_to_text(clips, {}, 4)
    assert [e.letter for e in parse_track_text(flat, {})] == ["c", "d", "e", "f"]


def test_rewrite_tokens_keeps_layout_and_comments():
    text = "4: c d  // do re\n| C7 |"
    out = rewrite_tokens(text, lambda tok: transpose_tokens([tok], 2, 4)[0])
    assert out == "4: d*4 e*4  // do re\n| D7 |"


def test_freeze_chords_keeps_comments(monkeypatch):
    from PySide6.QtWidgets import QApplication, QMessageBox
    QApplication.instance() or QApplication([])
    from gui.main_window import MainWindow
    w = MainWindow()
    w.project.add_track("Piano", "Piano", "4: C // accordo\n| c")
    w.refresh_mixer()
    w.select_track("Piano")
    w.freeze_chords()
    text = w.project.tracks[0].text
    assert text.startswith("4: [") and text.endswith("] // accordo\n| c")
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Discard)
    w.close()


# ------------------------------------------------------------------ interfaccia

def test_editor_label_and_highlighter_show_the_warning(monkeypatch):
    from PySide6.QtWidgets import QApplication, QMessageBox
    QApplication.instance() or QApplication([])
    from gui.main_window import MainWindow
    w = MainWindow()
    w.project.add_track("Piano", "Piano", "4: c d e | f g a b |")
    w.refresh_mixer()
    w._dirty = False
    w.select_track("Piano")
    assert "battuta 1: manca 1 semiminima" in w.validation_label.text()
    assert w.highlighter._bar_errors == {9}
    w.highlighter.set_bar_errors({19})
    assert not w._dirty            # ricolorare la '|' non e' una modifica
    w._on_metrica_changed("3/4")
    assert "battuta 2" in w.validation_label.text()
    w.history.reset(w.project)
    w._dirty = False
    w.editor.setPlainText("4: c d e | f g a |")
    assert w.project.tracks[0].text == "4: c d e | f g a |"
    assert "Sintassi valida" in w.validation_label.text()
    assert w.highlighter._bar_errors == frozenset()
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Discard)
    w.close()


def test_box_dialog_uses_the_box_position():
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from gui.box_edit_dialog import BoxEditDialog
    dlg = BoxEditDialog(None, Project(name="t"), "Piano", 120, clip_text="4: c d | e f g a |",
                        start_beat=2.0)
    assert "Sintassi valida" in dlg.status_label.text()
    dlg.body_edit.setPlainText("4: c d e | f g a b |")
    dlg._update_status()
    assert "battuta 1: 1 semiminima di troppo" in dlg.status_label.text()
    dlg.reject()
