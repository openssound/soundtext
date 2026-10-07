"""
Test per gui.keyboard_scancodes.canonical_key(): la mappa tastiera del
dialogo "Suona con la tastiera" deve restare ancorata alla POSIZIONE fisica
del tasto premuto, non al carattere che produce sotto il layout di sistema
attivo (che puo' cambiare lingua senza che l'utente tocchi la tastiera).

Esecuzione:
    python3 -m pytest tests/test_keyboard_scancodes.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from core.model import Project
from gui.keyboard_play_dialog import KeyboardPlayDialog
from gui.keyboard_scancodes import canonical_key, _EVDEV, _LINUX_X11_OFFSET, _POSITION_TO_ITALIAN_KEY

_app = QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _linux_tables(monkeypatch):
    """Questi test usano i codici di Linux (evdev + 8): le tavole sono quelle
    di Linux su qualunque sistema giri la suite (le altre sono provate a
    parte, vedi test_keyboard_scancodes.py)."""
    from gui import keyboard_scancodes
    monkeypatch.setattr(keyboard_scancodes, "_PLATFORM", "linux")
    monkeypatch.setattr(keyboard_scancodes, "_scancode_table_cache", None)


class _FakeKeyEvent:
    def __init__(self, key, native_scan_code=0):
        self._key = key
        self._native_scan_code = native_scan_code

    def key(self):
        return self._key

    def nativeScanCode(self):
        return self._native_scan_code


def test_all_covered_positions_resolve_to_italian_key_regardless_of_reported_key():
    # key() e' deliberatamente "sbagliata" (un valore che non corrisponde a
    # nessun tasto reale): deve essere completamente ignorata quando lo
    # scancode nativo e' tra quelli coperti - solo la POSIZIONE conta.
    for pos, evdev_code in _EVDEV.items():
        scancode = evdev_code + _LINUX_X11_OFFSET
        event = _FakeKeyEvent(key=999999, native_scan_code=scancode)
        assert canonical_key(event) == _POSITION_TO_ITALIAN_KEY[pos], f"posizione '{pos}' non risolta correttamente"


def test_uncovered_scancode_falls_back_to_key():
    # Uno scancode fuori tavola (es. Esc) deve ricadere sul comportamento
    # originale, legato al carattere/key() riportato dall'evento.
    event = _FakeKeyEvent(key=Qt.Key_Escape, native_scan_code=1 + _LINUX_X11_OFFSET)
    assert canonical_key(event) == Qt.Key_Escape


def test_zero_scancode_falls_back_to_key():
    # Molte librerie/ambienti di test emettono nativeScanCode()==0 quando
    # l'evento e' sintetico: deve comunque ricadere su key(), mai risolversi
    # per sbaglio a una nota (0 non e' mai una voce valida della tavola).
    event = _FakeKeyEvent(key=Qt.Key_Q, native_scan_code=0)
    assert canonical_key(event) == Qt.Key_Q


def test_executive_keys_are_never_intercepted_by_the_scancode_table():
    # Ctrl/Alt/Maiusc/Tab/Bloc Maiusc/Spazio non sono "caratteri": la loro
    # posizione fisica e' gia' indipendente dal layout di per se', quindi non
    # devono mai passare per la tavola (che copre solo le note e la fila
    # qualita'). Qui li si preme con uno scancode di note reale (di
    # proposito, per verificare che canonical_key() NON li confonda con una
    # nota solo perche' capitano su quello scancode in un ambiente sintetico):
    # la funzione deve comunque ritornare key() invariato per questi tasti.
    for k in (Qt.Key_CapsLock, Qt.Key_Alt, Qt.Key_Shift, Qt.Key_Control, Qt.Key_Tab, Qt.Key_Space):
        event = _FakeKeyEvent(key=k, native_scan_code=0)  # scancode reale di questi tasti non e' nella tavola note
        assert canonical_key(event) == k


def _make_dialog():
    p = Project(name="Test")
    p.add_track("Piano1", "Piano", "")
    dlg = KeyboardPlayDialog(None, project=p, instrument_name="Piano", context_label="test")
    dlg._instrument_active = lambda: True
    return dlg


def test_dialog_plays_same_note_regardless_of_simulated_layout():
    """Simula il cambio di lingua della tastiera: lo stesso tasto FISICO
    (riga numerica, 2a posizione da sinistra) produce Qt.Key_2 sotto layout
    italiano ma, per esempio, un carattere diverso sotto un altro layout -
    qui simulato passando un Qt.Key deliberatamente 'sbagliato' come key(),
    ma il vero scancode nativo di quella posizione. Il dialogo deve suonare
    comunque la stessa nota (re, seconda posizione della riga numerica)."""
    dlg = _make_dialog()
    position_2_scancode = _EVDEV["2"] + _LINUX_X11_OFFSET

    # "Sotto layout italiano": key() coerente con la posizione.
    dlg._on_surface_key_press(_FakeKeyEvent(key=Qt.Key_2, native_scan_code=position_2_scancode))
    note_it = dlg._active_notes[Qt.Key_2]["midi_notes"]
    dlg._on_surface_key_release(_FakeKeyEvent(key=Qt.Key_2, native_scan_code=position_2_scancode))

    # "Sotto un altro layout": stessa posizione fisica, key() diversa/estranea.
    dlg._on_surface_key_press(_FakeKeyEvent(key=Qt.Key_QuoteDbl, native_scan_code=position_2_scancode))
    note_other = dlg._active_notes[Qt.Key_2]["midi_notes"]  # risolta comunque a Qt.Key_2, la chiave canonica
    dlg._on_surface_key_release(_FakeKeyEvent(key=Qt.Key_QuoteDbl, native_scan_code=position_2_scancode))

    assert note_it == note_other


def test_quality_row_position_also_language_independent():
    """La fila qualita' (Z X C V B N M , . /) deve godere della stessa
    indipendenza dalla lingua: qui la posizione di 'Z' (maggiore) tenuta
    insieme alla posizione '1' della riga numerica, con key() estranee su
    entrambe, deve comunque produrre un accordo maggiore."""
    dlg = _make_dialog()
    z_scancode = _EVDEV["Z"] + _LINUX_X11_OFFSET
    pos1_scancode = _EVDEV["1"] + _LINUX_X11_OFFSET

    dlg._on_surface_key_press(_FakeKeyEvent(key=12345, native_scan_code=z_scancode))
    dlg._on_surface_key_press(_FakeKeyEvent(key=54321, native_scan_code=pos1_scancode))
    notes = sorted(dlg._active_notes[Qt.Key_1]["midi_notes"])
    assert sorted(n - notes[0] for n in notes) == [0, 4, 7]  # struttura maggiore
    dlg._on_surface_key_release(_FakeKeyEvent(key=54321, native_scan_code=pos1_scancode))
    dlg._on_surface_key_release(_FakeKeyEvent(key=12345, native_scan_code=z_scancode))


def test_enter_plays_same_note_as_ugrave_in_every_layout_mode():
    """Ripiego per l'unico tasto non coperto dalla tavola scancode ('ù',
    posizione fisica ambigua sui layout ISO europei, vedi il modulo): Invio
    (principale e del tastierino numerico) suona sempre la stessa nota,
    qualunque sia il layout attivo - Invio non e' un tasto-carattere, la sua
    posizione fisica e' gia' di per se' indipendente dal layout."""
    from gui.keyboard_note_map import build_note_key_map, build_scale_key_map, build_janko_key_map

    for note_key_map in (
        build_note_key_map(4),
        build_scale_key_map(4, "C", "diatonica"),
        build_janko_key_map(4),
    ):
        assert note_key_map[Qt.Key_Return] == note_key_map[Qt.Key_Ugrave]
        assert note_key_map[Qt.Key_Enter] == note_key_map[Qt.Key_Ugrave]

    dlg = _make_dialog()
    dlg._on_surface_key_press(_FakeKeyEvent(key=Qt.Key_Ugrave, native_scan_code=0))
    via_ugrave = dlg._active_notes[Qt.Key_Ugrave]["midi_notes"]
    dlg._on_surface_key_release(_FakeKeyEvent(key=Qt.Key_Ugrave, native_scan_code=0))

    dlg._on_surface_key_press(_FakeKeyEvent(key=Qt.Key_Return, native_scan_code=0))
    via_enter = dlg._active_notes[Qt.Key_Return]["midi_notes"]
    dlg._on_surface_key_release(_FakeKeyEvent(key=Qt.Key_Return, native_scan_code=0))

    assert via_ugrave == via_enter


