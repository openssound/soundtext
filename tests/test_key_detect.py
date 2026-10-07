"""
Test di core.key_detect.detect_key_of_text: la tonalita' di un singolo box,
proposta da "Genera giro armonico" per il box successivo.

Esecuzione:
    python3 -m pytest tests/test_key_detect.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.key_detect import detect_key_of_text
from core.rhythm_generate import PROGRESSION_STYLES, generate_chord_progression, parse_key

KEYS = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B",
        "Cm", "C#m", "Dm", "Ebm", "Em", "Fm", "F#m", "Gm", "G#m", "Am", "Bbm", "Bm"]


@pytest.mark.parametrize("style", sorted(PROGRESSION_STYLES))
def test_every_generated_progression_is_recognised_in_every_key(style):
    """Anche i casi ambigui con la relativa (Am F C G), i giri che restano
    piu' a lungo fuori dalla tonica (Cm Bb Ab Bb) e quelli che non partono
    dalla tonica (II-V-I)."""
    mode = PROGRESSION_STYLES[style]["mode"]
    for key in (k for k in KEYS if parse_key(k)[1] == mode):
        for variability in (0.0, 0.6, 1.0):
            for bars in (0, 8):
                text = generate_chord_progression(key, style, bars=bars, variability=variability, seed=1)
                found = detect_key_of_text(text, {})
                assert found is not None and parse_key(found)[:2] == parse_key(key)[:2], \
                    (style, key, variability, bars, text, found)


def test_melody_without_chords_uses_the_note_statistics():
    assert detect_key_of_text("4: a b c*5 d*5 e*5 c*5 a*2", {}) == "Am"
    assert detect_key_of_text("4: c d e f g e c*2", {}) == "C"


def test_nothing_to_analyse():
    assert detect_key_of_text("", {}) is None
    assert detect_key_of_text("4: 4r", {}) is None
