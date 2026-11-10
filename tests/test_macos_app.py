"""
Test per SoundText.app su macOS (packaging/macos): cartelle dei dati in
Contents/Resources, file dell'utente mai dentro l'app, brani aperti dal
Finder (QFileOpenEvent), permesso del microfono, icona .icns.

Esecuzione:
    python3 -m pytest tests/test_macos_app.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from PySide6.QtCore import QEvent
from PySide6.QtGui import QFileOpenEvent
from PySide6.QtWidgets import QApplication, QMessageBox

from core import version


def _fake_app(tmp_path):
    """Una SoundText.app finta: eseguibile in Contents/MacOS, dati in
    Contents/Resources."""
    contents = tmp_path / "SoundText.app" / "Contents"
    (contents / "MacOS").mkdir(parents=True)
    (contents / "MacOS" / "SoundText").write_text("")
    (contents / "Resources" / "assets").mkdir(parents=True)
    return contents


@pytest.mark.skipif(sys.platform != "darwin", reason="l'app esiste solo su macOS")
def test_app_root_is_contents_resources_in_the_mac_app(tmp_path, monkeypatch):
    contents = _fake_app(tmp_path)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(contents / "MacOS" / "SoundText"))
    assert version.macos_app_resources() == str(contents / "Resources")
    assert version.get_app_root() == str(contents / "Resources")
    # senza assets/ in Resources (un altro impacchettamento): come prima
    os.rmdir(contents / "Resources" / "assets")
    assert version.macos_app_resources() == ""
    assert version.get_app_root() == str(contents / "MacOS")


def test_user_files_never_go_inside_the_app(tmp_path, monkeypatch):
    contents = _fake_app(tmp_path)
    monkeypatch.setattr(version, "macos_app_resources", lambda: str(contents / "Resources"))
    fallback = tmp_path / "Documents" / "SoundText" / "songs"
    assert version.pick_writable_dir(str(contents / "Resources" / "songs"), str(fallback)) == str(fallback)
    assert not (contents / "Resources" / "songs").exists()
    elsewhere = tmp_path / "altrove"
    assert version.pick_writable_dir(str(elsewhere), str(fallback)) == str(elsewhere)


def test_not_frozen_means_no_mac_app():
    assert version.macos_app_resources() == ""


# ------------------------------------------------------------------ brani aperti dal Finder

class _Window:
    def __init__(self):
        self.opened = []

    def open_path(self, path, ask_to_save=True):
        self.opened.append((path, ask_to_save))
        return True


def test_finder_file_open_waits_for_the_window_then_opens():
    import main
    QApplication.instance() or QApplication([])
    app = type("App", (), {"_window": None, "_pending": []})()
    event = QFileOpenEvent("/brani/prova.st")
    assert event.type() == QEvent.FileOpen
    assert main._SoundTextApp.event(app, event) is True          # all'avvio: ancora niente finestra
    window = _Window()
    main._SoundTextApp.open_files_with(app, window)
    assert window.opened == [("/brani/prova.st", False)]          # niente da salvare all'avvio
    main._SoundTextApp.event(app, QFileOpenEvent("/brani/altro.st"))
    assert window.opened[-1] == ("/brani/altro.st", True)         # con un brano aperto: chiede


def test_open_path_imports_by_extension_and_asks_to_save(tmp_path, monkeypatch):
    from gui.main_window import MainWindow
    calls = []
    window = MainWindow()
    monkeypatch.setattr(window, "_load_and_apply_project", lambda p: calls.append(("st", p)))
    monkeypatch.setattr(window, "_import_musicxml_as_new_project", lambda p: calls.append(("xml", p)))
    monkeypatch.setattr(window, "_import_abc_as_new_project", lambda p: calls.append(("abc", p)))
    monkeypatch.setattr(window, "_confirm_discard_unsaved", lambda: False)
    files = {}
    for name in ("a.st", "b.musicxml", "c.abc"):
        files[name] = str(tmp_path / name)
        open(files[name], "w").close()
    assert window.open_path(files["a.st"]) is False                # annullato dall'utente
    assert window.open_path(files["a.st"], ask_to_save=False)
    assert window.open_path(files["b.musicxml"], ask_to_save=False)
    assert window.open_path(files["c.abc"], ask_to_save=False)
    assert window.open_path(str(tmp_path / "manca.st"), ask_to_save=False) is False
    assert calls == [("st", files["a.st"]), ("xml", files["b.musicxml"]), ("abc", files["c.abc"])]


# ------------------------------------------------------------------ microfono

def test_microphone_status_is_a_known_value():
    from core.macos_permissions import microphone_status
    status = microphone_status()
    assert status in ("", "authorized", "denied", "restricted", "not_determined")
    if sys.platform != "darwin":
        assert status == ""


def test_record_dialog_explains_a_denied_microphone(tmp_path, monkeypatch):
    from core import macos_permissions
    import test_audio_record_dialog_gui as rec
    monkeypatch.setattr(macos_permissions, "microphone_blocked", lambda: True)
    shown = []
    monkeypatch.setattr(QMessageBox, "exec", lambda self: shown.append(self.text()) or 0)
    dlg, _track, streams = rec._dialog(tmp_path)
    dlg.start_recording()
    assert "duplex" not in streams                                  # niente ripresa muta
    assert shown and "Privacy e sicurezza" in shown[0]
    dlg.reject()


# ------------------------------------------------------------------ icona

def test_icns_has_every_size_as_png(tmp_path):
    import generate_icons
    from PySide6.QtSvg import QSvgRenderer
    QApplication.instance() or QApplication([])
    path = tmp_path / "SoundText.icns"
    generate_icons.write_icns(str(path), QSvgRenderer(generate_icons.SVG_PATH))
    data = path.read_bytes()
    assert data[:4] == b"icns" and struct.unpack(">I", data[4:8])[0] == len(data)
    kinds, pos = [], 8
    while pos < len(data):
        kind, size = data[pos:pos + 4].decode(), struct.unpack(">I", data[pos + 4:pos + 8])[0]
        assert data[pos + 8:pos + 16] == b"\x89PNG\r\n\x1a\n"
        kinds.append(kind)
        pos += size
    assert kinds == [k for k, _ in generate_icons.ICNS_TYPES]
    assert os.path.isfile(generate_icons.ICNS_PATH)               # quello usato da soundtext.spec
