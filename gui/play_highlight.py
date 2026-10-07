"""
Evidenziazione, in un editor di testo, del token che si sta ascoltando
mentre un PlaybackEngine riproduce quel testo (anteprime dei dialoghi di
generazione, del box, della tastiera e della conversione audio). Stesso aspetto e stessa
tecnica di scorrimento dell'editor principale
(gui.main_window_playback._update_playback_highlight).

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

from .main_window_playback import TEXT_DIM_INVERT_BG

PLAY_HIGHLIGHT_INTERVAL_MS = 100


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
        text = self.editor.toPlainText()
        try:
            # Sul testo intero dell'editor, non su quello ripulito dagli spazi
            # passato a project: gli offset devono corrispondere al documento.
            self._spans = compute_token_spans(text, patterns, midi_dir=midi_dir, default_octave=default_octave,
                                              meter=project.meter(), origin_beat=lead_beats)
        except Exception:
            self._spans = None
        self._text = text
        self._lead_beats = lead_beats
        self._tempo_map = build_tempo_beat_map(project, midi_dir=midi_dir)
        if lead_beats:
            play_kwargs["start_offset_beats"] = lead_beats
        self.playback.play(project, on_audio_started=self._mark_audio_started, **play_kwargs)
        self._timer.start()

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
        cursor = self.editor.textCursor()
        cursor.setPosition(char_start)
        cursor.setPosition(char_end, QTextCursor.KeepAnchor)
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(TEXT_DIM_INVERT_BG))
        fmt.setForeground(QColor("#101010"))
        selection = QTextEdit.ExtraSelection()
        selection.cursor = cursor
        selection.format = fmt
        self.editor.setExtraSelections([selection])

        # Scorre solo se il token non e' gia' visibile, senza spostare il
        # cursore dell'utente (vedi gui.box_edit_dialog._update_play_highlight).
        scrollbar = self.editor.verticalScrollBar()
        saved_cursor = self.editor.textCursor()
        self.editor.setTextCursor(cursor)
        self.editor.ensureCursorVisible()
        target_scroll = scrollbar.value()
        self.editor.setTextCursor(saved_cursor)
        scrollbar.setValue(target_scroll)
