"""
Test per il checkbox "Ascolta anche le altre tracce" del dialogo "Suona con
la tastiera" (gui.keyboard_play_dialog.KeyboardPlayDialog): quando spuntato,
la riproduzione dal vivo/anteprima deve includere le altre tracce del
progetto rispettando Solo/Mute, escludendo la traccia corrente per non
sovrapporne il contenuto vecchio; quando non spuntato, comportamento di
sempre (isolato).

Esecuzione:
    python3 -m pytest tests/test_keyboard_play_dialog.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication

from core.model import Project
from gui.keyboard_play_dialog import KeyboardPlayDialog

_app = QApplication.instance() or QApplication([])


def _make_dialog(project, current_track_name=None):
    return KeyboardPlayDialog(
        None, project=project, instrument_name="Piano",
        context_label="traccia 'Piano1'", current_track_name=current_track_name,
    )


def _project_with_three_tracks():
    p = Project(name="Test")
    p.add_track("Piano1", "Piano", "16: c*4")
    p.add_track("Bass1", "Bass", "16: c*2")
    p.add_track("Guitar1", "Guitar", "16: c*3")
    return p


def test_other_tracks_unchecked_by_default_and_context_project_empty():
    p = _project_with_three_tracks()
    dlg = _make_dialog(p, current_track_name="Piano1")
    assert dlg.other_tracks_checkbox.isChecked() is False
    ctx = dlg._build_context_project()
    assert ctx.tracks == []


def test_other_tracks_unchecked_preview_has_only_anteprima_track():
    p = _project_with_three_tracks()
    dlg = _make_dialog(p, current_track_name="Piano1")
    ctx = dlg._build_context_project(preview_text="c*4 e*4")
    assert [t.name for t in ctx.tracks] == ["Anteprima"]
    assert ctx.tracks[0].text == "c*4 e*4"


def test_other_tracks_checked_includes_other_tracks_excludes_current():
    p = _project_with_three_tracks()
    dlg = _make_dialog(p, current_track_name="Piano1")
    dlg.other_tracks_checkbox.setChecked(True)
    ctx = dlg._build_context_project()
    assert sorted(t.name for t in ctx.tracks) == ["Bass1", "Guitar1"]


def test_other_tracks_checked_respects_mute():
    p = _project_with_three_tracks()
    p.get_track("Bass1").mute = True
    dlg = _make_dialog(p, current_track_name="Piano1")
    dlg.other_tracks_checkbox.setChecked(True)
    ctx = dlg._build_context_project()
    assert [t.name for t in ctx.tracks] == ["Guitar1"]


def test_other_tracks_checked_respects_solo():
    p = _project_with_three_tracks()
    p.get_track("Guitar1").solo = True
    dlg = _make_dialog(p, current_track_name="Piano1")
    dlg.other_tracks_checkbox.setChecked(True)
    ctx = dlg._build_context_project()
    # Piano1 e' comunque esclusa in quanto traccia corrente, anche se fosse solo
    assert [t.name for t in ctx.tracks] == ["Guitar1"]


def test_other_tracks_checked_with_preview_includes_both():
    p = _project_with_three_tracks()
    dlg = _make_dialog(p, current_track_name="Piano1")
    dlg.other_tracks_checkbox.setChecked(True)
    ctx = dlg._build_context_project(preview_text="c*4")
    assert sorted(t.name for t in ctx.tracks) == ["Anteprima", "Bass1", "Guitar1"]


def test_no_current_track_name_nothing_excluded():
    # Caso del dialogo aperto per un pattern (non una traccia reale):
    # current_track_name None, nessuna esclusione per nome.
    p = _project_with_three_tracks()
    dlg = _make_dialog(p, current_track_name=None)
    dlg.other_tracks_checkbox.setChecked(True)
    ctx = dlg._build_context_project()
    assert sorted(t.name for t in ctx.tracks) == ["Bass1", "Guitar1", "Piano1"]


def test_other_tracks_checkbox_disabled_while_recording():
    p = _project_with_three_tracks()
    dlg = _make_dialog(p, current_track_name="Piano1")
    assert dlg.other_tracks_checkbox.isEnabled()
    dlg._set_controls_enabled(False)
    assert not dlg.other_tracks_checkbox.isEnabled()
    dlg._set_controls_enabled(True)
    assert dlg.other_tracks_checkbox.isEnabled()


def test_key_combo_shows_project_key_on_open():
    p = _project_with_three_tracks()
    p.key = "Em"
    dlg = _make_dialog(p, current_track_name="Piano1")
    assert dlg.key_combo.currentText() == "Em"


def test_key_combo_empty_when_project_key_unset():
    p = _project_with_three_tracks()
    dlg = _make_dialog(p, current_track_name="Piano1")
    assert dlg.key_combo.currentText() == ""


def test_changing_key_combo_updates_shared_project():
    p = _project_with_three_tracks()
    dlg = _make_dialog(p, current_track_name="Piano1")
    dlg.key_combo.setCurrentText("C#m")
    assert p.key == "C#m"  # stesso oggetto Project passato al dialogo, non una copia


def test_changing_key_combo_rebuilds_scale_layout():
    # Con Layout su 'Scala della tonalita'' e nessuna tonalita' impostata, la
    # mappa nota ricade sulla cromatica (36 tasti mappati comunque, ma sulle
    # 12 note cromatiche per riga): impostando una tonalita' valida nel
    # dialogo deve passare subito alla scala, senza dover riaprire il dialogo.
    p = _project_with_three_tracks()
    dlg = _make_dialog(p, current_track_name="Piano1")
    # trova l'indice della voce "Scala della tonalità (diatonica)"
    for i in range(dlg.layout_combo.count()):
        mode, _ = dlg.layout_combo.itemData(i)
        if mode == "scale":
            dlg.layout_combo.setCurrentIndex(i)
            break
    assert "cromatica" in dlg.legend_label.text().lower() or "cromatico" in dlg.legend_label.text().lower()

    dlg.key_combo.setCurrentText("C")
    assert "scala" in dlg.legend_label.text().lower()
    assert "(C)" in dlg.legend_label.text()


if __name__ == "__main__":
    import inspect
    here = sys.modules[__name__]
    tests = [f for name, f in inspect.getmembers(here) if name.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        passed += 1
        print(f"OK  {t.__name__}")
    print(f"\n{passed}/{len(tests)} test superati.")
