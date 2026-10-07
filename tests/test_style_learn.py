"""
Test per gli stili personali dei generatori (core.user_styles,
core.style_learn) e per la variabilita' per aspetto e la rigenerazione di
alcune battute (core.rhythm_generate.Variability/splice_bars).
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core import user_styles
from core.chords import note_name_to_pc
from core.notation import parse_track_text, validate_track_text
from core.rhythm_generate import (
    Variability, extract_chords_from_track, generate_bass_from_chords, generate_chord_progression,
    generate_drum_pattern, generate_melodic_line, splice_bars,
)
from core.style_learn import describe_style, learn_drum_style, learn_line_style


@pytest.fixture
def styles_file(tmp_path, monkeypatch):
    """Stili personali in un file temporaneo, vuoto a inizio test."""
    monkeypatch.setattr(user_styles, "USER_STYLES_FILE", str(tmp_path / "generator_styles.json"))
    monkeypatch.setattr(user_styles, "CONFIG_DIR", str(tmp_path))
    user_styles.load_user_styles(reload=True)
    yield tmp_path
    monkeypatch.undo()
    user_styles.load_user_styles(reload=True)


GROOVE_A = "105@ kick r 70@ hihat r 100@ [snare hihat] r 70@ hihat kick 105@ kick r 70@ hihat r 100@ [snare hihat] r 70@ hihat r"
GROOVE_B = "105@ kick r 70@ hihat r 100@ [snare hihat] r 70@ hihat r 105@ kick kick 70@ hihat r 100@ [snare hihat] r 70@ hihat r"
FILL = "105@ kick r 70@ hihat r 100@ [snare hihat] r 70@ hihat r 95@ tom1 tom1 tom2 tom2 floor floor snare snare"
DRUM_TEXT = "16: " + " ".join([GROOVE_A, GROOVE_A, GROOVE_B, FILL])

CHORDS = "4Am 4F 4C 4G"
BASS_TEXT = ("8: a*2 a*2 e*3 a*2 r a*2 g*2 g#*2 f*2 f*2 c*3 f*2 r f*2 e*2 b*1 "
             "c*2 c*2 g*2 c*3 r c*2 b*1 g*1 g*2 g*2 d*3 g*2 r g*2 f#*2 g#*2")


# ------------------------------------------------------------ batteria

def test_learn_drum_style_finds_groove_alternative_and_fill():
    spec = learn_drum_style(DRUM_TEXT, meter="4/4")
    assert spec["grid"] == "16:" and spec["meter"] == "4/4" and len(spec["main"]) == 16
    assert spec["main"][7] == [("kick", 70)]             # il giro A (due volte su quattro)
    assert len(spec["alts"]) == 1 and spec["alts"][0][9] == [("kick", 105)]   # il giro B
    assert any(name == "tom1" for slot in spec["fill"] if slot for name, _v in slot)
    assert "fill ricavato dal box" in describe_style("drums", spec)


def test_learned_drum_style_is_saved_and_used_by_the_generator(styles_file):
    user_styles.save_user_style("drums", "Mio rock", learn_drum_style(DRUM_TEXT, meter="4/4"))
    assert (styles_file / "generator_styles.json").exists()
    user_styles.load_user_styles(reload=True)          # riletto dal file
    plain = generate_drum_pattern("user:Mio rock", bars=8, fill_every=4)
    ok, msg = validate_track_text(plain, {})
    assert ok, msg
    assert plain.startswith("16: " + GROOVE_A.split(" hihat kick")[0])
    assert "tom1" in plain                               # il suo fill
    varied = {generate_drum_pattern("user:Mio rock", bars=16, variability=1.0, seed=n) for n in range(6)}
    assert len(varied) > 1


def test_learn_drum_style_in_six_eight_uses_eighths_and_the_dotted_pulse():
    spec = learn_drum_style("8: kick hihat hihat snare hihat hihat " * 2, meter="6/8")
    assert spec["grid"] == "8:" and len(spec["main"]) == 6 and spec["pulse"] == 3
    assert spec["fill"] is None and "fill generico" in describe_style("drums", spec)


def test_learn_drum_style_rejects_text_without_drums():
    with pytest.raises(ValueError):
        learn_drum_style("4: c d e f", meter="4/4")


# ------------------------------------------------------------ basso, accompagnamento, riff

def test_learned_bass_follows_new_chords_with_the_right_degrees(styles_file):
    spans = extract_chords_from_track(CHORDS, {})
    spec = learn_line_style(BASS_TEXT, "bass", chords=spans)
    assert spec["grid"] == "8:"
    assert spec["bar"][:3] == [(0.0, "L:root:0"), (0.5, "L:root:0"), (1.0, "L:fifth:0")]
    assert (2.0, "rest") in spec["bar"]
    user_styles.save_user_style("bass", "Mio basso", spec)
    # sugli stessi accordi, la linea (senza varianti) ripete il disegno base
    replay = generate_bass_from_chords(spans, "user:Mio basso", 2, 0)
    assert replay.split()[:6] == ["8:", "a*2", "a*2", "e*3", "a*2", "r"]
    # su un altro giro, fondamentale e quinta dei nuovi accordi
    other = generate_bass_from_chords(extract_chords_from_track("4Dm 4Bb", {}), "user:Mio basso", 2, 0)
    ok, msg = validate_track_text(other, {})
    assert ok, msg
    assert other.split()[1:4] == ["d*2", "d*2", "a*2"] and other.split()[9:12] == ["a#*2", "a#*2", "f*3"]


def test_learned_approach_note_targets_the_next_chord(styles_file):
    spans = extract_chords_from_track(CHORDS, {})
    spec = learn_line_style(BASS_TEXT, "bass", chords=spans)
    learned = [spec["bar"], spec["variant"]] + spec["alts"]
    assert any(role == "L:next:-1" for bar in learned for _t, role in bar)   # il si prima del do
    user_styles.save_user_style("bass", "Avvicinamento", spec)
    text = generate_bass_from_chords(extract_chords_from_track("4F 4G", {}), "user:Avvicinamento", 2, 1)
    notes = [e for e in parse_track_text(text, {}) if e.kind == "note"]
    last_of_first_chord = max((e for e in notes if e.start < 4.0), key=lambda e: e.start)
    assert note_name_to_pc(last_of_first_chord.letter) == 6          # fa# prima di sol


def test_learn_line_without_chords_uses_the_first_note_of_each_bar():
    spec = learn_line_style("4: c*3 e*3 g*3 e*3 d*3 f*3 a*3 f*3", "riff")
    assert spec["bar"] == [(0.0, "L:root:0"), (1.0, "L:third:0"), (2.0, "L:fifth:0"), (3.0, "L:third:0")]
    # re-fa-la e' un accordo minore: la sua terza e' "la terza", quindi le due
    # battute hanno lo stesso disegno per gradi (nessuna variante)
    assert spec["variant"] is None and spec["bars_learned"] == 2


def test_learn_comping_rhythm_from_chord_symbols(styles_file):
    spec = learn_line_style("8: 3C 3C 2C 3F 3F 2F", "comping")
    assert spec["polyphonic"] and spec["bar"] == [(0.0, ["root", "third", "fifth"]),
                                                   (1.5, ["root", "third", "fifth"]),
                                                   (3.0, ["root", "third", "fifth"])]
    user_styles.save_user_style("comping", "Spinta", spec)
    text = generate_melodic_line(extract_chords_from_track("4G 4Em", {}), "user:Spinta", 4, 40, 90,
                                 polyphonic=True, variation_every=0)
    blocks = [e for e in parse_track_text(text, {}, default_octave=4) if e.kind == "block"]
    assert [round(e.start, 3) for e in blocks] == [0.0, 1.5, 3.0, 4.0, 5.5, 7.0]


def test_user_style_storage_rename_delete(styles_file):
    user_styles.save_user_style("riff", "Uno", learn_line_style("4: c*4 e*4", "riff"))
    assert user_styles.user_style_names("riff") == ["Uno"]
    user_styles.rename_user_style("riff", "Uno", "Due")
    assert user_styles.get_user_style("riff", "user:Due") is not None
    assert user_styles.get_user_style("bass", "user:Due") is None      # ogni tipo il suo elenco
    user_styles.delete_user_style("riff", "Due")
    assert user_styles.user_style_names("riff") == []
    with pytest.raises(ValueError):
        user_styles.save_user_style("riff", "  ", {})


def test_broken_styles_file_counts_as_empty(styles_file):
    (styles_file / "generator_styles.json").write_text("{ non e' json", encoding="utf-8")
    assert user_styles.load_user_styles(reload=True) == {k: {} for k in user_styles.KINDS}


# ------------------------------------------------------------ variabilita' per aspetto (G)

def test_a_single_number_is_the_same_for_every_aspect():
    spans = extract_chords_from_track(CHORDS, {})
    for gen in (lambda v: generate_drum_pattern("funk", 8, variability=v, seed=3),
                lambda v: generate_bass_from_chords(spans, "walking", 2, 4, variability=v, seed=3),
                lambda v: generate_chord_progression("C", "pop", bars=8, variability=v, seed=3)):
        assert gen(0.6) == gen(Variability(0.6, 0.6, 0.6)) == gen({"rhythm": 0.6, "notes": 0.6, "dynamics": 0.6})


def test_dynamics_only_changes_velocities_not_notes():
    spans = extract_chords_from_track(CHORDS, {})
    strip = lambda t: " ".join(x for x in t.split() if not x.endswith("@"))
    plain = generate_bass_from_chords(spans, "eighths", 2, 0)
    dynamic = generate_bass_from_chords(spans, "eighths", 2, 0, variability=Variability(0, 0, 1), seed=1)
    assert "@" not in plain and "@" in dynamic and strip(dynamic) == plain
    velocities = {e.velocity for e in parse_track_text(dynamic, {}) if e.kind == "note"}
    assert len(velocities) > 3
    drums_plain = generate_drum_pattern("rock", 4)
    drums_dyn = generate_drum_pattern("rock", 4, variability=Variability(0, 0, 1), seed=1)
    assert strip(drums_dyn) == strip(drums_plain) and drums_dyn != drums_plain


def test_rhythm_only_keeps_the_harmony_of_a_progression():
    plain = generate_chord_progression("C", "pop", bars=8)
    assert generate_chord_progression("C", "pop", bars=8, variability=Variability(1, 0, 1), seed=2) == plain
    assert generate_chord_progression("C", "pop", bars=8, variability=Variability(0, 1, 0), seed=2) != plain


# ------------------------------------------------------------ rigenerare alcune battute (G)

def _bar_hits(text, bar_beats=4.0):
    out = {}
    for e in parse_track_text(text, {}):
        if e.kind in ("percussion", "block"):
            out.setdefault(int(e.start // bar_beats), []).append((round(e.start, 4), e.velocity, e.name or str(e.items)))
    return out


def test_splice_bars_replaces_only_the_chosen_bars():
    a = generate_drum_pattern("rock", 8, variability=0.8, seed=1)
    b = generate_drum_pattern("rock", 8, variability=0.8, seed=2)
    mixed = splice_bars(a, b, 3, 4, 4.0)
    ok, msg = validate_track_text(mixed, {})
    assert ok, msg
    A, B, M = _bar_hits(a), _bar_hits(b), _bar_hits(mixed)
    assert all(M[i] == (B[i] if i in (2, 3) else A[i]) for i in range(8))
    assert splice_bars(a, b, 1, 8, 4.0) == b and splice_bars(a, a, 2, 5, 4.0) == a


def test_splice_bars_widens_to_keep_notes_whole_and_length_exact():
    spans = extract_chords_from_track(CHORDS, {})
    x = generate_bass_from_chords(spans, "eighths", 2, 0, variability=1.0, seed=1)
    y = generate_bass_from_chords(spans, "eighths", 2, 0, variability=1.0, seed=5)
    z = splice_bars(x, y, 2, 2, 4.0)
    events = parse_track_text(z, {})
    assert max(e.start + e.duration for e in events) == pytest.approx(16.0)
    assert z.split()[:3] == x.split()[:3]


def test_splice_bars_rejects_texts_of_different_shape():
    with pytest.raises(ValueError):
        splice_bars("16: kick r", "8: kick r", 1, 1, 4.0)
    with pytest.raises(ValueError):
        splice_bars("kick r", "kick r", 1, 1, 4.0)
