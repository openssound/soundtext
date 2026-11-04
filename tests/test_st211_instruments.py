"""Strumenti con st-language 2.11: un nome in italiano, francese o spagnolo
prende il suo strumento, uno sconosciuto suona come pianoforte solo per la
sessione (non finisce in instruments.json e l'avviso torna a ogni apertura),
e i pianoforti salvati dalle versioni vecchie si possono correggere."""

import pytest

from core import instruments, settings
from core.instruments import (InstrumentProfile, all_instruments, instrument_suggestion,
                              legacy_instrument_fix, make_instrument_available,
                              pending_instrument_fixes, replace_custom_instrument)
from core.project_io import parse_project_text, project_to_text


@pytest.fixture(autouse=True)
def _clean_instruments():
    """Ogni test parte senza strumenti personalizzati ne' risposte salvate."""
    def reset():
        for name in list(instruments._load_custom_instruments()):
            instruments.remove_custom_instrument(name)
        instruments._unresolved_instruments.clear()
        settings._load()
        settings._cache.pop("instrument_fixes_accepted", None)
        settings._cache.pop("instrument_fixes_declined", None)
    reset()
    yield
    reset()


def _song(instrument):
    return f"Tempo: 120 BPM\n\nTraccia Melodia [{instrument}]:\n  4: c d e f |\n"


def _legacy_piano(name):
    return InstrumentProfile(name=name, gm_program=0, is_percussion=False, default_octave=4,
                             range_low=21, range_high=108, polyphonic=True, voicing_style="spread")


def test_italian_name_gets_its_instrument():
    project = parse_project_text(_song("Flauto"))
    instr = project.get_track("Melodia").instrument
    assert instr.resolved and instr.gm_program == 73
    assert project.file_warnings == []
    assert "Flauto" in all_instruments()


def test_unknown_instrument_is_not_saved_and_warns_every_time():
    for _ in range(2):
        project = parse_project_text(_song("Flautoo"))
        instr = project.get_track("Melodia").instrument
        assert not instr.resolved and instr.gm_program == 0
        assert "Flautoo" not in all_instruments()
        assert project.file_warnings == [(3, instruments.unknown_instrument_message("Flautoo"))]
        assert "flauto" in project.file_warnings[0][1]
    # salvato e riletto: niente blocco "Strumento Flautoo:", l'avviso resta
    text = project_to_text(project)
    assert "Strumento Flautoo" not in text
    assert parse_project_text(text).file_warnings


def test_suggestion_makes_the_track_playable():
    assert instrument_suggestion("Flautoo") == "Flauto"
    assert instrument_suggestion("Pianno") == "Piano"     # predefinito: com'e' scritto li'
    assert instrument_suggestion("xyzzy") is None
    project = parse_project_text(_song("Flautoo"))
    assert make_instrument_available("Flauto")
    project.update_track("Melodia", "Melodia", "Flauto")
    assert project.get_track("Melodia").instrument.gm_program == 73


def test_legacy_piano_is_fixed_only_when_the_name_is_now_known():
    replace_custom_instrument(_legacy_piano("Flauto"))
    replace_custom_instrument(_legacy_piano("MioPiano"))                 # nome sconosciuto
    replace_custom_instrument(InstrumentProfile(name="Ottavino", gm_program=72, default_octave=5))
    fixes = pending_instrument_fixes()
    assert [f.name for f in fixes] == ["Flauto"]
    assert fixes[0].gm_program == 73
    assert pending_instrument_fixes(declined=["Flauto"]) == []


def test_legacy_bassoon_basso_is_fixed():
    old = InstrumentProfile(name="Basso", gm_program=70, default_octave=3, range_low=34, range_high=75,
                            polyphonic=False, voicing_style="monophonic")
    fresh = legacy_instrument_fix(old)
    assert fresh is not None and fresh.gm_program != 70


def test_accepted_fix_applies_to_songs_that_embed_the_old_piano():
    song = ("Strumento Flauto:\n"
            "  program=0 percussione=no ottava=4 range=21-108 poly=si voicing=spread\n\n"
            + _song("Flauto"))
    assert parse_project_text(song).get_track("Melodia").instrument.gm_program == 0
    settings.record_instrument_fix("Flauto", True)
    assert parse_project_text(song).get_track("Melodia").instrument.gm_program == 73
