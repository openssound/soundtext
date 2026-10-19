"""Dimensione del testo st-language: Ctrl+ / Ctrl- / Ctrl+0 e Ctrl+rotella.

Una sola dimensione per tutti i campi che mostrano notazione (l'editor della
traccia e i dialoghi con anteprima o modifica del testo), salvata nelle
impostazioni: cambiandola in uno si aggiornano anche gli altri aperti.

La dimensione si applica col foglio di stile del widget: quello del tema
(font-size su QWidget) avrebbe la meglio su setFont."""

import weakref

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QAction, QKeySequence

from core import settings as app_settings
from core.i18n import tr

# Dimensioni (pixel) fra cui scorrono Ctrl+ e Ctrl-.
TEXT_SIZES = (8, 9, 10, 11, 12, 13, 14, 16, 18, 20, 22, 24, 28, 32, 36, 40, 48)
DEFAULT_TEXT_SIZE = 13

_edits = weakref.WeakSet()


def text_size() -> int:
    return app_settings.get_editor_text_size()


def set_text_size(size: int):
    size = max(TEXT_SIZES[0], min(TEXT_SIZES[-1], int(size)))
    if size != text_size():
        app_settings.set_editor_text_size(size)
    for edit in list(_edits):
        _apply(edit, size)


def enlarge():
    current = text_size()
    set_text_size(next((s for s in TEXT_SIZES if s > current), TEXT_SIZES[-1]))


def shrink():
    current = text_size()
    set_text_size(next((s for s in reversed(TEXT_SIZES) if s < current), TEXT_SIZES[0]))


def reset():
    set_text_size(DEFAULT_TEXT_SIZE)


def _apply(edit, size):
    try:
        edit.setStyleSheet(f"QPlainTextEdit, QTextEdit {{ font-size: {size}px; }}")
    except RuntimeError:        # widget C++ gia' distrutto
        _edits.discard(edit)


class _WheelZoom(QObject):
    """Ctrl+rotella sul campo (la rotella arriva al viewport)."""

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel and event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                enlarge()
            elif delta < 0:
                shrink()
            return True
        return False


def enable(edit):
    """Attiva lo zoom del testo su un QPlainTextEdit/QTextEdit e ne
    restituisce le azioni (Testo piu' grande / piu' piccolo / normale), con
    scorciatoie valide solo col fuoco nel campo: chi vuole le mette in un menu."""
    _edits.add(edit)
    _apply(edit, text_size())
    edit._text_zoom_filter = _WheelZoom(edit)
    edit.viewport().installEventFilter(edit._text_zoom_filter)
    actions = []
    for label, slot, keys in ((tr("Testo piu' grande"), enlarge, ["Ctrl++", "Ctrl+=", "Ctrl+Num++"]),
                              (tr("Testo piu' piccolo"), shrink, ["Ctrl+-", "Ctrl+Num+-"]),
                              (tr("Testo di dimensione normale"), reset, ["Ctrl+0", "Ctrl+Num+0"])):
        act = QAction(label, edit)
        act.setShortcuts([QKeySequence(k) for k in keys])
        act.setShortcutContext(Qt.WidgetShortcut)
        act.triggered.connect(lambda _checked=False, slot=slot: slot())
        edit.addAction(act)
        actions.append(act)
    return actions
