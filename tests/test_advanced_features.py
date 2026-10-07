import os
import sys
import shutil
import tempfile
import glob

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _config_isolation  # noqa: F401  (prima di importare core)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.notation import parse_track_text, validate_track_text, Pattern, tokenize, NotationError
from core.instruments import (
    add_custom_instrument, remove_custom_instrument, get_instrument,
    list_instrument_names, InstrumentProfile, CUSTOM_INSTRUMENTS_FILE,
    resolve_or_create_instrument_by_program,
)
from core.model import Project
from core.midi_export import export_project_to_midi, export_single_track_to_midi
from core.midi_import import import_midi_file, import_midi_channel_into_track, list_midi_channels
from core import midi_convert


def _reset_custom_instruments():
    import core.instruments as im
    if os.path.exists(CUSTOM_INSTRUMENTS_FILE):
        os.remove(CUSTOM_INSTRUMENTS_FILE)
    im._custom_cache = None


def test_add_and_use_custom_instrument():
    _reset_custom_instruments()
    add_custom_instrument(InstrumentProfile(name="Synth", gm_program=81, range_low=36, range_high=96))
    assert "Synth" in list_instrument_names()
    instr = get_instrument("Synth")
    assert instr.gm_program == 81
    remove_custom_instrument("Synth")
    assert "Synth" not in list_instrument_names()


def test_cannot_remove_default_instrument():
    try:
        remove_custom_instrument("Piano")
        assert False, "doveva sollevare ValueError"
    except ValueError:
        pass


def test_rename_and_change_instrument():
    p = Project()
    p.add_track("Chitarra", "Guitar", "c d e")
    p.update_track("Chitarra", "Solo1", "Piano")
    t = p.get_track("Solo1")
    assert t.instrument_name == "Piano"
    try:
        p.get_track("Chitarra")
        assert False
    except KeyError:
        pass


def test_duplicate_rename_rejected():
    p = Project()
    p.add_track("A", "Piano")
    p.add_track("B", "Guitar")
    try:
        p.update_track("A", "B", "Piano")
        assert False
    except ValueError:
        pass


def test_pattern_repeat():
    patterns = {"R": Pattern(name="R", tokens=tokenize("16: 90@ c e g"))}
    ev = parse_track_text("3%R", patterns)
    assert len(ev) == 9


def test_pattern_reference_transpose_suffix_removed():
    """La trasposizione inline sui riferimenti a pattern (%Nome/N) e' stata
    rimossa dalla grammatica su richiesta: '%R/3' non e' piu' un riferimento
    valido (RE_PATTERN_REF non accetta piu' il suffisso '/N')."""
    patterns = {"R": Pattern(name="R", tokens=tokenize("16: c*4"))}
    ok, msg = validate_track_text("%R/3", patterns)
    assert not ok


def test_note_accidental_grammar():
    ev = parse_track_text("c# db*3 f#*5", {})
    assert [(e.letter, e.octave) for e in ev] == [("c#", 4), ("db", 3), ("f#", 5)]


def test_flat_accidental_synonyms_are_equivalent():
    """'b', '-' e '♭' devono essere sinonimi intercambiabili per il bemolle,
    sia sulle note sia sulla fondamentale di un accordo (vedi RE_NOTE/RE_CHORD
    in core.notation e note_name_to_pc/parse_chord_symbol in core.chords)."""
    from core.chords import note_name_to_pc, parse_chord_symbol

    assert note_name_to_pc("eb") == note_name_to_pc("e♭")
    assert note_name_to_pc("bb") == note_name_to_pc("b♭")  # Si bemolle

    for symbol in ("Bb7", "B♭7"):
        assert parse_chord_symbol(symbol).root_pc == 10

    ev = parse_track_text("e♭ eb", {})
    pcs = {note_name_to_pc(e.letter) for e in ev}
    assert pcs == {note_name_to_pc("eb")}

    # la lettera nota 'b' (Si) resta valida e distinta da un'alterazione
    ev_b = parse_track_text("b", {})
    assert ev_b[0].letter == "b"


def test_export_single_track_only_selected():
    tmpdir = tempfile.mkdtemp()
    try:
        p = Project()
        p.add_track("Solo", "Piano", "16: c d e f")
        p.add_track("Altra", "Bass", "16: c d e f")
        path = os.path.join(tmpdir, "solo.mid")
        export_single_track_to_midi(p, "Solo", path)
        _, _, channels = midi_convert.analyze_midi(path)
        total_notes = sum(c.note_count for c in channels.values())
        assert total_notes == 4  # solo la traccia "Solo", non anche "Altra"
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_recognizes_non_piano_instruments():
    tmpdir = tempfile.mkdtemp()
    try:
        p = Project()
        p.add_track("Trumpet", "Trumpet", "16: c*5 d*5 e*5 f*5")
        path = os.path.join(tmpdir, "tr.mid")
        export_single_track_to_midi(p, "Trumpet", path)
        imported = import_midi_file(path)
        assert imported.tracks[0].instrument_name == "Trumpet"
    finally:
        shutil.rmtree(tmpdir)


def test_midi_library_reference_and_repeat():
    tmpdir = tempfile.mkdtemp()
    try:
        p = Project()
        p.add_track("Lick", "Piano", "16: c*4 d*4 e*4 f*4")
        export_single_track_to_midi(p, "Lick", os.path.join(tmpdir, "MyLick.mid"))
        midi_convert.clear_midi_ref_cache()

        ev = parse_track_text('&"MyLick"', {}, midi_dir=tmpdir)
        assert len(ev) == 4

        ev2 = parse_track_text('2&"MyLick"', {}, midi_dir=tmpdir)
        assert len(ev2) == 8
    finally:
        shutil.rmtree(tmpdir)


def test_midi_library_missing_reference_errors():
    ok, msg = validate_track_text('&"NonEsisteDavvero"', {})
    assert not ok and "NonEsisteDavvero" in msg


def test_midi_import_creates_missing_instrument():
    _reset_custom_instruments()
    tmpdir = tempfile.mkdtemp()
    try:
        import mido
        mid = mido.MidiFile()
        track = mido.MidiTrack()
        mid.tracks.append(track)
        # Program 81 = "Lead 2 (sawtooth)", non tra gli strumenti predefiniti
        # (Piano/Guitar/Bass/Trumpet/Drums): un file MIDI "esterno" puo'
        # legittimamente usare uno qualsiasi dei 128 programmi GM.
        track.append(mido.Message("program_change", program=81, channel=0, time=0))
        track.append(mido.Message("note_on", note=60, velocity=100, channel=0, time=0))
        track.append(mido.Message("note_off", note=60, velocity=0, channel=0, time=480))
        path = os.path.join(tmpdir, "foreign.mid")
        mid.save(path)

        before = set(list_instrument_names())
        imported = import_midi_file(path)
        created = set(list_instrument_names()) - before

        assert len(created) == 1
        new_name = created.pop()
        assert imported.tracks[0].instrument_name == new_name
        assert get_instrument(new_name).gm_program == 81
    finally:
        shutil.rmtree(tmpdir)
        _reset_custom_instruments()


def test_midi_import_exact_default_match_creates_nothing():
    _reset_custom_instruments()
    tmpdir = tempfile.mkdtemp()
    try:
        p = Project()
        p.add_track("Tromba", "Trumpet", "16: c*5 d*5")
        path = os.path.join(tmpdir, "tr.mid")
        export_single_track_to_midi(p, "Tromba", path)

        before = set(list_instrument_names())
        imported = import_midi_file(path)
        assert set(list_instrument_names()) == before  # nessun nuovo strumento creato
        assert imported.tracks[0].instrument_name == "Trumpet"
    finally:
        shutil.rmtree(tmpdir)
        _reset_custom_instruments()


def test_channel_to_tokens_keeps_explicit_block_by_default():
    """Comportamento di sempre, invariato: senza recognize_chords, un
    gruppo di note simultanee resta un blocco esplicito [...], anche se
    corrisponde a un accordo standard riconoscibile."""
    from core.midi_convert import channel_to_tokens, ChannelData

    ch = ChannelData(channel=0)
    tpb = 480
    ch.notes = [(0, tpb, 60, 100), (0, tpb, 64, 100), (0, tpb, 67, 100)]  # Do maggiore
    tokens = channel_to_tokens(ch, tpb)
    assert tokens == ["16:", "100@", "4[c*4 e*4 g*4]"]


def test_channel_to_tokens_recognizes_chord_when_enabled():
    """Con recognize_chords=True, lo stesso accordo standard diventa la
    forma implicita equivalente (root/ottava), non piu' il blocco esplicito."""
    from core.midi_convert import channel_to_tokens, ChannelData
    from core.notation import validate_track_text

    ch = ChannelData(channel=0)
    tpb = 480
    ch.notes = [(0, tpb, 60, 100), (0, tpb, 64, 100), (0, tpb, 67, 100)]  # Do maggiore
    tokens = channel_to_tokens(ch, tpb, recognize_chords=True)
    assert tokens == ["16:", "100@", "4C*4"]
    ok, msg = validate_track_text(" ".join(tokens), {})
    assert ok, msg


def test_channel_to_tokens_recognizes_bare_fifth_as_power_chord():
    """Con recognize_chords=True, una semplice quinta (fondamentale+quinta,
    niente terza) e' riconosciuta come power chord ('5'), non lasciata
    come blocco esplicito: da quando '5' e' una qualita' vera non e' piu'
    un caso ambiguo."""
    from core.midi_convert import channel_to_tokens, ChannelData

    ch = ChannelData(channel=0)
    tpb = 480
    ch.notes = [(0, tpb, 60, 100), (0, tpb, 67, 100)]  # Do + Sol: solo quinta
    tokens = channel_to_tokens(ch, tpb, recognize_chords=True)
    assert tokens == ["16:", "100@", "4C5*4"]


def test_channel_to_tokens_falls_back_to_explicit_for_unrecognized_chord():
    """Con recognize_chords=True, un intervallo che non corrisponde a
    nessuna qualita' nota (es. una semplice seconda maggiore) deve
    comunque restare un blocco esplicito, non essere forzato in una forma
    implicita errata."""
    from core.midi_convert import channel_to_tokens, ChannelData

    ch = ChannelData(channel=0)
    tpb = 480
    ch.notes = [(0, tpb, 60, 100), (0, tpb, 62, 100)]  # Do + Re: seconda maggiore
    tokens = channel_to_tokens(ch, tpb, recognize_chords=True)
    assert tokens == ["16:", "100@", "4[c*4 d*4]"]


