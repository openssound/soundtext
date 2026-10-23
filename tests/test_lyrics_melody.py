"""
Test di Melodia dal testo (core.lyrics_melody): sillabe e accenti
dell'italiano, una nota per sillaba con gli accenti sui tempi forti e le
sillabe scritte sotto le note.

Esecuzione:
    python3 -m pytest tests/test_lyrics_melody.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)

import os

import pytest

from core.lyrics_melody import lyric_lines, lyrics_to_melody, phrase_rhythm, stressed_index, syllabify
from core.notation import parse_track_text, validate_track_text
from core.rhythm_generate import extract_chords_from_track


@pytest.mark.parametrize("word, expected, stress", [
    ("casa", ["ca", "sa"], 0), ("paese", ["pa", "e", "se"], 1), ("strumento", ["stru", "men", "to"], 1),
    ("città", ["cit", "tà"], 1), ("perché", ["per", "ché"], 1), ("lassù", ["las", "sù"], 1),
    ("tristezza", ["tri", "stez", "za"], 1), ("cantare", ["can", "ta", "re"], 1),
    ("Ma-ri-a", ["Ma", "ri", "a"], 1), ("blu", ["blu"], 0), ("di", ["di"], None),
])
def test_syllables_and_stress(word, expected, stress):
    sylls = syllabify(word)
    assert sylls == expected and stressed_index(word, sylls) == stress


def test_stressed_syllables_fall_on_the_beat():
    line = lyric_lines("Nel blu dipinto di blu")[0]
    rhythm, beats = phrase_rhythm(line, 4.0)
    assert beats == 8.0 and len(rhythm) == len(line) == 7
    for (onset, _d), (_syl, stressed, _end) in zip(rhythm, line):
        if stressed:
            assert abs(onset - round(onset)) < 1e-9
    long_line = lyric_lines("questa e' una riga lunghissima con tantissime parole da cantare tutte quante")[0]
    assert phrase_rhythm(long_line, 4.0)[1] == 16.0              # non ci sta: quattro battute


def test_melody_with_the_lyrics_under_the_notes():
    chords = extract_chords_from_track("4: 4C 4Am 4F 4G", {})
    text = lyrics_to_melody("Nel blu dipinto di blu\nfelice di stare lassù", chords, "C", 5, 60, 81)
    assert validate_track_text(text, {})[0]
    notes = [e for e in parse_track_text(text, {}) if e.kind == "note"]
    assert [e.lyric for e in notes] == ["Nel", "blu", "di-", "pin-", "to", "di", "blu",
                                        "fe-", "li-", "ce", "di", "sta-", "re", "las-", "sù"]
    assert notes[7].start == 8.0                                    # seconda frase: battuta 3
    with pytest.raises(ValueError):
        lyrics_to_melody("   ", chords, "C", 5, 60, 81)


def test_dialog_from_the_track_menu(monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from core.model import Project
    from PySide6.QtWidgets import QDialogButtonBox
    from gui.rhythm_generate_dialog import LyricsMelodyDialog, chord_source_tracks
    p = Project(tempo_bpm=100)
    p.add_track("Accordi", "Piano", "4: 4C 4Am 4F 4G")
    p.add_track("Voce", "Trumpet", "")
    dlg = LyricsMelodyDialog(None, p, "Trumpet", "prova", chord_source_tracks(p, "Voce"), 5, 54, 82,
                             track_name="Voce")
    assert not dlg.button_box.button(QDialogButtonBox.Ok).isEnabled()
    dlg.lyrics_edit.setPlainText("volare oh oh\ncantare oh oh oh oh")
    text = dlg.preview_edit.toPlainText()
    assert '"vo- la- re oh oh"' in text and dlg.button_box.button(QDialogButtonBox.Ok).isEnabled()
    dlg.reject()
