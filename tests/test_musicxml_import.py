"""
Importazione MusicXML (core.musicxml_import): andata e ritorno con
l'esportazione di SoundText, e partiture scritte come le salvano MuseScore
e gli altri programmi: levare, legature di valore fra battute, ritornelli
con finali 1./2., strumenti traspositori, sigle (anche con alterazioni),
due voci sullo stesso pentagramma, abbellimenti, metronomo, dinamiche,
batteria, .mxl compresso e formato "timewise".
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core.model import Project
from core.musicxml_export import export_project_to_musicxml
from core.musicxml_import import (MeasureData, MusicXMLError, _play_order, import_musicxml_file,
                                  parse_score)
from core.notation import validate_track_text


def _score(parts_xml, part_list, title="Brano di prova"):
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" '
            f'"http://www.musicxml.org/dtds/partwise.dtd">\n'
            f'<score-partwise version="4.0"><work><work-title>{title}</work-title></work>'
            f'<part-list>{part_list}</part-list>{parts_xml}</score-partwise>')


def _note(step, octave, duration, typ="quarter", alter=None, extra="", voice=1):
    alter_xml = f"<alter>{alter}</alter>" if alter is not None else ""
    return (f"<note><pitch><step>{step}</step>{alter_xml}<octave>{octave}</octave></pitch>"
            f"<duration>{duration}</duration>{extra}<voice>{voice}</voice><type>{typ}</type></note>")


def _rest(duration, voice=1):
    return f"<note><rest/><duration>{duration}</duration><voice>{voice}</voice></note>"


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def _tracks(project):
    return {t.name: t for t in project.tracks}


ATTR = ('<attributes><divisions>2</divisions><key><fifths>0</fifths></key>'
        '<time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>')


# --------------------------------------------------------------- andata e ritorno

def test_round_trip_with_soundtext_export(tmp_path):
    p = Project(name="Andata e ritorno", tempo_bpm=100, key="Am")
    p.add_track("Melodia", "Trumpet", "4: a*4 c*5 2e*5 8: d*5 c*5 b*4 a*4 2g*4")
    p.add_track("Chitarra", "Guitar", "4: 2Am 2F 2C 2G")
    p.add_track("Batteria", "Drums", "8: kick hihat snare hihat kick kick snare hihat")
    path = str(tmp_path / "brano.musicxml")
    export_project_to_musicxml(p, path)
    q = import_musicxml_file(path)
    assert (q.name, q.tempo_bpm, q.key, q.time_sig) == ("Andata e ritorno", 100, "Am", "4/4")
    t = _tracks(q)
    assert t["Melodia"].instrument_name == "Trumpet"
    assert "4a*4 4c*5 8e*5 2d*5 2c*5 2b*4 2a*4 4g*4" in t["Melodia"].text
    assert "2kick 2hihat 2snare 2hihat" in t["Batteria"].text
    assert "8[a*3 c*4 e*4]" in t["Chitarra"].text
    # le sigle tornano come traccia "Accordi", muta: la chitarra suona gia' l'armonia
    assert t["Accordi"].text == "2: 1Am 1F 1C 1G" and t["Accordi"].mute
    for track in q.tracks:
        assert validate_track_text(track.text, q.patterns) == (True, "")


# --------------------------------------------------------------- partiture "esterne"

def _lead_sheet():
    harmony = ('<harmony><root><root-step>{0}</root-step>{1}</root><kind{2}>{3}</kind>{4}</harmony>')
    m1 = ('<measure number="0" implicit="yes">' + ATTR +
          '<direction><direction-type><metronome><beat-unit>quarter</beat-unit><per-minute>90</per-minute>'
          '</metronome></direction-type></direction>' +
          _note("G", 4, 2) + '</measure>')
    m2 = ('<measure number="1"><barline location="left"><repeat direction="forward"/></barline>' +
          harmony.format("C", "", "", "major", "") +
          '<direction><direction-type><dynamics><f/></dynamics></direction-type></direction>' +
          _note("C", 5, 4, "half") + _note("E", 5, 4, "half", extra='<tie type="start"/>') + '</measure>')
    m3 = ('<measure number="2"><barline location="left"><ending number="1" type="start"/></barline>' +
          harmony.format("G", "", ' text="7"', "dominant",
                         '<degree><degree-value>9</degree-value><degree-alter>-1</degree-alter>'
                         '<degree-type>add</degree-type></degree>') +
          _note("E", 5, 4, "half", extra='<tie type="stop"/>') + _note("D", 5, 4, "half") +
          '<barline location="right"><ending number="1" type="stop"/><repeat direction="backward"/></barline>'
          '</measure>')
    m4 = ('<measure number="3"><barline location="left"><ending number="2" type="start"/></barline>' +
          harmony.format("A", "", "", "minor-seventh", '<bass><bass-step>G</bass-step></bass>') +
          _note("C", 5, 8, "whole") +
          '<barline location="right"><ending number="2" type="stop"/>'
          '<bar-style>light-heavy</bar-style></barline></measure>')
    part = f'<part id="P1">{m1}{m2}{m3}{m4}</part>'
    part_list = ('<score-part id="P1"><part-name>Voce</part-name>'
                 '<midi-instrument id="P1-I1"><midi-program>57</midi-program></midi-instrument></score-part>')
    return _score(part, part_list, title="Lead sheet")


def test_lead_sheet_pickup_ties_repeats_and_chords(tmp_path):
    q = import_musicxml_file(_write(tmp_path, "lead.musicxml", _lead_sheet()))
    assert q.name == "Lead sheet" and q.tempo_bpm == 90
    t = _tracks(q)
    # levare: la battuta 0 (un quarto) e' completata con 3 quarti di pausa;
    # poi battute 1, 2 (1. finale), di nuovo 1, infine 3 (2. finale). La
    # legatura Mi-Mi unisce la fine della battuta 1 al 1. finale (4 quarti),
    # ma non al 2. finale, che riparte con un Do; il forte vale dalla battuta 1.
    assert t["Voce"].text == "16: " + "r " * 12 + "80@ 4g*4 88@ 8c*5 16e*5 8d*5 8c*5 8e*5 16c*5"
    # sigle: C (b.1), G7b9 (1. finale), C (ripresa), Am7/G (2. finale); con
    # una sola parte (lead sheet) la traccia degli accordi si sente
    assert t["Accordi"].text == "1: 1r 1C 1G7b9 1C 1Am7/G" and not t["Accordi"].mute


def test_transposing_instrument_sounds_at_concert_pitch(tmp_path):
    part = ('<part id="P1"><measure number="1">' + ATTR +
            '<attributes><transpose><diatonic>-1</diatonic><chromatic>-2</chromatic></transpose></attributes>' +
            _note("D", 5, 8, "whole") + '</measure></part>')
    part_list = ('<score-part id="P1"><part-name>Clarinetto in Sib</part-name>'
                 '<midi-instrument id="P1-I1"><midi-program>72</midi-program></midi-instrument></score-part>')
    score = parse_score(_write(tmp_path, "cl.musicxml", _score(part, part_list)))
    assert [n[2] for n in score.notes["P1"]] == [72]          # Re scritto = Do reale
    assert score.parts[0].program == 71


def test_two_voices_chords_grace_notes_and_drums(tmp_path):
    voices = ('<measure number="1">' + ATTR +
              _note("E", 5, 4, "half") + _note("G", 5, 4, "half", extra="<chord/>") + _note("F", 5, 4, "half") +
              '<backup><duration>8</duration></backup>' +
              '<note><grace/><pitch><step>B</step><octave>3</octave></pitch><voice>2</voice><type>eighth</type></note>' +
              _note("C", 4, 8, "whole", voice=2) + '</measure>')
    drums = ('<measure number="1"><attributes><divisions>1</divisions><time><beats>4</beats>'
             '<beat-type>4</beat-type></time><clef><sign>percussion</sign></clef></attributes>' +
             ''.join('<note><unpitched><display-step>F</display-step><display-octave>4</display-octave></unpitched>'
                     f'<duration>1</duration><instrument id="{iid}"/><voice>1</voice><type>quarter</type></note>'
                     for iid in ("P2-K", "P2-S", "P2-K", "P2-S")) + '</measure>')
    part_list = ('<score-part id="P1"><part-name>Pianoforte</part-name></score-part>'
                 '<score-part id="P2"><part-name>Batteria</part-name>'
                 '<score-instrument id="P2-K"><instrument-name>Kick</instrument-name></score-instrument>'
                 '<score-instrument id="P2-S"><instrument-name>Snare</instrument-name></score-instrument>'
                 '<midi-instrument id="P2-K"><midi-channel>10</midi-channel><midi-unpitched>37</midi-unpitched></midi-instrument>'
                 '<midi-instrument id="P2-S"><midi-channel>10</midi-channel><midi-unpitched>39</midi-unpitched></midi-instrument>'
                 '</score-part>')
    path = _write(tmp_path, "duo.musicxml",
                  _score(f'<part id="P1">{voices}</part><part id="P2">{drums}</part>', part_list))
    score = parse_score(path)
    assert sorted(n[2] for n in score.notes["P1"]) == [60, 76, 77, 79]      # niente acciaccatura (Si)
    assert score.parts[0].program == 0                                          # Pianoforte dal nome
    assert [n[2] for n in score.notes["P2"]] == [36, 38, 36, 38]
    q = import_musicxml_file(path)
    names = [t.name for t in q.tracks]
    assert names == ["Pianoforte", "Batteria"]           # le due voci nella stessa traccia
    assert "{" in _tracks(q)["Pianoforte"].text
    assert "4kick 4snare 4kick 4snare" in _tracks(q)["Batteria"].text


def test_compressed_mxl_and_timewise(tmp_path):
    xml = _lead_sheet()
    mxl = tmp_path / "lead.mxl"
    with zipfile.ZipFile(mxl, "w") as z:
        z.writestr("META-INF/container.xml",
                   '<?xml version="1.0"?><container><rootfiles>'
                   '<rootfile full-path="score/lead.xml"/></rootfiles></container>')
        z.writestr("score/lead.xml", xml)
    a = import_musicxml_file(str(mxl))
    b = import_musicxml_file(_write(tmp_path, "lead.musicxml", xml))
    assert [t.text for t in a.tracks] == [t.text for t in b.tracks]

    timewise = ('<?xml version="1.0"?><score-timewise><part-list><score-part id="P1"><part-name>Basso</part-name>'
                '</score-part></part-list><measure number="1"><part id="P1">' + ATTR.replace("G</sign><line>2", "F</sign><line>4") +
                _note("C", 2, 8, "whole") + '</part></measure><measure number="2"><part id="P1">' +
                _note("G", 2, 8, "whole") + '</part></measure></score-timewise>')
    score = parse_score(_write(tmp_path, "tw.xml", timewise))
    assert [(n[0], n[2]) for n in score.notes["P1"]] == [(0, 36), (4, 43)]
    assert score.parts[0].program == 33                                         # Basso dal nome


def test_errors_are_readable(tmp_path):
    with pytest.raises(MusicXMLError):
        import_musicxml_file(_write(tmp_path, "rotto.musicxml", "<score-partwise><part"))
    with pytest.raises(MusicXMLError):
        import_musicxml_file(_write(tmp_path, "altro.xml", "<html><body/></html>"))
    with pytest.raises(MusicXMLError):
        import_musicxml_file(_write(tmp_path, "vuoto.musicxml", _score("", "")))


@pytest.mark.parametrize("spec,expected", [
    (["", "F", "", "B"], [0, 1, 2, 3, 1, 2, 3]),
    (["", "", "B", ""], [0, 1, 2, 0, 1, 2, 3]),
    (["F", "", "1BS", "2S", ""], [0, 1, 2, 0, 1, 3, 4]),
    (["F", "1", "BS", "2", "S", ""], [0, 1, 2, 0, 3, 4, 5]),
    (["F", "B3", ""], [0, 1, 0, 1, 0, 1, 2]),
    (["F", "1BS", "2S", "F", "1BS", "2S"], [0, 1, 0, 2, 3, 4, 3, 5]),
    # D.C. al Fine; minuetto (ritornello, poi D.C. senza ritornelli fino a Fine)
    (["", "", "N", "", "", "C"], [0, 1, 2, 3, 4, 5, 0, 1, 2]),
    (["F", "", "B", "", "N", "", "", "C"], [0, 1, 2, 0, 1, 2, 3, 4, 5, 6, 7, 0, 1, 2, 3, 4]),
    # D.S. al Coda: dal segno (1) fino a "al Coda" (3), poi la Coda (6)
    (["", "G", "", "T", "", "D", "K", ""], [0, 1, 2, 3, 4, 5, 1, 2, 3, 6, 7]),
    # dopo un D.C. si suona l'ultimo finale
    (["F", "", "1BS", "2S", "C"], [0, 1, 2, 0, 1, 3, 4, 0, 1, 3, 4]),
])
def test_repeat_unrolling(spec, expected):
    measures = []
    for code in spec:
        m = MeasureData()
        m.forward_repeat = "F" in code
        m.backward_repeat = 3 if "B3" in code else (2 if "B" in code else 0)
        m.endings = [1] if "1" in code else ([2] if "2" in code else None)
        m.ending_stop = "S" in code
        m.da_capo, m.dal_segno, m.segno = "C" in code, "D" in code, "G" in code
        m.fine, m.to_coda, m.coda = "N" in code, "T" in code, "K" in code
        measures.append(m)
    assert _play_order(measures) == expected


def test_main_window_imports_a_score_as_new_project(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from gui.main_window import MainWindow
    w = MainWindow()
    w._import_musicxml_as_new_project(_write(tmp_path, "lead.musicxml", _lead_sheet()))
    assert w.project.name == "Lead sheet" and not w._dirty
    assert "lead.musicxml" in w.windowTitle()
    assert [t.name for t in w.project.tracks] == ["Voce", "Accordi"]
    assert all(t.clips for t in w.project.tracks)            # subito visibili nella vista Struttura
    from gui.command_palette import collect_commands
    assert ("Progetto › Importa", "MusicXML...") in {(c.path, c.title) for c in collect_commands(w.menuBar())}
    w.close()


def test_jumps_written_only_as_text(tmp_path):
    words = '<direction><direction-type><words>{0}</words></direction-type></direction>'
    m = lambda num, step, extra="": (f'<measure number="{num}">' + (ATTR if num == 1 else "") + extra +
                                     _note(step, 4, 8, "whole") + '</measure>')
    part = ('<part id="P1">' + m(1, "C") + m(2, "D", words.format("Fine")) +
            m(3, "E", words.format("D.C. al Fine")) + '</part>')
    score = parse_score(_write(tmp_path, "dc.musicxml",
                               _score(part, '<score-part id="P1"><part-name>Piano</part-name></score-part>')))
    assert [n[2] for n in score.notes["P1"]] == [60, 62, 64, 60, 62]