def test_midi_import_recognize_chords_option_end_to_end():
    """L'opzione si propaga correttamente da import_midi_file() fino al
    testo della traccia importata."""
    tmpdir = tempfile.mkdtemp()
    try:
        import mido
        mid = mido.MidiFile()
        track = mido.MidiTrack()
        mid.tracks.append(track)
        track.append(mido.Message("program_change", program=0, channel=0, time=0))
        for note in (60, 64, 67):  # Do maggiore in blocco
            track.append(mido.Message("note_on", note=note, velocity=100, channel=0, time=0))
        for i, note in enumerate((60, 64, 67)):
            track.append(mido.Message("note_off", note=note, velocity=0, channel=0,
                                       time=480 if i == 0 else 0))
        path = os.path.join(tmpdir, "chord.mid")
        mid.save(path)

        explicit = import_midi_file(path)
        assert "[" in explicit.tracks[0].text

        implicit = import_midi_file(path, recognize_chords=True)
        assert "[" not in implicit.tracks[0].text
        assert "C*4" in implicit.tracks[0].text
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_recognize_chords_setting_roundtrip():
    """L'opzione persistente deve valere False finche' non viene attivata
    esplicitamente (preserva il comportamento esistente per chi gia' usa
    l'app), e ricordare il valore impostato tra una lettura e l'altra."""
    from core import settings
    original = settings.get_midi_import_recognize_chords()
    try:
        settings.set_midi_import_recognize_chords(False)
        assert settings.get_midi_import_recognize_chords() is False
        settings.set_midi_import_recognize_chords(True)
        assert settings.get_midi_import_recognize_chords() is True
    finally:
        settings.set_midi_import_recognize_chords(original)


def _write_bend_midi(tmpdir, rpn_range, peak_semitones):
    """MIDI di una sola nota lunga con un bend fino a peak_semitones (su un
    canale con sensibilita' RPN rpn_range) che poi rientra sul centro."""
    import mido
    mid = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    for control, value in ((101, 0), (100, 0), (6, rpn_range), (38, 0)):
        track.append(mido.Message("control_change", control=control, value=value, channel=0, time=0))
    track.append(mido.Message("note_on", note=60, velocity=100, channel=0, time=0))
    peak = round(peak_semitones / rpn_range * 8192)
    track.append(mido.Message("pitchwheel", pitch=peak, channel=0, time=120))
    track.append(mido.Message("pitchwheel", pitch=peak, channel=0, time=240))
    track.append(mido.Message("pitchwheel", pitch=0, channel=0, time=120))
    track.append(mido.Message("note_off", note=60, velocity=0, channel=0, time=0))
    path = os.path.join(tmpdir, "bend.mid")
    mid.save(path)
    return path


def test_midi_import_min_bend_semitones_recovers_small_bend_on_wide_range():
    """Con RPN a 12 semitoni la soglia di sempre e' 1,2 semitoni: un bend di
    circa 1 semitono non e' uno slide, a meno di abbassare la soglia."""
    from core import midi_convert
    tmpdir = tempfile.mkdtemp()
    try:
        path = _write_bend_midi(tmpdir, rpn_range=12, peak_semitones=1.0)
        _, _, default = midi_convert.analyze_midi(path)
        assert not default[0].bends and not default[0].bend_paths
        _, _, sensitive = midi_convert.analyze_midi(path, min_bend_semitones=0.8)
        assert sensitive[0].bends or sensitive[0].bend_paths
        project = import_midi_file(path, min_bend_semitones=0.8)
        assert ">" in project.tracks[0].text
        assert ">" not in import_midi_file(path).tracks[0].text
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_min_bend_semitones_never_raises_threshold():
    """La soglia personalizzata puo' solo abbassare quella di sempre: con
    sensibilita' stretta (2 semitoni) un bend di 1 semitono e' gia' slide e
    resta identico, anche con una soglia richiesta alta."""
    from core import midi_convert
    tmpdir = tempfile.mkdtemp()
    try:
        path = _write_bend_midi(tmpdir, rpn_range=2, peak_semitones=1.0)
        _, _, default = midi_convert.analyze_midi(path)
        _, _, custom = midi_convert.analyze_midi(path, min_bend_semitones=1.2)
        assert default[0].bends and custom[0].bends == default[0].bends
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_slide_settings_roundtrip():
    from core import settings
    orig = (settings.get_midi_import_slide_sensitive(), settings.get_midi_import_slide_threshold())
    try:
        settings.set_midi_import_slide_sensitive(False)
        assert settings.get_midi_import_min_bend_semitones() is None
        settings.set_midi_import_slide_threshold(0.7)
        settings.set_midi_import_slide_sensitive(True)
        assert settings.get_midi_import_min_bend_semitones() == 0.7
        settings.set_midi_import_slide_threshold(9)  # fuori scala: limitato
        assert settings.get_midi_import_slide_threshold() == settings.MIDI_IMPORT_SLIDE_THRESHOLD_MAX
        settings.set_midi_import_slide_threshold(0)
        assert settings.get_midi_import_slide_threshold() == settings.MIDI_IMPORT_SLIDE_THRESHOLD_MIN
    finally:
        settings.set_midi_import_slide_threshold(orig[1])
        settings.set_midi_import_slide_sensitive(orig[0])


@pytest.mark.skipif(sys.platform == "win32", reason="i permessi delle cartelle funzionano diversamente su Windows")
def test_writable_dirs_fall_back_when_app_dir_is_read_only():
    """In un AppImage songs/, midi/ e soundfonts/ accanto all'eseguibile sono
    di sola lettura (o mancano): le cartelle proposte devono essere
    scrivibili."""
    from core import project_io, midi_library
    tmpdir = tempfile.mkdtemp()
    saved = (project_io.DEFAULT_SONGS_DIR, project_io.USER_SONGS_DIR,
             project_io.DEFAULT_SOUNDFONTS_DIR, project_io.USER_SOUNDFONTS_DIR,
             midi_library.DEFAULT_MIDI_DIR, midi_library.USER_MIDI_DIR)
    ro = os.path.join(tmpdir, "ro")
    os.makedirs(ro)
    os.chmod(ro, 0o555)
    try:
        if os.access(ro, os.W_OK):  # es. eseguiti come root: non simulabile
            return
        home = os.path.join(tmpdir, "home")
        project_io.DEFAULT_SONGS_DIR = os.path.join(ro, "songs")           # non creabile
        project_io.USER_SONGS_DIR = os.path.join(home, "songs")
        project_io.DEFAULT_SOUNDFONTS_DIR = os.path.join(ro, "soundfonts")  # non creabile
        project_io.USER_SOUNDFONTS_DIR = os.path.join(home, "soundfonts")
        midi_library.DEFAULT_MIDI_DIR = ro                                  # esiste, non scrivibile
        midi_library.USER_MIDI_DIR = os.path.join(home, "midi")
        assert project_io.ensure_songs_dir() == project_io.USER_SONGS_DIR
        assert project_io.ensure_soundfonts_dir() == project_io.USER_SOUNDFONTS_DIR
        assert midi_library.ensure_midi_dir() == midi_library.USER_MIDI_DIR
        assert all(os.path.isdir(d) for d in (project_io.USER_SONGS_DIR, project_io.USER_SOUNDFONTS_DIR,
                                              midi_library.USER_MIDI_DIR))
        # Se la cartella accanto all'app e' scrivibile, si usa quella.
        project_io.DEFAULT_SONGS_DIR = os.path.join(tmpdir, "writable")
        assert project_io.ensure_songs_dir() == project_io.DEFAULT_SONGS_DIR
    finally:
        (project_io.DEFAULT_SONGS_DIR, project_io.USER_SONGS_DIR,
         project_io.DEFAULT_SOUNDFONTS_DIR, project_io.USER_SOUNDFONTS_DIR,
         midi_library.DEFAULT_MIDI_DIR, midi_library.USER_MIDI_DIR) = saved
        os.chmod(ro, 0o755)
        shutil.rmtree(tmpdir)


def _write_scale_midi(tmpdir, declared_key=None):
    """MIDI con la scala di Sol maggiore ripetuta (tonica e quinta in
    evidenza), con un eventuale meta key signature dichiarato."""
    import mido
    mid = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    if declared_key:
        track.append(mido.MetaMessage("key_signature", key=declared_key, time=0))
    for note in (67, 69, 71, 72, 74, 76, 78, 79, 67, 74, 67, 71, 74, 67):
        track.append(mido.Message("note_on", note=note, velocity=100, channel=0, time=0))
        track.append(mido.Message("note_off", note=note, velocity=0, channel=0, time=480))
    path = os.path.join(tmpdir, "scale.mid")
    mid.save(path)
    return path


def test_midi_import_estimates_key_when_file_declares_none_or_c():
    tmpdir = tempfile.mkdtemp()
    try:
        assert import_midi_file(_write_scale_midi(tmpdir)).key == "G"
        assert import_midi_file(_write_scale_midi(tmpdir, "C")).key == "G"
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_keeps_declared_key_other_than_c():
    tmpdir = tempfile.mkdtemp()
    try:
        assert import_midi_file(_write_scale_midi(tmpdir, "D")).key == "D"
        assert import_midi_file(_write_scale_midi(tmpdir, "Am")).key == "Am"
    finally:
        shutil.rmtree(tmpdir)


def test_extract_chords_reads_explicit_blocks_like_symbols():
    """Le tracce importate da MIDI scrivono gli accordi come blocchi [...]:
    'Genera basso' deve seguirli come i simboli (Cmaj7...)."""
    from core.rhythm_generate import extract_chords_from_track
    symbols = extract_chords_from_track("4: C Am Dm G", {})
    blocks = extract_chords_from_track(
        "4: [c*4 e*4 g*4] [a*3 c*4 e*4] [d*4 f*4 a*4] [g*3 b*3 d*4]", {})
    assert [(c.root_pc, c.has_fifth) for c in blocks] == [(c.root_pc, c.has_fifth) for c in symbols]
    assert [c.start_beat for c in blocks] == [0.0, 1.0, 2.0, 3.0]


def test_extract_chords_unrecognized_block_uses_lowest_note_and_skips_single_notes():
    from core.rhythm_generate import extract_chords_from_track
    odd = extract_chords_from_track("4: [c*4 d*4 f#*4]", {})
    assert [(c.root_pc, c.has_fifth) for c in odd] == [(0, False)]
    assert extract_chords_from_track("4: c*4 e*4 g*4 a*4", {}) == []  # melodia: nessun accordo
    assert extract_chords_from_track("4: [c*4]", {}) == []           # blocco di una sola nota


def test_resolve_or_create_instrument_reuses_previously_created():
    _reset_custom_instruments()
    try:
        name1 = resolve_or_create_instrument_by_program(81, False)
        before = set(list_instrument_names())
        name2 = resolve_or_create_instrument_by_program(81, False)
        assert name1 == name2
        assert set(list_instrument_names()) == before  # idempotente: nessun duplicato
    finally:
        _reset_custom_instruments()


