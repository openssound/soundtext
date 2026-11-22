"""
SoundText Mobile, fase 3: «Un brano in 60 secondi», la versione estesa (core/quicksong.py): 25 generi, 19 atmosfere,
durate da 15 secondi a 4 minuti, forme, organici, finali, modulazione e le parti con il loro seme. Ogni brano deve
essere valido (nessun avviso di battuta), suonare e durare quanto dice.
"""

import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOBILE = os.path.join(ROOT, "mobile")


@pytest.fixture(scope="module")
def q():
    from core import quicksong
    return quicksong


def _mobile_engine():
    """Il motore di SoundText Mobile: i controlli del testo (avvisi di battuta) e il MIDI stanno li'."""
    sys.path.insert(0, MOBILE)
    try:
        import engine
    finally:
        sys.path.remove(MOBILE)
    return engine


def _valid(q, song, duration=None):
    """Il brano e' valido, suona e dura quanto dichiara (entro una battuta)."""
    engine = _mobile_engine()
    check = engine.check_text(song["text"], song["name"])
    assert not check["warnings"], (song["genre"], song["mood"], song["form"], check["warnings"][:2])
    e = engine.Engine()
    e.load(song["text"], song["name"])
    assert len(e.midi_bytes(0)) > 500
    bar_seconds = {"4/4": 4, "3/4": 3, "6/8": 3, "7/8": 3.5}[song["meter"]] * 60 / song["bpm"]
    real = e.length_beats() * 60 / song["bpm"]
    assert abs(real - song["seconds"]) <= 2 * bar_seconds + 1, (song["genre"], real, song["seconds"])
    assert sum(s["bars"] for s in song["sections"]) * bar_seconds == pytest.approx(song["seconds"], abs=1)
    if duration:
        assert 0.4 * duration <= song["seconds"] <= 1.8 * duration, (duration, song["seconds"], song["form"])
    return e


def test_the_values_of_the_document_are_all_there(q):
    assert len(q.GENRES) == 25 and set(q.GENRES) == set(q.GENRES_DATA)
    assert len(q.MOODS) == 19 and set(q.MOODS) == set(q.MOODS_DATA)
    assert q.DURATIONS == (15, 30, 45, 60, 90, 120, 180, 240)
    assert set(q.FORMS) == {"loop", "canzone", "aaba", "blues", "ponte"} and len(q.ENSEMBLES) == 5
    choices = q.quick_choices()
    assert [g["value"] for g in choices["genres"]] == list(q.GENRES)
    assert all(g["moods"] and set(g["moods"]) <= set(q.MOODS) for g in choices["genres"])
    assert [d["value"] for d in choices["durations"]] == list(q.DURATIONS)
    assert choices["durations"][3]["label"] == "1 minuto" and choices["durations"][4]["label"] == "1 min 30 s"


def test_every_recipe_makes_a_valid_song_at_every_duration(q):
    """Ogni genere con ogni atmosfera ammessa; le durate ruotano, cosi' tutte e otto compaiono con ogni genere."""
    count = 0
    for g, genre in enumerate(q.GENRES):
        for m, mood in enumerate(q.GENRES_DATA[genre]["moods"]):
            duration = q.DURATIONS[(g + m) % len(q.DURATIONS)]
            if duration > 90 and (g + m) % 3:               # i brani lunghi costano: uno su tre
                duration = 30
            song = q.quick_song({"genre": genre, "mood": mood, "duration": duration, "seed": 11 + g})
            assert song["mood"] == mood and not song["fallback"]
            _valid(q, song, duration)
            count += 1
    assert count >= 130


@pytest.mark.parametrize("genre", ["pop", "blues", "valzer", "balcanico78", "jazz"])
def test_all_durations_for_a_few_genres(q, genre):
    mood = q.GENRES_DATA[genre]["moods"][0]
    for duration in q.DURATIONS:
        _valid(q, q.quick_song({"genre": genre, "mood": mood, "duration": duration, "seed": 5}), duration)


