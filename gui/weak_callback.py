"""
Attributo-callback a riferimento debole per i widget che richiamano metodi
del loro proprietario (vedi WeakCallback).
"""

import inspect
import weakref


class WeakCallback:
    """Attributo-callback che tiene i metodi di un altro oggetto con un
    riferimento debole: il proprietario (dialogo/finestra) tiene il widget, e
    un riferimento forte del widget a un suo metodo creerebbe un ciclo
    widget <-> proprietario che, raccolto dal garbage collector di Python,
    manda in crash shiboken (PySide6). Funzioni e lambda restano forti; se il
    proprietario non esiste piu', l'attributo vale None."""

    def __set_name__(self, owner, name):
        self._slot = "_weak_cb_" + name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        ref = getattr(obj, self._slot, None)
        return ref() if isinstance(ref, weakref.WeakMethod) else ref

    def __set__(self, obj, value):
        if inspect.ismethod(value) and value.__self__ is not obj:
            value = weakref.WeakMethod(value)
        setattr(obj, self._slot, value)