def test_resolve_or_create_instrument_percussion_and_none_program():
    _reset_custom_instruments()
    try:
        assert resolve_or_create_instrument_by_program(None, False) == "Piano"
        assert resolve_or_create_instrument_by_program(0, True) == "Drums"
    finally:
        _reset_custom_instruments()


def test_list_midi_channels_multi_instrument():
    tmpdir = tempfile.mkdtemp()
    try:
        p = Project()
        p.add_track("Piano1", "Piano", "16: c d e f")
        p.add_track("Drums1", "Drums", "16: kick snare kick snare")
        path = os.path.join(tmpdir, "multi.mid")
        export_project_to_midi(p, path, only_audible=False)
        channels = list_midi_channels(path)
        guesses = {g for _, _, g in channels}
        assert "Drums" in guesses
    finally:
        shutil.rmtree(tmpdir)


def test_gm_catalog_covers_128_programs():
    from core.instruments import gm_instrument_catalog
    catalog = gm_instrument_catalog()
    programs = sorted(p for p, _, _ in catalog)
    assert programs == list(range(128))


def test_gm_family_lookup():
    from core.instruments import gm_family_for_program
    assert gm_family_for_program(0) == "Pianoforti"
    assert gm_family_for_program(56) == "Ottoni"
    assert gm_family_for_program(127) == "Effetti sonori"


def test_midi_recursive_lookup_in_subfolder():
    tmpdir = tempfile.mkdtemp()
    try:
        sub = os.path.join(tmpdir, "Guitar")
        os.makedirs(sub)
        p = Project()
        p.add_track("Lick", "Piano", "16: c*4 d*4 e*4 f*4")
        export_single_track_to_midi(p, "Lick", os.path.join(sub, "Riff.mid"))
        midi_convert.clear_midi_ref_cache()

        ev = parse_track_text('&"Riff"', {}, midi_dir=tmpdir)
        assert len(ev) == 4

        ev_qualified = parse_track_text('&"Guitar/Riff"', {}, midi_dir=tmpdir)
        assert len(ev_qualified) == 4
    finally:
        shutil.rmtree(tmpdir)


def test_midi_ambiguous_name_requires_qualification():
    tmpdir = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(tmpdir, "A"))
        os.makedirs(os.path.join(tmpdir, "B"))
        p = Project()
        p.add_track("Lick", "Piano", "16: c*4 d*4")
        export_single_track_to_midi(p, "Lick", os.path.join(tmpdir, "A", "Riff.mid"))
        export_single_track_to_midi(p, "Lick", os.path.join(tmpdir, "B", "Riff.mid"))
        midi_convert.clear_midi_ref_cache()

        ok, msg = validate_track_text('&"Riff"', {}, midi_dir=tmpdir)
        assert not ok and "ambiguo" in msg

        ok2, msg2 = validate_track_text('&"A/Riff"', {}, midi_dir=tmpdir)
        assert ok2
    finally:
        shutil.rmtree(tmpdir)


def test_midi_ref_repeat_still_works():
    tmpdir = tempfile.mkdtemp()
    try:
        p = Project()
        p.add_track("Lick", "Piano", "16: c*4")
        export_single_track_to_midi(p, "Lick", os.path.join(tmpdir, "One.mid"))
        midi_convert.clear_midi_ref_cache()

        base = parse_track_text('&"One"', {}, midi_dir=tmpdir)
        repeated = parse_track_text('2&"One"', {}, midi_dir=tmpdir)
        assert len(repeated) == 2 * len(base)
        assert repeated[0].letter == repeated[1].letter == base[0].letter  # ripetizione identica
    finally:
        shutil.rmtree(tmpdir)


def test_midi_ref_transpose_suffix_removed():
    """'&"One/-2"' e' un percorso letterale (il nome sta fra le virgolette),
    che qui non esiste -> errore di file non trovato, non un crash."""
    tmpdir = tempfile.mkdtemp()
    try:
        p = Project()
        p.add_track("Lick", "Piano", "16: c*4")
        export_single_track_to_midi(p, "Lick", os.path.join(tmpdir, "One.mid"))
        midi_convert.clear_midi_ref_cache()

        ok, msg = validate_track_text('&"One/-2"', {}, midi_dir=tmpdir)
        assert not ok and "non trovato" in msg
    finally:
        shutil.rmtree(tmpdir)


def test_midi_library_lists_subfolder_paths():
    tmpdir = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(tmpdir, "Blues"))
        p = Project()
        p.add_track("Lick", "Piano", "16: c*4")
        export_single_track_to_midi(p, "Lick", os.path.join(tmpdir, "Blues", "Shuffle.mid"))
        export_single_track_to_midi(p, "Lick", os.path.join(tmpdir, "Root.mid"))
        names = midi_convert.list_midi_library(tmpdir)
        assert "Blues/Shuffle" in names
        assert "Root" in names
    finally:
        shutil.rmtree(tmpdir)


def test_embedded_instrument_autoloads_on_open():
    """Funzionalita' richiesta: se una song usa uno strumento personalizzato
    non ancora presente in locale, viene caricato/registrato automaticamente
    e la traccia non va persa."""
    from core.project_io import project_to_text, parse_project_text, save_project_file, load_project_file
    from core.instruments import add_custom_instrument, get_instrument

    _reset_custom_instruments()
    add_custom_instrument(InstrumentProfile(name="MioSax", gm_program=65, default_octave=4,
                                              range_low=49, range_high=82, polyphonic=False,
                                              voicing_style="monophonic"))
    p = Project(name="Test", tempo_bpm=100)
    p.add_track("Sax1", "MioSax", "16: c*4 d*4 e*4 f*4")

    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "song.st")
        save_project_file(p, path)

        # Simula l'apertura su una macchina "pulita": rimuove lo strumento in locale
        _reset_custom_instruments()
        assert "MioSax" not in list_instrument_names()

        p2 = load_project_file(path)
        assert "MioSax" in list_instrument_names()
        assert len(p2.tracks) == 1
        assert p2.tracks[0].instrument_name == "MioSax"

        instr = get_instrument("MioSax")
        assert instr.gm_program == 65 and instr.polyphonic is False
    finally:
        shutil.rmtree(tmpdir)
        _reset_custom_instruments()


def test_embedded_instrument_does_not_override_local_custom_definition():
    """Se lo strumento personalizzato esiste gia' in locale, la definizione
    incorporata nel file NON deve sovrascrivere quella locale."""
    from core.project_io import save_project_file, load_project_file
    from core.instruments import add_custom_instrument, get_instrument

    _reset_custom_instruments()
    add_custom_instrument(InstrumentProfile(name="MioSax", gm_program=65, default_octave=4,
                                              range_low=49, range_high=82, polyphonic=False,
                                              voicing_style="monophonic"))
    p = Project(name="Test")
    p.add_track("Sax1", "MioSax", "16: c*4")

    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "song.st")
        save_project_file(p, path)

        # Sull'altra macchina esiste GIA' un MioSax diverso (definito localmente)
        _reset_custom_instruments()
        add_custom_instrument(InstrumentProfile(name="MioSax", gm_program=10, default_octave=5,
                                                  range_low=30, range_high=100, polyphonic=True,
                                                  voicing_style="spread"))
        load_project_file(path)
        instr = get_instrument("MioSax")
        assert instr.gm_program == 10  # non sovrascritto dal file
    finally:
        shutil.rmtree(tmpdir)
        _reset_custom_instruments()


def test_renamed_track_survives_save_reload_roundtrip():
    """Bug preesistente scoperto insieme alla funzionalita' precedente: una
    traccia rinominata (nome diverso dallo strumento) non deve andare persa
    al salvataggio/ricaricamento."""
    from core.project_io import save_project_file, load_project_file

    p = Project(name="Test")
    p.add_track("Guitar 1", "Guitar", "16: e*3 g*3")
    p.update_track("Guitar 1", "SoloRinominato", "Bass")

    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "song.st")
        save_project_file(p, path)
        p2 = load_project_file(path)
        assert len(p2.tracks) == 1
        assert p2.tracks[0].name == "SoloRinominato"
        assert p2.tracks[0].instrument_name == "Bass"
    finally:
        shutil.rmtree(tmpdir)


def test_soundfont_manual_setting_takes_priority():
    from core import settings, playback
    settings.clear_soundfont_path()
    try:
        assert playback._find_soundfont() != "/tmp/__nonexistent_fake__.sf2"

        fake = tempfile.NamedTemporaryFile(suffix=".sf2", delete=False)
        fake.close()
        try:
            settings.set_soundfont_path(fake.name)
            assert playback._find_soundfont() == fake.name
            path, is_manual = playback.get_active_soundfont_info()
            assert path == fake.name and is_manual is True
        finally:
            os.remove(fake.name)
    finally:
        settings.clear_soundfont_path()


def test_soundfont_reset_falls_back_to_autodetect():
    from core import settings, playback
    fake = tempfile.NamedTemporaryFile(suffix=".sf2", delete=False)
    fake.close()
    try:
        settings.set_soundfont_path(fake.name)
        assert settings.get_soundfont_path() == fake.name
        settings.clear_soundfont_path()
        assert settings.get_soundfont_path() is None
        path, is_manual = playback.get_active_soundfont_info()
        assert is_manual is False
    finally:
        os.remove(fake.name)
        settings.clear_soundfont_path()


def test_song_file_with_instruments_and_mixer_blocks():
    """Il formato del file: strumento personalizzato con 'Strumento Nome:'
    (program=...), volume e pan della traccia nel suo blocco 'Mixer'."""
    from core.project_io import parse_project_text
    from core.instruments import get_instrument
    _reset_custom_instruments()
    text = """Strumento MioSax:
  program=66 percussione=no ottava=4 range=49-81 poly=no voicing=monophonic

Tempo: 82 BPM

Traccia Sax [MioSax]:
  16: c*4 d*4

Mixer Sax:
  volume: 95 pan: -0.3 mute: no solo: no
"""
    try:
        p = parse_project_text(text)
        assert get_instrument("MioSax").gm_program == 66
        t = p.get_track("Sax")
        assert t.instrument_name == "MioSax" and t.volume == 95 and t.pan < 64
    finally:
        _reset_custom_instruments()


def test_alternative_song_format_is_no_longer_read():
    """Niente piu' forma doppia: 'Instrument Nome:' con 'type:' e le
    intestazioni 'Nome — Strumento:' non sono piu' blocchi del file."""
    from core.project_io import parse_project_text
    import st_language as st
    _reset_custom_instruments()
    text = """Instrument MioSax:
  type: tenor_sax

Guitar — Guitar:
  16: c*4 d*4

Guitar - Guitar:
  16: c*4 d*4
"""
    try:
        assert parse_project_text(text).tracks == []
        assert "MioSax" not in list_instrument_names()
        assert st.read_song(text).tracks == []
    finally:
        _reset_custom_instruments()


