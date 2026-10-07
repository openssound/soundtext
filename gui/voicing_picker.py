"""
Menu di selezione voicing su doppio click: fare doppio click su un accordo
(sia in forma compatta 'Cmaj7' sia in forma esplicita gia' congelata
'[c*3 g*3 b*3 e*4]') nell'editor della traccia o nell'editor di un pattern
apre un popup con le alternative di voicing sensate per lo strumento
corrente (core.chords.applicable_voicings), navigabile con le frecce con
anteprima audio ad ogni scelta (debounced), confermabile con Invio/click o
annullabile con Esc/click fuori (nativo di Qt.Popup).
"""

import re
from typing import Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import QEvent, Qt, QPoint, QTimer, QStringListModel, Signal
from PySide6.QtGui import QFont, QKeySequence, QTextCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QPlainTextEdit, QToolTip, QCompleter
)

from core.model import Project, copy_synth
from core.chords import (
    parse_chord_symbol, voice_chord, midi_to_token, pitch_to_midi,
    pc_to_letter, applicable_voicings, recognize_chord, apply_bass_note,
)
from core.completion import current_word_bounds
from core.instruments import InstrumentProfile
from core.notation import (
    RE_NOTE, RE_CHORD, RE_REPEAT_GROUP, RE_VOICES, compute_token_spans, Pattern, NotationError,
    split_note_value, split_voices,
)
from core.playback import PlaybackEngine

from .weak_callback import WeakCallback
from core.i18n import tr

VOICING_PREVIEW_DEBOUNCE_MS = 150

_BLOCK_RE = re.compile(r"^(\d*)\[(.*)\]$")


# ---------------------------------------------------------------------------
# Editor di testo con supporto al doppio click su un accordo
# ---------------------------------------------------------------------------

# Scorciatoia di digitazione per il bemolle: un '-' battuto subito dopo una
# lettera nota (a-g/A-G) viene sostituito automaticamente con il simbolo
# musicale reale '♭', per evitare l'ambiguita' visiva della 'b' testuale con
# la lettera nota 'b' (Si) senza dover digitare '♭' direttamente (vedi
# core.notation.RE_NOTE / RE_CHORD / RE_SLIDE, che accettano '#'/'b'/'♭'/'-'
# come sinonimi equivalenti in ingresso: questa e' solo una comodita' di
# visualizzazione nell'editor, non un requisito del parser).
_FLAT_TRIGGER_LETTERS = set("abcdefgABCDEFG")
# Caratteri che, immediatamente prima della lettera nota, confermano che la
# lettera e' davvero l'inizio di un token (fondamentale di nota/accordo) e non
# l'ultimo carattere di un'altra parola (es. 'snare', 'ride', che terminano
# per coincidenza con una lettera nota): spazio/inizio riga, apertura di
# blocco/gruppo, '>' di uno slide, o una cifra di moltiplicatore (es. '4c-').
_FLAT_TRIGGER_BOUNDARY = set(" \t\n[(>") | set("0123456789")


