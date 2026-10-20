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
    assert "Trasponi..." not in box and "Ritrova file..." not in box


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
    import gui.arrangement_view as av
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
