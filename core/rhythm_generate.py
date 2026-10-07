"""
Generazione algoritmica (non basata su IA) di linee di basso e di batteria:
risultato istantaneo, riproducibile per seme e senza dipendenze pesanti (nessun
modello, nessun download, nessuna GPU/CPU intensiva).

Batteria: libreria di pattern per genere (rock, funk, four-on-the-floor,
reggae one-drop, punk, soul, bossa nova, rock'n'roll, shuffle, swing jazz),
ciascuno un giro in 4/4: di 16 sedicesimi, oppure di 12 terzine di ottavo
per shuffle e swing (ogni stile dichiara la sua griglia, vedi
DRUM_STYLES) - vocabolario
ritmico generico e non protetto da copyright (come una progressione di
accordi: la definizione astratta di un genere, non l'espressione originale
di un autore), non importato da nessuna libreria esterna.

Basso: segue gli accordi gia' scritti in un'altra traccia del progetto
(estratti con extract_chords_from_track, simboli o blocchi [...]), in piu'
stili: fondamentale, fondamentale/quinta, walking bass (con la terza e la
settima vere dell'accordo e una nota di avvicinamento cromatico
all'accordo successivo), pedale, due quarti, ottave, blues 1-3-5-6, ottavi,
reggae, bossa nova e shuffle. Ogni stile dichiara la sua griglia (quarti,
ottavi o terzine di ottavo, vedi BASS_PATTERNS).

Entrambi hanno un parametro di variabilita' (0 = sempre lo stesso risultato,
fino a 1) e un seme: a parita' di stile, variabilita' e seme il testo generato
e' identico (riproducibile), cambiando il seme cambia la variazione - note
fantasma, cassa extra, fill diversi, note di passaggio, pause e note tenute
del basso; vedi generate_drum_pattern/generate_bass_from_chords.

Entrambi supportano una "variazione ogni N battute" (fill di batteria /
trattamento alternativo del basso) per evitare il suono meccanico di un
giro ripetuto identico all'infinito - vedi fill_every/variation_every.

Metriche: ogni stile di batteria dichiara la sua (4/4 se non indicata; vedi
drum_styles_for_meter per 3/4, 6/8 e 12/8). Basso e accompagnamento seguono
gli accordi e ripetono il disegno dello stile su battute della durata
indicata (bar_beats), quindi funzionano con qualunque metrica: un disegno
pensato per 4/4 viene troncato alla battuta piu' corta; alcuni stili sono
pensati apposta per 3/4 e 6/8 (valzer, arpeggio in 6/8).
"""

import random
import re
from fractions import Fraction
from typing import Dict, List, NamedTuple, Optional, Tuple

from .chords import parse_chord_symbol, pc_to_letter, midi_note, recognize_chord, CHORD_QUALITIES, pitch_to_midi
from .instruments import PERCUSSION_MAP
from .notation import NotationError, Pattern, parse_track_text
from .model import Project
from . import user_styles
from .i18n import tr


class Variability(NamedTuple):
    """Quanto variare, per aspetto (ciascuno 0-1): 'rhythm' (giri e ritmi
    alternativi, fill, colpi o note che saltano, si allungano o si
    aggiungono, anticipi), 'notes' (note e armonia: varianti, note di
    passaggio, salti d'ottava, note fantasma della batteria, colori e
    sostituzioni degli accordi) e 'dynamics' (velocity). I generatori
    accettano anche un solo numero, che vale per tutti e tre."""
    rhythm: float = 0.0
    notes: float = 0.0
    dynamics: float = 0.0

    def any(self) -> bool:
        return max(self) > 0


def _variability(value) -> Variability:
    """Variability con ogni aspetto limitato a 0-1, da un numero, una
    tupla/Variability o un dizionario {'rhythm', 'notes', 'dynamics'}."""
    if isinstance(value, dict):
        value = Variability(**value)
    if isinstance(value, (int, float)):
        value = (value, value, value)
    return Variability(*(max(0.0, min(1.0, float(v))) for v in value))

SLOTS_PER_BAR = 16  # sedicesimi per battuta in 4/4 (default di _pattern; le altre metriche passano i loro slot)
TRIPLET_SLOTS_PER_BAR = 12  # terzine di ottavo (8T:) per battuta in 4/4: 3 per beat, per shuffle/swing
DEFAULT_GRID = "16:"
TRIPLET_GRID = "8T:"


def tracks_duration_beats(project: Project, exclude_track_name: Optional[str] = None,
                           midi_dir: Optional[str] = None) -> float:
    """Durata (in beat) della piu' lunga tra le tracce del progetto gia'
    scritte, escludendo (se dato) 'exclude_track_name' - tipicamente la
    traccia di destinazione su cui si sta per generare batteria/basso, la cui
    durata attuale non e' un riferimento utile. Usata dai dialoghi di
    generazione per far coprire di default al risultato l'intera estensione
    della musica gia' presente nelle altre tracce, invece di fermarsi prima."""
    max_beats = 0.0
    for track in project.tracks:
        if track.name == exclude_track_name:
            continue
        events = track.parsed_events(project.patterns, midi_dir=midi_dir, meter=project.meter())
        if events:
            max_beats = max(max_beats, max(e.start + e.duration for e in events))
    return max_beats


# ---------------------------------------------------------------------------
# Batteria
# ---------------------------------------------------------------------------

# Ogni pattern e' una lista di SLOTS_PER_BAR elementi: None (pausa) oppure una
# lista di (nome_percussione, velocity) per gli hit simultanei in quello slot.
# 'fill' e' un pattern alternativo (stessa lunghezza) sostituito al posto di
# 'main' ogni fill_every battute (vedi generate_drum_pattern), con un crash
# aggiunto in automatico all'inizio della battuta successiva (rientro tipico
# dopo un fill).
# NB: gli strumenti che suonano nello stesso slot ([kick hihat]) condividono
# la velocity del primo (vedi _slots_to_tokens): nei nuovi stili i suoni
# simultanei hanno la stessa velocity, cosi' il valore scritto e' quello che
# si sente.
def _pattern(hits: Dict[int, List[Tuple[str, int]]],
             slots: int = SLOTS_PER_BAR) -> List[Optional[list]]:
    return [hits.get(i) for i in range(slots)]


def _triplet_pattern(hits: Dict[int, List[Tuple[str, int]]],
                     slots: int = TRIPLET_SLOTS_PER_BAR) -> List[Optional[list]]:
    """Come _pattern, su una griglia di terzine di ottavo (12 slot per
    battuta di 4/4, 3 per beat: 0 = battere, 1 e 2 = le altre due terzine)."""
    return _pattern(hits, slots)


def meter_beats(meter: str) -> float:
    """Durata in beat (quarti) di una battuta nella metrica 'N/D' (es. 3/4 ->
    3, 6/8 -> 3, 12/8 -> 6). ValueError se la metrica non e' valida."""
    try:
        num, den = (int(x) for x in meter.split("/"))
    except (ValueError, AttributeError):
        raise ValueError(tr("Metrica non valida: '{meter}'", meter=meter))
    if num <= 0 or den <= 0:
        raise ValueError(tr("Metrica non valida: '{meter}'", meter=meter))
    return num * 4.0 / den


def _normalize_meter(meter: str) -> str:
    return meter.replace(" ", "")


DRUM_STYLES: Dict[str, Dict[str, list]] = {
    "rock": {
        "main": _pattern({
            0: [("kick", 105)], 2: [("hihat", 70)], 4: [("snare", 100), ("hihat", 70)],
            6: [("hihat", 70)], 8: [("kick", 105)], 10: [("hihat", 70)],
            12: [("snare", 100), ("hihat", 70)], 14: [("hihat", 70)],
        }),
        "fill": _pattern({
            0: [("kick", 105)], 4: [("snare", 100)], 8: [("kick", 105)],
            10: [("tom1", 95)], 12: [("tom1", 95)], 13: [("tom2", 95)],
            14: [("tom2", 100)], 15: [("snare", 105)],
        }),
    },
    "funk": {
        "main": _pattern({
            0: [("kick", 105), ("hihat", 80)], 2: [("hihat", 65)],
            3: [("kick", 90)], 4: [("snare", 100), ("hihat", 80)],
            6: [("kick", 85), ("hihat", 65)], 7: [("hihat", 60)],
            8: [("hihat", 80)], 10: [("kick", 90), ("hihat", 65)],
            12: [("snare", 100), ("hihat", 80)], 14: [("snare", 55), ("hihat", 65)],
            15: [("hihat", 60)],
        }),
        "fill": _pattern({
            0: [("kick", 105), ("hihat", 80)], 4: [("snare", 100)],
            8: [("tom1", 90)], 9: [("tom1", 90)], 10: [("tom1", 95)],
            11: [("tom2", 90)], 12: [("tom2", 95)], 13: [("tom2", 95)],
            14: [("snare", 100)], 15: [("snare", 105)],
        }),
    },
    "disco": {
        "main": _pattern({
            0: [("kick", 105)], 2: [("hihat_open", 75)], 4: [("snare", 100)],
            6: [("hihat_open", 75)], 8: [("kick", 105)], 10: [("hihat_open", 75)],
            12: [("snare", 100)], 14: [("hihat_open", 75)],
        }),
        "fill": _pattern({
            0: [("kick", 105)], 4: [("snare", 100)], 8: [("kick", 105)],
            9: [("tom1", 90)], 10: [("tom1", 95)], 11: [("tom1", 95)],
            12: [("tom2", 95)], 13: [("tom2", 95)], 14: [("snare", 100)], 15: [("snare", 105)],
        }),
    },
    "reggae": {
        # "One drop": niente cassa/rullante sul battere 1, insieme solo sul 3.
        "main": _pattern({
            0: [("hihat", 65)], 2: [("hihat", 65)], 4: [("hihat", 65)],
            6: [("hihat", 65)], 8: [("kick", 105), ("snare", 100)], 10: [("hihat", 65)],
            12: [("hihat", 65)], 14: [("hihat", 65)],
        }),
        "fill": _pattern({
            2: [("hihat", 65)], 6: [("hihat", 65)], 8: [("kick", 105), ("snare", 100)],
            10: [("tom1", 90)], 12: [("tom1", 95)], 13: [("tom2", 90)],
            14: [("tom2", 95)], 15: [("snare", 100)],
        }),
    },
    "punk": {
        # Ottavi veloci e diritti, cassa sul 1 e sul 3 con una spinta prima del 4.
        "main": _pattern({
            0: [("kick", 100), ("hihat", 100)], 2: [("hihat", 85)],
            4: [("snare", 105), ("hihat", 105)], 6: [("hihat", 85)],
            8: [("kick", 100), ("hihat", 100)], 10: [("kick", 95), ("hihat", 95)],
            12: [("snare", 105), ("hihat", 105)], 14: [("hihat", 85)],
        }),
        "fill": _pattern({
            0: [("kick", 110)], 4: [("snare", 110)], 8: [("kick", 110)],
            10: [("snare", 105)], 12: [("snare", 110)], 13: [("snare", 105)],
            14: [("snare", 110)], 15: [("snare", 115)],
        }),
    },
    "soul": {
        # Groove alla Motown: rullante sul 2 e sul 4 con tamburello sugli ottavi.
        "main": _pattern({
            0: [("kick", 90), ("tambourine", 90)], 2: [("tambourine", 60)],
            4: [("snare", 100), ("tambourine", 100)], 6: [("kick", 80), ("tambourine", 80)],
            8: [("kick", 90), ("tambourine", 90)], 10: [("tambourine", 60)],
            12: [("snare", 100), ("tambourine", 100)], 14: [("tambourine", 60)],
        }),
        "fill": _pattern({
            0: [("kick", 100)], 4: [("snare", 100)], 8: [("kick", 95)],
            10: [("snare", 80)], 11: [("snare", 85)], 12: [("tom1", 95)],
            13: [("tom1", 95)], 14: [("tom2", 100)], 15: [("snare", 105)],
        }),
    },
    "bossa": {
        # Bossa nova: cassa in "dondolo" (1, e del 2, 3, e del 4), clave di
        # rullante sul bordo (rimshot) e charleston leggero sugli ottavi.
        "main": _pattern({
            0: [("kick", 70), ("rimshot", 70), ("hihat", 70)], 2: [("hihat", 50)],
            3: [("rimshot", 70)], 4: [("hihat", 55)],
            6: [("kick", 65), ("rimshot", 65), ("hihat", 65)],
            8: [("kick", 75), ("hihat", 75)], 10: [("rimshot", 60), ("hihat", 60)],
            12: [("rimshot", 60), ("hihat", 60)], 14: [("kick", 65), ("hihat", 65)],
        }),
        "fill": _pattern({
            0: [("kick", 75), ("rimshot", 75)], 3: [("rimshot", 70)], 6: [("kick", 70), ("rimshot", 70)],
            8: [("tom1", 75)], 10: [("tom1", 80)], 12: [("tom2", 80)],
            14: [("tom2", 85)], 15: [("rimshot", 85)],
        }),
    },
    "rocknroll": {
        # Rock'n'roll anni '50: ottavi sul ride, cassa sul 1 e sul 3, rullante
        # sul 2 e sul 4 con una spinta di cassa prima del 3.
        "main": _pattern({
            0: [("kick", 90), ("ride", 90)], 2: [("ride", 65)],
            4: [("snare", 100), ("ride", 100)], 6: [("ride", 65)],
            8: [("kick", 90), ("ride", 90)], 10: [("kick", 80), ("ride", 80)],
            12: [("snare", 100), ("ride", 100)], 14: [("ride", 65)],
        }),
        "fill": _pattern({
            0: [("kick", 100)], 4: [("snare", 105)], 8: [("kick", 100)],
            10: [("snare", 95)], 12: [("tom1", 100)], 13: [("tom1", 95)],
            14: [("tom2", 100)], 15: [("snare", 110)],
        }),
    },
    "shuffle": {
        # Shuffle blues: terzine di ottavo, charleston sulla prima e sulla
        # terza terzina di ogni beat, cassa sul 1 e sul 3, rullante sul 2 e 4.
        "grid": TRIPLET_GRID,
        "main": _triplet_pattern({
            0: [("kick", 95), ("hihat", 95)], 2: [("hihat", 60)],
            3: [("snare", 100), ("hihat", 100)], 5: [("hihat", 60)],
            6: [("kick", 90), ("hihat", 90)], 8: [("hihat", 60)],
            9: [("snare", 100), ("hihat", 100)], 11: [("hihat", 60)],
        }),
        "fill": _triplet_pattern({
            0: [("kick", 105)], 3: [("snare", 100)], 6: [("kick", 100)],
            8: [("tom1", 90)], 9: [("tom1", 95)], 10: [("tom2", 95)],
            11: [("snare", 105)],
        }),
    },
    "swing": {
        # Swing jazz: ride "spang-a-lang" (1, 2, la del 2, 3, 4, la del 4),
        # charleston col pedale sul 2 e sul 4 e un rullante di commento a
        # volume basso.
        "grid": TRIPLET_GRID,
        "main": _triplet_pattern({
            0: [("ride", 80)], 3: [("ride", 70), ("hihat_pedal", 70)],
            5: [("ride", 55)], 6: [("ride", 75)],
            8: [("snare", 45)], 9: [("ride", 70), ("hihat_pedal", 70)],
            11: [("ride", 55)],
        }),
        "fill": _triplet_pattern({
            0: [("ride", 80)], 3: [("hihat_pedal", 65)], 6: [("snare", 70)],
            8: [("snare", 80)], 9: [("tom1", 85)], 10: [("tom2", 90)], 11: [("snare", 95)],
        }),
    },

    # ---- 3/4 -------------------------------------------------------------
    "waltz": {
        # Valzer: cassa sul 1, rullante leggero e charleston sul 2 e sul 3.
        "meter": "3/4",
        "main": _pattern({
            0: [("kick", 100), ("hihat", 80)], 2: [("hihat", 50)],
            4: [("snare", 70), ("hihat", 75)], 6: [("hihat", 50)],
            8: [("snare", 70), ("hihat", 75)], 10: [("hihat", 50)],
        }, 12),
        "fill": _pattern({
            0: [("kick", 100)], 4: [("snare", 90)], 6: [("tom1", 90)],
            8: [("tom1", 95)], 9: [("tom2", 95)], 10: [("tom2", 100)], 11: [("snare", 105)],
        }, 12),
    },
    "jazz_waltz": {
        # Valzer jazz: ride in terzine, charleston col pedale sul 2 e sul 3.
        "meter": "3/4",
        "grid": TRIPLET_GRID,
        "main": _triplet_pattern({
            0: [("ride", 80), ("kick", 55)], 3: [("ride", 70), ("hihat_pedal", 65)],
            5: [("ride", 55)], 6: [("ride", 70), ("hihat_pedal", 65)], 8: [("ride", 55)],
        }, 9),
        "fill": _triplet_pattern({
            0: [("ride", 80)], 3: [("snare", 70)], 5: [("snare", 75)],
            6: [("tom1", 85)], 7: [("tom2", 90)], 8: [("snare", 95)],
        }, 9),
    },

    # ---- 6/8 (due pulsazioni di tre ottavi) -----------------------------
    "ballad_68": {
        # Ballata in 6/8: charleston su ogni ottavo, cassa sul 1, rullante sul 4.
        "meter": "6/8", "grid": "8:", "pulse": 3,
        "main": _pattern({
            0: [("kick", 100), ("hihat", 80)], 1: [("hihat", 55)], 2: [("hihat", 55)],
            3: [("snare", 95), ("hihat", 75)], 4: [("hihat", 55)], 5: [("hihat", 55)],
        }, 6),
        "fill": _pattern({
            0: [("kick", 100)], 1: [("snare", 80)], 2: [("snare", 85)],
            3: [("tom1", 95)], 4: [("tom2", 95)], 5: [("snare", 105)],
        }, 6),
    },
    "afro_68": {
        # 6/8 afro-cubano: campanaccio col classico disegno in 6/8, cassa sulle
        # due pulsazioni, conga sulle terze note di ogni gruppo.
        "meter": "6/8", "grid": "8:", "pulse": 3,
        "main": _pattern({
            0: [("kick", 95), ("cowbell", 90)], 2: [("cowbell", 75), ("conga_open", 70)],
            3: [("kick", 85), ("cowbell", 80)], 4: [("cowbell", 75)], 5: [("conga_open", 75)],
        }, 6),
        "fill": _pattern({
            0: [("kick", 100), ("cowbell", 90)], 1: [("conga_open", 80)], 2: [("conga_mute", 80)],
            3: [("tom1", 95)], 4: [("tom2", 95)], 5: [("snare", 105)],
        }, 6),
    },

    # ---- 12/8 (quattro pulsazioni di tre ottavi) -------------------------
    "blues_128": {
        # Slow blues in 12/8: charleston sugli ottavi, cassa sul 1 e sul 3,
        # rullante sul 2 e sul 4 (in pulsazioni).
        "meter": "12/8", "grid": "8:", "pulse": 3,
        "main": _pattern({
            0: [("kick", 100), ("hihat", 85)], 1: [("hihat", 55)], 2: [("hihat", 60)],
            3: [("snare", 100), ("hihat", 80)], 4: [("hihat", 55)], 5: [("hihat", 60)],
            6: [("kick", 95), ("hihat", 85)], 7: [("hihat", 55)], 8: [("kick", 70), ("hihat", 60)],
            9: [("snare", 100), ("hihat", 80)], 10: [("hihat", 55)], 11: [("hihat", 60)],
        }, 12),
        "fill": _pattern({
            0: [("kick", 100), ("hihat", 85)], 3: [("snare", 100)], 6: [("kick", 95)],
            7: [("snare", 80)], 8: [("snare", 85)], 9: [("tom1", 95)],
            10: [("tom2", 95)], 11: [("snare", 105)],
        }, 12),
    },
    "slow_rock_128": {
        # Slow rock anni '50 in 12/8: terzine sul ride, cassa sul 1 e sul 3,
        # rullante secco sul 2 e sul 4.
        "meter": "12/8", "grid": "8:", "pulse": 3,
        "main": _pattern({
            0: [("kick", 95), ("ride", 85)], 1: [("ride", 60)], 2: [("ride", 60)],
            3: [("snare", 105), ("ride", 80)], 4: [("ride", 60)], 5: [("ride", 60)],
            6: [("kick", 95), ("ride", 85)], 7: [("ride", 60)], 8: [("ride", 60)],
            9: [("snare", 105), ("ride", 80)], 10: [("ride", 60)], 11: [("ride", 60)],
        }, 12),
        "fill": _pattern({
            0: [("kick", 100), ("ride", 85)], 3: [("snare", 105)], 6: [("kick", 95)],
            8: [("tom1", 90)], 9: [("tom1", 95)], 10: [("tom2", 95)], 11: [("snare", 110)],
        }, 12),
    },
}


