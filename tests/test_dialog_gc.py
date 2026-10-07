"""
I dialoghi, una volta abbandonati, devono poter essere raccolti dal garbage
collector di Python senza mandare in crash il processo: un widget che tiene
un riferimento forte a un metodo del dialogo che lo possiede crea un ciclo
che, raccolto, fa andare in segmentation fault shiboken (PySide6). Vedi
gui.weak_callback.WeakCallback.

Ogni caso gira in un processo separato: un crash non si puo' intercettare
dall'interno.

Esecuzione:
    python3 -m pytest tests/test_dialog_gc.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import subprocess
import sys
import textwrap
import weakref

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from gui.weak_callback import WeakCallback

DIALOGS = {
    "box": "from gui.box_edit_dialog import BoxEditDialog as D; D(None, Project(name='t'), 'Piano', 120)",
    "pattern": "from gui.pattern_editor_dialog import PatternEditorDialog as D; D(Project(name='t'))",
    "tastiera": ("from gui.keyboard_play_dialog import KeyboardPlayDialog as D; "
                 "D(None, project=Project(name='t'), instrument_name='Piano', context_label='t')"),
    "audio": "from gui.audio_import_dialog import AudioImportDialog as D; D(None, Project(name='t'), 'Piano', 't')",
    "libreria_midi": "from gui.midi_library_dialog import MidiLibraryDialog as D; D(None)",
    "giro_armonico": ("from gui.rhythm_generate_dialog import ChordProgressionDialog as D; "
                      "D(None, Project(name='t'), 'Piano', 't')"),
    "batteria": ("from gui.rhythm_generate_dialog import DrumGenerateDialog as D; "
                 "D(None, Project(name='t'), 'Drums', 't')"),
}


@pytest.mark.parametrize("name", sorted(DIALOGS))
def test_abandoned_dialog_is_garbage_collected_without_crashing(name):
    script = textwrap.dedent(f"""
        import gc, sys
        sys.path.insert(0, {os.path.join(ROOT, 'tests')!r})
        sys.path.insert(0, {ROOT!r})
        import _config_isolation
        from PySide6.QtWidgets import QApplication
        app = QApplication([])
        from core.model import Project

        def make():
            {DIALOGS[name]}

        make()
        for _ in range(3):
            gc.collect()
        print("ok")
    """)
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    result = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0 and "ok" in result.stdout, (result.returncode, result.stderr[-2000:])


def test_weak_callback_does_not_keep_the_owner_alive():
    class Widget:
        callback = WeakCallback()

    class Owner:
        def __init__(self):
            self.widget = Widget()
            self.widget.callback = self.handle

        def handle(self):
            return "gestito"

    owner = Owner()
    widget = owner.widget
    assert widget.callback() == "gestito"
    ref = weakref.ref(owner)
    del owner
    assert ref() is None                    # nessun ciclo: liberato subito
    assert widget.callback is None


def test_weak_callback_keeps_plain_functions():
    class Widget:
        callback = WeakCallback()

    w = Widget()
    w.callback = lambda: 42
    assert w.callback() == 42
    w.callback = None
    assert w.callback is None
