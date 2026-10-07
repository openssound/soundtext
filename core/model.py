"""
Modello dati del progetto musicale: Project -> Track(s) -> Pattern library
condivisa. Mantiene anche lo stato del mixer per traccia (Solo/Mute/
Volume/Pan) come richiesto dall'MVP (sezione 8).
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .instruments import InstrumentProfile, get_instrument
from .notation import Pattern, parse_track_text, Event, Meter
from .i18n import tr

# Pseudo-strumento delle tracce audio (Track.kind == "audio"): non e' fra gli
# strumenti scelti per le tracce MIDI, e nel file .st compare come
# "Traccia Nome [Audio]:" (vedi core.project_io).
AUDIO_INSTRUMENT_NAME = "Audio"
AUDIO_INSTRUMENT = InstrumentProfile(name=AUDIO_INSTRUMENT_NAME, gm_program=0, polyphonic=False,
                                     voicing_style="monophonic")


@dataclass
class Clip:
    """Un 'box' della vista Struttura brano: una sezione autosufficiente di
    notazione (come il corpo di un Pattern), posizionata nel tempo assoluto
    della traccia che la contiene. Vedi core.arrangement per la logica di
    durata/appiattimento in Track.text."""
    name: str
    text: str = ""              # notazione st-language autosufficiente del box
    start_beat: float = 0.0     # posizione assoluta nella traccia, in beat (quarti)


@dataclass
class AudioClip:
    """Una clip di una traccia audio: un file audio (registrato altrove o
    importato) posizionato nel brano. Il file non viene mai modificato:
    tagli e guadagno sono solo parametri di riproduzione. Vedi
    core.audio_tracks."""
    name: str
    file: str                   # in memoria sempre assoluto (relativo solo nel file .st)
    start_beat: float = 0.0     # posizione nel brano, in beat (quarti), come Clip
    trim_start: float = 0.0     # secondi del file saltati all'inizio
    trim_end: float = 0.0       # secondi del file saltati alla fine
    gain_db: float = 0.0


@dataclass
class Effect:
    """Un effetto della catena di una traccia (vedi core.effects.EFFECT_KINDS):
    tipo, parametri e se e' acceso. 'preset' e' il nome del preset da cui
    si e' partiti (solo per mostrarlo; i parametri sono quelli che contano)."""
    kind: str
    params: Dict[str, float] = field(default_factory=dict)
    enabled: bool = True
    preset: str = ""
    # Amplificatore o profilo NAM con cassa "File IR": il file WAV della
    # risposta all'impulso (assoluto in memoria, relativo al file .st su disco).
    ir: str = ""
    # Profilo NAM: il file .nam (come 'ir').
    nam: str = ""
    # Plugin esterno (tipo "plugin", vedi core.plugins): il riferimento
    # ("vst3:percorso" o "lv2:uri"), i suoi parametri e, per i VST3, lo
    # stato interno in base64.
    plugin: str = ""
    plugin_params: Dict[str, float] = field(default_factory=dict)
    plugin_state: str = ""


def send_percent_to_cc(percent: int) -> int:
    """Invio al riverbero/chorus (0-100%) -> valore di controller MIDI 0-127."""
    return max(0, min(127, round(max(0, min(100, percent)) * 127 / 100)))


def cc_to_send_percent(value: int) -> int:
    """Valore di controller MIDI 0-127 -> invio al riverbero/chorus (0-100%)."""
    return max(0, min(100, round(max(0, min(127, value)) * 100 / 127)))


