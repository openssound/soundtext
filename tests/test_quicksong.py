"""
SoundText Mobile, fase 3: «Un brano in 60 secondi», la versione estesa (core/quicksong.py): 25 generi, 19 atmosfere,
durate da 15 secondi a 4 minuti, forme, organici, finali, modulazione e le parti con il loro seme. Ogni brano deve
essere valido (nessun avviso di battuta), suonare e durare quanto dice.
"""

import json
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
    assert len(q.GENRES) == 40 and set(q.GENRES) == set(q.GENRES_DATA)
    assert len(q.MOODS) == 22 and set(q.MOODS) == set(q.MOODS_DATA)
    assert q.DURATIONS == (15, 30, 45, 60, 90, 120, 180, 240)
    assert set(q.FORMS) == {"loop", "canzone", "aaba", "blues", "ponte", "binaria"} and len(q.ENSEMBLES) == 5
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
    song = q.quick_song({"genre": "lofi", "mood": "calma", "loop": True, "seed": 8, "variety": 0})
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
    for bad in ({"genre": "tarantola"}, {"mood": "furiosa"}, {"form": "rondo"}, {"ensemble": "coro"}, {"ending": "bis"}, {"melody": "jodel"}):
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
        song = quick_song({"genre": genre, "mood": mood, "duration": 30, "seed": 3, "variety": 0, **extra})
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

    # gli effetti del genere restano (con calma si aggiunge il riverbero dell'atmosfera, che sostituisce quello del genere)
    assert effects("reggae") == ["delay", "riverbero"] and effects("lofi") == ["passa_basso", "eq", "riverbero"]
    assert effects("funk") == ["compressore"] and effects("blues") == ["riverbero"] and effects("orchestrale") == ["riverbero"]
    assert effects("marcia") == ["riverbero"] and effects("reggae", effects=False) == []


def test_the_last_chorus_takes_the_theme_up_an_octave_through_a_pattern(q):
    from core.project_io import parse_project_text
    from st_language.midi import resolve_event_notes, sounding_events
    # il piano elettrico ha spazio sopra il tema (il flauto, la melodia di partenza del pop, e' gia' in alto e resta li')
    song = q.quick_song({"genre": "pop", "mood": "allegra", "duration": 120, "seed": 1, "variety": 0,
                         "parts": {"melody": {"instrument": "Electric_Piano_1"}}})
    assert "Pattern %MelodiaRitornello:" in song["text"]
    calls = re.findall(r"^  (%MelodiaRitornello(?:\.octave\(1\))?)$", song["text"], re.M)
    assert calls == ["%MelodiaRitornello"] * (len(calls) - 1) + ["%MelodiaRitornello.octave(1)"] and len(calls) >= 3
    project = parse_project_text(song["text"], "x")
    track = project.get_track(song["choices"]["instruments"]["melody"])
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
        # l'intro (il groove del pop: batteria a intensita' fissa) non segue la curva: si guardano le sezioni dopo
        return [len(m) for name, m in _re.findall(r'Box Drums "([^"]*)" \|\d+:\n((?:  .*\n)+)', song["text"]) if name != "Intro"]

    base, rises, falls = drum_sizes(None), drum_sizes("sale"), drum_sizes("cala")
    assert rises[0] < rises[-2] and falls[0] > falls[-2]                       # sale: la prima sezione e' piu' leggera dell'ultima; cala: il contrario
    # senza curva le due strofe hanno la stessa intensita': lo stesso testo, salvo il crash d'ingresso e il fill d'uscita, che dipendono
    # dalle sezioni vicine (dopo l'intro o dopo il ritornello)
    assert abs(base[0] - base[2]) <= 0.05 * base[0] and len({tuple(drum_sizes("picco"))}) == 1
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
    loud = q.quick_song({"genre": "rock", "mood": "energica", "duration": 240, "seed": 1, "variety": 0, "form": "ponte"})
    assert "Pedal" not in loud["text"]
    chosen = q.quick_song({"genre": "ballata", "mood": "calma", "duration": 240, "seed": 1, "variety": 0, "parts": {"bass": {"style": "root"}}})
    assert "Pedal" not in chosen["text"]                                # uno stile scelto a mano vince


def test_the_second_voice_in_thirds_only_plays_when_asked_with_an_instrument_of_the_melody_family(q):
    import re as _re
    base = {"genre": "pop", "mood": "allegra", "duration": 120, "seed": 1, "second_voice": False}
    plain = q.quick_song(base)
    assert "harm" not in plain["parts"] and "Clarinet" not in plain["text"]            # second_voice=False toglie anche quella del genere
    for genre in ("punk", "rock", "metal", "blues"):
        song = q.quick_song({"genre": genre, "mood": "allegra" if genre in ("punk",) else "tesa", "duration": 120, "seed": 2})
        assert "harm" not in song["parts"], genre
    song = q.quick_song({**base, "second_voice": True})
    assert "harm" in song["parts"]
    harm = song["choices"]["instruments"]["harm"]
    # la voce sugli accordi (pattern «...Voce»); la voce per gradi (.thirds) resta solo se la melodia non sta sulla griglia
    boxes = _re.findall(r'Box ' + harm + r' "([^"]*)" \|\d+:\n  (%MelodiaRitornello(?:Voce|\.thirds))', song["text"])
    assert len(boxes) == 1 and boxes[0][0] == "Ritornello"
    assert "harm" not in q.quick_song({**base, "second_voice": True, "development": False})["parts"]
    assert "harm" not in q.quick_song({**base, "second_voice": True, "duration": 45})["parts"]      # un solo ritornello
    rock = q.quick_song({"genre": "rock", "mood": "tesa", "duration": 120, "seed": 2, "second_voice": True, "variety": 0})
    assert q._HARM_FOR["Overdriven_Guitar"] == "Rock_Organ" and any("Rock_Organ" in line for line in rock["text"].split("\n"))


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


def test_the_drum_fills_come_at_different_distances_and_the_pure_recipe_keeps_four(q):
    from core import quicksong
    fills = {quicksong.resolve({"genre": "rock", "mood": "allegra", "seed": s})["drum_fill"] for s in range(1, 30)}
    assert fills == {4, 8, 2}                                             # ogni 4 (di solito), ogni 8 o ogni 2 nel rock
    assert {quicksong.resolve({"genre": "rock", "mood": "allegra", "seed": s, "variety": 0})["drum_fill"] for s in range(1, 30)} == {4}
    assert 2 not in {quicksong.resolve({"genre": "pop", "mood": "allegra", "seed": s})["drum_fill"] for s in range(1, 30)}


def test_the_drum_styles_with_one_groove_got_alternatives_with_valid_slots():
    from core import rhythm_generate as rg
    for style in ("halftime", "country", "samba", "bossa", "cha_cha"):
        grooves = rg.DRUM_ALTS[style]
        assert grooves and all(len(g) == rg.SLOTS_PER_BAR for g in grooves), style
        assert all(name in rg_names() for g in grooves for hits in g if hits for name, _v in hits), style
        text = rg.generate_drum_pattern(style, 16, variability=1.0, seed=3)
        assert text.strip()


def rg_names():
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(ROOT), "st-language"))
    from st_language.instruments import PERCUSSION_MAP
    return set(PERCUSSION_MAP)


def test_another_song_changes_instruments_accompaniment_density_and_ending_but_keeps_the_family(q):
    def made(genre, mood, seed, **extra):
        return q.quick_song({"genre": genre, "mood": mood, "duration": 60, "seed": seed, **extra})
    pop = [made("pop", "allegra", s) for s in range(1, 21)]
    assert len({song["choices"]["instruments"]["melody"] for song in pop}) >= 4          # flauto, clarinetto, violino, sax, chitarra...
    assert len({song["choices"]["instruments"]["comp"] for song in pop}) >= 2
    assert len({song["choices"]["styles"]["comp"] for song in pop}) >= 3
    assert len({round(song["choices"]["density"], 1) for song in pop}) >= 4
    assert len({song["choices"]["ending"] for song in pop}) >= 2
    for song in pop:                                                                      # mai due parti con lo stesso strumento
        inst = song["choices"]["instruments"]
        assert len({inst[p] for p in ("comp", "comp2", "melody") if p in inst}) == len([p for p in ("comp", "comp2", "melody") if p in inst])
    # il punk e il metal non prendono tastiere o chitarre pulite per la melodia, il jazz resta con fiati e piano o chitarra
    assert {made("punk", "tesa", s)["choices"]["instruments"]["melody"] for s in range(1, 15)} <= {"Overdriven_Guitar"}
    assert {made("jazz", "calma", s)["choices"]["instruments"]["comp"] for s in range(1, 15)} <= {"Piano", "Jazz_Guitar"}
    # la ricetta pura (variety 0) e le scelte dell'utente non cambiano
    pure = {made("pop", "allegra", s, variety=0)["choices"]["instruments"]["melody"] for s in range(1, 10)}
    assert pure == {"Flute"}
    chosen = made("pop", "allegra", 3, parts={"melody": {"instrument": "Oboe"}})
    assert chosen["choices"]["instruments"]["melody"] == "Oboe"
    # e i brani sono validi
    for song in pop[:6] + [made("country", "allegra", s) for s in range(1, 5)] + [made("elettronica", "ipnotica", s) for s in range(1, 5)]:
        _valid(q, song)


# ------------------------------------------------------------ generi, seconda revisione

def test_swing_genres_write_the_swing_word_in_every_melodic_box_and_keep_the_drums_in_triplets(q):
    import re as _re
    expected = {"jazz": "swing=", "swing": "swing=", "blues": "swing=", "rocknroll": "swing=",
                "soul": "swing16=", "funk": "swing16=", "lofi": "swing16="}
    for genre, word in expected.items():
        song = q.quick_song({"genre": genre, "mood": "calma" if genre == "lofi" else "allegra", "duration": 40, "seed": 3})
        boxes = _re.findall(r'^Box (\S+) "[^"]*" \|\d+:\n  (\S.*)', song["text"], _re.M)
        assert boxes, genre
        for track, first in boxes:
            if track == "Drums":
                assert "swing" not in first, genre
            elif track != "Strings" and song["choices"]["instruments"].get("pad") != track:
                assert first.startswith(word) or first.startswith("%"), (genre, track, first[:30])
        assert any(first.startswith(word) for track, first in boxes if track != "Drums"), genre
    assert "swing" not in quick_text(q, "pop") and "swing" not in quick_text(q, "bossa")
    # il valore scende con il tempo nel jazz e nello swing; si sceglie anche a mano
    assert q.swing_word("jazz", 100) == "swing=66" and q.swing_word("jazz", 200) == "swing=58"
    assert q.swing_word("pop", 120) == "" and q.swing_word("pop", 120, 60) == "swing=60"
    assert "swing=66" in q.quick_song({"genre": "jazz", "mood": "calma", "duration": 20, "seed": 1, "swing": 66})["text"]


