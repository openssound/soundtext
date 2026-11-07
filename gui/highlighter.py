"""
Evidenziazione sintattica per l'editor della notazione testuale.

Riusa le regex di classificazione di core.notation: cosi' i colori
mostrati nell'editor corrispondono sempre a come il parser interpreta il
testo. La suddivisione in token e' invece riga per riga e tollerante
(_LEX): un gruppo N(...) o un blocco di voci { ; } puo' andare a capo,
e ogni riga va colorata anche se da sola non e' un testo completo; dentro
gruppi e voci ogni token ha il suo colore.

Il contenuto di ogni voce di un blocco { ; } ha anche uno sfondo tenue,
diverso da una voce all'altra, cosi' si vede dove inizia e finisce ciascuna
anche quando il blocco va a capo. Le parentesi e i ';' restano senza sfondo,
a far da confine. Lo stato fra le righe (le voci aperte, una pila per i
blocchi annidati) passa da una riga all'altra con lo stato del blocco Qt.
"""

import re

from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont

from core.notation import (
    strip_comments, comment_spans, split_note_value, RE_PATTERN_REF, RE_MIDI_REF, RE_GRID,
    RE_VELOCITY, RE_REST, RE_NOTE, RE_CHORD, RE_PERC, RE_SLIDE,
    RE_TEMPO_SET, RE_RAMP_UP, RE_RAMP_DOWN, RE_CONTROL, RE_SWING, RE_SHIFT, RE_PITCH_MODE,
    RE_KEY_MODE, RE_BAR_ANCHOR, RE_TRANSPOSE, RESET_TOKEN, RE_NAVIGATION, RE_HARMONY, RE_ARP,
    RE_ARPEGGIO_SUFFIX, NotationError,
)
from st_language.transform import is_transform_reference, parse_reference
from .theme import get_active_theme