def test_drum_kit_type_alias_marks_percussion():
    from core.instruments import resolve_instrument_type
    instr = resolve_instrument_type("drum_kit", "TamburoTest")
    assert instr.is_percussion is True


def test_unregistered_instrument_in_track_header_is_auto_registered():
    """Bug fix: un'intestazione traccia con uno strumento non ancora
    registrato non deve far sparire silenziosamente la traccia. Va risolto
    con resolve_instrument_type/ensure_instrument_available."""
    from core.project_io import parse_project_text
    from core.instruments import get_instrument

    _reset_custom_instruments()
    assert "AcousticGuitar" not in list_instrument_names()
    text = """Traccia AcousticGuitar [AcousticGuitar]:
  16: c*4 d*4
"""
    try:
        p = parse_project_text(text)
        assert "AcousticGuitar" in list_instrument_names()
        assert len(p.tracks) == 1
        t = p.get_track("AcousticGuitar")
        assert t.instrument_name == "AcousticGuitar"
        instr = get_instrument("AcousticGuitar")
        assert instr.gm_program is not None  # dedotto per fuzzy-match sul nome GM
    finally:
        _reset_custom_instruments()


def test_pan_conversion_ranges():
    from core.project_io import _convert_pan_to_0_127
    assert _convert_pan_to_0_127("0.0") == 64
    assert _convert_pan_to_0_127("1.0") == 127
    assert _convert_pan_to_0_127("-1.0") == 1
    assert 70 <= _convert_pan_to_0_127("0.2") <= 80


@pytest.mark.skipif(not sys.platform.startswith("linux"),
                    reason="usa finti programmi bash e il player di Linux (paplay)")
def test_playback_offline_render_with_fake_fluidsynth():
    """Verifica il rendering offline in WAV + playback, usando un finto
    binario fluidsynth (nel sandbox di test non e' disponibile quello vero)."""
    import stat
    from core import playback, settings

    tmpdir = tempfile.mkdtemp()
    fakebin = os.path.join(tmpdir, "bin")
    os.makedirs(fakebin)

    fluidsynth_script = os.path.join(fakebin, "fluidsynth")
    with open(fluidsynth_script, "w") as f:
        f.write(
            "#!/bin/bash\n"
            "for i in \"$@\"; do\n"
            "  if [ \"$prev\" = \"-F\" ]; then outfile=\"$i\"; fi\n"
            "  prev=\"$i\"\n"
            "done\n"
            "if [ -n \"$outfile\" ]; then\n"
            "  printf 'RIFF' > \"$outfile\"\n"
            "  head -c 200 /dev/zero >> \"$outfile\"\n"
            "fi\n"
            "exit 0\n"
        )
    os.chmod(fluidsynth_script, os.stat(fluidsynth_script).st_mode | stat.S_IEXEC)

    player_script = os.path.join(fakebin, "paplay")
    with open(player_script, "w") as f:
        f.write("#!/bin/bash\nsleep 0.1\nexit 0\n")
    os.chmod(player_script, os.stat(player_script).st_mode | stat.S_IEXEC)

    fake_sf2 = os.path.join(tmpdir, "Fake.sf2")
    open(fake_sf2, "wb").close()

    old_path = os.environ.get("PATH", "")
    # Solo fakebin, senza fallback al PATH reale: su un sistema con
    # PipeWire, _find_audio_player() troverebbe "pw-play" (che ha
    # precedenza su "paplay") ancora presente nel PATH originale,
    # rendendo il test non deterministico.
    os.environ["PATH"] = fakebin
    try:
        settings.set_soundfont_path(fake_sf2)
        desc = playback.describe_playback_engine()
        assert "fluidsynth" in desc and fake_sf2 in desc and "paplay" in desc

        p = Project(name="Test")
        p.add_track("Piano1", "Piano", "16: c*4 e*4")
        engine = playback.PlaybackEngine()
        result = {}
        engine.play(p, on_finished=lambda ok: result.update(ok=ok))
        import time
        for _ in range(30):
            if "ok" in result:
                break
            time.sleep(0.1)
        assert result.get("ok") is True
    finally:
        os.environ["PATH"] = old_path
        settings.clear_soundfont_path()
        shutil.rmtree(tmpdir)


@pytest.mark.skipif(sys.platform == "win32", reason="usa finti programmi bash (#!/bin/bash)")
def test_playback_stop_during_offline_render_terminates_process():
    """Regressione: il rendering offline (necessario prima della riproduzione,
    puo' richiedere diversi secondi su un brano lungo/complesso) usava
    subprocess.run() bloccante, mai tracciato in self._proc: stop() non
    aveva quindi alcun processo su cui agire finche' il rendering non
    terminava da solo ('a volte lo stop non funziona' sui brani piu' lunghi).
    Simula un rendering lento con un finto fluidsynth che dorme, e verifica
    che stop() lo interrompa davvero (il player non deve mai partire)."""
    import stat
    import time
    from core import playback, settings

    tmpdir = tempfile.mkdtemp()
    fakebin = os.path.join(tmpdir, "bin")
    os.makedirs(fakebin)
    marker_path = os.path.join(tmpdir, "player_was_called")

    fluidsynth_script = os.path.join(fakebin, "fluidsynth")
    with open(fluidsynth_script, "w") as f:
        f.write(
            "#!/bin/bash\n"
            "sleep 5\n"  # simula un rendering lungo (brano complesso)
            "for i in \"$@\"; do\n"
            "  if [ \"$prev\" = \"-F\" ]; then outfile=\"$i\"; fi\n"
            "  prev=\"$i\"\n"
            "done\n"
            "if [ -n \"$outfile\" ]; then\n"
            "  printf 'RIFF' > \"$outfile\"\n"
            "  head -c 200 /dev/zero >> \"$outfile\"\n"
            "fi\n"
            "exit 0\n"
        )
    os.chmod(fluidsynth_script, os.stat(fluidsynth_script).st_mode | stat.S_IEXEC)

    player_script = os.path.join(fakebin, "paplay")
    with open(player_script, "w") as f:
        f.write(f"#!/bin/bash\ntouch {marker_path}\nexit 0\n")
    os.chmod(player_script, os.stat(player_script).st_mode | stat.S_IEXEC)

    fake_sf2 = os.path.join(tmpdir, "Fake.sf2")
    open(fake_sf2, "wb").close()

    old_path = os.environ.get("PATH", "")
    os.environ["PATH"] = fakebin + os.pathsep + old_path
    try:
        settings.set_soundfont_path(fake_sf2)
        p = Project(name="Test")
        p.add_track("Piano1", "Piano", "16: c*4 e*4")
        engine = playback.PlaybackEngine()
        engine.play(p)

        time.sleep(0.3)  # il finto rendering (5s di sleep) e' sicuramente partito
        assert engine.is_playing(), "il processo di rendering deve essere tracciato come 'in corso'"

        engine.stop()
        for _ in range(30):
            if not engine.is_playing():
                break
            time.sleep(0.1)
        assert not engine.is_playing(), "stop() deve interrompere il rendering, non solo l'eventuale playback successivo"

        time.sleep(0.2)
        assert not os.path.exists(marker_path), "il player non deve mai partire se si e' fermato durante il rendering"
    finally:
        os.environ["PATH"] = old_path
        settings.clear_soundfont_path()
        shutil.rmtree(tmpdir)


def test_extract_patterns_preserves_musical_content():
    """Round-trip: estrazione + validazione + confronto eventi identici."""
    from core.reorganize import extract_patterns_for_project, expand_patterns_for_project

    p = Project(name="Test")
    p.add_track("Guitar", "Guitar",
                "16: 100@ c*4 e*4 g*4 e*4 100@ c*4 e*4 g*4 e*4 90@ d*4 f*4 a*4 f*4 100@ c*4 e*4 g*4 e*4")
    orig_events = p.tracks[0].parsed_events({})

    summary = extract_patterns_for_project(p, min_window=4, min_repeats=2)
    assert "Guitar" in summary
    assert len(p.patterns) >= 1

    for t in p.tracks:
        ok, msg = validate_track_text(t.text, p.patterns, default_octave=t.instrument.default_octave)
        assert ok, msg

    new_events = p.tracks[0].parsed_events(p.patterns)
    key = lambda e: (e.letter, e.octave, e.velocity, e.start, e.duration)
    assert [key(e) for e in orig_events] == [key(e) for e in new_events]

    expand_summary = expand_patterns_for_project(p)
    assert not p.patterns  # nessun pattern residuo dopo l'espansione totale
    final_events = p.tracks[0].parsed_events(p.patterns)
    assert [key(e) for e in orig_events] == [key(e) for e in final_events]


def test_extract_patterns_noop_on_track_without_repeats():
    from core.reorganize import extract_patterns_for_project
    p = Project(name="Test")
    p.add_track("Piano", "Piano", "c*4 d*4 e*4")
    summary = extract_patterns_for_project(p)
    assert summary == {}
    assert p.tracks[0].text == "c*4 d*4 e*4"


def test_extract_patterns_handles_empty_track():
    from core.reorganize import extract_patterns_for_project
    p = Project(name="Test")
    p.add_track("Piano", "Piano", "")
    summary = extract_patterns_for_project(p)  # non deve sollevare eccezioni
    assert summary == {}


def test_expand_patterns_noop_without_references():
    from core.reorganize import expand_patterns_for_project
    p = Project(name="Test")
    p.add_track("Piano", "Piano", "16: c*4 d*4 e*4 f*4")
    summary = expand_patterns_for_project(p)
    assert summary == {}
    assert p.tracks[0].text == "16: c*4 d*4 e*4 f*4"


def test_extract_patterns_does_not_move_blocks_that_depend_on_key_or_rel():
    """Un pattern parte senza tonalita' e in ottave assolute: i blocchi dopo
    key= o rel: non vanno estratti, altrimenti suonerebbero diversi."""
    from core.reorganize import extract_patterns_from_tokens
    from core.notation import tokenize
    toks = tokenize("key=F 4: b*4 a*4 g*4 f*4 b*4 a*4 g*4 f*4 b*4 a*4 g*4 f*4")
    new, pats = extract_patterns_from_tokens(toks, [], min_window=4, min_repeats=2)
    assert pats == {} and new == toks
    # senza il comando di stato la ripetizione si estrae come prima
    toks = tokenize("4: b*4 a*4 g*4 f*4 b*4 a*4 g*4 f*4 b*4 a*4 g*4 f*4")
    new, pats = extract_patterns_from_tokens(toks, [], min_window=4, min_repeats=2)
    assert pats


