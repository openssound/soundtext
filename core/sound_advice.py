"""
I suoni consigliati per un brano (la finestra «Un brano in 60 secondi» del PC): il brano suona col SoundFont generale, ma
dove ci sono strumenti campionati migliori (SFZ) li propone, traccia per traccia. Non cambia niente da solo: chi usa
SoundText sceglie se usarli (apply_sfz) o se scaricarli (download_keys, voci di "Scarica e installa").

- SoundFont generale: se non ce n'e' nessuno, o se c'e' solo quello leggero (TimGM6mb), propone MuseScore General (gia'
  scaricato: si usa con un clic; se no, da scaricare).
- Tracce: ogni installazione e' diversa, quindi si guardano i file .sfz che ci sono davvero nella cartella degli
  strumenti (quella di "Scarica e installa", ~/Strumenti), scaricati da SoundText o messi a mano. Lo strumento di un
  file si riconosce dal nome del file e delle cartelle (o dalla voce di "Scarica e installa" del suo gruppo):
  KINDS. Per lo strumento General MIDI della traccia si provano prima i file preferiti (SFZ_PER_PROGRAMMA, l'orchestra
  di core.orchestra), poi gli altri riconosciuti, e si propone il primo che suona tutte le note della traccia
  (core.sfz_coverage: un basso o un kit con meno tasti lascerebbe note mute). Se nessuno va, si consiglia la voce da
  scaricare: la preferita, se no la piu' piccola fra quelle che hanno quello strumento. Le batterie elettroniche, a
  spazzole o d'orchestra (anche se scelte in Gestione strumenti) restano al SoundFont: un kit acustico le snaturerebbe.
"""

import logging
import os
import re
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .downloads import _split, load_script
from .i18n import tr

log = logging.getLogger(__name__)

_PIANO = (("splendid-piano", "Splendid Grand Piano.sfz"), ("piano", "*/SalamanderGrandPiano-V3*.sfz"), ("upright", "*/*.sfz"))

# i file preferiti: programma General MIDI (da 0) -> (gruppo di scarica_strumenti, schema nel gruppo), dal preferito
SFZ_PER_PROGRAMMA = {
    0: _PIANO, 1: _PIANO,
    4: (("rhodes", "jRhodes3d-mono.sfz"), ("epiano-vintage", "Wurlitzer EP200/Wurlitzer EP200.sfz")),
    5: (("epiano", "*/*.sfz"),),
    19: (("organo", "*/*.sfz"),),
    24: (("chitarra", "*/*.sfz"),),
    25: (("emilyguitar", "*/emily_basic.sfz"),),
    26: (("shinyguitar", "*/Programs/electric_one.sfz"),),
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
    105: (("banjo", "FS KayBanjo (release mw1).sfz"),),
}
# la batteria: solo i kit acustici (standard, room, power); il MuldjordKit nella copia con le note GM
SFZ_BATTERIA = (("batteria", "*/*-GM.sfz"), ("salamander-drums", "ALL.sfz"))
KIT_ACUSTICI = (0, 8, 16)
DRUMS = -1                  # la "famiglia" della batteria in KINDS

