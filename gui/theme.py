"""
Tema visivo globale dell'applicazione: un foglio di stile Qt (QSS), scuro o
chiaro (vedi stylesheet_for/Opzioni -> Tema), applicato a livello di
QApplication cosi' da coprire anche i dialoghi secondari (gestione
strumenti, libreria MIDI, guida...).
"""

# Costanti del tema scuro (predefinito), esportate anche singolarmente per i
# pochi punti che le usano fuori dal foglio di stile globale (colori di
# stato Play/Stop, testo secondario...): NON cambiano con il tema chiaro,
# restano leggibili su entrambi gli sfondi.
ACCENT = "#5aa9e6"
ACCENT_DIM = "#3d7bab"
BG_BASE = "#1e1e1e"
BG_PANEL = "#252526"
BG_FIELD = "#2d2d30"
BG_HOVER = "#333338"
BORDER = "#3a3a3a"
TEXT = "#e0e0e0"
TEXT_DIM = "#999999"
GOOD = "#4caf50"
BAD = "#e05555"
WARN = "#e0a030"   # avvisi che non bloccano (es. controlli di battuta)

_DARK = dict(ACCENT=ACCENT, ACCENT_DIM=ACCENT_DIM, BG_BASE=BG_BASE, BG_PANEL=BG_PANEL,
             BG_FIELD=BG_FIELD, BG_HOVER=BG_HOVER, BORDER=BORDER, TEXT=TEXT, TEXT_DIM=TEXT_DIM,
             LINK=ACCENT)

# ACCENT resta lo stesso blu in entrambi i temi: e' abbastanza chiaro da
# restare leggibile come bordo/handle/sfondo di stato "attivo" (col testo
# scuro fisso usato da QPushButton:checkable:checked) sia su sfondo scuro
# che chiaro. Cio' che cambia davvero fra i due temi sono i neutri
# (sfondi/bordi/testo) e ACCENT_DIM (sfondo di hover/selezione, che deve
# restare in contrasto col TEXT del tema). LINK (i link della guida e dei
# QTextBrowser) invece cambia: ACCENT su bianco come testo si legge poco.
_LIGHT = dict(ACCENT=ACCENT, ACCENT_DIM="#cfe3f5", BG_BASE="#f5f5f5", BG_PANEL="#ffffff",
              BG_FIELD="#ffffff", BG_HOVER="#e8f0f8", BORDER="#d3d3d6", TEXT="#1c1c1e",
              TEXT_DIM="#6b6b6f", LINK="#1d5f99")


# Stato del tema attivo, usato dai widget che si disegnano con un
# QSS PER-ISTANZA invece che tramite il foglio di stile globale (vedi
# track_card_colors piu' sotto): a differenza dei widget
# standard, questi non seguono automaticamente app.setStyleSheet(...), quindi
# vanno ridisegnati esplicitamente da chi cambia tema (vedi
# MainWindow._apply_theme) DOPO aver chiamato set_active_theme().
_active_theme = "dark"


def set_active_theme(name: str):
    global _active_theme
    _active_theme = "light" if name == "light" else "dark"


def get_active_theme() -> str:
    return _active_theme


def track_card_colors() -> dict:
    """Colori per le 'card' del mixer (testate delle tracce, gui.track_header), che si disegnano
    con uno sfondo scuro fisso indipendente dal foglio di stile globale:
    qui si aggancia anche quel dettaglio al tema attivo, cosi' da non
    restare illeggibili (sfondo scuro fisso + testo scuro del tema chiaro)
    quando l'utente passa al tema chiaro."""
    if _active_theme == "light":
        return dict(bg="#ffffff", border="#d3d3d6", text_dim="#6b6b6f")
    return dict(bg="#232323", border="#3a3a3a", text_dim="#999999")


