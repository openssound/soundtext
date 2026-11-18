"""
"Le note sempre a portata di mano": chi legge %Tema.invert(e*5).retro vede e
sente che cosa suona senza esportare. Fermando il mouse sul richiamo (o con
Ctrl+I) compare un riquadro con le prime battute in partitura, la catena passo
per passo, gli avvisi della libreria e un pulsante per ascoltare. La partitura
si disegna dopo aver mostrato il riquadro: il testo c'e' subito.
"""

from typing import Callable, Optional

from PySide6.QtCore import QByteArray, QPoint, QRect, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from core import score_render
from core.i18n import tr
from core.musicxml_export import project_to_musicxml
from core.notation import NotationError
from core.transform_preview import (expansion, preview_notation, preview_project, reference_at, reference_point,
                                    stage_lines)
from .theme import tooltip_style, warn_text


class ScoreSnippet(QWidget):
    """Le prime battute di un progetto d'anteprima, in una piccola partitura."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 90)
        self._renderer: Optional[QSvgRenderer] = None
        self._message = ""
        self._project = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(0)
        self._timer.timeout.connect(self._render)

    def set_project(self, project):
        self._project = project
        self._timer.start()

    def clear(self, message: str = ""):
        self._timer.stop()
        self._project, self._renderer, self._message = None, None, message
        self.update()

    def _render(self):
        if self._project is None:
            return
        self._renderer = None
        self._message = ""
        if not score_render.available():
            self._message = tr("Per vedere la partitura serve la libreria Verovio.")
        else:
            try:
                xml = project_to_musicxml(self._project, tracks=list(self._project.tracks))
                renderer = QSvgRenderer(QByteArray(score_render.render_snippet(xml).encode("utf-8")))
                self._renderer = renderer if renderer.isValid() else None
            except Exception as e:      # una partitura che non si impagina non ferma l'anteprima
                self._message = str(e)
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(420, 120)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("white"))
        if self._renderer is not None:
            size = self._renderer.defaultSize()
            scale = min(self.width() / max(1, size.width()), self.height() / max(1, size.height()))
            self._renderer.render(painter, QRectF(0, 0, size.width() * scale, size.height() * scale))
        elif self._message:
            painter.setPen(QColor("#555555"))
            painter.drawText(self.rect().adjusted(6, 6, -6, -6), Qt.TextWordWrap, self._message)


class ReferencePreviewPopup(QFrame):
    """Il riquadro dell'anteprima: resta finche' il cursore e' sul richiamo o
    sul riquadro (controllato ogni 150 ms, come gui.level_meter.HoverTip);
    aperto con Ctrl+I resta finche' si scrive o si muove il cursore del testo."""

    def __init__(self, owner: QWidget):
        super().__init__(None, Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFrameShape(QFrame.StyledPanel)
        owner.destroyed.connect(self.deleteLater)
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self.title = QLabel()
        self.title.setTextFormat(Qt.PlainText)
        top.addWidget(self.title, 1)
        self.play_btn = QPushButton("▶")
        self.play_btn.setToolTip(tr("Ascolta il risultato con lo strumento della traccia"))
        self.play_btn.setFixedWidth(36)
        self.play_btn.clicked.connect(self._on_play)
        top.addWidget(self.play_btn)
        self.freeze_btn = QPushButton(tr("Congela"))
        self.freeze_btn.setToolTip(tr("Scrive per esteso le note del richiamo"))
        self.freeze_btn.clicked.connect(self._on_freeze)
        top.addWidget(self.freeze_btn)
        layout.addLayout(top)
        self.score = ScoreSnippet()
        layout.addWidget(self.score)
        self.stages = QLabel()
        self.stages.setTextFormat(Qt.PlainText)
        self.stages.setWordWrap(True)
        layout.addWidget(self.stages)
        self.notation = QLabel()
        self.notation.setTextFormat(Qt.PlainText)
        self.notation.setWordWrap(True)
        layout.addWidget(self.notation)
        self.warnings = QLabel()
        self.warnings.setTextFormat(Qt.PlainText)
        self.warnings.setWordWrap(True)
        layout.addWidget(self.warnings)
        self.setMaximumWidth(520)
        self._play: Optional[Callable[[], None]] = None
        self._freeze: Optional[Callable[[], None]] = None
        self._anchor = QRect()
        self._sticky = False
        self._poll = QTimer(self)
        self._poll.setInterval(150)
        self._poll.timeout.connect(self._check_cursor)

    def _on_play(self):
        if self._play is not None:
            self._play()

    def _on_freeze(self):
        if self._freeze is not None:
            self.hide()
            self._freeze()

    def present(self, title: str, stages: str, warnings: str, project, play, at: QPoint, sticky: bool,
                notation: str = "", freeze: Optional[Callable[[], None]] = None):
        self.setStyleSheet(tooltip_style())
        self.title.setText(title)
        self.stages.setText(stages)
        self.stages.setVisible(bool(stages))
        self.warnings.setText(warnings)
        self.warnings.setStyleSheet(f"color: {warn_text()};")
        self.warnings.setVisible(bool(warnings))
        self.notation.setText(notation)
        self.notation.setVisible(bool(notation))
        self._play, self._freeze, self._sticky = play, freeze, sticky
        self.play_btn.setVisible(play is not None)
        self.freeze_btn.setVisible(freeze is not None)
        self.score.setVisible(project is not None)
        if project is not None:
            self.score.set_project(project)
        self.adjustSize()
        screen = (QApplication.screenAt(at) or QApplication.primaryScreen()).availableGeometry()
        x = max(screen.left(), min(at.x() + 8, screen.right() + 1 - self.width()))
        y = at.y() + 18
        if y + self.height() > screen.bottom():
            y = max(screen.top(), at.y() - self.height() - 18)
        self.move(x, y)
        self._anchor = QRect(at - QPoint(40, 20), QSize(80, 40))
        self.show()
        self.raise_()
        self._poll.start()

    def _check_cursor(self):
        pos = QCursor.pos()
        if not self._sticky and not self.geometry().adjusted(-12, -12, 12, 12).contains(pos) \
                and not self._anchor.contains(pos):
            self.hide()

    def hideEvent(self, event):
        self._poll.stop()
        super().hideEvent(event)


def show_reference_preview(owner: QWidget, text: str, pos: int, project, track, playback,
                           global_pos: Optional[QPoint], origin_beat: float = 0.0,
                           freeze: Optional[Callable[[int, int], None]] = None) -> bool:
    """L'anteprima del richiamo con funzioni al carattere pos del testo di
    'owner', se ce n'e' uno. global_pos None: chiesta da tastiera. freeze: chi
    scrive per esteso il richiamo, (inizio, fine) nel testo."""
    popup = getattr(owner, "_reference_popup", None)
    found = reference_at(text, pos)
    if found is None:
        if popup is not None:
            popup.hide()
        return False
    if popup is None:
        popup = owner._reference_popup = ReferencePreviewPopup(owner)
        if hasattr(owner, "cursorPositionChanged"):
            owner.cursorPositionChanged.connect(lambda: popup._sticky and popup.hide())
    start, end, token = found
    instrument = track.instrument
    point = reference_point(text, start, project.patterns, instrument, project.meter(), origin_beat)
    sticky = global_pos is None
    if sticky:
        cursor_rect = owner.cursorRect() if hasattr(owner, "cursorRect") else QRect()
        global_pos = owner.mapToGlobal(cursor_rect.bottomLeft())
    try:
        result = expansion(token, project, point, instrument)
    except NotationError as e:
        popup.present(token, "", str(e), None, None, global_pos, sticky)
        return True
    lines = stage_lines(token, result)
    stages = "\n".join(f"{label}:  {notes}" for label, notes in lines) if len(lines) > 2 else ""
    preview = preview_project(project, token, point, track.instrument_name, track)
    try:
        notation = preview_notation(token, project, point, instrument)
    except (NotationError, ValueError):     # un evento che non si scrive: restano le note in partitura
        notation = ""
    popup.present(token, stages, "\n".join(result.warnings), preview,
                  lambda: playback.play(preview, only_audible=False), global_pos, sticky, notation,
                  (lambda: freeze(start, end)) if freeze is not None else None)
    return True
