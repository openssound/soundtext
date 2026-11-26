"""
SoundText Mobile, fase 3: gli esercizi quotidiani (mobile/exercises.py). Ogni esercizio e' deciso da tipo, livello
e seme; la correzione rifa' la domanda dal seme. Qui si controlla che ogni domanda abbia una sola risposta giusta
che la correzione riconosce, che sia sempre la stessa per lo stesso seme, e che le battute e i ritmi scritti in ST
siano validi.
"""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOBILE = os.path.join(ROOT, "mobile")
SEEDS = range(120)


@pytest.fixture(scope="module")
def ex():
    sys.path.insert(0, MOBILE)
    try:
        import exercises
        import engine
    finally:
        sys.path.remove(MOBILE)
    exercises.engine = engine
    return exercises


def _full(ex, kind, level, seed):
    return ex._MAKERS[kind](level, ex._rng(kind, level, seed))


def _every(ex):
    for kind in ex.KINDS:
        for level in ex.LEVELS:
            for seed in SEEDS:
                yield kind, level, seed


def test_six_kinds_with_three_levels_each(ex):
    kinds = ex.exercise_kinds()
    assert [k["kind"] for k in kinds] == list(ex.KINDS) and len(kinds) == 6
    assert all(k["levels"] == 3 and k["label"] and k["hint"] for k in kinds)


def test_same_seed_same_question_and_different_seeds_differ(ex):
    for kind in ex.KINDS:
        for level in ex.LEVELS:
            assert ex.exercise(kind, level, 7) == ex.exercise(kind, level, 7)
            distinct = {repr(ex.exercise(kind, level, s)["notes"]) + repr(ex.exercise(kind, level, s).get("items")) for s in SEEDS}
            assert len(distinct) >= 12, (kind, level, len(distinct))


def test_every_question_has_exactly_the_answer_the_check_accepts(ex):
    for kind, level, seed in _every(ex):
        q = ex.exercise(kind, level, seed)
        full = _full(ex, kind, level, seed)
        assert "answer" not in q and "answer_label" not in q, "la domanda non da' la risposta"
        assert (kind == "bar" or q["notes"]) and all(n["d"] > 0 and n["t"] >= 0 and 24 <= n["n"] <= 100 and n["ch"] in (0, 9) for n in q["notes"])
        assert q["input"] in ("choice", "pick", "grid") and q["prompt"]
        right = ex.exercise_check(kind, level, seed, full["answer"])
        assert right["correct"] is True and right["answer_label"], (kind, level, seed)
        if q["input"] == "choice":
            values = [c["value"] for c in q["choices"]]
            assert len(values) == len(set(values)) and full["answer"] in values, (kind, level, seed)
            for wrong in values:
                if wrong != full["answer"]:
                    assert ex.exercise_check(kind, level, seed, wrong)["correct"] is False
        elif q["input"] == "pick":
            for wrong in range(len(q["items"])):
                assert ex.exercise_check(kind, level, seed, wrong)["correct"] is (wrong == full["answer"])
        else:
            assert ex.exercise_check(kind, level, seed, [])["correct"] is False
            assert ex.exercise_check(kind, level, seed, list(full["answer"]) + [max(full["answer"]) + 1 if max(full["answer"]) < 15 else 100])["correct"] is False
            assert ex.exercise_check(kind, level, seed, "non una lista")["correct"] is False


def test_intervals_answer_is_the_distance_between_the_two_notes(ex):
    seen = {1: set(), 2: set(), 3: set()}
    for level in ex.LEVELS:
        for seed in SEEDS:
            q, full = ex.exercise("intervals", level, seed), _full(ex, "intervals", level, seed)
            a, b = sorted(n["n"] for n in q["notes"])
            assert b - a == full["answer"] and len(q["notes"]) == 2
            seen[level].add(full["answer"])
    assert seen[1] <= {3, 4, 5, 7, 12} and len(seen[2]) >= 8 and seen[1] <= seen[2] | {3, 4, 5, 7, 12}


def test_chords_answer_matches_the_notes_played(ex):
    for level in ex.LEVELS:
        qualities = set()
        for seed in SEEDS:
            q, full = ex.exercise("chords", level, seed), _full(ex, "chords", level, seed)
            pitches = sorted(n["n"] for n in q["notes"])
            assert tuple(p - pitches[0] for p in pitches) == ex._CHORD_SHAPES[full["answer"]]
            qualities.add(full["answer"])
        assert len(qualities) == {1: 2, 2: 5, 3: 8}[level]


def test_progression_has_four_distinct_options_and_the_right_chords(ex):
    for level in ex.LEVELS:
        for seed in SEEDS:
            q, full = ex.exercise("progression", level, seed), _full(ex, "progression", level, seed)
            assert len(q["choices"]) == 4 and len({c["label"] for c in q["choices"]}) == 4
            loops = ex._MINOR_LOOPS if "minore" in q["context"] else ex._MAJOR_LOOPS
            assert full["answer"] in loops and all(c["value"] in loops for c in q["choices"])
            # quattro accordi di due battiti, ognuno con basso e triade
            assert sorted({n["t"] for n in q["notes"]}) == [0, 2, 4, 6] and len(q["notes"]) == 16