def test_extract_and_expand_all_real_songs_roundtrip():
    """Verifica su tutti i progetti reali (examples/ + songs/): l'estrazione
    non deve mai alterare il contenuto musicale ne' produrre sintassi non valida."""
    from core.reorganize import extract_patterns_for_project
    files = glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                    "examples", "*.st"))
    files += glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                     "songs", "*.st"))
    assert files, "nessun file di esempio trovato per il test"

    from core.project_io import load_project_file
    key = lambda e: (e.kind, getattr(e, "letter", None), getattr(e, "symbol", None),
                      getattr(e, "name", None), e.start, e.duration)

    for f in files:
        proj = load_project_file(f)
        orig = {t.name: [key(e) for e in t.parsed_events(proj.patterns)] for t in proj.tracks}
        extract_patterns_for_project(proj, min_window=4, min_repeats=2)
        for t in proj.tracks:
            ok, msg = validate_track_text(t.text, proj.patterns, default_octave=t.instrument.default_octave)
            assert ok, f"{f} :: {t.name}: {msg}"
            new_ev = [key(e) for e in t.parsed_events(proj.patterns)]
            assert new_ev == orig[t.name], f"{f} :: {t.name}: contenuto alterato"


def test_extract_patterns_consolidates_without_creating_wrapper_pattern():
    """Regressione: se una traccia scrive per esteso un riferimento gia'
    ripetuto (es. 8 volte '%RockDrums'), l'estrazione deve consolidarlo in
    '8%RockDrums' anche quando questo non richiede la creazione di un nuovo
    pattern 'involucro' (in tal caso summary resta vuoto per quella traccia,
    ma il testo va comunque riscritto in forma compatta)."""
    from core.reorganize import extract_patterns_for_project
    p = Project(name="Test")
    p.patterns["RockDrums"] = Pattern(name="RockDrums", tokens=tokenize("8: kick hihat snare hihat"))
    p.add_track("Drums", "Drums", " ".join(["%RockDrums"] * 8))

    summary = extract_patterns_for_project(p)
    assert summary == {}  # nessun NUOVO pattern creato
    assert p.tracks[0].text == "8%RockDrums"  # ma il testo e' stato comunque compattato


def test_mixer_settings_persist_across_save_reload():
    """Bug corretto: volume/pan/mute/solo non venivano salvati nel file."""
    from core.project_io import save_project_file, load_project_file
    p = Project(name="Test")
    p.add_track("Piano1", "Piano", "16: c*4 d*4")
    p.tracks[0].volume = 40
    p.tracks[0].pan = 20
    p.tracks[0].mute = True
    p.add_track("Bass1", "Bass", "16: c*2 e*2")  # tutto default

    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "song.st")
        save_project_file(p, path)
        p2 = load_project_file(path)
        t1 = p2.get_track("Piano1")
        assert t1.volume == 40
        assert abs(t1.pan - 20) <= 1
        assert t1.mute is True
        t2 = p2.get_track("Bass1")
        assert t2.volume == 100 and t2.pan == 64 and t2.mute is False and t2.solo is False
    finally:
        shutil.rmtree(tmpdir)


def test_mixer_block_not_written_for_default_tracks():
    """Le tracce con mixer tutto di default non devono generare un blocco
    Mixer nel file (per non appesantire inutilmente i progetti semplici)."""
    from core.project_io import project_to_text
    p = Project(name="Test")
    p.add_track("Piano1", "Piano", "16: c*4")
    text = project_to_text(p)
    assert "Mixer" not in text


def test_volume_scales_note_velocity_in_export():
    """Il volume (0-200, 100=default) deve scalare direttamente la velocity
    delle note esportate: e' il meccanismo che rende il controllo udibile."""
    from core.midi_export import export_project_to_midi
    from core import midi_convert

    tmpdir = tempfile.mkdtemp()
    try:
        p = Project(name="Test")
        p.add_track("Piano1", "Piano", "16: 100@ c*4 e*4 g*4")

        path100 = os.path.join(tmpdir, "v100.mid")
        export_project_to_midi(p, path100)
        _, _, ch = midi_convert.analyze_midi(path100)
        assert [v for _, _, _, v in list(ch.values())[0].notes] == [100, 100, 100]

        p.tracks[0].volume = 50
        path50 = os.path.join(tmpdir, "v50.mid")
        export_project_to_midi(p, path50)
        _, _, ch2 = midi_convert.analyze_midi(path50)
        assert [v for _, _, _, v in list(ch2.values())[0].notes] == [50, 50, 50]

        p.tracks[0].volume = 200
        path200 = os.path.join(tmpdir, "v200.mid")
        export_project_to_midi(p, path200)
        _, _, ch3 = midi_convert.analyze_midi(path200)
        assert [v for _, _, _, v in list(ch3.values())[0].notes] == [127, 127, 127]  # clampato

        p.tracks[0].volume = 0
        path0 = os.path.join(tmpdir, "v0.mid")
        export_project_to_midi(p, path0)
        _, _, ch4 = midi_convert.analyze_midi(path0)
        # volume a zero = nessun suono (non "velocity 1"): vedi il commento nel
        # ramo note di core.midi_export.export_project_to_midi
        assert sum(c.note_count for c in ch4.values()) == 0
    finally:
        shutil.rmtree(tmpdir)


def test_humanize_off_by_default_is_fully_deterministic():
    """Senza humanize (default), esportare due volte lo stesso progetto deve
    produrre esattamente gli stessi tick/velocity: nessuna casualita' entra
    in gioco se la funzionalita' non e' esplicitamente richiesta."""
    tmpdir = tempfile.mkdtemp()
    try:
        p = Project(name="Test")
        p.add_track("Piano1", "Piano", "16: c*4 d*4 e*4 f*4 g*4 a*4 b*4 c*5")

        path1 = os.path.join(tmpdir, "a.mid")
        path2 = os.path.join(tmpdir, "b.mid")
        export_project_to_midi(p, path1)
        export_project_to_midi(p, path2)
        _, _, ch1 = midi_convert.analyze_midi(path1)
        _, _, ch2 = midi_convert.analyze_midi(path2)
        assert list(ch1.values())[0].notes == list(ch2.values())[0].notes
    finally:
        shutil.rmtree(tmpdir)


def test_humanize_jitters_timing_and_velocity_when_enabled():
    """Con humanize=True e intensita' massima, due export dello stesso
    progetto devono differire (nessun seed fisso: e' proprio l'incoerenza
    tra un ascolto e l'altro a suonare 'umana', vedi commento nella spec)."""
    tmpdir = tempfile.mkdtemp()
    try:
        p = Project(name="Test")
        p.add_track("Piano1", "Piano", "16: c*4 d*4 e*4 f*4 g*4 a*4 b*4 c*5 c*4 d*4 e*4 f*4")

        path1 = os.path.join(tmpdir, "a.mid")
        path2 = os.path.join(tmpdir, "b.mid")
        export_project_to_midi(p, path1, humanize=True, humanize_amount=100)
        export_project_to_midi(p, path2, humanize=True, humanize_amount=100)
        _, _, ch1 = midi_convert.analyze_midi(path1)
        _, _, ch2 = midi_convert.analyze_midi(path2)
        notes1 = list(ch1.values())[0].notes
        notes2 = list(ch2.values())[0].notes
        assert notes1 != notes2  # timing e/o velocity diversi tra i due render
    finally:
        shutil.rmtree(tmpdir)


def test_humanize_keeps_velocity_and_timing_within_valid_bounds():
    """Anche a intensita' massima, la velocity deve restare in 1-127 (mai 0,
    che sarebbe un note-off) e ogni nota deve avere una durata positiva
    (start < end), su un campione ampio di note per ridurre la probabilita'
    di un falso positivo dovuto al caso."""
    tmpdir = tempfile.mkdtemp()
    try:
        p = Project(name="Test")
        p.add_track("Piano1", "Piano", "16: " + "c*4 d*4 e*4 f*4 " * 20)
        path = os.path.join(tmpdir, "stress.mid")
        export_project_to_midi(p, path, humanize=True, humanize_amount=100)
        _, _, ch = midi_convert.analyze_midi(path)
        notes = list(ch.values())[0].notes
        assert len(notes) == 80
        for start, end, _pitch, vel in notes:
            assert 1 <= vel <= 127
            assert end > start
    finally:
        shutil.rmtree(tmpdir)


def test_humanize_does_not_shift_percussion_timing_only_velocity():
    """La batteria non deve ricevere il jitter di timing (una griglia
    percussiva e' quasi sempre voluta), solo quello di velocity."""
    tmpdir = tempfile.mkdtemp()
    try:
        p = Project(name="Test")
        p.add_track("Drums1", "Drums", "16: " + "kick hihat snare hihat " * 10)
        path_off = os.path.join(tmpdir, "off.mid")
        path_on = os.path.join(tmpdir, "on.mid")
        export_project_to_midi(p, path_off)
        export_project_to_midi(p, path_on, humanize=True, humanize_amount=100)
        _, _, ch_off = midi_convert.analyze_midi(path_off)
        _, _, ch_on = midi_convert.analyze_midi(path_on)
        starts_off = [start for start, _end, _pitch, _vel in list(ch_off.values())[0].notes]
        starts_on = [start for start, _end, _pitch, _vel in list(ch_on.values())[0].notes]
        assert starts_off == starts_on  # nessuno spostamento di timing sulla batteria
    finally:
        shutil.rmtree(tmpdir)


def test_humanize_settings_roundtrip():
    from core import settings
    original_enabled = settings.get_humanize_enabled()
    original_amount = settings.get_humanize_amount()
    try:
        settings.set_humanize_enabled(True)
        assert settings.get_humanize_enabled() is True
        settings.set_humanize_enabled(False)
        assert settings.get_humanize_enabled() is False

        settings.set_humanize_amount(75)
        assert settings.get_humanize_amount() == 75
        settings.set_humanize_amount(150)  # fuori range, deve essere clampato
        assert settings.get_humanize_amount() == 100
        settings.set_humanize_amount(-10)
        assert settings.get_humanize_amount() == 0
    finally:
        settings.set_humanize_enabled(original_enabled)
        settings.set_humanize_amount(original_amount)


def test_extract_patterns_uses_instrument_name_as_prefix():
    from core.reorganize import extract_patterns_for_project
    p = Project(name="Test")
    p.add_track("Guitar1", "Guitar",
                "16: 100@ c*4 e*4 g*4 e*4 100@ c*4 e*4 g*4 e*4 90@ d*4 f*4 a*4 f*4 100@ c*4 e*4 g*4 e*4")
    summary = extract_patterns_for_project(p)
    assert "Guitar1" in summary
    created_names = list(summary["Guitar1"].keys())
    assert all(name.startswith("Guitar") for name in created_names)
    assert all(name.startswith("Guitar") for name in p.patterns.keys())


