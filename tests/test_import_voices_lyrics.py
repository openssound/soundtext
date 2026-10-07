"""
Import MIDI e MusicXML: le voci sovrapposte di un canale restano nella
stessa traccia come blocchi { ; } (core.voice_merge), senza cambiare una
nota; il testo cantato (eventi lyrics, file karaoke, sillabe MusicXML con
strofe e ritornelli) diventa testo fra virgolette (core.import_lyrics).
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys
import textwrap
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mido

from core.import_lyrics import add_lyrics, midi_text, midi_text_bytes, syllables
from core.midi_import import import_midi_channel_into_track, import_midi_file
from core.notation import notation_warnings, parse_track_text
from core.voice_merge import check_round_trip, merge_voices, merged_text


def _notes(text):
    return [(e.letter, e.octave, e.start, e.duration, e.voice, e.lyric)
            for e in parse_track_text(text, {}) if e.kind == "note"]


# ------------------------------------------------------------------ unione delle voci

def test_one_voice_is_unchanged():
    assert merge_voices([["4:", "c", "d"]]) == ["4:", "c", "d"]
    assert merge_voices([["4:", "c", "d"], []]) == ["4:", "c", "d"]


def test_block_only_where_the_second_voice_plays():
    v1 = "16: 80@ 4c*4 4d*4 4e*4 4f*4 16g*4 4a*4 4b*4".split()
    v2 = "16: 80@ 32r 8c*3 8g*2".split()
    text = merged_text([v1, v2])
    assert text == "16: 80@ 4c*4 4d*4 4e*4 4f*4 16g*4\n{ 4a*4 4b*4 ; 16: 80@ 8c*3 8g*2 }"
    assert check_round_trip([v1, v2], text)


def test_block_starts_on_the_bar_line_with_a_rest():
    v1 = "4: c d e f g a b c".split()
    v2 = "4: 5r 3g*3".split()                       # entra a meta' della seconda battuta
    text = merged_text([v1, v2])
    assert text == "4: c d e f\n{ g a b c ; 4: r'4 3g*3 }"
    assert check_round_trip([v1, v2], text)


def test_a_held_note_widens_the_block():
    v1 = "4: c 4d e f".split()                      # la d tiene fino a meta' della battuta dopo
    v2 = "4: 2r 2g*3".split()
    text = merged_text([v1, v2])
    assert text.startswith("{ ") and check_round_trip([v1, v2], text)


def test_state_after_the_block_is_restored():
    v1 = "4: c d 8: e f g a 4: b c".split()
    v2 = "4: 2r 2g*3".split()
    text = merged_text([v1, v2], time_sig="2/4")
    assert check_round_trip([v1, v2], text)
    assert [n[2] for n in _notes(text) if n[4] == 1] == [0.0, 1.0, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0]


def test_main_voice_ending_early_is_filled_with_rests():
    v1 = "4: c d".split()
    v2 = "4: 8r 2e 12r 2g".split()
    text = merged_text([v1, v2])
    assert check_round_trip([v1, v2], text)


def test_odd_gap_uses_a_local_grid():
    from core.voice_merge import _rest_tokens_any
    assert _rest_tokens_any(Fraction(3, 2)) == ["r'4", "r'8"]
    assert _rest_tokens_any(Fraction(3, 20)) == ["{ 80: 3r }"]


# ------------------------------------------------------------------ testo dagli eventi MIDI

def test_syllable_conventions():
    # SoundText ("Ma" "ri" "a "), karaoke (" Ma" "ri" " a" con a capo '/'), trattino esplicito
    assert syllables([(0, "Ma"), (1, "ri"), (2, "a "), (3, "sei ")]) == [
        (0, "Ma-"), (1, "ri-"), (2, "a"), (3, "sei")]
    assert syllables([(0, "/Hap"), (1, "py"), (2, " birth"), (3, "day"), (4, "\\ to")]) == [
        (0, "Hap-"), (1, "py"), (2, "birth-"), (3, "day"), (4, "to")]
    assert syllables([(0, "lu-"), (1, "ce "), (2, 'il "re"')]) == [(0, "lu-"), (1, "ce"), (2, "il‿'re'")]


def test_utf8_lyrics_survive_the_midi_file():
    for text in ("città", "‿", "春"):
        assert midi_text(midi_text_bytes(text)) == text


def test_add_lyrics_one_line_per_bar_with_skips():
    tokens = "4: c d e f g a b c c d e f".split()
    lyrics = [(Fraction(0), "Ma-"), (Fraction(1), "ri-"), (Fraction(3), "a"), (Fraction(8), "fi-"), (Fraction(9), "ne")]
    out = add_lyrics(tokens, lyrics)
    assert " ".join(out) == '4: c d e f "Ma- ri- * a" g a b c "" c d e f "fi- ne"'
    assert [n[5] for n in _notes(" ".join(out))] == ["Ma-", "ri-", None, "a", None, None, None, None,
                                                       "fi-", "ne", None, None]


def _midi(path, track_events, ticks_per_beat=480):
    """track_events: per traccia [(tick, messaggio)]."""
    mid = mido.MidiFile(ticks_per_beat=ticks_per_beat)
    for events in track_events:
        track = mido.MidiTrack()
        now = 0
        for tick, msg in sorted(events, key=lambda e: (e[0], e[1].type != "note_off")):
            track.append(msg.copy(time=tick - now))
            now = tick
        mid.tracks.append(track)
    mid.save(path)


def _melody(notes, channel=0):
    out = []
    for tick, length, note in notes:
        out.append((tick, mido.Message("note_on", note=note, velocity=80, channel=channel)))
        out.append((tick + length, mido.Message("note_off", note=note, velocity=0, channel=channel)))
    return out


def test_midi_import_one_track_with_voices_and_lyrics(tmp_path):
    path = str(tmp_path / "canto.mid")
    events = [(0, mido.Message("note_on", note=40, velocity=80)), (1920, mido.Message("note_off", note=40, velocity=0))]
    events += _melody([(i * 240, 200, 60 + i) for i in range(8)])
    events += [(i * 240, mido.MetaMessage("lyrics", text=t)) for i, t in enumerate(
        ["Ma", "ri", "a ", "sei ", "qui ", "con ", "noi ", "ora "])]
    _midi(path, [events])
    project = import_midi_file(path)
    assert [t.name for t in project.tracks] == ["Piano"]
    notes = _notes(project.tracks[0].text)
    assert [n[5] for n in notes if n[4] == 1] == ["Ma-", "ri-", "a", "sei", "qui", "con", "noi", "ora"]
    assert [n[0] for n in notes if n[4] == 2] == ["e"]
    assert notation_warnings(project.tracks[0].text, {}) == []


def test_karaoke_text_events_in_a_track_without_notes(tmp_path):
    path = str(tmp_path / "karaoke.kar")
    words = ["@TTitolo", "/Can", "ta", " con", " me", " que", "sta", " can", "zo", "ne", " a", " voce"]
    lyric_track = [(0, mido.MetaMessage("text", text=words[0]))]
    lyric_track += [(i * 480, mido.MetaMessage("text", text=w)) for i, w in enumerate(words[1:])]
    melody = _melody([(i * 480, 400, 60 + i % 5) for i in range(11)], channel=1)
    other = _melody([(i * 960 + 240, 300, 48) for i in range(5)], channel=2)
    _midi(path, [lyric_track, melody, other])
    project = import_midi_file(path)
    sung = [t for t in project.tracks if '"' in t.text]
    assert len(sung) == 1
    lyrics = [n[5] for n in _notes(sung[0].text) if n[5]]
    assert lyrics == ["Can-", "ta", "con", "me", "que-", "sta", "can-", "zo-", "ne", "a", "voce"]


def test_single_channel_import_keeps_both_voices(tmp_path):
    path = str(tmp_path / "ov.mid")
    events = [(0, mido.Message("note_on", note=40, velocity=80)), (1920, mido.Message("note_off", note=40, velocity=0))]
    events += _melody([(i * 240, 200, 60 + i) for i in range(8)])
    _midi(path, [events])
    text, _instrument = import_midi_channel_into_track(path, 0)
    assert "{" in text and len(_notes(text)) == 9


# ------------------------------------------------------------------ MusicXML

def _musicxml(path, measures_xml, repeat=False):
    measures = "".join(
        f'<measure number="{n}">' + ("<attributes><divisions>1</divisions><time><beats>4</beats>"
                                     "<beat-type>4</beat-type></time></attributes>" if n == 1 else "")
        + body + ('<barline location="right"><repeat direction="backward"/></barline>'
                  if repeat and n == len(measures_xml) else "") + "</measure>"
        for n, body in enumerate(measures_xml, 1))
    with open(path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(f"""<?xml version="1.0" encoding="UTF-8"?>
            <score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Voce</part-name>
            </score-part></part-list><part id="P1">{measures}</part></score-partwise>"""))


def _note(step, lyric_xml="", duration=1, octave=5):
    return (f"<note><pitch><step>{step}</step><octave>{octave}</octave></pitch>"
            f"<duration>{duration}</duration><type>quarter</type>{lyric_xml}</note>")


def _lyric(text, syllabic="single", number="1", extra=""):
    return f'<lyric number="{number}"><syllabic>{syllabic}</syllabic><text>{text}</text>{extra}</lyric>'


def test_musicxml_lyrics_with_hyphens_and_elision(tmp_path):
    from core.musicxml_import import import_musicxml_file
    path = str(tmp_path / "canto.musicxml")
    elision = ('<lyric number="1"><syllabic>single</syllabic><text>a</text><elision/>'
               "<syllabic>single</syllabic><text>e</text></lyric>")
    _musicxml(path, [_note("C", _lyric("Ma", "begin")) + _note("D", _lyric("ri", "middle"))
                     + _note("E", _lyric("a", "end")) + _note("F", elision),
                     _note("G", duration=4)])
    project = import_musicxml_file(path)
    lyrics = [n[5] for n in _notes(project.tracks[0].text)]
    assert lyrics == ["Ma-", "ri-", "a", "a‿e", None]


def test_musicxml_second_verse_on_the_repeat(tmp_path):
    from core.musicxml_import import import_musicxml_file
    path = str(tmp_path / "strofe.musicxml")
    body = "".join(_note(s, _lyric(a) + _lyric(b, number="2")) for s, a, b in
                   (("C", "uno", "cin"), ("D", "due", "sei"), ("E", "tre", "set"), ("F", "quat", "ot")))
    _musicxml(path, [body], repeat=True)
    project = import_musicxml_file(path)
    lyrics = [n[5] for n in _notes(project.tracks[0].text)]
    assert lyrics == ["uno", "due", "tre", "quat", "cin", "sei", "set", "ot"]


def test_musicxml_two_voices_on_a_staff_stay_in_one_track(tmp_path):
    from core.musicxml_import import import_musicxml_file
    path = str(tmp_path / "voci.musicxml")
    voice1 = "".join(_note(s) for s in "CDEF")
    voice2 = '<backup><duration>4</duration></backup>' + _note("C", duration=4, octave=4)
    _musicxml(path, [voice1 + voice2, _note("G", duration=4)])
    project = import_musicxml_file(path)
    assert len(project.tracks) == 1
    notes = _notes(project.tracks[0].text)
    assert sorted((n[0], n[4]) for n in notes) == [("c", 1), ("c", 2), ("d", 1), ("e", 1), ("f", 1), ("g", 1)]


# ------------------------------------------------------------------ cambi di strumento

def _program_change_midi(path, channel, events):
    """events: [(tick, ("prog", n) | ("cc", controllo, valore) | ("note", nota, durata))]."""
    mid = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    msgs = []
    for tick, ev in events:
        if ev[0] == "prog":
            msgs.append((tick, 0, mido.Message("program_change", channel=channel, program=ev[1])))
        elif ev[0] == "cc":
            msgs.append((tick, 0, mido.Message("control_change", channel=channel, control=ev[1], value=ev[2])))
        else:
            msgs.append((tick, 1, mido.Message("note_on", channel=channel, note=ev[1], velocity=100)))
            msgs.append((tick + ev[2], -1, mido.Message("note_off", channel=channel, note=ev[1], velocity=0)))
    last = 0
    for tick, _order, msg in sorted(msgs, key=lambda m: (m[0], m[1])):
        msg.time = tick - last
        last = tick
        track.append(msg)
    mid.save(path)


def test_channel_changing_instrument_becomes_one_track_per_instrument(tmp_path):
    """Layla: il riff dell'intro in chitarra overdrive e poi pianoforte sullo
    stesso canale. Ogni strumento ha la sua traccia, con le sue sole note e
    il volume in vigore quando attacca; le parti tornate dallo stesso
    strumento stanno insieme."""
    path = str(tmp_path / "cambi.mid")
    _program_change_midi(path, 0, [
        (0, ("prog", 29)), (0, ("cc", 7, 80)), (0, ("note", 62, 480)), (480, ("note", 65, 480)),
        (1920, ("prog", 0)), (1920, ("cc", 7, 100)), (1920, ("note", 60, 480)),
        (3840, ("prog", 29)), (3840, ("note", 67, 480)),
    ])
    project = import_midi_file(path)
    guitar, piano = project.tracks
    assert guitar.instrument.gm_program == 29 and piano.instrument.gm_program == 0
    assert guitar.volume == 80 and piano.volume == 100
    pitches = lambda t: [(e.letter, e.start) for e in parse_track_text(t.text, {}) if e.kind == "note"]
    assert pitches(guitar) == [("d", 0), ("f", 1), ("g", 8)]
    assert pitches(piano) == [("c", 4)]


def test_repeated_same_program_or_drum_kits_do_not_split(tmp_path):
    same = str(tmp_path / "stesso.mid")
    _program_change_midi(same, 0, [(0, ("prog", 29)), (0, ("note", 62, 480)),
                                   (960, ("prog", 29)), (960, ("note", 64, 480))])
    assert len(import_midi_file(same).tracks) == 1
    drums = str(tmp_path / "kit.mid")
    _program_change_midi(drums, 9, [(0, ("prog", 0)), (0, ("note", 36, 240)),
                                    (960, ("prog", 25)), (960, ("note", 38, 240))])
    assert len(import_midi_file(drums).tracks) == 1