@dataclass
class Track:
    name: str
    instrument_name: str
    text: str = ""              # notazione testuale grezza della traccia
    volume: int = 100            # 0-200 (100 = guadagno originale/unita', scala la velocity delle note)
    pan: int = 64                # 0 (sx) - 64 (centro) - 127 (dx)
    mute: bool = False
    solo: bool = False
    # Invio al riverbero e al chorus del synth (0-100%, 0 = nessuno, come
    # finora): solo tracce di testo, mandati come CC91/CC93 a inizio traccia
    # (vedi core.midi_export). Si sentono subito, senza rielaborare nulla
    # oltre al normale rendering del brano.
    reverb: int = 0
    chorus: int = 0
    # Catena di effetti (fase 2, vedi core.effects): elaborata dopo il
    # rendering della traccia, nell'ordine; vale per tracce di testo e audio.
    effects: List[Effect] = field(default_factory=list)
    # Strumento plugin (VST3/LV2, vedi core.plugins): se impostato, le note
    # della traccia le suona il plugin invece del SoundFont (riferimento,
    # parametri e stato come per Effect.plugin).
    synth: str = ""
    synth_params: Dict[str, float] = field(default_factory=dict)
    synth_state: str = ""
    # Se popolata, la traccia e' in modalita' "Struttura brano": 'text' e'
    # un valore derivato (ricalcolato da core.arrangement.flatten_clips_to_text
    # ad ogni modifica dei box) e non va piu' editato a mano - vedi
    # core.arrangement.
    clips: List[Clip] = field(default_factory=list)
    # "midi" (notazione, il caso di sempre) o "audio" (clip di file audio in
    # audio_clips; text resta vuoto e instrument_name e' AUDIO_INSTRUMENT_NAME).
    kind: str = "midi"
    audio_clips: List[AudioClip] = field(default_factory=list)
    # Solo tracce audio: come registrarle (vedi core.audio_recording) - profilo
    # d'ingresso ("voce", "chitarra", "tastiera"; "" = non ancora scelto) e
    # canali della scheda audio ("1", "2", "1+2", ...).
    input_profile: str = ""
    input_channels: str = ""
    # Lo strumento come lo definisce il brano (blocco "Strumento Nome:" del
    # file, vedi Project.instruments): se c'e', vale lui e non quello con lo
    # stesso nome registrato in locale, che puo' venire da un altro brano.
    instrument_def: Optional[InstrumentProfile] = field(default=None, repr=False, compare=False)

    @property
    def is_audio(self) -> bool:
        return self.kind == "audio"

    @property
    def instrument(self) -> InstrumentProfile:
        if self.is_audio:
            return AUDIO_INSTRUMENT
        if self.instrument_def is not None and self.instrument_def.name == self.instrument_name:
            return InstrumentProfile(**self.instrument_def.__dict__)
        return get_instrument(self.instrument_name)

    def parsed_events(self, patterns: Dict[str, Pattern], midi_dir: str = None,
                      meter: Optional[Meter] = None) -> List[Event]:
        instr = self.instrument
        return parse_track_text(self.text, patterns, default_octave=instr.default_octave,
                                 midi_dir=midi_dir, meter=meter)


def copy_synth(dst: "Track", src: Optional["Track"]) -> "Track":
    """Dalla traccia 'src' (se c'e' e ha uno strumento plugin) a 'dst': le
    anteprime e gli ascolti provvisori suonano cosi' con il plugin della
    traccia vera, invece che con il SoundFont. Ritorna 'dst'."""
    if src is not None and src.synth and not src.is_audio:
        dst.synth, dst.synth_params, dst.synth_state = src.synth, dict(src.synth_params), src.synth_state
    return dst


