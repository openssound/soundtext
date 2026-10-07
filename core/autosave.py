"""
Salvataggio automatico per il recupero dopo una chiusura anomala (crash,
blocco, computer spento): mentre il progetto ha modifiche non salvate,
SoundText ne scrive a intervalli una copia di recupero nella cartella
'recupero/' della configurazione (core.settings.CONFIG_DIR). Il file del
progetto non viene mai toccato: salvare resta una scelta dell'utente.

Ogni finestra di SoundText aperta ha la sua sessione di recupero
(RecoverySession): un file .st (percorsi assoluti, cosi' si apre da
qualunque cartella), un .json con le informazioni per chiedere all'utente
(progetto, file originale, ora) e un file di blocco (QLockFile) tenuto
finche' la sessione e' viva. Alla chiusura normale, al salvataggio e
all'apertura di un altro progetto la copia viene tolta. Una copia il cui
blocco e' libero (il programma che la scriveva non c'e' piu') e'
recuperabile: la si propone al prossimo avvio (find_recoverable).
"""

import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import List, Optional

from .settings import CONFIG_DIR

RECOVERY_DIR = os.path.join(CONFIG_DIR, "recupero")
# Secondi tra un salvataggio automatico e l'altro (solo se ci sono modifiche
# nuove da allora).
AUTOSAVE_INTERVAL_S = 60


def _write_atomic(path: str, text: str):
    """Scrive tutto o niente: un'interruzione a meta' lascia il file
    precedente intatto invece di uno troncato."""
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _lock_file(path: str):
    from PySide6.QtCore import QLockFile
    lock = QLockFile(path)
    lock.setStaleLockTime(0)       # vale solo se il processo che lo teneva non c'e' piu'
    return lock


@dataclass
class RecoveryCandidate:
    """Una copia di recupero lasciata da una sessione che non si e' chiusa
    normalmente."""
    session_id: str
    project_path: str          # il .st di recupero
    original_path: Optional[str]
    project_name: str
    saved_at: float

    def load(self):
        """Il progetto recuperato (core.model.Project)."""
        from .project_io import parse_project_text
        with open(self.project_path, encoding="utf-8") as f:
            text = f.read()
        return parse_project_text(text, project_name=self.project_name)

    def discard(self):
        _remove_session_files(self.session_id)


def _session_paths(session_id: str):
    base = os.path.join(RECOVERY_DIR, f"sessione_{session_id}")
    return base + ".st", base + ".json", base + ".lock"


def _remove_session_files(session_id: str):
    for path in _session_paths(session_id):
        try:
            os.remove(path)
        except OSError:
            pass


class RecoverySession:
    """La sessione di recupero di una finestra di SoundText."""

    def __init__(self):
        self.session_id = uuid.uuid4().hex[:12]
        self._st, self._meta, lock_path = _session_paths(self.session_id)
        self._lock = None
        self._lock_path = lock_path
        self.saved_at: Optional[float] = None

    def _ensure_lock(self) -> bool:
        if self._lock is None:
            os.makedirs(RECOVERY_DIR, exist_ok=True)
            self._lock = _lock_file(self._lock_path)
            if not self._lock.tryLock(0):
                self._lock = None
                return False
        return True

    def save(self, project, original_path: Optional[str]) -> bool:
        """Scrive la copia di recupero di project; False se non si puo'
        (cartella non scrivibile, disco pieno...): il programma continua,
        semplicemente senza rete di sicurezza per questo giro."""
        from .project_io import project_to_text
        try:
            if not self._ensure_lock():
                return False
            _write_atomic(self._st, project_to_text(project))   # percorsi assoluti
            meta = {"original_path": original_path, "project_name": project.name,
                    "saved_at": time.time()}
            _write_atomic(self._meta, json.dumps(meta, ensure_ascii=False))
        except OSError:
            return False
        self.saved_at = meta["saved_at"]
        return True

    def clear(self):
        """Toglie la copia (progetto salvato, chiuso o sostituito); la
        sessione resta utilizzabile per i salvataggi successivi."""
        for path in (self._st, self._meta):
            try:
                os.remove(path)
            except OSError:
                pass
        self.saved_at = None

    def close(self):
        """Fine della sessione (chiusura normale della finestra)."""
        self.clear()
        if self._lock is not None:
            self._lock.unlock()
            self._lock = None


def find_recoverable() -> List[RecoveryCandidate]:
    """Le copie lasciate da sessioni finite male (blocco libero), dalla piu'
    recente. Le sessioni ancora aperte (un'altra finestra di SoundText) non
    compaiono; le copie illeggibili vengono tolte."""
    if not os.path.isdir(RECOVERY_DIR):
        return []
    found = []
    for name in os.listdir(RECOVERY_DIR):
        if not (name.startswith("sessione_") and name.endswith(".json")):
            continue
        session_id = name[len("sessione_"):-len(".json")]
        st_path, meta_path, lock_path = _session_paths(session_id)
        lock = _lock_file(lock_path)
        if not lock.tryLock(0):
            continue                      # sessione viva in un'altra finestra
        lock.unlock()
        try:
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
            if not os.path.isfile(st_path):
                raise ValueError("copia mancante")
            found.append(RecoveryCandidate(
                session_id=session_id, project_path=st_path,
                original_path=meta.get("original_path") or None,
                project_name=str(meta.get("project_name") or ""),
                saved_at=float(meta.get("saved_at") or os.path.getmtime(st_path))))
        except (OSError, ValueError, TypeError):
            _remove_session_files(session_id)
    found.sort(key=lambda c: c.saved_at, reverse=True)
    return found
