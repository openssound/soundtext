"""
"Arrangia il brano": dalle sezioni della traccia degli accordi (i suoi box:
Intro, Strofa, Pre-ritornello, Ritornello, Ponte, Finale...) tutte le parti
in un passaggio, una sezione alla volta:

- l'intensita' di ogni sezione viene dal suo nome (SECTION_INTENSITY: la
  strofa leggera, il pre-ritornello in crescendo, il ritornello pieno...),
  modificabile prima di generare;
- batteria con un fill completo alla fine di ogni sezione (salvo l'ultima,
  che chiude con il colpo finale); un'intro suona senza batteria ne' basso;
- basso e accompagnamento sugli accordi di quella sezione;
- ogni parte e' un box per sezione, allineato al box degli accordi, con lo
  stesso nome: si possono rigenerare o modificare uno per uno.
"""

import math
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from .i18n import tr
from .model import Clip, Project, Track

# Parole del nome di un box -> intensita' (core.rhythm_generate.INTENSITIES).
# La prima che compare nel nome vale; il resto e' "normal".
SECTION_INTENSITY = [
    (("intro", "introduzione", "inizio"), "intro"),
    (("pre-ritornello", "preritornello", "pre ritornello", "pre-rit", "pre-chorus", "prechorus",
      "pre chorus", "bridge", "ponte", "build"), "build"),
    (("ritornello", "rit", "chorus", "refrain", "climax", "finale pieno"), "full"),
    (("strofa", "verse", "couplet", "estrofa"), "light"),
    (("outro", "coda", "finale", "fine", "ending"), "outro"),
    (("assolo", "solo", "special", "interludio", "interlude"), "normal"),
]


def section_intensity(name: str) -> str:
    """L'intensita' di una sezione dal suo nome: 'intro', 'light', 'normal',
    'build', 'full' o 'outro'."""
    lower = name.lower()
    for words, level in SECTION_INTENSITY:
        for word in words:
            if re.search(rf"(^|[^a-z]){re.escape(word)}([^a-z]|$)", lower):
                return level
    return "normal"


@dataclass
class Section:
    name: str
    start_beat: float
    length_beats: float
    text: str
    intensity: str


def song_sections(project: Project, chord_track: Track) -> List[Section]:
    """Le sezioni del brano: i box della traccia degli accordi, in ordine."""
    from .arrangement import clip_duration_beats
    out = []
    for clip in sorted(chord_track.clips, key=lambda c: c.start_beat):
        length = clip_duration_beats(clip.text, project.patterns, chord_track.instrument.default_octave,
                                     start_beat=clip.start_beat, meter=project.meter())
        if length > 0:
            out.append(Section(clip.name, clip.start_beat, length, clip.text, section_intensity(clip.name)))
    return out


@dataclass
class ArrangeOptions:
    drum_style: Optional[str] = "rock"
    bass_style: Optional[str] = "root"
    comping_style: Optional[str] = "block_chords"
    comping_instrument: str = "Piano"
    bass_instrument: str = "Bass"
    variability: float = 0.3
    seed: Optional[int] = None


def _level(intensity: str) -> str:
    return {"intro": "light", "outro": "light"}.get(intensity, intensity)


def arrange(project: Project, sections: List[Section], options: ArrangeOptions,
            bar_beats: float) -> Dict[str, List[Clip]]:
    """{"drums"/"bass"/"comping": [box, uno per sezione]} delle parti scelte
    (uno stile None = quella parte non si genera). Solleva ValueError se le
    sezioni non hanno accordi."""
    from .instruments import get_instrument
    from .rhythm_generate import (extract_chords_from_track, generate_bass_from_chords, generate_drum_pattern,
                                  generate_melodic_line)
    parts: Dict[str, List[Clip]] = {"drums": [], "bass": [], "comping": []}
    comp = get_instrument(options.comping_instrument)
    for k, section in enumerate(sections):
        last = k == len(sections) - 1
        level = _level(section.intensity)
        seed = None if options.seed is None else options.seed + k
        chords = extract_chords_from_track(section.text, project.patterns)
        bars = max(1, math.ceil(section.length_beats / bar_beats - 1e-6))
        if options.drum_style and section.intensity != "intro":
            fills = [] if last else [bars - 1]
            text = generate_drum_pattern(options.drum_style, bars, fill_every=0, variability=options.variability,
                                         seed=seed, intensity=level, phrase_fills=True,
                                         ending=last and bars > 1, section_fill_bars=fills)
            parts["drums"].append(Clip(section.name, text, section.start_beat))
        if not chords:
            continue
        if options.bass_style and section.intensity != "intro":
            text = generate_bass_from_chords(chords, options.bass_style, octave=2,
                                             min_total_beats=section.length_beats, variability=options.variability,
                                             seed=seed, bar_beats=bar_beats, intensity=level)
            parts["bass"].append(Clip(section.name, text, section.start_beat))
        if options.comping_style:
            text = generate_melodic_line(chords, options.comping_style, comp.default_octave, comp.range_low,
                                         comp.range_high, True, min_total_beats=section.length_beats,
                                         variability=options.variability, seed=seed, bar_beats=bar_beats,
                                         intensity=level, voice_leading=True)
            parts["comping"].append(Clip(section.name, text, section.start_beat))
    if not any(parts.values()):
        raise ValueError(tr("Nelle sezioni della traccia non ci sono accordi da arrangiare."))
    return parts
