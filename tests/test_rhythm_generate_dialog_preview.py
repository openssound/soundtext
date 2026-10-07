"""Test GUI (offscreen) dell'ascolto nei dialoghi Genera batteria/basso:
▶ suona l'anteprima (con o senza le altre tracce), ■ e la chiusura fermano."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import _config_isolation  # noqa: F401,E402

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox  # noqa: E402

_app = QApplication.instance() or QApplication([])

from core.model import Project  # noqa: E402
from gui.rhythm_generate_dialog import (  # noqa: E402
    BassGenerateDialog, DrumGenerateDialog, MelodyGenerateDialog, ChordProgressionDialog,
    COMPING_STYLE_LABELS, RIFF_STYLE_LABELS,
)


class FakePlayback:
    def __init__(self):
        self.played = []
        self.stops = 0

    def play(self, project, **kwargs):
        self.played.append(project)

    def stop(self):
        self.stops += 1


def _project():
    p = Project(name="t", tempo_bpm=100)
    p.add_track("Piano", "Piano", "4: [c*4 e*4 g*4] [f*4 a*4 c*5]")
    p.add_track("Drums", "Drums", "16: kick r snare r")   # traccia di destinazione
    p.tracks[0].solo = True
    return p


def test_drum_preview_plays_generated_text_with_other_tracks_but_not_destination():
    dlg = DrumGenerateDialog(None, _project(), "Drums", "traccia 'Drums'", default_bars=2, track_name="Drums")
    dlg._playback = FakePlayback()
    dlg._play_preview()
    (preview,) = dlg._playback.played
    names = [t.name for t in preview.tracks]
    assert names == ["Piano", "Anteprima generata"]           # niente vecchio contenuto di Drums
    assert preview.tracks[-1].text == dlg.preview_edit.toPlainText().strip()
    assert preview.tracks[-1].instrument_name == "Drums"
    assert not any(t.solo for t in preview.tracks)             # il Solo non deve silenziare l'anteprima
    assert preview.tempo_bpm == 100
    assert dlg._playback.stops >= 1                            # ferma quanto suonava prima


def test_preview_alone_when_checkbox_off_and_uses_edited_text():
    dlg = DrumGenerateDialog(None, _project(), "Drums", "traccia 'Drums'", default_bars=2, track_name="Drums")
    dlg._playback = FakePlayback()
    dlg.with_others_check.setChecked(False)
    dlg.preview_edit.setPlainText("16: kick r snare r")         # modifica a mano
    dlg._play_preview()
    (preview,) = dlg._playback.played
    assert [t.name for t in preview.tracks] == ["Anteprima generata"]
    assert preview.tracks[0].text == "16: kick r snare r"


def test_bass_preview_and_stop_on_close_and_stop_button():
    p = _project()
    dlg = BassGenerateDialog(None, p, "Bass", "traccia 'Basso'", [("Piano", p.tracks[0].text)],
                              default_bars=2, track_name="Basso")
    dlg._playback = FakePlayback()
    dlg._play_preview()
    (preview,) = dlg._playback.played
    assert [t.name for t in preview.tracks] == ["Piano", "Drums", "Anteprima generata"]  # "Basso" non c'e' ancora
    assert preview.tracks[-1].instrument_name == "Bass"
    stops = dlg._playback.stops
    dlg._stop_preview()
    assert dlg._playback.stops == stops + 1
    dlg.reject()                                                # chiusura: ferma l'anteprima
    assert dlg._playback.stops == stops + 2


def test_invalid_or_empty_preview_does_not_play():
    dlg = DrumGenerateDialog(None, _project(), "Drums", "traccia 'Drums'", default_bars=2, track_name="Drums")
    dlg._playback = FakePlayback()
    shown = []
    QMessageBox.information = staticmethod(lambda *a, **k: shown.append("info"))
    QMessageBox.critical = staticmethod(lambda *a, **k: shown.append("critical"))
    dlg.preview_edit.setPlainText("")
    dlg._play_preview()
    dlg.preview_edit.setPlainText("16: nonesiste!!")
    dlg._play_preview()
    assert dlg._playback.played == [] and shown == ["info", "critical"]


def test_variability_slider_zero_is_the_plain_pattern_and_reroll_changes_it():
    from core.rhythm_generate import generate_drum_pattern
    dlg = DrumGenerateDialog(None, _project(), "Drums", "traccia 'Drums'", default_bars=8, track_name="Drums")
    assert dlg.variability_slider.value() == 35 and dlg.variability_label.text() == "35%"
    dlg.style_combo.setCurrentIndex(dlg.style_combo.findData("rock"))
    dlg.variability_slider.setValue(0)
    assert dlg.variability_label.text() == "0%"
    plain = generate_drum_pattern("rock", bars=8, fill_every=4, phrase_fills=True)
    assert dlg.preview_edit.toPlainText() == plain                  # 0% = disegno di sempre
    dlg.variability_slider.setValue(80)
    with_var = dlg.preview_edit.toPlainText()
    assert with_var != plain
    dlg._seed = 123
    dlg._regenerate_preview()
    first = dlg.preview_edit.toPlainText()
    dlg._regenerate_preview()
    assert dlg.preview_edit.toPlainText() == first                  # stesso seme = stesso testo
    seen = set()
    for _ in range(6):
        dlg.reroll_btn.click()
        seen.add(dlg.preview_edit.toPlainText())
    assert len(seen) > 1                                            # "Nuova variazione" cambia il risultato


def test_melody_dialog_lists_comping_styles_for_polyphonic_instrument():
    p = _project()
    dlg = MelodyGenerateDialog(
        None, p, "Piano", "traccia 'Organo'", [("Drums", p.tracks[1].text)],
        polyphonic=True, default_octave=4, range_low=21, range_high=108,
        default_bars=2, track_name="Organo",
    )
    labels = [dlg.style_combo.itemData(i) for i in range(dlg.style_combo.count())]
    assert labels == [v for v, _ in COMPING_STYLE_LABELS]
    assert dlg.octave_spin.value() == 4


def test_melody_dialog_lists_riff_styles_for_monophonic_instrument():
    p = _project()
    dlg = MelodyGenerateDialog(
        None, p, "Trumpet", "traccia 'Tromba'", [("Piano", p.tracks[0].text)],
        polyphonic=False, default_octave=4, range_low=52, range_high=82,
        default_bars=2, track_name="Tromba",
    )
    labels = [dlg.style_combo.itemData(i) for i in range(dlg.style_combo.count())]
    assert labels == [v for v, _ in RIFF_STYLE_LABELS]


def test_melody_preview_plays_generated_text_with_other_tracks_but_not_destination():
    p = _project()
    dlg = MelodyGenerateDialog(
        None, p, "Trumpet", "traccia 'Tromba'", [("Piano", p.tracks[0].text)],
        polyphonic=False, default_octave=4, range_low=52, range_high=82,
        default_bars=2, track_name="Tromba",
    )
    dlg._playback = FakePlayback()
    dlg._play_preview()
    (preview,) = dlg._playback.played
    names = [t.name for t in preview.tracks]
    assert names == ["Piano", "Drums", "Anteprima generata"]
    assert preview.tracks[-1].instrument_name == "Trumpet"
    assert not any(t.solo for t in preview.tracks)


def test_melody_dialog_clamps_notes_to_instrument_range():
    from core.chords import midi_note, note_name_to_pc
    from core.notation import parse_track_text

    p = Project(name="t")
    p.add_track("Piano", "Piano", "4: Cmaj7*4 Fmaj7*4")
    dlg = MelodyGenerateDialog(
        None, p, "Trumpet", "traccia 'Tromba'", [("Piano", p.tracks[0].text)],
        polyphonic=False, default_octave=7, range_low=52, range_high=82,
        default_bars=2, track_name="Tromba",
    )
    dlg.octave_spin.setValue(7)  # deliberatamente fuori registro: deve rientrare comunque
    events = [e for e in parse_track_text(dlg.preview_edit.toPlainText(), {}, default_octave=4)
              if e.kind == "note"]
    assert events
    assert all(52 <= midi_note(note_name_to_pc(e.letter), e.octave) <= 82 for e in events)


def test_bass_dialog_passes_variability_and_seed():
    p = Project(name="t")
    p.add_track("Piano", "Piano", "4: 4[a*3 c*4 e*4 g*4] 4[d*3 f#*3 a*3 c*4] 4Gmaj7 4Cmaj7")  # accordi da 4 beat
    dlg = BassGenerateDialog(None, p, "Bass", "traccia 'Basso'", [("Piano", p.tracks[0].text)],
                              default_bars=4, track_name="Basso")
    dlg.style_combo.setCurrentIndex(dlg.style_combo.findData("blues"))
    dlg.variability_slider.setValue(0)
    plain = dlg.preview_edit.toPlainText()
    dlg.variability_slider.setValue(90)
    outs = set()
    for _ in range(6):
        dlg.reroll_btn.click()
        outs.add(dlg.preview_edit.toPlainText())
    assert len(outs) > 1        # "Nuova variazione" produce risultati diversi
    assert outs != {plain}      # e con variabilita' alta non torna sempre il disegno di base


def test_chord_progression_dialog_starts_from_project_key_and_filters_styles_by_mode():
    from core.rhythm_generate import PROGRESSION_STYLES
    p = Project(name="t", key="Dm")
    p.add_track("Piano", "Piano", "")
    dlg = ChordProgressionDialog(None, p, "Piano", "traccia 'Piano'", track_name="Piano")
    assert dlg.key_combo.currentData() == "Dm"
    styles = [dlg.style_combo.itemData(i) for i in range(dlg.style_combo.count())]
    assert styles and all(PROGRESSION_STYLES[s]["mode"] == "minor" for s in styles)
    # giro intero, tonica per prima (con la variabilita' puo' durare meta': dominante secondaria dopo)
    assert re.match(r"4: [24]?Dm", dlg.preview_edit.toPlainText())
    dlg.key_combo.setCurrentIndex(dlg.key_combo.findData("G"))
    styles = [dlg.style_combo.itemData(i) for i in range(dlg.style_combo.count())]
    assert styles and all(PROGRESSION_STYLES[s]["mode"] == "major" for s in styles)
    assert re.match(r"4: [24]?G(?!b|#)", dlg.preview_edit.toPlainText())
    dlg.variability_slider.setValue(0)
    dlg.style_combo.setCurrentIndex(dlg.style_combo.findData("pop"))
    dlg.bars_spin.setValue(8)
    dlg.chord_duration_combo.setCurrentIndex(0)                   # mezza battuta
    assert dlg.preview_edit.toPlainText() == "4: " + " ".join(["2G", "2D", "2Em", "2C"] * 4)
    dlg.accept()
    assert dlg.result_text() == dlg.preview_edit.toPlainText()


def test_chord_progression_dialog_uses_c_major_without_a_project_key():
    p = Project(name="t")
    dlg = ChordProgressionDialog(None, p, "Piano", "traccia 'Piano'", default_bars=4)
    assert dlg.key_combo.currentData() == "C"
    assert dlg.bars_spin.value() == 4



def test_chord_progression_dialog_proposes_key_of_the_previous_box():
    from core.model import Clip
    from gui.rhythm_generate_dialog import last_box_key
    p = Project(name="t")                  # tonalita' del progetto non impostata
    t = p.add_track("Piano", "Piano", "")
    t.clips = [Clip("Strofa", "4: 4Em 4C 4G 4D", 0.0), Clip("Ritornello", "4: 4Am 4Dm 4E7 4Am", 16.0)]
    assert last_box_key(p, t) == "Am"      # l'ultimo box, non il primo
    dlg = ChordProgressionDialog(None, p, "Piano", "nuovo box", track_name="Piano",
                                 default_key=last_box_key(p, t))
    assert dlg.key_combo.currentData() == "Am"


def test_chord_progression_dialog_prefers_the_project_key_when_set():
    p = Project(name="t", key="Eb")
    dlg = ChordProgressionDialog(None, p, "Piano", "nuovo box", default_key="Am")
    assert dlg.key_combo.currentData() == "Eb"


def test_last_box_key_falls_back_when_there_is_nothing_to_read():
    from gui.rhythm_generate_dialog import last_box_key
    p = Project(name="t", key="D")
    t = p.add_track("Piano", "Piano", "")
    assert last_box_key(p, t) is None
    t.text = "4: [c e"                     # errore di sintassi
    assert last_box_key(p, t) is None
    dlg = ChordProgressionDialog(None, p, "Piano", "nuovo box", default_key=last_box_key(p, t))
    assert dlg.key_combo.currentData() == "D"


class _ClockPlayback(FakePlayback):
    """Riproduzione finta in streaming: position_seconds dice a che punto e'."""

    def __init__(self):
        super().__init__()
        self.seconds = None

    def play(self, project, **kwargs):
        super().play(project, **kwargs)
        self.seconds = 0.0

    def stop(self):
        super().stop()
        self.seconds = None

    def is_playing(self):
        return self.seconds is not None

    def position_seconds(self):
        return self.seconds


