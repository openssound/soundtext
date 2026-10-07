import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import re
"""
Test per le funzionalita' aggiunte al SoundText Language / ST-Syntax:
gruppi di ripetizione N(...), modificatori nota (staccato/mute/legato),
slide, pedale sustain SON/SOFF, marcatori dinamici pppp@..ffff@, rampe di
tempo (tempo=N >> <<) e di dinamica (>> << tra due @), cambi di tempo/metrica
indicizzati per battuta.

Esecuzione: python3 tests/test_language_extensions.py
"""

import os
import sys
import shutil
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.notation import parse_track_text, validate_track_text, tokenize, NotationError
from core.model import Project
from core.project_io import (
    parse_project_text, project_to_text, save_project_file, load_project_file,
    compute_bar_beat_offsets,
)
from core.midi_export import export_project_to_midi
from core import midi_convert


# ---------------------------------------------------------------------- ripetizioni

def _overdriven_guitar():
    """Nome di uno strumento con il programma GM 29 (Overdriven Guitar), che non
    e' fra i predefiniti: lo registra (nella configurazione isolata dei test)
    invece di presupporre che l'utente l'abbia gia' creato importando un MIDI."""
    from core.instruments import resolve_or_create_instrument_by_program
    return resolve_or_create_instrument_by_program(29, False)


def test_repeat_group_basic():
    ev = [e for e in parse_track_text("4(c d e f)", {}) if e.kind != "repeat"]
    assert len(ev) == 16
    letters = [e.letter for e in ev]
    assert letters == ["c", "d", "e", "f"] * 4


def test_repeat_group_with_durations_matches_user_example():
    # esempio dell'utente: 4(2C7 2e c d 2A7) ripete 4 volte la sequenza
    ok, msg = validate_track_text("4(2C7 2e c d 2A7)", {})
    assert ok, msg
    ev = [e for e in parse_track_text("4(2C7 2e c d 2A7)", {}) if e.kind != "repeat"]
    # ogni ripetizione produce: 1 accordo + 4 note = 5 eventi -> 4 ripetizioni = 20
    assert len(ev) == 20
    kinds_per_rep = [e.kind for e in ev[:5]]
    assert kinds_per_rep == ["chord", "note", "note", "note", "chord"]


def test_repeat_group_nested():
    ev = [e for e in parse_track_text("2(c 2(d e))", {}) if e.kind != "repeat"]
    # esterno x2: [c, (d e)x2] = c d e d e -> x2 = 10 eventi
    assert len(ev) == 10


def test_repeat_group_preserves_musical_timing():
    flat = parse_track_text("c d e f c d e f c d e f c d e f", {})
    grouped = [e for e in parse_track_text("4(c d e f)", {}) if e.kind != "repeat"]
    key = lambda e: (e.letter, e.start, e.duration)
    assert [key(e) for e in flat] == [key(e) for e in grouped]


# ---------------------------------------------------------------------- tuplet (terzine/quintine/settimine)

def test_ternary_grid_unaffected_by_new_tuplet_letters():
    """8T: (terzina di ottavi) resta invariata: 3 note nello spazio di 2
    ottavi normali, cioe' un quarto."""
    ev = parse_track_text("8T: c d e", {})
    assert len(ev) == 3
    assert all(abs(e.duration - (0.5 * 2 / 3)) < 1e-9 for e in ev)
    assert abs(sum(e.duration for e in ev) - 1.0) < 1e-9


def test_quintuplet_grid_fills_expected_duration():
    """16Q: (quintina di sedicesimi): 5 note nello spazio di 4 sedicesimi
    normali, cioe' un quarto - stessa convenzione della terzina (3:2),
    generalizzata al rapporto 5:4."""
    ev = parse_track_text("16Q: c d e f g", {})
    assert len(ev) == 5
    assert all(abs(e.duration - (0.25 * 4 / 5)) < 1e-9 for e in ev)
    assert abs(sum(e.duration for e in ev) - 1.0) < 1e-9


def test_septuplet_grid_fills_expected_duration():
    """8S: (settimina di ottavi): 7 note nello spazio di 4 ottavi normali,
    cioe' due quarti (rapporto 7:4)."""
    ev = parse_track_text("8S: c d e f g a b", {})
    assert len(ev) == 7
    assert all(abs(e.duration - (0.5 * 4 / 7)) < 1e-9 for e in ev)
    assert abs(sum(e.duration for e in ev) - 2.0) < 1e-9


@pytest.mark.parametrize("grid,per_beat", [("8T:", 3), ("16Q:", 5), ("8S:", 7 / 2)])
def test_tuplet_onsets_land_exactly_on_whole_beats(grid, per_beat):
    """Dopo molte note a tuplet l'attacco successivo cade ESATTAMENTE sul
    beat intero: con la griglia in virgola mobile l'accumulo di 1/3, 1/5...
    dava 7.9999999999999964 invece di 8.0, e chi calcola la battuta con
    floor(start / 4) metteva la nota in quella precedente."""
    n = round(8 * per_beat)
    ev = parse_track_text(f"{grid} " + "c*4 " * n + "d*4", {})
    assert ev[-1].start == 8.0
    assert all(isinstance(e.start, float) and isinstance(e.duration, float) for e in ev)


def test_tuplet_grid_can_be_reverted_to_binary():
    ev = parse_track_text("16Q: c d e f g 16: a", {})
    assert len(ev) == 6
    assert abs(ev[-1].duration - 0.25) < 1e-9  # torna alla durata binaria normale (sedicesimo)


def test_quintuplet_and_septuplet_export_correct_note_count():
    tmpdir = tempfile.mkdtemp()
    try:
        import mido
        p = Project(name="Test")
        p.add_track("Piano1", "Piano", "16Q: c*4 d*4 e*4 f*4 g*4  8S: c*4 d*4 e*4 f*4 g*4 a*4 b*4")
        path = os.path.join(tmpdir, "tuplet.mid")
        export_project_to_midi(p, path)
        mid = mido.MidiFile(path, clip=True)
        note_ons = [m for t in mid.tracks for m in t if m.type == "note_on" and m.velocity > 0]
        assert len(note_ons) == 12  # 5 (quintina) + 7 (settimina)
    finally:
        shutil.rmtree(tmpdir)


def test_invalid_tuplet_letter_is_not_recognized_as_grid():
    """Una lettera non riconosciuta (es. 'X') dopo il numero non deve
    essere confusa con un comando griglia valido: RE_GRID non deve
    accettare lettere fuori da T/Q/S."""
    ok, msg = validate_track_text("16X: c", {})
    assert not ok


# ---------------------------------------------------------------------- modificatori nota

def test_staccato_shortens_audible_duration_not_timeline():
    tmpdir = tempfile.mkdtemp()
    try:
        p = Project(name="Test")
        p.add_track("Piano1", "Piano", "16: c*4! d*4")
        path = os.path.join(tmpdir, "stacc.mid")
        export_project_to_midi(p, path)
        _, tpb, channels = midi_convert.analyze_midi(path)
        notes = sorted(list(channels.values())[0].notes, key=lambda n: n[0])
        c_start, c_end, _, _ = notes[0]
        d_start, d_end, _, _ = notes[1]
        # d*4 deve comunque iniziare all'inizio del suo slot (1/16 dopo c),
        # non ritardato dall'accorciamento di c: la timeline resta intatta
        expected_d_start = round(tpb * 0.25)
        assert d_start == expected_d_start
        # la durata udibile di c deve essere circa il 50% dello slot nominale
        nominal = expected_d_start
        assert 0 < (c_end - c_start) < nominal
    finally:
        shutil.rmtree(tmpdir)


