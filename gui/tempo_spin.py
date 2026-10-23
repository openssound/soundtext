"""
Campo del tempo (BPM) con un decimale, come la riga Tempo: dalla 2.9 del
linguaggio (101.4): un tempo intero si scrive senza decimali ("120 BPM",
non "120,0 BPM") e bpm() lo restituisce intero, cosi' nel file .st resta
"Tempo: 120 BPM" come prima.
"""

from PySide6.QtWidgets import QDoubleSpinBox

TEMPO_RANGE = (20, 300)


def tempo_value(value: float):
    """Intero se lo e' (120), altrimenti con un decimale (101.4)."""
    rounded = round(float(value), 1)
    return int(rounded) if rounded.is_integer() else rounded


class TempoSpinBox(QDoubleSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDecimals(1)
        self.setRange(*TEMPO_RANGE)
        self.setSingleStep(1.0)
        self.setSuffix(" BPM")

    def textFromValue(self, value: float) -> str:
        value = tempo_value(value)
        if isinstance(value, int):
            return self.locale().toString(value)
        return self.locale().toString(float(value), "f", 1)

    def bpm(self):
        return tempo_value(self.value())