def _highlighted(dlg):
    sel = dlg.preview_edit.extraSelections()
    return sel[0].cursor.selectedText() if sel else None


def test_preview_highlights_what_is_playing():
    p = Project(name="t", tempo_bpm=120)               # 1 beat = 0,5 s
    dlg = ChordProgressionDialog(None, p, "Piano", "nuovo box", track_name="Piano")
    dlg._playback = _ClockPlayback()
    dlg.preview_edit.setPlainText("4: 4C 4F 4G 4C")
    dlg._play_preview()
    for seconds, expected in ((0.1, "4C"), (2.2, "4F"), (4.5, "4G")):
        dlg._playback.seconds = seconds
        dlg._play_highlight._update()
        assert _highlighted(dlg) == expected, seconds
    dlg.preview_edit.setPlainText("4: 4Am 4F")          # testo cambiato mentre suona
    dlg._play_highlight._update()
    assert _highlighted(dlg) is None
    dlg._stop_preview()
    assert not dlg._play_highlight.is_active() and _highlighted(dlg) is None


def test_preview_highlight_stops_when_playback_ends():
    dlg = ChordProgressionDialog(None, Project(name="t"), "Piano", "nuovo box", track_name="Piano")
    dlg._playback = _ClockPlayback()
    dlg._play_preview()
    dlg._playback.seconds = 0.1
    dlg._play_highlight._update()
    assert _highlighted(dlg) is not None
    dlg._playback.seconds = None                          # finita da sola
    dlg._play_highlight._start_wall = 0.0                 # l'audio era partito
    dlg._play_highlight._update()
    assert not dlg._play_highlight.is_active() and _highlighted(dlg) is None

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK ", name)