def test_mute_is_shorter_than_staccato():
    tmpdir = tempfile.mkdtemp()
    try:
        p1 = Project(name="T1")
        p1.add_track("Piano1", "Piano", "16: c*4!")
        path1 = os.path.join(tmpdir, "stacc.mid")
        export_project_to_midi(p1, path1)
        _, _, ch1 = midi_convert.analyze_midi(path1)
        stacc_dur = ch1[list(ch1.keys())[0]].notes[0]
        stacc_len = stacc_dur[1] - stacc_dur[0]

        p2 = Project(name="T2")
        p2.add_track("Piano1", "Piano", "16: c*4x")
        path2 = os.path.join(tmpdir, "mute.mid")
        export_project_to_midi(p2, path2)
        _, _, ch2 = midi_convert.analyze_midi(path2)
        mute_dur = ch2[list(ch2.keys())[0]].notes[0]
        mute_len = mute_dur[1] - mute_dur[0]

        assert mute_len < stacc_len
    finally:
        shutil.rmtree(tmpdir)


def test_chord_staccato_shortens_all_voiced_notes():
    """Estensione: '!' e' valido anche sugli accordi e va applicato a TUTTE
    le note generate dal voicing, non solo alla fondamentale."""
    tmpdir = tempfile.mkdtemp()
    try:
        p = Project(name="Test")
        p.add_track("Piano1", "Piano", "16: Cmaj7!")
        path = os.path.join(tmpdir, "chord_stacc.mid")
        export_project_to_midi(p, path)
        _, tpb, channels = midi_convert.analyze_midi(path)
        notes = list(channels.values())[0].notes
        nominal = round(tpb * 0.25)
        assert len(notes) >= 3  # accordo: piu' di una nota
        for start, end, _pitch, _vel in notes:
            assert 0 < (end - start) < nominal
    finally:
        shutil.rmtree(tmpdir)


def test_chord_voicing_and_staccato_combine():
    """'.stile' (voicing) e '!' (staccato) devono poter comparire insieme
    sullo stesso accordo, es. Cmaj7.drop2!"""
    ok, msg = validate_track_text("Cmaj7.drop2!", {})
    assert ok, msg


def test_legato_extends_beyond_slot():
    tmpdir = tempfile.mkdtemp()
    try:
        p = Project(name="Test")
        p.add_track("Piano1", "Piano", "16: c*4_")
        path = os.path.join(tmpdir, "legato.mid")
        export_project_to_midi(p, path)
        _, tpb, channels = midi_convert.analyze_midi(path)
        start, end, _, _ = list(channels.values())[0].notes[0]
        nominal = round(tpb * 0.25)
        assert (end - start) > nominal  # legato = piu' lunga dello slot nominale
    finally:
        shutil.rmtree(tmpdir)


def test_note_modifiers_validate_correctly():
    for tok in ["c!", "cx", "c_", "c*4!", "c*4x", "c*4_"]:
        ok, msg = validate_track_text(tok, {})
        assert ok, f"'{tok}' -> {msg}"


# ---------------------------------------------------------------------- slide

def test_slide_produces_slide_event():
    ev = parse_track_text("c*4>d*4", {})
    assert len(ev) == 1
    assert ev[0].kind == "slide"
    assert ev[0].letter == "c" and ev[0].octave == 4
    assert ev[0].slide_points == [("d", 4)]


def test_slide_chain_produces_multiple_slide_points():
    """Bend-and-release: c*4>d*4>c*4 sale a d*4 e poi rilascia a c*4, tutto
    entro la stessa unita' di griglia (un solo Event, non due)."""
    ev = parse_track_text("c*4>d*4>c*4", {})
    assert len(ev) == 1
    assert ev[0].kind == "slide"
    assert ev[0].letter == "c" and ev[0].octave == 4
    assert ev[0].slide_points == [("d", 4), ("c", 4)]


def test_slide_one_rule_for_every_chain():
    """Una regola sola: ogni rampa dura il moltiplicatore della tappa da cui
    parte (1 se manca), l'ultima tappa resta ferma per il suo (0 se manca).
    c*4>d*4 dura quindi un'unita' come una nota."""
    ev = parse_track_text("2f*4>f#*4", {})[0]
    assert ev.duration == 2.0
    assert ev.slide_segment_durations == [2.0, 0.0]

    ev = parse_track_text("c*4>d*4>c*4", {})[0]       # bend-and-release: sale in 1, scende in 1
    assert ev.duration == 2.0
    assert ev.slide_segment_durations == [1.0, 1.0, 0.0]

    ev = parse_track_text("6c*4>d*4>c*4", {})[0]
    assert ev.slide_segment_durations == [6.0, 1.0, 0.0]

    with pytest.raises(NotationError):
        parse_track_text("0c*4>d*4", {})               # durata nulla


def test_slide_per_point_duration_quick_bend_then_hold():
    """Un moltiplicatore esplicito su una tappa OLTRE la prima attiva la
    2c*4>3d*4 sale a d*4 in 2 unita' e vi resta ferma per altre 3 (bend
    rapido poi tenuto), diverso da 5c*4>d*4 (rampa lineare per tutte le 5
    unita')."""
    ev = parse_track_text("2c*4>3d*4", {})[0]
    assert ev.duration == 5.0
    assert ev.slide_segment_durations == [2.0, 3.0]

    ev = parse_track_text("5c*4>d*4", {})[0]
    assert ev.duration == 5.0
    assert ev.slide_segment_durations == [5.0, 0.0]


def test_slide_per_point_duration_unspecified_points_default_to_one():
    """Una tappa intermedia senza il proprio moltiplicatore vale 1 (come
    una nota senza moltiplicatore)."""
    ev = parse_track_text("c*4>3d*4", {})[0]
    assert ev.duration == 4.0
    assert ev.slide_segment_durations == [1.0, 3.0]

    ev = parse_track_text("2c*4>d*4>3c*4", {})[0]
    assert ev.duration == 6.0
    assert ev.slide_segment_durations == [2.0, 1.0, 3.0]


def test_slide_exports_pitchwheel_messages():
    tmpdir = tempfile.mkdtemp()
    try:
        p = Project(name="Test")
        p.add_track("Piano1", "Piano", "4: c*4>e*4")
        path = os.path.join(tmpdir, "slide.mid")
        export_project_to_midi(p, path)
        import mido
        mid = mido.MidiFile(path, clip=True)
        pitchwheel_msgs = [m for track in mid.tracks for m in track if m.type == "pitchwheel"]
        assert len(pitchwheel_msgs) >= 2  # almeno rampa + reset finale
        # deve iniziare vicino a 0 (nessun bend) e salire verso un bend positivo
        assert pitchwheel_msgs[0].pitch == 0
        assert any(m.pitch > 0 for m in pitchwheel_msgs)
    finally:
        shutil.rmtree(tmpdir)


