"""
La finestra in cui si apre l'interfaccia grafica di un plugin CLAP
(clap.gui, vedi core.clap_host.ClapInstance.open_gui).

Il plugin non apre una finestra sua: disegna dentro una finestra che gli da'
l'host, e chiede all'host di chiamarlo a intervalli (i suoi timer) e quando
un descrittore di file e' pronto (su Linux la connessione a X11). Qui la
finestra e' un widget Qt, i timer li serve un QTimer e i descrittori dei
QSocketNotifier. run_editor() la mostra e torna quando viene chiusa.

Gira nel processo dei plugin (core.plugin_worker), non in SoundText: Qt si
importa solo qui dentro, quando serve.

Su Linux CLAP ha solo l'api X11: con Wayland Qt va avviato sul suo
backend X11 (xcb, cioe' XWayland), e per questo lo si chiede prima di creare
l'applicazione.
"""

import math
import os
import sys

from .clap_host import FD_ERROR, FD_READ, FD_WRITE, ClapError, gui_api
from .i18n import tr

IDLE_MS = 15


def _application():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        platform = os.environ.get("QT_QPA_PLATFORM", "")
        if sys.platform.startswith("linux") and (not platform or platform.startswith("wayland")):
            os.environ["QT_QPA_PLATFORM"] = "xcb"
        app = QApplication([sys.argv[0] if sys.argv else "soundtext"])
        app.setQuitOnLastWindowClosed(False)
    return app


def run_editor(inst, title: str = ""):
    """Apre l'interfaccia del plugin 'inst' (ClapInstance) in una finestra
    e aspetta che venga chiusa. Solleva ClapError se non si puo' aprire."""
    if gui_api() is None:
        raise ClapError(tr("per l'interfaccia dei plugin CLAP su Linux serve X11 (con Wayland: XWayland)"))
    from PySide6.QtCore import QEventLoop, QSocketNotifier, Qt, QTimer
    from PySide6.QtWidgets import QWidget

    app = _application()
    loop = QEventLoop()

    class EditorWindow(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle(title or inst.info.name)
            self.setAttribute(Qt.WA_NativeWindow)
            self.setAttribute(Qt.WA_DontCreateNativeAncestors)
            self.opened = False
            self.resizable = False
            self._notifiers = {}
            self._fds_version = None
            self._idle = QTimer(self)
            self._idle.setInterval(IDLE_MS)
            self._idle.timeout.connect(self._on_idle)
            self._resize_timer = QTimer(self)
            self._resize_timer.setSingleShot(True)
            self._resize_timer.setInterval(60)
            self._resize_timer.timeout.connect(self._apply_resize)

        # le misure di CLAP sono in pixel veri, quelle di Qt logiche (non su macOS)
        def _ratio(self) -> float:
            return 1.0 if sys.platform == "darwin" else (self.devicePixelRatioF() or 1.0)

        def _set_plugin_size(self, width: int, height: int):
            if width <= 0 or height <= 0:
                return
            w, h = math.ceil(width / self._ratio()), math.ceil(height / self._ratio())
            if self.resizable:
                self.resize(w, h)
            else:
                self.setFixedSize(w, h)

        def open(self):
            self.resize(640, 400)
            self.show()                    # la finestra deve esistere prima che il plugin ci entri
            app.processEvents()
            width, height = inst.open_gui(int(self.winId()), self._ratio(), self)
            self.opened = True
            self.resizable = inst.gui_resizable()
            self._set_plugin_size(width, height)
            self._idle.start()

        # -- chiamate del plugin (ClapInstance.gui_listener) --
        def request_resize(self, width: int, height: int) -> bool:
            self._set_plugin_size(width, height)
            return True

        def closed(self):
            QTimer.singleShot(0, self.close)

        # -- vita della finestra --
        def _on_idle(self):
            inst.idle()
            if inst.fds_version != self._fds_version:
                self._sync_notifiers()

        def _sync_notifiers(self):
            self._fds_version = inst.fds_version
            for notifier in self._notifiers.values():
                notifier.setEnabled(False)
                notifier.deleteLater()
            self._notifiers = {}
            kinds = ((FD_READ, QSocketNotifier.Read), (FD_WRITE, QSocketNotifier.Write),
                     (FD_ERROR, QSocketNotifier.Exception))
            for fd, flags in inst.fds.items():
                for flag, kind in kinds:
                    if flags & flag:
                        notifier = QSocketNotifier(fd, kind, self)
                        notifier.activated.connect(lambda *_a, fd=fd, flag=flag: inst.fd_event(fd, flag))
                        self._notifiers[(fd, flag)] = notifier

        def resizeEvent(self, event):
            super().resizeEvent(event)
            if self.opened and self.resizable:
                self._resize_timer.start()

        def _apply_resize(self):
            if not self.opened:
                return
            ratio = self._ratio()
            wanted = (round(self.width() * ratio), round(self.height() * ratio))
            got = inst.gui_resize(*wanted)
            if got != wanted and got[0] > 0 and got[1] > 0:
                self.resize(math.ceil(got[0] / ratio), math.ceil(got[1] / ratio))

        def closeEvent(self, event):
            self._idle.stop()
            self._resize_timer.stop()
            for notifier in self._notifiers.values():
                notifier.setEnabled(False)
            self._notifiers = {}
            if self.opened:
                self.opened = False
                inst.close_gui()
            super().closeEvent(event)
            loop.quit()

    window = EditorWindow()
    try:
        window.open()
    except Exception:
        window.close()
        window.deleteLater()
        raise
    window.raise_()
    window.activateWindow()
    loop.exec()
    window.deleteLater()
    app.processEvents()
