"""
Fase 4 di ST-language 2.4: micro-timing (shift=N in millisecondi),
accordatura in cent (tune=N, anche con rampe), piu' di 16 canali (porte
MIDI in export, import e riproduzione) e ponte verso il formato MTXT.
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core.model import Project

SOUNDFONT = "/usr/share/sounds/sf2/TimGM6mb.sf2"


def _many(n, last_text="4r"):
    p = Project(name="t", tempo_bpm=60)
    p.add_track("T0", "Trumpet", "4a*4")
    for i in range(1, n - 1):
        p.add_track(f"T{i}", "Trumpet", "4r")
    p.add_track(f"T{n - 1}", "Trumpet", last_text)
    return p


# ------------------------------------------------------------------ porte MIDI

def _ports(path):
    import mido
    out = []
    for track in mido.MidiFile(path).tracks:
        port = next((m.port for m in track if m.type == "midi_port"), None)
        channel = next((m.channel for m in track if hasattr(m, "channel")), None)
        if channel is not None:
            out.append((port, channel))
    return out


def test_up_to_15_tracks_write_no_port(tmp_path):
    from core.midi_export import export_project_to_midi
    path = str(tmp_path / "a.mid")
    export_project_to_midi(_many(15), path, only_audible=False)
    assert all(port is None for port, _c in _ports(path))


def test_more_tracks_go_to_the_next_port(tmp_path):
    import st_language as st
    from core.midi_export import export_project_to_midi
    app, lib = str(tmp_path / "app.mid"), str(tmp_path / "lib.mid")
    p = _many(17)
    export_project_to_midi(p, app, only_audible=False)
    assert _ports(app)[14:] == [(0, 15), (1, 0), (1, 1)]
    song = "Tempo: 60 BPM\n\n" + "".join(f"Traccia {t.name} [Trumpet]:\n  {t.text}\n\n" for t in p.tracks)
    st.to_midi(st.read_song(song), lib)
    assert _ports(lib) == _ports(app)


def test_import_keeps_tracks_on_different_ports_apart(tmp_path):
    from core.midi_export import export_project_to_midi
    from core.midi_import import import_midi_file
    path = str(tmp_path / "a.mid")
    p = _many(18, last_text="4c*5")
    p.tracks[15].text = "4e*5"
    export_project_to_midi(p, path, only_audible=False)
    imported = import_midi_file(path)
    assert len(imported.tracks) == 3      # le tracce di sole pause non si importano


@pytest.mark.skipif(not os.path.exists(SOUNDFONT), reason="SoundFont di prova assente")
def test_playback_renders_each_port_on_its_own(tmp_path, monkeypatch):
    import numpy as np
    from core import playback
    from core.midi_export import export_project_to_midi
    if playback._shared_synth is None:
        pytest.skip("libreria FluidSynth non installata")
    monkeypatch.setenv("SOUNDTEXT_SOUNDFONT", SOUNDFONT)
    path = str(tmp_path / "a.mid")
    # la traccia 16 (porta 1, canale 1) alza il bend: sulla porta 0 il la non cambia
    export_project_to_midi(_many(16, last_text="bend=2 4r"), path, only_audible=False)
    samples, rate = playback.render_midi_file_to_samples(path)
    x = samples[rate // 2: rate * 3 // 2, 0]
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    peak = np.fft.rfftfreq(len(x), 1 / rate)[np.argmax(spectrum)]
    assert min(abs(peak - 440 * k) for k in range(1, 6)) < 8      # un'armonica del la, non del si


# ------------------------------------------------------------------ shift= e tune=

from core.notation import parse_track_text, tokenize, transpose_tokens, validate_track_text  # noqa: E402


def test_shift_is_a_state_that_moves_the_following_notes():
    events = [e for e in parse_track_text("c shift=-20 d { e ; f } kick shift=0 g", {}) if e.kind != "rest"]
    assert [(e.letter or e.name, e.shift) for e in events] == \
        [("c", None), ("d", -20), ("e", -20), ("f", -20), ("kick", -20), ("g", None)]
    assert [e.start for e in events] == [0, 1, 2, 2, 3, 4]        # il ritmo scritto non cambia


def test_tune_is_an_automation_with_ramps():
    events = [e for e in parse_track_text("tune=-30 >> 2c tune=50", {}) if e.kind == "control"]
    assert [(e.name, e.value, e.start_value, e.duration) for e in events] == \
        [("tune", -30, None, 0), ("tune", 50, -30, 2)]


@pytest.mark.parametrize("text", ["shift=501 c", "shift=-501 c", "shift=1.5 c", "tune=101 c", "tune=-101 c"])
def test_shift_and_tune_errors(text):
    assert not validate_track_text(text, {})[0]


def test_rewrites_keep_shift_and_tune():
    assert transpose_tokens(tokenize("shift=-10 c tune=20 d"), 2, 4) == ["shift=-10", "d*4", "tune=20", "e*4"]


def _midi(path):
    import mido
    out = []
    for track in mido.MidiFile(path).tracks:
        now = 0
        for msg in track:
            now += msg.time
            if msg.type == "note_on" and msg.velocity:
                out.append((now, "on", msg.note))
            elif msg.type == "control_change" and msg.control in (6, 38, 100, 101):
                out.append((now, msg.control, msg.value))
    return out


def test_app_midi_shift_uses_the_tempo_and_tune_is_rpn_1(tmp_path):
    from core.midi_export import export_project_to_midi
    p = Project(name="t", tempo_bpm=120)
    p.add_track("A", "Piano", "4: c shift=-50 d tempo=60 shift=25 e tune=-50 f")
    path = str(tmp_path / "a.mid")
    export_project_to_midi(p, path)
    msgs = _midi(path)
    assert [t for t, kind, _n in msgs if kind == "on"] == [0, 480 - 48, 960 + 12, 1440 + 12]
    tune = [(c, v) for t, c, v in msgs if c != "on" and t == 1440]
    assert tune == [(101, 0), (100, 1), (6, 32), (38, 0), (101, 127), (100, 127)]   # -50 cent = 4096


def test_starting_mid_song_applies_the_tuning(tmp_path):
    from core.midi_export import export_project_to_midi
    p = Project(name="t")
    p.add_track("A", "Piano", "4: tune=100 c d e f")
    path = str(tmp_path / "a.mid")
    export_project_to_midi(p, path, start_offset_beats=2)
    assert [(c, v) for t, c, v in _midi(path) if t == 0 and c in (6, 38)] == [(6, 127), (38, 127)]


def test_library_midi_matches_the_app(tmp_path):
    import st_language as st
    from core.midi_export import export_project_to_midi
    text = "4: c shift=-30 d tune=-20 >> 2e tune=40 shift=15 f tempo=90 g shift=0 a"
    app, lib = str(tmp_path / "app.mid"), str(tmp_path / "lib.mid")
    p = Project(name="t", tempo_bpm=120)
    p.add_track("A", "Piano", text)
    export_project_to_midi(p, app)
    st.to_midi(st.read_song(f"Tempo: 120 BPM\n\nTraccia A [Piano]:\n  {text}\n"), lib)
    assert _midi(lib) == _midi(app)


def test_boxes_reset_the_shift():
    from core.arrangement import flatten_clips_to_text
    from core.model import Clip
    clips = [Clip(name="A", text="shift=-20 c d", start_beat=0.0), Clip(name="B", text="e", start_beat=2.0)]
    text = flatten_clips_to_text(clips, {}, 4)
    assert [e.shift for e in parse_track_text(text, {}) if e.kind == "note"] == [-20, -20, None]


def test_highlighter_colours_shift_and_tune():
    from PySide6.QtWidgets import QApplication, QPlainTextEdit
    QApplication.instance() or QApplication([])
    from gui.highlighter import NotationHighlighter, _COLORS
    editor = QPlainTextEdit()
    editor.setPlainText("shift=-10 tune=20 c")
    h = NotationHighlighter(editor.document())
    h.rehighlight()
    colours = {(f.start, f.length): f.format.foreground().color().name()
               for f in editor.document().firstBlock().layout().formats()}
    dark = {k: v[0] for k, v in _COLORS.items()}
    assert colours[(0, 9)] == dark["state"] and colours[(10, 7)] == dark["state"]


# ------------------------------------------------------------------ MTXT

SONG = """Tempo: 100 BPM
Tonalita: Am

