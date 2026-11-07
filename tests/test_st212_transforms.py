"""
Adeguamento a st-language 2.12: i brani vecchi non cambiano suono (conversione
all'apertura, versione al salvataggio), i comandi che spostano note dentro e
fuori dai pattern, la tonalita' e lo strumento verso la libreria, editor,
anteprima e finestra Trasforma.

Esecuzione:
    python3 -m pytest tests/test_st212_transforms.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import hashlib
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox, QPlainTextEdit

from core.i18n import set_language
from core.midi_export import export_project_to_midi
from core.notation import Pattern, notation_warnings, tokenize
from core.project_io import parse_project_text, project_to_text
from core.reorganize import expand_patterns_for_project, extract_patterns_for_project
from core.transform_preview import (arp_region, arpeggiable, expansion, freeze_all, freeze_span, reference_at,
                                    reference_point, sounding, stage_lines, with_arpeggio)

_app = QApplication.instance() or QApplication([])

OLD = "ST: 2.8\nTempo: 120 BPM\n\nPattern %A:\n  8: 100@ c d\n\nTraccia Melodia [Pianoforte]:\n  %A e f %A g\n"
NEW = "Tempo: 120 BPM\nTonalita: G\n\nPattern %M:\n  8: g a b c*5\n\nTraccia Melodia [Pianoforte]:\n  %M.step(1)\n"


def _midi(project, tmp_path) -> str:
    path = tmp_path / "x.mid"
    export_project_to_midi(project, str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _notes(project, name="Melodia"):
    track = project.get_track(name)
    return [(round(e.start, 4), round(e.duration, 4), e.kind, e.letter, e.octave, e.velocity)
            for e in track.parsed_events(project.patterns, meter=project.meter()) if e.kind != "control"]


def test_library_follows_the_interface_language():
    import st_language
    try:
        for code in ("en", "fr", "it"):
            set_language(code)
            assert st_language.language() == code
    finally:
        set_language("it")


# ---------------------------------------------------------------- 1. apertura e salvataggio

def test_old_song_is_upgraded_and_keeps_its_sound():
    project = parse_project_text(OLD)
    assert "%A 8: 100@ e" in project.get_track("Melodia").text
    events = _notes(project)
    assert [e[1] for e in events] == [0.5] * 7 and {e[5] for e in events} == {100}


def test_song_with_patterns_saves_as_212_and_sounds_the_same(tmp_path):
    project = parse_project_text(OLD)
    text = project_to_text(project)
    assert text.startswith("ST: 2.12")
    again = parse_project_text(text)
    assert again.get_track("Melodia").text == project.get_track("Melodia").text
    assert _midi(again, tmp_path) == _midi(project, tmp_path)


def test_new_rule_text_does_not_change_on_reopening():
    text = "ST: 2.12\nTempo: 120 BPM\n\nPattern %A:\n  8: 100@ c d\n\nTraccia Melodia [Pianoforte]:\n  %A c\n"
    project = parse_project_text(text)
    assert project.get_track("Melodia").text.split() == ["%A", "c"]
    assert parse_project_text(project_to_text(project)).get_track("Melodia").text.split() == ["%A", "c"]


def test_declared_version_is_the_one_in_the_file():
    assert parse_project_text(OLD).st_version == (2, 8)
    assert parse_project_text("Tempo: 120 BPM\n").st_version is None


def test_song_without_patterns_keeps_its_version():
    project = parse_project_text("ST: 2.8\nTempo: 120 BPM\n\nTraccia Melodia [Pianoforte]:\n  c d e f\n")
    assert project_to_text(project).startswith("ST: 2.8")


def test_arpeggio_without_patterns_declares_212():
    project = parse_project_text("ST: 2.12\nTempo: 120 BPM\n\nTraccia Melodia [Pianoforte]:\n  arp=up C arp=off\n")
    assert project_to_text(project).startswith("ST: 2.12")


def test_warning_lines_do_not_count_the_added_header():
    project = parse_project_text("Tempo: 120 BPM\n\nTraccia Melodia [Flautoo]:\n  c d\n")
    assert [line for line, _message in project.file_warnings] == [3]


def test_file_newer_than_the_library_warns_about_tracks(monkeypatch, tmp_path):
    import st_language.stfile
    from gui.main_window import MainWindow
    shown = []
    monkeypatch.setattr(st_language.stfile, "LANGUAGE_VERSION", (2, 11))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda _p, _t, text: shown.append(text)))
    song = tmp_path / "brano.st"
    song.write_text(NEW.replace("Tempo:", "ST: 2.12\nTempo:", 1), encoding="utf-8")
    MainWindow()._load_and_apply_project(str(song))
    assert shown and "non suona" in shown[0]


# ---------------------------------------------------------------- 2. dentro e fuori dai pattern

def _editor(text, start, end):
    editor = QPlainTextEdit()
    editor.setPlainText(text)
    return editor


@pytest.mark.parametrize("text, selected", [
    ("4: c 8: 100@ d e f g", "8: 100@ d e"),
    ("arp=up C F arp=off G", "arp=up C F"),
])
def test_transform_into_pattern_keeps_the_sound(text, selected, monkeypatch, tmp_path):
    from gui.selection_actions import _transform_into_pattern
    before = parse_project_text(f"ST: 2.12\nTempo: 120 BPM\n\nTraccia Melodia [Pianoforte]:\n  {text}\n")
    expected = _midi(before, tmp_path)
    start = text.index(selected)
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("P", True)))
    editor = _editor(text, start, start + len(selected))
    patterns = {}
    _transform_into_pattern(editor, patterns, start, start + len(selected), selected)
    assert "%P" in editor.toPlainText()
    editor.undo()
    assert editor.toPlainText() == text                       # una modifica sola
    editor.redo()
    before.patterns = patterns
    before.get_track("Melodia").text = editor.toPlainText()
    assert _midi(before, tmp_path) == expected


def test_extract_patterns_keeps_the_sound(tmp_path):
    body = "8: 100@ c d e f 4: 60@ g a " * 3 + "b"
    project = parse_project_text(f"ST: 2.12\nTempo: 120 BPM\n\nTraccia Melodia [Pianoforte]:\n  {body}\n")
    expected = _midi(project, tmp_path)
    assert extract_patterns_for_project(project, min_window=4, min_repeats=2)
    assert "%" in project.get_track("Melodia").text
    assert _midi(project, tmp_path) == expected


def test_extract_patterns_leaves_a_reference_with_functions_whole():
    text = "%T.invert(e*5).retro c d e f %T.invert(e*5).retro c d e f"
    project = parse_project_text(f"ST: 2.12\nTempo: 120 BPM\n\nPattern %T:\n  c d\n\nTraccia Melodia [Pianoforte]:\n  {text}\n")
    extract_patterns_for_project(project, min_window=4, min_repeats=2)
    assert project.get_track("Melodia").text.count("%T.invert(e*5).retro") == 2 \
        or all("%T.invert(e*5).retro" in " ".join(p.tokens) or name == "T" for name, p in project.patterns.items())
    assert not any("." in t and t.startswith("%") for name, p in project.patterns.items() if name != "T" for t in p.tokens)


@pytest.mark.parametrize("body", [
    "8: %A 2%A+2 e",
    "%W e f",
    "2%W e",
    "%A.retro %W.octave(1) e",
    "rel: c %W g",
    "key=G %W f",
    "%A.canon('2,12) e",
])
def test_expand_patterns_writes_plain_text_with_the_same_sound(body, tmp_path):
    project = parse_project_text("ST: 2.12\nTempo: 120 BPM\n\nPattern %A:\n  c d\n\nPattern %W:\n  8: 100@ c d\n\n"
                                 f"Traccia Melodia [Pianoforte]:\n  {body}\n")
    expected = _midi(project, tmp_path)
    assert expand_patterns_for_project(project)
    text = project.get_track("Melodia").text
    assert "\x00" not in text and "%" not in text and not project.patterns
    assert _midi(project, tmp_path) == expected


def test_expand_patterns_reaches_the_boxes(tmp_path):
    from core.arrangement import flatten_clips_to_text
    from core.model import Clip
    project = parse_project_text("ST: 2.12\nTempo: 120 BPM\n\nPattern %W:\n  8: 100@ c d\n\n"
                                 "Traccia Melodia [Pianoforte]:\n  c\n")
    track = project.get_track("Melodia")
    track.clips = [Clip(name="A", text="%W e", start_beat=0.0), Clip(name="B", text="%W.retro", start_beat=8.0)]
    track.text = flatten_clips_to_text(track.clips, project.patterns, 4, meter=project.meter())
    expected = _midi(project, tmp_path)
    expand_patterns_for_project(project)
    assert not any("%" in clip.text for clip in track.clips) and "%" not in track.text
    assert _midi(project, tmp_path) == expected


def test_expand_patterns_keeps_the_voicing_of_the_track(tmp_path):
    project = parse_project_text("ST: 2.12\nTempo: 120 BPM\n\nPattern %G:\n  4C\n\n"
                                 "Traccia Melodia [Chitarra]:\n  %G.arpeggio(up,8)\n")
    expected = _midi(project, tmp_path)
    expand_patterns_for_project(project)
    assert _midi(project, tmp_path) == expected


def test_expand_patterns_refuses_a_different_sound_and_changes_nothing():
    # expand_to_text conosce una tonalita' sola, il cambio di Tonalita: sposterebbe le note
    project = parse_project_text("ST: 2.12\nTempo: 120 BPM\nTonalita: 1: C, 2: Eb\n\nPattern %M:\n  c d e f\n\n"
                                 "Traccia P [Pianoforte]:\n  %M c\n\n"
                                 "Traccia Melodia [Pianoforte]:\n  1r'1 2r'1 %M.step(1)\n")
    with pytest.raises(ValueError, match="Melodia"):
        expand_patterns_for_project(project)
    assert project.patterns and project.get_track("P").text.split() == ["%M", "c"]


# ---------------------------------------------------------------- 3. tonalita' e strumento

def test_song_key_reaches_the_library():
    project = parse_project_text(NEW)
    track = project.get_track("Melodia")
    assert [(e.letter, e.octave) for e in track.parsed_events(project.patterns, meter=project.meter())
            if e.kind == "note"] == [("a", 4), ("b", 4), ("c", 5), ("d", 5)]
    meter_less = notation_warnings(track.text, project.patterns)
    with_key = notation_warnings(track.text, project.patterns, key=project.key, key_changes=project.key_changes)
    assert [i.kind for i in meter_less] == ["transform"] and with_key == []


def test_arpeggio_follows_the_track_instrument():
    text = "ST: 2.12\nTempo: 120 BPM\n\nTraccia G [Chitarra]:\n  4C.arpeggio(up,8)\n\nTraccia P [Pianoforte]:\n  4C.arpeggio(up,8)\n"
    project = parse_project_text(text)
    guitar = project.get_track("G").parsed_events(project.patterns)
    piano = project.get_track("P").parsed_events(project.patterns)
    assert [(e.letter, e.octave) for e in guitar] != [(e.letter, e.octave) for e in piano]


def test_arp_command_and_suffix_give_the_same_midi(tmp_path):
    head = "ST: 2.12\nTempo: 120 BPM\n\nTraccia Melodia [Pianoforte]:\n  "
    assert _midi(parse_project_text(head + "arp=up,8 2C 2F arp=off\n"), tmp_path) \
        == _midi(parse_project_text(head + "2C.arpeggio(up,8) 2F.arpeggio(up,8)\n"), tmp_path)


# ---------------------------------------------------------------- 4. editor

def test_completion_offers_the_functions_in_the_interface_language():
    from core.completion import completions_for_word
    set_language("it")
    try:
        items = completions_for_word("%Tema.")
        assert len(items) == 11 and "%Tema.retrogrado" in items
        sequence = next(i for i in items if ".progressione" in i)
        assert str(sequence) == "%Tema.progressione(n,passo)"
        assert str(sequence)[sequence.select[0]:sequence.select[1]] == "n"
        assert "Il motivo" in sequence.label
        set_language("en")
        assert "%Tema.retro" in completions_for_word("%Tema.")
    finally:
        set_language("it")


def test_completion_after_voices_and_on_chords():
    from core.completion import completions_for_word, current_word_bounds
    set_language("it")
    for word in ("%T.canon('2).", "%T.thirds."):
        names = [str(i) for i in completions_for_word(word)]
        assert not any(n.endswith(("arpeggio(su)", "terze")) or "canone" in n for n in names) and names
    assert "Cmaj7.arpeggio(su)" in completions_for_word("Cmaj7.")
    assert "Cmaj7.drop2.arpeggio(su)" in completions_for_word("Cmaj7.drop2.")
    assert completions_for_word("C$arp.") == []
    assert completions_for_word(".arpeggio(") == [f".arpeggio({k})" for k in ("su", "giu", "sugiu", "alberti")]
    assert ".arpeggio(off)" in completions_for_word(".arpeggio(", text_before="arp=su C ")
    assert ".arpeggio(off)" not in completions_for_word(".arpeggio(", text_before="arp=su C arp=off ")
    assert "arp=off" in completions_for_word("arp=")
    assert completions_for_word(".", text_before="[c e g]") == [".arpeggio(su)"]
    text = "4: 2(%T.invert(e*5).re"
    assert text[current_word_bounds(text, len(text))[0]:] == "%T.invert(e*5).re"


def _colors(text):
    from PySide6.QtGui import QTextDocument
    from gui.highlighter import NotationHighlighter
    document = QTextDocument()
    highlighter = NotationHighlighter(document)
    document.setPlainText(text)
    highlighter.rehighlight()
    block = document.firstBlock()
    return highlighter, {r.start: r.format for r in block.layout().formats()}, \
        [(r.start, r.length, r.format.foreground().color().name()) for r in block.layout().formats()]


def test_highlighter_colors_pattern_functions_and_arguments():
    text = "%Tema.invert(e*5).retro+5"
    highlighter, _formats, runs = _colors(text)
    color = {pos: name for start, length, name in runs for pos in range(start, start + length)}
    ref = highlighter.fmt_ref.foreground().color().name()
    function = highlighter.fmt_transform.foreground().color().name()
    note = highlighter.fmt_note.foreground().color().name()
    assert color[text.index("T")] == ref and color[text.index("invert")] == function
    assert color[text.index("e*5")] == note and color[text.index("retro")] == function
    assert color[text.index("+5")] == ref


def test_highlighter_marks_an_unknown_function_and_colors_arp():
    highlighter, _f, runs = _colors("%Tema.foo")
    assert runs[0][2] == highlighter.fmt_bar_error.foreground().color().name() and runs[0][1] == len("%Tema.foo")
    highlighter, _f, runs = _colors("arp=alberti,16")
    assert runs[0][2] == highlighter.fmt_state.foreground().color().name()
    highlighter, _f, runs = _colors("Cmaj7.drop2.arpeggio(up,8)")
    colors = [r[2] for r in runs]
    assert highlighter.fmt_chord.foreground().color().name() in colors
    assert highlighter.fmt_transform.foreground().color().name() in colors


def test_chords_under_arp_are_underlined_across_lines():
    from PySide6.QtGui import QTextCharFormat, QTextDocument
    from gui.highlighter import NotationHighlighter
    document = QTextDocument()
    highlighter = NotationHighlighter(document)
    document.setPlainText("arp=up C\nF arp=off\nG")
    highlighter.rehighlight()
    styles = []
    block = document.firstBlock()
    while block.isValid():
        formats = block.layout().formats()
        styles.append(any(r.format.underlineStyle() == QTextCharFormat.DotLine for r in formats))
        block = block.next()
    assert styles == [True, True, False]


def test_rename_reaches_references_with_functions():
    project = parse_project_text("ST: 2.12\nTempo: 120 BPM\n\nPattern %Tema:\n  c d\n\nTraccia Melodia [Pianoforte]:\n"
                                 "  %Tema.retro 2%Tema.octave(1)+2\n")
    project.rename_pattern("Tema", "Motivo")
    assert project.get_track("Melodia").text.split() == ["%Motivo.retro", "2%Motivo.octave(1)+2"]


# ---------------------------------------------------------------- 5. anteprima e Trasforma

SONG = ("ST: 2.12\nTempo: 120 BPM\nTonalita: C\n\nPattern %Tema:\n  8: c d e g\n\nPattern %Giro:\n  2C 2F\n\n"
        "Traccia Melodia [Pianoforte]:\n  4: @@\n")


@pytest.mark.parametrize("token", [
    "%Tema.octave(1)", "%Tema.invert(e*4)", "%Tema.step(2)", "%Tema.augment(2)", "%Tema.diminish(2)", "%Tema.retro",
    "%Tema.sequence(3,-1)", "%Tema.vel(+10)", "%Tema.canon('2,12)", "%Tema.thirds", "%Giro.arpeggio(up,8)",
])
def test_preview_shows_what_plays(token):
    project = parse_project_text(SONG.replace("@@", token))
    track = project.get_track("Melodia")
    start = track.text.index("%")
    point = reference_point(track.text, start, project.patterns, track.instrument, project.meter())
    shown = expansion(token, project, point, track.instrument)
    played = track.parsed_events(project.patterns, meter=project.meter())

    def key(events):
        return sorted((round(e.start, 4), round(e.duration, 4), e.kind, e.letter, e.octave, e.symbol, e.velocity)
                      for e in events if e.kind not in ("rest", "control"))
    assert key(shown.events) == key(played)
    assert shown.duration > 0


def test_stages_and_point():
    project = parse_project_text(SONG.replace("@@", "c 8: 90@ %Tema.invert(e*4).retro"))
    track = project.get_track("Melodia")
    text = track.text
    start, end, token = reference_at(text, text.index("invert"))
    assert text[start:end] == token == "%Tema.invert(e*4).retro"
    point = reference_point(text, start, project.patterns, track.instrument, project.meter())
    assert (point.grid, point.velocity, point.position) == (0.5, 90, 1.0)
    lines = stage_lines(token, expansion(token, project, point, track.instrument))
    assert [label for label, _n in lines][1:] == [".invert(e*4)", ".retro"]
    assert lines[0][1].startswith("c*4 d*4")
    assert reference_at("c %Tema d", 3) is None and reference_at("c %Tema d", 3, with_functions=False)


def test_arpeggio_suffix_helpers():
    assert arpeggiable("Cmaj7") and arpeggiable("4C") and arpeggiable("[c e g]") and arpeggiable("Cmaj7.drop2")
    assert not arpeggiable("c") and not arpeggiable("C$arp") and not arpeggiable("8:")
    assert with_arpeggio("Cmaj7.drop2", "up", "8") == "Cmaj7.drop2.arpeggio(up,8)"
    assert with_arpeggio("[c e]~", "down") == "[c e].arpeggio(down)~"
    assert with_arpeggio("C.arpeggio(up,8)~", "alberti", "16") == "C.arpeggio(alberti,16)~"


class _Playback:
    def __init__(self):
        self.played = []

    def play(self, project, **_kwargs):
        self.played.append(project)


def _dialog(project, **kwargs):
    from gui.transform_dialog import TransformDialog
    return TransformDialog(None, project, _Playback(), "Pianoforte", **kwargs)


def test_dialog_takes_the_arguments_from_the_library():
    project = parse_project_text(SONG.replace("@@", "%Tema"))
    dialog = _dialog(project, token="%Tema")
    dialog.select_function("canon")
    assert dialog._controls[2].maximum() == 4 and dialog._controls[0].text() == "'2"
    assert dialog.tree.topLevelItemCount() == 5


def test_dialog_builds_the_chain_and_replaces():
    set_language("en")
    try:
        project = parse_project_text(SONG.replace("@@", "%Tema"))
        dialog = _dialog(project, token="%Tema")
        assert not dialog.replace_btn.isHidden() and not dialog.replace_btn.isEnabled()
        dialog.select_function("sequence")
        assert dialog.current_call() == ".sequence(3,-1)"
        dialog._refresh()
        assert dialog.text.text() == "%Tema.sequence(3,-1)" and dialog.replace_btn.isEnabled()
        dialog._add_to_chain()
        dialog.select_function("retro")
        dialog._add_to_chain()
        assert dialog.chain == [".sequence(3,-1)", ".retro"]
        dialog.chain_list.setCurrentRow(1)
        dialog._move(-1)
        dialog._refresh()
        assert dialog.text.text() == "%Tema.retro.sequence(3,-1)"
        dialog._replace()
        assert dialog.result_token == "%Tema.retro.sequence(3,-1)"
    finally:
        set_language("it")


def test_dialog_writes_italian_names_and_keeps_an_existing_chain():
    set_language("it")
    project = parse_project_text(SONG.replace("@@", "%Tema"))
    dialog = _dialog(project, token="2%Tema.invert(e*4)+5")
    assert dialog.chain == [".invert(e*4)", "+5"]
    dialog._refresh()
    assert dialog.text.text() == "2%Tema.inverti(e*4)+5"


def test_dialog_shows_errors_and_hints_and_voices():
    project = parse_project_text(SONG.replace("@@", "%Tema"))
    dialog = _dialog(project, pattern="Tema")
    assert dialog.replace_btn.isHidden()
    dialog.select_function("vel")
    dialog._controls[0].setText("xx")
    dialog._refresh()
    assert dialog.status.text() and not dialog.create_btn.isEnabled()
    for name in ("retro", "retro", "retro", "thirds"):
        dialog.select_function(name)
        dialog._add_to_chain()
    assert not dialog.hint.isHidden()
    from PySide6.QtCore import Qt
    disabled = [dialog.tree.topLevelItem(i).child(k).data(0, Qt.UserRole)
                for i in range(dialog.tree.topLevelItemCount()) for k in range(dialog.tree.topLevelItem(i).childCount())
                if dialog.tree.topLevelItem(i).child(k).isDisabled()]
    assert sorted(disabled) == ["arpeggio", "canon", "thirds"]


def test_dialog_creates_a_pattern_and_listens(monkeypatch):
    from gui.transform_dialog import TransformDialog
    set_language("en")
    try:
        project = parse_project_text(SONG.replace("@@", "%Tema"))
        dialog = _dialog(project, pattern="Tema")
        dialog.select_function("retro")
        dialog._refresh()
        dialog.play_after.click()
        dialog.play_before.click()
        assert [p.tracks[0].text for p in dialog.playback.played] == ["%Tema.retro", "%Tema"]
        monkeypatch.setattr(TransformDialog, "_ask_name", lambda self: "Nuovo")
        dialog._create_pattern()
        assert project.patterns["Nuovo"].tokens == ["%Tema.retro"] and dialog.created_pattern == "Nuovo"
    finally:
        set_language("it")


def _window(tmp_path, text, monkeypatch):
    from core.project_io import save_project_file
    from gui.main_window import MainWindow
    for name in ("information", "warning"):
        monkeypatch.setattr(QMessageBox, name, staticmethod(lambda *a, **k: QMessageBox.Ok))
    song = tmp_path / "brano.st"
    save_project_file(parse_project_text(text), str(song))
    window = MainWindow()
    window._load_and_apply_project(str(song))
    window.select_track("Melodia")
    return window


def test_window_replaces_and_undo_brings_it_back(tmp_path, monkeypatch):
    from gui.transform_dialog import TransformDialog
    set_language("en")
    try:
        window = _window(tmp_path, SONG.replace("@@", "%Tema c"), monkeypatch)
        cursor = window.editor.textCursor()
        cursor.setPosition(window.editor.toPlainText().index("%Tema") + 2)
        window.editor.setTextCursor(cursor)

        def accept(dialog):
            dialog.select_function("retro")
            dialog._replace()
            return TransformDialog.Accepted
        monkeypatch.setattr(TransformDialog, "exec", accept)
        window.transform_reference()
        assert "%Tema.retro" in window.project.get_track("Melodia").text
        window.undo()
        assert "%Tema.retro" not in window.project.get_track("Melodia").text
    finally:
        set_language("it")


def test_window_create_pattern_and_undo(tmp_path, monkeypatch):
    from gui.transform_dialog import TransformDialog
    window = _window(tmp_path, SONG.replace("@@", "c"), monkeypatch)

    def accept(dialog):
        dialog.select_function("retro")
        monkeypatch.setattr(TransformDialog, "_ask_name", lambda self: "Nuovo")
        dialog._create_pattern()
        return TransformDialog.Accepted
    monkeypatch.setattr(TransformDialog, "exec", accept)
    window.transform_reference()
    assert "Nuovo" in window.project.patterns
    window.undo()
    assert "Nuovo" not in window.project.patterns


def test_preview_popup_on_a_reference(tmp_path, monkeypatch):
    from gui.transform_preview import show_reference_preview
    window = _window(tmp_path, SONG.replace("@@", "%Tema.invert(e*4).retro"), monkeypatch)
    track = window.project.get_track("Melodia")
    text = window.editor.toPlainText()
    assert show_reference_preview(window.editor, text, text.index("retro"), window.project, track, _Playback(), None)
    popup = window.editor._reference_popup
    assert popup.isVisible() and ".invert(e*4)" in popup.stages.text() and popup.notation.text()
    assert popup.title.text() == "%Tema.invert(e*4).retro"
    popup.score._render()
    assert popup.score._renderer is not None or popup.score._message
    assert not show_reference_preview(window.editor, text, 0, window.project, track, _Playback(), None)
    assert not popup.isVisible()


TOKENS = ["%Tema.octave(1)", "%Tema.invert(e*4)", "%Tema.step(2)", "%Tema.augment(2)", "%Tema.diminish(2)", "%Tema.retro",
          "%Tema.sequence(3,-1)", "%Tema.vel(+10)", "%Tema.canon('2,12)", "%Tema.thirds", "%Giro.arpeggio(up,8)"]


@pytest.mark.parametrize("token", TOKENS)
@pytest.mark.parametrize("name, instrument", [("Pianoforte", "Pianoforte"), ("Chitarra", "Chitarra")])
def test_freeze_keeps_the_midi(token, name, instrument, tmp_path):
    project = parse_project_text(SONG.replace("@@", f"60@ c {token} d e").replace("[Pianoforte]", f"[{instrument}]"))
    track = project.get_track("Melodia")
    expected = _midi(project, tmp_path)
    start = track.text.index("%")
    track.text = freeze_span(track.text, start, start + len(token), project, track.instrument)
    assert "%" not in track.text.replace(f"// da {token}", "")
    assert f"// da {token}\n" in track.text
    assert _midi(project, tmp_path) == expected


def test_freeze_writes_voices_restores_the_state_and_can_skip_the_comment():
    project = parse_project_text(SONG.replace("@@", "%Tema.thirds c"))
    track = project.get_track("Melodia")
    start = track.text.index("%")
    frozen = freeze_span(track.text, start, start + len("%Tema.thirds"), project, track.instrument, comment=False)
    assert "//" not in frozen and "{" in frozen and frozen.rstrip().endswith("c")
    project = parse_project_text(SONG.replace("@@", "%Tema.retro c"))
    text = project.get_track("Melodia").text
    frozen = freeze_span(text, text.index("%"), text.index(" c"), project, project.get_track("Melodia").instrument,
                         comment=False)
    assert "4:" in frozen.split()[-3:]


def test_freeze_inside_rel_and_key():
    for body in ("rel: c %Tema.retro g", "key=G %Tema.octave(1) f"):
        project = parse_project_text(SONG.replace("@@", body))
        track = project.get_track("Melodia")
        before = sounding(track.text, project.patterns, track.instrument, project.meter())
        ref = reference_at(track.text, track.text.index("%") + 1)
        frozen = freeze_span(track.text, ref[0], ref[1], project, track.instrument)
        assert sounding(frozen, project.patterns, track.instrument, project.meter()) == before


def test_freeze_arp_region_and_arpeggio_chord(tmp_path):
    project = parse_project_text(SONG.replace("@@", "c arp=up,8 2C 2F arp=off d"))
    track = project.get_track("Melodia")
    expected = _midi(project, tmp_path)
    start, end = arp_region(track.text, track.text.index("2F"))
    assert track.text[start:end] == "arp=up,8 2C 2F arp=off"
    track.text = freeze_span(track.text, start, end, project, track.instrument, comment=False)
    assert "arp=" not in track.text
    assert _midi(project, tmp_path) == expected
    assert arp_region("c arp=up C arp=off d", 0) is None and arp_region("c arp=up C arp=off d", 19) is None
    assert arp_region("arp=up C F", 8) == (0, 10)
    project = parse_project_text(SONG.replace("@@", "2C.arpeggio(up,8) d"))
    track = project.get_track("Melodia")
    expected = _midi(project, tmp_path)
    token = "2C.arpeggio(up,8)"
    start = track.text.index(token)
    track.text = freeze_span(track.text, start, start + len(token), project, track.instrument)
    assert "arpeggio(" not in track.text.replace(f"// da {token}", "") and _midi(project, tmp_path) == expected


def test_freeze_all_and_the_expanded_view(tmp_path, monkeypatch):
    from core.arrangement import expand_pattern_refs_text
    project = parse_project_text(SONG.replace("@@", "%Tema.retro c %Tema %Tema.octave(1)"))
    track = project.get_track("Melodia")
    text, done, kept = freeze_all(track.text, project, track.instrument)
    assert (done, kept) == (2, []) and "%Tema " in text
    shown = expand_pattern_refs_text("%Tema.retro", project.patterns, 4, project.meter())
    assert "%" not in shown and "g*4" in shown

    from gui.selection_actions import freeze_in_editor
    window = _window(tmp_path, SONG.replace("@@", "%Tema.retro c"), monkeypatch)
    track = window.project.get_track("Melodia")
    before = window.editor.toPlainText()
    start = before.index("%")
    assert freeze_in_editor(window.editor, start, start + len("%Tema.retro"), window.project, track)
    assert "%Tema.retro\n" in track.text
    window.undo()
    assert window.project.get_track("Melodia").text.strip() == before.strip()
    window.freeze_all_transforms()
    assert "%Tema.retro\n" in window.project.get_track("Melodia").text


def test_freeze_chords_keeps_the_arpeggio_suffix(tmp_path, monkeypatch):
    window = _window(tmp_path, SONG.replace("@@", "2C.arpeggio(up,8)"), monkeypatch)
    window.freeze_chords()
    text = window.project.get_track("Melodia").text
    assert "[" in text and ".arpeggio(up,8)" in text


def test_dialog_writes_the_notes(tmp_path, monkeypatch):
    from gui.transform_dialog import TransformDialog
    set_language("en")
    try:
        window = _window(tmp_path, SONG.replace("@@", "%Tema c"), monkeypatch)
        cursor = window.editor.textCursor()
        cursor.setPosition(window.editor.toPlainText().index("%Tema") + 2)
        window.editor.setTextCursor(cursor)

        def accept(dialog):
            dialog.select_function("retro")
            dialog._write_notes()
            return TransformDialog.Accepted
        monkeypatch.setattr(TransformDialog, "exec", accept)
        window.transform_reference()
        assert "from %Tema.retro\n" in window.project.get_track("Melodia").text
    finally:
        set_language("it")


def test_arpeggiate_selection_writes_the_commands():
    from gui.selection_actions import arp_selection_text
    assert arp_selection_text("C F", "alberti", "16") == "arp=alberti,16 C F arp=off"
    assert arp_selection_text("C F", "su") == "arp=su C F arp=off"


# ---------------------------------------------------------------- 6. verifiche

def test_box_length_follows_the_functions():
    project = parse_project_text(SONG.replace("@@", "%Tema"))
    from core.arrangement import clip_duration_beats
    assert clip_duration_beats("%Tema.augment(2)", project.patterns, 4) == 4.0
    assert clip_duration_beats("%Tema.sequence(3,-1)", project.patterns, 4) == 6.0


def test_transpose_keeps_functions_and_arpeggio_suffix():
    from core.notation import transpose_tokens
    assert transpose_tokens(["%Tema.retro"], 2, 4) == ["%Tema.retro+2"]
    assert transpose_tokens(["Cmaj7.arpeggio(up,8)"], 2, 4) == ["Dmaj7.arpeggio(up,8)"]


def test_play_highlight_span_covers_the_whole_canon():
    from core.notation import compute_token_spans
    project = parse_project_text(SONG.replace("@@", "%Tema.canon('2,12)"))
    text = project.get_track("Melodia").text
    span = compute_token_spans(text, project.patterns)[0]
    assert text[span[0]:span[1]] == "%Tema.canon('2,12)" and span[3] == 4.0


def test_bar_check_after_a_transformed_reference():
    project = parse_project_text(SONG.replace("@@", "%Tema"))
    assert notation_warnings("%Tema.augment(2) |", project.patterns, key="C") == []
    assert notation_warnings("%Tema.sequence(3,-1) |", project.patterns, key="C") != []


def test_score_writes_canon_as_voices_of_one_staff():
    from core.musicxml_export import project_to_musicxml
    project = parse_project_text(SONG.replace("@@", "%Tema.canon('2,12)"))
    xml = project_to_musicxml(project, tracks=list(project.tracks))
    assert xml.count("<part ") == 1 and "<voice>2</voice>" in xml


def test_tempo_markers_inside_a_transformed_pattern():
    from core.tempo_map import build_tempo_beat_map
    project = parse_project_text("ST: 2.12\nTempo: 120 BPM\n\nPattern %T:\n  c tempo=90 d\n\nTraccia Melodia [Pianoforte]:\n  %T.octave(1)\n")
    assert any(bpm == 90 for _beat, bpm in build_tempo_beat_map(project))
