"""
Tastiera pianistica visuale per il dialogo "Suona con la tastiera" (vedi
gui.keyboard_play_dialog): mostra N ottave di una tastiera di pianoforte e
colora i tasti corrispondenti alle note (singole o in accordo) che stanno
suonando in questo momento sulla tastiera del computer - puro riscontro
visivo, non cliccabile (le note si suonano solo dalla tastiera del
computer, vedi gui.keyboard_note_map).
"""

from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtWidgets import QWidget

from core.chords import midi_note

# Pitch class (0-11) -> indice del tasto bianco nell'ottava (0=do...6=si).
_WHITE_PCS = [0, 2, 4, 5, 7, 9, 11]
# Pitch class dei tasti neri -> indice (0-6) del tasto bianco nella stessa
# ottava subito alla sua sinistra, per posizionarlo a cavallo del confine
# tra i due tasti bianchi.
_BLACK_PC_AFTER_WHITE = {1: 0, 3: 1, 6: 3, 8: 4, 10: 5}

WHITE_KEY_COLOR = QColor("#f5f2ea")
BLACK_KEY_COLOR = QColor("#1c1c1a")
KEY_BORDER_COLOR = QColor("#30302c")
# Stesso colore usato per evidenziare il token in esecuzione nell'editor
# durante la riproduzione (vedi gui.main_window_playback.TEXT_DIM_INVERT_BG):
# un solo colore di evidenziazione in tutta l'app per lo stesso concetto
# ("questo sta suonando ORA").
HIGHLIGHT_COLOR = QColor("#e8c96d")


class PianoKeyboardWidget(QWidget):
    """Tastiera di n_octaves ottave a partire dal Do di start_octave
    (convenzione scientifica: Do4 = MIDI 60, vedi core.chords.midi_note).
    set_active() riceve l'insieme delle note MIDI da evidenziare."""

    def __init__(self, n_octaves: int = 4, start_octave: int = 3, parent=None):
        super().__init__(parent)
        self.n_octaves = n_octaves
        self.start_octave = start_octave
        self._active = frozenset()
        self.setMinimumHeight(64)
        # Larghezza fissa (non solo minima): senza, il layout verticale del
        # dialogo la stirerebbe per riempire tutta la larghezza disponibile,
        # con tasti molto piu' larghi di quelli di una tastiera vera.
        self.setFixedWidth(7 * n_octaves * 14)

    def set_range(self, start_octave: int):
        if start_octave != self.start_octave:
            self.start_octave = start_octave
            self.update()

    def set_active(self, midi_pitches):
        new_active = frozenset(midi_pitches)
        if new_active != self._active:
            self._active = new_active
            self.update()

    def _white_key_count(self) -> int:
        return 7 * self.n_octaves

    def paintEvent(self, event):
        n_white = self._white_key_count()
        if n_white == 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        white_w = w / n_white
        start_midi = midi_note(0, self.start_octave)
        pen = QPen(KEY_BORDER_COLOR, 1)

        for i in range(n_white):
            octave_idx, white_idx = divmod(i, 7)
            pitch = start_midi + octave_idx * 12 + _WHITE_PCS[white_idx]
            painter.setBrush(HIGHLIGHT_COLOR if pitch in self._active else WHITE_KEY_COLOR)
            painter.setPen(pen)
            painter.drawRect(QRectF(i * white_w, 0, white_w, h))

        black_w = white_w * 0.6
        black_h = h * 0.6
        for octave_idx in range(self.n_octaves):
            for pc, after_white_idx in _BLACK_PC_AFTER_WHITE.items():
                pitch = start_midi + octave_idx * 12 + pc
                boundary_x = (octave_idx * 7 + after_white_idx + 1) * white_w
                painter.setBrush(HIGHLIGHT_COLOR if pitch in self._active else BLACK_KEY_COLOR)
                painter.setPen(pen)
                painter.drawRect(QRectF(boundary_x - black_w / 2, 0, black_w, black_h))
