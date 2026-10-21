"""
Test GUI (PySide6, offscreen) delle tracce audio (fase 1): creazione dal
mixer, box con forma d'onda nella vista Struttura brano, importazione di un
file come clip, menu dedicati e azioni sulla notazione rifiutate.

Esecuzione:
    python3 -m pytest tests/test_audio_tracks_gui.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QFileDialog, QInputDialog, QMessageBox

from core import audio_tracks
from core.audio_tracks import AUDIO_SAMPLE_RATE, write_wav
from core.model import AudioClip, Clip
from gui.arrangement_view import AudioBoxItem, BoxItem
from gui.main_window import MainWindow

_app = QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _isolated_staging(tmp_path, monkeypatch):
    staging = tmp_path / "staging"
    staging.mkdir()
    monkeypatch.setattr(audio_tracks, "staging_audio_dir", lambda: str(staging))


def _wav(path, seconds=1.0):
    t = np.arange(int(seconds * AUDIO_SAMPLE_RATE)) / AUDIO_SAMPLE_RATE
    write_wav(str(path), (0.5 * np.sin(2 * np.pi * 220 * t)).reshape(-1, 1).astype(np.float32),
              AUDIO_SAMPLE_RATE, bits=16)
    return str(path)


def _window():
    w = MainWindow()
    w.resize(1000, 650)
    w.show()
    w.arrangement_action.setChecked(True)
    _app.processEvents()
    return w


def _menu_actions(open_menu_fn):
    captured = {}

    def check_and_close():
        menu = QApplication.activePopupWidget()
        if menu is not None:
            captured["actions"] = [a.text() for a in menu.actions() if a.text()]
            menu.close()

    QTimer.singleShot(50, check_and_close)
    open_menu_fn()
    return captured.get("actions", [])


def test_add_audio_track_from_mixer(monkeypatch):
    w = _window()
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("Voce", True)))
    w.add_audio_track()
    track = w.project.get_track("Voce")
    assert track.is_audio
    assert w.current_track_name == "Voce"
    assert w.editor.isReadOnly()
    assert "traccia audio" in w.track_title.text()
    assert w.track_headers["Voce"].instr_label.text() == "Audio"


def test_import_audio_clip_creates_waveform_box_and_undo_removes_it(tmp_path, monkeypatch):
    w = _window()
    w.project.add_audio_track("Chitarra")
    w.history.reset(w.project)
    w.refresh_mixer()
    src = _wav(tmp_path / "riff.wav", seconds=2.0)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (src, "")))
    w.arrangement_view.import_audio_clip("Chitarra", 4.0)
    _app.processEvents()
    _app.processEvents()

    [clip] = w.project.get_track("Chitarra").audio_clips
    assert clip.name == "riff" and clip.start_beat == 4.0
    assert os.path.dirname(clip.file) == str(tmp_path / "staging")
    items = [it for it in w.arrangement_view.canvas._scene.items() if isinstance(it, AudioBoxItem)]
    assert len(items) == 1
    assert items[0].rect().width() == pytest.approx(4.0 * 24)   # 2 s a 120 BPM = 4 beat
    w.arrangement_view.canvas.viewport().grab()   # disegna la forma d'onda senza errori

    w.undo()
    assert w.project.get_track("Chitarra").audio_clips == []


def test_second_import_goes_after_the_first_instead_of_overlapping(tmp_path, monkeypatch):
    w = _window()
    w.project.add_audio_track("Voce")
    w.refresh_mixer()
    src = _wav(tmp_path / "take.wav", seconds=2.0)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (src, "")))
    w.arrangement_view.import_audio_clip("Voce", 0.0)
    w.arrangement_view.import_audio_clip("Voce", 1.0)
    starts = sorted(c.start_beat for c in w.project.get_track("Voce").audio_clips)
    assert starts == [0.0, 4.0]


def test_audio_menus_offer_audio_actions_only(tmp_path):
    w = _window()
    t = w.project.add_audio_track("Voce")
    t.audio_clips.append(AudioClip("Strofa", _wav(tmp_path / "s.wav"), 0.0))
    w.refresh_mixer()
    view = w.arrangement_view
    pos = w.mapToGlobal(w.rect().center())

    empty = _menu_actions(lambda: view.show_empty_menu("Voce", 8.0, pos))
    assert "Importa file audio qui..." in empty
    assert not any("box" in a.lower() or "genera" in a.lower() for a in empty)

    header = _menu_actions(lambda: view.show_track_menu("Voce", pos))
    assert "Importa file audio..." in header and not any("MIDI" in a for a in header)
    assert "Esporta WAV (solo questa)..." in header

    item = next(it for it in view.canvas._scene.items() if isinstance(it, AudioBoxItem))
    box = _menu_actions(lambda: view.show_box_menu(item, pos))
    assert "Guadagno clip (dB)..." in box
    # Trasponi c'e' anche per le clip audio (senza cambiare la velocita')
    assert "Trasponi..." in box and "Ritrova file..." not in box
    assert "Suona al contrario" in box and "Inverti la fase" in box


def test_missing_file_box_offers_relink(tmp_path, monkeypatch):
    w = _window()
    t = w.project.add_audio_track("Voce")
    t.audio_clips.append(AudioClip("Persa", str(tmp_path / "manca.wav"), 0.0))
    w.refresh_mixer()
    view = w.arrangement_view
    item = next(it for it in view.canvas._scene.items() if isinstance(it, AudioBoxItem))
    assert "MANCANTE" in item.toolTip()
    actions = _menu_actions(lambda: view.show_box_menu(item, w.mapToGlobal(w.rect().center())))
    assert "Ritrova file..." in actions

    src = _wav(tmp_path / "ritrovata.wav")
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (src, "")))
    view._relink_clip("Voce", t.audio_clips[0])
    assert not audio_tracks.clip_is_missing(t.audio_clips[0])


def test_clipboard_does_not_mix_audio_clips_and_notation_boxes(tmp_path):
    w = _window()
    w.project.add_track("Piano", "Piano", "")
    w.project.get_track("Piano").clips.append(Clip(name="A", text="c*4", start_beat=0.0))
    audio = w.project.add_audio_track("Voce")
    audio.audio_clips.append(AudioClip("S", _wav(tmp_path / "s.wav"), 0.0))
    w.refresh_mixer()
    view = w.arrangement_view

    view._clipboard = AudioClip("S", audio.audio_clips[0].file, 0.0)
    view.paste_at("Piano", 8.0)
    assert len(w.project.get_track("Piano").clips) == 1
    view.paste_at("Voce", 8.0)
    assert [c.start_beat for c in audio.audio_clips] == [0.0, 8.0]

    view._clipboard = Clip(name="A", text="c*4", start_beat=0.0)
    view.paste_at("Voce", 16.0)
    assert len(audio.audio_clips) == 2


def test_notation_actions_are_refused_on_audio_tracks(monkeypatch):
    w = _window()
    w.project.add_audio_track("Voce")
    w.refresh_mixer()
    w.select_track("Voce")
    shown = []
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: shown.append(a[1])))
    for action in (w.export_selected_track_midi, w.play_keyboard_into_selected_track,
                   w.generate_drums_into_selected_track, w.generate_progression_into_selected_track,
                   w.freeze_chords):
        action()
    assert shown == ["Traccia audio"] * 5


def test_rename_audio_track_keeps_it_audio(monkeypatch):
    w = _window()
    w.project.add_audio_track("Voce")
    w.refresh_mixer()
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("Voce solista", True)))
    w._open_edit_dialog_for("Voce")
    assert w.project.get_track("Voce solista").is_audio


def test_notation_boxes_still_work_next_to_audio_tracks(tmp_path):
    w = _window()
    w.project.add_track("Piano", "Piano", "")
    w.project.get_track("Piano").clips.append(Clip(name="A", text="c*4", start_beat=0.0))
    audio = w.project.add_audio_track("Voce")
    audio.audio_clips.append(AudioClip("S", _wav(tmp_path / "s.wav"), 0.0))
    w.refresh_mixer()
    items = w.arrangement_view.canvas._scene.items()
    assert sum(isinstance(it, AudioBoxItem) for it in items) == 1
    assert sum(isinstance(it, BoxItem) and not isinstance(it, AudioBoxItem) for it in items) == 1


def test_dragging_an_audio_box_moves_the_clip_and_can_be_undone(tmp_path):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    w = _window()
    t = w.project.add_audio_track("Voce")
    clip = AudioClip("S", _wav(tmp_path / "s.wav"), 0.0)
    t.audio_clips.append(clip)
    w.history.reset(w.project)
    w.refresh_mixer()
    _app.processEvents()
    canvas = w.arrangement_view.canvas
    item = next(it for it in canvas._scene.items() if isinstance(it, AudioBoxItem))
    start = canvas.mapFromScene(item.sceneBoundingRect().center())
    end = start + type(start)(96, 0)   # ~4 beat
    QTest.mousePress(canvas.viewport(), Qt.LeftButton, Qt.NoModifier, start)
    QTest.mouseMove(canvas.viewport(), end)
    QTest.mouseRelease(canvas.viewport(), Qt.LeftButton, Qt.NoModifier, end)
    _app.processEvents()
    assert clip.start_beat == 4.0
    w.undo()
    assert w.project.get_track("Voce").audio_clips[0].start_beat == 0.0


def test_tempo_change_resizes_audio_boxes(tmp_path):
    w = _window()
    t = w.project.add_audio_track("Voce")
    t.audio_clips.append(AudioClip("S", _wav(tmp_path / "s.wav", seconds=2.0), 0.0))
    w.refresh_mixer()

    def width():
        item = next(it for it in w.arrangement_view.canvas._scene.items() if isinstance(it, AudioBoxItem))
        return item.rect().width()

    assert width() == pytest.approx(4 * 24)     # 2 s a 120 BPM
    w.tempo_spin.setValue(60)
    assert width() == pytest.approx(2 * 24)     # 2 s a 60 BPM


# --------------------------------------------------------------- fase 3: taglio, divisione, conversione

def _window_with_clip(tmp_path, seconds=2.0, start_beat=4.0):
    w = _window()
    t = w.project.add_audio_track("Voce")
    clip = AudioClip("S", _wav(tmp_path / "s.wav", seconds=seconds), start_beat)
    t.audio_clips.append(clip)
    w.history.reset(w.project)
    w.refresh_mixer()
    _app.processEvents()
    item = next(it for it in w.arrangement_view.canvas._scene.items() if isinstance(it, AudioBoxItem))
    return w, t, clip, item


def _drag(canvas, start, end):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    QTest.mousePress(canvas.viewport(), Qt.LeftButton, Qt.NoModifier, start)
    QTest.mouseMove(canvas.viewport(), end)
    QTest.mouseRelease(canvas.viewport(), Qt.LeftButton, Qt.NoModifier, end)
    _app.processEvents()


def test_dragging_the_left_edge_trims_the_start_keeping_audio_in_place(tmp_path):
    w, t, clip, item = _window_with_clip(tmp_path)
    canvas = w.arrangement_view.canvas
    rect = item.sceneBoundingRect()
    start = canvas.mapFromScene(rect.left() + 2, rect.center().y())
    _drag(canvas, start, start + type(start)(24, 0))            # +1 beat
    assert (clip.start_beat, clip.trim_start) == (5.0, 0.5)
    assert w.history.can_undo()
    w.undo()
    restored = w.project.get_track("Voce").audio_clips[0]
    assert (restored.start_beat, restored.trim_start) == (4.0, 0.0)


def test_dragging_the_right_edge_trims_the_end(tmp_path):
    w, t, clip, item = _window_with_clip(tmp_path)
    canvas = w.arrangement_view.canvas
    rect = item.sceneBoundingRect()
    start = canvas.mapFromScene(rect.right() - 2, rect.center().y())
    _drag(canvas, start, start - type(start)(48, 0))            # -2 beat = -1 s
    assert clip.start_beat == 4.0 and clip.trim_end == pytest.approx(1.0)
    item = next(it for it in canvas._scene.items() if isinstance(it, AudioBoxItem))
    assert item.rect().width() == pytest.approx(2 * 24)


def test_split_and_precise_trim_from_the_box_menu(tmp_path):
    w, t, clip, item = _window_with_clip(tmp_path)
    view = w.arrangement_view
    actions = _menu_actions(lambda: view._show_audio_box_menu("Voce", clip, w.mapToGlobal(w.rect().center()), 6.0))
    assert "Dividi qui (beat 6)" in actions
    assert "Taglio preciso (secondi)..." in actions and "Converti in notazione..." in actions
    view._split_clip("Voce", clip, 6.0)
    assert sorted((c.start_beat, c.trim_start, c.trim_end) for c in t.audio_clips) == \
        [(4.0, 0.0, 1.0), (6.0, 1.0, 0.0)]

    view._apply_clip_trim("Voce", clip, 0.25, 0.5)
    assert (clip.start_beat, clip.trim_start, clip.trim_end) == (4.5, 0.25, 0.5)


def test_convert_clip_to_notation_creates_a_new_track_aligned_with_the_clip(tmp_path, monkeypatch):
    import gui.arrangement_audio as av
    w, t, clip, item = _window_with_clip(tmp_path)
    t.input_profile = "chitarra"
    seen = {}

    class FakeImport:
        Accepted = 1

        def __init__(self, parent, project, instrument_name, context_label):
            seen["instrument"] = instrument_name

        def _set_source(self, path):
            from core.audio_tracks import read_wav_info
            seen["seconds"] = read_wav_info(path).seconds

        def exec(self):
            return 1

        def result_text(self):
            return "4: e g a b"

    monkeypatch.setattr(av, "AudioImportDialog", FakeImport)
    monkeypatch.setattr(QInputDialog, "getItem", staticmethod(lambda *a, **k: (a[3][a[4]], True)))
    clip.trim_end = 0.5
    w.arrangement_view._convert_clip_to_notation("Voce", clip)
    assert seen == {"instrument": "Guitar", "seconds": pytest.approx(1.5)}
    new = w.project.get_track("S (note)")
    assert new.instrument_name == "Guitar"
    assert [(c.start_beat, c.text) for c in new.clips] == [(4.0, "4: e g a b")]


def test_note_track_menu_offers_midi_and_wav_export():
    w = _window()
    w.project.add_track("Piano", "Piano", "4: c d e f")
    w.refresh_mixer()
    header = _menu_actions(lambda: w.arrangement_view.show_track_menu("Piano", w.mapToGlobal(w.rect().center())))
    assert "Esporta MIDI (solo questa)..." in header
    assert "Esporta WAV (solo questa)..." in header


def test_export_track_wav_renders_only_that_track(tmp_path, monkeypatch):
    from core import playback
    monkeypatch.setattr(playback, "_shared_synth", None)
    w = _window()
    w.current_path = str(tmp_path / "Brano.st")
    gtr = w.project.add_audio_track("Chitarra")
    gtr.audio_clips.append(AudioClip("Riff", _wav(tmp_path / "g.wav", 1.0), 0.0))
    voice = w.project.add_audio_track("Voce")
    voice.audio_clips.append(AudioClip("Strofa", _wav(tmp_path / "v.wav", 1.0), 8.0))
    proposed = {}

    def fake_dialog(_parent, _caption, directory, *a, **k):
        proposed["path"] = directory
        return str(tmp_path / "out"), ""

    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(fake_dialog))
    w.export_track_wav("Chitarra")
    w._export_wav_worker.wait()
    _app.processEvents()
    assert proposed["path"] == str(tmp_path / "Chitarra.wav")
    from core.audio_tracks import read_wav_info
    assert read_wav_info(str(tmp_path / "out.wav")).seconds == pytest.approx(1.0, abs=0.001)


# --------------------------------------------------------------- dissolvenze, slip, normalizza, silenzia

def test_dragging_the_fade_handles_sets_the_fades_and_can_be_undone(tmp_path):
    w, t, clip, item = _window_with_clip(tmp_path)              # 2 s a 120 BPM = 96 px
    canvas = w.arrangement_view.canvas
    rect = item.sceneBoundingRect()
    start = canvas.mapFromScene(rect.left() + 1, rect.top() + 3)
    _drag(canvas, start, start + type(start)(24, 0))            # 24 px = 0,5 s
    assert clip.fade_in == pytest.approx(0.5, abs=0.03)
    assert (clip.start_beat, clip.trim_start) == (4.0, 0.0)     # non e' un taglio
    item = next(it for it in canvas._scene.items() if isinstance(it, AudioBoxItem))
    rect = item.sceneBoundingRect()
    start = canvas.mapFromScene(rect.right() - 1, rect.top() + 3)
    _drag(canvas, start, start - type(start)(48, 0))
    assert clip.fade_out == pytest.approx(1.0, abs=0.03)
    assert clip.trim_end == 0.0
    w.undo()
    w.undo()
    restored = w.project.get_track("Voce").audio_clips[0]
    assert (restored.fade_in, restored.fade_out) == (0.0, 0.0)


def test_alt_drag_slips_the_content_inside_the_clip(tmp_path):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    w, t, clip, item = _window_with_clip(tmp_path)
    clip.trim_start, clip.trim_end = 0.5, 0.5
    w.refresh_mixer()
    _app.processEvents()
    canvas = w.arrangement_view.canvas
    item = next(it for it in canvas._scene.items() if isinstance(it, AudioBoxItem))
    start = canvas.mapFromScene(item.sceneBoundingRect().center())
    end = start + type(start)(12, 0)                            # 12 px = 0,25 s
    QTest.mousePress(canvas.viewport(), Qt.LeftButton, Qt.AltModifier, start)
    QTest.mouseMove(canvas.viewport(), end)
    QTest.mouseRelease(canvas.viewport(), Qt.LeftButton, Qt.AltModifier, end)
    _app.processEvents()
    assert clip.start_beat == 4.0
    assert (clip.trim_start, clip.trim_end) == (pytest.approx(0.25, abs=0.03), pytest.approx(0.75, abs=0.03))
    assert w.history.can_undo()


def test_box_menu_offers_fades_normalize_and_mute(tmp_path):
    w, t, clip, item = _window_with_clip(tmp_path)
    view = w.arrangement_view
    actions = _menu_actions(lambda: view._show_audio_box_menu("Voce", clip, w.mapToGlobal(w.rect().center())))
    assert {"Normalizza (picco a −1 dB)", "Dissolvenze...", "Silenzia clip"} <= set(actions)

    view._normalize_clip("Voce", clip)                           # seno a 0,5 di picco
    assert clip.gain_db == pytest.approx(-1.0 - 20 * np.log10(0.5), abs=0.05)

    view._apply_clip_fades("Voce", clip, 0.5, 5.0, "equal")      # l'uscita non supera il resto
    assert (clip.fade_in, clip.fade_out, clip.fade_shape) == (0.5, 1.5, "equal")


def test_fade_dialog_applies_the_values(tmp_path):
    from PySide6.QtWidgets import QComboBox, QDoubleSpinBox
    w, t, clip, item = _window_with_clip(tmp_path)
    view = w.arrangement_view

    def fill():
        dlg = view._fade_dialog
        spins = dlg.findChildren(QDoubleSpinBox)
        spins[0].setValue(0.2)
        spins[1].setValue(0.3)
        combo = dlg.findChildren(QComboBox)[0]
        combo.setCurrentIndex(combo.findData("equal"))
        dlg.accept()

    QTimer.singleShot(50, fill)
    view._edit_clip_fades("Voce", clip)
    assert (clip.fade_in, clip.fade_out, clip.fade_shape) == (0.2, 0.3, "equal")


def test_muted_clip_is_drawn_grey_and_labelled(tmp_path):
    from gui.arrangement_view import MUTED_CLIP_COLOR
    w, t, clip, item = _window_with_clip(tmp_path)
    clip.muted = True
    w.arrangement_view.on_clip_changed("Voce")
    _app.processEvents()
    item = next(it for it in w.arrangement_view.canvas._scene.items() if isinstance(it, AudioBoxItem))
    assert item.brush().color().name() == MUTED_CLIP_COLOR
    assert "silenziata" in item.toolTip()
    w.undo()
    assert not w.project.get_track("Voce").audio_clips[0].muted


# --------------------------------------------------------------- traccia audio -> notazione, accordi dall'audio

def _chord_clip_window(tmp_path):
    from core.audio_tracks import import_audio_file
    from test_audio_chords import RATE, _hz, _tone_mix
    x = np.concatenate([_tone_mix([_hz(m) for m in chord], 2.0)
                        for chord in [(48, 64, 67), (45, 60, 64), (41, 60, 65), (43, 59, 62)]])
    src = str(tmp_path / "giro.wav")
    write_wav(src, x[:, None], RATE, bits=16)
    w = _window()
    t = w.project.add_audio_track("Chitarra")
    path = import_audio_file(src, audio_tracks.staging_audio_dir())
    t.audio_clips += [AudioClip("Strofa", path, 8.0), AudioClip("Ritornello", path, 32.0)]
    w.history.reset(w.project)
    w.refresh_mixer()
    _app.processEvents()
    return w, t


def _run_track_conversion(w, track_name, setup):
    """Lancia la conversione con le scelte fatte da setup(dialogo) e aspetta la fine."""
    from gui.audio_track_convert_dialog import AudioTrackConvertDialog
    view = w.arrangement_view

    def fake_exec(dlg):
        setup(dlg)
        return AudioTrackConvertDialog.Accepted

    original = AudioTrackConvertDialog.exec
    AudioTrackConvertDialog.exec = fake_exec
    try:
        view.convert_track_to_notation(track_name)
    finally:
        AudioTrackConvertDialog.exec = original
    worker = view._track_convert_worker
    worker.wait()
    for _ in range(50):
        _app.processEvents()
        if view._track_convert_worker is None:
            break


def _chords_mode(dlg):
    dlg.mode_combo.setCurrentIndex(dlg.mode_combo.findData("chords"))


def test_audio_track_menu_offers_the_track_conversion(tmp_path):
    w, t = _chord_clip_window(tmp_path)
    actions = _menu_actions(lambda: w.arrangement_view.show_track_menu("Chitarra", w.mapToGlobal(w.rect().center())))
    assert "Converti la traccia in notazione..." in actions


def test_convert_track_into_one_new_note_track_and_undo(tmp_path):
    w, t = _chord_clip_window(tmp_path)
    _run_track_conversion(w, "Chitarra", _chords_mode)
    notes = w.project.get_track("Chitarra (note)")
    assert notes.instrument_name == "Piano"
    assert [(c.name, c.start_beat) for c in notes.clips] == [("Strofa", 8.0), ("Ritornello", 32.0)]
    assert notes.clips[0].text.startswith("4: 4C | 4Am | 4F | 4G")
    assert len(w.project.get_track("Chitarra").audio_clips) == 2          # l'audio resta
    w.undo()
    assert w.project.find_track("Chitarra (note)") is None


def test_convert_track_into_an_existing_track_uses_free_slots(tmp_path):
    w, t = _chord_clip_window(tmp_path)
    keys = w.project.add_track("Tastiera", "Piano", "")
    keys.clips = [Clip(name="Intro", text="4: c d e f | g a b c*5", start_beat=6.0)]   # 6-14: sopra la Strofa
    w.refresh_mixer()
    _app.processEvents()

    def existing(dlg):
        _chords_mode(dlg)
        dlg.existing_radio.setChecked(True)
        dlg.target_combo.setCurrentText("Tastiera")

    _run_track_conversion(w, "Chitarra", existing)
    keys = w.project.get_track("Tastiera")
    starts = {c.name: c.start_beat for c in keys.clips}
    assert starts["Intro"] == 6.0 and starts["Ritornello"] == 32.0
    assert starts["Strofa"] >= 14.0                                       # spostata dopo l'Intro
    assert w.project.find_track("Chitarra (note)") is None


def test_reconvert_replaces_the_note_track_with_the_last_choices(tmp_path):
    """Riconvertire dopo una modifica all'audio: il dialogo propone la
    traccia "Nome (note)" e le scelte dell'ultima volta, e la sostituisce."""
    import gui.audio_track_convert_dialog as convert_module
    convert_module._last_choices.clear()
    w, t = _chord_clip_window(tmp_path)
    _run_track_conversion(w, "Chitarra", _chords_mode)
    notes = w.project.get_track("Chitarra (note)")
    notes.clips.append(Clip(name="Mio", text="4: c d e f", start_beat=60.0))   # aggiunto a mano
    t = w.project.get_track("Chitarra")
    t.audio_clips = [c for c in t.audio_clips if c.name == "Ritornello"]      # l'audio cambia
    w._mark_dirty()
    w.refresh_mixer()
    seen = {}

    def accept_as_proposed(dlg):
        seen["mode"] = dlg.mode_combo.currentData()
        seen["destination"] = dlg.destination()

    _run_track_conversion(w, "Chitarra", accept_as_proposed)
    assert seen == {"mode": "chords", "destination": ("replace", "Chitarra (note)")}
    notes = w.project.get_track("Chitarra (note)")
    assert [(c.name, c.start_beat) for c in notes.clips] == [("Ritornello", 32.0)]
    assert notes.clips[0].text.startswith("4: 4C | 4Am | 4F | 4G")
    assert [t.name for t in w.project.tracks].count("Chitarra (note)") == 1
    w.undo()
    assert [c.name for c in w.project.get_track("Chitarra (note)").clips] == ["Strofa", "Ritornello", "Mio"]
    convert_module._last_choices.clear()


