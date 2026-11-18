"""
Il tempo e' del brano: i cambi 'tempo=' e le corone scritti in una traccia
valgono per tutte, anche se quella traccia e' in mute o se se ne suona una
sola (il rendering degli strumenti SFZ e degli stem, una traccia alla
volta). Prima una traccia renderizzata da sola restava al tempo iniziale:
nella sinfonia l'orchestra finiva 40 secondi dopo i violini.

Esecuzione:
    python3 -m pytest tests/test_song_tempo.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

import mido

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.midi_export import export_project_to_midi  # noqa: E402
from core.project_io import parse_project_text  # noqa: E402
from core.tempo_map import build_tempo_beat_map, song_tempo_beat_map_heard  # noqa: E402

SONG = """ST: 2.6
Tempo: 60 BPM

Pattern %Veloce:
  tempo=120 4: c d e f |

Traccia Guida [Piano]:

Box Guida "A" |0:
  4: c d e f |

Box Guida "B" |4:
  tempo=120 4: c d e f | g a b 4c*5$fermata |

Traccia Altra [Piano]:

Box Altra "A" |0:
  4: e f g a | b c*5 d*5 e*5 | f*5 g*5 a*5 4b*5 |
"""


def _length(project, path, tracks=None):
    export_project_to_midi(project, path, tracks=tracks)
    return mido.MidiFile(path).length


def test_a_track_alone_keeps_the_tempo_of_the_song(tmp_path):
    p = parse_project_text(SONG)
    other = next(t for t in p.tracks if t.name == "Altra")
    full = _length(p, str(tmp_path / "tutto.mid"))
    assert abs(_length(p, str(tmp_path / "altra.mid"), tracks=[other]) - full) < 0.01
    assert build_tempo_beat_map(p, tracks=[other]) == [(0.0, 60), (4.0, 120)]


def test_a_muted_track_still_sets_the_tempo(tmp_path):
    p = parse_project_text(SONG)
    full = _length(p, str(tmp_path / "tutto.mid"))
    next(t for t in p.tracks if t.name == "Guida").mute = True
    assert build_tempo_beat_map(p) == [(0.0, 60), (4.0, 120)]
    assert abs(_length(p, str(tmp_path / "senza_guida.mid")) - full) < 0.01


def test_a_fermata_slows_every_track():
    p = parse_project_text(SONG)
    heard = song_tempo_beat_map_heard(p)
    assert heard != build_tempo_beat_map(p)                    # la corona rallenta
    next(t for t in p.tracks if t.name == "Guida").mute = True
    assert song_tempo_beat_map_heard(p) == heard


def test_tempo_inside_a_pattern_counts_too():
    p = parse_project_text(SONG.replace('tempo=120 4: c d e f | g a b 4c*5$fermata |', '%Veloce'))
    other = next(t for t in p.tracks if t.name == "Altra")
    assert build_tempo_beat_map(p, tracks=[other]) == [(0.0, 60), (4.0, 120)]