Traccia Piano [Piano]:
  4: vol=40 >>exp c d vol=110 pan=-0.5 e< f$tr | swing=60 8: c d e f tune=-30 >> g a tune=30 2b |

Traccia Basso [Bass]:
  4: bend=-2 >> 2c bend=2 2r | c*2( d e f) |

Traccia Batteria [Drums]:
  4: kick snare kick snare | kick snare 2r |
"""


def _channel_messages(tracks, with_bend=False):
    out = []
    for i, track in enumerate(tracks[1:]):
        for tick, _p, m in track:
            kind = m[0] & 0xF0
            if m[0] >= 0xF0 or (kind == 0xB0 and m[1] in (0, 6, 38, 100, 101)) or (kind == 0xE0) != with_bend:
                continue
            if kind == 0x90 and m[2] == 0:
                kind = 0x80
            out.append((tick, i, kind, m[1], m[2] if kind not in (0x80, 0xC0) else 0))
    return sorted(out)


def test_mtxt_export_reads_well():
    import st_language as st
    from st_language.mtxt import song_to_mtxt
    text = song_to_mtxt(st.read_song(SONG))
    lines = text.splitlines()
    assert lines[0] == "mtxt 1.0" and "meta global key A minor" in lines
    assert "alias kick C2" in lines and "alias snare D2" in lines
    assert "0.0 tempo 100.0" in lines and "0.0 timesig 4/4" in lines
    assert "ch=0" in lines and "meta name Piano" in lines
    assert "0.0 voice piano_acoustic, Acoustic Grand Piano" in lines
    assert "0.0 note kick dur=1.0 vel=0.62993" in lines
    assert any(line.startswith("0.0 cc pitch -2.0") for line in lines)


def test_mtxt_round_trip_gives_the_same_midi():
    import st_language as st
    from st_language.midi import song_midi_tracks
    from st_language.mtxt import mtxt_to_midi_tracks, song_to_mtxt
    song = st.read_song(SONG)
    direct = song_midi_tracks(song)[0]
    again = mtxt_to_midi_tracks(song_to_mtxt(song))
    assert _channel_messages(again) == _channel_messages(direct)

    def semitones(tracks, bend_range):
        return {(t, i): round(((v | msb << 7) - 8192) / 8192 * bend_range, 2)
                for t, i, _k, v, msb in _channel_messages(tracks, with_bend=True)}
    direct_bends, mtxt_bends = semitones(direct, 24), semitones(again, 12)
    assert all(mtxt_bends[key] == value for key, value in direct_bends.items() if key[1] == 1)


def test_mtxt_reader():
    from st_language.mtxt import mtxt_to_midi_tracks
    text = """mtxt 1.0
