"""
Analisi del pitch bend di un canale MIDI importato: riconosce, per ogni
nota, bending, "scoop" e rilasci (anche a catena) da riscrivere come slide
della notazione (c*4>d*4...), distinguendoli dalle oscillazioni di vibrato
e dai pre-bend della nota successiva. Usato da core.midi_convert.analyze_midi.
"""

import bisect
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from .midi_convert import ChannelData


# Un bending importato oltre questa ampiezza (in semitoni) e' quasi certamente
# il sintomo di una sensibilita' RPN non riflette un'intenzione di bending
# nota per nota (es. impostata genericamente su tutti i canali da chi ha
# generato il file, non specificamente per questa nota) piuttosto che un
# bending chitarristico vero: i bending blues/rock reali restano quasi
# sempre entro 2-3 semitoni, raramente oltre una terza (4 semitoni) con
# tecnica estrema - un'ottava piena (12 semitoni, verificato importando un
# MIDI reale su un canale con RPN dichiarato a 12) non e' un bending su
# NESSUNO strumento, chitarra inclusa: sarebbe una nota diversa, non una
# piegatura della stessa. Meglio ignorarlo e importare la nota "piatta" che
# generare uno slide senza senso musicale.
MAX_IMPORTED_BEND_SEMITONES = 12

# Un evento di pitch wheel che si allontana dal centro entro questa distanza
# (in beat) prima dell'attacco della nota successiva, e dopo l'inizio di
# quella corrente, e' il pre-bend della successiva, non un gesto di questa.
NEXT_PREBEND_LEAD_BEATS = 0.1

# Frazione minima del fondo scala del pitch wheel (0..8192) che il picco deve
# raggiungere perche' sia considerato un bending deliberato, indipendentemente
# da quanti semitoni rappresenti alla sensibilita' dichiarata. Verificato su
# MIDI reali: con una sensibilita' RPN ampia (es. 12+ semitoni, usata da
# alcuni patch di chitarra per un'espressione/umanizzazione continua) anche
# un'oscillazione minima del pitch wheel puo' arrotondare a "1 semitone" pur
# non essendo affatto un bending intenzionale - questa soglia e' invece
# sostanzialmente un no-op sulle sensibilita' standard/strette (es. il default
# GM di 2 semitoni), dove il solo arrotondamento al semitono (sotto) e' gia'
# piu' restrittivo di questa frazione.
MIN_BEND_FRACTION_OF_RANGE = 0.10

BEND_ONSET_MIN_FRACTION = 0.15

BEND_LATE_ONSET_FRACTION = 0.5

# Un tuffo oltre il punto di partenza di uno scoop conta se supera questo (semitoni)
BEND_OVERSHOOT_SEMITONES = 1.5

# Scarto massimo (in semitoni) fra la curva del wheel e il suo percorso
# semplificato a tappe (bend a due direzioni, vedi _two_sided_bend_path).
BEND_PATH_TOLERANCE_SEMITONES = 0.7

def _rdp(points, tolerance):
    """Ramer-Douglas-Peucker sulla distanza VERTICALE (semitoni): tiene solo i
    punti necessari a restare entro 'tolerance' dalla curva originale."""
    if len(points) < 3:
        return list(points)
    (t0, y0), (t1, y1) = points[0], points[-1]
    worst, worst_i = 0.0, 0
    for i in range(1, len(points) - 1):
        t, y = points[i]
        line = y0 + (y1 - y0) * ((t - t0) / (t1 - t0) if t1 != t0 else 0.0)
        if abs(y - line) > worst:
            worst, worst_i = abs(y - line), i
    if worst <= tolerance:
        return [points[0], points[-1]]
    left = _rdp(points[:worst_i + 1], tolerance)
    return left[:-1] + _rdp(points[worst_i:], tolerance)

