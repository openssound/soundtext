"""
Test per core.rhythm_generate: generazione algoritmica (non basata su IA) di
batteria e linee di basso.

Esecuzione:
    python3 -m pytest tests/test_rhythm_generate.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core.chords import note_name_to_pc, midi_note
from core.notation import validate_track_text, parse_track_text
from core.rhythm_generate import (
    DRUM_STYLES, BASS_STYLES, COMPING_STYLES, RIFF_STYLES, PROGRESSION_STYLES, ChordSpan,
    generate_drum_pattern, extract_chords_from_track, generate_bass_from_chords,
    generate_melodic_line, generate_chord_progression, parse_key, project_has_chords,
    drum_styles_for_meter, meter_beats,
)


# ------------------------------------------------------------ batteria

def _style_bar_beats(style):
    return meter_beats(DRUM_STYLES[style].get("meter", "4/4"))


@pytest.mark.parametrize("style", list(DRUM_STYLES))
def test_drum_pattern_is_valid_notation(style):
    text = generate_drum_pattern(style, bars=8, fill_every=4)
    ok, msg = validate_track_text(text, {})
    assert ok, msg


@pytest.mark.parametrize("style", list(DRUM_STYLES))
def test_drum_pattern_uses_only_known_percussion_names(style):
    from core.instruments import PERCUSSION_MAP
    text = generate_drum_pattern(style, bars=4, fill_every=0)
    for tok in text.split():
        if tok.endswith(":"):  # cambio di griglia (16:, 8T:)
            continue
        for name in tok.strip("[]").split():
            name = name.lstrip("0123456789")
            if name == "r" or name.endswith("@") or name == "":
                continue
            assert name in PERCUSSION_MAP, f"nome percussione sconosciuto: '{name}' in '{tok}'"


def test_drum_pattern_no_fill_when_fill_every_zero():
    text = generate_drum_pattern("rock", bars=8, fill_every=0)
    tokens = text.split()
    assert not any("tom" in t or "crash" in t for t in tokens)


def test_drum_pattern_inserts_fill_and_crash_with_enough_bars():
    text = generate_drum_pattern("rock", bars=8, fill_every=4)
    tokens = text.split()
    assert any("tom" in t for t in tokens)   # il fill (battuta 4) usa i tom
    assert any("crash" in t for t in tokens)  # rientro accentato (battuta 5)


def test_drum_pattern_never_ends_on_a_fill():
    # Con esattamente 'fill_every' battute richieste, il fill cadrebbe
    # sull'ULTIMA battuta: si preferisce chiudere sul giro base.
    text = generate_drum_pattern("rock", bars=4, fill_every=4)
    tokens = text.split()
    assert not any("tom" in t for t in tokens)


def test_drum_pattern_rejects_unknown_style():
    with pytest.raises(ValueError):
        generate_drum_pattern("polka", bars=4)


@pytest.mark.parametrize("style", list(DRUM_STYLES))
@pytest.mark.parametrize("fill_every", [0, 4])
def test_drum_pattern_bar_lasts_one_bar_of_its_meter_on_any_grid(style, fill_every):
    """Ogni stile, a sedicesimi, ottavi o terzine, riempie esattamente
    'bars' battute della sua metrica (nessuna battuta corta o lunga)."""
    from core.notation import parse_track_text
    bars = 8
    events = parse_track_text(generate_drum_pattern(style, bars=bars, fill_every=fill_every), {})
    end = max(e.start + e.duration for e in events)
    assert end == pytest.approx(bars * _style_bar_beats(style))


@pytest.mark.parametrize("style,grid", [("shuffle", "8T:"), ("swing", "8T:"), ("rock", "16:"), ("bossa", "16:")])
def test_drum_style_declares_its_grid(style, grid):
    assert generate_drum_pattern(style, bars=2, fill_every=0).split()[0] == grid


def test_new_drum_styles_are_available():
    for style in ("punk", "soul", "bossa", "rocknroll", "shuffle", "swing"):
        assert style in DRUM_STYLES


def test_drum_pattern_rejects_non_positive_bars():
    with pytest.raises(ValueError):
        generate_drum_pattern("rock", bars=0)


# ------------------------------------------------------------ nuovi stili di basso

MINOR_BLUES_PROGRESSION = "4: 4Am7 4D7 4Gmaj7 4Cmaj7"


def _bass(style, variation_every=0, progression=MINOR_BLUES_PROGRESSION):
    spans = extract_chords_from_track(progression, {})
    return generate_bass_from_chords(spans, style, octave=2, variation_every=variation_every)


@pytest.mark.parametrize("style", list(BASS_STYLES))
@pytest.mark.parametrize("variation_every", [0, 1])
def test_bass_style_is_valid_and_fills_every_chord_exactly(style, variation_every):
    from core.notation import parse_track_text
    text = _bass(style, variation_every)
    ok, msg = validate_track_text(text, {})
    assert ok, msg
    end = max(e.start + e.duration for e in parse_track_text(text, {}))
    assert end == pytest.approx(16.0)  # 4 accordi da 4 beat, nessuno corto o lungo


@pytest.mark.parametrize("style,grid", [
    ("root", "4:"), ("pedal", "4:"), ("blues", "4:"),
    ("eighths", "8:"), ("reggae", "8:"), ("bossa", "8:"), ("shuffle", "8T:"),
])
def test_bass_style_declares_its_grid(style, grid):
    assert _bass(style).split()[0] == grid


def test_bass_pedal_is_one_long_note_per_chord():
    assert _bass("pedal") == "4: 4a*2 4d*2 4g*2 4c*2"


def test_bass_blues_uses_the_real_third_of_each_chord():
    # Am7 (terza minore) e D7 (terza maggiore): 1-3-5-6
    assert _bass("blues") == "4: a*2 c*2 e*2 f#*2 d*2 f#*2 a*2 b*2 g*2 b*2 d*2 e*2 c*2 e*2 g*2 a*2"


def test_bass_walking_variant_uses_minor_third_and_seventh_on_a_minor_chord():
    # prima si scriveva una terza maggiore (c#) anche su Am7
    text = _bass("walking", variation_every=1, progression="4: 4Am7 4D7")
    assert text.split()[1:3] == ["a*2", "c*2"]   # fondamentale, terza MINORE
    assert text.split()[3] == "g*2"               # settima di Am7


def test_bass_reggae_leaves_the_first_beat_empty():
    tokens = _bass("reggae").split()
    assert tokens[1] == "2r"  # 2 ottavi di pausa = tutto il primo beat


def test_bass_eighths_play_eight_notes_per_bar():
    tokens = _bass("eighths", progression="4: 4C").split()[1:]
    assert tokens == ["c*2"] * 8


def test_bass_shorter_chord_truncates_the_pattern_without_overflowing():
    from core.notation import parse_track_text
    spans = extract_chords_from_track("4: 2C 2G", {})
    for style in ("bossa", "reggae", "shuffle", "eighths", "two_feel"):
        text = generate_bass_from_chords(spans, style, octave=2, variation_every=0)
        end = max(e.start + e.duration for e in parse_track_text(text, {}))
        assert end == pytest.approx(4.0), style


def test_extract_chords_block_root_is_the_lowest_note_when_it_forms_a_chord():
    # La-Do-Mi-Sol ha le stesse note di Do6, ma il basso segue il La
    am7, c_over_e, c6 = extract_chords_from_track(
        "4: [a*3 c*4 e*4 g*4] [e*3 g*3 c*4] [c*4 e*4 g*4 a*4]", {})
    assert (am7.root_pc, am7.third, am7.seventh) == (9, 3, 10)
    assert c_over_e.root_pc == 0  # rivolto: la fondamentale e' il Do, non il Mi piu' basso
    assert c6.root_pc == 0


def test_extract_chords_carries_third_and_seventh():
    minor7, dom7, power = extract_chords_from_track("4: Am7 D7 [e*3 b*3]", {})
    assert (minor7.third, minor7.seventh) == (3, 10)
    assert (dom7.third, dom7.seventh) == (4, 10)
    assert power.third is None  # quinta vuota: nessuna terza


# ------------------------------------------------------------ variabilita'

def _drum_hits(text):
    from core.notation import parse_track_text
    hits = set()
    for ev in parse_track_text(text, {}):
        if ev.kind == "percussion":
            hits.add((round(ev.start, 6), ev.name))  # arrotondato: le terzine accumulano errori di virgola mobile
        elif ev.kind == "block":
            hits.update((round(ev.start, 6), it["name"]) for it in ev.items if it.get("kind") == "percussion")
    return hits


@pytest.mark.parametrize("style", list(DRUM_STYLES))
def test_drum_zero_variability_is_identical_whatever_the_seed(style):
    base = generate_drum_pattern(style, bars=8, fill_every=4)
    assert generate_drum_pattern(style, bars=8, fill_every=4, variability=0.0, seed=1) == base
    assert generate_drum_pattern(style, bars=8, fill_every=4, variability=0.0, seed=99) == base


def test_variability_is_reproducible_by_seed_and_changes_with_it():
    a = generate_drum_pattern("rock", bars=8, variability=0.6, seed=7)
    assert a == generate_drum_pattern("rock", bars=8, variability=0.6, seed=7)
    assert len({generate_drum_pattern("rock", bars=8, variability=0.6, seed=n) for n in range(8)}) > 1
    assert a != generate_drum_pattern("rock", bars=8)  # diverso dalla versione senza variabilita'
    b1 = _bass("blues")
    spans = extract_chords_from_track(MINOR_BLUES_PROGRESSION, {})
    same = [generate_bass_from_chords(spans, "blues", 2, 0, variability=0.6, seed=3) for _ in range(2)]
    assert same[0] == same[1]
    assert len({generate_bass_from_chords(spans, "blues", 2, 0, variability=0.6, seed=n) for n in range(8)}) > 1
    assert same[0] != b1


@pytest.mark.parametrize("style", list(DRUM_STYLES))
@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_drum_variability_keeps_bars_exact_and_never_removes_pattern_hits(style, seed):
    from core.notation import parse_track_text
    bars = 8
    varied = generate_drum_pattern(style, bars=bars, fill_every=4, variability=1.0, seed=seed)
    ok, msg = validate_track_text(varied, {})
    assert ok, msg
    end = max(e.start + e.duration for e in parse_track_text(varied, {}))
    assert end == pytest.approx(bars * _style_bar_beats(style))
    # senza fill: in ogni battuta restano al loro posto i colpi che non sono di
    # tempo (cassa, rullante, tom...) di uno dei giri dello stile (quello
    # base o uno dei giri alternativi, DRUM_ALTS)
    from core.rhythm_generate import DRUM_ALTS
    timekeepers = ("hihat", "ride", "tambourine")
    bar_beats = _style_bar_beats(style)
    main = DRUM_STYLES[style]["main"]
    unit = bar_beats / len(main)
    grooves = [{(round(i * unit, 6), name) for i, hits in enumerate(g) if hits
                for name, _vel in hits if name not in timekeepers}
               for g in [main] + DRUM_ALTS.get(style, [])]
    varied_nofill = _drum_hits(generate_drum_pattern(style, bars=bars, fill_every=0, variability=1.0, seed=seed))
    for b in range(bars):
        in_bar = {(round(t - b * bar_beats, 6), name) for t, name in varied_nofill
                  if b * bar_beats - 1e-6 <= t < (b + 1) * bar_beats - 1e-6 and name not in timekeepers}
        assert any(g <= in_bar for g in grooves), (style, seed, b)


@pytest.mark.parametrize("style", list(BASS_STYLES))
@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_bass_variability_keeps_length_and_opening_root(style, seed):
    from core.chords import pc_to_letter
    from core.notation import parse_track_text
    spans = extract_chords_from_track(MINOR_BLUES_PROGRESSION, {})
    text = generate_bass_from_chords(spans, style, octave=2, variation_every=0, variability=1.0, seed=seed)
    ok, msg = validate_track_text(text, {})
    assert ok, msg
    events = parse_track_text(text, {})
    assert max(e.start + e.duration for e in events) == pytest.approx(16.0)
    if style != "reggae":  # il reggae lascia volutamente vuoto il primo tempo
        # la nota che suona al cambio d'accordo e' la sua fondamentale: attaccata
        # li', o anticipata di un ottavo e legata oltre il cambio (sincope)
        notes = [e for e in events if e.kind == "note"]
        for beat, span in zip((0.0, 4.0, 8.0, 12.0), spans):
            sounding = [e for e in notes if e.start - 1e-6 <= beat < e.start + e.duration - 1e-6]
            assert len(sounding) == 1 and beat - sounding[0].start <= 0.5 + 1e-6, (style, seed, beat)
            assert sounding[0].letter == pc_to_letter(span.root_pc), (style, seed, beat)


def test_variability_is_clamped_to_zero_one():
    base = generate_drum_pattern("rock", bars=4)
    assert generate_drum_pattern("rock", bars=4, variability=-3, seed=1) == base
    assert generate_drum_pattern("rock", bars=4, variability=9, seed=1) == \
        generate_drum_pattern("rock", bars=4, variability=1, seed=1)


# ------------------------------------------------------------ estrazione accordi

def test_extract_chords_from_track_basic():
    spans = extract_chords_from_track("4Cmaj7 4F 4G7 4C", {})
    assert len(spans) == 4
    assert [s.root_pc for s in spans] == [note_name_to_pc(l) for l in ("c", "f", "g", "c")]
    assert [s.start_beat for s in spans] == [0.0, 4.0, 8.0, 12.0]
    assert all(s.duration_beats == 4.0 for s in spans)
    assert all(s.has_fifth for s in spans)


def test_extract_chords_ignores_notes_and_percussion():
    spans = extract_chords_from_track("c*4 d*4 4Cmaj7 kick snare", {})
    assert len(spans) == 1
    assert spans[0].root_pc == note_name_to_pc("c")


def test_extract_chords_power_chord_has_no_fifth_flag_but_still_a_fifth_interval():
    # '5' (power chord) e' root+quinta: has_fifth deve risultare True lo stesso.
    spans = extract_chords_from_track("4C5", {})
    assert spans[0].has_fifth is True


def test_extract_chords_dim_chord_has_no_natural_fifth():
    spans = extract_chords_from_track("4Cdim", {})
    assert spans[0].has_fifth is False


def test_extract_chords_empty_track_returns_empty_list():
    assert extract_chords_from_track("c*4 kick r", {}) == []


# ------------------------------------------------------------ basso

def _c_f_g_c_spans():
    return extract_chords_from_track("4Cmaj7 4F 4G7 4C", {})


@pytest.mark.parametrize("style", list(BASS_STYLES))
def test_bass_from_chords_is_valid_notation(style):
    text = generate_bass_from_chords(_c_f_g_c_spans(), style, octave=2, variation_every=4)
    ok, msg = validate_track_text(text, {})
    assert ok, msg


def test_bass_root_style_plain_repeats_root():
    spans = _c_f_g_c_spans()
    text = generate_bass_from_chords(spans, "root", octave=2, variation_every=0)
    assert text == "4: c*2 c*2 c*2 c*2 f*2 f*2 f*2 f*2 g*2 g*2 g*2 g*2 c*2 c*2 c*2 c*2"


def test_bass_root_style_variation_bounces_octave():
    spans = _c_f_g_c_spans()
    text = generate_bass_from_chords(spans, "root", octave=2, variation_every=4)
    # Solo il 4o accordo (indice 3, l'unico multiplo di 4) e' "variant".
    tokens = text.split()
    last_chord_notes = tokens[-4:]
    assert last_chord_notes == ["c*2", "c*3", "c*2", "c*3"]


def test_bass_root_fifth_alternates_root_and_fifth():
    spans = extract_chords_from_track("4C", {})
    text = generate_bass_from_chords(spans, "root_fifth", octave=2, variation_every=0)
    assert text == "4: c*2 g*2 c*2 g*2"  # G = quinta di C


def test_bass_walking_uses_chromatic_approach_to_next_chord():
    spans = _c_f_g_c_spans()
    text = generate_bass_from_chords(spans, "walking", octave=2, variation_every=0)
    tokens = text.split()
    # Il 4o attacco del 1o accordo (C) deve essere la nota di avvicinamento
    # cromatico all'accordo successivo (F): un semitono sotto, cioe' Mi.
    assert tokens[4] == "e*2"


def test_bass_walking_last_chord_has_no_next_falls_back_to_root_approach():
    spans = _c_f_g_c_spans()
    text = generate_bass_from_chords(spans, "walking", octave=2, variation_every=0)
    tokens = text.split()
    # Ultimo accordo (C, nessun accordo successivo): l'avvicinamento ricade
    # sulla tonica stessa dell'accordo corrente (si', un semitono sotto Do).
    assert tokens[-1] == "b*2"


def test_bass_handles_gap_between_chords_as_rest():
    spans = [
        ChordSpan(start_beat=0.0, duration_beats=4.0, root_pc=0, has_fifth=True),
        ChordSpan(start_beat=8.0, duration_beats=4.0, root_pc=5, has_fifth=True),  # 4 beat di buco
    ]
    text = generate_bass_from_chords(spans, "root", octave=2, variation_every=0)
    assert "4r" in text.split() or text.split().count("r") >= 4


def test_bass_rejects_empty_chord_list():
    with pytest.raises(ValueError):
        generate_bass_from_chords([], "root")


def test_bass_rejects_unknown_style():
    with pytest.raises(ValueError):
        generate_bass_from_chords(_c_f_g_c_spans(), "bebop")


# ------------------------------------------------------------ melodia/accompagnamento

def _all_midi_pitches(text):
    """Ogni altezza (nota MIDI) presente nel testo generato, sia le note
    singole sia quelle dei blocchi [...] - per verificare che il registro
    generato rientri in [range_low, range_high]."""
    pitches = []
    for e in parse_track_text(text, {}, default_octave=4):
        if e.kind == "note":
            pitches.append(midi_note(note_name_to_pc(e.letter), e.octave))
        elif e.kind == "block":
            for item in e.items or []:
                if item.get("kind") == "note":
                    pitches.append(midi_note(note_name_to_pc(item["letter"]), item["octave"]))
    return pitches


@pytest.mark.parametrize("style", list(COMPING_STYLES))
def test_melodic_line_comping_is_valid_notation(style):
    text = generate_melodic_line(_c_f_g_c_spans(), style, octave=4, range_low=40, range_high=88,
                                  polyphonic=True, variation_every=4)
    ok, msg = validate_track_text(text, {})
    assert ok, msg


@pytest.mark.parametrize("style", list(RIFF_STYLES))
def test_melodic_line_riff_is_valid_notation(style):
    text = generate_melodic_line(_c_f_g_c_spans(), style, octave=5, range_low=48, range_high=84,
                                  polyphonic=False, variation_every=4)
    ok, msg = validate_track_text(text, {})
    assert ok, msg


@pytest.mark.parametrize("style,polyphonic", [(s, True) for s in COMPING_STYLES] +
                                              [(s, False) for s in RIFF_STYLES])
def test_melodic_line_stays_within_instrument_range(style, polyphonic):
    text = generate_melodic_line(_c_f_g_c_spans(), style, octave=6, range_low=52, range_high=64,
                                  polyphonic=polyphonic, variation_every=4)
    pitches = _all_midi_pitches(text)
    assert pitches, "nessuna nota generata"
    assert all(52 <= p <= 64 for p in pitches), pitches


def test_melodic_line_block_chords_plays_simultaneous_notes():
    spans = extract_chords_from_track("4C", {})
    text = generate_melodic_line(spans, "block_chords", octave=4, range_low=40, range_high=88,
                                  polyphonic=True, variation_every=0)
    events = [e for e in parse_track_text(text, {}, default_octave=4) if e.kind == "block"]
    assert events and len(events[0].items) >= 2


def test_melodic_line_rejects_style_for_wrong_polyphony():
    spans = _c_f_g_c_spans()
    with pytest.raises(ValueError):
        generate_melodic_line(spans, "block_chords", octave=4, range_low=40, range_high=88, polyphonic=False)
    with pytest.raises(ValueError):
        generate_melodic_line(spans, "riff_short", octave=5, range_low=40, range_high=88, polyphonic=True)


def test_melodic_line_rejects_unknown_style():
    with pytest.raises(ValueError):
        generate_melodic_line(_c_f_g_c_spans(), "bebop", octave=4, range_low=40, range_high=88, polyphonic=True)


def test_melodic_line_rejects_empty_chord_list():
    with pytest.raises(ValueError):
        generate_melodic_line([], "block_chords", octave=4, range_low=40, range_high=88, polyphonic=True)


def test_riff_arpeggio_updown_ascends_then_descends():
    span = ChordSpan(start_beat=0.0, duration_beats=4.0, root_pc=0, has_fifth=True)
    text = generate_melodic_line([span], "arpeggio_updown", octave=4, range_low=40, range_high=88,
                                  polyphonic=False, variation_every=0)
    tokens = text.split()[1:]
    assert tokens[:4] == ["c*4", "e*4", "g*4", "c*5"]   # sale: radice, terza, quinta, ottava
    assert tokens[4:7] == ["g*4", "e*4", "c*4"]          # ridiscende sulle stesse note


def test_riff_reggae_skank_plays_only_on_the_offbeat():
    span = ChordSpan(start_beat=0.0, duration_beats=4.0, root_pc=0, has_fifth=True)
    text = generate_melodic_line([span], "reggae_skank", octave=5, range_low=48, range_high=84,
                                  polyphonic=False, variation_every=0)
    events = [e for e in parse_track_text(text, {}, default_octave=4) if e.kind == "note"]
    assert [round(e.start, 3) for e in events] == [0.5, 1.5, 2.5, 3.5]


def test_riff_pedal_riff_repeats_the_same_note():
    span = ChordSpan(start_beat=0.0, duration_beats=4.0, root_pc=0, has_fifth=True)
    text = generate_melodic_line([span], "pedal_riff", octave=5, range_low=48, range_high=84,
                                  polyphonic=False, variation_every=0)
    assert text == "8: " + " ".join(["c*5"] * 8)


def test_riff_held_note_is_one_long_note_per_chord():
    spans = _c_f_g_c_spans()  # 4 accordi da 4 beat ciascuno
    text = generate_melodic_line(spans, "held_note", octave=5, range_low=40, range_high=88,
                                  polyphonic=False, variation_every=0)
    assert text == "4: 4c*5 4f*5 4g*5 4c*5"


def test_comping_skank_chords_plays_only_on_the_offbeat():
    span = ChordSpan(start_beat=0.0, duration_beats=4.0, root_pc=0, has_fifth=True)
    text = generate_melodic_line([span], "skank_chords", octave=4, range_low=40, range_high=88,
                                  polyphonic=True, variation_every=0)
    events = [e for e in parse_track_text(text, {}, default_octave=4) if e.kind == "block"]
    assert [round(e.start, 3) for e in events] == [0.5, 1.5, 2.5, 3.5]
    assert len(events[0].items) >= 2  # accordo, non nota singola


def test_comping_funk_stab_is_short_hits_with_silence_between():
    span = ChordSpan(start_beat=0.0, duration_beats=4.0, root_pc=0, has_fifth=True)
    text = generate_melodic_line([span], "funk_stab", octave=4, range_low=40, range_high=88,
                                  polyphonic=True, variation_every=0)
    events = [e for e in parse_track_text(text, {}, default_octave=4) if e.kind == "block"]
    assert [(round(e.start, 3), round(e.duration, 3)) for e in events] == [(0.0, 0.5), (2.5, 0.5)]


def test_comping_quarter_chords_hits_every_beat():
    span = ChordSpan(start_beat=0.0, duration_beats=4.0, root_pc=0, has_fifth=True)
    text = generate_melodic_line([span], "quarter_chords", octave=4, range_low=40, range_high=88,
                                  polyphonic=True, variation_every=0)
    events = [e for e in parse_track_text(text, {}, default_octave=4) if e.kind == "block"]
    assert [round(e.start, 3) for e in events] == [0.0, 1.0, 2.0, 3.0]


def test_melodic_line_reproducible_by_seed_and_changes_with_it():
    spans = _c_f_g_c_spans()
    kwargs = dict(octave=4, range_low=40, range_high=88, polyphonic=True, variability=0.7)
    a1 = generate_melodic_line(spans, "arpeggio_up", seed=1, **kwargs)
    a2 = generate_melodic_line(spans, "arpeggio_up", seed=1, **kwargs)
    b = generate_melodic_line(spans, "arpeggio_up", seed=2, **kwargs)
    assert a1 == a2
    assert a1 != b


# ------------------------------------------------------------ giro armonico

def _key_for(style):
    return "C" if PROGRESSION_STYLES[style]["mode"] == "major" else "Am"


@pytest.mark.parametrize("style", list(PROGRESSION_STYLES))
def test_chord_progression_is_valid_and_readable_by_the_other_generators(style):
    text = generate_chord_progression(_key_for(style), style)
    ok, msg = validate_track_text(text, {})
    assert ok, msg
    spans = extract_chords_from_track(text, {})
    cycle_bars = sum(length for _, _, length in PROGRESSION_STYLES[style]["chords"])
    assert len(spans) == len(PROGRESSION_STYLES[style]["chords"])
    assert spans[-1].start_beat + spans[-1].duration_beats == pytest.approx(cycle_bars * 4.0)
    # basso e accompagnamento ci lavorano sopra senza errori
    generate_bass_from_chords(spans, "walking", octave=2)
    generate_melodic_line(spans, "block_chords", 4, 40, 88, polyphonic=True)


def test_chord_progression_follows_the_key_and_its_spelling():
    assert generate_chord_progression("C", "pop") == "4: 4C 4G 4Am 4F"
    assert generate_chord_progression("Am", "andalusian") == "4: 4Am 4G 4F 4E"
    assert generate_chord_progression("F", "jazz_251") == "4: 4Gm7 4C7 8Fmaj7"      # Si bemolle, non La#
    assert generate_chord_progression("Dm", "minor_pop") == "4: 4Dm 4Bb 4F 4C"
    assert generate_chord_progression("E", "pop") == "4: 4E 4B 4C#m 4A"


@pytest.mark.parametrize("bars,chord_bars,bar_beats", [
    (8, 1.0, 4.0), (8, 0.5, 4.0), (6, 2.0, 3.0), (5, 1.0, 3.0), (3, 0.5, 3.5), (7, 1.0, 6.0),
])
def test_chord_progression_fills_exactly_the_requested_bars_in_any_meter(bars, chord_bars, bar_beats):
    text = generate_chord_progression("G", "pop", bars=bars, chord_bars=chord_bars, bar_beats=bar_beats)
    events = parse_track_text(text, {})
    assert events[-1].start + events[-1].duration == bars * bar_beats


def test_chord_progression_rejects_style_of_the_other_mode_and_unknown_style():
    with pytest.raises(ValueError):
        generate_chord_progression("Am", "pop")
    with pytest.raises(ValueError):
        generate_chord_progression("C", "andalusian")
    with pytest.raises(ValueError):
        generate_chord_progression("C", "bebop")


def test_chord_progression_variability_colors_chords_reproducibly():
    plain = generate_chord_progression("C", "pop", bars=8)
    assert generate_chord_progression("C", "pop", bars=8, variability=0.0, seed=5) == plain
    a = generate_chord_progression("C", "pop", bars=8, variability=1.0, seed=5)
    assert a == generate_chord_progression("C", "pop", bars=8, variability=1.0, seed=5)
    outs = {generate_chord_progression("C", "pop", bars=8, variability=1.0, seed=s) for s in range(10)}
    assert len(outs) > 1 and plain not in outs


def test_chord_colors_alone_keep_roots_and_durations(monkeypatch):
    import core.rhythm_generate as rg
    for name in ("_SECONDARY_P", "_TRITONE_P", "_MINOR_IV_P"):
        monkeypatch.setattr(rg, name, 0.0)
    plain = generate_chord_progression("C", "pop", bars=8)
    a = generate_chord_progression("C", "pop", bars=8, variability=1.0, seed=5)
    # stesse fondamentali e durate: cambia solo il "colore" dell'accordo
    roots = lambda t: [(s.root_pc, s.start_beat, s.duration_beats) for s in extract_chords_from_track(t, {})]
    assert roots(a) == roots(plain) and a != plain


def test_parse_key():
    assert parse_key("C") == (0, "major", False)
    assert parse_key("Am") == (9, "minor", False)
    assert parse_key("Bb") == (10, "major", True)
    assert parse_key("F#m") == (6, "minor", False)
    assert parse_key("Dm") == (2, "minor", True)
    assert parse_key("") == (0, "major", False)
    assert parse_key("boh") == (0, "major", False)


def test_project_has_chords():
    from core.model import Project
    p = Project(name="t")
    p.add_track("Tromba", "Trumpet", "4: c*5 d*5 e*5")
    p.add_track("Drums", "Drums", "16: kick r snare r")
    p.add_track("Piano", "Piano", "4: c*4 [e*4")   # testo incompleto, in corso di scrittura
    assert not project_has_chords(p)
    p.get_track("Piano").text = "4: [c*4 e*4 g*4] [f*4 a*4 c*5]"   # blocchi: contano come accordi
    assert project_has_chords(p)
    p.get_track("Piano").text = "4: 4Am 4F"
    assert project_has_chords(p)
    assert not project_has_chords(p, exclude_track_name="Piano")   # gli unici accordi sono li'

# ------------------------------------------------------------ altre metriche

def test_drum_styles_are_grouped_by_meter():
    assert drum_styles_for_meter("3/4") == ["waltz", "jazz_waltz"]
    assert drum_styles_for_meter("6/8") == ["ballad_68", "afro_68"]
    assert drum_styles_for_meter("12/8") == ["blues_128", "slow_rock_128"]
    assert "rock" in drum_styles_for_meter("4/4")
    assert drum_styles_for_meter("5/4") == ["rock_54", "jazz_54"]
    assert drum_styles_for_meter("7/8") == ["rock_78", "balkan_78"]
    assert drum_styles_for_meter("9/8") == []


@pytest.mark.parametrize("meter,beats", [("4/4", 4.0), ("3/4", 3.0), ("6/8", 3.0), ("12/8", 6.0), ("2/2", 4.0)])
def test_meter_beats(meter, beats):
    assert meter_beats(meter) == beats


def test_meter_beats_rejects_garbage():
    with pytest.raises(ValueError):
        meter_beats("tre quarti")


@pytest.mark.parametrize("style", list(BASS_STYLES))
def test_bass_in_three_four_follows_the_chords(style):
    from core.notation import parse_track_text
    spans = extract_chords_from_track("4: 3C 3F 3G 3C", {})
    text = generate_bass_from_chords(spans, style, variation_every=0, bar_beats=3.0)
    events = parse_track_text(text, {})
    assert max(e.start + e.duration for e in events) == pytest.approx(12.0)
    notes = [e for e in events if e.kind == "note"]
    # nessun attacco oltre la battuta di 3/4 di ciascun accordo: ogni accordo inizia con una sua nota
    if style != "reggae":
        starts = {e.start for e in notes}
        assert {0.0, 3.0, 6.0, 9.0} <= starts


def test_waltz_comping_plays_on_two_and_three():
    from core.notation import parse_track_text
    spans = extract_chords_from_track("4: 3C 3F", {})
    text = generate_melodic_line(spans, "waltz_comp", 4, 40, 90, polyphonic=True,
                                 variation_every=0, bar_beats=3.0)
    blocks = [e.start for e in parse_track_text(text, {}) if e.kind == "block"]
    assert blocks == [1.0, 2.0, 4.0, 5.0]


if __name__ == "__main__":
    import inspect
    here = sys.modules[__name__]
    tests = [f for name, f in inspect.getmembers(here) if name.startswith("test_") and callable(f)]
    passed = 0
    for t in tests:
        try:
            t()
        except TypeError:
            continue  # test parametrizzati, saltati nell'esecuzione diretta (usare pytest)
        passed += 1
        print(f"OK  {t.__name__}")
    print(f"\n{passed}/{len(tests)} test superati (i parametrizzati richiedono pytest).")


# ------------------------------------------------------------ nuovi modelli e intensita'

@pytest.mark.parametrize("meter,styles", [("5/4", ["rock_54", "jazz_54"]), ("7/8", ["rock_78", "balkan_78"])])
def test_odd_meter_styles_fill_their_bars(meter, styles):
    from core.notation import parse_track_text
    for style in styles:
        assert DRUM_STYLES[style]["meter"] == meter
        text = generate_drum_pattern(style, bars=6, fill_every=3, variability=0.5, seed=4)
        end = max(e.start + e.duration for e in parse_track_text(text, {}))
        assert end == pytest.approx(6 * meter_beats(meter))


def test_drum_alternative_grooves_appear_only_with_variability():
    from core.rhythm_generate import DRUM_ALTS
    assert len(DRUM_ALTS["rock"]) >= 2
    plain = generate_drum_pattern("rock", bars=16, fill_every=0)
    assert generate_drum_pattern("rock", bars=16, fill_every=0, variability=0.0, seed=5) == plain
    varied = {generate_drum_pattern("rock", bars=16, fill_every=0, variability=1.0, seed=n) for n in range(10)}
    assert len(varied) > 1


def test_drum_intensity_light_thins_and_full_moves_to_ride():
    normal = _drum_hits(generate_drum_pattern("rock", bars=4, fill_every=0))
    light = _drum_hits(generate_drum_pattern("rock", bars=4, fill_every=0, intensity="light"))
    full = _drum_hits(generate_drum_pattern("rock", bars=4, fill_every=0, intensity="full"))
    assert len(light) < len(normal)
    assert {n for _t, n in light} <= {n for _t, n in normal}
    assert any(n == "ride" for _t, n in full) and not any(n == "hihat" for _t, n in full)
    # kick e rullante restano dove sono
    core_hits = {h for h in normal if h[1] in ("kick", "snare")}
    assert core_hits <= light and core_hits <= full


def test_drum_intensity_full_opens_each_block_with_a_crash():
    hits = _drum_hits(generate_drum_pattern("rock", bars=8, fill_every=0, intensity="full"))
    assert (16.0, "crash") in hits          # battuta 5: inizio del secondo gruppo


def test_drum_intensity_build_grows_through_the_part():
    hits = _drum_hits(generate_drum_pattern("rock", bars=9, fill_every=0, intensity="build"))
    first = [h for h in hits if h[0] < 12.0]
    last = [h for h in hits if h[0] >= 24.0]
    assert not any(n == "ride" for _t, n in first)
    assert any(n == "ride" for _t, n in last)
    assert len(first) < len([h for h in hits if 12.0 <= h[0] < 24.0])


def test_drum_rejects_unknown_intensity():
    with pytest.raises(ValueError):
        generate_drum_pattern("rock", bars=4, intensity="fortissimo")


def test_phrase_fills_are_small_then_big():
    plain = _drum_hits(generate_drum_pattern("rock", bars=16, fill_every=4))
    phrase = _drum_hits(generate_drum_pattern("rock", bars=16, fill_every=4, phrase_fills=True))
    toms = lambda hits, lo, hi: {h for h in hits if lo <= h[0] < hi and "tom" in h[1]}
    # battuta 4: fill piccolo, solo nell'ultimo beat
    small = toms(phrase, 12.0, 16.0)
    assert small and all(t >= 15.0 for t, _n in small)
    assert toms(plain, 12.0, 15.0)            # senza "fill a frasi" il fill e' completo
    # battuta 8: fill completo
    assert toms(phrase, 28.0, 31.0)


def test_ending_bar_closes_with_a_single_hit():
    from core.notation import parse_track_text
    text = generate_drum_pattern("rock", bars=4, fill_every=4, ending=True)
    hits = _drum_hits(text)
    assert {h for h in hits if h[0] >= 12.0} == {(12.0, "crash"), (12.0, "kick")}
    end = max(e.start + e.duration for e in parse_track_text(text, {}))
    assert end == pytest.approx(16.0)
    # con una sola battuta non si chiude: resta il giro
    assert generate_drum_pattern("rock", bars=1, ending=True) == generate_drum_pattern("rock", bars=1)


def _sounding_starts(text):
    return [round(e.start, 3) for e in parse_track_text(text, {}, default_octave=3) if e.kind in ("note", "block")]


@pytest.mark.parametrize("style", list(BASS_STYLES))
def test_bass_intensity_keeps_length_and_light_plays_fewer_notes(style):
    spans = _c_f_g_c_spans()
    total = spans[-1].start_beat + spans[-1].duration_beats
    lengths = {}
    for level in ("light", "normal", "full", "build"):
        text = generate_bass_from_chords(spans, style, octave=2, variation_every=0, intensity=level)
        ok, msg = validate_track_text(text, {})
        assert ok, (level, msg)
        events = parse_track_text(text, {}, default_octave=2)
        assert max(e.start + e.duration for e in events) == pytest.approx(total)
        lengths[level] = len(_sounding_starts(text))
    assert lengths["light"] <= lengths["normal"]


def test_bass_full_lifts_the_last_root_an_octave():
    spans = _c_f_g_c_spans()
    normal = generate_bass_from_chords(spans, "root", octave=2, variation_every=0)
    full = generate_bass_from_chords(spans, "root", octave=2, variation_every=0, intensity="full")
    assert normal.split()[:4] == ["4:", "c*2", "c*2", "c*2"]
    assert full.split()[4] == "c*3"


def test_comping_full_adds_the_upper_octave_to_chords():
    spans = _c_f_g_c_spans()
    kwargs = dict(octave=4, range_low=40, range_high=96, polyphonic=True, variation_every=0)
    normal = generate_melodic_line(spans, "block_chords", **kwargs)
    full = generate_melodic_line(spans, "block_chords", intensity="full", **kwargs)
    size = lambda text: max(len(e.items) for e in parse_track_text(text, {}, default_octave=4) if e.kind == "block")
    assert size(full) > size(normal)


def test_line_generators_reject_unknown_intensity():
    spans = _c_f_g_c_spans()
    with pytest.raises(ValueError):
        generate_bass_from_chords(spans, "root", intensity="boh")
    with pytest.raises(ValueError):
        generate_melodic_line(spans, "block_chords", 4, 40, 88, polyphonic=True, intensity="boh")


@pytest.mark.parametrize("style", ["two_feel", "walking", "block_chords", "arpeggio_up"])
def test_pattern_alternatives_only_with_variability(style):
    from core.rhythm_generate import PATTERN_ALTS
    spans = extract_chords_from_track("4C 4F 4G 4C " * 4, {})
    if style in BASS_STYLES:
        gen = lambda **kw: generate_bass_from_chords(spans, style, 2, 0, **kw)
    else:
        gen = lambda **kw: generate_melodic_line(spans, style, 4, 40, 96, polyphonic=style in COMPING_STYLES,
                                                 variation_every=0, **kw)
    assert gen(variability=0.0, seed=1) == gen(variability=0.0, seed=2) == gen()
    if style in PATTERN_ALTS:
        assert len({gen(variability=1.0, seed=n) for n in range(10)}) > 1


@pytest.mark.parametrize("key,style,expected", [
    ("C", "mixolydian", "4: 4C 4Bb 4F 4C"),
    ("F#", "mixolydian", "4: 4F# 4E 4B 4F#"),
    ("Am", "phrygian", "4: 8Am 8Bb"),
])
def test_modal_progressions_spell_the_flat_degrees(key, style, expected):
    assert generate_chord_progression(key, style) == expected


def test_new_progressions_are_available():
    for style in ("three_chord", "ballad", "royal_road", "mixolydian", "gospel", "circle", "rhythm_changes",
                  "jazz_blues", "minor_three", "minor_epic", "dorian_vamp", "line_cliche", "minor_circle",
                  "phrygian"):
        assert style in PROGRESSION_STYLES


# ------------------------------------------------------------ variabilita' che aggiunge (B)

def _only(monkeypatch, **probabilities):
    """Azzera le probabilita' delle variazioni casuali tranne quelle date."""
    import core.rhythm_generate as rg
    for name in ("_VARY_MERGE_P", "_VARY_REST_P", "_VARY_OCTAVE_P", "_VARY_VARIANT_P", "_ALT_P",
                 "_PASSING_P", "_ANTICIPATE_P", "_COLOR_P", "_SECONDARY_P", "_TRITONE_P", "_MINOR_IV_P"):
        monkeypatch.setattr(rg, name, probabilities.get(name, 0.0))