# riconoscere lo strumento di un file dal nome: (programmi General MIDI o DRUMS, se c'e', se non c'e'), su un testo in
# minuscolo con spazi al posto di _ - . / ( ) (vedi _words); in italiano e in inglese, per i file e per le voci di
# "Scarica e installa"
KINDS = [
    ((0, 1, 2, 3), r"piano|grand|upright", r"e ?piano|electric|elettric|rhodes|wurl|pianet|\bfm|toy|cp ?80|clav|scary|bass|sax"),
    ((4,), r"rhodes|wurl|pianet|e ?piano|electric piano|piano elettric|ep ?200|cp ?80", r"\bfm"),
    ((5,), r"fm ?piano|piano elettrico fm|\bdx ?7", ""),
    ((16, 17, 18), r"organ", r"church|chiesa|pipe|canne"),
    ((19,), r"(church|chiesa|pipe|canne).*organ|organ.*(church|chiesa|pipe|canne)", ""),
    ((21, 23), r"accordion|fisarmonica", ""),
    ((22,), r"harmonica|armonica", r"fisarmonica"),
    ((24,), r"nylon|classical guitar|classic guitar|spanish|chitarra classica", ""),
    ((25,), r"steel guitar|acciaio|acoustic guitar|chitarra acustica|emilyguitar|emily", r"electric|elettric"),
    ((26,), r"archtop|jazz guitar|guitar jazz|chitarra jazz|da jazz|shinyguitar", ""),
    ((27, 28), r"(clean|pulit).*(guitar|chitarra)|(guitar|chitarra).*(clean|pulit)|electric guitar|chitarra elettrica",
     r"dist|overdr|crunch|bass|basso|emily|acoustic|acustic|jazz"),
    ((29, 30), r"(guitar|chitarra).*(dist|overdr|crunch)|(dist|overdr|crunch).*(guitar|chitarra)", r"bass|basso"),
    ((32,), r"double ?bass|contrabass|contrabbasso|upright bass|acoustic bass|sneakybass", r"\barco"),
    ((33,), r"finger ?bass|basso elettrico|electric bass|bass guitar|pastabass|meatbass|fashionbass|growlybass|swagbass"
     r"|big little bass", r"pick|plettro|synth|double|contra|upright|\barco|fretless"),
    ((34,), r"pick(ed)? ?bass|basso (elettrico )?plettro", ""),
    ((35,), r"fretless", ""),
    ((40, 110), r"violin|violino|fiddle", r"\bens|viola\b"),
    ((41,), r"\bviola\b", ""),
    ((42,), r"cello|violoncell", ""),
    ((46,), r"\bharp\b|\barpa\b|concert ?harp", r"harpsi"),
    ((56, 59), r"trumpet|tromba", ""),
    ((57,), r"trombone", ""),
    ((58,), r"\btuba", ""),
    ((60,), r"french horn|\bf ?horn|\bcorno\b", ""),
    ((64,), r"soprano ?sax|sax soprano", ""),
    ((65,), r"alto ?sax|sax (contr)?alto|weresax.* alto|\bcontralto", ""),
    ((66,), r"tenor ?sax|sax tenore|bear sax|\btenore\b", ""),
    ((67,), r"bari(tone)? ?sax|sax baritono|\bbaritono\b", ""),
    ((68,), r"\boboe", ""),
    ((70,), r"bassoon|fagotto", ""),
    ((71,), r"clarinet", ""),
    ((72,), r"piccolo|ottavino", r"piano|vertical|guitar|chitarra|bass"),       # «piccolo» e' anche l'aggettivo
    ((73,), r"flute|flauto", ""),
    ((11,), r"vibraphone|vibrafono", ""),
    ((12,), r"marimba", ""),
    ((13,), r"xylophone|xilofono", ""),
    ((105,), r"banjo", r"ganjo"),
    ((DRUMS,), r"drum|batteria|\bkit\b", r"electr|elettr|\b808|\b909|steel ?drum|brush|spazzol|orchestr|sfx"),
]
_KINDS = [(set(progs), re.compile(inc), re.compile(exc) if exc else None) for progs, inc, exc in KINDS]
_SEP = re.compile(r"[\s_\-./(),+]+")
# file che non sono lo strumento da suonare (solo i rumori, le code, i controlli, le prove)
_NOT_PLAYABLE = re.compile(r"(^| )(noises?|release|releases|controls?|test|fx)$")
# varianti meno adatte a suonare una parte normale: si provano dopo (tranne dove sono proprio lo strumento: _FITTING)
_VARIANT = re.compile(r"keyswitch|\bks\b|staccato|stacc|hammer|chords?\b|harmonic|mute|trem|twang|noise|pizz|spicc|"
                      r"mono|no ?xfade|split|fx|saxcordion|sxnth|synth")
_FITTING = {28: re.compile(r"mute"), 32: re.compile(r"pizz"), 33: re.compile(r"pizz"), 45: re.compile(r"pizz"),
            44: re.compile(r"trem")}

# i campioni generati da sfizz (onde, rumore, silenzio): un file che suona solo questi e' un segnaposto (il banco GM
# incompleto ne ha uno per ogni strumento non campionato), non uno strumento
_SAMPLE = re.compile(r"\bsample\s*=\s*([^\r\n<]*)")

LIGHT_SOUNDFONT = "TimGM6mb.sf2"
FULL_SOUNDFONTS = ("sf-musescore", "sf-fluidr3")


def _words(text: str) -> str:
    return " " + _SEP.sub(" ", text.lower()).strip() + " "


_PIANOS = {0, 1, 2, 3}


def kinds_of(text: str) -> Set[int]:
    """I programmi General MIDI (e DRUMS) che il testo (nome di un file, voce di "Scarica e installa") nomina. «piano»
    e «grand» accanto a un altro strumento sono la dinamica o un aggettivo («Violin piano», «Grand Organ»): non il
    pianoforte."""
    words = _words(text)
    out: Set[int] = set()
    for progs, include, exclude in _KINDS:
        if include.search(words) and not (exclude and exclude.search(words)):
            out |= progs
    if out & _PIANOS and out - _PIANOS:
        out -= _PIANOS
    return out


@dataclass
class TrackSound:
    track: str              # il nome della traccia
    group: str              # la voce di "Scarica e installa" (o la cartella del file, se non e' una voce)
    group_label: str        # come mostrarla
    path: str = ""          # il file .sfz, se c'e' gia'
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


# ---- i file .sfz che ci sono

