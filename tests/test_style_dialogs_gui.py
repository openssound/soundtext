"""
Test (offscreen) dei controlli della variabilita' nei dialoghi dei
generatori (preset, dettagli per aspetto, rigenera solo alcune battute) e
del dialogo "Salva come stile del generatore".
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _config_isolation  # noqa: F401,E402

import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from core import user_styles  # noqa: E402
from core.model import Project  # noqa: E402
from core.rhythm_generate import Variability, generate_drum_pattern, splice_bars  # noqa: E402
from gui.rhythm_generate_dialog import (  # noqa: E402
    BassGenerateDialog, ChordProgressionDialog, DrumGenerateDialog,
)
from gui.save_style_dialog import (  # noqa: E402
    SaveStyleDialog, StyleSource, UserStylesDialog, chord_sources_of, source_for_part,
)

app = QApplication.instance() or QApplication([])


@pytest.fixture
def styles_file(tmp_path, monkeypatch):
    monkeypatch.setattr(user_styles, "USER_STYLES_FILE", str(tmp_path / "generator_styles.json"))
    monkeypatch.setattr(user_styles, "CONFIG_DIR", str(tmp_path))
    user_styles.load_user_styles(reload=True)
    yield tmp_path
    monkeypatch.undo()
    user_styles.load_user_styles(reload=True)


def _project():
    p = Project(name="t", tempo_bpm=100)
    p.add_track("Piano", "Piano", "4: 4Am 4F 4C 4G")
    p.add_track("Bass", "Bass", "8: a*2 a*2 e*3 a*2 r a*2 g*2 g#*2 f*2 f*2 c*3 f*2 r f*2 e*2 b*1")
    p.add_track("Drums", "Drums", "16: kick r hihat r snare r hihat r kick r hihat r snare r hihat r")
    return p


def _drums(**kw):
    return DrumGenerateDialog(None, _project(), "Drums", "traccia 'Drums'", default_bars=8,
                              track_name="Drums", **kw)


# ------------------------------------------------------------ variabilita'

def test_presets_set_the_sliders_and_follow_them():
    dlg = _drums()
    assert dlg.preset_combo.currentData() == "musician"
    assert not dlg.details_widget.isVisibleTo(dlg)
    dlg.preset_combo.setCurrentIndex(dlg.preset_combo.findData("faithful"))
    assert dlg.variability_slider.value() == 15
    assert [dlg.aspect_sliders[a].value() for a in ("rhythm", "notes", "dynamics")] == [60, 30, 100]
    assert dlg._variability() == Variability(0.15 * 0.6, 0.15 * 0.3, 0.15)
    dlg.aspect_sliders["dynamics"].setValue(50)                 # a mano: personalizzata
    assert dlg.preset_combo.currentData() == "custom"
    dlg.preset_combo.setCurrentIndex(dlg.preset_combo.findData("creative"))
    assert dlg.variability_slider.value() == 75 and dlg.variability_label.text() == "75%"
    dlg.details_btn.setChecked(True)
    assert dlg.details_widget.isVisibleTo(dlg)


def test_preview_uses_the_aspects():
    dlg = _drums()
    dlg.style_combo.setCurrentIndex(dlg.style_combo.findData("rock"))
    dlg.variability_slider.setValue(100)
    for aspect in ("rhythm", "notes"):
        dlg.aspect_sliders[aspect].setValue(0)
    expected = generate_drum_pattern("rock", bars=8, fill_every=4, phrase_fills=True,
                                     variability=Variability(0, 0, 1), seed=dlg._seed)
    assert dlg.preview_edit.toPlainText() == expected


def test_progression_dialog_only_has_the_harmony_aspect():
    dlg = ChordProgressionDialog(None, Project(name="t"), "Piano", "nuovo box", default_bars=8)
    assert list(dlg.aspect_sliders) == ["notes"]
    assert dlg.preset_combo.currentData() == "musician"
    dlg.preset_combo.setCurrentIndex(dlg.preset_combo.findData("faithful"))
    assert dlg.variability_slider.value() == 15 and dlg.aspect_sliders["notes"].value() == 30


def test_regenerate_only_some_bars_keeps_the_others():
    dlg = _drums()
    dlg.style_combo.setCurrentIndex(dlg.style_combo.findData("rock"))
    dlg.variability_slider.setValue(80)
    before = dlg.preview_edit.toPlainText()
    assert dlg.regen_to_spin.maximum() == 8 and not dlg.undo_bars_btn.isEnabled()
    dlg.regen_from_spin.setValue(5)
    dlg.regen_to_spin.setValue(6)
    dlg._regenerate_bars()
    after = dlg.preview_edit.toPlainText()
    (first, last, seed), = dlg._overrides
    assert (first, last) == (5, 6)
    alt = generate_drum_pattern("rock", bars=8, fill_every=4, phrase_fills=True,
                                variability=dlg._variability(), seed=seed)
    assert after == splice_bars(before, alt, 5, 6, 4.0)
    assert dlg.undo_bars_btn.isEnabled()
    dlg.fill_every_spin.setValue(2)                     # il ritocco resta cambiando i controlli
    assert len(dlg._overrides) == 1
    dlg._clear_overrides()
    assert dlg._overrides == [] and not dlg.undo_bars_btn.isEnabled()
    dlg._overrides = [(1, 1, 7)]
    dlg._reroll()                                       # nuova variazione: tutto da capo
    assert dlg._overrides == []


def test_regenerate_bars_disabled_without_variability():
    dlg = _drums()
    dlg.variability_slider.setValue(0)
    assert not dlg.regen_bars_btn.isEnabled()


# ------------------------------------------------------------ stili personali

def test_save_style_dialog_learns_from_a_bass_track(styles_file):
    p = _project()
    track = p.get_track("Bass")
    dlg = SaveStyleDialog(None, [source_for_part("traccia 'Bass'", track.text, track.instrument)],
                          chord_sources_of(p, "Bass"), p.patterns, meter="4/4")
    assert dlg.kind_combo.currentData() == "bass"
    assert dlg.chords_combo.currentData() == "Piano"                  # l'unica traccia con accordi
    assert "battute lette" in dlg.summary_label.text()
    dlg.name_edit.setText("Mio basso")
    dlg.accept()
    assert dlg.saved_style() == ("bass", "Mio basso")
    assert user_styles.user_style_names("bass") == ["Mio basso"]
    # compare nel dialogo del basso con la stella
    bass = BassGenerateDialog(None, p, "Bass", "traccia 'Basso'", [("Piano", p.get_track("Piano").text)],
                              default_bars=4, track_name="Basso")
    index = bass.style_combo.findData("user:Mio basso")
    assert index >= 0 and bass.style_combo.itemText(index) == "★ Mio basso"
    bass.style_combo.setCurrentIndex(index)
    assert bass.preview_edit.toPlainText().startswith("8: ")


def test_save_style_dialog_drums_and_errors(styles_file, monkeypatch):
    p = _project()
    track = p.get_track("Drums")
    source = source_for_part("traccia 'Drums'", track.text, track.instrument)
    dlg = SaveStyleDialog(None, [source, StyleSource("vuota", "4: r r r r", False)], [], p.patterns)
    assert [dlg.kind_combo.itemData(i) for i in range(dlg.kind_combo.count())] == ["drums"]
    assert not dlg.chords_combo.isEnabled()
    dlg.name_edit.setText("Groove")
    dlg.accept()
    assert user_styles.user_style_names("drums") == ["Groove"]
    # stesso nome: chiede se sostituire
    again = SaveStyleDialog(None, [source], [], p.patterns)
    again.name_edit.setText("Groove")
    asked = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: asked.append(a) or QMessageBox.No)
    again.accept()
    assert asked and again.saved_style() is None
    # una parte senza note: errore e Salva disattivato
    dlg.source_combo.setCurrentIndex(1)
    assert "✗" in dlg.summary_label.text()
    from PySide6.QtWidgets import QDialogButtonBox
    assert not dlg.button_box.button(QDialogButtonBox.Save).isEnabled()
    # il dialogo della batteria propone lo stile salvato
    drums = _drums()
    assert drums.style_combo.findData("user:Groove") >= 0


def test_user_style_in_another_meter_is_not_offered(styles_file):
    from core.style_learn import learn_drum_style
    user_styles.save_user_style("drums", "Valzerino", learn_drum_style("16: kick r r r snare r r r snare r r r",
                                                                         meter="3/4"))
    assert _drums().style_combo.findData("user:Valzerino") < 0
    p = _project()
    p.time_sig = "3/4"
    waltz = DrumGenerateDialog(None, p, "Drums", "x", default_bars=4)
    assert waltz.style_combo.findData("user:Valzerino") >= 0


def test_user_styles_dialog_rename_and_delete(styles_file, monkeypatch):
    from core.style_learn import learn_line_style
    user_styles.save_user_style("riff", "Uno", learn_line_style("4: c*4 e*4", "riff"))
    dlg = UserStylesDialog(None)
    assert dlg.list_widget.count() == 1 and "Riff/melodia — Uno" in dlg.list_widget.item(0).text()
    from PySide6.QtWidgets import QInputDialog
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("Due", True))
    dlg._rename()
    assert user_styles.user_style_names("riff") == ["Due"]
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    dlg._delete()
    assert user_styles.user_style_names("riff") == [] and dlg.list_widget.count() == 0
    assert not dlg.delete_btn.isEnabled()


# ------------------------------------------------------------ punti d'accesso

class _FakeSaveDialog:
    seen = []
    Accepted = 1

    def __init__(self, parent, sources, chord_sources, patterns=None, meter="4/4", midi_dir=None):
        _FakeSaveDialog.seen.append({"sources": sources, "chords": [n for n, _t in chord_sources],
                                     "meter": meter})

    def exec(self):
        return 1

    def saved_style(self):
        return ("bass", "X")


def test_track_menu_and_box_menu_open_the_save_dialog(styles_file, monkeypatch):
    import gui.save_style_dialog as module
    from core.model import Clip
    from gui.main_window import MainWindow
    monkeypatch.setattr(module, "SaveStyleDialog", _FakeSaveDialog)
    _FakeSaveDialog.seen = []
    w = MainWindow()
    w.project.add_track("Piano", "Piano", "4: 4Am 4F")
    w.project.add_track("Bass", "Bass", "4: a*2 e*2")
    w.refresh_mixer()
    from gui.command_palette import collect_commands
    entries = {(c.path, c.title) for c in collect_commands(w.menuBar())}
    assert ("Componi › Stili dei generatori", "Salva la traccia come stile...") in entries
    assert ("Componi › Stili dei generatori", "Stili personali...") in entries
    w.select_track("Bass")
    w.save_selected_track_as_style()
    (seen,) = _FakeSaveDialog.seen
    assert seen["sources"][0].label == "traccia 'Bass'" and seen["sources"][0].is_bass
    assert seen["chords"] == ["Piano"]
    # tasto destro su un box: la parte parte dal punto del box
    clip = Clip(name="Riff", text="4: a*2 e*2", start_beat=8.0)
    w.project.get_track("Bass").clips.append(clip)
    w.arrangement_view._save_clip_as_style("Bass", clip)
    box = _FakeSaveDialog.seen[-1]["sources"][0]
    assert box.label == "box 'Riff'" and box.offset_beats == 8.0
    w.close()


def test_midi_library_offers_every_channel(styles_file, tmp_path, monkeypatch):
    import gui.save_style_dialog as module
    from core import midi_library
    from gui.midi_library_dialog import MidiLibraryDialog
    midi_dir = tmp_path / "midi"
    midi_dir.mkdir()
    midi_library.render_tokens_to_midi("8: a*2 a*2 e*2 a*2 f*2 f*2 c*3 f*2", "Bass", tempo_bpm=120,
                                       path=str(midi_dir / "linea.mid"))
    monkeypatch.setattr(module, "SaveStyleDialog", _FakeSaveDialog)
    _FakeSaveDialog.seen = []
    dlg = MidiLibraryDialog(None, midi_dir=str(midi_dir))
    dlg._save_as_style()
    (seen,) = _FakeSaveDialog.seen
    assert len(seen["sources"]) == 1 and seen["sources"][0].label.startswith("canale ")
    assert seen["sources"][0].is_bass and not seen["sources"][0].is_percussion