def test_bass_passing_note_leads_to_the_next_root(monkeypatch):
    _only(monkeypatch, _PASSING_P=10.0)
    spans = extract_chords_from_track("4C 4F 4G 4C", {})
    text = generate_bass_from_chords(spans, "two_feel", 2, 0, variability=1.0, seed=3)
    events = [e for e in parse_track_text(text, {}, default_octave=2) if e.kind == "note"]
    assert max(e.start + e.duration for e in events) == pytest.approx(16.0)
    # una nota in piu' sull'ultimo beat di ogni accordo che ne ha uno dopo
    assert len(events) == 2 * 4 + 3
    for beat, target in ((3.0, "f"), (7.0, "g"), (11.0, "c")):
        note = next(e for e in events if e.start == pytest.approx(beat))
        pc = note_name_to_pc(note.letter)
        assert (pc - note_name_to_pc(target)) % 12 in (11, 1, 10, 7), (beat, note.letter)


def test_passing_notes_only_with_variability():
    spans = extract_chords_from_track("4C 4F 4G 4C", {})
    plain = generate_bass_from_chords(spans, "two_feel", 2, 0)
    assert generate_bass_from_chords(spans, "two_feel", 2, 0, variability=0.0, seed=4) == plain


def test_anticipation_ties_the_next_chord_over_the_bar_line(monkeypatch):
    _only(monkeypatch, _ANTICIPATE_P=10.0)
    spans = extract_chords_from_track("4C 4F 4G 4C", {})
    text = generate_bass_from_chords(spans, "eighths", 2, 0, variability=1.0, seed=1)
    ok, msg = validate_track_text(text, {})
    assert ok, msg
    events = [e for e in parse_track_text(text, {}, default_octave=2) if e.kind == "note"]
    assert max(e.start + e.duration for e in events) == pytest.approx(16.0)
    for change, root in ((4.0, "f"), (8.0, "g"), (12.0, "c")):
        pushed = next(e for e in events if e.start == pytest.approx(change - 0.5))
        assert pushed.letter == root and pushed.duration == pytest.approx(1.0)   # legata oltre il cambio
        assert not any(e.start == pytest.approx(change) for e in events)