@dataclass
class SfzFile:
    path: str
    group: str              # la cartella del gruppo (DEST/<sub>/<gruppo>), '' se il file sta altrove
    kinds: Set[int]


_scan_cache: Dict[str, List[SfzFile]] = {}
_scan_lock = threading.Lock()


def forget_installed():
    """Dimentica i file trovati: dopo uno scarico (o se si sono aggiunti strumenti a mano) si cercano di nuovo."""
    with _scan_lock:
        _scan_cache.clear()


def prefetch(script=None) -> threading.Thread:
    """Cerca i .sfz e ne legge le regioni in un thread (la finestra lo avvia all'apertura, mentre si sceglie il genere):
    i consigli, dopo, non fermano la finestra. installed_sfz aspetta la ricerca se non e' finita."""
    def run():
        try:
            from .sfz_coverage import sfz_regions
            for found in installed_sfz(script or load_script()) if (script or load_script()) is not None else ():
                sfz_regions(found.path)
        except Exception:
            log.warning("Ricerca degli strumenti SFZ non riuscita", exc_info=True)
    thread = threading.Thread(target=run, name="sfz-prefetch", daemon=True)
    thread.start()
    return thread


def _placeholder(path: str) -> bool:
    """Il .sfz suona solo campioni generati (sample=*sine...): non e' uno strumento campionato."""
    from .sfz_coverage import _expand
    try:
        samples = _SAMPLE.findall(_expand(path, {}))                 # anche i campioni dei file inclusi
    except (OSError, RecursionError):
        return True
    return bool(samples) and all(sample.strip().startswith("*") for sample in samples)


def _short(label: str) -> str:
    """La voce di "Scarica e installa" fino alla prima virgola o parentesi (quella del banco GM e' un paragrafo)."""
    return re.split(r"[,(:;]", label, maxsplit=1)[0].strip() or label


def _group_text(script, group: str) -> str:
    """La voce di "Scarica e installa" del gruppo, se nomina un solo strumento (una voce con legni o archi diversi, o
    un banco General MIDI, non dice quale sia ogni file); '' altrimenti."""
    voce = script.trova(group) if group else None
    if voce is None:
        return ""
    label = _split(voce[1])[0]
    return label if len(kinds_of(label)) == 1 else ""


def installed_sfz(script) -> List[SfzFile]:
    """Tutti i .sfz della cartella degli strumenti, con lo strumento riconosciuto (ricordati: vedi forget_installed)."""
    with _scan_lock:
        return _scan(script)


def _scan(script) -> List[SfzFile]:
    root = str(script.DEST)
    if root in _scan_cache:
        return _scan_cache[root]
    found: List[SfzFile] = []
    group_text: Dict[str, str] = {}
    for folder, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if not d.startswith((".", "_")))          # _download: gli archivi
        rel = os.path.relpath(folder, root)
        parts = [] if rel == "." else rel.split(os.sep)
        group = parts[1] if len(parts) >= 2 else ""
        for name in sorted(files):
            stem, ext = os.path.splitext(name)
            if ext.lower() != ".sfz" or _NOT_PLAYABLE.search(_words(stem).strip()):
                continue
            own = os.path.join(*(parts[1:] or [""]), stem)
            kinds = kinds_of(own)
            if group not in group_text:
                group_text[group] = _group_text(script, group)
            if group_text[group]:
                # la voce del gruppo dice lo strumento: il nome lo puo' solo escludere (cosi' «arco» in un basso elettrico
                # lo esclude comunque) o precisare, non cambiarlo (una dinamica nel nome di un sax non e' un pianoforte)
                instrument = kinds_of(group_text[group])
                kinds = (kinds & instrument) if kinds else kinds_of(group_text[group] + " " + own) & instrument
            if kinds and not _placeholder(os.path.join(folder, name)):
                found.append(SfzFile(os.path.join(folder, name), group, kinds))
    _scan_cache[root] = found
    return found


# ---- la traccia

def _kit_program(track) -> int:
    """Il programma del kit di batteria: quello scelto in Gestione strumenti, se c'e', altrimenti quello dello strumento."""
    from .settings import get_drum_kit_override
    override = get_drum_kit_override(track.instrument_name or track.instrument.name)
    return track.instrument.gm_program if override is None else int(override)


def _kind(track) -> Optional[int]:
    """Il programma General MIDI della traccia (DRUMS per una batteria acustica), None se non le si propone niente."""
    profile = track.instrument
    if profile.is_percussion:
        return DRUMS if _kit_program(track) in KIT_ACUSTICI else None
    return profile.gm_program


def _candidates(kind: int) -> Tuple[Tuple[str, str], ...]:
    """I file preferiti per lo strumento: (gruppo, schema)."""
    if kind == DRUMS:
        return SFZ_BATTERIA
    if kind in SFZ_PER_PROGRAMMA:
        return SFZ_PER_PROGRAMMA[kind]
    from .orchestra import FILE_PER_PROGRAMMA
    group, sfz = FILE_PER_PROGRAMMA.get(kind, (None, None))
    return ((group, sfz),) if group else ()


