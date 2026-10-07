"""
Test GUI (PySide6, piattaforma offscreen) per il ciclo di vita della
riproduzione. Regressione coperta: MainWindow non aveva un closeEvent che
chiamasse playback.stop(), quindi il processo audio (fluidsynth e/o il
player WAV) restava orfano e continuava a suonare fino alla fine anche a
finestra chiusa.

Esecuzione:
    python3 -m pytest tests/test_gui_playback.py -v
oppure:
    python3 tests/test_gui_playback.py
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys
import stat
import shutil
import tempfile
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

from core import settings

_app = QApplication.instance() or QApplication([])


def test_editor_auto_converts_hyphen_to_flat_after_note_letter():
    """Digitare '-' subito dopo una lettera nota (a-g/A-G) deve sostituirlo
    automaticamente con '♭' nell'editor (comodita' di digitazione ASCII per
    il simbolo musicale di bemolle, vedi gui.voicing_picker.NotationEditor);
    un '-' che non segue una lettera nota a inizio token (es. dopo un'altra
    parola come 'snare') non deve invece essere toccato."""
    from gui.voicing_picker import NotationEditor

    editor = NotationEditor()

    QTest.keyClicks(editor, "e-")
    assert editor.toPlainText() == "e♭"

    editor.setPlainText("")
    QTest.keyClicks(editor, "4c-")
    assert editor.toPlainText() == "4c♭"

    editor.setPlainText("")
    QTest.keyClicks(editor, "B-7")
    assert editor.toPlainText() == "B♭7"

    editor.setPlainText("")
    QTest.keyClicks(editor, "c*4>e-*4")
    assert editor.toPlainText() == "c*4>e♭*4"

    editor.setPlainText("")
    QTest.keyClicks(editor, "snare-")
    assert editor.toPlainText() == "snare-"


def _make_fake_synth_env():
    """Crea un finto 'fluidsynth' che dorme (simula un rendering lento, come
    su un brano lungo/complesso) e un finto player che lascia una traccia se
    viene eseguito, per verificare che l'audio non parta mai dopo lo stop."""
    tmpdir = tempfile.mkdtemp()
    fakebin = os.path.join(tmpdir, "bin")
    os.makedirs(fakebin)
    marker_path = os.path.join(tmpdir, "player_was_called")

    fluidsynth_script = os.path.join(fakebin, "fluidsynth")
    with open(fluidsynth_script, "w") as f:
        f.write(
            "#!/bin/bash\n"
            "sleep 5\n"
            "for i in \"$@\"; do\n"
            "  if [ \"$prev\" = \"-F\" ]; then outfile=\"$i\"; fi\n"
            "  prev=\"$i\"\n"
            "done\n"
            "if [ -n \"$outfile\" ]; then printf 'RIFF' > \"$outfile\"; fi\n"
            "exit 0\n"
        )
    os.chmod(fluidsynth_script, os.stat(fluidsynth_script).st_mode | stat.S_IEXEC)

    player_script = os.path.join(fakebin, "paplay")
    with open(player_script, "w") as f:
        f.write(f"#!/bin/bash\ntouch {marker_path}\nexit 0\n")
    os.chmod(player_script, os.stat(player_script).st_mode | stat.S_IEXEC)

    fake_sf2 = os.path.join(tmpdir, "Fake.sf2")
    open(fake_sf2, "wb").close()
    return tmpdir, fakebin, fake_sf2, marker_path