def test_slide_chain_exports_bend_and_release_pitchwheel_curve():
    """c*4>d*4>c*4 (bend-and-release) deve esportare un'unica nota (un solo
    note_on/note_off, non due note separate) con una rampa di pitchwheel che
    sale fino a meta' della durata e poi rilascia simmetricamente a 0."""
    tmpdir = tempfile.mkdtemp()
    try:
        p = Project(name="Test")
        p.add_track("Guitar1", _overdriven_guitar(), "4: c*4>d*4>c*4")
        path = os.path.join(tmpdir, "bend_release.mid")
        export_project_to_midi(p, path, only_audible=False)
        import mido
        mid = mido.MidiFile(path, clip=True)
        events = []
        for track in mid.tracks:
            abs_tick = 0
            for m in track:
                abs_tick += m.time
                if m.type in ("note_on", "note_off", "pitchwheel"):
                    events.append((abs_tick, m))
        events.sort(key=lambda e: e[0])

        note_ons = [(t, m) for t, m in events if m.type == "note_on"]
        note_offs = [(t, m) for t, m in events if m.type == "note_off"]
        assert len(note_ons) == 1 and note_ons[0][1].note == 60  # un'unica nota, c4
        assert len(note_offs) == 1

        pitchwheel = [(t, m.pitch) for t, m in events if m.type == "pitchwheel"]
        end_tick = note_offs[0][0]
        mid_tick = end_tick // 2
        peak_tick, peak_pitch = max(pitchwheel, key=lambda tp: tp[1])
        # il picco (bend massimo, verso d*4) cade a meta' della durata della nota
        assert abs(peak_tick - mid_tick) <= end_tick * 0.05
        assert peak_pitch > 0
        # rilascia poi simmetricamente verso 0 entro la fine della nota
        assert pitchwheel[-1][1] == 0
        near_release = max(p for t, p in pitchwheel if t > peak_tick + end_tick * 0.1)
        assert near_release < peak_pitch
    finally:
        shutil.rmtree(tmpdir)


def test_slide_per_point_duration_exports_quick_bend_then_flat_hold():
    """2c*4>3d*4 (bend rapido poi tenuto, sezione 2.3): la rampa deve
    completarsi entro i primi 2 beat (2/5 della nota) e restare PIATTA
    (nessun'altra variazione di pitch bend) per i restanti 3, a differenza
    di 5c*4>d*4 (rampa lineare per l'intera durata, gia' coperto da
    test_slide_exports_pitchwheel_messages)."""
    tmpdir = tempfile.mkdtemp()
    try:
        p = Project(name="Test")
        p.add_track("Guitar1", _overdriven_guitar(), "4: 2c*4>3d*4")
        path = os.path.join(tmpdir, "quick_bend.mid")
        export_project_to_midi(p, path, only_audible=False)
        import mido
        mid = mido.MidiFile(path, clip=True)
        events = []
        for track in mid.tracks:
            abs_tick = 0
            for m in track:
                abs_tick += m.time
                if m.type in ("note_on", "note_off", "pitchwheel"):
                    events.append((abs_tick, m))
        events.sort(key=lambda e: e[0])

        note_offs = [t for t, m in events if m.type == "note_off"]
        end_tick = note_offs[0]
        ramp_end_tick = round(end_tick * 2 / 5)  # 2 dei 5 beat totali

        pitchwheel = [(t, m.pitch) for t, m in events if m.type == "pitchwheel"]
        peak_pitch = max(p for _, p in pitchwheel)
        # la rampa raggiunge il picco entro la fine del primo segmento (2/5)...
        first_peak_tick = next(t for t, p in pitchwheel if p == peak_pitch)
        assert first_peak_tick <= ramp_end_tick + 5
        # ...e resta li' (piatta) per tutto il resto della nota, non oltre.
        after_ramp = [p for t, p in pitchwheel if ramp_end_tick + 5 < t < end_tick]
        assert after_ramp and all(p == peak_pitch for p in after_ramp)
    finally:
        shutil.rmtree(tmpdir)