def _group_label(script, group: str) -> str:
    voce = script.trova(group) if group else None
    return tr(_split(voce[1])[0]) if voce is not None else group


def _installed_group(script, group: str) -> bool:
    voce = script.trova(group)
    return voce is not None and (script.DEST / voce[3] / group / ".completo").exists()


def _preferred_files(script, kind: int) -> List[str]:
    out = []
    for group, pattern in _candidates(kind):
        voce = script.trova(group)
        if voce is None or not _installed_group(script, group):
            continue
        folder = script.DEST / voce[3] / group
        out += [str(p) for p in sorted(folder.glob(pattern)) if p.is_file()]
    return out


def _size_mb(detail: str) -> float:
    """"~370 MB" -> 370, "~1,5 GB" -> 1500 (molto se non si legge)."""
    m = re.search(r"([\d.,]+)\s*(MB|GB)", detail)
    if not m:
        return 1e9
    value = float(m.group(1).replace(",", "."))
    return value * (1000 if m.group(2) == "GB" else 1)


def _to_download(script, kind: int) -> Optional[str]:
    """La voce di "Scarica e installa" da consigliare per lo strumento: la preferita non ancora scaricata, se no la
    piu' piccola fra quelle che lo nominano."""
    for group, _pattern in _candidates(kind):
        if script.trova(group) is not None and not _installed_group(script, group):
            return group
    others = [(_size_mb(_split(desc)[1]), name) for name, desc, _url, _sub in script.GRUPPI + script.ORCHESTRA + script.EXTRA
              if kind in kinds_of(_split(desc)[0]) and not _installed_group(script, name)]
    return min(others)[1] if others else None


def _notes(project, track) -> Optional[List[Tuple[int, int]]]:
    """(nota, dinamica) di ogni nota della traccia, None se non si leggono."""
    from .sfz_coverage import track_notes
    try:
        return track_notes(project, track)
    except Exception:
        log.warning("Note della traccia %s non lette per la copertura SFZ", track.name, exc_info=True)
        return None


def _covers_notes(path: str, notes: List[Tuple[int, int]]) -> bool:
    from .sfz_coverage import sfz_regions, sounds
    regions = sfz_regions(path)
    if not regions:
        return False                                    # un file che non si legge non si propone
    return all(sounds(regions, note, velocity) for note, velocity in notes)


def covers(project, track, path: str) -> bool:
    """Il .sfz 'path' suona tutte le note (con la loro dinamica) che la traccia suona nel progetto."""
    notes = _notes(project, track)
    return notes is not None and _covers_notes(path, notes)


def _rank(path: str, kind: Optional[int] = None):
    """Prima i file normali, poi le varianti (staccato, keyswitch...; non quelle che sono proprio lo strumento della
    traccia, come «muted» per la chitarra smorzata), dal nome piu' corto."""
    stem = _words(os.path.splitext(os.path.basename(path))[0])
    fitting = _FITTING.get(kind)
    variant = bool(_VARIANT.search(fitting.sub(" ", stem) if fitting else stem))
    return (variant, not bool(fitting and fitting.search(stem)), len(stem), path)


def track_sound(track, script=None, project=None) -> Optional[TrackSound]:
    """Lo strumento campionato per la traccia: il primo file presente (i preferiti, poi gli altri riconosciuti) che
    (con 'project') suona tutte le note della traccia, o la voce da scaricare; None se non c'e' niente (o la traccia
    ha gia' un suo strumento plugin)."""
    if track.is_audio or track.synth or track.mute:
        return None
    kind = _kind(track)
    script = script or load_script()
    if kind is None or script is None:
        return None
    preferred = _preferred_files(script, kind)
    found = installed_sfz(script)
    others = sorted((f.path for f in found if kind in f.kinds and f.path not in preferred), key=lambda p: _rank(p, kind))
    groups = {f.path: f.group for f in found}
    notes = _notes(project, track) if project is not None else []
    if notes is None:
        return None
    for path in preferred + others:                      # tutti: le regioni sono gia' lette (prefetch) e ricordate
        if project is None or _covers_notes(path, notes):
            group = groups.get(path, "")
            label = _group_label(script, group)
            if path not in preferred:                    # quale file del gruppo
                stem = os.path.splitext(os.path.basename(path))[0]
                label = f"{_short(label)}: {stem}" if label else stem
            return TrackSound(track.name, group, label, path, True)
    group = _to_download(script, kind)
    if group is None:
        return None
    return TrackSound(track.name, group, _group_label(script, group))


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
        track = next((t for t in project.tracks if t.name == sound.track), None)
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
