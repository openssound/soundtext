"""
Conversione delle note di un canale MIDI (analizzato da
core.midi_convert.analyze_midi) in token della notazione: quantizzazione
su griglie di sedicesimi o tuplet scelte battito per battito, separazione
delle sovrapposizioni in voci, articolazioni, dinamiche, slide dal pitch
bend, pedale del sustain e marcatori di tempo.
"""

import bisect
from collections import Counter, defaultdict
from typing import TYPE_CHECKING, Dict, List, Optional

from .instruments import PERCUSSION_MAP
from .chords import midi_to_token, midi_to_pitch, recognize_chord, pc_to_letter, CHORD_QUALITIES

if TYPE_CHECKING:
    from .midi_convert import ChannelData


SIXTEENTH_FRACTION = 0.25  # in beat (quarti)

# Posizioni sulla timeline dell'import, in unita' intere: 420 = mcm(3,4,5,6,7)
# per beat, cosi' tutte le suddivisioni supportate (sedicesimi, terzine,
# sestine, quintine, settimine) cadono su interi e non c'e' deriva.
BEAT_UNITS = 420

# Suddivisioni per beat -> comando griglia di ST (sezione 2.1bis/3)
GRID_COMMANDS = {4: "16:", 3: "8T:", 6: "16T:", 5: "16Q:", 7: "16S:"}

# Scarto massimo (in beat) fra un attacco e il punto di griglia perche' la
# griglia sia considerata "adatta" a quella battuta (~10 ms a 120 BPM).
GRID_FIT_TOLERANCE = 0.03

# Al massimo tante voci per canale nell'import (unite poi in blocchi { ; },
# vedi core.voice_merge)
MAX_IMPORT_VOICES = 2

def _nearest_percussion(note: int) -> str:
    best_name, best_dist = "kick", 999
    for name, midi_n in PERCUSSION_MAP.items():
        d = abs(midi_n - note)
        if d < best_dist:
            best_name, best_dist = name, d
    return best_name

def _chord_symbol_for_notes(midi_notes: List[int]) -> Optional[str]:
    """Se le note simultanee corrispondono a una qualita' di accordo nota
    (vedi core.chords.recognize_chord), ritorna il token implicito
    equivalente (es. 'Cmaj7*3'); None se l'accordo non e' riconoscibile
    (es. note estranee) — in quel caso il chiamante deve ricadere sul
    blocco esplicito [...]."""
    recognized = recognize_chord(midi_notes)
    if recognized is None:
        return None
    root_pc, quality, anchor_octave = recognized
    # Il simbolo rigenera il voicing: va usato solo se riproduce le note
    # suonate. Con note estranee all'accordo (una 6a sopra una quinta ->
    # 'A5'), raddoppi o rivolti (fondamentale non al basso) il simbolo le
    # perderebbe o le sposterebbe: in quei casi resta il blocco esplicito.
    pcs = [n % 12 for n in midi_notes]
    chord_pcs = {(root_pc + iv) % 12 for iv in CHORD_QUALITIES[quality]}
    if set(pcs) != chord_pcs or len(pcs) != len(set(pcs)) or min(midi_notes) % 12 != root_pc:
        return None
    if quality == "maj":
        quality = ""  # forma idiomatica: 'C', non 'Cmaj', per l'accordo maggiore semplice
    symbol = pc_to_letter(root_pc).upper() + quality
    return f"{symbol}*{anchor_octave}"