def _build_bend_midi(path, pitchwheel_msgs, rpn_range=None, tpb=480):
    """Costruisce un MIDI minimo (una nota, canale 0) con una rampa di
    pitchwheel sovrapposta, per testare il rilevamento del bending in
    import (vedi midi_convert._collect_pitch_bend_targets). rpn_range, se
    dato, dichiara esplicitamente la sensibilita' del pitch bend via RPN 0
    prima della nota (altrimenti si assume il default General MIDI, +-2
    semitoni)."""
    import mido
    mid = mido.MidiFile(ticks_per_beat=tpb)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    if rpn_range is not None:
        track.append(mido.Message("control_change", control=101, value=0, channel=0, time=0))
        track.append(mido.Message("control_change", control=100, value=0, channel=0, time=0))
        track.append(mido.Message("control_change", control=6, value=rpn_range, channel=0, time=0))
    track.append(mido.Message("note_on", note=60, velocity=100, channel=0, time=0))
    time = 0
    for pitch in pitchwheel_msgs:
        track.append(mido.Message("pitchwheel", pitch=pitch, channel=0, time=time))
        time = tpb // 8
    track.append(mido.Message("note_off", note=60, velocity=0, channel=0, time=tpb // 4))
    mid.save(path)


def test_midi_import_detects_bend_with_default_gm_sensitivity():
    """Nessun RPN dichiarato: la sensibilita' assunta e' il default General
    MIDI (+-2 semitoni) - un bend a fondo scala (pitch=8191) deve arrivare
    a d*4 (60 + 2 semitoni), tradotto in uno slide c*4>d*4. Il picco cade a
    1/3 della durata della nota (vedi _build_bend_midi): lo slide importato
    riflette questo timing reale (rampa piu' corta del mantenimento) invece
    di dividere sempre a meta'."""
    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "bend.mid")
        _build_bend_midi(path, [0, 8191])
        _, tpb, channels = midi_convert.analyze_midi(path)
        ch = channels[0]
        peak_fraction, waypoints = ch.bends[(0, 60)]
        assert waypoints == [62]
        assert peak_fraction == pytest.approx(1 / 3)
        tokens = midi_convert.channel_to_tokens(ch, tpb)
        assert "1c*4>1d*4" in " ".join(tokens)
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_respects_declared_pitch_bend_sensitivity():
    """Con RPN 0 (Pitch Bend Sensitivity) dichiarato a 12 semitoni, un bend
    a un quarto di scala (pitch=2048) deve arrivare a 3 semitoni sopra la
    nota di partenza (60 -> 63, re#4), non a 0.5 (arrotondato a 0, quindi
    nessun bending) come darebbero i 2 semitoni del default GM - un valore
    scelto apposta entro MAX_IMPORTED_BEND_SEMITONES (una terza, 4 semitoni:
    oltre e' implausibile per qualunque strumento, vedi quella costante) per
    restare distinguibile dal filtro di plausibilita', non solo dalla
    sensibilita'. Il valore 0 esplicito prima del picco rispecchia come una
    rampa di bending e' quasi sempre codificata in un MIDI vero (vedi
    _collect_pitch_bend_targets: un singolo evento coincidente col note-on,
    senza uno 0 di riferimento precedente, verrebbe altrimenti scambiato per
    lo stato 'a riposo' del canale invece che per un bending)."""
    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "bend_rpn.mid")
        _build_bend_midi(path, [0, 2048], rpn_range=12)
        _, tpb, channels = midi_convert.analyze_midi(path)
        ch = channels[0]
        peak_fraction, waypoints = ch.bends[(0, 60)]
        assert waypoints == [63]
        assert peak_fraction == pytest.approx(1 / 3)
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_rejects_bend_wider_than_a_third_even_if_range_allows_it():
    """Un canale con RPN ampio (24 semitoni, come quello usato dal nostro
    stesso export per gli slide) puo' comunque contenere un bend che a
    fondo scala arriverebbe a un'ottava piena: non e' un bending plausibile
    su nessuno strumento (sarebbe una nota diversa, non una piegatura della
    stessa) - resta una nota normale invece di produrre uno slide senza
    senso musicale, indipendentemente da quanto la sensibilita' dichiarata
    lo renderebbe tecnicamente rappresentabile."""
    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "bend_wide.mid")
        _build_bend_midi(path, [0, 8191], rpn_range=24)  # fondo scala = 24 semitoni = 2 ottave
        _, tpb, channels = midi_convert.analyze_midi(path)
        ch = channels[0]
        assert ch.bends == {}
        tokens = midi_convert.channel_to_tokens(ch, tpb)
        assert not any(">" in t for t in tokens)
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_ignores_small_bend_as_vibrato():
    """Un pitch bend troppo piccolo per arrotondare a un semitono intero
    (qui ~0.24 semitoni col default GM) e' probabilmente vibrato/rumore di
    registrazione, non un bending deliberato: non deve produrre uno slide."""
    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "vibrato.mid")
        _build_bend_midi(path, [1000])
        _, tpb, channels = midi_convert.analyze_midi(path)
        ch = channels[0]
        assert ch.bends == {}
        tokens = midi_convert.channel_to_tokens(ch, tpb)
        assert not any(">" in t for t in tokens)
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_bend_ignores_stale_state_from_previous_note():
    """Due note legate consecutive (la seconda inizia esattamente dove
    finisce la prima, come tipico in un assolo legato): la prima piega di
    un tono e poi rilascia a 0 esattamente alla fine/inizio della seconda,
    che a sua volta piega di un altro tono verso l'alto. Il riferimento
    'a riposo' della seconda nota deve essere il reset a 0 coincidente col
    suo inizio, non il picco (ancora presente nella timeline globale degli
    eventi) della prima nota - bug reale scoperto importando un file MIDI
    con note legate, corretto usando l'ULTIMO evento con tick <= inizio
    della nota come riferimento (vedi midi_convert._collect_pitch_bend_targets)."""
    import mido
    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "legato_bend.mid")
        mid = mido.MidiFile(ticks_per_beat=480)
        track = mido.MidiTrack()
        mid.tracks.append(track)
        # Nota 1 (sol, 67): piega di un tono (default GM, +-2 semitoni) e rilascia.
        track.append(mido.Message("note_on", note=67, velocity=100, channel=0, time=0))
        track.append(mido.Message("pitchwheel", pitch=0, channel=0, time=60))
        track.append(mido.Message("pitchwheel", pitch=8191, channel=0, time=60))
        track.append(mido.Message("pitchwheel", pitch=0, channel=0, time=60))
        track.append(mido.Message("note_off", note=67, velocity=0, channel=0, time=0))
        # Nota 2 (re, 62), legata subito dopo: piega anch'essa di un tono verso l'alto.
        track.append(mido.Message("note_on", note=62, velocity=100, channel=0, time=0))
        track.append(mido.Message("pitchwheel", pitch=0, channel=0, time=0))
        track.append(mido.Message("pitchwheel", pitch=8191, channel=0, time=60))
        track.append(mido.Message("pitchwheel", pitch=0, channel=0, time=60))
        track.append(mido.Message("note_off", note=62, velocity=0, channel=0, time=0))
        mid.save(path)

        _, tpb, channels = midi_convert.analyze_midi(path)
        ch = channels[0]
        # Ogni nota rilascia a 0 esattamente alla propria fine (vedi sopra):
        # ognuna ottiene correttamente la propria catena bend-and-release a
        # due tappe (picco, poi rilascio), senza che il picco della prima
        # contamini il riferimento della seconda.
        peak1, waypoints1 = ch.bends[(0, 67)]
        peak2, waypoints2 = ch.bends[(180, 62)]
        assert waypoints1 == [69, 67]
        assert waypoints2 == [64, 62]
        assert peak1 == pytest.approx(2 / 3)
        assert peak2 == pytest.approx(0.5)
        tokens = midi_convert.channel_to_tokens(ch, tpb)
        text = " ".join(tokens)
        assert "1g*4>1a*4>0g*4" in text
        assert "1d*4>0e*4>0d*4" in text
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_bend_release_ignores_next_note_at_same_tick():
    """Due note legate: la prima rilascia a 0 esattamente al proprio
    note_off, la seconda inizia allo stesso tick gia' con un proprio bend
    (un pre-bend). Il rilascio della prima nota deve leggere il PROPRIO
    reset a 0 (che nello stream precede il note_on/pre-bend della seconda,
    pur condividendone il tick), non il valore del pre-bend della seconda -
    bug scoperto con un lick di test a piu' tecniche di bending in sequenza."""
    import mido
    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "boundary.mid")
        mid = mido.MidiFile(ticks_per_beat=480)
        track = mido.MidiTrack()
        mid.tracks.append(track)
        # Nota 1 (re, 62): bend-and-release, rilascia a 0 esattamente alla fine.
        track.append(mido.Message("note_on", note=62, velocity=100, channel=0, time=0))
        track.append(mido.Message("pitchwheel", pitch=8191, channel=0, time=96))
        track.append(mido.Message("pitchwheel", pitch=0, channel=0, time=144))
        track.append(mido.Message("note_off", note=62, velocity=0, channel=0, time=0))
        # Nota 2 (mi, 64), legata subito dopo, allo STESSO tick: pre-bend
        # (parte gia' a fondo scala).
        track.append(mido.Message("note_on", note=64, velocity=100, channel=0, time=0))
        track.append(mido.Message("pitchwheel", pitch=8191, channel=0, time=0))
        track.append(mido.Message("pitchwheel", pitch=0, channel=0, time=168))
        track.append(mido.Message("note_off", note=64, velocity=0, channel=0, time=72))
        mid.save(path)

        _, tpb, channels = midi_convert.analyze_midi(path)
        ch = channels[0]
        # Nota 1: bend a d*4 (62+2) e rilascio a d*4 stesso (62+0) - NON deve
        # risultare "nessun rilascio" per colpa del pre-bend della nota 2.
        peak_fraction, waypoints = ch.bends[(0, 62)]
        assert waypoints == [64, 62]
        assert peak_fraction == pytest.approx(0.4)
    finally:
        shutil.rmtree(tmpdir)


def _one_note_midi_with_wheel(tmpdir, name, note, wheel_events):
    """wheel_events: [(tick, pitch)], nota di 480 tick a tick 200 (prima ci sono
    i pitchwheel di 'pre-bend'); ritorna (tokens, channel)."""
    import mido
    path = os.path.join(tmpdir, name)
    mid = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    msgs = [(200, mido.Message("note_on", note=note, velocity=100, channel=0)),
            (680, mido.Message("note_off", note=note, velocity=0, channel=0))]
    msgs += [(t, mido.Message("pitchwheel", pitch=p, channel=0)) for t, p in wheel_events]
    last = 0
    for t, m in sorted(msgs, key=lambda x: x[0]):
        m.time = t - last
        last = t
        track.append(m)
    mid.save(path)
    _, tpb, channels = midi_convert.analyze_midi(path)
    return midi_convert.channel_to_tokens(channels[0], tpb), channels[0]