def test_drum_dialog_offers_only_styles_for_the_project_meter():
    p = _project()
    p.time_sig = "3/4"
    dlg = DrumGenerateDialog(None, p, "Drums", "traccia 'Drums'", default_bars=2, track_name="Drums")
    styles = [dlg.style_combo.itemData(i) for i in range(dlg.style_combo.count())]
    assert styles == ["waltz", "jazz_waltz"]
    assert dlg.button_box.button(dlg.button_box.StandardButton.Ok).isEnabled()
    from core.notation import parse_track_text
    events = parse_track_text(dlg.preview_edit.toPlainText(), {})
    assert max(e.start + e.duration for e in events) == 6.0   # 2 battute di 3/4
    dlg.reject()


def test_drum_dialog_explains_an_unsupported_meter():
    p = _project()
    p.time_sig = "9/8"
    dlg = DrumGenerateDialog(None, p, "Drums", "traccia 'Drums'", default_bars=2, track_name="Drums")
    assert not dlg.button_box.button(dlg.button_box.StandardButton.Ok).isEnabled()
    assert "9/8" in dlg._unsupported_reason()
    dlg.reject()


def test_bass_dialog_uses_bars_of_the_project_meter():
    p = _project()
    p.time_sig = "3/4"
    dlg = BassGenerateDialog(None, p, "Bass", "traccia 'Bass'", other_tracks=[("Piano", "4: 3C 3G")],
                             default_bars=4)
    from core.notation import parse_track_text
    events = parse_track_text(dlg.preview_edit.toPlainText(), {})
    assert max(e.start + e.duration for e in events) == 12.0   # 4 battute di 3/4
    dlg.reject()