def _two_sided_bend_path(events, start, end, base, bend_range_semitones, duration,
                          start_value=None, require_two_sided=True):
    """Percorso a tappe [(frazione, scarto in semitoni interi), ...] del
    wheel durante la nota, se ha escursioni significative da ENTRAMBI i lati
    della nota scritta (es. sale di un tono e poi scende sotto: tipico dello
    slide/bottleneck), altrimenti None. Il modello a un solo picco terrebbe
    solo l'escursione piu' grande ignorando l'altra. Il percorso e' la curva
    del wheel semplificata (RDP) e arrotondata ai semitoni, coi tratti fermi
    conservati come tappe consecutive alla stessa altezza."""
    if duration <= 0:
        return None
    if start_value is None:
        start_value = base
    points = [(0.0, (start_value - base) / 8192.0 * bend_range_semitones)]
    end_seen = False
    for tick, value in events:
        if tick <= start:
            continue
        if tick > end:
            break
        if tick == end:
            if end_seen:
                continue
            end_seen = True
        points.append(((tick - start) / duration, (value - base) / 8192.0 * bend_range_semitones))
    if len(points) < 3:
        return None
    offsets = [o for _, o in points]
    if require_two_sided and not (round(max(offsets)) >= 1 and round(min(offsets)) <= -1):
        return None
    if any(abs(round(o)) > MAX_IMPORTED_BEND_SEMITONES for o in offsets):
        return None
    if points[-1][0] < 1.0:
        points.append((1.0, points[-1][1]))
    path = [(t, round(o)) for t, o in _rdp(points, BEND_PATH_TOLERANCE_SEMITONES)]
    # una tappa in mezzo a due alla stessa altezza e' ridondante; l'ultima
    # alla stessa altezza della precedente e' gia' la tenuta finale
    slim = [path[0]]
    for i in range(1, len(path)):
        if i + 1 < len(path) and path[i][1] == slim[-1][1] == path[i + 1][1]:
            continue
        slim.append(path[i])
    if len(slim) > 1 and slim[-1][1] == slim[-2][1]:
        slim.pop()
    return slim if len(slim) >= 3 else None

def _detect_scoop(events, start, end, note, value_at_start, bend_range_semitones, min_peak):
    """Vedi il commento nel chiamante. Ritorna (peak_fraction, [nota], nota
    di partenza) se la nota e' un pre-bend/scoop che rientra sul centro
    entro la fine, altrimenti None (bend normale o offset statico)."""
    if abs(value_at_start) < min_peak:
        return None
    start_semitones = round(value_at_start / 8192.0 * bend_range_semitones)
    if start_semitones == 0 or abs(start_semitones) > MAX_IMPORTED_BEND_SEMITONES:
        return None

    inside = []
    end_tick_seen = False
    for tick, pitch_value in events:
        if tick <= start:
            continue
        if tick > end:
            break
        if tick == end:
            if end_tick_seen:  # solo il primo evento allo stesso tick della fine (vedi sotto)
                continue
            end_tick_seen = True
        inside.append((tick, pitch_value))
    if not inside or abs(inside[-1][1]) >= min_peak:
        return None  # non rientra sul centro: offset statico o bend che parte da un valore fisso

    arrival_tick = next(t for t, v in inside if abs(v) < min_peak)
    duration = end - start
    fraction = min(max((arrival_tick - start) / duration, 0.0), 1.0) if duration > 0 else 1.0
    return (fraction, [note], note + start_semitones)

def _own_wheel_end(events, start, end, note_starts, lead, min_peak):
    """Ultimo tick fino a cui gli eventi di pitch wheel appartengono alla nota
    (start, end). Se subito dopo (o proprio alla fine) inizia un'altra nota, il
    wheel che si allontana dal centro nell'ultimo tratto e' il PRE-BEND di
    quella (la corda viene piegata prima di essere pizzicata), non un gesto di
    questa: lo si escluderebbe altrimenti come un bend fantasma in coda alla
    nota (visibile con bend ampi, es. un salto a -12 semitoni a fine nota).
    Un rilascio (movimento verso il centro) non e' un pre-bend e resta di
    questa nota."""
    i = bisect.bisect_right(note_starts, start)
    if i >= len(note_starts):
        return end
    next_start = note_starts[i]
    # E' un pre-bend della nota successiva solo se il wheel e' ANCORA fuori
    # centro al suo attacco: un movimento che torna a 0 proprio li' (un
    # fall-off di questa nota, che poi si azzera) e' un gesto di questa nota.
    value_at_next = 0
    for tick, value in events:
        if tick > next_start:
            break
        value_at_next = value
    if abs(value_at_next) < min_peak:
        return end
    # Finestra: gli ultimi 'lead' tick prima della fine di questa nota, o
    # dell'attacco successivo se cade prima (nota successiva sovrapposta).
    window_start = max(start + 1, min(next_start, end) - lead)
    previous_value = 0
    for tick, value in events:
        if tick >= window_start:
            break
        previous_value = value
    for tick, value in events:
        if tick < window_start:
            continue
        if tick > min(end, next_start):
            break
        if abs(value) >= min_peak and abs(value) > abs(previous_value):
            # Allo stesso tick della fine, gli eventi (il reset a 0 di QUESTA
            # nota, poi il pre-bend della successiva) li ordina gia' la logica
            # del chiamante, che ne tiene solo il primo.
            return end if tick >= end else tick - 1
        previous_value = value
    return end

