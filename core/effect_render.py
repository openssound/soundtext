"""
Rendering delle tracce con una catena di effetti (fase 2 degli effetti).

Una traccia con effetti accesi non entra nel rendering unico del brano: la
si renderizza da sola (tracce di testo: sintesi del suo MIDI; tracce audio:
mix delle sue clip), la si fa passare per la catena (core.effects) e la si
somma al resto come "stem" (core.audio_tracks.mix_layers).

Due cache in memoria, per non rifare lavoro inutile:
- la traccia "asciutta" (prima degli effetti), che cambia solo se cambiano
  le note, le clip, il volume/pan o il suono del synth;
- la traccia elaborata, che dipende anche dai parametri della catena.
Cambiare una manopola rifa' quindi solo l'elaborazione (decimi di secondo),
non la sintesi; e cambiare un'altra traccia non tocca questa.

prepare_stem va chiamata sul thread principale (legge il progetto, che puo'
cambiare subito dopo), render_stem anche in un thread di sottofondo.
"""

import copy
import hashlib
import os
import tempfile
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from .effects import (DRY_SYNTH_ROOM, active_effects, apply_effect_chain, chain_signature, effects_available,
                      lv2_instrument_missing, plugin_substitute, synth_dry_for)
from .model import Project, Track

# Memoria massima delle due cache insieme (una traccia stereo di 3 minuti a
# 48 kHz occupa circa 70 MB).
STEM_CACHE_BYTES = 600 * 1024 * 1024

_cache: "OrderedDict[str, np.ndarray]" = OrderedDict()
_cache_lock = threading.Lock()


def _cache_get(key: str) -> Optional[np.ndarray]:
    with _cache_lock:
        value = _cache.pop(key, None)
        if value is not None:
            _cache[key] = value      # piu' recente in fondo
        return value


def _cache_put(key: str, value: np.ndarray):
    with _cache_lock:
        _cache.pop(key, None)
        _cache[key] = value
        total = sum(v.nbytes for v in _cache.values())
        while total > STEM_CACHE_BYTES and len(_cache) > 1:
            _key, old = _cache.popitem(last=False)
            total -= old.nbytes


def clear_stem_cache():
    with _cache_lock:
        _cache.clear()


# Un lock per chiave di cache: chi chiede una traccia che un altro thread
# sta gia' renderizzando (il pre-rendering, vedi prerender_stems) aspetta
# quel risultato invece di rifare lo stesso lavoro.
_key_locks: dict = {}
_key_locks_lock = threading.Lock()


def _key_lock(key: str) -> threading.Lock:
    with _key_locks_lock:
        lock = _key_locks.get(key)
        if lock is None:
            if len(_key_locks) > 1024:      # chiavi vecchie: si tengono solo quelle in uso
                for old in [k for k, v in _key_locks.items() if not v.locked()]:
                    del _key_locks[old]
            lock = _key_locks[key] = threading.Lock()
        return lock


def fx_tracks(tracks: List[Track]) -> List[Track]:
    """Le tracce che vanno renderizzate a parte: quelle con almeno un
    effetto acceso (se pedalboard e' installato) e quelle suonate da uno
    strumento plugin (Track.synth)."""
    with_fx = effects_available()
    return [t for t in tracks if (with_fx and active_effects(t.effects)) or (t.synth and not t.is_audio)]


def plugin_uses(project: Project) -> list:
    """I plugin che l'ascolto del brano usera': (ref, parametri, stato) degli
    strumenti plugin delle tracce di testo e degli effetti plugin accesi
    (tracce e master), senza doppioni."""
    uses = [(t.synth, t.synth_params, t.synth_state) for t in project.tracks
            if t.synth and not t.is_audio and t.text.strip() and not lv2_instrument_missing(t.synth)]
    if effects_available():
        for chain in [t.effects for t in project.tracks] + [project.master_effects]:
            uses += [(e.plugin, e.plugin_params, e.plugin_state) for e in active_effects(chain)
                     if e.kind == "plugin" and e.plugin and plugin_substitute(e) is None]
    out, seen = [], set()
    for ref, params, state in uses:
        key = (ref, tuple(sorted((params or {}).items())), state or "")
        if key not in seen:
            seen.add(key)
            out.append((ref, dict(params or {}), state or ""))
    return out


