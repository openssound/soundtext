"""Collegamenti del pannello a sinistra del dialogo file di Qt su Linux
(gui.file_dialogs.repair_sidebar_shortcuts): quelli verso cartelle inesistenti
(es. /home/<altro utente>/Documenti) si cliccavano senza mostrare niente."""

import os
import sys

import pytest
from PySide6.QtCore import QSettings, QUrl
from PySide6.QtWidgets import QApplication

from gui.file_dialogs import repair_sidebar_shortcuts

app = QApplication.instance() or QApplication([])

pytestmark = pytest.mark.skipif(sys.platform in ("win32", "darwin"),
                                reason="su Windows e macOS il dialogo e' quello di sistema")


@pytest.fixture
def qt_settings(tmp_path):
    QSettings.setPath(QSettings.Format.NativeFormat, QSettings.Scope.UserScope, str(tmp_path))
    yield lambda: QSettings(QSettings.Scope.UserScope, "QtProject")
    QSettings.setPath(QSettings.Format.NativeFormat, QSettings.Scope.UserScope,
                      os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"))


def _shortcuts(settings):
    value = settings.value("FileDialog/shortcuts")
    return [value] if isinstance(value, str) else value


def _url(path):
    return QUrl.fromLocalFile(str(path)).toString()


def test_missing_folders_are_dropped_and_valid_ones_kept(qt_settings, tmp_path):
    good = tmp_path / "brani"
    good.mkdir()
    qt_settings().setValue("FileDialog/shortcuts", [_url("/home/nessuno/Documenti"), _url(good)])
    repair_sidebar_shortcuts()
    assert _shortcuts(qt_settings()) == [_url(good)]


def test_all_missing_replaced_by_real_folders(qt_settings, tmp_path):
    songs = tmp_path / "songs"
    songs.mkdir()
    qt_settings().setValue("FileDialog/shortcuts", [_url("/home/nessuno"), _url("/home/nessuno/Musica")])
    repair_sidebar_shortcuts([str(songs)])
    shortcuts = _shortcuts(qt_settings())
    assert _url(os.path.expanduser("~")) in shortcuts
    assert _url(songs) in shortcuts
    assert all(os.path.isdir(QUrl(u).toLocalFile()) for u in shortcuts)


def test_untouched_when_never_saved(qt_settings):
    repair_sidebar_shortcuts(["/tmp"])
    assert qt_settings().value("FileDialog/shortcuts") is None
