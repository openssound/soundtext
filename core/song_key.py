"""
Alzare o abbassare la tonalita' di tutto il brano, per esempio per trovare
quella giusta per chi canta (gui.song_key_dialog): le tracce di note, i box,
la riga Tonalita: con i suoi cambi e le clip audio (AudioClip.transpose, che
non tocca i file); le percussioni restano.

I richiami prendono il suffisso +N, come in core.arrange.transpose_track, e i
pattern restano com'erano. Non basta se un richiamo lavora nella scala del
brano (%M.step(1)): la scala si sposta con il brano, quindi il suffisso
trasporterebbe due volte. In quel caso si riscrivono i pattern. Il risultato si
controlla sempre: ogni nota deve essere quella di prima, N semitoni piu' su.
"""

import copy
import re
from typing import List, Tuple

from st_language.chords import midi_to_token, note_name_to_pc, pitch_to_midi
from st_language.midi import resolve_event_notes
from st_language.notation import _transpose_key_name
from st_language.transform import RE_NOTE_ARGUMENT, _spell, is_transform_reference

from .arrange import transpose_track
from .arrangement import flatten_clips_to_text
from .i18n import tr
from .model import Project
from .notation import NotationError, PitchRewriter, RE_PATTERN_REF, rewrite_tokens, tokenize
from .sfz_coverage import silent_notes

MAX_SEMITONES = 12
AUDIO_QUALITY_SEMITONES = 3         # oltre, chi ascolta una clip audio sente la trasposizione
AUDIO_LIMIT = 24.0                  # come AudioClip.transpose

_RE_INVERT_AXIS = re.compile(r"(\.(?:invert|inverti)\()([^(),]+)(\))", re.IGNORECASE)
_RE_ROOT = re.compile(r"^[A-G][#b♭]?")


def transposed_key(key: str, semitones: int) -> str:
    return _transpose_key_name(key, semitones) if key else key


class _PatternRewriter(PitchRewriter):
    """Riscrive le note lasciando i richiami ai pattern come sono: i pattern
    richiamati sono trasposti anche loro. L'asse di .invert si sposta. Le
    note si scrivono nella tonalita' nuova del brano (si bemolle in Fa, non la
    diesis): le funzioni sulla scala leggono cosi' il grado giusto."""

    def __init__(self, semitones: int, default_octave: int, song_key: str):
        super().__init__(semitones, default_octave)
        self.song_key = song_key

    def _spell(self, midi: int) -> Tuple[str, int]:
        return super()._spell(midi) if self.dst.alters else _spell(midi, self.song_key)

    def __call__(self, tok: str) -> str:
        if is_transform_reference(tok):
            return _RE_INVERT_AXIS.sub(self._axis, tok)
        if RE_PATTERN_REF.match(tok):
            return tok
        return super().__call__(tok)

    def _axis(self, m) -> str:
        note = RE_NOTE_ARGUMENT.match(m.group(2))
        if not note:
            return m.group()
        octave = int(note.group(3)) if note.group(3) else self.src.default_octave
        midi = pitch_to_midi(note.group(1) + note.group(2), octave) + self.semitones
        return m.group(1) + midi_to_token(midi) + m.group(3)


def _note_tracks(project: Project) -> list:
    return [t for t in project.tracks if not t.is_audio and not t.instrument.is_percussion]


def _with_suffixes(project: Project, semitones: int) -> None:
    for track in _note_tracks(project):
        transpose_track(project, track, semitones)


def _in_patterns(project: Project, semitones: int) -> None:
    if not project.key:
        project.key = "C"           # le funzioni sulla scala ripiegano sul Do: ora si sposta
    key = transposed_key(project.key, semitones)
    for pattern in project.patterns.values():
        text = rewrite_tokens(" ".join(pattern.tokens), _PatternRewriter(semitones, 4, key))
        pattern.tokens = tokenize(text)
    for track in _note_tracks(project):
        octave = track.instrument.default_octave
        if track.clips:
            for clip in track.clips:
                clip.text = rewrite_tokens(clip.text, _PatternRewriter(semitones, octave, key))
            track.text = flatten_clips_to_text(track.clips, project.patterns, octave, meter=project.meter())
        else:
            track.text = rewrite_tokens(track.text, _PatternRewriter(semitones, octave, key))