def warm_plugins(project: Project) -> Optional[threading.Thread]:
    """Carica in sottofondo, nel processo del rendering, i plugin del brano
    (vedi plugin_uses): il primo Play non aspetta l'avvio del processo e il
    caricamento dei plugin (decine di secondi per un VST3 grande). Un plugin
    che non si carica qui fallira' poi al rendering, che ripiega sul
    SoundFont come sempre."""
    from .audio_tracks import AUDIO_SAMPLE_RATE

    uses = plugin_uses(project)
    if not uses:
        return None

    def warm_all(group):
        from .plugins import PluginError, warm
        for ref, params, state in group:
            try:
                warm(ref, params, state, AUDIO_SAMPLE_RATE)
            except (PluginError, OSError) as e:
                import logging
                logging.getLogger(__name__).info("Plugin %s non precaricato: %s", ref, e)

    def work():
        # Un gruppo per processo del rendering, in parallelo: ogni processo
        # si avvia e carica i suoi plugin mentre gli altri fanno lo stesso.
        from .plugins import render_channel
        groups = {}
        for use in uses:
            groups.setdefault(render_channel(use[0]), []).append(use)
        threads = [threading.Thread(target=warm_all, args=(g,), daemon=True) for g in groups.values()]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    thread = threading.Thread(target=work, daemon=True)
    thread.start()
    return thread


_prerender_generation = 0


def prerender_stems(project: Project) -> Optional[threading.Thread]:
    """Renderizza in sottofondo, nella cache, le tracce con effetti o
    strumenti plugin che il Play userebbe ora (stesse tracce udibili, stesse
    chiavi: vedi PlaybackEngine.play): al Play sono gia' pronte. Lavora su
    una copia del progetto, quindi si puo' chiamare dal thread principale
    senza bloccarlo; una chiamata successiva annulla quella in corso (il
    plugin che sta suonando finisce comunque il suo pezzo). Se il Play
    arriva prima che abbia finito, aspetta la traccia in corso invece di
    rifarla (vedi _key_lock)."""
    global _prerender_generation
    _prerender_generation += 1
    generation = _prerender_generation
    snapshot = copy.deepcopy(project)

    def work():
        from .tempo_map import build_tempo_beat_map
        requests = []
        try:
            tracks = snapshot.audible_tracks()
            fx = fx_tracks([t for t in tracks if t.is_audio or t.text.strip()])
            if not fx:
                return
            tempo_map = build_tempo_beat_map(snapshot, tracks=tracks)
            requests = [prepare_stem(snapshot, t, tempo_map) for t in fx]
            render_stems(requests, lambda: _prerender_generation != generation)
        except RuntimeError:
            pass                 # annullato da una modifica successiva
        except Exception as e:   # per esempio una traccia con un errore di sintassi mentre si scrive
            import logging
            logging.getLogger(__name__).debug("Pre-rendering non riuscito: %s", e)
        finally:
            for request in requests:
                request.cleanup()

    thread = threading.Thread(target=work, daemon=True)
    thread.start()
    return thread

@dataclass
class StemRequest:
    """Tutto cio' che serve a renderizzare una traccia con effetti, preso
    dal progetto al momento della richiesta."""
    track_name: str
    dry_key: str
    effects: list
    midi_path: Optional[str] = None           # traccia di testo: il suo MIDI (file temporaneo)
    channel_overrides: Optional[dict] = None
    reverb_room: Optional[str] = None
    layers: list = field(default_factory=list)  # traccia audio: le sue clip
    bpm: float = 120.0                          # per il delay a tempo
    # traccia suonata da uno strumento plugin (vedi core.plugins)
    synth: str = ""
    synth_params: dict = field(default_factory=dict)
    synth_state: str = ""
    # Il pan della traccia si applica dopo la catena (vedi apply_pan): la
    # traccia asciutta e' al centro, cosi' un ampli mono (NAM) non riporta
    # al centro una chitarra spostata a sinistra.
    pan: int = 64

    @property
    def wet_key(self) -> str:
        return self.dry_key + "|" + chain_signature(self.effects, self.bpm) + f"|pan{self.pan}"

    def cleanup(self):
        if self.midi_path and os.path.exists(self.midi_path):
            try:
                os.remove(self.midi_path)
            except OSError:
                pass
        self.midi_path = None