def test_extract_patterns_never_nests_pattern_references():
    """I pattern estratti non devono mai contenere riferimenti ad altri
    pattern (ne' a quelli preesistenti ne' a quelli creati nella stessa
    passata di estrazione): nessun nesting."""
    from core.reorganize import extract_patterns_for_project
    p = Project(name="Test")
    p.patterns["Lib1"] = Pattern(name="Lib1", tokens=tokenize("kick snare"))
    p.add_track("Drums1", "Drums",
                "%Lib1 c*4 d*4 e*4 f*4 %Lib1 c*4 d*4 e*4 f*4 %Lib1 c*4 d*4 e*4 f*4")

    extract_patterns_for_project(p)

    for name, pat in p.patterns.items():
        for tok in pat.tokens:
            stripped = tok.lstrip("0123456789")
            assert not stripped.startswith("%"), f"pattern nidificato trovato in '{name}': {tok}"

    for t in p.tracks:
        ok, msg = validate_track_text(t.text, p.patterns, default_octave=t.instrument.default_octave)
        assert ok, msg


def test_compute_token_spans_basic_notes():
    from core.notation import compute_token_spans
    text = "16: c*4 d*4 e*4 f*4"
    spans = compute_token_spans(text, {})
    assert len(spans) == 4
    assert text[spans[0][0]:spans[0][1]] == "c*4"
    assert spans[0][2] == 0.0
    assert abs(spans[0][3] - 0.25) < 1e-9
    assert abs(spans[1][2] - 0.25) < 1e-9


def test_compute_token_spans_pattern_is_single_span():
    from core.notation import compute_token_spans, Pattern
    patterns = {"Riff": Pattern(name="Riff", tokens=tokenize("16: c*4 e*4 g*4"))}
    text = "2%Riff d*4"
    spans = compute_token_spans(text, patterns)
    assert len(spans) == 2
    assert text[spans[0][0]:spans[0][1]] == "2%Riff"
    assert abs(spans[0][3] - 1.5) < 1e-9  # 2 ripetizioni x 3 note x 1/16 = 1.5 beat


def test_compute_token_spans_skips_invalid_token_without_crashing():
    from core.notation import compute_token_spans
    spans = compute_token_spans("c*4 Cxyz123 d*4", {})
    assert len(spans) == 2  # il token non valido viene semplicemente saltato


def test_find_span_at_beat():
    from core.notation import compute_token_spans, find_span_at_beat
    text = "16: c*4 d*4 e*4 f*4"
    spans = compute_token_spans(text, {})
    found = find_span_at_beat(spans, 0.3)
    assert text[found[0]:found[1]] == "d*4"
    assert find_span_at_beat(spans, 999) is None


def test_compute_project_duration_beats():
    from core.midi_export import compute_project_duration_beats
    p = Project(name="Test")
    p.add_track("Piano1", "Piano", "16: c*4 d*4 e*4 f*4 g*4 a*4 b*4 c*5")
    dur = compute_project_duration_beats(p)
    assert abs(dur - 2.0) < 1e-6


def test_export_with_start_offset_skips_earlier_notes():
    from core.midi_export import export_project_to_midi
    from core import midi_convert
    tmpdir = tempfile.mkdtemp()
    try:
        p = Project(name="Test")
        p.add_track("Piano1", "Piano", "16: c*4 d*4 e*4 f*4 g*4 a*4 b*4 c*5")

        path_full = os.path.join(tmpdir, "full.mid")
        export_project_to_midi(p, path_full)
        _, _, ch = midi_convert.analyze_midi(path_full)
        assert list(ch.values())[0].note_count == 8

        path_offset = os.path.join(tmpdir, "offset.mid")
        export_project_to_midi(p, path_offset, start_offset_beats=1.0)
        _, _, ch2 = midi_convert.analyze_midi(path_offset)
        assert list(ch2.values())[0].note_count == 4
    finally:
        shutil.rmtree(tmpdir)


# ---- Import MIDI: tempo variabile, metrica, pedale sustain ----

def _write_midi(path, events, tpb=480):
    """events: [(abs_tick, mido.Message | mido.MetaMessage), ...] su una traccia."""
    import mido
    mid = mido.MidiFile(ticks_per_beat=tpb)
    tr = mido.MidiTrack()
    mid.tracks.append(tr)
    last = 0
    for tick, msg in sorted(events, key=lambda e: e[0]):
        msg.time = tick - last
        last = tick
        tr.append(msg)
    mid.save(path)


def test_midi_import_tempo_changes_become_inline_markers():
    import mido
    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "t.mid")
        ev = [(0, mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(100))),
              (1920, mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(140))),
              (3840, mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(140)))]  # duplicato: ignorato
        for i in range(8):
            ev.append((i * 480, mido.Message("note_on", note=60, velocity=80, time=0)))
            ev.append((i * 480 + 400, mido.Message("note_off", note=60, velocity=0, time=0)))
        _write_midi(path, ev)
        project = import_midi_file(path)
        assert project.tempo_bpm == 100
        text = project.tracks[0].text
        assert text.count("tempo=") == 1 and "tempo=140" in text
        # il marcatore cade alla battuta 2 (beat 4): parsando il testo lo ritroviamo li'
        markers = [e for e in project.tracks[0].parsed_events({}) if e.kind == "tempo_marker"]
        assert [(m.start, m.bpm) for m in markers] == [(4.0, 140)]
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_tempo_markers_only_in_one_track_with_least_drift():
    import mido
    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "t2.mid")
        ev = [(0, mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(90))),
              (480, mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(120)))]
        # canale 0: una nota lunga che "copre" il cambio di tempo (beat 1);
        # canale 1: note brevi, il marcatore cade esattamente sul suo slot.
        ev.append((0, mido.Message("note_on", channel=0, note=60, velocity=80)))
        ev.append((1920, mido.Message("note_off", channel=0, note=60, velocity=0)))
        for i in range(4):
            ev.append((i * 480, mido.Message("note_on", channel=1, note=64, velocity=80)))
            ev.append((i * 480 + 240, mido.Message("note_off", channel=1, note=64, velocity=0)))
        _write_midi(path, ev)
        project = import_midi_file(path)
        assert len(project.tracks) == 2
        texts = [t.text for t in project.tracks]
        assert sum("tempo=" in t for t in texts) == 1
        carrier = next(t for t in project.tracks if "tempo=" in t.text)
        markers = [e for e in carrier.parsed_events({}) if e.kind == "tempo_marker"]
        assert [(m.start, m.bpm) for m in markers] == [(1.0, 120)]
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_time_signature_and_changes():
    import mido
    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "m.mid")
        # 2 battute di 3/4 (6 beat = 2880 tick), poi 4/4
        ev = [(0, mido.MetaMessage("time_signature", numerator=3, denominator=4)),
              (2880, mido.MetaMessage("time_signature", numerator=4, denominator=4)),
              (0, mido.Message("note_on", note=60, velocity=80)),
              (480, mido.Message("note_off", note=60, velocity=0))]
        _write_midi(path, ev)
        project = import_midi_file(path)
        assert project.time_sig == "3/4"
        assert project.metrica_changes == [(1, "3/4"), (3, "4/4")]

        # metrica costante: solo time_sig, nessuna lista di cambi
        path2 = os.path.join(tmpdir, "m2.mid")
        _write_midi(path2, [(0, mido.MetaMessage("time_signature", numerator=6, denominator=8)),
                            (0, mido.Message("note_on", note=60, velocity=80)),
                            (480, mido.Message("note_off", note=60, velocity=0))])
        p2 = import_midi_file(path2)
        assert p2.time_sig == "6/8" and p2.metrica_changes == []
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_sustain_pedal_becomes_son_soff():
    import mido
    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "s.mid")
        ev = [(0, mido.Message("control_change", control=64, value=127)),
              (960, mido.Message("control_change", control=64, value=0)),
              (960, mido.Message("control_change", control=64, value=0)),   # ripetuto: ignorato
              (1440, mido.Message("control_change", control=64, value=100))]  # mai rilasciato
        for i in range(4):
            ev.append((i * 480, mido.Message("note_on", note=60 + i, velocity=80)))
            ev.append((i * 480 + 400, mido.Message("note_off", note=60 + i, velocity=0)))
        _write_midi(path, ev)
        project = import_midi_file(path)
        tokens = project.tracks[0].text.split()
        assert [t for t in tokens if t in ("SON", "SOFF")] == ["SON", "SOFF", "SON", "SOFF"]
        assert tokens[-1] == "SOFF"  # pedale ancora premuto a fine canale: chiuso
        events = project.tracks[0].parsed_events({})
        assert [e.name for e in events if e.kind == "sustain"] == ["on", "off", "on", "off"]
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_sustain_roundtrip_through_export():
    tmpdir = tempfile.mkdtemp()
    try:
        p = Project(tempo_bpm=100, time_sig="3/4")
        p.add_track("Piano", "Piano", "8: SON c d e f SOFF g a b c")
        path = os.path.join(tmpdir, "rt.mid")
        export_midi = __import__("core.midi_export", fromlist=["export_project_to_midi"])
        export_midi.export_project_to_midi(p, path)
        back = import_midi_file(path)
        assert back.time_sig == "3/4"
        assert back.tracks[0].text.count("SON") == 1 and back.tracks[0].text.count("SOFF") == 1
    finally:
        shutil.rmtree(tmpdir)


def _channel_from_notes(notes_beats, tpb=480, program=0):
    """notes_beats: [(start_beat, dur_beats, midi_note), ...] -> ChannelData."""
    ch = midi_convert.ChannelData(0)
    ch.program = program
    ch.notes = [(round(s * tpb), round((s + d) * tpb), n, 80) for s, d, n in notes_beats]
    return ch


def test_midi_import_triplets_use_8t_grid():
    tokens = midi_convert.channel_to_tokens(
        _channel_from_notes([(0, 1 / 3, 60), (1 / 3, 1 / 3, 62), (2 / 3, 1 / 3, 64), (1, 1, 65)]), 480)
    assert tokens[:2] == ["16:", "8T:"] or tokens[0] == "16:" and "8T:" in tokens
    assert "8T:" in tokens
    # parsando i token gli attacchi cadono esattamente sui terzi di beat
    events = [e for e in parse_track_text(" ".join(tokens), {}, default_octave=4) if e.kind == "note"]
    assert [round(e.start, 3) for e in events] == [0.0, 0.333, 0.667, 1.0]