def test_midi_import_scoop_from_below_slides_up_to_written_note():
    """Wheel a -1 semitono PRIMA della nota che rientra a 0 durante la nota
    (scoop): l'altezza scritta e' quella d'arrivo. Deve diventare do#>re,
    NON re>re# (bug: stonatura sopra la nota scritta)."""
    tmpdir = tempfile.mkdtemp()
    try:
        tokens, ch = _one_note_midi_with_wheel(
            tmpdir, "scoop.mid", 62, [(190, -4096), (260, -2048), (300, 0)])
        assert any(t.split(">")[0].endswith("c#*4") and t.split(">")[-1].endswith("d*4") for t in tokens), tokens
        assert not any("d#*4" in t for t in tokens)
        assert len(ch.bends[(200, 62)]) == 3
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_prebend_from_above_slides_down_to_written_note():
    tmpdir = tempfile.mkdtemp()
    try:
        tokens, _ = _one_note_midi_with_wheel(
            tmpdir, "prebend.mid", 62, [(190, 4096), (300, 0)])
        assert any(t.split(">")[0].endswith("d#*4") and t.split(">")[-1].endswith("d*4") for t in tokens), tokens
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_static_wheel_offset_is_not_a_scoop():
    """Wheel fisso a -1 semitono che non rientra mai a 0: offset statico del
    canale, non un pre-bend - resta una nota normale."""
    tmpdir = tempfile.mkdtemp()
    try:
        tokens, ch = _one_note_midi_with_wheel(tmpdir, "static.mid", 62, [(190, -4096)])
        assert ch.bends == {}
        assert not any(">" in t for t in tokens)
    finally:
        shutil.rmtree(tmpdir)


def _long_note_midi(tmpdir, name, note, wheel_events, length=1920):
    """Nota di 'length' tick a tick 200 (480 tick per beat: 16 sedicesimi se
    length=1920) con i pitchwheel dati; ritorna (tokens, channel)."""
    import mido
    path = os.path.join(tmpdir, name)
    mid = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    msgs = [(200, mido.Message("note_on", note=note, velocity=100, channel=0)),
            (200 + length, mido.Message("note_off", note=note, velocity=0, channel=0))]
    msgs += [(t, mido.Message("pitchwheel", pitch=p, channel=0)) for t, p in wheel_events]
    last = 0
    for t, m in sorted(msgs, key=lambda x: x[0]):
        m.time = t - last
        last = t
        track.append(m)
    mid.save(path)
    _, tpb, channels = midi_convert.analyze_midi(path)
    return midi_convert.channel_to_tokens(channels[0], tpb), channels[0]


def test_midi_import_release_tail_of_previous_note_is_not_a_bend():
    """Il wheel sta ancora scendendo (8191 -> 4096 -> 0) dal rilascio della
    nota precedente quando questa inizia: quel valore d'attacco non e' un
    riferimento, e la discesa a 0 NON e' un bend verso il basso sotto la nota
    scritta (Layla: f -> d#, stonato)."""
    tmpdir = tempfile.mkdtemp()
    try:
        tokens, ch = _long_note_midi(tmpdir, "tail.mid", 65, [(100, 8191), (190, 4096), (215, 0)], length=480)
        assert ch.bends == {}
        assert not any(">" in t for t in tokens)
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_bend_holds_at_peak_until_late_release():
    """Sale subito, TIENE il picco per gran parte della nota e rilascia solo
    verso la fine: la tenuta va scritta come tappa a se' (picco>picco), non
    come rilascio lineare distribuito su tutta la nota (che fa scivolare
    l'intonazione per tutta la durata)."""
    tmpdir = tempfile.mkdtemp()
    try:
        wheel = [(230, 4096), (260, 8191), (1700, 4000), (1800, 0)]
        tokens, _ = _long_note_midi(tmpdir, "hold.mid", 62, wheel)
        token = next(t for t in tokens if ">" in t)
        taps = token.split(">")
        assert len(taps) == 4, token
        durs = [int(re.match(r"\d+", t).group()) for t in taps]
        assert durs[0] <= 2 and durs[1] >= 9 and durs[2] <= 3 and durs[3] >= 2, token
        pitches = [re.sub(r"^\d+", "", t) for t in taps]
        assert pitches == ["d*4", "e*4", "e*4", "d*4"], token
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_bend_release_finishes_early_then_holds_final_pitch():
    """Bend che scende di un semitono e risale quasi subito (nel primo terzo
    della nota), poi resta sull'altezza scritta: il rilascio non va steso
    linearmente su tutta la nota."""
    tmpdir = tempfile.mkdtemp()
    try:
        wheel = [(230, -4096), (300, -3500), (420, -100), (440, 0)]
        tokens, _ = _long_note_midi(tmpdir, "early.mid", 64, wheel)
        token = next(t for t in tokens if ">" in t)
        durs = [int(re.match(r"\d+", t).group()) for t in token.split(">")]
        assert len(durs) >= 3 and durs[-1] >= 8, token  # lunga tenuta finale sull'altezza scritta
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_hold_release_chain_roundtrips_through_export():
    tmpdir = tempfile.mkdtemp()
    try:
        p = Project()
        p.add_track("Guitar", "Piano", "16: 1c*4>10e*4>1e*4>4c*4")
        path = os.path.join(tmpdir, "hold_rt.mid")
        export_project_to_midi(p, path)
        _, tpb, channels = midi_convert.analyze_midi(path)
        tokens = midi_convert.channel_to_tokens(list(channels.values())[0], tpb)
        token = next(t for t in tokens if ">" in t)
        assert token.count(">") == 3, token
        assert re.sub(r"\d+", "", token.split(">")[1]) == "e*"
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_bend_waits_for_late_onset_when_wheel_is_flat_before():
    """Wheel praticamente fermo (piccola deriva, sotto la soglia) per quasi meta'
    nota, poi scende di un semitono: il bend non parte dall'attacco - ci vuole
    una tenuta iniziale (prima e seconda tappa alla stessa altezza)."""
    tmpdir = tempfile.mkdtemp()
    try:
        wheel = [(300, 200), (400, 300), (600, 400), (1100, -4096), (1200, -4096)]
        tokens, ch = _long_note_midi(tmpdir, "onset.mid", 62, wheel)
        token = next(t for t in tokens if ">" in t)
        taps = token.split(">")
        pitches = [re.sub(r"^\d+", "", t) for t in taps]
        durs = [int(re.match(r"\d+", t).group()) for t in taps]
        assert pitches[0] == pitches[1] == "d*4" and pitches[-1] == "c#*4", token
        assert durs[0] >= 6, token  # la tenuta iniziale dura quasi meta' nota
        assert ch.bend_onset[(200, 62)] > 0.4
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_two_sided_bend_keeps_both_excursions():
    """Sale di un tono e poi scende un tono SOTTO la nota scritta (slide):
    il modello a un solo picco terrebbe una sola delle due escursioni."""
    tmpdir = tempfile.mkdtemp()
    try:
        wheel = [(300, 4000), (500, 8191), (900, 8191), (1200, 0), (1300, -8000), (1800, -8000)]
        tokens, ch = _long_note_midi(tmpdir, "twosided.mid", 62, wheel)
        token = next(t for t in tokens if ">" in t)
        pitches = {re.sub(r"^\d+", "", t) for t in token.split(">")}
        assert "e*4" in pitches and "c*4" in pitches, token  # +2 e -2 semitoni
        assert (200, 62) in ch.bend_paths
    finally:
        shutil.rmtree(tmpdir)