def prepare_stem(project: Project, track: Track, tempo_map) -> StemRequest:
    """La richiesta di rendering di 'track' (con una copia della sua catena)."""
    from .audio_tracks import build_audio_layers, layers_signature
    from .midi_export import export_project_to_midi
    from .playback import _find_soundfont, _resolve_channel_soundfont_overrides
    from .settings import get_playback_gain

    effects = copy.deepcopy(track.effects)
    pan = track.pan
    centered = copy.copy(track)          # la traccia asciutta, al centro (vedi StemRequest.pan)
    centered.pan = 64
    if track.is_audio:
        layers = build_audio_layers(project, [centered], tempo_map)
        key = hashlib.sha1(("audio" + layers_signature(layers)).encode()).hexdigest()
        return StemRequest(track.name, key, effects, layers=layers, bpm=project.tempo_bpm, pan=pan)
    handle = tempfile.NamedTemporaryFile(suffix=".mid", delete=False)
    handle.close()
    export_project_to_midi(project, handle.name, tracks=[centered])
    if track.synth and not lv2_instrument_missing(track.synth):
        from .plugins import signature as plugin_signature
        with open(handle.name, "rb") as f:
            digest = hashlib.sha1(f.read())
        digest.update(repr(plugin_signature(track.synth, track.synth_params, track.synth_state)).encode())
        return StemRequest(track.name, "synth" + digest.hexdigest(), effects, midi_path=handle.name,
                           reverb_room=project.reverb_room, bpm=project.tempo_bpm, synth=track.synth, synth_params=dict(track.synth_params),
                           synth_state=track.synth_state, pan=pan)
    overrides = _resolve_channel_soundfont_overrides(project, False, tracks=[track])
    # verso un amplificatore simulato la traccia va senza riverbero e chorus del synth
    room = DRY_SYNTH_ROOM if synth_dry_for(effects) else project.reverb_room
    with open(handle.name, "rb") as f:
        digest = hashlib.sha1(f.read())
    digest.update(repr((_find_soundfont(), sorted((overrides or {}).items()), get_playback_gain(),
                        room)).encode())
    return StemRequest(track.name, "midi" + digest.hexdigest(), effects, midi_path=handle.name,
                       channel_overrides=overrides, reverb_room=room, bpm=project.tempo_bpm,
                       pan=pan)


def render_dry(request: StemRequest, stop_check=None) -> Optional[np.ndarray]:
    """La traccia prima degli effetti (float32 (frame, 2) a 48 kHz), dalla
    cache o renderizzata ora. None se non si puo' (niente SoundFont...).
    Solleva RuntimeError se annullata."""
    dry = _cache_get(request.dry_key)
    if dry is not None:
        return dry
    with _key_lock(request.dry_key):
        return _render_dry_locked(request, stop_check)


def _render_dry_locked(request: StemRequest, stop_check=None) -> Optional[np.ndarray]:
    from .audio_tracks import AUDIO_SAMPLE_RATE, mix_layers, resample

    dry = _cache_get(request.dry_key)      # renderizzata intanto da chi teneva il lock
    if dry is not None:
        return dry
    if request.synth:
        dry = render_synth(request, stop_check)
    if dry is None and request.midi_path is not None:
        # traccia di testo col SoundFont (anche quando il suo strumento
        # plugin non funziona: meglio sentirla col SoundFont che non sentirla)
        from .playback import render_midi_file_to_samples
        try:
            dry, rate = render_midi_file_to_samples(request.midi_path, request.channel_overrides,
                                                    request.reverb_room, stop_check)
        except RuntimeError:
            if stop_check and stop_check():
                raise
            return None
        if rate != AUDIO_SAMPLE_RATE and len(dry):
            dry = resample(dry, rate, AUDIO_SAMPLE_RATE)
    elif dry is None:
        dry = mix_layers(np.zeros((0, 2), dtype=np.float32), AUDIO_SAMPLE_RATE, request.layers)
    dry = np.ascontiguousarray(dry, dtype=np.float32)
    _cache_put(request.dry_key, dry)
    return dry


SYNTH_TAIL_SECONDS = 4.0