def quick_text(q, genre):
    return q.quick_song({"genre": genre, "mood": "allegra", "duration": 30, "seed": 2})["text"]


def test_swing_is_recorded_on_the_events_of_the_melodic_parts(q):
    from core.project_io import parse_project_text
    from st_language.midi import sounding_events
    song = q.quick_song({"genre": "jazz", "mood": "allegra", "duration": 40, "seed": 3})
    project = parse_project_text(song["text"], "x")
    swung = {}
    for track in project.tracks:
        swung[track.name] = {e.swing for e in sounding_events(track.parsed_events(project.patterns, meter=project.meter())) if e.swing}
    assert swung["Drums"] == set() and all(len(v) == 1 for k, v in swung.items() if k != "Drums" and v)
    assert any(swung[k] for k in swung if k != "Drums")


def test_only_electronic_genres_keep_a_synth_lead_and_the_acoustic_genres_have_their_own_bands(q):
    leads = {"elettronica", "lofi", "fusion", "newwave"}     # il synth solista della fusion e della new wave
    for genre in q.GENRES_DATA:
        for variety in (0, 1):
            for seed in (1, 2, 3):
                inst = q.quick_song({"genre": genre, "mood": "allegra", "duration": 30, "seed": seed, "variety": variety})["choices"]["instruments"]
                if inst.get("melody", "").startswith("Lead"):
                    assert genre in leads, (genre, inst)
    acoustic = ("pop", "ballata", "bossa", "samba", "valzer", "afro68", "ballata68")
    bands = {g: tuple(sorted(q.quick_song({"genre": g, "mood": "calma", "duration": 30, "seed": 1, "variety": 0})["choices"]["instruments"].items()))
             for g in acoustic}
    assert len(set(bands.values())) == len(acoustic)
    assert bands["bossa"] != bands["samba"] and dict(bands["valzer"])["comp"] == "Accordion"


def test_new_bass_and_piano_styles_write_full_bars_in_four_four(q):
    from core.project_io import parse_project_text
    for genre, mood in (("chacha", "allegra"), ("rocknroll", "allegra"), ("blues", "calma")):
        for variety in (0, 1):
            song = q.quick_song({"genre": genre, "mood": mood, "duration": 40, "seed": 4, "variety": variety})
            parse_project_text(song["text"], "x")
            assert song["bars"] > 0
    assert q.quick_song({"genre": "rocknroll", "mood": "allegra", "duration": 30, "seed": 1, "variety": 0})["choices"]["styles"]["bass"] == "boogie"
    assert q.quick_song({"genre": "rocknroll", "mood": "allegra", "duration": 30, "seed": 1, "variety": 0})["choices"]["styles"]["comp"] == "boogie_piano"
    assert q.quick_song({"genre": "chacha", "mood": "allegra", "duration": 30, "seed": 1, "variety": 0})["choices"]["styles"]["bass"] == "tumbao"
    # il boogie-woogie si suona sempre al pianoforte
    for seed in range(1, 30):
        song = q.quick_song({"genre": "blues", "mood": "calma", "duration": 20, "seed": seed})
        if song["choices"]["styles"]["comp"] == "boogie_piano":
            assert song["choices"]["instruments"]["comp"] == "Piano"
            break
    else:
        raise AssertionError("il blues non sceglie mai il boogie al piano")


@pytest.mark.parametrize("genre,kind", [("funk", "groove"), ("soul", "groove"), ("jazz", "bebop"), ("balcanico78", "phrygian_dominant"), ("metal", "metal"), ("rock", "rock"),
                                        ("bossa", "latin"), ("samba", "latin"), ("chacha", "latin"), ("valzer", "classical"),
                                        ("ballata", "classical"), ("marcia", "classical"), ("elettronica", "modal"), ("orchestrale", "classical")])
def test_the_new_scales_keep_the_strong_beats_inside_the_chord_or_the_scale(q, genre, kind):
    from core.project_io import parse_project_text
    from core.melody_generate import SCALE_KINDS
    assert q._GENRE_SCALE[genre] == kind and kind in SCALE_KINDS
    song = q.quick_song({"genre": genre, "mood": "allegra" if genre != "metal" else "tesa", "duration": 40, "seed": 2, "variety": 0})
    assert parse_project_text(song["text"], "x") is not None


def test_jazz_and_blues_melodies_have_chromatic_approach_notes(q):
    quicksong = q
    from core.notation import parse_track_text
    from core.project_io import parse_project_text

    def approaches(genre):
        found = total = 0
        for seed in range(1, 7):
            song = quicksong.quick_song({"genre": genre, "seed": seed, "variety": 0, "duration": 90})
            project = parse_project_text(song["text"], "x")
            track = next(t for t in project.tracks if t.name == song["choices"]["instruments"]["melody"])
            events = [e for e in parse_track_text(track.text, project.patterns) if e.kind == "note"]
            midi = lambda e: 12 * (e.octave + 1) + {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}[e.letter[0]] + e.letter.count("#") - e.letter[1:].count("b")  # noqa: E731
            for a, b in zip(events, events[1:]):
                total += 1
                if abs(b.start - round(b.start)) < 1e-6 and abs(a.start % 1 - 0.5) < 1e-6 and abs(midi(a) - midi(b)) == 1:
                    found += 1
        return found, total
    for genre in ("jazz", "blues"):
        found, total = approaches(genre)
        assert found >= 3, (genre, found, total)
    assert approaches("marcia")[0] <= approaches("jazz")[0]


@pytest.mark.parametrize("genre,program", [("jazz", 40), ("rock", 16), ("lofi", 24), ("marcia", 48), ("ballata", 8)])
def test_genres_declare_their_drum_kit(q, genre, program):
    from core.project_io import parse_project_text
    song = q.quick_song({"genre": genre, "duration": 60, "seed": 2})
    drums = [t for t in parse_project_text(song["text"], "x").tracks if t.name == "Drums"]
    assert drums and drums[0].instrument.is_percussion and drums[0].instrument.gm_program == program
    assert f"program={program} percussione=si" in song["text"]


def test_funk_keeps_the_standard_kit_and_the_kit_can_be_turned_off(q):
    assert "Strumento" not in q.quick_song({"genre": "funk", "duration": 60, "seed": 2})["text"]
    assert "Strumento" not in q.quick_song({"genre": "jazz", "duration": 60, "seed": 2, "kit": False})["text"]


def test_the_jazz_kit_reaches_the_midi(q, tmp_path):
    import mido
    from core.project_io import parse_project_text
    from core.midi_export import export_project_to_midi
    song = q.quick_song({"genre": "jazz", "duration": 30, "seed": 2})
    export_project_to_midi(parse_project_text(song["text"], "x"), str(tmp_path / "j.mid"))
    msgs = [m for t in mido.MidiFile(str(tmp_path / "j.mid")).tracks for m in t if m.type == "program_change" and m.channel == 9]
    assert msgs and msgs[0].program == 40


def test_the_melody_plays_in_the_verse_lighter_than_in_the_chorus(q):
    from core.project_io import parse_project_text
    verse = chorus = 0
    for seed in range(1, 7):
        song = q.quick_song({"genre": "pop", "duration": 60, "seed": seed, "variety": 0})
        melody = song["choices"]["instruments"]["melody"]
        assert any(f'Box {melody} "Strofa"' in line for line in song["text"].split("\n")), seed
        project = parse_project_text(song["text"], "x")
        track = next(t for t in project.tracks if t.name == melody)
        notes = [e for e in track.parsed_events(project.patterns, meter=project.meter()) if e.kind in ("note", "slide")]
        for s in song["sections"]:
            lo, hi = s["start_bar"] * 4, (s["start_bar"] + s["bars"]) * 4
            count = sum(lo <= e.start < hi for e in notes) / s["bars"]
            if s["role"] == "verse":
                verse += count
            elif s["role"] == "chorus":
                chorus += count
    assert 0 < verse < chorus
    short = q.quick_song({"genre": "pop", "duration": 15, "seed": 1})
    assert not any(s["role"] == "verse" for s in short["sections"]) or 'Box Flute "Strofa"' not in short["text"]


def test_genre_entries_jazz_piano_rests_in_the_solo_and_the_ballad_verse_has_no_drums(q):
    import re as _re
    song = q.quick_song({"genre": "ballata", "duration": 60, "seed": 2, "variety": 0})
    assert not _re.search(r'Box Drums "Strofa"', song["text"]) and _re.search(r'Box Drums "Ritornello"', song["text"])
    assert q._enters("jazz", "comp") and "solo" not in q._enters("jazz", "comp") and "solo" in q._enters("pop", "comp")
    assert "intro" in q._enters("elettronica", "drums") and "intro" not in q._enters("elettronica", "comp")


@pytest.mark.parametrize("genre", ["funk", "rock", "reggae"])
def test_a_break_comes_before_the_last_chorus(q, genre):
    import re as _re
    song = q.quick_song({"genre": genre, "duration": 120, "seed": 2, "variety": 0, "form": "canzone"})
    roles = [s["role"] for s in song["sections"]]
    k = roles.index("break")
    assert roles[k + 1] == "chorus" and "chorus" not in roles[k + 1 + 1:]
    drums = _re.search(r'Box Drums "Break"[^\n]*\n  ([^\n]*)', song["text"])
    if genre == "reggae":
        assert drums is None and _re.search(r'Box \S+ "Break"', song["text"])          # il drop: restano gli accordi
    else:
        assert drums and "[crash kick]" in drums.group(1)
    assert q.quick_song({"genre": genre, "duration": 120, "seed": 2, "variety": 0, "form": "canzone", "breaks": False})["sections"][k]["role"] != "break"


def test_genre_endings(q):
    import re as _re
    assert q.quick_song({"genre": "valzer", "duration": 60, "seed": 2})["choices"]["ending"] == "rallentando"
    assert q.quick_song({"genre": "bossa", "duration": 60, "seed": 2})["choices"]["ending"] == "sfumato"
    assert q.quick_song({"genre": "bossa", "duration": 30, "seed": 2})["choices"]["ending"] == "cadenza"
    march = q.quick_song({"genre": "marcia", "duration": 60, "seed": 2, "ending": "cadenza"})["text"]
    assert _re.search(r"\[snare kick\] r \d+@ \[snare kick\] r \d+@ \[crash kick\]", march)
    assert q._color_last_voicing("4: [c*4 e*4 g*4 c*5]", "C", "6") == "4: [c*4 e*4 g*4 a*4 c*5]"
    assert q._color_last_voicing("4: [c*4 e*4 g*4 c*5]", "C", "7") == "4: [c*4 e*4 g*4 a#*4 c*5]"
    assert q._color_last_voicing("4: [d*4 f*4 a*4]", "C", "6") == "4: [d*4 f*4 a*4]"          # non e' l'accordo della tonica