# ---- Stili aggiunti (4/4, 5/4, 7/8) -------------------------------------
# Tenuti in un blocco a parte per non spostare quelli storici: stesso
# formato di DRUM_STYLES.
DRUM_STYLES.update({
    "hiphop": {
        # Boom-bap: cassa sul 1, sul "e" del 2 e sul 3 in levare, rullante
        # pieno sul 2 e sul 4, charleston sugli ottavi.
        "main": _pattern({
            0: [("kick", 105), ("hihat", 75)], 2: [("hihat", 60)], 4: [("snare", 105), ("hihat", 75)],
            6: [("hihat", 60)], 7: [("kick", 85)], 8: [("hihat", 75)], 10: [("kick", 95), ("hihat", 60)],
            12: [("snare", 105), ("hihat", 75)], 14: [("hihat", 60)],
        }),
        "fill": _pattern({
            0: [("kick", 105)], 4: [("snare", 105)], 8: [("kick", 100)], 10: [("snare", 90)],
            12: [("snare", 95)], 13: [("snare", 100)], 14: [("tom1", 100)], 15: [("tom2", 105)],
        }),
    },
    "halftime": {
        # Half-time: rullante solo sul 3 (la battuta "respira" il doppio).
        "main": _pattern({
            0: [("kick", 105), ("hihat", 75)], 2: [("hihat", 60)], 4: [("hihat", 70)], 6: [("hihat", 60)],
            7: [("kick", 80)], 8: [("snare", 110), ("hihat", 75)], 10: [("hihat", 60)],
            11: [("kick", 85)], 12: [("hihat", 70)], 14: [("hihat", 60)],
        }),
        "fill": _pattern({
            0: [("kick", 105)], 8: [("snare", 110)], 12: [("tom1", 95)], 13: [("tom1", 95)],
            14: [("tom2", 100)], 15: [("floor", 105)],
        }),
    },
    "metal": {
        # Doppia cassa a sedicesimi, ride sui quarti, rullante sul 2 e sul 4.
        "main": _pattern({i: ([("kick", 95)] + ([("ride", 90)] if i % 4 == 0 else [])
                              + ([("snare", 115)] if i in (4, 12) else [])) for i in range(16)}),
        "fill": _pattern({
            0: [("kick", 105)], 2: [("kick", 100)], 4: [("snare", 115)], 6: [("kick", 100)],
            8: [("tom1", 105)], 9: [("tom1", 105)], 10: [("tom2", 105)], 11: [("tom2", 105)],
            12: [("floor", 110)], 13: [("floor", 110)], 14: [("snare", 115)], 15: [("snare", 120)],
        }),
    },
    "country": {
        # "Train beat": rullante su ogni sedicesimo (piano) con gli accenti sul
        # 2 e sul 4, cassa sul 1 e sul 3.
        "main": _pattern({i: ([("kick", 95)] if i in (0, 8) else [])
                         + [("snare", 100 if i in (4, 12) else 42)] for i in range(16)}),
        "fill": _pattern({
            0: [("kick", 100), ("snare", 45)], 2: [("snare", 45)], 4: [("snare", 100)], 6: [("snare", 45)],
            8: [("snare", 70)], 9: [("snare", 75)], 10: [("snare", 80)], 11: [("snare", 85)],
            12: [("snare", 95)], 13: [("snare", 100)], 14: [("tom1", 105)], 15: [("tom2", 110)],
        }),
    },
    "samba": {
        # Samba: sedicesimi di charleston, surdo (cassa) che accenta la seconda
        # meta' di ogni mezza battuta, tamborim sul bordo del rullante.
        "main": _pattern({
            0: [("kick", 70), ("hihat", 70)], 1: [("hihat", 45)], 2: [("hihat", 55)],
            3: [("kick", 60), ("hihat", 45)], 4: [("kick", 100), ("hihat", 70)], 5: [("hihat", 45)],
            6: [("rimshot", 80), ("hihat", 55)], 7: [("hihat", 45)], 8: [("kick", 70), ("hihat", 70)],
            9: [("hihat", 45)], 10: [("rimshot", 80), ("hihat", 55)], 11: [("kick", 60), ("hihat", 45)],
            12: [("kick", 100), ("hihat", 70)], 13: [("hihat", 45)], 14: [("rimshot", 85), ("hihat", 55)],
            15: [("hihat", 45)],
        }),
        "fill": _pattern({
            0: [("kick", 80)], 4: [("kick", 100)], 8: [("rimshot", 85)], 9: [("rimshot", 80)],
            10: [("tom1", 90)], 11: [("tom1", 90)], 12: [("tom2", 95)], 13: [("tom2", 95)],
            14: [("floor", 100)], 15: [("floor", 105)],
        }),
    },
    "cha_cha": {
        # Cha-cha-cha: campanaccio sui quarti, cassa sul 1 e sul 3, i due
        # colpi di timbales del "cha-cha" sul 4 e sul "e" del 4.
        "main": _pattern({
            0: [("kick", 95), ("cowbell", 90)], 2: [("cabasa", 60)], 4: [("cowbell", 75)],
            6: [("conga_mute", 70), ("cabasa", 60)], 8: [("kick", 90), ("cowbell", 85)], 10: [("cabasa", 60)],
            12: [("cowbell", 75), ("timbale_hi", 85)], 14: [("timbale_hi", 90), ("conga_open", 80)],
        }),
        "fill": _pattern({
            0: [("kick", 95), ("cowbell", 90)], 4: [("cowbell", 75)], 8: [("timbale_hi", 90)],
            10: [("timbale_hi", 90)], 12: [("timbale_low", 95)], 13: [("timbale_low", 95)],
            14: [("timbale_hi", 100)], 15: [("timbale_low", 105)],
        }),
    },
    "march": {
        # Marcia: grancassa sul 1 e sul 3, rullante con i classici "ta-ta-ta".
        "main": _pattern({
            0: [("kick", 100), ("snare", 100)], 4: [("snare", 85)], 6: [("snare", 70)], 7: [("snare", 75)],
            8: [("kick", 95), ("snare", 100)], 12: [("snare", 85)], 14: [("snare", 70)], 15: [("snare", 75)],
        }),
        "fill": _pattern({
            0: [("kick", 100), ("snare", 100)], 4: [("snare", 85)], **{i: [("snare", 60 + 6 * (i - 8))]
                                                                       for i in range(8, 16)},
        }),
    },

    # ---- 5/4 (cinque quarti) ------------------------------------------------
    "rock_54": {
        # 5/4 diviso 3+2: cassa sul 1 e sul 4, rullante sul 3 e sul 5.
        "meter": "5/4",
        "main": _pattern({
            0: [("kick", 100), ("hihat", 80)], 2: [("hihat", 60)], 4: [("hihat", 70)], 6: [("kick", 80), ("hihat", 60)],
            8: [("snare", 100), ("hihat", 80)], 10: [("hihat", 60)], 12: [("kick", 100), ("hihat", 80)],
            14: [("hihat", 60)], 16: [("snare", 100), ("hihat", 80)], 18: [("hihat", 60)],
        }, 20),
        "fill": _pattern({
            0: [("kick", 100), ("hihat", 80)], 4: [("hihat", 70)], 8: [("snare", 100)], 12: [("kick", 100)],
            14: [("snare", 90)], 16: [("tom1", 100)], 17: [("tom1", 100)], 18: [("tom2", 105)], 19: [("floor", 110)],
        }, 20),
    },
    "jazz_54": {
        # 5/4 jazz (alla "Take Five"): ride swing, pedale del charleston sul
        # 2 e sul 4, rullante di commento sul 4.
        "meter": "5/4", "grid": TRIPLET_GRID,
        "main": _triplet_pattern({
            0: [("ride", 80), ("kick", 55)], 3: [("ride", 70), ("hihat_pedal", 65)], 5: [("ride", 55)],
            6: [("ride", 75)], 9: [("ride", 70), ("hihat_pedal", 65), ("rimshot", 60)], 11: [("ride", 55)],
            12: [("ride", 75)],
        }, 15),
        "fill": _triplet_pattern({
            0: [("ride", 80)], 3: [("hihat_pedal", 65)], 6: [("ride", 75)], 9: [("snare", 75)],
            10: [("snare", 80)], 11: [("snare", 85)], 12: [("tom1", 90)], 13: [("tom2", 95)], 14: [("snare", 100)],
        }, 15),
    },

    # ---- 7/8 (sette ottavi) -------------------------------------------------
    "rock_78": {
        # 7/8 diviso 2+2+3: cassa all'inizio dei gruppi da 2, rullante sulla
        # seconda meta' del primo gruppo e sul gruppo da 3.
        "meter": "7/8", "grid": "8:", "pulse": 1,
        "main": _pattern({
            0: [("kick", 100), ("hihat", 80)], 1: [("hihat", 55)], 2: [("snare", 100), ("hihat", 75)],
            3: [("hihat", 55)], 4: [("kick", 95), ("hihat", 80)], 5: [("hihat", 55)], 6: [("snare", 100), ("hihat", 75)],
        }, 7),
        "fill": _pattern({
            0: [("kick", 100)], 2: [("snare", 100)], 3: [("tom1", 95)], 4: [("tom1", 100)],
            5: [("tom2", 100)], 6: [("snare", 110)],
        }, 7),
    },
    "balkan_78": {
        # 7/8 balcanico diviso 3+2+2: cassa sul primo gruppo, rullante sugli altri due.
        "meter": "7/8", "grid": "8:", "pulse": 1,
        "main": _pattern({
            0: [("kick", 100), ("hihat", 80)], 1: [("hihat", 55)], 2: [("hihat", 60)],
            3: [("snare", 95), ("hihat", 75)], 4: [("hihat", 55)], 5: [("snare", 90), ("hihat", 75)],
            6: [("kick", 80), ("hihat", 55)],
        }, 7),
        "fill": _pattern({
            0: [("kick", 100)], 1: [("snare", 80)], 2: [("snare", 85)], 3: [("tom1", 95)],
            4: [("tom1", 95)], 5: [("tom2", 100)], 6: [("snare", 110)],
        }, 7),
    },
})