def render_synth(request: StemRequest, stop_check=None) -> Optional[np.ndarray]:
    """Le note della traccia suonate dal suo strumento plugin, a 48 kHz, al
    centro (il pan arriva dopo la catena, vedi apply_pan; il volume e' gia'
    nella velocity delle note).
    None se il plugin non si carica o non risponde (l'errore va nel log)."""
    from .audio_tracks import AUDIO_SAMPLE_RATE
    from .plugins import PluginError, midi_file_events, render_events

    # Niente describe() preventivo: caricherebbe il plugin una seconda volta
    # (nel processo dell'interfaccia, con l'elenco di tutti i parametri) solo
    # per scoprirne un errore che render_events riporta comunque.
    events, end = midi_file_events(request.midi_path)
    if stop_check and stop_check():
        raise RuntimeError("annullato")
    try:
        y = render_events(request.synth, request.synth_params, request.synth_state, events,
                          end + SYNTH_TAIL_SECONDS, AUDIO_SAMPLE_RATE)
    except PluginError as e:
        import logging
        logging.getLogger(__name__).warning("Strumento plugin %s non usato per «%s»: %s",
                                            request.synth, request.track_name, e)
        return None
    # la coda dopo l'ultima nota si tiene fin dove suona ancora: si cerca
    # solo li' (su tutto il brano costava quasi un secondo a traccia)
    notes_end = int(end * AUDIO_SAMPLE_RATE)
    tail = y[notes_end:]
    loud = np.flatnonzero((np.abs(tail) > 1e-5).any(axis=1)) if len(tail) else []
    return np.ascontiguousarray(y[:notes_end + (int(loud[-1]) + 1 if len(loud) else 0)], dtype=np.float32)


def apply_pan(samples: np.ndarray, request: StemRequest) -> np.ndarray:
    """Il pan della traccia sulla traccia gia' elaborata dalla catena, come
    in un mixer: gli effetti (ampli mono compresi) lavorano sul suono al
    centro, poi lo si sposta. Tracce audio: bilanciamento, come nel mix
    delle clip; tracce di note: potenza costante, come il pan del synth
    (al centro il livello resta quello di prima)."""
    if request.pan == 64:
        return samples
    if request.layers or request.midi_path is None:
        from .audio_tracks import _pan_gains
        left, right = _pan_gains(request.pan)
    else:
        angle = (max(0, min(127, request.pan)) / 127.0) * np.pi / 2
        left, right = np.sqrt(2.0) * np.cos(angle), np.sqrt(2.0) * np.sin(angle)
    return np.multiply(samples, np.array([left, right], dtype=np.float32), dtype=np.float32)


def render_stem(request: StemRequest, stop_check=None) -> Optional[np.ndarray]:
    """La traccia elaborata dalla catena (con le code di delay e riverbero),
    a 48 kHz, dall'inizio del brano. None se la traccia non si puo'
    renderizzare."""
    from .audio_tracks import AUDIO_SAMPLE_RATE

    wet = _cache_get(request.wet_key)
    if wet is not None:
        return wet
    with _key_lock(request.wet_key):
        wet = _cache_get(request.wet_key)
        if wet is not None:
            return wet
        dry = render_dry(request, stop_check)
        if dry is None:
            return None
        wet = apply_pan(apply_effect_chain(dry, AUDIO_SAMPLE_RATE, request.effects, bpm=request.bpm), request)
        _cache_put(request.wet_key, wet)
        return wet


def render_stems(requests: List[StemRequest], stop_check=None) -> List[Optional[np.ndarray]]:
    """render_stem di ogni richiesta, in parallelo (un thread per traccia):
    i plugin lavorano nei loro processi (vedi core.plugins.render_channel)
    e la sintesi col SoundFont ha il suo lock, quindi le tracce si
    sovrappongono invece di sommarsi. Solleva RuntimeError se annullata."""
    if len(requests) <= 1:
        return [render_stem(r, stop_check) for r in requests]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=min(8, len(requests))) as pool:
        futures = [pool.submit(render_stem, r, stop_check) for r in requests]
        return [f.result() for f in futures]


def render_stem_window(request: StemRequest, start_seconds: float, end_seconds: float,
                       preroll: float = 2.0, stop_check=None) -> Optional[np.ndarray]:
    """Solo il tratto [start, end) della traccia elaborata, veloce: la
    catena lavora su quei secondi piu' 'preroll' secondi prima (poi
    scartati) perche' compressore, delay e riverbero partano "a regime".
    Serve al loop di calibrazione del pannello Effetti."""
    from .audio_tracks import AUDIO_SAMPLE_RATE

    dry = render_dry(request, stop_check)
    if dry is None:
        return None
    rate = AUDIO_SAMPLE_RATE
    first = max(0, int((start_seconds - preroll) * rate))
    begin = int(start_seconds * rate)
    end = int(end_seconds * rate)
    piece = dry[first:end]
    if len(piece) < end - first:
        piece = np.concatenate([piece, np.zeros((end - first - len(piece), 2), dtype=np.float32)])
    wet = apply_pan(apply_effect_chain(piece, rate, request.effects, with_tail=False, bpm=request.bpm), request)
    return np.ascontiguousarray(wet[begin - first:end - first])