def _wide_range_midi(tmpdir, name, notes, wheel_events, bend_range=12):
    """notes: [(start, end, midi_note)] sullo stesso canale; RPN 0 (sensibilita'
    del pitch bend) = bend_range semitoni. Ritorna (tokens, channel)."""
    import mido
    path = os.path.join(tmpdir, name)
    mid = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    msgs = [(0, mido.Message("control_change", control=101, value=0, channel=0)),
            (0, mido.Message("control_change", control=100, value=0, channel=0)),
            (0, mido.Message("control_change", control=6, value=bend_range, channel=0))]
    for st, en, n in notes:
        msgs.append((st, mido.Message("note_on", note=n, velocity=100, channel=0)))
        msgs.append((en, mido.Message("note_off", note=n, velocity=0, channel=0)))
    msgs += [(t, mido.Message("pitchwheel", pitch=p, channel=0)) for t, p in wheel_events]
    last = 0
    for t, m in sorted(msgs, key=lambda x: x[0]):
        m.time = t - last
        last = t
        track.append(m)
    mid.save(path)
    _, tpb, channels = midi_convert.analyze_midi(path)
    return midi_convert.channel_to_tokens(channels[0], tpb), channels[0]


def test_midi_import_wide_bend_up_to_an_octave_is_imported():
    """Uno slide di 7 semitoni (bottleneck, calo a nastro) con sensibilita'
    dichiarata di 12: prima il tetto di 4 semitoni lo scartava."""
    tmpdir = tempfile.mkdtemp()
    try:
        # +7 semitoni a range 12 = 7/12 del fondo scala
        wheel = [(300, 2000), (500, 4780), (700, 4780)]
        tokens, ch = _wide_range_midi(tmpdir, "wide.mid", [(200, 1200, 60)], wheel)
        token = next(t for t in tokens if ">" in t)
        assert token.split(">")[-1].endswith("g*4"), token   # 60 + 7
        assert (200, 60) in ch.bends
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_bend_beyond_an_octave_is_still_ignored():
    tmpdir = tempfile.mkdtemp()
    try:
        # +24 semitoni (fondo scala con sensibilita' 24): non e' un bending
        tokens, ch = _wide_range_midi(tmpdir, "huge.mid", [(200, 1200, 60)],
                                      [(300, 8191)], bend_range=24)
        assert ch.bends == {}
        assert not any(">" in t for t in tokens)
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_bend_starting_with_the_note_returns_to_written_pitch():
    """Layla, fine assolo: il wheel e' gia' a -640 (sotto soglia) sull'attacco
    perche' il bend parte con la nota, scende di ~7 semitoni e torna a 0. Il
    riferimento e' il centro: la nota finisce sul la scritto, non sul la#."""
    tmpdir = tempfile.mkdtemp()
    try:
        wheel = [(200, -640), (260, -3680), (300, -4800), (500, -1500), (800, 0)]
        tokens, ch = _wide_range_midi(tmpdir, "dip.mid", [(200, 2100, 69)], wheel)
        token = next(t for t in tokens if ">" in t)
        assert token.split(">")[-1].endswith("a*4"), token
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_prebend_of_next_note_is_not_a_phantom_bend_on_this_one():
    """Il wheel salta a -12 semitoni pochi tick prima dell'attacco della nota
    successiva e ci resta: e' il pre-bend di QUELLA nota, non un bend in coda
    alla prima (che restava altrimenti una nota normale)."""
    tmpdir = tempfile.mkdtemp()
    try:
        wheel = [(1190, -8192), (1500, -4000), (1600, 0)]
        tokens, ch = _wide_range_midi(tmpdir, "next_pre.mid",
                                      [(200, 1200, 62), (1210, 2100, 64)], wheel)
        assert (200, 62) not in ch.bends
        assert (1210, 64) in ch.bends and len(ch.bends[(1210, 64)]) == 3  # scoop dal basso
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_falloff_that_resets_at_next_onset_belongs_to_this_note():
    """Il wheel scende in una rampa lunga verso il fondo e torna a 0
    esattamente all'attacco successivo: e' un fall-off di questa nota (la
    successiva parte da 0), non un pre-bend."""
    tmpdir = tempfile.mkdtemp()
    try:
        wheel = [(900, -1500), (1000, -3000), (1100, -5000), (1200, -8000), (1210, 0)]
        _tokens, ch = _wide_range_midi(tmpdir, "falloff.mid",
                                       [(200, 1215, 62), (1210, 2100, 64)], wheel, bend_range=2)
        assert (200, 62) in ch.bends
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_scoop_with_deeper_dive_keeps_the_dive():
    """Il wheel parte gia' a -6 semitoni, si tuffa a -12 e poi risale a 0: lo
    scoop semplice (da -6 a 0) ignorerebbe il tuffo piu' profondo."""
    tmpdir = tempfile.mkdtemp()
    try:
        # sensibilita' 12: -3072 = -4.5, -8192 = -12
        wheel = [(190, -4096), (260, -8192), (500, -6000), (800, -2000), (1000, 0)]
        tokens, ch = _wide_range_midi(tmpdir, "dive.mid", [(200, 1300, 62)], wheel)
        token = next(t for t in tokens if ">" in t)
        pitches = [re.sub(r"^\d+", "", t) for t in token.split(">")]
        assert "d*3" in pitches, token          # 62 - 12: il fondo del tuffo
        assert pitches[-1] == "d*4", token      # e ritorna alla nota scritta
        assert (200, 62) in ch.bend_paths
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_late_dive_with_sampled_ramp_starts_late():
    """Nota lunga con il wheel fermo fin quasi alla fine e poi un tuffo
    campionato con molti eventi: la discesa NON e' distribuita su tutta la
    nota (nemmeno se prima del tuffo c'e' un solo evento)."""
    tmpdir = tempfile.mkdtemp()
    try:
        wheel = [(300, 0), (1700, -1500), (1750, -4000), (1800, -8000), (1850, -8192)]
        tokens, ch = _wide_range_midi(tmpdir, "late.mid", [(200, 1950, 62)], wheel)
        token = next(t for t in tokens if ">" in t)
        taps = token.split(">")
        durs = [int(re.match(r"\d+", t).group() or 1) for t in taps]
        pitches = [re.sub(r"^\d+", "", t) for t in taps]
        assert pitches[0] == pitches[1] == "d*4", token   # tenuta iniziale sulla nota scritta
        assert durs[0] >= 8, token                          # lunga: il tuffo e' alla fine
        assert pitches[-1] == "d*3", token
    finally:
        shutil.rmtree(tmpdir)


def _many_track_project(guitar_voices, other_programs):
    """Project con 'guitar_voices' tracce dello stesso strumento (programma 29)
    seguite da una traccia per ciascuno dei programmi in other_programs."""
    from core.instruments import resolve_or_create_instrument_by_program
    guitar = resolve_or_create_instrument_by_program(29, False)
    p = Project(name="Many")
    for i in range(guitar_voices):
        p.add_track(f"Guitar {i}", guitar, "16: c d e f")
    for prog in other_programs:
        name = resolve_or_create_instrument_by_program(prog, False)
        p.add_track(f"T{prog}", name, "16: c d e f")
    return p, guitar


