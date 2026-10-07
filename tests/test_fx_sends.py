"""
Test del primo passo degli effetti: invio al riverbero e al chorus del synth
per traccia (Track.reverb/chorus, CC91/CC93) e ambiente del riverbero per
tutto il brano (Project.reverb_room, core.effects).
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mido
import pytest

from core.effects import DEFAULT_REVERB_ROOM, REVERB_ROOMS, apply_reverb, reverb_cli_options, reverb_params
from core.midi_export import export_project_to_midi
from core.midi_import import import_midi_file
from core.model import Project, cc_to_send_percent, send_percent_to_cc
from core.project_io import parse_project_text, project_to_text


def _controls(path):
    return [[(m.control, m.value) for m in tr if m.type == "control_change"] for tr in mido.MidiFile(path).tracks]


def _project():
    p = Project(name="t")
    p.add_track("Piano", "Piano", "4: c d e f")
    p.add_track("Basso", "Bass", "4: c*2 g*1")
    return p


def test_percent_and_cc_conversions():
    assert [send_percent_to_cc(v) for v in (0, 35, 50, 100, 150, -5)] == [0, 44, 64, 127, 127, 0]
    assert [cc_to_send_percent(v) for v in (0, 44, 64, 127, 200)] == [0, 35, 50, 100, 100]


def test_midi_export_sends_cc91_cc93_only_when_set(tmp_path):
    p = _project()
    plain = str(tmp_path / "plain.mid")
    export_project_to_midi(p, plain)
    assert all(c not in (91, 93) for track in _controls(plain) for c, _v in track)
    p.get_track("Piano").reverb, p.get_track("Piano").chorus = 35, 12
    wet = str(tmp_path / "wet.mid")
    export_project_to_midi(p, wet)
    piano, bass = [t for t in _controls(wet) if t]
    assert (91, 44) in piano and (93, 15) in piano
    assert all(c not in (91, 93) for c, _v in bass)


def test_project_file_round_trip_and_old_files():
    p = _project()
    p.get_track("Piano").reverb, p.get_track("Basso").chorus = 35, 20
    p.reverb_room = "sala_grande"
    text = project_to_text(p)
    assert "Ambiente: sala_grande" in text and "riverbero: 35" in text and "chorus: 20" in text
    q = parse_project_text(text)
    assert (q.get_track("Piano").reverb, q.get_track("Piano").chorus) == (35, 0)
    assert (q.get_track("Basso").reverb, q.get_track("Basso").chorus) == (0, 20)
    assert q.reverb_room == "sala_grande"
    # un progetto senza riverbero non scrive nulla di nuovo
    plain = project_to_text(_project())
    assert "Ambiente" not in plain and "Mixer" not in plain
    # file vecchi o scritti a mano
    old = parse_project_text("Tempo: 100 BPM\nMetrica: 4/4\n\nPiano:\n  c d e\n")
    assert old.reverb_room == DEFAULT_REVERB_ROOM and old.tracks[0].reverb == 0
    odd = parse_project_text("Tempo: 100 BPM\nMetrica: 4/4\nAmbiente: cantina\n\nPiano:\n  c d\n\n"
                             "Mixer Piano:\n  volume: 100 reverb: 250\n")
    assert odd.reverb_room == DEFAULT_REVERB_ROOM and odd.tracks[0].reverb == 100


def test_midi_import_reads_reverb_and_chorus(tmp_path):
    p = _project()
    p.get_track("Piano").reverb, p.get_track("Piano").chorus = 31, 8
    path = str(tmp_path / "in.mid")
    export_project_to_midi(p, path)
    imported = {t.instrument_name: t for t in import_midi_file(path).tracks}
    piano = next(t for name, t in imported.items() if "Piano" in name)
    assert (piano.reverb, piano.chorus) == (31, 8)
    assert all((t.reverb, t.chorus) == (0, 0) for t in imported.values() if t is not piano)


def test_default_room_is_the_classic_fluidsynth_room():
    assert reverb_params(DEFAULT_REVERB_ROOM) == (0.2, 0.0, 0.5, 0.9)
    assert reverb_params("sconosciuto") == reverb_params(DEFAULT_REVERB_ROOM)
    sizes = [reverb_params(k)[0] for k in REVERB_ROOMS]
    assert sizes == sorted(sizes) and len(set(sizes)) == len(sizes)
    assert "synth.reverb.room-size=0.7" in reverb_cli_options("sala_grande")
    from core import fluid
    if not fluid.available():
        pytest.skip("libreria FluidSynth non installata")
    # "stanza" sono i valori predefiniti storici di FluidSynth 2.0-2.3; le
    # versioni piu' recenti ne hanno altri, ma SoundText imposta sempre la
    # sala: il suono non cambia con la versione della libreria
    synth = fluid.Synth()
    try:
        apply_reverb(synth, DEFAULT_REVERB_ROOM)
        assert round(synth.get_setting("synth.reverb.room-size"), 3) == 0.2
        assert round(synth.get_setting("synth.reverb.level"), 3) == 0.9
    finally:
        synth.delete()


def test_room_changes_the_reverb_tail():
    """Con un SoundFont vero: con la sala grande l'invio al riverbero allunga
    la coda molto piu' che nella stanza piccola."""
    import numpy as np
    from core import settings
    sf = "/usr/share/sounds/sf2/TimGM6mb.sf2"
    if not os.path.exists(sf):
        pytest.skip("SoundFont di prova non installato")
    from core import fluid
    if not fluid.available():
        pytest.skip("libreria FluidSynth non installata")
    from core.playback import render_project_mix
    previous = settings.get_soundfont_path()
    settings.set_soundfont_path(sf)
    try:
        def tail_db(send, room):
            p = Project(name="t", tempo_bpm=120, reverb_room=room)
            p.add_track("Piano", "Piano", "4: [c*4 e*4 g*4] 7r").reverb = send
            audio, rate = render_project_mix(p)
            tail = audio[int(0.6 * rate):int(1.5 * rate)]
            return 20 * np.log10(np.sqrt(np.mean(tail ** 2)) + 1e-12)
        small = tail_db(60, "stanza") - tail_db(0, "stanza")
        large = tail_db(60, "sala_grande") - tail_db(0, "sala_grande")
        assert large > small + 3
    finally:
        if previous:
            settings.set_soundfont_path(previous)


