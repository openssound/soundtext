"""
Tavole tasto fisico (scancode/keycode nativo) -> Qt.Key "canonico" (quello
che lo stesso tasto produce sotto layout italiano), per rendere la mappa
tastiera del dialogo "Suona con la tastiera" (gui.keyboard_play_dialog)
indipendente dalla lingua di sistema attiva: la CORRISPONDENZA CON LA
POSIZIONE del tasto premuto non cambia mai, anche se cambia il carattere che
quel tasto produce sotto un altro layout (es. passando da italiano a
US/UK/tedesco...).

QKeyEvent.key() (usato altrove in questo pacchetto per i tasti esecutivi -
Ctrl/Alt/Maiusc/Tab/Bloc Maiusc/Spazio - che non sono caratteri e quindi non
si spostano comunque cambiando layout) e' il codice "logico", legato al
CARATTERE che il layout attivo assegna al tasto fisico premuto.
QKeyEvent.nativeScanCode() e' invece il codice hardware del tasto fisico,
indipendente dal layout - ma e' un numero specifico della PIATTAFORMA
(Linux, Windows, macOS riportano valori diversi per lo stesso tasto
fisico), quindi servono tavole separate, scelte a runtime in base a
sys.platform.

Copertura: le tre righe di note (36 tasti, gui.keyboard_note_map.NOTE_ROW_KEYS)
e la fila qualita' accordi (10 tasti, QUALITY_ROW_KEYS/BASS_DOUBLE_KEY) - 45
dei 46 tasti coinvolti. Il 46esimo (l'ultimo tasto della riga ASDF, quello
che produce 'ù' su layout italiano) e' l'unico tasto "extra" dei layout ISO
europei senza equivalente univoco su tastiera US, e la sua esatta posizione
fisica (quale scancode nativo lo produce, su ciascuna piattaforma) resta
ambigua nelle fonti disponibili: deliberatamente NON incluso in queste
tavole, per non rischiare di piazzare male una nota invece di lasciarla
semplicemente non ancora indipendente dal layout. Quel singolo tasto resta
quindi legato al carattere come prima (si sposta se si cambia layout);
tutti gli altri 45 no.

Attendibilita': le tavole Linux (X11/Wayland) sono le piu' solide (codici
evdev del kernel, stabili da sempre, piu' la convenzione X11 di sommare 8 -
mantenuta anche dal plugin QPA wayland di Qt per compatibilita'). Le tavole
Windows (Scan Code Set 1, PS/2) e macOS (costanti kVK_ANSI_*, HIToolbox) si
basano su standard altrettanto stabili e documentati, ma non e' stato
possibile verificarle interattivamente su quelle piattaforme in questa
sessione di sviluppo (fatto solo su Linux): se un tasto risultasse
leggermente fuori posto su Windows/macOS, segnalarlo cosi' da correggere la
tavola specifica invece di doverle rifare tutte.
"""

import sys

from PySide6.QtCore import Qt

# ---------------------------------------------------------------------------
# Nome-posizione (indipendente da piattaforma/layout) -> Qt.Key canonico
# (layout italiano) - stesso ordine fisico gia' codificato in
# gui.keyboard_note_map.NOTE_ROW_KEYS/QUALITY_ROW_KEYS, qui usato per fare da
# ponte fra nome-posizione e Qt.Key.
_POSITION_TO_ITALIAN_KEY = {
    "1": Qt.Key_1, "2": Qt.Key_2, "3": Qt.Key_3, "4": Qt.Key_4, "5": Qt.Key_5,
    "6": Qt.Key_6, "7": Qt.Key_7, "8": Qt.Key_8, "9": Qt.Key_9, "0": Qt.Key_0,
    "MINUS": Qt.Key_Apostrophe, "EQUAL": Qt.Key_Igrave,
    "Q": Qt.Key_Q, "W": Qt.Key_W, "E": Qt.Key_E, "R": Qt.Key_R, "T": Qt.Key_T,
    "Y": Qt.Key_Y, "U": Qt.Key_U, "I": Qt.Key_I, "O": Qt.Key_O, "P": Qt.Key_P,
    "LEFTBRACE": Qt.Key_Egrave, "RIGHTBRACE": Qt.Key_Plus,
    "A": Qt.Key_A, "S": Qt.Key_S, "D": Qt.Key_D, "F": Qt.Key_F, "G": Qt.Key_G,
    "H": Qt.Key_H, "J": Qt.Key_J, "K": Qt.Key_K, "L": Qt.Key_L,
    "SEMICOLON": Qt.Key_Ograve, "APOSTROPHE": Qt.Key_Agrave,
    "Z": Qt.Key_Z, "X": Qt.Key_X, "C": Qt.Key_C, "V": Qt.Key_V, "B": Qt.Key_B,
    "N": Qt.Key_N, "M": Qt.Key_M,
    "COMMA": Qt.Key_Comma, "DOT": Qt.Key_Period, "SLASH": Qt.Key_Slash,
}

# --- Linux (X11 e Wayland) --------------------------------------------------
# nativeScanCode() = codice evdev del kernel + 8 (convenzione X11/XKB, vedi
# docstring del modulo). Codici evdev da linux/input-event-codes.h.
_EVDEV = {
    "1": 2, "2": 3, "3": 4, "4": 5, "5": 6, "6": 7, "7": 8, "8": 9, "9": 10, "0": 11,
    "MINUS": 12, "EQUAL": 13,
    "Q": 16, "W": 17, "E": 18, "R": 19, "T": 20, "Y": 21, "U": 22, "I": 23, "O": 24, "P": 25,
    "LEFTBRACE": 26, "RIGHTBRACE": 27,
    "A": 30, "S": 31, "D": 32, "F": 33, "G": 34, "H": 35, "J": 36, "K": 37, "L": 38,
    "SEMICOLON": 39, "APOSTROPHE": 40,
    "Z": 44, "X": 45, "C": 46, "V": 47, "B": 48, "N": 49, "M": 50,
    "COMMA": 51, "DOT": 52, "SLASH": 53,
}
_LINUX_X11_OFFSET = 8