class NotationEditor(QPlainTextEdit):
    """QPlainTextEdit specializzato per la notazione: se il proprietario
    imposta on_double_click_token, il doppio click prova prima quel
    callback (posizione carattere + posizione globale del mouse); se
    ritorna False (token non gestito, es. una nota semplice), ricade sul
    comportamento nativo (selezione della parola). Se il proprietario imposta
    on_selection_context_menu, un tasto destro con una selezione attiva prova
    prima quel callback (posizione inizio/fine selezione + posizione globale
    del mouse); se ritorna False, ricade sul menu contestuale nativo. Sostituisce
    inoltre automaticamente '-' con '♭' quando digitato subito dopo una lettera
    nota (vedi _FLAT_TRIGGER_LETTERS).

    Se il proprietario imposta on_completion_request(word) -> list[str],
    mostra durante la digitazione un popup di autocompletamento con i token
    completi pertinenti al frammento gia' scritto (vedi core.completion),
    per velocizzare l'inserimento di qualita' d'accordo, stili di voicing,
    percussioni/dinamiche e riferimenti %pattern / &midi. Frecce su/giu' per
    scorrere le proposte, Invio/Tab/click per accettare, Esc per chiudere.

    Con use_window_undo() l'editor rinuncia al proprio Annulla/Ripeti e
    lascia Ctrl+Z/Ctrl+Y alle azioni della finestra (la cronologia unica del
    progetto, vedi core.history): senza, l'editor li intercetterebbe sempre,
    anche con l'undo nativo disattivato."""

    on_double_click_token = WeakCallback()
    on_selection_context_menu = WeakCallback()
    on_completion_request = WeakCallback()

    def __init__(self, parent=None):
        # Prima di super().__init__: Qt chiama gia' event() durante la costruzione.
        self._window_undo = False
        super().__init__(parent)
        self.on_double_click_token: Optional[Callable[[int, QPoint], bool]] = None
        self.on_selection_context_menu: Optional[Callable[[int, int, QPoint], bool]] = None
        self.on_completion_request: Optional[Callable[[str], List[str]]] = None

        self._completer = QCompleter(self)
        self._completer.setWidget(self)
        self._completer.setCompletionMode(QCompleter.PopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseSensitive)
        self._completer.setModelSorting(QCompleter.UnsortedModel)
        self._completer.activated.connect(self._insert_completion)

        self.textChanged.connect(self._update_completer)
        self.cursorPositionChanged.connect(self._update_completer)

    def use_window_undo(self):
        self._window_undo = True
        self.setUndoRedoEnabled(False)

    def event(self, event):
        if (self._window_undo and event.type() == QEvent.ShortcutOverride
                and (event.matches(QKeySequence.Undo) or event.matches(QKeySequence.Redo))):
            event.ignore()   # non consumarlo: arriva allo shortcut della finestra
            return False
        return super().event(event)

    def contextMenuEvent(self, event):
        if self.on_selection_context_menu is not None:
            cursor = self.textCursor()
            if cursor.hasSelection():
                if self.on_selection_context_menu(cursor.selectionStart(), cursor.selectionEnd(),
                                                   event.globalPos()):
                    return
        super().contextMenuEvent(event)

    def keyPressEvent(self, event):
        # Le frecce su/giu' e la conferma sono gestite dal QCompleter stesso
        # (installato via setWidget); qui va solo impedito che Invio/Tab/Esc
        # producano anche il loro effetto nativo nell'editor (a capo, tab,
        # deselezione) mentre il popup e' visibile.
        if self._completer.popup().isVisible() and event.key() in (
            Qt.Key_Enter, Qt.Key_Return, Qt.Key_Escape, Qt.Key_Tab, Qt.Key_Backtab,
        ):
            event.ignore()
            return
        if event.text() == "-" and self._flat_shortcut_applies():
            cursor = self.textCursor()
            cursor.insertText("♭")
            self.setTextCursor(cursor)
            return
        super().keyPressEvent(event)

    def _flat_shortcut_applies(self) -> bool:
        cursor = self.textCursor()
        if cursor.hasSelection():
            return False
        pos = cursor.position()
        if pos < 1:
            return False
        text = self.toPlainText()
        if text[pos - 1] not in _FLAT_TRIGGER_LETTERS:
            return False
        return pos == 1 or text[pos - 2] in _FLAT_TRIGGER_BOUNDARY

    def mouseDoubleClickEvent(self, event):
        self._completer.popup().hide()
        if self.on_double_click_token is not None:
            char_offset = self.cursorForPosition(event.pos()).position()
            if self.on_double_click_token(char_offset, event.globalPos()):
                return
        super().mouseDoubleClickEvent(event)

    # --------------------------------------------------- Autocompletamento

    def _current_word(self) -> Tuple[int, int, str]:
        text = self.toPlainText()
        pos = self.textCursor().position()
        start, end = current_word_bounds(text, pos)
        return start, end, text[start:end]

    def _update_completer(self):
        if self.on_completion_request is None:
            return
        if self.textCursor().hasSelection():
            self._completer.popup().hide()
            return
        _start, _end, word = self._current_word()
        candidates = self.on_completion_request(word) if word else []
        if not candidates:
            self._completer.popup().hide()
            return
        self._completer.setModel(QStringListModel(candidates, self._completer))
        # i candidati sono gia' filtrati da on_completion_request (e per
        # &"nome" non cominciano per forza con quello che si e' digitato)
        self._completer.setCompletionPrefix("")
        self._completer.popup().setCurrentIndex(self._completer.completionModel().index(0, 0))
        rect = self.cursorRect()
        rect.setWidth(
            self._completer.popup().sizeHintForColumn(0)
            + self._completer.popup().verticalScrollBar().sizeHint().width()
        )
        self._completer.complete(rect)

    def _insert_completion(self, completion: str):
        start, end, _word = self._current_word()
        cursor = self.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        cursor.insertText(completion)
        self.setTextCursor(cursor)