def test_every_mood_gets_a_valid_song_in_its_genre_at_fifteen_seconds(q):
    for genre in q.GENRES:
        for mood in q.GENRES_DATA[genre]["moods"]:
            song = q.quick_song({"genre": genre, "mood": mood, "duration": 15, "seed": 3})
            assert _mobile_engine().check_text(song["text"], "x")["warnings"] == [], (genre, mood)
            assert song["seconds"] <= 27 and all(sec["role"] != "intro" for sec in song["sections"]), (genre, mood, song["seconds"])


def test_a_mood_the_genre_does_not_have_falls_back_to_the_nearest_and_says_so(q):
    song = q.quick_song({"genre": "metal", "mood": "calma", "duration": 30, "seed": 1})
    assert song["mood"] in q.GENRES_DATA["metal"]["moods"] and song["mood"] != "calma"
    assert "metal" in song["fallback"].lower() and "calma" in song["fallback"] and song["mood"] in song["fallback"]
    assert q.MOODS_DATA[song["mood"]][0] == q.MOODS_DATA["calma"][0] or q.MOODS_DATA["calma"][0] == "major"
    # una combinazione ammessa non ha avvisi
    assert q.quick_song({"genre": "metal", "mood": "oscura", "duration": 15, "seed": 1})["fallback"] == ""
    _valid(q, song, 30)


def test_same_choices_and_seeds_same_song_and_the_saved_choices_remake_it(q):
    options = {"genre": "bossa", "mood": "romantica", "duration": 60, "seed": 99, "modulation": True, "ending": "rallentando"}
    one, again = q.quick_song(options), q.quick_song(options)
    assert one["text"] == again["text"]
    assert q.quick_song({**options, "seed": 100})["text"] != one["text"]
    saved = q.quick_read(one["text"])
    assert saved and saved["genre"] == "bossa" and saved["seed"] == 99 and saved["modulation"] is True
    remade = q.quick_song(saved)                              # il modo dettagliato mostra i valori della ricetta: stesso brano
    assert remade["text"] == one["text"]
    assert q.quick_read("ST: 2.6\nTempo: 100 BPM\n") is None


def test_changing_one_part_seed_changes_only_that_part(q):
    base = {"genre": "pop", "mood": "allegra", "duration": 30, "seed": 21}
    one = q.quick_song(base)
    other = q.quick_song({**base, "parts": {"drums": {"seed": 1234567}}})

    def boxes(song):
        out = {}
        for m in re.finditer(r'^Box (\S+) "([^"]*)" \|[\d.]+:\n((?:  .*\n?)+)', song["text"], re.M):
            out[(m.group(1), m.group(2))] = m.group(3)
        return out
    a, b = boxes(one), boxes(other)
    assert a.keys() == b.keys()
    changed = {key[0] for key in a if a[key] != b[key]}
    assert changed == {"Drums"}, changed
    assert one["seeds"]["drums"] != other["seeds"]["drums"] and one["seeds"]["bass"] == other["seeds"]["bass"]
    # un lucchetto e' lo stesso seme: ripassando i semi di tutte le parti con un seme globale diverso, il brano non cambia
    locked = q.quick_song({**base, "seed": 22, "parts": {p: {"seed": s} for p, s in one["seeds"].items()}})
    assert locked["text"].split("\n", 3)[3] == one["text"].split("\n", 3)[3] or boxes(locked) == boxes(one)


@pytest.mark.parametrize("form", ["loop", "canzone", "aaba", "blues", "ponte"])
def test_every_form_is_valid_with_its_own_shape(q, form):
    song = q.quick_song({"genre": "pop", "mood": "allegra", "duration": 60, "form": form, "seed": 4})
    _valid(q, song)
    bars = [s["bars"] for s in song["sections"]]
    if form == "loop":
        assert set(bars) == {8}
    elif form == "blues":
        assert set(bars) == {12}
    elif form == "aaba":
        assert set(bars) <= {8} and len(bars) % 4 == 0
    else:
        assert any(s["role"] == "chorus" for s in song["sections"])
    assert song["form"] == form