def _wait_for_conversion(view):
    worker = view._track_convert_worker
    worker.wait()
    for _ in range(50):
        _app.processEvents()
        if view._track_convert_worker is None:
            break


def test_reconvert_from_the_menus_uses_the_saved_choices(tmp_path):
    """Dopo la conversione la traccia di note ricorda da dove viene (blocco
    Conversione, salvato nel file): Riconverti la rifa' senza dialogo."""
    from core.project_io import parse_project_text, project_to_text
    w, t = _chord_clip_window(tmp_path)
    _run_track_conversion(w, "Chitarra", _chords_mode)
    notes = w.project.get_track("Chitarra (note)")
    assert notes.conversion["from"] == "Chitarra" and notes.conversion["mode"] == "chords"
    assert parse_project_text(project_to_text(w.project)).get_track("Chitarra (note)").conversion == notes.conversion
    view = w.arrangement_view
    point = w.mapToGlobal(w.rect().center())
    assert "Riconverti da 'Chitarra'" in _menu_actions(lambda: view.show_track_menu("Chitarra (note)", point))
    assert "Riconverti le tracce collegate (1)" in _menu_actions(lambda: view.show_track_menu("Chitarra", point))
    t = w.project.get_track("Chitarra")
    t.audio_clips = [c for c in t.audio_clips if c.name == "Ritornello"]      # l'audio cambia
    w._mark_dirty()
    w.refresh_mixer()
    view.reconvert_tracks(["Chitarra (note)"])
    _wait_for_conversion(view)
    notes = w.project.get_track("Chitarra (note)")
    assert [(c.name, c.start_beat) for c in notes.clips] == [("Ritornello", 32.0)]
    assert notes.clips[0].text.startswith("4: 4C | 4Am | 4F | 4G")          # ancora accordi
    w.undo()
    assert [c.name for c in w.project.get_track("Chitarra (note)").clips] == ["Strofa", "Ritornello"]