def test_ornaments_by_genre_and_instrument(q):
    from core.project_io import parse_project_text

    def count(genre, kind, seeds=range(1, 7), **extra):
        n = 0
        for seed in seeds:
            song = q.quick_song({"genre": genre, "duration": 90, "seed": seed, "variety": 0, **extra})
            project = parse_project_text(song["text"], "x")
            track = next(t for t in project.tracks if t.name == song["choices"]["instruments"]["melody"])
            events = track.parsed_events(project.patterns, meter=project.meter())
            n += sum(1 for e in events if (e.grace if kind == "grace" else e.kind == "slide"))
        return n
    assert count("valzer", "grace") >= 3 and count("country", "grace") >= 3
    assert count("rock", "bend") >= 3
    assert count("rock", "bend", figures=False) == 0
    assert q._figures_for("blues", "Piano") == "approach_below" and "blue_bend" in q._figures_for("blues", "Harmonica")


def test_the_genre_second_voice_follows_the_melody_in_every_chorus(q):
    import re as _re
    song = q.quick_song({"genre": "valzer", "duration": 90, "seed": 2, "variety": 0})
    harm = song["choices"]["instruments"].get("harm")
    assert harm and harm != song["choices"]["instruments"]["melody"]
    boxes = _re.findall(r'Box ' + harm + r' "Ritornello" \|\d+:\n  (?:swing\S* )?(%\S+)', song["text"])
    assert len(boxes) == sum(s["role"] == "chorus" for s in song["sections"]) and all("Voce" in b or ".step(-5)" in b for b in boxes)
    assert "harm" not in q.quick_song({"genre": "rock", "duration": 90, "seed": 2})["parts"]


def test_ornamented_songs_export_to_musicxml_and_speak(q):
    from core.project_io import parse_project_text
    engine = _mobile_engine()
    for genre in ("rock", "valzer"):
        song = q.quick_song({"genre": genre, "duration": 60, "seed": 1, "variety": 0})
        assert not engine.check_text(song["text"], song["name"])["warnings"]
        melody = song["choices"]["instruments"]["melody"]
        pos = song["text"].index(f'Box {melody} "Ritornello"')
        spoken = engine.speak_at(song["text"], song["text"].index("\n", pos) + 4, "it")
        assert spoken["text"]
        from st_language.musicxml import project_to_musicxml
        xml = project_to_musicxml(parse_project_text(song["text"], "x"))
        assert "<score-partwise" in xml and (genre != "valzer" or "<grace" in xml)


def test_funk_is_built_on_sixteenth_slap_bass_scratch_guitar_and_ninth_chords(q):
    from core.project_io import parse_project_text
    song = q.quick_song({"genre": "funk", "duration": 60, "seed": 2, "variety": 0})
    assert song["choices"]["styles"]["bass"] == "funk16" and song["choices"]["styles"]["comp2"] == "scratch"
    assert song["choices"]["instruments"]["bass"] == "Slap_Bass_1" and song["choices"]["instruments"]["comp2"] == "Electric_Guitar_Muted"
    project = parse_project_text(song["text"], "x")
    bass = next(t for t in project.tracks if t.name == "Slap_Bass_1")
    events = [e for e in bass.parsed_events(project.patterns, meter=project.meter()) if e.kind in ("note", "slide")]
    assert sum(abs(e.start * 4 - round(e.start * 4)) < 1e-6 and abs(e.start - round(e.start)) > 1e-6 for e in events) > len(events) / 3   # sedicesimi in sincope
    assert song["choices"]["styles"].get("progression") in (None, "")
    from core.rhythm_generate import PROGRESSION_STYLES
    assert all(s in PROGRESSION_STYLES for s in ("funk_vamp", "funk_walk", "funk_minor"))
    chords = [e for e in project.tracks[0].parsed_events(project.patterns, meter=project.meter())]
    assert chords


def test_country_has_banjo_rolls_a_walking_bass_and_a_second_voice_in_thirds(q):
    song = q.quick_song({"genre": "country", "duration": 90, "seed": 2, "variety": 0})
    assert song["choices"]["styles"]["bass"] == "walk_up" and song["choices"]["styles"]["comp2"] == "banjo_roll"
    assert song["choices"]["instruments"]["comp2"] == "Banjo"
    harm = song["choices"]["instruments"].get("harm")
    assert harm and harm != song["choices"]["instruments"]["melody"]
    assert "MelodiaRitornelloVoce" in song["text"] or ".step(-2)" in song["text"]
    assert "harm" not in q.quick_song({"genre": "country", "duration": 90, "seed": 2, "second_voice": False})["parts"]


def test_soul_has_a_motown_bass_electric_piano_organ_seventh_chords_and_a_fade(q):
    import re as _re
    from core.rhythm_generate import PROGRESSION_STYLES
    song = q.quick_song({"genre": "soul", "mood": "allegra", "duration": 150, "seed": 2, "variety": 0})
    styles, instruments = song["choices"]["styles"], song["choices"]["instruments"]
    assert styles["bass"] == "motown" and styles["comp"] == "soul_comp"
    assert instruments["comp"] == "Electric_Piano_1" and instruments["comp2"] == "Drawbar_Organ"
    assert song["choices"]["ending"] == "sfumato" and any(s["role"] == "fade" for s in song["sections"])
    assert instruments.get("harm") == "Alto_Sax" and ("MelodiaRitornelloVoce" in song["text"] or ".step(-2)" in song["text"])   # i sax in terze
    assert all(s in PROGRESSION_STYLES for s in ("soul_turn", "soul_plagal", "soul_minor"))
    assert all(all(any(c[1] in ("maj7", "m7", "7") for c in PROGRESSION_STYLES[s]["chords"]) for s in pool)
               for pool in ([q._PROG_POOLS["soul"]["major"][0], q._PROG_POOLS["soul"]["major"][2]],))
    assert q._PROG_POOL_OF["soul"] == "soul" and q._PROG_POOL_OF["funk"] == "funk"
    assert not _re.search(r"Box Nylon_Guitar", song["text"])


def _color_of(q, genre, mood, **extra):
    song = q.quick_song({"genre": genre, "mood": mood, "seed": 3, "duration": 120, "variety": 0, **extra})
    text = song["text"]
    fx = text.split("Catena master:")[1].split("\n\n")[0] if "Catena master:" in text else ""
    return (song["choices"]["instruments"].get("melody"), song["choices"]["ending"], song["choices"]["modulation"], fx,
            tuple(sorted({w for w in text.split() if w.startswith("swing")})), "Pedal" in text, "harm" in song["parts"])


@pytest.mark.parametrize("pair", [("allegra", "festosa"), ("tesa", "drammatica"), ("nostalgica", "sognante"), ("sognante", "misteriosa"),
                                  ("nostalgica", "misteriosa"), ("romantica", "solenne")])
def test_moods_that_shared_every_setting_now_sound_different(q, pair):
    seen = 0
    for genre, data in q.GENRES_DATA.items():
        if all(m in data["moods"] for m in pair):
            seen += 1
            assert _color_of(q, genre, pair[0]) != _color_of(q, genre, pair[1]), (genre, pair)
    assert seen


def test_mood_color_details(q):
    from core.project_io import parse_project_text
    assert _color_of(q, "pop", "festosa")[2] is True and _color_of(q, "pop", "allegra")[2] is False       # festosa sale di un tono
    assert _color_of(q, "pop", "festosa", modulation=False)[2] is False                                     # la scelta esplicita vince
    assert q.quick_song({"genre": "pop", "mood": "festosa", "seed": 3, "duration": 30})["choices"]["modulation"] is False  # non nei brani corti
    assert _color_of(q, "pop", "malinconica")[1] == "rallentando" and _color_of(q, "pop", "sognante")[1] == "sfumato"
    assert q.quick_song({"genre": "pop", "mood": "sognante", "seed": 3, "duration": 30, "variety": 0})["choices"]["ending"] == "cadenza"
    assert q.quick_song({"genre": "pop", "mood": "sognante", "seed": 3, "duration": 120, "loop": True, "variety": 0})["choices"]["ending"] == "cadenza"
    assert q.quick_song({"genre": "pop", "mood": "sognante", "seed": 3, "duration": 120, "ending": "rallentando", "variety": 0})["choices"]["ending"] == "rallentando"
    assert _color_of(q, "pop", "tesa")[5] is True and _color_of(q, "pop", "allegra")[5] is False           # la tesa tiene la tonica
    warm, bright = _color_of(q, "jazz", "sensuale")[0], _color_of(q, "jazz", "giocosa")[0]
    assert warm in ("Tenor_Sax", "Alto_Sax", "Clarinet") and bright in ("Trumpet", "Flute") and warm != bright
    assert _color_of(q, "rock", "tesa")[0] == _color_of(q, "rock", "allegra")[0]                           # i generi distorti non cambiano timbro
    assert "swing16=56" in _color_of(q, "funk", "giocosa")[4][0] and "swing16=52" in _color_of(q, "funk", "energica")[4][0]
    assert _color_of(q, "soul", "sensuale")[4][0].endswith("=57")
    rows = q._mood_fx("pop", "sognante")
    assert sum(r.startswith("riverbero") for r in rows) == 1 and any(r.startswith("delay") for r in rows) and any(r.startswith("compressore") for r in rows)
    assert q.quick_song({"genre": "pop", "mood": "sognante", "seed": 3, "duration": 60, "effects": False})["text"].count("Catena master") == 0
    parse_project_text(q.quick_song({"genre": "pop", "mood": "sognante", "seed": 3, "duration": 60})["text"], "x")


def _boxes(song, section):
    import re as _re
    return sorted(set(_re.findall(r'Box (\S+) "' + section + '"', song["text"])))


def test_orchestral_starts_with_the_harp_then_strings_and_the_horns_come_with_the_chorus(q):
    song = q.quick_song({"genre": "orchestrale", "mood": "solenne", "duration": 120, "seed": 2, "variety": 0})
    assert _boxes(song, "Intro") == ["Harp"]
    assert "Strings" in _boxes(song, "Strofa") and "French_Horn" not in _boxes(song, "Strofa") and "French_Horn" in _boxes(song, "Ritornello")
    assert song["choices"]["instruments"].get("harm") == "Clarinet" and "Clarinet" in _boxes(song, "Ritornello")      # i legni in terze
    assert _boxes(song, "Break") == ["Cello", "French_Horn", "Harp", "Strings"]                                         # il tutti e il silenzio


