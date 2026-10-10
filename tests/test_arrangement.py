"""
Test per la vista Struttura brano (core.arrangement, box Clip in
core.model/core.project_io). Esecuzione:
    python3 -m pytest tests/ -v
oppure semplicemente:
    python3 tests/test_arrangement.py
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.model import Project, Clip
from core.notation import parse_track_text
from core.arrangement import clip_duration_beats, flatten_clips_to_text
from core.project_io import parse_project_text, project_to_text


def _project_with_boxed_track():
    p = Project(name="t", tempo_bpm=120)
    t = p.add_track("Basso", "Bass", "")
    t.clips = [
        Clip(name="Intro", text="4: 100@ c e g", start_beat=0.0),
        Clip(name="Verse", text="4: 100@ c d e f", start_beat=8.0),
    ]
    return p, t


def test_clip_duration_beats_counts_quarter_notes():
    assert clip_duration_beats("4: 100@ c e g", {}, default_octave=2) == 3.0


def test_clip_duration_beats_empty_text_is_zero():
    assert clip_duration_beats("", {}, default_octave=4) == 0.0


def test_flatten_clips_orders_by_start_beat_regardless_of_list_order():
    p, t = _project_with_boxed_track()
    t.clips = list(reversed(t.clips))  # Verse prima di Intro nella lista
    flat = flatten_clips_to_text(t.clips, p.patterns, t.instrument.default_octave)
    events = parse_track_text(flat, p.patterns, default_octave=t.instrument.default_octave)
    starts = [e.start for e in events if e.kind in ("note",)]
    assert starts == sorted(starts)


def test_flatten_clips_fills_gap_with_exact_rest():
    p, t = _project_with_boxed_track()
    flat = flatten_clips_to_text(t.clips, p.patterns, t.instrument.default_octave)
    events = parse_track_text(flat, p.patterns, default_octave=t.instrument.default_octave)
    # Verse (secondo box) deve iniziare esattamente al beat 8 dichiarato,
    # indipendentemente dal gap di riempimento prima di esso.
    verse_events = [e for e in events if e.start >= 8.0]
    assert verse_events and verse_events[0].start == 8.0


def test_flatten_clips_resets_state_between_boxes():
    """Un box e' autosufficiente come il corpo di un Pattern: la griglia (e
    quindi la durata di default delle note) del box successivo non deve
    dipendere dalla griglia usata per riempire il vuoto prima di esso."""
    p = Project(name="t", tempo_bpm=120)
    t = p.add_track("Piano", "Piano")
    t.clips = [
        Clip(name="A", text="4: 100@ c", start_beat=0.0),        # 1 beat (nera)
        Clip(name="B", text="100@ c", start_beat=5.0),            # nessuna griglia esplicita: deve valere 1 beat (default), non 1/16
    ]
    flat = flatten_clips_to_text(t.clips, p.patterns, t.instrument.default_octave)
    events = parse_track_text(flat, p.patterns, default_octave=t.instrument.default_octave)
    note_b = [e for e in events if e.start == 5.0]
    assert note_b and note_b[0].duration == 1.0


def test_flatten_clips_empty_list_is_empty_text():
    assert flatten_clips_to_text([], {}, default_octave=4) == ""


def test_project_roundtrip_preserves_boxes():
    p, t = _project_with_boxed_track()
    t.text = flatten_clips_to_text(t.clips, p.patterns, t.instrument.default_octave)

    text = project_to_text(p)
    p2 = parse_project_text(text, "p2")
    t2 = p2.get_track("Basso")

    assert [(c.name, c.text, c.start_beat) for c in t2.clips] == \
           [(c.name, c.text, c.start_beat) for c in t.clips]
    assert t2.text == t.text


def test_project_without_boxes_has_no_box_block():
    p = Project(name="t", tempo_bpm=120)
    p.add_track("Piano", "Piano", "c e g")
    text = project_to_text(p)
    assert "Box " not in text



def test_boxed_track_text_is_written_only_in_its_boxes():
    """Il testo di una traccia con box si ricostruisce dai box alla lettura:
    scriverlo anche sotto la traccia raddoppiava il file."""
    p, t = _project_with_boxed_track()
    t.text = flatten_clips_to_text(t.clips, p.patterns, t.instrument.default_octave)
    p.add_track("Piano", "Piano", "4: c e g")
    text = project_to_text(p)
    assert text.count("c d e f") == 1                       # solo nel box
    assert "Traccia Basso [Bass]:\n\n" in text              # l'intestazione resta
    assert "Piano:\n  4: c e g" in text                     # le tracce senza box come prima
    assert text.index("Traccia Basso") < text.index("Box Basso")   # le tracce in cima, prima dei box
    p2 = parse_project_text(text, "p2")
    assert p2.get_track("Basso").text == t.text
    assert len(p2.get_track("Basso").clips) == 2


def test_short_header_with_digits_in_the_instrument_name():
    """Gli strumenti GM creati dall'import hanno spesso cifre nel nome
    (Lead8basslead, Pad8sweep): la loro intestazione corta va riletta, se no
    la traccia spariva insieme ai suoi box."""
    from core.instruments import resolve_or_create_instrument_by_program
    import st_language as st
    lead = resolve_or_create_instrument_by_program(87, False)
    assert any(ch.isdigit() for ch in lead)
    p = Project(name="t", tempo_bpm=120)
    p.add_track(lead, lead, "4: c d")
    t = p.add_track(f"{lead} 2", lead, "")
    t.clips = [Clip(name="Solo", text="4: e f", start_beat=4.0)]
    t.text = flatten_clips_to_text(t.clips, p.patterns, t.instrument.default_octave)
    text = project_to_text(p)
    assert f"\n{lead}:\n" in text and f"\n{lead} 2:\n" in text
    p2 = parse_project_text(text, "p2")
    assert [(x.name, x.instrument_name, x.text) for x in p2.tracks] == \
           [(x.name, x.instrument_name, x.text) for x in p.tracks]
    song = st.read_song(text)
    assert [x.name for x in song.tracks] == [lead, f"{lead} 2"]
    # l'indice va dopo uno spazio: la vecchia forma "Piano2:" non e' piu' una traccia
    assert [x.name for x in parse_project_text("Piano 2:\n  c\n", "x").tracks] == ["Piano 2"]
    assert parse_project_text("Piano2:\n  c\n", "x").tracks == []


def _notes(text, meter=None):
    return [(round(float(e.start), 4), e.letter) for e in parse_track_text(text, {}, default_octave=4, meter=meter)
            if e.kind == "note"]


def test_boxes_split_on_bar_starts_and_sound_the_same():
    """Con la metrica i box dell'import cominciano all'inizio della battuta
    della prima nota (anche fuori dalla griglia a sedicesimi, in terzina),
    con una pausa fino a quella nota; le note restano dove sono."""
    from core.arrangement import split_text_into_box_segments
    from core.notation import Meter
    # c a 0; d in terzina a 5 + 2/3 (battuta 2, che comincia a 4); e a 11,5 (battuta 3, a 8)
    text = "4: c 4r 12: 2r 8T: d 4: 4r 8: 3r 12: e"
    meter = Meter("4/4")
    # senza metrica: sul sedicesimo prima della nota (vedi _align_to_fill_grid)
    assert [s for s, _ in split_text_into_box_segments(text, {}, 4)] == [0.0, 5.5, 11.5]
    segments = split_text_into_box_segments(text, {}, 4, meter=meter)
    assert [s for s, _ in segments] == [0.0, 4.0, 8.0]
    clips = [Clip(name=str(i), text=t, start_beat=s) for i, (s, t) in enumerate(segments)]
    assert _notes(flatten_clips_to_text(clips, {}, 4, meter=meter), meter) == _notes(text, meter)


def test_box_stays_on_its_first_note_when_the_bar_start_would_overlap():
    """Un'entrata il cui inizio di battuta cade dentro il box precedente
    resta sulla sua prima nota: i box non si sovrappongono."""
    from core.arrangement import split_text_into_box_segments
    from core.notation import Meter
    # c da 4 a 8,25 (oltre l'inizio della battuta 3, a 8), e a 11,75
    text = "4: 4r 16: 17c 8: 7r 16: e"
    assert [s for s, _ in split_text_into_box_segments(text, {}, 4, meter=Meter("4/4"))] == [4.0, 11.75]


def test_boxes_off_the_sixteenth_grid_do_not_shift_what_follows():
    """Un box che comincia o finisce in terzina: lo spazio fra i box si
    riempie a sedicesimi, e senza l'allineamento il resto della traccia
    slittava di 1/12 di quarto (la Voce di Dancin' Fool dal quarto 295)."""
    from core.arrangement import split_text_into_box_segments
    text = "12: c 4: 4r 12: d 4: 8r e"
    segments = split_text_into_box_segments(text, {}, 4)
    assert all(abs(s * 4 - round(s * 4)) < 1e-9 for s, _ in segments)
    clips = [Clip(name=str(i), text=t, start_beat=s) for i, (s, t) in enumerate(segments)]
    assert _notes(flatten_clips_to_text(clips, {}, 4)) == _notes(text)


def test_tempo_change_between_boxes_keeps_the_track_whole():
    """tempo=N nella pausa fra due box non occupa tempo: dividendo andava
    perso insieme alla pausa, e con lui il tempo di tutto il seguito."""
    from core.arrangement import split_text_into_box_segments
    assert split_text_into_box_segments("4: c 8r tempo=90 4r d", {}, 4) == [(0.0, "4: c 8r tempo=90 4r d")]
    assert len(split_text_into_box_segments("4: c 8r 4r d", {}, 4)) == 2


if __name__ == "__main__":
    import inspect
    here = sys.modules[__name__]
    tests = [f for name, f in inspect.getmembers(here) if name.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        passed += 1
        print(f"OK  {t.__name__}")
    print(f"\n{passed}/{len(tests)} test superati.")
