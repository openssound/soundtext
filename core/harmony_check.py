"""Il controllo armonico di un brano: dove la melodia stona con quello che suonano basso e accompagnamento.

Per ogni nota della melodia che pesa (inizia sul tempo, oppure dura almeno un quarto) guarda che cosa suona in quel momento nelle altre parti
e segnala:
- la seconda minore (un semitono): la melodia contro una nota dell'accompagnamento o del basso (la nona minore no: la melodia sulla
  fondamentale sopra una maj7 e' normale);
- il tritono contro il basso.
Le note brevi in levare (passaggi, abbellimenti) non contano: li' lo scontro e' voluto. Il controllo serve ai test dei generatori
(ogni genere e atmosfera) e a chi scrive un brano a mano:

    python -m core.harmony_check brano.st
"""
import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class Clash:
    kind: str                 # "minor_second" o "tritone"
    beat: float               # dove, dall'inizio del brano (in quarti)
    melody_track: str
    melody_pitch: int
    other_track: str
    other_pitch: int

    def __str__(self) -> str:
        names = ("do", "do#", "re", "re#", "mi", "fa", "fa#", "sol", "sol#", "la", "la#", "si")
        what = "seconda minore" if self.kind == "minor_second" else "tritono col basso"
        return (f"battuta {int(self.beat // 4) + 1}, quarto {self.beat % 4 + 1:g}: {what} fra {self.melody_track} "
                f"({names[self.melody_pitch % 12]}{self.melody_pitch // 12 - 1}) e {self.other_track} "
                f"({names[self.other_pitch % 12]}{self.other_pitch // 12 - 1})")


def _sounding(project, track) -> List[Tuple[float, float, int]]:
    """(inizio, durata, nota MIDI) di tutte le note che la traccia suona."""
    from st_language.midi import resolve_event_notes, sounding_events
    out = []
    for ev in sounding_events(track.parsed_events(project.patterns, meter=project.meter())):
        if getattr(ev, "grace", None) or ev.duration <= 0:
            continue                                          # l'acciaccatura si suona prima del tempo: non e' la nota che pesa
        try:
            notes, _velocity = resolve_event_notes(ev, track.instrument)
        except Exception:
            continue
        if getattr(ev, "kind", "") == "slide" and getattr(ev, "slide_points", None) and notes:
            # il bend e lo slide partono da una nota di passaggio e arrivano a quella che conta: si guarda dove arriva
            from st_language.midi import pitch_to_midi
            letter, octave = ev.slide_points[-1]
            out.append((float(ev.start), float(ev.duration), int(pitch_to_midi(letter, octave))))
            continue
        for note in notes or ():
            out.append((float(ev.start), float(ev.duration), int(note)))
    return out


def _role(track) -> Optional[str]:
    from core.instruments import gm_family_for_program
    if track.is_audio or track.instrument.is_percussion or track.mute:
        return None
    if gm_family_for_program(track.instrument.gm_program) == "Bassi":
        return "bass"
    return "comp" if track.instrument.polyphonic else "melody"


def check_project(project, weighty: float = 1.0, melody_tracks: Optional[List[str]] = None) -> List[Clash]:
    """Gli scontri della melodia con basso e accompagnamenti del progetto. La melodia e' quella delle tracce a una voce, o delle tracce
    'melody_tracks' (per nome) se date: in un brano generato i fiati e le seconde voci sono a una voce ma fanno parte dell'accompagnamento."""
    roles = {t.name: _role(t) for t in project.tracks}
    notes = {t.name: _sounding(project, t) for t in project.tracks if roles[t.name]}
    clashes: List[Clash] = []
    for melody in (t for t in project.tracks if (t.name in melody_tracks if melody_tracks is not None else roles[t.name] == "melody")):
        for start, duration, pitch in notes[melody.name]:
            on_beat = abs(start - round(start)) < 1e-6
            if not (on_beat or duration >= weighty - 1e-6):
                continue
            for other in project.tracks:
                if other.name == melody.name or roles[other.name] not in ("bass", "comp") and not (melody_tracks is not None and roles[other.name] == "melody"):
                    continue
                for o_start, o_duration, o_pitch in notes[other.name]:
                    if o_start > start + 1e-6 or o_start + o_duration <= start + 1e-6:
                        continue                                  # non suona in quel momento
                    if abs(pitch - o_pitch) == 1:
                        clashes.append(Clash("minor_second", start, melody.name, pitch, other.name, o_pitch))
                    elif roles[other.name] == "bass" and (pitch - o_pitch) % 12 == 6:
                        clashes.append(Clash("tritone", start, melody.name, pitch, other.name, o_pitch))
    return clashes


def check_text(text: str, melody_tracks: Optional[List[str]] = None) -> List[Clash]:
    """Come check_project, su un testo ST."""
    from core.project_io import parse_project_text
    return check_project(parse_project_text(text, "Brano"), melody_tracks=melody_tracks)


def weighty_notes(project, melody_tracks: Optional[List[str]] = None) -> int:
    """Quante note della melodia pesano (il denominatore per misurare gli scontri)."""
    total = 0
    for track in project.tracks:
        if (track.name in melody_tracks) if melody_tracks is not None else _role(track) == "melody":
            total += sum(1 for s, d, _p in _sounding(project, track) if abs(s - round(s)) < 1e-6 or d >= 1.0 - 1e-6)
    return total


def main(argv: Optional[List[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("uso: python -m core.harmony_check brano.st")
        return 2
    with open(args[0], encoding="utf-8") as handle:
        clashes = check_text(handle.read())
    for clash in clashes:
        print(clash)
    print(f"{len(clashes)} scontri")
    return 1 if clashes else 0


if __name__ == "__main__":
    sys.exit(main())
