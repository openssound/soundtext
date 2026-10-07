"""Le sinfonie a box suonano esattamente come quelle a testo."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _config_isolation  # noqa: E402,F401

import pytest  # noqa: E402

from core.project_io import load_project_file  # noqa: E402

EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
PAIRS = [("sinfonia_re_minore.st", "sinfonia_re_minore_box.st"),
         ("sinfonia_do_minore.st", "sinfonia_do_minore_box.st")]


def _events(project, track):
    meter = project.meter()
    out = []
    for e in track.parsed_events(project.patterns, meter=meter):
        if e.kind == "rest":
            continue
        out.append((e.kind, e.letter, e.octave, e.symbol, e.bass, e.name, round(e.start, 6),
                    round(e.duration, 6), e.velocity, e.bpm, e.value, e.articulation))
    return sorted(out, key=lambda k: (k[6], str(k)))


@pytest.mark.parametrize("plain,boxed", PAIRS)
def test_boxed_symphony_sounds_like_the_text_one(plain, boxed):
    a = load_project_file(os.path.join(EXAMPLES, plain))
    b = load_project_file(os.path.join(EXAMPLES, boxed))
    assert [t.name for t in a.tracks] == [t.name for t in b.tracks]
    assert a.tempo_bpm == b.tempo_bpm and a.time_sig == b.time_sig
    assert not any(t.clips for t in a.tracks)
    assert all(t.clips for t in b.tracks)
    for ta, tb in zip(a.tracks, b.tracks):
        assert _events(a, ta) == _events(b, tb), ta.name


@pytest.mark.parametrize("plain,boxed", PAIRS)
def test_boxes_are_in_order_and_do_not_overlap(plain, boxed):
    from core.arrangement import clip_duration_beats
    b = load_project_file(os.path.join(EXAMPLES, boxed))
    for t in b.tracks:
        end = 0.0
        for clip in sorted(t.clips, key=lambda c: c.start_beat):
            assert clip.start_beat >= end - 1e-9, (t.name, clip.name)
            end = clip.start_beat + clip_duration_beats(clip.text, b.patterns, t.instrument.default_octave)