def _sound(project: Project, track) -> list:
    """Per ogni evento che suona: tempo, durata, forza, altezze, e la
    fondamentale se e' un accordo."""
    sound = []
    for ev in track.parsed_events(project.patterns, meter=project.meter()):
        if ev.kind in ("note", "chord", "block", "percussion", "slide"):
            root = _RE_ROOT.match(ev.symbol) if ev.kind == "chord" and ev.symbol else None
            sound.append((round(ev.start, 6), round(ev.duration, 6), ev.kind, ev.velocity,
                          sorted(resolve_event_notes(ev, track.instrument)[0]),
                          note_name_to_pc(root.group()) if root else None))
    return sorted(sound, key=repr)


def _follows(before: tuple, after: tuple, semitones: int, exact: bool) -> bool:
    """Se l'evento 'after' e' 'before' spostato. Le note di un accordo
    dipendono dal voicing: di quelle contano solo i nomi."""
    if before[:4] != after[:4]:
        return False
    old, new = before[4], after[4]
    if before[5] is not None:
        return after[5] == (before[5] + semitones) % 12
    if exact:
        return new == [n + semitones for n in old]
    return {(n + semitones) % 12 for n in old} == {n % 12 for n in new}


def _same_music(project: Project, trial: Project, semitones: int) -> bool:
    for track, moved in zip(project.tracks, trial.tracks):
        if track.is_audio:
            continue
        try:
            before, after = _sound(project, track), _sound(trial, moved)
        except (NotationError, ValueError):
            return False
        if track.instrument.is_percussion:
            if before != after:
                return False
            continue
        # gli accordi arpeggiati diventano note, con il voicing del nuovo accordo
        exact = "arp" not in track.text and not any("arp" in p for pat in project.patterns.values() for p in pat.tokens)
        if len(before) != len(after) or not all(_follows(a, b, semitones, exact) for a, b in zip(before, after)):
            return False
    return True


def transposed_song(project: Project, semitones: int) -> Project:
    """Una copia del brano spostata di 'semitones'; quello di partenza non
    cambia. Solleva ValueError se le note non si possono spostare tutte."""
    for track in project.tracks:
        if not track.is_audio:
            try:
                track.parsed_events(project.patterns, meter=project.meter())
            except (NotationError, ValueError) as e:
                raise ValueError(tr("Correggi prima gli errori della traccia «{name}»: {msg}",
                                    name=track.name, msg=e)) from e
    for strategy in (_with_suffixes, _in_patterns):
        trial = copy.deepcopy(project)
        try:
            strategy(trial, semitones)
        except (NotationError, ValueError):
            continue
        trial.key = transposed_key(trial.key, semitones)
        trial.key_changes = [(bar, transposed_key(key, semitones)) for bar, key in trial.key_changes]
        if _same_music(project, trial, semitones):
            for track in trial.tracks:
                for clip in track.audio_clips:
                    clip.transpose = max(-AUDIO_LIMIT, min(AUDIO_LIMIT, round(clip.transpose + semitones, 3)))
            return trial
    raise ValueError(tr("Non si puo' spostare il brano di {n} semitoni senza cambiare le note: qualcuna esce "
                        "dall'estensione MIDI o da un pattern che non si puo' riscrivere.", n=f"{semitones:+d}"))


def apply_transposition(project: Project, trial: Project) -> None:
    """Porta in 'project' il risultato di transposed_song, senza sostituire
    gli oggetti che la finestra tiene (tracce, dizionario dei pattern)."""
    for track, moved in zip(project.tracks, trial.tracks):
        track.text, track.clips, track.audio_clips = moved.text, moved.clips, moved.audio_clips
    project.patterns.clear()
    project.patterns.update(trial.patterns)
    project.key, project.key_changes = trial.key, trial.key_changes


def warnings_for(project: Project, trial: Project, semitones: int) -> List[str]:
    """Quello che chi sceglie la tonalita' deve sapere prima di confermare."""
    out = []
    for track in _note_tracks(trial):
        instrument = track.instrument
        notes = [n for sound in _sound(trial, track) for n in sound[4]]
        low = sum(n < instrument.range_low for n in notes)
        high = sum(n > instrument.range_high for n in notes)
        if low or high:
            out.append(tr("«{name}»: {n} note fuori dall'estensione dello strumento", name=track.name, n=low + high))
        silent = silent_notes(trial, track)
        if silent is not None:
            out.append(f"«{track.name}»: {silent.message()}")
    if abs(semitones) >= AUDIO_QUALITY_SEMITONES and any(t.audio_clips for t in project.tracks):
        out.append(tr("Le tracce audio si spostano di {n} semitoni: con salti grandi il suono peggiora",
                      n=f"{semitones:+d}"))
    return out
