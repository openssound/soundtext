"""
Esegue una funzione qualsiasi del core in un QThread separato, cosi' la
finestra principale non si blocca mentre il lavoro procede (riorganizzazione
pattern, import audio, generazione con IA...). Il progress_callback (quando
pass_progress=True, il default) gira nel thread worker ed emette un segnale
Qt, mai una chiamata diretta a widget dal thread secondario.
"""

import logging

from PySide6.QtCore import QThread, Signal


class Worker(QThread):
    progress = Signal(float)      # 0.0 - 1.0, emesso solo se pass_progress=True
    finished_ok = Signal(object)   # risultato (di qualunque tipo) della funzione core
    finished_error = Signal(str)

    def __init__(self, func, *args, pass_progress: bool = True, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.pass_progress = pass_progress

    def run(self):
        try:
            if self.pass_progress:
                result = self.func(*self.args, progress_callback=self.progress.emit, **self.kwargs)
            else:
                result = self.func(*self.args, **self.kwargs)
            self.finished_ok.emit(result)
        except Exception as e:
            logging.getLogger(__name__).warning("Operazione in background fallita", exc_info=True)
            self.finished_error.emit(str(e))


def run_with_wait(parent, label: str, func, *args, **kwargs):
    """Esegue func(*args, **kwargs) in un Worker e ne ritorna il risultato,
    lasciando che la finestra si ridisegni intanto (un'analisi di qualche
    secondo non la blocca); dopo WAIT_DIALOG_MS mostra una finestra
    d'attesa con 'label'. Un errore della funzione diventa RuntimeError con
    il suo messaggio."""
    from PySide6.QtCore import QEventLoop, Qt
    from PySide6.QtWidgets import QProgressDialog
    outcome = {}
    loop = QEventLoop()
    worker = Worker(func, *args, pass_progress=False, **kwargs)
    worker.finished_ok.connect(lambda result: (outcome.__setitem__("ok", result), loop.quit()))
    worker.finished_error.connect(lambda message: (outcome.__setitem__("error", message), loop.quit()))
    dialog = QProgressDialog(label, None, 0, 0, parent)
    dialog.setWindowModality(Qt.WindowModal)
    dialog.setMinimumDuration(WAIT_DIALOG_MS)
    dialog.setCancelButton(None)
    worker.start()
    if "ok" not in outcome and "error" not in outcome:
        loop.exec()
    worker.wait()
    dialog.close()
    if "error" in outcome:
        raise RuntimeError(outcome["error"])
    return outcome.get("ok")


WAIT_DIALOG_MS = 400