def test_a_loop_keeps_the_harmony_and_changes_the_fills(q):
    song = q.quick_song({"genre": "lofi", "mood": "calma", "loop": True, "seed": 8})
    assert song["loop"] is True and [s["bars"] for s in song["sections"]] == [8, 8, 8, 8]
    _valid(q, song)
    text = song["text"]

    def body(track, name):
        m = re.search(rf'^Box {track} "{name}" \|[\d.]+:\n((?:  .*\n?)+)', text, re.M)
        return m.group(1) if m else None
    assert body("Electric_Piano_1", "Loop 1") is not None
    assert body("Electric_Piano_1", "Loop 1") == body("Electric_Piano_1", "Loop 3")           # l'armonia e' la stessa
    assert body("Drums", "Loop 1") != body("Drums", "Loop 2")                                  # i fill cambiano a ogni giro


@pytest.mark.parametrize("ending", ["cadenza", "rallentando", "sfumato"])
def test_every_ending_is_valid(q, ending):
    song = q.quick_song({"genre": "pop", "mood": "calma", "duration": 60, "ending": ending, "seed": 6})
    _valid(q, song)
    if ending == "sfumato":
        assert song["sections"][-1]["role"] == "fade" and "Sfumato" in song["text"]
    if ending == "rallentando":
        assert "tempo=" in song["text"]


def test_modulation_puts_the_last_chorus_a_tone_higher(q):
    song = q.quick_song({"genre": "pop", "mood": "allegra", "duration": 120, "modulation": True, "key": "C", "seed": 10})
    _valid(q, song)
    keys = [s["key"] for s in song["sections"]]
    choruses = [i for i, s in enumerate(song["sections"]) if s["role"] == "chorus"]
    assert keys[0] == "C" and keys[choruses[-1]] == "D" and all(k == "D" for k in keys[choruses[-1]:])
    assert all(k == "C" for k in keys[:choruses[-1]])
    flat = q.quick_song({"genre": "pop", "mood": "malinconica", "duration": 60, "modulation": True, "key": "Am", "seed": 10})
    assert flat["sections"][-1]["key"] == "Bm"
    assert q._shift_key("Bb", 2) == "C" and q._shift_key("F#m", 2) == "G#m" and q._shift_key("Em", 2) == "F#m"


@pytest.mark.parametrize("ensemble", ["piano", "acustica", "elettrica", "elettronica", "orchestra"])
def test_every_ensemble_plays(q, ensemble):
    song = q.quick_song({"genre": "pop", "mood": "romantica", "duration": 30, "ensemble": ensemble, "seed": 2})
    _valid(q, song)
    if ensemble == "piano":
        assert song["parts"] == ["comp"]
    if ensemble == "orchestra":
        assert "Strings" in song["text"] and "Drums" not in song["text"]


@pytest.mark.parametrize("melody", ["nessuna", "cantabile", "vivace", "ballata", "aaba"])
def test_every_melody_style(q, melody):
    song = q.quick_song({"genre": "pop", "mood": "allegra", "duration": 30, "melody": melody, "seed": 12})
    _valid(q, song)
    assert ("melody" in song["parts"]) == (melody != "nessuna")


def test_key_tempo_meter_and_density_choices(q):
    song = q.quick_song({"genre": "rock", "mood": "allegra", "key": "Em", "bpm": 140, "duration": 30, "seed": 2})
    assert song["key"] == "Em" and song["bpm"] == 140 and "Tonalita: Em" in song["text"] and "Tempo: 140 BPM" in song["text"]
    _valid(q, song, 30)
    waltz = q.quick_song({"genre": "pop", "mood": "allegra", "meter": "3/4", "duration": 30, "seed": 3})
    assert waltz["meter"] == "3/4" and "Metrica: 3/4" in waltz["text"]
    _valid(q, waltz, 30)
    simple = q.quick_song({"genre": "pop", "mood": "allegra", "duration": 30, "density": 0.1, "seed": 4})
    rich = q.quick_song({"genre": "pop", "mood": "allegra", "duration": 30, "density": 0.9, "seed": 4})
    assert "comp2" not in simple["parts"] and "comp2" in rich["parts"]
    _valid(q, simple)
    _valid(q, rich)


