"""
Notazione ABC (standard 2.1): esportazione (st_language.abc) e importazione
(core.abc_import). Andata e ritorno con le stesse note; brani scritti come
nelle raccolte tradizionali: unita' di nota, ritmo puntato, terzine,
accordi, legature fra battute con le alterazioni, modi (Dmix, Ador),
ritornelli con finali 1./2., levare, piu' voci raggruppate con %%score,
testo cantato, batteria e chiavi all'ottava.
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys
import textwrap
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core.abc_export import project_to_abc
from core.abc_import import ABCError, import_abc_file, parse_abc
from core.model import Project


def _abc(text):
    return textwrap.dedent(text).strip() + "\n"


def _notes(score, pid=None):
    """(inizio, durata, nota MIDI) in quarti, dalla prima parte o da pid."""
    pid = pid or score.parts[0].pid
    return [(a, b - a, n) for a, b, n, _v in score.notes[pid]]


def _project(*tracks, key="C", tempo=100):
    project = Project(name="Prova", tempo_bpm=tempo, key=key)
    for name, instrument, text in tracks:
        project.add_track(name, instrument, text)
    return project


# ------------------------------------------------------------------ esportazione

def test_export_header_voices_and_instruments():
    text = project_to_abc(_project(("Melodia", "Trumpet", "4: c*5 d*5 e*5 f*5"),
                                   ("Basso", "Bass", "4: 4c*2"), ("Batteria", "Drums", "4: kick snare kick snare"),
                                   key="Am", tempo=96))
    lines = text.splitlines()
    assert lines[:5] == ["X:1", "T:Prova", "M:4/4", "L:1/8", "Q:1/4=96"]
    assert "K:Am" in lines
    assert 'V:T1 clef=treble name="Melodia"' in lines
    assert 'V:T2 clef=bass-8 name="Basso"' in lines          # basso: chiave all'ottava, note un'ottava sopra
    assert "%%MIDI program 56" in lines and "%%MIDI channel 10" in lines
    body = text.split("V:T2\n")[1]
    assert body.splitlines()[1].startswith("!mf!C,8")        # do2 scritto do3 in chiave bass-8
    drums = text.split("V:T3\n")[1].splitlines()[1]
    assert drums.startswith("C,,2 D,,2 C,,2 D,,2")             # cassa 36, rullante 38 (suoni GM)


def test_export_accidentals_follow_the_bar_in_every_octave():
    """Lo standard propaga l'alterazione a quella nota in tutte le ottave
    fino alla stanghetta: va riscritta solo quando cambia."""
    text = project_to_abc(_project(("M", "Trumpet", "8: f#*4 f#*5 f*4 f*4 | f#*4 b*4 bb*4 b*4"), key="F"))
    music = text.split("%%MIDI program 56\n")[1].splitlines()[0]
    assert music.startswith("!mf!^Ff =FF ^F=B _B=B")


def test_export_ties_across_bars_tuplets_and_voices():
    text = project_to_abc(_project(("M", "Trumpet", "4: 3c*5 2d*5 4T: e*5 f*5 g*5 4: { 2a*5 ; 2c*5 }")))
    assert "d2- | d2" in text                                  # la nota che scavalca la stanghetta
    assert "(3:2:3e2 f2 g2" in text
    assert "%%score (T1 T1v2)" in text and "V:T1v2" in text
    assert "x6 c2- | c2 x6 |]" in text                         # seconda voce: pause invisibili


def test_export_chord_symbols_lyrics_and_meter_change():
    project = _project(("Canto", "Trumpet", '4: c*5 d*5 e*5 f*5 | g*5 a*5 b*5\n"Ma- ri- a, sei"'),
                       ("Piano", "Piano", "4: 4Am | 3Dm"))
    project.metrica_changes = [(1, "4/4"), (2, "3/4")]
    text = project_to_abc(project)
    assert "w: Ma-ri-a, sei" in text
    assert '"Am"' in text and '"Dm"' in text
    assert "| [M:3/4] " in text


def test_export_reads_back_with_the_same_notes():
    project = _project(("Melodia", "Trumpet", "8: c*5 d*5 e*5 f#*5 2g*5 r a*5 | 4T: b*5 c*6 d*6 4: 2c*6"),
                       ("Piano", "Piano", "4: C Am 2F | 2G7 { 2c*5 ; e*4 f*4 }"),
                       ("Basso", "Bass", "4: 2c*2 2e*2 | 3f*2 g*2"),
                       ("Batteria", "Drums", "8: kick hihat snare hihat kick hihat snare hihat"), key="G")
    score = parse_abc(project_to_abc(project))
    original = {}
    for track in project.tracks:
        from st_language.musicxml import _track_items
        items, _ = _track_items(track.parsed_events(project.patterns), track.instrument, False, None)
        from core.instruments import PERCUSSION_MAP
        original[track.name] = sorted((i.start, i.end - i.start, p) for i in items for p in
                                      [x.midi for x in i.pitches] + [PERCUSSION_MAP[d] for d in i.drums])
    back = {p.name: sorted(_notes(score, p.pid)) for p in score.parts}
    assert back == original


# ------------------------------------------------------------------ importazione

def test_lengths_broken_rhythm_triplets_chords_and_ties():
    score = parse_abc(_abc("""
        X:1
        T:Prova
        M:4/4
        L:1/16
        K:Dm
        A2>B2 c2<d2 (3e2f2g2 a4- | a4 ^c4 c8 | [D8F8A8] z8 | _B,4 B,4 B4 =B4 |]
        """))
    assert score.title == "Prova" and score.key == "Dm"
    notes = _notes(score)
    assert notes[:4] == [(0, Fraction(3, 4), 69), (Fraction(3, 4), Fraction(1, 4), 70),
                         (1, Fraction(1, 4), 72), (Fraction(5, 4), Fraction(3, 4), 74)]
    assert [d for _s, d, _n in notes[4:7]] == [Fraction(1, 3)] * 3
    assert (3, 2, 81) in notes                                 # la legato oltre la stanghetta
    assert (5, 1, 73) in notes and (6, 2, 73) in notes          # c# vale per tutta la battuta
    assert [n for s, _d, n in notes if s == 8] == [62, 65, 69]
    assert [n for _s, _d, n in notes[-4:]] == [58, 58, 70, 71]  # B, bemolle in chiave, poi =B


def test_tied_note_keeps_its_accidental_in_the_next_bar():
    score = parse_abc("X:1\nM:2/4\nL:1/4\nK:C\nc ^F- | F2 |]\n")
    assert _notes(score) == [(0, 1, 72), (1, 3, 66)]


# i modi diventano la tonalita' maggiore con la stessa armatura (ST conosce
# solo maggiore e minore)
@pytest.mark.parametrize("key, expected", [("Dmix", "G"), ("Ador", "G"), ("Bb", "Bb"),
                                           ("F#m", "F#m"), ("E minor", "Em"), ("G lyd", "D")])
def test_key_signatures_and_modes(key, expected):
    score = parse_abc(f"X:1\nL:1/4\nK:{key}\nc|]\n")
    assert score.key == expected


def test_modal_key_alters_notes():
    score = parse_abc("X:1\nL:1/4\nK:Dmix\nc f B|]\n")     # Re misolidio: fa#, do naturale
    assert [n for _s, _d, n in _notes(score)] == [72, 78, 71]


def test_repeats_endings_pickup_and_tempo():
    score = parse_abc(_abc("""
        X:1
        T:Giga
        M:6/8
        L:1/8
        Q:3/8=100
        K:G
        |:D|G3 GAB|1A3 A2:|2B3 B2||
        """))
    starts = [(s, n) for s, _d, n in _notes(score)]
    # levare completata con una pausa (5/2), poi: battuta, finale 1, ritornello (levare, battuta), finale 2
    assert [n for _s, n in starts] == [62, 67, 67, 69, 71, 69, 69, 62, 67, 67, 69, 71, 71, 71]
    assert starts[0][0] == Fraction(5, 2)
    assert score.tempos[0] == (0, 150.0)                       # 100 alla semiminima puntata
    assert score.time_sigs == [(0, 6, 8)]


def test_default_unit_note_length_from_meter():
    assert _notes(parse_abc("X:1\nM:2/4\nK:C\nc|]\n"))[0][1] == Fraction(1, 4)    # 2/4 < 3/4: L=1/16
    assert _notes(parse_abc("X:1\nM:4/4\nK:C\nc|]\n"))[0][1] == Fraction(1, 2)


def test_voices_grouped_by_score_become_one_track(tmp_path):
    path = tmp_path / "corale.abc"
    path.write_text(_abc("""
        X:1
        T:Corale
        M:3/4
        L:1/4
        %%score {(S A) | (T B)}
        V:S clef=treble name="Soprano"
        V:A clef=treble
        V:T clef=bass name="Tenore"
        V:B clef=bass
        K:Eb
        [V:S] !p!G A B | c2 B |]
        w: Can-ti-a-mo in-sie-me
        [V:A] E F G | A2 G |]
        [V:T] B, C D | E2 D |]
        [V:B] E, F, G, | A,2 G, |]
        """), encoding="utf-8")
    project = import_abc_file(str(path))
    assert project.name == "Corale" and project.key == "Eb" and project.time_sig == "3/4"
    assert [t.name for t in project.tracks] == ["Soprano", "Tenore"]
    assert all(t.instrument.gm_program == 52 for t in project.tracks)   # voci: dal nome
    soprano = project.tracks[0].text
    assert '"Can- ti- a-"' in soprano or '"Can- ti- a- mo' in soprano
    score = parse_abc(path.read_text(encoding="utf-8"))
    assert [v for a, _b, n, v in score.notes["S"] if a == 0] == [49, 80]   # !p! sul soprano, non sul contralto


def test_piano_hands_and_midi_program(tmp_path):
    score = parse_abc(_abc("""
        X:1
        L:1/4
        %%score {RH | LH}
        V:RH clef=treble name="Piano"
        V:LH clef=bass
        K:C
        V:RH
        %%MIDI program 0
        c e g c' |]
        V:LH
        %%MIDI program 0
        C, G, C G, |]
        V:3 name="Flauto"
        %%MIDI program 73
        z4 |]
        """))
    assert [(p.name, p.program) for p in score.parts if score.notes[p.pid]] == [("Piano", 0)]
    assert len(score.notes["RH"]) == 8


def test_drums_clef_octave_transpose_and_chord_symbols():
    score = parse_abc(_abc("""
        X:1
        L:1/4
        V:G clef=treble-8 name="Chitarra"
        V:D clef=perc name="Batteria"
        %%MIDI channel 10
        K:C
        V:G
        "Am"E A "G/B"d "N.C."g |]
        V:D
        C,, D,, C,, D,, |]
        """))
    guitar, drums = score.parts
    assert [n for _s, _d, n in _notes(score, "G")] == [52, 57, 62, 67]    # un'ottava sotto lo scritto
    assert drums.is_drums and [n for _s, _d, n in _notes(score, "D")] == [36, 38, 36, 38]
    assert score.harmonies == [(0, "Am"), (2, "G/B"), (3, None)]


def test_lyrics_with_holds_skips_and_bars():
    score = parse_abc("X:1\nL:1/4\nK:C\nc d e f | g a b c' |]\nw: Ma-ri-a _ | * la\n")
    lyrics = score.lyrics[score.parts[0].pid]
    assert [s for _t, s in lyrics] == ["Ma-", "ri-", "a", "la"]
    assert [t for t, _s in lyrics] == [0, 1, 2, 5]


def test_errors_are_readable(tmp_path):
    with pytest.raises(ABCError):
        parse_abc("X:1\nT:Vuoto\nK:C\n")
    with pytest.raises(ABCError):
        import_abc_file(str(tmp_path / "manca.abc"))


def test_overlapping_unison_notes_are_not_lost(tmp_path):
    """Una nota tenuta in una voce e la stessa altezza ribattuta nell'altra:
    nel MIDI intermedio la prima si chiude dove riattacca la seconda."""
    path = tmp_path / "unisono.abc"
    path.write_text("X:1\nL:1/4\n%%score (A B)\nV:A\nV:B\nK:C\n[V:A] c4 |]\n[V:B] z2 c2 |]\n", encoding="utf-8")
    project = import_abc_file(str(path))
    events = [(e.start, e.duration) for e in project.tracks[0].parsed_events(project.patterns)
              if e.kind == "note"]
    assert sorted(events) == [(0.0, 2.0), (2.0, 2.0)]
