"""Nomi per lo screen reader (docs, sezione 6.1): ogni controllo interattivo ne ha uno.

Un pulsante con il testo, una casella con la sua etichetta (QFormLayout fa il buddy) hanno gia' il nome dal sistema. Per
gli altri (un pulsante con la sola icona, una manopola, un cursore, un campo senza etichetta, una barra di scorrimento) il
filtro installato sull'applicazione (install) lo ricava, al primo disegno, dal suggerimento (la prima frase) o dal
segnaposto; la descrizione e' il suggerimento intero. Il test tests/test_accessibility_gui.py percorre le finestre
principali e fallisce se un controllo resta senza nome: chi aggiunge un pulsante non puo' dimenticarlo.
"""

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QAccessible
from PySide6.QtWidgets import (
    QAbstractButton, QAbstractSlider, QAbstractSpinBox, QComboBox, QLineEdit, QListWidget, QPlainTextEdit, QScrollBar,
    QTableWidget, QTabBar, QTextEdit, QWidget,
)

from core.i18n import tr

CONTROLS = (QAbstractButton, QComboBox, QAbstractSlider, QAbstractSpinBox, QLineEdit, QPlainTextEdit, QTextEdit, QTabBar,
            QListWidget, QTableWidget)


def name_of(widget) -> str:
    """Il nome che legge lo screen reader (quello di QAccessible)."""
    iface = QAccessible.queryAccessibleInterface(widget)
    return (iface.text(QAccessible.Text.Name) if iface else "") or ""


def _first_sentence(text: str, limit: int = 70) -> str:
    text = " ".join(text.split())
    for sep in (". ", "\n", " (", ": "):
        if sep in text:
            text = text.split(sep, 1)[0]
    return text.rstrip(".:")[:limit]


def ensure_name(widget):
    """Da' un nome (e una descrizione) a un controllo che non ne ha; True se l'ha fatto."""
    if not isinstance(widget, CONTROLS) or name_of(widget).strip():
        return False
    if widget.objectName().startswith("qt_"):                    # i pulsanti interni di Qt (menu, barra degli strumenti)
        widget.setAccessibleName(tr("Altri comandi"))
        return True
    name = ""
    if isinstance(widget, QScrollBar):
        name = tr("Scorrimento verticale") if widget.orientation() == Qt.Vertical else tr("Scorrimento orizzontale")
    if not name:
        name = _first_sentence(widget.toolTip())
    if not name and isinstance(widget, QLineEdit):
        name = widget.placeholderText()
    if not name and isinstance(widget, QAbstractButton):
        name = widget.statusTip() or widget.whatsThis()
    if not name:
        return False
    widget.setAccessibleName(name)
    if widget.toolTip() and not widget.accessibleDescription():
        widget.setAccessibleDescription(widget.toolTip())
    return True


class _Namer(QObject):
    """Filtro dell'applicazione: ogni controllo, al primo disegno, ha il suo nome."""

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Polish, QEvent.Show) and isinstance(obj, QWidget):
            ensure_name(obj)
        return False


_namer = None


def install(app):
    """Da chiamare una volta all'avvio (main.py), prima di costruire le finestre."""
    global _namer
    if _namer is None:
        _namer = _Namer(app)
        app.installEventFilter(_namer)
    return _namer


def unnamed(root) -> list:
    """I controlli di 'root' ancora senza nome: [(classe, nome oggetto, suggerimento)]. Per il test."""
    out = []
    for widget in root.findChildren(QWidget):
        if isinstance(widget, CONTROLS) and not name_of(widget).strip():
            if isinstance(widget, QLineEdit) and isinstance(widget.parent(), (QAbstractSpinBox, QComboBox)):
                continue                                              # il campo interno di una casella: ha il nome del padre
            out.append((type(widget).__name__, widget.objectName(), widget.toolTip()[:50]))
    return out