def test_anticipation_also_moves_comping_chords(monkeypatch):
    _only(monkeypatch, _ANTICIPATE_P=10.0)
    spans = extract_chords_from_track("4C 4F", {})
    text = generate_melodic_line(spans, "bossa_comp", 4, 40, 90, polyphonic=True, variation_every=0,
                                 variability=1.0, seed=1)
    blocks = [e for e in parse_track_text(text, {}, default_octave=4) if e.kind == "block"]
    pushed = next(e for e in blocks if e.start == pytest.approx(3.5))
    assert {note_name_to_pc(it["letter"]) for it in pushed.items} == {5, 9, 0}    # F A C


def test_line_starts_can_pick_a_different_alternative_every_bar(monkeypatch):
    _only(monkeypatch, _ALT_P=10.0)
    spans = extract_chords_from_track("16C", {})     # un accordo di 4 battute
    outs = {generate_bass_from_chords(spans, "octaves", 2, 0, variability=1.0, seed=n) for n in range(12)}
    # battute diverse all'interno dello stesso accordo
    bars = lambda t: [" ".join(t.split()[1 + 4 * b:5 + 4 * b]) for b in range(4)]
    assert any(len(set(bars(t))) > 1 for t in outs)


def test_voice_leading_keeps_chords_close():
    spans = extract_chords_from_track("4C 4F 4G 4C 4Am 4Dm 4G 4C", {})
    kwargs = dict(octave=4, range_low=48, range_high=84, polyphonic=True, variation_every=0)
    plain = generate_melodic_line(spans, "sustained", **kwargs)
    led = generate_melodic_line(spans, "sustained", voice_leading=True, **kwargs)
    assert generate_melodic_line(spans, "sustained", **kwargs) == plain   # senza: posizione fondamentale
    chords = lambda t: [sorted(midi_note(note_name_to_pc(it["letter"]), it["octave"]) for it in e.items)
                        for e in parse_track_text(t, {}, default_octave=4) if e.kind == "block"]
    moves = lambda cs: sum(sum(abs(a - b) for a, b in zip(x, y)) for x, y in zip(cs, cs[1:]))
    assert chords(led)[0] == chords(plain)[0]           # il primo accordo resta com'e'
    assert moves(chords(led)) < moves(chords(plain))
    for voiced, root_position in zip(chords(led), chords(plain)):   # stesse note, nell'estensione
        assert all(48 <= n <= 84 for n in voiced)
        assert {n % 12 for n in voiced} == {n % 12 for n in root_position}


