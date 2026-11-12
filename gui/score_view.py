"""
Vista Partitura: le tracce del progetto su pentagramma, impaginate da
Verovio (vedi core.score_render) a partire dal MusicXML dell'esportazione,
aggiornate mentre si scrive; da qui si esporta in PDF e si stampa.
Durante l'ascolto le note che suonano diventano rosse e la vista le segue
(la finestra principale chiama show_playing_beat a ogni scatto della barra
di avanzamento).

La finestra non e' modale: resta aperta accanto all'editor. Ogni mezzo
secondo controlla se il progetto e' cambiato (lo stesso contatore delle
modifiche del salvataggio automatico) e, dopo una breve pausa nella
digitazione, ridisegna. Se una traccia ha un errore di sintassi resta la
partitura dell'ultima versione valida, con un avviso.
"""

from typing import Callable, List, Optional

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPageLayout, QPageSize, QPainter, QPdfWriter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

from core import score_render
from core.i18n import tr
from core.musicxml_export import project_to_musicxml
from core.notation import validate_track_text
from .file_dialogs import file_dialog_options

# Larghezza in pixel di una pagina a zoom 100%.
PAGE_PIXELS = 794
PAGE_GAP = 16
ZOOM_STEPS = [50, 67, 80, 100, 125, 150, 200]
REFRESH_POLL_MS = 500
REFRESH_DELAY_MS = 400
# Le note che suonano si ridisegnano in rosso sopra quelle nere.
PLAYING_COLOR = QColor(220, 30, 30)

INSTALL_HINT = "pip install verovio"


def score_tracks(project, only_current: bool = False, current_track_name: Optional[str] = None):
    """Le tracce da mettere in partitura: quelle udibili con notazione,
    oppure solo la traccia selezionata."""
    if only_current:
        tracks = [t for t in project.tracks if t.name == current_track_name]
    else:
        tracks = project.audible_tracks()
    return [t for t in tracks if not t.is_audio]


def render_score(project, tracks) -> List[str]:
    """Le pagine SVG della partitura di queste tracce. Solleva ValueError
    con un messaggio leggibile se una traccia ha un errore di sintassi."""
    return render_score_with_timing(project, tracks)[0]


def render_score_with_timing(project, tracks):
    """Come render_score, con i tempi delle note (core.score_render.NoteTiming)."""
    for track in tracks:
        ok, msg = validate_track_text(track.text, project.patterns,
                                      default_octave=track.instrument.default_octave)
        if not ok:
            raise ValueError(tr("Errore di sintassi nella traccia '{name}': {msg}", name=track.name, msg=msg))
    return score_render.render_pages_with_timing(project_to_musicxml(project, tracks=tracks))


def paint_pages(pages: List[str], painter: QPainter, page_rect: Callable[[], QRectF],
                new_page: Callable[[], bool]) -> None:
    """Disegna le pagine una per foglio (PDF o stampante), ciascuna adattata
    al foglio mantenendo le proporzioni."""
    for n, svg in enumerate(pages):
        if n and not new_page():
            return
        renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        target = page_rect()
        size = renderer.defaultSize()
        if size.width() > 0 and size.height() > 0:
            scale = min(target.width() / size.width(), target.height() / size.height())
            target = QRectF(target.x(), target.y(), size.width() * scale, size.height() * scale)
        renderer.render(painter, target)


def export_pdf(pages: List[str], path: str) -> None:
    writer = QPdfWriter(path)
    writer.setPageSize(QPageSize(QPageSize.A4))
    writer.setPageMargins(QPageLayout().margins())      # nessun margine: li ha gia' la pagina
    writer.setResolution(300)
    writer.setCreator("SoundText")
    painter = QPainter(writer)
    try:
        paint_pages(pages, painter, lambda: QRectF(0, 0, writer.width(), writer.height()), writer.newPage)
    finally:
        painter.end()