@dataclass
class Project:
    name: str = "Nuovo progetto"
    tempo_bpm: int = 120
    time_sig: str = "4/4"
    key: str = ""                # tonalita' del brano, es. "C", "Am", "F#" (vuota = non impostata)
    tracks: List[Track] = field(default_factory=list)
    patterns: Dict[str, Pattern] = field(default_factory=dict)
    # Cambi di tempo/metrica a partire da una certa battuta: [(nr_battuta, valore), ...].
    # Se vuoti, si usano semplicemente tempo_bpm/time_sig per l'intero brano
    # (comportamento originale, invariato). Se popolati, tempo_bpm/time_sig
    # continuano a rappresentare il valore alla battuta 1.
    tempo_changes: List[tuple] = field(default_factory=list)     # [(bar:int, bpm:int), ...]
    metrica_changes: List[tuple] = field(default_factory=list)    # [(bar:int, "N/D"), ...]
    master_volume: int = 100     # 0-200 (100 = guadagno originale/unita'), applicato sopra al volume di ogni traccia
    # Ambiente del riverbero del synth per tutto il brano (chiave di
    # core.effects.REVERB_ROOMS; "stanza" = i valori di sempre di fluidsynth).
    reverb_room: str = "stanza"
    # Catena di effetti sul master (core.effects): elabora il mix finale del
    # brano, in ascolto e nell'export WAV (vedi core.effect_render.apply_master).
    master_effects: List[Effect] = field(default_factory=list)
    # Strumenti definiti nel file del brano (blocchi "Strumento Nome:"): per
    # le tracce di questo brano valgono loro (vedi Track.instrument_def).
    instruments: Dict[str, InstrumentProfile] = field(default_factory=dict)
    # Battuta in levare, in quarti (intestazione "Levare:"): la battuta 1 e'
    # la prima intera e comincia li'. 0 = nessun levare.
    pickup: float = 0.0
    # Versione del linguaggio dichiarata dal file ("ST: 2.6"), se c'era.
    st_version: Optional[tuple] = None
    # Tonalita' per battuta ("Tonalita: 1: C, 17: G"): [(battuta, "G")]; se
    # popolata, key e' la tonalita' della battuta 1.
    key_changes: List[tuple] = field(default_factory=list)
    # Titolo e autori del brano (intestazioni Titolo:, Autore:, Parole:):
    # vanno nella partitura; senza titolo la partitura usa name.
    title: str = ""
    composer: str = ""
    lyricist: str = ""

    def meter(self) -> Meter:
        """Dove cominciano le battute del progetto (per le ancore bar=N)."""
        return Meter(self.time_sig, self.metrica_changes, self.pickup)

    def add_track(self, name: str, instrument_name: str, text: str = "") -> Track:
        if instrument_name not in self.instruments:
            get_instrument(instrument_name)  # valida che lo strumento esista
        t = Track(name=name, instrument_name=instrument_name, text=text,
                  instrument_def=self.instruments.get(instrument_name))
        self.tracks.append(t)
        return t

    def add_audio_track(self, name: str) -> Track:
        if any(t.name == name for t in self.tracks):
            raise ValueError(tr("Esiste gia' una traccia chiamata '{name}'.", name=name))
        t = Track(name=name, instrument_name=AUDIO_INSTRUMENT_NAME, kind="audio")
        self.tracks.append(t)
        return t

    def remove_track(self, name: str):
        self.tracks = [t for t in self.tracks if t.name != name]

    def get_track(self, name: str) -> Track:
        for t in self.tracks:
            if t.name == name:
                return t
        raise KeyError(tr("Traccia '{name}' non trovata", name=name))

    def find_track(self, name: Optional[str]) -> Optional[Track]:
        """La traccia con quel nome, o None (nome vuoto o non esistente)."""
        return next((t for t in self.tracks if name and t.name == name), None)

    def update_track(self, old_name: str, new_name: str, new_instrument: str):
        """Rinomina la traccia e/o le cambia strumento (funzionalita' 2)."""
        track = self.get_track(old_name)
        if new_name != old_name and any(t.name == new_name for t in self.tracks):
            raise ValueError(tr("Esiste gia' una traccia chiamata '{new_name}'.", new_name=new_name))
        if track.is_audio:
            # Una traccia audio resta audio: qui si puo' solo rinominarla.
            track.name = new_name
            return
        if new_instrument not in self.instruments:
            get_instrument(new_instrument)  # valida
        track.name = new_name
        track.instrument_name = new_instrument
        track.instrument_def = self.instruments.get(new_instrument)

    def add_pattern(self, name: str, body_text: str):
        from .notation import tokenize
        self.patterns[name] = Pattern(name=name, tokens=tokenize(body_text))

    def pattern_usages(self, name: str) -> List[str]:
        """Dove il pattern 'name' e' richiamato (%name): tracce, box e altri
        pattern, come etichette da mostrare prima di eliminarlo."""
        ref_re = re.compile(r"%" + re.escape(name) + r"(?!\w)")
        places = []
        for track in self.tracks:
            if track.clips:
                places += [tr("box '{box}' della traccia '{track}'", box=clip.name, track=track.name)
                           for clip in track.clips if ref_re.search(clip.text)]
            elif ref_re.search(track.text):
                places.append(tr("traccia '{track}'", track=track.name))
        for other in self.patterns.values():
            if other.name != name and any(ref_re.search(tok) for tok in other.tokens):
                places.append(tr("pattern '%{pattern}'", pattern=other.name))
        return places

    def rename_pattern(self, old_name: str, new_name: str):
        """Rinomina un pattern e aggiorna tutti i riferimenti %vecchio_nome
        (nel testo di ogni traccia, nei suoi box e nel corpo di ogni altro pattern) in
        %nuovo_nome, cosi' la rinomina non spezza silenziosamente cio' che
        lo richiama (anche dentro i box). new_name deve rispettare la stessa sintassi di un nome
        di pattern nei riferimenti (core.notation.RE_PATTERN_REF: \\w+)."""
        if old_name not in self.patterns:
            raise KeyError(tr("Pattern '{old_name}' non trovato", old_name=old_name))
        if not re.match(r"^\w+$", new_name):
            raise ValueError(
                tr("Nome pattern non valido: '{new_name}' (solo lettere, cifre e underscore, senza spazi).", new_name=new_name)
            )
        if new_name != old_name and new_name in self.patterns:
            raise ValueError(tr("Esiste gia' un pattern chiamato '{new_name}'.", new_name=new_name))

        pattern = self.patterns.pop(old_name)
        pattern.name = new_name
        self.patterns[new_name] = pattern

        # (?!\w) evita di rinominare per sbaglio un riferimento a un pattern
        # con un nome piu' lungo che inizia allo stesso modo (es. %Vamp non
        # deve toccare %VampIntro).
        ref_re = re.compile(r"%" + re.escape(old_name) + r"(?!\w)")
        for track in self.tracks:
            track.text = ref_re.sub("%" + new_name, track.text)
            for clip in track.clips:
                clip.text = ref_re.sub("%" + new_name, clip.text)
        for other in self.patterns.values():
            if other is pattern:
                continue
            other.tokens = [ref_re.sub("%" + new_name, tok) for tok in other.tokens]

    def rename_midi_ref(self, old_names: List[str], new_name: str, apply: bool = True) -> int:
        """Riscrive i richiami &"vecchio" (per ognuno dei nomi di old_names:
        per esempio "Sub/Nome" e "Nome") in &"new_name", nelle tracce, nei
        box e nei pattern; moltiplicatore e trasposizione (+N/-N) restano.
        Ritorna quanti richiami ha cambiato (apply=False: solo li conta)."""
        if not old_names:
            return 0
        names = "|".join(re.escape(n) for n in old_names)
        ref_re = re.compile(r'&"(?:' + names + r')"')
        count = 0

        def sub(text: str) -> str:
            nonlocal count
            text, n = ref_re.subn(lambda _m: '&"' + new_name + '"', text)
            count += n
            return text

        for track in self.tracks:
            text = sub(track.text)
            clips = [sub(clip.text) for clip in track.clips]
            if apply:
                track.text = text
                for clip, clip_text in zip(track.clips, clips):
                    clip.text = clip_text
        for pattern in self.patterns.values():
            tokens = [sub(tok) for tok in pattern.tokens]
            if apply:
                pattern.tokens = tokens
        return count

    def audible_tracks(self) -> List[Track]:
        """Applica la logica Solo/Mute: se almeno una traccia e' in Solo,
        suonano solo le tracce in Solo (che non siano anche Mute)."""
        any_solo = any(t.solo for t in self.tracks)
        result = []
        for t in self.tracks:
            if t.mute:
                continue
            if any_solo and not t.solo:
                continue
            result.append(t)
        return result
