"""
Pitch bend nell'import MIDI: due casi di Strange Brew (Cream) che gli slide
leggevano male, e la curva esatta per il bottleneck (core.midi_bend_curve,
Opzioni > Slide nell'import MIDI... > Bottleneck).

Esecuzione:
    python3 -m pytest tests/test_midi_bend_curve.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)


import mido
import numpy as np

from core import midi_convert
from core.midi_bend_curve import bend_curve_span, split_with_curves
from core.midi_export import export_project_to_midi
from core.midi_import import import_midi_channel_into_track, import_midi_file
from core.notation import validate_track_text

TPB = 480


def _midi(path, messages, program=30):
    """Un file con un canale di chitarra: messages = [(tick assoluto, messaggio)]."""
    mid = mido.MidiFile(ticks_per_beat=TPB)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.Message("program_change", program=program, channel=0, time=0))
    now = 0
    for tick, msg in messages:
        track.append(msg.copy(time=tick - now))
        now = tick
    mid.save(path)
    return str(path)


def _on(note):
    return mido.Message("note_on", note=note, velocity=100, channel=0)


def _off(note):
    return mido.Message("note_off", note=note, velocity=0, channel=0)


def _wheel(value):
    return mido.Message("pitchwheel", pitch=value, channel=0)


def _pitch_track(path, channel=0, step_ticks=10):
    """Altezza nel tempo (in tick): nota piu' alta che suona + bend (RPN letto)."""
    mid = mido.MidiFile(path)
    events = []
    for track in mid.tracks:
        tick = 0
        for msg in track:
            tick += msg.time
            if getattr(msg, "channel", None) != channel:
                continue
            events.append((tick, msg))
    events.sort(key=lambda e: e[0])
    end = events[-1][0]
    curve = np.full(end // step_ticks + 1, np.nan)
    rng, rpn, bend, on, i = 2.0, [127, 127], 0.0, set(), 0
    for k in range(len(curve)):
        now = k * step_ticks
        while i < len(events) and events[i][0] <= now:
            msg = events[i][1]
            if msg.type == "control_change":
                if msg.control == 101:
                    rpn[0] = msg.value
                elif msg.control == 100:
                    rpn[1] = msg.value
                elif msg.control == 6 and rpn == [0, 0]:
                    rng = float(msg.value)
            elif msg.type == "pitchwheel":
                bend = msg.pitch / 8192.0
            elif msg.type == "note_on" and msg.velocity:
                on.add(msg.note)
            elif msg.type in ("note_on", "note_off"):
                on.discard(msg.note)
            i += 1
        if on:
            curve[k] = max(on) + bend * rng
    return curve


def _exported(project, track, tmp_path):
    out = str(tmp_path / "out.mid")
    for other in project.tracks:
        other.mute = other is not track
    export_project_to_midi(project, out, tracks=[track])
    return out


# ---------------------------------------------------------------------------
# Le due correzioni degli slide
# ---------------------------------------------------------------------------

def test_prebend_of_the_next_note_as_first_event_at_the_end_is_not_a_release(tmp_path):
    """Strange Brew: un la che parte un tono sotto (scoop dal sol) e torna al
    centro; la nota dopo, allo stesso tick della fine, riparte un tono sotto.
    Il pre-bend della seconda e' il PRIMO evento a quel tick (la prima era
    gia' al centro): non e' un rilascio della prima (diventava la>si>la)."""
    path = _midi(tmp_path / "scoop.mid", [
        (0, _wheel(-8190)), (0, _on(69)), (60, _wheel(0)),
        (1920, _off(69)), (1920, _wheel(-8190)), (1920, _on(69)), (1980, _wheel(0)),
        (2400, _off(69))])
    _bpm, _tpb, channels = midi_convert.analyze_midi(path)
    ch = channels[0]
    assert ch.bends[(0, 69)][1:] == ([69], 67)               # scoop dal sol, come la seconda
    assert ch.bends[(1920, 69)][1:] == ([69], 67)


def test_a_reset_at_the_note_off_is_not_a_release(tmp_path):
    """Strange Brew: un re piegato al mi e tenuto fino alla fine; il wheel
    torna a 0 sul note_off, dove non si sente: niente rilascio (diventava
    re>mi>re e il mi tenuto non si sentiva)."""
    ramp = [(i * 18, _wheel(min(8191, 1365 * i))) for i in range(1, 7)]
    path = _midi(tmp_path / "hold.mid", [(0, _wheel(0)), (0, _on(74))] + ramp + [
        (480, _off(74)), (480, _wheel(0)), (480, _on(74)), (960, _off(74))])
    _bpm, _tpb, channels = midi_convert.analyze_midi(path)
    ch = channels[0]
    assert ch.bends[(0, 74)][1] == [76]
    assert (0, 74) not in ch.bend_release


# ---------------------------------------------------------------------------
# Curva esatta (bottleneck)
# ---------------------------------------------------------------------------

def _slide_guitar(tmp_path):
    """Un la che scende di 0,9 semitoni, resta fra due semitoni, risale e
    alla fine cade di 2,5: con RPN a 12, come i MIDI di slide guitar."""
    messages = [(0, mido.Message("control_change", control=101, value=0, channel=0)),
                (0, mido.Message("control_change", control=100, value=0, channel=0)),
                (0, mido.Message("control_change", control=6, value=12, channel=0)),
                (0, _wheel(0)), (0, _on(69))]
    for i in range(1, 11):                                   # -0,9 in 100 tick
        messages.append((i * 10, _wheel(round(-614 * i / 10))))
    for i in range(1, 11):                                   # risale fra 600 e 700
        messages.append((600 + i * 10, _wheel(round(-614 * (10 - i) / 10))))
    messages += [(1700, _wheel(-1706)), (1800, _off(69)), (1800, _wheel(0)),
                 (1800, _on(64)), (2400, _off(64))]
    return _midi(tmp_path / "slide.mid", messages, program=26)


def test_curve_follows_the_slide_between_semitones(tmp_path):
    path = _slide_guitar(tmp_path)
    project = import_midi_file(path, bend_curve=True)
    track = project.tracks[0]
    assert "bend=" in track.text and ">>" in track.text
    assert validate_track_text(track.text, project.patterns)[0]
    assert ">" not in track.text.replace(">>", "")            # niente slide sulle note
    original, imported = _pitch_track(path), _pitch_track(_exported(project, track, tmp_path))
    n = min(len(original), len(imported))
    both = ~np.isnan(original[:n]) & ~np.isnan(imported[:n])
    error = np.abs(original[:n] - imported[:n])[both]
    assert both.sum() > 150 and np.percentile(error, 95) < 0.25


def test_without_the_option_the_import_is_unchanged(tmp_path):
    path = _slide_guitar(tmp_path)
    text, _instrument = import_midi_channel_into_track(path, 0)
    assert "bend=" not in text


def test_channel_without_bends_gets_no_curve(tmp_path):
    path = _midi(tmp_path / "flat.mid", [(0, _on(60)), (480, _off(60)), (480, _on(62)), (960, _off(62))])
    text, _instrument = import_midi_channel_into_track(path, 0, bend_curve=True)
    assert "bend=" not in text and "{" not in text


def test_curve_span_writes_holds_ramps_and_jumps():
    # rampa a -1 in 120 tick (passi da 10), tenuta fino a 480, salto a 0
    events = [(10 * i, round(-4096 * i / 12)) for i in range(13)] + [(480, 0)]
    text = bend_curve_span(events, 2.0, TPB, 0, 960)
    assert text.startswith("64:")
    tokens = text.split()
    assert tokens[1:3] == ["bend=0", ">>"]                    # la rampa parte dallo 0 iniziale
    assert tokens[3] == "4r" and tokens[4] == "bend=-1"       # arriva a -1 dopo 120 tick (4/64)
    assert tokens[5:8] == ["12r", "bend=-1", "bend=0"]        # tenuta fino a 480, poi il salto
    assert bend_curve_span([(0, 100)], 2.0, TPB, 0, 960) is None   # sotto un quarto di semitono


def test_boxes_keep_their_own_piece_of_curve(tmp_path):
    """Due frasi separate da una pausa lunga diventano due box, ognuno con la
    sua curva, senza sovrapporsi e con lo stesso suono di prima."""
    from core.arrangement import clip_duration_beats
    from core.box_conversion import split_track_into_boxes
    first = _slide_guitar(tmp_path)
    mid = mido.MidiFile(first)
    track = mid.tracks[0]
    # la stessa frase ripetuta dopo 16 beat di pausa
    msgs, tick = [], 0
    for msg in track:
        tick += msg.time
        if not msg.is_meta:
            msgs.append((tick, msg))
    again = [(t + 16 * TPB + 2400, m) for t, m in msgs if m.type != "program_change"]
    path = _midi(tmp_path / "two.mid", [(t, m) for t, m in msgs if m.type != "program_change"] + again, program=26)
    project = import_midi_file(path, bend_curve=True)
    split_with_curves(project, split_track_into_boxes)
    track = project.tracks[0]
    assert len(track.clips) == 2 and all("bend=" in c.text for c in track.clips)
    octave = track.instrument.default_octave
    spans = [(c.start_beat, c.start_beat + clip_duration_beats(c.text, project.patterns, octave,
                                                              c.start_beat, project.meter()))
             for c in track.clips]
    assert spans[0][1] <= spans[1][0]
    original, imported = _pitch_track(path), _pitch_track(_exported(project, track, tmp_path))
    n = min(len(original), len(imported))
    both = ~np.isnan(original[:n]) & ~np.isnan(imported[:n])
    assert np.percentile(np.abs(original[:n] - imported[:n])[both], 95) < 0.25
    assert not getattr(project, "imported_bend_curves", {})


def test_dialog_remembers_the_bottleneck_option():
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from core import settings
    from gui.midi_import_slide_dialog import MidiImportSlideDialog
    settings.set_midi_import_bend_curve(False)
    dialog = MidiImportSlideDialog()
    assert not dialog.curve_check.isChecked()
    dialog.curve_check.setChecked(True)
    dialog._accept()
    assert settings.get_midi_import_bend_curve()
    assert MidiImportSlideDialog().curve_check.isChecked()
    settings.set_midi_import_bend_curve(False)


# ---------------------------------------------------------------------------
# Griglia ritmica: trentaduesimi
# ---------------------------------------------------------------------------

def _onsets(path):
    mid = mido.MidiFile(path)
    tick, out = 0, []
    for msg in mido.merge_tracks(mid.tracks):
        tick += msg.time
        if msg.type == "note_on" and msg.velocity:
            out.append(tick)
    return out


def test_a_grace_note_on_the_thirty_second_keeps_its_place(tmp_path):
    """Strange Brew: un do di un trentaduesimo prima del la. A sedicesimi il
    la si spostava di un trentaduesimo (70 ms a 105 BPM)."""
    path = _midi(tmp_path / "grace.mid", [(0, _on(72)), (60, _off(72)), (60, _on(69)), (960, _off(69))])
    project = import_midi_file(path)
    assert "32:" in project.tracks[0].text
    assert _onsets(_exported(project, project.tracks[0], tmp_path)) == [0, 60]


def test_fine_rhythm_follows_a_loose_performance(tmp_path):
    """Un attacco fra un sedicesimo e un trentaduesimo (suonato dal vivo): di
    norma resta a sedicesimi, con il ritmo fedele va al trentaduesimo."""
    messages = [(0, _on(60)), (230, _off(60)), (230, _on(62)), (288, _off(62)), (288, _on(64)), (960, _off(64))]
    path = _midi(tmp_path / "loose.mid", messages)
    normal = _onsets(_exported(import_midi_file(path), import_midi_file(path).tracks[0], tmp_path))
    fine_project = import_midi_file(path, fine_rhythm=True)
    fine = _onsets(_exported(fine_project, fine_project.tracks[0], tmp_path))
    real = [0, 230, 288]
    assert sum(abs(a - b) for a, b in zip(fine, real)) < sum(abs(a - b) for a, b in zip(normal, real))


def test_dialog_remembers_the_fine_rhythm_option():
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from core import settings
    from gui.midi_import_slide_dialog import MidiImportSlideDialog
    settings.set_midi_import_fine_rhythm(False)
    dialog = MidiImportSlideDialog()
    dialog.rhythm_check.setChecked(True)
    dialog._accept()
    assert settings.get_midi_import_fine_rhythm()
    settings.set_midi_import_fine_rhythm(False)
