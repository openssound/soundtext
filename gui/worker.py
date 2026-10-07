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
