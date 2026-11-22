"""Qualita' misurabile dei generatori (docs, 8.7): per ogni genere di «Un brano in 60 secondi» e per un insieme fisso di semi,
i registri delle parti non si sovrappongono, le note forti della melodia sono dell'accordo, le quinte e le ottave parallele
fra basso e melodia restano rare; per ogni stile, piu' intensita' non e' mai meno note. Le soglie sono quelle misurate sul
generatore di oggi (con un po' di margine): una modifica che peggiora una misura fa fallire il test, e va ascoltata a
confronto prima e dopo con gli stessi semi."""
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _config_isolation  # noqa: F401,E402

import pytest  # noqa: E402

from core import rhythm_generate as rg  # noqa: E402
from core.project_io import parse_project_text  # noqa: E402
from core.quicksong import GENRES_DATA, quick_song  # noqa: E402

SEEDS = (1, 2)
_cache = {}


def _notes(project, track):
    """[(inizio in beat, durata, [note MIDI])] di una traccia."""
    from st_language.midi import resolve_event_notes, sounding_events
    out = []
    for ev in sounding_events(track.parsed_events(project.patterns, meter=project.meter())):
        if ev.kind in ("control", "sustain", "tempo_marker", "rest"):
            continue
        notes, _velocity = resolve_event_notes(ev, track.instrument)
        if notes:
            out.append((ev.start, ev.duration, sorted(notes)))
    return out


def _song(genre, seed):
    key = (genre, seed)
    if key not in _cache:
        mood = GENRES_DATA[genre]["moods"][seed % len(GENRES_DATA[genre]["moods"])]
        made = quick_song({"genre": genre, "mood": mood, "duration": 45, "seed": seed, "variety": 0})
        project = parse_project_text(made["text"], "Prova")
        names = made["choices"]["instruments"]
        parts = {part: _notes(project, t) for part, name in names.items() for t in project.tracks if t.name == name
                 and part in ("melody", "bass", "comp", "comp2")}
        bar = {"4/4": 4.0, "3/4": 3.0, "6/8": 3.0, "7/8": 3.5}[made["meter"]]
        _cache[key] = (parts, bar)
    return _cache[key]


@pytest.mark.parametrize("genre", list(GENRES_DATA))
def test_registers_of_the_parts_do_not_overlap(genre):
    for seed in SEEDS:
        parts, _bar = _song(genre, seed)
        if not parts.get("melody") or not parts.get("bass") or not parts.get("comp"):
            continue
        bass = statistics.mean(n[2][0] for n in parts["bass"])
        comp = statistics.mean(sum(n[2]) / len(n[2]) for n in parts["comp"])
        melody = statistics.mean(n[2][-1] for n in parts["melody"])
        assert bass + 5 <= comp, (genre, seed, bass, comp)               # il basso sta sotto l'accompagnamento (elettronica: il pad e' basso, 6 semitoni)
        assert melody >= comp - 8, (genre, seed, melody, comp)           # la melodia non scende sotto di esso
        assert melody >= bass + 12, (genre, seed, melody, bass)
        assert min(n[2][0] for n in parts["bass"]) >= 28, genre          # nessuna nota sotto il mi basso del contrabbasso


def _strong_beat_hits(genre, seed):
    parts, bar = _song(genre, seed)
    harmony = parts.get("comp", []) + parts.get("bass", []) + parts.get("comp2", [])
    hits = total = 0
    for start, _dur, notes in parts.get("melody", []):
        if abs(start % bar) > 1e-6:
            continue
        index = int(start // bar)
        pitch_classes = {n % 12 for s, _d, ns in harmony if index * bar - 1e-6 <= s < (index + 1) * bar - 1e-6 for n in ns}
        hits += notes[-1] % 12 in pitch_classes
        total += 1
    return hits, total


def test_melody_notes_on_the_strong_beat_belong_to_the_chord():
    all_hits = all_total = 0
    for genre in GENRES_DATA:
        hits = total = 0
        for seed in SEEDS:
            h, t = _strong_beat_hits(genre, seed)
            hits, total = hits + h, total + t
        if total >= 6:
            assert hits / total >= 0.7, (genre, hits, total)
        all_hits, all_total = all_hits + hits, all_total + total
    assert all_hits / all_total >= 0.9, (all_hits, all_total)


def test_parallel_fifths_and_octaves_between_bass_and_melody_stay_rare():
    parallel = pairs = 0
    for genre in GENRES_DATA:
        for seed in SEEDS:
            parts, bar = _song(genre, seed)
            previous = None
            for start, _dur, notes in parts.get("melody", []):
                if abs(start % bar) > 1e-6:
                    continue
                under = [n for s, d, n in parts.get("bass", []) if s - 1e-6 <= start < s + d - 1e-6]
                current = (notes[-1], under[0][0]) if under else None
                if previous and current:
                    pairs += 1
                    first, second = (previous[0] - previous[1]) % 12, (current[0] - current[1]) % 12
                    moved = previous[0] != current[0] and previous[1] != current[1]
                    parallel += moved and first == second and first in (0, 7)
                previous = current
    assert pairs > 300
    assert parallel / pairs <= 0.2, (parallel, pairs)                # misurato 0.14: da portare a zero


SONG = "ST: 2.6\nTempo: 100 BPM\nMetrica: 4/4\nTonalita: C\n\nPiano:\n  1: C | Am | F | G | C | Am | F | G |\n"
def _energy(text, instrument):
    """La somma delle velocity di tutti gli attacchi: la «forza» di un testo."""
    from core.model import Project
    project = Project(name="t")
    track = project.add_track("X", instrument, text)
    return sum(max(1, e.velocity or 80) for e in track.parsed_events(project.patterns, meter=project.meter())
               if e.kind in ("note", "chord", "block"))


def test_more_intensity_means_more_energy_for_every_style():
    from mobile import engine
    for kind, styles, instrument in (("drums", rg.DRUM_STYLES, "Drums"), ("bass", rg.BASS_STYLES, "Bass"),
                                     ("comping", rg.COMPING_STYLES, "Piano")):
        for style in styles:
            energy = []
            for intensity in ("light", "normal", "full"):
                total = 0
                for seed in (1, 2, 3):
                    text = engine.generate(SONG, kind, {"style": style, "bars": 8, "seed": seed, "intensity": intensity,
                                                        "variability": 0, "source": "Piano"})["text"]
                    total += _energy(text, instrument)
                energy.append(total)
            assert energy[0] < energy[1] <= energy[2] and energy[0] < energy[2], (kind, style, energy)