def _collect_pitch_bend_targets(channel: "ChannelData", pitchwheel_events: List[tuple],
                                 bend_range_semitones: float, ticks_per_beat: int = 480,
                                 min_bend_semitones: Optional[float] = None):
    """Riempie channel.bends individuando, per ogni nota, il pitch bend di
    picco attivo durante la sua durata RISPETTO al valore che il pitch wheel
    aveva gia' all'inizio della nota (non rispetto al centro/0 assoluto): un
    canale con un offset statico impostato una volta sola (es. un trasporto
    fine di tutto il canale, mai un bending) resterebbe altrimenti "sempre
    piegato" per ogni singola nota, dato che il pitch wheel non torna mai a
    0. Il valore di riferimento e' quello dell'ULTIMO evento con tick <=
    l'inizio della nota (incluso un evento esattamente coincidente, es. il
    reset a 0 di un bending della nota precedente che finisce esattamente
    dove inizia questa): usare invece un confronto "prima dell'inizio" in
    senso stretto lascerebbe come riferimento un valore ormai superato,
    facendo risultare un bending della nota precedente come se appartenesse
    (con verso capovolto) a questa, come succede con note consecutive legate.

    E' cosi' che un bending chitarristico "in the wild" (bend-and-hold, o
    bend-and-release) viene tipicamente codificato in MIDI - note_on
    all'altezza di partenza, una rampa di eventi pitchwheel, poi note_off.
    channel.bends[(start, note)] e' una coppia (peak_fraction, waypoints) - o una
    terna (peak_fraction, waypoints, nota_di_partenza) per un pre-bend/scoop,
    vedi _detect_scoop:
    - waypoints e' una LISTA di tappe (mai vuota): una sola per un
      bend-and-hold (il picco resta fino alla fine), due per un
      bend-and-release (picco, poi il valore a cui il pitch wheel e'
      rientrato entro la fine della nota, se e' rientrato in modo
      significativo verso un semitono diverso - vedi end_delta sotto) -
      riusa cosi' lo slide a catena di core.notation (c*4>d*4>c*4) per
      rappresentare fedelmente anche il rilascio, non solo la salita.
    - peak_fraction e' la posizione temporale del picco all'interno della
      nota (0.0 = subito all'inizio, 1.0 = proprio alla fine), usata da
      channel_to_tokens per assegnare durate per singola tappa allo slide
      (vedi core.notation, sintassi 'NcNota') invece di assumere sempre una
      divisione a meta' fra rampa e mantenimento: un bend rapido seguito da
      un lungo mantenimento (peak_fraction basso) suona molto diverso da un
      bend lento che raggiunge il picco solo alla fine (peak_fraction alto),
      e il MIDI sorgente lo sa gia' con precisione.
    Un pre-bend/scoop (wheel gia' fuori centro prima dell'attacco, che
    rientra sul centro durante la nota) e' riconosciuto a parte da
    _detect_scoop e importato come slide dall'altezza di partenza reale.
    Resta non distinguibile un pre-bend che NON rientra sul centro (offset
    fisso a inizio nota): e' trattato come offset statico del canale.

    Un picco che arrotonda a 0 semitoni (vibrato/imprecisioni di
    registrazione), troppo piccolo rispetto al fondo scala del pitch wheel
    (MIN_BEND_FRACTION_OF_RANGE: automazione continua di espressione/
    umanizzazione, non un bending deliberato) o implausibilmente ampio
    (sensibilita' RPN non riconosciuta) NON viene registrato: la nota resta
    un token normale.

    min_bend_semitones (opzionale) puo' solo ABBASSARE la soglia della
    frazione di fondo scala: con una sensibilita' RPN ampia (12 semitoni)
    la frazione di default equivale a 1,2 semitoni e scarta i bend brevi di
    un semitono tipici della slide guitar. Con una sensibilita' stretta
    (es. 2) la frazione di default e' gia' piu' bassa della soglia richiesta
    e non cambia nulla: li' decide solo l'arrotondamento al semitono."""
    if not pitchwheel_events:
        return
    events = sorted(pitchwheel_events)
    min_fraction = MIN_BEND_FRACTION_OF_RANGE
    if min_bend_semitones is not None and bend_range_semitones > 0:
        min_fraction = min(min_fraction, min_bend_semitones / bend_range_semitones)
    min_peak = min_fraction * 8192
    note_starts = sorted({n[0] for n in channel.notes})
    lead = max(1, round(NEXT_PREBEND_LEAD_BEATS * ticks_per_beat))
    for start, real_end, note, _vel in channel.notes:
        end = _own_wheel_end(events, start, real_end, note_starts, lead, min_peak)
        value_at_start = 0
        start_idx = -1
        for i, (tick, pitch_value) in enumerate(events):
            if tick > start:
                break
            start_idx = i
            # Un evento ESATTAMENTE allo start della nota (tipicamente il
            # reset a 0 di un bending della nota precedente, o il valore
            # "a riposo" gia' in corso) ne stabilisce il valore di riferimento:
            # senza includerlo qui, uno start coincidente con un reset
            # lascerebbe come riferimento un valore ormai superato, di un
            # bending precedente non collegato a questa nota (note
            # consecutive legate).
            value_at_start = pitch_value
        # Coda di rilascio della nota precedente: il valore d'attacco e' un
        # punto di una discesa verso il centro ancora in corso (l'evento
        # precedente e' piu' lontano dal centro, con lo stesso segno), non un
        # pre-bend voluto (che invece sarebbe un salto FUORI dal centro).
        # Il riferimento e' allora il centro: usare quel valore come
        # riferimento leggerebbe la discesa fino a 0 come un bend di segno
        # opposto sotto la nota scritta (Layla: f -> d#, stonato).
        if start_idx >= 1 and abs(value_at_start) >= min_peak:
            previous_value = events[start_idx - 1][1]
            if previous_value * value_at_start > 0 and abs(previous_value) > abs(value_at_start):
                value_at_start = 0
        # Un valore d'attacco sotto la soglia non e' un offset del canale ma il
        # primo campione di un bend che parte proprio con la nota: usarlo come
        # riferimento sposterebbe tutto il bend di quello scarto, e il ritorno
        # al centro arrotonderebbe a un semitono sopra la nota scritta (Layla,
        # bend sul la a fine assolo: wheel a -640 all'attacco, la -> la#).
        if abs(value_at_start) < min_peak:
            value_at_start = 0
        # Pre-bend/scoop: il pitch wheel e' gia' lontano dal centro PRIMA
        # dell'attacco e rientra sul centro durante la nota (la corda viene
        # pizzicata gia' piegata e rilascia, o una nota "scooped" dal basso).
        # L'altezza scritta nel MIDI e' quella d'arrivo (wheel a 0): il suono
        # parte da nota + offset_iniziale e sale/scende alla nota. Va
        # importato cosi', come slide dall'altezza di partenza reale verso la
        # nota, NON come bend relativo al valore d'attacco: quello lo
        # leggerebbe come un'escursione di segno opposto, oltre la nota
        # scritta (stonatura: es. una nota re con wheel da -1 semitono a 0
        # diventava re>re# invece di do#>re).
        scoop = _detect_scoop(events, start, end, note, value_at_start,
                              bend_range_semitones, min_peak)
        if scoop is not None:
            channel.bends[(start, note)] = scoop
            # Se dentro la nota il wheel va PIU' LONTANO dal centro di dove
            # era partito (dive-and-recover: parte a -4, si tuffa a -12, poi
            # risale), lo scoop semplice ignorerebbe il tuffo: percorso a
            # tappe generico, con il centro come riferimento.
            deepest = max((abs(v) for t, v in events if start < t <= end), default=0)
            overshoot_needed = max(min_peak, BEND_OVERSHOOT_SEMITONES / bend_range_semitones * 8192)
            if deepest > abs(value_at_start) + overshoot_needed:
                path = _two_sided_bend_path(events, start, end, 0, bend_range_semitones,
                                            real_end - start, start_value=value_at_start,
                                            require_two_sided=False)
                if path is not None:
                    channel.bend_paths[(start, note)] = [(t, note + off) for t, off in path]
            continue

        peak_delta = 0
        peak_tick = start
        end_delta = 0
        end_tick_seen = False
        for tick, pitch_value in events:
            if tick > end:
                break
            if tick > start:
                if tick == end:
                    # Come per lo start, un evento esattamente alla fine (in
                    # genere il reset di QUESTA nota prima del suo note_off)
                    # va incluso - ma solo il PRIMO: se una nota successiva
                    # inizia esattamente allo stesso tick con un proprio
                    # gesto (es. un pre-bend), i suoi eventi allo stesso
                    # tick vengono dopo nello stream e appartengono a lei,
                    # non al rilascio di questa nota (es. due note legate
                    # allo stesso tick, la seconda con un pre-bend).
                    if end_tick_seen:
                        continue
                    end_tick_seen = True
                delta = pitch_value - value_at_start
                if abs(delta) > abs(peak_delta):
                    peak_delta = delta
                    peak_tick = tick
                end_delta = delta  # l'ultimo evento incontrato e' quello piu' vicino alla fine
        if abs(peak_delta) < min_peak:
            continue
        semitone_peak = round(peak_delta / 8192.0 * bend_range_semitones)
        if semitone_peak == 0 or abs(semitone_peak) > MAX_IMPORTED_BEND_SEMITONES:
            continue
        waypoints = [note + semitone_peak]
        # Bend-and-release: se il pitch wheel e' rientrato in modo
        # significativo verso un semitono diverso entro la fine della nota
        # (non solo tenuto sul picco), lo slide importato ha una seconda
        # tappa - vedi core.notation per la sintassi a catena (c*4>d*4>c*4).
        semitone_end = round(end_delta / 8192.0 * bend_range_semitones)
        if (semitone_end != semitone_peak and abs(end_delta - peak_delta) >= min_peak
                and abs(semitone_end) <= MAX_IMPORTED_BEND_SEMITONES):
            waypoints.append(note + semitone_end)
        note_duration = real_end - start
        peak_fraction = ((peak_tick - start) / note_duration) if note_duration > 0 else 1.0
        peak_fraction = min(max(peak_fraction, 0.0), 1.0)
        channel.bends[(start, note)] = (peak_fraction, waypoints)
        path = _two_sided_bend_path(events, start, end, value_at_start,
                                    bend_range_semitones, note_duration)
        if path is not None:
            channel.bend_paths[(start, note)] = [(t, note + off) for t, off in path]
            continue
        # Inizio del bend: un wheel che resta (quasi) fermo per un tratto
        # prima di muoversi (es. uno slide che parte a meta' nota) non e' una
        # rampa dall'attacco. Contano solo tratti fermi "provati" da almeno
        # due eventi intermedi e di almeno BEND_ONSET_MIN_FRACTION della nota:
        # un singolo salto isolato da un valore fermo e' ambiguo con una
        # rampa campionata a bassa risoluzione (resta rampa dall'attacco).
        for tick, pitch_value in events:
            if start < tick <= peak_tick and abs(pitch_value - value_at_start) > min_peak:
                onset_fraction = (tick - start) / note_duration if note_duration > 0 else 0.0
                seen = sum(1 for t, _ in events if start < t < tick)
                # ...oppure il movimento stesso e' una rampa campionata bene
                # (almeno 3 eventi dall'inizio al picco): non un salto isolato.
                ramp_events = sum(1 for t, _ in events if tick <= t <= peak_tick)
                if onset_fraction >= BEND_ONSET_MIN_FRACTION and (
                        seen >= 2 or (ramp_events >= 3 and onset_fraction >= BEND_LATE_ONSET_FRACTION)):
                    channel.bend_onset[(start, note)] = onset_fraction
                break
        if len(waypoints) == 2 and note_duration > 0:
            # Il wheel resta al valore dell'ultimo evento finche' non ne
            # arriva un altro: la tenuta sul picco finisce all'evento in cui
            # il valore se ne allontana (oltre la tolleranza del vibrato); il
            # rilascio finisce al primo evento successivo che e' gia' sul
            # valore finale (se non ci arriva, dura fino a fine nota).
            peak_value = value_at_start + peak_delta
            end_value = value_at_start + end_delta
            release_tick = None
            settle_tick = None
            for tick, pitch_value in events:
                if not (peak_tick < tick <= end):
                    continue
                if release_tick is None:
                    if abs(pitch_value - peak_value) > min_peak:
                        release_tick = tick
                    else:
                        continue
                if abs(pitch_value - end_value) <= min_peak:
                    settle_tick = tick
                    break
            if release_tick is not None:
                def frac(t):
                    return min(max((t - start) / note_duration, 0.0), 1.0)
                channel.bend_release[(start, note)] = (
                    frac(release_tick), frac(settle_tick) if settle_tick is not None else 1.0)