class CalibrationSession:
    """Il loop di calibrazione del pannello Effetti: [start, end) secondi
    della traccia 'track', da risentire a ogni ritocco della catena senza
    rifare il resto. Il costruttore legge il progetto (thread principale);
    prepare() fa la parte lenta (sintesi della traccia e, con 'with_others',
    del resto del brano in quel tratto: in sottofondo); mix(effects) e'
    veloce e da' il loop con la catena data.

    Con track=None si calibra il master: il loop e' il mix di tutto il
    brano e mix(effects) gli applica 'effects' come catena del master.
    Negli altri casi il loop passa comunque per la catena del master del
    progetto, perche' si senta come il brano finito. Il tratto si elabora
    da 'preroll' secondi prima (poi scartati) perche' compressori e
    limiter partano a regime."""

    PREROLL = 2.0

    def __init__(self, project: Project, track: Optional[Track], start_seconds: float, end_seconds: float,
                 with_others: bool = True):
        from .audio_tracks import AUDIO_SAMPLE_RATE, build_audio_layers
        from .midi_export import export_project_to_midi
        from .playback import _resolve_channel_soundfont_overrides
        from .tempo_map import build_tempo_beat_map

        self.start_seconds = max(0.0, start_seconds)
        self.end_seconds = max(self.start_seconds + 0.5, end_seconds)
        self.is_master = track is None
        self.with_others = with_others or self.is_master
        self.bpm = project.tempo_bpm
        self.master_effects = [] if self.is_master else master_chain(project)
        self.preroll = min(self.PREROLL, self.start_seconds)
        self._pre_frames = int(round(self.preroll * AUDIO_SAMPLE_RATE))
        tempo_map = build_tempo_beat_map(project)
        self.target = None if self.is_master else prepare_stem(project, track, tempo_map)
        self._rest = None
        self._others_midi = None
        self._others_overrides = None
        self._others_key = None
        self._other_stems: List[StemRequest] = []
        self._layers = []
        if self.with_others:
            others = [t for t in project.audible_tracks() if t is not track and (t.is_audio or t.text.strip())]
            fx_ids = {id(t) for t in fx_tracks(others)}
            self._other_stems = [prepare_stem(project, t, tempo_map) for t in others if id(t) in fx_ids]
            plain = [t for t in others if id(t) not in fx_ids]
            midi_tracks = [t for t in plain if not t.is_audio]
            self._layers = build_audio_layers(project, plain, tempo_map)
            if midi_tracks:
                handle = tempfile.NamedTemporaryFile(suffix=".mid", delete=False)
                handle.close()
                export_project_to_midi(project, handle.name, tracks=midi_tracks)
                self._others_midi = handle.name
                self._others_overrides = _resolve_channel_soundfont_overrides(project, False, tracks=midi_tracks)
                with open(handle.name, "rb") as f:
                    self._others_key = "rest" + hashlib.sha1(
                        f.read() + repr((self._others_overrides, project.reverb_room)).encode()).hexdigest()
                self._room = project.reverb_room

    @property
    def frames(self) -> int:
        """Frame del loop (senza il tratto di rodaggio)."""
        from .audio_tracks import AUDIO_SAMPLE_RATE
        return int(round((self.end_seconds - self.start_seconds) * AUDIO_SAMPLE_RATE))

    def _window(self, samples: Optional[np.ndarray]) -> np.ndarray:
        """Il tratto di rodaggio piu' il loop, da 'samples' (dall'inizio del brano)."""
        from .audio_tracks import AUDIO_SAMPLE_RATE
        total = self._pre_frames + self.frames
        out = np.zeros((total, 2), dtype=np.float32)
        if samples is None:
            return out
        first = int(round(self.start_seconds * AUDIO_SAMPLE_RATE)) - self._pre_frames
        part = samples[first:first + total]
        out[:len(part)] = part[:, :2]
        return out

    def prepare(self, stop_check=None):
        """La parte lenta: la traccia asciutta e il resto del brano nel
        tratto del loop. Solleva RuntimeError se annullata."""
        from .audio_tracks import AUDIO_SAMPLE_RATE, mix_layers, resample

        if self.target is not None:
            render_dry(self.target, stop_check)
        rest = np.zeros((self._pre_frames + self.frames, 2), dtype=np.float32)
        if self.with_others:
            if self._others_midi is not None:
                full = _cache_get(self._others_key)
                if full is None:
                    from .playback import render_midi_file_to_samples
                    try:
                        full, rate = render_midi_file_to_samples(self._others_midi, self._others_overrides,
                                                                 self._room, stop_check)
                    except RuntimeError:
                        if stop_check and stop_check():
                            raise
                        full, rate = None, AUDIO_SAMPLE_RATE
                    if full is not None:
                        if rate != AUDIO_SAMPLE_RATE and len(full):
                            full = resample(full, rate, AUDIO_SAMPLE_RATE)
                        full = np.ascontiguousarray(full, dtype=np.float32)
                        _cache_put(self._others_key, full)
                rest += self._window(full)
            if self._layers:
                rest += self._window(mix_layers(np.zeros((0, 2), dtype=np.float32), AUDIO_SAMPLE_RATE,
                                                self._layers))
            for stem in self._other_stems:
                rest += self._window(render_stem(stem, stop_check))
        self._rest = rest

    @property
    def ready(self) -> bool:
        return self._rest is not None

    def mix(self, effects) -> np.ndarray:
        """Il loop (float32 (frame, 2)): la traccia elaborata da 'effects'
        (lista vuota = asciutta) sopra al resto, poi la catena del master;
        per il master, il mix con 'effects' come catena del master."""
        from .audio_tracks import AUDIO_SAMPLE_RATE

        out = (self._rest.copy() if self._rest is not None
               else np.zeros((self._pre_frames + self.frames, 2), dtype=np.float32))
        if self.target is not None:
            request = copy.copy(self.target)
            request.effects = copy.deepcopy(effects)
            wet = render_stem_window(request, self.start_seconds - self.preroll, self.end_seconds)
            if wet is not None:
                out[:len(wet)] += wet[:len(out)]
        master = effects if self.is_master else self.master_effects
        if active_effects(master):
            out = apply_effect_chain(out, AUDIO_SAMPLE_RATE, master, with_tail=False, bpm=self.bpm)
        return np.ascontiguousarray(out[self._pre_frames:self._pre_frames + self.frames])

    def cleanup(self):
        if self.target is not None:
            self.target.cleanup()
        for stem in self._other_stems:
            stem.cleanup()
        if self._others_midi and os.path.exists(self._others_midi):
            try:
                os.remove(self._others_midi)
            except OSError:
                pass
        self._others_midi = None