def test_midi_import_binary_stays_on_sixteenths():
    tokens = midi_convert.channel_to_tokens(
        _channel_from_notes([(0, 0.25, 60), (0.25, 0.25, 62), (0.5, 0.5, 64), (1, 1, 65)]), 480)
    assert not any(t.endswith(":") and t != "16:" for t in tokens)
    # anche con un po' di imprecisione umana (< tolleranza) resta binario
    ch = _channel_from_notes([(0.01, 0.25, 60), (0.26, 0.25, 62), (0.49, 0.5, 64), (1.02, 1, 65)])
    assert not any(t.endswith(":") and t != "16:" for t in midi_convert.channel_to_tokens(ch, 480))


def test_midi_import_swing_shuffle_becomes_triplet_grid():
    # ottavi in shuffle 2:1: attacchi a 0 e 2/3 di ogni beat
    notes = [(b + off, 1 / 3 if off == 0 else 1 / 3, 60 + b) for b in range(4) for off in (0, 2 / 3)]
    tokens = midi_convert.channel_to_tokens(_channel_from_notes(notes), 480)
    assert tokens.count("8T:") == 1  # il comando resta attivo, non si ripete per ogni beat


def test_midi_import_mixed_binary_triplet_keeps_absolute_timing():
    # beat 0: sedicesimi, beat 1: terzine, beat 2: sedicesimi, con una nota
    # lunga che attraversa il cambio di griglia (deve chiudersi sul confine)
    notes = [(0, .25, 60), (.25, .25, 61), (.5, .25, 62), (.75, .25, 63),
             (1, 1 / 3, 64), (1 + 1 / 3, 1 / 3, 65), (1 + 2 / 3, 1 / 3, 66),
             (2, .25, 67), (2.25, .25, 68), (2.5, .5, 69),
             (3, 1.25, 70), (4.25, 0.75, 71), (5, 1, 72)]
    tokens = midi_convert.channel_to_tokens(_channel_from_notes(notes), 480)
    events = [e for e in parse_track_text(" ".join(tokens), {}, default_octave=4) if e.kind == "note"]
    starts = [round(e.start, 3) for e in events]
    expected = [round(s, 3) for s, _, _ in notes]
    assert starts == expected


def test_midi_import_triplet_roundtrip_through_export():
    tmpdir = tempfile.mkdtemp()
    try:
        p = Project()
        p.add_track("Piano", "Piano", "4: c*4 8T: d e f 16: g a b c")
        path = os.path.join(tmpdir, "tr.mid")
        export_project_to_midi(p, path)
        back = import_midi_file(path)
        text = back.tracks[0].text
        assert "8T:" in text
        orig = [round(e.start, 3) for e in p.tracks[0].parsed_events({}) if e.kind == "note"]
        got = [round(e.start, 3) for e in back.tracks[0].parsed_events({}) if e.kind == "note"]
        assert got == orig
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_sloppy_playing_is_not_read_as_quintuplets_or_septuplets():
    import random
    rnd = random.Random(7)
    notes = [(b + rnd.uniform(0, 0.97), 0.2, 60) for b in range(60)
             for _ in range(1)]
    notes.sort()
    tokens = midi_convert.channel_to_tokens(_channel_from_notes(notes), 480)
    assert "16Q:" not in tokens and "16S:" not in tokens



def test_midi_import_chord_velocity_is_mean_of_notes():
    ch = midi_convert.ChannelData(0)
    ch.notes = [(0, 480, 60, 100), (0, 480, 64, 60), (0, 480, 67, 80), (480, 960, 62, 90)]
    tokens = midi_convert.channel_to_tokens(ch, 480)
    assert "80@" in tokens and "90@" in tokens
    # indipendente dall'ordine in cui le note del gruppo sono elencate
    ch2 = midi_convert.ChannelData(0)
    ch2.notes = list(reversed(ch.notes))
    assert midi_convert.channel_to_tokens(ch2, 480) == tokens
    # velocity uguali: invariata
    ch3 = midi_convert.ChannelData(0)
    ch3.notes = [(0, 480, 60, 77), (0, 480, 64, 77)]
    assert "77@" in midi_convert.channel_to_tokens(ch3, 480)


def test_midi_import_expression_crescendo_becomes_velocity_steps():
    import mido
    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "cresc.mid")
        ev = []
        for i in range(8):
            ev.append((i * 480, mido.Message("control_change", control=11, value=40 + i * 12)))
            ev.append((i * 480, mido.Message("note_on", note=60, velocity=100)))
            ev.append((i * 480 + 400, mido.Message("note_off", note=60, velocity=0)))
        _write_midi(path, ev)
        project = import_midi_file(path)
        vels = [e.velocity for e in project.tracks[0].parsed_events({}) if e.kind == "note"]
        assert len(vels) == 8
        assert vels == sorted(vels) and vels[0] < vels[-1] * 0.5  # crescendo
        assert vels[-1] == 100  # il punto piu' alto del canale mantiene la velocity originale
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_constant_channel_volume_does_not_change_velocity():
    import mido
    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "const.mid")
        ev = [(0, mido.Message("control_change", control=7, value=100))]
        for i in range(4):
            ev.append((i * 480, mido.Message("note_on", note=60, velocity=90)))
            ev.append((i * 480 + 400, mido.Message("note_off", note=60, velocity=0)))
        # una piccola oscillazione (sotto la soglia di profondita') e' ignorata
        ev.append((960, mido.Message("control_change", control=11, value=120)))
        _write_midi(path, ev)
        vels = [e.velocity for e in import_midi_file(path).tracks[0].parsed_events({}) if e.kind == "note"]
        assert vels == [90, 90, 90, 90]
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_articulations_from_note_length():
    tpb = 480
    def run(ratio, ioi_beats=0.5, n=4):
        ch = midi_convert.ChannelData(0)
        step = int(ioi_beats * tpb)
        ch.notes = [(i * step, i * step + int(step * ratio), 60 + i, 80) for i in range(n)]
        return midi_convert.channel_to_tokens(ch, tpb)
    assert run(0.5)[1:].count("2c*4!") + " ".join(run(0.5)).count("!") >= 3       # staccato
    assert " ".join(run(0.15)).count("x") >= 3                                    # mute
    assert " ".join(run(1.15)).count("_") >= 3                                    # legato
    for normal in (0.85, 1.0):
        assert not any(m in " ".join(run(normal)) for m in ("!", "_")) and "x" not in " ".join(run(normal))
    # nota corta seguita da una lunga pausa: NON e' un'articolazione
    ch = midi_convert.ChannelData(0)
    ch.notes = [(0, 60, 60, 80), (4 * tpb, 4 * tpb + 60, 62, 80)]
    assert not any(m in " ".join(midi_convert.channel_to_tokens(ch, tpb)) for m in ("!", "_", " x", "x "))


def test_midi_import_articulation_roundtrip_through_export():
    tmpdir = tempfile.mkdtemp()
    try:
        p = Project()
        p.add_track("Piano", "Piano", "8: c*4! d*4! e*4! f*4! g*4 a*4 b*4 c*5")
        path = os.path.join(tmpdir, "art.mid")
        export_project_to_midi(p, path)
        back = import_midi_file(path).tracks[0]
        assert back.text.count("!") == 4
        events = [e for e in back.parsed_events({}) if e.kind == "note"]
        assert [round(e.start, 3) for e in events] == [round(e.start, 3) for e in p.tracks[0].parsed_events({}) if e.kind == "note"]
        assert [e.articulation for e in events[:4]] == ["staccato"] * 4
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_ignores_small_tempo_jitter():
    import mido
    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "jitter.mid")
        ev = [(0, mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(145))),
              (480, mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(146))),
              (960, mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(145))),
              (1440, mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(147))),
              (1920, mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(160)))]
        for i in range(8):
            ev.append((i * 480, mido.Message("note_on", note=60, velocity=80)))
            ev.append((i * 480 + 400, mido.Message("note_off", note=60, velocity=0)))
        _write_midi(path, ev)
        tempo_changes, _ = midi_convert.detect_tempo_and_meter(path)
        assert [bpm for _, bpm in tempo_changes] == [160]   # 146/147 sono rumore, 160 e' un cambio vero
    finally:
        shutil.rmtree(tmpdir)


def test_beat_grid_merges_near_simultaneous_onsets():
    # kick e ride con qualche tick di scarto: 3 punti ritmici, non 7 attacchi
    fracs = [0.0, 0.0, 0.01, 0.143, 0.143, 0.286, 0.286]
    assert midi_convert._choose_beat_grid(fracs) not in (5, 7)


def test_beat_grid_sixteenth_triplet_needs_mixed_binary_and_ternary_hits():
    # rullante dritto a meta' beat (0.5, spiegato dai sedicesimi) insieme a
    # cassa/hi-hat in terzina (1/3 e 2/3, spiegati dalla terzina): nessuna
    # delle due griglie da sola spiega tutti gli attacchi, solo la sestina
    # (16T) li spiega tutti - vedi il commento in _choose_beat_grid.
    fracs = [0.0, 1 / 3, 0.5, 2 / 3]
    assert midi_convert._choose_beat_grid(fracs) == 6


def test_dominant_swing_grid_resolves_a_beat_spoiled_by_one_ghost_note():
    # Uno shuffle a terzine (0, 2/3) su piu' battute e' inequivocabile: deve
    # diventare la griglia dominante del canale.
    onset_fracs = {b: [0.0, 2 / 3] for b in range(6)}
    assert midi_convert._dominant_swing_grid(onset_fracs) == 3
    # Una battuta con un ghost note leggermente anticipato (0.62 invece di
    # 2/3) non spiega ne' i sedicesimi ne' la terzina da sola (fallirebbe
    # a 4 di default), ma il resto dei suoi attacchi e' compatibile con la
    # terzina dominante del canale: deve seguirla, non spezzare lo shuffle.
    spoiled = [0.0, 0.62, 2 / 3]
    assert midi_convert._choose_beat_grid(spoiled) == 4  # da sola, ambigua
    assert midi_convert._choose_beat_grid(spoiled, dominant_grid=3) == 3

    # Ma un canale senza vero shuffle (poche battute non binarie, nessuna
    # maggioranza) non deve forzare le battute ambigue a terzine.
    mostly_straight = {b: [0.0, 0.5] for b in range(10)}
    mostly_straight[10] = [0.0, 2 / 3]
    assert midi_convert._dominant_swing_grid(mostly_straight) == 4


def _note_events(tokens):
    return [e for e in parse_track_text(" ".join(tokens), {}, default_octave=4)
            if e.kind in ("note", "block", "chord")]


