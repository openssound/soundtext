"""
Salvataggio automatico e recupero dopo una chiusura anomala (core.autosave,
gui.main_window_project): la copia di recupero si scrive solo con modifiche
nuove, sparisce al salvataggio, alla chiusura normale e all'apertura di un
altro progetto, resta dopo un crash vero (processo terminato) e al riavvio
si recupera come progetto modificato; una sessione ancora aperta non viene
proposta. Il salvataggio normale e' "tutto o niente".
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import subprocess
import sys
import textwrap

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PySide6.QtWidgets import QApplication, QMessageBox

from core import autosave, project_io
from core.model import AudioClip, Project
from core.project_io import load_project_file, save_project_file

_app = QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _clean_recovery_dir():
    for c in autosave.find_recoverable():
        c.discard()
    yield
    for c in autosave.find_recoverable():
        c.discard()


def _project(name="Canzone"):
    p = Project(name=name, tempo_bpm=96)
    p.add_track("Piano", "Piano", "4: c*4 e*4 g*4 c*5")
    return p


def _crash_session(project, original_path):
    """Una sessione che ha salvato la copia e poi e' 'morta' (blocco libero)."""
    s = autosave.RecoverySession()
    assert s.save(project, original_path)
    s._lock.unlock()
    s._lock = None
    return s


# --------------------------------------------------------------- core.autosave

def test_copy_round_trip_with_absolute_audio_paths(tmp_path):
    p = _project()
    voce = p.add_audio_track("Voce")
    take = str(tmp_path / "audio" / "take.wav")
    voce.audio_clips.append(AudioClip("Strofa", take, 4.0))
    _crash_session(p, str(tmp_path / "canzone.st"))
    [cand] = autosave.find_recoverable()
    assert cand.original_path == str(tmp_path / "canzone.st")
    assert cand.project_name == "Canzone"
    q = cand.load()
    assert q.tempo_bpm == 96
    assert q.tracks[0].text == "4: c*4 e*4 g*4 c*5"
    assert q.tracks[1].audio_clips[0].file == take         # si apre da qualunque cartella


def test_live_session_is_not_offered_and_clear_removes_the_copy():
    s = autosave.RecoverySession()
    assert s.save(_project(), None)
    assert autosave.find_recoverable() == []               # un'altra finestra e' ancora aperta
    s.clear()
    s._lock.unlock()
    s._lock = None
    assert autosave.find_recoverable() == []
    s.close()


def test_a_real_crash_leaves_a_recoverable_copy():
    script = textwrap.dedent(f"""
        import os, sys
        sys.path.insert(0, {ROOT!r})
        from PySide6.QtCore import QCoreApplication
        app = QCoreApplication([])
        from core import autosave
        from core.model import Project
        p = Project(name="Crash")
        p.add_track("Basso", "Bass", "4: e*2")
        assert autosave.RecoverySession().save(p, None)
        os._exit(1)                                        # niente chiusura normale
    """)
    subprocess.run([sys.executable, "-c", script], check=False, timeout=60)
    [cand] = autosave.find_recoverable()
    assert cand.project_name == "Crash" and cand.original_path is None
    assert cand.load().tracks[0].text == "4: e*2"


def test_broken_copies_are_removed():
    os.makedirs(autosave.RECOVERY_DIR, exist_ok=True)
    with open(os.path.join(autosave.RECOVERY_DIR, "sessione_rotta.json"), "w") as f:
        f.write("{non json")
    assert autosave.find_recoverable() == []
    assert not os.path.exists(os.path.join(autosave.RECOVERY_DIR, "sessione_rotta.json"))


def test_save_is_all_or_nothing(tmp_path, monkeypatch):
    path = str(tmp_path / "brano.st")
    save_project_file(_project(), path)
    before = open(path, encoding="utf-8").read()

    def broken_replace(src, dst):
        raise OSError("disco pieno")
    monkeypatch.setattr(project_io.os, "replace", broken_replace)
    changed = _project()
    changed.tracks[0].text = "4: d*4"
    with pytest.raises(OSError):
        save_project_file(changed, path)
    assert open(path, encoding="utf-8").read() == before     # il vecchio file e' intatto
    assert os.listdir(tmp_path) == ["brano.st"]               # niente file temporanei
    monkeypatch.undo()
    save_project_file(changed, path)
    assert load_project_file(path).tracks[0].text == "4: d*4"