# ---------------------------------------------------------------------------
# Catena sul master: elabora il mix finale del brano (Project.master_effects).
# ---------------------------------------------------------------------------

def master_chain(project: Project) -> list:
    """Copia della catena del master se ha effetti accesi (e pedalboard c'e'),
    altrimenti lista vuota: niente elaborazione, il mix resta quello di prima."""
    if not effects_available() or not active_effects(project.master_effects):
        return []
    return copy.deepcopy(project.master_effects)


def master_signature(project: Project) -> str:
    """Parte della chiave di cache dell'ascolto che dipende dal master
    ('' senza catena, cosi' le chiavi restano quelle di prima)."""
    chain = master_chain(project)
    return chain_signature(chain, project.tempo_bpm) if chain else ""


def apply_master(samples: np.ndarray, rate: int, effects, bpm: float = 120.0) -> np.ndarray:
    """Il mix 'samples' (float32 (frame, 2)) passato per la catena del master
    (con le code di delay/riverbero)."""
    if not active_effects(effects):
        return samples
    return apply_effect_chain(np.ascontiguousarray(samples[:, :2], dtype=np.float32), rate, effects, bpm=bpm)


def apply_master_int16(entry: tuple, effects, bpm: float = 120.0) -> tuple:
    """Come apply_master, per i campioni int16 (frame, canali) della cache di
    ascolto (core.playback)."""
    samples, rate = entry
    if not active_effects(effects) or len(samples) == 0:
        return entry
    x = samples.astype(np.float32) / 32768.0
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    y = apply_master(x, rate, effects, bpm)
    return (np.clip(y * 32767.0, -32768, 32767).astype(np.int16), rate)
