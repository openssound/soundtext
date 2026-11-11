"""
Evidenziazione sintattica per l'editor della notazione testuale.

Riusa le regex di classificazione di core.notation: cosi' i colori
mostrati nell'editor corrispondono sempre a come il parser interpreta il
testo. La suddivisione in token e' invece riga per riga e tollerante
(core.syntax._LEX): un gruppo N(...) o un blocco di voci { ; } puo' andare a capo,
e ogni riga va colorata anche se da sola non e' un testo completo; dentro
gruppi e voci ogni token ha il suo colore.

Il contenuto di ogni voce di un blocco { ; } ha anche uno sfondo tenue,
diverso da una voce all'altra, cosi' si vede dove inizia e finisce ciascuna
anche quando il blocco va a capo. Le parentesi e i ';' restano senza sfondo,
a far da confine. Lo stato fra le righe (le voci aperte, una pila per i
blocchi annidati) passa da una riga all'altra con lo stato del blocco Qt.
"""

from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont

from core.syntax import LineState, line_spans

from .theme import get_active_theme

# Colori per categoria sintattica: versioni sature/luminose per lo sfondo
# scuro (prima colonna: dei pastelli resterebbero leggibili ma "spenti") e
# versioni scure per lo sfondo chiaro (seconda colonna: dei pastelli
# avrebbero contrasto insufficiente su sfondo bianco). Grassetto/corsivo restano fissi per categoria, solo il
# colore cambia con il tema.
_COLORS = {
    "note":       ("#6fd0ff", "#0f6fb0"),  # note melodiche - azzurro
    "chord":      ("#f0b854", "#8a5a00"),  # accordi astratti - ambra
    "perc":       ("#e685e6", "#8a2d8a"),  # percussioni - viola
    "state":      ("#7de87d", "#1f7a1f"),  # N: NT:/NQ:/NS: N@ - verde
    "ref":        ("#ff6f6f", "#b03030"),  # %pattern e &midi - corallo
    "rest":       ("#8f8f8f", "#5a5a5a"),  # pause - grigio
    "block":      ("#f0f060", "#8a6d00"),  # [ ... ] - giallo
    "repeat":     ("#d6a8f5", "#7030a0"),  # N(...) - lilla
    "slide":      ("#6fd0ff", "#0f6fb0"),  # slide c*4>d*4 - azzurro corsivo
    "sustain":    ("#7de8b0", "#1f8a5a"),  # SON/SOFF - verde acqua
    "tempo_ramp": ("#f5a065", "#a85a1a"),  # tempo=N, >>, << - arancio
    "comment":    ("#7f8c8d", "#6b7378"),  # // commento - grigio corsivo
    "voices":     ("#5fe0d0", "#00807a"),  # { ; } voci - turchese
    "lyric":      ("#ffb0d0", "#a0306a"),  # "testo cantato" - rosa
    "bar":        ("#b8b8b8", "#4a4a4a"),  # | controllo di battuta - grigio chiaro
    "bar_error":  ("#ff5050", "#c00000"),  # | che non cade su una stanghetta - rosso
    "transform":  ("#9fb4ff", "#3b4fc0"),  # .retro, .arpeggio(...): funzioni - indaco
}

# Sfondi delle voci di un blocco { ; }, a rotazione: prima voce azzurra,
# seconda ambra, terza lilla, quarta verde (tinte scure per il tema scuro,
# chiare per quello chiaro, che lasciano leggibili i colori dei token).
_VOICE_BACKGROUNDS = [
    ("#1e3a4f", "#dcefff"),
    ("#4a3a1a", "#fff0d2"),
    ("#3c2550", "#f0e2ff"),
    ("#1e4630", "#dcf5e4"),
]

# Pila delle voci aperte, codificata nello stato intero di una riga: i 3 bit
# bassi la profondita', poi 4 bit per l'indice di voce di ogni livello.
_MAX_DEPTH = 6
_VOICE_BITS = 4


_ARP_BIT = 1 << 28           # dopo la pila: un arp= e' attivo a fine riga


def _pack_voices(stack, arp: bool = False) -> int:
    stack = stack[-_MAX_DEPTH:]
    state = len(stack) | (_ARP_BIT if arp else 0)
    for level, voice in enumerate(stack):
        state |= min(voice, 2 ** _VOICE_BITS - 1) << (3 + _VOICE_BITS * level)
    return state


def _unpack_voices(state: int):
    if state < 0:                 # -1: riga senza stato (inizio documento)
        return []
    mask = 2 ** _VOICE_BITS - 1
    return [(state >> (3 + _VOICE_BITS * level)) & mask for level in range(state & 7)]