# ------------------------------------------------------------ armonia piu' ricca (D)

def _symbols(text):
    return [tok.lstrip("0123456789") for tok in text.split()[1:]]


def test_secondary_dominant_prepares_the_next_chord(monkeypatch):
    _only(monkeypatch, _SECONDARY_P=10.0)
    text = generate_chord_progression("C", "pop", variability=1.0, seed=2)
    ok, msg = validate_track_text(text, {})
    assert ok, msg
    symbols = _symbols(text)
    # C G Am F: prima di G arriva D7 (o un II-V), prima di Am arriva E7;
    # l'ultimo accordo (F, non la tonica) non viene preparato
    assert "D7" in symbols and "E7" in symbols and "C7" not in symbols
    assert sum(s.duration_beats for s in extract_chords_from_track(text, {})) == pytest.approx(16.0)


def test_tritone_substitution_replaces_a_dominant_but_not_the_tonic(monkeypatch):
    _only(monkeypatch, _TRITONE_P=10.0)
    assert _symbols(generate_chord_progression("C", "jazz_251", variability=1.0, seed=1)) == ["Dm7", "Db7", "Cmaj7"]
    blues = _symbols(generate_chord_progression("C", "jazz_blues", variability=1.0, seed=1))
    assert blues[0] == "C7"          # il C7 del blues e' la tonica: resta


