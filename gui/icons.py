"""
Icone della barra dei comandi e delle testate traccia, disegnate da SVG a
tratto (stile uniforme, nessun file esterno da distribuire, nessuna emoji
che cambia aspetto da un sistema all'altro). Il colore si sceglie a ogni
richiesta, cosi' le icone seguono il tema chiaro/scuro.
"""

from functools import lru_cache

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_STROKE = ('fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" '
           'stroke-linejoin="round"')

# Corpo SVG (viewBox 0 0 24 24) di ogni icona; {c} = colore.
_ICONS = {
    "rewind": f'<path d="M6 5v14" {_STROKE}/><path d="M19 5l-10 7 10 7z" {_STROKE}/>',
    "play": '<path d="M7 4l13 8-13 8z" fill="{c}"/>',
    "pause": '<rect x="6" y="5" width="4" height="14" rx="1" fill="{c}"/>'
             '<rect x="14" y="5" width="4" height="14" rx="1" fill="{c}"/>',
    "stop": '<rect x="6" y="6" width="12" height="12" rx="1.5" fill="{c}"/>',
    "record": '<circle cx="12" cy="12" r="6.5" fill="{c}"/>',
    "loop": f'<path d="M17 2l4 4-4 4" {_STROKE}/><path d="M3 11V9a3 3 0 0 1 3-3h15" {_STROKE}/>'
            f'<path d="M7 22l-4-4 4-4" {_STROKE}/><path d="M21 13v2a3 3 0 0 1-3 3H3" {_STROKE}/>',
    "metronome": f'<path d="M9 3h6l4 18H5z" {_STROKE}/><path d="M12 15l5-8" {_STROKE}/>',
    "more": '<circle cx="5" cy="12" r="1.8" fill="{c}"/><circle cx="12" cy="12" r="1.8" fill="{c}"/>'
            '<circle cx="19" cy="12" r="1.8" fill="{c}"/>',
    "plus": f'<path d="M12 5v14M5 12h14" {_STROKE}/>',
}


@lru_cache(maxsize=128)
def _pixmap(name: str, color: str, size: int) -> QPixmap:
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
           + _ICONS[name].replace("{c}", color) + "</svg>")
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return pix


def icon(name: str, color: str = "#e0e0e0", size: int = 32) -> QIcon:
    """QIcon dell'icona 'name' (vedi _ICONS) nel colore indicato."""
    return QIcon(_pixmap(name, color, size))
