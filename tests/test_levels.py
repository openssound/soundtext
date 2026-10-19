import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)

import numpy as np

from core.levels import analyze_int16, bars_for_seconds, format_bars, peak_dbfs, BLOCK_SECONDS
from core.model import Project
from core.tempo_map import build_tempo_beat_map

RATE = 48000


def _tone(seconds, amplitude):
    t = np.arange(int(seconds * RATE)) / RATE
    x = amplitude * np.sin(2 * np.pi * 440 * t)
    return np.stack([x, x], axis=1)


def _int16(x):
    return (np.clip(x, -1.0, 1.0) * 32767).astype(np.int16)


def test_loud_but_clean_mix_does_not_clip():
    levels = analyze_int16(_int16(_tone(1.0, 0.9)), RATE)
    assert not levels.clipped.any()
    assert 0.89 < levels.max_peak < 0.91


def test_mix_over_full_scale_clips_only_where_it_does():
    # 1 s pulito, 0.5 s a 1.5 volte il fondo scala (tagliato), 1 s pulito
    x = np.concatenate([_tone(1.0, 0.5), _tone(0.5, 1.5), _tone(1.0, 0.5)])
    levels = analyze_int16(_int16(x), RATE)
    regions = levels.clip_regions()
    assert len(regions) == 1
    start, end = regions[0]
    assert abs(start - 1.0) < 2 * BLOCK_SECONDS and abs(end - 1.5) < 2 * BLOCK_SECONDS
    assert levels.clipped_between(1.1, 1.2) and not levels.clipped_between(0.2, 0.8)


def test_single_full_scale_sample_is_a_peak_not_a_clip():
    x = np.zeros((RATE, 2))
    x[1000] = 1.0
    levels = analyze_int16(_int16(x), RATE)
    assert levels.max_peak > 0.99 and not levels.clipped.any()


def test_peak_dbfs_of_float_signal_can_exceed_full_scale():
    assert abs(peak_dbfs(_tone(0.1, 2.0)) - 6.02) < 0.05
    assert peak_dbfs(np.zeros((10, 2))) < -80


def test_bars_for_seconds_follow_tempo_and_meter():
    project = Project(name="p")       # 120 BPM, 4/4: una battuta ogni 2 s
    project.tempo_bpm = 120
    tempo_map = build_tempo_beat_map(project)
    assert bars_for_seconds(project, tempo_map, [0.5, 2.1, 2.5, 9.0]) == [1, 2, 5]
    assert format_bars([1, 2, 3, 5, 9, 10]) == "1-3, 5, 9-10"


def test_level_meter_latches_clip_until_clicked():
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from gui.level_meter import LevelMeter
    meter = LevelMeter()
    meter.set_level(0.5)
    meter.set_clipped(True, "battute 3")
    assert meter.clipped and "battute 3" in meter.toolTip()
    meter.silence()
    assert meter.clipped                        # lo Stop non la spegne
    pos = QPointF(meter.width() - 5, 5)
    meter.mousePressEvent(QMouseEvent(QMouseEvent.MouseButtonPress, pos, meter.mapToGlobal(pos),
                                      Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    assert not meter.clipped


def test_main_window_shows_clipping_during_playback_and_after_stop():
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from gui.main_window import MainWindow
    w = MainWindow()
    w.project.tempo_bpm = 120
    w._playback_tempo_map = build_tempo_beat_map(w.project)
    x = np.concatenate([_tone(4.0, 0.5), _tone(0.5, 1.5), _tone(2.0, 0.5)])   # clippa a 4 s: battuta 3
    w.playback.master_levels = analyze_int16(_int16(x), RATE)
    position = {"s": 1.0}
    w.playback.position_seconds = lambda: position["s"]
    w._update_level_meter()
    assert not w.level_meter.clipped
    position["s"] = 4.2
    w._update_level_meter()
    assert w.level_meter.clipped and "3" in w.level_meter.toolTip()
    w.stop()
    assert "clippa" in w.statusBar().currentMessage()
    w.close()


def test_analyze_project_levels_measures_each_track_and_the_mix():
    import pytest
    from core.levels import analyze_project_levels
    from core.playback import _find_soundfont
    if not _find_soundfont():
        pytest.skip("serve un SoundFont")
    project = Project(name="p")
    project.add_track("Piano", "Piano", "4: c e g c*5")
    project.add_track("Basso", "Piano", "4: c*2 c*2 c*2 c*2")
    project.tracks[1].volume = 10
    report = analyze_project_levels(project)
    assert set(report.tracks) == {"Piano", "Basso"}
    assert report.tracks["Basso"].peak_db < report.tracks["Piano"].peak_db
    assert report.master_peak_db >= report.tracks["Piano"].peak_db - 0.5


def test_level_report_marks_track_headers_until_the_song_changes():
    from PySide6.QtWidgets import QApplication, QMessageBox
    QApplication.instance() or QApplication([])
    from core.levels import LevelReport, TrackPeak
    from gui.main_window import MainWindow
    from gui.track_header import TrackHeaderWidget
    w = MainWindow()
    w.project.add_track("Piano", "Piano", "c d e f")
    w.project.add_track("Basso", "Piano", "c d e f")
    w.refresh_mixer()
    shown = []
    original = QMessageBox.information
    QMessageBox.information = staticmethod(lambda *a, **k: shown.append(a[2]))
    try:
        w._show_level_report(LevelReport({"Piano": TrackPeak(0.0, [3, 4]), "Basso": TrackPeak(-9.0, [])},
                                         0.0, [3, 4], 1.5))
    finally:
        QMessageBox.information = original
    headers = {h.track_name: h for h in w.findChildren(TrackHeaderWidget)}
    assert headers["Piano"].meter._static == (0.0, True) and "3-4" in headers["Piano"].meter.toolTip()
    assert headers["Basso"].meter._static == (-9.0, False)
    assert "Piano" in shown[0] and "3-4" in shown[0]
    w._mark_dirty()
    assert all(h.meter._static is None for h in w.findChildren(TrackHeaderWidget))
    w._dirty = False      # niente domanda "salvare le modifiche?" alla chiusura
    w.close()


def test_analyze_levels_command_shows_the_report_when_it_finishes(monkeypatch):
    """Il comando intero, con la finestra di avanzamento: chiuderla alla fine
    emette canceled, e prima il risultato veniva scartato come annullato."""
    import time
    from PySide6.QtWidgets import QApplication, QMessageBox
    app = QApplication.instance() or QApplication([])
    import core.levels
    from core.levels import LevelReport, TrackPeak
    from gui.main_window import MainWindow
    monkeypatch.setattr(core.levels, "analyze_project_levels",
                        lambda project, stop_check=None, progress_callback=None:
                        LevelReport({"Piano": TrackPeak(-6.0, [])}, -6.0, [], 0.0))
    shown = []
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: shown.append(a[2])))
    w = MainWindow()
    w.project.add_track("Piano", "Piano", "c d e f")
    w.analyze_levels()
    deadline = time.time() + 10
    while not shown and time.time() < deadline:
        app.processEvents()
        time.sleep(0.01)
    assert shown and "-6.0" in shown[0]
    assert w._track_peaks["Piano"].peak_db == -6.0
    w._dirty = False
    w.close()


