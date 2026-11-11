"""
SoundText Mobile, fase 2: i generatori del motore dell'app
(mobile/engine.py, generate) danno lo stesso testo delle finestre «Genera
...» di SoundText (gui/rhythm_generate_dialog.py) con gli stessi parametri
e lo stesso seme (criterio della fase 2). Le finestre si aprono senza
schermo (offscreen), si impostano come farebbe l'utente e si confronta il
testo dell'anteprima con quello del motore.

Esecuzione:
    python3 -m pytest tests/test_mobile_generators.py -v
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOBILE = os.path.join(ROOT, "mobile")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import _config_isolation  # noqa: F401,E402

import pytest  # noqa: E402

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication  # noqa: E402

_app = QApplication.instance() or QApplication([])

from core.instruments import get_instrument  # noqa: E402
from core.project_io import parse_project_text  # noqa: E402
from gui.rhythm_generate_dialog import (  # noqa: E402
    BassGenerateDialog, ChordProgressionDialog, DrumGenerateDialog, MelodyGenerateDialog,
)

sys.path.insert(0, MOBILE)
import engine  # noqa: E402
sys.path.remove(MOBILE)

SONG = """ST: 2.6
Tempo: 100 BPM
Metrica: 4/4
Tonalita: F

Piano:
  1: F | Dm7 | Gm7 | C7 | F | Bb | C7 | F |

Drums:
  16: kick r hihat r snare r hihat r kick r hihat r snare r hihat r |
"""

SEEDS = (1, 4242, 2 ** 31 - 7)


def _project():
    return parse_project_text(SONG, "Prova")


def _select(combo, value):
    index = combo.findData(value)
    assert index >= 0, value
    combo.setCurrentIndex(index)


def _text(dlg, seed):
    dlg._seed = seed
    dlg._overrides = []
    return dlg._compose_text()


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("key,style,chord_bars,ending", [
    ("F", "pop", 1.0, False), ("C", "jazz_251", 1.0, True), ("Bb", "blues_12", 2.0, False), ("Am", None, 0.5, True),
])
def test_progression_like_soundtext(seed, key, style, chord_bars, ending):
    dlg = ChordProgressionDialog(None, _project(), "Piano", "prova", default_bars=8, track_name="Giro")
    _select(dlg.key_combo, key)
    if style is None:
        style = dlg.style_combo.currentData()
    _select(dlg.style_combo, style)
    _select(dlg.chord_duration_combo, chord_bars)
    dlg.ending_check.setChecked(ending)
    expected = _text(dlg, seed)
    got = engine.generate(SONG, "progression", {"key": key, "style": style, "bars": 8, "chord_bars": chord_bars,
                                                "ending": ending, "seed": seed, "track": "Giro"})
    assert got == {"text": expected, "seed": seed}


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("style,intensity,ending", [("rock", "normal", False), ("funk", "full", True),
                                                    ("swing", "light", False), ("bossa", "build", True)])
def test_drums_like_soundtext(seed, style, intensity, ending):
    dlg = DrumGenerateDialog(None, _project(), "Drums", "prova", default_bars=8, track_name="Batteria")
    _select(dlg.style_combo, style)
    _select(dlg.intensity_combo, intensity)
    dlg.ending_check.setChecked(ending)
    expected = _text(dlg, seed)
    got = engine.generate(SONG, "drums", {"style": style, "bars": 8, "intensity": intensity, "ending": ending,
                                          "seed": seed, "track": "Batteria"})
    assert got["text"] == expected


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("style,intensity,performance,kick", [
    ("root", "normal", False, False), ("walking", "normal", True, False), ("root_fifth", "full", False, True),
])
def test_bass_like_soundtext(seed, style, intensity, performance, kick):
    project = _project()
    dlg = BassGenerateDialog(None, project, "Bass", "prova", [("Piano", project.get_track("Piano").text)],
                             default_bars=8, track_name="Basso")
    _select(dlg.style_combo, style)
    _select(dlg.intensity_combo, intensity)
    dlg.performance_check.setChecked(performance)
    if kick:
        _select(dlg.kick_combo, "Drums")
    expected = _text(dlg, seed)
    got = engine.generate(SONG, "bass", {"source": "Piano", "style": style, "bars": 8, "intensity": intensity,
                                         "performance": performance, "kick_track": "Drums" if kick else None,
                                         "seed": seed, "track": "Basso"})
    assert got["text"] == expected


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("instrument,style,performance", [
    ("Piano", "block_chords", False), ("Piano", "arpeggio_up", True), ("Guitar", "broken_chord", True),
])
def test_comping_like_soundtext(seed, instrument, style, performance):
    project = _project()
    profile = get_instrument(instrument)
    dlg = MelodyGenerateDialog(None, project, instrument, "prova", [("Piano", project.get_track("Piano").text)],
                               polyphonic=True, default_octave=profile.default_octave,
                               range_low=profile.range_low, range_high=profile.range_high,
                               default_bars=8, track_name="Accompagnamento")
    _select(dlg.style_combo, style)
    dlg.performance_check.setChecked(performance)
    expected = _text(dlg, seed)
    got = engine.generate(SONG, "comping", {"source": "Piano", "style": style, "bars": 8, "instrument": instrument,
                                            "performance": performance, "seed": seed,
                                            "track": "Accompagnamento"})
    assert got["text"] == expected


def test_without_a_seed_one_is_chosen_and_returned():
    first = engine.generate(SONG, "drums", {"bars": 2})
    assert isinstance(first["seed"], int)
    assert engine.generate(SONG, "drums", {"bars": 2, "seed": first["seed"]}) == first


def test_readable_errors():
    with pytest.raises(ValueError, match="accordi"):
        engine.generate("ST: 2.6\nTempo: 100 BPM\n\nPiano:\n  4: c d e f |\n", "bass", {"bars": 2})
    with pytest.raises(ValueError):
        engine.generate(SONG, "fisarmonica", {})
