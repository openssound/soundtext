"""
Cronologia delle modifiche al progetto (Annulla/Ripeti), unica per tutta
l'app: testo delle tracce, mixer, tracce aggiunte/rimosse, generazione,
import, pattern, box della vista Struttura brano...

Invece di chiedere a ogni azione di registrare "cosa sta per cambiare" (e
dimenticarsene in qualche punto), la cronologia tiene una copia dell'ultimo
stato confermato e riceve lo stato nuovo DOPO ogni modifica (record): se e'
diverso, la copia precedente diventa un passo annullabile. Basta quindi che
ogni modifica passi da un unico punto (gui MainWindow._mark_dirty).

Le modifiche a raffica dello stesso tipo (digitazione nella stessa traccia,
trascinamento di uno slider) si fondono in un solo passo se arrivano a
breve distanza l'una dall'altra (merge_key + merge_seconds), come fanno gli
editor di testo con le parole digitate.
"""

import copy
import time
from typing import List, Optional, Tuple

from .model import Project

# (progetto, traccia selezionata in quel momento)
State = Tuple[Project, Optional[str]]


class ProjectHistory:
    def __init__(self, limit: int = 100, merge_seconds: float = 1.5, clock=time.monotonic):
        self._limit = limit
        self._merge_seconds = merge_seconds
        self._clock = clock
        self._undo: List[State] = []
        self._redo: List[State] = []
        self._committed: Optional[State] = None
        self._last_merge_key = None
        self._last_time = 0.0

    def reset(self, project: Project, current_track: Optional[str] = None):
        """Nuovo punto di partenza (progetto aperto/creato): niente da annullare."""
        self._undo.clear()
        self._redo.clear()
        self._committed = (copy.deepcopy(project), current_track)
        self._last_merge_key = None

    def record(self, project: Project, current_track: Optional[str] = None,
               merge_key: Optional[str] = None) -> bool:
        """Da chiamare DOPO una modifica: ritorna True se e' diventata un
        passo annullabile (nuovo o fuso nel precedente), False se il
        progetto non era davvero cambiato."""
        if self._committed is None:
            self.reset(project, current_track)
            return False
        if project == self._committed[0]:
            return False
        now = self._clock()
        merge = (merge_key is not None and merge_key == self._last_merge_key
                 and now - self._last_time <= self._merge_seconds and self._undo)
        if not merge:
            # Lo stato "prima" ricorda la traccia selezionata al momento
            # della modifica, cosi' annullando si torna a vederla.
            before_project, _ = self._committed
            self._undo.append((before_project, current_track))
            del self._undo[:-self._limit]
        self._redo.clear()
        self._committed = (copy.deepcopy(project), current_track)
        self._last_merge_key = merge_key
        self._last_time = now
        return True

    def can_undo(self) -> bool:
        return bool(self._undo)

    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo(self) -> Optional[State]:
        """Stato precedente (una copia da usare come nuovo progetto), o None."""
        if not self._undo:
            return None
        self._redo.append(self._committed)
        self._committed = self._undo.pop()
        self._last_merge_key = None
        return self._copy(self._committed)

    def redo(self) -> Optional[State]:
        if not self._redo:
            return None
        self._undo.append(self._committed)
        self._committed = self._redo.pop()
        self._last_merge_key = None
        return self._copy(self._committed)

    @staticmethod
    def _copy(state: State) -> State:
        project, track = state
        return copy.deepcopy(project), track