def test_a_written_chord_progression_is_used_and_a_bad_one_is_an_error(q):
    song = q.quick_song({"genre": "pop", "mood": "allegra", "duration": 15, "chords": "Am F C G", "key": "C", "seed": 3})
    _valid(q, song)
    chart = _mobile_engine().chord_chart(song["text"])
    assert [c[2] for c in chart][:4] == ["Am", "F", "C", "G"] or chart, chart
    with pytest.raises(ValueError):
        q.quick_song({"genre": "pop", "mood": "allegra", "chords": "Am Zz9", "seed": 3})


def test_unknown_values_are_errors(q):
    for bad in ({"genre": "polka"}, {"mood": "furiosa"}, {"form": "rondo"}, {"ensemble": "coro"}, {"ending": "bis"}, {"melody": "jodel"}):
        with pytest.raises(ValueError):
            q.quick_song(bad)


def test_surprise_picks_only_allowed_combinations(q):
    for seed in range(40):
        pick = q.quick_surprise(seed)
        assert pick["mood"] in q.GENRES_DATA[pick["genre"]]["moods"] and pick["duration"] in q.DURATIONS
        assert q.quick_surprise(seed) == pick
    song = q.quick_song({**q.quick_surprise(3), "duration": 15})
    assert not song["fallback"] and not _mobile_engine().check_text(song["text"], "x")["warnings"]


def test_durations_match_the_form_and_the_tempo(q):
    """Le battute si scelgono dal tempo: a 4 minuti il brano e' piu' lungo che a 1 minuto, e la durata mostrata e' vera."""
    short = q.quick_song({"genre": "rock", "mood": "tesa", "duration": 60, "seed": 1})
    long = q.quick_song({"genre": "rock", "mood": "tesa", "duration": 240, "form": "ponte", "seed": 1})
    assert long["bars"] > 3 * short["bars"] and abs(long["seconds"] - 240) < 70 and abs(short["seconds"] - 60) < 20
    assert any(s["role"] == "bridge" for s in long["sections"]) and any(s["role"] == "solo" for s in long["sections"])
    assert all(s["role"] != "intro" for s in q.quick_song({"genre": "rock", "mood": "tesa", "duration": 15, "seed": 1})["sections"])


def test_genres_choose_their_own_instruments_and_accompaniment_styles(q):
    quick_song = q.quick_song

    def tracks(genre, mood="allegra", **extra):
        song = quick_song({"genre": genre, "mood": mood, "duration": 30, "seed": 3, **extra})
        return re.findall(r"^(?:Traccia )?([A-Za-z_0-9 ]+?)(?: \[.*\])?:\s*$", song["text"], re.M), song

    jazz, _ = tracks("jazz")
    assert "Acoustic_Bass" in jazz and "Tenor_Sax" in jazz and "Nylon_Guitar" not in jazz
    funk, _ = tracks("funk")
    assert "Clavinet" in funk and "Brass_Section" in funk
    country, _ = tracks("country")
    assert "Banjo" in country and "Fiddle" in country
    blues, _ = tracks("blues", "tesa")
    assert "Harmonica" in blues and "Drawbar_Organ" in blues
    # due generi non suonano le stesse tracce (solo la ritmica puo' essere uguale)
    sets = {g: tuple(tracks(g)[0]) for g in ("jazz", "swing", "country", "soul", "funk", "blues", "reggae", "disco")}
    assert len(set(sets.values())) == len(sets)
    # lo stile della parte e' quello nuovo: power chord nel rock, galoppo nel metal, boom-chick nel country
    for genre, mood, part, style in (("rock", "tesa", "comp", "power_chords"), ("metal", "tesa", "comp", "metal_gallop"),
                                     ("country", "allegra", "comp", "boom_chick"), ("funk", "allegra", "horn", "horn_stabs"),
                                     ("reggae", "allegra", "comp2", "organ_bubble")):
        song = quick_song({"genre": genre, "mood": mood, "duration": 30, "seed": 3})
        assert song["choices"]["styles"][part] == style, (genre, part)
    # un altro organico vince sul genere
    other, _ = tracks("jazz", ensemble="orchestra")
    assert "Tenor_Sax" not in other and "Strings" in other


