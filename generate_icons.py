#!/usr/bin/env python3
"""
Rigenera assets/icon.png e assets/soundtext.ico a partire da assets/icon.svg,
l'unica sorgente dell'icona: modificare lo SVG e rilanciare questo script.

L'.ico contiene piu' dimensioni (16..256 px), ciascuna disegnata dallo SVG
alla sua misura reale invece che rimpicciolita da un'unica bitmap: Windows
sceglie quella adatta per barra delle applicazioni, Esplora risorse, ecc.
Viene versionato e usato cosi' com'e' dalle build Windows (vedi
build-windows-portable.ps1 e .github/workflows/build-release.yml).

Uso:
    python generate_icons.py
"""

import os
import struct
import sys

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

ROOT = os.path.dirname(os.path.abspath(__file__))
SVG_PATH = os.path.join(ROOT, "assets", "icon.svg")
PNG_PATH = os.path.join(ROOT, "assets", "icon.png")
ICO_PATH = os.path.join(ROOT, "assets", "soundtext.ico")
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)


def render(renderer: QSvgRenderer, size: int) -> QImage:
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return image


def png_bytes(image: QImage) -> bytes:
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.WriteOnly)
    image.save(buf, "PNG")
    buf.close()
    return bytes(data)


def write_ico(path: str, images):
    """ICO con immagini PNG incorporate (supportate da Windows Vista in poi)."""
    entries = [(size, png_bytes(img)) for size, img in images]
    header = struct.pack("<HHH", 0, 1, len(entries))
    offset = len(header) + 16 * len(entries)
    directory = b""
    for size, data in entries:
        dim = 0 if size >= 256 else size  # 0 = 256 nel formato ICO
        directory += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    with open(path, "wb") as f:
        f.write(header + directory + b"".join(data for _, data in entries))


def main():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication(sys.argv)  # noqa: F841  (necessaria per QPainter)
    renderer = QSvgRenderer(SVG_PATH)
    if not renderer.isValid():
        sys.exit(f"SVG non valido: {SVG_PATH}")
    render(renderer, 256).save(PNG_PATH, "PNG")
    write_ico(ICO_PATH, [(size, render(renderer, size)) for size in ICO_SIZES])
    print(f"Scritti {PNG_PATH} e {ICO_PATH}")


if __name__ == "__main__":
    main()