# ---------------------------------------------------------------------------
# Popup di selezione
# ---------------------------------------------------------------------------

class VoicingPickerPopup(QWidget):
    """Popup dismissabile (Qt.Popup: si chiude nativamente su Esc, click
    fuori o perdita del focus). options: [(chiave_stile, etichetta), ...],
    chiave "" = Automatico (rimuove l'override)."""

    style_highlighted = Signal(str)
    style_chosen = Signal(str)

    def __init__(self, options: List[Tuple[str, str]], parent=None):
        super().__init__(parent, Qt.Popup)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        self.list_widget = QListWidget()
        self.list_widget.setFont(QFont("Monospace", 9))
        for key, label in options:
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, key)
            self.list_widget.addItem(item)
        layout.addWidget(self.list_widget)
        self.setFocusProxy(self.list_widget)

        self.list_widget.currentItemChanged.connect(self._on_highlight)
        self.list_widget.itemActivated.connect(self._on_activate)
        self.list_widget.itemClicked.connect(self._on_activate)

    def select_first(self):
        """Da chiamare DOPO essersi collegati a style_highlighted/style_chosen,
        cosi' l'anteprima della prima voce non va persa."""
        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)

    def _on_highlight(self, current, _previous):
        if current is not None:
            self.style_highlighted.emit(current.data(Qt.UserRole))

    def _on_activate(self, item):
        self.style_chosen.emit(item.data(Qt.UserRole))
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.list_widget.setFocus()


# ---------------------------------------------------------------------------
# Anteprima audio di un singolo token
# ---------------------------------------------------------------------------

def preview_chord_token(playback: PlaybackEngine, instrument_name: str, token_text: str, tempo_bpm: int,
                        synth_track=None):
    """Riproduce un singolo token (accordo/blocco) usa-e-getta, stesso
    schema di PatternEditorDialog._play_current. token_text e' sempre
    generato internamente da rebuild_token (mai testo scritto dall'utente),
    quindi sintatticamente valido per costruzione: nessuna validazione qui."""
    project = Project(name="preview", tempo_bpm=tempo_bpm)
    copy_synth(project.add_track("Anteprima", instrument_name, f"4: {token_text}"), synth_track)
    playback.play(project, only_audible=False)


# ---------------------------------------------------------------------------
# Identificazione del token sotto al click e ricostruzione del token scelto
# ---------------------------------------------------------------------------

