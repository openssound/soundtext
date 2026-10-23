"""ST-language 2.10 dentro SoundText: il blocco "Conversione Nome:" dice da
quale traccia audio e' nata una traccia di note e con quali scelte, per
Riconverti. Lettura, scrittura, versione del file e tracce rinominate o
tolte."""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest  # noqa: E402

from core.audio_quantize import QuantizeSettings  # noqa: E402
from core.audio_track_notation import (  # noqa: E402
    ConversionOptions, conversion_record, converted_from, options_from_conversion,
)
from core.model import Project  # noqa: E402
from core.project_io import parse_project_text, project_to_text  # noqa: E402


def _project(conversion=True):
    p = Project(name="p", tempo_bpm=96)
    p.add_audio_track("Voce")
    notes = p.add_track("Voce (note)", "Trumpet", "4: c d e f")
    if conversion:
        options = ConversionOptions(mode="melody", grid_denominator=8, ternary=True,
                                    quantize=QuantizeSettings(strength=0.8, swing=0.5))
        notes.conversion = conversion_record("Voce", options)
    return p


def test_conversion_is_written_and_read_back():
    text = project_to_text(_project())
    assert text.startswith("ST: 2.10\n")
    assert 'Conversione Voce (note):\n  da="Voce" griglia=8 terzine forza=80\n' in text
    back = parse_project_text(text)
    assert back.get_track("Voce (note)").conversion == _project().get_track("Voce (note)").conversion
    assert back.get_track("Voce (note)").text == "4: c d e f"     # il blocco non finisce nelle note
    assert project_to_text(back) == text


def test_files_without_conversions_keep_their_version():
    assert project_to_text(_project(conversion=False)).startswith("ST: 2.8\n")


def test_a_link_to_a_missing_audio_track_is_not_written():
    p = _project()
    p.remove_track("Voce")
    assert p.get_track("Voce (note)").conversion is None
    p = _project()
    p.get_track("Voce (note)").conversion["from"] = "Altro"
    text = project_to_text(p)
    assert "Conversione" not in text and text.startswith("ST: 2.8\n")


def test_renaming_the_audio_track_follows_the_link():
    p = _project()
    p.update_track("Voce", "Canto", "Audio")
    assert p.get_track("Voce (note)").conversion["from"] == "Canto"
    assert [t.name for t in converted_from(p, "Canto")] == ["Voce (note)"]
    p.update_track("Voce (note)", "Melodia", "Trumpet")
    assert 'Conversione Melodia:\n  da="Canto"' in project_to_text(p)


def test_english_aliases_and_blocks_that_do_not_fit_are_ignored():
    text = """ST: 2.10
Tempo: 96 BPM

Traccia Voce [Audio]:

Traccia Tromba [Trumpet]:
  4: c d e f
Conversion Tromba:
  from="Voce" mode=chords sevenths

Conversione Nessuna:
  da="Voce"

Conversione Voce:
  da="Voce"

Traccia Piano [Piano]:
  4: c

Conversione Piano:
  da="Tromba"
"""
    p = parse_project_text(text)
    conversion = p.get_track("Tromba").conversion
    assert conversion["from"] == "Voce" and conversion["mode"] == "chords" and conversion["sevenths"]
    assert p.get_track("Tromba").text == "4: c d e f"
    assert p.get_track("Voce").conversion is None                  # una traccia audio non e' convertita
    assert p.get_track("Piano").conversion is None                 # da= non e' una traccia audio


@pytest.mark.parametrize("options", [
    ConversionOptions(mode="drums", grid_denominator=16, voice_source=True,
                      quantize=QuantizeSettings(strength=0.5, window=0.4, swing=0.66,
                                                min_note_sec=0.03, merge_gap_sec=0.02)),
    ConversionOptions(mode="chords", grid_denominator=16, sevenths=True),
])
def test_options_survive_the_record(options):
    back = options_from_conversion(conversion_record("Voce", options))
    assert (back.mode, back.grid_denominator, back.ternary, back.sevenths, back.voice_source) == \
        (options.mode, options.grid_denominator, options.ternary, options.sevenths, options.voice_source)
    if options.mode == "chords":
        assert back.quantize is None
    else:
        assert back.quantize == options.quantize
