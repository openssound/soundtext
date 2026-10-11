"""Opzioni comuni per i QFileDialog dell'applicazione.

Su Windows e macOS si usa il dialogo nativo. Su Windows quello di Qt non
mostra Accesso rapido, OneDrive, raccolte e unita' di rete, e quindi non
elenca tutti i file e le cartelle; su macOS prende il tema scuro dell'app ed
e' poco leggibile, mentre il pannello del Finder segue l'aspetto del sistema
e ha la barra laterale (iCloud, Download, dischi). Su Linux resta il dialogo
di Qt, uniforme fra i desktop.
"""
import sys

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
