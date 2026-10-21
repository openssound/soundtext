import os
import time

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QTextCharFormat, QColor, QTextCursor
from PySide6.QtWidgets import QMessageBox, QFileDialog, QTextEdit

from core.notation import validate_track_text
from core import settings as app_settings
from core.tempo_map import (
    build_tempo_beat_map, build_metrica_beat_map, beat_at_elapsed_seconds,
    seconds_for_beats, value_at_beat,
)
from core.i18n import tr
from .file_dialogs import file_dialog_options
from .tempo_spin import tempo_value

TEXT_DIM_INVERT_BG = "#e8c96d"  # colore di sfondo per il token in esecuzione durante la riproduzione


class PlaybackMixin:
    """Riproduzione dell'ensemble: avvio/stop, barra di avanzamento,
    evidenziazione del token corrente nell'editor e gestione SoundFont."""

    # ------------------------------------------------------------ playback

    def toggle_play_pause(self):
        """Pulsante/azione unico Play/Pausa (F5, vedi _build_menu/_build_ui):
        in riproduzione mette in pausa (pause()); altrimenti avvia da capo o
        riprende dal punto dell'ultima pausa (self._playback_paused_beat, vedi
        pause()), a seconda che ci fosse o meno una pausa in corso."""
        if self.playback.is_playing():
            self.pause()
            return
        resume_beat = self._playback_paused_beat if self._playback_paused_beat is not None else 0.0
        loop = self._active_loop_beats()
        if loop is not None and not (loop[0] <= resume_beat < loop[1]):
            resume_beat = loop[0]  # con il loop attivo Play parte da A, non da capo
        self.play(_resume_offset_beats=resume_beat)

    def pause(self):
        """Ferma l'audio ma memorizza il beat raggiunto (self._playback_paused_beat)
        cosi' che il prossimo Play (vedi toggle_play_pause) possa ripartire
        da li' invece che da capo: a differenza di stop(), non azzera barra
        di avanzamento/evidenziazione/testina, che restano congelate sul
        punto di interruzione."""
        if not self.playback.is_playing():
            return
        self._playback_paused_beat = self._current_elapsed_beats()
        self._mixer_restart_timer.stop()
        self._mixer_restart_pending = False
        self.playback.stop()
        self._playback_timer.stop()
        self.metronome_engine.stop()
        self._playback_start_wall = None
        self._set_play_pause_button(playing=False)
        self.statusBar().showMessage(tr("Riproduzione in pausa."), 4000)

    def _set_play_pause_button(self, playing: bool):
        if playing:
            self.play_pause_btn.setText(tr("Pausa"))
            self.play_pause_btn.setToolTip(tr("Mette in pausa la riproduzione (F5)"))
            self.play_pause_action.setText(tr("Pausa"))
        else:
            self.play_pause_btn.setText(tr("Play"))
            self.play_pause_btn.setToolTip(tr("Riproduce l'ensemble, o riprende dal punto di pausa (F5)"))
            self.play_pause_action.setText(tr("Play ensemble"))
        self._refresh_toolbar_icons()

    def _current_elapsed_beats(self) -> float:
        """Beat corrente della riproduzione in corso, in base al cronometro
        avviato da _mark_audio_started: stessa formula usata da
        _update_playback_progress/_perform_pending_mixer_restart/
        _on_metronome_toggled/pause(), centralizzata qui per non doverla
        tenere sincronizzata a mano in ognuno di quei punti."""
        stream_beat = self._stream_position_beats()
        if stream_beat is not None:
            return stream_beat
        if self._playback_start_wall is None:
            return self._playback_offset_beats
        elapsed_since_resume = time.time() - self._playback_start_wall
        return beat_at_elapsed_seconds(
            self._playback_tempo_map, self._playback_offset_beats, elapsed_since_resume)

    def _stream_position_beats(self):
        """Beat che si sta ascoltando secondo il clock del driver audio
        (core.audio_stream), o None se la riproduzione non e' in streaming:
        e' la fonte piu' precisa, e l'unica che segue i salti indietro del
        loop A-B."""
        seconds = self.playback.position_seconds()
        if seconds is None or not self._playback_tempo_map:
            return None
        return beat_at_elapsed_seconds(self._playback_tempo_map, 0.0, seconds)

    def play(self, _resume_offset_beats: float = 0.0):
        self.arrangement_view._stop_preview()   # un solo ascolto alla volta
        self.effects_panel.stop_loop()
        for t in self.project.tracks:
            ok, msg = validate_track_text(t.text, self.project.patterns)
            if not ok:
                QMessageBox.critical(self, tr("Errore di sintassi"),
                                      tr("Impossibile riprodurre: la traccia '{name}' contiene un errore:\n{msg}", name=t.name, msg=msg))
                return
        if not self.playback.backend_available():
            QMessageBox.information(
                self, tr("Sintetizzatore non trovato"),
                tr("Nessun synth MIDI (fluidsynth/timidity/wildmidi) trovato sul sistema.\n"
                "Verra' tentata l'apertura con il player predefinito, oppure installa "
                "'fluidsynth' con un soundfont GM per la riproduzione diretta.")
            )
        from core.playback import describe_playback_engine
        from core.midi_export import compute_project_duration_beats

        engine_desc = describe_playback_engine()
        self._playback_duration_beats = compute_project_duration_beats(self.project)
        self._playback_offset_beats = _resume_offset_beats
        # Mappa di tempo/metrica del brano cosi' com'e' in questo momento:
        # calcolata una volta qui (non ad ogni tick) perche' il progetto non
        # cambia struttura durante l'esecuzione, solo Mute/Solo/Volume (che
        # riavviano comunque play() da capo, vedi _perform_pending_mixer_restart).
        self._playback_tempo_map = build_tempo_beat_map(self.project)
        self._playback_metrica_map = build_metrica_beat_map(self.project)
        # Il cronometro NON parte qui: partirebbe prima che l'audio sia
        # davvero udibile (esportazione MIDI + rendering offline richiedono
        # tempo), causando una barra/evidenziazione sistematicamente "in
        # anticipo" rispetto a cio' che si sente. Parte invece dentro
        # _mark_audio_started, richiamato dal motore di playback nel momento
        # esatto in cui il processo audio viene avviato.
        self._playback_start_wall = None

        for header in self._track_meter_headers():
            header.meter.start()
        self.playback.play(self.project, start_offset_beats=_resume_offset_beats,
                            on_audio_started=self._mark_audio_started,
                            humanize=self.humanize_checkbox.isChecked(),
                            humanize_amount=app_settings.get_humanize_amount(),
                            loop_beats=self._active_loop_beats())
        self._playback_timer.start()
        if self.metronome_checkbox.isChecked():
            # start_immediately=False: come la barra di avanzamento, il primo
            # click deve aspettare che l'audio inizi DAVVERO (vedi
            # _mark_audio_started), non il momento in cui play() e' stato
            # chiamato (l'export MIDI + il rendering offline non sono istantanei).
            self.metronome_engine.start(self._playback_tempo_map, self._playback_metrica_map,
                                          offset_beats=_resume_offset_beats, start_immediately=False)
        self._playback_paused_beat = None
        self._set_play_pause_button(playing=True)
        self.statusBar().showMessage(tr("Riproduzione in corso — {engine_desc}", engine_desc=engine_desc), 8000)
        from core.playback import streaming_available
        if self._active_loop_beats() is not None and not streaming_available():
            self.statusBar().showMessage(
                tr("Il loop richiede la libreria FluidSynth e sounddevice: con il motore di "
                "riproduzione attuale il brano non verra' ripetuto."), 8000)

    def _mark_audio_started(self):
        """Richiamato dal thread di riproduzione (core.playback) nel momento
        esatto in cui l'audio inizia davvero: e' il punto zero corretto da
        cui calcolare il tempo trascorso per barra di avanzamento ed
        evidenziazione. Si limita ad assegnamenti semplici (nessuna chiamata
        a widget Qt), sicuro anche se eseguito da un altro thread."""
        self._playback_start_wall = time.time()
        self.metronome_engine.mark_started()

    def stop(self):
        # Un solo Stop: ferma anche l'ascolto di un box (vista Struttura).
        self.arrangement_view._stop_preview()
        self._mixer_restart_timer.stop()
        self._mixer_restart_pending = False
        self.playback.stop()
        self._playback_timer.stop()
        self.metronome_engine.stop()
        self._playback_start_wall = None
        self._playback_paused_beat = None
        self._set_play_pause_button(playing=False)
        self.playback_progress.setValue(0)
        self.playback_progress.setFormat("00:00 / 00:00")
        self._finish_level_meter()
        self._clear_playback_highlight()
        self.arrangement_view.set_playhead_beat(None)
        # Riporta i campi Tempo/Metrica al valore "a riposo" del progetto
        # (battuta 1): durante l'esecuzione potevano mostrare un cambio
        # successivo (vedi _sync_playback_fields).
        self._sync_playback_fields(self.project.tempo_bpm, self.project.time_sig)
        if not self.level_meter.clipped:   # altrimenti resta l'avviso del clipping
            self.statusBar().showMessage(tr("Riproduzione interrotta."), 4000)

    def closeEvent(self, event):
        # Senza questo override, il thread/processo di riproduzione (fluidsynth
        # e/o il player WAV) resta orfano e continua a suonare fino alla fine
        # anche a finestra chiusa: chiudere l'app deve fermare l'audio come
        # farebbe il pulsante Stop.
        self._mixer_restart_timer.stop()
        self.metronome_engine.stop()
        self.playback.stop()
        self.effects_panel.shutdown()
        from core import plugins
        plugins.shutdown()
        super().closeEvent(event)
        if getattr(self, "_restart_requested", False) and event.isAccepted():
            self._restart_requested = False
            self._restart_app()

    @staticmethod
    def _restart_app():
        """Riavvia SoundText (dopo il cambio di lingua): un nuovo processo
        con gli stessi argomenti, mentre questo si chiude."""
        import sys
        from PySide6.QtCore import QProcess
        from core.version import get_app_root
        if getattr(sys, "frozen", False):
            QProcess.startDetached(sys.executable, sys.argv[1:])
        else:
            main_py = os.path.join(get_app_root(), "main.py")
            QProcess.startDetached(sys.executable, [main_py] + sys.argv[1:])

    @staticmethod
    def _format_mmss(seconds: float) -> str:
        seconds = max(0, int(seconds))
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    def _update_playback_progress(self):
        if self._playback_start_wall is None:
            return
        elapsed_beats_total = self._current_elapsed_beats()
        total_beats = self._playback_duration_beats
        total_seconds = seconds_for_beats(self._playback_tempo_map, total_beats) if total_beats > 0 else 0.0
        elapsed_seconds_total = seconds_for_beats(self._playback_tempo_map, elapsed_beats_total)

        if total_beats > 0:
            pct = max(0, min(100, int(elapsed_beats_total / total_beats * 100)))
        else:
            pct = 0
        self.playback_progress.setValue(pct)
        self.playback_progress.setFormat(
            f"{self._format_mmss(elapsed_seconds_total)} / {self._format_mmss(total_seconds)}"
        )

        self._update_playback_highlight(elapsed_beats_total)
        self.arrangement_view.set_playhead_beat(elapsed_beats_total)
        self._update_level_meter()
        self.metronome_engine.resync()
        self._sync_playback_fields(
            value_at_beat(self._playback_tempo_map, elapsed_beats_total),
            value_at_beat(self._playback_metrica_map, elapsed_beats_total),
        )

        # Fine naturale del brano: ferma timer/barra senza richiedere Stop manuale.
        if total_beats > 0 and elapsed_beats_total >= total_beats + 0.5 and self._active_loop_beats() is None:
            self._playback_timer.stop()
            self.metronome_engine.stop()
            self._playback_start_wall = None
            self._playback_paused_beat = None
            self._set_play_pause_button(playing=False)
            self.playback_progress.setValue(100)
            self._finish_level_meter()
            self._clear_playback_highlight()
            self.arrangement_view.set_playhead_beat(None)
            self._sync_playback_fields(self.project.tempo_bpm, self.project.time_sig)

    def _update_level_meter(self):
        """Livello del master nel punto che si sta ascoltando e spia di
        clipping (vedi core.levels, misurati dal motore prima di suonare)."""
        seconds = self.playback.position_seconds()
        self._update_track_meters(seconds)
        levels = self.playback.master_levels
        if seconds is None or levels is None:
            # audio partito ma senza streaming: niente livelli da mostrare
            self.level_meter.set_available(not (self._playback_start_wall is not None and seconds is None))
            return
        self.level_meter.set_available(True)
        self.level_meter.set_level(levels.peak_between(seconds - 0.06, seconds))
        if levels.clipped_between(seconds - 0.1, seconds):
            self.level_meter.set_clipped(True, self._clip_detail(levels))

    def _track_meter_headers(self):
        from .track_header import TrackHeaderWidget
        return self.findChildren(TrackHeaderWidget)

    def _update_track_meters(self, seconds):
        """Vu-meter delle tracce nel punto che si sta ascoltando (vedi
        PlaybackEngine.track_levels)."""
        levels = self.playback.track_levels
        for header in self._track_meter_headers():
            level = None
            if levels is not None and seconds is not None:
                level = levels.level(header.track_name, seconds - 0.06, seconds)
            if level is None:
                header.meter.silence()
            else:
                header.meter.set_level(level)

    def _clip_detail(self, levels) -> str:
        """'Il master clippa alle battute ...' per i livelli dati (una volta
        sola per rendering)."""
        if self._clip_detail_for is not None and self._clip_detail_for[0] is levels:
            return self._clip_detail_for[1]
        from core.levels import bars_for_seconds, format_bars
        bars = bars_for_seconds(self.project, self._playback_tempo_map,
                                [start for start, _end in levels.clip_regions()])
        text = tr("Il master clippa alle battute: {bars}", bars=format_bars(bars)) if bars else ""
        self._clip_detail_for = (levels, text)
        return text

    def _finish_level_meter(self):
        """Stop o fine del brano: la barra torna a zero, la spia resta; se il
        master ha clippato, lo dice anche nella barra di stato."""
        self.level_meter.silence()
        for header in self._track_meter_headers():
            header.meter.silence()
        if self.level_meter.clipped:
            levels = self.playback.master_levels
            detail = self._clip_detail(levels) if levels is not None else ""
            self.statusBar().showMessage(
                tr("Attenzione: il master clippa (il suono si rompe). Abbassa il volume del master "
                   "o delle tracce piu' forti.") + (" " + detail if detail else ""), 15000)

    def _forget_track_peaks(self):
        """Il brano e' cambiato: i picchi di Analizza livelli non valgono piu'."""
        if not getattr(self, "_track_peaks", None):
            return
        self._track_peaks = {}
        from .track_header import TrackHeaderWidget
        for header in self.findChildren(TrackHeaderWidget):
            header.set_peak(None)

    def analyze_levels(self):
        """Riproduzione -> Analizza livelli: sintetizza ogni traccia da sola e
        il mix (in background, annullabile) e mostra i picchi nelle testate
        delle tracce e un riepilogo (vedi core.levels.analyze_project_levels)."""
        import copy
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QProgressDialog
        from core.levels import analyze_project_levels
        from .worker import Worker
        if getattr(self, "_levels_worker", None) is not None:
            return
        project = copy.deepcopy(self.project)   # il brano puo' cambiare mentre si analizza
        cancelled = {"value": False}
        dialog = QProgressDialog(tr("Analisi dei livelli: ogni traccia viene sintetizzata da sola..."),
                                 tr("Annulla"), 0, 100, self)
        dialog.setWindowTitle(tr("Analizza livelli"))
        dialog.setWindowModality(Qt.WindowModal)
        dialog.setMinimumDuration(0)
        dialog.canceled.connect(lambda: cancelled.__setitem__("value", True))
        worker = Worker(analyze_project_levels, project, stop_check=lambda: cancelled["value"])
        worker.progress.connect(lambda f: dialog.setValue(int(f * 100)))

        def finish() -> bool:
            """Chiude la finestra di avanzamento; True se l'utente aveva
            annullato. Lo stato va letto PRIMA di close(): chiudere una
            QProgressDialog emette canceled, e il risultato si perdeva."""
            was_cancelled = cancelled["value"]
            self._levels_worker = None
            dialog.canceled.disconnect()
            dialog.close()
            return was_cancelled

        def done(report):
            if not finish():
                self._show_level_report(report)

        def failed(message):
            if not finish():
                QMessageBox.warning(self, tr("Analizza livelli"),
                                    tr("Analisi dei livelli non riuscita:\n{message}", message=message))

        worker.finished_ok.connect(done)
        worker.finished_error.connect(failed)
        self._levels_worker = worker
        worker.start()

    def _show_level_report(self, report):
        from core.levels import format_bars
        from .track_header import TrackHeaderWidget
        self._track_peaks = dict(report.tracks)
        for header in self.findChildren(TrackHeaderWidget):
            header.set_peak(self._track_peaks.get(header.track_name))
        lines = []
        if report.master_clip_bars:
            lines.append(tr("Il master clippa per {seconds} s, alle battute {bars}.",
                            seconds=f"{report.master_clip_seconds:.1f}", bars=format_bars(report.master_clip_bars)))
        else:
            lines.append(tr("Il master non clippa (picco {db} dBFS).", db=f"{report.master_peak_db:.1f}"))
        alone = [(n, p) for n, p in report.tracks.items() if p.clip_bars]
        if alone:
            lines.append("")
            lines.append(tr("Clippano anche da sole:"))
            lines += [f"  • {n}: " + tr("battute {bars}", bars=format_bars(p.clip_bars, 6)) for n, p in alone]
        loudest = sorted(report.tracks.items(), key=lambda kv: -kv[1].peak_db)[:5]
        if loudest:
            lines.append("")
            lines.append(tr("Le tracce piu' forti (picco suonate da sole):"))
            lines += [f"  • {n}: {p.peak_db:.1f} dBFS" for n, p in loudest]
        if report.master_clip_bars:
            lines.append("")
            lines.append(tr("Per rimediare abbassa il volume delle tracce che clippano o di quelle piu' "
                            "forti, il volume del master, oppure Suoni -> Volume di sintesi (gain)."))
        QMessageBox.information(self, tr("Analizza livelli"), "\n".join(lines))

    def _update_playback_highlight(self, elapsed_beats: float):
        if not self.current_track_name:
            return
        try:
            track = self.project.get_track(self.current_track_name)
        except KeyError:
            return
        from core.notation import compute_token_spans, find_span_at_beat

        # Richiamata ad ogni tick del timer (100 ms): gli span dipendono solo
        # dal testo della traccia e dai pattern, quindi si ricalcolano solo
        # quando cambiano, invece di ritokenizzare/espandere/parsare l'intera
        # traccia 10 volte al secondo per tutta la riproduzione.
        default_octave = track.instrument.default_octave
        cache_key = (track.text, default_octave,
                     tuple((name, tuple(p.tokens)) for name, p in self.project.patterns.items()))
        cached = self._highlight_spans_cache
        if cached is not None and cached[0] == cache_key:
            spans = cached[1]
        else:
            try:
                spans = compute_token_spans(track.text, self.project.patterns,
                                             default_octave=default_octave, meter=self.project.meter())
            except Exception:
                return
            self._highlight_spans_cache = (cache_key, spans)
        span = find_span_at_beat(spans, elapsed_beats)
        if span is None:
            self._clear_playback_highlight()
            return

        char_start, char_end, _, _ = span
        cursor = self.editor.textCursor()
        cursor.setPosition(char_start)
        cursor.setPosition(char_end, QTextCursor.KeepAnchor)

        fmt = QTextCharFormat()
        # Colori invertiti rispetto al tema: sfondo chiaro, testo scuro.
        fmt.setBackground(QColor(TEXT_DIM_INVERT_BG))
        fmt.setForeground(QColor("#101010"))

        selection = QTextEdit.ExtraSelection()
        selection.cursor = cursor
        selection.format = fmt
        self.editor.setExtraSelections([selection])

        # Scorre l'editor solo se il token evidenziato non e' gia' visibile
        # (ensureCursorVisible e' un no-op altrimenti), senza spostare il
        # cursore di modifica reale dell'utente: si sposta temporaneamente
        # sul cursore del token per calcolare lo scroll necessario, poi si
        # ripristina il cursore originale. NOTA: setTextCursor() in Qt
        # scorre sempre alla posizione del cursore appena impostato (anche
        # quando si ripristina quello salvato!), quindi la sola sequenza
        # "sposta -> scrolla -> ripristina" annullerebbe lo scroll appena
        # fatto; si cattura percio' la posizione di scroll calcolata e la
        # si riapplica dopo il ripristino del cursore.
        scrollbar = self.editor.verticalScrollBar()
        saved_cursor = self.editor.textCursor()
        self.editor.setTextCursor(cursor)
        self.editor.ensureCursorVisible()
        target_scroll = scrollbar.value()
        self.editor.setTextCursor(saved_cursor)
        scrollbar.setValue(target_scroll)

    # ------------------------------------------------------ salto e loop A-B

    def eventFilter(self, obj, event):
        # Click sulla barra di avanzamento: salta al punto corrispondente.
        if (obj is getattr(self, "playback_progress", None)
                and event.type() == QEvent.MouseButtonPress
                and event.button() == Qt.LeftButton):
            width = max(1, obj.width())
            fraction = max(0.0, min(1.0, event.position().x() / width))
            self.seek_to_beat(fraction * self._song_duration_beats())
            return True
        return super().eventFilter(obj, event)

    def _song_duration_beats(self) -> float:
        from core.midi_export import compute_project_duration_beats
        try:
            return compute_project_duration_beats(self.project)
        except Exception:
            return self._playback_duration_beats

    def _position_for_markers(self) -> float:
        """Beat su cui fissare A/B: quello in riproduzione, oppure il punto di
        pausa (o l'inizio del brano se fermo)."""
        if self.playback.is_playing():
            return self._current_elapsed_beats()
        return self._playback_paused_beat or 0.0

    def seek_to_beat(self, beat: float):
        """Salta a 'beat': se si sta suonando riparte da li' (istantaneo in
        streaming, il rendering e' in cache), altrimenti lo memorizza come
        punto di ripresa del prossimo Play e sposta testina/barra."""
        beat = max(0.0, beat)
        if self.playback.is_playing():
            self._mixer_restart_timer.stop()
            self._mixer_restart_pending = False
            self.playback.stop()
            self.metronome_engine.stop()
            self.play(_resume_offset_beats=beat)
            return
        self._playback_paused_beat = beat
        total = self._song_duration_beats()
        tempo_map = build_tempo_beat_map(self.project)
        self.playback_progress.setValue(max(0, min(100, int(beat / total * 100))) if total > 0 else 0)
        self.playback_progress.setFormat(
            f"{self._format_mmss(seconds_for_beats(tempo_map, beat))} / "
            f"{self._format_mmss(seconds_for_beats(tempo_map, total))}")
        self.arrangement_view.set_playhead_beat(beat)
        self.statusBar().showMessage(tr("Il prossimo Play partira' dal beat {beat:.1f}.", beat=beat), 4000)

    def _active_loop_beats(self):
        if (self.loop_action.isChecked() and self._loop_a_beat is not None
                and self._loop_b_beat is not None and self._loop_b_beat > self._loop_a_beat):
            return (self._loop_a_beat, self._loop_b_beat)
        return None

    def set_loop_start(self, *_):
        self._loop_a_beat = float(round(self._position_for_markers()))
        if self._loop_b_beat is not None and self._loop_b_beat <= self._loop_a_beat:
            self._loop_b_beat = None
        self._loop_markers_changed()

    def set_loop_end(self, *_):
        self._loop_b_beat = float(round(self._position_for_markers()))
        if self._loop_a_beat is None:
            self._loop_a_beat = 0.0
        if self._loop_b_beat <= self._loop_a_beat:
            self.statusBar().showMessage(tr("La fine del loop (B) deve venire dopo l'inizio (A)."), 5000)
            self._loop_b_beat = None
        elif not self.loop_action.isChecked():
            self.loop_action.setChecked(True)  # impostare B e' l'intenzione di usare il loop
        self._loop_markers_changed()

    def clear_loop(self, *_):
        self._loop_a_beat = self._loop_b_beat = None
        self.loop_action.setChecked(False)
        self._loop_markers_changed()

    def toggle_loop(self, *_):
        self._loop_markers_changed()

    def _loop_markers_changed(self):
        complete = self._loop_a_beat is not None and self._loop_b_beat is not None
        self.loop_action.setEnabled(complete)
        if not complete and self.loop_action.isChecked():
            self.loop_action.setChecked(False)
        active = self._active_loop_beats()
        self.arrangement_view.set_loop_region(
            (self._loop_a_beat, self._loop_b_beat) if complete else
            ((self._loop_a_beat, None) if self._loop_a_beat is not None else None),
            active=active is not None)
        if self.playback.is_playing():
            from core.playback import streaming_available
            if streaming_available():
                self.playback.set_loop_seconds(None if active is None else (
                    seconds_for_beats(self._playback_tempo_map, active[0]),
                    seconds_for_beats(self._playback_tempo_map, active[1])))
            elif active is not None:
                self.statusBar().showMessage(
                    tr("Il loop richiede la libreria FluidSynth e sounddevice: con il motore di "
                    "riproduzione attuale il brano non verra' ripetuto."), 8000)
                return
        if active is not None:
            self.statusBar().showMessage(tr("Loop attivo: beat {0:.0f} - {1:.0f}.", active[0], active[1]), 5000)
        elif self._loop_a_beat is not None:
            b = f"{self._loop_b_beat:.0f}" if self._loop_b_beat is not None else "?"
            self.statusBar().showMessage(tr("Loop: A = {_loop_a_beat:.0f}, B = {b} (non attivo).", _loop_a_beat=self._loop_a_beat, b=b), 5000)

    def _clear_playback_highlight(self):
        self.editor.setExtraSelections([])

    def _on_mixer_changed(self, track_name):
        """Mute/Solo/Volume/Pan/Master modificati dall'utente: se e' in corso
        una riproduzione, la si riavvia automaticamente dalla posizione
        corrente con le nuove impostazioni, invece di richiedere stop+play
        manuali. Il riavvio vero e proprio e' pero' posticipato (debounce, vedi
        _mixer_restart_timer): trascinando uno slider si riceve un evento per
        ogni tick, e riavviare (stop + ri-export MIDI + re-render offline) ad
        ognuno accoderebbe decine di render sul lock del synth condiviso,
        facendo crescere di molto l'attesa prima di sentire l'ultima
        impostazione scelta. Qui ci si limita a segnare che un riavvio e'
        dovuto; verra' eseguito una sola volta quando l'interazione si ferma."""
        self._mark_dirty(merge_key=f"mixer:{track_name}")
        if self._playback_start_wall is None or not self.playback.is_playing():
            return
        self._mixer_restart_pending = True
        self._mixer_restart_timer.start()

    def _perform_pending_mixer_restart(self):
        """Eseguito dal timer di debounce (vedi _on_mixer_changed) quando
        l'utente ha smesso di modificare Mute/Solo/Volume/Pan/Master da
        almeno _mixer_restart_timer.interval() ms."""
        if not self._mixer_restart_pending:
            return
        self._mixer_restart_pending = False
        if self._playback_start_wall is None or not self.playback.is_playing():
            return
        elapsed_beats = self._current_elapsed_beats()
        if self._playback_duration_beats > 0 and elapsed_beats >= self._playback_duration_beats:
            return  # il brano e' comunque finito, non serve riavviare
        self.playback.stop()
        self.play(_resume_offset_beats=elapsed_beats)

    def choose_soundfont(self):
        from core.project_io import ensure_soundfonts_dir
        path, _ = QFileDialog.getOpenFileName(self, tr("Scegli file SoundFont"), ensure_soundfonts_dir(),
                                              tr("SoundFont (*.sf2)"),
                                              options=file_dialog_options())
        if not path:
            return
        app_settings.set_soundfont_path(path)
        self.statusBar().showMessage(tr("SoundFont impostato: {path}", path=path), 6000)
        QMessageBox.information(self, tr("SoundFont impostato"),
                                 tr("Verra' usato per la riproduzione:\n{path}", path=path))

    def reset_soundfont(self):
        app_settings.clear_soundfont_path()
        self.statusBar().showMessage(tr("Rilevamento automatico del SoundFont ripristinato."), 4000)

    def show_soundfont_info(self):
        from core.playback import get_active_soundfont_info, describe_playback_engine
        path, is_manual = get_active_soundfont_info()
        if path:
            origin = tr("impostato manualmente") if is_manual else tr("rilevato automaticamente")
            QMessageBox.information(
                self, tr("SoundFont in uso"),
                tr("{path}\n({origin})\n\nMotore di riproduzione: {0}", describe_playback_engine(), path=path, origin=origin)
            )
        else:
            QMessageBox.warning(
                self, tr("Nessun SoundFont trovato"),
                tr("Non e' stato trovato nessun file .sf2, ne' nei percorsi standard ne' "
                "impostato manualmente.\n\nUsa 'Playback → Scegli SoundFont (.sf2)...' "
                "per indicarne uno (ad es. FluidR3_GM.sf2), oppure installa un pacchetto "
                "SoundFont di sistema.")
            )

    # -------------------------------------------------------- campi Tempo/Metrica

    def _sync_playback_fields(self, bpm, time_sig):
        """Aggiorna i campi Tempo/Metrica della toolbar per riflettere il
        valore in vigore in questo momento della riproduzione (che puo'
        differire da quello 'a riposo' del progetto se ci sono cambi di
        tempo/metrica), senza far scattare _on_tempo_changed/_on_metrica_changed
        (che altrimenti riscriverebbero il valore di battuta 1 del progetto)."""
        if bpm is not None and self.tempo_spin.bpm() != tempo_value(bpm):
            self.tempo_spin.blockSignals(True)
            self.tempo_spin.setValue(bpm)
            self.tempo_spin.blockSignals(False)
        if time_sig is not None and self.metrica_combo.currentText() != time_sig:
            self.metrica_combo.blockSignals(True)
            self.metrica_combo.setCurrentText(time_sig)
            self.metrica_combo.blockSignals(False)

    # -------------------------------------------------------------- metronomo

    def _on_metronome_toggled(self, checked):
        if checked and self.playback.is_playing():
            current_beat = self._current_elapsed_beats()
            # start_immediately=True: la riproduzione e' gia' in corso (audio
            # gia' avviato), quindi il riferimento temporale del click va
            # fissato subito, non aspettato da mark_started() (che qui non
            # verrebbe piu' richiamato da _mark_audio_started).
            self.metronome_engine.start(self._playback_tempo_map, self._playback_metrica_map,
                                          offset_beats=current_beat, start_immediately=True)
        else:
            self.metronome_engine.stop()

    def show_metronome_settings(self):
        from .metronome_dialog import MetronomeSettingsDialog
        dlg = MetronomeSettingsDialog(self)
        dlg.exec()

    def show_playback_gain_settings(self):
        from .playback_gain_dialog import PlaybackGainDialog
        dlg = PlaybackGainDialog(self)
        dlg.exec()

    # -------------------------------------------------------------- umanizzazione

    def _on_humanize_toggled(self, checked):
        """A differenza del metronomo (motore audio separato, avviabile/
        fermabile all'istante), umanizzazione agisce sul render MIDI stesso:
        attivarla/disattivarla durante l'esecuzione richiede un riavvio
        (riusa lo stesso meccanismo di debounce gia' usato per Mute/Solo/
        Volume/Pan, vedi _on_mixer_changed)."""
        app_settings.set_humanize_enabled(checked)
        self._on_mixer_changed(None)

    def show_humanize_settings(self):
        from .humanize_dialog import HumanizeSettingsDialog
        dlg = HumanizeSettingsDialog(self)
        dlg.exec()