def find_chord_token_at(text: str, char_offset: int, patterns: Dict[str, Pattern],
                         default_octave: int, midi_dir: Optional[str] = None) -> Optional[dict]:
    """Se il token alla posizione char_offset e' un accordo gestibile dal
    popup di voicing, ritorna un dict descrittivo:
      kind: 'implicit' | 'explicit' | 'unrecognized'
      char_start, char_end: posizione del token nel testo ORIGINALE (anche se
        l'accordo si trova annidato dentro un gruppo N(...), vedi sotto)
      chord, anchor_octave, mult, octv_raw: presenti secondo il kind
    'unrecognized' significa "blocco tutto di note ma non riconoscibile
    come accordo standard" (va segnalato, nessun popup). None significa
    "token non gestito da questa funzionalita'" (fallback al comportamento
    nativo dell'editor).

    Se il token individuato e' un gruppo di ripetizione N(...), la ricerca
    prosegue RICORSIVAMENTE nel suo contenuto (i gruppi possono annidare
    altri gruppi), cosi' un doppio click su un accordo scritto dentro un
    gruppo apre lo stesso popup di un accordo a livello di traccia."""
    search_text = text
    base_offset = 0

    for _depth in range(32):  # stesso limite di expand_patterns: mai un ciclo indefinito
        try:
            spans = compute_token_spans(search_text, patterns, midi_dir=midi_dir,
                                         default_octave=default_octave)
        except (NotationError, ValueError):  # testo momentaneamente non valido: nessun popup
            return None
        local_offset = char_offset - base_offset
        char_start = char_end = None
        token = None
        for cs, ce, _beat_start, _beat_dur in spans:
            if cs <= local_offset < ce:
                char_start, char_end, token = cs, ce, search_text[cs:ce]
                break
        if token is None:
            return None

        gm = RE_REPEAT_GROUP.match(token)
        if gm:
            mult_s, inner = gm.groups()
            # posizione di '(' (subito dopo l'eventuale moltiplicatore) + 1 = inizio del contenuto
            base_offset += char_start + len(mult_s) + 1
            search_text = inner
            continue

        vm = RE_VOICES.match(token)
        if vm:
            # blocco di voci: si entra nella voce che contiene il clic
            rel = local_offset - (char_start + 1)
            pos = 0
            for voice_text in split_voices(vm.group(1)):
                if pos <= rel <= pos + len(voice_text):
                    base_offset += char_start + 1 + pos
                    search_text = voice_text
                    break
                pos += len(voice_text) + 1
            else:
                return None
            continue

        token, value = split_note_value(token)
        m = RE_CHORD.match(token)
        if m:
            mult, letter, accidental, suffix, _voicing, bass, octv, _modifier = m.groups()
            symbol = letter + accidental + suffix
            try:
                chord = parse_chord_symbol(symbol)
            except ValueError:
                return None
            return {
                "kind": "implicit",
                "char_start": base_offset + char_start, "char_end": base_offset + char_end,
                "chord": chord, "anchor_octave": int(octv) if octv else default_octave,
                "mult": mult or "", "octv_raw": octv, "bass_raw": bass, "value": value,
            }

        bm = _BLOCK_RE.match(token)
        if bm:
            mult_s, inner_block = bm.groups()
            sub_toks = inner_block.split()
            if not sub_toks:
                return None
            parsed = [RE_NOTE.match(st) for st in sub_toks]
            if not all(parsed):
                return None  # blocco misto (percussione/accordo annidato): fuori scope
            midi_notes = []
            for nm in parsed:
                _n_mult, letter, accidental, mark, _modifier = nm.groups()
                octave = int(mark[1:]) if mark and mark[1:].isdigit() else default_octave
                accidental = "" if accidental in ("n", "♮") else accidental
                midi_notes.append(pitch_to_midi(letter + accidental, octave))
            recognized = recognize_chord(midi_notes)
            if recognized is None:
                return {"kind": "unrecognized",
                        "char_start": base_offset + char_start, "char_end": base_offset + char_end}
            root_pc, quality, anchor_octave = recognized
            symbol = pc_to_letter(root_pc).upper() + quality
            chord = parse_chord_symbol(symbol)
            return {
                "kind": "explicit",
                "char_start": base_offset + char_start, "char_end": base_offset + char_end,
                "chord": chord, "anchor_octave": anchor_octave, "mult": mult_s or "", "value": value,
            }

        return None

    return None

    return None


