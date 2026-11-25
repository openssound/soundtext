"""
Bemolli e diesis con i simboli e percussioni con le abbreviazioni: la
sostituzione mentre si scrive, lo stile del testo generato, i comandi
(core.accidental_style) e il lessico dell'editor.
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from core import accidental_style as style
from core import settings

_app = QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _defaults():
    settings.set_accidental_symbols(True)
    settings.set_percussion_abbreviations(False)
    yield
    settings.set_accidental_symbols(True)
    settings.set_percussion_abbreviations(False)


def _typed(text):
    from gui.voicing_picker import NotationEditor
    editor = NotationEditor()
    QTest.keyClicks(editor, text)
    return editor


@pytest.mark.parametrize("typed, expected", [
    (" eb  ", " e♭  "),
    (" Bb7  ", " B♭7  "),
    ("F#m|", "F♯m|"),
    (" bb  ", " b♭  "),
    ("C/Bb ", "C/B♭ "),
    ("key=Eb ", "key=E♭ "),
    ("[c# eb g]", "[c♯ e♭ g]"),
    ("2(bb b) ", "2(b♭ b) "),
    ("c#*4>d# ", "c♯*4>d♯ "),
    # quello che non va toccato
    ("snare ", "snare "),
    ("b ", "b "),
    ("%Bb_Giro ", "%Bb_Giro "),
    ("Bb_Clarinet ", "Bb_Clarinet "),
    ("// eb Bb7 ", "// eb Bb7 "),
    ('"la bb do" ', '"la bb do" '),
    ("C7#9 Cm7b5 ", "C7#9 Cm7b5 "),
    ("bd hh sn ", "bd hh sn "),
])
def test_the_closed_token_is_written_with_symbols(typed, expected):
    assert _typed(typed).toPlainText() == expected


def test_nothing_changes_while_the_token_is_still_open():
    assert _typed("eb").toPlainText() == "eb"
    assert _typed("c#").toPlainText() == "c#"


def test_newline_closes_a_token_too():
    editor = _typed("eb")
    QTest.keyClick(editor, Qt.Key_Return)
    assert editor.toPlainText() == "e♭\n"


def test_one_undo_gives_back_the_token_as_written():
    editor = _typed("c eb ")
    assert editor.toPlainText() == "c e♭ "
    editor.undo()
    assert editor.toPlainText() == "c eb "


def test_the_option_switches_it_off():
    settings.set_accidental_symbols(False)
    assert _typed("eb Bb7 F# ").toPlainText() == "eb Bb7 F# "


def test_flat_shortcut_still_works():
    assert _typed("e-").toPlainText() == "e♭"


def test_selection_is_not_touched_by_typing_over_it():
    from gui.voicing_picker import NotationEditor
    editor = NotationEditor()
    editor.setPlainText("c eb")
    cursor = editor.textCursor()
    cursor.select(QTextCursor.Document)
    editor.setTextCursor(cursor)
    QTest.keyClicks(editor, "d ")
    assert editor.toPlainText() == "d "


# ------------------------------------------------------------ testo generato

def test_styled_text_follows_the_options():
    text = "4: eb Bb7 F#m7 kick hihat snare"
    assert style.styled(text) == "4: e♭ B♭7 F♯m7 kick hihat snare"
    settings.set_accidental_symbols(False)
    assert style.styled(text) == text
    settings.set_percussion_abbreviations(True)
    assert style.styled(text) == "4: eb Bb7 F#m7 bd hh sn"
    assert style.accidentals_style() is None
    settings.set_accidental_symbols(True)
    assert style.accidentals_style() == "symbols"


def test_percussion_commands_go_both_ways_and_leave_the_rest():
    text = '8: kick hihat [snare hihat] 2(kick) cowbell // kick\n"kick" %kick c d'
    short = style.abbreviate_percussion(text)
    assert short == '8: bd hh [sn hh] 2(bd) cow // kick\n"kick" %kick c d'
    assert style.expand_percussion(short) == text.replace("cowbell", "cowbell")


def test_convert_accidentals_command_round_trip():
    text = "4: eb Bb7 F#m7 C7#9 // eb\n"
    symbols = style.convert_accidentals(text, "symbols")
    assert symbols == "4: e♭ B♭7 F♯m7 C7#9 // eb\n"
    assert style.convert_accidentals(symbols, "ascii") == text


# -------------------------------------------------- colori e completamento

def test_abbreviations_get_the_percussion_colour():
    from core.syntax import classify
    for short in ("bd", "hh", "sn", "cow", "2bd"):
        assert classify(short.lstrip("0123456789")) == "perc"


def test_completion_offers_abbreviations_with_the_long_name():
    from core.completion import completions_for_word
    from core.instruments import get_instrument
    drums = get_instrument("Drums")
    found = completions_for_word("h", instrument=drums)
    labels = {str(c): getattr(c, "label", str(c)) for c in found}
    assert "hh" in labels and "hihat" in labels["hh"]
    assert "hihat" in labels
    assert "hh" not in {str(c) for c in completions_for_word("h", instrument=get_instrument("Piano"))}


def test_rewrite_project_texts_covers_tracks_boxes_and_patterns():
    from core.model import Clip, Project
    from core.notation import Pattern, tokenize
    project = Project()
    project.add_track("Piano", "Piano", "4: eb Bb7 |")
    project.add_track("Drums", "Drums", "8: kick hihat snare hihat |")
    boxed = project.add_track("Lead", "Piano", "")
    boxed.clips.append(Clip(name="A", text="4: F#m7 |", start_beat=0))
    boxed.clips.append(Clip(name="B", text="4: c d |", start_beat=4))
    project.patterns["Giro"] = Pattern(name="Giro", tokens=tokenize("4: Ab7 Db |"))
    changed = style.rewrite_project_texts(project, lambda t: style.convert_accidentals(t, "symbols"))
    assert changed == 3                                     # Piano, la clip A, il pattern
    assert project.get_track("Piano").text == "4: e♭ B♭7 |"
    assert [c.text for c in boxed.clips] == ["4: F♯m7 |", "4: c d |"]
    assert "F♯m7" in boxed.text
    assert " ".join(project.patterns["Giro"].tokens) == "4: A♭7 D♭ |"
    assert style.rewrite_project_texts(project, lambda t: style.convert_accidentals(t, "symbols")) == 0
    style.rewrite_project_texts(project, style.abbreviate_percussion)
    assert project.get_track("Drums").text == "8: bd hh sn hh |"


# --------------------------------------------------- il file e la versione

def _saved(*tracks, key=""):
    from core.model import Project
    from core.project_io import project_to_text
    project = Project()
    for name, instrument, text in tracks:
        project.add_track(name, instrument, text)
    if key:
        project.key = key
    return project_to_text(project)


def test_a_file_that_uses_the_new_symbols_or_abbreviations_declares_2_13():
    assert _saved(("Piano", "Piano", "4: F♯m7 c |")).startswith("ST: 2.13\n")
    assert _saved(("Drums", "Drums", "8: bd hh sn hh |")).startswith("ST: 2.13\n")
    assert _saved(("Piano", "Piano", "4: c |"), key="F♯").startswith("ST: 2.13\n")


def test_a_file_that_uses_neither_keeps_its_old_version():
    for text in (_saved(("Piano", "Piano", "4: F#m7 e♭ |")), _saved(("Drums", "Drums", "8: kick hihat |"))):
        assert not text.startswith("ST: 2.13")


def test_the_saved_file_reads_back_with_the_same_sound(tmp_path):
    from core.project_io import parse_project_text
    text = _saved(("Piano", "Piano", "4: F♯m7 e♭ |"), ("Drums", "Drums", "8: bd hh sn hh |"))
    project = parse_project_text(text)
    assert project.get_track("Piano").text.strip() == "4: F♯m7 e♭ |"
    events = project.get_track("Drums").parsed_events(project.patterns)
    assert [e.name for e in events if e.kind == "percussion"] == ["kick", "hihat", "snare", "hihat"]