def test_channel_assignment_moves_tracks_beyond_15_to_the_next_port():
    """20 tracce melodiche (8 voci di chitarra e 12 strumenti diversi): ognuna ha
    il suo canale; dalla sedicesima si passa alla porta 1 (slot = porta * 16 +
    canale), senza mai usare il canale delle percussioni."""
    from core.midi_export import _assign_channels, DRUM_MIDI_CHANNEL
    p, _guitar = _many_track_project(8, [1, 3, 22, 35, 66, 18, 30, 28, 40, 24, 57, 71])
    mapping = _assign_channels(p.tracks)
    slots = [mapping[t.name] for t in p.tracks]
    assert len(set(slots)) == 20
    assert all(slot % 16 != DRUM_MIDI_CHANNEL for slot in slots)
    assert slots[:15] == [c for c in range(16) if c != DRUM_MIDI_CHANNEL]
    assert slots[15:] == [16, 17, 18, 19, 20]


def test_channel_assignment_keeps_one_channel_per_track_when_they_fit():
    from core.midi_export import _assign_channels
    p, _ = _many_track_project(5, [1, 3, 22])
    mapping = _assign_channels(p.tracks)
    assert len(set(mapping.values())) == len(p.tracks) and max(mapping.values()) < 16


def test_export_with_many_tracks_never_mixes_programs_on_a_port_channel():
    import mido
    p, _ = _many_track_project(8, [1, 3, 22, 35, 66, 18, 30, 28, 40, 24, 57, 71])
    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "many.mid")
        export_project_to_midi(p, path, only_audible=False)
        programs = {}
        for track in mido.MidiFile(path).tracks:
            port = next((m.port for m in track if m.type == "midi_port"), None)
            for m in track:
                if m.type == "program_change":
                    assert port is not None
                    programs.setdefault((port, m.channel), set()).add(m.program)
        assert len(programs) == 20 and all(len(v) == 1 for v in programs.values()), programs
    finally:
        shutil.rmtree(tmpdir)


def test_voice_cap_is_never_exceeded_even_with_many_durations_at_one_onset():
    """Sei note che iniziano insieme con sei durate diverse: servirebbero 6 voci;
    il tetto e' 2. Le eccedenti si fondono con la piu' vicina (nessuna nota
    persa, mai una terza voce)."""
    from core.chords import midi_to_token
    ch = midi_convert.ChannelData(0)
    ch.notes = [(0, 480 * (i + 1), 50 + 2 * i, 80) for i in range(6)]
    ch.notes += [(480 * 8, 480 * 9, 70, 80)]
    voices = midi_convert.channel_to_voices(ch, 480)
    assert len(voices) <= midi_convert.MAX_IMPORT_VOICES == 2
    text = " ".join(t for v in voices for t in v)
    for i in range(6):
        assert midi_to_token(50 + 2 * i) in text, (i, text)
    assert midi_to_token(70) in text


def test_midi_import_does_not_bend_chords():
    """Uno slide riguarda una sola altezza per volta: un bending durante un
    accordo (piu' note simultanee) non e' rappresentabile e va ignorato,
    lasciando l'accordo come blocco esplicito normale."""
    import mido
    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "chord_bend.mid")
        mid = mido.MidiFile(ticks_per_beat=480)
        track = mido.MidiTrack()
        mid.tracks.append(track)
        track.append(mido.Message("note_on", note=60, velocity=100, channel=0, time=0))
        track.append(mido.Message("note_on", note=64, velocity=100, channel=0, time=0))
        track.append(mido.Message("pitchwheel", pitch=8191, channel=0, time=120))
        track.append(mido.Message("note_off", note=60, velocity=0, channel=0, time=120))
        track.append(mido.Message("note_off", note=64, velocity=0, channel=0, time=0))
        mid.save(path)
        _, tpb, channels = midi_convert.analyze_midi(path)
        tokens = midi_convert.channel_to_tokens(channels[0], tpb)
        assert not any(">" in t for t in tokens)
    finally:
        shutil.rmtree(tmpdir)


def test_midi_import_bend_roundtrips_through_export():
    """L'importazione di un bending (-> slide) e la successiva
    riesportazione (-> rampa pitchwheel, vedi test_slide_exports_
    pitchwheel_messages) devono comporsi senza perdere il bending."""
    import mido
    from core.midi_import import import_midi_file
    tmpdir = tempfile.mkdtemp()
    try:
        src_path = os.path.join(tmpdir, "bend.mid")
        _build_bend_midi(src_path, [0, 8191])
        project = import_midi_file(src_path, project_name="Test")
        assert ">" in project.tracks[0].text

        out_path = os.path.join(tmpdir, "out.mid")
        export_project_to_midi(project, out_path, only_audible=False)
        out = mido.MidiFile(out_path, clip=True)
        pitchwheel_msgs = [m for track in out.tracks for m in track if m.type == "pitchwheel"]
        assert any(m.pitch > 0 for m in pitchwheel_msgs)
    finally:
        shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------- sustain pedale

def test_sustain_on_off_tokens_parse():
    ev = parse_track_text("SON c*4 d*4 SOFF", {})
    assert [e.kind for e in ev] == ["sustain", "note", "note", "sustain"]
    assert ev[0].name == "on"
    assert ev[-1].name == "off"


def test_sustain_exports_control_change_64():
    tmpdir = tempfile.mkdtemp()
    try:
        p = Project(name="Test")
        p.add_track("Piano1", "Piano", "8: SON c*4 d*4 SOFF")
        path = os.path.join(tmpdir, "sustain.mid")
        export_project_to_midi(p, path)
        import mido
        mid = mido.MidiFile(path, clip=True)
        cc64 = [m for track in mid.tracks for m in track
                if m.type == "control_change" and m.control == 64]
        assert len(cc64) == 2
        assert cc64[0].value == 127  # SON
        assert cc64[1].value == 0    # SOFF
    finally:
        shutil.rmtree(tmpdir)


def test_sustain_left_open_is_auto_closed_at_track_end():
    """Rete di sicurezza: se manca SOFF, il pedale va comunque rilasciato
    alla fine della traccia per evitare code sonore infinite."""
    tmpdir = tempfile.mkdtemp()
    try:
        p = Project(name="Test")
        p.add_track("Piano1", "Piano", "8: SON c*4 d*4")  # nessun SOFF
        path = os.path.join(tmpdir, "sustain_open.mid")
        export_project_to_midi(p, path)
        import mido
        mid = mido.MidiFile(path, clip=True)
        cc64 = [m for track in mid.tracks for m in track
                if m.type == "control_change" and m.control == 64]
        assert len(cc64) == 2
        assert cc64[0].value == 127
        assert cc64[1].value == 0  # rilascio automatico aggiunto
    finally:
        shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------- dinamiche testuali

def test_named_dynamics_map_to_expected_velocity():
    expected = {
        "pppp": 10, "ppp": 23, "pp": 36, "p": 49, "mp": 62,
        "mf": 75, "f": 88, "ff": 101, "fff": 114, "ffff": 127,
    }
    for name, val in expected.items():
        ev = parse_track_text(f"{name}@ c*4", {})
        assert ev[0].velocity == val, f"{name}@ -> {ev[0].velocity}, atteso {val}"


def test_dynamics_ramp_crescendo_interpolates_linearly():
    ev = parse_track_text("p@ >> c*4 d*4 e*4 f*4 f@", {})
    vels = [e.velocity for e in ev]
    # interpolazione lineare esatta da p(49) a f(88) su 4 note: la prima
    # nota ottiene esattamente il valore di partenza, l'ultima quello di arrivo
    assert vels == [49, 62, 75, 88]
    assert vels == sorted(vels)  # crescente