def _build_stylesheet(p: dict) -> str:
    ACCENT, ACCENT_DIM = p["ACCENT"], p["ACCENT_DIM"]
    BG_BASE, BG_PANEL, BG_FIELD, BG_HOVER = p["BG_BASE"], p["BG_PANEL"], p["BG_FIELD"], p["BG_HOVER"]
    BORDER, TEXT, TEXT_DIM = p["BORDER"], p["TEXT"], p["TEXT_DIM"]
    return f"""
QMainWindow, QDialog {{
    background-color: {BG_BASE};
    color: {TEXT};
}}

QWidget {{
    color: {TEXT};
    font-size: 13px;
}}

QLabel {{
    background: transparent;
}}

QMenuBar {{
    background-color: {BG_PANEL};
    color: {TEXT};
    border-bottom: 1px solid {BORDER};
    padding: 2px;
}}
QMenuBar::item {{
    background: transparent;
    padding: 4px 10px;
    border-radius: 4px;
}}
QMenuBar::item:selected {{
    background-color: {BG_HOVER};
}}
QMenu {{
    background-color: {BG_PANEL};
    color: {TEXT};
    border: 1px solid {BORDER};
    padding: 4px;
}}
QMenu::item {{
    padding: 5px 24px 5px 12px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {ACCENT_DIM};
}}
QMenu::separator {{
    height: 1px;
    background: {BORDER};
    margin: 4px 6px;
}}

QToolBar {{
    background-color: {BG_PANEL};
    border-bottom: 1px solid {BORDER};
    padding: 4px;
    spacing: 6px;
}}

QStatusBar {{
    background-color: {BG_PANEL};
    color: {TEXT_DIM};
    border-top: 1px solid {BORDER};
}}

QPushButton {{
    background-color: {BG_FIELD};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 6px 12px;
}}
QPushButton:hover {{
    background-color: {BG_HOVER};
    border-color: {ACCENT_DIM};
}}
QPushButton:pressed {{
    background-color: {ACCENT_DIM};
}}
QPushButton:checkable:checked {{
    background-color: {ACCENT};
    color: #10151a;
    font-weight: bold;
    border-color: {ACCENT};
}}
QToolButton {{
    background: transparent;
    color: {TEXT};
    border: 1px solid transparent;
    border-radius: 5px;
    padding: 5px 10px;
}}
QToolButton:hover {{
    background-color: {BG_HOVER};
    border-color: {BORDER};
}}
QToolButton:checked {{
    background-color: {ACCENT};
    color: #10151a;
    font-weight: bold;
    border-color: {ACCENT};
}}

QPushButton:disabled {{
    color: {TEXT_DIM};
    background-color: {BG_PANEL};
}}

QLineEdit, QPlainTextEdit, QTextEdit {{
    background-color: {BG_FIELD};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 4px;
    selection-background-color: {ACCENT_DIM};
}}
QLineEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {ACCENT};
}}

QComboBox {{
    background-color: {BG_FIELD};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 4px 8px;
}}
QComboBox:hover {{
    border-color: {ACCENT_DIM};
}}
QComboBox QAbstractItemView {{
    background-color: {BG_PANEL};
    color: {TEXT};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT_DIM};
    outline: none;
}}

QSpinBox, QDoubleSpinBox {{
    background-color: {BG_FIELD};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 5px;
    /* padding-right riserva lo spazio alle frecce su/giu': una volta che un
    foglio di stile tocca QSpinBox, Qt passa al layout CSS e NON riserva piu'
    automaticamente questo spazio (a differenza dello stile nativo) — senza
    questa regola il testo (es. il valore di un campo stretto come "Ottava"
    in Suona con la tastiera) finisce sotto le frecce, illeggibile. */
    padding: 3px 20px 3px 6px;
}}
QSpinBox:disabled, QDoubleSpinBox:disabled {{
    color: {TEXT_DIM};
    background-color: {BG_PANEL};
}}

QCheckBox {{
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 15px; height: 15px;
    border: 1px solid {BORDER};
    border-radius: 3px;
    background: {BG_FIELD};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}

/* Come QCheckBox::indicator ma circolare: senza questa regola QRadioButton
non e' toccato dal foglio di stile e resta nel pallino nero pieno nativo,
indistinguibile fra selezionato e non (es. "Modalita' di analisi" nel
dialogo di importazione audio). */
QRadioButton {{
    spacing: 8px;
}}
QRadioButton::indicator {{
    width: 15px; height: 15px;
    border: 1px solid {BORDER};
    border-radius: 8px;
    background: {BG_FIELD};
}}
QRadioButton::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}

QProgressBar {{
    background-color: {BG_FIELD};
    border: 1px solid {BORDER};
    border-radius: 5px;
    text-align: center;
    color: {TEXT};
    font-weight: bold;
}}
QProgressBar::chunk {{
    background-color: {ACCENT_DIM};
    border-radius: 4px;
}}

QSlider::groove:horizontal {{
    height: 4px;
    background: {BORDER};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {ACCENT};
    width: 13px;
    margin: -5px 0;
    border-radius: 6px;
}}
QSlider::handle:horizontal:hover {{
    background: #77bced;
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT_DIM};
    border-radius: 2px;
}}

QScrollArea {{
    background-color: {BG_BASE};
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background-color: {BG_BASE};
}}
QAbstractScrollArea::corner {{
    background-color: {BG_BASE};
}}
QScrollBar:vertical {{
    background: {BG_BASE};
    width: 11px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 5px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {ACCENT_DIM};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QListWidget {{
    background-color: {BG_FIELD};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 5px;
    outline: none;
}}
QListWidget::item {{
    padding: 5px 6px;
    border-radius: 3px;
}}
QListWidget::item:selected {{
    background-color: {ACCENT_DIM};
}}
QListWidget::item:hover {{
    background-color: {BG_HOVER};
}}

/* Selettore senza tipo (non "QFrame#panelBox"): usato anche su QLabel per
altri "pannelli scatolati" scuri con contenuto informativo (es. la legenda
tasti e l'area della tastiera in Suona con la tastiera), che altrimenti
resterebbero fissi al grigio scuro del tema originale — illeggibili col
testo scuro del tema chiaro. */
#panelBox {{
    background-color: {BG_FIELD};
    border: 1px solid {BORDER};
    border-radius: 6px;
}}

QTreeView, QListView {{
    background-color: {BG_FIELD};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 5px;
    outline: none;
    alternate-background-color: {BG_PANEL};
}}
QTreeView::item, QListView::item {{
    padding: 3px 4px;
}}
QTreeView::item:selected, QListView::item:selected {{
    background-color: {ACCENT_DIM};
}}
QTreeView::item:hover, QListView::item:hover {{
    background-color: {BG_HOVER};
}}
QHeaderView::section {{
    background-color: {BG_PANEL};
    color: {TEXT};
    padding: 4px 6px;
    border: none;
    border-right: 1px solid {BORDER};
    border-bottom: 1px solid {BORDER};
}}

QSplitter::handle {{
    background-color: {BORDER};
}}
QSplitter::handle:hover {{
    background-color: {ACCENT_DIM};
}}

QTextBrowser {{
    background-color: {BG_FIELD};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 5px;
}}

QToolTip {{
    background-color: {BG_PANEL};
    color: {TEXT};
    border: 1px solid {ACCENT_DIM};
    padding: 4px 6px;
    border-radius: 4px;
}}
"""