def test_boxes_added_to_an_existing_track_do_not_link_it(tmp_path):
    w, t = _chord_clip_window(tmp_path)
    w.project.add_track("Tastiera", "Piano", "")
    w.refresh_mixer()

    def existing(dlg):
        _chords_mode(dlg)
        dlg.existing_radio.setChecked(True)
        dlg.target_combo.setCurrentText("Tastiera")

    _run_track_conversion(w, "Chitarra", existing)
    assert len(w.project.get_track("Tastiera").clips) == 2
    assert w.project.get_track("Tastiera").conversion is None


def test_bass_dialog_can_follow_the_chords_of_an_audio_track(tmp_path):
    from gui.rhythm_generate_dialog import BassGenerateDialog, chord_source_tracks
    w, t = _chord_clip_window(tmp_path)
    sources = chord_source_tracks(w.project)
    assert [label for label, _s in sources] == ["Chitarra (audio)"]
    dlg = BassGenerateDialog(w, project=w.project, instrument_name="Bass", context_label="prova",
                             other_tracks=sources, default_bars=4)
    text = dlg.preview_edit.toPlainText()
    assert text.strip() and dlg.status_label.text() == ""
    assert "c" in text.lower()                                           # il basso parte dal Do della Strofa
    dlg.reject()


# --------------------------------------------------------------- riprese multiple e comping

