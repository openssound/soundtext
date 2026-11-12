"""
I livelli della finestra principale: il vu-meter del master e quelli delle
tracce durante l'ascolto, la spia di clipping e il comando Riproduzione ->
Analizza livelli.

La finestra possiede un LevelMonitor (MainWindow.levels) e lo chiama dalla
riproduzione: start() al Play, update() a ogni scatto della barra di
avanzamento, finish() allo Stop o alla fine del brano, forget_track_peaks()
quando il brano cambia. I livelli li misura il motore prima di suonare (vedi
core.levels e PlaybackEngine.master_levels/track_levels).
"""

import copy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox, QProgressDialog

from core.i18n import tr


class LevelMonitor:
    def __init__(self, window):
        self.window = window
        self._clip_detail_for = None    # (livelli, testo con le battute)
        self.track_peaks = {}           # nome traccia -> core.levels.TrackPeak (Analizza livelli)
        self._worker = None

    # ------------------------------------------------------------ durante l'ascolto

    def _track_headers(self):
        from .track_header import TrackHeaderWidget
        return self.window.findChildren(TrackHeaderWidget)

    def start(self):
        """Play: i vu-meter delle tracce ripartono."""
        for header in self._track_headers():
            header.meter.start()

    def update(self):
        """Livello del master nel punto che si sta ascoltando e spia di
        clipping (vedi core.levels, misurati dal motore prima di suonare)."""
        window = self.window
        seconds = window.playback.position_seconds()
        self.update_tracks(seconds)
        levels = window.playback.master_levels
        meter = window.level_meter
        if seconds is None or levels is None:
            # audio partito ma senza streaming: niente livelli da mostrare
            meter.set_available(not (window._playback_start_wall is not None and seconds is None))
            return
        meter.set_available(True)
        meter.set_levels(*levels.channel_peak_between(seconds - 0.06, seconds))
        if levels.clipped_between(seconds - 0.1, seconds):
            meter.set_clipped(True, self._clip_detail(levels))

    def update_tracks(self, seconds):
        """Vu-meter delle tracce nel punto che si sta ascoltando (vedi
        PlaybackEngine.track_levels)."""
        levels = self.window.playback.track_levels
        for header in self._track_headers():
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
        bars = bars_for_seconds(self.window.project, self.window._playback_tempo_map,
                                [start for start, _end in levels.clip_regions()])
        text = tr("Il master clippa alle battute: {bars}", bars=format_bars(bars)) if bars else ""
        self._clip_detail_for = (levels, text)
        return text

    def finish(self):
        """Stop o fine del brano: la barra torna a zero, la spia resta; se il
        master ha clippato, lo dice anche nella barra di stato."""
        window = self.window
        window.level_meter.silence()
        for header in self._track_headers():
            header.meter.silence()
        if window.level_meter.clipped:
            levels = window.playback.master_levels
            detail = self._clip_detail(levels) if levels is not None else ""
            window.statusBar().showMessage(
                tr("Attenzione: il master clippa (il suono si rompe). Abbassa il volume del master "
                   "o delle tracce piu' forti.") + (" " + detail if detail else ""), 15000)

    # ------------------------------------------------------------ Analizza livelli

    def peak_for(self, track_name):
        """Il picco di Analizza livelli della traccia, o None."""
        return self.track_peaks.get(track_name)

    def forget_track_peaks(self):
        """Il brano e' cambiato: i picchi di Analizza livelli non valgono piu'."""
        if not self.track_peaks:
            return
        self.track_peaks = {}
        for header in self._track_headers():
            header.set_peak(None)

    def analyze(self):
        """Sintetizza ogni traccia da sola e il mix (in background,
        annullabile) e mostra i picchi nelle testate delle tracce e un
        riepilogo (vedi core.levels.analyze_project_levels)."""
        from core.levels import analyze_project_levels
        from .worker import Worker
        if self._worker is not None:
            return
        window = self.window
        project = copy.deepcopy(window.project)   # il brano puo' cambiare mentre si analizza
        cancelled = {"value": False}
        dialog = QProgressDialog(tr("Analisi dei livelli: ogni traccia viene sintetizzata da sola..."),
                                 tr("Annulla"), 0, 100, window)
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
            self._worker = None
            dialog.canceled.disconnect()
            dialog.close()
            return was_cancelled

        def done(report):
            if not finish():
                self.show_report(report)

        def failed(message):
            if not finish():
                QMessageBox.warning(window, tr("Analizza livelli"),
                                    tr("Analisi dei livelli non riuscita:\n{message}", message=message))

        worker.finished_ok.connect(done)
        worker.finished_error.connect(failed)
        self._worker = worker
        worker.start()

    def show_report(self, report):
        from core.levels import format_bars
        self.track_peaks = dict(report.tracks)
        for header in self._track_headers():
            header.set_peak(self.track_peaks.get(header.track_name))
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
        QMessageBox.information(self.window, tr("Analizza livelli"), "\n".join(lines))