def _count_pitches(tokens):
    n = 0
    for e in _note_events(tokens):
        n += len(e.items) if e.kind == "block" else 1
    return n


def test_overlap_held_note_under_melody_goes_to_second_voice():
    # nota tenuta (4 beat) sotto una melodia di 8 ottavi: prima le note della
    # melodia dopo il primo attacco andavano perse
    notes = [(0, 4, 40)] + [(i * 0.5, 0.5, 60 + i) for i in range(8)]
    ch = _channel_from_notes(notes)
    voices = midi_convert.channel_to_voices(ch, 480)
    assert len(voices) == 2
    assert sum(_count_pitches(v) for v in voices) == 9   # nessuna nota persa
    long_voice = next(v for v in voices if any(e.duration >= 4 for e in _note_events(v)))
    held = [e for e in _note_events(long_voice) if e.duration >= 4]
    assert len(held) == 1 and held[0].start == 0.0 and held[0].duration == 4.0
    melody_voice = next(v for v in voices if v is not long_voice)
    assert [round(e.start, 3) for e in _note_events(melody_voice)] == [i * 0.5 for i in range(8)]


def test_overlap_single_voice_mode_never_loses_notes():
    notes = [(0, 4, 40)] + [(i * 0.5, 0.5, 60 + i) for i in range(8)]
    tokens = midi_convert.channel_to_tokens(_channel_from_notes(notes), 480)
    assert _count_pitches(tokens) == 9   # tutte le note (la tenuta e' accorciata, non persa)
    starts = [round(e.start, 3) for e in _note_events(tokens)]
    assert starts == [i * 0.5 for i in range(8)]


def test_overlap_tiny_legato_overlap_does_not_open_a_voice():
    # ogni nota si sovrappone di poco alla successiva (entro un sedicesimo)
    notes = [(i * 0.5, 0.5 + 0.2, 60 + i) for i in range(8)]
    voices = midi_convert.channel_to_voices(_channel_from_notes(notes), 480)
    assert len(voices) == 1 and _count_pitches(voices[0]) == 8


def test_overlap_chord_with_slightly_different_ends_stays_one_block():
    notes = [(0, 1.0, 60), (0, 0.9, 64), (0, 1.05, 67), (1, 1.0, 62)]
    voices = midi_convert.channel_to_voices(_channel_from_notes(notes), 480)
    assert len(voices) == 1
    assert _count_pitches(voices[0]) == 4


def test_overlap_drums_never_split_into_voices():
    ch = midi_convert.ChannelData(9)
    ch.notes = [(0, 1920, 36, 90), (480, 960, 42, 90), (960, 1440, 38, 90)]
    voices = midi_convert.channel_to_voices(ch, 480)
    assert len(voices) == 1


def test_overlap_import_puts_the_second_voice_in_a_voice_block():
    import mido
    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "ov.mid")
        ev = [(0, mido.Message("note_on", note=40, velocity=80)),
              (1920, mido.Message("note_off", note=40, velocity=0))]
        for i in range(8):
            ev.append((i * 240, mido.Message("note_on", note=60 + i, velocity=80)))
            ev.append((i * 240 + 200, mido.Message("note_off", note=60 + i, velocity=0)))
        _write_midi(path, ev)
        project = import_midi_file(path)
        assert len(project.tracks) == 1                 # una traccia, con un blocco { ; }
        text = project.tracks[0].text
        assert text.count("{") == 1 and ";" in text
        events = parse_track_text(text, {})
        assert len([e for e in events if e.kind == "note"]) == 9
        assert {e.voice for e in events if e.kind == "note"} == {1, 2}
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_very_low_notes():
    """Le note MIDI 0-11 (ottava -1) non sono esprimibili nella grammatica:
    vengono portate un'ottava sopra invece di produrre 'c*-1'."""
    import mido
    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "low.mid")
        ev = []
        for i, n in enumerate((0, 7, 11)):
            ev.append((i * 480, mido.Message("note_on", note=n, velocity=80)))
            ev.append((i * 480 + 400, mido.Message("note_off", note=n, velocity=0)))
        _write_midi(path, ev)
        project = import_midi_file(path)
        text = " ".join(t.text for t in project.tracks)
        assert "*-1" not in text
        assert "c*0" in text and "g*0" in text and "b*0" in text
    finally:
        shutil.rmtree(tmpdir)


# ---- Export MIDI: selezione del drum kit (Bank Select + Program Change) ----

def test_export_percussion_sends_bank_select_and_program_change_for_drum_kit():
    """Il canale percussioni deve ricevere, prima di qualsiasi nota, il Bank
    Select GM2 (CC0=120) seguito dal Program Change che seleziona il kit
    scelto dall'utente (qui 32 = Jazz Kit) - non solo per gli strumenti
    melodici, come accadeva prima di questo fix."""
    import mido
    _reset_custom_instruments()
    add_custom_instrument(InstrumentProfile(
        name="JazzDrums", gm_program=32, is_percussion=True,
        polyphonic=True, voicing_style="none",
    ))
    tmpdir = tempfile.mkdtemp()
    try:
        p = Project(name="Test")
        p.add_track("Drums1", "JazzDrums", "16: kick snare kick snare")
        path = os.path.join(tmpdir, "jazz_kit.mid")
        export_project_to_midi(p, path)

        mid = mido.MidiFile(path)
        events = [msg for track in mid.tracks for msg in track if msg.type in
                  ("control_change", "program_change", "note_on") and getattr(msg, "channel", None) == 9]
        # prima di qualsiasi nota: Bank Select (CC0=120) poi Program Change(32)
        first_note_idx = next(i for i, m in enumerate(events) if m.type == "note_on")
        before_note = events[:first_note_idx]
        bank_select = [m for m in before_note if m.type == "control_change" and m.control == 0]
        program_change = [m for m in before_note if m.type == "program_change"]
        assert len(bank_select) == 1 and bank_select[0].value == 120
        assert len(program_change) == 1 and program_change[0].program == 32
        assert before_note.index(bank_select[0]) < before_note.index(program_change[0])
    finally:
        shutil.rmtree(tmpdir)
        remove_custom_instrument("JazzDrums")


def test_drum_kit_override_lets_you_change_a_predefined_percussion_instrument():
    """A differenza degli altri campi, il kit percussioni si puo' cambiare
    anche per uno strumento predefinito come 'Drums' (Gestione strumenti):
    l'override (core.settings.set/get/clear_drum_kit_override) e' applicato
    sopra al profilo, non richiede crearne uno nuovo, e si riflette sia su
    get_instrument() sia sull'export MIDI."""
    from core import settings as app_settings
    import mido
    assert get_instrument("Drums").gm_program == 0  # Standard Kit di base
    try:
        app_settings.set_drum_kit_override("Drums", 32)  # Jazz Kit
        assert get_instrument("Drums").gm_program == 32

        tmpdir = tempfile.mkdtemp()
        try:
            p = Project(name="Test")
            p.add_track("D1", "Drums", "16: kick snare kick snare")
            path = os.path.join(tmpdir, "drums_override.mid")
            export_project_to_midi(p, path)
            mid = mido.MidiFile(path)
            programs = [m.program for track in mid.tracks for m in track
                        if m.type == "program_change" and getattr(m, "channel", None) == 9]
            assert programs == [32]
        finally:
            shutil.rmtree(tmpdir)

        app_settings.clear_drum_kit_override("Drums")
        assert get_instrument("Drums").gm_program == 0
    finally:
        app_settings.clear_drum_kit_override("Drums")  # non lasciare residui per gli altri test


def test_instrument_list_groups_similar_instruments_together():
    """list_instrument_names() deve tenere vicini strumenti simili (fiati
    con fiati, corde con corde, ...) invece di limitarsi all'ordine di
    creazione, anche mescolando predefiniti e personalizzati."""
    from core.instruments import list_instrument_names
    _reset_custom_instruments()
    add_custom_instrument(InstrumentProfile(name="Sax", gm_program=66, default_octave=4,
                                             range_low=49, range_high=82, polyphonic=False,
                                             voicing_style="monophonic"))     # Ance (tenor sax)
    add_custom_instrument(InstrumentProfile(name="Cello", gm_program=42, default_octave=3,
                                             range_low=36, range_high=76, polyphonic=False,
                                             voicing_style="monophonic"))     # Archi
    add_custom_instrument(InstrumentProfile(name="Congas", gm_program=0, is_percussion=True,
                                             polyphonic=True, voicing_style="none"))
    try:
        names = list_instrument_names()
        # Archi (Cello) precede Ottoni (Trumpet) che precede Ance (Sax) in
        # GM_FAMILIES; le percussioni (Congas, Drums) restano in fondo,
        # in ordine alfabetico tra loro.
        assert names == ["Piano", "Guitar", "Bass", "Cello", "Trumpet", "Sax", "Congas", "Drums"]
    finally:
        remove_custom_instrument("Sax")
        remove_custom_instrument("Cello")
        remove_custom_instrument("Congas")


def test_midi_import_reads_channel_volume_and_pan_into_track_mixer():
    """Il volume (CC7) e il pan (CC10) di base di un canale (tipicamente
    impostati una sola volta a inizio brano dall'arrangiamento originale)
    devono diventare il volume/pan della traccia importata, non restare ai
    valori predefiniti (100/centro): altrimenti il bilanciamento del mix
    (uno strumento piu' in secondo piano, uno spostato a sinistra/destra...)
    va perso, e la riproduzione in SoundText suona sbilanciata rispetto
    all'originale (rispetto, ad es., a un lettore MIDI generico come VLC,
    che questi CC li applica sempre)."""
    import mido
    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "volpan.mid")
        ev = [
            (0, mido.Message("program_change", program=0, channel=0)),
            (0, mido.Message("control_change", control=7, value=90, channel=0)),   # volume
            (0, mido.Message("control_change", control=10, value=30, channel=0)),  # pan a sinistra
            (0, mido.Message("note_on", note=60, velocity=100, channel=0)),
            (480, mido.Message("note_off", note=60, velocity=0, channel=0)),
            # canale senza CC7/CC10 esplicito: deve restare ai default
            (0, mido.Message("program_change", program=0, channel=1)),
            (0, mido.Message("note_on", note=64, velocity=100, channel=1)),
            (480, mido.Message("note_off", note=64, velocity=0, channel=1)),
        ]
        _write_midi(path, ev)
        project = import_midi_file(path)
        # entrambe le tracce sono Piano (program 0): distinguile per volume/pan
        loud = [t for t in project.tracks if t.volume == 90]
        default = [t for t in project.tracks if t.volume == 100]
        assert len(loud) == 1 and loud[0].pan == 30
        assert len(default) == 1 and default[0].pan == 64
    finally:
        shutil.rmtree(tmpdir)


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