@pytest.mark.skipif(sys.platform == "win32", reason="usa finti programmi bash (#!/bin/bash)")
def test_closing_main_window_stops_playback():
    from gui.main_window import MainWindow

    tmpdir, fakebin, fake_sf2, marker_path = _make_fake_synth_env()
    old_path = os.environ.get("PATH", "")
    os.environ["PATH"] = fakebin + os.pathsep + old_path
    try:
        settings.set_soundfont_path(fake_sf2)
        win = MainWindow()
        win.project.add_track("Piano1", "Piano", "16: c*4 e*4")
        win.refresh_mixer()
        win.play()
        time.sleep(0.3)
        assert win.playback.is_playing(), "il rendering simulato deve essere tracciato come 'in corso'"

        win.close()

        for _ in range(30):
            if not win.playback.is_playing():
                break
            time.sleep(0.1)
        assert not win.playback.is_playing(), "chiudere la finestra deve fermare la riproduzione"

        time.sleep(0.2)
        assert not os.path.exists(marker_path), "il player non deve mai partire se la finestra e' gia' stata chiusa"
    finally:
        os.environ["PATH"] = old_path
        settings.clear_soundfont_path()
        shutil.rmtree(tmpdir)


def test_double_click_opens_voicing_picker_for_chord_inside_group():
    """Un accordo (anche con moltiplicatore, es. '2C7') scritto dentro un
    gruppo N(...) deve essere riconosciuto da find_chord_token_at come se
    fosse a livello di traccia, con le posizioni carattere riportate al
    testo ORIGINALE (non a quello del solo contenuto del gruppo)."""
    from gui.voicing_picker import find_chord_token_at

    text = "4(2C7 2e c d 2A7)"
    info = find_chord_token_at(text, text.index("C7"), {}, default_octave=4)
    assert info is not None and info["kind"] == "implicit"
    assert text[info["char_start"]:info["char_end"]] == "2C7"
    assert info["chord"].symbol == "C7"

    # gruppi annidati
    nested = "2(c 2(Dm7 e))"
    info2 = find_chord_token_at(nested, nested.index("Dm7"), {}, default_octave=4)
    assert info2 is not None and info2["kind"] == "implicit"
    assert nested[info2["char_start"]:info2["char_end"]] == "Dm7"


def test_selection_snapping_and_ref_detection():
    from gui.selection_actions import snap_selection_to_tokens, _is_reusable_ref

    text = "16: 90@ c*4 e*4 %Riff g*4"
    # selezione che taglia i token a meta': si aggancia ai confini interi
    snap = snap_selection_to_tokens(text, text.index("c*4") + 1, text.index("g*4") + 1)
    assert snap == (text.index("c*4"), text.index("g*4") + 3, ["c*4", "e*4", "%Riff", "g*4"])
    assert any(_is_reusable_ref(t) for t in snap[2])

    # comando di stato finale scartato (non deve restare 'in sospeso')
    text2 = "c*4 e*4 16:"
    snap2 = snap_selection_to_tokens(text2, 0, len(text2))
    assert snap2 == (0, 7, ["c*4", "e*4"])

    # selezione senza alcun token sonoro: nessuno snap possibile
    assert snap_selection_to_tokens("16:", 0, 3) is None


def test_group_action_wraps_selection_in_parentheses():
    from gui.voicing_picker import NotationEditor
    from gui.selection_actions import snap_selection_to_tokens, _replace_range

    editor = NotationEditor()
    editor.setPlainText("c*4 e*4 g*4")
    char_start, char_end, _tokens = snap_selection_to_tokens(editor.toPlainText(), 4, 11)
    _replace_range(editor, char_start, char_end, f"({editor.toPlainText()[char_start:char_end]})")
    assert editor.toPlainText() == "c*4 (e*4 g*4)"


def test_pattern_action_creates_pattern_and_replaces_selection():
    from gui.voicing_picker import NotationEditor
    from gui import selection_actions as sa

    editor = NotationEditor()
    editor.setPlainText("c*4 e*4 g*4")
    patterns = {}
    char_start, char_end, _tokens = sa.snap_selection_to_tokens(editor.toPlainText(), 4, 11)
    selected = editor.toPlainText()[char_start:char_end]

    original_get_text = sa.QInputDialog.getText
    sa.QInputDialog.getText = staticmethod(lambda *a, **k: ("MioRiff", True))
    try:
        sa._transform_into_pattern(editor, patterns, char_start, char_end, selected)
    finally:
        sa.QInputDialog.getText = original_get_text

    assert editor.toPlainText() == "c*4 %MioRiff"
    assert "MioRiff" in patterns
    assert patterns["MioRiff"].tokens == ["e*4", "g*4"]


