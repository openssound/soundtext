"""
Azioni sulle clip audio della vista Struttura brano (gui.arrangement_view):
menu delle clip e delle righe audio, importazione, tagli, dissolvenze,
riprese e comping, tempo dalla ripresa, time-stretch, quantizzazione,
unione dei pezzi, conversione in notazione. Una classe "mixin" da cui
ArrangementView eredita, come le parti di MainWindow (main_window_project,
main_window_mixer...): i metodi lavorano su self, che e' la vista.
"""

import dataclasses
import os

import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFileDialog, QInputDialog, QLabel, QMenu, QMessageBox

from core import audio_takes, audio_tracks
from core.arrangement import flatten_clips_to_text
from core.i18n import tr
from core.model import AudioClip, Clip

from .audio_import_dialog import AudioImportDialog
from .file_dialogs import file_dialog_options


class AudioClipActions:
    def _show_audio_box_menu(self, track_name: str, clip: AudioClip, global_pos, at_beat=None):
        missing = audio_tracks.clip_is_missing(clip)
        menu = QMenu(self)
        play_action = menu.addAction(tr("▶ Play"))
        stop_action = menu.addAction(tr("■ Stop"))
        rename_action = menu.addAction(tr("Rinomina..."))
        gain_action = menu.addAction(tr("Guadagno clip (dB)..."))
        normalize_action = menu.addAction(tr("Normalizza (picco a −1 dB)")) if not missing else None
        fade_action = menu.addAction(tr("Dissolvenze...")) if not missing else None
        mute_action = menu.addAction(tr("Silenzia clip"))
        mute_action.setCheckable(True)
        mute_action.setChecked(clip.muted)
        follow_action = menu.addAction(tr("Segui il tempo del brano")) if not missing else None
        if follow_action is not None:
            follow_action.setCheckable(True)
            follow_action.setChecked(clip.source_bpm > 0)
            follow_action.setToolTip(tr("Se il tempo del brano cambia, la clip si allunga o si accorcia "
                                        "(time-stretch) per restare a tempo."))
        speed_action = menu.addAction(tr("Velocita' (time-stretch)...")) if not missing else None
        trim_action = menu.addAction(tr("Taglio preciso (secondi)...")) if not missing else None
        curve_action = menu.addAction(tr("Curva del volume: punto qui")) \
            if not missing and at_beat is not None and at_beat >= clip.start_beat else None
        if curve_action is not None:
            curve_action.setToolTip(tr("Aggiunge un punto alla curva del volume dentro la clip: trascinalo "
                                       "su e giu'; Ctrl+clic sulla clip ne aggiunge altri, doppio clic su un "
                                       "punto lo toglie."))
        uncurve_action = menu.addAction(tr("Togli la curva del volume")) if clip.gain_points else None
        loop_action = menu.addAction(tr("Ripeti in loop...")) if not missing else None
        unloop_action = menu.addAction(tr("Togli la ripetizione")) if not missing and clip.loop_length > 0 else None
        transpose_action = tuning_action = reverse_action = invert_action = None
        channel_actions = {}
        if not missing:
            transpose_action = menu.addAction(tr("Trasponi...") if not clip.transpose else
                                              tr("Trasponi ({semitones:+g} semitoni)...", semitones=clip.transpose))
            tuning_action = menu.addAction(tr("Controlla l'accordatura..."))
            reverse_action = menu.addAction(tr("Suona al contrario"))
            reverse_action.setCheckable(True)
            reverse_action.setChecked(clip.reverse)
            invert_action = menu.addAction(tr("Inverti la fase"))
            invert_action.setCheckable(True)
            invert_action.setChecked(clip.invert)
            info = audio_tracks.cached_wav_info(clip.file)
            if info is not None and info.channels >= 2:
                channel_menu = menu.addMenu(tr("Canale"))
                for value, label in (("stereo", tr("Stereo")), ("left", tr("Solo sinistro")),
                                     ("right", tr("Solo destro")), ("mono", tr("Mono (somma dei due)"))):
                    action = channel_menu.addAction(label)
                    action.setCheckable(True)
                    action.setChecked(clip.channel == value)
                    channel_actions[action] = value
        split_action = None
        if not missing and at_beat is not None and at_beat > clip.start_beat:
            split_action = menu.addAction(tr("Dividi qui (beat {at_beat:g})", at_beat=at_beat))
        duplicate_action = menu.addAction(tr("Duplica"))
        take_actions, comp_action, keep_one_action = {}, None, None
        if audio_takes.has_takes(clip):
            takes_menu = menu.addMenu(tr("Riprese"))
            for i, take in enumerate(clip.takes):
                action = takes_menu.addAction(take.name)
                action.setCheckable(True)
                action.setChecked(i == clip.active_take)
                take_actions[action] = i
            takes_menu.addSeparator()
            comp_action = takes_menu.addAction(tr("Comping..."))
            keep_one_action = takes_menu.addAction(tr("Tieni solo la ripresa attiva"))
        convert_action = menu.addAction(tr("Converti in notazione...")) if not missing else None
        style_action = menu.addAction(tr("Salva come stile del generatore...")) if not missing else None
        harmonize_action = menu.addAction(tr("Armonizza la melodia...")) if not missing else None
        tempo_action = menu.addAction(tr("Ricava il tempo dalla ripresa...")) if not missing else None
        quantize_action = menu.addAction(tr("Quantizza l'audio...")) if not missing else None
        silences_action = menu.addAction(tr("Rimuovi i silenzi...")) if not missing else None
        pieces = [] if missing else audio_tracks.connected_pieces(
            self.host.project.get_track(track_name).audio_clips, clip, self._tempo_map())
        join_action = menu.addAction(tr("Unisci i pezzi in una clip ({n})", n=len(pieces))) if len(pieces) > 1 else None
        relink_action = menu.addAction(tr("Ritrova file...")) if missing else None
        menu.addSeparator()
        cut_action = menu.addAction(tr("Taglia"))
        copy_action = menu.addAction(tr("Copia"))
        paste_action = menu.addAction(tr("Incolla qui")) if isinstance(self._clipboard, AudioClip) else None
        menu.addSeparator()
        delete_action = menu.addAction(tr("Elimina"))

        chosen = menu.exec(global_pos)
        track = self.host.project.get_track(track_name)
        if chosen is play_action:
            self._play_clip(track_name, clip)
        elif chosen is stop_action:
            self._stop_preview()
        elif chosen is rename_action:
            self._rename_clip(track_name, clip)
        elif chosen is gain_action:
            self._set_clip_gain(track_name, clip)
        elif normalize_action is not None and chosen is normalize_action:
            self._normalize_clip(track_name, clip)
        elif fade_action is not None and chosen is fade_action:
            self._edit_clip_fades(track_name, clip)
        elif chosen is mute_action:
            clip.muted = not clip.muted
            self.on_clip_changed(track_name)
        elif follow_action is not None and chosen is follow_action:
            self._toggle_follow_tempo(track_name, clip)
        elif speed_action is not None and chosen is speed_action:
            self._edit_clip_speed(track_name, clip)
        elif trim_action is not None and chosen is trim_action:
            self._edit_clip_trim(track_name, clip)
        elif curve_action is not None and chosen is curve_action:
            self._add_curve_point_at(track_name, clip, at_beat)
        elif uncurve_action is not None and chosen is uncurve_action:
            clip.gain_points = []
            self.on_clip_changed(track_name)
        elif loop_action is not None and chosen is loop_action:
            self._loop_clip(track_name, clip)
        elif unloop_action is not None and chosen is unloop_action:
            clip.loop_length = 0.0
            self.on_clip_changed(track_name)
        elif transpose_action is not None and chosen is transpose_action:
            self._transpose_clip(track_name, clip)
        elif tuning_action is not None and chosen is tuning_action:
            self.check_clip_tuning(track_name, clip)
        elif reverse_action is not None and chosen is reverse_action:
            clip.reverse = not clip.reverse
            self.on_clip_changed(track_name)
        elif invert_action is not None and chosen is invert_action:
            clip.invert = not clip.invert
            self.on_clip_changed(track_name)
        elif chosen in channel_actions:
            if clip.channel != channel_actions[chosen]:
                clip.channel = channel_actions[chosen]
                self.on_clip_changed(track_name)
        elif split_action is not None and chosen is split_action:
            self._split_clip(track_name, clip, at_beat)
        elif chosen is duplicate_action:
            self._duplicate_clip(track_name, clip)
        elif chosen in take_actions:
            self._set_active_take(track_name, clip, take_actions[chosen])
        elif comp_action is not None and chosen is comp_action:
            self._comp_clip(track_name, clip)
        elif keep_one_action is not None and chosen is keep_one_action:
            self._keep_only_active_take(track_name, clip)
        elif convert_action is not None and chosen is convert_action:
            self._convert_clip_to_notation(track_name, clip)
        elif harmonize_action is not None and chosen is harmonize_action:
            self._harmonize_audio_clip(track_name, clip)
        elif style_action is not None and chosen is style_action:
            self._save_audio_clip_as_style(track_name, clip)
        elif tempo_action is not None and chosen is tempo_action:
            self._tempo_from_clip(track_name, clip)
        elif quantize_action is not None and chosen is quantize_action:
            self._quantize_clip_audio(track_name, clip)
        elif silences_action is not None and chosen is silences_action:
            self._remove_clip_silences(track_name, clip)
        elif join_action is not None and chosen is join_action:
            self._join_pieces(track_name, pieces)
        elif relink_action is not None and chosen is relink_action:
            self._relink_clip(track_name, clip)
        elif chosen is cut_action:
            self._clipboard = dataclasses.replace(clip)
            track.audio_clips.remove(clip)
            self.on_clip_changed(track_name)
        elif chosen is copy_action:
            self._clipboard = dataclasses.replace(clip)
        elif paste_action is not None and chosen is paste_action:
            self.paste_at(track_name, clip.start_beat)
        elif chosen is delete_action:
            track.audio_clips.remove(clip)
            self.on_clip_changed(track_name)

    def _show_audio_empty_menu(self, track_name: str, beat: float, global_pos):
        menu = QMenu(self)
        record_action = menu.addAction(tr("● Registra da qui..."))
        import_action = menu.addAction(tr("Importa file audio qui..."))
        paste_action = menu.addAction(tr("Incolla qui")) if isinstance(self._clipboard, AudioClip) else None
        chosen = menu.exec(global_pos)
        if chosen is record_action:
            self.host.record_into_audio_track(track_name, start_beat=beat)
        elif chosen is import_action:
            self.import_audio_clip(track_name, beat)
        elif paste_action is not None and chosen is paste_action:
            self.paste_at(track_name, beat)

    def _pick_audio_file(self, title: str):
        patterns = " ".join(f"*{ext}" for ext in audio_tracks.AUDIO_FILE_EXTENSIONS)
        path, _ = QFileDialog.getOpenFileName(self, title, "", tr("Audio ({patterns});;Tutti i file (*)", patterns=patterns),
                                              options=file_dialog_options())
        return path or None

    def _import_audio_file(self, src_path: str):
        """Copia/converte src_path nella cartella audio del progetto (vedi
        core.audio_tracks.import_audio_file); None (dopo averlo detto
        all'utente) se non si riesce."""
        error = None
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            dest_dir = audio_tracks.target_audio_dir(getattr(self.host, "current_path", None))
            path = audio_tracks.import_audio_file(src_path, dest_dir)
        except (RuntimeError, OSError, ValueError) as e:
            path, error = None, str(e)
        finally:
            QApplication.restoreOverrideCursor()
        if error:
            QMessageBox.critical(self, tr("Importazione audio non riuscita"), error)
        return path

    def import_audio_clip(self, track_name: str, beat: float):
        """Sceglie un file audio e lo aggiunge come clip alla traccia audio
        track_name, a partire da beat (o dal primo posto libero dopo)."""
        from .arrangement_view import _snap
        src = self._pick_audio_file(tr("Importa file audio"))
        if not src:
            return
        path = self._import_audio_file(src)
        if not path:
            return
        name = os.path.splitext(os.path.basename(src))[0]
        clip = AudioClip(name=name, file=path, start_beat=beat)
        clip.start_beat = _snap(self.resolve_free_slot(track_name, clip, beat))
        self.host.project.get_track(track_name).audio_clips.append(clip)
        self.on_clip_changed(track_name)
        self.host.statusBar().showMessage(
            tr("Clip '{name}' aggiunta alla traccia '{track_name}' (file: {path}).", name=name, track_name=track_name, path=path), 6000)

    def _relink_clip(self, track_name: str, clip: AudioClip):
        src = self._pick_audio_file(tr("Ritrova il file di '{name}'", name=clip.name))
        if not src:
            return
        path = self._import_audio_file(src)
        if not path:
            return
        audio_takes.replace_file(clip, clip.file, path)   # anche nella ripresa attiva della lista
        self.on_clip_changed(track_name)

    def _split_clip(self, track_name: str, clip: AudioClip, at_beat: float):
        second = audio_tracks.split_clip(clip, at_beat, self._tempo_map())
        if second is None:
            self.host.statusBar().showMessage(tr("Il punto scelto e' troppo vicino ai bordi della clip."), 4000)
            return
        self.host.project.get_track(track_name).audio_clips.append(second)
        self.on_clip_changed(track_name)

    def _edit_clip_trim(self, track_name: str, clip: AudioClip):
        """Taglio di inizio e fine in secondi, per chi preferisce i numeri al
        mouse: come trascinando i bordi, l'audio resta dov'e' nel tempo."""
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout
        total = audio_tracks.clip_file_seconds(clip)
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("Taglio — {name}", name=clip.name))
        form = QFormLayout(dlg)
        form.addRow(QLabel(tr("Durata del file: {total:.3f} s", total=total)))
        spins = []
        for label, value in ((tr("Salta all'inizio (s):"), clip.trim_start), (tr("Salta alla fine (s):"), clip.trim_end)):
            spin = QDoubleSpinBox()
            spin.setDecimals(3)
            spin.setSingleStep(0.01)
            spin.setRange(0.0, max(0.0, total - audio_tracks.MIN_CLIP_SECONDS))
            spin.setValue(value)
            form.addRow(label, spin)
            spins.append(spin)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)
        self._trim_dialog = dlg   # per i test
        if dlg.exec() != QDialog.Accepted:
            return
        self._apply_clip_trim(track_name, clip, spins[0].value(), spins[1].value())

    def _apply_clip_trim(self, track_name: str, clip: AudioClip, trim_start: float, trim_end: float):
        from core.tempo_map import beat_at_elapsed_seconds, seconds_for_beats
        tempo_map = self._tempo_map()
        before = (clip.start_beat, clip.trim_start, clip.trim_end)
        clip.trim_end = 0.0
        start_s = seconds_for_beats(tempo_map, clip.start_beat) + (trim_start - clip.trim_start)
        if start_s < 0:
            trim_start -= start_s   # la clip non puo' iniziare prima del brano
            start_s = 0.0
        audio_tracks.trim_clip_start_to_beat(clip, beat_at_elapsed_seconds(tempo_map, 0.0, start_s), tempo_map)
        total = audio_tracks.clip_file_seconds(clip)
        clip.trim_end = round(max(0.0, min(trim_end, total - clip.trim_start - audio_tracks.MIN_CLIP_SECONDS)), 6)
        if (clip.start_beat, clip.trim_start, clip.trim_end) != before:
            self.on_clip_changed(track_name)

    def _clip_notation_text(self, track_name: str, clip: AudioClip, title: str, prompt: str):
        """La parte riprodotta della clip convertita in notazione (stesso
        motore di 'Importa audio', vedi gui.audio_import_dialog), con lo
        strumento chiesto all'utente: (strumento, testo), o None se annullato."""
        import tempfile
        from core.instruments import list_instrument_names
        track = self.host.project.get_track(track_name)
        names = list_instrument_names()
        preferred = {"chitarra": "Guitar", "tastiera": "Piano", "voce": "Trumpet"}.get(track.input_profile, "Piano")
        instrument, ok = QInputDialog.getItem(self, title, prompt, names,
                                              names.index(preferred) if preferred in names else 0, False)
        if not ok:
            return None
        fd, tmp = tempfile.mkstemp(suffix=".wav", prefix="soundtext_clip_")
        os.close(fd)
        try:
            audio_tracks.extract_clip_audio(clip, tmp)
            dlg = AudioImportDialog(self, project=self.host.project, instrument_name=instrument,
                                     context_label=tr("clip '{name}' (traccia '{track_name}')", name=clip.name, track_name=track_name))
            dlg._set_source(tmp)
            accepted = dlg.exec() == AudioImportDialog.Accepted
            text = dlg.result_text() if accepted else None
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        self.host._sync_tempo_metrica_fields()
        return (instrument, text) if text else None

    def _convert_clip_to_notation(self, track_name: str, clip: AudioClip):
        """Converte la parte riprodotta della clip in notazione in una nuova
        traccia, con un box che parte dove parte la clip."""
        converted = self._clip_notation_text(track_name, clip, tr("Converti in notazione"),
                                             tr("Strumento della nuova traccia:"))
        if converted is None:
            return
        instrument, text = converted
        project = self.host.project
        existing = {t.name for t in project.tracks}
        name, n = f"{clip.name} (note)", 2
        while name in existing:
            name, n = tr("{name} (note {n})", name=clip.name, n=n), n + 1
        new_track = project.add_track(name, instrument, "")
        new_track.clips = [Clip(name=clip.name, text=text, start_beat=clip.start_beat)]
        new_track.text = flatten_clips_to_text(new_track.clips, project.patterns, new_track.instrument.default_octave,
                                              meter=project.meter())
        self.host._mark_dirty()
        self.host.refresh_mixer()
        self.host.select_track(name)
        self.host.statusBar().showMessage(
            tr("Clip '{name}' convertita in notazione nella nuova traccia '{0}'.", name, name=clip.name), 6000)

    def _save_audio_clip_as_style(self, track_name: str, clip: AudioClip):
        """Salva come stile del generatore una ripresa: prima la conversione
        in note (strumento a scelta: una batteria per uno stile di batteria),
        poi lo stesso dialogo dei box (gui.save_style_dialog)."""
        from core.instruments import get_instrument
        from .save_style_dialog import SaveStyleDialog, chord_sources_of, source_for_part
        converted = self._clip_notation_text(track_name, clip, tr("Salva come stile del generatore"),
                                             tr("Strumento della ripresa (Drums per uno stile di batteria):"))
        if converted is None:
            return
        instrument, text = converted
        project = self.host.project
        source = source_for_part(tr("clip '{name}'", name=clip.name), text, get_instrument(instrument),
                                 offset_beats=clip.start_beat)
        dlg = SaveStyleDialog(self, [source], chord_sources_of(project, track_name), project.patterns,
                              meter=project.time_sig)
        self._save_style_dialog = dlg   # per i test
        if dlg.exec() == SaveStyleDialog.Accepted and dlg.saved_style():
            self.host.statusBar().showMessage(
                tr("Stile «{0}» salvato fra gli stili personali.", dlg.saved_style()[1]), 4000)

    def convert_track_to_notation(self, track_name: str):
        """Tutta la traccia audio in una traccia SoundText, un box per clip
        (vedi core.audio_track_notation.convert_audio_track): le scelte nel
        dialogo, poi la conversione in background, annullabile."""
        from PySide6.QtWidgets import QDialog
        from core.instruments import get_instrument
        from .audio_track_convert_dialog import AudioTrackConvertDialog
        project = self.host.project
        track = project.get_track(track_name)
        dlg = AudioTrackConvertDialog(self, project, track)
        self._track_convert_dialog = dlg   # per i test
        if dlg.exec() != QDialog.Accepted:
            return
        options = dlg.options()
        default_octave = get_instrument(dlg.instrument_name()).default_octave
        self._run_track_conversion(track_name, [(dlg.destination(), options, default_octave)],
                                   on_placed=dlg.remember_choices)

    def key_from_audio_track(self, track_name: str):
        """La tonalita' del brano dagli accordi riconosciuti nella traccia
        audio (core.audio_track_notation, core.key_detect): serve al giro
        armonico e alla melodia. Chiede prima di cambiarla."""
        from core.audio_track_notation import audio_track_chord_text
        from core.key_detect import detect_key_of_text
        from .worker import run_with_wait
        project = self.host.project
        track = project.get_track(track_name)
        try:
            text = run_with_wait(self, tr("Riconosco gli accordi di '{name}'...", name=track_name),
                                 audio_track_chord_text, project, track)
        except RuntimeError as e:
            QMessageBox.warning(self, tr("Tonalita' dalla ripresa"), str(e))
            return
        key = detect_key_of_text(text, project.patterns) if text.strip() else None
        if not key:
            QMessageBox.information(self, tr("Tonalita' dalla ripresa"), tr(
                "Nella traccia audio '{name}' non ho riconosciuto accordi: serve una parte che suoni accordi "
                "(chitarra ritmica, pianoforte, un brano intero), non una melodia.", name=track_name))
            return
        if key == project.key:
            QMessageBox.information(self, tr("Tonalita' dalla ripresa"), tr(
                "La tonalita' riconosciuta in '{name}' e' {key}, quella gia' impostata.", name=track_name, key=key))
            return
        current = project.key or tr("non impostata")
        answer = QMessageBox.question(self, tr("Tonalita' dalla ripresa"), tr(
            "Dagli accordi di '{name}' la tonalita' e' {key}.\nImpostarla come tonalita' del brano "
            "(ora: {current})?", name=track_name, key=key, current=current))
        if answer == QMessageBox.Yes:
            self.host.key_combo.setCurrentText(key)        # come scriverla a mano (_on_key_changed)
            self.host.statusBar().showMessage(tr("Tonalita' del brano: {key} (da '{name}').",
                                                 key=key, name=track_name), 6000)

    def reconvert_tracks(self, note_track_names):
        """Riconverti: rifa' la conversione di ogni traccia di note dalla sua
        traccia audio, con le scelte salvate (Track.conversion), senza
        dialogo; i box nuovi prendono il posto dei vecchi, un Annulla per
        traccia."""
        from core.audio_track_notation import options_from_conversion
        from .audio_track_convert_dialog import with_pitch_params
        project = self.host.project
        by_source = {}
        for name in note_track_names:
            target = project.get_track(name)
            options = with_pitch_params(options_from_conversion(target.conversion), target.instrument_name)
            by_source.setdefault(target.conversion["from"], []).append(
                (("replace", name), options, target.instrument.default_octave))
        for source, jobs in by_source.items():
            self._run_track_conversion(source, jobs)

    def _run_track_conversion(self, track_name: str, jobs, on_placed=None):
        """Le conversioni 'jobs' [(destinazione, opzioni, ottava)] della
        traccia audio, una dopo l'altra in background con una sola finestra
        di avanzamento, annullabile; on_placed(nome della traccia di note)
        dopo ognuna."""
        import copy
        from PySide6.QtWidgets import QProgressDialog
        from core.audio_import import ConversionCancelled
        from core.audio_track_notation import convert_audio_track
        from .worker import Worker
        project = self.host.project
        snapshot = copy.deepcopy(project)   # il brano puo' cambiare mentre si converte
        cancelled = {"value": False}
        progress_dlg = QProgressDialog(tr("Conversione delle clip di '{name}' in notazione...", name=track_name),
                                       tr("Annulla"), 0, 100, self)
        progress_dlg.setWindowTitle(tr("Converti la traccia in notazione"))
        progress_dlg.setWindowModality(Qt.WindowModal)
        progress_dlg.setMinimumDuration(0)
        progress_dlg.canceled.connect(lambda: cancelled.__setitem__("value", True))

        def convert_all(progress_callback):
            results = []
            for i, (_destination, options, default_octave) in enumerate(jobs):
                def progress(frac, i=i):
                    if cancelled["value"]:
                        raise ConversionCancelled()
                    progress_callback((i + frac) / len(jobs))
                results.append(convert_audio_track(snapshot, snapshot.get_track(track_name), options,
                                                   default_octave, progress_callback=progress))
            return results

        worker = Worker(convert_all)
        worker.progress.connect(lambda f: progress_dlg.setValue(int(f * 100)))

        def finish() -> bool:
            # come in "Analizza livelli": lo stato prima di close(), che emette canceled
            was_cancelled = cancelled["value"]
            self._track_convert_worker = None
            progress_dlg.canceled.disconnect()
            progress_dlg.close()
            return was_cancelled

        def done(results):
            if finish():
                return
            for (destination, options, _octave), (boxes, silent) in zip(jobs, results):
                target = self._place_converted_boxes(track_name, destination, boxes, silent)
                if target is None:
                    continue
                if destination[0] != "existing":     # aggiunti a una traccia: Riconverti la svuoterebbe
                    from core.audio_track_notation import conversion_record
                    self.host.project.get_track(target).conversion = conversion_record(track_name, options)
                if on_placed is not None:
                    on_placed(target)

        def failed(message):
            if not finish():
                QMessageBox.warning(self, tr("Converti la traccia in notazione"),
                                    tr("Conversione non riuscita:\n{message}", message=message))

        worker.finished_ok.connect(done)
        worker.finished_error.connect(failed)
        self._track_convert_worker = worker
        worker.start()

    def _place_converted_boxes(self, source_name: str, destination, boxes, silent):
        """I box della conversione nella traccia di destinazione (nuova,
        esistente, o esistente svuotata per rifare la conversione), ciascuno
        alla posizione della sua clip o, se li' c'e' gia' qualcosa, nello
        spazio libero piu' vicino. Il nome della traccia, o None."""
        project = self.host.project
        if not boxes:
            QMessageBox.information(self, tr("Converti la traccia in notazione"),
                                    tr("Nelle clip di '{name}' non ho riconosciuto niente da scrivere.", name=source_name))
            return None
        kind, value = destination
        if kind == "new":
            existing = {t.name for t in project.tracks}
            name, n = tr("{name} (note)", name=source_name), 2
            while name in existing:
                name, n = tr("{name} (note {n})", name=source_name, n=n), n + 1
            target = project.add_track(name, value, "")
        elif kind == "replace":
            target = project.get_track(value)
            target.clips = []
            target.text = ""
        else:
            target = project.get_track(value)
            self._wrap_free_text_in_box(target)
        moved = 0
        for box in boxes:
            target.clips.append(box)
            beat = self.resolve_free_slot(target.name, box, box.start_beat)
            if abs(beat - box.start_beat) > 1e-9:
                box.start_beat = round(beat, 6)
                moved += 1
        target.text = flatten_clips_to_text(target.clips, project.patterns, target.instrument.default_octave,
                                            meter=project.meter())
        self.host._mark_dirty()
        self.host.refresh_mixer()
        self.host.select_track(target.name)
        message = tr("Traccia '{source}' convertita: {n} box nella traccia '{target}'.",
                     source=source_name, n=len(boxes), target=target.name)
        if moved:
            message += " " + tr("{n} spostati nello spazio libero piu' vicino.", n=moved)
        if silent:
            message += " " + tr("Clip senza note riconosciute: {names}.", names=", ".join(silent))
        self.host.statusBar().showMessage(message, 8000)
        return target.name

    def _set_clip_gain(self, track_name: str, clip: AudioClip):
        value, ok = QInputDialog.getDouble(
            self, tr("Guadagno clip"), tr("Guadagno in dB (0 = originale, negativo = piu' piano):"),
            clip.gain_db, -48.0, 24.0, 1)
        if not ok or value == clip.gain_db:
            return
        clip.gain_db = value
        self.on_clip_changed(track_name)

    def _add_curve_point_at(self, track_name: str, clip: AudioClip, at_beat: float):
        """Un punto della curva del volume al beat del clic, sulla curva com'e'
        (0 dB se e' la prima): poi lo si trascina."""
        from core.tempo_map import seconds_for_beats
        tempo_map = self._tempo_map()
        t = seconds_for_beats(tempo_map, at_beat) - seconds_for_beats(tempo_map, clip.start_beat)
        play = audio_tracks.clip_play_seconds(clip)
        if play <= 0:
            return
        t = round(max(0.0, min(play, t % play if clip.loop_length > 0 else t)), 3)
        db = round(float(audio_tracks.gain_curve_db(np.array([t]), clip.gain_points)[0]), 1)
        clip.gain_points = sorted([p for p in clip.gain_points if abs(p[0] - t) > 1e-3] + [(t, db)])
        self.on_clip_changed(track_name)

    def _harmonize_audio_clip(self, track_name: str, clip: AudioClip):
        """La melodia della clip (riconosciuta come in Converti in notazione,
        modalita' melodia) armonizzata: vedi harmonize_melody."""
        from core.audio_track_notation import ConversionOptions, _convert_clip
        from .worker import run_with_wait
        track = self.host.project.get_track(track_name)
        options = ConversionOptions(mode="melody", voice_source=track.input_profile == "voce")
        try:
            text = run_with_wait(self, tr("Ascolto la melodia di '{name}'...", name=clip.name),
                                 _convert_clip, self.host.project, clip, options, 4)
        except RuntimeError as e:
            QMessageBox.warning(self, tr("Armonizza la melodia"), str(e))
            return
        if not text:
            QMessageBox.information(self, tr("Armonizza la melodia"), tr(
                "In '{name}' non ho riconosciuto una melodia: serve una parte a una voce (canto, linea di "
                "chitarra o di fiato).", name=clip.name))
            return
        self.harmonize_melody(clip.name, text, clip.start_beat)

    def _loop_clip(self, track_name: str, clip: AudioClip):
        """Quante volte suonare la clip di fila (AudioClip.loop_length); lo
        stesso si fa con Ctrl+trascina del bordo destro."""
        content = audio_tracks.clip_duration_beats(clip, self._tempo_map())
        if content <= 0:
            return
        current = max(1, round(clip.loop_length / content)) if clip.loop_length > 0 else 4
        times, ok = QInputDialog.getInt(
            self, tr("Ripeti in loop"),
            tr("Quante volte suona la clip di fila (1 = nessuna ripetizione)?\n"
               "Anche con Ctrl+trascina del bordo destro, fino a dove vuoi."), current, 1, 256)
        if not ok:
            return
        clip.loop_length = round(content * times, 6) if times > 1 else 0.0
        self.on_clip_changed(track_name)

    def _transpose_clip(self, track_name: str, clip: AudioClip):
        """Trasposizione senza cambiare la velocita' (AudioClip.transpose):
        anche frazionaria, per correggere una ripresa scordata."""
        value, ok = QInputDialog.getDouble(
            self, tr("Trasponi"),
            tr("Semitoni (0 = originale, negativo = piu' basso; i decimali correggono "
               "una ripresa scordata: 0,1 = 10 cent):"),
            clip.transpose, -24.0, 24.0, 2, step=0.1)
        if not ok or abs(value - clip.transpose) < 1e-6:
            return
        clip.transpose = round(value, 3)
        self.on_clip_changed(track_name)

    def check_clip_tuning(self, track_name: str, clip: AudioClip, after_recording: bool = False):
        """Di quanto la clip e' sopra o sotto il La 440 (core.tuning); se lo
        e' abbastanza da sentirsi, propone di correggerla tutta con la
        trasposizione. Dopo una registrazione tace se la ripresa e' intonata
        o non ha un'accordatura chiara (batteria)."""
        from core import tuning
        from .worker import run_with_wait
        try:
            offset = run_with_wait(self, tr("Controllo l'accordatura di '{name}'...", name=clip.name),
                                   tuning.clip_tuning, clip)
        except RuntimeError as e:
            if not after_recording:
                QMessageBox.warning(self, tr("Accordatura"), str(e))
            return
        if not tuning.detune_to_correct(offset):
            if not after_recording:
                QMessageBox.information(self, tr("Accordatura"), tr(
                    "'{name}' e' intonata (La a 440 Hz).", name=clip.name) if offset is not None else tr(
                    "In '{name}' non trovo un'accordatura chiara (serve una parte con delle note, "
                    "non batteria o rumore).", name=clip.name))
            return
        cents = int(round(abs(offset) * 100))
        where = tr("calante") if offset < 0 else tr("crescente")
        answer = QMessageBox.question(self, tr("Ripresa scordata"), tr(
            "'{name}' e' {where} di {cents} cent rispetto al La a 440 Hz.\n\nCorreggerla tutta? "
            "(Trasponi {semitones:+.2f} semitoni: il file non cambia, si puo' annullare.)",
            name=clip.name, where=where, cents=cents, semitones=-offset))
        if answer != QMessageBox.Yes:
            return
        clip.transpose = round(clip.transpose - offset, 3)
        self.on_clip_changed(track_name)

    def _tempo_from_clip(self, track_name: str, clip: AudioClip):
        """Il brano prende il tempo della ripresa, battuta per battuta (vedi
        core.performance_tempo e gui.tempo_from_take_dialog)."""
        from PySide6.QtWidgets import QDialog
        from core import performance_tempo
        from .tempo_from_take_dialog import TempoFromTakeDialog
        from .worker import run_with_wait
        project = self.host.project
        try:
            analysis = run_with_wait(self, tr("Cerco il battito di '{name}'...", name=clip.name),
                                     performance_tempo.analyze_clip, project, clip)
        except RuntimeError as e:
            QMessageBox.warning(self, tr("Tempo dalla ripresa"), str(e))
            return
        if analysis.bars < 2:
            QMessageBox.information(self, tr("Tempo dalla ripresa"), tr(
                "Nella clip '{name}' non trovo un battito regolare per almeno due battute: serve una parte "
                "ritmica (chitarra, batteria, pianoforte) suonata per qualche battuta.", name=clip.name))
            return
        dlg = TempoFromTakeDialog(self, clip.name, analysis,
                                  performance_tempo.suggested_first_bar(project, clip, analysis))
        self._tempo_dialog = dlg   # per i test
        if dlg.exec() != QDialog.Accepted:
            return
        bpm = dlg.fixed_bpm()
        if bpm is None:
            bars = performance_tempo.apply_performance_tempo(project, clip, analysis, dlg.first_bar())
            message = tr("Il brano segue il tempo di '{name}' dalla battuta {bar} per {n} battute.",
                         name=clip.name, bar=dlg.first_bar(), n=bars)
        else:
            pieces = performance_tempo.warp_to_fixed_tempo(project, clip, analysis, dlg.first_bar(), bpm)
            track = project.get_track(track_name)
            index = track.audio_clips.index(clip)
            track.audio_clips[index:index + 1] = pieces
            message = tr("'{name}' adattata a {bpm} BPM: {n} pezzi, divisi alle battute.", name=clip.name, bpm=bpm,
                         n=len(pieces))
        if hasattr(self.host, "_sync_tempo_metrica_fields"):
            self.host._sync_tempo_metrica_fields()
        self.on_clip_changed(track_name)
        self.host.statusBar().showMessage(message, 6000)

    def _quantize_clip_audio(self, track_name: str, clip: AudioClip):
        """Quantizza l'audio: pezzi tagliati agli attacchi e spostati verso
        la griglia (core.audio_slice), un solo Annulla per tutto."""
        from PySide6.QtWidgets import QDialog
        from core import audio_slice
        from .audio_quantize_dialog import AudioQuantizeDialog
        from .worker import run_with_wait
        try:
            attacks = run_with_wait(self, tr("Cerco gli attacchi di '{name}'...", name=clip.name),
                                    audio_slice.clip_attacks, clip, 0.06)
        except RuntimeError as e:
            QMessageBox.warning(self, tr("Quantizza l'audio"), str(e))
            return
        dlg = AudioQuantizeDialog(self, clip.name, len(attacks))
        self._audio_quantize_dialog = dlg   # per i test
        if dlg.exec() != QDialog.Accepted:
            return
        pieces = audio_slice.quantize_clip(self.host.project, clip, dlg.grid_beats(), dlg.settings(), attacks)
        track = self.host.project.get_track(track_name)
        index = track.audio_clips.index(clip)
        track.audio_clips[index:index + 1] = pieces
        self.on_clip_changed(track_name)
        self.host.statusBar().showMessage(
            tr("Audio di '{name}' quantizzato: {n} pezzi.", name=clip.name, n=len(pieces)), 5000)

    def _remove_clip_silences(self, track_name: str, clip: AudioClip):
        """Rimuovi i silenzi: la clip divisa nei pezzi che suonano, ognuno
        dove era (core.audio_silence), un solo Annulla per tutto."""
        from PySide6.QtWidgets import QDialog
        from core import audio_silence
        from .remove_silences_dialog import RemoveSilencesDialog
        from .worker import run_with_wait
        try:
            levels, total = run_with_wait(self, tr("Misuro il livello di '{name}'...", name=clip.name),
                                          audio_silence.clip_levels_db, clip)
        except RuntimeError as e:
            QMessageBox.warning(self, tr("Rimuovi i silenzi"), str(e))
            return
        dlg = RemoveSilencesDialog(self, clip.name, levels, total)
        self._remove_silences_dialog = dlg   # per i test
        if dlg.exec() != QDialog.Accepted:
            return
        pieces = audio_silence.remove_silences(self.host.project, clip, dlg.regions())
        track = self.host.project.get_track(track_name)
        index = track.audio_clips.index(clip)
        track.audio_clips[index:index + 1] = pieces
        self.on_clip_changed(track_name)
        self.host.statusBar().showMessage(
            tr("Silenzi di '{name}' rimossi: {n} pezzi.", name=clip.name, n=len(pieces)), 5000)

    def _join_pieces(self, track_name: str, pieces):
        """Unisci i pezzi in una clip: un file nuovo con il mix dei pezzi
        (vedi core.audio_tracks.join_clips), al posto dei pezzi; un solo Annulla."""
        from core.audio_tracks import join_clips, target_audio_dir
        from .worker import run_with_wait
        try:
            joined = run_with_wait(self, tr("Unisco {n} pezzi...", n=len(pieces)), join_clips, self.host.project,
                                   pieces, target_audio_dir(getattr(self.host, "current_path", None)),
                                   pieces[0].name)
        except RuntimeError as e:
            QMessageBox.warning(self, tr("Unisci i pezzi"), str(e))
            return
        track = self.host.project.get_track(track_name)
        index = min(track.audio_clips.index(c) for c in pieces)
        track.audio_clips = [c for c in track.audio_clips if c not in pieces]
        track.audio_clips.insert(min(index, len(track.audio_clips)), joined)
        self.on_clip_changed(track_name)
        self.host.statusBar().showMessage(
            tr("{n} pezzi uniti nella clip '{name}' (file nuovo: {file}).", n=len(pieces), name=joined.name,
               file=os.path.basename(joined.file)), 6000)

    def _tempo_at(self, beat: float) -> float:
        from core.tempo_map import value_at_beat
        return float(value_at_beat(self._tempo_map(), beat) or self.host.project.tempo_bpm)

    def _toggle_follow_tempo(self, track_name: str, clip: AudioClip):
        """Segui il tempo del brano: la clip ricorda il tempo a cui va a tempo
        adesso (quello del brano dove comincia, per lo stretch che ha)."""
        clip.source_bpm = 0.0 if clip.source_bpm > 0 else round(self._tempo_at(clip.start_beat) * clip.stretch, 3)
        self.on_clip_changed(track_name)

    def _edit_clip_speed(self, track_name: str, clip: AudioClip):
        """Velocita' della clip in percentuale (time-stretch senza cambiare
        l'intonazione): 50% = lunga il doppio."""
        value, ok = QInputDialog.getDouble(
            self, tr("Velocita' — {name}", name=clip.name),
            tr("Velocita' in percentuale (100 = originale, 50 = lenta il doppio; l'intonazione non cambia):"),
            round(100.0 / clip.stretch, 2), 100.0 / audio_tracks.MAX_STRETCH, 100.0 / audio_tracks.MIN_STRETCH, 1)
        if not ok:
            return
        stretch = round(100.0 / value, 6)
        if abs(stretch - clip.stretch) < 1e-6:
            return
        clip.stretch = stretch
        if clip.source_bpm > 0:
            clip.source_bpm = round(self._tempo_at(clip.start_beat) * stretch, 3)   # resta a tempo cosi'
        self.on_clip_changed(track_name)

    def _set_active_take(self, track_name: str, clip: AudioClip, index: int):
        if index == clip.active_take:
            return
        audio_takes.set_active_take(clip, index)
        self.on_clip_changed(track_name)

    def _keep_only_active_take(self, track_name: str, clip: AudioClip):
        others = len(clip.takes) - 1
        reply = QMessageBox.question(
            self, tr("Tieni solo la ripresa attiva"),
            tr("Togliere dalla clip '{name}' le altre {n} riprese? I loro file restano nella cartella "
               "audio del progetto; Ctrl+Z le rimette.", name=clip.name, n=others))
        if reply != QMessageBox.Yes:
            return
        audio_takes.keep_only_active_take(clip)
        self.on_clip_changed(track_name)

    def _comp_clip(self, track_name: str, clip: AudioClip):
        """Comping: la clip diventa i tratti scelti nella finestra (vedi
        gui.comping_dialog), un solo Annulla per tutto."""
        from .comping_dialog import CompingDialog
        dlg = CompingDialog(self, clip, self._tempo_map())
        self._comping_dialog = dlg   # per i test
        if dlg.exec() != CompingDialog.Accepted:
            return
        parts = dlg.result_clips()
        if not parts:
            return
        track = self.host.project.get_track(track_name)
        index = track.audio_clips.index(clip)
        track.audio_clips[index:index + 1] = parts
        self.on_clip_changed(track_name)
        self.host.statusBar().showMessage(
            tr("Comping di '{name}': {n} tratti.", name=clip.name, n=len(parts)), 5000)

    def _normalize_clip(self, track_name: str, clip: AudioClip):
        before = clip.gain_db
        if not audio_tracks.normalize_clip(clip):
            self.host.statusBar().showMessage(tr("La clip '{name}' e' muta: niente da normalizzare.", name=clip.name), 4000)
            return
        if clip.gain_db != before:
            self.on_clip_changed(track_name)
        self.host.statusBar().showMessage(
            tr("Clip '{name}' normalizzata: guadagno {gain_db:+g} dB.", name=clip.name, gain_db=clip.gain_db), 4000)

    def _edit_clip_fades(self, track_name: str, clip: AudioClip):
        """Dissolvenze in secondi e loro forma, per chi preferisce i numeri
        alle maniglie (e per scegliere la forma, che con le maniglie non c'e')."""
        from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout
        play = audio_tracks.clip_play_seconds(clip)
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("Dissolvenze — {name}", name=clip.name))
        form = QFormLayout(dlg)
        form.addRow(QLabel(tr("Durata della clip: {play:.3f} s", play=play)))
        spins = []
        for label, value in ((tr("In entrata (s):"), clip.fade_in), (tr("In uscita (s):"), clip.fade_out)):
            spin = QDoubleSpinBox()
            spin.setDecimals(3)
            spin.setSingleStep(0.05)
            spin.setRange(0.0, max(0.0, play))
            spin.setValue(value)
            form.addRow(label, spin)
            spins.append(spin)
        shape = QComboBox()
        shape.addItem(tr("Lineare"), "linear")
        shape.addItem(tr("Equal power (nessun calo di volume a meta')"), "equal")
        shape.setCurrentIndex(max(0, shape.findData(clip.fade_shape)))
        form.addRow(tr("Forma:"), shape)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)
        self._fade_dialog = dlg   # per i test
        if dlg.exec() != QDialog.Accepted:
            return
        self._apply_clip_fades(track_name, clip, spins[0].value(), spins[1].value(), shape.currentData())

    def _apply_clip_fades(self, track_name: str, clip: AudioClip, fade_in: float, fade_out: float, shape: str):
        play = audio_tracks.clip_play_seconds(clip)
        before = (clip.fade_in, clip.fade_out, clip.fade_shape)
        fade_in = max(0.0, min(fade_in, play))
        clip.fade_in = round(fade_in, 3)
        clip.fade_out = round(max(0.0, min(fade_out, play - fade_in)), 3)
        clip.fade_shape = shape
        if (clip.fade_in, clip.fade_out, clip.fade_shape) != before:
            self.on_clip_changed(track_name)
