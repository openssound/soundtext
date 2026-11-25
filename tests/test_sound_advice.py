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


def _install(dest, group, relative, region="<region> sample=a.wav"):
    """Un gruppo di scarica_strumenti finto, scaricato tutto (con .completo) e con il file .sfz 'relative' (che di
    solito suona tutti i tasti)."""
    _name, _desc, _url, sub = load_script().trova(group)
    folder = dest / sub / group
    (folder / relative).parent.mkdir(parents=True, exist_ok=True)
    (folder / relative).write_text(region + "\n")
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
    _join_prefetch()
    sound_advice.forget_installed()
    yield tmp_path
    _join_prefetch()
    sound_advice.forget_installed()


def _join_prefetch():
    """Le ricerche in background (sound_advice.prefetch) di una finestra aperta prima: finite, non toccano la cartella
    finta del test."""
    import threading
    for thread in threading.enumerate():
        if thread.name == "sfz-prefetch":
            thread.join(timeout=60)


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
    script = load_script()
    monkeypatch.setattr(script, "libreria_precompilata", lambda: "libsfizz.so")
    _made, project = _song("rock")
    advice = sound_advice.sound_advice(project)
    assert not advice.usable and "libreria" in advice.download_keys
    assert any("motore SFZ" in line for line in sound_advice.describe(advice))
    # dove la libreria si dovrebbe compilare (minuti) non si spunta: lo dice solo il testo
    monkeypatch.setattr(script, "libreria_precompilata", lambda: None)
    advice = sound_advice.sound_advice(project)
    assert "libreria" not in advice.download_keys and any("motore SFZ" in line for line in sound_advice.describe(advice))


def test_a_file_that_leaves_notes_silent_is_not_proposed_and_the_next_candidate_is_tried(instruments):
    _made, project = _song("jazz")
    piano = project.get_track("Piano") or pytest.skip("niente pianoforte in questo jazz")
    _install(instruments, "splendid-piano", "Splendid Grand Piano.sfz", "<region> sample=a.wav lokey=60 hikey=61")
    assert not sound_advice.covers(project, piano, str(next(instruments.rglob("Splendid Grand Piano.sfz"))))
    sound = sound_advice.track_sound(piano, project=project)                    # niente di scaricato che suoni tutto:
    assert not sound.installed and sound.group == "piano"                       # si propone di scaricare il seguente
    upright = _install(instruments, "upright", "U/U.sfz")
    sound = sound_advice.track_sound(piano, project=project)
    assert sound.installed and sound.path == str(upright)
    advice = sound_advice.sound_advice(project)
    assert [s.path for s in advice.usable if s.track == "Piano"] == [str(upright)]
    sound_advice.apply_sfz(project, advice)
    from core.sfz_coverage import silent_notes
    assert silent_notes(project, project.get_track("Piano")) is None


def _with_track(genre, name):
    """Un brano del genere con la traccia 'name' (il seme che la mette nella formazione)."""
    for seed in range(1, 80):
        _made, project = _song(genre, seed)
        track = next((t for t in project.tracks if t.name == name), None)
        if track is not None:
            return project, track
    pytest.skip(f"nessun {genre} con {name}")


def test_the_jazz_guitar_gets_an_archtop_never_the_bridge_electric(instruments):
    project, guitar = _with_track("jazz", "Jazz_Guitar")
    _install(instruments, "chitarra-elettrica", "G/EGuitar clean bridge.sfz")
    sound = sound_advice.track_sound(guitar, project=project)
    assert not sound.installed and sound.group == "shinyguitar"                 # la archtop da scaricare
    archtop = _install(instruments, "shinyguitar", "Shinyguitar/Programs/electric_one.sfz")
    sound_advice.forget_installed()
    sound = sound_advice.track_sound(guitar, project=project)
    assert sound.installed and sound.path == str(archtop)


def test_any_sfz_in_the_instruments_folder_is_found_by_its_name(instruments):
    """Ogni installazione e' diversa: un file messo a mano, fuori dalle voci di "Scarica e installa", si riconosce dal
    nome; un segnaposto (solo onde generate) no."""
    project, guitar = _with_track("jazz", "Jazz_Guitar")
    mine = instruments / "miei"
    mine.mkdir()
    (mine / "Jazz Guitar.sfz").write_text("<region> sample=*sine\n")             # segnaposto
    assert not sound_advice.track_sound(guitar, project=project).installed
    (mine / "Archtop Jazz Guitar.sfz").write_text("<region> sample=a.wav\n")
    sound_advice.forget_installed()
    sound = sound_advice.track_sound(guitar, project=project)
    assert sound.installed and sound.path == str(mine / "Archtop Jazz Guitar.sfz")
    assert sound.group_label == "Archtop Jazz Guitar"
    assert sound_advice.kinds_of("Archtop Jazz Guitar") == {26}


def test_names_are_read_with_the_group_and_the_plain_variant_comes_first(instruments):
    _made, project = _song("rock")
    bass = project.get_track("Bass")
    _install(instruments, "meatbass", "Meatbass/Programs/arco_six.sfz")         # basso elettrico, ma suonato con l'arco
    sound_advice.forget_installed()
    assert not sound_advice.track_sound(bass, project=project).installed
    pizz = _install(instruments, "meatbass", "Meatbass/Programs/pizz.sfz")
    sound_advice.forget_installed()
    assert sound_advice.track_sound(bass, project=project).path == str(pizz)
    files = ["alto_map_saxcordion.sfz", "alto_map_forte_dynamic.sfz"]
    assert sorted(files, key=sound_advice._rank)[0] == "alto_map_forte_dynamic.sfz"


