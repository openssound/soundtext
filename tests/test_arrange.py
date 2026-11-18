"""
Test di "Arrangia il brano" (core.arrange, gui.arrange_dialog): intensita'
dalle sezioni, parti generate un box per sezione, fill di sezione e finale.

Esecuzione:
    python3 -m pytest tests/test_arrange.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)

import os

import pytest

from core.arrange import ArrangeOptions, arrange, section_intensity, song_sections
from core.model import Clip, Project
from core.notation import parse_track_text, validate_track_text


def _song():
    p = Project(tempo_bpm=100)
    acc = p.add_track("Accordi", "Piano", "")
    acc.clips = [Clip("Intro", "4: 4C 4G", 0.0), Clip("Strofa", "4: 4C 4Am 4F 4G", 8.0),
                 Clip("Pre-ritornello", "4: 4Dm 4G", 24.0), Clip("Ritornello", "4: 4F 4G 4C 4C", 32.0),
                 Clip("Finale", "4: 4C 4C", 48.0)]
    return p, acc


@pytest.mark.parametrize("name, level", [("Intro", "intro"), ("Strofa 2", "light"), ("Verse", "light"),
                                         ("Pre-ritornello", "build"), ("Ritornello", "full"),
                                         ("Chorus 2", "full"), ("Ponte", "build"), ("Finale", "outro"),
                                         ("Coda", "outro"), ("Tema", "normal")])
def test_intensity_from_the_section_name(name, level):
    assert section_intensity(name) == level


def test_parts_one_box_per_section_with_fills_and_ending():
    p, acc = _song()
    sections = song_sections(p, acc)
    assert [(s.name, s.start_beat, s.length_beats) for s in sections] == [
        ("Intro", 0.0, 8.0), ("Strofa", 8.0, 16.0), ("Pre-ritornello", 24.0, 8.0), ("Ritornello", 32.0, 16.0),
        ("Finale", 48.0, 8.0)]
    parts = arrange(p, sections, ArrangeOptions(seed=3), 4.0)
    assert [c.name for c in parts["drums"]] == ["Strofa", "Pre-ritornello", "Ritornello", "Finale"]   # intro: niente
    assert [c.name for c in parts["bass"]] == ["Strofa", "Pre-ritornello", "Ritornello", "Finale"]
    assert [c.start_beat for c in parts["comping"]] == [0.0, 8.0, 24.0, 32.0, 48.0]
    for clips in parts.values():
        for clip in clips:
            assert validate_track_text(clip.text, {})[0]
    verse = parse_track_text(parts["drums"][0].text, {})
    names = lambda ev: [ev.name] if ev.kind == "percussion" else [i["name"] for i in (ev.items or [])]   # noqa: E731
    last_bar = [n for ev in verse if 12.0 <= ev.start < 16.0 for n in names(ev)]
    assert any(n.startswith("tom") for n in last_bar)                    # fill a fine sezione
    chorus = parse_track_text(parts["drums"][2].text, {})
    assert any("ride" in names(ev) or "crash" in names(ev) for ev in chorus)   # ritornello pieno


def test_dialog_creates_the_tracks_in_one_undo_step(monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QDialog
    QApplication.instance() or QApplication([])
    from gui.arrange_dialog import ArrangeDialog
    from gui.main_window import MainWindow
    w = MainWindow()
    w.arrangement_action.setChecked(True)
    p, acc = _song()
    track = w.project.add_track("Accordi", "Piano", "")
    track.clips = acc.clips
    w.arrangement_view.on_clip_changed("Accordi")

    def fake_exec(dlg):
        assert dlg.table.rowCount() == 5
        assert dlg.table.cellWidget(0, 2).currentData() == "intro"
        dlg.table.cellWidget(1, 2).setCurrentIndex(dlg.table.cellWidget(1, 2).findData("full"))
        dlg.accept()
        return QDialog.Accepted

    monkeypatch.setattr(ArrangeDialog, "exec", fake_exec)
    w.arrange_song()
    names = [t.name for t in w.project.tracks]
    assert names == ["Accordi", "Batteria", "Basso", "Accompagnamento"]
    assert [c.name for c in w.project.get_track("Basso").clips][0] == "Strofa"
    assert w.project.get_track("Batteria").text.strip()
    w.undo()
    assert [t.name for t in w.project.tracks] == ["Accordi"]


# ---------------------------------------------------------------------------
# Finale, rallentando, stop e break, crescendo di frase, accompagnamento
# rado, modulazione, tessiture
# ---------------------------------------------------------------------------

from core.arrange import busy_bars, melody_attacks   # noqa: E402

_SOUNDING = ("note", "chord", "block", "percussion")


def _attacks(text, lo=0.0, hi=1e9):
    return [ev for ev in parse_track_text(text, {}) if ev.kind in _SOUNDING and lo - 1e-9 <= ev.start < hi - 1e-9]


def _song_with(*boxes):
    p = Project(tempo_bpm=100)
    acc = p.add_track("Accordi", "Piano", "")
    acc.clips = [Clip(name, text, start) for name, text, start in boxes]
    return p, acc


def test_ending_holds_bass_and_comping_with_a_rallentando():
    p, acc = _song_with(("Strofa", "4: 4C 4Am 4F 4G", 0.0), ("Finale", "4: 4F 4G 4C", 16.0))
    parts = arrange(p, song_sections(p, acc), ArrangeOptions(seed=5), 4.0)
    bass, comping, drums = parts["bass"][-1].text, parts["comping"][-1].text, parts["drums"][-1].text
    for text in (bass, comping, drums):
        assert validate_track_text(text, {})[0], text
    last_bass = _attacks(bass, 8.0)
    assert len(last_bass) == 1 and last_bass[0].duration == 4.0 and last_bass[0].letter.upper() == "C"
    last_comp = _attacks(comping, 8.0)
    assert len(last_comp) == 1 and last_comp[0].duration == 4.0
    tempos = [float(t.split("=")[1]) for t in drums.split() if t.startswith("tempo=")]
    assert len(tempos) >= 4 and tempos == sorted(tempos, reverse=True)
    assert tempos[0] < 100 and tempos[-1] == 75
    assert drums.index(f"tempo={tempos[-1]:g}") < drums.index("[crash kick]")   # il colpo finale gia' lento


def test_without_ending_the_lines_keep_their_pattern():
    p, acc = _song_with(("Finale", "4: 4F 4G 4C", 0.0))
    parts = arrange(p, song_sections(p, acc), ArrangeOptions(seed=5, ending=False, drum_style=None), 4.0)
    assert len(_attacks(parts["bass"][-1].text, 8.0)) > 1
    assert "tempo=" not in parts["bass"][-1].text


@pytest.mark.parametrize("name, level", [("Stop", "stop"), ("Break", "break"), ("Stop 2", "stop")])
def test_stop_and_break_from_the_name(name, level):
    assert section_intensity(name) == level


def test_stop_silences_every_part_and_break_keeps_one_hit():
    p, acc = _song_with(("Strofa", "4: 4C 4Am 4F 4G", 0.0), ("Stop", "4: 4C", 16.0),
                        ("Break", "4: 4r", 20.0), ("Ritornello", "4: 4F 4G 4C 4C", 24.0))
    parts = arrange(p, song_sections(p, acc), ArrangeOptions(seed=1), 4.0)
    for kind in ("drums", "bass", "comping"):
        names = [c.name for c in parts[kind]]
        assert "Stop" not in names
        for clip in parts[kind]:
            assert validate_track_text(clip.text, {})[0], clip.text
            end = clip.start_beat + max((ev.start + ev.duration for ev in _attacks(clip.text)), default=0.0)
            assert end <= 16.0 + 1e-9 or clip.start_beat >= 20.0 - 1e-9     # nulla suona nello Stop
        brk = next(c for c in parts[kind] if c.name == "Break")
        hits = _attacks(brk.text)
        assert len(hits) == 1 and hits[0].start == 0.0 and hits[0].duration <= 1.0
    assert "crash" in parts["drums"][1].text


def test_phrase_crescendo_and_chorus_accent():
    p, acc = _song_with(("Strofa", "4: 4C 4C 4C 4C", 0.0), ("Ritornello", "4: 4C 4C 4C 4C", 16.0))
    options = ArrangeOptions(seed=0, variability=0.0, drum_style=None, comping_style=None, bass_style="root",
                             ending=False)
    plain = arrange(p, song_sections(p, acc), ArrangeOptions(**{**options.__dict__, "phrase_dynamics": False}), 4.0)
    shaped = arrange(p, song_sections(p, acc), options, 4.0)
    verse = _attacks(shaped["bass"][0].text)
    first_of_bar = [next(ev.velocity for ev in verse if ev.start >= b * 4.0) for b in range(4)]
    assert first_of_bar == sorted(first_of_bar) and first_of_bar[0] < first_of_bar[-1]
    chorus_plain = _attacks(plain["bass"][1].text)[0].velocity
    chorus_shaped = _attacks(shaped["bass"][1].text)[0].velocity
    assert chorus_shaped >= chorus_plain + 6      # accento sull'ingresso del ritornello


def test_comping_thins_out_where_the_melody_is_busy():
    p, acc = _song_with(("Tema", "4: 4C 4F", 0.0))
    melody = p.add_track("Melodia", "Trumpet", "16: c d e f g a b c d e f g a b c d 4: 4e")
    attacks = melody_attacks(p, melody)
    assert busy_bars(attacks, 0.0, 8.0, 4.0) == {0}
    options = ArrangeOptions(seed=2, drum_style=None, bass_style=None, comping_style="arpeggio_up",
                             variability=0.0, ending=False, phrase_dynamics=False)
    free = arrange(p, song_sections(p, acc), options, 4.0)["comping"][0].text
    spaced = arrange(p, song_sections(p, acc), ArrangeOptions(**{**options.__dict__, "melody_track": "Melodia"}),
                     4.0)["comping"][0].text
    assert validate_track_text(spaced, {})[0]
    assert len(_attacks(spaced, 0.0, 4.0)) < len(_attacks(spaced, 4.0, 8.0))
    assert len(_attacks(spaced, 0.0, 4.0)) < len(_attacks(free, 0.0, 4.0))
    assert _attacks(spaced, 4.0, 8.0) == _attacks(free, 4.0, 8.0)       # dove la melodia tiene, niente cambia


def test_modulation_raises_the_last_chorus_by_a_tone():
    p, acc = _song_with(("Ritornello", "4: 4F 4G 4C 4Am", 0.0), ("Strofa", "4: 4C 4G", 16.0),
                        ("Ritornello", "4: 4F 4G 4C 4Am", 24.0), ("Finale", "4: 4C", 40.0))
    parts = arrange(p, song_sections(p, acc), ArrangeOptions(seed=4, modulation=2), 4.0)
    assert [(c.name, c.start_beat) for c in parts["chords"]] == [("Ritornello", 24.0), ("Finale", 40.0)]
    first = [(ev.symbol) for ev in parse_track_text(acc.clips[0].text, {}) if ev.kind == "chord"]
    last = [(ev.symbol) for ev in parse_track_text(parts["chords"][0].text, {}) if ev.kind == "chord"]
    assert first == ["F", "G", "C", "Am"] and last == ["G", "A", "D", "Bm"]
    bass = parse_track_text(parts["bass"][2].text, {})
    assert bass[0].letter.upper() == "G"           # il basso segue gli accordi trasposti
    assert "chords" not in arrange(p, song_sections(p, acc), ArrangeOptions(seed=4), 4.0)


@pytest.mark.parametrize("voice", ["soprano", "contralto", "tenore", "basso"])
def test_vocal_range_keeps_the_melody_inside(voice):
    from core.lyrics_melody import lyrics_to_melody
    from core.melody_generate import VOICE_RANGES, voice_octave
    from core.rhythm_generate import extract_chords_from_track, generate_melodic_line
    from core.chords import pitch_to_midi
    low, high = VOICE_RANGES[voice]
    chords = extract_chords_from_track("4: 4C 4Am 4F 4G 4C 4Am 4F 4G", {})
    texts = [generate_melodic_line(chords, style, voice_octave(voice), low, high, False, min_total_beats=32,
                                   variability=0.5, seed=seed)
             for style in ("melody_aaba", "melody_lively", "riff_short") for seed in range(3)]
    texts.append(lyrics_to_melody("la canzone del mare\nche torna sempre qui", chords, "C", voice_octave(voice),
                                  low, high))
    for text in texts:
        for ev in parse_track_text(text, {}):
            if ev.kind == "note":
                assert low <= pitch_to_midi(ev.letter, ev.octave) <= high, (voice, text)


def test_dialog_modulation_transposes_the_chord_boxes_in_the_same_undo_step(monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QDialog
    QApplication.instance() or QApplication([])
    from gui.arrange_dialog import ArrangeDialog
    from gui.main_window import MainWindow
    w = MainWindow()
    w.arrangement_action.setChecked(True)
    track = w.project.add_track("Accordi", "Piano", "")
    track.clips = [Clip("Strofa", "4: 4C 4G", 0.0), Clip("Ritornello", "4: 4F 4C", 8.0)]
    w.arrangement_view.on_clip_changed("Accordi")
    voce = w.project.add_track("Voce", "Trumpet", "")
    voce.clips = [Clip("Strofa", "4: c*5 d*5", 0.0), Clip("Ritornello", "4: f*5 e*5", 8.0)]
    w.arrangement_view.on_clip_changed("Voce")

    def fake_exec(dlg):
        assert dlg.melody_combo.currentData() == "Voce"
        dlg.modulation_combo.setCurrentIndex(dlg.modulation_combo.findData(2))
        dlg.accept()
        return QDialog.Accepted

    monkeypatch.setattr(ArrangeDialog, "exec", fake_exec)
    w.arrange_song()
    chords = w.project.get_track("Accordi")
    assert [c.text for c in chords.clips] == ["4: 4C 4G", "4: 4G 4D"]
    assert "4G 4D" in chords.text
    assert [c.text for c in w.project.get_track("Voce").clips] == ["4: c*5 d*5", "4: g*5 f#*5"]
    w.undo()
    assert w.project.get_track("Accordi").clips[1].text == "4: 4F 4C"
    assert w.project.get_track("Voce").clips[1].text == "4: f*5 e*5"
    assert "Batteria" not in [t.name for t in w.project.tracks]


def test_modulation_also_raises_the_melody_boxes():
    """Con la modulazione sale anche la melodia (i box delle altre tracce di
    note dall'ultimo ritornello in poi): prima restava nella tonalita' di
    partenza sopra gli accordi saliti. Percussioni e tracce senza box no."""
    p, acc = _song_with(("Strofa", "4: 4C 4G", 0.0), ("Ritornello", "4: 4F 4C", 8.0))
    melody = p.add_track("Melodia", "Trumpet", "")
    melody.clips = [Clip("Strofa", "4: e*5 d*5", 0.0), Clip("Ritornello", "4: c*5 a*4", 8.0)]
    p.add_track("Libera", "Trumpet", "4: c*5")
    p.add_track("Percussioni", "Drums", "")
    parts = arrange(p, song_sections(p, acc), ArrangeOptions(seed=1, modulation=2), 4.0, chord_track="Accordi")
    assert list(parts["modulated"]) == ["Melodia"]
    [chorus] = parts["modulated"]["Melodia"]
    assert (chorus.name, chorus.start_beat, chorus.text) == ("Ritornello", 8.0, "4: d*5 b*4")
    assert "modulated" not in arrange(p, song_sections(p, acc), ArrangeOptions(seed=1), 4.0)