class ScorePagesWidget(QWidget):
    """Le pagine una sotto l'altra, su fondo grigio come in un lettore PDF."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._renderers: List[QSvgRenderer] = []
        self.zoom = 100
        self._highlight = ()        # (pagina, id della nota) evidenziate
        self._note_boxes = {}       # (pagina, id) -> riquadro nelle coordinate della pagina SVG
        self.setAutoFillBackground(True)

    def set_pages(self, pages: List[str]) -> None:
        self._renderers = [QSvgRenderer(QByteArray(svg.encode("utf-8")), self) for svg in pages]
        self._highlight = ()
        self._note_boxes = {}
        self._update_size()

    def page_count(self) -> int:
        return len(self._renderers)

    def set_zoom(self, zoom: int) -> None:
        self.zoom = zoom
        self._update_size()

    def _page_size(self, renderer: QSvgRenderer) -> QSize:
        size = renderer.defaultSize()
        width = round(PAGE_PIXELS * self.zoom / 100)
        height = round(width * size.height() / size.width()) if size.width() else width
        return QSize(width, height)

    def _update_size(self) -> None:
        sizes = [self._page_size(r) for r in self._renderers]
        width = max([s.width() for s in sizes] + [PAGE_PIXELS * self.zoom // 100]) + 2 * PAGE_GAP
        height = sum(s.height() + PAGE_GAP for s in sizes) + PAGE_GAP
        self.setFixedSize(width, height)
        self.update()

    def _page_rects(self) -> List[QRectF]:
        rects = []
        y = PAGE_GAP
        for renderer in self._renderers:
            size = self._page_size(renderer)
            x = (self.width() - size.width()) // 2
            rects.append(QRectF(x, y, size.width(), size.height()))
            y += size.height() + PAGE_GAP
        return rects

    # ------------------------------------------------------- note che suonano

    def _note_rect(self, page_rects, page: int, note_id: str) -> Optional[QRectF]:
        """Il riquadro della nota nel widget, o None se non c'e'."""
        if page >= len(self._renderers):
            return None
        renderer = self._renderers[page]
        key = (page, note_id)
        if key not in self._note_boxes:
            box = None
            if renderer.elementExists(note_id):
                box = renderer.transformForElement(note_id).mapRect(renderer.boundsOnElement(note_id))
            self._note_boxes[key] = box
        box = self._note_boxes[key]
        view = renderer.viewBoxF()
        if box is None or view.width() <= 0 or view.height() <= 0:
            return None
        target = page_rects[page]
        sx, sy = target.width() / view.width(), target.height() / view.height()
        return QRectF(target.x() + (box.x() - view.x()) * sx, target.y() + (box.y() - view.y()) * sy,
                      box.width() * sx, box.height() * sy)

    def _highlight_notes(self):
        """(pagina, id, riquadro nel widget) delle note evidenziate."""
        page_rects = self._page_rects()
        notes = ((page, note_id, self._note_rect(page_rects, page, note_id)) for page, note_id in self._highlight)
        return [n for n in notes if n[2] is not None]

    def _highlight_rects(self) -> List[QRectF]:
        return [rect for _page, _id, rect in self._highlight_notes()]

    def _paint_playing_note(self, painter: QPainter, page: int, note_id: str, rect: QRectF):
        """La nota ridisegnata da sola in rosso: QtSvg non cambia il colore
        di un elemento, quindi la si disegna in un'immagine trasparente e se
        ne colora la forma."""
        ratio = self.devicePixelRatioF()
        image = QImage(max(1, round(rect.width() * ratio) + 1), max(1, round(rect.height() * ratio) + 1),
                       QImage.Format_ARGB32_Premultiplied)
        image.setDevicePixelRatio(ratio)
        image.fill(Qt.transparent)
        local = QRectF(0, 0, rect.width(), rect.height())
        note_painter = QPainter(image)
        note_painter.setRenderHint(QPainter.Antialiasing)
        self._renderers[page].render(note_painter, note_id, local)
        note_painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        note_painter.fillRect(local, PLAYING_COLOR)
        note_painter.end()
        painter.drawImage(rect.topLeft(), image)

    def set_highlight(self, notes) -> Optional[QRectF]:
        """Evidenzia queste note ((pagina, id), vedi NoteTiming.notes_at);
        restituisce il riquadro che le contiene, o None. Ridisegna solo i
        riquadri vecchi e nuovi: le pagine intere costano troppo a ogni
        scatto dell'ascolto."""
        old = self._highlight_rects()
        self._highlight = tuple(notes)
        new = self._highlight_rects()
        for rect in old + new:
            self.update(rect.toAlignedRect().adjusted(-3, -3, 3, 3))
        if not new:
            return None
        bounds = new[0]
        for rect in new[1:]:
            bounds = bounds.united(rect)
        return bounds

    def highlighted(self):
        return self._highlight

    def paintEvent(self, event):
        painter = QPainter(self)
        area = QRectF(event.rect())
        painter.fillRect(area, QColor("#808080"))
        for renderer, rect in zip(self._renderers, self._page_rects()):
            if not rect.intersects(area):
                continue
            painter.fillRect(rect, QColor("white"))
            renderer.render(painter, rect)
        for page, note_id, rect in self._highlight_notes():
            if rect.intersects(area):
                self._paint_playing_note(painter, page, note_id, rect)
        painter.end()