DARK_STYLESHEET = _build_stylesheet(_DARK)
LIGHT_STYLESHEET = _build_stylesheet(_LIGHT)


def palette_for(theme_name: str):
    """QPalette coerente con il tema: va applicata insieme al foglio di stile
    (vedi main.main e MainWindow._apply_theme). Lo stile Fusion prende i
    colori dalla palette per tutto cio' che il QSS non copre (sfondo del
    canvas a box, pulsanti "attivi" della toolbar, tooltip...): lasciando
    quella di sistema, su un desktop con tema scuro quelle parti restavano
    scure anche col tema chiaro dell'app (e viceversa)."""
    from PySide6.QtGui import QColor, QPalette
    p = _LIGHT if theme_name == "light" else _DARK
    pal = QPalette()
    for role, key in ((QPalette.Window, "BG_BASE"), (QPalette.WindowText, "TEXT"),
                      (QPalette.Base, "BG_FIELD"), (QPalette.AlternateBase, "BG_PANEL"),
                      (QPalette.Text, "TEXT"), (QPalette.Button, "BG_FIELD"),
                      (QPalette.ButtonText, "TEXT"), (QPalette.ToolTipBase, "BG_PANEL"),
                      (QPalette.ToolTipText, "TEXT"), (QPalette.PlaceholderText, "TEXT_DIM"),
                      (QPalette.Highlight, "ACCENT"), (QPalette.Mid, "BORDER"),
                      (QPalette.Link, "LINK"), (QPalette.LinkVisited, "LINK")):
        pal.setColor(role, QColor(p[key]))
    pal.setColor(QPalette.HighlightedText, QColor("#10151a"))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, QColor(p["TEXT_DIM"]))
    return pal


def stylesheet_for(theme_name: str) -> str:
    """Foglio di stile per il nome di tema salvato nelle impostazioni
    (vedi core.settings.get_theme/set_theme): 'light' o, per qualunque altro
    valore (incluso quello predefinito 'dark'), il tema scuro."""
    return LIGHT_STYLESHEET if theme_name == "light" else DARK_STYLESHEET
