"""
La sezione A-B da ripetere durante l'ascolto (menu Riproduzione -> Loop).

La finestra principale possiede un LoopRegion (MainWindow.loop): i comandi
del menu fissano A e B sulla posizione d'ascolto, active() dice la sezione
che si ripete davvero (A e B impostati, B dopo A, "Ripeti la sezione A-B"
acceso) e changed() aggiorna l'azione del menu, la vista Struttura e, se si
sta suonando, il motore. Anche il pannello degli effetti la usa per far
ripetere il pezzo che si sta regolando (snapshot/set_region/restore).
"""

from core.i18n import tr
from core.tempo_map import seconds_for_beats


class LoopRegion:
    def __init__(self, window):
        self.window = window
        self.a = None       # beat di inizio, None finche' non si imposta
        self.b = None       # beat di fine

    @property
    def _action(self):
        return self.window.loop_action

    def complete(self) -> bool:
        return self.a is not None and self.b is not None

    def active(self):
        """(A, B) se la sezione si ripete, altrimenti None."""
        if self._action.isChecked() and self.complete() and self.b > self.a:
            return (self.a, self.b)
        return None

    # ------------------------------------------------------------ comandi del menu

    def set_start(self, beat: float):
        self.a = float(round(beat))
        if self.b is not None and self.b <= self.a:
            self.b = None
        self.changed()

    def set_end(self, beat: float):
        self.b = float(round(beat))
        if self.a is None:
            self.a = 0.0
        if self.b <= self.a:
            self.window.statusBar().showMessage(tr("La fine del loop (B) deve venire dopo l'inizio (A)."), 5000)
            self.b = None
        elif not self._action.isChecked():
            self._action.setChecked(True)  # impostare B e' l'intenzione di usare il loop
        self.changed()

    def clear(self):
        self.a = self.b = None
        self._action.setChecked(False)
        self.changed()

    # ------------------------------------------------------------ pannello degli effetti

    def snapshot(self):
        """Lo stato da rimettere con restore: (A, B, acceso)."""
        return (self.a, self.b, self._action.isChecked())

    def set_region(self, a: float, b: float):
        """Ripete subito la sezione [a, b)."""
        self.a, self.b = a, b
        self._action.setEnabled(True)
        self._action.setChecked(True)
        self.changed()

    def restore(self, saved):
        a, b, checked = saved
        self.a, self.b = a, b
        self._action.setChecked(bool(checked and a is not None and b is not None))
        self.changed()

    # ------------------------------------------------------------ aggiornamento

    def changed(self):
        """A, B o l'interruttore sono cambiati: menu, vista Struttura,
        motore (se si sta suonando) e barra di stato."""
        window, action = self.window, self._action
        complete = self.complete()
        action.setEnabled(complete)
        if not complete and action.isChecked():
            action.setChecked(False)
        active = self.active()
        window.arrangement_view.set_loop_region(
            (self.a, self.b) if complete else ((self.a, None) if self.a is not None else None),
            active=active is not None)
        status = window.statusBar()
        if window.playback.is_playing():
            from core.playback import streaming_available
            if streaming_available():
                tempo_map = window._playback_tempo_map
                window.playback.set_loop_seconds(None if active is None else (
                    seconds_for_beats(tempo_map, active[0]), seconds_for_beats(tempo_map, active[1])))
            elif active is not None:
                status.showMessage(
                    tr("Il loop richiede la libreria FluidSynth e sounddevice: con il motore di "
                    "riproduzione attuale il brano non verra' ripetuto."), 8000)
                return
        if active is not None:
            status.showMessage(tr("Loop attivo: beat {0:.0f} - {1:.0f}.", active[0], active[1]), 5000)
        elif self.a is not None:
            b = f"{self.b:.0f}" if self.b is not None else "?"
            status.showMessage(tr("Loop: A = {_loop_a_beat:.0f}, B = {b} (non attivo).", _loop_a_beat=self.a, b=b), 5000)