meta global title Sunrise // commento
alias Cmaj7 C4,E4,G4,B4
0.0 tempo 100
ch=2
dur=0.5
vel=0.5
meta name Lead
0.0 voice piano, Electric Piano 1
1.0 note Cmaj7 dur=2.0
0.0 note bb3+60
0.0 cc volume 0.0
4.0 cc volume 1.0 transition_time=2.0
3.0 meta lyric la
4.0 note C4 ch=20
"""
    tracks = mtxt_to_midi_tracks(text)
    assert tracks[0][0][2] == b"\xff\x03\x07Sunrise"
    lead = sorted(tracks[1], key=lambda e: (e[0], e[1]))
    assert (0, 1, b"\xff\x03\x04Lead") in lead
    assert (0, 1, bytes([0xC2, 4])) in lead                                  # Electric Piano 1
    notes = [(t, m[1], m[2]) for t, _p, m in lead if m[0] == 0x92]
    assert notes == [(0, 59, 64), (480, 60, 64), (480, 64, 64), (480, 67, 64), (480, 71, 64)]
    volume = [(t, m[2]) for t, _p, m in lead if m[0] == 0xB2 and m[1] == 7]
    assert volume[0] == (0, 0) and volume[-1] == (1920, 127) and volume[1][0] > 960
    assert any(m == b"\xff\x05\x02la" for _t, _p, m in lead)
    assert [m for _t, _p, m in tracks[2] if m[:2] == b"\xff\x21"] == [b"\xff\x21\x01\x01"]     # canale 20: porta 1


@pytest.mark.parametrize("text", ["", "note C4", "mtxt 2.0", "mtxt 1.0\n0.0 note C4",
                                  "mtxt 1.0\nch=0\n0.0 note H4", "mtxt 1.0\nch=0\n0.0 jump C4",
                                  "mtxt 1.0\nch=0\n0.0 note C11"])
def test_mtxt_errors(text):
    from st_language.mtxt import MtxtError, mtxt_to_midi_tracks
    with pytest.raises(MtxtError):
        mtxt_to_midi_tracks(text)


def test_app_mtxt_export_and_import(tmp_path):
    from core.mtxt_io import export_project_to_mtxt, import_mtxt_file
    p = Project(name="Prova", tempo_bpm=90)
    p.key = "G"
    p.add_track("Melodia", "Trumpet", "4: g a b c | 2d 2r |")
    p.add_track("Ritmo", "Drums", "4: kick snare kick snare |")
    path = str(tmp_path / "a.mtxt")
    export_project_to_mtxt(p, path)
    q = import_mtxt_file(path)
    assert q.name == "Prova" and q.tempo_bpm == 90 and q.key == "G"
    assert [(t.name, t.instrument_name) for t in q.tracks] == [("Melodia", "Trumpet"), ("Ritmo", "Drums")]
    assert [(e.letter, e.octave, e.start) for e in parse_track_text(q.tracks[0].text, {}) if e.kind == "note"] == \
        [("g", 4, 0), ("a", 4, 1), ("b", 4, 2), ("c", 4, 3), ("d", 4, 4)]


def test_cli_mtxt(tmp_path, capsys):
    from st_language.cli import main
    song = tmp_path / "s.st"
    song.write_text(SONG, encoding="utf-8")
    assert main(["mtxt", str(song)]) == 0
    mtxt = tmp_path / "s.mtxt"
    assert mtxt.read_text(encoding="utf-8").startswith("mtxt 1.0\n")
    assert main(["mtxt", str(mtxt), "-o", str(tmp_path / "back.mid")]) == 0
    assert (tmp_path / "back.mid").read_bytes()[:4] == b"MThd"
    bad = tmp_path / "bad.mtxt"
    bad.write_text("mtxt 1.0\n0.0 note C4\n", encoding="utf-8")
    assert main(["mtxt", str(bad)]) == 1