def _fluid_ready():
    from core import fluid
    from core.playback import _find_soundfont
    return fluid.available() and hasattr(fluid._load(), "fluid_synth_process") and _find_soundfont()


def test_per_channel_synthesis_sounds_like_the_plain_mix(tmp_path):
    """Le uscite per canale sommate danno lo stesso audio di write_s16 (a
    parte il dither: al massimo pochi passi su 32767)."""
    import os
    import pytest
    if not _fluid_ready():
        pytest.skip("serve la libreria FluidSynth con fluid_synth_process e un SoundFont")
    from core import fluid
    from core.midi_export import export_project_to_midi
    from core.playback import _find_soundfont, apply_reverb, DEFAULT_REVERB_ROOM
    project = Project(name="p")
    project.add_track("A", "Piano", "4: c e g c*5 | 2[c e g] 2r")
    project.add_track("B", "Piano", "4: c*3 g*2 c*3 g*2 | 4c*3")
    midi = str(tmp_path / "x.mid")
    export_project_to_midi(project, midi)

    def render(grouped):
        extra = {"synth.audio-channels": 16, "synth.audio-groups": 16} if grouped else {}
        s = fluid.Synth(gain=0.9, samplerate=48000, **{"synth.reverb.active": 1, "synth.chorus.active": 1}, **extra)
        s.sfload(_find_soundfont()); s.system_reset(); apply_reverb(s, DEFAULT_REVERB_ROOM); s.set_effects_on(True)
        player = fluid.Player(s); player.add(midi); player.play()
        out = []
        while player.playing():
            if grouped:
                mix, _dry = s.render_groups(4800)
                out.append(np.clip(np.rint(mix * 32767), -32768, 32767))
            else:
                out.append(s.get_samples(4800).reshape(-1, 2))
        player.delete()
        return np.concatenate(out).astype(np.int32)

    a, b = render(False), render(True)
    n = min(len(a), len(b))
    assert np.abs(a).max() > 1000 and np.abs(a[:n] - b[:n]).max() <= 4


def test_render_measures_each_track_in_the_same_pass(tmp_path):
    import pytest
    if not _fluid_ready():
        pytest.skip("serve la libreria FluidSynth con fluid_synth_process e un SoundFont")
    from core.midi_export import _assign_channels, export_project_to_midi
    from core.playback import _PersistentSynth, _assemble_track_levels, _find_soundfont
    project = Project(name="p")
    project.add_track("Forte", "Piano", "4: [c e g] [c e g] [c e g] [c e g]")
    project.add_track("Piano piano", "Piano", "4: c*5 d*5 e*5 f*5")
    project.add_track("Muta", "Piano", "4r")
    project.tracks[1].volume = 20
    midi = str(tmp_path / "x.mid")
    export_project_to_midi(project, midi)
    levels = {}
    assert _PersistentSynth().render_to_wav(midi, str(tmp_path / "x.wav"), _find_soundfont(), lambda: False,
                                            channel_levels=levels)
    track_levels = _assemble_track_levels(levels, _assign_channels(project.tracks), [], {})
    loud = track_levels.level("Forte", 0, 4)
    soft = track_levels.level("Piano piano", 0, 4)
    assert loud > soft > 0
    assert track_levels.level("Muta", 0, 4) is None


def test_track_meters_follow_playback():
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from core.levels import TrackLevels
    from gui.main_window import MainWindow
    from gui.track_header import TrackHeaderWidget
    w = MainWindow()
    w.project.add_track("Piano", "Piano", "c d e f")
    w.project.add_track("Basso", "Piano", "c d e f")
    w.refresh_mixer()
    block = 0.02
    w.playback.track_levels = TrackLevels(block, {"Piano": np.full(200, 0.5, np.float32),
                                                  "Basso": np.full(200, 1.2, np.float32)})
    w._update_track_meters(1.0)
    meters = {h.track_name: h.meter for h in w.findChildren(TrackHeaderWidget)}
    assert -6.5 < meters["Piano"]._db < -5.5 and not meters["Piano"].over
    assert meters["Basso"].over                      # oltre il fondo scala: cima rossa
    w._update_track_meters(None)                     # fermo: barre a zero, la spia resta
    assert meters["Piano"]._db < -40 and meters["Basso"].over
    w.close()
