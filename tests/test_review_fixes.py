"""
Test di regressione per i bug trovati nella revisione del codice del
2026-09-24 (un test per ciascun caso, riprodotto prima della correzione).

Esecuzione:
    python3 -m pytest tests/test_review_fixes.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mido
import pytest

from core import playback
from core.chords import pitch_to_midi, transpose_pitch
from core.midi_export import export_project_to_midi
from core.model import Project
from core.notation import NotationError, compute_token_spans, parse_track_text, validate_track_text
from core.project_io import parse_project_text
from core.rhythm_generate import extract_chords_from_track, generate_bass_from_chords, generate_melodic_line
from core.tempo_map import build_tempo_beat_map


def _abs_messages(midi_track):
    tick = 0
    out = []
    for msg in midi_track:
        tick += msg.time
        out.append((tick, msg))
    return out


def _note_events(path, track_index=1):
    return [(tick, msg.type, msg.note) for tick, msg in _abs_messages(mido.MidiFile(path).tracks[track_index])
            if msg.type in ("note_on", "note_off")]


def _assert_no_same_pitch_overlap(events):
    """Ogni note_on di un'altezza deve essere preceduto dal note_off della
    nota precedente della stessa altezza (nessuna sovrapposizione)."""
    active = set()
    for _tick, kind, note in events:
        if kind == "note_on":
            assert note not in active, f"nota {note} riattaccata mentre suona ancora"
            active.add(note)
        else:
            assert note in active, f"note_off {note} senza note_on"
            active.discard(note)


# ------------------------------------------------------------ export MIDI

def test_resume_offset_starts_with_the_tempo_active_at_the_offset(tmp_path):
    project = parse_project_text("Tempo: 1: 60, 5: 180, 9: 90\nMetrica: 4/4\n\n[Piano]\n40c\n")
    path = str(tmp_path / "out.mid")
    export_project_to_midi(project, path, start_offset_beats=16)
    tempos = [(tick, round(mido.tempo2bpm(msg.tempo))) for tick, msg in _abs_messages(mido.MidiFile(path).tracks[0])
              if msg.type == "set_tempo"]
    # Battuta 5 = beat 16 (tempo 180 dal punto di ripresa), battuta 9 = beat 32 -> 16 beat dopo l'offset.
    assert tempos == [(0, 180), (16 * 480, 90)]


def test_legato_note_does_not_cut_the_next_note_of_same_pitch(tmp_path):
    project = Project()
    project.add_track("P", "Piano", "c_ c")
    path = str(tmp_path / "out.mid")
    export_project_to_midi(project, path)
    events = _note_events(path)
    _assert_no_same_pitch_overlap(events)
    assert events[-1] == (960, "note_off", 60)
    assert (480, "note_on", 60) in events


def test_humanize_never_overlaps_repeated_notes(tmp_path):
    project = Project()
    project.add_track("B", "Bass", "8: " + " ".join(["c*2"] * 64))
    path = str(tmp_path / "out.mid")
    for _ in range(5):
        export_project_to_midi(project, path, humanize=True, humanize_amount=100)
        _assert_no_same_pitch_overlap(_note_events(path))


# ------------------------------------------------------------ metrica/tempo

def test_single_metrica_is_used_for_bar_offsets():
    project = parse_project_text("Tempo: 1: 100, 3: 140\nMetrica: 3/4\n\n[Piano]\nc d e f g a\n")
    assert build_tempo_beat_map(project) == [(0.0, 100), (6.0, 140)]


def test_metrica_list_not_starting_at_bar_one_keeps_4_4_before_it():
    project = parse_project_text("Tempo: 1: 100, 3: 140\nMetrica: 5: 3/4\n\n[Piano]\nc\n")
    assert build_tempo_beat_map(project) == [(0.0, 100), (8.0, 140)]


# ------------------------------------------------------------ altezze

def test_out_of_range_note_is_a_notation_error_not_an_export_crash(tmp_path):
    ok, msg = validate_track_text("c a*9", {})
    assert not ok and "a*9" in msg
    with pytest.raises(NotationError):
        parse_track_text("c*4>a*9", {})
    assert validate_track_text("g*9", {})[0]


def test_chord_voicing_out_of_range_does_not_crash_export(tmp_path):
    project = Project()
    project.add_track("P", "Piano", "C*9")
    export_project_to_midi(project, str(tmp_path / "out.mid"))


def test_cb_and_b_sharp_keep_the_right_octave(tmp_path):
    assert pitch_to_midi("cb", 4) == 59
    assert pitch_to_midi("b#", 4) == 72
    assert transpose_pitch("cb", 4, 0) == ("b", 3)
    project = Project()
    project.add_track("P", "Piano", "cb*4 b#*4 [cb*4 e*4]")
    path = str(tmp_path / "out.mid")
    export_project_to_midi(project, path)
    assert [note for _, kind, note in _note_events(path) if kind == "note_on"] == [59, 72, 59, 64]


# ------------------------------------------------------------ notazione

def test_tempo_ramp_without_events_still_applies_the_final_tempo():
    events = parse_track_text("tempo=120 >> tempo=140 c d", {})
    markers = [(e.start, e.bpm) for e in events if e.kind == "tempo_marker"]
    assert markers[-1] == (0.0, 140)


def test_token_spans_inherit_the_current_grid_in_groups_and_patterns():
    spans = compute_token_spans("8: 4(c d) e", {})
    assert [(start, dur) for _, _, start, dur in spans] == [(0.0, 4.0), (4.0, 0.5)]

    project = Project()
    project.add_pattern("Riff", "c d")
    project.add_pattern("Grid", "16: c")
    spans = compute_token_spans("8: %Riff e", project.patterns)
    assert [(start, dur) for _, _, start, dur in spans] == [(0.0, 1.0), (1.0, 0.5)]
    # Una griglia cambiata dentro il pattern vale anche per i token successivi.
    spans = compute_token_spans("%Grid e", project.patterns)
    assert [(start, dur) for _, _, start, dur in spans] == [(0.0, 0.25), (0.25, 0.25)]
    assert parse_track_text("%Grid e", project.patterns)[-1].start == 0.25


# ------------------------------------------------------------ generatore

def _duration_beats(text):
    events = parse_track_text(text, {})
    return max(e.start + e.duration for e in events)


@pytest.mark.parametrize("style", ["root", "walking", "eighths", "shuffle"])
def test_generated_bass_stays_aligned_with_uneven_chords(style):
    chords = extract_chords_from_track("8: 3C 3F 2G 3C 3F 2G", {})
    assert _duration_beats(generate_bass_from_chords(chords, style)) == pytest.approx(8.0)


def test_generated_comping_stays_aligned_with_uneven_chords():
    chords = extract_chords_from_track("8: 3C 3F 2G 3C 3F 2G", {})
    text = generate_melodic_line(chords, "quarter_chords", 4, 40, 90, polyphonic=True)
    assert _duration_beats(text) == pytest.approx(8.0)


# ------------------------------------------------------------ playback

def test_stop_during_backend_selection_prevents_the_old_player_from_starting(monkeypatch):
    """Uno stop() che arriva mentre il thread di riproduzione ha gia'
    superato i suoi controlli ma non ha ancora avviato il processo non deve
    lasciar partire l'audio."""
    reached = threading.Event()
    proceed = threading.Event()
    main_thread = threading.current_thread()

    def fake_which(name):
        if name == "timidity":
            if threading.current_thread() is not main_thread:
                reached.set()
                proceed.wait(5)
            return "/usr/bin/timidity"
        return None

    spawned = []
    monkeypatch.setattr(playback, "_shared_synth", None)
    monkeypatch.setattr(playback.shutil, "which", fake_which)
    monkeypatch.setattr(playback.subprocess, "Popen", lambda *a, **k: spawned.append(a))

    engine = playback.PlaybackEngine()
    engine.play_file("/nonexistent.mid")
    assert reached.wait(5)
    engine.stop()
    proceed.set()
    engine._thread.join(5)
    assert spawned == []


def test_cb_and_b_sharp_chords_keep_the_right_octave():
    from core.chords import parse_chord_symbol, voice_chord
    from core.instruments import get_instrument
    piano = get_instrument("Piano")
    assert min(voice_chord(parse_chord_symbol("Cb"), 4, piano, voicing_override="close")) == 59
    assert min(voice_chord(parse_chord_symbol("B#"), 4, piano, voicing_override="close")) == 72
    assert min(voice_chord(parse_chord_symbol("B"), 3, piano, voicing_override="close")) == 59