def test_dynamics_ramp_diminuendo_with_explicit_values():
    ev = parse_track_text("110@ << g*4 f*4 e*4 d*4 30@", {})
    vels = [e.velocity for e in ev]
    assert vels[0] == 110 and vels[-1] == 30
    assert vels == sorted(vels, reverse=True)  # decrescente


def test_velocity_ramp_orphaned_by_tempo_change_raises_explicit_error():
    """Una rampa di velocity aperta (>> dopo N@/dinamica) ma mai richiusa
    da un altro N@/dinamica prima che arrivi un cambio di tempo (tempo=N) deve
    sollevare un errore esplicito, non restare 'orfana' in silenzio senza
    che il crescendo/diminuendo richiesto venga mai applicato."""
    try:
        parse_track_text("p@ >> c*4 d*4 tempo=120 ff@", {})
        assert False, "doveva sollevare NotationError"
    except NotationError as e:
        assert "orfana" not in str(e).lower()  # messaggio esplicito, non un bug silenzioso
        assert "tempo=N" in str(e) or "tempo" in str(e).lower()


def test_tempo_ramp_orphaned_by_velocity_change_raises_explicit_error():
    """Speculare: una rampa di tempo aperta (>> dopo tempo=N) ma mai richiusa da
    un altro tempo=N prima che arrivi un comando di velocity deve anch'essa
    sollevare un errore esplicito."""
    try:
        parse_track_text("tempo=100 >> c*4 d*4 90@ tempo=140", {})
        assert False, "doveva sollevare NotationError"
    except NotationError as e:
        assert "velocity" in str(e).lower() or "N@" in str(e)


# ---------------------------------------------------------------------- rampe di tempo

def test_tempo_marker_inline_token():
    ev = parse_track_text("tempo=120 c*4", {})
    assert ev[0].kind == "tempo_marker"
    assert ev[0].bpm == 120
    assert ev[1].kind == "note"


def test_tempo_ramp_interpolates_across_notes():
    ev = parse_track_text("tempo=100 >> c*4 d*4 e*4 f*4 tempo=140", {})
    tempo_markers = [e for e in ev if e.kind == "tempo_marker"]
    bpms = [m.bpm for m in tempo_markers]
    assert bpms[0] == 100
    assert bpms[-1] == 140
    assert bpms == sorted(bpms)  # accelerando: crescente


def test_tempo_ramp_exports_multiple_set_tempo_messages():
    tmpdir = tempfile.mkdtemp()
    try:
        p = Project(name="Test")
        p.add_track("Piano1", "Piano", "4: tempo=100 >> c*4 d*4 e*4 f*4 tempo=140")
        path = os.path.join(tmpdir, "temporamp.mid")
        export_project_to_midi(p, path)
        import mido
        mid = mido.MidiFile(path, clip=True)
        tempos = [mido.tempo2bpm(m.tempo) for track in mid.tracks for m in track if m.type == "set_tempo"]
        assert len(tempos) >= 4
        assert round(tempos[0]) == 100
        assert round(tempos[-1]) == 140
    finally:
        shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------- cambi tempo/metrica per battuta

def test_bar_beat_offsets_with_time_signature_changes():
    tempo_changes = [(1, 120), (5, 140), (9, 100)]
    metrica_changes = [(1, "4/4"), (5, "3/4"), (8, "4/4")]
    offsets = compute_bar_beat_offsets(tempo_changes, metrica_changes)
    assert offsets[1] == 0.0
    assert offsets[5] == 16.0   # 4 battute x 4/4 = 16 quarti
    assert offsets[8] == 25.0    # + 3 battute x 3/4 = 9 quarti
    assert offsets[9] == 29.0     # + 1 battuta x 4/4 = 4 quarti


def test_parse_and_reserialize_bar_indexed_tempo_metrica():
    text = (
        "Tempo: 1: 120, 5: 140, 9: 100\n"
        "Metrica: 1: 4/4, 5: 3/4, 8: 4/4\n\n"
        "Piano:\n  16: c*4 d*4 e*4 f*4\n"
    )
    p = parse_project_text(text, project_name="Test")
    assert p.tempo_changes == [(1, 120), (5, 140), (9, 100)]
    assert p.metrica_changes == [(1, "4/4"), (5, "3/4"), (8, "4/4")]
    assert p.tempo_bpm == 120  # compatibilita': primo valore
    assert p.time_sig == "4/4"

    reserialized = project_to_text(p)
    p2 = parse_project_text(reserialized, project_name="Test2")
    assert p2.tempo_changes == p.tempo_changes
    assert p2.metrica_changes == p.metrica_changes


def test_simple_single_value_tempo_still_works():
    """Retrocompatibilita': il vecchio formato a valore singolo deve
    continuare a funzionare esattamente come prima."""
    text = "Tempo: 96 BPM\nMetrica: 4/4\n\nPiano:\n  c*4\n"
    p = parse_project_text(text, project_name="Test")
    assert p.tempo_bpm == 96
    assert p.time_sig == "4/4"
    assert p.tempo_changes == []
    assert p.metrica_changes == []


def test_bar_indexed_tempo_exports_correct_first_tempo():
    tmpdir = tempfile.mkdtemp()
    try:
        text = (
            "Tempo: 1: 120, 5: 140, 9: 100\n"
            "Metrica: 4/4\n\n"
            "Piano:\n  16: c*4 d*4 e*4 f*4 g*4 a*4 b*4 c*5\n"
        )
        p = parse_project_text(text, project_name="Test")
        path = os.path.join(tmpdir, "bartest.mid")
        export_project_to_midi(p, path)
        tempo, _, _ = midi_convert.analyze_midi(path)
        assert tempo == 120  # tempo iniziale, non l'ultimo del file
    finally:
        shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------- round-trip su tutti i progetti reali

def test_all_real_projects_still_valid_after_extensions():
    import glob
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = glob.glob(os.path.join(root, "examples", "*.st")) + glob.glob(os.path.join(root, "songs", "*.st"))
    assert files, "nessun progetto di esempio trovato"
    for f in files:
        proj = load_project_file(f)
        for t in proj.tracks:
            ok, msg = validate_track_text(t.text, proj.patterns, default_octave=t.instrument.default_octave)
            assert ok, f"{f} :: {t.name}: {msg}"


# ---------------------------------------------------------------------- evidenziazione durante la riproduzione

def test_compute_token_spans_repeat_group_is_single_span_full_duration():
    from core.notation import compute_token_spans
    spans = compute_token_spans("4(c d e f)", {})
    assert len(spans) == 1
    assert spans[0][3] == 16.0  # 4 ripetizioni x 4 note x 1 beat = 16


def test_compute_token_spans_slide_is_single_span():
    from core.notation import compute_token_spans
    spans = compute_token_spans("c*4>d*4", {})
    assert len(spans) == 1
    assert spans[0][3] == 1.0


def test_compute_token_spans_ignores_stateless_tokens():
    from core.notation import compute_token_spans
    for text in ("SON c*4 SOFF", "tempo=120 c*4", "tempo=100 >> c*4 tempo=140"):
        spans = compute_token_spans(text, {})
        # solo il token nota deve produrre uno span, mai i comandi di stato
        assert len(spans) == 1


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
