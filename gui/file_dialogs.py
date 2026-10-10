"""Opzioni comuni per i QFileDialog dell'applicazione.

Su Windows si usa il dialogo nativo: quello di Qt non mostra Accesso rapido,
OneDrive, raccolte e unità di rete, e quindi non elenca tutti i file e le
cartelle. Altrove resta il dialogo di Qt, uniforme fra i desktop Linux.
"""
import sys

from PySide6.QtWidgets import QFileDialog


def file_dialog_options() -> QFileDialog.Option:
    if sys.platform == "win32":
        return QFileDialog.Option(0)
    return QFileDialog.Option.DontUseNativeDialog
