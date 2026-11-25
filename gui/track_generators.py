"""
I generatori della finestra principale: batteria, basso, giro armonico,
accompagnamento o riff scritti nella traccia selezionata oppure in una
traccia nuova (menu "+ Aggiungi traccia"), "Suona con la tastiera" e gli
stili personali del generatore.

La finestra possiede un TrackGenerators (MainWindow.generators). Quello che
un generatore produce si aggiunge con add_text: accodato al testo della
traccia, o in un box nuovo nella vista Struttura brano.
"""

import math

from PySide6.QtWidgets import QDialog, QInputDialog, QMessageBox

from core.accidental_style import styled
from core.i18n import tr
from core.rhythm_generate import project_has_chords, tracks_duration_beats
from .keyboard_play_dialog import KeyboardPlayDialog
from .rhythm_generate_dialog import (
    DrumGenerateDialog, BassGenerateDialog, MelodyGenerateDialog, ChordProgressionDialog, chord_source_tracks,
    last_box_key,
)


class TrackGenerators:
    def __init__(self, window):
        self.window = window

    def play_keyboard(self):
        window = self.window
        track, clip = window._resolve_edit_target()
        if track is None:
            QMessageBox.information(window, tr("Nessuna traccia"), tr("Seleziona prima una traccia (o un box) in cui suonare."))
            return
        if window._reject_audio_track(track, tr("suonare con la tastiera")):
            return
        label = tr("box '{name}' (traccia '{0}')", track.name, name=clip.name) if clip is not None else tr("traccia '{name}'", name=track.name)
        dlg = KeyboardPlayDialog(window, project=window.project, instrument_name=track.instrument_name,
                                  context_label=label, current_track_name=track.name)
        accepted = dlg.exec() == QDialog.Accepted
        # Il dialogo puo' aver cambiato Tempo/Metrica del progetto (stesso
        # oggetto condiviso) anche se poi annullato: i campi in toolbar
        # vanno comunque riallineati.
        window._sync_tempo_metrica_fields()
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
            window.arrangement_view.on_clip_changed(track.name)
            window.statusBar().showMessage(tr("Performance registrata e aggiunta al box '{name}' (traccia '{0}').", track.name, name=clip.name), 4000)
        else:
            track.text = f"{track.text.rstrip()} {new_text}" if track.text.strip() else new_text
            window._mark_dirty()
            window.refresh_mixer()
            window.select_track(track.name)
            window.statusBar().showMessage(tr("Performance registrata e aggiunta alla traccia '{name}'.", name=track.name), 4000)

    def add_text(self, track, new_text, box_name: str = "Box"):
        """Accoda 'new_text' al contenuto gia' presente nella traccia (o lo
        sostituisce se la traccia era vuota) - stessa convenzione di
        play_keyboard, per non perdere musica scritta a
        mano o importata in precedenza. Nella vista Struttura brano, o se la
        traccia e' gia' divisa in box, il testo diventa un box nuovo
        ('box_name') dopo l'ultimo: il testo di una traccia con box viene
        dai box, e accodato li' non si vedrebbe nella Struttura."""
        window = self.window
        new_text = styled(new_text)
        if track.clips or window.arrangement_action.isChecked():
            from core.model import Clip
            view = window.arrangement_view
            view._wrap_free_text_in_box(track)
            beat = view.end_of_track_beat(track.name)
            clip = Clip(name=box_name, text=new_text, start_beat=beat)
            clip.start_beat = view.resolve_free_slot(track.name, clip, beat)
            track.clips.append(clip)
            view.on_clip_changed(track.name)          # ricalcola il testo dai box e segna la modifica
            view.select_box(track.name, clip)
            return
        if track.text.strip():
            track.text = f"{track.text.rstrip()} {new_text}"
        else:
            track.text = new_text
        window._mark_dirty()

    def drums(self):
        window = self.window
        if not window.current_track_name:
            QMessageBox.information(window, tr("Nessuna traccia"), tr("Seleziona prima una traccia in cui generare la batteria."))
            return
        track = window.project.get_track(window.current_track_name)
        if window._reject_audio_track(track, tr("la generazione della batteria")):
            return
        if not track.instrument.is_percussion:
            QMessageBox.information(
                window, tr("Traccia non percussiva"),
                tr("La traccia '{name}' usa lo strumento '{instrument_name}', non percussivo.\nSeleziona (o crea) una traccia con uno strumento a percussione (es. Drums).", name=track.name, instrument_name=track.instrument_name)
            )
            return
        # Preimposta le battute su quelle necessarie a coprire l'estensione
        # delle altre tracce gia' scritte (vedi core.rhythm_generate.
        # tracks_duration_beats), cosi' la batteria generata copre di default
        # l'intero brano invece di fermarsi a meta' - 8 se non c'e' ancora
        # nient'altro da coprire (comportamento originale).
        other_beats = tracks_duration_beats(window.project, exclude_track_name=track.name)
        from .rhythm_generate_dialog import project_bar_beats
        default_bars = math.ceil(other_beats / project_bar_beats(window.project)) if other_beats > 0 else 8
        dlg = DrumGenerateDialog(window, project=window.project, instrument_name=track.instrument_name,
                                  context_label=tr("traccia '{name}'", name=track.name), default_bars=default_bars,
                                  track_name=track.name)
        if dlg.exec() != QDialog.Accepted:
            return
        self.add_text(track, dlg.result_text(), tr("Groove"))
        window.refresh_mixer()
        window.select_track(track.name)
        window.statusBar().showMessage(tr("Batteria generata e aggiunta alla traccia '{name}'.", name=track.name), 4000)

    def bass(self):
        window = self.window
        if not window.current_track_name:
            QMessageBox.information(window, tr("Nessuna traccia"), tr("Seleziona prima una traccia in cui generare il basso."))
            return
        track = window.project.get_track(window.current_track_name)
        if window._reject_audio_track(track, tr("la generazione del basso")):
            return
        other_tracks = chord_source_tracks(window.project, exclude_track_name=track.name)
        if not other_tracks:
            QMessageBox.information(
                window, tr("Nessuna traccia sorgente"),
                tr("Serve un'altra traccia con degli accordi scritti da cui far derivare il basso.")
            )
            return
        # Fa ripetere ciclicamente la progressione di accordi (vedi
        # core.rhythm_generate.generate_bass_from_chords) finche' non copre
        # l'estensione delle altre tracce gia' scritte, invece di fermarsi
        # alla fine della sola traccia di accordi sorgente scelta.
        other_beats = tracks_duration_beats(window.project, exclude_track_name=track.name)
        dlg = BassGenerateDialog(window, project=window.project, instrument_name=track.instrument_name,
                                  context_label=tr("traccia '{name}'", name=track.name), other_tracks=other_tracks,
                                  min_total_beats=other_beats, track_name=track.name)
        if dlg.exec() != QDialog.Accepted:
            return
        self.add_text(track, dlg.result_text(), tr("Basso"))
        window.refresh_mixer()
        window.select_track(track.name)
        window.statusBar().showMessage(tr("Basso generato e aggiunto alla traccia '{name}'.", name=track.name), 4000)

    def save_as_style(self):
        """Traccia → Salva come stile del generatore: tutta la traccia selezionata."""
        window = self.window
        from .save_style_dialog import SaveStyleDialog, chord_sources_of, source_for_part
        if not window.current_track_name:
            QMessageBox.information(window, tr("Nessuna traccia"), tr("Seleziona prima la traccia da cui ricavare lo stile."))
            return
        track = window.project.get_track(window.current_track_name)
        if window._reject_audio_track(track, tr("il salvataggio come stile")):
            return
        if not track.text.strip():
            QMessageBox.information(window, tr("Traccia vuota"), tr("La traccia non contiene note da cui ricavare uno stile."))
            return
        dlg = SaveStyleDialog(window, [source_for_part(tr("traccia '{name}'", name=track.name), track.text, track.instrument)],
                              chord_sources_of(window.project, track.name), window.project.patterns,
                              meter=window.project.time_sig)
        if dlg.exec() == QDialog.Accepted and dlg.saved_style():
            window.statusBar().showMessage(tr("Stile «{0}» salvato fra gli stili personali.", dlg.saved_style()[1]), 4000)

    def manage_styles(self):
        window = self.window
        from .save_style_dialog import UserStylesDialog
        UserStylesDialog(window).exec()

    def melody(self):
        window = self.window
        if not window.current_track_name:
            QMessageBox.information(
                window, tr("Nessuna traccia"),
                tr("Seleziona prima una traccia in cui generare l'accompagnamento o il riff.")
            )
            return
        track = window.project.get_track(window.current_track_name)
        if window._reject_audio_track(track, tr("la generazione di accompagnamento e riff")):
            return
        instrument = track.instrument
        if instrument.is_percussion:
            QMessageBox.information(
                window, tr("Traccia percussiva"),
                tr("La traccia '{name}' usa lo strumento '{instrument_name}', percussivo.\nUsa 'Genera batteria...' invece: qui le note sono altezze, non hanno senso su una traccia percussiva.", name=track.name, instrument_name=track.instrument_name)
            )
            return
        if not project_has_chords(window.project, exclude_track_name=track.name, audio=True):
            QMessageBox.information(
                window, tr("Nessun giro di accordi"),
                tr("L'accompagnamento e il riff seguono gli accordi di un'altra traccia, ma nel brano "
                "non ce ne sono ancora.\nCrea prima un giro armonico in una traccia polifonica "
                "(Traccia → Genera giro armonico in questa traccia...).")
            )
            return
        other_tracks = chord_source_tracks(window.project, exclude_track_name=track.name)
        other_beats = tracks_duration_beats(window.project, exclude_track_name=track.name)
        dlg = MelodyGenerateDialog(
            window, project=window.project, instrument_name=track.instrument_name,
            context_label=tr("traccia '{name}'", name=track.name), other_tracks=other_tracks,
            polyphonic=instrument.polyphonic, default_octave=instrument.default_octave,
            range_low=instrument.range_low, range_high=instrument.range_high,
            min_total_beats=other_beats, track_name=track.name,
        )
        if dlg.exec() != QDialog.Accepted:
            return
        self.add_text(track, dlg.result_text(),
                                           tr("Accompagnamento") if instrument.polyphonic else tr("Riff"))
        window.refresh_mixer()
        window.select_track(track.name)
        kind = tr("Accompagnamento") if instrument.polyphonic else tr("Riff/melodia")
        window.statusBar().showMessage(tr("{kind} generato e aggiunto alla traccia '{name}'.", kind=kind, name=track.name), 4000)

    def progression(self):
        window = self.window
        if not window.current_track_name:
            QMessageBox.information(window, tr("Nessuna traccia"),
                                    tr("Seleziona prima una traccia in cui generare il giro armonico."))
            return
        track = window.project.get_track(window.current_track_name)
        if window._reject_audio_track(track, tr("la generazione del giro armonico")):
            return
        instrument = track.instrument
        if instrument.is_percussion or not instrument.polyphonic:
            QMessageBox.information(
                window, tr("Strumento non adatto"),
                tr("La traccia '{name}' usa lo strumento '{instrument_name}', che non suona accordi.\nScegli una traccia con uno strumento polifonico (pianoforte, chitarra, organo, pad...).", name=track.name, instrument_name=track.instrument_name)
            )
            return
        from .rhythm_generate_dialog import project_bar_beats
        other_beats = tracks_duration_beats(window.project, exclude_track_name=track.name)
        default_bars = round(other_beats / project_bar_beats(window.project)) if other_beats > 0 else 0
        dlg = ChordProgressionDialog(window, project=window.project, instrument_name=track.instrument_name,
                                     context_label=tr("traccia '{name}'", name=track.name), default_bars=default_bars,
                                     track_name=track.name, default_key=last_box_key(window.project, track))
        if dlg.exec() != QDialog.Accepted:
            return
        self.add_text(track, dlg.result_text(), tr("Giro"))
        window.refresh_mixer()
        window.select_track(track.name)
        window.statusBar().showMessage(tr("Giro armonico generato e aggiunto alla traccia '{name}'.", name=track.name), 4000)

    def new_track(self, kind: str):
        """Crea una traccia gia' generata (batteria, giro armonico, basso,
        accompagnamento/riff): prima il dialogo del generatore, la traccia
        solo se lo si conferma."""
        window = self.window
        from core.instruments import get_instrument, list_instrument_names
        from .rhythm_generate_dialog import project_bar_beats
        other_beats = tracks_duration_beats(window.project)
        bar_beats = project_bar_beats(window.project)
        other_tracks = chord_source_tracks(window.project)
        if kind == "drums":
            instrument, base, box = "Drums", tr("Batteria"), tr("Groove")
        elif kind == "progression":
            instrument, base, box = "Piano", tr("Accordi"), tr("Giro")
        elif kind == "bass":
            instrument, base, box = "Bass", tr("Basso"), tr("Basso")
        else:
            names = [n for n in list_instrument_names() if not get_instrument(n).is_percussion]
            instrument, ok = QInputDialog.getItem(
                window, tr("Accompagnamento o riff"), tr("Strumento della nuova traccia (polifonico = "
                "accompagnamento, monofonico = riff/melodia):"), names,
                names.index("Guitar") if "Guitar" in names else 0, False)
            if not ok:
                return
            base = instrument
            box = tr("Accompagnamento") if get_instrument(instrument).polyphonic else tr("Riff")
        name = window._unique_track_name(base)
        context = tr("nuova traccia '{name}'", name=name)
        if kind == "drums":
            dlg = DrumGenerateDialog(window, project=window.project, instrument_name=instrument, context_label=context,
                                     default_bars=math.ceil(other_beats / bar_beats) if other_beats > 0 else 8,
                                     track_name=name, start_beat=0.0)
        elif kind == "progression":
            dlg = ChordProgressionDialog(window, project=window.project, instrument_name=instrument,
                                         context_label=context,
                                         default_bars=round(other_beats / bar_beats) if other_beats > 0 else 0,
                                         track_name=name)
        elif kind == "bass":
            dlg = BassGenerateDialog(window, project=window.project, instrument_name=instrument, context_label=context,
                                     other_tracks=other_tracks, min_total_beats=other_beats, track_name=name,
                                     start_beat=0.0)
        else:
            instr = get_instrument(instrument)
            dlg = MelodyGenerateDialog(
                window, project=window.project, instrument_name=instrument, context_label=context,
                other_tracks=other_tracks, polyphonic=instr.polyphonic, default_octave=instr.default_octave,
                range_low=instr.range_low, range_high=instr.range_high, min_total_beats=other_beats,
                track_name=name)
        if dlg.exec() != QDialog.Accepted:
            return
        window._add_filled_track(name, instrument, dlg.result_text(), box)
        window.statusBar().showMessage(tr("Traccia '{name}' creata e generata.", name=name), 4000)
