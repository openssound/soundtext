"""
Partitura disegnata dentro SoundText: il MusicXML dell'esportazione
(core.musicxml_export) impaginato da Verovio (libreria di incisione
musicale, LGPL) in pagine SVG, che l'interfaccia mostra e stampa in PDF
con QtSvg (gui.score_view).

Verovio e' facoltativo: senza, available() e' False e la vista partitura
spiega come installarlo; il resto del programma non ne dipende.

L'SVG di Verovio usa due costrutti che QtSvg (SVG Tiny 1.2) non disegna:
un <svg> annidato per la scala e dei <tspan> annidati nei testi (titolo,
nomi delle parti, testo cantato, indicazioni di tempo). qt_svg() li
riscrive in forma equivalente: un gruppo con la trasformazione al posto
dell'<svg> interno, tspan in fila con gli attributi ereditati.
"""

import os
import re
import sys
import xml.etree.ElementTree as ET
from typing import List, Optional

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)

# Pagina A4 nelle unita' di Verovio (decimi di millimetro) e scala del
# disegno (percentuale): la stessa impaginazione per schermo e PDF.
PAGE_WIDTH = 2100
PAGE_HEIGHT = 2970
DEFAULT_SCALE = 40
# Il carattere dei testi della partitura: quello che Verovio misura per
# spaziarli (Times), col nome che i tre sistemi risolvono (fontconfig lo
# sostituisce con Liberation Serif o Nimbus Roman).
SERIF_FONT = "Times New Roman"

# Glifi SMuFL del carattere musicale di Verovio usati nei testi (indicazioni
# di metronomo): senza quel carattere installato si scrivono con i simboli
# Unicode equivalenti.
_SMUFL_TEXT = {
    "": "\U0001D15D", "": "\U0001D15E", "": "♩", "": "♪",
    "": "♬", "": ".",
    "": "\U0001D15D", "": "\U0001D15E", "": "♩", "": "♪", "": ".",
}

_toolkit = None


def _import_verovio():
    """verovio e' compilato con il vecchio ABI di std::string ma esporta le
    istanze di std::regex con gli stessi nomi del nuovo: se un'altra libreria
    gia' caricata le esporta (libLLVM, che Mesa carica per la grafica), le
    chiamate di verovio finiscono nelle sue e il processo muore con
    "free(): invalid pointer". RTLD_DEEPBIND gli fa usare le sue."""
    if "verovio" in sys.modules or not hasattr(os, "RTLD_DEEPBIND"):
        import verovio
        return verovio
    flags = sys.getdlopenflags()
    sys.setdlopenflags(flags | os.RTLD_DEEPBIND)
    try:
        import verovio
    finally:
        sys.setdlopenflags(flags)
    return verovio


def available() -> bool:
    try:
        _import_verovio()
        return True
    except Exception:
        return False


def version() -> Optional[str]:
    try:
        return _get_toolkit().getVersion()
    except Exception:
        return None


# Cartella dei dati di Verovio (caratteri musicali) accanto al programma
# impacchettato: gli script di build ve la copiano, cosi' la partitura
# funziona anche se PyInstaller non ha incluso i dati del pacchetto.
BUNDLED_DATA_DIR = "verovio-data"


def bundled_data_dir() -> Optional[str]:
    from .version import get_app_root
    path = os.path.join(get_app_root(), BUNDLED_DATA_DIR)
    return path if os.path.isdir(path) else None


def _get_toolkit():
    global _toolkit
    if _toolkit is None:
        verovio = _import_verovio()
        verovio.enableLog(verovio.LOG_OFF) if hasattr(verovio, "enableLog") else None
        data = bundled_data_dir()
        if data and hasattr(verovio, "setDefaultResourcePath"):
            verovio.setDefaultResourcePath(data)
        _toolkit = verovio.toolkit()
    return _toolkit


def render_pages(musicxml: str, scale: int = DEFAULT_SCALE) -> List[str]:
    """Le pagine della partitura come SVG gia' adatti a QtSvg."""
    tk = _get_toolkit()
    tk.setOptions({
        "pageWidth": PAGE_WIDTH, "pageHeight": PAGE_HEIGHT, "scale": scale,
        "adjustPageHeight": False, "footer": "none", "breaks": "auto",
    })
    if not tk.loadData(musicxml):
        raise ValueError("Verovio non ha potuto leggere la partitura")
    return [qt_svg(tk.renderToSVG(n)) for n in range(1, tk.getPageCount() + 1)]


def _tag(el) -> str:
    return el.tag.rsplit("}", 1)[-1]


def qt_svg(svg: str) -> str:
    """L'SVG di Verovio riscritto per QtSvg (vedi la descrizione del modulo)."""
    root = ET.fromstring(svg)
    width = float(re.sub(r"[^\d.]", "", root.get("width", "0")) or 0)
    height = float(re.sub(r"[^\d.]", "", root.get("height", "0")) or 0)
    for parent in root.iter():
        for child in list(parent):
            if child is not root and _tag(child) == "svg":
                view = [float(v) for v in (child.get("viewBox") or "0 0 1 1").split()]
                child.tag = f"{{{SVG_NS}}}g"
                child.attrib.pop("viewBox", None)
                if view[2] and view[3] and width and height:
                    child.set("transform", f"scale({width / view[2]:.6f} {height / view[3]:.6f})")
    for text in root.iter(f"{{{SVG_NS}}}text"):
        _flatten_text(text)
    for el in root.iter():
        # QtSvg prende "Times, serif" come un nome solo, che non esiste, e
        # ripiega su un carattere senza grazie piu' largo: i testi cantati
        # (spaziati da Verovio per il Times) si accavallerebbero.
        if el.get("font-family", "").startswith("Times"):
            el.set("font-family", SERIF_FONT)
    return ET.tostring(root, encoding="unicode")


def _flatten_text(text) -> None:
    leaves = []

    def walk(el, inherited):
        for child in list(el):
            if _tag(child) != "tspan":
                continue
            attrs = dict(inherited)
            attrs.update({k: v for k, v in child.attrib.items() if k not in ("id", "class")})
            if child.text and child.text.strip():
                leaves.append((attrs, child.text))
            walk(child, attrs)

    walk(text, {})
    if not leaves and not len(text):
        return
    for child in list(text):
        text.remove(child)
    text.text = None
    if text.get("font-size") == "0px":
        del text.attrib["font-size"]
    for attrs, content in leaves:
        if attrs.get("font-family") == "Leipzig":
            content = "".join(_SMUFL_TEXT.get(c, c) for c in content)
            attrs.pop("font-family")
            size = re.match(r"([\d.]+)px", attrs.get("font-size", ""))
            if size:       # i glifi SMuFL sono disegnati piu' grandi del testo
                attrs["font-size"] = f"{float(size.group(1)) * 0.6:.0f}px"
        if not content:
            continue
        tspan = ET.SubElement(text, f"{{{SVG_NS}}}tspan", attrs)
        tspan.text = content
