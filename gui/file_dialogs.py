"""Opzioni comuni per i QFileDialog dell'applicazione.

Su Windows e macOS si usa il dialogo nativo. Su Windows quello di Qt non
mostra Accesso rapido, OneDrive, raccolte e unita' di rete, e quindi non
elenca tutti i file e le cartelle; su macOS prende il tema scuro dell'app ed
e' poco leggibile, mentre il pannello del Finder segue l'aspetto del sistema
e ha la barra laterale (iCloud, Download, dischi). Su Linux resta il dialogo
di Qt, uniforme fra i desktop.
"""
import sys

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QFileDialog


def file_dialog_options() -> QFileDialog.Option:
    if sys.platform in ("win32", "darwin"):
        return QFileDialog.Option(0)
    return QFileDialog.Option.DontUseNativeDialog


def repair_sidebar_shortcuts(extra_dirs=()):
    """Collegamenti del pannello a sinistra del dialogo di Qt (Linux), che Qt
    salva in ~/.config/QtProject.conf e condivide fra tutti i programmi Qt.
    Quelli verso cartelle che non esistono (per esempio una configurazione
    copiata da un altro utente: /home/<altro>/Documenti) si cliccavano senza
    mostrare niente a destra: si tolgono, e se non ne resta nessuno si mettono
    le cartelle dell'utente (Home, Scrivania, Documenti, Musica, Scaricati) e
    quelle di SoundText (extra_dirs). Su Windows e macOS il dialogo e' quello
    di sistema e non serve."""
    if sys.platform in ("win32", "darwin"):
        return
    import os
    from PySide6.QtCore import QSettings, QStandardPaths, QUrl

    store = QSettings(QSettings.Scope.UserScope, "QtProject")
    saved = store.value("FileDialog/shortcuts")
    if saved is None:
        return                      # mai aperto: Qt usa gia' le cartelle predefinite
    if isinstance(saved, str):
        saved = [saved]

    def usable(url: str) -> bool:
        local = QUrl(url).toLocalFile()
        return not local or os.path.isdir(local)     # i non-file (smb://...) restano

    kept = [url for url in saved if usable(url)]
    if not kept:
        locations = (QStandardPaths.StandardLocation.HomeLocation,
                     QStandardPaths.StandardLocation.DesktopLocation,
                     QStandardPaths.StandardLocation.DocumentsLocation,
                     QStandardPaths.StandardLocation.MusicLocation,
                     QStandardPaths.StandardLocation.DownloadLocation)
        dirs = [QStandardPaths.writableLocation(loc) for loc in locations] + list(extra_dirs)
        for path in dirs:
            url = QUrl.fromLocalFile(path).toString()
            if path and os.path.isdir(path) and url not in kept:
                kept.append(url)
    if kept != list(saved):
        store.setValue("FileDialog/shortcuts", kept)


# Dimensione del dialogo di Qt la prima volta: con quella predefinita (circa
# 600x430) si vedeva solo la colonna Nome, Tipo e Data restavano tagliate.
DEFAULT_SIZE = (960, 600)


class _FileDialogSizer(QObject):
    """Da' a ogni dialogo file di Qt la dimensione dell'ultima volta (o
    DEFAULT_SIZE), entro lo schermo, e lo centra sulla finestra da cui e' stato
    aperto; alla chiusura ne ricorda la dimensione. Lavora sugli eventi, cosi'
    vale anche per i dialoghi creati da QFileDialog.getOpenFileName & co."""

    def eventFilter(self, obj, event):
        if isinstance(obj, QFileDialog):
            if event.type() == QEvent.Type.Show:
                self._fit(obj)
            elif event.type() == QEvent.Type.Hide:
                from core import settings
                settings.set_file_dialog_size(obj.width(), obj.height())
        return False

    @staticmethod
    def _fit(dialog):
        from core import settings
        width, height = settings.get_file_dialog_size() or DEFAULT_SIZE
        parent = dialog.parentWidget()
        screen = (parent.screen() if parent is not None else None) or dialog.screen()
        area = screen.availableGeometry()
        width = min(width, int(area.width() * 0.9))
        height = min(height, int(area.height() * 0.9))
        dialog.resize(width, height)
        center = parent.window().frameGeometry().center() if parent is not None else area.center()
        frame = dialog.frameGeometry()
        frame.moveCenter(center)
        x = max(area.left(), min(frame.left(), area.right() - frame.width()))
        y = max(area.top(), min(frame.top(), area.bottom() - frame.height()))
        dialog.move(x, y)


def install_file_dialog_sizing(app):
    """Su Linux (dialogo di Qt) attiva _FileDialogSizer per tutta l'applicazione."""
    if sys.platform in ("win32", "darwin"):
        return
    app._file_dialog_sizer = _FileDialogSizer(app)       # resta vivo quanto l'app
    app.installEventFilter(app._file_dialog_sizer)
