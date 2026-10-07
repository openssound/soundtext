"""
Test per l'esportazione della partitura in MusicXML (core.musicxml_export):
battute sempre complete, note e legature, tuplet, sigle, armatura, chiavi,
batteria e dinamiche.

Esecuzione:
    python3 -m pytest tests/test_musicxml_export.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import glob
import os
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core.model import Project
from core.musicxml_export import export_project_to_musicxml, key_fifths, project_to_musicxml
from core.project_io import load_project_file

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _project(*tracks, key="", metrica=None):
    p = Project(name="Prova")
    for name, instrument, text in tracks:
        p.add_track(name, instrument, text)
    p.key = key
    if metrica:
        p.time_sig = metrica
    return p


def _parts(xml):
    return ET.fromstring(xml.split("\n", 2)[2]).findall("part")


def _notes(part):
    return [n for m in part.findall("measure") for n in m.findall("note")]


def _pitch(note):
    p = note.find("pitch")
    alter = p.find("alter")
    return p.find("step").text + {None: "", "1": "#", "-1": "b"}[None if alter is None else alter.text] \
        + p.find("octave").text


def _check_measures(xml):
    """Ogni battuta di ogni pentagramma dura esattamente quanto la metrica."""
    for part in _parts(xml):
        divisions = beats = None
        for m in part.findall("measure"):
            attrs = m.find("attributes")
            if attrs is not None:
                if attrs.find("divisions") is not None:
                    divisions = int(attrs.find("divisions").text)
                t = attrs.find("time")
                if t is not None:
                    beats = Fraction(4 * int(t.find("beats").text), int(t.find("beat-type").text))
            pos = high = 0
            for el in m:
                if el.tag == "note" and el.find("chord") is None:
                    pos += int(el.find("duration").text)
                elif el.tag == "backup":
                    pos -= int(el.find("duration").text)
                high = max(high, pos)
            assert Fraction(high, divisions) == beats, (part.get("id"), m.get("number"))
            assert Fraction(pos, divisions) == beats, (part.get("id"), m.get("number"))


def test_notes_rests_and_measures():
    xml = project_to_musicxml(_project(("Voce", "Trumpet", "4: c*5 d*5 r e*5 2: f*5 g*5")))
    _check_measures(xml)
    part = _parts(xml)[0]
    assert len(part.findall("measure")) == 2
    notes = _notes(part)
    pitched = [_pitch(n) for n in notes if n.find("pitch") is not None]
    assert pitched == ["C5", "D5", "E5", "F5", "G5"]
    assert [n.find("type").text for n in notes] == ["quarter", "quarter", "quarter", "quarter", "half", "half"]
    assert notes[2].find("rest") is not None
    assert part.find("measure/attributes/clef/sign").text == "G"


def test_note_across_the_barline_is_tied():
    xml = project_to_musicxml(_project(("Voce", "Trumpet", "2: r 1: c*5 r 2: r")))
    _check_measures(xml)
    c = [n for n in _notes(_parts(xml)[0]) if n.find("pitch") is not None]
    assert len(c) == 2 and [n.find("type").text for n in c] == ["half", "half"]
    assert [t.get("type") for t in c[0].findall("tie")] == ["start"]
    assert [t.get("type") for t in c[1].findall("tie")] == ["stop"]


def test_odd_durations_become_tied_values_and_dots():
    xml = project_to_musicxml(_project(("Voce", "Trumpet", "8: 6c*5 5d*5 5r")))
    _check_measures(xml)
    notes = [n for n in _notes(_parts(xml)[0]) if n.find("pitch") is not None]
    assert notes[0].find("type").text == "half" and len(notes[0].findall("dot")) == 1   # 6 crome
    # 5 crome dal terzo quarto: un quarto, poi un quarto puntato oltre la stanghetta
    assert [(n.find("type").text, len(n.findall("dot"))) for n in notes[1:]] == [("quarter", 0), ("quarter", 1)]
    assert [t.get("type") for t in notes[1].findall("tie")] == ["start"]


def test_unwritable_duration_inside_a_measure_is_split_and_tied():
    xml = project_to_musicxml(_project(("Voce", "Trumpet", "8: 5c*5 3r")))
    _check_measures(xml)
    notes = [n for n in _notes(_parts(xml)[0]) if n.find("pitch") is not None]
    assert [n.find("type").text for n in notes] == ["half", "eighth"]
    assert [t.get("type") for t in notes[0].findall("tie")] == ["start"]
    assert [t.get("type") for t in notes[1].findall("tie")] == ["stop"]


def test_menu_command_writes_the_file(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QFileDialog
    QApplication.instance() or QApplication([])
    from gui.main_window import MainWindow
    w = MainWindow()
    w.project.add_track("Piano", "Piano", "4: C F G C")
    from gui.command_palette import collect_commands
    assert ("Progetto › Esporta", "Partitura MusicXML...") in {(c.path, c.title) for c in collect_commands(w.menuBar())}
    target = str(tmp_path / "brano")                       # senza estensione: la aggiunge
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (target, "")))
    w.export_musicxml()
    xml = open(target + ".musicxml", encoding="utf-8").read()
    assert "<harmony>" in xml and "score-partwise" in xml


def test_triplets_get_time_modification_and_brackets():
    xml = project_to_musicxml(_project(("Voce", "Trumpet", "8T: c*5 d*5 e*5 f*5 g*5 a*5 4: r r")))
    _check_measures(xml)
    notes = [n for n in _notes(_parts(xml)[0]) if n.find("pitch") is not None]
    assert all(n.find("time-modification/actual-notes").text == "3" for n in notes)
    marks = [n.find("notations/tuplet").get("type") if n.find("notations/tuplet") is not None else None
             for n in notes]
    assert marks == ["start", None, "stop", "start", None, "stop"]
    beams = [n.find("beam").text if n.find("beam") is not None else None for n in notes]
    assert beams == ["begin", "continue", "end", "begin", "continue", "end"]


def test_chords_write_symbol_and_voiced_notes_on_two_staves():
    xml = project_to_musicxml(_project(("Piano", "Piano", "1: Cmaj7 C/E Am7 Am7")))
    _check_measures(xml)
    part = _parts(xml)[0]
    assert part.find("measure/attributes/staves").text == "2"
    harmonies = part.findall("measure/harmony")
    assert [(h.find("root/root-step").text, h.find("kind").get("text"), h.find("kind").text)
            for h in harmonies] == [("C", "maj7", "major-seventh"), ("C", "", "major"), ("A", "m7", "minor-seventh")]
    assert harmonies[1].find("bass/bass-step").text == "E"            # sigla slash
    assert len(harmonies) == 3                                        # Am7 ribattuto: una sola sigla
    notes = _notes(part)
    assert {n.find("staff").text for n in notes} == {"1", "2"} or {n.find("staff").text for n in notes} == {"1"}
    assert sum(1 for n in notes if n.find("pitch") is not None) >= 4 * 3


def test_key_signature_and_flat_spelling():
    assert key_fifths("C") == (0, "major")
    assert key_fifths("Am") == (0, "minor")
    assert key_fifths("Eb") == (-3, "major")
    assert key_fifths("F#") == (6, "major")
    assert key_fifths("Gb") == (-6, "major")
    assert key_fifths("Ebm") == (-6, "minor")
    assert key_fifths("") is None and key_fifths("H") is None
    xml = project_to_musicxml(_project(("Piano", "Piano", "1: Eb Ab Bb7 Eb"), key="Eb"))
    part = _parts(xml)[0]
    assert part.find("measure/attributes/key/fifths").text == "-3"
    spelled = {_pitch(n)[:-1] for n in _notes(part) if n.find("pitch") is not None}
    assert "Eb" in spelled and "D#" not in spelled and "G#" not in spelled


def test_written_accidentals_are_kept():
    xml = project_to_musicxml(_project(("Voce", "Trumpet", "4: c#*5 db*5 cb*5 e*5")))
    pitched = [_pitch(n) for n in _notes(_parts(xml)[0]) if n.find("pitch") is not None]
    assert pitched == ["C#5", "Db5", "Cb5", "E5"]


def test_guitar_and_bass_use_octave_clefs():
    xml = project_to_musicxml(_project(("Chit", "Guitar", "4: e*3 a*3 d*4 g*4"), ("Basso", "Bass", "1: e*2")))
    guitar, bass = _parts(xml)
    assert guitar.find("measure/attributes/clef/sign").text == "G"
    assert guitar.find("measure/attributes/clef/clef-octave-change").text == "-1"
    assert bass.find("measure/attributes/clef/sign").text == "F"
    assert bass.find("measure/attributes/clef/clef-octave-change").text == "-1"


def test_drums_are_unpitched_with_instruments():
    xml = project_to_musicxml(_project(("Batteria", "Drums", "8: [kick hihat] hihat [snare hihat] hihat "
                                                            "[kick hihat] hihat [snare hihat] hihat")))
    _check_measures(xml)
    root = ET.fromstring(xml.split("\n", 2)[2])
    instruments = {i.find("instrument-name").text for i in root.findall("part-list/score-part/score-instrument")}
    assert instruments == {"kick", "hihat", "snare"}
    part = root.find("part")
    assert part.find("measure/attributes/clef/sign").text == "percussion"
    assert part.find("measure/attributes/key") is None
    notes = _notes(part)
    assert all(n.find("unpitched") is not None for n in notes)
    heads = {n.find("instrument").get("id"): n.find("notehead") for n in notes}
    hihat_id = next(i.get("id") for i in root.findall("part-list/score-part/score-instrument")
                    if i.find("instrument-name").text == "hihat")
    assert heads[hihat_id].text == "x"
    assert not part.findall("measure/direction/direction-type/dynamics")


def test_dynamics_only_on_lasting_changes():
    text = "4: 49@ c*5 c*5 c*5 c*5 88@ c*5 49@ c*5 c*5 c*5 88@ c*5 c*5 c*5 c*5"
    xml = project_to_musicxml(_project(("Voce", "Trumpet", text)))
    marks = [d[0].tag for d in _parts(xml)[0].findall("measure/direction/direction-type/dynamics")]
    assert marks == ["p", "f"]


def test_tempo_and_meter_changes():
    p = _project(("Voce", "Trumpet", "4: " + " ".join(["c*5"] * 10)), metrica="3/4")
    p.tempo_bpm = 100
    xml = project_to_musicxml(p)
    _check_measures(xml)
    part = _parts(xml)[0]
    assert part.find("measure/attributes/time/beats").text == "3"
    assert part.find("measure/direction/sound").get("tempo") == "100"
    assert len(part.findall("measure")) == 4


def test_audio_tracks_and_muted_tracks_are_left_out(tmp_path):
    p = _project(("Voce", "Trumpet", "4: c*5"), ("Muta", "Piano", "4: c*4"))
    p.add_audio_track("Registrazione")
    p.get_track("Muta").mute = True
    path = export_project_to_musicxml(p, str(tmp_path / "prova.musicxml"))
    xml = open(path, encoding="utf-8").read()
    assert [sp.find("part-name").text for sp in ET.fromstring(xml.split("\n", 2)[2]).findall("part-list/score-part")] \
        == ["Voce"]


@pytest.mark.parametrize("path", sorted(glob.glob(os.path.join(ROOT, "examples", "*.st"))))
def test_examples_export_complete_measures(path):
    _check_measures(project_to_musicxml(load_project_file(path)))
