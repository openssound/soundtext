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
