"""
Test dei generatori che suonano insieme e seguono la forma del brano
(core.rhythm_generate): fill di batteria alla fine delle sezioni, basso
agganciato alla cassa e riarmonizzazione di un giro gia' scritto.

Esecuzione:
    python3 -m pytest tests/test_generators_together.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)

import pytest

from core.model import Clip, Project
from core.notation import parse_track_text
from core.rhythm_generate import (
    extract_chords_from_track, generate_bass_from_chords, generate_drum_pattern, kick_beats_of_track,
    reharmonize_text, section_end_bars, track_end_beat,
)


def _bars(text, bar_beats=4.0):
    """{battuta: [nomi delle percussioni]} di un testo di batteria."""
    out = {}
    for ev in parse_track_text(text, {}):
        names = [ev.name] if ev.kind == "percussion" else [i["name"] for i in (ev.items or [])]
        out.setdefault(int(ev.start // bar_beats), []).extend(n for n in names if n)
    return out


def _has_tom(names):
    return any(n.startswith("tom") for n in names)


def test_section_end_bars_come_from_the_boxes_of_other_tracks():
    p = Project(tempo_bpm=120)
    chords = p.add_track("Accordi", "Piano", "")
    chords.clips = [Clip("Strofa", "4: C", 0.0), Clip("Ritornello", "4: F", 32.0), Clip("Coda", "4: G", 50.0)]
    p.add_track("Batteria", "Drums", "").clips = [Clip("Groove", "4: kick", 16.0)]
    assert section_end_bars(p, 0.0, 16, 4.0, exclude_track_name="Batteria") == [7]   # 50 non e' a inizio battuta
    assert section_end_bars(p, 16.0, 16, 4.0, exclude_track_name="Batteria") == [3]
    assert section_end_bars(p, 0.0, 8, 4.0, exclude_track_name="Batteria") == []      # l'ultima battuta e' il finale


def test_drums_fill_at_the_end_of_each_section_then_crash():
    plain = generate_drum_pattern("rock", 12, fill_every=0)
    sections = generate_drum_pattern("rock", 12, fill_every=0, section_fill_bars=[3, 7])
    bars = _bars(sections)
    assert not any(_has_tom(names) for names in _bars(plain).values())
    assert _has_tom(bars[3]) and _has_tom(bars[7]) and not _has_tom(bars[5])
    assert "crash" in bars[4] and "crash" in bars[8]
    # con i fill a frasi, quello di sezione e' comunque completo
    phrase = _bars(generate_drum_pattern("rock", 12, fill_every=4, phrase_fills=True, section_fill_bars=[5]))
    assert _has_tom(phrase[5])


def test_bass_attacks_fall_on_the_kicks():
    p = Project(tempo_bpm=120)
    drums = p.add_track("Batteria", "Drums", "16: kick 3r snare 2r kick kick r r r snare 3r " * 4)
    kicks = kick_beats_of_track(p, drums)
    assert kicks[:3] == [0.0, 1.75, 2.0] and len(kicks) == 12
    chords = extract_chords_from_track("4: 4C 4G 4Am 4F", {})
    bass = generate_bass_from_chords(chords, "root", kick_beats=kicks)
    starts = [ev.start for ev in parse_track_text(bass, {}) if ev.kind == "note"]
    assert starts == kicks
    # dopo start_beat: i colpi prima si scartano
    assert kick_beats_of_track(p, drums, start_beat=4.0)[:3] == [0.0, 1.75, 2.0]


def test_bass_on_kicks_always_states_the_chord_change():
    chords = extract_chords_from_track("4: 4C 4G", {})
    bass = generate_bass_from_chords(chords, "root", kick_beats=[1.0, 5.0])
    notes = [(ev.start, ev.letter) for ev in parse_track_text(bass, {}) if ev.kind == "note"]
    assert notes == [(0.0, "c"), (1.0, "c"), (4.0, "g"), (5.0, "g")]


def test_reharmonize_keeps_durations_rests_and_untouched_spelling():
    text = "4: 4Bb 4Gm 2r 2Eb 4F7"
    assert reharmonize_text(text, {}, "Bb", 0.0) == text
    rich = reharmonize_text(text, {}, "Bb", 1.0, seed=3)
    assert rich != text
    events = parse_track_text(rich, {})
    assert sum(ev.duration for ev in events) == pytest.approx(16.0)
    assert [ev.start for ev in events if ev.kind == "rest"] == [8.0]
    assert not any("#" in (ev.symbol or "") for ev in events)         # in Sib si scrive in bemolle
    assert reharmonize_text(text, {}, "Bb", 1.0, seed=3) == rich       # riproducibile


def test_reharmonize_refuses_notes():
    with pytest.raises(ValueError):
        reharmonize_text("4: c d e f", {}, "C", 0.5)


def test_track_end_beat_is_where_generated_text_goes():
    p = Project(tempo_bpm=120)
    assert track_end_beat(p, p.add_track("Vuota", "Piano", "")) == 0.0
    assert track_end_beat(p, p.add_track("Piena", "Piano", "4: c d e f g")) == 5.0


# ---------------------------------------------------------------------------
# Dialoghi (offscreen)
# ---------------------------------------------------------------------------

def _qt():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _song():
    p = Project(name="t", tempo_bpm=100)
    chords = p.add_track("Accordi", "Piano", "")
    chords.clips = [Clip("Strofa", "4: 4C 4G 4Am 4F", 0.0), Clip("Ritornello", "4: 4F 4G 4C 4C", 16.0)]
    chords.text = "4: 4C 4G 4Am 4F 4F 4G 4C 4C"
    p.add_track("Drums", "Drums", "")
    return p


def test_drum_dialog_offers_section_fills_when_the_song_has_boxes():
    _qt()
    from gui.rhythm_generate_dialog import DrumGenerateDialog
    dlg = DrumGenerateDialog(None, _song(), "Drums", "prova", default_bars=8, track_name="Drums")
    dlg.fill_every_spin.setValue(0)
    assert dlg.section_fills_check.isEnabled() and dlg.section_fills_check.isChecked()
    assert _has_tom(_bars(dlg._generate_text(seed=1))[3])
    dlg.section_fills_check.setChecked(False)
    assert not _has_tom(_bars(dlg._generate_text(seed=1))[3])
    dlg.reject()
    lonely = Project(tempo_bpm=100)
    lonely.add_track("Drums", "Drums", "")
    dlg = DrumGenerateDialog(None, lonely, "Drums", "prova", default_bars=8, track_name="Drums")
    assert not dlg.section_fills_check.isEnabled()
    dlg.reject()


def test_bass_dialog_follows_the_kick_of_a_drum_track():
    _qt()
    from gui.rhythm_generate_dialog import BassGenerateDialog, chord_source_tracks
    p = _song()
    p.get_track("Drums").text = "16: kick 3r snare 2r kick kick r r r snare 3r " * 8
    p.add_track("Basso", "Bass", "")
    dlg = BassGenerateDialog(None, p, "Bass", "prova", chord_source_tracks(p, "Basso"), default_bars=8,
                             track_name="Basso")
    assert [dlg.kick_combo.itemText(i) for i in range(dlg.kick_combo.count())] == ["nessuna", "Drums"]
    dlg.kick_combo.setCurrentIndex(1)
    starts = [ev.start for ev in parse_track_text(dlg._generate_text(seed=1), {}) if ev.kind == "note"]
    assert starts[:3] == [0.0, 1.75, 2.0]
    dlg.reject()


def test_reharmonize_dialog_previews_and_returns_the_new_box():
    _qt()
    from gui.reharmonize_dialog import ReharmonizeDialog, can_reharmonize
    p = _song()
    assert can_reharmonize("4: 4C 4G", p.patterns) and not can_reharmonize("4: c d e f", p.patterns)
    dlg = ReharmonizeDialog(None, p, "4: 4C 4Am 4F 4G 4C", "Strofa")
    assert dlg.key_combo.currentText() == "C"
    dlg.richness.setValue(0)
    assert dlg.result_text() == "4: 4C 4Am 4F 4G 4C"
    dlg.richness.setValue(100)
    seen = {dlg.result_text()}
    for _ in range(4):
        dlg._reroll()
        seen.add(dlg.result_text())
    assert len(seen) > 1
    dlg.reject()