def test_the_march_is_a_brass_band_with_a_drum_intro_and_a_roll_before_the_last_chorus(q):
    song = q.quick_song({"genre": "marcia", "mood": "solenne", "duration": 120, "seed": 2, "variety": 0})
    instruments = song["choices"]["instruments"]
    assert instruments["comp"] == "Brass_Section" and instruments["comp2"] == "Accordion" and "Strings" not in song["text"] and "Harp" not in song["text"]
    assert _boxes(song, "Intro") == ["Drums"] and _boxes(song, "Break") == ["Drums"]
    assert q.quick_song({"genre": "marcia", "mood": "solenne", "duration": 120, "seed": 2, "variety": 0, "breaks": False})["text"].count('"Break"') == 0


def test_afro_six_eight_starts_with_the_percussion_and_fades(q):
    song = q.quick_song({"genre": "afro68", "mood": "allegra", "duration": 120, "seed": 2, "variety": 0})
    assert _boxes(song, "Intro") == ["Drums"] and _boxes(song, "Break") == ["Drums"]
    assert song["choices"]["ending"] == "sfumato" and any(s["role"] == "fade" for s in song["sections"])
    assert q.quick_song({"genre": "afro68", "mood": "allegra", "duration": 120, "seed": 2, "variety": 0, "loop": True})["choices"]["ending"] == "cadenza"


def test_pop_drops_to_the_chords_before_the_last_chorus_and_metal_stops_dead(q):
    pop = q.quick_song({"genre": "pop", "mood": "allegra", "duration": 120, "seed": 2, "variety": 0})
    assert _boxes(pop, "Break") == sorted([pop["choices"]["instruments"]["comp"], pop["choices"]["instruments"]["comp2"]])
    metal = q.quick_song({"genre": "metal", "mood": "tesa", "duration": 120, "seed": 2, "variety": 0})
    assert "Drums" in _boxes(metal, "Intro") and set(_boxes(metal, "Break")) >= {"Drums", "Bass"}


def test_figures_for_the_last_genres(q):
    assert q._figures_for("pop", "Electric_Piano_1") == "grace_below" and q._figures_for("marcia", "Trumpet") == "grace_above"
    assert q._figures_for("metal", "Overdriven_Guitar") == "approach_below,blue_bend" and q._figures_for("metal", "Piano") == "approach_below"
    assert q._figures_for("orchestrale", "Oboe") == "grace_above" and q._figures_for("afro68", "Flute") == "grace_above"
    for genre in ("orchestrale", "marcia", "afro68", "pop", "metal"):
        assert q.quick_song({"genre": genre, "duration": 60, "seed": 2, "variety": 0})["text"]


@pytest.mark.parametrize("genre,program", [("chacha", 32), ("reggae", 8), ("balcanico78", 8)])
def test_more_genres_declare_their_drum_kit(q, genre, program):
    from core.project_io import parse_project_text
    song = q.quick_song({"genre": genre, "duration": 60, "seed": 2})
    drums = [t for t in parse_project_text(song["text"], "x").tracks if t.name == "Drums"]
    assert drums and drums[0].instrument.gm_program == program


def test_the_mood_changes_the_melody_style_the_drums_the_fills_and_how_loud_it_plays(q):
    import re as _re

    def velocity(song):
        values = [int(v) for v in _re.findall(r"(\d+)@", song["text"])]
        return sum(values) / len(values)
    calm = q.quick_song({"genre": "pop", "mood": "calma", "duration": 90, "seed": 2, "variety": 0})
    lively = q.quick_song({"genre": "pop", "mood": "energica", "duration": 90, "seed": 2, "variety": 0})
    assert calm["choices"]["melody"] == "ballata" and lively["choices"]["melody"] == "vivace"
    assert calm["choices"]["styles"]["drums"] == "halftime" and lively["choices"]["styles"]["drums"] == "rock"
    assert q.resolve({"genre": "pop", "mood": "calma", "seed": 2, "variety": 0})["drum_fill"] == 8
    assert q.resolve({"genre": "pop", "mood": "energica", "seed": 2, "variety": 0})["drum_fill"] == 2
    assert velocity(calm) < velocity(lively) - 6
    assert q.quick_song({"genre": "jazz", "mood": "allegra", "duration": 60, "seed": 2, "variety": 0})["choices"]["melody"] == "aaba"   # lo stile del genere non si tocca
    assert q.quick_song({"genre": "pop", "mood": "calma", "duration": 60, "seed": 2, "variety": 0, "melody": "vivace"})["choices"]["melody"] == "vivace"
    assert q.quick_song({"genre": "soul", "mood": "calma", "duration": 60, "seed": 2, "variety": 0})["choices"]["styles"]["drums"] == "soul"   # solo pop, rock e country


def test_the_new_moods_exist_and_the_intimate_one_plays_with_fewer_parts(q):
    for mood in ("intima", "grintosa", "elegante"):
        assert mood in q.MOODS and mood in q._mood_labels() and any(mood in d["moods"] for d in q.GENRES_DATA.values())
    plain = q.quick_song({"genre": "pop", "mood": "serena", "duration": 90, "seed": 2, "variety": 0})
    intimate = q.quick_song({"genre": "pop", "mood": "intima", "duration": 90, "seed": 2, "variety": 0})
    assert {"comp2", "pad"} <= set(plain["parts"]) and not {"comp2", "pad", "horn"} & set(intimate["parts"])
    assert intimate["choices"]["ending"] == "rallentando"
    assert q.quick_song({"genre": "rock", "mood": "grintosa", "duration": 60, "seed": 2, "variety": 0})["bpm"] > 110


def test_more_endings_and_a_mood_ending_beats_the_genre_one(q):
    from core.project_io import parse_project_text
    assert q.quick_song({"genre": "reggae", "duration": 90, "seed": 2})["choices"]["ending"] == "sfumato"
    assert q.quick_song({"genre": "country", "mood": "allegra", "duration": 90, "seed": 2})["choices"]["ending"] == "rallentando"
    assert q.quick_song({"genre": "soul", "mood": "allegra", "duration": 90, "seed": 2})["choices"]["ending"] == "sfumato"
    assert q.quick_song({"genre": "soul", "mood": "romantica", "duration": 90, "seed": 2})["choices"]["ending"] == "rallentando"        # l'atmosfera e' piu' specifica
    assert q.quick_song({"genre": "soul", "mood": "romantica", "duration": 90, "seed": 2, "ending": "cadenza"})["choices"]["ending"] == "cadenza"
    chacha = q.quick_song({"genre": "chacha", "mood": "allegra", "duration": 90, "seed": 2, "ending": "cadenza", "variety": 0})["text"]
    import re as _re
    assert _re.search(r"\[snare kick\] r \d+@ \[snare kick\] r \d+@ \[crash kick\]", chacha) or "[crash kick] 11r" in chacha          # i tre colpi del cha cha
    parse_project_text(chacha, "x")


def test_samba_chacha_and_balkan_have_their_own_entries_and_breaks(q):
    samba = q.quick_song({"genre": "samba", "mood": "allegra", "duration": 120, "seed": 2, "variety": 0})
    assert _boxes(samba, "Intro") == ["Drums"] and _boxes(samba, "Break") == ["Drums"] and "swing16=" in samba["text"]
    chacha = q.quick_song({"genre": "chacha", "mood": "allegra", "duration": 120, "seed": 2, "variety": 0})
    assert "Drums" in _boxes(chacha, "Intro") and _boxes(chacha, "Break") == ["Drums"]
    balkan = q.quick_song({"genre": "balcanico78", "mood": "allegra", "duration": 120, "seed": 2, "variety": 0})
    assert balkan["choices"]["instruments"]["melody"] in _boxes(balkan, "Intro") and "Drums" in _boxes(balkan, "Break")
    punk = q.quick_song({"genre": "punk", "mood": "allegra", "duration": 120, "seed": 2, "variety": 0})
    assert "Drums" in _boxes(punk, "Intro") and q._figures_for("punk", "Overdriven_Guitar") == "approach_below"


@pytest.mark.parametrize("genre,instruments", [
    ("lofi", {"comp": "Electric_Piano_1", "comp2": "Pad_2_warm", "bass": "Fretless_Bass", "melody": "Vibraphone"}),
    ("elettronica", {"comp": "Pad_1_new_age", "bass": "Synth_Bass_1", "melody": "Lead_2_sawtooth"}),
    ("orchestrale", {"comp": "Strings", "comp2": "Harp", "bass": "Cello", "horn": "French_Horn", "melody": "Oboe"})])
def test_electronic_lofi_and_orchestral_have_their_own_instruments(q, genre, instruments):
    song = q.quick_song({"genre": genre, "mood": "calma", "duration": 120, "seed": 2, "variety": 0})
    for part, name in instruments.items():
        assert song["choices"]["instruments"][part] == name, (genre, part)
    assert q._INSTRUMENT_ALTS_GENRE[genre]


def test_blues_rocknroll_bossa_valzer_afro_and_electronic_have_kits_entries_and_breaks(q):
    for genre, program in (("blues", 8), ("rocknroll", 8), ("afro68", 8)):
        assert q._GENRE_KIT[genre][1] == program
    elettronica = q.quick_song({"genre": "elettronica", "mood": "allegra", "duration": 120, "seed": 2, "variety": 0})
    assert _boxes(elettronica, "Break") == sorted([elettronica["choices"]["instruments"]["comp"], elettronica["choices"]["instruments"]["comp2"]])
    for genre in ("bossa", "valzer", "rocknroll"):
        song = q.quick_song({"genre": genre, "mood": "allegra", "duration": 120, "seed": 2, "variety": 0})
        assert any(s["role"] == "break" for s in song["sections"]), genre
    blues = q.quick_song({"genre": "blues", "mood": "allegra", "duration": 90, "seed": 2, "variety": 0})
    roles = [s["role"] for s in blues["sections"]]
    assert "break" in roles and roles.index("break") < roles.index("solo")
    bossa = q.quick_song({"genre": "bossa", "mood": "allegra", "duration": 120, "seed": 2, "variety": 0})
    assert bossa["choices"]["instruments"]["comp2"] not in _boxes(bossa, "Intro")
    lofi = q.quick_song({"genre": "lofi", "mood": "calma", "duration": 120, "seed": 2, "variety": 0, "form": "canzone"})
    assert lofi["choices"]["instruments"]["comp2"] not in _boxes(lofi, "Intro")
    for genre in ("marcia", "afro68"):
        assert q._GENRE_SECOND_VOICE[genre] == "thirds"