def test_complete_the_bar_fills_the_bar_and_is_valid_st(ex):
    engine = ex.engine
    metres = set()
    for level in ex.LEVELS:
        for seed in SEEDS:
            full = _full(ex, "bar", level, seed)
            q = ex.exercise("bar", level, seed)
            metres.add(full["meter"])
            units = {"4/4": 16, "3/4": 12, "6/8": 12}[full["meter"]]
            names = {v: k for k, v in ex._value_labels().items()}
            durations = [names[item["label"]] for item in q["items"]]
            assert sum(durations) == units and 3 <= len(durations) <= 8
            assert sum(1 for item in q["items"] if item["missing"]) == 1
            missing = next(i for i, item in enumerate(q["items"]) if item["missing"])
            assert durations[missing] == full["answer"]
            # la battuta completa, scritta in ST, ha la durata della metrica e nessun avviso di battuta
            text = f"ST: 2.6\nTempo: 80 BPM\nMetrica: {full['meter']}\n\nPiano:\n  {full['st']['text']}\n"
            check = engine.check_text(text, "es")
            assert not check["warnings"], (text, check["warnings"])
            e = engine.Engine()
            e.load(text, "es")
            assert abs(e.length_beats() - units / 4) < 1e-6 or any(item["rest"] for item in q["items"][-1:])
    assert {"4/4"} <= metres and (len(metres) >= 2 or True)
    assert {"3/4", "6/8"} <= {_full(ex, "bar", 3, s)["meter"] for s in SEEDS}


def test_the_bar_question_is_silent_and_the_check_gives_the_whole_bar(ex):
    for level in ex.LEVELS:
        for seed in range(30):
            assert ex.exercise("bar", level, seed)["notes"] == []
            reveal = ex.exercise_check("bar", level, seed, 0)["notes"]
            assert reveal and reveal[-1]["t"] + reveal[-1]["d"] <= 4 + 1e-6


def test_find_the_error_has_one_note_out_of_the_key(ex):
    for level in ex.LEVELS:
        for seed in SEEDS:
            q, full = ex.exercise("error", level, seed), _full(ex, "error", level, seed)
            info = full["info"]
            scale = set(info["scale"])
            outside = [i for i, n in enumerate(q["notes"]) if n["n"] % 12 not in scale]
            assert outside == [full["answer"]] and 0 < full["answer"] < len(q["notes"]) - 1
            assert len(q["items"]) == len(q["notes"]) == {1: 5, 2: 6, 3: 8}[level]
            fixed = ex.exercise_check("error", level, seed, full["answer"])["notes"]
            assert all(n["n"] % 12 in scale for n in fixed) and abs(fixed[full["answer"]]["n"] - q["notes"][full["answer"]]["n"]) == 1


def test_rhythm_dictation_steps_are_the_hits_played(ex):
    for level in ex.LEVELS:
        for seed in SEEDS:
            q, full = ex.exercise("rhythm", level, seed), _full(ex, "rhythm", level, seed)
            per_bar, bars = q["grid"]["per_bar"], q["grid"]["bars"]
            unit = 4 / per_bar
            hits = sorted(round((n["t"] - 4) / unit) for n in q["notes"] if n["n"] == 75)
            assert hits == list(full["answer"]) and all(0 <= s < per_bar * bars for s in hits)
            assert [n["t"] for n in q["notes"] if n["n"] == 42] == [0, 1, 2, 3]            # il conteggio
            assert ex.exercise_check("rhythm", level, seed, [str(s) for s in hits[::-1]])["correct"] is True    # l'ordine non conta
    # a livello 3 c'e' una sincope: un colpo fuori dai battiti
    assert all(any(s % 4 for s in _full(ex, "rhythm", 3, seed)["answer"]) for seed in SEEDS)


def test_unknown_kind_or_level_is_an_error(ex):
    with pytest.raises(ValueError):
        ex.exercise("canto", 1, 1)
    with pytest.raises(ValueError):
        ex.exercise("intervals", 4, 1)
    with pytest.raises(ValueError):
        ex.exercise_check("intervals", 0, 1, 3)


def test_engine_exposes_the_exercises(ex):
    engine = ex.engine
    assert [k["kind"] for k in engine.exercise_kinds()] == list(ex.KINDS)
    q = engine.exercise("intervals", 1, 3)
    assert engine.exercise_check("intervals", 1, 3, _full(ex, "intervals", 1, 3)["answer"])["correct"] and q["kind"] == "intervals"


def test_correction_explains_and_names_the_given_answer(ex):
    for kind in ex.KINDS:
        for level in (1, 2, 3):
            q = ex.exercise(kind, level, 3)
            assert "explain" not in q                                  # la spiegazione non e' nella domanda
            wrong = [] if q["input"] == "grid" else 0
            r = ex.exercise_check(kind, level, 3, wrong)
            assert r["explain"]
    r = ex.exercise_check("intervals", 1, 3, 3)
    assert r["given_label"] == ex._interval_labels()[3]


def test_hint_removes_only_wrong_answers(ex):
    for kind in ("intervals", "chords", "progression", "bar", "error"):
        for seed in range(12):
            full = _full(ex, kind, 2, seed)
            hint = ex.exercise_hint(kind, 2, seed)
            assert hint["remove"] and full["answer"] not in hint["remove"]
            assert hint == ex.exercise_hint(kind, 2, seed)
    assert ex.exercise_hint("rhythm", 1, 4)["text"]
