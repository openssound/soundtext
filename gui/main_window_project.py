import os
import re

import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFileDialog, QMessageBox, QProgressDialog

from core.model import Project, Clip
from core.arrangement import flatten_clips_to_text, split_text_into_box_segments
from core.instruments import list_instrument_names, set_session_instruments
from core.notation import (validate_track_text, rewrite_tokens, map_nested_tokens, split_note_value,
                           RE_CHORD, relative_text, key_signature_alters, NotationError)
from core.chords import parse_chord_symbol, voice_chord, midi_to_token, apply_bass_note
from core.project_io import load_project_file, save_project_file, ensure_songs_dir
from core.autosave import AUTOSAVE_INTERVAL_S, RecoverySession, find_recoverable
from core.midi_export import export_project_to_midi
from core.musicxml_export import export_project_to_musicxml
from core.midi_import import import_midi_file
from core.musicxml_import import import_musicxml_file
from core.abc_export import export_project_to_abc
from core.abc_import import import_abc_file
from core.mtxt_io import export_project_to_mtxt, import_mtxt_file
from core.key_detect import detect_key
from core import settings as app_settings

from core.version import APP_NAME

from .instrument_dialog import InstrumentManagerDialog
from .midi_library_dialog import MidiLibraryDialog
from .pattern_editor_dialog import PatternEditorDialog
from .help_dialog import HelpDialog
from .about_dialog import AboutDialog
from .worker import Worker
from core.i18n import tr
from .file_dialogs import file_dialog_options