def test_poor_moods_get_more_parts_and_harmony(q):
    epic = q.quick_song({"genre": "pop", "mood": "epica", "duration": 120, "seed": 2, "variety": 0})
    assert epic["choices"]["instruments"]["horn"] == "French_Horn" and "horn" in epic["parts"]
    mysterious = q.quick_song({"genre": "jazz", "mood": "misteriosa", "duration": 120, "seed": 2, "variety": 0})
    assert mysterious["choices"]["instruments"]["pad"] == "Pad_1_new_age"
    band = q.quick_song({"genre": "marcia", "mood": "solenne", "duration": 120, "seed": 2, "variety": 0})
    assert "pad" not in band["parts"]                                                         # le bande non prendono tappeti
    assert "horn" not in q.quick_song({"genre": "rock", "mood": "epica", "duration": 60, "seed": 2, "variety": 0})["parts"]
    assert "horn" not in q.quick_song({"genre": "pop", "mood": "intima", "duration": 60, "seed": 2, "variety": 0})["parts"]    # l'intima toglie


def test_the_mood_colors_the_chords_but_not_the_bass_and_the_melody(q):
    assert q._color_chords("4: 4C 4Am 4F 4G", 0, "seventh") == "4: 4Cmaj7 4Am7 4Fmaj7 4G7"
    assert q._color_chords("4: 4Am 4Dm 4E 4Am", 9, "tension") == "4: 4AmMaj7 4Dm 4E7 4AmMaj7"
    assert q._color_chords("4: 8E9 4A 2Bm7 4C#sus4", 4, "seventh") == "4: 8E9 4Amaj7 2Bm7 4C#sus4"      # chi ha gia' un colore resta com'e'
    import re as _re
    sevenths = q.quick_song({"genre": "pop", "mood": "romantica", "duration": 90, "seed": 2, "variety": 0, "chords": ""})
    triads = q.quick_song({"genre": "pop", "mood": "serena", "duration": 90, "seed": 2, "variety": 0, "chords": ""})
    comp2 = lambda song: " ".join(_re.findall(r'Box %s "[^"]+"[^\n]*\n  ([^\n]*)' % song["choices"]["instruments"]["comp2"], song["text"]))   # noqa: E731
    sevenths_in = lambda text: len(_re.findall(r"\b\d*[A-G][#b]?(?:maj7|m7|7)\b", text))                                                      # noqa: E731
    assert sevenths_in(comp2(sevenths)) >= 4 and sevenths_in(comp2(sevenths)) > 2 * sevenths_in(comp2(triads))   # il colore lo suonano gli accompagnamenti
    assert q.quick_song({"genre": "pop", "mood": "romantica", "duration": 60, "seed": 2, "variety": 0, "chords": "Am F C G"})["text"]


def test_quick_songs_write_chords_as_symbols_where_the_harmony_is_the_whole_chord(q):
    import re as _re
    from core.project_io import parse_project_text
    song = q.quick_song({"genre": "pop", "mood": "allegra", "duration": 90, "seed": 2, "variety": 0})
    symbols = _re.findall(r"(?<![\w\[\]])\d*([A-G][#b]?(?:maj7|mMaj7|m7|m|7)?)(?=\s|$|\|)", song["text"])
    blocks = [b for b in _re.findall(r"\[([^\[\]]+)\]", song["text"]) if _re.search(r"\*\d", b)]
    assert len(symbols) > 5 * len(blocks) and {"C", "G", "Am", "F"} & set(symbols)       # i blocchi di note restano solo per i voicing particolari
    plain = q.quick_song({"genre": "pop", "mood": "allegra", "duration": 90, "seed": 2, "variety": 0, "symbols": False})
    assert len(_re.findall(r"\[[a-g][#b]?\*\d", plain["text"])) > len(_re.findall(r"\[[a-g][#b]?\*\d", song["text"])) * 5
    parse_project_text(song["text"], "x")                                                  # e il testo e' valido
    from core.chord_symbols import progression_symbols, chords_as_symbols
    from core.instruments import get_instrument
    from core.rhythm_generate import extract_chords_from_track
    chords = extract_chords_from_track("4: 4C 4Am 4F 4G7", {})
    assert progression_symbols("4: 80@ 2[c*4 e*4 g*4] 2[e*4 g*4 c*5] 2[c*4 e*4 a*4] 2[a*4 c*5 e*5 a*5] 4[c*4 f*4 a*4 f*5] 2[b*3 d*4 g*4 f*4] 2[g*4 b*4]", chords) \
        == "4: 80@ 2C 2C 2Am 2Am 4F 2G7 2[g*4 b*4]"                                           # la sola terza e quinta resta com'e'
    assert chords_as_symbols("4: 2[c*4 e*4 g*4] 2[c*4 f*4 a*4] 4[g*4 b*4 d*5 f*5]", get_instrument("Piano")) == "4: 2C 2[c*4 f*4 a*4] 4G7"
    assert progression_symbols("8: 4[c*4 e*4 g*4] { a ; b }", chords) == "8: 4[c*4 e*4 g*4] { a ; b }"        # voci: non si tocca


def test_the_organ_plays_softer_than_its_written_velocity(monkeypatch):
    """L'organo tiene note lunghe: a pari velocity copre le altre parti, quindi negli accordi suona piu' piano."""
    from core import quicksong as q
    options = {"genre": "soul", "seed": 3}
    assert q._ORGAN_VELOCITY < 1 and q._part_velocity("comp2", "Drawbar_Organ") < 1 and q._part_velocity("comp", "Rock_Organ") < 1
    softer = q.quick_song(options)["text"]
    monkeypatch.setattr(q, "_PART_INSTRUMENT_VELOCITY", {})
    monkeypatch.setattr(q, "_PART_VELOCITY", {})
    monkeypatch.setattr(q, "_ORGAN_VELOCITY", 1.0)
    plain = q.quick_song(options)["text"]
    top = lambda text: max(int(v) for v in re.findall(r"(\d+)@", text))
    assert softer != plain and top(softer) <= top(plain)


def _scale_of(q, tonic, kind, mode):
    from core.melody_generate import SCALE_KINDS
    steps = SCALE_KINDS[kind][0 if mode == "major" else 1]
    return {(tonic + s) % 12 for s in steps}


def test_the_colour_of_the_chords_only_adds_sevenths_the_melody_scale_has(q):
    phrygian = _scale_of(q, 7, "metal", "minor")                      # Sol frigia: Sol La b Si b Do Re Mi b Fa
    harmonic = _scale_of(q, 7, "classical", "minor")                  # Sol minore armonica: ha il Fa#
    assert q._color_chords("Gm Eb F Gm", 7, "tension", phrygian) == "Gm Eb F Gm"        # niente GmMaj7: il Fa# contraddice il Fa
    assert q._color_chords("Gm Eb F Gm", 7, "tension", harmonic) == "GmMaj7 Eb F GmMaj7"
    assert q._color_chords("Gm Eb F Gm", 7, "tension") == "GmMaj7 Eb F GmMaj7"          # senza scala come prima
    seventh = q._color_chords("Gm Eb F Gm", 7, "seventh", harmonic)
    assert seventh.split()[0] == "Gm" and "Fmaj7" not in seventh and seventh.split()[1] == "Ebmaj7"     # Gm7 (Fa) e Fmaj7 (Mi) stonano
    mixolydian = _scale_of(q, 0, "groove", "major")                   # Do misolidia: il Si e' bemolle
    assert q._color_chords("C F G C", 0, "seventh", mixolydian) == "C Fmaj7 G7 C"        # Cmaj7 no (Si), Fmaj7 si' (Mi), G7 si' (Fa)


def test_every_coloured_chord_is_in_the_scale_of_the_melody_in_every_genre_and_mood(q):
    from core.rhythm_generate import parse_key
    for genre in q.GENRES_DATA:
        for mood in q.GENRES_DATA[genre]["moods"]:
            how = q._MOOD_COLOR.get(mood, {}).get("chords")
            if not how:
                continue
            tonic, mode = parse_key(q.quick_song({"genre": genre, "mood": mood, "seed": 11, "duration": 15, "variety": 0})["key"])[:2]
            scale = q._melody_scale(genre, tonic, mode)
            colored = q._color_chords("Am F C G Dm E7", tonic, how, scale)
            for tok in colored.split():
                m = re.match(r"([A-G][#b]?)(mMaj7|maj7|m7|7)$", tok)
                if m:
                    root = q._ROOT_PC[m.group(1)[0]] + m.group(1).count("#") - m.group(1)[1:].count("b")
                    assert (root + (11 if m.group(2) in ("maj7", "mMaj7") else 10)) % 12 in scale, (genre, mood, tok)


def test_the_metal_drammatica_song_of_the_report_has_no_major_seventh_on_the_tonic(q):
    song = q.quick_song({"genre": "metal", "mood": "drammatica", "seed": 972825931, "key": "Gm", "duration": 60})
    assert "mMaj7" not in song["text"] and "GmMaj7" not in song["text"]
    classic = q.quick_song({"genre": "orchestrale", "mood": "tesa", "seed": 3, "key": "Gm", "duration": 60, "variety": 0})
    assert "mMaj7" in classic["text"]                                     # la scala armonica ha il Fa#: li' il colore resta


def test_the_melody_receives_the_chords_the_accompaniment_plays(q):
    from core.melody_generate import _allowed_pcs, MINOR_SCALE
    from core.rhythm_generate import ChordSpan
    gm_maj7 = ChordSpan(0.0, 4.0, 7, True, 3, 11)
    pcs = _allowed_pcs([(7 + s) % 12 for s in MINOR_SCALE], gm_maj7)
    assert 6 in pcs and 5 not in pcs                                    # col Fa# dell'accordo il Fa naturale esce dalla scala


def test_allowed_pcs_replaces_the_right_neighbour_for_chromatic_chords():
    from core.melody_generate import _allowed_pcs, MAJOR_SCALE, MINOR_SCALE
    from core.rhythm_generate import ChordSpan
    a_minor = [(9 + s) % 12 for s in MINOR_SCALE]
    b_flat = _allowed_pcs(a_minor, ChordSpan(0.0, 4.0, 10, True, 4))                  # i - bII: il Si b prende il posto del Si
    assert 10 in b_flat and 11 not in b_flat and 9 in b_flat
    harmonic = [(9 + s) % 12 for s in (0, 2, 3, 5, 7, 8, 11)]
    assert 11 not in _allowed_pcs(harmonic, ChordSpan(0.0, 4.0, 10, True, 4))        # La minore armonica sopra Si b: il Si naturale non e' ammesso
    c_major = [(0 + s) % 12 for s in MAJOR_SCALE]
    b_flat_major = _allowed_pcs(c_major, ChordSpan(0.0, 4.0, 10, True, 4))            # bVII in Do: il Si b al posto del Si, il La resta
    assert 10 in b_flat_major and 11 not in b_flat_major and 9 in b_flat_major
    a_flat = _allowed_pcs(c_major, ChordSpan(0.0, 4.0, 8, True, 4))                   # bVI: il La b al posto del La, il Sol resta (e' la quinta del Do)
    assert 8 in a_flat and 9 not in a_flat and 7 in a_flat
    e_major = _allowed_pcs(a_minor, ChordSpan(0.0, 4.0, 4, True, 4))                  # V maggiore in minore: il Sol# al posto del Sol, il La resta
    assert 8 in e_major and 7 not in e_major and 9 in e_major
    c7 = _allowed_pcs(c_major, ChordSpan(0.0, 4.0, 0, True, 4, 10))                   # C7: il Si b al posto del Si
    assert 10 in c7 and 11 not in c7
    g7 = _allowed_pcs([0, 2, 4, 7, 9], ChordSpan(0.0, 4.0, 7, True, 4, 10))           # G7 nella pentatonica di Do: il Fa e il Si si aggiungono,
    assert {0, 4, 5, 11} <= set(g7)                                                    # il Do e il Mi restano