def test_sends_card_changes_track_and_room():
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from gui.effects_panel import SendsCard, fx_summary, has_fx

    class _Panel:
        calls = 0

        def sends_changed(self):
            self.calls += 1
    p = _project()
    track = p.get_track("Piano")
    panel = _Panel()
    card = SendsCard(track, p, panel)
    assert not has_fx(track) and "nessuno" in fx_summary(track)
    card.reverb_slider.setValue(40)
    card.chorus_slider.setValue(15)
    assert (track.reverb, track.chorus) == (40, 15) and panel.calls == 2
    assert card.reverb_label.text() == "40%" and "Riverbero 40% · Chorus 15%" in fx_summary(track)
    assert not card.room_hint.isHidden()                 # stanza piccola: il riverbero si sente appena
    card.room_combo.setCurrentIndex(card.room_combo.findData("sala"))
    assert p.reverb_room == "sala" and card.room_hint.isHidden()


def test_fx_buttons_in_both_headers_open_the_effects_panel():
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from gui.main_window import MainWindow
    w = MainWindow()
    w.project.add_track("Piano", "Piano", "4: c d")
    w.project.add_audio_track("Voce")
    w.refresh_mixer()
    header = w.arrangement_view.canvas.header_widgets["Piano"]
    text_header = w.track_headers["Piano"]
    assert w.arrangement_view.canvas.header_widgets["Voce"].fx_btn is not None   # anche le tracce audio
    assert w.track_headers["Voce"].fx_btn is not None
    assert header.fx_btn.objectName() == "fxBtn"
    header._open_fx()
    panel = w.effects_panel
    assert panel.is_open() and panel.track is w.project.get_track("Piano")
    assert w.current_track_name == "Piano"
    panel.sends_card.reverb_slider.setValue(30)
    assert w.project.get_track("Piano").reverb == 30
    assert header.fx_btn.objectName() == "fxBtnOn"
    assert "Riverbero 30%" in text_header.fx_btn.toolTip()     # la testata della vista Testo si riallinea
    text_header.fx_btn.click()
    panel.sends_card.room_combo.setCurrentIndex(panel.sends_card.room_combo.findData("chiesa"))
    assert w.project.reverb_room == "chiesa"
    assert w.history.can_undo()
    w.track_headers["Voce"].fx_btn.click()                                      # traccia audio: niente invio al synth
    assert panel.track is w.project.get_track("Voce") and panel.sends_card is None
    panel.close_panel()
    assert not panel.is_open() and panel.isHidden()