class ProjectMixin:
    """Ciclo di vita del progetto (nuovo/apri/salva, import/export MIDI
    dell'intero ensemble), congelamento accordi, gestione di
    strumenti/pattern/libreria MIDI e riorganizzazione con pattern."""

    # ------------------------------------------------------------ progetto

    def _on_tempo_changed(self, value):
        self.project.tempo_bpm = value
        self._mark_dirty(merge_key="tempo")
        if any(t.audio_clips for t in self.project.tracks):
            # L'audio non viene stirato (vedi core.audio_tracks): le clip
            # restano al loro beat ma durano gli stessi secondi, quindi
            # occupano piu' o meno beat e i loro box vanno ridisegnati.
            self.arrangement_view.refresh()
            self.statusBar().showMessage(
                tr("Nota: le tracce audio non seguono il cambio di tempo (restano alla stessa "
                "velocita', ancorate al beat in cui iniziano)."), 6000)

    def _on_metrica_changed(self, text):
        text = text.strip()
        if re.match(r"^\d+/\d+$", text):
            self.project.time_sig = text
            self._mark_dirty(merge_key="metrica")
            self._validate_current()     # i controlli di battuta dipendono dalla metrica

    def _on_pickup_changed(self, value):
        self.project.pickup = float(value)
        self._mark_dirty(merge_key="pickup")
        self._validate_current()     # i controlli di battuta dipendono dal levare
        self.arrangement_view.refresh()

    def _on_key_changed(self, text):
        self.project.key = text.strip()
        self._mark_dirty(merge_key="key")

    def _on_master_volume_changed(self, value):
        self.project.master_volume = value
        self.master_vol_value_label.setText(f"{value}%")
        self._on_mixer_changed(None)  # marca gia' dirty (vedi gui.main_window_playback)

    APP_TITLE = APP_NAME

    def _update_window_title(self, filename: str = None):
        if filename:
            self.setWindowTitle(f"{self.APP_TITLE} — {filename}")
        else:
            self.setWindowTitle(self.APP_TITLE)

    def new_project(self):
        if not self._confirm_discard_unsaved():
            return
        self._replace_project(Project(name=tr("Nuovo progetto")))

    def _confirm_discard_unsaved(self) -> bool:
        """Se il progetto ha modifiche non salvate (vedi _mark_dirty), chiede
        se salvarle prima di procedere (Salva/Scarta/Annulla) - stessa logica
        usata da closeEvent, condivisa anche da nuovo/apri/importa MIDI
        prima di sostituire il progetto corrente (vedi _replace_project).
        Ritorna True se si puo' procedere (nessuna modifica da salvare, o
        l'utente ha scelto Scarta, o ha salvato con successo), False se
        l'operazione va annullata (Annulla, o 'Salva con nome' a sua volta
        annullato: non si puo' considerare salvato)."""
        if not self._dirty:
            return True
        reply = QMessageBox.question(
            self, tr("Modifiche non salvate"),
            tr("Il progetto contiene modifiche non salvate. Vuoi salvarle prima di continuare?"),
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save,
        )
        if reply == QMessageBox.Cancel:
            return False
        if reply == QMessageBox.Save:
            self.save_project()
            if self._dirty:
                return False
        return True

    def _sync_tempo_metrica_fields(self):
        """Aggiorna i campi Tempo/Metrica/Tonalita' della toolbar con i
        valori 'a riposo' (battuta 1) del progetto corrente, usato dopo aver
        sostituito self.project (nuovo/apri/importa) o dopo Annulla/Ripeti.
        Senza emettere i segnali di modifica: i valori vengono dal progetto
        stesso, e altrimenti un progetto appena aperto risulterebbe gia'
        "modificato" (con la richiesta di salvarlo alla chiusura)."""
        widgets = (self.tempo_spin, self.metrica_combo, self.key_combo, self.pickup_spin)
        for widget in widgets:
            widget.blockSignals(True)
        self.pickup_spin.setValue(self.project.pickup)
        self.tempo_spin.setValue(self.project.tempo_bpm)
        self.metrica_combo.setCurrentText(self.project.time_sig)
        self.key_combo.setCurrentText(self.project.key)
        for widget in widgets:
            widget.blockSignals(False)

    def _sync_master_volume_slider(self):
        """Aggiorna lo slider del volume master senza ri-emettere valueChanged
        (e quindi senza far ripartire una riproduzione in corso), usato dopo
        aver sostituito self.project (nuovo/apri/importa)."""
        self.master_vol_slider.blockSignals(True)
        self.master_vol_slider.setValue(self.project.master_volume)
        self.master_vol_slider.blockSignals(False)
        self.master_vol_value_label.setText(f"{self.project.master_volume}%")
        self.refresh_master_fx_button()

    def _replace_project(self, project, *, path=None, title=None, status_msg=None, status_timeout=4000):
        """Sostituisce self.project con `project` e aggiorna tutta la UI che ne
        dipende (campi tempo/metrica, slider volume master, mixer, titolo
        finestra ed eventuale messaggio in barra di stato). Usato da
        nuovo/apri/importa MIDI, che condividono questa sequenza."""
        self.effects_panel.discard()      # il pannello Effetti era sul brano precedente
        self.project = project
        set_session_instruments(project.instruments)
        self.current_path = path
        self.current_track_name = None
        # Il progetto appena sostituito e' per definizione "a riposo": non ci
        # sono ancora modifiche da salvare rispetto a questo stato (vedi
        # _mark_dirty/closeEvent).
        self._dirty = False
        self._clear_recovery_copy()
        # Loop A-B e punto di ripresa si riferiscono al brano precedente.
        self._playback_paused_beat = None
        self.clear_loop()
        self.history.reset(project)
        self._update_undo_actions()
        self._sync_tempo_metrica_fields()
        self._sync_master_volume_slider()
        self.refresh_mixer()
        self._update_window_title(title)
        if status_msg:
            self.statusBar().showMessage(status_msg, status_timeout)

    def open_project(self):
        if not self._confirm_discard_unsaved():
            return
        path, _ = QFileDialog.getOpenFileName(self, tr("Apri progetto"), ensure_songs_dir(),
                                              tr("Progetti (*.st *.txt)"),
                                              options=file_dialog_options())
        if not path:
            return
        try:
            self._load_and_apply_project(path)
        except Exception as e:
            QMessageBox.critical(self, tr("Errore apertura"), str(e))

    def _load_and_apply_project(self, path):
        """Carica un progetto da percorso e aggiorna la UI, notificando
        l'utente se sono stati registrati automaticamente strumenti
        personalizzati incorporati nel file (usato sia da 'Apri progetto'
        sia dall'avvio da riga di comando)."""
        before = set(list_instrument_names())
        project = load_project_file(path)
        after = set(list_instrument_names())
        newly_loaded = sorted(after - before)

        self._replace_project(project, path=path, title=os.path.basename(path))

        from st_language.stfile import LANGUAGE_VERSION
        if project.st_version and project.st_version > LANGUAGE_VERSION:
            QMessageBox.warning(
                self, tr("File di una versione piu' recente"),
                tr("Il file e' scritto con ST {0}.{1}, questa versione di SoundText conosce la {2}.{3}: "
                   "qualcosa potrebbe non essere letto. Salvandolo, quelle parti andrebbero perse.",
                   *project.st_version, *LANGUAGE_VERSION))

        if newly_loaded:
            msg = (tr("Progetto caricato: {path}  —  strumenti personalizzati caricati automaticamente: {0}", ', '.join(newly_loaded), path=path))
            self.statusBar().showMessage(msg, 8000)
            QMessageBox.information(
                self, tr("Strumenti caricati automaticamente"),
                tr("Questo progetto usa strumenti personalizzati non ancora presenti "
                "sul tuo sistema. Sono stati registrati automaticamente dalla "
                "definizione incorporata nel file:\n\n") + "\n".join(f"• {n}" for n in newly_loaded)
            )
        else:
            self.statusBar().showMessage(tr("Progetto caricato: {path}", path=path), 4000)

    def save_project(self):
        if not self.current_path:
            self.save_project_as()
            return
        try:
            save_project_file(self.project, self.current_path)
        except OSError as e:
            QMessageBox.critical(self, tr("Errore di salvataggio"), tr("Impossibile salvare '{current_path}':\n{e}", current_path=self.current_path, e=e))
            return
        self._dirty = False
        self._clear_recovery_copy()
        self._update_window_title(os.path.basename(self.current_path))
        self.statusBar().showMessage(tr("Salvato: {current_path}", current_path=self.current_path), 4000)

    def _default_save_filename(self) -> str:
        """Nome file proposto da 'Salva progetto come': il titolo del
        progetto (project.name), se ce n'e' uno diverso dal placeholder
        generico assegnato da new_project()/Project() — tipicamente
        impostato importando un MIDI (nome del file). 'progetto.st'
        resta il default solo per un progetto nuovo mai rinominato."""
        name = (self.project.name or "").strip()
        if not name or name == "Nuovo progetto":
            return "progetto.st"
        safe_name = re.sub(r'[\\/:*?"<>|]', "_", name).strip()
        return f"{safe_name}.st" if safe_name else "progetto.st"

    def save_project_as(self):
        path, _ = QFileDialog.getSaveFileName(self, tr("Salva progetto come"), self._default_export_path(".st"),
                                                tr("Progetto (*.st)"),
                                                options=file_dialog_options())
        if not path:
            return
        try:
            save_project_file(self.project, path)
        except OSError as e:
            QMessageBox.critical(self, tr("Errore di salvataggio"), tr("Impossibile salvare '{path}':\n{e}", path=path, e=e))
            return
        self.current_path = path
        # Come al caricamento (load_project_file), il nome del progetto e' il
        # nome del file: cosi' le esportazioni successive lo propongono.
        self.project.name = os.path.splitext(os.path.basename(path))[0]
        self._dirty = False
        self._clear_recovery_copy()
        self._update_window_title(os.path.basename(path))
        self.statusBar().showMessage(tr("Salvato: {path}", path=path), 4000)

    def _default_export_path(self, ext: str) -> str:
        """Percorso proposto da "Salva come" e dalle esportazioni del brano
        (MIDI, WAV): nome del progetto con l'estensione data, nella cartella
        del progetto salvato (o in quella dei brani se non e' ancora stato
        salvato)."""
        base = os.path.splitext(self._default_save_filename())[0]
        start_dir = os.path.dirname(self.current_path) if self.current_path else ensure_songs_dir()
        return os.path.join(start_dir, base + ext)

    def show_midi_import_slide_settings(self):
        from .midi_import_slide_dialog import MidiImportSlideDialog
        MidiImportSlideDialog(self).exec()

    def import_midi(self):
        if not self._confirm_discard_unsaved():
            return
        path, _ = QFileDialog.getOpenFileName(self, tr("Importa MIDI"), "", tr("MIDI (*.mid *.midi)"),
                                              options=file_dialog_options())
        if not path:
            return
        try:
            self._import_midi_as_new_project(
                path, project_name=os.path.splitext(os.path.basename(path))[0],
                title=os.path.basename(path), status_msg=tr("MIDI importato: {path}", path=path),
            )
        except Exception as e:
            QMessageBox.critical(self, tr("Errore import MIDI"), str(e))

    def import_musicxml(self):
        if not self._confirm_discard_unsaved():
            return
        path, _ = QFileDialog.getOpenFileName(self, tr("Importa MusicXML"), "",
                                              tr("MusicXML (*.musicxml *.mxl *.xml)"),
                                              options=file_dialog_options())
        if not path:
            return
        try:
            self._import_musicxml_as_new_project(path)
        except Exception as e:
            QMessageBox.critical(self, tr("Errore import MusicXML"), str(e))

    def _import_musicxml_as_new_project(self, path):
        """Importa una partitura MusicXML come nuovo progetto (vedi
        core.musicxml_import), come l'import MIDI."""
        before = set(list_instrument_names())
        project = import_musicxml_file(
            path,
            recognize_chords=app_settings.get_midi_import_recognize_chords(),
            min_bend_semitones=app_settings.get_midi_import_min_bend_semitones(),
        )
        newly_created = sorted(set(list_instrument_names()) - before)
        self._split_tracks_into_boxes(project)
        self._replace_project(project, title=os.path.basename(path),
                              status_msg=tr("MusicXML importato: {path}", path=path))
        self._notify_new_instruments(newly_created)

    def import_abc(self):
        if not self._confirm_discard_unsaved():
            return
        path, _ = QFileDialog.getOpenFileName(self, tr("Importa ABC"), "", tr("ABC (*.abc)"),
                                              options=file_dialog_options())
        if not path:
            return
        try:
            self._import_abc_as_new_project(path)
        except Exception as e:
            QMessageBox.critical(self, tr("Errore import ABC"), str(e))

    def _import_abc_as_new_project(self, path):
        """Importa un brano ABC come nuovo progetto (vedi core.abc_import),
        come l'import MusicXML."""
        before = set(list_instrument_names())
        project = import_abc_file(
            path,
            recognize_chords=app_settings.get_midi_import_recognize_chords(),
            min_bend_semitones=app_settings.get_midi_import_min_bend_semitones(),
        )
        newly_created = sorted(set(list_instrument_names()) - before)
        self._split_tracks_into_boxes(project)
        self._replace_project(project, title=os.path.basename(path),
                              status_msg=tr("ABC importato: {path}", path=path))
        self._notify_new_instruments(newly_created)

    def import_mtxt(self):
        if not self._confirm_discard_unsaved():
            return
        path, _ = QFileDialog.getOpenFileName(self, tr("Importa MTXT"), "", tr("MTXT (*.mtxt)"),
                                              options=file_dialog_options())
        if not path:
            return
        try:
            self._import_mtxt_as_new_project(path)
        except Exception as e:
            QMessageBox.critical(self, tr("Errore import MTXT"), str(e))

    def _import_mtxt_as_new_project(self, path):
        """Importa un file MTXT come nuovo progetto (vedi core.mtxt_io),
        come l'import MIDI."""
        before = set(list_instrument_names())
        project = import_mtxt_file(
            path,
            recognize_chords=app_settings.get_midi_import_recognize_chords(),
            min_bend_semitones=app_settings.get_midi_import_min_bend_semitones(),
        )
        newly_created = sorted(set(list_instrument_names()) - before)
        self._split_tracks_into_boxes(project)
        self._replace_project(project, title=os.path.basename(path),
                              status_msg=tr("MTXT importato: {path}", path=path))
        self._notify_new_instruments(newly_created)

    def _import_midi_as_new_project(self, path, project_name, title, status_msg):
        """Importa un file MIDI come nuovo progetto (rimpiazza quello
        corrente, come new_project()) e notifica eventuali strumenti creati
        automaticamente."""
        before = set(list_instrument_names())
        project = import_midi_file(
            path, project_name=project_name,
            recognize_chords=app_settings.get_midi_import_recognize_chords(),
            min_bend_semitones=app_settings.get_midi_import_min_bend_semitones(),
        )
        newly_created = sorted(set(list_instrument_names()) - before)
        self._split_tracks_into_boxes(project)
        self._replace_project(project, title=title, status_msg=status_msg)
        self._notify_new_instruments(newly_created)

    def _split_tracks_into_boxes(self, project):
        """Racchiude il testo gia' importato/generato di ogni traccia in uno
        o piu' box (vedi core.model.Clip/core.arrangement.
        split_text_into_box_segments, che divide dove una pausa continua
        supera GAP_SPLIT_THRESHOLD_BEATS, minimizzando le pause "incollate"
        dentro il testo di un singolo box), cosi' il contenuto e' subito
        visibile e strutturato anche nella vista Struttura brano invece di
        apparire come un canvas vuoto (che si vedrebbe solo passando
        all'editor classico). Una traccia vuota non genera alcun box, come
        per il salvataggio (vedi core.project_io.project_to_text)."""
        for t in project.tracks:
            if not t.text.strip():
                continue
            segments = split_text_into_box_segments(t.text, project.patterns, t.instrument.default_octave,
                                                    meter=project.meter())
            if len(segments) <= 1:
                # Il segmento non ha le pause iniziali: il box comincia dove
                # comincia lui, non a 0 (altrimenti una parte che entra a
                # meta' brano suonerebbe dall'inizio).
                t.clips = [Clip(name=t.name, text=(segments[0][1] if segments else t.text),
                                start_beat=(segments[0][0] if segments else 0.0))]
            else:
                t.clips = [
                    Clip(name=f"{t.name} {i + 1}", text=seg_text, start_beat=start_beat)
                    for i, (start_beat, seg_text) in enumerate(segments)
                ]
            t.text = flatten_clips_to_text(t.clips, project.patterns, t.instrument.default_octave,
                                           meter=project.meter())

    def _notify_new_instruments(self, newly_created):
        """Avvisa l'utente quando l'import MIDI ha registrato automaticamente
        nuovi strumenti personalizzati (nessuno strumento disponibile aveva
        esattamente il Program Change GM richiesto)."""
        if not newly_created:
            return
        QMessageBox.information(
            self, tr("Nuovi strumenti creati automaticamente"),
            tr("Il MIDI importato usa Program Change GM non presenti tra gli "
            "strumenti disponibili: sono stati creati automaticamente, con i "
            "parametri suggeriti per la famiglia General MIDI corrispondente "
            "(modificabili in Strumenti → Gestisci strumenti):\n\n")
            + "\n".join(f"• {n}" for n in newly_created)
        )

    def _check_tracks_syntax(self) -> bool:
        for t in self.project.tracks:
            ok, msg = validate_track_text(t.text, self.project.patterns)
            if not ok:
                QMessageBox.critical(self, tr("Errore di sintassi"),
                                      tr("Impossibile esportare: la traccia '{name}' contiene un errore:\n{msg}", name=t.name, msg=msg))
                return False
        return True

    def export_midi(self):
        if not self._check_tracks_syntax():
            return
        path, _ = QFileDialog.getSaveFileName(self, tr("Esporta MIDI"), self._default_export_path(".mid"), tr("MIDI (*.mid)"),
                                                options=file_dialog_options())
        if not path:
            return
        try:
            export_project_to_midi(self.project, path)
        except Exception as e:
            QMessageBox.critical(self, tr("Errore export MIDI"), str(e))
            return
        audio_tracks = [t.name for t in self.project.audible_tracks() if t.is_audio and t.audio_clips]
        if audio_tracks:
            QMessageBox.information(
                self, tr("Tracce audio non incluse"),
                tr("MIDI esportato: {path}\n\nUn file MIDI contiene solo note: {0} tracce audio non sono incluse ({1}).\nPer un file con tutto il brano usa Progetto → Esporta mix audio (WAV)...", len(audio_tracks), ', '.join(audio_tracks), path=path))
        self.statusBar().showMessage(tr("MIDI esportato: {path}", path=path), 4000)

    def export_musicxml(self):
        """Esporta le tracce udibili come partitura MusicXML (vedi
        core.musicxml_export)."""
        if not self._check_tracks_syntax():
            return
        path, _ = QFileDialog.getSaveFileName(self, tr("Esporta partitura (MusicXML)"),
                                                self._default_export_path(".musicxml"),
                                                tr("MusicXML (*.musicxml *.xml)"),
                                                options=file_dialog_options())
        if not path:
            return
        if not os.path.splitext(path)[1]:
            path += ".musicxml"
        try:
            export_project_to_musicxml(self.project, path)
        except Exception as e:
            QMessageBox.critical(self, tr("Errore export MusicXML"), str(e))
            return
        self.statusBar().showMessage(tr("Partitura MusicXML esportata: {path}", path=path), 4000)

    def export_abc(self):
        """Esporta le tracce udibili in notazione ABC (vedi core.abc_export)."""
        if not self._check_tracks_syntax():
            return
        path, _ = QFileDialog.getSaveFileName(self, tr("Esporta partitura (ABC)"),
                                                self._default_export_path(".abc"),
                                                tr("ABC (*.abc)"),
                                                options=file_dialog_options())
        if not path:
            return
        if not os.path.splitext(path)[1]:
            path += ".abc"
        try:
            export_project_to_abc(self.project, path)
        except Exception as e:
            QMessageBox.critical(self, tr("Errore export ABC"), str(e))
            return
        self.statusBar().showMessage(tr("Partitura ABC esportata: {path}", path=path), 4000)

    def export_mtxt(self):
        """Esporta le tracce udibili in MTXT (vedi core.mtxt_io)."""
        if not self._check_tracks_syntax():
            return
        path, _ = QFileDialog.getSaveFileName(self, tr("Esporta MTXT"), self._default_export_path(".mtxt"),
                                                tr("MTXT (*.mtxt)"),
                                                options=file_dialog_options())
        if not path:
            return
        if not os.path.splitext(path)[1]:
            path += ".mtxt"
        try:
            export_project_to_mtxt(self.project, path)
        except Exception as e:
            QMessageBox.critical(self, tr("Errore export MTXT"), str(e))
            return
        self.statusBar().showMessage(tr("MTXT esportato: {path}", path=path), 4000)

    def _score_unavailable(self) -> bool:
        """Avvisa se manca Verovio (la libreria che impagina la partitura)."""
        from core import score_render
        if score_render.available():
            return False
        QMessageBox.information(
            self, tr("Partitura"),
            tr("Per vedere e stampare la partitura serve la libreria Verovio, che non risulta "
               "installata.\n\nInstallala con:\n    {cmd}\npoi riavvia SoundText. Intanto puoi usare "
               "Esporta partitura (MusicXML) e aprire il file con MuseScore.", cmd="pip install verovio"))
        return True

    def show_score_view(self):
        """Vista Partitura (gui.score_view): finestra non modale, una sola."""
        if self._score_unavailable():
            return
        from .score_view import ScoreDialog
        dlg = getattr(self, "_score_dialog", None)
        if dlg is None:
            dlg = self._score_dialog = ScoreDialog(self)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def export_score_pdf(self):
        """Partitura delle tracce udibili in PDF, senza aprire la vista."""
        if self._score_unavailable() or not self._check_tracks_syntax():
            return
        from .score_view import export_pdf, render_score, score_tracks
        tracks = score_tracks(self.project)
        if not tracks:
            QMessageBox.information(self, tr("Partitura"), tr("Nessuna traccia con note da mettere in partitura."))
            return
        path, _ = QFileDialog.getSaveFileName(self, tr("Esporta partitura (PDF)"), self._default_export_path(".pdf"),
                                              tr("PDF (*.pdf)"), options=file_dialog_options())
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        try:
            export_pdf(render_score(self.project, tracks), path)
        except Exception as e:
            QMessageBox.critical(self, tr("Errore export PDF"), str(e))
            return
        self.statusBar().showMessage(tr("Partitura esportata: {path}", path=path), 4000)

    def export_mix_wav(self):
        """Esporta il brano come si sente (tracce udibili, audio compreso)
        in un WAV, renderizzando in un thread separato."""
        if not self._check_tracks_syntax():
            return
        self._export_wav(tr("Esporta mix audio"), self._default_export_path(".wav"), None, tr("Mix audio esportato"))

    def export_track_wav(self, track_name: str, dry: bool = False):
        """Esporta in un WAV una sola traccia (con notazione o audio), come
        si sente in Solo: ignora Solo/Mute delle altre. Con 'dry' la traccia
        esce asciutta (senza effetti, riverbero/chorus e pan), per farla
        passare in un simulatore di amplificatore esterno (re-amping)."""
        track = self.project.get_track(track_name)
        if not track.is_audio:
            ok, msg = validate_track_text(track.text, self.project.patterns)
            if not ok:
                QMessageBox.critical(self, tr("Errore di sintassi"), tr("Impossibile esportare:\n{msg}", msg=msg))
                return
        start_dir = os.path.dirname(self._default_export_path(".wav"))
        safe_name = re.sub(r'[\\/:*?"<>|]', "_", track.name).strip() or "traccia"
        if dry:
            self._export_wav(tr("Esporta WAV asciutto della traccia"),
                             os.path.join(start_dir, safe_name + "_asciutto.wav"), [track],
                             tr("Traccia '{name}' esportata asciutta (senza effetti)", name=track.name), dry=True)
            return
        self._export_wav(tr("Esporta WAV della traccia"), os.path.join(start_dir, safe_name + ".wav"), [track],
                         tr("Traccia '{name}' esportata", name=track.name))

    def _export_wav(self, title: str, default_path: str, tracks, done_msg: str, dry: bool = False):
        """Chiede dove salvare e renderizza in un WAV, in un thread separato,
        le tracce udibili (tracks=None) o solo tracks (asciutte con 'dry')."""
        from core.playback import render_project_mix_to_wav
        path, _ = QFileDialog.getSaveFileName(self, title, default_path,
                                                tr("WAV (*.wav)"), options=file_dialog_options())
        if not path:
            return
        if not path.lower().endswith(".wav"):
            path += ".wav"

        progress_dlg = QProgressDialog(tr("Rendering audio in corso..."), tr("Annulla"), 0, 0, self)
        progress_dlg.setWindowTitle(title)
        progress_dlg.setWindowModality(Qt.WindowModal)
        progress_dlg.setMinimumDuration(0)
        progress_dlg.setAutoClose(False)
        cancelled = {"value": False}
        worker = Worker(render_project_mix_to_wav, self.project, path,
                        stop_check=lambda: cancelled["value"], tracks=tracks, dry=dry, pass_progress=False)
        self._export_wav_worker = worker  # riferimento forte finche' il thread e' attivo

        def handle_ok(_result):
            worker.wait()
            progress_dlg.close()
            self._export_wav_worker = None
            self.statusBar().showMessage(f"{done_msg}: {path}", 6000)

        def handle_error(msg):
            worker.wait()
            progress_dlg.close()
            self._export_wav_worker = None
            if not cancelled["value"]:
                QMessageBox.critical(self, tr("Errore esportazione audio"), msg)

        def handle_cancel():
            cancelled["value"] = True

        worker.finished_ok.connect(handle_ok)
        worker.finished_error.connect(handle_error)
        progress_dlg.canceled.connect(handle_cancel)
        worker.start()

    # ------------------------------------------------------------ strumenti / libreria MIDI / aiuto

    def manage_instruments(self):
        dlg = InstrumentManagerDialog(self)
        dlg.exec()
        # Le definizioni di strumenti personalizzati usati dalle tracce
        # vengono incorporate nel file al momento del salvataggio (vedi
        # _load_and_apply_project): una modifica qui puo' quindi cambiare
        # cio' che verrebbe salvato anche senza toccare le tracce stesse.
        self._mark_dirty()

    def manage_midi_library(self):
        dlg = MidiLibraryDialog(self, project=self.project)
        dlg.exec()
        if dlg.project_changed:
            # rinomina di un file: richiami &Nome aggiornati nel brano
            self._reload_editor_from_track()
            self.arrangement_view.refresh()
            self._mark_dirty()
        self._validate_current()

    def download_nam_profiles(self, ask: bool = True):
        """Scarica i profili NAM consigliati nella cartella profili_nam
        (in sottofondo, con una barra di avanzamento)."""
        from core.nam_profiles import PROFILES, SOURCE_REPO, download_profiles, ensure_nam_dir
        folder = ensure_nam_dir()
        self._download_in_background(
            "_nam_download_worker", download_profiles, folder, len(PROFILES),
            title=tr("Profili NAM consigliati"),
            question=tr("Scarico {0} profili NAM di amplificatori e pedali famosi (circa 3 MB) dalla raccolta della comunita' di Neural Amp Modeler su GitHub ({SOURCE_REPO}, licenza GNU GPL v3)?\n\nCartella: {folder}\n\nI profili gia' presenti non vengono riscaricati.", len(PROFILES), SOURCE_REPO=SOURCE_REPO, folder=folder) if ask else "",
            progress_label=tr("Download dei profili NAM..."),
            hint=tr("\nCartella: {0}\nNel pannello Effetti: + Effetto → Saturazione → Profilo NAM. Agli amplificatori senza cassa aggiungi una cassa (File IR…).", folder))

    def download_cab_irs(self, ask: bool = True):
        """Scarica le casse (risposte all'impulso) per i profili NAM di sola
        testata nella sottocartella casse dei profili NAM."""
        from core.cab_irs import CABINETS, SOURCE_REPO, download_cabinets, ensure_cab_dir
        folder = ensure_cab_dir()
        self._download_in_background(
            "_cab_download_worker", download_cabinets, folder, len(CABINETS),
            title=tr("Casse per gli amplificatori NAM"),
            question=tr("Scarico {0} casse per chitarra (risposte all'impulso, meno di 1 MB) da usare con i profili NAM di sola testata? Sono il pacchetto BestPlugins Mega Pack 2 di David Fau Casquel, licenza GNU GPL v2 o successiva, dal repository di Guitarix su GitHub ({SOURCE_REPO}).\n\nCartella: {folder}\n\nLe casse gia' presenti non vengono riscaricate.", len(CABINETS), SOURCE_REPO=SOURCE_REPO, folder=folder) if ask else "",
            progress_label=tr("Download delle casse..."),
            hint=tr("\nCartella: {0}\nNella card del Profilo NAM (o dell'Amplificatore) scegli Cassa → File IR… e apri una di queste casse. Ogni file prende il nome dell'amplificatore di cui riproduce la cassa.", folder))

    def _download_in_background(self, worker_attr, download, folder, total, title, question,
                                progress_label, hint):
        """Chiede conferma (se question non e' vuota) e scarica in sottofondo
        con download(folder, progress, should_stop), con barra di avanzamento
        e riepilogo finale. worker_attr tiene il riferimento al thread."""
        if question and QMessageBox.question(self, title, question) != QMessageBox.StandardButton.Yes:
            return
        cancelled = {"value": False}
        progress_dlg = QProgressDialog(progress_label, tr("Annulla"), 0, total, self)
        progress_dlg.setWindowModality(Qt.WindowModal)
        progress_dlg.setMinimumDuration(0)
        progress_dlg.canceled.connect(lambda: cancelled.__setitem__("value", True))
        worker = Worker(download, folder, pass_progress=False,
                        progress=lambda i, n, _name: worker.progress.emit(i / n),
                        should_stop=lambda: cancelled["value"])
        worker.progress.connect(lambda frac: progress_dlg.setValue(round(frac * total)))
        setattr(self, worker_attr, worker)      # riferimento forte finche' il thread e' attivo

        def handle_ok(result):
            worker.wait()
            progress_dlg.close()
            setattr(self, worker_attr, None)
            lines = [tr("Scaricati: {0}, gia' presenti: {1}.", len(result['downloaded']), len(result['present']))]
            if result["failed"]:
                lines.append(tr("Non riusciti (controlla la connessione e riprova):"))
                lines += [f"  • {name}: {reason}" for name, reason in result["failed"]]
            lines.append(hint)
            box = QMessageBox.warning if result["failed"] else QMessageBox.information
            box(self, title, "\n".join(lines))

        def handle_error(msg):
            worker.wait()
            progress_dlg.close()
            setattr(self, worker_attr, None)
            QMessageBox.warning(self, title, tr("Download non riuscito: {msg}", msg=msg))

        worker.finished_ok.connect(handle_ok)
        worker.finished_error.connect(handle_error)
        worker.start()

    def show_help(self):
        dlg = HelpDialog(self)
        dlg.exec()

    def show_about(self):
        dlg = AboutDialog(self)
        dlg.exec()

    def freeze_chords(self):
        """Converte ('congela') ogni accordo astratto della traccia corrente
        nel blocco esplicito di note concrete generato dal motore di voicing."""
        if not self.current_track_name:
            return
        track = self.project.get_track(self.current_track_name)
        if self._reject_audio_track(track, tr("il congelamento degli accordi")):
            return
        instrument = track.instrument
        changed = False

        def freeze(tok):
            nonlocal changed
            tok, value = split_note_value(tok)
            m = RE_CHORD.match(tok)
            if not m:
                return tok + value
            mult, letter, accidental, suffix, voicing, bass, octv, _modifier = m.groups()
            symbol = letter + accidental + suffix
            try:
                chord = parse_chord_symbol(symbol)
            except ValueError:
                return tok + value
            octave = int(octv) if octv else instrument.default_octave
            notes = voice_chord(chord, octave, instrument, voicing_override=voicing)
            if bass:
                notes = apply_bass_note(notes, bass, octave)
            note_tokens = [midi_to_token(n) for n in notes]
            changed = True
            return ("" if not mult else mult) + "[" + " ".join(note_tokens) + "]" + value

        # Solo i token cambiano: a capo e commenti restano dove sono.
        new_text = rewrite_tokens(track.text, lambda tok: map_nested_tokens(tok, freeze))
        if changed:
            track.text = new_text
            self.editor.blockSignals(True)
            self.editor.setPlainText(track.text)
            self.editor.blockSignals(False)
            self._mark_dirty()

    def rewrite_relative(self):
        """Riscrive la traccia corrente con le ottave relative (rel:) e la
        tonalita' del brano (key=), senza cambiare le note."""
        if not self.current_track_name:
            return
        track = self.project.get_track(self.current_track_name)
        if self._reject_audio_track(track, tr("la riscrittura delle altezze")):
            return
        ok, _message = validate_track_text(track.text, self.project.patterns,
                                           default_octave=track.instrument.default_octave)
        if not ok:
            QMessageBox.warning(self, tr("Altezze relative"),
                                tr("Correggi prima gli errori della traccia: la riscrittura deve sapere "
                                   "quali note ci sono."))
            return
        key = (self.project.key or "").strip() or None
        if key:
            try:
                key_signature_alters(key)
            except NotationError:
                key = None
        new_text = relative_text(track.text, track.instrument.default_octave, key)
        if new_text != track.text:
            track.text = new_text
            self.editor.blockSignals(True)
            self.editor.setPlainText(track.text)
            self.editor.blockSignals(False)
            self._mark_dirty()
            self._validate_current()

    def analyze_key_action(self):
        """Analizza le note di tutte le tracce non percussive del progetto e
        stima la tonalita' con l'algoritmo di Krumhansl-Schmuckler (vedi
        core.key_detect), impostandola nel campo Tonalita' della toolbar
        (che a sua volta aggiorna project.key tramite _on_key_changed, come
        se l'utente l'avesse digitata a mano - sovrascrive silenziosamente
        un eventuale valore gia' impostato)."""
        detected = detect_key(self.project)
        if detected is None:
            QMessageBox.information(
                self, tr("Nessuna nota da analizzare"),
                tr("Non ci sono note intonate nelle tracce del progetto (percussioni escluse): "
                "impossibile stimare una tonalita'.")
            )
            return
        self.key_combo.setCurrentText(detected)
        self.statusBar().showMessage(tr("Tonalità rilevata dall'analisi delle tracce: {detected}", detected=detected), 6000)

    # ------------------------------------------------------------ pattern

    def manage_patterns(self):
        dlg = PatternEditorDialog(self.project, self)
        dlg.exec()
        # Puo' aver aperto al suo interno "Importa audio", che puo' aver
        # cambiato Tempo/Metrica del progetto (stesso oggetto condiviso).
        self._sync_tempo_metrica_fields()
        # Una rinomina riscrive i richiami %Nome nei testi delle tracce.
        self._reload_editor_from_track()
        self.arrangement_view.refresh()
        self._validate_current()
        # self.project.patterns e' sempre lo stesso dict condiviso col
        # dialogo: non c'e' un modo semplice per sapere se e' stato
        # effettivamente modificato, quindi si segna dirty per sicurezza.
        self._mark_dirty()

    # ------------------------------------------------------------ riorganizzazione con pattern

    def extract_patterns_action(self):
        if not self.project.tracks:
            QMessageBox.information(self, tr("Nessuna traccia"), tr("Il progetto non ha tracce da riorganizzare."))
            return
        from core.reorganize import extract_patterns_for_project

        reply = QMessageBox.question(
            self, tr("Estrai pattern dalle tracce"),
            tr("Verranno cercati blocchi di note/eventi ripetuti in ciascuna traccia e "
            "convertiti automaticamente in pattern riutilizzabili (%Nome).\n\n"
            "Il contenuto musicale non cambia: e' solo una riscrittura piu' compatta.\n\n"
            "Procedere?")
        )
        if reply != QMessageBox.Yes:
            return

        def on_finished(summary):
            if not summary:
                QMessageBox.information(self, tr("Nessuna ripetizione trovata"),
                                         tr("Non sono stati trovati blocchi ripetuti abbastanza lunghi da convenire "
                                         "come pattern in nessuna traccia."))
                return
            lines = []
            total_patterns = 0
            for track_name, patterns in summary.items():
                names = ", ".join(f"%{n}" for n in patterns)
                lines.append(f"• {track_name}: {names}")
                total_patterns += len(patterns)
            QMessageBox.information(
                self, tr("Pattern estratti"),
                tr("Creati {total_patterns} nuovi pattern in {0} traccia/e:\n\n", len(summary), total_patterns=total_patterns) + "\n".join(lines)
            )
            self._finish_reorganize_ui(tr("Estratti {total_patterns} pattern.", total_patterns=total_patterns))

        self._run_reorganize(extract_patterns_for_project, on_finished,
                              tr("Estrazione pattern in corso..."))

    def expand_patterns_action(self):
        if not self.project.tracks:
            QMessageBox.information(self, tr("Nessuna traccia"), tr("Il progetto non ha tracce da riorganizzare."))
            return
        if not self.project.patterns and not any(
            "%" in t.text or "&" in t.text for t in self.project.tracks
        ):
            QMessageBox.information(self, tr("Niente da espandere"),
                                     tr("Nessuna traccia usa pattern (%) o riferimenti MIDI (&) al momento."))
            return
        from core.reorganize import expand_patterns_for_project

        reply = QMessageBox.question(
            self, tr("Espandi pattern nelle tracce"),
            tr("Ogni riferimento %pattern e &midi verra' sostituito con i token letterali "
            "corrispondenti, rendendo le tracce autosufficienti. I pattern non piu' "
            "utilizzati verranno rimossi dal progetto.\n\n"
            "Il contenuto musicale non cambia.\n\n"
            "Procedere?")
        )
        if reply != QMessageBox.Yes:
            return

        def on_finished(summary):
            if not summary:
                QMessageBox.information(self, tr("Niente da espandere"),
                                         tr("Nessuna traccia conteneva riferimenti da espandere."))
                return
            lines = [tr("• {name}: {before} → {after} token", name=name, before=before, after=after) for name, (before, after) in summary.items()]
            QMessageBox.information(
                self, tr("Pattern espansi"),
                tr("Espanse {0} traccia/e (pattern ora inutilizzati rimossi dal progetto):\n\n", len(summary))
                + "\n".join(lines)
            )
            self._finish_reorganize_ui(tr("Espanse {0} tracce.", len(summary)))

        self._run_reorganize(expand_patterns_for_project, on_finished,
                              tr("Espansione pattern in corso..."))

    def _finish_reorganize_ui(self, status_msg):
        """Aggiorna mixer e traccia selezionata dopo una riorganizzazione
        (estrazione/espansione pattern) completata, e mostra il messaggio
        riassuntivo in barra di stato."""
        self._mark_dirty()
        self.refresh_mixer()
        if self.current_track_name:
            self.select_track(self.current_track_name)
        self.statusBar().showMessage(status_msg, 5000)

    def _run_reorganize(self, func, on_finished, title):
        """Esegue una funzione di riorganizzazione (core.reorganize) in un
        thread separato, mostrando una QProgressDialog con percentuale reale
        alimentata dal progress_callback della funzione core."""
        progress_dlg = QProgressDialog(title, tr("Annulla"), 0, 100, self)
        progress_dlg.setWindowTitle(tr("Riorganizzazione in corso"))
        progress_dlg.setWindowModality(Qt.WindowModal)
        progress_dlg.setMinimumDuration(0)
        progress_dlg.setAutoClose(False)
        progress_dlg.setValue(0)

        worker = Worker(func, self.project)
        self._reorganize_worker = worker  # mantiene un riferimento forte finche' il thread e' attivo

        def handle_progress(frac):
            progress_dlg.setValue(min(100, int(frac * 100)))

        def handle_ok(result):
            worker.wait()
            progress_dlg.close()
            on_finished(result)
            self._reorganize_worker = None

        def handle_error(msg):
            worker.wait()
            progress_dlg.close()
            QMessageBox.critical(self, tr("Errore durante la riorganizzazione"), msg)
            self._reorganize_worker = None

        worker.progress.connect(handle_progress)
        worker.finished_ok.connect(handle_ok)
        worker.finished_error.connect(handle_error)
        progress_dlg.canceled.connect(worker.terminate)

        worker.start()

    # ------------------------------------------------------------ salvataggio automatico

    def _init_autosave(self):
        """Mentre ci sono modifiche non salvate, ogni AUTOSAVE_INTERVAL_S
        secondi ne scrive una copia di recupero (core.autosave), che al
        prossimo avvio si puo' recuperare se SoundText non si e' chiuso
        normalmente (vedi offer_recovery). Il file del progetto non viene
        toccato. _autosave_generation conta le modifiche (vedi _mark_dirty):
        la copia si riscrive solo se ce ne sono di nuove."""
        self._recovery = RecoverySession()
        self._autosave_generation = 0
        self._autosaved_generation = 0
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(AUTOSAVE_INTERVAL_S * 1000)
        self._autosave_timer.timeout.connect(self.autosave_now)
        self._autosave_timer.start()

    def autosave_now(self) -> bool:
        """Scrive la copia di recupero se ci sono modifiche non salvate nuove
        rispetto all'ultima copia; True se l'ha scritta."""
        if not self._dirty or self._autosave_generation == self._autosaved_generation:
            return False
        if not self._recovery.save(self.project, self.current_path):
            return False
        self._autosaved_generation = self._autosave_generation
        return True

    def _clear_recovery_copy(self):
        """Progetto salvato o sostituito: la copia di recupero non serve piu'."""
        self._recovery.clear()
        self._autosaved_generation = self._autosave_generation

    def offer_recovery(self):
        """All'avvio: se una sessione precedente si e' chiusa male lasciando
        modifiche non salvate, propone di recuperarle (la piu' recente; le
        altre al prossimo avvio). Chiamata da main.py dopo aver mostrato la
        finestra."""
        candidates = find_recoverable()
        if not candidates:
            return
        cand = candidates[0]
        when = time.strftime("%d/%m/%Y %H:%M", time.localtime(cand.saved_at))
        name = cand.project_name or tr("Nuovo progetto")
        if cand.original_path:
            where = tr("File del progetto: {path}", path=cand.original_path)
        else:
            where = tr("Il progetto non era mai stato salvato.")
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle(tr("Recupero del progetto"))
        box.setText(tr("L'ultima volta SoundText non si è chiuso normalmente."))
        box.setInformativeText(
            tr("C'è una copia di recupero del progetto «{name}» con le modifiche non salvate "
               "(salvata automaticamente il {when}).\n{where}\n\nVuoi recuperarla?",
               name=name, when=when, where=where))
        recover_btn = box.addButton(tr("Recupera"), QMessageBox.AcceptRole)
        discard_btn = box.addButton(tr("Elimina la copia"), QMessageBox.DestructiveRole)
        box.addButton(tr("Decidi dopo"), QMessageBox.RejectRole)
        box.setDefaultButton(recover_btn)
        box.exec()
        clicked = box.clickedButton()
        if clicked is discard_btn:
            cand.discard()
        elif clicked is recover_btn:
            self.recover_project(cand)

    def recover_project(self, cand) -> bool:
        """Apre la copia di recupero cand al posto del progetto corrente,
        come progetto con modifiche non salvate (Salva scrive sul file
        originale, se c'era)."""
        if not self._confirm_discard_unsaved():
            return False
        try:
            project = cand.load()
        except Exception as e:
            QMessageBox.critical(self, tr("Recupero del progetto"),
                                 tr("La copia di recupero non si può aprire:\n{e}", e=e))
            return False
        original = cand.original_path if cand.original_path and os.path.isdir(
            os.path.dirname(cand.original_path)) else None
        title = os.path.basename(original) if original else (project.name or tr("Nuovo progetto"))
        self._replace_project(project, path=original, title=tr("{title} (recuperato)", title=title),
                              status_msg=tr("Progetto recuperato: salvalo per conservare le modifiche."),
                              status_timeout=10000)
        cand.discard()
        # Recuperato ma non ancora salvato: resta "modificato", e la copia
        # passa subito a questa sessione (se si chiudesse male di nuovo).
        self._dirty = True
        self._autosave_generation += 1
        self.autosave_now()
        return True

    # ------------------------------------------------------------ chiusura finestra

    def closeEvent(self, event):
        """Se il progetto ha modifiche non salvate (vedi _mark_dirty), chiede
        se salvarle prima di uscire (Salva/Scarta/Annulla) - scegliendo
        Salva si passa da save_project(), che apre da solo 'Salva con nome'
        se il progetto non ha ancora un percorso; se quel dialogo viene
        annullato self._dirty resta True e la chiusura si annulla a sua
        volta, invece di uscire silenziosamente senza aver salvato nulla.

        ProjectMixin precede PlaybackMixin nell'MRO di MainWindow (vedi
        gui.main_window): questo override e super().closeEvent(event) fanno
        proseguire la catena fino a PlaybackMixin.closeEvent (ferma
        playback/metronomo) e infine QMainWindow.closeEvent."""
        if self._dirty:
            reply = QMessageBox.question(
                self, tr("Modifiche non salvate"),
                tr("Il progetto contiene modifiche non salvate. Vuoi salvarle prima di uscire?"),
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save,
            )
            if reply == QMessageBox.Cancel:
                event.ignore()
                return
            if reply == QMessageBox.Save:
                self.save_project()
                if self._dirty:
                    # 'Salva con nome' e' stato a sua volta annullato (nessun
                    # percorso scelto): non si puo' considerare salvato, si
                    # annulla anche la chiusura invece di uscire comunque.
                    event.ignore()
                    return

        # Chiusura normale: la copia di recupero non serve piu' (sia che le
        # modifiche siano state salvate sia che si sia scelto di scartarle).
        self._autosave_timer.stop()
        self._recovery.close()
        super().closeEvent(event)
