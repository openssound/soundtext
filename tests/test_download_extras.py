"""
Le aggiunte a "Scarica e installa": strumenti per compilare e libreria lilv
installati su richiesta, plugin LV2, SoundFont, casella di gruppo e
sorgenti dei download modificabili. Niente rete ne' comandi veri: download,
apt e winget sono finti.

Esecuzione:
    python3 -m pytest tests/test_download_extras.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import io
import os
import sys
import tarfile
import zipfile

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from core import downloads  # noqa: E402
from core import settings as app_settings  # noqa: E402

_app = QApplication.instance() or QApplication([])


@pytest.fixture
def script(tmp_path, monkeypatch):
    s = downloads.load_script()
    monkeypatch.setattr(s, "DEST", tmp_path / "Strumenti")
    monkeypatch.setattr(s, "user_lv2_dir", lambda: tmp_path / "lv2")
    return s


@pytest.fixture
def no_sources():
    app_settings.set_download_sources({})
    yield
    app_settings.set_download_sources({})


# ------------------------------------------------------------ strumenti per compilare

def test_missing_build_tools_are_installed_with_one_apt_command(script, monkeypatch):
    commands = []
    present = {"pkexec"}
    monkeypatch.setattr(script, "SISTEMA", "linux")
    monkeypatch.setattr(script.shutil, "which", lambda name: f"/usr/bin/{name}"
                        if name in present or name == "apt-get" else None)
    monkeypatch.setattr(script.sys, "stdin", None)                       # dalla finestra: pkexec
    assert [n for n, _c in script.strumenti_compilazione_mancanti()] == [
        "git", "il compilatore C++ e make", "cmake"]

    def fake_run(cmd, **kw):
        commands.append([str(c) for c in cmd])
        present.update({"git", "g++", "make", "cmake"})                   # apt li ha installati

    monkeypatch.setattr(script, "_esegui", fake_run)
    script.installa_strumenti_compilazione()
    assert len(commands) == 1                                            # una sola password
    assert commands[0][:3] == ["pkexec", "sh", "-c"] and commands[0][-3:] == ["git", "build-essential", "cmake"]


def test_build_tools_that_cannot_be_installed_say_why(script, monkeypatch):
    monkeypatch.setattr(script, "SISTEMA", "linux")
    monkeypatch.setattr(script.shutil, "which", lambda name: "/usr/bin/apt-get" if name == "apt-get" else None)
    monkeypatch.setattr(script.sys, "stdin", None)                       # niente terminale, niente pkexec
    assert "terminale" in script.motivo_installazione_impossibile()
    with pytest.raises(script.Errore):
        script.installa_strumenti_compilazione()


def test_windows_installs_git_and_the_build_tools_with_winget(script, monkeypatch):
    commands = []
    monkeypatch.setattr(script, "SISTEMA", "windows")
    monkeypatch.setattr(script.shutil, "which", lambda name: "C:/winget.exe" if name == "winget" else None)
    monkeypatch.setattr(script, "_git_windows", lambda: "")
    installed = {"vs": False}
    monkeypatch.setattr(script, "visual_studio", lambda: "C:/VS" if installed["vs"] else "")

    def fake_run(cmd, **kw):
        commands.append(cmd)
        if "Microsoft.VisualStudio.2022.BuildTools" in cmd:
            installed["vs"] = True
            monkeypatch.setattr(script, "_git_windows", lambda: "C:/Git/cmd")

    monkeypatch.setattr(script, "_esegui", fake_run)
    script.installa_strumenti_compilazione()
    assert [c[3] for c in commands] == ["Git.Git", "Microsoft.VisualStudio.2022.BuildTools"]


def _dialog_with(monkeypatch, missing, problem, answer):
    from gui.download_dialog import DownloadDialog
    monkeypatch.setattr(downloads, "missing_build_tools", lambda: missing)
    monkeypatch.setattr(downloads, "build_tools_install_problem", lambda: problem)
    asked, warned = [], []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: asked.append(a[2]) or answer)
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warned.append(a[2]))
    dlg = DownloadDialog()
    dlg._items["libreria"].installed = False
    return dlg, asked, warned


def test_dialog_offers_to_install_the_build_tools(script, monkeypatch):
    dlg, asked, _w = _dialog_with(monkeypatch, ["cmake"], "", QMessageBox.Yes)
    assert dlg._add_requirements(["libreria", "piano"]) == ["strumenti-compilazione", "libreria", "piano"]
    assert "cmake" in asked[0]
    dlg.close()
    dlg, _a, _w = _dialog_with(monkeypatch, ["cmake"], "", QMessageBox.No)
    assert dlg._add_requirements(["libreria", "piano"]) == ["piano"]       # senza strumenti, niente compilazione
    dlg.close()
    dlg, asked, warned = _dialog_with(monkeypatch, ["cmake"], "manca winget", QMessageBox.Yes)
    assert dlg._add_requirements(["libreria"]) == [] and not asked and "manca winget" in warned[0]
    dlg.close()


def test_dialog_offers_to_install_lilv_for_the_lv2_plugins(script, monkeypatch):
    dlg, asked, _w = _dialog_with(monkeypatch, [], "", QMessageBox.Yes)
    monkeypatch.setattr(downloads, "lilv_missing", lambda: True)
    assert dlg._add_requirements(["lv2"]) == ["lilv", "lv2"] and "lilv" in asked[0]
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.No)
    assert dlg._add_requirements(["lv2"]) == ["lv2"]                     # i plugin si scaricano lo stesso
    monkeypatch.setattr(downloads, "lilv_missing", lambda: False)
    assert dlg._add_requirements(["lv2"]) == ["lv2"]
    dlg.close()


def test_lilv_is_installed_with_apt(script, monkeypatch):
    commands = []
    monkeypatch.setattr(script, "SISTEMA", "linux")
    monkeypatch.setattr(script, "lilv_presente", lambda: False)
    monkeypatch.setattr(script.shutil, "which", lambda name: f"/usr/bin/{name}" if name in ("apt-get", "pkexec") else None)
    monkeypatch.setattr(script.sys, "stdin", None)
    monkeypatch.setattr(script, "_esegui", lambda cmd, **kw: commands.append([str(c) for c in cmd]))
    script.installa_lilv()
    assert commands == [["pkexec", "apt-get", "install", "-y", "liblilv-0-0"]]


# ------------------------------------------------------------ plugin LV2

def test_lv2_plugins_are_copied_into_the_user_folder(script, tmp_path, monkeypatch):
    archive = tmp_path / "plugin.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("dentro/Prova.lv2/manifest.ttl", "# finto\n")
        z.writestr("dentro/Prova.vst3/finto", "x")
    monkeypatch.setattr(script, "SISTEMA", "linux")
    monkeypatch.setattr(script, "chiave_sistema", lambda: "linux-x86_64")
    monkeypatch.setattr(script, "PLUGIN_LV2", [("Prova", "finto", "a/b", "latest", {"linux-x86_64": r"plugin\.zip"})])
    monkeypatch.setattr(script, "asset_github", lambda *a: "https://example.invalid/plugin.zip")
    monkeypatch.setattr(script, "scarica_file", lambda url, dest: dest.write_bytes(archive.read_bytes()))
    monkeypatch.setattr(script, "lilv_presente", lambda: True)
    script.installa_lv2()
    assert (tmp_path / "lv2" / "Prova.lv2" / "manifest.ttl").exists()
    assert not (tmp_path / "lv2" / "Prova.vst3").exists()                # solo gli LV2


def test_lv2_item_is_offered_only_on_linux(script, monkeypatch):
    from gui.download_dialog import DownloadDialog, KEY_ROLE
    for system, enabled in (("linux", True), ("windows", False)):
        monkeypatch.setattr(script, "SISTEMA", system)
        dlg = DownloadDialog()
        row = next(r for r in dlg._rows() if r.data(0, KEY_ROLE) == "lv2")
        assert bool(row.flags() & Qt.ItemIsEnabled) == enabled
        dlg.close()


# ------------------------------------------------------------ SoundFont

def test_soundfont_is_extracted_with_its_license(tmp_path, monkeypatch):
    from core import soundfont_downloads as sf
    folder = tmp_path / "soundfonts"
    folder.mkdir()
    monkeypatch.setattr(sf, "ensure_soundfonts_dir", lambda: str(folder))
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w:xz") as tar:
        for name, data in (("Kit/Kit.sf2", b"RIFF finto"), ("Kit/gpl.txt", b"GPL"), ("Altro/x.txt", b"no")):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    source = sf.SoundFontSource("sf-prova", "Prova", "GPL", "https://example.invalid/Kit.tar.xz", "Kit.sf2")
    path = sf.download(source, fetch=lambda url, dest: open(dest, "wb").write(archive.getvalue()), log=lambda s: None)
    assert open(path, "rb").read() == b"RIFF finto"
    assert (folder / "Kit-gpl.txt").read_bytes() == b"GPL" and not (folder / "Kit-x.txt").exists()


def test_plain_soundfont_gets_its_license_file(tmp_path, monkeypatch):
    from core import soundfont_downloads as sf
    monkeypatch.setattr(sf, "ensure_soundfonts_dir", lambda: str(tmp_path))
    source = sf.find("sf-musescore")
    files = {source.url: b"sfbk finto", source.license_url: b"MIT"}
    sf.download(source, fetch=lambda url, dest: open(dest, "wb").write(files[url]), log=lambda s: None)
    assert (tmp_path / "MuseScore_General.sf3").read_bytes() == b"sfbk finto"
    assert (tmp_path / "MuseScore_General-LICENSE.md").read_bytes() == b"MIT"


def test_soundfonts_are_in_the_catalog():
    items = {i.key: i for i in downloads.catalog()}
    assert {k for k, i in items.items() if i.category == downloads.CATEGORY_SOUNDFONTS} == {
        "sf-musescore", "sf-timgm6mb", "sf-freepats-drums"}


# ------------------------------------------------------------ casella di gruppo

def test_group_checkbox_checks_every_instrument(script):
    from gui.download_dialog import DownloadDialog, KEY_ROLE
    dlg = DownloadDialog()
    head = next(dlg.tree.topLevelItem(i) for i in range(dlg.tree.topLevelItemCount())
                if dlg.tree.topLevelItem(i).text(0) == downloads.category_label(downloads.CATEGORY_SFZ))
    sfz = [head.child(j).data(0, KEY_ROLE) for j in range(head.childCount())]
    head.setCheckState(0, Qt.Checked)
    assert dlg.checked_keys() == sfz and dlg.install_btn.isEnabled()
    head.child(0).setCheckState(0, Qt.Unchecked)
    assert head.checkState(0) == Qt.PartiallyChecked
    head.setCheckState(0, Qt.Unchecked)
    assert dlg.checked_keys() == []
    other = next(dlg.tree.topLevelItem(i) for i in range(dlg.tree.topLevelItemCount())
                 if dlg.tree.topLevelItem(i).text(0) == downloads.category_label(downloads.CATEGORY_PLUGINS))
    assert not other.flags() & Qt.ItemIsUserCheckable                    # solo i gruppi di strumenti
    dlg.close()


# ------------------------------------------------------------ sorgenti

def test_sources_cover_every_kind_of_item():
    keys = {s.key for s in downloads.sources()}
    assert {"sfz:piano", "sfz:fashionbass", "sf:sf-musescore", "profili-nam", "casse-ir", "nam-plugin",
            "vst3:Dexed", "lv2:Geonkick", "surge", "sfizz-deb", "libreria"} <= keys


def test_overrides_reach_the_script_and_the_modules(script, monkeypatch):
    import core.nam_profiles
    from core import soundfont_downloads
    monkeypatch.setattr(script, "GRUPPI", list(script.GRUPPI))
    monkeypatch.setattr(script, "PLUGIN_VST3", list(script.PLUGIN_VST3))
    monkeypatch.setattr(core.nam_profiles, "RAW_BASE", core.nam_profiles.RAW_BASE)
    monkeypatch.setattr(soundfont_downloads, "SOUNDFONTS", list(soundfont_downloads.SOUNDFONTS))
    monkeypatch.setattr(script, "SURGE_REPO", script.SURGE_REPO)
    downloads.apply_source_overrides(script, {
        "sfz:piano": "https://mirror.example/piano.tar.gz", "vst3:Dexed": "https://github.com/io/dexed",
        "profili-nam": "https://mirror.example/nam", "sf:sf-timgm6mb": "https://mirror.example/tim.tar.gz",
        "surge": "https://github.com/io/surge/"})
    assert script.trova("piano")[2] == "https://mirror.example/piano.tar.gz"
    assert next(p for p in script.PLUGIN_VST3 if p[0] == "Dexed")[2] == "io/dexed"
    assert core.nam_profiles.RAW_BASE == "https://mirror.example/nam/"
    assert soundfont_downloads.find("sf-timgm6mb").url == "https://mirror.example/tim.tar.gz"
    assert script.SURGE_REPO == "io/surge"
    # gli originali restano quelli del file
    assert next(s for s in downloads.sources() if s.key == "sfz:piano").default.startswith("https://freepats")


def test_sources_dialog_checks_saves_and_restores(no_sources, monkeypatch):
    from gui.download_sources_dialog import DownloadSourcesDialog
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    dlg = DownloadSourcesDialog()
    assert dlg.set_value("sfz:piano", "ftp://non va") != ""              # rifiutato, resta l'originale
    assert dlg.changed_values() == {}
    assert dlg.set_value("vst3:Dexed", "https://example.com/dexed") != ""   # non e' un progetto GitHub
    assert dlg.set_value("sfz:piano", "https://mirror.example/piano.tar.gz") == ""
    assert dlg.set_value("vst3:Dexed", "https://github.com/io/dexed") == ""
    dlg.accept()
    assert app_settings.get_download_sources() == {"sfz:piano": "https://mirror.example/piano.tar.gz",
                                                   "vst3:Dexed": "https://github.com/io/dexed"}
    again = DownloadSourcesDialog()
    assert again.changed_values() == app_settings.get_download_sources()
    again.reset_all()
    again.accept()
    assert app_settings.get_download_sources() == {}


def test_options_menu_opens_the_sources_dialog():
    from gui.command_palette import collect_commands
    from gui.main_window import MainWindow
    w = MainWindow()
    entries = {(c.path, c.title) for c in collect_commands(w.menuBar())}
    assert ("Opzioni", "Sorgenti dei download...") in entries
    w.close()