def test_without_a_preferred_download_the_smallest_group_naming_the_instrument_is_suggested(instruments):
    script = load_script()
    group = sound_advice._to_download(script, 110)                              # violino da fiddle: nessun preferito
    assert group and 110 in sound_advice.kinds_of(script.trova(group)[1])
    assert sound_advice._to_download(script, 35) is None                        # basso fretless: nessuna voce


def test_the_drum_kit_override_counts(instruments, monkeypatch):
    from core import settings
    _install(instruments, "batteria", "Kit/Kit-GM.sfz")
    _made, project = _song("rock")
    drums = next(t for t in project.tracks if t.instrument.is_percussion)
    assert sound_advice.track_sound(drums, project=project) is not None
    overrides = {drums.instrument_name or drums.instrument.name: 24}             # kit elettronico in Gestione strumenti
    monkeypatch.setattr(settings, "get_drum_kit_override", lambda name: overrides.get(name))
    assert sound_advice.track_sound(drums, project=project) is None


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
    dlg = QuickSongDialog()
    monkeypatch.setattr(dlg._playback, "play", lambda project, *a, **k: setattr(dlg, "played", project))
    monkeypatch.setattr(dlg._playback, "stop", lambda *a, **k: None)
    assert not dlg.sounds_label.text()                                    # prima di comporre niente
    dlg.genre_list.setCurrentRow(next(i for i, g in enumerate(dlg.choices["genres"]) if g["value"] == "jazz"))
    dlg.duration_combo.setCurrentIndex(0)
    dlg.detail_check.setChecked(True)
    dlg.seed_spin.setValue(1)                                             # un jazz col pianoforte
    dlg.sfz_check.setChecked(False)
    dlg.compose()
    comp = dlg._advice.usable[0].track
    assert comp == "Piano"
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


def test_dynamics_and_adjectives_do_not_make_a_piano():
    assert sound_advice.kinds_of("Violin piano") == {40, 110}
    assert sound_advice.kinds_of("Grand Organ") == {16, 17, 18}
    assert sound_advice.kinds_of("Piano verticale piccolo") == {0, 1, 2, 3}           # «piccolo» non e' l'ottavino
    assert sound_advice.kinds_of("PiccoloSus") == {72}
    assert sound_advice.kinds_of("Sax soprano, contralto, tenore e baritono MTG") == {64, 65, 66, 67}
    assert sound_advice.kinds_of("Piano elettrico FM") == {5}


def test_the_group_names_the_instrument_and_a_dynamic_in_the_file_name_cannot_change_it(instruments):
    _install(instruments, "sax", "S/tenor_map_piano_dynamic.sfz")                     # voce: «Sax tenore»
    found = {os.path.basename(f.path): f.kinds for f in sound_advice.installed_sfz(load_script())}
    assert found == {"tenor_map_piano_dynamic.sfz": {66}}


def test_a_placeholder_hidden_in_an_include_is_skipped(instruments):
    mine = instruments / "miei"
    mine.mkdir()
    (mine / "sine.sfzh").write_text("<region> sample=*sine\n")
    (mine / "Archtop Jazz Guitar.sfz").write_text('#include "sine.sfzh"\n')
    assert sound_advice.installed_sfz(load_script()) == []


def test_variants_that_are_the_instrument_come_first_and_every_file_is_tried(instruments):
    names = ["Guitar Clean.sfz", "Guitar Muted.sfz"]
    assert sorted(names, key=lambda p: sound_advice._rank(p, 28))[0] == "Guitar Muted.sfz"
    assert sorted(names, key=lambda p: sound_advice._rank(p, 27))[0] == "Guitar Clean.sfz"
    project, guitar = _with_track("jazz", "Jazz_Guitar")
    mine = instruments / "miei"
    mine.mkdir()
    for i in range(20):                                                               # tante varianti che non bastano
        (mine / f"Archtop {i:02d}.sfz").write_text("<region> sample=a.wav lokey=0 hikey=1\n")
    (mine / "Archtop Jazz Guitar Full Range Sustain.sfz").write_text("<region> sample=a.wav\n")
    sound = sound_advice.track_sound(guitar, project=project)
    assert sound.installed and sound.path.endswith("Full Range Sustain.sfz")         # l'ultima, la sola che suona tutto


def test_prefetch_scans_in_the_background_and_reads_the_regions(instruments):
    from core import sfz_coverage
    path = _install(instruments, "basso", "B/B.sfz")
    sound_advice.prefetch().join(timeout=30)
    assert [f.path for f in sound_advice.installed_sfz(load_script())] == [str(path)]
    assert str(path) in sfz_coverage._cache                                           # gia' letto: comporre non aspetta


def test_the_archtop_plays_a_few_dB_lower_but_a_volume_you_set_stays(instruments):
    """La Shinyguitar suonava gli accordi del jazz 6 dB sopra il contrabbasso: apply_sfz porta la traccia a 55; un volume
    gia' scelto dall'utente non si tocca."""
    project, guitar = _with_track("jazz", "Jazz_Guitar")
    _install(instruments, "shinyguitar", "Shinyguitar/Programs/electric_one.sfz")
    sound_advice.forget_installed()
    advice = sound_advice.sound_advice(project)
    assert guitar.volume == 100
    sound_advice.apply_sfz(project, advice)
    assert guitar.synth.startswith("sfz:") and guitar.volume == sound_advice.SFZ_VOLUME["shinyguitar"] == 55
    project2, guitar2 = _with_track("jazz", "Jazz_Guitar")
    guitar2.volume = 80
    sound_advice.apply_sfz(project2, sound_advice.sound_advice(project2))
    assert guitar2.volume == 80