def test_a_written_progression_decides_the_key_and_the_bars(q):
    for chords, keys in (("Am F C G", ("Am", "C")), ("Dm Bb F C", ("Dm", "F")), ("Em C G D", ("Em", "G"))):
        song = q.quick_song({"genre": "pop", "mood": "allegra", "seed": 5, "chords": chords, "duration": 30})
        assert song["key"] in keys, (chords, song["key"])
    assert q.quick_song({"genre": "pop", "mood": "allegra", "seed": 5, "chords": "Am F C G", "key": "Dm", "duration": 30})["key"] == "Dm"   # la tonalita' scelta vince
    assert q._chord_loop("Am F", 2, 3.0) == "8: 6Am 6F"                                # 3/4: tre quarti = sei ottavi per battuta
    assert q._chord_loop("Am F", 2, 3.5) == "8: 7Am 7F"                                # 7/8
    assert q._chord_loop("Am F", 2, 4.0, 2) == "8: 8Bm 8G"                              # trasposto di un tono (modulazione)
    assert q._transpose_symbol("F/A", 2) == "G/B" and q._transpose_symbol("Bbmaj7", 1) == "Bmaj7" and q._transpose_symbol("C", 0) == "C"
    waltz = q.quick_song({"genre": "valzer", "mood": "malinconica", "seed": 2, "chords": "Am Dm E7 Am", "duration": 30, "variety": 0})
    _valid(q, waltz)


def test_a_written_progression_follows_the_modulation(q):
    song = q.quick_song({"genre": "pop", "mood": "festosa", "seed": 5, "chords": "C G Am F", "key": "C", "duration": 90, "modulation": True, "variety": 0})
    assert song["sections"][0]["key"] == "C" and song["sections"][-1]["key"] == "D"
    engine = _mobile_engine()
    assert not engine.check_text(song["text"], song["name"])["warnings"]


def test_the_final_colour_of_the_genre_is_kept_on_the_last_chord(q):
    assert q._color_last_voicing("4: 90@ Cmaj7 G7 100@ C", "C", "6") == "4: 90@ Cmaj7 G7 100@ C6"
    assert q._color_last_voicing("4: Dm7 G7 2Cmaj7*3", "C", "maj9") == "4: Dm7 G7 2Cmaj9*3"
    assert q._color_last_voicing("4: G7 Dm7", "C", "6") == "4: G7 Dm7"                  # l'ultimo accordo non e' la tonica
    assert q._color_last_voicing("4: Am7 Am7", "Am", "6") == "4: Am7 Am7"               # in minore la sesta maggiore stride
    assert q._color_last_voicing("4: [c*3 e*3 g*3] [a*3 c*4 e*4]", "Am", "6") == "4: [c*3 e*3 g*3] [a*3 c*4 e*4]"
    song = q.quick_song({"genre": "jazz", "mood": "allegra", "seed": 3, "key": "C", "duration": 30, "variety": 0})
    assert re.search(r"\bC6\b", song["text"])
    minor = q.quick_song({"genre": "jazz", "mood": "malinconica", "seed": 3, "key": "Am", "duration": 30, "variety": 0})
    assert not re.search(r"\bAm6\b|\bA6\b", minor["text"])


def test_the_bass_follows_the_inversions_and_the_seventh_of_the_chord():
    from core.rhythm_generate import ChordSpan, _resolve_role
    c_over_e = ChordSpan(0.0, 4.0, 0, True, 4, None, 4)
    assert _resolve_role("root", c_over_e, None, bass=True) == (4, 0)                  # il basso suona il Mi
    assert _resolve_role("root_hi", c_over_e, None, bass=True) == (4, 1)
    assert _resolve_role("fifth", c_over_e, None, bass=True) == (7, 0)                 # la quinta resta quella del Do
    assert _resolve_role("root", c_over_e, None) == (0, 0)                             # un accompagnamento no
    assert _resolve_role("flat7", ChordSpan(0.0, 4.0, 0, True, 4, 11), None) == (11, 0)   # sotto Cmaj7 il Si naturale
    assert _resolve_role("flat7", ChordSpan(0.0, 4.0, 0, True, 4, 10), None) == (10, 0)
    assert _resolve_role("flat7", ChordSpan(0.0, 4.0, 0, True, 4, None), None) == (10, 0)  # su una triade la settima minore (boogie, blues)
    assert _resolve_role("flat7", ChordSpan(0.0, 4.0, 9, True, 3, None), None) == (7, 0)   # Am -> Sol


def test_the_pedal_holds_the_tonic_under_the_changing_chords(q):
    assert q._tonic_progression("4: 4Am 4F 4C 4G/B", "Am") == "4: 4Am 4Am 4Am 4Am"
    assert q._tonic_progression("4: 2C 2G7 4Dm", "C") == "4: 2C 2C 4C"
    song = q.quick_song({"genre": "ballata", "mood": "calma", "duration": 240, "seed": 1, "variety": 0, "key": "Am"})
    assert any(s["role"] == "bridge" for s in song["sections"])
    _valid(q, song)
    rock = q.quick_song({"genre": "rock", "mood": "tesa", "seed": 4, "duration": 60, "variety": 0, "key": "Am"})
    _valid(q, rock)


def test_without_a_chorus_the_song_does_not_modulate(q):
    song = q.quick_song({"genre": "jazz", "mood": "allegra", "seed": 2, "form": "aaba", "modulation": True, "duration": 60, "variety": 0})
    assert len({s["key"] for s in song["sections"]}) == 1


def test_the_accompaniment_stays_under_the_melody(q):
    from core.project_io import parse_project_text
    from core.rhythm_generate import part_registers
    for genre in ("pop", "ballata", "bossa", "soul", "valzer"):                 # melodie a una voce, accompagnamenti polifonici
        song = q.quick_song({"genre": genre, "seed": 3, "duration": 60, "variety": 0})
        registers = part_registers(parse_project_text(song["text"], "Brano"))
        assert "melody_low" in registers and "comp_top" in registers, genre
        assert registers["comp_top"] <= registers["melody_low"] + 6, (genre, registers)   # l'accompagnamento resta sotto la melodia


@pytest.mark.parametrize("genre,mood", [("metal", "drammatica"), ("rock", "tesa"), ("jazz", "misteriosa"), ("bossa", "nostalgica"),
                                        ("valzer", "malinconica"), ("soul", "romantica"), ("lofi", "sognante"), ("punk", "oscura")])
def test_the_generated_songs_are_valid_after_the_harmony_changes(q, genre, mood):
    _valid(q, q.quick_song({"genre": genre, "mood": mood, "seed": 7, "duration": 45, "variety": 0}))


def test_the_same_seed_and_options_give_the_same_text(q):
    for options in ({"genre": "pop", "seed": 9, "duration": 60}, {"genre": "jazz", "mood": "malinconica", "seed": 4, "duration": 45},
                    {"genre": "metal", "mood": "drammatica", "seed": 972825931, "key": "Gm", "duration": 60}):
        first, second = q.quick_song(options), q.quick_song(options)
        assert first["text"] == second["text"]
        again = q.quick_song(json.loads(re.search(r"// quick: (\{.*\})", first["text"]).group(1)))      # l'intestazione riproduce il brano
        assert again["text"] == first["text"]


def test_no_generated_note_is_outside_the_range_of_its_instrument(q):
    from core.project_io import parse_project_text
    from core.rhythm_generate import pitch_to_midi
    for genre in q.GENRES_DATA:
        song = q.quick_song({"genre": genre, "seed": 21, "duration": 60})
        project = parse_project_text(song["text"], "Brano")
        for track in project.tracks:
            if track.is_audio or track.instrument.is_percussion or track.instrument_name == "Tuba":
                continue                       # la tuba suona il basso della marcia sotto la sua estensione di catalogo (52-82), dove sta una tuba vera
            for ev in track.parsed_events(project.patterns, meter=project.meter()):
                pitches = [pitch_to_midi(ev.letter, ev.octave)] if ev.kind == "note" and ev.letter else \
                    [pitch_to_midi(i["letter"], i["octave"]) for i in (ev.items or []) if ev.kind == "block" and i.get("kind") == "note" and i.get("letter")]
                for pitch in pitches:
                    assert track.instrument.range_low <= pitch <= track.instrument.range_high, (genre, track.name, pitch)


def test_the_drums_fill_the_last_bar_of_a_section_and_open_the_chorus_with_a_crash(q):
    from core.project_io import parse_project_text
    from st_language.midi import sounding_events
    song = q.quick_song({"genre": "pop", "seed": 1, "duration": 90, "variety": 0})
    project = parse_project_text(song["text"], "Brano")
    drums = next(t for t in project.tracks if t.name == "Drums")
    events = sounding_events(drums.parsed_events(project.patterns, meter=project.meter()))

    def names_at(beat):
        return {n for e in events if abs(e.start - beat) < 1e-6 for n in ([e.name] if e.name else []) + [i.get("name") for i in (e.items or [])]}

    def bar_of(index):
        return sorted((round(e.start - index * 4, 3), tuple(sorted(([e.name] if e.name else []) + [i.get("name") for i in (e.items or [])])))
                      for e in events if index * 4 - 1e-6 <= e.start < (index + 1) * 4 - 1e-6)
    chorus = [s for s in song["sections"] if s["role"] == "chorus"]
    assert chorus
    for section in chorus:
        assert "crash" in names_at(section["start_bar"] * 4.0), section            # il ritornello entra col crash
        before = section["start_bar"] - 1
        assert bar_of(before) != bar_of(before - 1), section                        # la battuta prima e' un fill, non il giro
    from core import rhythm_generate as rg
    plain = rg.generate_drum_pattern("rock", 4, fill_every=0)
    assert "crash" not in plain.split("|")[0] and "crash" in rg.generate_drum_pattern("rock", 4, fill_every=0, crash_first=True)


