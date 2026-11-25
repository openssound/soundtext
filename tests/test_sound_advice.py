"""I suoni consigliati per un brano (core.sound_advice) e la loro parte nella finestra «Un brano in 60 secondi»: si propongono
gli strumenti campionati gia' scaricati e quelli da scaricare, e il SoundFont completo al posto di quello leggero; niente
cambia da solo."""
import os

import pytest

from core import sound_advice
from core.downloads import load_script
from core.project_io import parse_project_text, project_to_text
from core.quicksong import quick_song


def _song(genre, seed=3):
    made = quick_song({"genre": genre, "seed": seed, "duration": 15})
    return made, parse_project_text(made["text"], made["name"])


def _install(dest, group, relative):
    """Un gruppo di scarica_strumenti finto, scaricato tutto (con .completo) e con il file .sfz 'relative'."""
    _name, _desc, _url, sub = load_script().trova(group)
    folder = dest / sub / group
    (folder / relative).parent.mkdir(parents=True, exist_ok=True)
    (folder / relative).write_text("<region> sample=a.wav\n")
    (folder / ".completo").write_text("")
    return folder / relative


@pytest.fixture
def instruments(tmp_path, monkeypatch):
    """Una cartella degli strumenti vuota, il motore SFZ presente e un SoundFont completo in uso."""
    script = load_script()
    if script is None:
        pytest.skip("manca scarica_strumenti.py")
    monkeypatch.setattr(script, "DEST", tmp_path)
    monkeypatch.setattr("core.sfz_engine.sfz_available", lambda: True)
    monkeypatch.setattr("core.playback._find_soundfont", lambda: "/x/MuseScore_General.sf3")
    return tmp_path


def test_nothing_downloaded_suggests_what_to_download_and_changes_nothing(instruments):
    _made, project = _song("rock")
    advice = sound_advice.sound_advice(project)
    groups = {s.track: s.group for s in advice.tracks}
    assert groups["Distortion_Guitar"] == "chitarra-dist" and groups["Bass"] == "basso" and groups["Drums"] == "batteria"
    assert not advice.usable and not advice.soundfont_note and not advice.use_soundfont
    assert {"chitarra-dist", "basso", "batteria"} <= set(advice.download_keys)
    assert sound_advice.apply_sfz(project, advice) == [] and not any(t.synth for t in project.tracks)
    lines = sound_advice.describe(advice)
    assert lines[0] == "Suoni: MuseScore_General.sf3" and any(line.startswith("Da scaricare") for line in lines)


def test_downloaded_instruments_are_used_on_request_and_saved_in_the_song(instruments):
    piano = _install(instruments, "splendid-piano", "Splendid Grand Piano.sfz")
    bass = _install(instruments, "contrabbasso", "dsmolken_double_bass/d_smolken_rubner_bass_pizz.sfz")
    _made, project = _song("jazz")
    advice = sound_advice.sound_advice(project)
    usable = {s.track: s.path for s in advice.usable}
    assert usable == {"Piano": str(piano), "Acoustic_Bass": str(bass)}
    assert sound_advice.apply_sfz(project, advice) == ["Piano", "Acoustic_Bass"]
    again = parse_project_text(project_to_text(project), "x")             # il file .sfz resta nel brano salvato
    assert again.get_track("Piano").synth.endswith("Splendid Grand Piano.sfz")
    assert again.get_track("Piano").synth.startswith("sfz:")
    drums = next(t for t in again.tracks if t.instrument.is_percussion)
    assert not drums.synth                                                # le spazzole del jazz restano al SoundFont


def test_preferred_downloaded_candidate_wins_and_electronic_kits_stay_on_the_soundfont(instruments):
    _install(instruments, "upright", "Upright/Upright.sfz")
    _made, project = _song("jazz")
    piano = next(s for s in sound_advice.sound_advice(project).tracks if s.track == "Piano")
    assert piano.group == "upright" and piano.installed                    # il primo gia' scaricato, anche se non il preferito
    _install(instruments, "batteria", "Kit/Kit-GM.sfz")
    _made, lofi = _song("lofi")
    assert not any(t.instrument.is_percussion and sound_advice.track_sound(t) for t in lofi.tracks)


def test_without_the_sfz_engine_nothing_is_usable_and_the_engine_is_suggested(instruments, monkeypatch):
    _install(instruments, "basso", "B/B.sfz")
    monkeypatch.setattr("core.sfz_engine.sfz_available", lambda: False)
    _made, project = _song("rock")
    advice = sound_advice.sound_advice(project)
    assert not advice.usable and "libreria" in advice.download_keys
    assert any("motore SFZ" in line for line in sound_advice.describe(advice))