def _takes_window(tmp_path):
    from core import audio_takes
    w = _window()
    t = w.project.add_audio_track("Voce")
    clip = AudioClip("Strofa", _wav(tmp_path / "a.wav", seconds=4.0), 0.0, trim_start=1.0)
    audio_takes.add_take(clip, "Ripresa 2", _wav(tmp_path / "b.wav", seconds=4.0), 1.0)
    t.audio_clips.append(clip)
    w.history.reset(w.project)
    w.refresh_mixer()
    _app.processEvents()
    return w, t, clip


def test_clip_with_takes_shows_them_and_switches(tmp_path):
    w, t, clip = _takes_window(tmp_path)
    view = w.arrangement_view
    actions = _menu_actions(lambda: view._show_audio_box_menu("Voce", clip, w.mapToGlobal(w.rect().center())))
    assert "Riprese" in actions
    view._set_active_take("Voce", clip, 0)
    assert clip.active_take == 0 and clip.file.endswith("a.wav")
    _app.processEvents()
    w.undo()
    assert w.project.get_track("Voce").audio_clips[0].active_take == 1


def test_comping_replaces_the_clip_with_its_stretches(tmp_path):
    from gui.comping_dialog import CompingDialog
    w, t, clip = _takes_window(tmp_path)
    view = w.arrangement_view

    def fake_exec(dlg):
        dlg.lanes.choose(0, 0.0, 2.0)                     # primo secondo dalla ripresa 1
        return CompingDialog.Accepted

    original = CompingDialog.exec
    CompingDialog.exec = fake_exec
    try:
        view._comp_clip("Voce", clip)
    finally:
        CompingDialog.exec = original
    parts = sorted(t.audio_clips, key=lambda c: c.start_beat)
    assert [os.path.basename(c.file) for c in parts] == ["a.wav", "b.wav"]
    assert parts[0].fade_out == pytest.approx(0.01) and parts[1].fade_in == pytest.approx(0.01)
    w.undo()
    assert len(w.project.get_track("Voce").audio_clips) == 1