if __name__ == "__main__":
    import inspect
    here = sys.modules[__name__]
    tests = [f for name, f in inspect.getmembers(here) if name.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        passed += 1
        print(f"OK  {t.__name__}")
    print(f"\n{passed}/{len(tests)} test superati.")


class _FakeMacKeyEvent:
    """Un evento come lo manda Qt su macOS: nativeScanCode() sempre 0, la
    posizione in nativeVirtualKey() (kVK_*), modificatori nativi di Cocoa."""

    def __init__(self, key, virtual_key, native_modifiers=0x100):
        self._key, self._virtual, self._mods = key, virtual_key, native_modifiers

    def key(self):
        return self._key

    def nativeScanCode(self):
        return 0

    def nativeVirtualKey(self):
        return self._virtual

    def nativeModifiers(self):
        return self._mods


def _use_platform(monkeypatch, platform):
    from gui import keyboard_scancodes
    monkeypatch.setattr(keyboard_scancodes, "_PLATFORM", platform)
    monkeypatch.setattr(keyboard_scancodes, "_scancode_table_cache", None)


def test_macos_uses_the_virtual_key_code(monkeypatch):
    from gui.keyboard_scancodes import _MACOS
    _use_platform(monkeypatch, "darwin")
    for pos, vk in _MACOS.items():
        # layout francese (AZERTY): il tasto in posizione Q scrive 'a'
        event = _FakeMacKeyEvent(key=999999, virtual_key=vk)
        assert canonical_key(event) == _POSITION_TO_ITALIAN_KEY[pos], pos
    assert canonical_key(_FakeMacKeyEvent(key=Qt.Key_A, virtual_key=0x0C)) == Qt.Key_Q


def test_macos_zero_is_key_a_only_for_real_events(monkeypatch):
    _use_platform(monkeypatch, "darwin")
    assert canonical_key(_FakeMacKeyEvent(key=Qt.Key_Q, virtual_key=0)) == Qt.Key_A      # kVK_ANSI_A
    synthetic = _FakeMacKeyEvent(key=Qt.Key_Q, virtual_key=0, native_modifiers=0)
    assert canonical_key(synthetic) == Qt.Key_Q          # nessun dato nativo: vale il carattere
    assert canonical_key(_FakeKeyEvent(key=Qt.Key_Z)) == Qt.Key_Z   # evento senza nativeVirtualKey


def test_windows_uses_the_scan_code(monkeypatch):
    from gui.keyboard_scancodes import _WINDOWS
    _use_platform(monkeypatch, "win32")
    for pos, sc in _WINDOWS.items():
        assert canonical_key(_FakeKeyEvent(key=999999, native_scan_code=sc)) == _POSITION_TO_ITALIAN_KEY[pos], pos
    assert canonical_key(_FakeKeyEvent(key=Qt.Key_Q, native_scan_code=0)) == Qt.Key_Q
