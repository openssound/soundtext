"""
Test per le melodie a frasi (core.melody_generate, stili MELODY_STYLES di
core.rhythm_generate): forma A A' B A e domanda-risposta, note dell'accordo
sui tempi forti, andamento ad arco, cadenze, metriche.
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core.chords import midi_note, note_name_to_pc
from core.melody_generate import _allowed_pcs, _chord_pcs, estimate_key
from core.notation import parse_track_text, validate_track_text
from core.rhythm_generate import (
    MELODY_STYLES, RIFF_STYLES, ChordSpan, Variability, extract_chords_from_track, generate_melodic_line,
    meter_beats,
)

PROGRESSIONS = ["4C 4G 4Am 4F", "4Am 4Dm 4E7 4Am", "4Dm7 4G7 8Cmaj7", "4C 4F 4C 4G7", "4F 4Bb 4C7 4F"]


def _melody(prog, style="melody_aaba", bars=8, bar_beats=4.0, **kw):
    spans = extract_chords_from_track(prog, {})
    kw.setdefault("variation_every", 0)
    return generate_melodic_line(spans, style, 5, 55, 88, polyphonic=False,
                                 min_total_beats=bars * bar_beats, bar_beats=bar_beats, **kw)


def _notes(text):
    return [(e.start, e.duration, midi_note(note_name_to_pc(e.letter), e.octave))
            for e in parse_track_text(text, {}) if e.kind == "note"]


def _phrase(notes, index, beats=8.0):
    return [n for n in notes if index * beats - 1e-6 <= n[0] < (index + 1) * beats - 1e-6]


def test_melody_styles_are_riff_styles():
    assert set(MELODY_STYLES) <= set(RIFF_STYLES)
    with pytest.raises(ValueError):
        generate_melodic_line(extract_chords_from_track("4C 4G", {}), "melody_aaba", 4, 40, 90, polyphonic=True)


@pytest.mark.parametrize("meter", ["4/4", "3/4", "2/4", "5/4", "6/8", "7/8", "12/8"])
@pytest.mark.parametrize("style", list(MELODY_STYLES))
def test_melody_fills_exactly_the_requested_bars_in_any_meter(style, meter):
    bar_beats = meter_beats(meter)
    for v, seed in ((0.0, None), (0.7, 3)):
        text = _melody("4C 4G 4Am 4F", style, bars=9, bar_beats=bar_beats, meter=meter, variability=v, seed=seed)
        ok, msg = validate_track_text(text, {})
        assert ok, msg
        notes = _notes(text)
        # come basso e accompagnamento: il giro di accordi (16 beat) si ripete
        # per intero fino a coprire le battute richieste
        expected = 16.0 * -(-9 * bar_beats // 16.0)
        assert notes and max(s + d for s, d, _m in notes) == pytest.approx(expected)
        assert all(55 <= m <= 88 for _s, _d, m in notes)


@pytest.mark.parametrize("prog", PROGRESSIONS)
@pytest.mark.parametrize("style", list(MELODY_STYLES))
def test_chord_tones_on_the_downbeats(prog, style):
    spans = extract_chords_from_track(prog, {})
    cycle = spans[-1].start_beat + spans[-1].duration_beats
    for v, seed in ((0.0, None), (1.0, 5)):
        for start, _d, pitch in _notes(_melody(prog, style, variability=v, seed=seed)):
            if abs(start % 4.0) < 1e-6:
                span = [s for s in spans if s.start_beat <= start % cycle + 1e-6][-1]
                assert pitch % 12 in _chord_pcs(span), (prog, style, start)


@pytest.mark.parametrize("prog", PROGRESSIONS)
def test_melody_moves_mostly_by_step_with_an_arch(prog):
    steps = total = peaks_inside = 0
    for style in MELODY_STYLES:
        notes = _notes(_melody(prog, style))
        for p in range(4):
            pitches = [m for _s, _d, m in _phrase(notes, p)]
            for a, b in zip(pitches, pitches[1:]):
                assert abs(a - b) <= 9, (prog, style, p, pitches)     # niente salti enormi nella frase
                total += 1
                steps += abs(a - b) <= 2
            peak = pitches.index(max(pitches))
            peaks_inside += 0 < peak < len(pitches) - 1
    assert steps / total >= 0.6
    assert peaks_inside >= 12                  # su 16 frasi: l'apice sta dentro la frase


def test_aaba_repeats_the_motif_and_contrasts_with_b():
    # A su do-sol, A' su do-do (chiude sulla tonica), B su fa-sol, A su do-sol
    notes = _notes(_melody("4C 4G 4C 4C 4F 4G 4C 4G"))
    rhythm = lambda p: [round(s - 8 * p, 3) for s, _d, _m in _phrase(notes, p)]
    pitches = lambda p: [m for _s, _d, m in _phrase(notes, p)]
    first_bar = lambda p: [m for s, _d, m in _phrase(notes, p) if s < 8 * p + 4]
    assert rhythm(0) == rhythm(1) == rhythm(3)           # A, A', A: stesso ritmo
    assert rhythm(2) != rhythm(0)                        # B: un altro ritmo
    assert first_bar(0) == first_bar(1)                  # A' riprende A...
    assert pitches(0)[-1] != pitches(1)[-1]              # ...ma chiude diversamente
    assert pitches(1)[-1] % 12 == 0                      # sulla tonica
    assert pitches(3)[:-2] == pitches(0)[:-2]            # la ripresa di A
    assert max(pitches(2)) > max(pitches(0))             # B sta piu' in alto


def test_question_and_answer():
    for prog in ("4C 4G 4C 4C", "4C 4F 4G 4C"):
        notes = _notes(_melody(prog, "melody_period", bars=4))
        question, answer = _phrase(notes, 0), _phrase(notes, 1)
        assert question[-1][2] % 12 != 0                  # la domanda resta aperta
        assert answer[-1][2] % 12 == 0                    # la risposta chiude sulla tonica
        # la risposta riprende il ritmo della domanda
        assert [round(s, 3) for s, _d, _m in question] == [round(s - 8, 3) for s, _d, _m in answer]


def test_closed_ending_over_the_dominant_uses_the_tonic_triad():
    notes = _notes(_melody("4C 4G", "melody_period", bars=4))
    question, answer = _phrase(notes, 0), _phrase(notes, 1)
    assert answer[-1][2] % 12 == 7                        # sul sol: la quinta della tonica
    assert question[-1][2] != answer[-1][2]


@pytest.mark.parametrize("prog,key,tonic", [("4C 4G 4Am 4F", None, 0), ("4Am 4Dm 4E7 4Am", None, 9),
                                            ("4C 4G 4Am 4F", "Am", 9), ("4Dm7 4G7 8Cmaj7", None, 0)])
def test_melody_ends_on_the_tonic(prog, key, tonic):
    for bars in (8, 6):
        last = _notes(_melody(prog, bars=bars, key=key))[-1]
        spans = extract_chords_from_track(prog, {})
        cycle = spans[-1].start_beat + spans[-1].duration_beats
        last_chord = [s for s in spans if s.start_beat <= last[0] % cycle + 1e-6][-1]
        expected = tonic if tonic in _chord_pcs(last_chord) else None
        if expected is not None:
            assert last[2] % 12 == expected, (prog, key, bars)
        else:
            assert last[2] % 12 in _chord_pcs(last_chord)


def test_estimate_key():
    assert estimate_key(extract_chords_from_track("4C 4G 4Am 4F", {})) == (0, "major")
    assert estimate_key(extract_chords_from_track("4Am 4Dm 4E7 4Am", {})) == (9, "minor")
    assert estimate_key(extract_chords_from_track("4Dm7 4G7 8Cmaj7", {})) == (0, "major")
    assert estimate_key(extract_chords_from_track("4Em 4C 4G 4D", {})) == (4, "minor")


def test_altered_chord_tones_replace_the_scale_note():
    minor = [9, 11, 0, 2, 4, 5, 7]                       # la minore naturale
    e7 = extract_chords_from_track("4E7", {})[0]
    assert 8 in _allowed_pcs(minor, e7) and 7 not in _allowed_pcs(minor, e7)   # sol# al posto di sol
    major = [0, 2, 4, 5, 7, 9, 11]
    c7 = extract_chords_from_track("4C7", {})[0]
    assert 10 in _allowed_pcs(major, c7) and 11 not in _allowed_pcs(major, c7)  # sib al posto di si


def test_zero_variability_ignores_the_seed_and_variability_is_reproducible():
    plain = _melody("4C 4G 4Am 4F")
    assert _melody("4C 4G 4Am 4F", variability=0.0, seed=1) == plain == _melody("4C 4G 4Am 4F", seed=99)
    a = _melody("4C 4G 4Am 4F", variability=0.6, seed=4)
    assert a == _melody("4C 4G 4Am 4F", variability=0.6, seed=4)
    assert len({_melody("4C 4G 4Am 4F", variability=0.6, seed=n) for n in range(6)}) > 3
    # solo dinamica: stesse note, con le velocity
    dyn = _melody("4C 4G 4Am 4F", variability=Variability(0, 0, 1), seed=2)
    assert "@" in dyn and " ".join(t for t in dyn.split() if not t.endswith("@")) == plain


def test_intensity_changes_the_density():
    counts = {level: len(_notes(_melody("4C 4G 4Am 4F", intensity=level))) for level in ("light", "normal", "full")}
    assert counts["light"] < counts["normal"] < counts["full"]
    with pytest.raises(ValueError):
        _melody("4C 4G", intensity="boh")


def test_melody_needs_chords_and_a_known_style():
    from core.melody_generate import generate_phrase_melody
    with pytest.raises(ValueError):
        generate_phrase_melody([], "melody_aaba", 5, 55, 88)
    with pytest.raises(ValueError):
        generate_phrase_melody([ChordSpan(0.0, 4.0, 0, True)], "melody_xyz", 5, 55, 88)


def test_dialog_passes_the_key_and_disables_variation_every():
    import os as _os
    _os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from core.model import Project
    from gui.rhythm_generate_dialog import MelodyGenerateDialog
    p = Project(name="t", key="Am")
    p.add_track("Piano", "Piano", "4: 4C 4G 4Am 4F")
    dlg = MelodyGenerateDialog(None, p, "Trumpet", "traccia 'Tromba'", [("Piano", p.tracks[0].text)],
                               polyphonic=False, default_octave=5, range_low=52, range_high=82,
                               default_bars=8, track_name="Tromba")
    assert dlg.variation_every_spin.isEnabled()
    dlg.variability_slider.setValue(0)
    dlg.style_combo.setCurrentIndex(dlg.style_combo.findData("melody_period"))
    assert not dlg.variation_every_spin.isEnabled()
    spans = extract_chords_from_track(p.tracks[0].text, {})
    expected = generate_melodic_line(spans, "melody_period", 5, 52, 82, polyphonic=False,
                                     min_total_beats=32.0, key="Am", meter="4/4")
    assert dlg.preview_edit.toPlainText() == expected