def _slide_import_durations(dur_slots: int, peak_fraction: float, num_waypoints: int) -> List[int]:
    """Converte la posizione temporale del picco (peak_fraction, vedi
    _collect_pitch_bend_targets) in un numero di sedicesimi per ciascuna
    tappa dello slide importato, in modo che la somma torni ESATTAMENTE
    dur_slots (mai approssimata per eccesso/difetto, altrimenti la nota
    importata avrebbe una durata complessiva diversa da quella MIDI
    originale): l'ultima tappa assorbe sempre il resto della divisione
    invece di essere arrotondata anch'essa in modo indipendente. Sostituisce
    la vecchia assunzione implicita di una divisione sempre a meta' fra
    rampa e mantenimento con il timing reale rilevato nel MIDI sorgente.

    num_waypoints e' il numero di tappe DOPO la nota di partenza (1 per un
    bend-and-hold, 2 per un bend-and-release): il valore di ritorno ha
    sempre num_waypoints + 1 elementi (uno per ogni nota della catena)."""
    if num_waypoints == 1:
        # bend-and-hold: [rampa verso il picco, mantenimento sul picco].
        ramp_slots = max(1, min(dur_slots, round(peak_fraction * dur_slots)))
        return [ramp_slots, dur_slots - ramp_slots]
    # bend-and-release: [rampa verso il picco, rilascio verso il valore
    # finale]; nessun mantenimento successivo, dato che il rilascio occupa
    # per costruzione tutto il tempo rimanente fino alla fine della nota.
    if dur_slots > 1:
        ramp1_slots = max(1, min(dur_slots - 1, round(peak_fraction * dur_slots)))
    else:
        ramp1_slots = dur_slots
    return [ramp1_slots, dur_slots - ramp1_slots, 0]

def _bend_taps(start_note, waypoints, peak_fraction, onset_fraction, release, dur_slots):
    """Tappe (altezze MIDI, durate in unita') dello slide che riproduce un
    bend con il timing rilevato: (fermo iniziale) -> salita al picco ->
    (tenuta sul picco -> rilascio -> tenuta finale). Ogni tappa e' un punto
    della spezzata (frazione della nota, altezza); la sua durata e' la
    distanza dal punto successivo (l'ultima: fino a fine nota), come nella
    sintassi a catena di ST. Una tenuta e' una rampa piatta (stessa altezza
    su due tappe consecutive). Ogni tratto con cambio d'altezza dura almeno
    un'unita'; un tratto piatto di durata 0 si omette. Ritorna None se non
    c'e' spazio (troppe rampe per la durata): il chiamante usa allora il
    modello a durate semplici (_slide_import_durations)."""
    peak = waypoints[0]
    pts = [(0.0, start_note)]
    if onset_fraction > 0:
        pts.append((onset_fraction, start_note))
    pts.append((max(peak_fraction, onset_fraction), peak))
    if len(waypoints) == 2:
        end = waypoints[1]
        if release is None or release[0] >= 1.0:
            pts.append((1.0, end))  # rilascio lineare fino a fine nota
        elif round(release[0] * dur_slots) < dur_slots:
            pts.append((release[0], peak))
            pts.append((max(release[1], release[0]), end))
        # else: il rilascio inizia nell'ultimo istante -> solo bend con tenuta

    return _points_to_taps(pts, dur_slots)

def _points_to_taps(pts, dur_slots):
    """Da una spezzata [(frazione, altezza MIDI), ...] (la prima a frazione 0)
    alle tappe (altezze, durate in unita') della catena di ST: vedi
    _bend_taps per la convenzione. None se non c'e' spazio."""
    n = len(pts)
    ramp = [1 if pts[i + 1][1] != pts[i][1] else 0 for i in range(n - 1)]
    if sum(ramp) > dur_slots:
        return None
    bounds = [0] + [round(t * dur_slots) for t, _ in pts[1:]]
    bounds[-1] = min(bounds[-1], dur_slots)
    for i in range(n - 2, 0, -1):          # lascia spazio alle rampe successive
        bounds[i] = min(bounds[i], bounds[i + 1] - ramp[i])
    for i in range(1, n):                  # e almeno un'unita' a ogni rampa
        bounds[i] = max(bounds[i], bounds[i - 1] + ramp[i - 1])
    if bounds[-1] > dur_slots:
        return None
    notes, durations = [], []
    for i in range(n):
        span = (bounds[i + 1] if i + 1 < n else dur_slots) - bounds[i]
        if span == 0 and i + 1 < n and not ramp[i]:
            continue  # tenuta di durata 0: si fonde con la tappa seguente
        notes.append(pts[i][1])
        durations.append(span)
    return notes, durations

def channel_to_tokens(channel: "ChannelData", ticks_per_beat: int,
                       recognize_chords: bool = False,
                       tempo_changes: Optional[List[tuple]] = None) -> List[str]:
    """Vedi _channel_to_tokens_impl (questo e' solo il wrapper che scarta lo
    scostamento dei marcatori di tempo)."""
    return _channel_to_tokens_impl(channel, ticks_per_beat, recognize_chords, tempo_changes)[0][0]