# --------------------------------------------------------------- tempo dalla ripresa

def test_tempo_from_take_sets_the_song_tempo_and_can_be_undone(tmp_path):
    from test_beat_track import RATE as BT_RATE, _accelerando, _hits
    from gui.tempo_from_take_dialog import TempoFromTakeDialog
    path = str(tmp_path / "acc.wav")
    write_wav(path, _hits(_accelerando(90, 110, 32), 2.0)[:, None], BT_RATE, bits=16)
    w = _window()
    w.project.tempo_bpm = 120
    t = w.project.add_audio_track("Chitarra")
    clip = AudioClip("Ritmica", path, 6.0)
    t.audio_clips.append(clip)
    w.history.reset(w.project)
    w.refresh_mixer()
    view = w.arrangement_view
    actions = _menu_actions(lambda: view._show_audio_box_menu("Chitarra", clip, w.mapToGlobal(w.rect().center())))
    assert "Ricava il tempo dalla ripresa..." in actions

    original = TempoFromTakeDialog.exec
    TempoFromTakeDialog.exec = lambda dlg: (dlg.bar_spin.setValue(3), TempoFromTakeDialog.Accepted)[1]
    try:
        view._tempo_from_clip("Chitarra", clip)
    finally:
        TempoFromTakeDialog.exec = original
    assert [b for b, _v in w.project.tempo_changes][:3] == [1, 3, 4]
    assert 90 <= w.project.tempo_changes[1][1] <= 95            # con un decimale, dalla 2.9
    _app.processEvents()
    w.undo()
    assert w.project.tempo_changes == []


