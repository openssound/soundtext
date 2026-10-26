"""Le sinfonie a box: ogni traccia ha i suoi box, in fila e senza sovrapporsi."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _config_isolation  # noqa: E402,F401

import pytest  # noqa: E402

from core.project_io import load_project_file  # noqa: E402

EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
BOXED = ["sinfonia_re_minore_box.st"]


@pytest.mark.parametrize("boxed", BOXED)
def test_boxes_are_in_order_and_do_not_overlap(boxed):
    from core.arrangement import clip_duration_beats
    b = load_project_file(os.path.join(EXAMPLES, boxed))
    assert b.tracks and all(t.clips for t in b.tracks)
    for t in b.tracks:
        end = 0.0
        for clip in sorted(t.clips, key=lambda c: c.start_beat):
            assert clip.start_beat >= end - 1e-9, (t.name, clip.name)
            end = clip.start_beat + clip_duration_beats(clip.text, b.patterns, t.instrument.default_octave)
