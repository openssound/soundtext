"""
La finestra "Scarica e installa" e cio' che c'e' sotto (core.downloads,
scarica_strumenti.py): l'elenco con lo stato delle voci, il processo che le
esegue, il plugin Neural Amp Modeler verificato con lo SHA-256. Niente rete:
download e processi sono finti.

Esecuzione:
    python3 -m pytest tests/test_downloads.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import hashlib
import os
import sys
import tarfile

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication  # noqa: E402

from core import downloads  # noqa: E402

_app = QApplication.instance() or QApplication([])


@pytest.fixture
def script(tmp_path, monkeypatch):
    s = downloads.load_script()
    monkeypatch.setattr(s, "DEST", tmp_path / "Strumenti")
    monkeypatch.setattr(s, "user_lv2_dir", lambda: tmp_path / "lv2")
    return s


def test_catalog_has_every_category_and_reads_the_state(script):
    (script.DEST / "sfz" / "piano").mkdir(parents=True)
    (script.DEST / "sfz" / "piano" / ".completo").touch()
    items = {i.key: i for i in downloads.catalog()}
    assert {i.category for i in items.values()} == {downloads.CATEGORY_SFZ, downloads.CATEGORY_SFZ_EXTRA,
                                                  downloads.CATEGORY_ORCHESTRA,
                                                  downloads.CATEGORY_SOUNDFONTS, downloads.CATEGORY_AMP,
                                                  downloads.CATEGORY_PLUGINS, downloads.CATEGORY_ENGINES}
    assert items["piano"].installed is True and items["upright"].installed is False
    assert items["piano"].detail.endswith("740 MB")
    assert items["nam-plugin"].installed is False
    assert items["vst3"].installed is None                  # non si sa: si puo' sempre reinstallare
    # si compila solo dove non c'e' gia' compilata (release libsfizz-*)
    assert items["libreria"].needs_build == (script.libreria_precompilata() is None)


def test_the_process_is_soundtext_itself():
    cmd = downloads.command(["piano", "nam-plugin"])
    assert cmd[-3:] == ["--scarica-strumenti", "piano", "nam-plugin"]
    assert cmd[0] == sys.executable


def test_nam_items_go_to_the_program_functions(monkeypatch, capsys):
    import core.cab_irs
    import core.nam_profiles
    monkeypatch.setattr(core.nam_profiles, "download_profiles",
                        lambda progress=None: (progress(1, 1, "a.nam"), {"folder": "/p", "failed": []})[1])
    monkeypatch.setattr(core.cab_irs, "download_cabinets",
                        lambda progress=None: {"folder": "/c", "failed": [("b.wav", "rete")]})
    assert downloads.run_script(["profili-nam", "casse-ir"]) == 1        # una cassa non riuscita
    out = capsys.readouterr().out
    assert "== profili-nam" in out and "1/1 a.nam" in out and "non riuscito: b.wav" in out


def _fake_release(tmp_path):
    bundle = tmp_path / "rilascio" / "neural_amp_modeler.lv2"
    bundle.mkdir(parents=True)
    (bundle / "manifest.ttl").write_text("# finto\n")
    archive = tmp_path / "neural_amp_modeler_lv2_linux_x64.tgz"
    with tarfile.open(archive, "w:gz") as t:
        t.add(bundle, arcname="neural_amp_modeler.lv2")
    return archive


def test_nam_plugin_is_checked_and_installed(script, tmp_path, monkeypatch):
    archive = _fake_release(tmp_path)
    sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    monkeypatch.setattr(script, "SISTEMA", "linux")
    monkeypatch.setattr(script, "NAM_PLUGIN_FILES", {"linux": (archive.name, sha)})
    monkeypatch.setattr(script, "scarica_file", lambda url, dest: dest.parent.mkdir(parents=True, exist_ok=True)
                        or dest.write_bytes(archive.read_bytes()))
    import platform
    monkeypatch.setattr(platform, "machine", lambda: "x86_64")
    script.installa_plugin_nam()
    installed = tmp_path / "lv2" / "neural_amp_modeler.lv2"
    assert (installed / "manifest.ttl").exists()
    assert (installed / "soundtext.versione").read_text().strip() == script.NAM_PLUGIN_VERSION
    assert {i.key: i for i in downloads.catalog()}["nam-plugin"].installed is True


def test_nam_plugin_with_the_wrong_file_is_refused(script, tmp_path, monkeypatch):
    archive = _fake_release(tmp_path)
    monkeypatch.setattr(script, "SISTEMA", "linux")
    monkeypatch.setattr(script, "NAM_PLUGIN_FILES", {"linux": (archive.name, "0" * 64)})
    monkeypatch.setattr(script, "scarica_file", lambda url, dest: dest.parent.mkdir(parents=True, exist_ok=True)
                        or dest.write_bytes(archive.read_bytes()))
    import platform
    monkeypatch.setattr(platform, "machine", lambda: "x86_64")
    with pytest.raises(script.Errore):
        script.installa_plugin_nam()
    assert not (tmp_path / "lv2" / "neural_amp_modeler.lv2").exists()


def _fake_libsfizz(script, tmp_path, monkeypatch, sha=None):
    """La libreria gia' compilata, finta: il download scrive dei byte e
    ctypes.CDLL la "carica" senza aprirla."""
    content = b"finta libsfizz"
    monkeypatch.setattr(script, "SISTEMA", "linux")
    monkeypatch.setattr(script, "LIB_FILE", "libsfizz.so")
    monkeypatch.setattr(script, "user_lib_dir", lambda: tmp_path / "lib")
    monkeypatch.setattr(script, "LIBSFIZZ_FILES", {("linux", "x86_64"): (
        "libsfizz-linux-x86_64.so", sha or hashlib.sha256(content).hexdigest())})
    urls = []
    monkeypatch.setattr(script, "scarica_file", lambda url, dest: urls.append(url) or
                        dest.parent.mkdir(parents=True, exist_ok=True) or dest.write_bytes(content))
    monkeypatch.setattr(script.ctypes, "CDLL", lambda path: type("Lib", (), {"sfizz_create_synth": 1})())
    import platform
    monkeypatch.setattr(platform, "machine", lambda: "AMD64")      # come lo dice Windows: x86_64
    return urls


def test_prebuilt_libsfizz_is_downloaded_and_checked(script, tmp_path, monkeypatch):
    urls = _fake_libsfizz(script, tmp_path, monkeypatch)
    monkeypatch.setattr(script, "compila_libreria", lambda *a: pytest.fail("non deve compilare"))
    script.installa_libreria()
    assert urls == [script.LIBSFIZZ_BASE + "libsfizz-linux-x86_64.so"]
    assert f"libsfizz-{script.SFIZIOSO_COMMIT[:7]}/" in urls[0]
    assert (tmp_path / "lib" / "libsfizz.so").read_bytes() == b"finta libsfizz"
    assert (tmp_path / "lib" / "sfizioso.commit").read_text().strip() == script.SFIZIOSO_COMMIT
    item = {i.key: i for i in downloads.catalog()}["libreria"]
    assert item.installed and not item.needs_build


def test_prebuilt_libsfizz_is_loaded_only_where_it_stays(script, tmp_path, monkeypatch):
    """Su Windows una DLL caricata non si cancella finche' il processo vive:
    la prova si fa sulla copia installata, non sul file della cartella
    temporanea, che poi si toglie (la build v1.15.0 si era fermata li')."""
    _fake_libsfizz(script, tmp_path, monkeypatch)
    loaded = []

    def cdll(path):
        loaded.append(path)
        return type("Lib", (), {"sfizz_create_synth": 1})()
    monkeypatch.setattr(script.ctypes, "CDLL", cdll)
    removed = []
    real_remove = script._rimuovi
    monkeypatch.setattr(script, "_rimuovi", lambda path: (removed.append(path), real_remove(path)))
    script.installa_libreria()
    assert loaded == [str(tmp_path / "lib" / "libsfizz.so")]
    assert removed and all(str(path) not in loaded[0] for path in removed)


def test_prebuilt_libsfizz_that_does_not_load_is_not_left_installed(script, tmp_path, monkeypatch):
    _fake_libsfizz(script, tmp_path, monkeypatch)

    def cdll(path):
        raise OSError("GLIBC_2.38 not found")
    monkeypatch.setattr(script.ctypes, "CDLL", cdll)
    compiled = []
    monkeypatch.setattr(script, "compila_libreria", lambda lib_dir, stamp: compiled.append(lib_dir))
    script.installa_libreria()
    assert compiled and not (tmp_path / "lib" / "libsfizz.so").exists()


def test_prebuilt_libsfizz_with_the_wrong_sha_is_refused(script, tmp_path, monkeypatch):
    _fake_libsfizz(script, tmp_path, monkeypatch, sha="0" * 64)
    monkeypatch.setattr(script, "compila_libreria", lambda *a: pytest.fail("non deve compilare"))
    with pytest.raises(script.Errore, match="SHA-256"):
        script.installa_libreria()
    assert not (tmp_path / "lib" / "libsfizz.so").exists()


def test_libsfizz_is_compiled_without_a_prebuilt_or_when_asked(script, tmp_path, monkeypatch):
    _fake_libsfizz(script, tmp_path, monkeypatch)
    compiled = []
    monkeypatch.setattr(script, "compila_libreria", lambda lib_dir, stamp: compiled.append(lib_dir))
    script.installa_libreria(compila=True)                 # libreria --compila
    import platform
    monkeypatch.setattr(platform, "machine", lambda: "aarch64")    # Linux ARM: nessuna gia' compilata
    script.installa_libreria()
    assert compiled == [tmp_path / "lib", tmp_path / "lib"]
    assert not (tmp_path / "lib" / "libsfizz.so").exists()


def test_libsfizz_for_the_installers_goes_in_the_given_folder(script, tmp_path, monkeypatch):
    _fake_libsfizz(script, tmp_path, monkeypatch)
    assert script.main(["libreria", "--in", str(tmp_path / "dist" / "lib")]) == 0
    assert (tmp_path / "dist" / "lib" / "libsfizz.so").exists()
    assert not (tmp_path / "lib" / "sfizioso.commit").exists()    # la cartella dell'utente non si tocca


def test_dialog_runs_the_process_and_shows_the_log(script, monkeypatch):
    from gui.download_dialog import DownloadDialog
    monkeypatch.setattr(downloads, "command", lambda keys: [
        sys.executable, "-c",
        "import sys,time; print('== piano: Piano'); sys.stdout.write('\\r   5 MB 50%'); sys.stdout.flush();"
        "print('\\r   10 MB scaricati'); print('   -> fatto')"])
    dlg = DownloadDialog()
    dlg.set_checked(["piano"])
    assert dlg.checked_keys() == ["piano"] and dlg.install_btn.isEnabled()
    dlg.install()
    assert dlg._process is not None and not dlg.tree.isEnabled()
    dlg._process.waitForFinished(10000)
    for _ in range(20):
        _app.processEvents()
    log = dlg.log.toPlainText()
    assert "== piano: Piano" in log and "10 MB scaricati" in log and "-> fatto" in log
    assert "50%" not in log                                  # l'avanzamento resta sulla riga di stato
    assert dlg.changed and dlg.tree.isEnabled() and not dlg.checked_keys()
    dlg.close()


def test_linux_host_item_asks_the_password_with_pkexec(script, monkeypatch):
    from gui import download_dialog
    from gui.download_dialog import DownloadDialog, KEY_ROLE
    from PySide6.QtCore import Qt
    monkeypatch.setattr(script, "SISTEMA", "linux")
    for pkexec, enabled in (("/usr/bin/pkexec", True), (None, False)):     # senza pkexec: dal terminale
        monkeypatch.setattr(download_dialog.shutil, "which", lambda name, p=pkexec: p if name == "pkexec" else None)
        dlg = DownloadDialog()
        row = next(r for r in dlg._rows() if r.data(0, KEY_ROLE) == "host")
        assert bool(row.flags() & Qt.ItemIsEnabled) == enabled
        dlg.close()


def test_linux_host_installs_everything_with_one_password(script, tmp_path, monkeypatch):
    import types
    from pathlib import PureWindowsPath
    commands = []
    monkeypatch.setattr(script, "_esegui", lambda cmd, **kw: commands.append([str(c) for c in cmd]))
    monkeypatch.setattr(script, "asset_github", lambda *a: "https://example.invalid/surge.deb")
    monkeypatch.setattr(script, "scarica_file", lambda url, dest: dest.write_bytes(b"deb"))
    monkeypatch.setattr(script.subprocess, "run", lambda *a, **k: types.SimpleNamespace(returncode=1))
    monkeypatch.setattr(script.sys, "stdin", None)                       # lanciato dalla finestra
    monkeypatch.setattr(script.shutil, "which", lambda name: "/usr/bin/pkexec" if name == "pkexec" else None)
    script.host_linux()
    assert len(commands) == 1                                            # una sola richiesta di password
    cmd = commands[0]
    assert cmd[:3] == ["pkexec", "sh", "-c"] and "apt-get install -y" in cmd[3]
    # i .deb stanno nella cartella temporanea: sulla CI Windows i percorsi hanno "\\"
    assert cmd[5] == "7zip" and [PureWindowsPath(c).name for c in cmd[6:]] == [
        "surge-xt.deb", "libsfizz1.deb", "sfizz.deb"]
    monkeypatch.setattr(script.shutil, "which", lambda name: None)
    with pytest.raises(script.Errore):                                   # niente pkexec, niente terminale
        script.host_linux()
