"""
Evidenziazione, in un editor di testo, del token che si sta ascoltando:
nell'editor della finestra principale (TrackPlayHighlight, durante
l'ascolto del brano) e nei dialoghi (PlayHighlighter: anteprime di
generazione, del box, della tastiera e della conversione audio), con lo
stesso aspetto e la stessa tecnica di scorrimento (show_playing_token).

La posizione si legge dal clock del driver audio quando la riproduzione
passa da core.audio_stream (PlaybackEngine.position_seconds), altrimenti da
un cronometro avviato quando l'audio parte davvero (on_audio_started), e si
converte in beat con la mappa dei tempi del progetto riprodotto: le
anteprime possono suonare insieme alle altre tracce, con i loro cambi di
tempo.
"""

import time
import weakref

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QTextEdit

from core.notation import compute_token_spans, find_span_at_beat
from core.tempo_map import beat_at_elapsed_seconds, build_tempo_beat_map

TEXT_DIM_INVERT_BG = "#e8c96d"  # colore di sfondo per il token in esecuzione durante la riproduzione
PLAY_HIGHLIGHT_INTERVAL_MS = 100


def show_playing_token(editor, char_start: int, char_end: int, scroll_editor=None):
    """Evidenzia in 'editor' il token [char_start, char_end) che si sta
    ascoltando (colori invertiti rispetto al tema: sfondo chiaro, testo
    scuro) e fa scorrere scroll_editor (di solito lo stesso editor) solo se
    il token non e' gia' visibile.

    Lo scorrimento non sposta il cursore di modifica dell'utente: si sposta
    temporaneamente sul cursore del token per calcolare lo scroll
    necessario, poi si ripristina il cursore originale. setTextCursor() in Qt
    scorre sempre alla posizione del cursore appena impostato (anche quando
    si ripristina quello salvato), quindi la sola sequenza "sposta ->
    scrolla -> ripristina" annullerebbe lo scroll appena fatto: si cattura
    percio' la posizione calcolata e la si riapplica dopo il ripristino."""
    cursor = editor.textCursor()
    cursor.setPosition(char_start)
    cursor.setPosition(char_end, QTextCursor.KeepAnchor)
    fmt = QTextCharFormat()
    fmt.setBackground(QColor(TEXT_DIM_INVERT_BG))
    fmt.setForeground(QColor("#101010"))
    selection = QTextEdit.ExtraSelection()
    selection.cursor = cursor
    selection.format = fmt
    editor.setExtraSelections([selection])

    scroll_editor = scroll_editor or editor
    scrollbar = scroll_editor.verticalScrollBar()
    saved_cursor = scroll_editor.textCursor()
    scroll_editor.setTextCursor(cursor)
    scroll_editor.ensureCursorVisible()
    target_scroll = scrollbar.value()
    scroll_editor.setTextCursor(saved_cursor)
    scrollbar.setValue(target_scroll)


class TrackPlayHighlight:
    """Il token della traccia selezionata che si sta ascoltando, evidenziato
    nell'editor della finestra principale (o in quello con i pattern espansi,
    se Espandi i pattern e' acceso: ha lo stesso tempo del testo della
    traccia, vedi _sync_expanded_patterns). La finestra lo possiede
    (MainWindow.track_highlight) e lo chiama a ogni scatto della barra di
    avanzamento."""

    def __init__(self, window):
        self.window = window
        # (chiave, span) dell'ultimo testo evidenziato: gli span dipendono solo
        # dal testo della traccia e dai pattern, quindi si ricalcolano solo
        # quando cambiano, invece di ritokenizzare/espandere/parsare l'intera
        # traccia 10 volte al secondo per tutta la riproduzione.
        self._spans_cache = None

    def update(self, elapsed_beats: float):
        window = self.window
        if not window.current_track_name:
            return
        project = window.project
        track = project.find_track(window.current_track_name)
        if track is None:
            return
        expanded = window.expand_patterns_check.isChecked()
        editor = window.expanded_editor if expanded else window.editor
        text = editor.toPlainText() if expanded else track.text
        default_octave = track.instrument.default_octave
        cache_key = (text, default_octave,
                     tuple((name, tuple(p.tokens)) for name, p in project.patterns.items()))
        cached = self._spans_cache
        if cached is not None and cached[0] == cache_key:
            spans = cached[1]
        else:
            try:
                spans = compute_token_spans(text, project.patterns,
                                            default_octave=default_octave, meter=project.meter())
            except Exception:
                return
            self._spans_cache = (cache_key, spans)
        span = find_span_at_beat(spans, elapsed_beats)
        if span is None:
            self.clear()
            return
        char_start, char_end, _, _ = span
        (window.editor if expanded else window.expanded_editor).setExtraSelections([])
        show_playing_token(editor, char_start, char_end, scroll_editor=window.editor)

    def clear(self):
        self.window.editor.setExtraSelections([])
        self.window.expanded_editor.setExtraSelections([])


