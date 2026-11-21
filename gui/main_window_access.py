"""Accessibilita' per chi non vede o vede poco (docs, sezione 6): annunci per lo screen reader, «Dove sono?», «Vai
all'errore successivo/precedente» e i tre modi di ascoltare il punto in cui si e' (la nota o l'accordo sotto il
cursore, la battuta, dal cursore). Il testo e' gia' la forma ideale per chi non vede: qui si rende accessibile cio' che
gli sta intorno.
"""

import bisect

from PySide6.QtGui import QAccessible, QAccessibleAnnouncementEvent

from core.i18n import current_language, tr
from core.notation import compute_token_spans
from core.speech_text import token_words
from st_language.notation import bar_starts

from . import selection_actions


def announce(widget, text: str):
    """Fa leggere 'text' allo screen reader (se ce n'e' uno attivo), senza spostare il fuoco."""
    if not text:
        return
    try:
        QAccessible.updateAccessibility(QAccessibleAnnouncementEvent(widget, text))
    except Exception:                    # un sistema senza accessibilita': il messaggio resta a vista
        pass


def beat_name(beat_in_bar: float) -> str:
    """«primo tempo», «terzo tempo»: il battito della battuta (da 0) in parole, o «tempo 2,5»."""
    ordinal = {0: tr("primo"), 1: tr("secondo"), 2: tr("terzo"), 3: tr("quarto"), 4: tr("quinto"), 5: tr("sesto"),
               6: tr("settimo")}
    whole = int(beat_in_bar + 1e-6)
    if abs(beat_in_bar - whole) < 1e-6 and whole in ordinal:
        return tr("{n} tempo", n=ordinal[whole])
    return tr("tempo {n}", n=f"{beat_in_bar + 1:g}")


class AccessibilityMixin:
    # ------------------------------------------------------------ annunci

    def _setup_accessibility(self):
        """Ogni messaggio della barra di stato (salvato, esportato, errore...) si annuncia, non solo si mostra."""
        self.statusBar().messageChanged.connect(lambda message: announce(self, message))
        self._validation_issues = []         # [(char_start, messaggio)] della traccia corrente

    def announce(self, text: str):
        announce(self, text)

    # ------------------------------------------------------------ dove sono

    def _editing_track(self):
        track = self._editable_track() if hasattr(self, "_editable_track") else None
        return track

    def _token_spans(self, track, text):
        try:
            return compute_token_spans(text, self.project.patterns, default_octave=track.instrument.default_octave,
                                       meter=self.project.meter())
        except Exception:
            return []

    def _bar_of(self, beat: float):
        """(numero della battuta da 1, battito dentro la battuta)."""
        starts = []
        for start in bar_starts(self.project.time_sig, self.project.metrica_changes, self.project.pickup):
            starts.append(float(start))
            if starts[-1] > beat + 1e-6 or len(starts) > 100000:
                break
        i = max(0, bisect.bisect_right(starts, beat + 1e-6) - 1)
        return i + 1, beat - starts[i]

    def where_am_i_text(self):
        """«Melodia, battuta 5, terzo tempo, accordo La minore, box Ritornello», o None se non c'e' una traccia di note."""
        track = self._editing_track()
        if track is None:
            return None
        text = self.editor.toPlainText()
        pos = self.editor.textCursor().position()
        spans = self._token_spans(track, text)
        here = next((s for s in spans if s[0] <= pos <= s[1]), None)
        if here is None:
            before = [s for s in spans if s[1] <= pos]
            here = before[-1] if before else None
        parts = [track.name]
        if here is None:
            return ", ".join(parts + [tr("nessuna nota qui")])
        bar, in_bar = self._bar_of(here[2])
        parts += [tr("battuta {n}", n=bar), beat_name(in_bar)]
        word = token_words(text[here[0]:here[1]], here[3], current_language())
        if word:
            parts.append(word)
        clip = next((c for c in track.clips if c.start_beat - 1e-6 <= here[2] < c.start_beat + self._clip_length(track, c) - 1e-6), None)
        if clip is not None and clip.name:
            parts.append(tr("box {name}", name=clip.name))
        return ", ".join(parts)

    def _clip_length(self, track, clip) -> float:
        from core.arrangement import clip_duration_beats
        try:
            return clip_duration_beats(clip.text, self.project.patterns, track.instrument.default_octave,
                                       start_beat=clip.start_beat, meter=self.project.meter())
        except Exception:
            return 0.0

    def where_am_i(self):
        said = self.where_am_i_text()
        message = said or tr("Qui non c'e' una traccia di note.")
        self.statusBar().showMessage(message, 6000)
        announce(self, message)

    # ------------------------------------------------------------ errori

    def go_to_issue(self, direction: int):
        """F8 / Maiusc+F8: il cursore va all'errore o all'avviso successivo (precedente) e il messaggio si annuncia."""
        issues = sorted(getattr(self, "_validation_issues", []))
        if not issues:
            message = tr("Nessun errore in questa traccia.")
            self.statusBar().showMessage(message, 4000)
            announce(self, message)
            return
        pos = self.editor.textCursor().position()
        if direction > 0:
            target = next((i for i in issues if i[0] > pos), issues[0])
        else:
            target = next((i for i in reversed(issues) if i[0] < pos), issues[-1])
        cursor = self.editor.textCursor()
        cursor.setPosition(target[0])
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()
        self.statusBar().showMessage(target[1], 8000)
        announce(self, target[1])

    # ------------------------------------------------------------ ascoltare il punto in cui si e'

    def _play_range(self, start: int, end: int):
        track = self._editing_track()
        if track is None:
            self.statusBar().showMessage(tr("Qui non c'e' una traccia di note."), 4000)
            return
        text = self.editor.toPlainText()
        selected = text[start:end]
        if not selected.strip():
            announce(self, tr("Niente da ascoltare qui."))
            return
        self.playback.stop()
        selection_actions._play_selection(
            self.editor, self.playback, self.project.patterns, track.instrument_name, self.project.tempo_bpm, text, start,
            selected, track.instrument.default_octave, None, track, host_project=self.project)

    def play_token_at_cursor(self):
        """La nota o l'accordo sotto il cursore."""
        track = self._editing_track()
        if track is None:
            return self._play_range(0, 0)
        text = self.editor.toPlainText()
        pos = self.editor.textCursor().position()
        spans = self._token_spans(track, text)
        here = next((s for s in spans if s[0] <= pos <= s[1]), None)
        if here is None:
            before = [s for s in spans if s[1] <= pos]
            here = before[-1] if before else None
        if here is None:
            return self._play_range(0, 0)
        self._play_range(here[0], here[1])

    def play_bar_at_cursor(self):
        """La battuta del cursore: il testo fra due stanghette |."""
        text = self.editor.toPlainText()
        pos = self.editor.textCursor().position()
        start = text.rfind("|", 0, pos) + 1
        end = text.find("|", pos)
        end = len(text) if end < 0 else end
        line_start = text.rfind("\n", 0, pos) + 1
        start = max(start, line_start) if text.rfind("|", 0, pos) < line_start else start
        self._play_range(start, end)

    def play_from_cursor(self):
        """Dal cursore alla fine del testo della traccia."""
        text = self.editor.toPlainText()
        self._play_range(self.editor.textCursor().position(), len(text))

    def _record_issues(self, track, issues, ok: bool, message: str):
        """Chiamata da _validate_current: gli errori della traccia, per F8 e Maiusc+F8."""
        found = [(i.char_start, i.message) for i in issues]
        if not ok and message:
            found.append((0, message))
        self._validation_issues = found
