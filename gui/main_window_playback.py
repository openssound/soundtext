import os
import time

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QMessageBox

from core.notation import validate_track_text
from core import settings as app_settings
from core.tempo_map import (
    build_tempo_beat_map, build_metrica_beat_map, beat_at_elapsed_seconds,
    seconds_for_beats, value_at_beat,
)
from core.i18n import tr
from .tempo_spin import tempo_value


class PlaybackMixin:
    """Riproduzione dell'ensemble: avvio/stop, barra di avanzamento,
    evidenziazione del token corrente nell'editor e gestione SoundFont."""

    # ------------------------------------------------------------ playback

    def analyze_levels(self):
        """Riproduzione -> Analizza livelli (vedi gui.level_monitor)."""
        self.levels.analyze()

    def toggle_play_pause(self):
        """Pulsante/azione unico Play/Pausa (F5, vedi _build_menu/_build_ui):
        in riproduzione mette in pausa (pause()); altrimenti avvia da capo o
        riprende dal punto dell'ultima pausa (self._playback_paused_beat, vedi
        pause()), a seconda che ci fosse o meno una pausa in corso."""
        if self.playback.is_playing():
            self.pause()
            return
        resume_beat = self._playback_paused_beat if self._playback_paused_beat is not None else 0.0
        loop = self.loop.active()
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
        if self._playback_start_wall is None:   # ancora in preparazione: via "Preparazione…"
            self.playback_progress.setFormat(self._time_text(self._playback_paused_beat))
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

    def _show_preparing(self):
        """Riscontro immediato del Play: Pausa sul pulsante e
        "Preparazione…" sul tempo, disegnati subito. Quello che segue in
        play() (controllo della sintassi, esportazione MIDI, mappe di tempo)
        gira sul thread della GUI e su un brano lungo dura anche mezzo
        secondo: senza ridisegnare qui, il pulsante cambiava solo alla fine,
        e il rendering che viene dopo (in un thread) lasciava il tempo fermo
        su 00:00 finche' non partiva l'audio."""
        self._set_play_pause_button(playing=True)
        self.playback_progress.setFormat(tr("Preparazione…"))
        self.statusBar().showMessage(tr("Preparazione dell'ascolto…"))
        for widget in (self.play_pause_btn, self.time_display, self.statusBar()):
            widget.repaint()

    def play(self, _resume_offset_beats: float = 0.0):
        self.flush_validation()                  # gli errori della traccia scritta adesso
        self.arrangement_view._stop_preview()   # un solo ascolto alla volta
        self.effects_panel.stop_loop()
        previous_time = self.playback_progress.format()
        self._show_preparing()
        for t in self.project.tracks:
            ok, msg = validate_track_text(t.text, self.project.patterns)
            if not ok:
                self._set_play_pause_button(playing=False)
                self.playback_progress.setFormat(previous_time)
                self.statusBar().clearMessage()
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
        self._playback_tempo_map = self._tempo_map_as_heard()
        self._playback_metrica_map = build_metrica_beat_map(self.project)
        # Il cronometro NON parte qui: partirebbe prima che l'audio sia
        # davvero udibile (esportazione MIDI + rendering offline richiedono
        # tempo), causando una barra/evidenziazione sistematicamente "in
        # anticipo" rispetto a cio' che si sente. Parte invece dentro
        # _mark_audio_started, richiamato dal motore di playback nel momento
        # esatto in cui il processo audio viene avviato.
        self._playback_start_wall = None

        self.levels.start()
        self.playback.play(self.project, start_offset_beats=_resume_offset_beats,
                            on_audio_started=self._mark_audio_started,
                            humanize=self.humanize_checkbox.isChecked(),
                            humanize_amount=app_settings.get_humanize_amount(),
                            loop_beats=self.loop.active())
        self._playback_timer.start()
        if self.metronome_checkbox.isChecked():
            # start_immediately=False: come la barra di avanzamento, il primo
            # click deve aspettare che l'audio inizi DAVVERO (vedi
            # _mark_audio_started), non il momento in cui play() e' stato
            # chiamato (l'export MIDI + il rendering offline non sono istantanei).
            self.metronome_engine.start(self._metronome_tempo_map(), self._playback_metrica_map,
                                          offset_beats=_resume_offset_beats, start_immediately=False)
        self._playback_paused_beat = None
        self.statusBar().showMessage(tr("Riproduzione in corso — {engine_desc}", engine_desc=engine_desc), 8000)
        silent = self.silent_tracks_message()
        if silent:
            self.statusBar().showMessage(silent, 15000)
        from core.playback import streaming_available
        if self.loop.active() is not None and not streaming_available():
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
        self.levels.finish()
        self.track_highlight.clear()
        self._show_beat_in_score(None)
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
        from core import disk_cache, plugins
        plugins.shutdown()
        disk_cache.wait_writes(5.0)        # i rendering in scrittura nella cache su disco
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

    def _time_text(self, elapsed_beats: float) -> str:
        """'mm:ss / mm:ss' del beat elapsed_beats sulla durata del brano."""
        total_beats = self._playback_duration_beats
        total_seconds = seconds_for_beats(self._playback_tempo_map, total_beats) if total_beats > 0 else 0.0
        elapsed_seconds = seconds_for_beats(self._playback_tempo_map, elapsed_beats)
        return f"{self._format_mmss(elapsed_seconds)} / {self._format_mmss(total_seconds)}"

    def _update_playback_progress(self):
        if self._playback_start_wall is None:
            if not self.playback.is_playing():
                # finito senza mai far partire l'audio (nessun motore, rendering
                # fallito): non si resta su "Preparazione…" con Pausa acceso
                self.stop()
                return
            # l'audio non e' ancora partito: si stanno preparando le tracce
            # con effetti o strumenti plugin (con i profili NAM anche un minuto)
            # o si renderizza il brano
            prepared = getattr(self.playback, "stem_progress", None)
            if prepared:
                done, total = prepared
                self.playback_progress.setValue(int(done / max(1, total) * 100))
                self.playback_progress.setFormat(
                    tr("Preparo strumenti ed effetti… {done} di {total}", done=done, total=total))
            else:
                self.playback_progress.setFormat(tr("Preparazione…"))
            return
        elapsed_beats_total = self._current_elapsed_beats()
        total_beats = self._playback_duration_beats
        total_seconds = seconds_for_beats(self._playback_tempo_map, total_beats) if total_beats > 0 else 0.0
        if total_beats > 0 and self.loop.active() is None:
            elapsed_beats_total = min(elapsed_beats_total, total_beats + 0.5)   # la coda dopo la fine: la barra resta li'
        elapsed_seconds_total = min(seconds_for_beats(self._playback_tempo_map, elapsed_beats_total),
                                    total_seconds if total_beats > 0 else float("inf"))

        if total_beats > 0:
            pct = max(0, min(100, int(elapsed_beats_total / total_beats * 100)))
        else:
            pct = 0
        self.playback_progress.setValue(pct)
        self.playback_progress.setFormat(
            f"{self._format_mmss(elapsed_seconds_total)} / {self._format_mmss(total_seconds)}"
        )

        self.track_highlight.update(elapsed_beats_total)
        self._show_beat_in_score(elapsed_beats_total)
        self.arrangement_view.set_playhead_beat(elapsed_beats_total)
        self.levels.update()
        self.metronome_engine.resync()
        self._sync_playback_fields(
            value_at_beat(self._playback_tempo_map, elapsed_beats_total),
            value_at_beat(self._playback_metrica_map, elapsed_beats_total),
        )

        # Fine naturale del brano: ferma timer/barra senza richiedere Stop
        # manuale, ma solo quando l'audio e' davvero finito (la coda del
        # riverbero suona ancora dopo l'ultima nota: fino ad allora si resta
        # "in riproduzione" e Stop la ferma).
        if total_beats > 0 and elapsed_beats_total >= total_beats + 0.5 and self.loop.active() is None:
            self.metronome_engine.stop()          # niente click sulla coda
            if self.playback.is_playing():
                return
            self._playback_timer.stop()
            self._playback_start_wall = None
            self._playback_paused_beat = None
            self._set_play_pause_button(playing=False)
            self.playback_progress.setValue(100)
            self.levels.finish()
            self.track_highlight.clear()
            self._show_beat_in_score(None)
            self.arrangement_view.set_playhead_beat(None)
            self._sync_playback_fields(self.project.tempo_bpm, self.project.time_sig)

    def _show_beat_in_score(self, beat):
        """Le note che suonano evidenziate nella vista Partitura, se e' stata
        aperta (gui.score_view.ScoreDialog.show_playing_beat); None le spegne."""
        score = getattr(self, "_score_dialog", None)
        if score is not None:
            score.show_playing_beat(beat)

    # ------------------------------------------------------ salto e loop A-B

    def eventFilter(self, obj, event):
        # Clic sulla riga della sintassi: il cursore va al primo avviso
        if (obj is getattr(self, "validation_label", None) and event.type() == QEvent.MouseButtonPress
                and event.button() == Qt.LeftButton):
            self.jump_to_first_issue()
            return True
        # Click sulla barra di avanzamento: salta al punto corrispondente.
        if (obj is getattr(self, "playback_progress", None)
                and event.type() == QEvent.MouseButtonPress
                and event.button() == Qt.LeftButton):
            width = max(1, obj.width())
            fraction = max(0.0, min(1.0, event.position().x() / width))
            self.seek_to_beat(fraction * self._song_duration_beats())
            return True
        return super().eventFilter(obj, event)

    def _tempo_map_as_heard(self):
        """La mappa del tempo del brano come suona: con le corone ($fermata),
        che l'esportazione MIDI rallenta (vedi core.midi_export); senza, dopo
        una corona tempo, barra e testina restano indietro rispetto all'audio
        (e alla fine il brano risulta finito mentre la corona suona ancora)."""
        from core.tempo_map import song_tempo_beat_map_heard
        try:
            return song_tempo_beat_map_heard(self.project)
        except Exception:
            return build_tempo_beat_map(self.project)

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
        tempo_map = self._tempo_map_as_heard()
        self.playback_progress.setValue(max(0, min(100, int(beat / total * 100))) if total > 0 else 0)
        self.playback_progress.setFormat(
            f"{self._format_mmss(seconds_for_beats(tempo_map, beat))} / "
            f"{self._format_mmss(seconds_for_beats(tempo_map, total))}")
        self.arrangement_view.set_playhead_beat(beat)
        self.statusBar().showMessage(tr("Il prossimo Play partira' dal beat {beat:.1f}.", beat=beat), 4000)

    # Menu Riproduzione -> Loop (vedi gui.loop_region)
    def set_loop_start(self, *_):
        self.loop.set_start(self._position_for_markers())

    def set_loop_end(self, *_):
        self.loop.set_end(self._position_for_markers())

    def clear_loop(self, *_):
        self.loop.clear()

    def toggle_loop(self, *_):
        self.loop.changed()

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

    def _listening_speed(self) -> float:
        """La velocita' d'ascolto che vale davvero: solo in streaming."""
        from core.playback import streaming_available
        return self.playback.speed if streaming_available() else 1.0

    def _metronome_tempo_map(self):
        """La mappa del tempo per il click: rallentata come l'ascolto."""
        speed = self._listening_speed()
        if speed >= 1.0 - 1e-6:
            return self._playback_tempo_map
        return [(beat, bpm * speed) for beat, bpm in self._playback_tempo_map]

    def _on_speed_changed(self, *_args):
        """Rallenta l'ascolto (tendina della barra, o Riproduzione ->
        Velocita' d'ascolto): riparte dal punto in cui si e' se sta suonando."""
        from core.playback import streaming_available
        speed = self.speed_combo.currentData() or 1.0
        actions = self.speed_actions.actions()
        if 0 <= self.speed_combo.currentIndex() < len(actions):
            actions[self.speed_combo.currentIndex()].setChecked(True)
        self.playback.set_speed(speed)
        if speed < 1.0 and not streaming_available():
            self.statusBar().showMessage(tr("Rallentare l'ascolto richiede la libreria FluidSynth e "
                                            "sounddevice: con il motore attuale si ascolta a velocita' normale."),
                                         8000)
            return
        if self._playback_start_wall is not None and self.playback.is_playing():
            beat = self._current_elapsed_beats()
            self.playback.stop()
            self.metronome_engine.stop()
            self.play(_resume_offset_beats=beat)

    def _on_metronome_toggled(self, checked):
        if checked and self.playback.is_playing():
            current_beat = self._current_elapsed_beats()
            # start_immediately=True: la riproduzione e' gia' in corso (audio
            # gia' avviato), quindi il riferimento temporale del click va
            # fissato subito, non aspettato da mark_started() (che qui non
            # verrebbe piu' richiamato da _mark_audio_started).
            self.metronome_engine.start(self._metronome_tempo_map(), self._playback_metrica_map,
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
