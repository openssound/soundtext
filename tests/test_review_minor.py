"""Note minori della revisione: "Trasponi" sui richiami %Nome/&Nome,
ascolto di box e selezioni con le ancore bar=N, rinomina di un file della
libreria MIDI nei richiami &Nome del brano."""

from st_language import notation
from st_language.notation import PitchRewriter, parse_track_text, rewrite_tokens, tokenize

from core.arrangement import anchored_preview_text, has_bar_anchor
from core.model import Clip, Project


def _transpose(text, semitones):
    return rewrite_tokens(text, PitchRewriter(semitones, 4))


# ------------------------------------------------------------------ Trasponi

def test_transpose_rewrites_pattern_references():
    assert _transpose("4: c %Giro 2%Giro+3 %Giro-2", 2) == "4: d*4 %Giro+2 2%Giro+5 %Giro"
    assert _transpose("%Giro+2", -2) == "%Giro"
    assert _transpose("%Giro", 0) == "%Giro"


def test_transposed_pattern_reference_sounds_transposed():
    patterns = {"Giro": notation.Pattern("Giro", tokenize("4: c e g"))}
    before = [e.letter for e in parse_track_text("%Giro", patterns) if e.kind == "note"]
    after = [e.letter for e in parse_track_text(_transpose("%Giro", 2), patterns) if e.kind == "note"]
    assert before == ["c", "e", "g"] and after == ["d", "f#", "a"]


def test_transpose_rewrites_midi_references():
    # il nome sta fra le virgolette: quello che segue e' sempre la trasposizione
    assert _transpose('&"Riff" 2&"Solo/Riff"+1', 3) == '&"Riff"+3 2&"Solo/Riff"+4'
    assert _transpose('&"Riff-2"', 1) == '&"Riff-2"+1'          # il file si chiama 'Riff-2'
    assert _transpose('&"Riff"+1', -3) == '&"Riff"-2'
    assert _transpose('&"bass line"-2', 2) == '&"bass line"'


# ------------------------------------------------------------------ ascolto con le ancore

def test_anchored_preview_text_pads_only_texts_with_anchors():
    assert anchored_preview_text("4: c d", 8, {}) == ("4: c d", 0.0)
    assert anchored_preview_text("4: c bar=5 d", 0, {}) == ("4: c bar=5 d", 0.0)
    text, lead = anchored_preview_text("4: c bar=5 d", 8, {})
    assert lead == 8.0
    starts = [e.start for e in parse_track_text(text, {}) if e.kind == "note"]
    assert [s - lead for s in starts] == [0, 8]          # d alla battuta 5 del brano, non alla 5 contata da 0


def test_anchor_inside_a_pattern_is_found():
    patterns = {"Coda": notation.Pattern("Coda", tokenize("bar=9 4: c"))}
    assert has_bar_anchor("%Coda", patterns)
    assert not has_bar_anchor("4: c %Nessuno", patterns)


# ------------------------------------------------------------------ rinomina nella libreria MIDI

def _project():
    project = Project()
    project.add_pattern("Usa", '&"Blues/riff" 2&"riff"+2')
    project.add_track("Basso", "Bass", '&"riff" &"riff"-1 &"riffone" &"Blues/riff"-2 (&"riff") &"riff-2"')
    voce = project.add_track("Voce", "Piano", "")
    voce.clips = [Clip(name="A", text='3&"Blues/riff"'), Clip(name="B", text='&"riff2"', start_beat=4)]
    return project


def test_rename_midi_ref_keeps_multiplier_and_transposition():
    project = _project()
    assert project.rename_midi_ref(["riff"], "groove", apply=False) == 4
    assert project.get_track("Basso").text.startswith('&"riff" ')          # apply=False: niente cambia
    assert project.rename_midi_ref(["riff"], "groove") == 4
    assert project.get_track("Basso").text == \
        '&"groove" &"groove"-1 &"riffone" &"Blues/riff"-2 (&"groove") &"riff-2"'
    assert project.patterns["Usa"].tokens == ['&"Blues/riff"', '2&"groove"+2']
    assert project.rename_midi_ref(["Blues/riff"], "Funk/groove") == 3
    assert [c.text for c in project.get_track("Voce").clips] == ['3&"Funk/groove"', '&"riff2"']
    assert '&"Funk/groove"-2' in project.get_track("Basso").text