# --- Windows -----------------------------------------------------------------
# Scan Code Set 1 (PS/2, standard fin dall'XT originale): e' il valore che
# arriva nel campo scancode di WM_KEYDOWN/lParam, indipendente dal layout di
# tastiera installato in Windows.
_WINDOWS = {
    "1": 0x02, "2": 0x03, "3": 0x04, "4": 0x05, "5": 0x06, "6": 0x07, "7": 0x08, "8": 0x09,
    "9": 0x0A, "0": 0x0B, "MINUS": 0x0C, "EQUAL": 0x0D,
    "Q": 0x10, "W": 0x11, "E": 0x12, "R": 0x13, "T": 0x14, "Y": 0x15, "U": 0x16, "I": 0x17,
    "O": 0x18, "P": 0x19, "LEFTBRACE": 0x1A, "RIGHTBRACE": 0x1B,
    "A": 0x1E, "S": 0x1F, "D": 0x20, "F": 0x21, "G": 0x22, "H": 0x23, "J": 0x24, "K": 0x25,
    "L": 0x26, "SEMICOLON": 0x27, "APOSTROPHE": 0x28,
    "Z": 0x2C, "X": 0x2D, "C": 0x2E, "V": 0x2F, "B": 0x30, "N": 0x31, "M": 0x32,
    "COMMA": 0x33, "DOT": 0x34, "SLASH": 0x35,
}

# --- macOS ---------------------------------------------------------------
# Costanti kVK_ANSI_* (HIToolbox/Events.h): Apple le documenta esplicitamente
# come posizioni fisiche del tasto su una tastiera ANSI, non influenzate dal
# layout attivo.
_MACOS = {
    "1": 0x12, "2": 0x13, "3": 0x14, "4": 0x15, "5": 0x17, "6": 0x16, "7": 0x1A, "8": 0x1C,
    "9": 0x19, "0": 0x1D, "MINUS": 0x1B, "EQUAL": 0x18,
    "Q": 0x0C, "W": 0x0D, "E": 0x0E, "R": 0x0F, "T": 0x11, "Y": 0x10, "U": 0x20, "I": 0x22,
    "O": 0x1F, "P": 0x23, "LEFTBRACE": 0x21, "RIGHTBRACE": 0x1E,
    "A": 0x00, "S": 0x01, "D": 0x02, "F": 0x03, "G": 0x05, "H": 0x04, "J": 0x26, "K": 0x28,
    "L": 0x25, "SEMICOLON": 0x29, "APOSTROPHE": 0x27,
    "Z": 0x06, "X": 0x07, "C": 0x08, "V": 0x09, "B": 0x0B, "N": 0x2D, "M": 0x2E,
    "COMMA": 0x2B, "DOT": 0x2F, "SLASH": 0x2C,
}


def _build_table(position_to_native, offset=0):
    return {native + offset: _POSITION_TO_ITALIAN_KEY[pos] for pos, native in position_to_native.items()}


_scancode_table_cache = None
# Piattaforma delle tavole (i test la cambiano per provarle tutte).
_PLATFORM = sys.platform


def native_key_code(event):
    """Il codice nativo della posizione fisica del tasto, o None se
    l'evento non ne ha. Su macOS Qt non fornisce lo scan code
    (nativeScanCode() vale 0 per ogni tasto): la posizione e' in
    nativeVirtualKey(), il keyCode di Cocoa (costanti kVK_*). Il tasto A vale
    pero' 0 come un evento sintetico senza dati nativi: lo si prende per
    buono solo se l'evento porta anche i modificatori nativi di Cocoa."""
    if _PLATFORM == "darwin":
        virtual = getattr(event, "nativeVirtualKey", None)
        code = virtual() if virtual else 0
        if code == 0:
            modifiers = getattr(event, "nativeModifiers", None)
            if not (modifiers and modifiers()):
                return None
        return code
    return event.nativeScanCode() or None


def _scancode_table():
    """Tavola scancode nativo -> Qt.Key canonico per la piattaforma corrente
    (costruita una sola volta, vedi sys.platform). Vuota su piattaforme non
    riconosciute: canonical_key() ricade allora sempre sul comportamento
    originale (invariato, legato al carattere)."""
    global _scancode_table_cache
    if _scancode_table_cache is None:
        if _PLATFORM.startswith("linux"):
            _scancode_table_cache = _build_table(_EVDEV, offset=_LINUX_X11_OFFSET)
        elif _PLATFORM.startswith("win"):
            _scancode_table_cache = _build_table(_WINDOWS)
        elif _PLATFORM == "darwin":
            _scancode_table_cache = _build_table(_MACOS)
        else:
            _scancode_table_cache = {}
    return _scancode_table_cache


def canonical_key(event):
    """Ritorna il Qt.Key 'canonico' (posizione fisica, layout italiano) del
    tasto che ha generato l'evento, se la sua posizione e' tra quelle
    coperte (vedi il modulo); altrimenti ritorna semplicemente event.key()
    invariato (comportamento originale, legato al carattere prodotto sotto
    il layout attivo) - sia per i tasti esecutivi (Ctrl/Alt/Maiusc/Tab/Bloc
    Maiusc/Spazio, gia' indipendenti dal layout di loro natura, mai nella
    tavola) sia per l'unico tasto-nota non coperto (vedi docstring del
    modulo)."""
    code = native_key_code(event)
    if code is None:
        return event.key()
    return _scancode_table().get(code, event.key())