# Token di una riga, per colorarla: testo cantato, blocco [...] (col suo
# eventuale valore di nota), aperture e chiusure di gruppi e voci, la
# stanghetta e i token semplici.
_LEX = re.compile(r"""
    (?P<text>\$"[^"\n]*"?)
  | (?P<midiref>\d*&"[^"\n]*"?(?:[+-]\d+)?)
  | (?P<lyric>"[^"\n]*"?)
  | (?P<block>\d*\[[^\]\n]*\]?(?:'[^\s|"(){};]*)?(?:\$[a-z]+)*(?:\.(?i:arpeggio)(?:\([^()\s]*\)?)?)?[<>]?~?\(?)
  | (?P<group>\d*\(|\))
  | (?P<voices>[{};])
  | (?P<bar>:\|(?:[1-9]\.)?|\|(?::|\||[1-9]\.)?)
  | (?P<transform>\d*%\w+(?:[+-]\d+)*(?:\.\w*(?:\([^()\s]*\)?)?(?:[+-]\d+)?)+)
  | (?P<arpeggio>(?:[^\s|"(){};\[\]:]|:(?!\|))+?\.(?i:arpeggio)(?:\([^()\s]*\)?)?[^\s|"(){};\[\]:]*)
  | (?P<plain>(?:[^\s|"(){};\[\]:]|:(?!\|))+\(?)
""", re.VERBOSE)

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

    def update_theme(self):
        """Da richiamare quando l'utente cambia tema con l'editor gia'
        aperto: i QTextCharFormat sono creati una volta sola in base al
        tema attivo al momento e un rehighlight() da solo riusa gli stessi
        oggetti, quindi il testo resterebbe colorato con la palette del tema
        precedente, illeggibile su uno sfondo opposto."""
        self._apply_theme_colors()
        self.rehighlight()

    def _voice_background(self, stack):
        """Lo sfondo della voce piu' interna aperta (None fuori dai blocchi):
        un blocco annidato parte da un altro colore di quello che lo contiene."""
        if not stack:
            return None
        palette = self.voice_backgrounds
        return palette[(stack[-1] + 2 * (len(stack) - 1)) % len(palette)]

    def highlightBlock(self, text: str):
        stripped = strip_comments(text)
        lexemes = list(_LEX.finditer(stripped))

        # Sfondo di ogni carattere: quello della voce aperta in quel punto.
        stack = _unpack_voices(self.previousBlockState())
        backgrounds = [None] * len(text)
        pos = 0
        for m in lexemes:
            background = self._voice_background(stack)
            for i in range(pos, m.start()):
                backgrounds[i] = background
            tok = m.group()
            if m.lastgroup == "voices":
                if tok == "{":
                    stack.append(0)
                elif tok == ";" and stack:
                    stack[-1] += 1
                elif tok == "}" and stack:
                    stack.pop()
            else:
                for i in range(m.start(), m.end()):
                    backgrounds[i] = background
            pos = m.end()
        background = self._voice_background(stack)
        for i in range(pos, len(text)):
            backgrounds[i] = background
        previous = self.previousBlockState()
        arp = previous >= 0 and bool(previous & _ARP_BIT)
        arp_after = arp
        for m in lexemes:
            if RE_ARP.match(m.group()):
                arp_after = not m.group().lower().startswith("arp=off")
        self.setCurrentBlockState(_pack_voices(stack, arp_after))

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
        for start, end in comment_spans(text):
            apply(start, end - start, self.fmt_comment)
        block_start = self.currentBlock().position()
        # ')' chiude un gruppo N(...) o una legatura di portamento c( ... f):
        # vale il gruppo aperto per ultimo sulla riga (se non ce n'e', la
        # legatura aperta sulla riga, altrimenti un gruppo di una riga prima).
        opened = []
        for m in lexemes:
            kind, tok = m.lastgroup, m.group()
            if kind == "group" and tok != ")":
                opened.append("group")
            elif kind in ("plain", "block") and tok.endswith("("):
                opened.append("slur")
            elif tok == ")" and opened and opened.pop() == "slur":
                kind = "slur_close"
            if kind == "plain" and RE_ARP.match(tok):
                arp = not tok.lower().startswith("arp=off")
            if kind == "transform":
                if block_start + m.start() in self._bar_errors:
                    apply(m.start(), len(tok), self.fmt_bar_error)
                else:
                    self._apply_reference(apply, m.start(), tok)
                continue
            if kind == "arpeggio" or (kind == "block" and ".arpeggio" in tok.lower()):
                self._apply_arpeggio(apply, m.start(), tok, kind)
                continue
            if kind == "slur_close":
                fmt = self.fmt_note
            elif kind == "bar":
                fmt = self.fmt_bar_error if block_start + m.start() in self._bar_errors else self.fmt_bar
            elif kind in ("lyric", "text"):
                fmt = self.fmt_lyric
            elif kind == "block":
                fmt = self.fmt_block
            elif kind == "group":
                fmt = self.fmt_repeat
            elif kind == "voices":
                fmt = self.fmt_voices
            else:
                fmt = self._classify(split_note_value(tok)[0])
            if kind != "bar" and block_start + m.start() in self._bar_errors:
                fmt = self.fmt_bar_error     # avviso sul testo cantato o su un blocco di voci
            if fmt is self.fmt_chord and arp:
                fmt = self.fmt_chord_arp
            if fmt:
                apply(m.start(), len(tok), fmt)

    def _apply_reference(self, apply, start: int, tok: str):
        """Un richiamo con funzioni: il pattern corallo, le funzioni con il
        loro colore, gli argomenti con quelli che hanno gia'. La grammatica e'
        quella della libreria (parse_reference); un richiamo che non si legge
        e' tutto un errore."""
        try:
            steps = parse_reference(tok).steps
        except NotationError:
            apply(start, len(tok), self.fmt_bar_error)
            return
        apply(start, steps[0].start if steps else len(tok), self.fmt_ref)
        for step in steps:
            if step.name == "transpose":
                apply(start + step.start, step.end - step.start, self.fmt_ref)
            else:
                self._apply_call(apply, start + step.start, tok[step.start:step.end])

    def _apply_call(self, apply, start: int, call: str):
        """'.nome(a,b)': nome e parentesi colore funzione, argomenti i loro."""
        apply(start, len(call), self.fmt_transform)
        opened = call.find("(")
        if opened < 0:
            return
        pos = opened + 1
        for argument in call[pos:].rstrip(")").split(","):
            if argument:
                apply(start + pos, len(argument), self._classify(argument) or self.fmt_state)
            pos += len(argument) + 1

    def _apply_arpeggio(self, apply, start: int, tok: str, kind: str):
        """Un accordo o un blocco con .arpeggio(...): prima il suo colore, poi
        il suffisso."""
        m = RE_ARPEGGIO_SUFFIX.match(tok)
        if not m:
            apply(start, len(tok), self.fmt_block if kind == "block" else self.fmt_chord)
            return
        base = self.fmt_block if kind == "block" else (self._classify(split_note_value(m.group(1))[0]) or self.fmt_chord)
        apply(start, len(tok), base)
        suffix_end = len(tok) - len(m.group(3))
        self._apply_call(apply, start + len(m.group(1)), tok[len(m.group(1)):suffix_end])

    def _classify(self, tok: str):
        if RE_PATTERN_REF.match(tok) or RE_MIDI_REF.match(tok):
            return self.fmt_ref
        if tok in ("SON", "SOFF"):
            return self.fmt_sustain
        if RE_TEMPO_SET.match(tok) or RE_RAMP_UP.match(tok) or RE_RAMP_DOWN.match(tok):
            return self.fmt_tempo_ramp
        if is_transform_reference(tok):
            return self.fmt_bar_error     # scritto a meta': un richiamo valido e' un lessema 'transform'
        if RE_GRID.match(tok) or RE_VELOCITY.match(tok) or RE_ARP.match(tok) or RE_CONTROL.match(tok) or RE_SWING.match(tok) \
                or RE_SHIFT.match(tok) or RE_PITCH_MODE.match(tok) or RE_KEY_MODE.match(tok) \
                or RE_BAR_ANCHOR.match(tok) or RE_TRANSPOSE.match(tok) or tok == RESET_TOKEN:
            return self.fmt_state
        if RE_NAVIGATION.match(tok):
            return self.fmt_repeat        # $segno, $dc...: struttura, come i ritornelli
        if RE_HARMONY.match(tok):
            return self.fmt_chord         # $Am7: sigla senza suono
        if RE_REST.match(tok):
            return self.fmt_rest
        if RE_SLIDE.match(tok):
            return self.fmt_slide
        if RE_NOTE.match(tok):
            return self.fmt_note
        if RE_CHORD.match(tok):
            return self.fmt_chord
        if RE_PERC.match(tok):
            return self.fmt_perc
        return None