# Giri alternativi dello stesso stile (con la variabilita' il batterista
# cambia giro all'inizio di un gruppo di battute, vedi generate_drum_pattern).
DRUM_ALTS: Dict[str, List[list]] = {
    "rock": [
        _pattern({0: [("kick", 105), ("hihat", 70)], 2: [("hihat", 70)], 4: [("snare", 100), ("hihat", 70)],
                  6: [("hihat", 70)], 8: [("kick", 105), ("hihat", 70)], 10: [("kick", 90), ("hihat", 70)],
                  12: [("snare", 100), ("hihat", 70)], 14: [("hihat_open", 75)]}),
        _pattern({0: [("kick", 105), ("ride", 80)], 2: [("ride", 65)], 4: [("snare", 100), ("ride", 80)],
                  6: [("ride", 65)], 7: [("kick", 85)], 8: [("kick", 100), ("ride", 80)], 10: [("ride", 65)],
                  12: [("snare", 100), ("ride", 80)], 14: [("ride", 65)]}),
    ],
    "funk": [
        _pattern({0: [("kick", 105), ("hihat", 80)], 2: [("hihat", 65)], 4: [("snare", 100), ("hihat", 80)],
                  5: [("kick", 85)], 6: [("hihat", 65)], 7: [("snare", 40)], 8: [("hihat", 80)],
                  10: [("kick", 90), ("hihat", 65)], 11: [("kick", 80)], 12: [("snare", 100), ("hihat", 80)],
                  14: [("hihat", 65)], 15: [("snare", 40)]}),
    ],
    "disco": [
        _pattern({0: [("kick", 105), ("hihat", 70)], 2: [("hihat_open", 75)], 4: [("kick", 100), ("snare", 100)],
                  6: [("hihat_open", 75)], 8: [("kick", 105), ("hihat", 70)], 10: [("hihat_open", 75)],
                  12: [("kick", 100), ("snare", 100), ("clap", 90)], 14: [("hihat_open", 75)]}),
    ],
    "punk": [
        _pattern({0: [("kick", 100), ("hihat", 100)], 2: [("snare", 95), ("hihat", 85)],
                  4: [("kick", 100), ("hihat", 100)], 6: [("snare", 95), ("hihat", 85)],
                  8: [("kick", 100), ("hihat", 100)], 10: [("snare", 95), ("hihat", 85)],
                  12: [("kick", 100), ("hihat", 100)], 14: [("snare", 100), ("hihat", 85)]}),
    ],
    "soul": [
        _pattern({0: [("kick", 90), ("tambourine", 90)], 2: [("tambourine", 60)],
                  4: [("snare", 100), ("tambourine", 100)], 6: [("tambourine", 70)], 7: [("kick", 80)],
                  8: [("kick", 90), ("tambourine", 90)], 10: [("tambourine", 60)],
                  12: [("snare", 100), ("tambourine", 100)], 14: [("tambourine", 60)], 15: [("kick", 75)]}),
    ],
    "rocknroll": [
        _pattern({0: [("kick", 90), ("ride", 90)], 2: [("ride", 65)], 3: [("kick", 75)],
                  4: [("snare", 100), ("ride", 100)], 6: [("ride", 65)], 8: [("kick", 90), ("ride", 90)],
                  10: [("ride", 65)], 11: [("kick", 80)], 12: [("snare", 100), ("ride", 100)], 14: [("ride", 65)]}),
    ],
    "reggae": [
        # "Steppers": cassa su ogni quarto, rullante di bordo sul 3.
        _pattern({0: [("kick", 95), ("hihat", 65)], 2: [("hihat", 65)], 4: [("kick", 95), ("hihat", 65)],
                  6: [("hihat", 65)], 8: [("kick", 100), ("rimshot", 90)], 10: [("hihat", 65)],
                  12: [("kick", 95), ("hihat", 65)], 14: [("hihat", 65)]}),
    ],
    "shuffle": [
        _triplet_pattern({0: [("kick", 95), ("ride", 95)], 2: [("ride", 60)], 3: [("snare", 100), ("ride", 100)],
                          5: [("ride", 60), ("kick", 75)], 6: [("kick", 90), ("ride", 90)], 8: [("ride", 60)],
                          9: [("snare", 100), ("ride", 100)], 11: [("ride", 60)]}),
    ],
    "swing": [
        _triplet_pattern({0: [("ride", 80), ("kick", 50)], 3: [("ride", 70), ("hihat_pedal", 70)],
                          5: [("ride", 55), ("snare", 45)], 6: [("ride", 75)],
                          9: [("ride", 70), ("hihat_pedal", 70)], 11: [("ride", 55), ("kick", 55)]}),
    ],
    "hiphop": [
        _pattern({0: [("kick", 105), ("hihat", 75)], 2: [("hihat", 60)], 3: [("kick", 85)],
                  4: [("snare", 105), ("hihat", 75)], 6: [("hihat", 60)], 8: [("hihat", 75)], 9: [("kick", 90)],
                  10: [("kick", 95), ("hihat", 60)], 12: [("snare", 105), ("hihat", 75)], 14: [("hihat", 60)],
                  15: [("kick", 80)]}),
    ],
    "metal": [
        _pattern({i: ([("kick", 95)] if i % 2 == 0 else []) + ([("crash", 95)] if i == 0 else
                                                              [("ride", 85)] if i % 4 == 0 else [])
                  + ([("snare", 115)] if i in (4, 12) else []) for i in range(16)}),
    ],
    "rock_54": [
        _pattern({0: [("kick", 100), ("ride", 85)], 2: [("ride", 60)], 4: [("kick", 85), ("ride", 70)],
                  6: [("ride", 60)], 8: [("snare", 100), ("ride", 85)], 10: [("ride", 60)],
                  12: [("kick", 100), ("ride", 85)], 14: [("kick", 80), ("ride", 60)],
                  16: [("snare", 100), ("ride", 85)], 18: [("ride", 60)]}, 20),
    ],
}

# Code di fill generiche per la seconda meta' (o l'ultimo quarto) di una
# battuta in 4/4, da unire all'inizio del giro dello stile: danno a ogni
# stile a sedicesimi o a terzine piu' fill fra cui scegliere.
_GENERIC_FILL_TAILS_16 = [
    {8: [("snare", 70)], 9: [("snare", 75)], 10: [("snare", 80)], 11: [("snare", 85)],
     12: [("snare", 90)], 13: [("snare", 95)], 14: [("snare", 100)], 15: [("snare", 110)]},
    {8: [("tom1", 95)], 10: [("tom1", 95)], 12: [("tom2", 100)], 14: [("floor", 105)], 15: [("floor", 105)]},
    {8: [("kick", 100)], 10: [("snare", 95)], 11: [("snare", 90)], 12: [("kick", 100)],
     14: [("snare", 100)], 15: [("snare", 105)]},
    {12: [("tom1", 100)], 13: [("tom1", 100)], 14: [("tom2", 105)], 15: [("floor", 110)]},
]
_GENERIC_FILL_TAILS_T12 = [
    {6: [("snare", 75)], 7: [("snare", 80)], 8: [("snare", 85)], 9: [("tom1", 95)],
     10: [("tom2", 100)], 11: [("floor", 105)]},
    {9: [("snare", 90)], 10: [("snare", 95)], 11: [("snare", 105)]},
]


def _drum_spec(style: str) -> dict:
    """La specifica dello stile: uno di DRUM_STYLES o uno stile personale
    'user:<nome>' (vedi core.user_styles). ValueError se non esiste."""
    spec = DRUM_STYLES.get(style) or user_styles.get_user_style("drums", style)
    if spec is None:
        raise ValueError(tr("Stile di batteria sconosciuto: '{style}' (validi: {0})", ', '.join(DRUM_STYLES), style=style))
    return spec


def _generic_fill(main: List[Optional[list]], per_pulse: int) -> List[Optional[list]]:
    """Fill per uno stile che non ne ha uno suo (stili personali): il giro,
    poi rullante su ogni unita' dell'ultima pulsazione, sempre piu' forte."""
    start = max(0, len(main) - per_pulse)
    tail = [[("snare", min(127, 80 + 8 * k))] for k in range(len(main) - start)]
    return list(main[:start]) + tail


def _style_fills(style: str) -> List[list]:
    """Il fill dello stile piu', per gli stili in 4/4 a sedicesimi o a
    terzine, i fill generici costruiti sul suo giro."""
    spec = _drum_spec(style)
    main = spec["main"]
    fills = [spec.get("fill") or _generic_fill(main, _slots_per_pulse(style, spec.get("grid", DEFAULT_GRID)))]
    if spec.get("meter", "4/4") == "4/4":
        grid = spec.get("grid", DEFAULT_GRID)
        tails = (_GENERIC_FILL_TAILS_16 if grid == DEFAULT_GRID and len(main) == 16
                 else _GENERIC_FILL_TAILS_T12 if grid == TRIPLET_GRID and len(main) == 12 else [])
        for tail in tails:
            start = min(tail)
            fills.append(list(main[:start]) + [tail.get(i) for i in range(start, len(main))])
    return fills


def drum_styles_for_meter(meter: str) -> List[str]:
    """Stili di DRUM_STYLES scritti per la metrica 'meter' (es. '3/4'),
    nell'ordine in cui sono definiti; [] se nessuno la supporta."""
    meter = _normalize_meter(meter)
    return [name for name, spec in DRUM_STYLES.items() if spec.get("meter", "4/4") == meter]


# Strumenti "di tempo" (charleston/ride/tamburello): un colpo isolato fuori dai
# battiti principali puo' saltare senza cambiare il groove.
_TIMEKEEPERS = ("hihat", "ride", "tambourine")

# Dove, per ogni stile, la variabilita' puo' aggiungere (solo su slot vuoti)
# una cassa in piu' ('extra_kick') o un rullante fantasma a volume basso
# ('ghost'). Uno stile senza voce qui (reggae, bossa, disco...) non riceve
# note aggiunte: il suo groove e' definito dai pochi colpi che ha; restano
# le variazioni di velocity, i colpi di tempo saltati e i fill alternativi.
DRUM_VARIATION: Dict[str, Dict[str, list]] = {
    "rock": {"extra_kick": [3, 7, 10, 11, 14]},
    "funk": {"extra_kick": [1, 5, 9, 11, 13], "ghost": [1, 5, 9, 11, 13]},
    "disco": {"ghost": [7, 15]},
    "punk": {"extra_kick": [3, 7, 11, 14]},
    "soul": {"extra_kick": [3, 10, 14], "ghost": [3, 7, 11, 15]},
    "rocknroll": {"extra_kick": [3, 7, 11, 14], "ghost": [3, 7, 15]},
    "shuffle": {"extra_kick": [10], "ghost": [4, 7]},
    "swing": {"extra_kick": [7], "ghost": [4, 7, 10]},
    "waltz": {"ghost": [3, 7, 11]},
    "ballad_68": {"extra_kick": [5], "ghost": [2, 5]},
    "blues_128": {"extra_kick": [5, 11], "ghost": [2, 5, 11]},
    "slow_rock_128": {"extra_kick": [5, 11], "ghost": [8]},
    "hiphop": {"extra_kick": [3, 9, 15], "ghost": [7, 11, 15]},
    "halftime": {"extra_kick": [3, 14], "ghost": [4, 13]},
    "country": {"extra_kick": [6, 14]},
    "march": {"ghost": [2, 10]},
    "rock_54": {"extra_kick": [3, 10, 18], "ghost": [7, 15]},
    "rock_78": {"extra_kick": [5], "ghost": [3]},
    "balkan_78": {"extra_kick": [4], "ghost": [2]},
}


def _slots_per_pulse(style: str, grid: str) -> int:
    """Slot per pulsazione "sentita" dello stile: un quarto in 4/4 e 3/4
    (4 sedicesimi o 3 terzine), un quarto puntato in 6/8 e 12/8 (3 ottavi,
    vedi la chiave 'pulse' di DRUM_STYLES)."""
    spec = DRUM_STYLES.get(style) or user_styles.get_user_style("drums", style) or {}
    pulse = spec.get("pulse")
    if pulse:
        return pulse
    return 3 if grid == TRIPLET_GRID else 4


def _vary_drum_bar(bar: List[Optional[list]], style: str, grid: str,
                   amount: Variability, rng: random.Random, allow_additions: bool) -> List[Optional[list]]:
    """Copia di una battuta con la variazione applicata: colpi di tempo
    isolati che saltano, cassa extra e rullanti fantasma sugli slot VUOTI
    (mai sopra un colpo del disegno: solo se 'allow_additions', cioe' non nei
    fill) e piccole variazioni di velocity sugli slot rimasti."""
    out = [list(h) if h else None for h in bar]
    per_beat = _slots_per_pulse(style, grid)
    if allow_additions:
        for i, hits in enumerate(bar):
            if (hits and len(hits) == 1 and hits[0][0] in _TIMEKEEPERS
                    and i % per_beat != 0 and rng.random() < 0.10 * amount.rhythm):
                out[i] = None
        spec = DRUM_VARIATION.get(style, {})
        for i in spec.get("extra_kick", ()):
            if bar[i] is None and rng.random() < 0.35 * amount.rhythm:
                out[i] = [("kick", rng.randint(80, 100))]
        for i in spec.get("ghost", ()):
            if bar[i] is None and out[i] is None and rng.random() < 0.30 * amount.notes:
                out[i] = [("snare", rng.randint(30, 48))]
    jitter = round(12 * amount.dynamics)
    if jitter:
        for i, hits in enumerate(out):
            if hits:
                delta = rng.randint(-jitter, jitter)
                out[i] = [(name, max(1, min(127, vel + delta))) for name, vel in hits]
    return out


def _vary_fill(main: List[Optional[list]], fill: List[Optional[list]],
               variability: float, rng: random.Random) -> List[Optional[list]]:
    """Il fill completo, oppure (piu' spesso al crescere della variabilita') un
    fill a meta' battuta o sull'ultimo beat: il giro base prosegue e poi il
    fill lo interrompe."""
    kind = rng.choices(["full", "half", "last"], weights=[1.0, variability, variability])[0]
    if kind == "full":
        return list(fill)
    cut = len(main) // 2 if kind == "half" else (len(main) * 3) // 4
    return list(main[:cut]) + list(fill[cut:])


# Intensita' della parte (sezione "C" della proposta: struttura del brano):
# 'light' (strofa tranquilla, intro), 'normal', 'full' (ritornello),
# 'build' (in crescendo: leggera, normale, piena per terzi del brano).
INTENSITIES = ("light", "normal", "full", "build")


def _intensity_at(intensity: str, bar_idx: int, bars: int) -> str:
    if intensity != "build":
        return intensity
    third = bar_idx * 3 // max(1, bars)
    return ("light", "normal", "full")[min(2, third)]


def _apply_drum_intensity(bar: List[Optional[list]], style: str, grid: str, level: str) -> List[Optional[list]]:
    """'light': via i colpi di tempo in levare e le note fantasma, tutto un po'
    piu' piano; 'full': charleston chiuso -> ride, tutto un po' piu' forte."""
    if level == "normal":
        return bar
    per_beat = _slots_per_pulse(style, grid)
    out = []
    for i, hits in enumerate(bar):
        if not hits:
            out.append(None)
            continue
        new = []
        for name, vel in hits:
            if level == "light":
                if name in _TIMEKEEPERS and i % per_beat != 0:
                    continue
                if name == "snare" and vel < 50:
                    continue
                new.append((name, max(1, vel - 18)))
            else:
                new.append(("ride" if name == "hihat" else name, min(127, vel + 10)))
        # niente doppioni (es. charleston diventato ride accanto a un ride)
        seen, unique = set(), []
        for name, vel in new:
            if name not in seen:
                seen.add(name)
                unique.append((name, vel))
        out.append(unique or None)
    return out


def _ending_bar(length: int) -> List[Optional[list]]:
    """Chiusura: colpo finale di piatto e cassa sul primo tempo, poi silenzio."""
    return [[("crash", 110), ("kick", 110)]] + [None] * (length - 1)


def _with_crash(bar: List[Optional[list]]) -> List[Optional[list]]:
    bar = list(bar)
    existing = bar[0] or []
    if not any(name == "crash" for name, _ in existing):
        bar[0] = existing + [("crash", 100)]
    return bar


def generate_drum_pattern(style: str, bars: int, fill_every: int = 4,
                          variability=0.0, seed: Optional[int] = None,
                          intensity: str = "normal", phrase_fills: bool = False,
                          ending: bool = False) -> str:
    """Genera 'bars' battute di batteria nello stile scelto (vedi
    DRUM_STYLES), ripetendo il giro base e sostituendolo ogni 'fill_every'
    battute con un fill (0 o un numero <=0 disabilita i fill: solo il giro
    base ripetuto). Aggiunge un crash all'inizio della battuta subito dopo
    ogni fill, per il classico "rientro" accentato. Solleva ValueError se lo
    stile non e' tra DRUM_STYLES, 'bars' non e' positivo o l'intensita' non
    e' fra INTENSITIES.

    'variability' (0-1, 0 = nessuna: sempre lo stesso risultato) aggiunge
    variazione, decisa dal generatore casuale inizializzato con 'seed'
    (stesso seme = stesso testo; None = seme casuale): all'inizio di ogni
    gruppo di battute il giro puo' passare a uno dei giri alternativi dello
    stile (DRUM_ALTS), i fill si scelgono fra quelli disponibili (vedi
    _style_fills) e possono essere a meta' o sull'ultimo beat, e in ogni
    battuta colpi di tempo che saltano, cassa extra e rullanti fantasma (vedi
    DRUM_VARIATION) e velocity leggermente diverse. 'variability' puo' anche
    essere una Variability, con un valore per aspetto: ritmo (giri, fill,
    colpi che saltano, cassa extra), note (rullanti fantasma) e dinamica
    (velocity). 'style' puo' essere uno stile personale 'user:<nome>' (vedi
    core.user_styles), con i suoi giri alternativi e il suo fill.

    Struttura: 'intensity' (vedi INTENSITIES) alleggerisce o riempie la
    parte ('full' passa al ride e apre ogni gruppo di battute con un crash);
    'phrase_fills' fa fill piccoli (solo l'ultimo beat) ogni 'fill_every'
    battute e completi ogni 2*'fill_every'; 'ending' chiude l'ultima battuta
    con un colpo finale."""
    spec = _drum_spec(style)
    if bars <= 0:
        raise ValueError(tr("Il numero di battute deve essere positivo"))
    if intensity not in INTENSITIES:
        raise ValueError(tr("Intensita' sconosciuta: '{intensity}' (valide: {0})", ', '.join(INTENSITIES), intensity=intensity))

    main = spec["main"]
    grid = spec.get("grid", DEFAULT_GRID)
    amount = _variability(variability)
    rng = random.Random(seed)
    grooves = [main] + (spec.get("alts") or DRUM_ALTS.get(style, []))
    fills = _style_fills(style)
    block = fill_every if fill_every > 0 else 4

    slots: List[Optional[list]] = []
    groove = main
    for bar_idx in range(bars):
        level = _intensity_at(intensity, bar_idx, bars)
        is_last = bar_idx == bars - 1
        if bar_idx > 0 and bar_idx % block == 0 and amount.rhythm > 0 and len(grooves) > 1:
            groove = rng.choices(grooves, weights=[1.0] + [amount.rhythm] * (len(grooves) - 1))[0]
        is_fill_bar = fill_every > 0 and (bar_idx + 1) % fill_every == 0 and not is_last
        if ending and is_last and bars > 1:
            slots.extend(_ending_bar(len(main)))
            continue
        if is_fill_bar:
            fill = fills[0]
            if amount.rhythm > 0 and len(fills) > 1:
                fill = rng.choices(fills, weights=[1.0] + [amount.rhythm] * (len(fills) - 1))[0]
            big = not phrase_fills or (bar_idx + 1) % (2 * fill_every) == 0
            if not big:
                cut = (len(groove) * 3) // 4
                bar = list(groove[:cut]) + list(fill[cut:])
            elif amount.rhythm > 0:
                bar = _vary_fill(groove, fill, amount.rhythm, rng)
            else:
                bar = list(fill)
        else:
            bar = list(groove)
        if amount.any():
            bar = _vary_drum_bar(bar, style, grid, amount, rng, allow_additions=not is_fill_bar)
        bar = _apply_drum_intensity(bar, style, grid, level)
        if bar_idx > 0:
            prev_was_fill = fill_every > 0 and bar_idx % fill_every == 0 and bar_idx != 1
            if prev_was_fill or (level == "full" and bar_idx % block == 0):
                bar = _with_crash(bar)
        slots.extend(bar)

    return " ".join(_slots_to_tokens(slots, grid))