def channel_to_voices(channel: "ChannelData", ticks_per_beat: int,
                       recognize_chords: bool = False,
                       tempo_changes: Optional[List[tuple]] = None,
                       max_voices: int = MAX_IMPORT_VOICES) -> List[List[str]]:
    """Come channel_to_tokens, ma le note sovrapposte (una nota tenuta sotto una
    melodia, un accordo che continua sotto una voce) vanno in voci separate
    invece di essere accorciate: una lista di token per voce, la prima e' la
    "principale" (l'unica con i marcatori di tempo)."""
    return _channel_to_tokens_impl(channel, ticks_per_beat, recognize_chords,
                                   tempo_changes, max_voices)[0]

def tempo_marker_drift(channel: "ChannelData", ticks_per_beat: int,
                        tempo_changes: List[tuple]) -> int:
    """Quanto i marcatori tempo=N di tempo_changes slitterebbero (in sedicesimi,
    sommando tutti i marcatori) se emessi nei token di questo canale: 0 se
    ognuno cade esattamente sul proprio slot, di piu' se cadono dentro note
    lunghe (emessi solo alla fine della nota) - un marcatore che non trova
    piu' alcun token dopo di se' conta come perso (penalita' alta). Serve a
    scegliere la traccia piu' adatta a portare i cambi di tempo (in genere la
    batteria, fatta di colpi brevi)."""
    if not channel.notes:
        return 10 ** 9
    return _channel_to_tokens_impl(channel, ticks_per_beat, False, tempo_changes, MAX_IMPORT_VOICES)[1]

# Valori GM di partenza di volume/pan/espressione prima del primo CC ricevuto
DEFAULT_CC_VOLUME = 100

DEFAULT_CC_EXPRESSION = 127

DEFAULT_CC_PAN = 64  # centro

# Le dinamiche da CC si applicano solo se il livello scende almeno di questa
# frazione sotto il massimo del canale: un volume costante (o quasi) non e'
# una dinamica, e non deve riempire il testo di N@ per variazioni minime.
DYNAMICS_MIN_DEPTH = 0.15

# Articolazioni dedotte dal rapporto fra durata reale della nota e intervallo
# fino all'attacco successivo (stessi effetti dell'export: staccato 50%,
# mute 15%, legato 115% - vedi core.midi_export._ARTICULATION_DURATION_FACTOR).
# Soglie a meta' strada fra i valori nominali e la nota "normale" (~0.85-1).
MUTE_MAX_RATIO = 0.3

STACCATO_MAX_RATIO = 0.7

LEGATO_MIN_RATIO = 1.05

LEGATO_MAX_RATIO = 1.5

# Oltre queste distanze dal prossimo attacco (in beat) una nota corta seguita
# da una lunga pausa e' una nota corta + pausa, non un'articolazione.
ARTICULATION_MAX_IOI_BEATS = 1.0

MUTE_MAX_IOI_BEATS = 0.5

def _dynamics_scale(channel: "ChannelData"):
    """Funzione tick -> fattore di velocity (0..1) che porta in ST le
    dinamiche del canale scritte con volume (CC7) ed espressione (CC11):
    crescendo, diminuendo e fade sono automazioni continue, mentre ST le
    esprime solo come velocity delle note (N@). Il livello e' CC7*CC11 al
    tick d'attacco della nota, normalizzato al massimo del canale (cosi' un
    CC7 costante, tipicamente 100, non abbassa tutte le note). Ritorna None
    se il canale non ha CC o se la profondita' della dinamica e' sotto
    DYNAMICS_MIN_DEPTH."""
    if not channel.notes or not (channel.volume_cc or channel.expression_cc):
        return None

    def series(events, default):
        events = sorted(events, key=lambda e: e[0])
        ticks = [t for t, _ in events]
        values = [v for _, v in events]

        def at(tick):
            i = bisect.bisect_right(ticks, tick)
            return values[i - 1] if i else default
        return at

    volume = series(channel.volume_cc, DEFAULT_CC_VOLUME)
    expression = series(channel.expression_cc, DEFAULT_CC_EXPRESSION)

    def level(tick):
        return volume(tick) * expression(tick)

    levels = [level(start) for start, _e, _n, _v in channel.notes]
    top = max(levels)
    if top <= 0 or min(levels) / top > 1.0 - DYNAMICS_MIN_DEPTH:
        return None
    return lambda tick: level(tick) / top

