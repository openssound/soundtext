"""
Bilancia i volumi (core.auto_balance): i ruoli delle tracce (del brano generato o indovinati dalle note), i volumi che
portano ogni traccia al livello del suo ruolo rispetto alla melodia, la scrittura nei blocchi «Mixer» del testo, la prova
col suono vero (se c'e' un SoundFont), il motore del telefono e il bottone del computer con Annulla.
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import auto_balance as ab                         # noqa: E402
from core.project_io import parse_project_text                # noqa: E402

HAND = """ST: 2.6
Tempo: 100 BPM

Piano:
  4: [c*4 e*4 g*4] [c*4 e*4 g*4] [f*4 a*4 c*5] [g*4 b*4 d*5] |

Strings:
  1: [c*4 e*4 g*4] | [f*4 a*4 c*5] |

Bass:
  4: c*2 g*2 f*2 g*2 |

Flute:
  4: e*5 g*5 a*5 g*5 |

Drums:
  4: kick snare kick snare |
"""


def test_roles_of_a_hand_written_song_are_guessed_from_the_notes():
    project = parse_project_text(HAND, "x")
    assert ab.track_roles(project, HAND) == {"Drums": "drums", "Bass": "bass", "Flute": "melody", "Piano": "comp",
                                             "Strings": "pad"}


def test_roles_of_a_generated_song_are_its_parts():
    from core import quicksong as q
    song = q.quick_song({"genre": "disco", "seed": 11, "duration": 30})
    roles = ab.track_roles(parse_project_text(song["text"], "x"), song["text"])
    inst = song["choices"]["instruments"]
    assert roles[inst["melody"]] == "melody" and roles[inst["bass"]] == "bass" and roles["Drums"] == "drums"
    assert ab.quick_parts("// niente\nPiano:\n") is None


def test_volumes_bring_each_role_to_its_level_and_leave_the_melody():
    project = parse_project_text(HAND, "x")
    roles = ab.track_roles(project, HAND)
    # tutti allo stesso livello: la melodia resta a 100, il tappeto scende di 10 dB, il basso di 2
    volumes = ab.target_volumes(project, {name: -30.0 for name in roles}, roles)
    assert "Flute" not in volumes or volumes["Flute"] == 100
    assert volumes["Strings"] == round(100 * 10 ** (-10 / ab.SLOPE_DB))
    assert volumes["Bass"] == round(100 * 10 ** (-2 / ab.SLOPE_DB))
    # una traccia che non suona (None) non si tocca; il volume resta fra MIN_VOLUME e MAX_VOLUME
    loud = ab.target_volumes(project, {"Flute": -30.0, "Bass": None, "Strings": +60.0}, roles)
    assert "Bass" not in loud and loud["Strings"] == ab.MIN_VOLUME


def test_volumes_are_written_in_the_mixer_blocks_without_touching_the_rest():
    text = HAND.replace("Drums:", "Mixer Piano:\n  volume: 100 pan: -20 mute: no solo: no\n\nDrums:")
    out = ab.set_volumes_in_text(text, {"Piano": 80, "Strings": 70})
    project = parse_project_text(out, "x")
    assert project.find_track("Piano").volume == 80 and project.find_track("Strings").volume == 70
    assert project.find_track("Piano").pan != 64                              # il resto del blocco resta
    assert out.replace("volume: 80", "volume: 100").replace("Mixer Strings:\n  volume: 70\n\n", "") == text
    # un nome con lo spazio («Guitar 1»): si cambia il suo blocco, non se ne aggiunge un altro
    spaced = "Mixer Guitar 1:\n  volume: 72 pan: 0 mute: no solo: no\n"
    assert ab.set_volumes_in_text(spaced, {"Guitar 1": 77}) == spaced.replace("72", "77")


def test_balancing_with_the_real_sound_reaches_the_targets():
    from core import quicksong as q
    song = q.quick_song({"genre": "pop", "seed": 11, "duration": 30})
    project = parse_project_text(song["text"], "x")
    try:
        ab.balance_project(project, song["text"])
        levels = ab.measure_levels(project, list(ab.track_roles(project, song["text"])))
    except RuntimeError as e:                                                 # niente SoundFont o fluidsynth
        pytest.skip(str(e))
    if not any(v is not None for v in levels.values()):
        pytest.skip("niente suono")
    roles = ab.track_roles(project, song["text"])
    melody = levels[song["choices"]["instruments"]["melody"]]
    for name, level in levels.items():
        if level is None or project.find_track(name).volume in (ab.MIN_VOLUME, ab.MAX_VOLUME):
            continue
        assert abs((level - melody) - ab.ROLE_OFFSETS[roles[name]]) < 1.5, (name, level - melody)


def test_phone_engine_gives_roles_and_writes_the_volumes():
    sys.path.insert(0, os.path.join(ROOT, "mobile"))
    try:
        import engine
    finally:
        sys.path.remove(os.path.join(ROOT, "mobile"))
    roles = engine.balance_roles(HAND)["roles"]
    assert roles["Strings"] == "pad"
    out = engine.balance_apply(HAND, {name: -30.0 for name in roles})
    assert out["changes"]["Strings"][0] == 100 and out["changes"]["Strings"][1] < 100
    assert parse_project_text(out["text"], "x").find_track("Strings").volume == out["changes"]["Strings"][1]


def test_the_balance_button_changes_the_volumes_and_undo_restores(monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from gui.main_window import MainWindow
    QApplication.instance() or QApplication([])
    win = MainWindow()
    win.project = parse_project_text(HAND, "x")
    win.refresh_mixer()
    win._mark_dirty()

    def fake_balance(project, text="", passes=2, stop_check=None):
        project.find_track("Strings").volume = 60
        return {"Strings": (100, 60)}
    monkeypatch.setattr(ab, "balance_project", fake_balance)
    assert win.balance_volumes() == {"Strings": (100, 60)}
    assert win.project.find_track("Strings").volume == 60
    assert win.master_strip.balance_btn is not None
    win.undo()
    assert win.project.find_track("Strings").volume == 100
    win._dirty = False                                  # niente domanda «salvare?» alla chiusura
    win.close()
