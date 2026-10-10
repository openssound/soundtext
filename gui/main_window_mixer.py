import math
import os

from PySide6.QtWidgets import QDialog, QFileDialog, QInputDialog, QMessageBox

from core.notation import validate_track_text, notation_warnings, bar_issues_summary
from core.rhythm_generate import project_has_chords, tracks_duration_beats
from core.instruments import list_instrument_names
from core.midi_export import export_single_track_to_midi
from core.midi_import import import_midi_channel_into_track, list_midi_channels
from core.completion import completions_for_word
from core import midi_library
from core import settings as app_settings

from .arrangement_view import HEADER_WIDTH, ROW_HEIGHT
from .track_header import TrackHeaderWidget
from .add_track_dialog import AddTrackDialog
from .voicing_picker import handle_chord_double_click
from .selection_actions import handle_selection_context_menu
from .audio_import_dialog import AudioImportDialog
from .keyboard_play_dialog import KeyboardPlayDialog
from .rhythm_generate_dialog import (
    DrumGenerateDialog, BassGenerateDialog, MelodyGenerateDialog, ChordProgressionDialog, last_box_key,
)
from .theme import GOOD, BAD, WARN
from core.i18n import tr
from .file_dialogs import file_dialog_options


class MixerMixin:
    """Mixer/tracce: creazione, rinomina, rimozione, selezione, editor della
    traccia corrente (validazione, doppio click, autocompletamento) e
    import/export MIDI/audio per singola traccia."""

    # ------------------------------------------------------------ mixer

    def refresh_mixer(self):
        for w in self.track_headers.values():
            # NON w.setParent(None) prima di deleteLater(): toglierlo dal
            # genitore (il widget del mixer, C++-owner finche' resta
            # parentato) lo rende "posseduto" da Python, e se poi
            # self.track_headers = {} sotto ne fa cadere subito l'ultimo
            # riferimento Python, shiboken lo distrugge SUBITO invece di
            # aspettare il DeferredDelete gia' accodato da deleteLater():
            # quando quell'evento arriva, tenta di distruggere un
            # QWidget C++ gia' liberato -> crash (SIGSEGV in
            # Shiboken::BindingManager::releaseWrapper, osservato dopo
            # import MIDI + Play). removeWidget() lo stacca dal layout senza
            # toccarne il parent, quindi resta C++-owned e la deferred
            # delete arriva su un oggetto ancora vivo.
            self.mixer_layout.removeWidget(w)
            w.hide()
            w.deleteLater()
        self.track_headers = {}
        for track in self.project.tracks:
            # Stessa testata della vista Struttura brano; il menu ⋯ tiene
            # conto delle tracce a testo libero (show_track_actions_menu).
            header = TrackHeaderWidget(self, track, HEADER_WIDTH, ROW_HEIGHT, self.show_track_actions_menu)
            self.mixer_layout.insertWidget(self.mixer_layout.indexOf(self.mixer_add_track_btn), header)
            self.track_headers[track.name] = header

        self.empty_state_label.setVisible(not self.project.tracks)

        # Il canvas della vista Struttura brano va tenuto sincronizzato ad
        # ogni refresh_mixer(), altrimenti una traccia appena aggiunta (o
        # rimossa/rinominata) non vi compare finche' non si esce e si
        # rientra dalla vista.
        self.arrangement_view.refresh()
        self.effects_panel.project_changed()

        if self.project.tracks and self.current_track_name not in self.track_headers:
            self.select_track(self.project.tracks[0].name)
        elif not self.project.tracks:
            self.current_track_name = None
            self.track_title.setText(tr("Nessuna traccia selezionata"))
            self.editor.blockSignals(True)
            self.editor.setPlainText("")
            self.editor.blockSignals(False)
            self.validation_label.setText("")
            self.validation_label.setStyleSheet("padding: 5px 10px; border-radius: 5px;")

    def sync_mixer_widgets(self, track_name, source=None):
        """Riallinea le due testate della traccia (colonna della vista Testo
        e vista Struttura brano) dopo che una delle due (source) ha cambiato
        Mute/Solo/Volume/Pan."""
        header = self.track_headers.get(track_name)
        if header is not None and header is not source:
            header.sync_from_track()
        header = self.arrangement_view.canvas.header_widgets.get(track_name)
        if header is not None and header is not source:
            header.sync_from_track()

    def open_effects_panel(self, track_name):
        """Pulsante FX di una traccia: la seleziona e apre il pannello
        Effetti in fondo alla finestra (gui.effects_panel)."""
        if track_name not in self.track_headers:
            return
        self.select_track(track_name)
        self.effects_panel.open_for(track_name)

    def select_track(self, name):
        self.current_track_name = name
        for n, header in self.track_headers.items():
            header.set_active(n == name)
        self.arrangement_view.set_active_track(name)
        track = self.project.get_track(name)
        if track.is_audio:
            self._show_audio_track_in_editor(track)
            return
        # Riaggancia la colorazione della notazione, staccata per le tracce
        # audio (vedi _show_audio_track_in_editor).
        if self.highlighter.document() is not self.editor.document():
            self.highlighter.setDocument(self.editor.document())
        uses_boxes = bool(track.clips)
        suffix = tr("   ·   vista Struttura brano attiva: apri un box per modificare il contenuto") \
            if uses_boxes else ""
        self.track_title.setText(f"{track.name}   ·   {track.instrument_name}{suffix}")
        self.editor.blockSignals(True)
        self.editor.setPlainText(track.text)
        self.editor.setReadOnly(uses_boxes)
        self.editor.blockSignals(False)
        self._validate_current()

    def _reload_editor_from_track(self):
        """Dopo che un dialogo ha riscritto i testi del brano (rinomina di un
        pattern o di un file MIDI): l'editor mostra il testo nuovo della
        traccia corrente, invece di riscriverci sopra quello vecchio alla
        prima modifica. Il cursore resta dov'era (per quanto possibile)."""
        if not self.current_track_name:
            return
        track = self.project.find_track(self.current_track_name)
        if track is None or track.is_audio or self.editor.toPlainText() == track.text:
            return
        position = self.editor.textCursor().position()
        self.editor.blockSignals(True)
        self.editor.setPlainText(track.text)
        cursor = self.editor.textCursor()
        cursor.setPosition(min(position, len(track.text)))
        self.editor.setTextCursor(cursor)
        self.editor.blockSignals(False)

    def _show_audio_track_in_editor(self, track):
        """Una traccia audio non ha notazione: l'editor mostra (in sola
        lettura) l'elenco delle sue clip e come aggiungerne."""
        from core.audio_tracks import clip_is_missing, clip_play_seconds
        self.track_title.setText(tr("{name}   ·   traccia audio", name=track.name))
        if track.audio_clips:
            lines = [tr("Clip audio di questa traccia (si spostano nella vista Struttura brano):"), ""]
            for c in sorted(track.audio_clips, key=lambda c: c.start_beat):
                state = tr("  [FILE MANCANTE]") if clip_is_missing(c) else f"  {clip_play_seconds(c):.1f} s"
                lines.append(tr("• {name} — dal beat {start_beat:g}{state} — {file}", name=c.name, start_beat=c.start_beat, state=state, file=c.file))
            text = "\n".join(lines)
        else:
            text = (tr("Traccia audio vuota.\n\nUsa Traccia → Importa file audio in questa traccia... "
                    "oppure, nella vista Struttura brano, tasto destro sulla riga della traccia → "
                    "Importa file audio qui."))
        # L'elenco delle clip non e' notazione: senza colorazione.
        self.highlighter.setDocument(None)
        self.editor.blockSignals(True)
        self.editor.setPlainText(text)
        self.editor.setReadOnly(True)
        self.editor.blockSignals(False)
        self.validation_label.setText(tr("Traccia audio · {0} clip", len(track.audio_clips)))
        self.validation_label.setToolTip("")
        self.validation_label.setStyleSheet("padding: 5px 10px; border-radius: 5px;")

    def _reject_audio_track(self, track, what: str) -> bool:
        """True (dopo averlo spiegato all'utente) se track e' una traccia
        audio, su cui 'what' (azioni sulla notazione) non ha senso."""
        if track is None or not track.is_audio:
            return False
        QMessageBox.information(
            self, tr("Traccia audio"),
            tr("'{name}' e' una traccia audio: {what} vale solo per le tracce con notazione.\nIn una traccia audio si importano file audio (Traccia → Importa file audio in questa traccia...).", name=track.name, what=what)
        )
        return True

    def on_editor_changed(self):
        if not self.current_track_name:
            return
        track = self.project.get_track(self.current_track_name)
        # Una traccia con box (vista Struttura brano) ha testo derivato da
        # core.arrangement.flatten_clips_to_text: l'editor resta di sola
        # lettura per quella traccia (vedi select_track), quindi qui non
        # dovrebbe mai arrivare una modifica - per sicurezza la ignora
        # comunque invece di corrompere il testo derivato.
        if track.clips or track.is_audio:
            return
        track.text = self.editor.toPlainText()
        self._mark_dirty(merge_key=f"text:{track.name}")
        self._validate_current()

    def _on_editor_double_click(self, char_offset: int, global_pos) -> bool:
        if not self.current_track_name:
            return False
        track = self.project.get_track(self.current_track_name)
        if track.is_audio:
            return False
        return handle_chord_double_click(
            self.editor, self.editor.toPlainText(), char_offset, global_pos,
            self.project.patterns, track.instrument, track.instrument_name,
            self.project.tempo_bpm, self.playback, synth_track=track,
        )

    def _on_editor_selection_context_menu(self, sel_start: int, sel_end: int, global_pos) -> bool:
        if not self.current_track_name:
            return False
        track = self.project.get_track(self.current_track_name)
        if track.is_audio:
            return False
        return handle_selection_context_menu(
            self.editor, self.editor.toPlainText(), sel_start, sel_end,
            self.project.patterns, track.instrument, track.instrument_name,
            self.project.tempo_bpm, self.playback, global_pos, synth_track=track,
            host_project=self.project,
        )

    def _editor_completions(self, word: str):
        if not self.current_track_name:
            return []
        track = self.project.get_track(self.current_track_name)
        if track.is_audio:
            return []
        return completions_for_word(
            word, patterns=self.project.patterns, instrument=track.instrument,
            midi_ref_names=midi_library.list_midi_library,
        )

    def _validate_current(self):
        if not self.current_track_name:
            return
        track = self.project.get_track(self.current_track_name)
        if track.is_audio:
            return
        ok, msg = validate_track_text(track.text, self.project.patterns)
        issues = notation_warnings(track.text, self.project.patterns, self.project.time_sig,
                                 self.project.metrica_changes, pickup=self.project.pickup) if ok else []
        self.highlighter.set_bar_errors(i.char_start for i in issues)
        self.validation_label.setToolTip("\n".join(i.message for i in issues))
        if issues:
            self.validation_label.setText(bar_issues_summary(issues))
            self.validation_label.setStyleSheet(
                f"padding: 5px 10px; border-radius: 5px; color: {WARN}; "
                f"background-color: rgba(224,160,48,30); border: 1px solid {WARN};"
            )
        elif ok:
            self.validation_label.setText(tr("✓  Sintassi valida"))
            self.validation_label.setStyleSheet(
                f"padding: 5px 10px; border-radius: 5px; color: {GOOD}; "
                f"background-color: rgba(76,175,80,30); border: 1px solid {GOOD};"
            )
        else:
            self.validation_label.setText(tr("✗  Errore di sintassi: {msg}", msg=msg))
            self.validation_label.setStyleSheet(
                f"padding: 5px 10px; border-radius: 5px; color: {BAD}; "
                f"background-color: rgba(224,85,85,30); border: 1px solid {BAD};"
            )

    # ------------------------------------------------------------ tracce

    def add_track(self):
        dlg = AddTrackDialog(self, existing_names=[t.name for t in self.project.tracks])
        if dlg.exec() == QDialog.Accepted:
            name, instrument = dlg.result_values()
            if not name:
                QMessageBox.warning(self, tr("Nome mancante"), tr("Inserisci un nome traccia."))
                return
            if any(t.name == name for t in self.project.tracks):
                QMessageBox.warning(self, tr("Nome duplicato"), tr("Esiste gia' una traccia con questo nome."))
                return
            self.project.add_track(name, instrument, "")
            self._mark_dirty()
            self.refresh_mixer()
            self.select_track(name)

    def add_plugin_track(self):
        """Nuova traccia suonata da uno strumento virtuale (VST3/LV2): prima
        si sceglie il plugin, poi il nome; lo strumento del profilo (voicing,
        registro) resta il pianoforte, cambiabile da "Modifica traccia"."""
        from core.plugins import display_name
        from .plugin_dialogs import PluginPickerDialog
        dialog = PluginPickerDialog(self, instrument=True)
        if dialog.exec() != QDialog.Accepted:
            return
        ref = dialog.selected_ref()
        if not ref:
            return
        existing = {t.name for t in self.project.tracks}
        base = display_name(ref) or "Plugin"
        suggested, n = base, 1
        while suggested in existing:
            n += 1
            suggested = f"{base} {n}"
        name, ok = QInputDialog.getText(
            self, tr("Aggiungi traccia con strumento virtuale"), tr("Nome della traccia:"), text=suggested)
        name = name.strip()
        if not ok or not name:
            return
        if name in existing:
            QMessageBox.warning(self, tr("Nome duplicato"), tr("Esiste gia' una traccia con questo nome."))
            return
        track = self.project.add_track(name, "Piano", "")
        track.synth, track.synth_params, track.synth_state = ref, {}, ""
        self._mark_dirty()
        self.refresh_mixer()
        self.select_track(name)
        self._track_synth_changed(name)
        if not ref.startswith("sfz:"):
            self.edit_track_synth(name)

    def add_audio_track(self):
        """Nuova traccia audio (clip di file audio invece che notazione)."""
        existing = {t.name for t in self.project.tracks}
        suggested, n = "Audio", 1
        while suggested in existing:
            n += 1
            suggested = f"Audio {n}"
        name, ok = QInputDialog.getText(
            self, tr("Aggiungi traccia audio"),
            tr("Nome della traccia (es. Voce, Chitarra, Tastiera):"), text=suggested)
        name = name.strip()
        if not ok or not name:
            return
        if name in existing:
            QMessageBox.warning(self, tr("Nome duplicato"), tr("Esiste gia' una traccia con questo nome."))
            return
        self.project.add_audio_track(name)
        self._mark_dirty()
        self.refresh_mixer()
        self.select_track(name)
        self.statusBar().showMessage(
            tr("Traccia audio '{name}' creata: importa un file audio con Traccia → Importa file audio in questa traccia...", name=name), 6000)

    def import_audio_clip_into_selected_track(self):
        """Aggiunge una clip (file audio importato) in coda alla traccia
        audio selezionata."""
        track, _clip = self._resolve_edit_target()
        if track is None or not track.is_audio:
            QMessageBox.information(
                self, tr("Nessuna traccia audio"),
                tr("Seleziona prima una traccia audio (Traccia → Aggiungi traccia audio... per crearne una)."))
            return
        self.arrangement_view.import_audio_clip(track.name, self.arrangement_view.end_of_track_beat(track.name))

    # ------------------------------------------------------------ menu "+ Aggiungi traccia"

    def populate_add_track_menu(self, menu):
        """Riempie (ogni volta che si apre) il menu dei pulsanti "+ Aggiungi
        traccia" (colonna mixer e vista Struttura brano): tracce vuote e
        tracce gia' riempite da un generatore. Basso e accompagnamento
        seguono gli accordi di un'altra traccia: senza, restano visibili ma
        disattivati, con il motivo."""
        menu.clear()
        menu.addSection(tr("Nuova traccia"))
        menu.addAction(tr("Traccia con strumento..."), self.add_track).setShortcut("Ctrl+T")
        menu.addAction(tr("Traccia con strumento virtuale (VST3)..."), self.add_plugin_track)
        menu.addAction(tr("Traccia audio (voce, chitarra, tastiera)..."), self.add_audio_track)
        menu.addSection(tr("Genera una traccia"))
        menu.addAction(tr("Batteria..."), lambda: self.add_generated_track("drums"))
        menu.addAction(tr("Giro armonico..."), lambda: self.add_generated_track("progression"))
        has_chords = project_has_chords(self.project)
        for kind, label in (("bass", tr("Basso dagli accordi...")), ("melody", tr("Accompagnamento o riff..."))):
            action = menu.addAction(label if has_chords else tr("{label}  (serve un giro di accordi)", label=label),
                                    lambda k=kind: self.add_generated_track(k))
            action.setEnabled(has_chords)
        menu.addSection(tr("Da file"))
        menu.addAction(tr("Traccia da un file MIDI..."), self.add_track_from_midi)

    def _unique_track_name(self, base: str) -> str:
        existing = {t.name for t in self.project.tracks}
        name, n = base, 2
        while name in existing:
            name, n = f"{base} {n}", n + 1
        return name

    def _add_filled_track(self, name: str, instrument: str, text: str, box_name: str):
        """Nuova traccia gia' con del contenuto: un box nella vista Struttura
        brano, testo libero nella vista Testo."""
        from core.arrangement import flatten_clips_to_text
        from core.model import Clip
        track = self.project.add_track(name, instrument, "")
        if self.arrangement_action.isChecked():
            track.clips = [Clip(name=box_name, text=text, start_beat=0.0)]
            track.text = flatten_clips_to_text(track.clips, self.project.patterns, track.instrument.default_octave,
                                               meter=self.project.meter())
        else:
            track.text = text
        self._mark_dirty()
        self.refresh_mixer()
        self.select_track(name)
        return track

    def add_generated_track(self, kind: str):
        """Crea una traccia gia' generata (batteria, giro armonico, basso,
        accompagnamento/riff): prima il dialogo del generatore, la traccia
        solo se lo si conferma."""
        from core.instruments import get_instrument, list_instrument_names
        from .rhythm_generate_dialog import project_bar_beats
        other_beats = tracks_duration_beats(self.project)
        bar_beats = project_bar_beats(self.project)
        other_tracks = [(t.name, t.text) for t in self.project.tracks if not t.is_audio]
        if kind == "drums":
            instrument, base, box = "Drums", "Batteria", "Groove"
        elif kind == "progression":
            instrument, base, box = "Piano", "Accordi", "Giro"
        elif kind == "bass":
            instrument, base, box = "Bass", "Basso", "Basso"
        else:
            names = [n for n in list_instrument_names() if not get_instrument(n).is_percussion]
            instrument, ok = QInputDialog.getItem(
                self, tr("Accompagnamento o riff"), tr("Strumento della nuova traccia (polifonico = "
                "accompagnamento, monofonico = riff/melodia):"), names,
                names.index("Guitar") if "Guitar" in names else 0, False)
            if not ok:
                return
            base = instrument
            box = "Accompagnamento" if get_instrument(instrument).polyphonic else "Riff"
        name = self._unique_track_name(base)
        context = tr("nuova traccia '{name}'", name=name)
        if kind == "drums":
            dlg = DrumGenerateDialog(self, project=self.project, instrument_name=instrument, context_label=context,
                                     default_bars=math.ceil(other_beats / bar_beats) if other_beats > 0 else 8,
                                     track_name=name)
        elif kind == "progression":
            dlg = ChordProgressionDialog(self, project=self.project, instrument_name=instrument,
                                         context_label=context,
                                         default_bars=round(other_beats / bar_beats) if other_beats > 0 else 0,
                                         track_name=name)
        elif kind == "bass":
            dlg = BassGenerateDialog(self, project=self.project, instrument_name=instrument, context_label=context,
                                     other_tracks=other_tracks, min_total_beats=other_beats, track_name=name)
        else:
            instr = get_instrument(instrument)
            dlg = MelodyGenerateDialog(
                self, project=self.project, instrument_name=instrument, context_label=context,
                other_tracks=other_tracks, polyphonic=instr.polyphonic, default_octave=instr.default_octave,
                range_low=instr.range_low, range_high=instr.range_high, min_total_beats=other_beats,
                track_name=name)
        if dlg.exec() != QDialog.Accepted:
            return
        self._add_filled_track(name, instrument, dlg.result_text(), box)
        self.statusBar().showMessage(tr("Traccia '{name}' creata e generata.", name=name), 4000)

    def add_track_from_midi(self):
        """Nuova traccia da un canale di un file MIDI (lo strumento e' quello
        riconosciuto nel file)."""
        result = self._pick_midi_channel_tokens()
        if result is None:
            return
        tokens_text, guessed_instrument, newly_created = result
        name = self._unique_track_name(guessed_instrument)
        self._add_filled_track(name, guessed_instrument, tokens_text, name)
        self._notify_new_instruments(newly_created)

    # ------------------------------------------------------------ menu ⋯ della traccia (mixer a colonna)

    def show_track_actions_menu(self, track_name, global_pos):
        """Menu ⋯ delle testate nella colonna della vista Testo. Tracce a box (o vuote, nella
        vista Struttura) e tracce audio: lo stesso menu delle testate della
        vista Struttura brano. Tracce a testo libero: le stesse azioni, ma
        che scrivono nel testo della traccia invece di creare box."""
        track = self.project.get_track(track_name)
        if track.is_audio or track.clips or (self.arrangement_action.isChecked() and not track.text.strip()):
            self.arrangement_view.show_track_menu(track_name, global_pos)
            return
        from PySide6.QtWidgets import QMenu
        view = self.arrangement_view
        instrument = track.instrument
        menu = QMenu(self)
        entries = []
        if instrument.is_percussion:
            entries.append((tr("Genera batteria..."), self.generate_drums_into_selected_track))
        elif view._is_bass_instrument(instrument):
            entries.append((tr("Genera basso da accordi..."), self.generate_bass_into_selected_track))
        if view._offers_chord_progression(track_name, instrument):
            entries.append((tr("Genera giro armonico..."), self.generate_progression_into_selected_track))
        if view._offers_melody(track_name, instrument):
            entries.append((tr("Genera accompagnamento...") if instrument.polyphonic else tr("Genera riff/melodia..."),
                            self.generate_melody_into_selected_track))
        actions = {}
        for label, slot in entries:
            actions[menu.addAction(label)] = slot
        if entries:
            menu.addSeparator()
        for label, slot in ((tr("Suona con la tastiera..."), self.play_keyboard_into_selected_track),
                            (tr("Importa MIDI..."), self.import_midi_into_selected_track),
                            (tr("Importa audio → note..."), self.import_audio_into_selected_track)):
            actions[menu.addAction(label)] = slot
        menu.addSeparator()
        actions[menu.addAction(tr("Nome e strumento..."))] = lambda: self._open_edit_dialog_for(track_name)
        if not self.project.get_track(track_name).is_audio:
            actions[menu.addAction(tr("Strumento plugin (VST3/LV2)..."))] = lambda: self.choose_track_synth(track_name)
            if self.project.get_track(track_name).synth:
                actions[menu.addAction(tr("Parametri dello strumento plugin..."))] = \
                    lambda: self.edit_track_synth(track_name)
        actions[menu.addAction(tr("Esporta MIDI (solo questa)..."))] = self.export_selected_track_midi
        actions[menu.addAction(tr("Esporta WAV (solo questa)..."))] = lambda: self.export_track_wav(track_name)
        actions[menu.addAction(tr("Esporta WAV asciutto (per il re-amping)..."))] = \
            lambda: self.export_track_wav(track_name, dry=True)
        menu.addSeparator()
        actions[menu.addAction(tr("Rimuovi traccia"))] = self.remove_track
        chosen = menu.exec(global_pos)
        if chosen in actions:
            view.select_box(None, None)
            self.select_track(track_name)
            actions[chosen]()

    def _record_start_options(self, preferred_beat=None):
        """[(etichetta, beat)] per 'Parti da:' del dialogo di registrazione:
        il punto richiesto (o la posizione corrente), l'inizio del loop se
        impostato, l'inizio del brano."""
        from .rhythm_generate_dialog import project_bar_beats
        bar_beats = project_bar_beats(self.project) or 4.0

        def bar(beat):
            return int(beat // bar_beats) + 1

        options = []
        if preferred_beat is not None:
            options.append((tr("Punto scelto (battuta {0})", bar(preferred_beat)), float(preferred_beat)))
        position = self._position_for_markers()
        if position > 0 and preferred_beat is None:
            options.append((tr("Posizione corrente (battuta {0})", bar(position)), float(position)))
        if getattr(self, "_loop_a_beat", None) is not None:
            options.append((tr("Inizio del loop A (battuta {0})", bar(self._loop_a_beat)), float(self._loop_a_beat)))
        options.append((tr("Inizio del brano"), 0.0))
        seen, unique = set(), []
        for label, beat in options:
            if beat not in seen:
                seen.add(beat)
                unique.append((label, beat))
        return unique

    def record_into_audio_track(self, track_name=None, start_beat=None):
        """Apre il dialogo di registrazione per una traccia audio (quella
        indicata, o la selezionata) e aggiunge la ripresa tenuta come clip."""
        from core.audio_recording import is_recording_available
        from core.audio_tracks import target_audio_dir

        if track_name is None:
            track, _clip = self._resolve_edit_target()
        else:
            track = self.project.get_track(track_name)
        if track is None or not track.is_audio:
            QMessageBox.information(
                self, tr("Nessuna traccia audio"),
                tr("Seleziona prima una traccia audio (Traccia → Aggiungi traccia audio... per crearne una)."))
            return
        if not is_recording_available():
            QMessageBox.warning(
                self, tr("Registrazione non disponibile"),
                tr("Per registrare serve la libreria di sistema PortAudio (libportaudio2 su Linux) "
                "insieme al pacchetto Python sounddevice. Vedi README.md, sezione Requisiti."))
            return
        options = self._record_start_options(start_beat)
        # La registrazione suona il brano per conto suo: niente doppio audio.
        if self.playback.is_playing():
            self.stop()
        self.arrangement_view._stop_preview()
        dlg = self._make_record_dialog(track, options, target_audio_dir(self.current_path))
        if dlg.exec() != QDialog.Accepted or dlg.result_clip() is None:
            return
        self._add_recorded_clip(track, dlg.result_clip(), dlg.input_profile(), dlg.input_channels_spec())

    def _make_record_dialog(self, track, options, target_dir):
        from .audio_record_dialog import AudioRecordDialog
        return AudioRecordDialog(self, self.project, track, options, target_dir)

    def _add_recorded_clip(self, track, clip, input_profile, input_channels):
        track.input_profile, track.input_channels = input_profile, input_channels
        view = self.arrangement_view
        end = clip.start_beat + view.clip_length_beats(track.name, clip)
        overlapped = [c for c in track.audio_clips
                      if c.start_beat < end and c.start_beat + view.clip_length_beats(track.name, c) > clip.start_beat]
        if overlapped:
            reply = QMessageBox.question(
                self, tr("Ripresa sovrapposta"),
                tr("La nuova ripresa si sovrappone a {0} clip della traccia '{name}'.\nEliminarle e tenere solo la nuova? (No = le tiene tutte: suoneranno insieme)", len(overlapped), name=track.name))
            if reply == QMessageBox.Yes:
                track.audio_clips = [c for c in track.audio_clips if c not in overlapped]
        track.audio_clips.append(clip)
        self._mark_dirty()
        self.refresh_mixer()
        self.select_track(track.name)
        self.statusBar().showMessage(
            tr("Ripresa '{name}' aggiunta alla traccia '{0}' (file: {file}).", track.name, name=clip.name, file=clip.file), 6000)

    def remove_track(self):
        if not self.current_track_name:
            return
        reply = QMessageBox.question(self, tr("Conferma"), tr("Rimuovere la traccia '{current_track_name}'?", current_track_name=self.current_track_name))
        if reply == QMessageBox.Yes:
            self.project.remove_track(self.current_track_name)
            self.current_track_name = None
            self._mark_dirty()
            self.refresh_mixer()

    def choose_track_synth(self, track_name=None):
        """Sceglie lo strumento plugin (VST3/LV2) che suona la traccia al
        posto del SoundFont, o lo toglie; poi apre i suoi parametri."""
        from .plugin_dialogs import PluginPickerDialog
        track_name = track_name or self.current_track_name
        if not track_name:
            QMessageBox.information(self, tr("Nessuna traccia"), tr("Seleziona prima una traccia."))
            return
        track = self.project.get_track(track_name)
        if track.is_audio:
            QMessageBox.information(self, tr("Traccia audio"), tr("Una traccia audio non ha note da far suonare a un plugin."))
            return
        dialog = PluginPickerDialog(self, instrument=True, current_ref=track.synth)
        if dialog.exec() != QDialog.Accepted:
            return
        ref = dialog.selected_ref()
        if ref is None or ref == track.synth:
            return
        track.synth, track.synth_params, track.synth_state = ref, {}, ""
        self._track_synth_changed(track_name)
        if ref and not ref.startswith("sfz:"):        # lo strumento SFZ interno non ha parametri
            self.edit_track_synth(track_name)

    def edit_track_synth(self, track_name=None):
        from .plugin_dialogs import PluginParamsDialog
        track_name = track_name or self.current_track_name
        if not track_name:
            return
        track = self.project.get_track(track_name)
        if not track.synth or track.synth.startswith("sfz:"):    # SFZ interno: niente parametri, si cambia il file
            self.choose_track_synth(track_name)
            return

        def changed(params, state, track=track, name=track_name):
            track.synth_params, track.synth_state = dict(params), state
            self._track_synth_changed(name)
        PluginParamsDialog(self, track.synth, track.synth_params, track.synth_state,
                           on_change=changed).exec()

    def _track_synth_changed(self, track_name):
        self.sync_mixer_widgets(track_name)
        self._on_mixer_changed(track_name)

    def edit_track(self):
        if not self.current_track_name:
            QMessageBox.information(self, tr("Nessuna traccia"), tr("Seleziona prima una traccia da modificare."))
            return
        self._open_edit_dialog_for(self.current_track_name)

    def _open_edit_dialog_for(self, name):
        track = self.project.get_track(name)
        if track.is_audio:
            self._rename_audio_track(track)
            return
        others = [t.name for t in self.project.tracks if t.name != name]
        dlg = AddTrackDialog(self, existing_names=others, edit_name=track.name,
                              edit_instrument=track.instrument_name)
        if dlg.exec() == QDialog.Accepted:
            new_name, new_instrument = dlg.result_values()
            if not new_name:
                QMessageBox.warning(self, tr("Nome mancante"), tr("Inserisci un nome traccia."))
                return
            try:
                self.project.update_track(name, new_name, new_instrument)
            except ValueError as e:
                QMessageBox.warning(self, tr("Errore"), str(e))
                return
            self._mark_dirty()
            self.refresh_mixer()
            self.select_track(new_name)
            self.statusBar().showMessage(tr("Traccia aggiornata: '{new_name}' ({new_instrument})", new_name=new_name, new_instrument=new_instrument), 4000)

    def _rename_audio_track(self, track):
        new_name, ok = QInputDialog.getText(self, tr("Rinomina traccia audio"), tr("Nome:"), text=track.name)
        new_name = new_name.strip()
        if not ok or not new_name or new_name == track.name:
            return
        try:
            self.project.update_track(track.name, new_name, track.instrument_name)
        except ValueError as e:
            QMessageBox.warning(self, tr("Errore"), str(e))
            return
        self._mark_dirty()
        self.refresh_mixer()
        self.select_track(new_name)

    # ------------------------------------------------------------ import/export singola traccia

    def _resolve_edit_target(self):
        """Traccia (ed eventuale box, se uno e' selezionato nella vista
        Struttura brano) su cui devono agire 'Suona con la tastiera/Importa
        audio/Importa MIDI (in questa/o)': se un box e' selezionato agiscono
        su di esso invece che sul testo lineare della traccia, esattamente
        come agiscono gia' sulla traccia selezionata nell'editor classico.
        Ritorna (track, clip_o_None), o (None, None) se non c'e' ne' una
        traccia ne' un box selezionati."""
        track = self.arrangement_view.selected_track()
        if track is not None:
            return track, self.arrangement_view.selected_clip
        if self.current_track_name:
            return self.project.get_track(self.current_track_name), None
        return None, None

    def export_selected_track_midi(self):
        if not self.current_track_name:
            QMessageBox.information(self, tr("Nessuna traccia"), tr("Seleziona prima una traccia da esportare."))
            return
        track = self.project.get_track(self.current_track_name)
        if self._reject_audio_track(track, tr("l'esportazione MIDI")):
            return
        ok, msg = validate_track_text(track.text, self.project.patterns)
        if not ok:
            QMessageBox.critical(self, tr("Errore di sintassi"), tr("Impossibile esportare:\n{msg}", msg=msg))
            return
        suggested = os.path.join(os.path.dirname(self._default_export_path(".mid")),
                                 f"{track.name.replace(' ', '_')}.mid")
        path, _ = QFileDialog.getSaveFileName(self, tr("Esporta MIDI della traccia"), suggested, tr("MIDI (*.mid)"),
                                                options=file_dialog_options())
        if not path:
            return
        try:
            export_single_track_to_midi(self.project, track.name, path)
            self.statusBar().showMessage(tr("Traccia '{name}' esportata: {path}", name=track.name, path=path), 4000)
        except Exception as e:
            QMessageBox.critical(self, tr("Errore export MIDI"), str(e))

    def export_selected_track_wav(self, dry: bool = False):
        """Menu Traccia → Esporta questa traccia → WAV (o WAV asciutto)."""
        if not self.current_track_name:
            QMessageBox.information(self, tr("Nessuna traccia"), tr("Seleziona prima una traccia da esportare."))
            return
        self.export_track_wav(self.current_track_name, dry=dry)

    def _pick_midi_channel_tokens(self):
        """Punto in comune fra 'Importa MIDI (in questa/o)' e 'Importa MIDI
        qui' (nuovo box, vedi gui.arrangement_view.new_box_from_midi_at):
        sceglie il file e l'eventuale canale e lo importa. Ritorna
        (tokens_text, guessed_instrument, newly_created) o None se l'utente
        ha annullato o non c'e' nulla da importare."""
        path, _ = QFileDialog.getOpenFileName(self, tr("Importa MIDI"), "", tr("MIDI (*.mid *.midi)"),
                                              options=file_dialog_options())
        if not path:
            return None
        try:
            channels = list_midi_channels(path)
        except Exception as e:
            QMessageBox.critical(self, tr("Errore lettura MIDI"), str(e))
            return None
        if not channels:
            QMessageBox.warning(self, tr("Nessuna nota"), tr("Il file MIDI non contiene note utilizzabili."))
            return None

        channel = None
        if len(channels) > 1:
            items = [tr("Canale {c} — {n} note — strumento suggerito: {g}", c=c, n=n, g=g) for c, n, g in channels]
            item, ok = QInputDialog.getItem(self, tr("Scegli il canale"), tr("Il MIDI contiene piu' canali:"),
                                              items, 0, False)
            if not ok:
                return None
            channel = channels[items.index(item)][0]

        before = set(list_instrument_names())
        try:
            tokens_text, guessed_instrument = import_midi_channel_into_track(
                path, channel, recognize_chords=app_settings.get_midi_import_recognize_chords(),
                min_bend_semitones=app_settings.get_midi_import_min_bend_semitones(),
            )
        except Exception as e:
            QMessageBox.critical(self, tr("Errore import MIDI"), str(e))
            return None
        newly_created = sorted(set(list_instrument_names()) - before)
        return tokens_text, guessed_instrument, newly_created

    def _maybe_update_instrument_from_midi(self, track, guessed_instrument):
        reply = QMessageBox.question(
            self, tr("Aggiorna strumento?"),
            tr("Strumento riconosciuto nel MIDI: '{guessed_instrument}'.\nImpostarlo anche per la traccia '{name}' (attualmente '{instrument_name}')?", guessed_instrument=guessed_instrument, name=track.name, instrument_name=track.instrument_name)
        )
        if reply == QMessageBox.Yes:
            try:
                self.project.update_track(track.name, track.name, guessed_instrument)
            except ValueError as e:
                QMessageBox.warning(self, tr("Errore"), str(e))

    def import_midi_into_selected_track(self):
        track, clip = self._resolve_edit_target()
        if track is None:
            QMessageBox.information(self, tr("Nessuna traccia"), tr("Seleziona prima una traccia (o un box) in cui importare."))
            return
        if self._reject_audio_track(track, tr("l'importazione MIDI")):
            return
        result = self._pick_midi_channel_tokens()
        if result is None:
            return
        tokens_text, guessed_instrument, newly_created = result
        self._maybe_update_instrument_from_midi(track, guessed_instrument)

        if clip is not None:
            clip.text = tokens_text
            self.arrangement_view.on_clip_changed(track.name)
            self.statusBar().showMessage(tr("MIDI importato nel box '{name}' (traccia '{0}').", track.name, name=clip.name), 4000)
        else:
            track.text = tokens_text
            self._mark_dirty()
            self.refresh_mixer()
            self.select_track(track.name)
            self.statusBar().showMessage(tr("MIDI importato nella traccia '{name}'.", name=track.name), 4000)
        self._notify_new_instruments(newly_created)

    def import_audio_into_selected_track(self):
        track, clip = self._resolve_edit_target()
        if track is None:
            QMessageBox.information(self, tr("Nessuna traccia"), tr("Seleziona prima una traccia (o un box) in cui importare l'audio."))
            return
        if track.is_audio:
            # Su una traccia audio il file resta audio: diventa una clip.
            self.arrangement_view.import_audio_clip(track.name, self.arrangement_view.end_of_track_beat(track.name))
            return
        label = tr("box '{name}' (traccia '{0}')", track.name, name=clip.name) if clip is not None else tr("traccia '{name}'", name=track.name)
        dlg = AudioImportDialog(self, project=self.project, instrument_name=track.instrument_name,
                                 context_label=label, track_name=track.name)
        accepted = dlg.exec() == QDialog.Accepted
        # Il dialogo puo' aver cambiato Tempo/Metrica del progetto (stesso
        # oggetto condiviso) anche se poi annullato: i campi in toolbar
        # vanno comunque riallineati.
        self._sync_tempo_metrica_fields()
        if not accepted:
            return
        if clip is not None:
            clip.text = dlg.result_text()
            self.arrangement_view.on_clip_changed(track.name)
            self.statusBar().showMessage(tr("Audio convertito e inserito nel box '{name}' (traccia '{0}').", track.name, name=clip.name), 4000)
        else:
            track.text = dlg.result_text()
            self._mark_dirty()
            self.refresh_mixer()
            self.select_track(track.name)
            self.statusBar().showMessage(tr("Audio convertito e inserito nella traccia '{name}'.", name=track.name), 4000)

    def play_keyboard_into_selected_track(self):
        track, clip = self._resolve_edit_target()
        if track is None:
            QMessageBox.information(self, tr("Nessuna traccia"), tr("Seleziona prima una traccia (o un box) in cui suonare."))
            return
        if self._reject_audio_track(track, tr("suonare con la tastiera")):
            return
        label = tr("box '{name}' (traccia '{0}')", track.name, name=clip.name) if clip is not None else tr("traccia '{name}'", name=track.name)
        dlg = KeyboardPlayDialog(self, project=self.project, instrument_name=track.instrument_name,
                                  context_label=label, current_track_name=track.name)
        accepted = dlg.exec() == QDialog.Accepted
        # Il dialogo puo' aver cambiato Tempo/Metrica del progetto (stesso
        # oggetto condiviso) anche se poi annullato: i campi in toolbar
        # vanno comunque riallineati.
        self._sync_tempo_metrica_fields()
        if not accepted:
            return
        new_text = dlg.result_text()
        # A differenza dei pattern (dove il corpo viene sostituito, vedi
        # PatternEditorDialog._play_keyboard): una traccia/box puo' gia'
        # contenere musica scritta a mano o importata prima, che andrebbe
        # persa sostituendola invece di accodare la performance appena
        # registrata.
        if clip is not None:
            clip.text = f"{clip.text.rstrip()} {new_text}" if clip.text.strip() else new_text
            self.arrangement_view.on_clip_changed(track.name)
            self.statusBar().showMessage(tr("Performance registrata e aggiunta al box '{name}' (traccia '{0}').", track.name, name=clip.name), 4000)
        else:
            track.text = f"{track.text.rstrip()} {new_text}" if track.text.strip() else new_text
            self._mark_dirty()
            self.refresh_mixer()
            self.select_track(track.name)
            self.statusBar().showMessage(tr("Performance registrata e aggiunta alla traccia '{name}'.", name=track.name), 4000)

    def _append_or_replace_track_text(self, track, new_text):
        """Accoda 'new_text' al contenuto gia' presente nella traccia (o lo
        sostituisce se la traccia era vuota) - stessa convenzione di
        play_keyboard_into_selected_track, per non perdere musica scritta a
        mano o importata in precedenza."""
        if track.text.strip():
            track.text = f"{track.text.rstrip()} {new_text}"
        else:
            track.text = new_text
        self._mark_dirty()

    def generate_drums_into_selected_track(self):
        if not self.current_track_name:
            QMessageBox.information(self, tr("Nessuna traccia"), tr("Seleziona prima una traccia in cui generare la batteria."))
            return
        track = self.project.get_track(self.current_track_name)
        if self._reject_audio_track(track, tr("la generazione della batteria")):
            return
        if not track.instrument.is_percussion:
            QMessageBox.information(
                self, tr("Traccia non percussiva"),
                tr("La traccia '{name}' usa lo strumento '{instrument_name}', non percussivo.\nSeleziona (o crea) una traccia con uno strumento a percussione (es. Drums).", name=track.name, instrument_name=track.instrument_name)
            )
            return
        # Preimposta le battute su quelle necessarie a coprire l'estensione
        # delle altre tracce gia' scritte (vedi core.rhythm_generate.
        # tracks_duration_beats), cosi' la batteria generata copre di default
        # l'intero brano invece di fermarsi a meta' - 8 se non c'e' ancora
        # nient'altro da coprire (comportamento originale).
        other_beats = tracks_duration_beats(self.project, exclude_track_name=track.name)
        from .rhythm_generate_dialog import project_bar_beats
        default_bars = math.ceil(other_beats / project_bar_beats(self.project)) if other_beats > 0 else 8
        dlg = DrumGenerateDialog(self, project=self.project, instrument_name=track.instrument_name,
                                  context_label=tr("traccia '{name}'", name=track.name), default_bars=default_bars,
                                  track_name=track.name)
        if dlg.exec() != QDialog.Accepted:
            return
        self._append_or_replace_track_text(track, dlg.result_text())
        self.refresh_mixer()
        self.select_track(track.name)
        self.statusBar().showMessage(tr("Batteria generata e aggiunta alla traccia '{name}'.", name=track.name), 4000)

    def generate_bass_into_selected_track(self):
        if not self.current_track_name:
            QMessageBox.information(self, tr("Nessuna traccia"), tr("Seleziona prima una traccia in cui generare il basso."))
            return
        track = self.project.get_track(self.current_track_name)
        if self._reject_audio_track(track, tr("la generazione del basso")):
            return
        other_tracks = [(t.name, t.text) for t in self.project.tracks
                        if t.name != track.name and not t.is_audio]
        if not other_tracks:
            QMessageBox.information(
                self, tr("Nessuna traccia sorgente"),
                tr("Serve un'altra traccia con degli accordi scritti da cui far derivare il basso.")
            )
            return
        # Fa ripetere ciclicamente la progressione di accordi (vedi
        # core.rhythm_generate.generate_bass_from_chords) finche' non copre
        # l'estensione delle altre tracce gia' scritte, invece di fermarsi
        # alla fine della sola traccia di accordi sorgente scelta.
        other_beats = tracks_duration_beats(self.project, exclude_track_name=track.name)
        dlg = BassGenerateDialog(self, project=self.project, instrument_name=track.instrument_name,
                                  context_label=tr("traccia '{name}'", name=track.name), other_tracks=other_tracks,
                                  min_total_beats=other_beats, track_name=track.name)
        if dlg.exec() != QDialog.Accepted:
            return
        self._append_or_replace_track_text(track, dlg.result_text())
        self.refresh_mixer()
        self.select_track(track.name)
        self.statusBar().showMessage(tr("Basso generato e aggiunto alla traccia '{name}'.", name=track.name), 4000)

    def save_selected_track_as_style(self):
        """Traccia → Salva come stile del generatore: tutta la traccia selezionata."""
        from .save_style_dialog import SaveStyleDialog, chord_sources_of, source_for_part
        if not self.current_track_name:
            QMessageBox.information(self, tr("Nessuna traccia"), tr("Seleziona prima la traccia da cui ricavare lo stile."))
            return
        track = self.project.get_track(self.current_track_name)
        if self._reject_audio_track(track, tr("il salvataggio come stile")):
            return
        if not track.text.strip():
            QMessageBox.information(self, tr("Traccia vuota"), tr("La traccia non contiene note da cui ricavare uno stile."))
            return
        dlg = SaveStyleDialog(self, [source_for_part(tr("traccia '{name}'", name=track.name), track.text, track.instrument)],
                              chord_sources_of(self.project, track.name), self.project.patterns,
                              meter=self.project.time_sig)
        if dlg.exec() == QDialog.Accepted and dlg.saved_style():
            self.statusBar().showMessage(tr("Stile «{0}» salvato fra gli stili personali.", dlg.saved_style()[1]), 4000)

    def manage_user_styles(self):
        from .save_style_dialog import UserStylesDialog
        UserStylesDialog(self).exec()

    def generate_melody_into_selected_track(self):
        if not self.current_track_name:
            QMessageBox.information(
                self, tr("Nessuna traccia"),
                tr("Seleziona prima una traccia in cui generare l'accompagnamento o il riff.")
            )
            return
        track = self.project.get_track(self.current_track_name)
        if self._reject_audio_track(track, tr("la generazione di accompagnamento e riff")):
            return
        instrument = track.instrument
        if instrument.is_percussion:
            QMessageBox.information(
                self, tr("Traccia percussiva"),
                tr("La traccia '{name}' usa lo strumento '{instrument_name}', percussivo.\nUsa 'Genera batteria...' invece: qui le note sono altezze, non hanno senso su una traccia percussiva.", name=track.name, instrument_name=track.instrument_name)
            )
            return
        if not project_has_chords(self.project, exclude_track_name=track.name):
            QMessageBox.information(
                self, tr("Nessun giro di accordi"),
                tr("L'accompagnamento e il riff seguono gli accordi di un'altra traccia, ma nel brano "
                "non ce ne sono ancora.\nCrea prima un giro armonico in una traccia polifonica "
                "(Traccia → Genera giro armonico in questa traccia...).")
            )
            return
        other_tracks = [(t.name, t.text) for t in self.project.tracks
                        if t.name != track.name and not t.is_audio]
        other_beats = tracks_duration_beats(self.project, exclude_track_name=track.name)
        dlg = MelodyGenerateDialog(
            self, project=self.project, instrument_name=track.instrument_name,
            context_label=tr("traccia '{name}'", name=track.name), other_tracks=other_tracks,
            polyphonic=instrument.polyphonic, default_octave=instrument.default_octave,
            range_low=instrument.range_low, range_high=instrument.range_high,
            min_total_beats=other_beats, track_name=track.name,
        )
        if dlg.exec() != QDialog.Accepted:
            return
        self._append_or_replace_track_text(track, dlg.result_text())
        self.refresh_mixer()
        self.select_track(track.name)
        kind = "Accompagnamento" if instrument.polyphonic else "Riff/melodia"
        self.statusBar().showMessage(tr("{kind} generato e aggiunto alla traccia '{name}'.", kind=kind, name=track.name), 4000)

    def generate_progression_into_selected_track(self):
        if not self.current_track_name:
            QMessageBox.information(self, tr("Nessuna traccia"),
                                    tr("Seleziona prima una traccia in cui generare il giro armonico."))
            return
        track = self.project.get_track(self.current_track_name)
        if self._reject_audio_track(track, tr("la generazione del giro armonico")):
            return
        instrument = track.instrument
        if instrument.is_percussion or not instrument.polyphonic:
            QMessageBox.information(
                self, tr("Strumento non adatto"),
                tr("La traccia '{name}' usa lo strumento '{instrument_name}', che non suona accordi.\nScegli una traccia con uno strumento polifonico (pianoforte, chitarra, organo, pad...).", name=track.name, instrument_name=track.instrument_name)
            )
            return
        from .rhythm_generate_dialog import project_bar_beats
        other_beats = tracks_duration_beats(self.project, exclude_track_name=track.name)
        default_bars = round(other_beats / project_bar_beats(self.project)) if other_beats > 0 else 0
        dlg = ChordProgressionDialog(self, project=self.project, instrument_name=track.instrument_name,
                                     context_label=tr("traccia '{name}'", name=track.name), default_bars=default_bars,
                                     track_name=track.name, default_key=last_box_key(self.project, track))
        if dlg.exec() != QDialog.Accepted:
            return
        self._append_or_replace_track_text(track, dlg.result_text())
        self.refresh_mixer()
        self.select_track(track.name)
        self.statusBar().showMessage(tr("Giro armonico generato e aggiunto alla traccia '{name}'.", name=track.name), 4000)
