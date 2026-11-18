"""
L'audio che esce dalla finestra principale: il mix (WAV, MP3, FLAC o OGG,
vedi core.audio_encode), una traccia sola
(anche asciutta, per il re-amping), tutte le tracce una per file (stem), un
box della vista Struttura, e il congelamento di una traccia in audio.

La finestra possiede un WavExport (MainWindow.wav_export): i menu chiamano
mix, stems, track e add_freeze_action; la vista Struttura usa anche render
per i box. Il rendering gira in un thread (gui.worker.Worker) con una
finestra di avanzamento annullabile; worker e freeze_worker restano
impostati finche' il thread lavora.
"""

import os
import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QProgressDialog, QWidget

from core.i18n import tr
from core.notation import validate_track_text
from .file_dialogs import file_dialog_options
from .worker import Worker


def _ask_audio_path(parent, title: str, default_path: str, wav_only: bool = False):
    """Il dialogo "Salva" con i formati audio (WAV, MP3, FLAC, OGG): propone
    l'ultimo usato e ricorda quello scelto. Ritorna il percorso con
    l'estensione giusta, o '' se si annulla. Un'estensione scritta a mano
    vince sul filtro scelto; con 'wav_only' si salva solo in WAV."""
    from core import audio_encode
    from core.settings import get_audio_export_format, set_audio_export_format
    ext = ".wav" if wav_only else get_audio_export_format()
    filters = [audio_encode.file_filter(".wav")] if wav_only else audio_encode.all_filters()
    path, chosen = QFileDialog.getSaveFileName(parent, title, audio_encode.with_extension(default_path, ext),
                                               ";;".join(filters), audio_encode.file_filter(ext),
                                               options=file_dialog_options())
    if not path:
        return ""
    typed = audio_encode.format_of(path)
    if wav_only:
        ext = ".wav"
    elif typed:
        ext = typed
    elif chosen:
        ext = audio_encode.ext_from_filter(chosen)
    path = audio_encode.with_extension(path, ext)
    if not wav_only:
        set_audio_export_format(ext)
    return path