def _merge_near_simultaneous(fracs: List[float]) -> List[float]:
    """Attacchi quasi simultanei (es. kick e ride colpiti insieme, con
    qualche tick di scarto) sono UN punto ritmico, non due: contarli
    separatamente gonfia le prove a favore delle tuplet meno comuni."""
    merged = []
    for f in sorted(fracs):
        if not merged or f - merged[-1] > GRID_FIT_TOLERANCE:
            merged.append(f)
    return merged

def _fits_grid_ignoring_one_outlier(fracs: List[float], n: int) -> bool:
    """Vero se tutti gli attacchi tranne al piu' uno rientrano nella griglia
    n entro GRID_FIT_TOLERANCE. Un singolo attacco fuori posto (ghost note,
    piccolo anticipo/ritardo di batteria) non deve far scartare una griglia
    altrimenti spiegata bene dal resto della battuta - solo _choose_beat_grid
    con un dominant_grid noto la usa, per risolvere le battute che da sole
    non bastano a decidere (vedi _dominant_swing_grid)."""
    if len(fracs) < 2:
        return False
    errors = sorted(abs(f * n - round(f * n)) / n for f in fracs)
    return errors[-2] <= GRID_FIT_TOLERANCE

def _dominant_swing_grid(onset_fracs: Dict[int, List[float]]) -> int:
    """Griglia (3 = terzine, 4 = dritto, ...) piu' frequente fra le battute
    del canale che hanno prove genuine di suddivisione, per stabilire il
    feel ritmico dominante (es. uno shuffle blues) e risolvere con quello le
    battute singolarmente ambigue in _choose_beat_grid, invece di forzarle a
    sedicesimi per default. Le battute con un solo attacco proprio
    sul movimento (nessuna suddivisione da giudicare) non votano: altrimenti
    in un brano shuffle i tanti quarti "vuoti" affogherebbero le poche
    battute che mostrano davvero la terzina."""
    votes = Counter()
    for fracs in onset_fracs.values():
        merged = _merge_near_simultaneous(fracs)
        if len(merged) < 2 and (not merged or merged[0] < 0.05):
            continue
        votes[_choose_beat_grid(fracs)] += 1
    if not votes:
        return 4
    grid, count = votes.most_common(1)[0]
    # Una maggioranza risicata (poche prove in tutto il canale, o quasi
    # pareggio con lo sfondo dritto) non basta a forzare le battute ambigue.
    if grid == 4 or count < max(3, sum(votes.values()) * 0.3):
        return 4
    return grid

def _choose_beat_grid(fracs: List[float], dominant_grid: Optional[int] = None) -> int:
    """Suddivisione per beat (4 = sedicesimi, 3 = terzine 8T, 6 = 16T,
    5 = quintine 16Q, 7 = settimine 16S) che spiega meglio gli attacchi di
    UNA battuta (fracs = posizione di ciascun attacco dentro il beat, in
    [0, 1)). Vince la griglia binaria se spiega tutti gli attacchi entro
    GRID_FIT_TOLERANCE; una tuplet viene scelta solo se quella binaria non
    li spiega e la tuplet si', con scarto almeno dimezzato: cosi' un
    suonato umano approssimativo non viene scambiato per terzine.

    dominant_grid (vedi _dominant_swing_grid) e' il feel ritmico dominante
    del canale: se la battuta non basta da sola a decidere, ma il resto dei
    suoi attacchi (tutti tranne al piu' un ghost note) e' compatibile con
    quella griglia, la usa invece di ripiegare sempre su sedicesimi - cosi'
    uno shuffle non si spezza beat per beat a causa di una singola nota
    leggermente fuori tempo."""
    fracs = _merge_near_simultaneous(fracs)

    def err(n):
        return max(abs(f * n - round(f * n)) / n for f in fracs)

    err4 = err(4)
    if err4 <= GRID_FIT_TOLERANCE:
        return 4
    unexplained = [f for f in fracs if abs(f * 4 - round(f * 4)) / 4 > GRID_FIT_TOLERANCE]
    e3 = err(3)
    if unexplained and e3 <= GRID_FIT_TOLERANCE and e3 <= err4 / 2:
        return 3
    # Sestine/quintine/settimine: molto piu' facili da "indovinare" per caso
    # su un suonato umano (misurato su un centinaio di MIDI reali: senza
    # queste soglie comparivano ovunque), quindi servono piu' attacchi in
    # battuta e uno scarto molto piu' stretto. Il test e' su "unexplained"
    # (non spiegati dai sedicesimi), non su chi non spiega neanche la
    # terzina: uno shuffle a sedicesimi (es. rullante dritto a meta' beat +
    # cassa/hi-hat in terzina) ha attacchi che singolarmente rientrano ora
    # nei sedicesimi ora nella terzina, ma nessuna delle due griglie da
    # sola spiega TUTTI gli attacchi della battuta - solo la sestina lo fa.
    if len(fracs) >= 3 and len(unexplained) >= 2 and err(6) <= GRID_FIT_TOLERANCE * 0.6:
        return 6
    if len(fracs) >= 4:
        for n in (5, 7):
            if len(unexplained) >= 3 and err(n) <= GRID_FIT_TOLERANCE * 0.4:
                return n
    if dominant_grid and dominant_grid != 4 and _fits_grid_ignoring_one_outlier(fracs, dominant_grid):
        return dominant_grid
    return 4

