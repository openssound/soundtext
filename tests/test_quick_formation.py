"""
La formazione del brano in 60 secondi (core.quick_formation, core.quicksong, gui.quick_formation_dialog): gli strumenti
scelti uno per uno, fra tutti quelli disponibili, al posto dell'organico.
"""
import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from core import quick_formation
from core.project_io import parse_project_text
from core.quicksong import GENRES, quick_song

JAZZ_GUITAR, ACOUSTIC_BASS, ALTO_SAX, PIANO = "Electric_Guitar_jazz", "Acoustic_Bass", "Alto_Sax", "Acoustic_Grand_Piano"

# le formazioni dell'utente: «solo chitarra», «chitarra, basso e batteria», «sax, piano, basso e batteria», «solo basso»
CASES = {
    "solo chitarra": ([JAZZ_GUITAR], {"comp"}),
    "chitarra basso batteria": ([JAZZ_GUITAR, ACOUSTIC_BASS, "Drums"], {"comp", "bass", "drums"}),
    "sax piano basso batteria": ([ALTO_SAX, PIANO, ACOUSTIC_BASS, "Drums"], {"comp", "bass", "drums", "melody"}),
    "solo basso": ([ACOUSTIC_BASS], {"bass"}),
}


def _tracks(project):
    return [t for t in project.tracks if t.text.strip()]


@pytest.mark.parametrize("genre", ["jazz", "pop", "rock", "orchestrale", "valzer", "balcanico"])
@pytest.mark.parametrize("label", sorted(CASES))
def test_the_chosen_instruments_play_and_nothing_else(genre, label):
    if genre not in GENRES:
        pytest.skip(f"nessun genere {genre}")
    instruments, parts = CASES[label]
    made = quick_song({"genre": genre, "seed": 5, "duration": 30, "formation": instruments})
    assert set(made["parts"]) == parts and made["left_out"] == []
    project = parse_project_text(made["text"], made["name"])
    played = {t.instrument_name for t in _tracks(project)}
    expected = {name for name in instruments if name != "Drums"}
    assert expected <= played
    assert len(played - expected) == (1 if "Drums" in instruments else 0)       # solo il kit scelto dal genere
    for track in _tracks(project):
        assert track.parsed_events(project.patterns, meter=project.meter()), track.name
    assert made["choices"]["formation"] == instruments


def test_without_a_formation_the_song_is_the_one_of_today():
    plain = quick_song({"genre": "jazz", "seed": 9, "duration": 30})
    assert plain["formation"] == [] and plain["left_out"] == []
    assert "formation" not in plain["choices"]
    assert quick_song({"genre": "jazz", "seed": 9, "duration": 30, "formation": []})["text"] == plain["text"]


def test_a_melodic_instrument_gets_the_melody_and_a_lone_chord_instrument_none():
    sax = quick_song({"genre": "pop", "seed": 3, "duration": 30, "formation": [ALTO_SAX]})
    assert sax["parts"] == ["melody"]
    guitar = quick_song({"genre": "pop", "seed": 3, "duration": 30, "formation": [JAZZ_GUITAR]})
    assert "melody" not in guitar["parts"]


def test_more_instruments_than_parts_leave_the_extra_ones_out_and_say_so():
    names = ["Acoustic_Grand_Piano", "Electric_Guitar_jazz", "Church_Organ", "Harpsichord", "Acoustic_Bass"]
    made = quick_song({"genre": "pop", "seed": 3, "duration": 30, "formation": names})
    assert set(made["parts"]) >= {"comp", "comp2", "pad", "bass"}
    assert made["left_out"] == ["Harpsichord"] or len(made["left_out"]) == 1


def test_wrong_formations_say_what_is_wrong():
    with pytest.raises(ValueError):
        quick_song({"genre": "pop", "seed": 3, "formation": ["Strumento_Che_Non_Esiste"]})
    with pytest.raises(ValueError):
        quick_formation.assign([])


def test_roles_follow_the_general_midi_program():
    assert quick_formation.role_of("Electric_Bass_finger") == "bass"
    assert quick_formation.role_of("Acoustic_Grand_Piano") == "chords"
    assert quick_formation.role_of("Alto_Sax") == "melody"
    assert quick_formation.role_of("String_Ensemble_1") == "pad"
    assert quick_formation.role_of("Drums") == "drums"
    assert quick_formation.role_of("Strumento_Che_Non_Esiste") is None


def test_the_catalog_lists_every_general_midi_instrument_once_with_a_working_name():
    groups = quick_formation.catalog()
    values = [i["value"] for g in groups for i in g["instruments"]]
    assert len(values) == len(set(values))
    assert len([v for v in values if v != "Drums"]) >= 128
    assert groups[0]["instruments"][0]["value"] == "Drums"
    for value in ("Alto_Sax", "Acoustic_Guitar_nylon", "Electric_Bass_finger"):
        assert value in values


# ----------------------------------------------------------------------- la finestra

@pytest.fixture
def app():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _dialog(app, monkeypatch):
    from gui.quick_song_dialog import QuickSongDialog
    dlg = QuickSongDialog()
    monkeypatch.setattr(dlg._playback, "play", lambda project, *a, **k: setattr(dlg, "played", project))
    monkeypatch.setattr(dlg._playback, "stop", lambda *a, **k: None)
    return dlg


def test_the_formation_dialog_lists_every_instrument_with_a_checkbox(app):
    from PySide6.QtCore import Qt
    from gui.quick_formation_dialog import FormationDialog
    dlg = FormationDialog(None, ["Alto_Sax", "Drums"])
    assert dlg.selected() == ["Drums", "Alto_Sax"]                 # nell'ordine dell'elenco
    items = list(dlg._items())
    assert len(items) >= 129 and all(i.flags() & Qt.ItemIsUserCheckable for i in items)
    from PySide6.QtWidgets import QDialogButtonBox
    assert dlg.buttons.button(QDialogButtonBox.Ok).text() == "Conferma formazione"
    assert "Batteria" in dlg.summary.text() or "Drums" in dlg.summary.text()
    dlg._clear()
    assert dlg.selected() == [] and "organico" in dlg.summary.text()
    dlg.filter.setText("sax")
    shown = [i.text(0) for i in items if not i.isHidden()]
    assert shown and all("sax" in s.lower() for s in shown)


def test_the_button_opens_the_dialog_and_the_formation_reaches_the_song(app, monkeypatch):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QDialog
    from gui.quick_formation_dialog import FormationDialog
    dlg = _dialog(app, monkeypatch)
    assert dlg.formation_button.text().startswith("Formazione") and dlg.formation == []
    assert "formation" not in dlg.options()

    def fake_exec(self):
        for item in self._items():
            item.setCheckState(0, Qt.Checked if item.data(0, Qt.UserRole) in (JAZZ_GUITAR, ACOUSTIC_BASS, "Drums") else Qt.Unchecked)
        return QDialog.Accepted
    monkeypatch.setattr(FormationDialog, "exec", fake_exec)
    dlg.choose_formation()
    assert dlg.formation == ["Drums", JAZZ_GUITAR, ACOUSTIC_BASS] or set(dlg.formation) == {JAZZ_GUITAR, ACOUSTIC_BASS, "Drums"}
    assert not dlg.ensemble_combo.isEnabled()
    assert set(dlg.options()["formation"]) == set(dlg.formation)
    dlg.compose(listen=False)
    assert dlg.song is not None and set(dlg.song["parts"]) == {"comp", "bass", "drums"}
    assert "Formazione:" in dlg.summary.text()
    dlg.set_formation([])
    assert dlg.ensemble_combo.isEnabled() and "formation" not in dlg.options()
