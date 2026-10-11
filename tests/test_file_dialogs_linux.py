"""Dialogo file di Qt su Linux (gui.file_dialogs).

- I collegamenti del pannello a sinistra verso cartelle inesistenti (es.
  /home/<altro utente>/Documenti) si cliccavano senza mostrare niente
  (repair_sidebar_shortcuts).
- Il dialogo si apriva piccolo, con Tipo e Data tagliate
  (install_file_dialog_sizing).
"""

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


def _show_dialog():
    from gui.file_dialogs import install_file_dialog_sizing
    if not hasattr(app, "_file_dialog_sizer"):
        install_file_dialog_sizing(app)
    from PySide6.QtWidgets import QFileDialog
    d = QFileDialog(None, "Apri progetto")
    d.setOption(QFileDialog.Option.DontUseNativeDialog)
    d.show()
    return d


def test_dialog_opens_large_and_remembers_size():
    from core import settings
    from gui.file_dialogs import DEFAULT_SIZE
    settings._load().pop("file_dialog_size", None)
    area = app.primaryScreen().availableGeometry()
    d = _show_dialog()
    assert d.width() == min(DEFAULT_SIZE[0], int(area.width() * 0.9))
    assert d.height() == min(DEFAULT_SIZE[1], int(area.height() * 0.9))
    d.resize(700, 500)
    d.hide()
    assert settings.get_file_dialog_size() == (700, 500)
    assert _show_dialog().size().toTuple() == (700, 500)


def test_dialog_never_larger_than_screen():
    from core import settings
    settings.set_file_dialog_size(10000, 10000)
    area = app.primaryScreen().availableGeometry()
    d = _show_dialog()
    assert d.width() <= area.width() and d.height() <= area.height()