def _channel_to_tokens_impl(channel: "ChannelData", ticks_per_beat: int,
                             recognize_chords: bool = False,
                             tempo_changes: Optional[List[tuple]] = None,
                             max_voices: int = 1):
    """Quantizza le note di un canale (su una griglia di sedicesimi, o di
    terzine/tuplet nelle battute dove gli attacchi lo richiedono: vedi
    _choose_beat_grid) e le converte in una sequenza di token della
    notazione interna. Se
    recognize_chords e' vero, un gruppo di note simultanee riconosciuto come
    una qualita' di accordo nota viene emesso in forma implicita (es.
    'Cmaj7/3') invece che come blocco esplicito '[...]': piu' leggibile e
    trasportabile, ma verra' ri-vocalizzato automaticamente dal motore per lo
    strumento di destinazione al prossimo export, invece di riprodurre
    esattamente il voicing/registro originale del MIDI importato (che invece
    il blocco esplicito preserva sempre fedelmente).

    Il pedale del sustain (CC64) del canale diventa token SON/SOFF (solo le
    transizioni effettive; un pedale ancora premuto a fine canale viene
    chiuso con un SOFF finale, cosi' non "sfora" nel resto della traccia in
    cui i token vengono incollati). tempo_changes ([(tick, bpm), ...], vedi
    detect_tempo_and_meter) diventa marcatori tempo=N: il tempo e' globale in ST,
    quindi il chiamante li passa a UNA sola traccia. Un marcatore che cadrebbe
    dentro una nota lunga viene emesso al primo punto utile successivo.

    Note sovrapposte: una traccia ST e' una sequenza di token, ognuno con la
    propria durata, e le uniche note simultanee sono quelle dello STESSO
    blocco (stessa durata). Una nota tenuta sotto una melodia che scorre, o un
    accordo che continua mentre la voce canta, si sovrappongono invece nel
    MIDI. Il canale viene quindi separato in "voci" monofoniche (al massimo
    max_voices, sempre 1 per la batteria): ogni gruppo di note che inizia
    insieme e finisce (entro un'unita') insieme va nella prima voce libera, o
    in una nuova; sovrapposizioni minime (entro un'unita') accorciano la nota
    precedente invece di aprire una voce. A voci esaurite la nota precedente
    viene accorciata all'attacco successivo (si perde solo la durata, mai la
    nota). Ritorna (lista di liste di token, una per voce; scarto dei
    marcatori di tempo nella prima voce).
    """
    if not channel.notes:
        return [[]], 0

    tpb = ticks_per_beat

    # Griglia per battuta (solo quelle non binarie sono memorizzate).
    onset_fracs = defaultdict(list)
    for start, _end, _note, _vel in channel.notes:
        beat, rem = divmod(start, tpb)
        onset_fracs[beat].append(rem / tpb)
    dominant_grid = _dominant_swing_grid(onset_fracs)
    beat_grid = {}
    for beat, fracs in onset_fracs.items():
        n = _choose_beat_grid(fracs, dominant_grid)
        if n != 4:
            beat_grid[beat] = n

    def grid_at(pos):
        return beat_grid.get(pos // BEAT_UNITS, 4)

    def snap(tick):
        n = beat_grid.get(tick // tpb, 4)
        return round(tick * n / tpb) * (BEAT_UNITS // n)

    # events: posizione -> [(nota, velocity, durata in unita' della griglia
    # della battuta d'attacco, bend)]. Una nota che finirebbe dentro una
    # battuta con una griglia diversa da quella d'attacco, in un punto che non
    # e' un confine di battuta, viene chiusa sul confine di battuta: cosi' il
    # cursore resta sempre su un punto valido della griglia in cui si trova,
    # senza deriva del resto della traccia.
    dynamics = _dynamics_scale(channel)
    by_pos: Dict[int, list] = {}  # ps -> [(pe, nota, velocity, bend, tick attacco, tick fine)]
    for start, end, note, vel in channel.notes:
        if dynamics is not None:
            vel = max(1, min(127, round(vel * dynamics(start))))
        ps = snap(start)
        n_s = grid_at(ps)
        unit = BEAT_UNITS // n_s
        pe = max(ps // unit + 1, round(end * n_s / tpb)) * unit
        if pe % BEAT_UNITS and grid_at(pe) != n_s:
            pe = (pe // BEAT_UNITS) * BEAT_UNITS
        bend = channel.bends.get((start, note))
        if bend is not None:
            # (frazione del picco, tappe, nota di partenza o None, frazione di inizio rilascio o None)
            bend = (bend[0], bend[1], bend[2] if len(bend) > 2 else None,
                    channel.bend_release.get((start, note)),
                    channel.bend_onset.get((start, note), 0.0),
                    channel.bend_paths.get((start, note)))
        by_pos.setdefault(ps, []).append((pe, note, vel, bend, start, end))

    # ---- separazione in voci (vedi il docstring) ------------------------
    is_perc = channel.is_percussion
    voice_limit = 1 if (is_perc or max_voices <= 1) else max_voices
    voice_groups: List[list] = []   # per voce: [[ps, pe, [record...]], ...] in ordine di ps
    voice_busy: List[int] = []      # per voce: fine (pe) dell'ultimo gruppo

    def truncate(vi, ps):
        """Accorcia l'ultimo gruppo della voce vi all'attacco ps. Se ps non e'
        un punto della griglia di quel gruppo (griglie diverse) chiude sul
        confine di battuta, come per le note che attraversano una griglia."""
        prev = voice_groups[vi][-1]
        prev_unit = BEAT_UNITS // grid_at(prev[0])
        new_pe = ps if (ps - prev[0]) % prev_unit == 0 else (ps // BEAT_UNITS) * BEAT_UNITS
        if new_pe <= prev[0]:
            return False
        prev[1] = voice_busy[vi] = new_pe
        return True

    for ps in sorted(by_pos):
        unit = BEAT_UNITS // grid_at(ps)
        records = sorted(by_pos[ps], key=lambda r: r[0])   # per fine crescente
        clusters = []   # [fine della prima nota, fine massima, [record]]
        for r in records:
            if clusters and (voice_limit == 1 or r[0] - clusters[-1][0] <= unit):
                clusters[-1][1] = max(clusters[-1][1], r[0])
                clusters[-1][2].append(r)
            else:
                clusters.append([r[0], r[0], [r]])
        for _first_end, group_end, group_records in clusters:
            group = [ps, group_end, group_records]
            free = [v for v in range(len(voice_groups)) if voice_busy[v] <= ps]
            if free:
                vi = max(free, key=lambda v: voice_busy[v])          # la piu' "stretta"
            else:
                overlap = [v for v in range(len(voice_groups)) if voice_busy[v] - ps <= unit]
                vi = min(overlap, key=lambda v: voice_busy[v]) if overlap else None
                if vi is not None and not truncate(vi, ps):
                    vi = None
                if vi is None and len(voice_groups) < voice_limit:
                    voice_groups.append([])
                    voice_busy.append(0)
                    vi = len(voice_groups) - 1
                elif vi is None:
                    # voci esaurite: accorcia quella che finisce prima
                    for v in sorted(range(len(voice_groups)), key=lambda v: voice_busy[v]):
                        if truncate(v, ps):
                            vi = v
                            break
                    if vi is None:
                        # Piu' durate diverse allo STESSO attacco che voci: nessuna
                        # voce puo' accorciare un gruppo che parte insieme a questo.
                        # Il gruppo si fonde con quello, fra i partenti dallo
                        # stesso punto, che finisce piu' vicino (un unico blocco, a
                        # durata massima): niente note perse e mai oltre il tetto.
                        same_onset = [v for v in range(len(voice_groups))
                                      if voice_groups[v] and voice_groups[v][-1][0] == ps]
                        if same_onset:
                            v = min(same_onset, key=lambda v: abs(voice_groups[v][-1][1] - group_end))
                            target = voice_groups[v][-1]
                            target[2].extend(group_records)
                            target[1] = voice_busy[v] = max(target[1], group_end)
                            continue
                        voice_groups.append([])   # non dovrebbe succedere: mai perdere note
                        voice_busy.append(0)
                        vi = len(voice_groups) - 1
            voice_groups[vi].append(group)
            voice_busy[vi] = group_end

    # ---- marcatori (tempo solo nella prima voce; il pedale in ogni voce,
    # cosi' ciascuna resta corretta anche da sola)
    tempo_markers = [(snap(tick), f"tempo={bpm}") for tick, bpm in (tempo_changes or [])]
    pedal_markers = []
    pedal_state = False
    for tick, down in sorted(channel.sustain, key=lambda e: e[0]):
        if down != pedal_state:
            pedal_state = down
            pedal_markers.append((snap(tick), "SON" if down else "SOFF"))

    def emit(groups, with_tempo):
        events: Dict[int, list] = {}
        raw_spans: Dict[int, list] = {}
        max_pos = 0
        for ps, pe, records in groups:
            unit = BEAT_UNITS // grid_at(ps)
            duration = (pe - ps) // unit
            events[ps] = [(note, vel, duration, bend) for _pe, note, vel, bend, _s, _e in records]
            raw_spans[ps] = [(s0, e0) for _pe, _n, _v, _b, s0, e0 in records]
            max_pos = max(max_pos, pe)
        group_positions = sorted(events)
        next_group = dict(zip(group_positions, group_positions[1:]))
        group_tick = {ps: min(st for st, _ in spans) for ps, spans in raw_spans.items()}

        def articulation_at(ps, unit):
            """(modificatore, durata in unita') se le note del gruppo a ps suonano
            staccato/mute/legato rispetto all'attacco successivo, altrimenti None.
            Il token occupa l'intero intervallo fino al prossimo attacco (e' la
            durata 'nominale' di ST); il modificatore ne riproduce la parte
            realmente udibile."""
            pn = next_group.get(ps)
            if pn is None or (pn - ps) % unit:
                return None
            ioi = group_tick[pn] - group_tick[ps]
            if ioi <= 0 or ioi > ARTICULATION_MAX_IOI_BEATS * tpb:
                return None
            spans = raw_spans[ps]
            ratio = sum(e - s for s, e in spans) / len(spans) / ioi
            if ratio <= MUTE_MAX_RATIO:
                modifier = "x" if ioi <= MUTE_MAX_IOI_BEATS * tpb else None
            elif ratio < STACCATO_MAX_RATIO:
                modifier = "!"
            elif LEGATO_MIN_RATIO < ratio <= LEGATO_MAX_RATIO:
                modifier = "_"
            else:
                modifier = None
            return (modifier, (pn - ps) // unit) if modifier else None

        markers = sorted(((tempo_markers if with_tempo else []) + pedal_markers),
                         key=lambda m: m[0])  # stabile: a parita' di posizione, ordine di arrivo
        next_marker = 0
        drift = 0

        tokens = ["16:"]
        current_grid = 4
        pos = 0
        last_velocity = None
        pedal_down = False
        while pos < max_pos:
            while next_marker < len(markers) and markers[next_marker][0] <= pos:
                marker_pos, marker = markers[next_marker]
                if marker.startswith("tempo="):
                    drift += (pos - marker_pos) // (BEAT_UNITS // 4)
                tokens.append(marker)
                if marker == "SON":
                    pedal_down = True
                elif marker == "SOFF":
                    pedal_down = False
                next_marker += 1

            n_here = grid_at(pos)
            if n_here != current_grid:
                tokens.append(GRID_COMMANDS[n_here])
                current_grid = n_here
            unit = BEAT_UNITS // n_here

            events_here = events.get(pos)
            if not events_here:
                tokens.append("r")
                pos += unit
                continue

            # ST ha una sola velocity per token (anche un blocco/accordo): con
            # velocity diverse fra le note simultanee si usa la media arrotondata,
            # che conserva l'intensita' complessiva, invece di quella (arbitraria,
            # dipende dall'ordine di fine nota) della prima nota del gruppo.
            vel = round(sum(e[1] for e in events_here) / len(events_here))
            if vel != last_velocity:
                tokens.append(f"{vel}@")
                last_velocity = vel

            dur_slots = max(d for _, _, d, _ in events_here)
            mult = f"{dur_slots}" if dur_slots > 1 else ""

            if is_perc:
                names = sorted({_nearest_percussion(n) for n, _, _, _ in events_here})
                token_body = names[0] if len(names) == 1 else "[" + " ".join(names) + "]"
            else:
                midi_notes_here = sorted({n for n, _, _, _ in events_here})
                bend_info = next((b for n, _, _, b in events_here if b is not None), None)
                if len(midi_notes_here) == 1 and bend_info is not None:
                    # Nota singola (mai un accordo: lo slide della notazione non
                    # supporta piu' altezze simultanee) con un bending rilevato in
                    # _collect_pitch_bend_targets: emette uno slide (a catena se
                    # bend_waypoints ha piu' di una tappa, cioe' un bend-and-
                    # release) invece del token di altezza semplice, cosi' il
                    # bending sopravvive all'importazione (vedi core.midi_export
                    # per il percorso inverso, che gia' traduce uno slide, anche
                    # a catena, in una rampa pitchwheel).
                    peak_fraction, bend_waypoints = bend_info[0], bend_info[1]
                    # Uno scoop porta come terzo elemento l'altezza di partenza
                    # reale (diversa da quella scritta, vedi _detect_scoop).
                    start_note = bend_info[2] if bend_info[2] is not None else midi_notes_here[0]
                    if bend_info[5] is not None:
                        taps = _points_to_taps(bend_info[5], dur_slots)
                    else:
                        taps = _bend_taps(start_note, bend_waypoints, peak_fraction, bend_info[4],
                                          bend_info[3], dur_slots)
                    if taps is None:
                        chain_notes = [start_note, *bend_waypoints]
                        durations = _slide_import_durations(dur_slots, peak_fraction, len(bend_waypoints))
                    else:
                        chain_notes, durations = taps
                    chain = [midi_to_pitch(n) for n in chain_notes]
                    # Ogni tappa porta gia' la propria durata esplicita (il
                    # timing reale del bend rilevato): il prefisso 'mult'
                    # calcolato sopra per il caso generale va quindi azzerato,
                    # altrimenti la durata della prima tappa verrebbe
                    # concatenata con quella dell'intero token (es. '2' + '1g'
                    # invece di '1g'), producendo una durata complessiva errata.
                    mult = ""
                    token_body = ">".join(
                        f"{durations[i]}{letter}*{octave}" for i, (letter, octave) in enumerate(chain)
                    )
                else:
                    pitches = sorted({midi_to_token(n) for n in midi_notes_here})
                    chord_symbol = None
                    if recognize_chords and len(pitches) > 1:
                        chord_symbol = _chord_symbol_for_notes(midi_notes_here)
                    if chord_symbol is not None:
                        token_body = chord_symbol
                    else:
                        token_body = pitches[0] if len(pitches) == 1 else "[" + " ".join(pitches) + "]"
                    # Il modificatore finale esiste per note singole e accordi
                    # impliciti, non per i blocchi espliciti [...] (vedi 2.2).
                    if len(pitches) == 1 or chord_symbol is not None:
                        art = articulation_at(pos, unit)
                        if art is not None:
                            token_body += art[0]
                            dur_slots = art[1]
                            mult = f"{dur_slots}" if dur_slots > 1 else ""

            tokens.append(mult + token_body)
            pos += dur_slots * unit

        if pedal_down:
            tokens.append("SOFF")
        drift += sum(10 ** 6 for _, m in markers[next_marker:] if m.startswith("tempo="))
        return tokens, drift

    results = [emit(groups, vi == 0) for vi, groups in enumerate(voice_groups)]
    return [tokens for tokens, _ in results], results[0][1]