# ---------------------------------------------------------------------------
# Basso
# ---------------------------------------------------------------------------

class ChordSpan(NamedTuple):
    start_beat: float
    duration_beats: float
    root_pc: int
    has_fifth: bool
    # Intervallo (in semitoni sopra la fondamentale) della terza (3 minore, 4
    # maggiore; None se l'accordo non ne ha, es. sus4 o quinta vuota) e della
    # settima (10 o 11; None se assente): servono agli stili che camminano
    # sui gradi dell'accordo (walking, blues) per non suonare una terza
    # maggiore su un accordo minore. Il default 4/None e' quello di una
    # triade maggiore.
    third: Optional[int] = 4
    seventh: Optional[int] = None


def _third_and_seventh(intervals) -> Tuple[Optional[int], Optional[int]]:
    ivs = set(intervals)
    third = 3 if 3 in ivs else 4 if 4 in ivs else None
    seventh = 10 if 10 in ivs else 11 if 11 in ivs else None
    return third, seventh


def _chord_span_from_block(ev) -> Optional[ChordSpan]:
    """Accordo di un blocco esplicito [c*4 e*4 g*4] (cosi' l'import MIDI e le
    tracce scritte a mano rappresentano gli accordi senza un simbolo):
    riconosciuto come qualita' nota, altrimenti la fondamentale e' la nota
    piu' bassa. None se il blocco ha meno di due note intonate."""
    midi_notes = sorted(pitch_to_midi(it["letter"], it["octave"])
                        for it in ev.items or [] if it.get("kind") == "note")
    if len({n % 12 for n in midi_notes}) < 2:
        return None
    lowest_pc = midi_notes[0] % 12
    relative = {(n - midi_notes[0]) % 12 for n in midi_notes}
    # Un basso segue la nota piu' bassa: se le note formano una qualita' nota
    # a partire da essa (stato fondamentale) e' quella la fondamentale. Serve
    # a distinguere gli accordi che hanno le stesse note (La-Do-Mi-Sol e'
    # Am7, non C6); solo se non c'e' si ricade sul riconoscitore, che
    # gestisce i rivolti (es. Mi-Sol-Do = C/E).
    root_position = next((q for q, ivs in CHORD_QUALITIES.items() if set(ivs) == relative), None)
    if root_position is not None:
        root_pc, intervals = lowest_pc, CHORD_QUALITIES[root_position]
    else:
        recognized = recognize_chord(midi_notes)
        if recognized is not None:
            root_pc, quality, _octave = recognized
            intervals = CHORD_QUALITIES[quality]
        else:
            root_pc, intervals = lowest_pc, relative
    third, seventh = _third_and_seventh(intervals)
    return ChordSpan(start_beat=ev.start, duration_beats=ev.duration, root_pc=root_pc,
                     has_fifth=7 in intervals, third=third, seventh=seventh)


def extract_chords_from_track(text: str, patterns: Dict[str, Pattern],
                               default_octave: int = 4, midi_dir: Optional[str] = None) -> List[ChordSpan]:
    """Estrae la sequenza di accordi da una traccia esistente, ignorando note
    singole/percussioni/pause: e' l'armonia di riferimento su cui far
    camminare il basso (vedi generate_bass_from_chords). Conta sia un accordo
    scritto come simbolo (kind='chord', es. Cmaj7, vedi core.notation.Event)
    sia un blocco esplicito [...] di almeno due note (come li scrive l'import
    MIDI). Ritorna [] se la traccia non contiene nessuno dei due."""
    events = parse_track_text(text, patterns, default_octave=default_octave, midi_dir=midi_dir)
    spans = []
    for ev in events:
        if ev.kind == "chord":
            chord = parse_chord_symbol(ev.symbol)
            third, seventh = _third_and_seventh(chord.intervals)
            spans.append(ChordSpan(
                start_beat=ev.start, duration_beats=ev.duration,
                root_pc=chord.root_pc, has_fifth=7 in chord.intervals,
                third=third, seventh=seventh,
            ))
        elif ev.kind == "block":
            span = _chord_span_from_block(ev)
            if span is not None:
                spans.append(span)
    return spans


BASS_STYLES = ("root", "root_fifth", "walking", "pedal", "two_feel", "octaves", "blues",
               "eighths", "reggae", "bossa", "shuffle", "waltz")


def _note_token(pc: int, octave: int) -> str:
    return f"{pc_to_letter(pc)}*{octave}"


def _beats_in_span(span: ChordSpan) -> List[float]:
    """Istanti (in beat, relativi all'inizio dell'accordo) su cui il basso
    attacca una nuova nota per quell'accordo: uno per ogni quarto intero
    contenuto nella durata dell'accordo (l'eventuale resto viene coperto
    tenendo l'ultima nota)."""
    beats = []
    b = 0.0
    while b < span.duration_beats - 1e-6:
        beats.append(b)
        b += 1.0
    return beats or [0.0]


def _bass_notes_for_span(span: ChordSpan, style: str, octave: int, variant: bool,
                          next_root_pc: Optional[int]) -> List[Tuple[int, int]]:
    """(classe di altezza, scarto d'ottava rispetto a 'octave') per ogni
    attacco (vedi _beats_in_span) di un accordo, nello stile scelto.
    'variant' alterna un trattamento leggermente diverso ogni
    variation_every accordi (vedi generate_bass_from_chords), per evitare la
    ripetizione meccanica dello stesso disegno per tutto il brano."""
    root = span.root_pc
    fifth = (span.root_pc + 7) % 12 if span.has_fifth else root
    n_beats = len(_beats_in_span(span))

    if style == "root":
        if not variant or n_beats < 2:
            return [(root, 0)] * n_beats
        # variante: salto d'ottava alternato invece della nota ripetuta ferma
        return [(root, 0 if i % 2 == 0 else 1) for i in range(n_beats)]

    if style == "root_fifth":
        base = [(root, 0), (fifth, 0), (root, 0), (fifth, 0)]
        if variant:
            base = [(root, 0), (root, 1), (fifth, 0), (fifth, 0)]
        return [base[i % 4] for i in range(n_beats)]

    if style == "walking":
        notes = [(root, 0)]
        if n_beats >= 2:
            # variante: la terza VERA dell'accordo (minore su un minore) al posto della quinta;
            # senza terza (sus, quinta vuota) si resta sulla quinta
            third = (root + span.third) % 12 if span.third is not None else fifth
            notes.append((fifth, 0) if not variant else (third, 0))
        if n_beats >= 3:
            if variant and span.seventh is not None:
                notes.append(((root + span.seventh) % 12, 0))  # variante: la settima dell'accordo
            else:
                notes.append((root, 1 if variant else 0))
        if n_beats >= 4:
            target = next_root_pc if next_root_pc is not None else root
            # nota di avvicinamento cromatico (un semitono sotto l'accordo successivo)
            notes.append(((target - 1) % 12, 0))
        while len(notes) < n_beats:
            notes.append((root, 0))
        return notes[:n_beats]

    raise ValueError(tr("Stile di basso sconosciuto: '{style}' (validi: {0})", ', '.join(BASS_STYLES), style=style))


def _expand_chords_to_cover(chords: List[ChordSpan], min_total_beats: float) -> List[ChordSpan]:
    """Ripete ciclicamente 'chords' (stessa progressione, non un trattamento
    diverso) finche' la durata totale non raggiunge almeno 'min_total_beats':
    usato per far seguire al basso l'intera estensione del brano anche
    quando la traccia di accordi sorgente e' piu' corta delle altre tracce
    gia' scritte nel progetto (vedi generate_bass_from_chords/
    tracks_duration_beats). Nessun effetto (ritorna 'chords' invariata) se
    gia' abbastanza lunga o se min_total_beats non e' positivo."""
    if not chords or min_total_beats <= 0:
        return chords
    last_end = chords[-1].start_beat + chords[-1].duration_beats
    period = last_end - chords[0].start_beat
    if period <= 1e-6:
        return chords
    expanded = list(chords)
    rep = 1
    while last_end + (rep - 1) * period < min_total_beats - 1e-6:
        offset = rep * period
        expanded.extend(
            span._replace(start_beat=span.start_beat + offset) for span in chords
        )
        rep += 1
    return expanded


# Stili "a disegno": ogni stile dichiara la griglia (un attacco al massimo per
# unita') e il disegno di UNA battuta di 4 beat come [(posizione in beat,
# ruolo), ...]; il disegno si ripete battuta per battuta sulla durata
# dell'accordo (troncato dove l'accordo finisce). Ruoli: root, root_hi
# (ottava sopra), fifth, third, sixth, flat7, seventh, approach (mezzo tono
# sotto la fondamentale dell'accordo successivo; solo nell'ultima battuta
# dell'accordo, altrove diventa root) e rest (pausa). Gli stili 'root',
# 'root_fifth' e 'walking' restano gestiti da _bass_notes_for_span.
# 'variant' e' il disegno alternativo usato ogni variation_every accordi.
_T = 1.0 / 3.0  # una terzina di ottavo, in beat (griglia 8T:)

BASS_PATTERNS: Dict[str, dict] = {
    # Una sola nota lunga per accordo: ballate.
    "pedal": {"grid": "4:", "tile": False, "bar": [(0.0, "root")], "variant": None},
    # "Two-feel": fondamentale sul 1, quinta sul 3 (jazz lento, country).
    "two_feel": {"grid": "4:", "bar": [(0.0, "root"), (2.0, "fifth")],
                 "variant": [(0.0, "root"), (2.0, "fifth"), (3.0, "approach")]},
    # Fondamentale e ottava alternate (disco/funk semplice).
    "octaves": {"grid": "4:", "bar": [(0.0, "root"), (1.0, "root_hi"), (2.0, "root"), (3.0, "root_hi")],
                "variant": [(0.0, "root"), (1.0, "root_hi"), (2.0, "fifth"), (3.0, "root_hi")]},
    # Blues/boogie 1-3-5-6 (variante 1-3-5-b7), con la terza vera dell'accordo.
    "blues": {"grid": "4:", "bar": [(0.0, "root"), (1.0, "third"), (2.0, "fifth"), (3.0, "sixth")],
              "variant": [(0.0, "root"), (1.0, "third"), (2.0, "fifth"), (3.0, "flat7")]},
    # Ottavi sulla fondamentale (rock, pop, punk).
    "eighths": {"grid": "8:", "bar": [(0.5 * i, "root") for i in range(8)],
                "variant": [(0.5 * i, "root") for i in range(6)] + [(3.0, "fifth"), (3.5, "root")]},
    # Reggae: il primo tempo resta vuoto, fondamentale lunga dal 2, quinta sul
    # "e" del 3, fondamentale sul 4.
    "reggae": {"grid": "8:", "bar": [(0.0, "rest"), (1.0, "root"), (2.5, "fifth"), (3.0, "root")],
               "variant": [(0.0, "rest"), (1.0, "root"), (2.5, "fifth"), (3.0, "fifth")]},
    # Bossa nova: fondamentale sul 1 e sul 3, quinta sul "e" del 2 e del 4.
    "bossa": {"grid": "8:", "bar": [(0.0, "root"), (1.5, "fifth"), (2.0, "root"), (3.5, "fifth")],
              "variant": [(0.0, "root"), (1.5, "fifth"), (2.0, "root"), (3.5, "approach")]},
    # Shuffle blues a terzine: 1-3-5-6-b7-6-5-3 in ottavi "dondolanti" (lunga-breve).
    "waltz": {"grid": "4:", "bar": [(0.0, "root"), (1.0, "rest")],
              "variant": [(0.0, "root"), (1.0, "rest"), (2.0, "fifth")]},
    "shuffle": {"grid": "8T:", "bar": [(0.0, "root"), (2 * _T, "third"), (1.0, "fifth"), (1 + 2 * _T, "sixth"),
                                       (2.0, "flat7"), (2 + 2 * _T, "sixth"), (3.0, "fifth"), (3 + 2 * _T, "third")],
                "variant": [(0.0, "root"), (2 * _T, "third"), (1.0, "fifth"), (1 + 2 * _T, "sixth"),
                            (2.0, "flat7"), (2 + 2 * _T, "sixth"), (3.0, "fifth"), (3 + 2 * _T, "approach")]},
}

# Griglia (in beat) di ciascuna dichiarazione "N:" / "NT:".
_GRID_UNIT_BEATS = {"4:": 1.0, "8:": 0.5, "8T:": _T, "16:": 0.25}
BEATS_PER_BAR = 4.0


# Note di avvicinamento alla fondamentale dell'accordo successivo (semitoni
# rispetto a quella): mezzo tono sotto (il classico cromatismo), mezzo tono
# sopra, un tono sotto (passo di scala) o la sua quinta (avvicinamento "di
# dominante"). Le ultime tre si usano come note di passaggio aggiunte dalla
# variabilita' (vedi _add_passing_note).
_APPROACH_STEPS = {"approach": -1, "approach_above": 1, "approach_step": -2, "approach_fifth": 7}


def _resolve_learned_role(role: str, span: ChordSpan) -> Tuple[int, int]:
    """Ruolo di uno stile personale (vedi core.style_learn): 'L:<grado>:<k>',
    il grado dell'accordo (root, third, fifth, sixth, flat7, seventh o
    'iN', N semitoni sopra la fondamentale) nella k-esima ottava sopra la
    fondamentale; terza, quinta e settima seguono l'accordo corrente."""
    _prefix, degree, k = role.split(":")
    if degree == "root":
        interval = 0
    elif degree == "third":
        interval = span.third if span.third is not None else 7
    elif degree == "fifth":
        interval = 7 if span.has_fifth else 0
    elif degree == "sixth":
        interval = 9
    elif degree == "flat7":
        interval = 10
    elif degree == "seventh":
        interval = span.seventh if span.seventh is not None else 10
    elif degree.startswith("i"):
        interval = int(degree[1:])
    else:
        raise ValueError(tr("Ruolo sconosciuto: '{role}'", role=role))
    absolute = span.root_pc + interval + 12 * int(k)
    return absolute % 12, absolute // 12


def _resolve_role(role, span: ChordSpan, next_root_pc: Optional[int]) -> Optional[Tuple[int, int]]:
    """(classe di altezza, scarto d'ottava) per un ruolo; None per una pausa.
    Un ruolo gia' risolto (tupla) passa invariato: e' cosi' che gli stili
    storici (_bass_notes_for_span) usano lo stesso emettitore."""
    if isinstance(role, tuple):
        return role
    if role.startswith("L:next:"):
        # stile personale: nota di avvicinamento, in semitoni dalla fondamentale
        # dell'accordo successivo (nell'ottava di riferimento)
        absolute = (next_root_pc if next_root_pc is not None else span.root_pc) + int(role[7:])
        return absolute % 12, absolute // 12
    if role.startswith("L:"):
        return _resolve_learned_role(role, span)
    root = span.root_pc
    fifth = (root + 7) % 12 if span.has_fifth else root
    if role == "rest":
        return None
    if role == "root":
        return (root, 0)
    if role == "root_hi":
        return (root, 1)
    if role == "fifth":
        return (fifth, 0)
    if role == "third":
        return (((root + span.third) % 12) if span.third is not None else fifth, 0)
    if role == "sixth":
        return ((root + 9) % 12, 0)
    if role == "flat7":
        return ((root + 10) % 12, 0)
    if role == "seventh":
        return (((root + span.seventh) % 12) if span.seventh is not None else root, 0 if span.seventh is not None else 1)
    if role in _APPROACH_STEPS:
        target = next_root_pc if next_root_pc is not None else root
        return ((target + _APPROACH_STEPS[role]) % 12, 0)
    raise ValueError(tr("Ruolo di basso sconosciuto: '{role}'", role=role))