class ScoreDialog(QDialog):
    """host: la finestra principale (project, current_track_name e il
    contatore delle modifiche autosave.generation)."""

    def __init__(self, host):
        super().__init__(host)
        self.host = host
        self.setWindowTitle(tr("Partitura"))
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
        self.resize(900, 760)
        self._pages: List[str] = []
        self._timing = None             # core.score_render.NoteTiming delle pagine mostrate
        self._playing_beat = None       # beat dell'ascolto, None da fermo
        self._shown_key = None
        self._pending_key = None

        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.tracks_combo = QComboBox()
        self.tracks_combo.addItem(tr("Tutte le tracce udibili"), False)
        self.tracks_combo.addItem(tr("Solo la traccia selezionata"), True)
        self.tracks_combo.currentIndexChanged.connect(lambda _i: self._schedule(now=True))
        bar.addWidget(self.tracks_combo)
        bar.addSpacing(12)
        self.zoom_out_btn = QPushButton("−")
        self.zoom_out_btn.setToolTip(tr("Riduci"))
        self.zoom_out_btn.clicked.connect(lambda: self._step_zoom(-1))
        self.zoom_label = QLabel()
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setToolTip(tr("Ingrandisci"))
        self.zoom_in_btn.clicked.connect(lambda: self._step_zoom(1))
        for w in (self.zoom_out_btn, self.zoom_label, self.zoom_in_btn):
            bar.addWidget(w)
        bar.addStretch(1)
        self.pdf_btn = QPushButton(tr("Esporta PDF..."))
        self.pdf_btn.clicked.connect(self.export_pdf_dialog)
        bar.addWidget(self.pdf_btn)
        self.print_btn = QPushButton(tr("Stampa..."))
        self.print_btn.clicked.connect(self.print_dialog)
        bar.addWidget(self.print_btn)
        layout.addLayout(bar)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.pages_widget = ScorePagesWidget()
        self.scroll = QScrollArea()
        self.scroll.setWidget(self.pages_widget)
        self.scroll.setAlignment(Qt.AlignHCenter)
        self.scroll.setStyleSheet("QScrollArea { background: #808080; }")
        layout.addWidget(self.scroll, 1)

        self._set_zoom(100)
        self._poll = QTimer(self)
        self._poll.setInterval(REFRESH_POLL_MS)
        self._poll.timeout.connect(self._check_changes)
        self._delay = QTimer(self)
        self._delay.setSingleShot(True)
        self._delay.setInterval(REFRESH_DELAY_MS)
        self._delay.timeout.connect(self.refresh)
        self._poll.start()
        self.refresh()

    # ----------------------------------------------------------- contenuto

    def _key(self):
        only_current = bool(self.tracks_combo.currentData())
        return (self.host.autosave.generation, only_current,
                self.host.current_track_name if only_current else None)

    def _check_changes(self):
        key = self._key()
        if key != self._shown_key and key != self._pending_key:
            self._schedule()

    def _schedule(self, now: bool = False):
        self._pending_key = self._key()
        if now:
            self.refresh()
        else:
            self._delay.start()

    def selected_tracks(self):
        return score_tracks(self.host.project, bool(self.tracks_combo.currentData()),
                            self.host.current_track_name)

    def refresh(self):
        self._delay.stop()
        key = self._key()
        self._shown_key = key
        self._pending_key = None
        tracks = self.selected_tracks()
        if not tracks:
            self._pages = []
            self._timing = None
            self.pages_widget.set_pages([])
            self._set_status(tr("Nessuna traccia con note da mettere in partitura."))
            return
        try:
            pages, timing = render_score_with_timing(self.host.project, tracks)
        except Exception as e:      # errore di sintassi o di impaginazione: resta l'ultima partitura
            self._set_status(tr("Partitura non aggiornata — {msg}", msg=str(e)), error=True)
            return
        self._pages = pages
        self._timing = timing
        self.pages_widget.set_pages(pages)
        if self._playing_beat is not None:
            self.show_playing_beat(self._playing_beat)
        self._set_status(tr("{n} pagine", n=len(pages)) if len(pages) != 1 else tr("1 pagina"))

    def _set_status(self, text: str, error: bool = False):
        self.status_label.setText(text)
        self.status_label.setStyleSheet("color: #e05555;" if error else "")
        has_pages = bool(self._pages)
        self.pdf_btn.setEnabled(has_pages)
        self.print_btn.setEnabled(has_pages)

    def pages(self) -> List[str]:
        return list(self._pages)

    # ----------------------------------------------------------- ascolto

    def show_playing_beat(self, beat: Optional[float]):
        """Evidenzia le note che suonano al beat dato (None: nessuna, a
        riproduzione ferma) e, se escono dalla vista, la fa scorrere fin li'."""
        self._playing_beat = beat
        notes = self._timing.notes_at(beat) if beat is not None and self._timing is not None else ()
        if notes == self.pages_widget.highlighted():
            return
        rect = self.pages_widget.set_highlight(notes)
        if rect is not None and self.isVisible():
            center = rect.center()
            viewport = self.scroll.viewport()
            # margine verticale ampio: si vede anche il rigo che segue
            self.scroll.ensureVisible(int(center.x()), int(center.y()),
                                      min(80, viewport.width() // 4), min(160, viewport.height() // 3))

    # ----------------------------------------------------------- zoom

    def _set_zoom(self, zoom: int):
        self.pages_widget.set_zoom(zoom)
        self.zoom_label.setText(f"{zoom}%")
        self.zoom_out_btn.setEnabled(zoom > ZOOM_STEPS[0])
        self.zoom_in_btn.setEnabled(zoom < ZOOM_STEPS[-1])

    def _step_zoom(self, direction: int):
        current = self.pages_widget.zoom
        if direction > 0:
            nxt = next((z for z in ZOOM_STEPS if z > current), ZOOM_STEPS[-1])
        else:
            nxt = next((z for z in reversed(ZOOM_STEPS) if z < current), ZOOM_STEPS[0])
        self._set_zoom(nxt)

    # ----------------------------------------------------------- PDF e stampa

    def export_pdf_dialog(self):
        if not self._pages:
            return
        default = self.host._default_export_path(".pdf") if hasattr(self.host, "_default_export_path") else ""
        path, _ = QFileDialog.getSaveFileName(self, tr("Esporta partitura (PDF)"), default, tr("PDF (*.pdf)"),
                                              options=file_dialog_options())
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        try:
            export_pdf(self._pages, path)
        except Exception as e:
            QMessageBox.critical(self, tr("Errore export PDF"), str(e))
            return
        self._set_status(tr("Partitura esportata: {path}", path=path))

    def print_dialog(self):
        if not self._pages:
            return
        from PySide6.QtPrintSupport import QPrintDialog, QPrinter
        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.A4))
        dialog = QPrintDialog(printer, self)
        if dialog.exec() != QDialog.Accepted:
            return
        painter = QPainter(printer)
        try:
            paint_pages(self._pages, painter,
                        lambda: QRectF(printer.pageRect(QPrinter.DevicePixel).toRect().translated(
                            -printer.pageRect(QPrinter.DevicePixel).toRect().topLeft())),
                        printer.newPage)
        finally:
            painter.end()

    def hideEvent(self, event):
        # chiusa (anche con Esc, che non passa da closeEvent): niente controlli
        self._poll.stop()
        self._delay.stop()
        super().hideEvent(event)

    def showEvent(self, event):
        self._poll.start()
        self._check_changes()
        super().showEvent(event)


