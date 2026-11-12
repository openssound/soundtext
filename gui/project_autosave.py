"""
Il salvataggio automatico della finestra principale e il recupero dopo una
chiusura anomala.

La finestra possiede un ProjectAutosave (MainWindow.autosave): mentre ci sono
modifiche non salvate, ogni AUTOSAVE_INTERVAL_S secondi ne scrive una copia di
recupero (core.autosave), che al prossimo avvio si puo' recuperare se
SoundText non si e' chiuso normalmente (offer_recovery, chiamata da main.py).
Il file del progetto non viene toccato.

generation conta le modifiche (la finestra chiama changed() da _mark_dirty):
la copia si riscrive solo se ce ne sono di nuove. Lo usa anche la vista
Partitura per sapere se il brano e' cambiato.
"""

import os
import time

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox

from core.autosave import AUTOSAVE_INTERVAL_S, RecoverySession, find_recoverable
from core.i18n import tr


class ProjectAutosave:
    def __init__(self, window):
        self.window = window
        self.session = RecoverySession()
        self.generation = 0             # modifiche dall'avvio
        self._saved_generation = 0      # quelle gia' nella copia di recupero
        self._timer = QTimer(window)
        self._timer.setInterval(AUTOSAVE_INTERVAL_S * 1000)
        self._timer.timeout.connect(self.save_now)
        self._timer.start()

    def changed(self):
        """Il progetto e' stato modificato."""
        self.generation += 1

    def save_now(self) -> bool:
        """Scrive la copia di recupero se ci sono modifiche non salvate nuove
        rispetto all'ultima copia; True se l'ha scritta."""
        window = self.window
        if not window._dirty or self.generation == self._saved_generation:
            return False
        if not self.session.save(window.project, window.current_path):
            return False
        self._saved_generation = self.generation
        return True

    def clear_copy(self):
        """Progetto salvato o sostituito: la copia di recupero non serve piu'."""
        self.session.clear()
        self._saved_generation = self.generation

    def close(self):
        """Chiusura normale della finestra: la copia di recupero si toglie."""
        self._timer.stop()
        self.session.close()

    # ------------------------------------------------------------ recupero

    def offer_recovery(self):
        """All'avvio: se una sessione precedente si e' chiusa male lasciando
        modifiche non salvate, propone di recuperarle (la piu' recente; le
        altre al prossimo avvio)."""
        candidates = find_recoverable()
        if not candidates:
            return
        cand = candidates[0]
        when = time.strftime("%d/%m/%Y %H:%M", time.localtime(cand.saved_at))
        name = cand.project_name or tr("Nuovo progetto")
        if cand.original_path:
            where = tr("File del progetto: {path}", path=cand.original_path)
        else:
            where = tr("Il progetto non era mai stato salvato.")
        box = QMessageBox(self.window)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle(tr("Recupero del progetto"))
        box.setText(tr("L'ultima volta SoundText non si è chiuso normalmente."))
        box.setInformativeText(
            tr("C'è una copia di recupero del progetto «{name}» con le modifiche non salvate "
               "(salvata automaticamente il {when}).\n{where}\n\nVuoi recuperarla?",
               name=name, when=when, where=where))
        recover_btn = box.addButton(tr("Recupera"), QMessageBox.AcceptRole)
        discard_btn = box.addButton(tr("Elimina la copia"), QMessageBox.DestructiveRole)
        box.addButton(tr("Decidi dopo"), QMessageBox.RejectRole)
        box.setDefaultButton(recover_btn)
        box.exec()
        clicked = box.clickedButton()
        if clicked is discard_btn:
            cand.discard()
        elif clicked is recover_btn:
            self.recover(cand)

    def recover(self, cand) -> bool:
        """Apre la copia di recupero cand al posto del progetto corrente,
        come progetto con modifiche non salvate (Salva scrive sul file
        originale, se c'era)."""
        window = self.window
        if not window._confirm_discard_unsaved():
            return False
        try:
            project = cand.load()
        except Exception as e:
            QMessageBox.critical(window, tr("Recupero del progetto"),
                                 tr("La copia di recupero non si può aprire:\n{e}", e=e))
            return False
        original = cand.original_path if cand.original_path and os.path.isdir(
            os.path.dirname(cand.original_path)) else None
        title = os.path.basename(original) if original else (project.name or tr("Nuovo progetto"))
        window._replace_project(project, path=original, title=tr("{title} (recuperato)", title=title),
                                status_msg=tr("Progetto recuperato: salvalo per conservare le modifiche."),
                                status_timeout=10000)
        cand.discard()
        # Recuperato ma non ancora salvato: resta "modificato", e la copia
        # passa subito a questa sessione (se si chiudesse male di nuovo).
        window._dirty = True
        self.changed()
        self.save_now()
        return True