def _fmt(color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    f = QTextCharFormat()
    f.setForeground(QColor(color))
    if bold:
        f.setFontWeight(QFont.Bold)
    if italic:
        f.setFontItalic(True)
    return f


class NotationHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self._bar_errors = frozenset()
        self._apply_theme_colors()

    def set_bar_errors(self, positions):
        """Posizioni (carattere, nel documento) dei token con un avviso
        (vedi core.notation.notation_warnings: '|' che non cadono su una
        stanghetta, testi cantati con troppe sillabe): in rosso."""
        positions = frozenset(positions)
        if positions == self._bar_errors:
            return
        self._bar_errors = positions
        # rehighlight() fa emettere al documento contentsChanged (e
        # all'editor textChanged) anche se il testo non cambia: chi ascolta
        # textChanged lo prenderebbe per una modifica dell'utente (progetto
        # segnato come modificato, voce di annulla). Cambiano solo i colori.
        document = self.document()
        blocked = document.blockSignals(True) if document is not None else False
        try:
            self.rehighlight()
        finally:
            if document is not None:
                document.blockSignals(blocked)

    def _apply_theme_colors(self):
        light = get_active_theme() == "light"

        def color(key: str) -> str:
            dark_c, light_c = _COLORS[key]
            return light_c if light else dark_c

        self.fmt_note = _fmt(color("note"))
        self.fmt_chord = _fmt(color("chord"), bold=True)
        self.fmt_perc = _fmt(color("perc"))
        self.fmt_state = _fmt(color("state"), italic=True)
        self.fmt_ref = _fmt(color("ref"), bold=True)
        self.fmt_rest = _fmt(color("rest"), italic=True)
        self.fmt_block = _fmt(color("block"))
        self.fmt_repeat = _fmt(color("repeat"), bold=True)
        self.fmt_slide = _fmt(color("slide"), italic=True)
        self.fmt_sustain = _fmt(color("sustain"), bold=True)
        self.fmt_tempo_ramp = _fmt(color("tempo_ramp"), bold=True)
        self.fmt_comment = _fmt(color("comment"), italic=True)
        self.fmt_voices = _fmt(color("voices"), bold=True)
        self.fmt_lyric = _fmt(color("lyric"), italic=True)
        self.fmt_bar = _fmt(color("bar"), bold=True)
        self.fmt_transform = _fmt(color("transform"), bold=True)
        # un accordo sotto un arp= attivo: si sente spezzato
        self.fmt_chord_arp = _fmt(color("chord"), bold=True)
        self.fmt_chord_arp.setUnderlineStyle(QTextCharFormat.DotLine)
        self.fmt_chord_arp.setUnderlineColor(QColor(color("transform")))
        self.fmt_bar_error = _fmt(color("bar_error"), bold=True)
        self.fmt_bar_error.setUnderlineStyle(QTextCharFormat.WaveUnderline)
        self.fmt_bar_error.setUnderlineColor(QColor(color("bar_error")))
        self.voice_backgrounds = [QColor(light_c if light else dark_c)
                                  for dark_c, light_c in _VOICE_BACKGROUNDS]
        self._category_formats = self._formats()

    def update_theme(self):
        """Da richiamare quando l'utente cambia tema con l'editor gia'
        aperto: i QTextCharFormat sono creati una volta sola in base al
        tema attivo al momento e un rehighlight() da solo riusa gli stessi
        oggetti, quindi il testo resterebbe colorato con la palette del tema
        precedente, illeggibile su uno sfondo opposto."""
        self._apply_theme_colors()
        self.rehighlight()

    def highlightBlock(self, text: str):
        previous = self.previousBlockState()
        state = LineState(_unpack_voices(previous), previous >= 0 and bool(previous & _ARP_BIT))
        block_start = self.currentBlock().position()
        errors = [p - block_start for p in self._bar_errors if block_start <= p < block_start + len(text)]
        spans, voices, after = line_spans(text, state, errors)
        self.setCurrentBlockState(_pack_voices(after.stack, after.arp))
        backgrounds = [None if v is None else self.voice_backgrounds[v] for v in voices]
        formats = self._category_formats

        def apply(start, length, fmt):
            """fmt sui caratteri [start, start+length), con lo sfondo della voce."""
            end = start + length
            while start < end:
                background = backgrounds[start]
                run = start + 1
                while run < end and backgrounds[run] == background:
                    run += 1
                if background is None:
                    if fmt is not None:
                        self.setFormat(start, run - start, fmt)
                else:
                    merged = QTextCharFormat(fmt) if fmt is not None else QTextCharFormat()
                    merged.setBackground(background)
                    self.setFormat(start, run - start, merged)
                start = run

        apply(0, len(text), None)
        for start, length, category in spans:
            apply(start, length, formats[category])

    def _formats(self) -> dict:
        """Categoria di core.syntax -> formato Qt del tema attivo (si
        prepara una volta per tema, in _apply_theme_colors)."""
        return {
            "note": self.fmt_note, "chord": self.fmt_chord, "chord_arp": self.fmt_chord_arp,
            "perc": self.fmt_perc, "state": self.fmt_state, "ref": self.fmt_ref, "rest": self.fmt_rest,
            "block": self.fmt_block, "repeat": self.fmt_repeat, "slide": self.fmt_slide,
            "sustain": self.fmt_sustain, "tempo_ramp": self.fmt_tempo_ramp, "comment": self.fmt_comment,
            "voices": self.fmt_voices, "lyric": self.fmt_lyric, "bar": self.fmt_bar,
            "bar_error": self.fmt_bar_error, "transform": self.fmt_transform,
        }