def show_selection_score(parent, project) -> None:
    """Mostra in una finestra non modale la partitura di un progetto di
    anteprima (la selezione di un editor, vedi gui.selection_actions)."""
    if not score_render.available():
        QMessageBox.information(
            parent, tr("Partitura"),
            tr("Per vedere e stampare la partitura serve la libreria Verovio, che non risulta "
               "installata.\n\nInstallala con:\n    {cmd}\npoi riavvia SoundText. Intanto puoi usare "
               "Esporta partitura (MusicXML) e aprire il file con MuseScore.", cmd=INSTALL_HINT))
        return
    try:
        pages = score_render.render_pages(project_to_musicxml(project, tracks=list(project.tracks)))
    except Exception as e:
        QMessageBox.critical(parent, tr("Partitura"), str(e))
        return
    dlg = QDialog(parent)
    dlg.setAttribute(Qt.WA_DeleteOnClose)
    dlg.setWindowTitle(tr("Partitura della selezione"))
    dlg.resize(900, 480)
    layout = QVBoxLayout(dlg)
    widget = ScorePagesWidget()
    widget.set_pages(pages)
    scroll = QScrollArea()
    scroll.setWidget(widget)
    scroll.setAlignment(Qt.AlignHCenter)
    scroll.setStyleSheet("QScrollArea { background: #808080; }")
    layout.addWidget(scroll, 1)
    dlg.show()