def _pattern_events(pattern: dict, span: ChordSpan, variant: bool,
                    bar_beats: float = BEATS_PER_BAR, bar_for=None) -> list:
    """[(posizione in beat dall'inizio dell'accordo, ruolo), ...] di un
    accordo per uno stile di BASS_PATTERNS/MELODIC_PATTERNS, ripetendo il
    disegno ogni 'bar_beats' beat (la durata della battuta nella metrica del
    brano, vedi meter_beats): gli attacchi del disegno che cadono oltre una
    battuta piu' corta di quella per cui e' scritto vengono tralasciati.
    'bar_for' (vedi _bar_picker), se dato, sceglie battuta per battuta il
    disegno da usare (quello base o uno dei PATTERN_ALTS)."""
    base = pattern["variant"] if (variant and pattern["variant"]) else pattern["bar"]

    def fit(bar):
        return [(offset, role) for offset, role in bar if offset < bar_beats - 1e-6]

    if not pattern.get("tile", True):
        return fit(base)
    n_bars = max(1, int(-(-span.duration_beats // bar_beats)))
    events = []
    for k in range(n_bars):
        bar = fit(bar_for(k) if bar_for is not None else base)
        for offset, role in bar:
            t = k * bar_beats + offset
            if t >= span.duration_beats - 1e-6:
                continue
            if role == "approach" and k != n_bars - 1:
                role = "root"  # l'avvicinamento cromatico solo alla fine dell'accordo
            events.append((t, role))
    return events


def _legacy_events(span: ChordSpan, style: str, octave: int, variant: bool,
                   next_root_pc: Optional[int]) -> list:
    """Gli stili storici (root/root_fifth/walking): un attacco per quarto."""
    notes = _bass_notes_for_span(span, style, octave, variant, next_root_pc)
    return [(beat, note) for beat, note in zip(_beats_in_span(span), notes)]


# Probabilita' (moltiplicate per 'variability', 0-1) delle variazioni casuali
# condivise da basso e melodia/accompagnamento (vedi _vary_events e
# generate_bass_from_chords/generate_melodic_line).
_VARY_MERGE_P = 0.20    # l'attacco si unisce al precedente (nota piu' lunga)
_VARY_REST_P = 0.50     # soglia cumulativa: fra MERGE e REST l'attacco diventa pausa
_VARY_OCTAVE_P = 0.25   # solo basso: la fondamentale sale d'ottava
_VARY_VARIANT_P = 0.6   # il trattamento alternativo scatta fuori da variation_every


def _vary_events(starts: list, amount: Variability, rng: random.Random,
                 octave_jumps: bool = False) -> list:
    """Variazione degli attacchi di un accordo. Restano sempre: tutto fino al
    primo attacco che suona (compreso: la nota/accordo che dichiara
    l'armonia, anche quando il disegno si apre con una pausa, es. il basso
    reggae), le note di avvicinamento e le pause del disegno (che non vanno
    riempite allungando la nota precedente, es. funk_stab). Gli altri
    attacchi possono unirsi al precedente (nota o accordo piu' lungo),
    diventare pausa o, con 'octave_jumps' (basso: ha senso per una
    fondamentale singola, non per un accordo di piu' note), salire di
    un'ottava. Le pause consecutive vengono fuse in una sola."""
    first = next((i for i, (_, role) in enumerate(starts) if role != "rest"), len(starts) - 1)
    out = list(starts[:first + 1])
    for u, role in starts[first + 1:]:
        if role == "rest":
            if out[-1][1] != "rest":
                out.append((u, role))
            continue
        if role != "approach":
            r = rng.random()
            if r < _VARY_MERGE_P * amount.rhythm:
                continue  # unita' alla nota/accordo precedente: dura di piu'
            if r < _VARY_REST_P * amount.rhythm:
                if out[-1][1] != "rest":
                    out.append((u, "rest"))
                continue
        if octave_jumps and rng.random() < _VARY_OCTAVE_P * amount.notes:
            if role == "root":
                role = "root_hi"
            elif isinstance(role, tuple) and role[1] == 0:
                role = (role[0], 1)
        out.append((u, role))
    return out


def _quantize_starts(events: list, unit: float, total_units: int, amount: Variability,
                     rng: Optional[random.Random], octave_jumps: bool) -> list:
    """[(unita' di griglia, ruolo), ...] degli attacchi di un accordo (uno al
    massimo per unita', entro la durata), variati se ritmo o note > 0 (vedi
    _vary_events). Se il disegno inizia in levare (nessun attacco sul primo
    movimento) apre con una pausa: altrimenti la prima nota scivolerebbe
    all'indietro fino a occupare anche lo spazio prima del suo vero attacco."""
    starts = []
    for t, role in events:
        u = round(t / unit)
        if u < total_units and (not starts or u > starts[-1][0]):
            starts.append((u, role))
    if (amount.rhythm > 0 or amount.notes > 0) and rng is not None and starts:
        starts = _vary_events(starts, amount, rng, octave_jumps)
    if starts and starts[0][0] > 0:
        starts.insert(0, (0, "rest"))
    return starts


def _span_units(span: ChordSpan, unit: float) -> Tuple[int, int]:
    """(prima unita', unita' di fine) di un accordo sulla griglia 'unit',
    arrotondando le posizioni ASSOLUTE e non la durata: arrotondare la
    durata di ogni accordo separatamente accumula l'errore (es. accordi di
    1.5 beat su una griglia di quarti: 2 + 2 unita' per 3 beat), e la linea
    generata scivolerebbe fuori tempo rispetto agli accordi."""
    start_u = round(span.start_beat / unit)
    end_u = round((span.start_beat + span.duration_beats) / unit)
    return start_u, max(start_u + 1, end_u)


# Disegni alternativi (oltre a 'bar' e 'variant') di alcuni stili di basso,
# accompagnamento e riff: con la variabilita', un accordo puo' usare uno di
# questi invece del disegno base (vedi _bar_picker). Stesso formato di
# 'bar' in BASS_PATTERNS/MELODIC_PATTERNS.
_CHORD = ["root", "third", "fifth"]
PATTERN_ALTS: Dict[str, List[list]] = {
    # basso
    "two_feel": [[(0.0, "root"), (2.0, "third")], [(0.0, "root"), (2.0, "root_hi")]],
    "octaves": [[(0.0, "root"), (1.0, "root_hi"), (2.0, "root"), (3.0, "approach")],
                [(0.0, "root"), (1.0, "root_hi"), (2.0, "root_hi"), (3.0, "root")]],
    "blues": [[(0.0, "root"), (1.0, "fifth"), (2.0, "sixth"), (3.0, "fifth")],
              [(0.0, "root"), (1.0, "third"), (2.0, "fifth"), (3.0, "third")]],
    "eighths": [[(0.5 * i, "root") for i in range(6)] + [(3.0, "root_hi"), (3.5, "root")],
                [(0.0, "root"), (0.5, "root"), (1.0, "fifth"), (1.5, "root"),
                 (2.0, "root"), (2.5, "root"), (3.0, "fifth"), (3.5, "approach")]],
    "reggae": [[(0.0, "rest"), (1.0, "root"), (1.5, "root"), (2.5, "fifth"), (3.5, "root_hi")],
               [(0.0, "rest"), (1.0, "root"), (2.0, "root"), (3.0, "fifth")]],
    "bossa": [[(0.0, "root"), (1.5, "root"), (2.0, "fifth"), (3.5, "fifth")],
              [(0.0, "root"), (1.5, "fifth"), (2.0, "fifth"), (3.5, "root")]],
    "shuffle": [[(0.0, "root"), (2 * _T, "root"), (1.0, "third"), (1 + 2 * _T, "fifth"),
                 (2.0, "sixth"), (2 + 2 * _T, "fifth"), (3.0, "third"), (3 + 2 * _T, "approach")],
                [(0.0, "root"), (2 * _T, "root_hi"), (1.0, "root"), (1 + 2 * _T, "root_hi"),
                 (2.0, "root"), (2 + 2 * _T, "root_hi"), (3.0, "fifth"), (3 + 2 * _T, "sixth")]],
    # accompagnamento
    "block_chords": [[(0.0, _CHORD), (1.0, _CHORD), (3.0, _CHORD)],
                     [(0.0, _CHORD), (2.0, _CHORD), (3.0, _CHORD)],
                     [(0.0, _CHORD), (1.0, _CHORD), (2.0, _CHORD)]],
    "arpeggio_up": [[(0.0, "root"), (0.5, "fifth"), (1.0, "root_hi"), (1.5, "fifth"),
                     (2.0, "third"), (2.5, "fifth"), (3.0, "root_hi"), (3.5, "fifth")],
                    [(0.0, "root"), (0.5, "third"), (1.0, "fifth"), (1.5, "third"),
                     (2.0, "root"), (2.5, "third"), (3.0, "fifth"), (3.5, "root_hi")]],
    "quarter_chords": [[(0.0, _CHORD), (1.0, "rest"), (2.0, _CHORD), (3.0, _CHORD)],
                       [(0.0, _CHORD), (1.0, _CHORD), (2.0, _CHORD), (3.0, "rest")]],
    "bossa_comp": [[(0.0, _CHORD), (1.5, _CHORD), (2.5, _CHORD), (3.5, _CHORD)],
                   [(0.0, _CHORD), (1.0, _CHORD), (2.5, _CHORD), (3.0, _CHORD)]],
    "funk_stab": [[(0.0, _CHORD), (0.5, "rest"), (1.5, _CHORD), (2.0, "rest"), (3.5, _CHORD)],
                  [(0.5, _CHORD), (1.0, "rest"), (2.5, _CHORD), (3.0, "rest")]],
    "skank_chords": [[(0.5, _CHORD), (1.5, _CHORD), (2.5, _CHORD), (3.0, "rest"), (3.5, _CHORD)]],
    "montuno": [[(0.0, ["root", "fifth"]), (0.5, ["third", "fifth"]), (1.5, ["root_hi", "third"]),
                 (2.0, ["root", "fifth"]), (3.0, ["third", "fifth"]), (3.5, ["root_hi", "third"])]],
    # riff/melodia
    "riff_short": [[(0.0, "root"), (0.5, "fifth"), (1.0, "root_hi"), (2.0, "fifth"), (2.5, "third"), (3.0, "root")],
                   [(0.0, "root"), (1.0, "third"), (1.5, "fifth"), (2.5, "root_hi"), (3.0, "fifth")]],
    "blues_lick": [[(0.0, "root_hi"), (2 * _T, "flat7"), (1.0, "fifth"), (2.0, "third"),
                    (2 + 2 * _T, "fifth"), (3.0, "root"), (3 + 2 * _T, "approach")]],
    "guide_tones": [[(0.0, "third"), (1.0, "fifth"), (2.0, "seventh")]],
    "call_response": [[(0.0, "rest"), (2.0, "root"), (2.5, "third"), (3.0, "fifth"), (3.5, "root_hi")]],
    "scale_run": [[(0.0, "root_hi"), (0.5, "seventh"), (1.0, "fifth"), (1.5, "third"),
                   (2.0, "root"), (3.0, "fifth"), (3.5, "approach")]],
    "arpeggio_updown": [[(0.0, "root_hi"), (0.5, "fifth"), (1.0, "third"), (1.5, "root"),
                         (2.0, "third"), (2.5, "fifth"), (3.0, "root_hi"), (3.5, "approach")]],
    "pedal_riff": [[(0.0, "root"), (0.5, "root"), (1.0, "root_hi"), (1.5, "root"),
                    (2.0, "root"), (2.5, "root"), (3.0, "root_hi"), (3.5, "root")]],
}
_ALT_P = 0.35   # probabilita' (x variabilita') che un accordo usi un disegno alternativo


def _bar_picker(style: str, pattern: dict, variant: bool, variability: float,
                rng: random.Random):
    """Scelta del disegno battuta per battuta (per _pattern_events): con la
    variabilita', ogni battuta dell'accordo puo' usare uno dei disegni
    alternativi dello stile invece di quello base (mai al posto della
    variante, che ha gia' il suo ritmo). None = sempre il disegno base. Il
    generatore casuale si consulta solo con variabilita' > 0: a variabilita'
    0 il risultato non dipende dal seme."""
    alts = pattern.get("alts") or PATTERN_ALTS.get(style)
    if variant or not alts or variability <= 0:
        return None
    chosen = {}

    def bar_for(k):
        if k not in chosen:
            chosen[k] = rng.choice(alts) if rng.random() < _ALT_P * variability else pattern["bar"]
        return chosen[k]
    return bar_for


# Variabilita' "che aggiunge" (oltre a quella che toglie, vedi _vary_events):
_PASSING_P = 0.45      # (x variabilita') basso/riff: nota di passaggio verso l'accordo successivo
_ANTICIPATE_P = 0.30   # (x variabilita') l'accordo successivo anticipa di un ottavo (sincope)
_PASSING_ROLES = tuple(_APPROACH_STEPS)


def _add_passing_note(starts: list, total_units: int, next_root_pc: Optional[int],
                      variability: float, rng: random.Random) -> list:
    """Basso e riff: con la variabilita', a fine accordo una nota di
    passaggio verso la fondamentale dell'accordo successivo (vedi
    _APPROACH_STEPS). Se l'ultima nota dura almeno due unita' la nota si
    aggiunge nella sua ultima unita' (una nota in piu'), altrimenti prende
    il posto dell'ultima nota (mai della prima che suona, ne' di una pausa
    del disegno)."""
    if next_root_pc is None or not starts or rng.random() >= _PASSING_P * variability:
        return starts
    role = rng.choice(_PASSING_ROLES)
    last_u, last_role = starts[-1]
    if last_role == "rest" or last_role in _PASSING_ROLES:
        return starts
    if total_units - last_u >= 2:
        return starts + [(total_units - 1, role)]
    first_sound = next(i for i, (_u, r) in enumerate(starts) if r != "rest")
    if len(starts) - 1 > first_sound:
        return starts[:-1] + [(last_u, role)]
    return starts


def _line_events(chords: List[ChordSpan], unit: float, span_starts, variability: float,
                 rng: random.Random, anticipate: bool) -> Tuple[list, int]:
    """Gli attacchi di tutta la linea (basso, accompagnamento, riff) come
    [(unita' assoluta, ruolo, accordo, fondamentale successiva), ...] e
    l'unita' di fine. 'span_starts(idx, span, next_root, total_units, level)'
    da' gli attacchi di un accordo in unita' relative. I buchi fra accordi
    diventano pause.

    Con 'anticipate' e variabilita' > 0, a un cambio d'accordo il primo
    attacco dell'accordo successivo puo' arrivare un'unita' (un ottavo)
    prima, legato oltre il cambio: la sincope tipica di pop, rock e latin."""
    blocks = []
    cursor_u = 0
    for idx, span in enumerate(chords):
        start_u, end_u = _span_units(span, unit)
        start_u = max(start_u, cursor_u)
        end_u = max(end_u, start_u + 1)
        next_root = chords[idx + 1].root_pc if idx + 1 < len(chords) else None
        starts = [(u, role, span, next_root)
                  for u, role in span_starts(idx, span, next_root, end_u - start_u)]
        blocks.append([start_u, end_u, cursor_u, starts])
        cursor_u = end_u

    if anticipate and variability > 0:
        for a, b in zip(blocks, blocks[1:]):
            total = a[1] - a[0]
            if b[0] != a[1] or total < 2 or not b[3] or b[3][0][0] != 0 or b[3][0][1] == "rest":
                continue
            kept = [ev for ev in a[3] if ev[0] < total - 1]
            if not any(ev[1] != "rest" for ev in kept) or rng.random() >= _ANTICIPATE_P * variability:
                continue
            _u, role, span, next_root = b[3][0]
            a[3] = kept + [(total - 1, role, span, next_root)]
            b[3] = b[3][1:]   # l'attacco anticipato continua oltre il cambio d'accordo

    line = []
    for start_u, _end_u, gap_from, starts in blocks:
        if start_u > gap_from:
            line.append((gap_from, "rest", None, None))
        line.extend((start_u + u, role, span, next_root) for u, role, span, next_root in starts)
    return line, (blocks[-1][1] if blocks else 0)


def _emit_line(line: list, end_u: int, render, velocity_at=None) -> List[str]:
    """Token di una linea (vedi _line_events): ogni attacco dura fino al
    successivo; 'render(ruolo, accordo, fondamentale successiva)' da' il
    corpo del token (None = pausa), preceduto dal moltiplicatore di durata.
    'velocity_at(unita')', se dato, da' la velocity di ogni attacco: si
    scrive 'N@' solo quando cambia."""
    tokens = []
    current_velocity = None
    for i, (u, role, span, next_root) in enumerate(line):
        mult = (line[i + 1][0] if i + 1 < len(line) else end_u) - u
        body = None if role == "rest" else render(role, span, next_root)
        if body is None:
            tokens.append(f"{mult}r" if mult > 1 else "r")
            continue
        if velocity_at is not None:
            velocity = velocity_at(u)
            if velocity != current_velocity:
                tokens.append(f"{velocity}@")
                current_velocity = velocity
        tokens.append((f"{mult}" if mult > 1 else "") + body)
    return tokens


_LINE_VELOCITY = 88   # velocity di base di basso/accompagnamento/riff con la dinamica


def _line_velocity(unit: float, bar_beats: float, amount: float, rng: random.Random):
    """Velocity degli attacchi con la dinamica (vedi _emit_line): accento
    sul primo tempo della battuta, un po' sui tempi, meno sui levare, piu'
    una piccola oscillazione; tutto in proporzione a 'amount'."""
    def velocity_at(u: int) -> int:
        pos = (u * unit) % bar_beats
        accent = 14 if abs(pos) < 1e-6 else 4 if abs(pos - round(pos)) < 1e-6 else -8
        return max(1, min(127, _LINE_VELOCITY + round(amount * (accent + rng.randint(-8, 8)))))
    return velocity_at


def _apply_line_intensity(events: list, level: str, fuller_chords: bool, octave_lift: bool) -> list:
    """Intensita' di basso/accompagnamento/riff (vedi INTENSITIES).
    'light': restano il primo attacco, le pause del disegno e gli attacchi
    sul 1 e sul 3 (le note rimaste durano di piu'); 'full': gli accordi
    prendono anche l'ottava sopra ('fuller_chords') e il basso sale d'ottava
    sull'ultimo attacco dell'accordo ('octave_lift')."""
    if level == "light":
        first_sound = next((i for i, (_t, role) in enumerate(events) if role != "rest"), 0)
        kept = [(t, role) for i, (t, role) in enumerate(events)
                if i <= first_sound or role == "rest" or abs(t % 2.0) < 1e-6]
        # niente pause di fila: la seconda allungherebbe solo il silenzio
        out = []
        for t, role in kept:
            if role == "rest" and out and out[-1][1] == "rest":
                continue
            out.append((t, role))
        return out
    if level == "full":
        out = []
        for t, role in events:
            if fuller_chords and isinstance(role, list) and "root_hi" not in role:
                role = role + ["root_hi"]
            out.append((t, role))
        if octave_lift and len(out) >= 3:
            t, role = out[-1]
            if role == "root":
                out[-1] = (t, "root_hi")
            elif isinstance(role, tuple) and role == out[0][1] and role[1] == 0:
                out[-1] = (t, (role[0], 1))   # stili storici: (classe di altezza, ottava)
        return out
    return events


def _line_level(intensity: str, idx: int, count: int) -> str:
    if intensity not in INTENSITIES:
        raise ValueError(tr("Intensita' sconosciuta: '{intensity}' (valide: {0})", ', '.join(INTENSITIES), intensity=intensity))
    return _intensity_at(intensity, idx, count)


def generate_bass_from_chords(chords: List[ChordSpan], style: str, octave: int = 2,
                               variation_every: int = 4, min_total_beats: float = 0.0,
                               variability=0.0, seed: Optional[int] = None,
                               bar_beats: float = BEATS_PER_BAR, intensity: str = "normal") -> str:
    """Genera una linea di basso che segue 'chords' (vedi
    extract_chords_from_track), nello stile scelto (vedi BASS_STYLES),
    all'ottava indicata. Ogni 'variation_every' accordi (0 disabilita le
    variazioni) usa un trattamento leggermente diverso dello stesso accordo
    invece di ripetere identico il disegno - vedi _bass_notes_for_span e
    BASS_PATTERNS. Ogni stile scrive la sua griglia ('4:', '8:' o '8T:').
    Se 'min_total_beats' e' dato e supera la durata di 'chords', la
    progressione viene ripetuta ciclicamente (vedi _expand_chords_to_cover)
    finche' non la raggiunge, cosi' il basso copre l'intera estensione delle
    altre tracce del progetto invece di fermarsi alla fine della sola
    traccia di accordi sorgente.

    'variability' (0-1, 0 = nessuna: sempre lo stesso risultato) varia il
    disegno con un generatore casuale inizializzato con 'seed' (stesso seme =
    stesso testo; None = seme casuale): il trattamento alternativo (note di
    avvicinamento, terza/settima...) scatta anche fuori dal ritmo di
    'variation_every', e le note non iniziali di un accordo possono
    allungarsi, tacere o salire d'ottava. 'variability' puo' anche essere
    una Variability (ritmo, note, dinamica: con la dinamica le note hanno
    accenti e velocity diverse). 'style' puo' essere uno stile personale
    'user:<nome>' (vedi core.user_styles). Solleva ValueError se 'chords'
    e' vuota o lo stile non e' valido."""
    if not chords:
        raise ValueError(tr("Nessun accordo da seguire: la traccia sorgente non ne contiene."))
    user = user_styles.get_user_style("bass", style)
    if style not in BASS_STYLES and user is None:
        raise ValueError(tr("Stile di basso sconosciuto: '{style}' (validi: {0})", ', '.join(BASS_STYLES), style=style))
    chords = _expand_chords_to_cover(chords, min_total_beats)
    amount = _variability(variability)
    rng = random.Random(seed)

    pattern = user or BASS_PATTERNS.get(style)
    grid = pattern["grid"] if pattern else "4:"  # gli stili storici: un attacco per quarto
    unit = _GRID_UNIT_BEATS[grid]
    _line_level(intensity, 0, 1)   # intensita' valida?

    def span_starts(idx, span, next_root, total_units):
        level = _line_level(intensity, idx, len(chords))
        variant = variation_every > 0 and (idx + 1) % variation_every == 0
        if amount.notes > 0 and rng.random() < _VARY_VARIANT_P * amount.notes:
            variant = True  # il trattamento alternativo scatta anche fuori dal ritmo fisso
        if pattern:
            events = _pattern_events(pattern, span, variant, bar_beats,
                                     _bar_picker(style, pattern, variant, amount.rhythm, rng))
        else:
            events = _legacy_events(span, style, octave, variant, next_root)
        events = _apply_line_intensity(events, level, fuller_chords=False, octave_lift=True)
        starts = _quantize_starts(events, unit, total_units, amount, rng, octave_jumps=True)
        if amount.notes > 0 and level != "light":
            starts = _add_passing_note(starts, total_units, next_root, amount.notes, rng)
        return starts

    def render(role, span, next_root):
        resolved = _resolve_role(role, span, next_root)
        return None if resolved is None else _note_token(resolved[0], octave + resolved[1])

    line, end_u = _line_events(chords, unit, span_starts, amount.rhythm, rng,
                               anticipate=unit <= 0.5 and intensity != "light")
    velocity_at = _line_velocity(unit, bar_beats, amount.dynamics, rng) if amount.dynamics > 0 else None
    return " ".join([grid] + _emit_line(line, end_u, render, velocity_at))


# ---------------------------------------------------------------------------
# Melodia (strumenti monofonici) e accompagnamento (strumenti polifonici)
# ---------------------------------------------------------------------------

# Come BASS_PATTERNS (stesso formato bar/variant/tile, vedi il commento
# sopra), con una differenza: il ruolo di un attacco puo' essere una LISTA di
# nomi (invece di un singolo nome/tupla) per suonare piu' note dell'accordo
# insieme (accompagnamento) - vedi _resolve_roles e generate_melodic_line.
# 'polyphonic' seleziona il vocabolario giusto per lo strumento di
# destinazione (vedi generate_melodic_line/COMPING_STYLES/RIFF_STYLES) ed e'
# solo un controllo di compatibilita', non influenza la generazione.
MELODIC_PATTERNS: Dict[str, dict] = {
    # --- Accompagnamento (chitarra, piano, organo, archi/pad, ensemble...) ---
    # Accordo battuto sul 1 e sul 3 (comping semplice, stile chitarra/piano).
    "block_chords": {"grid": "4:", "polyphonic": True,
                      "bar": [(0.0, ["root", "third", "fifth"]), (2.0, ["root", "third", "fifth"])],
                      "variant": [(0.0, ["root", "third", "fifth"]), (2.0, ["root", "third", "seventh"])]},
    # Note dell'accordo in sequenza ascendente, in ottavi (arpeggio classico).
    "arpeggio_up": {"grid": "8:",
                     "bar": [(0.0, "root"), (0.5, "third"), (1.0, "fifth"), (1.5, "root_hi"),
                             (2.0, "root"), (2.5, "third"), (3.0, "fifth"), (3.5, "root_hi")],
                     "variant": [(0.0, "root"), (0.5, "third"), (1.0, "fifth"), (1.5, "seventh"),
                                 (2.0, "root"), (2.5, "fifth"), (3.0, "third"), (3.5, "root_hi")],
                     "polyphonic": True},
    # Basso-alto alternati (stile Alberti): fondamentale sola, poi terza+quinta.
    "broken_chord": {"grid": "8:", "polyphonic": True, "variant": None,
                      "bar": [(0.0, "root"), (0.5, ["third", "fifth"]), (1.0, "root_hi"), (1.5, ["third", "fifth"]),
                              (2.0, "root"), (2.5, ["third", "fifth"]), (3.0, "root_hi"), (3.5, ["third", "fifth"])]},
    # Un solo accordo lungo per l'intera durata (pad, archi, organo sostenuto).
    "sustained": {"grid": "4:", "polyphonic": True, "tile": False,
                  "bar": [(0.0, ["root", "third", "fifth"])],
                  "variant": [(0.0, ["root", "third", "seventh"])]},
    # Montuno latin/piano: ottavi sincopati a due note.
    "montuno": {"grid": "8:", "polyphonic": True,
                "bar": [(0.0, ["root", "fifth"]), (1.0, ["third", "fifth"]), (1.5, ["root_hi", "third"]),
                        (2.5, ["root", "fifth"]), (3.0, ["third", "fifth"]), (3.5, ["root_hi", "third"])],
                "variant": [(0.0, ["root", "fifth"]), (1.0, ["third", "seventh"]), (1.5, ["root_hi", "third"]),
                            (2.5, ["root", "fifth"]), (3.0, ["third", "seventh"]), (3.5, ["root_hi", "third"])]},
    # Skank reggae/ska: accordo solo in levare (il "e" di ogni beat), come
    # chitarra/tastiera offbeat - vedi reggae_skank fra i RIFF_STYLES.
    "skank_chords": {"grid": "8:", "polyphonic": True,
                     "bar": [(0.5, ["root", "third", "fifth"]), (1.5, ["root", "third", "fifth"]),
                             (2.5, ["root", "third", "fifth"]), (3.5, ["root", "third", "fifth"])],
                     "variant": [(0.5, ["root", "third", "fifth"]), (1.5, ["root", "third", "seventh"]),
                                 (2.5, ["root", "third", "fifth"]), (3.5, ["root", "third", "seventh"])]},
    # Accordo su ogni quarto (comping semplice e regolare: pop/rock).
    "quarter_chords": {"grid": "4:", "polyphonic": True,
                       "bar": [(0.0, ["root", "third", "fifth"]), (1.0, ["root", "third", "fifth"]),
                               (2.0, ["root", "third", "fifth"]), (3.0, ["root", "third", "fifth"])],
                       "variant": [(0.0, ["root", "third", "fifth"]), (1.0, ["root", "third", "fifth"]),
                                   (2.0, ["root", "third", "fifth"]), (3.0, ["root", "third", "seventh"])]},
    # Bossa nova: accordo su 1, sul "e" del 2, sul 3 e sul "e" del 4 - stesso
    # profilo ritmico del basso "bossa" gia' esistente, per coerenza fra le parti.
    "bossa_comp": {"grid": "8:", "polyphonic": True,
                   "bar": [(0.0, ["root", "third", "fifth"]), (1.5, ["root", "third", "fifth"]),
                           (2.0, ["root", "third", "fifth"]), (3.5, ["root", "third", "fifth"])],
                   "variant": [(0.0, ["root", "third", "seventh"]), (1.5, ["root", "third", "fifth"]),
                               (2.0, ["root", "third", "seventh"]), (3.5, ["root", "third", "fifth"])]},
    # Stop-time funk: due colpi brevi e staccati (mezzo ottavo ciascuno),
    # silenzio nel resto della battuta - punteggiatura della sezione ritmica,
    # non un giro continuo.
    "waltz_comp": {"grid": "4:", "polyphonic": True,
                   "bar": [(0.0, "rest"), (1.0, ["root", "third", "fifth"]), (2.0, ["root", "third", "fifth"])],
                   "variant": [(0.0, "rest"), (1.0, ["root", "third", "fifth"]), (2.0, ["third", "fifth", "seventh"])]},
    "arpeggio_68": {"grid": "8:", "polyphonic": True,
                    "bar": [(0.0, "root"), (0.5, "fifth"), (1.0, "root_hi"), (1.5, "third"), (2.0, "fifth"), (2.5, "third")],
                    "variant": [(0.0, "root"), (0.5, "fifth"), (1.0, "seventh"), (1.5, "third"), (2.0, "fifth"), (2.5, "root_hi")]},
    "funk_stab": {"grid": "8:", "polyphonic": True,
                  "bar": [(0.0, ["root", "third", "fifth"]), (0.5, "rest"),
                          (2.5, ["root", "third", "fifth"]), (3.0, "rest")],
                  "variant": [(0.0, ["root", "third", "seventh"]), (0.5, "rest"),
                              (2.5, ["root", "third", "fifth"]), (3.0, "rest")]},

    # --- Melodia/riff (fiati, ottoni, archi soli, synth lead...) ---
    # Motivo breve sulle note dell'accordo, ripetuto a ogni accordo.
    "riff_short": {"grid": "8:", "polyphonic": False,
                   "bar": [(0.0, "root"), (0.5, "third"), (1.0, "fifth"), (2.0, "root_hi"), (3.0, "fifth")],
                   "variant": [(0.0, "root"), (0.5, "fifth"), (1.0, "third"), (2.0, "root_hi"), (3.0, "third")]},
    # Frase nella prima meta' della battuta, silenzio nella seconda ("botta e risposta").
    "call_response": {"grid": "8:", "polyphonic": False,
                       "bar": [(0.0, "root"), (0.5, "third"), (1.0, "fifth"), (1.5, "root_hi"), (2.0, "rest")],
                       "variant": [(0.0, "fifth"), (0.5, "third"), (1.0, "root"), (2.0, "rest")]},
    # Melodia lunga sulle note guida (terza/settima): jazz, ballad.
    "guide_tones": {"grid": "4:", "polyphonic": False,
                     "bar": [(0.0, "third"), (2.0, "seventh")],
                     "variant": [(0.0, "seventh"), (2.0, "third")]},
    # Passaggio scalare (note dell'accordo) verso l'accordo successivo.
    "scale_run": {"grid": "8:", "polyphonic": False,
                  "bar": [(0.0, "root"), (0.5, "third"), (1.0, "fifth"), (1.5, "seventh"),
                          (2.0, "root_hi"), (3.0, "fifth"), (3.5, "approach")],
                  "variant": [(0.0, "fifth"), (0.5, "third"), (1.0, "root"), (2.0, "third"),
                              (3.0, "fifth"), (3.5, "approach")]},
    # Lick blues a terzine, stile chorus/sax/armonica.
    "blues_lick": {"grid": "8T:", "polyphonic": False,
                   "bar": [(0.0, "root"), (2 * _T, "flat7"), (1.0, "fifth"), (1 + 2 * _T, "flat7"),
                           (2.0, "third"), (2 + 2 * _T, "root"), (3.0, "fifth"), (3 + 2 * _T, "approach")],
                   "variant": [(0.0, "flat7"), (2 * _T, "fifth"), (1.0, "third"), (1 + 2 * _T, "root"),
                               (2.0, "fifth"), (2 + 2 * _T, "flat7"), (3.0, "root"), (3 + 2 * _T, "approach")]},
    # Arpeggio su e giu' (salita poi discesa sulle note dell'accordo).
    "arpeggio_updown": {"grid": "8:", "polyphonic": False,
                        "bar": [(0.0, "root"), (0.5, "third"), (1.0, "fifth"), (1.5, "root_hi"),
                                (2.0, "fifth"), (2.5, "third"), (3.0, "root"), (3.5, "approach")],
                        "variant": [(0.0, "root"), (0.5, "fifth"), (1.0, "third"), (1.5, "root_hi"),
                                    (2.0, "third"), (2.5, "fifth"), (3.0, "root"), (3.5, "approach")]},
    # Skank reggae/ska: solo in levare (il "e" di ogni beat), come fiati/chitarra offbeat.
    "reggae_skank": {"grid": "8:", "polyphonic": False,
                     "bar": [(0.5, "third"), (1.5, "fifth"), (2.5, "third"), (3.5, "root_hi")],
                     "variant": [(0.5, "fifth"), (1.5, "third"), (2.5, "root_hi"), (3.5, "fifth")]},
    # Nota ribattuta (drone ritmico sotto l'armonia che cambia: rock/minimalista).
    "pedal_riff": {"grid": "8:", "polyphonic": False,
                   "bar": [(0.5 * i, "root") for i in range(8)],
                   "variant": [(0.5 * i, "root") for i in range(6)] + [(3.0, "fifth"), (3.5, "root")]},
    # Una sola nota lunga per accordo (melodia sostenuta: ballad, sezione fiati).
    "held_note": {"grid": "4:", "polyphonic": False, "tile": False,
                  "bar": [(0.0, "root")], "variant": [(0.0, "fifth")]},
}

# Melodie a frasi (vedi core.melody_generate): forma come [(frase, cadenza)]
# ('open' = domanda, 'closed' = risposta sulla tonica), densita' ritmica di A
# e di B (0 calma, 1 media, 2 mossa), altezza dell'arco e quanto sale B, in
# semitoni. Strumenti monofonici: sono fra i RIFF_STYLES.
MELODY_STYLES: Dict[str, dict] = {
    "melody_aaba": {"form": [("A", "open"), ("A'", "closed"), ("B", "open"), ("A", "closed")],
                    "density": 1, "b_density": 2, "height": 5, "b_lift": 3},
    "melody_period": {"form": [("A", "open"), ("A'", "closed")],
                      "density": 1, "b_density": 2, "height": 5, "b_lift": 3},
    "melody_ballad": {"form": [("A", "open"), ("A'", "closed"), ("B", "open"), ("A", "closed")],
                      "density": 0, "b_density": 1, "height": 4, "b_lift": 4},
    "melody_lively": {"form": [("A", "open"), ("A'", "closed"), ("B", "open"), ("A", "closed")],
                      "density": 2, "b_density": 1, "height": 6, "b_lift": 3},
}

COMPING_STYLES = tuple(name for name, p in MELODIC_PATTERNS.items() if p["polyphonic"])
RIFF_STYLES = tuple(name for name, p in MELODIC_PATTERNS.items() if not p["polyphonic"]) + tuple(MELODY_STYLES)


def _resolve_roles(role, span: ChordSpan, next_root_pc: Optional[int]) -> List[Tuple[int, int]]:
    """Come _resolve_role, ma 'role' puo' essere anche una lista di nomi (le
    note simultanee di un accordo di accompagnamento, vedi MELODIC_PATTERNS):
    risolve ciascun nome e scarta le pause. Un nome singolo (str o tupla
    pre-risolta) si comporta come _resolve_role."""
    names = role if isinstance(role, list) else [role]
    resolved = (_resolve_role(name, span, next_root_pc) for name in names)
    return [r for r in resolved if r is not None]


def generate_melodic_line(chords: List[ChordSpan], style: str, octave: int,
                           range_low: int, range_high: int, polyphonic: bool,
                           variation_every: int = 4, min_total_beats: float = 0.0,
                           variability=0.0, seed: Optional[int] = None,
                           bar_beats: float = BEATS_PER_BAR, intensity: str = "normal",
                           voice_leading: bool = False, key: Optional[str] = None,
                           meter: Optional[str] = None) -> str:
    """Genera una linea melodica (strumenti monofonici, vedi RIFF_STYLES) o un
    accompagnamento (strumenti polifonici, vedi COMPING_STYLES) che segue
    'chords' (vedi extract_chords_from_track), nello stile scelto -
    interfaccia e comportamento di variation_every/min_total_beats/
    variability/seed identici a generate_bass_from_chords. A differenza del
    basso, le altezze generate vengono riportate nel registro
    [range_low, range_high] dello strumento di destinazione (spostandole di
    ottava intera): 'octave' e' solo il punto di partenza, non basta
    da solo a restare nell'estensione di uno strumento qualsiasi. Solleva
    ValueError se 'chords' e' vuota, lo stile non esiste, o non e'
    compatibile con 'polyphonic' (es. uno stile di RIFF_STYLES scelto per
    una traccia polifonica).

    Con 'voice_leading' gli accordi di tre o piu' note (accompagnamento)
    scelgono il rivolto piu' vicino all'accordo precedente (vedi
    _voice_lead), invece di stare sempre in posizione fondamentale e
    saltare da una posizione all'altra.

    Gli stili di MELODY_STYLES scrivono una vera melodia a frasi (vedi
    core.melody_generate) nella tonalita' 'key' (None = ricavata dagli
    accordi) e nella metrica 'meter' (per le metriche composte, 6/8...);
    'variation_every' e 'voice_leading' non li riguardano."""
    if not chords:
        raise ValueError(tr("Nessun accordo da seguire: la traccia sorgente non ne contiene."))
    if style in MELODY_STYLES:
        if polyphonic:
            raise ValueError(tr("Lo stile '{style}' e' per strumenti monofonici.", style=style))
        from .melody_generate import generate_phrase_melody   # import locale: evita il ciclo
        return generate_phrase_melody(chords, style, octave, range_low, range_high, key=key,
                                      min_total_beats=min_total_beats, variability=variability, seed=seed,
                                      bar_beats=bar_beats, meter=meter, intensity=intensity)
    pattern = (MELODIC_PATTERNS.get(style) or user_styles.get_user_style("comping", style)
               or user_styles.get_user_style("riff", style))
    if pattern is None:
        raise ValueError(tr("Stile melodico sconosciuto: '{style}' (validi: {0})", ', '.join(MELODIC_PATTERNS), style=style))
    if pattern["polyphonic"] != polyphonic:
        wanted = "polifonici" if pattern["polyphonic"] else "monofonici"
        raise ValueError(tr("Lo stile '{style}' e' per strumenti {wanted}.", style=style, wanted=wanted))

    chords = _expand_chords_to_cover(chords, min_total_beats)
    amount = _variability(variability)
    rng = random.Random(seed)

    unit = _GRID_UNIT_BEATS[pattern["grid"]]
    _line_level(intensity, 0, 1)   # intensita' valida?

    def span_starts(idx, span, next_root, total_units):
        level = _line_level(intensity, idx, len(chords))
        variant = variation_every > 0 and (idx + 1) % variation_every == 0
        if amount.notes > 0 and rng.random() < _VARY_VARIANT_P * amount.notes:
            variant = True
        events = _pattern_events(pattern, span, variant, bar_beats,
                                 _bar_picker(style, pattern, variant, amount.rhythm, rng))
        events = _apply_line_intensity(events, level, fuller_chords=polyphonic, octave_lift=False)
        starts = _quantize_starts(events, unit, total_units, amount, rng, octave_jumps=False)
        if amount.notes > 0 and not polyphonic and level != "light":
            starts = _add_passing_note(starts, total_units, next_root, amount.notes, rng)
        return starts

    def octave_in_range(pc: int, octave_offset: int) -> int:
        midi = midi_note(pc, octave + octave_offset)
        while midi < range_low and midi + 12 <= range_high:
            midi += 12
        while midi > range_high and midi - 12 >= range_low:
            midi -= 12
        return midi

    voicing = {"prev": None, "anchor": None}

    def render(role, span, next_root):
        resolved = _resolve_roles(role, span, next_root)
        if not resolved:
            return None
        notes = [octave_in_range(pc, off) for pc, off in resolved]
        if voice_leading and len({n % 12 for n in notes}) >= 3:
            if voicing["prev"] is None:
                voicing["anchor"] = sum(notes) / len(notes)   # il primo accordo resta com'e'
            else:
                notes = _voice_lead([pc for pc, _off in resolved], voicing["prev"],
                                    range_low, range_high, voicing["anchor"]) or notes
            voicing["prev"] = sorted(notes)
        tokens = [_note_token(n % 12, n // 12 - 1) for n in notes]
        return tokens[0] if len(tokens) == 1 else "[" + " ".join(tokens) + "]"

    line, end_u = _line_events(chords, unit, span_starts, amount.rhythm, rng,
                               anticipate=unit <= 0.5 and intensity != "light")
    velocity_at = _line_velocity(unit, bar_beats, amount.dynamics, rng) if amount.dynamics > 0 else None
    return " ".join([pattern["grid"]] + _emit_line(line, end_u, render, velocity_at))


def _voice_lead(pcs: List[int], prev: List[int], low: int, high: int, anchor: float) -> Optional[List[int]]:
    """Il rivolto dell'accordo 'pcs' (classi di altezza; i doppioni, come
    l'ottava sopra dell'intensita' piena, diventano l'ottava della nota piu'
    bassa) in posizione stretta dentro [low, high] che si muove di meno
    rispetto all'accordo precedente 'prev' (note MIDI), senza allontanarsi
    troppo dal registro di partenza 'anchor'. None se nessun rivolto entra
    nell'estensione."""
    distinct = list(dict.fromkeys(pcs))
    extra = len(pcs) - len(distinct)
    candidates = []
    for k in range(len(distinct)):
        order = distinct[k:] + distinct[:k]
        for base_octave in range(-1, 10):
            notes = [midi_note(order[0], base_octave)]
            for pc in order[1:]:
                notes.append(notes[-1] + ((pc - notes[-1]) % 12 or 12))
            notes += [notes[j] + 12 for j in range(extra)]
            if notes[0] >= low and max(notes) <= high:
                candidates.append(sorted(notes))
    if not candidates:
        return None

    def cost(chord):
        movement = (sum(min(abs(x - y) for y in prev) for x in chord)
                    + sum(min(abs(x - y) for x in chord) for y in prev))
        return movement + 0.5 * abs(sum(chord) / len(chord) - anchor)
    return min(candidates, key=cost)


# ---------------------------------------------------------------------------
# Giro armonico: la progressione di accordi da cui partire quando il brano
# non ne ha ancora una (basso e accompagnamento hanno bisogno di accordi da
# seguire). Scrive simboli di accordo (Am7, G...) che il motore voca da solo
# per lo strumento della traccia.
# ---------------------------------------------------------------------------

# Ogni stile: modo della tonalita' e sequenza di accordi come (semitoni sopra
# la tonica, qualita' di core.chords.CHORD_QUALITIES, durata in battute).
# Progressioni generiche di genere, come i pattern di batteria qui sopra.
PROGRESSION_STYLES: Dict[str, dict] = {
    "pop": {"mode": "major", "chords": [(0, "", 1), (7, "", 1), (9, "m", 1), (5, "", 1)]},        # I-V-vi-IV
    "doo_wop": {"mode": "major", "chords": [(0, "", 1), (9, "m", 1), (5, "", 1), (7, "", 1)]},    # I-vi-IV-V
    "rock": {"mode": "major", "chords": [(0, "", 1), (5, "", 1), (0, "", 1), (7, "", 1)]},       # I-IV-I-V
    "canon": {"mode": "major", "chords": [(0, "", 1), (7, "", 1), (9, "m", 1), (4, "m", 1),     # Pachelbel
                                          (5, "", 1), (0, "", 1), (5, "", 1), (7, "", 1)]},
    "blues_12": {"mode": "major", "chords": [(0, "7", 4), (5, "7", 2), (0, "7", 2),
                                             (7, "7", 1), (5, "7", 1), (0, "7", 1), (7, "7", 1)]},
    "jazz_251": {"mode": "major", "chords": [(2, "m7", 1), (7, "7", 1), (0, "maj7", 2)]},
    "turnaround": {"mode": "major", "chords": [(0, "maj7", 1), (9, "m7", 1), (2, "m7", 1), (7, "7", 1)]},
    "minor_pop": {"mode": "minor", "chords": [(0, "m", 1), (8, "", 1), (3, "", 1), (10, "", 1)]},  # i-VI-III-VII
    "andalusian": {"mode": "minor", "chords": [(0, "m", 1), (10, "", 1), (8, "", 1), (7, "", 1)]},  # i-VII-VI-V
    "minor_rock": {"mode": "minor", "chords": [(0, "m", 1), (10, "", 1), (8, "", 1), (10, "", 1)]},  # i-VII-VI-VII
    "minor_cadence": {"mode": "minor", "chords": [(0, "m", 1), (5, "m", 1), (0, "m", 1), (7, "7", 1)]},  # i-iv-i-V7
    "minor_251": {"mode": "minor", "chords": [(2, "m7b5", 1), (7, "7", 1), (0, "m7", 2)]},
    "minor_blues_12": {"mode": "minor", "chords": [(0, "m7", 4), (5, "m7", 2), (0, "m7", 2),
                                                   (8, "7", 1), (7, "7", 1), (0, "m7", 1), (7, "7", 1)]},
    # --- aggiunte: maggiore ---
    "three_chord": {"mode": "major", "chords": [(0, "", 1), (5, "", 1), (7, "", 1), (0, "", 1)]},      # I-IV-V-I
    "ballad": {"mode": "major", "chords": [(0, "", 1), (4, "m", 1), (5, "", 1), (7, "", 1)]},          # I-iii-IV-V
    "royal_road": {"mode": "major", "chords": [(5, "maj7", 1), (7, "7", 1), (4, "m7", 1), (9, "m", 1),  # IV-V-iii-vi
                                               (2, "m7", 1), (7, "7", 1), (0, "maj7", 2)]},                  # ii-V-I
    "mixolydian": {"mode": "major", "flats": True, "chords": [(0, "", 1), (10, "", 1), (5, "", 1), (0, "", 1)]},      # I-bVII-IV-I
    "gospel": {"mode": "major", "chords": [(0, "", 1), (0, "7", 1), (5, "", 1), (5, "m", 1)]},        # I-I7-IV-iv
    "circle": {"mode": "major", "chords": [(0, "maj7", 1), (5, "maj7", 1), (11, "m7b5", 1), (4, "m7", 1),
                                           (9, "m7", 1), (2, "m7", 1), (7, "7", 1), (0, "maj7", 1)]},
    "rhythm_changes": {"mode": "major", "chords": [(0, "maj7", Fraction(1, 2)), (9, "m7", Fraction(1, 2)),
                                                   (2, "m7", Fraction(1, 2)), (7, "7", Fraction(1, 2)),
                                                   (4, "m7", Fraction(1, 2)), (9, "7", Fraction(1, 2)),
                                                   (2, "m7", Fraction(1, 2)), (7, "7", Fraction(1, 2))]},
    "jazz_blues": {"mode": "major", "chords": [(0, "7", 1), (5, "7", 1), (0, "7", 2), (5, "7", 2), (0, "7", 1),
                                               (9, "7", 1), (2, "m7", 1), (7, "7", 1), (0, "7", 1), (7, "7", 1)]},
    # --- aggiunte: minore ---
    "minor_three": {"mode": "minor", "chords": [(0, "m", 1), (5, "m", 1), (7, "m", 1), (0, "m", 1)]},  # i-iv-v-i
    "minor_epic": {"mode": "minor", "chords": [(0, "m", 1), (8, "", 1), (10, "", 1), (0, "m", 1)]},    # i-VI-VII-i
    "dorian_vamp": {"mode": "minor", "chords": [(0, "m7", 2), (5, "7", 2)]},                           # i7-IV7
    "line_cliche": {"mode": "minor", "chords": [(0, "m", 1), (0, "mMaj7", 1), (0, "m7", 1), (0, "m6", 1)]},
    "minor_circle": {"mode": "minor", "chords": [(0, "m7", 1), (5, "m7", 1), (10, "7", 1), (3, "maj7", 1),
                                                 (8, "maj7", 1), (2, "m7b5", 1), (7, "7", 1), (0, "m7", 1)]},
    "phrygian": {"mode": "minor", "flats": True, "chords": [(0, "m", 2), (1, "", 2)]},                                 # i-bII
}

# Con la variabilita', un accordo puo' "colorarsi" (settima, nona, sus...)
# restando della stessa funzione; la triade maggiore sul quinto grado diventa
# una dominante.
_CHORD_COLORS = {
    "": ["maj7", "add9", "6", "sus2"],
    "m": ["m7", "m9"],
    "7": ["9", "13", "7sus4"],
    "m7": ["m9"],
    "maj7": ["maj9", "6"],
}
_DOMINANT_COLORS = ["7", "9", "7sus4"]
_COLOR_P = 0.5

# Armonia piu' ricca (con la variabilita'): probabilita' moltiplicate per
# 'variability', vedi _enrich_harmony.
_SECONDARY_P = 0.35   # dominante secondaria (o II-V) verso l'accordo successivo
_TRITONE_P = 0.40     # una dominante che scende di quinta -> sostituto di tritono (bII7)
_MINOR_IV_P = 0.50    # in maggiore, il IV prima del I prende in prestito la iv minore
_DOMINANTS = ("7", "9", "13")
_NOT_TARGETS = ("m7b5", "dim", "dim7")
# Gradi (semitoni sopra la tonica) che si preparano con la loro dominante:
# in maggiore I, ii, iii, IV, V, vi; in minore i, III, iv, v/V, VI.
_TONICIZABLE = {"major": (0, 2, 4, 5, 7, 9), "minor": (0, 3, 5, 7, 8)}

# Cadenze finali (vedi _final_cadence): (semitoni sopra la tonica, qualita',
# accordo cromatico da scrivere in bemolle). La prima e' quella usata senza
# variabilita'; le altre sono le alternative.
_CADENCES = {
    "major": [(7, "7", False),       # autentica: V7 - I
              (5, "", False),        # plagale: IV - I ("amen")
              (5, "m6", False),      # plagale minore: iv - I
              (10, "7", True),       # "backdoor": bVII7 - I
              (7, "7sus4", False)],  # V7sus4 - I
    "minor": [(7, "7", False),       # V7 - i
              (5, "m", False),       # iv - i
              (10, "", False)],      # VII - i (eolia)
}
# I giri che non partono dalla tonica (II-V-I, royal road) la affermano solo
# con la dominante: per loro la cadenza e' V7 o il suo sostituto di tritono.
_AUTHENTIC_CADENCES = [(7, "7", False), (1, "7", True)]

_SHARP_ROOTS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_FLAT_ROOTS = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
_FLAT_KEYS = {("F", "major"), ("D", "minor"), ("G", "minor"), ("C", "minor"), ("F", "minor")}


def parse_key(key: str) -> Tuple[int, str, bool]:
    """(tonica 0-11, 'major'/'minor', scrivere le alterazioni come bemolli)
    per una tonalita' come quella del progetto ('C', 'Am', 'F#', 'Bbm'). Do
    maggiore se vuota o illeggibile."""
    m = re.match(r"^\s*([A-Ga-g])([#b]?)\s*(m|min|minor)?\s*$", key or "")
    if not m:
        return 0, "major", False
    letter, accidental, minor = m.groups()
    mode = "minor" if minor else "major"
    tonic = (_SHARP_ROOTS.index(letter.upper()) + {"#": 1, "b": -1}.get(accidental, 0)) % 12
    flats = accidental == "b" or (not accidental and (letter.upper(), mode) in _FLAT_KEYS)
    return tonic, mode, flats


def project_has_chords(project: Project, midi_dir: Optional[str] = None,
                       exclude_track_name: Optional[str] = None) -> bool:
    """Vero se almeno una traccia del progetto (tranne 'exclude_track_name',
    se dato) contiene accordi che basso e accompagnamento possono seguire
    (vedi extract_chords_from_track)."""
    for track in project.tracks:
        if track.instrument.is_percussion or track.name == exclude_track_name:
            continue
        try:
            if extract_chords_from_track(track.text, project.patterns,
                                         default_octave=track.instrument.default_octave,
                                         midi_dir=midi_dir):
                return True
        except (NotationError, ValueError):
            continue  # testo in corso di scrittura: non conta
    return False


def _enrich_harmony(seq: list, mode: str, bar: Fraction, variability: float, rng: random.Random) -> list:
    """Armonia piu' ricca: ogni accordo di 'seq' ([semitoni sopra la tonica,
    qualita', durata in beat, cromatico]) puo', con la variabilita':
    - se e' un IV maggiore seguito dal I, prendere in prestito la iv minore
      (per meta' della sua durata, o tutto se dura meno di una battuta);
    - se e' una dominante che scende di quinta (non la tonica, come il C7
      del blues), diventare il suo sostituto di tritono (Db7 al posto di G7
      in Do);
    - se dura almeno una battuta, lasciare la seconda meta' alla dominante
      secondaria dell'accordo successivo (A7 prima di Dm), o, se dura
      almeno due battute, la sua ultima battuta a un II-V verso di esso.
    Un accordo subisce al massimo una trasformazione."""
    out = []
    for i, (off, quality, dur, chromatic) in enumerate(seq):
        nxt = seq[i + 1] if i + 1 < len(seq) else None
        if (mode == "major" and off == 5 and quality in ("", "maj7", "6", "add9", "sus2")
                and nxt is not None and nxt[0] == 0 and rng.random() < _MINOR_IV_P * variability):
            if dur >= bar:
                out += [[off, quality, dur / 2, chromatic], [5, "m6", dur / 2, False]]
            else:
                out.append([5, "m6", dur, False])
            continue
        if (quality in _DOMINANTS and off != 0 and nxt is not None and (off - nxt[0]) % 12 == 7
                and rng.random() < _TRITONE_P * variability):
            out.append([(off + 6) % 12, "7", dur, True])
            continue
        # l'ultimo accordo si prepara con la sua dominante solo se e' la
        # tonica: un giro che finisce sul V preceduto dal V/V suonerebbe
        # come un cambio di tonalita'
        closing = i + 1 == len(seq) - 1 and nxt[0] != 0 if nxt is not None else False
        if (nxt is not None and not closing and dur >= bar and nxt[0] != off
                and nxt[0] in _TONICIZABLE[mode] and nxt[1] not in _NOT_TARGETS
                and (off - nxt[0]) % 12 != 7 and rng.random() < _SECONDARY_P * variability):
            target, target_minor = nxt[0], nxt[1].startswith("m") and not nxt[1].startswith("maj")
            dominant = [(target + 7) % 12, "7", None, False]
            if dur >= 2 * bar and rng.random() < 0.5:
                two = [(target + 2) % 12, "m7b5" if target_minor else "m7", bar / 2, False]
                out += [[off, quality, dur - bar, chromatic], two, dominant[:2] + [bar / 2, False]]
            else:
                out += [[off, quality, dur / 2, chromatic], dominant[:2] + [dur / 2, False]]
            continue
        out.append([off, quality, dur, chromatic])
    return out


def _final_cadence(seq: list, mode: str, tonic_quality: str, bar: Fraction, total: Fraction,
                   variability: float, rng: random.Random, authentic: bool = False) -> list:
    """Chiude il giro sulla tonica: l'ultima battuta diventa il I (o i), e
    la mezza battuta prima l'accordo di cadenza (V7 senza variabilita';
    con la variabilita' anche plagale, iv minore, bVII7...: vedi
    _CADENCES; con 'authentic' solo V7 o bII7, vedi _AUTHENTIC_CADENCES).
    Gli accordi prima vengono accorciati di conseguenza."""
    options = _AUTHENTIC_CADENCES if authentic else _CADENCES[mode]
    cad_off, cad_quality, cad_chromatic = options[0] if variability <= 0 else rng.choice(options)
    tail = min(bar, total)
    cad_len = min(bar / 2, total - tail)
    head_end = total - tail - cad_len
    out, cursor = [], Fraction(0)
    for off, quality, dur, chromatic in seq:
        if cursor >= head_end:
            break
        out.append([off, quality, min(dur, head_end - cursor), chromatic])
        cursor += dur
    if cad_len > 0:
        if out and out[-1][0] == cad_off and out[-1][1] == cad_quality:
            out[-1][2] += cad_len
        else:
            out.append([cad_off, cad_quality, cad_len, cad_chromatic])
    out.append([0, tonic_quality, tail, False])
    return out


def generate_chord_progression(key: str, style: str, bars: int = 0, chord_bars: float = 1.0,
                               bar_beats: float = BEATS_PER_BAR, variability=0.0,
                               seed: Optional[int] = None, ending: bool = False) -> str:
    """Genera un giro armonico nello stile scelto (vedi PROGRESSION_STYLES)
    nella tonalita' 'key' (vedi parse_key), come simboli di accordo. Ogni
    accordo dura la sua durata di stile in battute moltiplicata per
    'chord_bars' (0.5 = accordi due volte piu' rapidi, 2 = piu' lenti); il giro
    si ripete fino a 'bars' battute di 'bar_beats' beat (0 = il giro una volta
    sola), troncando l'ultimo accordo. Con 'variability' > 0 gli accordi
    possono arricchirsi (settime, none, sus: vedi _CHORD_COLORS) e
    l'armonia si arricchisce (dominanti secondarie, II-V, sostituti di
    tritono, iv minore: vedi _enrich_harmony), in modo riproducibile per
    'seed'. Con 'ending' il giro chiude su una cadenza e sulla tonica (vedi
    _final_cadence). Solleva ValueError se lo stile non esiste o e'
    pensato per l'altro modo (maggiore/minore) della tonalita'."""
    spec = PROGRESSION_STYLES.get(style)
    if spec is None:
        raise ValueError(tr("Stile di giro armonico sconosciuto: '{style}' (validi: {0})", ', '.join(PROGRESSION_STYLES), style=style))
    tonic, mode, flats = parse_key(key)
    if spec["mode"] != mode:
        wanted = "maggiore" if spec["mode"] == "major" else "minore"
        raise ValueError(tr("Lo stile '{style}' e' per tonalita' {wanted}: scegli una tonalita' {wanted}.", style=style, wanted=wanted))
    if bars < 0 or chord_bars <= 0 or bar_beats <= 0:
        raise ValueError(tr("Battute, durata degli accordi e metrica devono essere positive."))
    # nel giro armonico conta solo l'aspetto "note e armonia"
    variability = _variability(variability).notes
    rng = random.Random(seed)
    # Gli stili con accordi presi in prestito (bVII, bII: "flats") si scrivono
    # con i bemolli, salvo nelle tonalita' con i diesis nel nome.
    if spec.get("flats") and "#" not in (key or ""):
        flats = True
    roots = _FLAT_ROOTS if flats else _SHARP_ROOTS
    # gli accordi cromatici (sostituti di tritono, bVII7) in bemolle: Db7, non C#7
    chromatic_roots = _SHARP_ROOTS if "#" in (key or "") else _FLAT_ROOTS
    bar = Fraction(bar_beats).limit_denominator(64)
    scale = Fraction(chord_bars).limit_denominator(64)
    cycle = [(offset, quality, bar * scale * length) for offset, quality, length in spec["chords"]]
    total = bar * bars if bars else sum(dur for _, _, dur in cycle)

    seq = []  # [semitoni sopra la tonica, qualita', durata in beat, cromatico]
    cursor = Fraction(0)
    i = 0
    while cursor < total:
        offset, quality, dur = cycle[i % len(cycle)]
        dur = min(dur, total - cursor)
        if variability > 0 and rng.random() < _COLOR_P * variability:
            options = _DOMINANT_COLORS if (quality == "" and offset == 7) else _CHORD_COLORS.get(quality)
            if options:
                quality = rng.choice(options)
        seq.append([offset, quality, dur, False])
        cursor += dur
        i += 1
    if variability > 0:
        seq = _enrich_harmony(seq, mode, bar, variability, rng)
    if ending:
        tonic_quality = next((q for off, q, _l in spec["chords"] if off == 0), "" if mode == "major" else "m")
        seq = _final_cadence(seq, mode, tonic_quality, bar, total, variability, rng,
                             authentic=spec["chords"][0][0] != 0)
    chords = [((chromatic_roots if chromatic else roots)[(tonic + off) % 12] + quality, dur)
              for off, quality, dur, chromatic in seq if dur > 0]

    unit = next(u for u in (Fraction(1), Fraction(1, 2), Fraction(1, 4), Fraction(1, 8), Fraction(1, 16))
                if all((dur / u).denominator == 1 for _, dur in chords))
    tokens = [f"{int(4 / unit)}:"]
    for symbol, dur in chords:
        mult = int(dur / unit)
        tokens.append(f"{mult}{symbol}" if mult > 1 else symbol)
    return " ".join(tokens)


# ---------------------------------------------------------------------------
# Condiviso: slot (batteria) -> token ST-Syntax
# ---------------------------------------------------------------------------

def _slots_to_tokens(slots: List[Optional[list]], grid: str = DEFAULT_GRID) -> List[str]:
    """slots[i] = None (pausa) oppure [(nome_percussione, velocity), ...] per
    gli hit simultanei in quello slot (un'unita' della griglia 'grid':
    sedicesimi, o terzine di ottavo con '8T:'). Comprime le pause
    consecutive e ripete '@' solo al cambio di velocity, stessa convenzione
    di core.audio_quantize.events_to_tokens/core.midi_convert.channel_to_tokens."""
    tokens = [grid]
    last_velocity = None
    i, n = 0, len(slots)
    while i < n:
        if slots[i] is None:
            run = 0
            while i < n and slots[i] is None:
                run += 1
                i += 1
            tokens.append(f"{run}r" if run > 1 else "r")
            continue
        hits = slots[i]
        vel = hits[0][1]
        if vel != last_velocity:
            tokens.append(f"{vel}@")
            last_velocity = vel
        names = [name for name, _ in hits]
        assert all(name in PERCUSSION_MAP for name in names), names
        body = names[0] if len(names) == 1 else "[" + " ".join(names) + "]"
        tokens.append(body)
        i += 1
    return tokens


# ---------------------------------------------------------------------------
# Rigenerare solo alcune battute (sezione "G" della proposta)
# ---------------------------------------------------------------------------

_GENERATED_TOKEN = re.compile(r"(\d+)@|(\d*)(\[[^\]]*\]|\S+)")


def _generated_timeline(text: str) -> Tuple[str, list]:
    """(griglia, [(inizio, fine, corpo del token con moltiplicatore,
    velocity in vigore o None), ...]) di un testo scritto dai generatori di
    questo modulo: una sola dichiarazione di griglia all'inizio, poi pause,
    note, blocchi [...], simboli d'accordo e 'N@'. Tempi in beat, esatti
    (Fraction). ValueError per un testo di forma diversa (es. modificato a
    mano con altre dichiarazioni)."""
    body = text.strip()
    m = re.match(r"^(\d+)(T?):\s*", body)
    if not m:
        raise ValueError(tr("Il testo non inizia con una griglia (es. '16:')."))
    grid = m.group(0).strip()
    unit = Fraction(4, int(m.group(1))) * (Fraction(2, 3) if m.group(2) else 1)
    items, t, velocity = [], Fraction(0), None
    for tok in _GENERATED_TOKEN.finditer(body[m.end():]):
        if tok.group(1):
            velocity = int(tok.group(1))
            continue
        mult, core = tok.group(2), tok.group(3)
        if core.endswith(":") or core.endswith("@"):
            raise ValueError(tr("Token non previsto in un testo generato: '{0}'", tok.group(0)))
        end = t + unit * (int(mult) if mult else 1)
        items.append((t, end, tok.group(0), velocity))
        t = end
    return grid, items


def splice_bars(base: str, alt: str, first_bar: int, last_bar: int, bar_beats: float) -> str:
    """'base' con le battute da 'first_bar' a 'last_bar' (da 1, comprese)
    prese da 'alt': due testi generati con gli stessi controlli e semi
    diversi (vedi _generated_timeline). Il taglio avviene sul confine di
    token comune ai due testi piu' vicino all'esterno delle battute scelte,
    cosi' nessuna nota viene spezzata: se una nota attraversa l'inizio o la
    fine del tratto (un anticipo, un accordo lungo) il tratto si allarga fino
    a comprenderla. La velocity in vigore viene riscritta a ogni giunzione."""
    grid, old = _generated_timeline(base)
    alt_grid, new = _generated_timeline(alt)
    if grid != alt_grid or not old or old[-1][1] != new[-1][1]:
        raise ValueError(tr("I due testi non hanno la stessa griglia e la stessa durata."))
    bar = Fraction(bar_beats).limit_denominator(64)
    total = old[-1][1]
    lo = min(total, bar * max(0, first_bar - 1))
    hi = min(total, bar * max(first_bar, last_bar))
    common = sorted({i[0] for i in old} & {i[0] for i in new} | {total})
    cut1 = max(t for t in common if t <= lo)
    cut2 = min(t for t in common if t >= hi)
    chosen = ([i for i in old if i[1] <= cut1] + [i for i in new if cut1 <= i[0] < cut2]
              + [i for i in old if i[0] >= cut2])
    tokens, current = [grid], None
    for _start, _end, token, velocity in chosen:
        is_rest = re.fullmatch(r"\d*r", token) is not None
        if velocity is not None and velocity != current and not is_rest:
            tokens.append(f"{velocity}@")
            current = velocity
        tokens.append(token)
    return " ".join(tokens)