# --------------------------------------------------------------- time-stretch

def test_clips_that_follow_the_tempo_stretch_when_it_changes(tmp_path):
    pytest.importorskip("pedalboard")
    w, t, clip, item = _window_with_clip(tmp_path)               # 2 s a 120 BPM = 4 beat
    view = w.arrangement_view
    actions = _menu_actions(lambda: view._show_audio_box_menu("Voce", clip, w.mapToGlobal(w.rect().center())))
    assert "Segui il tempo del brano" in actions and "Velocita' (time-stretch)..." in actions
    view._toggle_follow_tempo("Voce", clip)
    assert clip.source_bpm == pytest.approx(w.project.tempo_bpm)
    w.tempo_spin.setValue(w.project.tempo_bpm // 2)               # tempo dimezzato: la clip dura il doppio
    _app.processEvents()
    assert clip.stretch == pytest.approx(2.0)
    assert view.clip_length_beats("Voce", clip) == pytest.approx(4.0)   # sempre le stesse battute
    view._toggle_follow_tempo("Voce", clip)
    assert clip.source_bpm == 0.0


def test_speed_dialog_sets_the_stretch(tmp_path, monkeypatch):
    w, t, clip, item = _window_with_clip(tmp_path)
    monkeypatch.setattr(QInputDialog, "getDouble", staticmethod(lambda *a, **k: (50.0, True)))
    w.arrangement_view._edit_clip_speed("Voce", clip)
    assert clip.stretch == pytest.approx(2.0)
    _app.processEvents()
    item = next(it for it in w.arrangement_view.canvas._scene.items() if isinstance(it, AudioBoxItem))
    assert item.rect().width() == pytest.approx(2 * 4 * 24)       # 4 s = 8 beat
    w.undo()
    assert w.project.get_track("Voce").audio_clips[0].stretch == 1.0


def test_tempo_from_take_can_keep_a_fixed_tempo(tmp_path):
    pytest.importorskip("pedalboard")
    from test_beat_track import RATE as BT_RATE, _accelerando, _hits
    from gui.tempo_from_take_dialog import TempoFromTakeDialog
    path = str(tmp_path / "acc.wav")
    write_wav(path, _hits(_accelerando(90, 110, 32), 2.0)[:, None], BT_RATE, bits=16)
    w = _window()
    w.project.tempo_bpm = 100
    t = w.project.add_audio_track("Chitarra")
    t.audio_clips.append(AudioClip("Ritmica", path, 0.0))
    w.history.reset(w.project)
    w.refresh_mixer()

    def fixed(dlg):
        dlg.bar_spin.setValue(2)
        dlg.fixed_radio.setChecked(True)
        dlg.bpm_spin.setValue(100)
        return TempoFromTakeDialog.Accepted

    original = TempoFromTakeDialog.exec
    TempoFromTakeDialog.exec = fixed
    try:
        w.arrangement_view._tempo_from_clip("Chitarra", t.audio_clips[0])
    finally:
        TempoFromTakeDialog.exec = original
    assert w.project.tempo_changes == [] and len(t.audio_clips) == 10
    _app.processEvents()
    w.undo()
    assert len(w.project.get_track("Chitarra").audio_clips) == 1


def test_quantize_audio_from_the_clip_menu(tmp_path):
    from test_audio_slice import _sloppy
    from gui.audio_quantize_dialog import AudioQuantizeDialog
    p, clip, _played = _sloppy(tmp_path)
    w = _window()
    w.project.tempo_bpm = 120
    t = w.project.add_audio_track("Batteria")
    t.audio_clips.append(clip)
    w.history.reset(w.project)
    w.refresh_mixer()
    view = w.arrangement_view
    assert "Quantizza l'audio..." in _menu_actions(
        lambda: view._show_audio_box_menu("Batteria", clip, w.mapToGlobal(w.rect().center())))

    def choose(dlg):
        dlg.grid_combo.setCurrentIndex(dlg.grid_combo.findData(8))
        return AudioQuantizeDialog.Accepted

    original = AudioQuantizeDialog.exec
    AudioQuantizeDialog.exec = choose
    try:
        view._quantize_clip_audio("Batteria", clip)
    finally:
        AudioQuantizeDialog.exec = original
    assert len(t.audio_clips) == 17
    _app.processEvents()
    w.undo()
    assert len(w.project.get_track("Batteria").audio_clips) == 1


def test_remove_silences_from_the_clip_menu(tmp_path):
    from test_remove_silences import _take
    from gui.remove_silences_dialog import RemoveSilencesDialog
    _p, clip = _take(tmp_path)
    w = _window()
    w.project.tempo_bpm = 120
    t = w.project.add_audio_track("Voce")
    t.audio_clips.append(clip)
    w.history.reset(w.project)
    w.refresh_mixer()
    view = w.arrangement_view
    assert "Rimuovi i silenzi..." in _menu_actions(
        lambda: view._show_audio_box_menu("Voce", clip, w.mapToGlobal(w.rect().center())))
    seen = []

    def choose(dlg):
        seen.append(dlg.result_label.text())
        dlg.min_silence_spin.setValue(100)           # anche lo 0,2 s fra la seconda e la terza frase
        seen.append(dlg.result_label.text())
        return RemoveSilencesDialog.Accepted

    original = RemoveSilencesDialog.exec
    RemoveSilencesDialog.exec = choose
    try:
        view._remove_clip_silences("Voce", clip)
    finally:
        RemoveSilencesDialog.exec = original
    assert seen[0].startswith("2 pezzi") and seen[1].startswith("3 pezzi")
    assert len(t.audio_clips) == 3
    _app.processEvents()
    w.undo()
    assert len(w.project.get_track("Voce").audio_clips) == 1


def test_join_pieces_from_the_clip_menu(tmp_path):
    from core import audio_slice
    from test_audio_slice import _sloppy
    p, clip, _played = _sloppy(tmp_path)
    w = _window()
    w.project.tempo_bpm = 120
    t = w.project.add_audio_track("Batteria")
    t.audio_clips = audio_slice.quantize_clip(w.project, clip, 0.5)
    w.history.reset(w.project)
    w.refresh_mixer()
    view = w.arrangement_view
    n = len(t.audio_clips)
    actions = _menu_actions(lambda: view._show_audio_box_menu("Batteria", t.audio_clips[3], w.mapToGlobal(w.rect().center())))
    assert f"Unisci i pezzi in una clip ({n})" in actions
    view._join_pieces("Batteria", list(t.audio_clips))
    assert len(t.audio_clips) == 1 and t.audio_clips[0].file != clip.file
    _app.processEvents()
    w.undo()
    assert len(w.project.get_track("Batteria").audio_clips) == n


def test_check_tuning_offers_to_fix_a_detuned_clip(tmp_path, monkeypatch):
    pytest.importorskip("pedalboard")
    w = _window()
    t = w.project.add_audio_track("Voce")
    x = np.arange(2 * AUDIO_SAMPLE_RATE) / AUDIO_SAMPLE_RATE
    path = str(tmp_path / "scordata.wav")
    write_wav(path, (0.4 * np.sin(2 * np.pi * 432.0 * x)).reshape(-1, 1).astype(np.float32), AUDIO_SAMPLE_RATE)
    clip = AudioClip("Scordata", path, 0.0)
    t.audio_clips.append(clip)
    w.refresh_mixer()
    asked = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: asked.append(a[2]) or QMessageBox.Yes)
    w.arrangement_view.check_clip_tuning("Voce", clip, after_recording=True)
    assert "calante di 31 cent" in asked[0] or "calante di 32 cent" in asked[0]
    assert clip.transpose == pytest.approx(0.318, abs=0.02)
    # corretta, non si chiede piu' niente
    w.arrangement_view.check_clip_tuning("Voce", clip, after_recording=True)
    assert len(asked) == 1