# --------------------------------------------------------------- finestra principale

def _window():
    from gui.main_window import MainWindow
    w = MainWindow()
    w.project.add_track("Piano", "Piano", "4: c*4")
    w.history.reset(w.project)
    w.refresh_mixer()
    return w


def _close_discarding(w, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Discard)
    w.close()


def test_window_writes_the_copy_only_with_new_changes(tmp_path, monkeypatch):
    w = _window()
    assert not w.autosave_now()                               # niente da salvare
    w.project.tracks[0].text = "4: d*4"
    w._mark_dirty()
    assert w.autosave_now()
    assert not w.autosave_now()                               # nessuna modifica nuova
    assert os.path.exists(w._recovery._st)
    w.current_path = str(tmp_path / "salvato.st")
    w.save_project()
    assert not os.path.exists(w._recovery._st)                # salvato: copia tolta
    w.project.tracks[0].text = "4: e*4"
    w._mark_dirty()
    assert w.autosave_now()
    _close_discarding(w, monkeypatch)
    assert not os.path.exists(w._recovery._st)                # chiusura normale: copia tolta
    assert autosave.find_recoverable() == []


def test_new_project_removes_the_copy(monkeypatch):
    w = _window()
    w._mark_dirty()
    assert w.autosave_now()
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Discard)
    w.new_project()
    assert not os.path.exists(w._recovery._st)
    w.close()


def test_recover_project_opens_it_as_modified(tmp_path, monkeypatch):
    original = str(tmp_path / "canzone.st")
    save_project_file(_project(), original)
    crashed = _project()
    crashed.tracks[0].text = "4: a*4 b*4"                     # modifica mai salvata
    _crash_session(crashed, original)
    w = _window()
    [cand] = autosave.find_recoverable()
    assert w.recover_project(cand)
    assert w.project.tracks[0].text == "4: a*4 b*4"
    assert w.current_path == original                          # Salva scrive sul file originale
    assert w._dirty and "(recuperato)" in w.windowTitle()
    assert autosave.find_recoverable() == []                   # la vecchia copia e' tolta...
    assert os.path.exists(w._recovery._st)                     # ...e la nuova e' di questa sessione
    w.save_project()
    assert load_project_file(original).tracks[0].text == "4: a*4 b*4"
    _close_discarding(w, monkeypatch)


@pytest.mark.parametrize("choice,left", [("Elimina la copia", 0), ("Decidi dopo", 1)])
def test_offer_recovery_buttons(choice, left, monkeypatch):
    _crash_session(_project("Da decidere"), None)
    w = _window()
    shown = []
    monkeypatch.setattr(QMessageBox, "exec", lambda self: shown.append(self.informativeText()) or 0)
    monkeypatch.setattr(QMessageBox, "clickedButton",
                        lambda self: next(b for b in self.buttons() if b.text() == choice))
    w.offer_recovery()
    assert "Da decidere" in shown[0] and "mai stato salvato" in shown[0]
    assert len(autosave.find_recoverable()) == left
    assert w.project.tracks[0].text == "4: c*4"                # progetto corrente non toccato
    _close_discarding(w, monkeypatch)


def test_offer_recovery_recovers(monkeypatch):
    _crash_session(_project("Da recuperare"), None)
    w = _window()
    monkeypatch.setattr(QMessageBox, "exec", lambda self: 0)
    monkeypatch.setattr(QMessageBox, "clickedButton",
                        lambda self: next(b for b in self.buttons() if b.text() == "Recupera"))
    w.offer_recovery()
    assert w.project.tracks[0].text == "4: c*4 e*4 g*4 c*5"
    assert w.current_path is None and w._dirty
    _close_discarding(w, monkeypatch)


def test_nothing_to_offer_shows_nothing(monkeypatch):
    w = _window()
    monkeypatch.setattr(QMessageBox, "exec", lambda self: pytest.fail("nessun dialogo atteso"))
    w.offer_recovery()
    _close_discarding(w, monkeypatch)
