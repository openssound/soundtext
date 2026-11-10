# Isola i test dalla configurazione dell'utente prima che qualunque test importi core.
import _config_isolation  # noqa: F401

import os

# Qt senza schermo in tutti i test (anche quelli che non creano finestre ma
# usano Qt Multimedia, vedi core.audio_decode)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest


@pytest.fixture(autouse=True)
def _reset_global_state():
    """Ogni test parte dallo stesso stato globale, qualunque test sia girato
    prima nello stesso processo (con pytest -n l'ordine cambia): lingua
    italiana e cache dei moduli audio vuote (vedi core.memory)."""
    import st_language
    from core import i18n
    from core.memory import clear_memory_caches
    # anche la lingua della libreria: un processo di test nuovo (pytest -n)
    # su un sistema in inglese (la CI) la sceglieva dal sistema
    if i18n._language != "it" or st_language.language() != "it":
        i18n.set_language("it")
    clear_memory_caches()
    yield


@pytest.fixture(autouse=True)
def _microphone_allowed(monkeypatch):
    """Il permesso del microfono di macOS (core.macos_permissions) vale come
    concesso: sul Mac della CI potrebbe risultare negato, e la finestra di
    registrazione aprirebbe l'avviso aspettando un clic. Il test
    dell'avviso lo cambia da se'."""
    from core import macos_permissions
    monkeypatch.setattr(macos_permissions, "microphone_blocked", lambda: False)


def _main_window_class():
    import sys
    module = sys.modules.get("gui.main_window")
    return getattr(module, "MainWindow", None) if module is not None else None


@pytest.fixture(autouse=True)
def _close_main_windows():
    """Chiude e distrugge le finestre principali create dal test: rimaste
    vive, ogni cambio di tema o di font le ridisegnerebbe tutte (i test di
    test_main_layout_gui.py passavano da 2 s a 40 s a fine suite). Le
    finestre gia' aperte prima (fixture di modulo) restano."""
    cls = _main_window_class()
    before = set()
    if cls is not None:
        from PySide6.QtWidgets import QApplication
        if QApplication.instance() is not None:
            before = {id(w) for w in QApplication.topLevelWidgets() if isinstance(w, cls)}
    yield
    cls = _main_window_class()
    if cls is None:
        return
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        return
    closed = False
    # la chiusura di una finestra spegne i processi dei plugin (closeEvent):
    # nei test li condividono tutte le finestre e le fixture di modulo, che
    # li ritroverebbero da riavviare (e i plugin da ricaricare)
    from core import plugins
    shutdown, plugins.shutdown = plugins.shutdown, lambda: None
    try:
        for window in QApplication.topLevelWidgets():
            if not isinstance(window, cls) or id(window) in before:
                continue
            window._dirty = False                   # niente domanda "Salvare le modifiche?"
            try:
                window.close()
            except RuntimeError:
                continue                            # gia' distrutta
            window.deleteLater()
            closed = True
    finally:
        plugins.shutdown = shutdown
    if closed:
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        app.processEvents()


def pytest_sessionfinish(session, exitstatus):
    """Controllo: a fine sessione restano poche finestre principali vive."""
    cls = _main_window_class()
    if cls is None:
        return
    from PySide6.QtWidgets import QApplication
    if QApplication.instance() is None:
        return
    alive = [w for w in QApplication.topLevelWidgets() if isinstance(w, cls)]
    if len(alive) >= 10:
        import warnings
        warnings.warn(f"{len(alive)} finestre principali ancora vive a fine test")
