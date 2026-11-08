"""
Menu a comparsa (QMenu.exec) nei test senza aprirli davvero.

Aprire il menu vero e sceglierne una voce da un QTimer dipende dai tempi:
su una macchina carica (test in parallelo della CI, soprattutto macOS) il
timer scattava prima che il menu comparisse e il test leggeva un menu
vuoto. QMenu.exec non si puo' sostituire sulla classe (e' un binding
Shiboken), quindi scripted_menus() mette al posto di QMenu, nei moduli
gui.* che l'hanno importata e in PySide6.QtWidgets (per gli import dentro
le funzioni), una sottoclasse la cui exec fa quello che farebbe l'utente:
legge le voci, sceglie quella richiesta (triggered e valore di ritorno,
come il menu vero) o chiude il menu senza scegliere (None).

    with scripted_menus(choose="▶ Play") as menus:
        editor.contextMenuEvent(...)
    assert menus.actions == ["▶ Play", "View"]
"""

import contextlib
import sys

from PySide6 import QtWidgets

_REAL_QMENU = QtWidgets.QMenu


class MenuScript:
    def __init__(self, choose):
        # choose: il testo della voce da scegliere, una funzione testo -> bool, o None
        self.choose = choose
        self.opened = []            # i testi delle voci di ogni menu aperto
        self.all_texts = []         # come opened, con i separatori ("")

    @property
    def actions(self):
        """I testi delle voci dell'ultimo menu aperto ([] se nessuno)."""
        return self.opened[-1] if self.opened else []

    def _matches(self, text):
        if self.choose is None:
            return False
        if callable(self.choose):
            return bool(self.choose(text))
        return text == self.choose

    def _find(self, menu):
        for action in menu.actions():
            if action.menu() is not None:
                found = self._find(action.menu())
                if found is not None:
                    return found
            elif action.text() and action.isEnabled() and self._matches(action.text()):
                return action
        return None

    def run(self, menu):
        self.all_texts.append([a.text() for a in menu.actions()])
        self.opened.append([a.text() for a in menu.actions() if a.text()])
        target = self._find(menu)
        if target is not None:
            target.trigger()
        return target


class _ScriptedMenu(_REAL_QMENU):
    script = None

    def exec(self, *args, **kwargs):
        return _ScriptedMenu.script.run(self)

    exec_ = exec


@contextlib.contextmanager
def scripted_menus(choose=None):
    script = MenuScript(choose)
    modules = [QtWidgets] + [module for name, module in list(sys.modules.items())
                             if name.startswith("gui.") and getattr(module, "QMenu", None) is _REAL_QMENU]
    previous = _ScriptedMenu.script
    _ScriptedMenu.script = script
    for module in modules:
        module.QMenu = _ScriptedMenu
    try:
        yield script
    finally:
        # anche i moduli importati per la prima volta qui dentro
        for module in [QtWidgets] + [m for name, m in list(sys.modules.items()) if name.startswith("gui.")]:
            if getattr(module, "QMenu", None) is _ScriptedMenu:
                module.QMenu = _REAL_QMENU
        _ScriptedMenu.script = previous