def test_song_key_from_the_chords_of_an_audio_track(tmp_path, monkeypatch):
    import core.audio_track_notation as atn
    w, t, clip, _item = _window_with_clip(tmp_path)
    monkeypatch.setattr(atn, "audio_track_chord_text", lambda project, track: "4: G | D | Em | C | D | G")
    asked = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: asked.append(a[2]) or QMessageBox.Yes)
    w.arrangement_view.key_from_audio_track("Voce")
    assert "G" in asked[0] and w.project.key == "G" and w.key_combo.currentText() == "G"


def test_export_stems_from_the_file_menu(tmp_path, monkeypatch):
    import time
    w, t, clip, _item = _window_with_clip(tmp_path)
    def press(box):
        next(b for b in box.buttons() if b.text() == "Asciutte").click()
    monkeypatch.setattr(QMessageBox, "exec", press)
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a, **k: str(tmp_path / "esportate"))
    w.export_stems()
    deadline = time.time() + 20
    while w._export_wav_worker is not None and time.time() < deadline:
        _app.processEvents()
        time.sleep(0.01)
    folder = next((tmp_path / "esportate").iterdir())
    assert folder.name.endswith(" - tracce")
    assert [f.name for f in folder.iterdir()] == ["01 Voce (asciutta).wav"]