def test_minor_iv_is_borrowed_before_the_tonic(monkeypatch):
    _only(monkeypatch, _MINOR_IV_P=10.0)
    assert _symbols(generate_chord_progression("C", "three_chord", variability=1.0, seed=1)) == \
        ["C", "F", "G", "C"]                      # IV -> V: niente prestito
    # IV -> I: meta' battuta di IV, meta' di iv minore
    assert generate_chord_progression("C", "rock", variability=1.0, seed=1) == "4: 4C 2F 2Fm6 4C 4G"


@pytest.mark.parametrize("style", list(PROGRESSION_STYLES))
def test_final_cadence_ends_on_the_tonic(style):
    key = _key_for(style)
    for seed, v in ((None, 0.0), (1, 1.0), (2, 1.0)):
        text = generate_chord_progression(key, style, bars=8, variability=v, seed=seed, ending=True)
        ok, msg = validate_track_text(text, {})
        assert ok, msg
        spans = extract_chords_from_track(text, {})
        tonic = 0 if key == "C" else 9
        assert spans[-1].root_pc == tonic and spans[-1].duration_beats == pytest.approx(4.0)
        assert spans[-1].start_beat + spans[-1].duration_beats == pytest.approx(32.0)
    plain = _symbols(generate_chord_progression("C", "pop", bars=8, ending=True))
    assert plain[-2:] == ["G7", "C"]              # senza variabilita': V7 - I


def test_final_cadence_variants_and_authentic_for_ii_v_i():
    cadences = {tuple(_symbols(generate_chord_progression("C", "pop", bars=8, variability=1.0, seed=n,
                                                           ending=True))[-2:]) for n in range(40)}
    assert len({c[0] for c in cadences}) >= 3            # V7, IV, iv, bVII7...
    for n in range(20):
        last = _symbols(generate_chord_progression("C", "jazz_251", bars=8, variability=1.0, seed=n, ending=True))
        assert last[-2] in ("G7", "Db7"), last


def test_chord_progression_enrichment_is_reproducible_and_seed_free_at_zero():
    plain = generate_chord_progression("Am", "andalusian", bars=8)
    assert generate_chord_progression("Am", "andalusian", bars=8, variability=0.0, seed=9) == plain
    a = generate_chord_progression("Am", "andalusian", bars=8, variability=0.8, seed=9)
    assert a == generate_chord_progression("Am", "andalusian", bars=8, variability=0.8, seed=9)