def rebuild_token(info: dict, instrument: InstrumentProfile, style: str) -> str:
    """Ricostruisce il token per lo stile scelto ('' = Automatico, rimuove
    l'override). Per un token implicito cambia solo il suffisso '.stile',
    lasciando invariati moltiplicatore/ottava originali; per un blocco
    esplicito ricalcola l'intero elenco di note."""
    if info["kind"] == "implicit":
        suffix = f".{style}" if style else ""
        bass_part = f"/{info['bass_raw']}" if info.get("bass_raw") else ""
        octv_part = f"*{info['octv_raw']}" if info["octv_raw"] else ""
        return f"{info['mult']}{info['chord'].symbol}{suffix}{bass_part}{octv_part}{info.get('value', '')}"
    notes = voice_chord(info["chord"], info["anchor_octave"], instrument,
                         voicing_override=(style or None))
    if info.get("bass_raw"):
        notes = apply_bass_note(notes, info["bass_raw"], info["anchor_octave"])
    note_tokens = " ".join(midi_to_token(n) for n in notes)
    return f"{info['mult']}[{note_tokens}]{info.get('value', '')}"


def build_voicing_options(info: dict, instrument: InstrumentProfile) -> List[Tuple[str, str]]:
    """Costruisce le voci del popup: 'Automatico' (nessun override) seguito
    da ogni stile applicabile allo strumento, ciascuna con un'anteprima
    testuale delle note risultanti."""
    def _label(style: str, prefix: str) -> str:
        notes = voice_chord(info["chord"], info["anchor_octave"], instrument,
                             voicing_override=(style or None))
        note_text = " ".join(midi_to_token(n) for n in notes)
        return f"{prefix}  →  {note_text}"

    options = [("", _label("", "Automatico"))]
    for style in applicable_voicings(instrument):
        options.append((style, _label(style, style)))
    return options


# ---------------------------------------------------------------------------
# Orchestrazione: dal doppio click al popup (o al tooltip "non riconosciuto")
# ---------------------------------------------------------------------------

def open_voicing_popup(editor: QPlainTextEdit, info: dict, instrument: InstrumentProfile,
                        instrument_name: str, tempo_bpm: int, playback: PlaybackEngine,
                        global_pos: QPoint, synth_track=None):
    """Apre il popup, collega anteprima audio (debounced) alla navigazione
    e sostituzione del token nell'editor alla scelta."""
    options = build_voicing_options(info, instrument)
    popup = VoicingPickerPopup(options, parent=editor)

    debounce = QTimer(popup)
    debounce.setSingleShot(True)
    debounce.setInterval(VOICING_PREVIEW_DEBOUNCE_MS)
    pending = {"style": ""}

    def _do_preview():
        token = rebuild_token(info, instrument, pending["style"])
        preview_chord_token(playback, instrument_name, token, tempo_bpm, synth_track)

    debounce.timeout.connect(_do_preview)

    def on_highlight(style):
        pending["style"] = style
        debounce.start()

    def on_chosen(style):
        token = rebuild_token(info, instrument, style)
        cursor = editor.textCursor()
        cursor.setPosition(info["char_start"])
        cursor.setPosition(info["char_end"], QTextCursor.KeepAnchor)
        cursor.insertText(token)

    popup.style_highlighted.connect(on_highlight)
    popup.style_chosen.connect(on_chosen)
    popup.move(global_pos)
    popup.show()
    popup.select_first()


def handle_chord_double_click(editor: QPlainTextEdit, text: str, char_offset: int, global_pos: QPoint,
                               patterns: Dict[str, Pattern], instrument: InstrumentProfile,
                               instrument_name: str, tempo_bpm: int, playback: PlaybackEngine,
                               midi_dir: Optional[str] = None, synth_track=None) -> bool:
    """Punto di ingresso unico per un doppio click nell'editor: ritorna True
    se il token era un accordo gestito da questa funzionalita' (popup
    aperto, o tooltip 'non riconosciuto' mostrato), False se il doppio
    click va lasciato al comportamento nativo dell'editor."""
    info = find_chord_token_at(text, char_offset, patterns, instrument.default_octave, midi_dir=midi_dir)
    if info is None:
        return False
    if info["kind"] == "unrecognized":
        QToolTip.showText(
            global_pos,
            tr("Blocco non riconosciuto come accordo standard: nessuna alternativa di voicing disponibile."),
            editor,
        )
        return True
    open_voicing_popup(editor, info, instrument, instrument_name, tempo_bpm, playback, global_pos, synth_track)
    return True