def test_pattern_action_rejects_invalid_name():
    from gui.voicing_picker import NotationEditor
    from gui import selection_actions as sa

    editor = NotationEditor()
    editor.setPlainText("c*4 e*4")
    patterns = {}

    original_get_text = sa.QInputDialog.getText
    original_warning = sa.QMessageBox.warning
    warned = []
    sa.QInputDialog.getText = staticmethod(lambda *a, **k: ("nome con spazi", True))
    sa.QMessageBox.warning = staticmethod(lambda *a, **k: warned.append(True))
    try:
        sa._transform_into_pattern(editor, patterns, 0, len(editor.toPlainText()), editor.toPlainText())
    finally:
        sa.QInputDialog.getText = original_get_text
        sa.QMessageBox.warning = original_warning

    assert warned, "un nome con spazi deve essere rifiutato con un avviso"
    assert not patterns
    assert editor.toPlainText() == "c*4 e*4"  # nessuna modifica in caso di nome non valido


def test_humanize_checkbox_persists_setting_and_is_safe_when_not_playing():
    """Il toggle deve salvare l'impostazione persistente e non deve
    sollevare quando la riproduzione non e' in corso (early-return in
    _on_mixer_changed, riusato per il riavvio a caldo)."""
    from gui.main_window import MainWindow
    from core import settings

    original = settings.get_humanize_enabled()
    win = MainWindow()
    try:
        win.humanize_checkbox.setChecked(True)
        assert settings.get_humanize_enabled() is True
        win.humanize_checkbox.setChecked(False)
        assert settings.get_humanize_enabled() is False
    finally:
        settings.set_humanize_enabled(original)


def test_humanize_settings_dialog_reflects_and_updates_amount():
    from gui.main_window import MainWindow
    from gui.humanize_dialog import HumanizeSettingsDialog
    from core import settings

    original = settings.get_humanize_amount()
    win = MainWindow()
    try:
        settings.set_humanize_amount(30)
        dlg = HumanizeSettingsDialog(win)
        assert dlg.amount_slider.value() == 30

        dlg.amount_slider.setValue(80)
        assert settings.get_humanize_amount() == 80
        assert dlg.amount_value_label.text() == "80%"
    finally:
        settings.set_humanize_amount(original)


def test_selecting_a_boxed_track_does_not_force_window_wider():
    """Regressione: track_title (nome traccia + strumento) non aveva
    word-wrap, quindi il suffisso "vista Struttura brano attiva: ..."
    mostrato per una traccia con box (select_track) lo rendeva cosi' lungo
    da far crescere il minimumSizeHint della finestra oltre la sua
    larghezza corrente - Qt/il window manager erano allora costretti a
    ridimensionarla (osservato sempre dopo un import MIDI, che porta le
    tracce importate in modalita' box), con l'effetto collaterale di
    perdere il doppio click sulla barra del titolo su alcuni window
    manager."""
    from gui.main_window import MainWindow
    from core.model import Clip

    win = MainWindow()
    try:
        assert win.track_title.wordWrap() is True

        width_before = win.minimumSizeHint().width()
        track = win.project.add_track("Piano1", "Piano", "16: c*4 e*4 g*4")
        track.clips = [Clip(name="Piano1 1", text=track.text, start_beat=0.0)]
        win.refresh_mixer()
        win.select_track("Piano1")
        assert "vista Struttura brano attiva" in win.track_title.text()

        assert win.minimumSizeHint().width() <= max(width_before, 900), (
            "selezionare una traccia con box non deve far crescere il minimo "
            "della finestra oltre la larghezza iniziale"
        )
    finally:
        win.close()


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
