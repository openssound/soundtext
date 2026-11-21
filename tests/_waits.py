"""Attese dei test che finiscono appena la condizione e' vera (e non dopo un tempo fisso).

- con Qt: wait_for(condition, timeout) fa girare gli eventi (QTest.qWaitFor);
- senza Qt: wait_until(condition, timeout), un ciclo con scadenza e un'attesa brevissima fra un controllo e l'altro.

Un'attesa che misura un tempo (la durata di un tasto premuto, un rendering finto che deve durare) non passa da qui.
"""
import time


def wait_for(condition, timeout=10.0):
    """Eventi Qt finche' condition() e' vera, al piu' 'timeout' secondi; True se e' diventata vera.
    (QTest.qWaitFor non c'e' in tutte le versioni di PySide6: stessa cosa, a passi di 2 ms.)"""
    from PySide6.QtTest import QTest
    if hasattr(QTest, "qWaitFor"):
        return QTest.qWaitFor(lambda: bool(condition()), int(timeout * 1000))
    end = time.monotonic() + timeout
    while not condition():
        if time.monotonic() >= end:
            return bool(condition())
        QTest.qWait(2)
    return True


def wait_until(condition, timeout=10.0, interval=0.002):
    """Senza Qt: controlla condition() finche' e' vera o scade il tempo; True se e' diventata vera."""
    end = time.monotonic() + timeout
    while not condition():
        if time.monotonic() >= end:
            return bool(condition())
        time.sleep(interval)
    return True
