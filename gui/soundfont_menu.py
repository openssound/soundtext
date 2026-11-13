"""
I comandi del menu Suoni -> SoundFont e la proposta di scaricarne uno.

La finestra principale possiede un SoundFontMenu (MainWindow.soundfont):
choose e reset fissano o tolgono il SoundFont scelto a mano (core.settings),
show_info dice quale si sta usando, offer_download (chiamata da main.py
all'avvio) propone "Scarica e installa" se non se ne trova nessuno.
"""

from PySide6.QtWidgets import QFileDialog, QMessageBox

from core import settings as app_settings
from core.i18n import tr
from .file_dialogs import file_dialog_options


class SoundFontMenu:
    def __init__(self, window):
        self.window = window

    def choose(self):
        from core.project_io import ensure_soundfonts_dir
        window = self.window
        path, _ = QFileDialog.getOpenFileName(window, tr("Scegli file SoundFont"), ensure_soundfonts_dir(),
                                              tr("SoundFont (*.sf2 *.sf3)"),
                                              options=file_dialog_options())
        if not path:
            return
        app_settings.set_soundfont_path(path)
        window.statusBar().showMessage(tr("SoundFont impostato: {path}", path=path), 6000)
        QMessageBox.information(window, tr("SoundFont impostato"),
                                tr("Verra' usato per la riproduzione:\n{path}", path=path))

    def reset(self):
        app_settings.clear_soundfont_path()
        self.window.statusBar().showMessage(tr("Rilevamento automatico del SoundFont ripristinato."), 4000)

    def show_info(self):
        from core.playback import get_active_soundfont_info, describe_playback_engine
        path, is_manual = get_active_soundfont_info()
        if path:
            origin = tr("impostato manualmente") if is_manual else tr("rilevato automaticamente")
            QMessageBox.information(
                self.window, tr("SoundFont in uso"),
                tr("{path}\n({origin})\n\nMotore di riproduzione: {0}", describe_playback_engine(), path=path, origin=origin)
            )
        else:
            self._ask_download()

    def offer_download(self):
        """All'avvio (main.py): SoundText non include un SoundFont, e senza
        nessuno non suona; se non ne trova, propone di scaricarlo."""
        from core.playback import _find_soundfont
        if not _find_soundfont():
            self._ask_download()

    def _ask_download(self):
        answer = QMessageBox.question(
            self.window, tr("Nessun SoundFont trovato"),
            tr("Per suonare, SoundText ha bisogno di un SoundFont General MIDI (.sf2 o .sf3), e non ne "
               "ha trovato nessuno.\n\nVuoi scaricare FluidR3 GM (gratuito, licenza MIT, circa 150 MB)? "
               "Si apre \"Scarica e installa\", dove ci sono anche altri SoundFont.\n\n"
               "Se ne hai gia' uno, indicalo con Suoni → SoundFont → Scegli SoundFont (.sf2/.sf3)..."))
        if answer == QMessageBox.Yes:
            self.window.open_download_dialog(preselect=["sf-fluidr3"])