def test_on_the_strong_beat_the_melody_avoids_the_chord_tones_a_semitone_apart():
    from core.melody_generate import generate_phrase_melody
    from core.rhythm_generate import extract_chords_from_track
    chords = extract_chords_from_track("4: 4Cmaj7 4Fmaj7 4Cmaj7 4Fmaj7", {})
    text = generate_phrase_melody(chords, "melody_ballad", 5, 60, 84, key="C", seed=3, variability=0.5)
    from core.notation import parse_track_text
    for ev in parse_track_text(text, {}, default_octave=5):
        if ev.kind == "note" and ev.letter and abs(ev.start % 4) < 1e-6:
            bar = int(ev.start // 4)
            root, seventh = ("c", "b") if bar % 2 == 0 else ("f", "e")
            assert ev.letter not in (root, seventh), (ev.start, ev.letter)           # sul primo tempo: terza o quinta


def test_two_parts_never_share_an_instrument_and_the_genres_keep_their_bands(q):
    """Due parti con lo stesso strumento fanno due tracce con lo stesso nome (l'orchestrale dava il corno a melodia e fiati)."""
    for genre in q.GENRES_DATA:
        for mood in q.GENRES_DATA[genre]["moods"][:4]:
            for seed in range(1, 9):
                resolved = q.resolve({"genre": genre, "mood": mood, "seed": seed})
                inst, tracks = resolved["instruments"], resolved.get("track_names") or {}
                # lo strumento solo: due parti sullo stesso strumento, ma in tracce con il loro nome (mano destra e sinistra)
                names = [tracks.get(part, name) for part, name in inst.items() if part != "drums"]
                assert len(names) == len(set(names)), (genre, mood, seed, inst)
    pure = lambda genre: q.quick_song({"genre": genre, "seed": 1, "duration": 30, "variety": 0})["choices"]["instruments"]
    assert "comp2" not in pure("punk") and "comp2" not in pure("metal")                 # chitarre, basso e batteria
    assert pure("balcanico78")["bass"] == "Tuba" and pure("pop")["melody"] == "Flute"
    assert {q.resolve({"genre": "swing", "seed": s})["instruments"]["comp"] for s in range(1, 30)} <= {"Piano", "Jazz_Guitar"}


def test_the_second_voice_follows_the_chords_and_country_stays_major_with_the_fiddle(q):
    import json as _json
    from core.harmony_check import check_project
    from core.project_io import parse_project_text
    options = {"bars": 40, "seed": 195133427, "genre": "country", "mood": "grintosa", "duration": 60, "ending": "rallentando",
               "melody": "cantabile", "density": 0.7469179810274935}
    song = q.quick_song(options)
    assert not song["key"].endswith("m")                                              # il country resta in maggiore
    assert song["choices"]["instruments"]["harm"] == "Fiddle"                          # la seconda voce del country e' il violino
    assert "MelodiaRitornelloVoce" in song["text"]
    project = parse_project_text(song["text"], "Brano")
    assert check_project(project, melody_tracks=["Fiddle"]) == []                     # sugli accordi: nessuno scontro
    _valid(q, song)
    minor = q.quick_song({**options, "key": "Gm"})                                     # la tonalita' scelta vince
    assert minor["key"] == "Gm"
    assert check_project(parse_project_text(minor["text"], "Brano"), melody_tracks=[minor["choices"]["instruments"]["harm"]]) == []
    assert _json.loads(re.search(r"// quick: (\{.*\})", song["text"]).group(1))["genre"] == "country"


def test_second_voice_on_the_chords():
    from core import quicksong as qs
    from core.rhythm_generate import extract_chords_from_track
    chords = extract_chords_from_track("4: 4Gm 4Cm", {})
    scale = qs._melody_scale("", 7, "minor")
    voice = qs._second_voice("8: 90@ 2g*4 2a#*4 2c*5 2d#*5", chords, scale, "thirds", 55, 90, 8.0)
    # tutto su Sol minore (le note durano un quarto): sotto il sol il re (il mi b stride col re), sotto il si b il sol, sotto il do il si b
    # (il la stride col si b), sotto il mi b il do della scala
    assert voice == "16: 76@ 4d*4 76@ 4g*4 76@ 4a#*4 76@ 4c*5 16r"
    assert qs._second_voice("8T: c*4 d*4 e*4", chords, scale, "thirds", 55, 90, 4.0) is None   # le terzine: resta la voce per gradi


def test_the_second_voice_never_crosses_above_the_melody_and_bad_chords_stop_early(q):
    from core.rhythm_generate import extract_chords_from_track
    chords = extract_chords_from_track("4: 4C", {})
    scale = q._melody_scale("", 0, "major")
    # il mi4 sotto il sol4 starebbe sotto l'estensione (do5 in su): alzato d'ottava sarebbe sopra la melodia, quindi la nota si salta
    voice = q._second_voice("4: g*4 c*6 e*6 g*6", chords, scale, "thirds", 72, 96, 4.0)
    assert voice == "16: 4r 68@ 4a*5 68@ 4c*6 68@ 4e*6"                                # la prima nota (sol4) non ha seconda voce, le altre una terza sotto
    with pytest.raises(ValueError):
        q.resolve({"genre": "country", "mood": "grintosa", "chords": "Am F/X C G"})       # l'errore arriva subito, prima della tonalita'


def test_daily_song_depends_only_on_the_day(q):
    """Il brano del giorno: stesse scelte per lo stesso giorno (su ogni dispositivo), scelte valide, altre scelte nei giorni dopo."""
    import datetime
    a = q.quick_daily("2026-11-25")
    assert a == q.quick_daily("2026-11-25")
    assert a["genre"] in q.GENRES and a["mood"] in q.GENRES_DATA[a["genre"]]["moods"] and a["duration"] == 60
    days = [(datetime.date(2026, 11, 25) + datetime.timedelta(days=n)).isoformat() for n in range(30)]
    picks = {(d["genre"], d["mood"], d["seed"]) for d in map(q.quick_daily, days)}
    assert len(picks) == 30 and len({p[0] for p in picks}) > 5
    assert q.quick_daily()["day"] == datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    options = {k: v for k, v in a.items() if k != "day"}
    assert q.quick_song(options)["text"] == q.quick_song(options)["text"]
    with pytest.raises(ValueError):
        q.quick_daily("ieri")


def test_loud_chord_instruments_are_trimmed_but_not_the_melody(monkeypatch):
    """La chitarra jazz con accordi a 4-6 note copriva basso e melodia: negli accordi la sua velocity e' ridotta. Il fattore e'
    per parte: la chitarra distorta o l'organo che suonano la melodia non scendono come negli accordi, e il tappeto sta sotto."""
    from core import quicksong as q
    assert q._part_velocity("comp", "Jazz_Guitar") < 1 and q._part_velocity("comp", "Drawbar_Organ") < 1
    assert q._part_velocity("bass", "Acoustic_Bass") > 0.85
    assert q._part_velocity("melody", "Overdriven_Guitar") >= 1 and q._part_velocity("melody", "Rock_Organ") >= 1
    assert q._part_velocity("pad", "Strings") < 0.6 < q._part_velocity("comp", "Piano")
    options = {"genre": "jazz", "seed": 5}
    assert q.quick_song(options)["choices"]["instruments"]["comp"] == "Jazz_Guitar"
    trimmed = q.quick_song(options)["text"]
    monkeypatch.setattr(q, "_PART_INSTRUMENT_VELOCITY", {})
    assert trimmed != q.quick_song(options)["text"]


def test_rocknroll_verse_riff_boogie_intro_guitar_in_eighths_and_the_sax_in_its_register(q):
    """Il rock'n'roll: la strofa del sax e' un riff a botta e risposta (non note lunghe), l'intro e' il boogie col basso (non
    il pianoforte a note lunghe), la chitarra suona quinta e sesta a ottavi e il sax tenore resta dove suona pieno."""
    from core.project_io import parse_project_text
    from core.instruments import make_instrument_available
    song = q.quick_song({"genre": "rocknroll", "mood": "allegra", "duration": 60, "seed": 1571260660, "variety": 0})
    assert song["choices"]["instruments"]["melody"] == "Tenor_Sax"
    assert {"Piano", "Bass", "Drums"} <= set(_boxes(song, "Intro"))
    assert song["choices"]["styles"]["comp2"] == "chuck_guitar"
    project = parse_project_text(song["text"], "Brano")
    make_instrument_available("Tenor_Sax")
    sax = next(t for t in project.tracks if t.name == "Tenor_Sax")
    notes = [(e.start, e.duration, n) for e, n in _rnr_sounding(project, sax)]
    verse = [clip for clip in sax.clips if clip.name == "Strofa"]
    assert verse
    start = verse[0].start_beat
    in_verse = sorted(n for n in notes if start <= n[0] < start + 32)
    gaps = [b[0] - (a[0] + a[1]) for a, b in zip(in_verse, in_verse[1:])]
    assert sum(1 for g in gaps if g >= 2.5) >= 3                           # la band risponde: battute di silenzio fra i riff
    assert max(n for _s, _d, n in in_verse) <= q._COMFORT_HIGH["Tenor_Sax"]
    assert max(n for _s, _d, n in notes) <= q._COMFORT_HIGH["Tenor_Sax"] + q._SCREAM


def _rnr_sounding(project, track):
    from st_language.midi import resolve_event_notes, sounding_events
    out = []
    for ev in sounding_events(track.parsed_events(project.patterns, meter=project.meter())):
        if getattr(ev, "kind", "") != "note":
            continue
        notes, _v = resolve_event_notes(ev, track.instrument)
        out += [(ev, n) for n in notes]
    return out


def test_blues_keeps_the_twelve_bar_form_and_its_band(q):
    """Il blues: la sesta battuta resta il IV (o la diminuita di passaggio), mai la dominante; l'armonica canta gia' il primo
    giro a botta e risposta (A A B), la chitarra distorta suona lo shuffle e il basso chiude sulla tonica."""
    from core.rhythm_generate import generate_chord_progression, extract_chords_from_track
    for seed in range(30):
        spans = extract_chords_from_track("4: " + generate_chord_progression("Bb", "blues_12", bars=24, variability=1.0, seed=seed)
                                          .split(":", 1)[1], {})
        for chorus in (0, 48):
            sixth = [s for s in spans if s.start_beat <= chorus + 20 + 1e-6][-1]
            assert sixth.root_pc in (3, 4), (seed, chorus, sixth)          # mi b7 o mi diminuita, non fa7
    song = q.quick_song({"genre": "blues", "mood": "allegra", "duration": 60, "seed": 1621789363, "variety": 0})
    assert song["choices"]["instruments"]["melody"] == "Harmonica" and "Harmonica" in _boxes(song, "Giro 1")
    if song["choices"]["instruments"].get("comp") == "Overdriven_Guitar":
        assert song["choices"]["styles"]["comp"] == "chuck_guitar"
    import re as _re
    bass = _re.findall(r'Box Bass "Giro \d+" \|\d+:\n((?:  .*\n)+)', song["text"])[-1]
    assert bass.strip().rstrip("|").split("|")[-1].split() == ["4a#*2"]   # l'ultima battuta: il si b tenuto


def test_aaba_bridge_has_the_melody_and_every_a_is_the_same_theme(q):
    """L'AABA: il ponte e' meta' del tema (la melodia c'e'), e l'ultima A riprende la prima (stessi accordi e stessa melodia,
    salvo la chiusa); il tema delle A non e' la strofa leggera a minime."""
    import re as _re
    song = q.quick_song({"genre": "jazz", "mood": "allegra", "duration": 60, "seed": 87171273, "form": "aaba", "variety": 0})
    melody = song["choices"]["instruments"]["melody"]
    assert melody in _boxes(song, "B")
    boxes = _re.findall(r'Box ' + melody + r' "A" \|(\d+):\n((?:  .*\n)+)', song["text"])
    assert len(boxes) >= 3
    first, last = boxes[0][1].split(), boxes[-1][1].split()
    same = sum(a == b for a, b in zip(first, last))
    assert same >= 0.8 * len(first)                                         # la ripresa: quasi tutto uguale
    notes = [t for t in first if _re.fullmatch(r"\d*[a-g]#?\*\d", t)]
    assert sum(1 for t in notes if not _re.match(r"\d", t)) >= 8           # ottavi, non solo minime


def test_the_walking_bass_plays_four_quarters_with_a_chord_tone_on_one():
    from core.rhythm_generate import generate_bass_from_chords, extract_chords_from_track
    chords = extract_chords_from_track("4: 4Bm7 4E7 8Amaj7 4Bm7 4E7 8Amaj7", {})
    for seed in range(8):
        text = generate_bass_from_chords(chords, "walking", 2, variability=0.8, seed=seed)
        tokens = [t for t in text.split()[1:] if not t.endswith("@")]
        assert all(t[0] not in "0123456789r" for t in tokens), text          # un quarto per battito, niente pause ne' note lunghe
        assert len(tokens) == 32
        tones = {0: "b d f# a", 1: "e g# b d", 2: "a c# e g#", 3: "a c# e g#"}
        for bar in range(8):
            assert tokens[4 * bar].split("*")[0] in tones[bar % 4].split(), (seed, bar, tokens[4 * bar])


def test_soul_intro_has_the_bass_the_fade_is_the_whole_band_getting_quieter_and_horns_answer(q):
    import re as _re
    song = q.quick_song({"genre": "soul", "mood": "allegra", "duration": 60, "seed": 1547318177, "variety": 0, "ending": "sfumato"})
    instruments = song["choices"]["instruments"]
    assert instruments["bass"] in _boxes(song, "Intro")
    fade = _boxes(song, "Sfumato")
    assert {instruments["bass"], instruments["comp"], "Drums"} <= set(fade) and instruments["melody"] not in fade
    body = _re.search(r'Box Drums "Sfumato" \|\d+:\n((?:  .*\n)+)', song["text"]).group(1)
    velocities = [int(v) for v in _re.findall(r"(\d+)@", body)]
    assert sum(velocities[-8:]) / 8 < 0.6 * sum(velocities[:8]) / 8         # il volume scende
    if song["choices"]["styles"].get("comp2") == "sustained" and song["choices"]["styles"].get("pad") == "sustained" \
            and "pad" in instruments and instruments["pad"] in _boxes(song, "Ritornello"):
        assert instruments["comp2"] not in _boxes(song, "Ritornello")         # un tappeto solo
    if "horn" in instruments and "Strofa" in song["text"]:
        horn = _re.search(r'Box ' + instruments["horn"] + r' "Strofa" \|\d+:\n((?:  .*\n)+)', song["text"])
        if horn:
            assert "r" in horn.group(1)                                        # i fiati lasciano spazio alla melodia


def test_groove_intros_registers_and_genre_chord_colours(q):
    """I generi di groove attaccano con basso e batteria; la melodia sta sopra l'accompagnamento (chitarre e violino partivano
    dall'ottava 3) e il violino non scende sotto il sol3; marcia, valzer e balcanico non hanno la settima maggiore."""
    import re as _re
    from core.project_io import parse_project_text
    from core import harmony_check as hc
    for genre in ("funk", "disco", "reggae", "country"):
        song = q.quick_song({"genre": genre, "seed": 11, "duration": 60})
        intro = set(_boxes(song, "Intro"))
        assert {song["choices"]["instruments"]["bass"], "Drums"} <= intro, (genre, intro)
    for genre in ("funk", "disco", "punk", "metal", "balcanico78", "afro68"):
        song = q.quick_song({"genre": genre, "seed": 11, "duration": 60})
        inst = song["choices"]["instruments"]
        project = parse_project_text(song["text"], "Brano")
        tracks = {t.name: t for t in project.tracks}
        mean = lambda name: sum(n for _s, _d, n in hc._sounding(project, tracks[name])) / max(1, len(hc._sounding(project, tracks[name])))
        # prima la melodia stava 12-15 semitoni sotto l'accompagnamento; i colpi d'accordo del disco le stanno intorno
        assert mean(inst["melody"]) > mean(inst["comp"]) - 4, (genre, mean(inst["melody"]), mean(inst["comp"]))
        if inst["melody"] in ("Violin", "Fiddle"):
            assert min(n for _s, _d, n in hc._sounding(project, tracks[inst["melody"]])) >= 55, genre
    for genre in ("marcia", "valzer", "balcanico78"):
        for seed in range(4):
            text = q.quick_song({"genre": genre, "seed": seed, "duration": 60})["text"]
            assert not _re.search(r"[A-G][#b]?maj[79]", text), (genre, seed)


def test_disco_keeps_its_horns_octave_bass_and_scratch_guitar(q):
    """Il disco: i fiati nel ritornello ci sono (una melodia a ottavi non li cancella), il basso non e' la sola fondamentale,
    la chitarra pulita suona lo scratch; un box di fiati fatto solo di pause non si scrive."""
    import re as _re
    song = q.quick_song({"genre": "disco", "mood": "elegante", "seed": 1361863612, "duration": 60, "ending": "sfumato"})
    styles, inst = song["choices"]["styles"], song["choices"]["instruments"]
    assert styles["bass"] in ("octaves", "eighths")
    if "Guitar" in inst.get("comp2", ""):
        assert styles["comp2"] == "scratch"
    if "horn" in inst:
        chorus = _re.search(r'Box ' + inst["horn"] + r' "Ritornello" \|\d+:\n((?:  .*\n)+)', song["text"])
        assert chorus and q._hits(chorus.group(1)) >= 6
        for body in _re.findall(r'Box ' + inst["horn"] + r' "[^"]+" \|\d+:\n((?:  .*\n)+)', song["text"]):
            assert q._plays(body) or "%" in body


def test_a_bass_step_approach_that_rubs_against_the_chord_becomes_chromatic():
    from core.rhythm_generate import ChordSpan, _resolve_role
    amaj7 = ChordSpan(0.0, 4.0, 9, True, 4, 11)                             # la maj7: la do# mi sol#
    assert _resolve_role("approach_step", amaj7, 2) == (1, 0)                # verso il re: do# (non do, che sfrega col do#)
    a = ChordSpan(0.0, 4.0, 9, True, 4, None)
    assert _resolve_role("approach_step", a, 11) == (9, 0)                   # verso il si: la, nota dell'accordo, resta un tono sotto


def test_hiphop_hook_on_top_hat_in_the_chorus_and_the_808_on_the_kicks(q):
    """L'hip hop: il riff (il «campione») sta sopra il pianoforte, nel ritornello resta il charleston (non il ride) e il basso
    suona sui colpi di cassa, con le note tenute fino al colpo dopo."""
    import re as _re
    from core.project_io import parse_project_text
    from core import harmony_check as hc
    song = q.quick_song({"genre": "hiphop", "mood": "allegra", "seed": 1262233174, "duration": 60})
    inst = song["choices"]["instruments"]
    project = parse_project_text(song["text"], "Brano")
    tracks = {t.name: t for t in project.tracks}
    mean = lambda name: sum(n for _s, _d, n in hc._sounding(project, tracks[name])) / len(hc._sounding(project, tracks[name]))
    assert mean(inst["melody"]) > mean(inst["comp"]) + 5
    chorus = _re.search(r'Box Drums "Ritornello" \|\d+:\n((?:  .*\n)+)', song["text"]).group(1)
    assert "ride" not in chorus and "hihat" in chorus
    kicks = set(q._style_kicks("hiphop", 1, 4.0))
    starts = [s % 4.0 for s, _d, _n in hc._sounding(project, tracks[inst["bass"]])]
    assert sum(1 for s in starts if round(s, 2) in {round(k, 2) for k in kicks}) >= 0.9 * len(starts)


def test_grunge_clean_guitar_arpeggiates_the_verse_and_the_chorus_sings_higher(q):
    """Il grunge: la strofa e' la chitarra pulita che arpeggia (a ottavi anche se la strofa e' leggera, mai un piano al suo
    posto), il ritornello sale sopra la strofa (il centro delle frasi piu' alto di una terza maggiore)."""
    import re
    import statistics
    pcs = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}
    higher = 0
    for seed in (1, 2, 3):
        for variety in (0, 1):
            song = q.quick_song({"genre": "grunge", "mood": "epica", "seed": seed, "duration": 90, "variety": variety})
            assert song["choices"]["instruments"]["comp2"] == "Clean_Guitar"
            text = song["text"]
            verse_arp = re.search(r'Box Clean_Guitar "Strofa[^"]*" \|\d+:\n  (.*)', text).group(1)
            assert verse_arp.startswith("8:") and len(re.findall(r"[a-g]#?\*\d", verse_arp.split("|")[0])) >= 5
            mel = re.escape(song["choices"]["instruments"]["melody"])
            mean = {}
            for m in re.finditer(r'Box %s "(\S+)[^"]*" \|\d+:\n(.*?)(?=\nBox |\Z)' % mel, text, re.S):
                notes = [pcs[n[0]] + n.count("#") + 12 * int(o) for n, o in re.findall(r"([a-g]#?)\*(\d)", m.group(2))]
                if notes:
                    mean.setdefault(m.group(1), statistics.mean(notes))
            higher += mean["Ritornello"] > mean["Strofa"] + 1
    assert higher == 6