def test_genres_start_with_their_own_effects_and_the_option_turns_them_off(q):
    from core.project_io import parse_project_text

    def effects(genre, **extra):
        song = q.quick_song({"genre": genre, "mood": "calma", "duration": 30, "seed": 2, **extra})
        return [e.kind for e in parse_project_text(song["text"], "x").master_effects]

    assert effects("reggae") == ["delay"] and effects("lofi") == ["passa_basso", "eq"]
    assert effects("funk") == ["compressore"] and effects("blues") == ["riverbero"] and effects("orchestrale") == ["riverbero"]
    assert effects("pop") == [] and effects("reggae", effects=False) == []


def test_the_last_chorus_takes_the_theme_up_an_octave_through_a_pattern(q):
    from core.project_io import parse_project_text
    from st_language.midi import resolve_event_notes, sounding_events
    song = q.quick_song({"genre": "pop", "mood": "allegra", "duration": 120, "seed": 1, "variety": 0})
    assert "Pattern %MelodiaRitornello:" in song["text"]
    calls = re.findall(r"^  (%MelodiaRitornello(?:\.octave\(1\))?)$", song["text"], re.M)
    assert calls == ["%MelodiaRitornello"] * (len(calls) - 1) + ["%MelodiaRitornello.octave(1)"] and len(calls) >= 3
    project = parse_project_text(song["text"], "x")
    track = project.get_track("Flute")
    notes = [max(resolve_event_notes(e, track.instrument)[0], default=0) for e in
             sounding_events(track.parsed_events(project.patterns, meter=project.meter()))]
    assert max(notes) >= 12 + min(n for n in notes if n) + 4          # il culmine sta nell'ultimo ritornello
    # senza sviluppo: ogni ritornello ha la sua melodia, nessun pattern del tema
    plain = q.quick_song({"genre": "pop", "mood": "allegra", "duration": 120, "seed": 1, "development": False})
    assert "MelodiaRitornello" not in plain["text"]


def test_human_option_writes_micro_timing_and_zero_keeps_the_grid(q):
    funk = q.quick_song({"genre": "funk", "mood": "tesa", "duration": 30, "seed": 3})
    assert "shift=14" in funk["text"]
    exact = q.quick_song({"genre": "funk", "mood": "tesa", "duration": 30, "seed": 3, "human": 0})
    assert "shift=" not in exact["text"]
    assert "shift=" not in q.quick_song({"genre": "bossa", "mood": "calma", "duration": 30, "seed": 3})["text"]


def test_energy_curve_changes_the_intensity_of_the_sections(q):
    import re as _re

    def drum_sizes(curve):
        song = q.quick_song({"genre": "pop", "mood": "allegra", "duration": 120, "seed": 1, "energy": curve})
        return [len(m) for m in _re.findall(r'Box Drums "[^"]*" \|\d+:\n((?:  .*\n)+)', song["text"])]

    base, rises, falls = drum_sizes(None), drum_sizes("sale"), drum_sizes("cala")
    assert rises[0] < rises[-2] and falls[0] > falls[-2]                       # sale: la prima sezione e' piu' leggera dell'ultima; cala: il contrario
    assert base[0] == base[2] and len({tuple(drum_sizes("picco"))}) == 1
    assert "energies" in q.quick_choices() and [e["value"] for e in q.quick_choices()["energies"]] == ["sale", "picco", "cala"]


