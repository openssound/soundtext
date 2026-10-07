"""
Test per core.notation.compute_token_spans: le posizioni evidenziate durante
la riproduzione vengono dal parser stesso, quindi coincidono con gli eventi
che si sentono per ogni sintassi (griglie ereditate, tuplet, slide, gruppi,
pattern) e un token non valido non fa sparire gli altri.

Esecuzione:
    python3 -m pytest tests/test_token_spans.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core.model import Project
from core.notation import compute_token_spans, parse_track_text
from core.project_io import load_project_file

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _spans(text, patterns=None):
    return [(text[cs:ce], start, dur) for cs, ce, start, dur in compute_token_spans(text, patterns or {})]


def test_state_commands_have_no_span_and_notes_follow_the_grid():
    assert _spans("8: 90@ c d 4: e") == [("c", 0.0, 0.5), ("d", 0.5, 0.5), ("e", 1.0, 1.0)]


def test_tuplets_slides_and_blocks():
    assert _spans("8T: c d e 4: 2c*4>d*4 [c e]") == [
        ("c", 0.0, pytest.approx(1 / 3)), ("d", pytest.approx(1 / 3), pytest.approx(1 / 3)),
        ("e", pytest.approx(2 / 3), pytest.approx(1 / 3)), ("2c*4>d*4", pytest.approx(1.0), 2.0),
        ("[c e]", pytest.approx(3.0), 1.0),
    ]


def test_group_and_pattern_cover_their_whole_expansion():
    p = Project()
    p.add_pattern("Riff", "8: c d e f")
    assert _spans("3(c r) %Riff g", p.patterns) == [("3(c r)", 0.0, 6.0), ("%Riff", 6.0, 2.0), ("g", 8.0, 0.5)]


def test_invalid_token_is_skipped_without_losing_the_others():
    assert _spans("c zzz d %Missing e") == [("c", 0.0, 1.0), ("d", 1.0, 1.0), ("e", 2.0, 1.0)]


@pytest.mark.parametrize("path", sorted(glob.glob(os.path.join(ROOT, "examples", "*.st"))))
def test_every_played_event_falls_inside_a_highlighted_span(path):
    project = load_project_file(path)
    for track in project.tracks:
        octave = track.instrument.default_octave
        spans = compute_token_spans(track.text, project.patterns, default_octave=octave)
        events = [e for e in parse_track_text(track.text, project.patterns, default_octave=octave)
                  if e.duration > 0]
        for ev in events:
            assert any(start - 1e-9 <= ev.start < start + dur - 1e-9 for _, _, start, dur in spans), \
                (os.path.basename(path), track.name, ev)
        ends = [start + dur for _, _, start, dur in spans]
        if events and ends:
            assert max(ends) == pytest.approx(max(e.start + e.duration for e in events))