def test_freeze_and_unfreeze_from_the_track_menu(tmp_path):
    import time
    from PySide6.QtWidgets import QMenu
    w, t, clip, _item = _window_with_clip(tmp_path)
    menu = QMenu()
    action = w.add_freeze_action(menu, "Voce")
    assert action.text() == "Congela in audio"
    action.trigger()
    deadline = time.time() + 20
    while getattr(w, "_freeze_worker", None) is not None and time.time() < deadline:
        _app.processEvents()
        time.sleep(0.01)
    assert [x.name for x in w.project.tracks] == ["Voce", "Voce (congelata)"]
    assert t.mute and t.frozen == "Voce (congelata)"
    assert w.add_freeze_action(QMenu(), "Voce (congelata)") is None     # la traccia stampata non si congela
    assert w.add_freeze_action(QMenu(), "Voce").text().startswith("Scongela")
    w.toggle_freeze("Voce")
    assert [x.name for x in w.project.tracks] == ["Voce"] and not t.mute
    w.undo()
    assert [x.name for x in w.project.tracks] == ["Voce", "Voce (congelata)"]


def test_ctrl_dragging_the_right_edge_loops_the_clip(tmp_path):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    w, t, clip, item = _window_with_clip(tmp_path)               # 2 s = 4 beat, dal beat 4
    canvas = w.arrangement_view.canvas
    rect = item.sceneBoundingRect()
    start = canvas.mapFromScene(rect.right() - 2, rect.center().y())
    end = start + type(start)(8 * 24, 0)                          # +8 beat
    QTest.mousePress(canvas.viewport(), Qt.LeftButton, Qt.ControlModifier, start)
    QTest.mouseMove(canvas.viewport(), end)
    QTest.mouseRelease(canvas.viewport(), Qt.LeftButton, Qt.ControlModifier, end)
    _app.processEvents()
    assert clip.loop_length == pytest.approx(12.0) and clip.trim_end == 0.0
    item = next(it for it in canvas._scene.items() if isinstance(it, AudioBoxItem))
    assert item.rect().width() == pytest.approx(12 * 24)
    w.undo()
    assert w.project.get_track("Voce").audio_clips[0].loop_length == 0.0


def test_gain_curve_points_on_the_box(tmp_path):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    w, t, clip, item = _window_with_clip(tmp_path)                 # 2 s = 4 beat = 96 px
    canvas = w.arrangement_view.canvas
    rect = item.sceneBoundingRect()
    vp = canvas.viewport()
    at_point = canvas.mapFromScene(rect.left() + 48, item.mapToScene(0, item._db_to_y(0.0)).y())
    QTest.mouseClick(vp, Qt.LeftButton, Qt.ControlModifier, at_point)
    _app.processEvents()
    assert clip.gain_points == [(1.0, 0.0)]
    item = next(it for it in canvas._scene.items() if isinstance(it, AudioBoxItem))
    low = canvas.mapFromScene(rect.left() + 48, item.mapToScene(0, item._db_to_y(-20.0)).y())
    QTest.mousePress(vp, Qt.LeftButton, Qt.NoModifier, at_point)
    QTest.mouseMove(vp, low)
    QTest.mouseRelease(vp, Qt.LeftButton, Qt.NoModifier, low)
    _app.processEvents()
    assert clip.gain_points[0][0] == pytest.approx(1.0, abs=0.02)
    assert clip.gain_points[0][1] == pytest.approx(-20.0, abs=1.0)
    item = next(it for it in canvas._scene.items() if isinstance(it, AudioBoxItem))
    import gui.arrangement_view as av
    renamed = []
    w.arrangement_view._rename_clip = lambda *a: renamed.append(a)     # mai una finestra modale nei test
    QTest.mouseDClick(vp, Qt.LeftButton, Qt.NoModifier, low)
    _app.processEvents()
    assert clip.gain_points == [] and renamed == []


def test_convert_melody_and_chords_together(tmp_path):
    w, t = _chord_clip_window(tmp_path)

    def both(dlg):
        dlg.mode_combo.setCurrentIndex(dlg.mode_combo.findData("melody"))
        assert dlg.with_chords_check.isVisibleTo(dlg)
        dlg.with_chords_check.setChecked(True)

    _run_track_conversion(w, "Chitarra", both)
    melody = w.project.get_track("Chitarra (note)")
    chords = w.project.get_track("Chitarra (note 2)")
    assert melody.conversion["mode"] == "melody" and chords.conversion["mode"] == "chords"
    assert chords.clips[0].text.startswith("4: 4C | 4Am | 4F | 4G")
    assert [c.start_beat for c in chords.clips] == [8.0, 32.0]
