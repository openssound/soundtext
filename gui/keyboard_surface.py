"""
Superficie che riceve i tasti del dialogo "Suona con la tastiera" (vedi
gui.keyboard_play_dialog): distingue una vera pressione/rilascio
dall'autorepeat del sistema operativo e tiene il focus anche con Tab.
"""

import logging
import sys
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QWidget

from .keyboard_scancodes import canonical_key
from .weak_callback import WeakCallback

log = logging.getLogger("soundtext.keyboard")


def _queue_delay_ms(event):
    """Millisecondi trascorsi fra la pressione registrata dal sistema e la
    gestione dell'evento qui: solo su Windows, dove QKeyEvent.timestamp() e'
    GetMessageTime(), nella stessa base di GetTickCount(). None altrove (i
    timestamp X11/Wayland non sono confrontabili con un orologio locale)."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        return (ctypes.windll.kernel32.GetTickCount() - event.timestamp()) & 0xFFFFFFFF
    except Exception:
        return None

# Finestra di tolleranza (vedi KeySurface) tra il "rilascio" e la
# "pressione" successiva dello stesso tasto per riconoscerli come lo stesso
# ciclo di ripetizione automatica invece che due eventi distinti: molto piu'
# breve di un doppio tocco intenzionale (anche suonando veloce), ma
# abbastanza larga da assorbire la latenza di rete di una tastiera instradata
# via InputLeap/Synergy.
_REPEAT_GRACE_MS = 80


class _FrozenKeyEvent:
    """Copia minima (solo i campi che canonical_key() legge) di un
    QKeyEvent, sicura da trattenere oltre la sua gestione sincrona - a
    differenza del vero QKeyEvent di Qt, che invece non e' garantito restare
    valido dopo il ritorno di keyPressEvent/keyReleaseEvent. Usata solo per
    il rilascio differito, vedi KeySurface.keyReleaseEvent."""

    def __init__(self, event):
        self._key = event.key()
        self._native_scan_code = event.nativeScanCode()
        self._native_virtual_key = event.nativeVirtualKey() if hasattr(event, "nativeVirtualKey") else 0
        self._native_modifiers = event.nativeModifiers() if hasattr(event, "nativeModifiers") else 0

    def key(self):
        return self._key

    def nativeScanCode(self):
        return self._native_scan_code

    def nativeVirtualKey(self):
        return self._native_virtual_key

    def nativeModifiers(self):
        return self._native_modifiers


class KeySurface(QWidget):
    """Superficie che cattura la tastiera fisica come se fosse uno strumento:
    ogni pressione/rilascio tasto viene inoltrato al dialogo (con la chiave
    gia' risolta da canonical_key, invece dell'evento Qt grezzo), ignorando
    la ripetizione automatica del sistema operativo (altrimenti un tasto
    tenuto premuto genererebbe decine di note-on ravvicinate invece di UNA
    nota sostenuta) e senza lasciare che Tab sposti il focus altrove a meta'
    registrazione.

    event.isAutoRepeat() da solo non basta: e' affidabile con una tastiera
    fisica locale, ma una tastiera esterna instradata via rete (es.
    InputLeap/Synergy) spesso inietta, per ogni "tick" della ripetizione,
    una coppia rilascio+pressione ravvicinata ma del tutto genuina (senza il
    flag di ripetizione, e senza che il tasto fisico sia mai stato lasciato
    davvero) - indistinguibile a livello di singolo evento da un doppio
    tocco intenzionale. Il rilascio percio' non viene inoltrato subito: si
    aspetta _REPEAT_GRACE_MS per vedere se arriva una nuova pressione dello
    stesso tasto (che annulla il rilascio pendente, vedi keyPressEvent) prima
    di considerarlo un rilascio vero."""

    # Metodi del dialogo proprietario: a riferimento debole (vedi WeakCallback).
    _on_key_press = WeakCallback()
    _on_key_release = WeakCallback()

    def __init__(self, on_key_press, on_key_release, parent=None):
        super().__init__(parent)
        self._on_key_press = on_key_press
        self._on_key_release = on_key_release
        self.setFocusPolicy(Qt.StrongFocus)
        self._pressed_keys = set()       # canonical_key() dei tasti attualmente tenuti
        self._pending_release = {}        # canonical_key() -> QTimer di rilascio differito

    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return
        key = canonical_key(event)
        pending = self._pending_release.pop(key, None)
        if pending is not None:
            # Vedi keyReleaseEvent: era solo il "falso" rilascio di un ciclo
            # di ripetizione, la pressione e' arrivata in tempo - si annulla
            # il rilascio pendente, la nota resta tenuta senza ritriggerarla.
            pending.stop()
            pending.deleteLater()
            return
        if key in self._pressed_keys:
            return
        self._pressed_keys.add(key)
        callback = self._on_key_press
        if callback is None:      # dialogo proprietario gia' distrutto
            return
        started = time.perf_counter()
        callback(event)
        self._log_press_timing(event, started)

    def _log_press_timing(self, event, started):
        """Diagnostica del ritardo fra tasti premuti insieme (nel log): se
        l'intervallo dal tasto precedente e' gia' ampio secondo il sistema,
        il distacco nasce prima dell'app (tastiera/driver); se e' ampio solo
        lato app, i tasti hanno aspettato in coda (thread dell'interfaccia
        occupato); se entrambi sono piccoli ma le note si sentono separate,
        la causa e' nel percorso audio."""
        now = time.perf_counter()
        os_ts = event.timestamp()
        prev = getattr(self, "_last_press", None)
        self._last_press = (os_ts, started)
        if prev is None:
            return
        os_gap = (os_ts - prev[0]) & 0xFFFFFFFF
        if os_gap > 1000:
            return  # tasti non ravvicinati: niente da diagnosticare
        log.info("Tasto: +%d ms dal precedente (sistema), +%.0f ms (app), attesa in coda %s ms, gestione %.1f ms",
                 os_gap, (started - prev[1]) * 1000, _queue_delay_ms(event), (now - started) * 1000)

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return
        key = canonical_key(event)
        if key not in self._pressed_keys or key in self._pending_release:
            return
        frozen = _FrozenKeyEvent(event)
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda k=key, e=frozen: self._finalize_release(k, e))
        self._pending_release[key] = timer
        timer.start(_REPEAT_GRACE_MS)

    def _finalize_release(self, key, event):
        timer = self._pending_release.pop(key, None)
        if timer is not None:
            timer.deleteLater()
        self._pressed_keys.discard(key)
        callback = self._on_key_release
        if callback is not None:
            callback(event)

    def focusNextPrevChild(self, next_child):
        # Impedisce a Tab/Maiusc+Tab di sottrarre il focus alla superficie
        # (altrimenti i tasti successivi non arriverebbero piu' qui).
        return False