def test_light_or_missing_soundfont(instruments, monkeypatch, tmp_path):
    from core import soundfont_downloads
    _made, project = _song("pop")
    monkeypatch.setattr("core.playback._find_soundfont", lambda: "/x/TimGM6mb.sf2")
    monkeypatch.setattr(soundfont_downloads, "installed_path", lambda source: "")
    advice = sound_advice.sound_advice(project)
    assert advice.soundfont_note and not advice.use_soundfont and advice.download_keys[0] == "sf-musescore"
    full = str(tmp_path / "MuseScore_General.sf3")
    monkeypatch.setattr(soundfont_downloads, "installed_path", lambda s: full if s.key == "sf-musescore" else "")
    assert sound_advice.sound_advice(project).use_soundfont == full
    monkeypatch.setattr("core.playback._find_soundfont", lambda: None)
    advice = sound_advice.sound_advice(project)
    assert "non si sente" in advice.soundfont_note and sound_advice.describe(advice)[0] == "Suoni: nessun SoundFont"


def test_a_track_with_its_own_plugin_is_left_alone(instruments):
    _install(instruments, "basso", "B/B.sfz")
    _made, project = _song("rock")
    project.get_track("Bass").synth = "vst3:/x/Bass.vst3"
    assert all(s.track != "Bass" for s in sound_advice.sound_advice(project).tracks)


# ---- la finestra

@pytest.fixture
def app():
    pytest.importorskip("PySide6")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_dialog_shows_the_advice_and_uses_the_sfz_only_when_ticked(app, instruments, monkeypatch):
    from gui.quick_song_dialog import QuickSongDialog
    _install(instruments, "splendid-piano", "Splendid Grand Piano.sfz")
    _install(instruments, "chitarra-elettrica", "G/G.sfz")                 # il jazz accompagna col piano o con la chitarra
    dlg = QuickSongDialog()
    monkeypatch.setattr(dlg._playback, "play", lambda project, *a, **k: setattr(dlg, "played", project))
    monkeypatch.setattr(dlg._playback, "stop", lambda *a, **k: None)
    assert not dlg.sounds_label.text()                                    # prima di comporre niente
    dlg.genre_list.setCurrentRow(next(i for i, g in enumerate(dlg.choices["genres"]) if g["value"] == "jazz"))
    dlg.duration_combo.setCurrentIndex(0)
    dlg.sfz_check.setChecked(False)
    dlg.compose()
    comp = dlg._advice.usable[0].track
    assert comp in ("Piano", "Jazz_Guitar")
    assert "Suoni: MuseScore_General.sf3" in dlg.sounds_label.text() and comp + " (" in dlg.sounds_label.text()
    assert not dlg.sfz_check.isHidden() and not dlg.played.get_track(comp).synth
    dlg.sfz_check.setChecked(True)
    dlg._listen()
    assert dlg.played.get_track(comp).synth.startswith("sfz:")
    assert dlg.project().get_track(comp).synth.startswith("sfz:")
    from core.settings import get_quick_song_sfz
    assert get_quick_song_sfz()                                           # la scelta resta per la prossima volta
    dlg.sfz_check.setChecked(False)
    assert not get_quick_song_sfz()


def test_dialog_switches_to_the_full_soundfont_and_opens_the_downloads(app, instruments, monkeypatch, tmp_path):
    from PySide6.QtWidgets import QWidget
    from core import settings, soundfont_downloads
    from gui.quick_song_dialog import QuickSongDialog
    full = str(tmp_path / "MuseScore_General.sf3")
    used = {"sf": "/x/TimGM6mb.sf2"}
    monkeypatch.setattr("core.playback._find_soundfont", lambda: used["sf"])
    monkeypatch.setattr(soundfont_downloads, "installed_path", lambda s: full if s.key == "sf-musescore" else "")
    monkeypatch.setattr(settings, "set_soundfont_path", lambda path: used.update(sf=path))

    class Window(QWidget):
        opened = None

        def open_download_dialog(self, preselect=None):
            Window.opened = preselect

    parent = Window()
    dlg = QuickSongDialog(parent)
    monkeypatch.setattr(dlg._playback, "play", lambda *a, **k: None)
    monkeypatch.setattr(dlg._playback, "stop", lambda *a, **k: None)
    dlg.duration_combo.setCurrentIndex(0)
    dlg.compose(listen=False)
    assert not dlg.use_soundfont_btn.isHidden() and "MuseScore_General.sf3" in dlg.use_soundfont_btn.text()
    dlg.use_soundfont_btn.click()
    assert used["sf"] == full and dlg.use_soundfont_btn.isHidden()
    assert not dlg.download_btn.isHidden()                                # niente e' scaricato: si propone di scaricare
    dlg.download_btn.click()
    assert Window.opened and set(Window.opened) == set(dlg._advice.download_keys)
