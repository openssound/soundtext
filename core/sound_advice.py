"""
I suoni consigliati per un brano (la finestra «Un brano in 60 secondi» del PC): il brano suona col SoundFont generale, ma
dove ci sono strumenti campionati migliori (SFZ di "Scarica e installa") li propone, traccia per traccia. Non cambia niente
da solo: chi usa SoundText sceglie se usarli (apply_sfz) o se scaricarli (download_keys, voci di "Scarica e installa").

- SoundFont generale: se non ce n'e' nessuno, o se c'e' solo quello leggero (TimGM6mb), propone MuseScore General (gia'
  scaricato: si usa con un clic; se no, da scaricare).
- Tracce: per lo strumento General MIDI della traccia il file .sfz di uno strumento scaricabile (pianoforte, chitarre,
  bassi, sax, batteria acustica...; per l'orchestra quello di core.orchestra). Gia' scaricato: si puo' usare solo se
  suona tutte le note della traccia (core.sfz_coverage: un basso o un kit con meno tasti lascerebbe note mute), se no
  si prova il candidato seguente; non scaricato: si dice quale voce scaricare. Le batterie elettroniche, a spazzole o
  d'orchestra (anche se scelte in Gestione strumenti) restano al SoundFont: un kit acustico le snaturerebbe.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .downloads import _split, load_script
from .i18n import tr

log = logging.getLogger(__name__)

_PIANO = (("splendid-piano", "Splendid Grand Piano.sfz"), ("piano", "*/SalamanderGrandPiano-V3*.sfz"), ("upright", "*/*.sfz"))

# programma General MIDI (da 0) -> i file .sfz candidati, dal preferito: (gruppo di scarica_strumenti, schema nel gruppo)
SFZ_PER_PROGRAMMA = {
    0: _PIANO, 1: _PIANO,
    4: (("rhodes", "jRhodes3d-mono.sfz"), ("epiano-vintage", "Wurlitzer EP200/Wurlitzer EP200.sfz")),
    5: (("epiano", "*/*.sfz"),),
    19: (("organo", "*/*.sfz"),),
    24: (("chitarra", "*/*.sfz"),),
    27: (("chitarra-elettrica", "*/*.sfz"),),
    29: (("chitarra-dist", "*/*.sfz"),),
    30: (("chitarra-dist", "*/*.sfz"),),
    32: (("contrabbasso", "*/d_smolken_rubner_bass_pizz.sfz"),),
    33: (("basso", "*/*.sfz"),),
    34: (("basso-plettro", "*/*.sfz"),),
    64: (("solosax", "*/MTG Soprano Sax.sfz"),),
    65: (("solosax", "*/MTG Alto Sax.sfz"),),
    66: (("sax", "*/*.sfz"), ("solosax", "*/MTG Tenor Sax.sfz")),
    67: (("solosax", "*/MTG Baritone Sax.sfz"),),
}
# la batteria: solo i kit acustici (standard, room, power); il MuldjordKit nella copia con le note GM
SFZ_BATTERIA = (("batteria", "*/*-GM.sfz"), ("salamander-drums", "ALL.sfz"))
KIT_ACUSTICI = (0, 8, 16)

LIGHT_SOUNDFONT = "TimGM6mb.sf2"
FULL_SOUNDFONTS = ("sf-musescore", "sf-fluidr3")


@dataclass
class TrackSound:
    track: str              # il nome della traccia
    group: str              # la voce di "Scarica e installa"
    group_label: str        # come la chiama "Scarica e installa"
    path: str = ""          # il file .sfz, se il gruppo e' scaricato
    installed: bool = False


@dataclass
class Advice:
    soundfont: str = ""                 # il SoundFont generale in uso ('' nessuno)
    soundfont_note: str = ""            # che cosa non va nel SoundFont generale ('' niente)
    use_soundfont: str = ""             # un SoundFont completo gia' scaricato da usare al suo posto
    sfz_engine: bool = True             # c'e' il motore SFZ interno
    tracks: List[TrackSound] = field(default_factory=list)
    download_keys: List[str] = field(default_factory=list)   # le voci di "Scarica e installa" consigliate

    @property
    def usable(self) -> List[TrackSound]:
        """Le tracce che possono passare subito a uno strumento campionato."""
        return [t for t in self.tracks if t.installed] if self.sfz_engine else []


def _kit_program(track) -> int:
    """Il programma del kit di batteria: quello scelto in Gestione strumenti, se c'e', altrimenti quello dello strumento."""
    from .settings import get_drum_kit_override
    override = get_drum_kit_override(track.instrument_name or track.instrument.name)
    return track.instrument.gm_program if override is None else int(override)


def _candidates(track) -> Tuple[Tuple[str, str], ...]:
    profile = track.instrument
    if profile.is_percussion:
        return SFZ_BATTERIA if _kit_program(track) in KIT_ACUSTICI else ()
    if profile.gm_program in SFZ_PER_PROGRAMMA:
        return SFZ_PER_PROGRAMMA[profile.gm_program]
    from .orchestra import FILE_PER_PROGRAMMA
    group, sfz = FILE_PER_PROGRAMMA.get(profile.gm_program, (None, None))
    return ((group, sfz),) if group else ()


def _resolve(script, group: str, pattern: str) -> Optional[TrackSound]:
    voce = script.trova(group)
    if voce is None:
        return None
    _name, desc, _url, sub = voce
    folder = script.DEST / sub / group
    files = sorted(p for p in folder.glob(pattern) if p.is_file()) if folder.is_dir() else []
    installed = (folder / ".completo").exists() and bool(files)
    return TrackSound("", group, tr(_split(desc)[0]), str(files[0]) if installed else "", installed)


def covers(project, track, path: str) -> bool:
    """Il .sfz 'path' suona tutte le note (con la loro dinamica) che la traccia suona nel progetto."""
    from .sfz_coverage import sfz_regions, sounds, track_notes
    regions = sfz_regions(path)
    if not regions:
        return False                                    # un file che non si legge non si propone
    try:
        notes = track_notes(project, track)
    except Exception:
        log.warning("Note della traccia %s non lette per la copertura SFZ", track.name, exc_info=True)
        return False
    return all(sounds(regions, note, velocity) for note, velocity in notes)


def track_sound(track, script=None, project=None) -> Optional[TrackSound]:
    """Lo strumento campionato per la traccia: il primo gia' scaricato fra i candidati che (con 'project') suona tutte
    le note della traccia, o il primo da scaricare; None se non c'e' (o la traccia ha gia' un suo strumento plugin)."""
    if track.is_audio or track.synth or track.mute:
        return None
    script = script or load_script()
    if script is None:
        return None
    found = [s for s in (_resolve(script, g, p) for g, p in _candidates(track)) if s is not None]
    usable = (s for s in found if s.installed and (project is None or covers(project, track, s.path)))
    best = next(usable, None) or next((s for s in found if not s.installed), None)
    if best is None:
        return None
    best.track = track.name
    return best


def _soundfont_advice(advice: Advice):
    from .playback import _find_soundfont
    from .soundfont_downloads import find, installed_path
    current = _find_soundfont() or ""
    advice.soundfont = current
    if current and os.path.basename(current) != LIGHT_SOUNDFONT:
        return
    full = [p for p in (installed_path(find(k)) for k in FULL_SOUNDFONTS) if p]
    if not current:
        advice.soundfont_note = tr("Non c'e' un SoundFont General MIDI: il brano non si sente.")
    else:
        advice.soundfont_note = tr("TimGM6mb e' il SoundFont leggero: uno completo suona molto meglio.")
    if full:
        advice.use_soundfont = full[0]
    else:
        advice.download_keys.append(FULL_SOUNDFONTS[0])


def sound_advice(project) -> Advice:
    """I suoni consigliati per il progetto (vedi il commento del modulo)."""
    from .sfz_engine import sfz_available
    advice = Advice(sfz_engine=sfz_available())
    _soundfont_advice(advice)
    script = load_script()
    if script is None:
        return advice
    for track in project.tracks:
        sound = track_sound(track, script, project)
        if sound is not None:
            advice.tracks.append(sound)
    if not advice.sfz_engine and advice.tracks and script.libreria_precompilata() is not None:
        advice.download_keys.append("libreria")          # da compilare (minuti) no: lo dice solo il testo
    for sound in advice.tracks:
        if not sound.installed and sound.group not in advice.download_keys:
            advice.download_keys.append(sound.group)
    return advice


def apply_sfz(project, advice: Advice) -> List[str]:
    """Le tracce che hanno uno strumento campionato gia' scaricato passano al motore SFZ interno; ritorna i loro nomi."""
    from .plugins import home_relative
    done = []
    for sound in advice.usable:
        track = project.get_track(sound.track)
        if track is not None and not track.synth:
            track.synth = "sfz:" + home_relative(sound.path)
            done.append(track.name)
    return done


def describe(advice: Advice) -> List[str]:
    """Le righe da mostrare: il SoundFont in uso, che cosa si puo' usare subito e che cosa si puo' scaricare."""
    lines = [tr("Suoni: {name}", name=os.path.basename(advice.soundfont) if advice.soundfont else tr("nessun SoundFont"))]
    if advice.soundfont_note:
        lines.append(advice.soundfont_note)
    usable = advice.usable
    if usable:
        lines.append(tr("Strumenti campionati gia' scaricati: {list}",
                        list=", ".join(f"{s.track} ({s.group_label})" for s in usable)))
    missing = [s for s in advice.tracks if not s.installed]
    if missing:
        lines.append(tr("Da scaricare per suonare meglio: {list}",
                        list=", ".join(f"{s.track} ({s.group_label})" for s in missing)))
    if advice.tracks and not advice.sfz_engine:
        lines.append(tr("Per gli strumenti campionati serve il motore SFZ interno (Scarica e installa, Motori)."))
    return lines