def test_comping_dialog_uses_voice_leading_by_default_and_riff_dialog_has_none():
    from core.rhythm_generate import extract_chords_from_track, generate_melodic_line
    p = Project(name="t")
    p.add_track("Chords", "Piano", "4: 4C 4F 4G 4Am")
    dlg = MelodyGenerateDialog(
        None, p, "Organ", "traccia 'Organo'", [("Chords", p.tracks[0].text)],
        polyphonic=True, default_octave=4, range_low=36, range_high=96,
        default_bars=4, track_name="Organo",
    )
    dlg.style_combo.setCurrentIndex(dlg.style_combo.findData("sustained"))
    dlg.variability_slider.setValue(0)
    assert dlg.voice_leading_check.isChecked()
    spans = extract_chords_from_track(p.tracks[0].text, {})
    kwargs = dict(octave=4, range_low=36, range_high=96, polyphonic=True, variation_every=4,
                  min_total_beats=16.0, bar_beats=4.0)
    led = generate_melodic_line(spans, "sustained", voice_leading=True, **kwargs)
    assert dlg.preview_edit.toPlainText() == led
    dlg.voice_leading_check.setChecked(False)
    assert dlg.preview_edit.toPlainText() == generate_melodic_line(spans, "sustained", **kwargs) != led

    riff = MelodyGenerateDialog(
        None, p, "Trumpet", "traccia 'Tromba'", [("Chords", p.tracks[0].text)],
        polyphonic=False, default_octave=4, range_low=52, range_high=82,
        default_bars=4, track_name="Tromba",
    )
    assert not hasattr(riff, "voice_leading_check")


def test_progression_dialog_final_cadence_checkbox():
    p = Project(name="t", tempo_bpm=100)
    dlg = ChordProgressionDialog(None, p, "Piano", "nuovo box", default_bars=8)
    dlg.variability_slider.setValue(0)
    assert not dlg.ending_check.isChecked()
    assert dlg.preview_edit.toPlainText() == "4: 4C 4G 4Am 4F 4C 4G 4Am 4F"
    dlg.ending_check.setChecked(True)
    assert dlg.preview_edit.toPlainText() == "4: 4C 4G 4Am 4F 4C 4G 2Am 2G7 4C"