def _safe_file_name(name: str, fallback: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", name).strip() or fallback


class WavExport:
    def __init__(self, window):
        self.window = window
        self.worker = None          # esportazione in corso (mix, traccia, stem, box)
        self.freeze_worker = None   # congelamento in corso

    def _export_dir(self) -> str:
        return os.path.dirname(self.window._default_export_path(".wav"))

    def _syntax_error(self, track):
        """Il messaggio dell'errore di sintassi della traccia, o None."""
        if track.is_audio:
            return None
        ok, msg = validate_track_text(track.text, self.window.project.patterns)
        return None if ok else msg

    def _start(self, attr: str, title: str, label: str, maximum: int, error_title: str, on_ok,
               func, *args, step_progress: bool = False, **kwargs):
        """Lancia func in un Worker con una finestra di avanzamento
        annullabile (stop_check), tenendolo in self.<attr> finche' lavora;
        on_ok(risultato) alla fine. Con step_progress func riceve
        progress(fatti, totale) e la barra va da 0 a maximum."""
        window = self.window
        dialog = QProgressDialog(label, tr("Annulla"), 0, maximum, window)
        dialog.setWindowTitle(title)
        dialog.setWindowModality(Qt.WindowModal)
        dialog.setMinimumDuration(0)
        dialog.setAutoClose(False)
        cancelled = {"value": False}
        worker = Worker(func, *args, stop_check=lambda: cancelled["value"], pass_progress=False, **kwargs)
        if step_progress:
            worker.kwargs["progress"] = lambda done, _total: worker.progress.emit(done)
            worker.progress.connect(lambda done: dialog.setValue(int(done)))
        setattr(self, attr, worker)   # riferimento forte finche' il thread e' attivo

        def finish():
            worker.wait()
            dialog.close()
            setattr(self, attr, None)

        def handle_ok(result):
            finish()
            on_ok(result)

        def handle_error(msg):
            finish()
            if not cancelled["value"]:
                QMessageBox.critical(window, error_title, msg)

        worker.finished_ok.connect(handle_ok)
        worker.finished_error.connect(handle_error)
        dialog.canceled.connect(lambda: cancelled.__setitem__("value", True))
        worker.start()

    # ------------------------------------------------------------ esportazioni

    def mix(self):
        """Esporta il brano come si sente (tracce udibili, audio compreso)
        in un file audio (WAV, MP3, FLAC o OGG)."""
        if not self.window._check_tracks_syntax():
            return
        self.render(tr("Esporta mix audio"), self.window._default_export_path(".wav"), None,
                    tr("Mix audio esportato"))

    def track(self, track_name: str, dry: bool = False):
        """Esporta in un WAV una sola traccia (con notazione o audio), come
        si sente in Solo: ignora Solo/Mute delle altre. Con 'dry' la traccia
        esce asciutta (senza effetti, riverbero/chorus e pan), per farla
        passare in un simulatore di amplificatore esterno (re-amping)."""
        track = self.window.project.get_track(track_name)
        msg = self._syntax_error(track)
        if msg is not None:
            QMessageBox.critical(self.window, tr("Errore di sintassi"), tr("Impossibile esportare:\n{msg}", msg=msg))
            return
        safe_name = _safe_file_name(track.name, "traccia")
        if dry:
            self.render(tr("Esporta WAV asciutto della traccia"),
                        os.path.join(self._export_dir(), safe_name + "_asciutto.wav"), [track],
                        tr("Traccia '{name}' esportata asciutta (senza effetti)", name=track.name), dry=True)
            return
        self.render(tr("Esporta l'audio della traccia"), os.path.join(self._export_dir(), safe_name + ".wav"), [track],
                    tr("Traccia '{name}' esportata", name=track.name))

    def stems(self):
        """Tutte le tracce, un WAV per traccia (core.playback.render_stems_to_dir),
        in una cartella scelta; con o senza effetti."""
        from core.playback import render_stems_to_dir, stem_tracks
        window = self.window
        if not window._check_tracks_syntax():
            return
        tracks = stem_tracks(window.project)
        if not tracks:
            QMessageBox.information(window, tr("Esporta le tracce"),
                                    tr("Niente da esportare: nessuna traccia udibile con note o clip audio."))
            return
        from core import audio_encode
        from core.settings import get_audio_export_format, set_audio_export_format
        box = QMessageBox(QMessageBox.Question, tr("Esporta le tracce"), tr(
            "{n} tracce, un file audio ciascuna. Con gli effetti (come si sentono) o asciutte "
            "(senza effetti, riverbero e pan, per mixarle altrove)?", n=len(tracks)), parent=window)
        format_row = QWidget(box)
        row_layout = QHBoxLayout(format_row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(QLabel(tr("Formato:"), format_row))
        format_combo = QComboBox(format_row)
        for ext, name in audio_encode.FORMATS.items():
            format_combo.addItem(name, ext)
        format_combo.setCurrentIndex(max(0, format_combo.findData(get_audio_export_format())))
        row_layout.addWidget(format_combo)
        row_layout.addStretch(1)
        grid = box.layout()
        grid.addWidget(format_row, grid.rowCount(), 0, 1, grid.columnCount())
        wet = box.addButton(tr("Con gli effetti"), QMessageBox.AcceptRole)
        dry = box.addButton(tr("Asciutte"), QMessageBox.AcceptRole)
        box.addButton(QMessageBox.Cancel)
        box.setDefaultButton(wet)
        box.exec()
        if box.clickedButton() not in (wet, dry):
            return
        dry_choice = box.clickedButton() is dry
        fmt = format_combo.currentData() or ".wav"
        set_audio_export_format(fmt)
        base = QFileDialog.getExistingDirectory(window, tr("Cartella in cui salvare le tracce"), self._export_dir(),
                                                options=file_dialog_options())
        if not base:
            return
        name = _safe_file_name(os.path.splitext(os.path.basename(window.current_path or ""))[0]
                               or window.project.name, "brano")
        out_dir = os.path.join(base, tr("{name} - tracce", name=name))

        def done(paths):
            window.statusBar().showMessage(tr("{n} tracce esportate in {folder}", n=len(paths), folder=out_dir), 8000)

        self._start("worker", tr("Esporta le tracce"), tr("Rendering delle tracce..."), len(tracks),
                    tr("Errore esportazione audio"), done,
                    render_stems_to_dir, window.project, out_dir, dry=dry_choice, fmt=fmt, step_progress=True)

    def render(self, title: str, default_path: str, tracks, done_msg: str, dry: bool = False,
               project=None, skip_seconds: float = 0.0, length_seconds=None):
        """Chiede dove salvare (WAV, MP3, FLAC o OGG; solo WAV se 'dry', che
        serve al re-amping) e renderizza le tracce udibili
        (tracks=None) o solo tracks (asciutte con 'dry') del brano, o di
        'project' (es. un solo box); 'skip_seconds' si tolgono dall'inizio, e
        con 'length_seconds' il WAV dura tanto. Se il tempo non cambia, il
        WAV lo porta con se' (core.playback.constant_tempo): importato in un
        altro brano ne segue il tempo."""
        from core.playback import constant_tempo, render_project_mix_to_wav
        window = self.window
        path = _ask_audio_path(window, title, default_path, wav_only=dry)
        if not path:
            return
        project = project or window.project
        self._start("worker", title, tr("Rendering audio in corso..."), 0, tr("Errore esportazione audio"),
                    lambda _result: window.statusBar().showMessage(f"{done_msg}: {path}", 6000),
                    render_project_mix_to_wav, project, path, tracks=tracks, dry=dry,
                    skip_seconds=skip_seconds, length_seconds=length_seconds, tempo=constant_tempo(project))

    # ------------------------------------------------------------ congelamento

    def add_freeze_action(self, menu, track_name: str):
        """Nel menu di una traccia: Congela in audio, o Scongela se lo e'
        gia'. Niente per la traccia audio che ne suona un'altra congelata."""
        from core import freeze
        project = self.window.project
        track = project.get_track(track_name)
        if any(t.frozen == track_name for t in project.tracks):
            return None
        if freeze.is_frozen(project, track):
            action = menu.addAction(tr("Scongela (torna a '{name}')", name=track.name))
            action.setToolTip(tr("Toglie la traccia audio congelata e la traccia torna a suonare com'era."))
        else:
            action = menu.addAction(tr("Congela in audio"))
            action.setToolTip(tr("La traccia diventa una clip audio, calcolata una volta sola (note, strumento, "
                                 "effetti): il computer lavora meno. La traccia resta, silenziata; "
                                 "Scongela la fa tornare."))
        action.triggered.connect(lambda _checked=False: self.toggle_freeze(track_name))
        return action

    def toggle_freeze(self, track_name: str):
        """Congela in audio (in un thread, annullabile) o scongela la traccia."""
        from core import freeze
        from core.audio_tracks import target_audio_dir
        window = self.window
        track = window.project.get_track(track_name)
        if freeze.is_frozen(window.project, track):
            removed = freeze.unfreeze(window.project, track)
            window._mark_dirty()
            window.refresh_mixer()
            window.statusBar().showMessage(tr("'{name}' scongelata: suona di nuovo dalle sue note ed effetti.",
                                              name=track.name) if removed else
                                           tr("'{name}' scongelata.", name=track.name), 6000)
            return
        msg = self._syntax_error(track)
        if msg is not None:
            QMessageBox.critical(window, tr("Errore di sintassi"), tr("Impossibile congelare:\n{msg}", msg=msg))
            return

        def done(path):
            if window.project.find_track(track_name) is not track:
                return                     # la traccia e' sparita intanto
            audio = freeze.apply_freeze(window.project, track, path)
            window._mark_dirty()
            window.refresh_mixer()
            window.statusBar().showMessage(tr("'{name}' congelata in audio nella traccia '{audio}'.",
                                              name=track.name, audio=audio.name), 6000)

        self._start("freeze_worker", tr("Congela in audio"), tr("Congelo '{name}' in audio...", name=track.name), 0,
                    tr("Congela in audio"), done,
                    freeze.render_frozen_audio, window.project, track, target_audio_dir(window.current_path))