class PlayHighlighter(QObject):
    """Da usare al posto di playback.play() per il testo di editor:
    play(project, ...) avvia la riproduzione e l'evidenziazione, stop() le
    ferma entrambe. Il PlaybackEngine e' l'attributo playback_attr di owner,
    letto ogni volta (owner puo' sostituirlo, es. nei test); owner e' tenuto
    con un riferimento debole, per non creare un ciclo con il dialogo che
    possiede l'editor (vedi gui.voicing_picker._WeakCallback)."""

    def __init__(self, editor, owner, playback_attr: str):
        super().__init__(editor)
        self.editor = editor
        self._owner = weakref.ref(owner)
        self._playback_attr = playback_attr
        self._text = None          # testo dell'editor congelato all'avvio
        self._spans = None
        self._span_args = None
        self._lead_beats = 0.0
        self._tempo_map = None
        self._start_wall = None
        self._timer = QTimer(self)
        self._timer.setInterval(PLAY_HIGHLIGHT_INTERVAL_MS)
        self._timer.timeout.connect(self._update)

    @property
    def playback(self):
        return getattr(self._owner(), self._playback_attr)

    def play(self, project, patterns, default_octave: int, midi_dir=None, lead_beats: float = 0.0,
             **play_kwargs):
        """Riproduce project, evidenziando nell'editor i token del suo testo
        attuale (quello della traccia di project che lo contiene, da beat 0).
        lead_beats: la traccia di project ha davanti al testo dell'editor una
        pausa di tanti beat (vedi core.arrangement.anchored_preview_text):
        l'ascolto parte da li' e le ancore bar=N contano da li'."""
        self.stop()
        self._span_args = (patterns, midi_dir, default_octave, project.meter())
        self._lead_beats = lead_beats
        self._compute_spans()
        self._tempo_map = build_tempo_beat_map(project, midi_dir=midi_dir)
        if lead_beats:
            play_kwargs["start_offset_beats"] = lead_beats
        self.playback.play(project, on_audio_started=self._mark_audio_started, **play_kwargs)
        self._timer.start()

    def _compute_spans(self):
        patterns, midi_dir, default_octave, meter = self._span_args
        text = self.editor.toPlainText()
        try:
            # Sul testo intero dell'editor, non su quello ripulito dagli spazi
            # passato a project: gli offset devono corrispondere al documento.
            self._spans = compute_token_spans(text, patterns, midi_dir=midi_dir, default_octave=default_octave,
                                              meter=meter, origin_beat=self._lead_beats)
        except Exception:
            self._spans = None
        self._text = text

    def follow_editor(self, editor):
        """Evidenzia d'ora in poi in 'editor' (con lo stesso tempo del testo
        che suona, es. lo stesso box con i pattern espansi, vedi
        gui.box_edit_dialog), anche a riproduzione in corso."""
        self.editor.setExtraSelections([])
        self.editor = editor
        if self._text is not None:
            self._compute_spans()

    def stop(self):
        self.playback.stop()
        self._timer.stop()
        self._text = None
        self._start_wall = None
        self.editor.setExtraSelections([])

    def is_active(self) -> bool:
        return self._timer.isActive()

    def _mark_audio_started(self):
        # Chiamato dal thread di riproduzione: nessun widget Qt qui.
        self._start_wall = time.time()

    def _elapsed_beats(self):
        """Beat del testo dell'editor (0 = il suo inizio) che si sta ascoltando."""
        lead = self._lead_beats
        seconds = self.playback.position_seconds()     # dall'inizio del brano
        if seconds is not None:
            return beat_at_elapsed_seconds(self._tempo_map, 0.0, seconds) - lead
        if self._start_wall is None:
            return None
        # cronometro: parte con l'audio, cioe' da lead_beats
        return beat_at_elapsed_seconds(self._tempo_map, lead, time.time() - self._start_wall) - lead

    def _update(self):
        if self._start_wall is None and self.playback.position_seconds() is None:
            # Esportazione e rendering non sono istantanei: finche' l'audio
            # non parte, is_playing() e' ancora False senza che sia finita.
            return
        if not self.playback.is_playing():
            self.stop()
            return
        # Testo cambiato mentre suona (rigenerato o modificato a mano): gli
        # offset non valgono piu' per il documento, si smette di evidenziare
        # fino al prossimo ascolto.
        if self._spans is None or self.editor.toPlainText() != self._text:
            self.editor.setExtraSelections([])
            return
        beat = self._elapsed_beats()
        span = find_span_at_beat(self._spans, beat) if beat is not None else None
        if span is None:
            self.editor.setExtraSelections([])
            return

        char_start, char_end, _, _ = span
        show_playing_token(self.editor, char_start, char_end)