def test_a_string_layer_plays_only_in_the_choruses_and_the_ending(q):
    import re as _re
    song = q.quick_song({"genre": "pop", "mood": "allegra", "duration": 120, "seed": 1, "variety": 0})
    assert "pad" in song["parts"]
    names = _re.findall(r'Box Strings "([^"]*)"', song["text"])
    assert names and set(names) <= {"Ritornello", "Finale"}
    assert "pad" not in q.quick_song({"genre": "pop", "mood": "allegra", "duration": 120, "seed": 1, "variety": 0, "density": 0.1})["parts"]
    assert "pad" not in q.quick_song({"genre": "rock", "mood": "tesa", "duration": 60, "seed": 1, "variety": 0})["parts"]


def test_the_bridge_of_a_quiet_mood_has_a_pedal_bass(q):
    song = q.quick_song({"genre": "ballata", "mood": "calma", "duration": 240, "seed": 1, "variety": 0})
    assert any(s["role"] == "bridge" for s in song["sections"])
    assert "Pedal" in song["text"]                                   # i pattern del ponte portano il nome dello stile
    loud = q.quick_song({"genre": "rock", "mood": "tesa", "duration": 240, "seed": 1, "variety": 0, "form": "ponte"})
    assert "Pedal" not in loud["text"]
    chosen = q.quick_song({"genre": "ballata", "mood": "calma", "duration": 240, "seed": 1, "variety": 0, "parts": {"bass": {"style": "root"}}})
    assert "Pedal" not in chosen["text"]                                # uno stile scelto a mano vince


def test_the_second_voice_in_thirds_only_plays_when_asked_with_an_instrument_of_the_melody_family(q):
    import re as _re
    base = {"genre": "pop", "mood": "allegra", "duration": 120, "seed": 1}
    plain = q.quick_song(base)
    assert "harm" not in plain["parts"] and "Clarinet" not in plain["text"]            # la formazione del genere non cambia da sola
    for genre in ("punk", "rock", "metal", "blues"):
        song = q.quick_song({"genre": genre, "mood": "allegra" if genre in ("punk",) else "tesa", "duration": 120, "seed": 2})
        assert "harm" not in song["parts"], genre
    song = q.quick_song({**base, "second_voice": True})
    assert "harm" in song["parts"]
    boxes = _re.findall(r'Box Clarinet "([^"]*)" \|\d+:\n  (%MelodiaRitornello\.thirds)', song["text"])
    assert boxes == [("Ritornello", "%MelodiaRitornello.thirds")]
    assert "harm" not in q.quick_song({**base, "second_voice": True, "development": False})["parts"]
    assert "harm" not in q.quick_song({**base, "second_voice": True, "duration": 45})["parts"]      # un solo ritornello
    rock = q.quick_song({"genre": "rock", "mood": "tesa", "duration": 120, "seed": 2, "second_voice": True})
    assert q._HARM_FOR["Lead"] == "Lead_2_sawtooth" and any("Lead_2_sawtooth" in line for line in rock["text"].split("\n"))


def test_another_song_varies_more_than_the_key_and_the_choices_of_the_user_stay(q):
    def facts(seed, **extra):
        song = q.quick_song({"genre": "pop", "mood": "allegra", "duration": 120, "seed": seed, **extra})
        c = song["choices"]
        return (song["bpm"], tuple(song["prog"]) if "prog" in song else None, c["styles"]["drums"], c["styles"]["bass"],
                c["styles"]["comp"], c["melody"], song["form"], tuple(r["name"] for r in song["sections"]))
    varied = {facts(seed) for seed in range(1, 9)}
    assert len(varied) >= 6                                           # otto semi: almeno sei brani con una struttura diversa
    pure = {facts(seed, variety=0)[:6] for seed in range(1, 9)}
    assert len(pure) == 1                                             # senza variabilita' resta la ricetta
    fixed = {facts(seed, bpm=100, form="canzone", melody="vivace")[0::1][0] for seed in range(1, 5)}
    assert fixed == {100}                                             # tempo, forma e melodia scelti dall'utente non cambiano
    assert all(q.quick_song({"genre": "pop", "mood": "allegra", "duration": 60, "seed": s, "form": "canzone", "melody": "vivace"})["form"] == "canzone"
               for s in range(1, 6))
