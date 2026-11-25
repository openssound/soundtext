"""
SoundText Mobile, fase 3: «Un brano in 60 secondi», la versione estesa.

Genere, atmosfera e durata (e, volendo, tonalita', tempo, metrica, forma, organico, melodia, finale, modulazione e
le scelte di ogni parte) diventano un brano completo con i generatori che il motore ha gia': giro armonico,
accompagnamento, basso, batteria, melodia. Ogni genere e' una riga di GENRES; ogni atmosfera una di MOODS. Il brano
si scrive in box, uno per sezione e per traccia, come nella vista Struttura.

Ogni parte (giro armonico, batteria, basso, accompagnamento...) ha il suo seme: «Un'altra» per una parte cambia solo
quello, e una parte con il lucchetto tiene il suo. Le scelte si salvano nel brano (un commento «// quick: {...}») e
con le stesse scelte e gli stessi semi esce lo stesso brano.
"""

import json
import random
import re
from typing import Dict, List, Optional, Tuple

from core.humanize_text import humanize_drums, humanize_part
from core.i18n import tr

# ------------------------------------------------------------ valori

GENRES = ("pop", "rock", "ballata", "bossa", "jazz", "swing", "funk", "soul", "disco", "lofi", "elettronica",
          "orchestrale", "blues", "reggae", "country", "punk", "metal", "rocknroll", "samba", "chacha", "valzer",
          "marcia", "ballata68", "afro68", "balcanico78")
MOODS = ("allegra", "malinconica", "tesa", "epica", "calma", "sognante", "misteriosa", "romantica", "nostalgica",
         "festosa", "oscura", "giocosa", "solenne", "drammatica", "serena", "energica", "sensuale", "avventurosa", "ipnotica",
         "intima", "grintosa", "elegante")
DURATIONS = (15, 30, 45, 60, 90, 120, 180, 240)
FORMS = ("loop", "canzone", "aaba", "blues", "ponte")
ENSEMBLES = ("piano", "acustica", "elettrica", "elettronica", "orchestra")
MELODIES = ("nessuna", "cantabile", "vivace", "ballata", "aaba")
ENERGY_CURVES = ("sale", "picco", "cala")


def energy_levels(curve: str, count: int) -> List[str]:
    """Il livello ("light", "normal", "full") di ognuna delle 'count' sezioni mobili lungo una curva dell'energia: sale, picco
    (sale fino a due terzi e poi cala) o cala. Lista vuota se la curva non esiste."""
    if curve not in ENERGY_CURVES:
        return []
    out = []
    for pos in range(count):
        e = pos / (count - 1) if count > 1 else 1.0
        height = {"sale": e, "cala": 1.0 - e, "picco": 1.0 - abs(e - 0.7) / 0.7}[curve]
        out.append("light" if height < 0.34 else "normal" if height < 0.67 else "full")
    return out
ENDINGS = ("cadenza", "rallentando", "sfumato")
PARTS = ("progression", "comp", "comp2", "horn", "pad", "bass", "drums", "melody", "harm")
_MELODY_STYLE = {"cantabile": "melody_period", "vivace": "melody_lively", "ballata": "melody_ballad", "aaba": "melody_aaba"}

# i parametri di ogni atmosfera: modo, fattore del tempo, intensita' (strofa, ritornello), giro armonico
# (strofa, ritornello, ponte), come stanno fra loro (energia 1-4)
MOODS_DATA = {
    "allegra": ("major", 1.10, ("normal", "full"), ("pop", "royal_road", "borrowed_flat6"), 3),
    "malinconica": ("minor", 0.88, ("light", "normal"), ("minor_pop", "andalusian", "minor_circle"), 1),
    "tesa": ("minor", 1.00, ("normal", "full"), ("minor_rock", "minor_cadence", "phrygian"), 3),
    "epica": ("minor", 1.05, ("normal", "full"), ("minor_epic", "minor_pop", "minor_deceptive"), 4),
    "calma": ("major", 0.82, ("light", "normal"), ("canon", "ballad", "plagal"), 1),
    "sognante": ("minor", 0.90, ("light", "normal"), ("dorian_vamp", "minor_pop", "dorian_vamp"), 1),
    "misteriosa": ("minor", 0.90, ("light", "normal"), ("phrygian", "minor_cadence", "phrygian"), 2),
    "romantica": ("major", 0.85, ("light", "normal"), ("ballad", "canon", "royal_road"), 1),
    "nostalgica": ("minor", 0.90, ("light", "normal"), ("line_cliche", "minor_pop", "line_cliche"), 1),
    "festosa": ("major", 1.10, ("normal", "full"), ("gospel", "pop", "mixolydian"), 4),
    "oscura": ("minor", 0.95, ("normal", "full"), ("phrygian", "minor_epic", "minor_three"), 3),
    "giocosa": ("major", 1.08, ("normal", "full"), ("doo_wop", "three_chord", "pop"), 3),
    "solenne": ("major", 0.85, ("light", "normal"), ("canon", "plagal", "ballad"), 2),
    "drammatica": ("minor", 1.0, ("normal", "full"), ("minor_epic", "minor_deceptive", "minor_cadence"), 4),
    "serena": ("major", 0.92, ("light", "normal"), ("ballad", "borrowed_iv", "canon"), 1),
    "energica": ("major", 1.15, ("normal", "full"), ("rock", "mixolydian", "borrowed_flat6"), 4),
    "sensuale": ("minor", 0.86, ("light", "normal"), ("line_cliche", "dorian_vamp", "minor_plagal"), 1),
    "avventurosa": ("major", 1.06, ("normal", "full"), ("royal_road", "mixolydian", "borrowed_flat6"), 3),
    "ipnotica": ("minor", 0.95, ("light", "normal"), ("dorian_vamp", "phrygian", "dorian_vamp"), 2),
    "intima": ("major", 0.84, ("light", "normal"), ("canon", "borrowed_iv", "ballad"), 1),
    "grintosa": ("minor", 1.04, ("normal", "full"), ("minor_rock", "minor_three", "minor_epic"), 4),
    "elegante": ("major", 0.96, ("light", "normal"), ("turnaround", "jazz_251", "royal_road"), 2),
}

# il colore di ogni atmosfera (quarta revisione, punto 1): oltre al modo, al tempo e all'intensita' di MOODS_DATA, ogni atmosfera ha
# - tone: "warm" o "bright", il timbro della melodia fra gli strumenti che il genere ammette (non nei generi distorti);
# - fx: gli effetti di partenza, che sostituiscono quelli del genere dello stesso tipo e si aggiungono agli altri;
# - ending: il finale se non lo si sceglie (e il genere non ne ha uno suo); lo sfumato solo dai 45 secondi in su, mai in un loop;
# - modulation: l'ultimo ritornello sale di un tono (dai 60 secondi in su, se non lo si sceglie);
# - voice: la seconda voce in terze nei ritornelli (se il genere non ne ha una sua);
# - swing: i punti di swing in piu' o in meno, nei generi che lo hanno;
# - pedal_verse: nella strofa e nell'intro il basso tiene la tonica (la tensione che non si scioglie).
_MOOD_COLOR = {
    "allegra": {"melody_style": "vivace", "velocity": 1.03},
    "festosa": {"tone": "bright", "modulation": True, "melody_style": "vivace", "velocity": 1.05},
    "giocosa": {"tone": "bright", "swing": 2, "melody_style": "vivace", "velocity": 1.04, "fill": 2},
    "energica": {"fx": ("compressore: soglia=-20 rapporto=3 attacco=10 rilascio=120 guadagno=3",), "swing": -2,
                 "melody_style": "vivace", "velocity": 1.08, "fill": 2},
    "avventurosa": {"modulation": True, "melody_style": "vivace", "add_horn": "Trumpet", "velocity": 1.04, "fill": 2, "fx": ("delay: suddivisione=1/8 tempo=375 ripetizioni=20 mix=10",)},
    "epica": {"modulation": True, "ending": "rallentando", "add_horn": "French_Horn", "velocity": 1.08, "fx": ("riverbero: stanza=70 smorzamento=40 ampiezza=100 mix=24",)},
    "drammatica": {"ending": "rallentando", "add_horn": "French_Horn", "chords": "tension", "velocity": 1.06, "fx": ("riverbero: stanza=55 smorzamento=45 ampiezza=100 mix=18",)},
    "tesa": {"pedal_verse": True, "fill": 8, "tone": "bright", "chords": "tension", "velocity": 1.04, "fx": ("riverbero: stanza=15 smorzamento=60 ampiezza=100 mix=6",)},
    "oscura": {"tone": "warm", "melody_style": "cantabile", "add_pad": "Pad_2_warm", "chords": "tension", "velocity": 0.96, "fill": 8, "fx": ("passa_basso: frequenza=4500 pendenza=12", "riverbero: stanza=60 smorzamento=50 ampiezza=100 mix=18")},
    "misteriosa": {"tone": "warm", "add_pad": "Pad_1_new_age", "chords": "tension", "velocity": 0.9, "fill": 8, "fx": ("riverbero: stanza=85 smorzamento=30 ampiezza=100 mix=28",)},
    "sognante": {"ending": "sfumato", "add_pad": "Pad_2_warm", "chords": "seventh", "melody_style": "ballata", "drums": "halftime", "velocity": 0.9, "fill": 8,
                 "fx": ("delay: suddivisione=1/8p tempo=375 ripetizioni=30 mix=12", "riverbero: stanza=80 smorzamento=35 ampiezza=100 mix=25")},
    "ipnotica": {"ending": "sfumato", "add_pad": "Pad_2_warm", "drums": "halftime", "velocity": 0.92, "fill": 8, "fx": ("delay: suddivisione=1/4 tempo=375 ripetizioni=40 mix=16",)},
    "malinconica": {"tone": "warm", "chords": "seventh", "ending": "rallentando", "melody_style": "ballata", "drums": "halftime", "velocity": 0.93,
                    "fx": ("riverbero: stanza=55 smorzamento=45 ampiezza=100 mix=18",)},
    "nostalgica": {"tone": "warm", "chords": "seventh", "voice": "thirds", "velocity": 0.94, "fx": ("passa_basso: frequenza=5500 pendenza=12", "eq: bassi=2 medi=0 alti=-2")},
    "sensuale": {"tone": "warm", "chords": "seventh", "swing": 3, "velocity": 0.94, "fx": ("riverbero: stanza=40 smorzamento=45 ampiezza=100 mix=14",)},
    "romantica": {"tone": "warm", "chords": "seventh", "voice": "thirds", "ending": "rallentando", "melody_style": "ballata", "velocity": 0.94,
                  "fx": ("riverbero: stanza=55 smorzamento=40 ampiezza=100 mix=18",)},
    "solenne": {"ending": "rallentando", "add_pad": "Strings", "velocity": 0.96, "fill": 8, "fx": ("riverbero: stanza=75 smorzamento=40 ampiezza=100 mix=26",)},
    "serena": {"voice": "thirds", "melody_style": "cantabile", "velocity": 0.94, "fill": 8, "fx": ("riverbero: stanza=50 smorzamento=40 ampiezza=100 mix=14",)},
    "calma": {"ending": "rallentando", "melody_style": "ballata", "drums": "halftime", "velocity": 0.92, "fill": 8,
              "fx": ("riverbero: stanza=50 smorzamento=40 ampiezza=100 mix=14",)},
    # le atmosfere nuove (quarta revisione, punto 4)
    "intima": {"tone": "warm", "chords": "seventh", "sparse": True, "ending": "rallentando", "melody_style": "ballata", "drums": "halftime", "velocity": 0.88, "fill": 8,
               "fx": ("riverbero: stanza=25 smorzamento=50 ampiezza=100 mix=8",)},
    "grintosa": {"tone": "bright", "swing": -1, "velocity": 1.07, "fill": 2,
                 "fx": ("compressore: soglia=-22 rapporto=4 attacco=8 rilascio=100 guadagno=3",)},
    "elegante": {"tone": "warm", "chords": "seventh", "voice": "thirds", "swing": 1, "velocity": 0.96,
                 "fx": ("riverbero: stanza=30 smorzamento=50 ampiezza=100 mix=10",)},
}
# il timbro degli strumenti della melodia (gli altri sono neutri)
_TONE = {"warm": ("Oboe", "Clarinet", "Cello", "Violin", "Fiddle", "Tenor_Sax", "Alto_Sax", "Harmonica", "Nylon_Guitar", "Acoustic_Guitar_Steel"),
         "bright": ("Flute", "Trumpet", "Lead", "Clean_Guitar", "Marimba", "Trombone")}
_NO_TONE_GENRES = ("rock", "punk", "metal")
# i generi dove un'atmosfera puo' aggiungere un tappeto o i fiati (non nelle bande, nel rock e nei generi di danza)
_ADD_PART_GENRES = ("pop", "ballata", "ballata68", "valzer", "bossa", "soul", "lofi", "elettronica", "orchestrale", "disco", "funk", "jazz", "swing")
_MOOD_DRUM_GENRES = ("pop", "rock", "country")

# gli strumenti di ogni organico (nomi che st-language riconosce, con il trattino basso)
_ENSEMBLE_PARTS = {
    "piano": {"comp": "Piano"},
    "acustica": {"comp": "Piano", "comp2": "Nylon_Guitar", "bass": "Bass", "drums": "Drums", "melody": "Flute"},
    "elettrica": {"comp": "Clean_Guitar", "comp2": "Electric_Piano_1", "bass": "Bass", "drums": "Drums", "melody": "Lead"},
    "elettronica": {"comp": "Pad", "comp2": "Electric_Piano_1", "bass": "Synth_Bass_1", "drums": "Drums", "melody": "Lead"},
    "orchestra": {"comp": "Strings", "comp2": "Harp", "horn": "French_Horn", "bass": "Cello", "melody": "Oboe"},
}

# Il genere: metrica, tempo, stile di batteria, di basso, di accompagnamento (e un secondo), stile di melodia,
# organico di partenza, forma, atmosfere ammesse e, se serve, i giri armonici che lo caratterizzano
# {"major": (strofa, ritornello, ponte), "minor": (...)}. «dist»: chitarre distorte.
GENRES_DATA = {
    "pop": dict(meter="4/4", bpm=104, drums="rock", bass="root_fifth", comp="arpeggio_up", comp2="block_chords", melody="cantabile",
                ens="acustica", form="canzone", moods=("allegra", "malinconica", "tesa", "epica", "calma", "romantica", "nostalgica", "festosa", "sognante", "giocosa", "serena", "energica", "avventurosa")),
    "rock": dict(meter="4/4", bpm=122, drums="rock", bass="eighths", comp="power_chords", comp2="block_chords", melody="vivace",
                 ens="elettrica", form="canzone", dist=True, moods=("allegra", "tesa", "epica", "oscura", "festosa", "malinconica", "drammatica", "energica", "avventurosa")),
    "ballata": dict(meter="4/4", bpm=72, drums="halftime", bass="root", comp="arpeggio_up", comp2="sustained", melody="ballata",
                    ens="acustica", form="ponte", moods=("malinconica", "calma", "romantica", "nostalgica", "epica", "sognante", "solenne", "serena", "sensuale")),
    "bossa": dict(meter="4/4", bpm=128, drums="bossa", bass="bossa", comp="bossa_comp", comp2="block_chords", melody="cantabile",
                  ens="acustica", form="canzone", moods=("allegra", "calma", "romantica", "nostalgica", "malinconica", "sognante", "serena", "sensuale", "giocosa"),
                  prog={"major": ("jazz_251", "turnaround", "circle"), "minor": ("minor_251", "minor_circle", "minor_251")}),
    "jazz": dict(meter="4/4", bpm=140, drums="swing", bass="walking", comp="quarter_chords", comp2="block_chords", melody="aaba",
                 ens="acustica", form="aaba", moods=("allegra", "malinconica", "calma", "romantica", "nostalgica", "misteriosa", "sognante", "serena", "sensuale", "giocosa"),
                 prog={"major": ("jazz_251", "rhythm_changes", "jazz_251"), "minor": ("minor_251", "minor_251", "minor_circle")}),
    "swing": dict(meter="4/4", bpm=160, drums="swing", bass="walking", comp="quarter_chords", comp2="block_chords", melody="vivace",
                  ens="acustica", form="aaba", moods=("allegra", "festosa", "romantica", "nostalgica", "malinconica", "giocosa", "energica"),
                  prog={"major": ("rhythm_changes", "jazz_251", "turnaround"), "minor": ("minor_251", "minor_circle", "minor_251")}),
    "funk": dict(meter="4/4", bpm=108, drums="funk", bass="funk16", comp="funk_stab", comp2="scratch", melody="vivace",
                 ens="elettrica", form="canzone", moods=("allegra", "tesa", "festosa", "oscura", "misteriosa", "giocosa", "energica", "sensuale"),
                 prog={"major": ("funk_vamp", "funk_walk", "gospel"), "minor": ("dorian_vamp", "funk_minor", "dorian_vamp")}),
    "soul": dict(meter="4/4", bpm=92, drums="soul", bass="motown", comp="soul_comp", comp2="sustained", melody="ballata",
                 ens="acustica", form="canzone", moods=("allegra", "malinconica", "romantica", "nostalgica", "calma", "festosa", "solenne", "sensuale", "serena"),
                 prog={"major": ("soul_turn", "gospel", "soul_plagal"), "minor": ("soul_minor", "minor_cadence", "minor_circle")}),
    "disco": dict(meter="4/4", bpm=118, drums="disco", bass="octaves", comp="funk_stab", comp2="quarter_chords", melody="vivace",
                  ens="elettrica", form="canzone", moods=("allegra", "festosa", "romantica", "malinconica", "giocosa", "energica", "sensuale"),
                  prog={"major": ("circle", "pop", "royal_road"), "minor": ("minor_circle", "minor_pop", "minor_cadence")}),
    "lofi": dict(meter="4/4", bpm=80, drums="hiphop", bass="root", comp="broken_chord", comp2="sustained", melody="ballata",
                 ens="elettronica", form="loop", moods=("calma", "malinconica", "nostalgica", "sognante", "romantica", "misteriosa", "serena", "sensuale", "ipnotica"),
                 prog={"major": ("jazz_251", "gospel", "turnaround"), "minor": ("minor_251", "dorian_vamp", "minor_pop")}),
    "elettronica": dict(meter="4/4", bpm=124, drums="disco", bass="octaves", comp="sustained", comp2="arpeggio_up", melody="vivace",
                        ens="elettronica", form="canzone", moods=("allegra", "tesa", "epica", "oscura", "sognante", "misteriosa", "festosa", "drammatica", "energica", "avventurosa", "ipnotica")),
    "orchestrale": dict(meter="4/4", bpm=92, drums=None, bass="root", comp="sustained", comp2="arpeggio_up", melody="cantabile",
                        ens="orchestra", form="ponte", moods=MOODS),
    "blues": dict(meter="4/4", bpm=96, drums="shuffle", bass="blues", comp="quarter_chords", comp2="block_chords", melody="vivace",
                  ens="elettrica", form="blues", moods=("allegra", "malinconica", "tesa", "oscura", "calma", "nostalgica", "sensuale", "drammatica"),
                  prog={"major": ("blues_12", "blues_12", "blues_12"), "minor": ("minor_blues_12", "minor_blues_12", "minor_blues_12")}),
    "reggae": dict(meter="4/4", bpm=76, drums="reggae", bass="reggae", comp="skank_chords", comp2="organ_bubble", melody="cantabile",
                   ens="elettrica", form="canzone", moods=("allegra", "calma", "festosa", "nostalgica", "sognante", "serena", "giocosa", "ipnotica", "sensuale"),
                   prog={"major": ("three_chord", "pop", "mixolydian"), "minor": ("minor_three", "minor_pop", "minor_cadence")}),
    "country": dict(meter="4/4", bpm=108, drums="country", bass="walk_up", comp="boom_chick", comp2="banjo_roll", melody="cantabile",
                    ens="acustica", form="canzone", moods=("allegra", "festosa", "malinconica", "nostalgica", "calma", "romantica", "giocosa", "serena", "avventurosa"),
                    prog={"major": ("three_chord", "pop", "canon"), "minor": ("minor_pop", "minor_three", "minor_cadence")}),
    "punk": dict(meter="4/4", bpm=170, drums="punk", bass="eighths", comp="power_chords", comp2="block_chords", melody="vivace",
                 ens="elettrica", form="canzone", dist=True, moods=("tesa", "allegra", "epica", "oscura", "festosa", "energica", "giocosa", "drammatica"),
                 prog={"major": ("three_chord", "rock", "mixolydian"), "minor": ("minor_three", "minor_rock", "minor_three")}),
    "metal": dict(meter="4/4", bpm=150, drums="metal", bass="eighths", comp="metal_gallop", comp2="block_chords", melody="vivace",
                  ens="elettrica", form="canzone", dist=True, moods=("tesa", "epica", "oscura", "misteriosa", "drammatica", "energica", "avventurosa"),
                  prog={"major": ("mixolydian", "rock", "mixolydian"), "minor": ("phrygian", "minor_epic", "minor_three")}),
    "rocknroll": dict(meter="4/4", bpm=150, drums="rocknroll", bass="boogie", comp="boogie_piano", comp2="quarter_chords", melody="vivace",
                      ens="elettrica", form="canzone", moods=("allegra", "festosa", "nostalgica", "tesa", "giocosa", "energica"),
                      prog={"major": ("doo_wop", "rock", "three_chord"), "minor": ("minor_rock", "minor_three", "minor_rock")}),
    "samba": dict(meter="4/4", bpm=100, drums="samba", bass="bossa", comp="bossa_comp", comp2="montuno", melody="vivace",
                  ens="acustica", form="canzone", moods=("allegra", "festosa", "romantica", "calma", "giocosa", "energica", "sensuale"),
                  prog={"major": ("jazz_251", "pop", "circle"), "minor": ("minor_251", "minor_circle", "minor_251")}),
    "chacha": dict(meter="4/4", bpm=112, drums="cha_cha", bass="tumbao", comp="montuno", comp2="block_chords", melody="cantabile",
                   ens="acustica", form="canzone", moods=("allegra", "festosa", "romantica", "nostalgica", "giocosa", "sensuale", "energica"),
                   prog={"major": ("pop", "circle", "jazz_251"), "minor": ("minor_pop", "minor_circle", "minor_251")}),
    "valzer": dict(meter="3/4", bpm=96, drums="waltz", bass="waltz", comp="waltz_comp", comp2="sustained", melody="cantabile",
                   ens="acustica", form="canzone", moods=("allegra", "romantica", "nostalgica", "malinconica", "festosa", "epica", "solenne", "giocosa", "serena")),
    "marcia": dict(meter="4/4", bpm=112, drums="march", bass="two_feel", comp="quarter_chords", comp2="block_chords", melody="vivace",
                   ens="orchestra", form="canzone", moods=("allegra", "epica", "festosa", "tesa", "solenne", "giocosa", "energica", "avventurosa"), drums_in_orchestra=True),
    "ballata68": dict(meter="6/8", bpm=66, drums="ballad_68", bass="root", comp="arpeggio_68", comp2="sustained", melody="ballata",
                      ens="acustica", form="ponte", moods=("malinconica", "romantica", "nostalgica", "calma", "sognante", "epica", "solenne", "serena", "sensuale")),
    "afro68": dict(meter="6/8", bpm=96, drums="afro_68", bass="two_feel", comp="arpeggio_68", comp2="block_chords", melody="cantabile",
                   ens="acustica", form="canzone", moods=("allegra", "festosa", "sognante", "misteriosa", "calma", "giocosa", "energica", "ipnotica", "avventurosa")),
    "balcanico78": dict(meter="7/8", bpm=140, drums="balkan_78", bass="eighths", comp="block_chords", comp2="quarter_chords", melody="vivace",
                        ens="acustica", form="canzone", moods=("allegra", "festosa", "tesa", "misteriosa", "epica", "giocosa", "energica", "drammatica", "avventurosa", "ipnotica"),
                        prog={"major": ("mixolydian", "pop", "mixolydian"), "minor": ("phrygian", "minor_rock", "phrygian")}),
}

# le atmosfere nuove, nei generi dove stanno bene
_NEW_MOODS = {"intima": ("pop", "ballata", "jazz", "bossa", "country", "soul", "lofi", "ballata68", "valzer", "orchestrale", "swing", "afro68"),
              "grintosa": ("rock", "punk", "metal", "funk", "blues", "rocknroll", "soul", "country", "reggae", "disco"),
              "elegante": ("jazz", "swing", "bossa", "soul", "pop", "lofi", "valzer", "orchestrale", "chacha", "ballata", "samba", "disco")}
for _mood, _genres in _NEW_MOODS.items():
    for _g in _genres:
        GENRES_DATA[_g]["moods"] = tuple(GENRES_DATA[_g]["moods"]) + (_mood,)

# la scala della melodia per genere (8.8.3): pentatonica, blues o minore armonica (vedi core.melody_generate.SCALE_KINDS)
_GENRE_SCALE = {"blues": "blues", "rocknroll": "blues", "country": "pentatonic", "pop": "pentatonic", "punk": "pentatonic",
                "rock": "rock", "metal": "metal", "balcanico78": "phrygian_dominant",
                "funk": "groove", "soul": "groove", "lofi": "groove", "reggae": "groove",
                "jazz": "bebop", "swing": "bebop",
                "bossa": "latin", "samba": "latin", "chacha": "latin", "disco": "groove", "afro68": "pentatonic",
                "valzer": "classical", "ballata": "classical", "ballata68": "classical", "marcia": "classical",
                "elettronica": "modal", "orchestrale": "classical"}
# le figure della melodia per genere (8.9): note di avvicinamento cromatiche sul levare, prima di una nota sul tempo
# (core.melody_generate._add_approaches): sopra o sotto nel jazz, sotto nel blues e nei generi che lo prendono
_GENRE_FIGURE = {"jazz": "approach", "swing": "approach", "blues": "approach_below,blue_bend", "rocknroll": "approach_below,blue_bend",
                 "funk": "approach_below", "soul": "approach_below,blue_bend", "disco": "approach_below",
                 "bossa": "approach", "samba": "approach,grace_above", "chacha": "approach", "country": "approach_below,grace_below",
                 "rock": "approach_below,blue_bend", "balcanico78": "grace_above", "valzer": "grace_above",
                 "ballata": "grace_above", "ballata68": "grace_above",
                 "orchestrale": "grace_above", "marcia": "grace_above", "afro68": "grace_above", "pop": "grace_below",
                 "metal": "approach_below,blue_bend", "reggae": "grace_below", "punk": "approach_below"}
# gli strumenti che piegano la nota (il bend alla blues, 2b): chitarre, sax, armonica, archi, voce, synth; non il pianoforte
BENDABLE = ("Overdriven_Guitar", "Distortion_Guitar", "Clean_Guitar", "Electric_Guitar_Jazz", "Nylon_Guitar", "Acoustic_Guitar_Steel",
            "Tenor_Sax", "Alto_Sax", "Soprano_Sax", "Baritone_Sax", "Harmonica", "Trumpet", "Trombone", "Violin", "Fiddle", "Cello",
            "Lead", "Lead_2_sawtooth", "Voice_Oohs", "Choir_Aahs")


def _figures_for(genre: str, instrument: str) -> str:
    """Le figure della melodia del genere che lo strumento sa suonare (niente bend sul pianoforte)."""
    return ",".join(f for f in _GENRE_FIGURE.get(genre, "").split(",") if f and (f != "blue_bend" or instrument in BENDABLE))

# gli strumenti che ogni genere sceglie per le sue parti (8.8.1): valgono quando si suona l'organico di partenza del genere
# (se si sceglie un altro organico, vale quello); None toglie la parte; "horn" aggiunge i fiati, che suonano lo stile "horn_style"
_GENRE_INSTRUMENTS = {
    "pop": {"comp": "Acoustic_Guitar_Steel", "comp2": "Piano", "melody": "Flute", "pad": "Strings"},
    "ballata": {"comp": "Piano", "comp2": "Acoustic_Guitar_Steel", "melody": "Oboe", "pad": "Strings"},
    "ballata68": {"comp": "Piano", "comp2": "Acoustic_Guitar_Steel", "melody": "Clarinet", "pad": "Strings"},
    "bossa": {"comp": "Nylon_Guitar", "comp2": "Electric_Piano_1", "bass": "Acoustic_Bass"},
    "samba": {"comp": "Nylon_Guitar", "comp2": "Acoustic_Guitar_Steel", "melody": "Trumpet", "bass": "Acoustic_Bass"},
    "valzer": {"comp": "Accordion", "comp2": "Pizzicato_Strings", "melody": "Clarinet", "bass": "Acoustic_Bass"},
    "afro68": {"comp": "Marimba", "comp2": "Nylon_Guitar"},
    "jazz": {"bass": "Acoustic_Bass", "melody": "Tenor_Sax", "comp2": None},
    "swing": {"bass": "Acoustic_Bass", "melody": "Trumpet", "comp2": None, "horn": "Brass_Section"},
    "country": {"comp": "Acoustic_Guitar_Steel", "comp2": "Banjo", "melody": "Fiddle"},
    "soul": {"comp": "Electric_Piano_1", "comp2": "Drawbar_Organ", "melody": "Tenor_Sax", "horn": "Brass_Section", "pad": "Strings"},
    "chacha": {"bass": "Acoustic_Bass", "horn": "Brass_Section"},
    "lofi": {"comp": "Electric_Piano_1", "comp2": "Pad_2_warm", "bass": "Fretless_Bass", "melody": "Vibraphone"},       # Rhodes, vibrafono, basso morbido
    "elettronica": {"comp": "Pad_1_new_age", "bass": "Synth_Bass_1", "melody": "Lead_2_sawtooth"},
    "orchestrale": {"comp": "Strings", "comp2": "Harp", "bass": "Cello", "horn": "French_Horn", "melody": "Oboe"},
    "funk": {"comp": "Clavinet", "comp2": "Electric_Guitar_Muted", "bass": "Slap_Bass_1", "melody": "Tenor_Sax", "horn": "Brass_Section"},
    "blues": {"comp": "Overdriven_Guitar", "comp2": "Drawbar_Organ", "melody": "Harmonica"},
    "balcanico78": {"comp": "Accordion", "melody": "Clarinet", "horn": "Brass_Section", "bass": "Tuba"},      # la banda di ottoni: il basso e' la tuba
    "reggae": {"comp2": "Drawbar_Organ", "melody": "Harmonica"},
    "disco": {"melody": "Tenor_Sax", "horn": "Brass_Section", "pad": "Strings"},
    "rock": {"melody": "Overdriven_Guitar", "comp2": "Clean_Guitar"},
    "punk": {"melody": "Overdriven_Guitar", "comp2": None},          # chitarre, basso e batteria: niente organo
    "metal": {"melody": "Overdriven_Guitar", "comp2": None},
    "marcia": {"melody": "Trumpet", "bass": "Tuba", "comp": "Brass_Section", "comp2": "Accordion"},      # una banda: ottoni e fisarmonica, non archi e arpa
    "rocknroll": {"comp": "Piano", "comp2": "Clean_Guitar", "melody": "Tenor_Sax"},
}
_HORN_STYLE = {"swing": "horn_stabs", "soul": "horn_stabs", "funk": "horn_stabs", "disco": "horn_stabs", "chacha": "horn_stabs"}

# lo strumento della seconda voce (il tema in terze dell'ultimo ritornello), nella famiglia della melodia: la formazione di un
# genere non cambia da sola, la seconda voce c'e' solo se la si chiede (opzione second_voice)
# la seconda voce del genere, se lo strumento e' libero (prima di quella che segue lo strumento della melodia)
_GENRE_HARM = {"country": "Fiddle"}
# i generi che restano in maggiore anche nelle atmosfere in minore (se la tonalita' non e' scelta): i giri da usare (strofa,
# ritornello, ponte), con il bVII misolidio al posto del minore
_MAJOR_GENRES = {"country": ("three_chord", "mixolydian", "rock")}
_HARM_FOR = {"Flute": "Clarinet", "Oboe": "Clarinet", "Clarinet": "Flute", "Lead": "Lead_2_sawtooth", "Tenor_Sax": "Alto_Sax",
             "Alto_Sax": "Tenor_Sax", "Trumpet": "Trombone", "Harmonica": "Clarinet", "Fiddle": "Violin", "Violin": "Flute",
             "Overdriven_Guitar": "Rock_Organ", "Cello": "Violin", "Electric_Piano_1": "Flute", "Accordion": "Clarinet"}

# La variabilita' fra un brano e il successivo («Un'altra»): con lo stesso genere e la stessa atmosfera, il seme sceglie fra
# alternative che stanno bene nel genere (giri armonici, stili del basso e della batteria, stile della melodia, forma, un po' di
# tempo in piu' o in meno). Quello che l'utente sceglie nei dettagli non si tocca, e con variety=0 vale la ricetta pura.
_PROG_POOLS = {
    "default": {"major": ("pop", "doo_wop", "canon", "ballad", "royal_road", "three_chord", "borrowed_iv", "plagal", "deceptive"),
                "minor": ("minor_pop", "andalusian", "minor_rock", "minor_cadence", "minor_epic", "minor_three", "minor_deceptive", "minor_plagal")},
    "jazz": {"major": ("jazz_251", "turnaround", "circle", "rhythm_changes", "royal_road"),
             "minor": ("minor_251", "minor_circle", "minor_cadence", "dorian_vamp")},
    "groove": {"major": ("mixolydian", "gospel", "pop", "circle", "royal_road"),
               "minor": ("dorian_vamp", "minor_three", "minor_pop", "minor_circle")},
    "funk": {"major": ("funk_vamp", "funk_walk", "mixolydian", "gospel"), "minor": ("dorian_vamp", "funk_minor", "minor_three")},
    "soul": {"major": ("soul_turn", "gospel", "soul_plagal", "pop", "circle"),
             "minor": ("soul_minor", "minor_cadence", "minor_circle", "minor_pop")},
    "folk": {"major": ("three_chord", "pop", "canon", "mixolydian", "doo_wop"),
             "minor": ("minor_three", "minor_pop", "minor_cadence", "andalusian")},
    "rock": {"major": ("rock", "mixolydian", "three_chord", "pop", "borrowed_flat6"),
             "minor": ("minor_rock", "minor_three", "phrygian", "minor_epic", "minor_pop")},
}
_PROG_POOL_OF = {"jazz": "jazz", "swing": "jazz", "bossa": "jazz", "samba": "jazz", "chacha": "jazz", "lofi": "jazz",
                 "funk": "funk", "soul": "soul", "disco": "groove", "reggae": "folk", "country": "folk",
                 "rock": "rock", "punk": "rock", "metal": "rock", "rocknroll": "rock", "blues": None}
_BASS_ALTS = {"pop": ("root_fifth", "root", "eighths"), "ballata": ("root", "root_fifth"), "country": ("walk_up", "root_fifth", "root"),
              "rock": ("eighths", "root_fifth", "octaves"), "rocknroll": ("boogie", "root_fifth"), "chacha": ("tumbao", "bossa"), "blues": ("blues", "boogie", "walking"), "soul": ("motown", "root_fifth", "root"),
              "disco": ("octaves", "eighths", "root"), "funk": ("funk16", "octaves", "eighths"), "samba": ("bossa", "two_feel", "root_fifth"), "bossa": ("bossa", "root", "two_feel"), "marcia": ("two_feel", "root"), "metal": ("eighths", "root"), "reggae": ("reggae", "root", "root_fifth"),
              "punk": ("eighths", "root_fifth"), "lofi": ("root", "root_fifth"),
              "elettronica": ("octaves", "eighths", "root")}
_DRUM_ALTS = {"pop": ("rock", "halftime"), "ballata": ("halftime", "slow_rock_128"), "lofi": ("hiphop", "halftime"),
              "soul": ("soul", "halftime")}
# i generi i cui due accompagnamenti sono stili generici (si possono scambiare); gli altri (power chord, boom-chick, skank...) no
_SWAP_COMP = ("pop", "ballata", "jazz", "swing", "lofi", "elettronica", "soul", "ballata68", "afro68", "balcanico78", "marcia", "orchestrale")
# gli strumenti alternativi di ogni parte: il primo e' quello della ricetta; il seme puo' sceglierne un altro (stessa famiglia e,
# dove si puo', gli stessi pacchetti di suoni del genere). Per genere se il genere ha il suo suono, se no per organico.
_INSTRUMENT_ALTS_GENRE = {
    "jazz": {"melody": ("Tenor_Sax", "Alto_Sax", "Trumpet", "Clarinet", "Flute"), "comp": ("Piano", "Jazz_Guitar")},
    "swing": {"melody": ("Trumpet", "Tenor_Sax", "Clarinet", "Alto_Sax"), "comp": ("Piano", "Jazz_Guitar")},
    "pop": {"comp": ("Acoustic_Guitar_Steel", "Piano", "Nylon_Guitar"), "comp2": ("Piano", "Nylon_Guitar", "Electric_Piano_1"),
            "melody": ("Flute", "Clarinet", "Piano", "Electric_Piano_1")},
    "ballata": {"comp": ("Piano", "Acoustic_Guitar_Steel"), "comp2": ("Acoustic_Guitar_Steel", "Nylon_Guitar"),
                "melody": ("Oboe", "Clarinet", "Flute")},
    "ballata68": {"comp": ("Piano", "Nylon_Guitar"), "comp2": ("Acoustic_Guitar_Steel", "Nylon_Guitar"),
                  "melody": ("Clarinet", "Oboe", "Flute")},
    "bossa": {"comp": ("Nylon_Guitar", "Piano"), "comp2": ("Electric_Piano_1", "Piano"), "melody": ("Flute", "Tenor_Sax", "Alto_Sax")},
    "samba": {"comp": ("Nylon_Guitar", "Acoustic_Guitar_Steel"), "comp2": ("Acoustic_Guitar_Steel", "Nylon_Guitar"),
              "melody": ("Trumpet", "Flute", "Clarinet")},
    "valzer": {"comp": ("Accordion", "Strings", "Piano"), "comp2": ("Pizzicato_Strings", "Nylon_Guitar"), "melody": ("Clarinet", "Flute", "Oboe")},
    "afro68": {"comp": ("Marimba", "Kalimba", "Nylon_Guitar"), "comp2": ("Nylon_Guitar", "Acoustic_Guitar_Steel"),
               "melody": ("Flute", "Clarinet", "Violin")},
    "country": {"melody": ("Fiddle", "Acoustic_Guitar_Steel", "Harmonica"), "comp": ("Acoustic_Guitar_Steel", "Piano")},
    "soul": {"melody": ("Tenor_Sax", "Alto_Sax", "Trumpet"), "comp": ("Electric_Piano_1", "Electric_Piano_2", "Clean_Guitar"),
             "comp2": ("Drawbar_Organ", "Clean_Guitar")},
    "blues": {"melody": ("Harmonica", "Overdriven_Guitar", "Tenor_Sax")},
    "balcanico78": {"melody": ("Clarinet", "Accordion", "Violin")},
    "rock": {"melody": ("Overdriven_Guitar", "Clean_Guitar", "Rock_Organ", "Tenor_Sax"), "comp2": ("Clean_Guitar", "Rock_Organ")},
    "punk": {"melody": ("Overdriven_Guitar",)},
    "rocknroll": {"melody": ("Tenor_Sax", "Harmonica", "Trumpet"), "comp2": ("Clean_Guitar", "Rock_Organ")},
    "reggae": {"melody": ("Harmonica", "Rock_Organ", "Electric_Piano_1")},
    "funk": {"melody": ("Tenor_Sax", "Trumpet", "Overdriven_Guitar"), "bass": ("Slap_Bass_1", "Bass")},
    "lofi": {"melody": ("Vibraphone", "Flute", "Electric_Piano_2"), "comp": ("Electric_Piano_1", "Electric_Piano_2", "Piano"),
             "bass": ("Fretless_Bass", "Acoustic_Bass")},
    "elettronica": {"melody": ("Lead_2_sawtooth", "Lead", "Lead_1_square"), "comp": ("Pad_1_new_age", "Pad_2_warm", "Pad_3_polysynth"),
                    "comp2": ("Electric_Piano_1", "Electric_Piano_2", "Synth_Strings_1"), "bass": ("Synth_Bass_1", "Synth_Bass_2")},
    "orchestrale": {"melody": ("Oboe", "Flute", "Clarinet", "Trumpet", "French_Horn"), "comp2": ("Harp", "Pizzicato_Strings"),
                    "bass": ("Cello", "Contrabass")},
    "marcia": {"melody": ("Trumpet", "Clarinet", "Flute")},
    "chacha": {"melody": ("Flute", "Trumpet", "Clarinet"), "comp": ("Piano", "Electric_Piano_1"), "bass": ("Acoustic_Bass", "Bass")},
    "disco": {"melody": ("Tenor_Sax", "Trumpet", "Clean_Guitar")},
}
_INSTRUMENT_ALTS = {
    "acustica": {"melody": ("Flute", "Clarinet", "Violin", "Piano", "Acoustic_Guitar_Steel", "Alto_Sax"),
                 "comp": ("Piano", "Acoustic_Guitar_Steel", "Nylon_Guitar"), "comp2": ("Nylon_Guitar", "Piano", "Acoustic_Guitar_Steel")},
    "elettrica": {"melody": ("Lead", "Clean_Guitar", "Overdriven_Guitar", "Electric_Piano_1", "Rock_Organ"),
                  "comp": ("Clean_Guitar", "Electric_Piano_1", "Drawbar_Organ"), "comp2": ("Electric_Piano_1", "Clean_Guitar", "Drawbar_Organ", "Electric_Piano_2")},
    "elettronica": {"melody": ("Lead", "Lead_2_sawtooth", "Lead_1_square", "Polysynth"), "comp": ("Pad", "Polysynth"),
                    "comp2": ("Electric_Piano_1", "Electric_Piano_2", "Pad"), "bass": ("Synth_Bass_1", "Synth_Bass_2")},
    "orchestra": {"melody": ("Oboe", "Flute", "Clarinet", "Violin", "Trumpet", "French_Horn"), "comp2": ("Harp", "Pizzicato_Strings")},
}
# gli accompagnamenti alternativi dei generi che non hanno uno stile caratteristico (4/4)
_COMP_ALTS = {"pop": ("arpeggio_up", "broken_chord", "block_chords", "quarter_chords"), "ballata": ("arpeggio_up", "broken_chord", "sustained"),
              "lofi": ("broken_chord", "sustained", "arpeggio_up"), "elettronica": ("sustained", "arpeggio_up", "broken_chord"),
              "soul": ("soul_comp", "broken_chord", "block_chords"), "jazz": ("quarter_chords", "block_chords", "broken_chord"),
              "swing": ("quarter_chords", "block_chords", "broken_chord", "boogie_piano"),
              "blues": ("quarter_chords", "boogie_piano"), "rocknroll": ("boogie_piano", "quarter_chords"),
              "samba": ("bossa_comp", "quarter_chords"), "bossa": ("bossa_comp", "broken_chord", "arpeggio_up"), "marcia": ("quarter_chords", "boom_chick"),
              "metal": ("metal_gallop", "power_chords"), "chacha": ("montuno", "bossa_comp"), "punk": ("power_chords", "block_chords"),
              "reggae": ("skank_chords", "organ_bubble"), "country": ("boom_chick", "block_chords"), "disco": ("funk_stab", "quarter_chords", "block_chords")}
_BUSY_DRUM_GENRES = ("rock", "funk", "metal", "rocknroll", "punk", "elettronica", "disco")
_MELODY_ALTS = {"cantabile": ("cantabile", "vivace", "ballata"), "vivace": ("vivace", "cantabile"), "ballata": ("ballata", "cantabile"),
                "aaba": ("aaba", "cantabile", "vivace")}


# lo swing dei generi in terzine (8.8): la batteria e' gia' scritta in terzine; melodia, accompagnamenti, basso e fiati si scrivono
# a ottavi dritti e una parola (swing=N, o swing16=N sulle semicrome) dice come suonarli. (parola, valore, bpm di riferimento):
# nel jazz e nello swing, piu' il tempo e' veloce piu' il valore scende verso 56
_GENRE_SWING = {"jazz": ("swing", 64, 140), "swing": ("swing", 60, 160), "blues": ("swing", 66, None), "rocknroll": ("swing", 62, None),
                "samba": ("swing16", 54, None), "soul": ("swing16", 54, None), "funk": ("swing16", 54, None), "lofi": ("swing16", 57, None)}
_SWING_PARTS = ("comp", "comp2", "horn", "bass", "melody", "harm")


def swing_word(genre: str, bpm: int, override=None) -> str:
    """La parola di swing (swing=64...) da mettere in testa a un box di melodia, accompagnamento o basso; "" se il genere non la chiede.
    override: un numero da 50 (dritto) a 80, o None per il valore del genere."""
    if override not in (None, ""):
        try:
            v = max(50, min(80, int(float(override))))
        except (TypeError, ValueError):
            return ""
        word = _GENRE_SWING.get(genre, ("swing",))[0]
        return f"{word}={v}" if v != 50 else ""
    if genre not in _GENRE_SWING:
        return ""
    word, value, ref = _GENRE_SWING[genre]
    if ref:
        value = max(56, min(66, int(round(value + (ref - bpm) * 0.1))))
    return f"{word}={value}"


# gli effetti con cui parte ogni genere (8.8.4): la catena master (riga per effetto), perche' e' quella che si sente sia sul
# computer sia sul telefono, dove le tracce escono da un solo sintetizzatore. Si cambiano o si tolgono come gli altri;
# con l'opzione effects=False non si scrivono.
_GENRE_FX = {
    "rocknroll": ("riverbero: stanza=35 smorzamento=30 ampiezza=100 mix=20",),          # riverbero a molla
    "blues": ("riverbero: stanza=35 smorzamento=30 ampiezza=100 mix=20",),
    "reggae": ("delay: suddivisione=1/8p tempo=375 ripetizioni=30 mix=14",),            # delay in levare
    "lofi": ("passa_basso: frequenza=5000 pendenza=12", "eq: bassi=2 medi=0 alti=-2"),  # caldo e senza brillantezza
    "orchestrale": ("riverbero: stanza=60 smorzamento=40 ampiezza=100 mix=22",),        # riverbero di sala
    "ballata": ("riverbero: stanza=60 smorzamento=40 ampiezza=100 mix=18",),
    "funk": ("compressore: soglia=-20 rapporto=4 attacco=10 rilascio=120 guadagno=3",),  # compressione piu' marcata
    "disco": ("compressore: soglia=-20 rapporto=4 attacco=10 rilascio=120 guadagno=3",),
    "jazz": ("riverbero: stanza=25 smorzamento=50 ampiezza=100 mix=10",),                                                          # un club: asciutto ma non secco
    "swing": ("riverbero: stanza=25 smorzamento=50 ampiezza=100 mix=10",),
    "bossa": ("riverbero: stanza=25 smorzamento=50 ampiezza=100 mix=10",),
    "elettronica": ("delay: suddivisione=1/8p tempo=375 ripetizioni=30 mix=14", "riverbero: stanza=80 smorzamento=35 ampiezza=100 mix=25"),
    "pop": ("compressore: soglia=-18 rapporto=2.5 attacco=15 rilascio=150 guadagno=2", "riverbero: stanza=45 smorzamento=40 ampiezza=100 mix=14"),         # compatto e radiofonico
    "rock": ("compressore: soglia=-20 rapporto=3 attacco=12 rilascio=120 guadagno=3", "riverbero: stanza=20 smorzamento=50 ampiezza=100 mix=8"),       # potenza, niente coda
    "punk": ("compressore: soglia=-20 rapporto=3 attacco=12 rilascio=120 guadagno=3", "riverbero: stanza=20 smorzamento=50 ampiezza=100 mix=8"),
    "metal": ("compressore: soglia=-20 rapporto=3 attacco=12 rilascio=120 guadagno=3", "passa_alto: frequenza=40 pendenza=12"),                       # cassa e chitarre piu' definite
    "soul": ("riverbero: stanza=45 smorzamento=40 ampiezza=100 mix=16",),               # calore
    "country": ("riverbero: stanza=45 smorzamento=40 ampiezza=100 mix=16",),
    "valzer": ("riverbero: stanza=70 smorzamento=40 ampiezza=100 mix=22",),                                                          # spazio
    "ballata68": ("riverbero: stanza=70 smorzamento=40 ampiezza=100 mix=22",),
    "samba": ("compressore: soglia=-18 rapporto=2.5 attacco=15 rilascio=150 guadagno=2", "riverbero: stanza=20 smorzamento=50 ampiezza=100 mix=8"),        # percussioni in primo piano
    "chacha": ("compressore: soglia=-18 rapporto=2.5 attacco=15 rilascio=150 guadagno=2", "riverbero: stanza=20 smorzamento=50 ampiezza=100 mix=8"),
    "marcia": ("riverbero: stanza=55 smorzamento=45 ampiezza=100 mix=16",),               # una piazza: aria, senza coda lunga
    "balcanico78": ("riverbero: stanza=30 smorzamento=50 ampiezza=100 mix=10",),
    "afro68": ("compressore: soglia=-18 rapporto=2.5 attacco=15 rilascio=150 guadagno=2", "riverbero: stanza=20 smorzamento=50 ampiezza=100 mix=8"),
}

# il kit di batteria per genere (programma GM2 sul canale 10): nel testo un blocco «Strumento <Nome>: program=N percussione=si» e la
# traccia «Traccia Drums [<Nome>]:», che resta Drums per il mixer, la cassa da seguire e la lettura. Il nome va tradotto ma resta
# un identificatore (\w+). Funk e soul restano sul kit standard.
_GENRE_KIT = {
    "jazz": ("brush", 40), "swing": ("jazz", 32), "bossa": ("brush", 40), "ballata": ("room", 8), "ballata68": ("room", 8),
    "valzer": ("room", 8), "lofi": ("electronic", 24), "elettronica": ("electronic", 24), "disco": ("electronic", 24),
    "rock": ("power", 16), "metal": ("power", 16), "punk": ("power", 16), "marcia": ("orchestra", 48), "orchestrale": ("orchestra", 48),
    "chacha": ("jazz", 32), "reggae": ("room", 8), "balcanico78": ("room", 8),
    "blues": ("room", 8), "rocknroll": ("room", 8), "afro68": ("room", 8),
}


def _kit_name(kit: str) -> str:
    return {"brush": tr("BatteriaSpazzole"), "jazz": tr("BatteriaJazz"), "room": tr("BatteriaSala"),
            "electronic": tr("BatteriaElettronica"), "power": tr("BatteriaPotente"), "orchestra": tr("BatteriaOrchestra")}[kit]


_PLAIN_CHORD = re.compile(r"^(\d*)([A-G][#b]?)(m?)$")
_ROOT_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def _melody_scale(genre: str, tonic: int, mode: str) -> set:
    """Le note (classi di altezza) della scala che la melodia del genere usa, come in generate_phrase_melody."""
    from .melody_generate import MAJOR_SCALE, MINOR_SCALE, SCALE_KINDS
    kind = SCALE_KINDS.get(_GENRE_SCALE.get(genre, ""))
    index = 0 if mode == "major" else 1
    steps = kind[index] if kind and kind[index] else (MAJOR_SCALE if mode == "major" else MINOR_SCALE)
    return {(tonic + s) % 12 for s in steps}


def _color_chords(progression: str, tonic: int, how: str, scale=None) -> str:
    """L'armonia dell'atmosfera: le triadi semplici del giro prendono la settima ("seventh": maj7, m7 e la dominante) o la tensione
    ("tension": la tonica minore con la settima maggiore, la dominante); gli accordi che hanno gia' un colore (di settima, di nona,
    sospesi) restano come sono. Il colore lo suonano gli accompagnamenti, i tappeti, i fiati e la melodia, che lo riceve
    nei suoi accordi (ne evita le note vicine): per questo, se si passa la scala della melodia, la settima si aggiunge solo
    dove sta nella scala; altrimenti l'accordo resta una triade e melodia e accompagnamento non si contraddicono."""
    out = []
    for tok in progression.split():
        m = _PLAIN_CHORD.match(tok)
        if not m:
            out.append(tok)
            continue
        count, root, minor = m.groups()
        pc = (_ROOT_PC[root[0]] + root.count("#") - root[1:].count("b")) % 12
        degree = (pc - tonic) % 12
        if how == "seventh":
            quality = ("m7" if minor else "7" if degree == 7 else "maj7")
        else:                                                       # tension
            quality = "mMaj7" if (minor and degree == 0) else ("7" if (not minor and degree == 7) else minor)
        if scale is not None and quality != minor:
            seventh = (pc + (11 if quality in ("maj7", "mMaj7") else 10)) % 12
            if seventh not in scale:
                quality = minor                      # la settima non e' nella scala della melodia: resta la triade
        out.append(f"{count}{root}{quality}")
    return " ".join(out)


def _mood_fx(genre: str, mood: str) -> Tuple[str, ...]:
    """Gli effetti di partenza: quelli del genere, con quelli dell'atmosfera al posto di quelli dello stesso tipo (un riverbero
    sostituisce l'altro) e in piu' per gli altri."""
    rows = {r.split(":")[0]: r for r in _GENRE_FX.get(genre, ())}
    rows.update({r.split(":")[0]: r for r in _MOOD_COLOR.get(mood, {}).get("fx", ())})
    return tuple(rows.values())


# in quali sezioni suona ogni parte
_ENTER = {
    "progression": (), "comp": ("intro", "verse", "chorus", "bridge", "solo", "end", "loop", "fade"),
    "comp2": ("chorus", "bridge", "solo", "end", "loop"), "horn": ("chorus", "solo", "end"), "pad": ("chorus", "bridge", "end"), "harm": (),
    "bass": ("verse", "chorus", "bridge", "solo", "end", "loop"), "drums": ("verse", "chorus", "bridge", "solo", "end", "loop"),
    "melody": ("chorus", "solo", "end", "loop"),
}
_ENTER_FADE = ("comp",)
# le eccezioni per genere (terza revisione, 3b): {genere: {parte: ruoli in cui suona}}, al posto di quelli di _ENTER
_GENRE_ENTER = {
    "jazz": {"comp": ("intro", "verse", "chorus", "bridge", "end", "loop", "fade"),       # nell'assolo del fiato: solo basso e batteria
             "bass": ("intro", "verse", "chorus", "bridge", "solo", "end", "loop")},       # l'intro: pianoforte e contrabbasso
    "swing": {"comp": ("intro", "verse", "chorus", "bridge", "end", "loop", "fade"),
              "bass": ("intro", "verse", "chorus", "bridge", "solo", "end", "loop")},
    "reggae": {"comp2": ("verse", "chorus", "bridge", "solo", "end", "loop")},           # l'organo bubble anche nella strofa
    "funk": {"horn": ("verse", "chorus", "solo", "end")},
    # orchestrale: l'intro e' l'arpa sola, poi entrano gli archi, nel ritornello i corni
    "orchestrale": {"comp": ("verse", "chorus", "bridge", "solo", "end", "loop", "fade"),
                    "comp2": ("intro", "verse", "chorus", "bridge", "solo", "end", "loop"),
                    "horn": ("chorus", "bridge", "solo", "end")},
    # marcia e afro 6/8: l'intro e' la sola batteria (il rullo, le percussioni), poi entrano gli accordi
    "marcia": {"comp": ("verse", "chorus", "bridge", "solo", "end", "loop", "fade"), "comp2": ("chorus", "bridge", "solo", "end", "loop"),
               "drums": ("intro", "verse", "chorus", "bridge", "solo", "end", "loop")},
    "afro68": {"comp": ("verse", "chorus", "bridge", "solo", "end", "loop", "fade"),
               "drums": ("intro", "verse", "chorus", "bridge", "solo", "end", "loop")},
    "metal": {"drums": ("intro", "verse", "chorus", "bridge", "solo", "end", "loop")},                # l'attacco: batteria e riff insieme
    "punk": {"drums": ("intro", "verse", "chorus", "bridge", "solo", "end", "loop")},                 # il conto e l'attacco
    "lofi": {"comp2": ("verse", "chorus", "bridge", "solo", "end", "loop")},                          # il Rhodes da solo, poi il pad
    "bossa": {"comp2": ("verse", "chorus", "bridge", "solo", "end", "loop")},                         # la chitarra apre, il pianoforte elettrico entra dopo
    "rocknroll": {"drums": ("intro", "verse", "chorus", "bridge", "solo", "end", "loop")},            # il conto e il boogie insieme
    "samba": {"comp": ("verse", "chorus", "bridge", "solo", "end", "loop", "fade"),                 # l'intro e' la batucada, le percussioni sole
              "drums": ("intro", "verse", "chorus", "bridge", "solo", "end", "loop")},
    "chacha": {"drums": ("intro", "verse", "chorus", "bridge", "solo", "end", "loop")},               # il cowbell e le percussioni aprono col montuno
    "balcanico78": {"melody": ("intro", "chorus", "solo", "end", "loop")},                          # il clarinetto apre da solo, sopra gli accordi                                 # colpi di fiati anche nella strofa
    "ballata": {"drums": ("chorus", "bridge", "solo", "end", "loop"),                    # strofa: pianoforte e melodia soli
                "bass": ("chorus", "bridge", "solo", "end", "loop")},
    "ballata68": {"drums": ("chorus", "bridge", "solo", "end", "loop"), "bass": ("chorus", "bridge", "solo", "end", "loop")},
    "elettronica": {"comp": ("verse", "chorus", "bridge", "solo", "end", "loop", "fade"),   # l'intro e' solo batteria: poi entrano gli strati
                    "drums": ("intro", "verse", "chorus", "bridge", "solo", "end", "loop")},
}
# lo stacco per genere (3c): (dove, come, battute). "hit": colpo d'insieme sul primo tempo e silenzio; "drop": restano gli
# accordi in levare, basso e batteria tacciono; "fill": suona solo la batteria, un fill
_GENRE_BREAK = {
    "funk": ("before_last_chorus", "hit", 1), "soul": ("before_last_chorus", "hit", 1), "rock": ("before_last_chorus", "hit", 1),
    "punk": ("before_last_chorus", "hit", 1), "reggae": ("before_last_chorus", "drop", 2),
    "jazz": ("before_solo", "fill", 1), "swing": ("before_solo", "fill", 1),
    "metal": ("before_last_chorus", "hit", 1), "orchestrale": ("before_last_chorus", "hit", 1),          # il colpo d'insieme e il silenzio
    "pop": ("before_last_chorus", "drop", 1),                                                             # restano gli accordi, poi rientra tutto
    "marcia": ("before_last_chorus", "fill", 1), "afro68": ("before_last_chorus", "fill", 1),
    "elettronica": ("before_last_chorus", "drop", 1), "bossa": ("before_last_chorus", "hit", 1), "valzer": ("before_last_chorus", "hit", 1),
    "rocknroll": ("before_last_chorus", "hit", 1), "blues": ("before_solo", "hit", 1),                      # il blues: lo stacco prima del primo assolo
    "country": ("before_last_chorus", "hit", 1), "disco": ("before_last_chorus", "fill", 1),
    "samba": ("before_last_chorus", "fill", 1), "chacha": ("before_last_chorus", "fill", 1), "balcanico78": ("before_last_chorus", "hit", 1),            # il rullo e le percussioni da soli
}
_BREAK_PARTS = {"hit": ("comp", "comp2", "horn", "bass", "drums"), "drop": ("comp", "comp2"), "fill": ("drums",)}

# i finali per genere (3d): quello di partenza (se non lo si sceglie), il colore dell'ultimo accordo e i colpi finali
_GENRE_ENDING = {"funk": "sfumato", "disco": "sfumato", "reggae": "sfumato", "samba": "sfumato", "country": "rallentando",
                 "rock": "rallentando", "metal": "rallentando", "jazz": "rallentando", "orchestrale": "rallentando",
                 "afro68": "sfumato", "soul": "sfumato", "valzer": "rallentando", "ballata": "rallentando", "ballata68": "rallentando",
                 "bossa": "sfumato", "lofi": "sfumato", "elettronica": "sfumato"}
_FINAL_CHORD = {"jazz": "6", "swing": "6", "blues": "7", "rocknroll": "7", "bossa": "maj9", "country": "6"}
_FINAL_HITS = ("marcia", "chacha", "punk", "rocknroll", "swing")
_LAST_CHORD = re.compile(r"(\d*)([A-G][#b]?)([^\s|]*)(\s*\|?\s*)$")


def _color_last_chord(progression: str, quality: str) -> str:
    """L'ultimo accordo del giro con il colore del genere (C -> C6, C7, Cmaj9), se e' un accordo maggiore o di settima."""
    m = _LAST_CHORD.search(progression.rstrip())
    if not m or m.group(3) not in ("", "7", "maj7", "6", "9", "maj9"):
        return progression
    return progression.rstrip()[:m.start()] + m.group(1) + m.group(2) + quality + m.group(4)


_FINAL_INTERVAL = {"6": 9, "7": 10, "maj9": 2}
_NOTE_IN_CHORD = re.compile(r"([a-g][#b]?)\*(\d)")


_FINAL_SYMBOL = re.compile(r"^(\d*)([A-G][#b]?)(|maj7|7|6|9|maj9)(\*\d+)?$")
_CHORD_TOKEN = re.compile(r"(?<![\w\]\[=])(\d*\[[^\[\]]+\]|\d*[A-G][#b]?[A-Za-z0-9]*(?:\*\d+)?)(?![\w\]\[=@:])")


def _color_last_voicing(body: str, key: str, quality: str) -> str:
    """L'ultimo accordo dell'accompagnamento con il colore del genere (la sesta, la settima o la nona della tonica): il giro finisce
    su C6, C7 o Cmaj9 e l'accompagnamento lo fa sentire. L'ultimo accordo e' un simbolo («C», «Cmaj7»: il colore prende il posto della
    qualita') o un blocco di note (la nota di colore va sotto la piu' alta). Solo in maggiore: sulla tonica minore la sesta maggiore
    stride. Un ultimo accordo che non e' quello della tonica resta com'e'."""
    from .rhythm_generate import _note_token, parse_key
    if quality not in _FINAL_INTERVAL:
        return body
    tonic, mode, _flats = parse_key(key)
    if mode != "major":
        return body
    chords = list(_CHORD_TOKEN.finditer(body))
    if not chords:
        return body
    last = chords[-1]
    token = last.group(1)
    names = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}
    m = _FINAL_SYMBOL.match(token)
    if m:
        root = (_ROOT_PC[m.group(2)[0]] + m.group(2).count("#") - m.group(2)[1:].count("b")) % 12
        if root != tonic % 12:
            return body
        return body[:last.start(1)] + m.group(1) + m.group(2) + quality + (m.group(4) or "") + body[last.end(1):]
    inner = re.match(r"\d*\[([^\]]+)\]$", token)
    if not inner:
        return body
    notes = [12 * (int(o) + 1) + names[n[0]] + n.count("#") - n[1:].count("b") for n, o in _NOTE_IN_CHORD.findall(inner.group(1))]
    if not notes or notes[0] % 12 != tonic % 12 and tonic % 12 not in {n % 12 for n in notes}:
        return body                                       # l'ultimo accordo non e' quello della tonica
    color = (tonic + _FINAL_INTERVAL[quality]) % 12
    if color in {n % 12 for n in notes}:
        return body
    top = max(notes)
    pitch = top - ((top - color) % 12 or 12)
    if pitch < min(notes):
        return body
    tokens = inner.group(1).split() + [_note_token(pitch % 12, pitch // 12 - 1)]
    tokens.sort(key=lambda t: 12 * (int(t.split("*")[1]) + 1) + names[t[0]] + t.split("*")[0].count("#") - t.split("*")[0][1:].count("b"))
    mult = re.match(r"\d*", token).group(0)
    return body[:last.start(1)] + mult + "[" + " ".join(tokens) + "]" + body[last.end(1):]


def _final_hits(drums: str) -> str:
    """I tre colpi finali della marcia (ta-ta-ta'): al posto del colpo solo dell'ultima battuta, tre colpi a crome."""
    tail = re.search(r"(\d+@ )?\[crash kick\] 15r\s*$", drums)
    if not drums.lstrip().startswith("16:") or not tail:
        return drums
    return drums[:tail.start()] + "100@ [snare kick] r 105@ [snare kick] r 120@ [crash kick] 11r"


# la seconda voce del genere (2c): terze o seste parallele sotto la melodia, nei ritornelli (con lo sviluppo del tema)
_GENRE_SECOND_VOICE = {"marcia": "thirds", "afro68": "thirds", "pop": "thirds", "country": "thirds", "soul": "thirds", "orchestrale": "thirds", "ballata": "thirds", "bossa": "thirds", "chacha": "thirds", "balcanico78": "thirds",
                       "valzer": "sixths", "ballata68": "sixths"}

# la melodia della strofa (3a): piu' rada del ritornello, che resta il culmine; non nei brani brevissimi
_VERSE_MELODY_STYLE = {"melody_lively": "melody_period", "melody_period": "melody_ballad", "melody_aaba": "melody_period",
                       "melody_ballad": "melody_ballad"}


def _enters(genre: str, part: str, verse_melody: bool = False) -> Tuple[str, ...]:
    """I ruoli delle sezioni in cui suona una parte: quelli del genere o quelli di sempre (con la strofa per la melodia)."""
    roles = _GENRE_ENTER.get(genre, {}).get(part, _ENTER[part])
    if part == "melody" and verse_melody and "verse" not in roles:
        roles = roles + ("verse",)
    return roles


# ------------------------------------------------------------ etichette

def _genre_labels() -> Dict[str, str]:
    return {"pop": tr("Pop"), "rock": tr("Rock"), "ballata": tr("Ballata"), "bossa": tr("Bossa nova"), "jazz": tr("Jazz"),
            "swing": tr("Swing"), "funk": tr("Funk"), "soul": tr("Soul"), "disco": tr("Disco"), "lofi": tr("Lo-fi"),
            "elettronica": tr("Elettronica"), "orchestrale": tr("Orchestrale"), "blues": tr("Blues"), "reggae": tr("Reggae"),
            "country": tr("Country"), "punk": tr("Punk"), "metal": tr("Metal"), "rocknroll": tr("Rock'n'roll"),
            "samba": tr("Samba"), "chacha": tr("Cha-cha-cha"), "valzer": tr("Valzer"), "marcia": tr("Marcia"),
            "ballata68": tr("Ballata 6/8"), "afro68": tr("Etnico 6/8"), "balcanico78": tr("Balcanico 7/8")}


def _mood_labels() -> Dict[str, str]:
    return {"allegra": tr("allegra"), "malinconica": tr("malinconica"), "tesa": tr("tesa"), "epica": tr("epica"),
            "calma": tr("calma"), "sognante": tr("sognante"), "misteriosa": tr("misteriosa"), "romantica": tr("romantica"),
            "nostalgica": tr("nostalgica"), "festosa": tr("festosa"), "oscura": tr("oscura"), "giocosa": tr("giocosa"),
            "solenne": tr("solenne"), "drammatica": tr("drammatica"), "serena": tr("serena"), "energica": tr("energica"),
            "sensuale": tr("sensuale"), "avventurosa": tr("avventurosa"), "ipnotica": tr("ipnotica"),
            "intima": tr("intima"), "grintosa": tr("grintosa"), "elegante": tr("elegante")}


def _form_labels() -> Dict[str, str]:
    return {"loop": tr("loop di 8 battute"), "canzone": tr("strofa e ritornello"), "aaba": tr("AABA"),
            "blues": tr("blues di 12 battute"), "ponte": tr("canzone con ponte")}


def _ensemble_labels() -> Dict[str, str]:
    return {"piano": tr("solo piano"), "acustica": tr("band acustica"), "elettrica": tr("band elettrica"),
            "elettronica": tr("elettronico"), "orchestra": tr("orchestra")}


def _melody_labels() -> Dict[str, str]:
    return {"nessuna": tr("nessuna"), "cantabile": tr("cantabile"), "vivace": tr("vivace"), "ballata": tr("ballata"),
            "aaba": tr("AABA")}


def _energy_labels() -> Dict[str, str]:
    return {"sale": tr("sale"), "picco": tr("sale e poi cala"), "cala": tr("cala")}


def _ending_labels() -> Dict[str, str]:
    return {"cadenza": tr("cadenza"), "rallentando": tr("rallentando"), "sfumato": tr("sfumato")}


def _part_labels() -> Dict[str, str]:
    return {"progression": tr("Giro armonico"), "comp": tr("Accompagnamento"), "comp2": tr("Secondo accompagnamento"),
            "horn": tr("Ottoni"), "pad": tr("Archi (strato)"), "harm": tr("Seconda voce"), "bass": tr("Basso"), "drums": tr("Batteria"), "melody": tr("Melodia")}


def _duration_label(seconds: int) -> str:
    if seconds < 60:
        return tr("{n} secondi", n=seconds)
    minutes, rest = divmod(seconds, 60)
    if rest == 0:
        return tr("1 minuto") if minutes == 1 else tr("{n} minuti", n=minutes)
    return tr("{m} min {s} s", m=minutes, s=rest)


def quick_choices() -> dict:
    """Le scelte di «Un brano in 60 secondi» con le etichette nella lingua dell'interfaccia, e per ogni genere
    quello che la sua ricetta prevede: metrica, tempo, atmosfere ammesse, forma, organico e gli stili delle parti."""
    from core import rhythm_generate as rg
    from core.generate_labels import generator_labels
    labels = generator_labels()
    genre_labels, mood_labels = _genre_labels(), _mood_labels()
    styles = {"drums": [{"value": v, "label": l} for v, l in labels["drums"]],
              "bass": [{"value": v, "label": l} for v, l in labels["bass"]],
              "comp": [{"value": v, "label": l} for v, l in labels["comping"]],
              "progression": [{"value": v, "label": l, "mode": rg.PROGRESSION_STYLES[v]["mode"]} for v, l in labels["progression"]]}
    # gli stili personali importati dal computer (engine.install_user_styles) si aggiungono alle liste
    try:
        from core import user_styles as us
        for target, kind in (("drums", "drums"), ("bass", "bass"), ("comp", "comping")):
            for name in us.user_style_names(kind):
                styles[target].append({"value": us.style_key(name), "label": tr("{name} (personale)", name=name)})
    except Exception:
        pass
    genres = []
    for g in GENRES:
        d = GENRES_DATA[g]
        genres.append({"value": g, "label": genre_labels[g], "meter": d["meter"], "bpm": d["bpm"], "moods": list(d["moods"]),
                       "form": d["form"], "ensemble": d["ens"], "melody": d["melody"], "drums": d["drums"] or "", "bass": d["bass"],
                       "comp": d["comp"]})
    keys = ("C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B", "Cm", "C#m", "Dm", "Ebm", "Em", "Fm", "F#m", "Gm", "G#m", "Am", "Bbm", "Bm")
    return {"genres": genres, "moods": [{"value": m, "label": mood_labels[m]} for m in MOODS],
            "durations": [{"value": d, "label": _duration_label(d)} for d in DURATIONS],
            "forms": [{"value": f, "label": l} for f, l in _form_labels().items()],
            "ensembles": [{"value": e, "label": l} for e, l in _ensemble_labels().items()],
            "melodies": [{"value": m, "label": l} for m, l in _melody_labels().items()],
            "endings": [{"value": e, "label": l} for e, l in _ending_labels().items()],
            "energies": [{"value": e, "label": l} for e, l in _energy_labels().items()],
            "parts": [{"value": p, "label": l} for p, l in _part_labels().items()],
            "meters": ["4/4", "3/4", "6/8", "7/8"], "keys": list(keys), "styles": styles,
            "drum_styles_by_meter": {m: rg.drum_styles_for_meter(m) for m in ("4/4", "3/4", "6/8", "7/8")}}


# ------------------------------------------------------------ chiavi e atmosfere

_NAMES_SHARP = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
_NAMES_FLAT = ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B")
_KEYS = {"major": ("C", "G", "D", "F", "A", "Bb"), "minor": ("Am", "Em", "Dm", "Gm", "Bm", "Cm")}


def _shift_key(key: str, semitones: int) -> str:
    """La tonalita' un tot di semitoni sopra, con lo stesso modo."""
    from core.rhythm_generate import parse_key
    tonic, mode, flats = parse_key(key)
    target = (tonic + semitones) % 12
    # come si scrive di solito: Fa, Sib, Mib, Lab, Reb maggiori e Rem, Solm, Dom, Fam, Sibm, Mibm minori con i bemolli
    flat = target in ((5, 10, 3, 8, 1) if mode == "major" else (2, 7, 0, 5, 10, 3))
    return (_NAMES_FLAT if flat else _NAMES_SHARP)[target] + ("m" if mode == "minor" else "")


def _nearest_mood(mood: str, allowed) -> str:
    """L'atmosfera ammessa piu' vicina: stesso modo, energia simile."""
    mode, _tempo, _int, _prog, energy = MOODS_DATA[mood]
    return min(allowed, key=lambda m: ((MOODS_DATA[m][0] != mode) * 10 + abs(MOODS_DATA[m][4] - energy), MOODS.index(m)))


# ------------------------------------------------------------ la forma

def _blocks(*items):
    return tuple(items)                                 # i nomi sono gia' tradotti: tr() qui sotto, cosi' l'estrattore li trova


def _phrases(bars: float, minimum: int = 4) -> int:
    """Battute a frasi intere (multipli di 4)."""
    return max(minimum, int(round(bars / 4.0)) * 4)


def _form_sections(form: str, target: int, loops: Optional[int] = None, short: bool = False) -> List[Tuple[str, str, int]]:
    """Le sezioni (nome, ruolo, battute) di una forma per un brano di circa 'target' battute. Con 'short' (fino a 20 secondi)
    la forma a strofa e ritornello e' una frase sola, senza intro."""
    if form == "loop":
        if not loops and target <= 6:                       # un brano brevissimo: mezzo loop
            return [(tr("Loop {n}", n=1), "loop", 4)]
        n = loops or max(1, int(round(target / 8.0)))
        return [(tr("Loop {n}", n=i + 1), "loop", 8) for i in range(n)]
    if form == "blues":
        if target < 10:                                     # meno di un giro: le prime battute del giro di blues
            return [(tr("Giro {n}", n=1), "chorus", _phrases(target, 4))]
        n = max(1, int(round(target / 12.0)))
        out = []
        for i in range(n):
            role = "chorus" if n == 1 else "end" if i == n - 1 else "solo" if 0 < i < n - 1 else "verse"
            out.append((tr("Giro {n}", n=i + 1), role, 12))              # un giro solo: suona anche la melodia
        return out
    if form == "aaba":
        reps = max(1, int(round(target / 32.0)))
        if target < 20:
            return [(tr("A"), "verse", 8), (tr("B"), "bridge", 8)][: 1 if target < 12 else 2]
        out = []
        for i in range(reps):
            last = i == reps - 1
            out += [(tr("A"), "verse", 8), (tr("A"), "verse", 8), (tr("B"), "bridge", 8), (tr("A"), "end" if last else "chorus", 8)]
        return out
    # strofa e ritornello (e con il ponte): una scala di forme di durata crescente
    bridge = form == "ponte"
    ladder = [
        (6, _blocks((tr("Frase"), "chorus", 4))),                      # 15 s: una sola frase, con tutte le parti, senza intro
        (8, _blocks((tr("Strofa"), "verse", 4), (tr("Ritornello"), "chorus", 4))),
        (12, _blocks((tr("Intro"), "intro", 2), (tr("Strofa"), "verse", 4), (tr("Ritornello"), "chorus", 4), (tr("Finale"), "end", 2))),
        (24, _blocks((tr("Intro"), "intro", 4), (tr("Strofa"), "verse", 8), (tr("Ritornello"), "chorus", 8), (tr("Finale"), "end", 4))),
        (40, _blocks((tr("Intro"), "intro", 4), (tr("Strofa"), "verse", 8), (tr("Ritornello"), "chorus", 8), (tr("Strofa"), "verse", 8),
                     (tr("Ritornello"), "chorus", 8), (tr("Finale"), "end", 4))),
        (56, _blocks((tr("Intro"), "intro", 4), (tr("Strofa"), "verse", 8), (tr("Ritornello"), "chorus", 8), (tr("Strofa"), "verse", 8),
                     (tr("Ritornello"), "chorus", 8), (tr("Ponte"), "bridge", 8), (tr("Ritornello"), "chorus", 8), (tr("Finale"), "end", 4))),
        (80, _blocks((tr("Intro"), "intro", 4), (tr("Strofa"), "verse", 8), (tr("Ritornello"), "chorus", 8), (tr("Strofa"), "verse", 8),
                     (tr("Ritornello"), "chorus", 8), (tr("Ponte"), "bridge", 8), (tr("Assolo"), "solo", 16), (tr("Ritornello"), "chorus", 8),
                     (tr("Ritornello"), "chorus", 8), (tr("Finale"), "end", 4))),
        (112, _blocks((tr("Intro"), "intro", 8), (tr("Strofa"), "verse", 8), (tr("Ritornello"), "chorus", 8), (tr("Strofa"), "verse", 8),
                      (tr("Ritornello"), "chorus", 8), (tr("Ponte"), "bridge", 8), (tr("Assolo"), "solo", 16), (tr("Strofa"), "verse", 8),
                      (tr("Ritornello"), "chorus", 8), (tr("Ritornello"), "chorus", 8), (tr("Ritornello"), "chorus", 8), (tr("Finale"), "end", 8))),
    ]
    best = min(ladder[:2] if short else ladder, key=lambda item: abs(item[0] - target))
    sections = list(best[1])
    if not bridge:                                     # senza ponte: il ponte e' una strofa in piu'
        sections = [(tr("Strofa"), "verse", b) if n == tr("Ponte") else (n, r, b) for n, r, b in sections]
    return sections


# ------------------------------------------------------------ opzioni

def _int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def resolve(options: Optional[dict] = None) -> dict:
    """Le scelte di un brano, tutte decise: quelle date, e per le altre i valori della ricetta del genere."""
    import random as _random
    from core import rhythm_generate as rg
    options = dict(options or {})
    genre = options.get("genre", "pop")
    if genre not in GENRES_DATA:
        raise ValueError(f"genere sconosciuto: {genre}")
    recipe = GENRES_DATA[genre]
    mood = options.get("mood", "allegra")
    if mood not in MOODS_DATA:
        raise ValueError(f"atmosfera sconosciuta: {mood}")
    fallback = ""
    if mood not in recipe["moods"]:
        near = _nearest_mood(mood, recipe["moods"])
        labels, moods = _genre_labels(), _mood_labels()
        fallback = tr("«{genre} {mood}» non c'è: ho scelto «{genre} {other}».", genre=labels[genre], mood=moods[mood], other=moods[near])
        mood = near
    seed = options.get("seed")
    seed = _random.randrange(2 ** 31) if seed is None or seed == "" else _int(seed, 0)
    rng = _random.Random(seed)

    parts_in = dict(options.get("parts") or {})
    seeds = {}
    for part in PARTS:
        given = (parts_in.get(part) or {}).get("seed")
        seeds[part] = _int(given, 0) if given not in (None, "") else _random.Random(f"{seed}/{part}").randrange(2 ** 31)
    mode, tempo_factor, intensities, mood_prog, _energy = MOODS_DATA[mood]
    key = options.get("key") or ""
    if options.get("chords"):
        _written_symbols(str(options["chords"]))            # un giro illeggibile si ferma qui, prima di scegliere tonalita' e modo
    if not key and options.get("chords"):
        key = _key_of_chords(str(options["chords"]))         # il giro scritto a mano decide la tonalita' (altrimenti e' a caso)
    minor_mood_in_major = not key and mode == "minor" and genre in _MAJOR_GENRES
    if minor_mood_in_major:
        mode = "major"                                       # il country e' in maggiore: la grinta la danno il tempo, la batteria e il bVII
    if key:
        mode = rg.parse_key(key)[1]
        prog_mood = mood if MOODS_DATA[mood][0] == mode else ("malinconica" if mode == "minor" else "allegra")
    else:
        key = rng.choice(_KEYS[mode])
        prog_mood = mood
    prog_triple = (recipe.get("prog") or {}).get(mode) or MOODS_DATA[prog_mood][3]
    if minor_mood_in_major:
        prog_triple = _MAJOR_GENRES[genre]
    variety = _float(options.get("variety"), 1.0)            # 0 = la ricetta pura, 1 = tutta la variabilita'
    # ogni scelta fra alternative dipende dal seme della sua parte: un lucchetto (stesso seme) tiene la sua parte uguale
    vrng = _random.Random(f"{seeds['progression']}/variety")                    # giri armonici, tempo e forma
    part_rng = {part: _random.Random(f"{seeds[part]}/variety") for part in PARTS}
    if variety > 0 and not options.get("chords") and _PROG_POOL_OF.get(genre, "default") is not None:
        pool = _PROG_POOLS[_PROG_POOL_OF.get(genre, "default")][mode]
        prog_triple = tuple(vrng.choice(pool) if vrng.random() < 0.75 * variety else base for base in prog_triple)
    meter = options.get("meter") or recipe["meter"]
    bpm = _int(options.get("bpm"), 0) or int(round(recipe["bpm"] * tempo_factor * (1 + variety * vrng.uniform(-0.08, 0.08))))
    bpm = max(40, min(240, bpm))

    drum_styles = rg.drum_styles_for_meter(meter)
    drums = options.get("drums") or recipe["drums"]
    if not options.get("drums") and variety > 0 and genre in _DRUM_ALTS and part_rng["drums"].random() < 0.6 * variety:
        drums = part_rng["drums"].choice(_DRUM_ALTS[genre])
    if drums is not None and drums not in drum_styles:
        drums = drum_styles[0] if drum_styles else None      # lo stile non esiste per questa metrica
    # ogni quante battute un fill (di solito 4: ogni tanto ogni 8, per un groove piu' disteso, o ogni 2 nei generi nervosi)
    drum_fill = 4
    if variety > 0 and part_rng["drums"].random() < 0.5 * variety:
        drum_fill = part_rng["drums"].choice((8, 8, 2) if genre in _BUSY_DRUM_GENRES else (8, 8))
    if not options.get("drums") and _MOOD_COLOR.get(mood, {}).get("drums") in drum_styles and genre in _MOOD_DRUM_GENRES:
        drums = _MOOD_COLOR[mood]["drums"]                   # le atmosfere quiete suonano a meta' tempo
    if _MOOD_COLOR.get(mood, {}).get("fill"):
        drum_fill = _MOOD_COLOR[mood]["fill"]                # meno fill nelle atmosfere raccolte, di piu' in quelle agitate
    ensemble = options.get("ensemble") or recipe["ens"]
    if ensemble not in _ENSEMBLE_PARTS:
        raise ValueError(f"organico sconosciuto: {ensemble}")
    melody = options.get("melody", recipe["melody"])
    if melody is True:
        melody = recipe["melody"]
    if melody is False or melody in ("", None):
        melody = "nessuna"
    if "melody" not in options and variety > 0 and melody in _MELODY_ALTS and part_rng["melody"].random() < 0.5 * variety:
        melody = part_rng["melody"].choice(_MELODY_ALTS[melody])
    if melody not in _MELODY_STYLE and melody != "nessuna":
        raise ValueError(f"stile di melodia sconosciuto: {melody}")
    color = _MOOD_COLOR.get(mood, {})
    if "melody" not in options and color.get("melody_style") and melody not in ("nessuna", "aaba"):
        melody = color["melody_style"]                       # la calma canta piano, l'energia a ottavi: lo stile della melodia segue l'atmosfera
    form = options.get("form") or recipe["form"]
    if not options.get("form") and variety > 0 and recipe["form"] in ("canzone", "ponte") and vrng.random() < 0.4 * variety:
        form = "ponte" if recipe["form"] == "canzone" else "canzone"
    if form not in FORMS:
        raise ValueError(f"forma sconosciuta: {form}")
    ending = options.get("ending") or ("cadenza" if options.get("loop") else _GENRE_ENDING.get(genre, "cadenza"))   # un loop si ripete: niente sfumato
    mood_ending = _MOOD_COLOR.get(mood, {}).get("ending")
    if mood_ending and not options.get("ending") and not options.get("loop"):
        ending = mood_ending                                # l'atmosfera, piu' specifica, vince sul finale di partenza del genere
    if ending == "sfumato" and not options.get("ending") and (options.get("duration") or 60) < 45:
        ending = "cadenza"                                  # lo sfumato aggiunge 4 battute: non nei brani corti
    if not options.get("ending") and variety > 0 and genre not in _GENRE_ENDING and not mood_ending:
        roll = vrng.random()
        if roll < 0.15 * variety:
            ending = "rallentando"
        elif roll < 0.25 * variety and (options.get("duration") or 60) >= 45:       # lo sfumato aggiunge 4 battute: non nei brani corti
            ending = "sfumato"
    if ending not in ENDINGS:
        raise ValueError(f"finale sconosciuto: {ending}")

    density = options.get("density")
    if density is None and variety > 0:
        density = 0.5 + random.Random(f"{seeds['progression']}/density").uniform(-0.25, 0.25) * variety    # piu' o meno pieno
    density = 0.5 if density is None else max(0.0, min(1.0, float(density)))
    bass_style, comp_style, comp2_style = recipe["bass"], recipe["comp"], recipe["comp2"]
    if variety > 0 and meter == "4/4":
        if genre in _BASS_ALTS and part_rng["bass"].random() < 0.5 * variety:
            bass_style = part_rng["bass"].choice(_BASS_ALTS[genre])
        if genre in _SWAP_COMP and part_rng["comp"].random() < 0.35 * variety:
            comp_style, comp2_style = comp2_style, comp_style           # i due accompagnamenti si scambiano
        elif genre in _COMP_ALTS:
            crng = random.Random(f"{seeds['comp']}/stile")
            if crng.random() < 0.5 * variety:
                comp_style = crng.choice([x for x in _COMP_ALTS[genre] if x != comp2_style] or _COMP_ALTS[genre])
    styles = {"drums": drums, "bass": bass_style, "comp": comp_style, "comp2": comp2_style, "horn": _HORN_STYLE.get(genre, "sustained"), "pad": "sustained",
              "progression": None}
    for part, spec in parts_in.items():
        if part in styles and spec.get("style"):
            styles[part] = spec["style"]
    instruments = dict(_ENSEMBLE_PARTS[ensemble])
    if recipe.get("dist") and ensemble == "elettrica":
        instruments["comp"] = "Distortion_Guitar"
    if ensemble == recipe["ens"]:                            # gli strumenti del genere (8.8.1)
        for part, name in _GENRE_INSTRUMENTS.get(genre, {}).items():
            if name is None:
                instruments.pop(part, None)
            elif not (part == "comp" and name == "Overdriven_Guitar" and instruments.get("comp") == "Distortion_Guitar"):
                instruments[part] = name
    if styles["comp"] == "boogie_piano" and instruments.get("comp") not in (None, "Piano"):
        instruments["comp"] = "Piano"                        # il boogie-woogie si suona al pianoforte
    if variety > 0:                                          # strumenti alternativi (sceglie il seme di ogni parte)
        genre_alts = _INSTRUMENT_ALTS_GENRE.get(genre, {}) if ensemble == recipe["ens"] else {}
        for part in ("comp", "comp2", "melody", "bass"):
            pool = genre_alts.get(part) or _INSTRUMENT_ALTS.get(ensemble, {}).get(part)
            if part == "melody" and recipe.get("dist") and ensemble == "elettrica" and not genre_alts.get("melody"):
                pool = ("Overdriven_Guitar",)                # niente tastiere nei generi distorti
            current = instruments.get(part)
            if not pool or current not in pool:
                continue                                     # lo strumento del genere (clavinet, chitarra distorta...) non si tocca
            irng = random.Random(f"{seeds[part]}/strumento")
            if irng.random() < 0.6 * variety:
                taken = {name for other, name in instruments.items() if other != part}      # anche fiati, tappeto e basso: due parti, due strumenti
                choices = [x for x in pool if x != current and x not in taken]
                if choices:
                    instruments[part] = irng.choice(choices)
    color = _MOOD_COLOR.get(mood, {})
    if color.get("tone") and genre not in _NO_TONE_GENRES and ensemble == recipe["ens"] and "melody" in instruments \
            and not (parts_in.get("melody") or {}).get("instrument"):
        wanted = _TONE[color["tone"]]
        pool = (_INSTRUMENT_ALTS_GENRE.get(genre, {}).get("melody") or _INSTRUMENT_ALTS.get(ensemble, {}).get("melody") or ())
        if instruments["melody"] not in wanted:
            taken = {instruments.get(o) for o in ("comp", "comp2", "bass", "horn", "pad")}
            pick = next((x for x in pool if x in wanted and x not in taken), None)
            if pick:
                instruments["melody"] = pick
    for extra, part in (("add_pad", "pad"), ("add_horn", "horn")):       # l'atmosfera porta una parte in piu': un tappeto, i fiati
        name = color.get(extra)
        if name and genre in _ADD_PART_GENRES and part not in instruments and name not in instruments.values():
            instruments[part] = name
    if drums is not None and "drums" not in instruments and (options.get("drums") or recipe.get("drums_in_orchestra")):
        instruments["drums"] = "Drums"                       # l'orchestra non ha la batteria, salvo una marcia o se la si sceglie
    if drums is None:
        instruments.pop("drums", None)
    for part, spec in parts_in.items():
        if spec.get("instrument") and part in instruments:
            instruments[part] = spec["instrument"]
    formation = [str(name) for name in (options.get("formation") or [])]
    left_out: List[str] = []
    if formation:                                            # gli strumenti scelti uno per uno al posto dell'organico
        from .quick_formation import assign
        instruments, left_out = assign(formation)
        if "drums" in instruments:
            if drums is None:
                drums = drum_styles[0] if drum_styles else None      # un genere senza batteria (l'orchestrale): uno stile per la metrica
            if drums is None:
                instruments.pop("drums")
        else:
            drums = None
        styles["drums"] = drums
        if "melody" not in instruments:
            melody = "nessuna"
        elif melody == "nessuna":
            melody = recipe["melody"] if recipe["melody"] in _MELODY_STYLE else "cantabile"
    return {"genre": genre, "mood": mood, "requested_mood": options.get("mood", "allegra"), "fallback": fallback, "seed": seed, "key": key,
            "mode": mode, "bpm": bpm, "meter": meter, "form": form, "ensemble": ensemble, "melody": melody, "ending": ending,
            "modulation": bool(options["modulation"]) if "modulation" in options else
                          bool(_MOOD_COLOR.get(mood, {}).get("modulation")) and (options.get("duration") or 60) >= 60 and not options.get("loop"),
            "density": density, "loop": bool(options.get("loop")),
            "duration": options.get("duration"), "bars": _int(options.get("bars"), 0), "variability": options.get("variability"),
            "prog": list(prog_triple), "intensities": list(intensities), "styles": styles, "instruments": instruments, "seeds": seeds,
            "chords": str(options.get("chords") or "").strip(), "parts": parts_in, "drum_fill": drum_fill,
            "formation": formation, "left_out": left_out}


# ------------------------------------------------------------ il brano

_LEVELS = ("light", "normal", "full")


_ORGAN_VELOCITY = 0.68
# Misurato col pacchetto di suoni del telefono (FluidSynth, un brano per genere): a pari velocity questi strumenti, con gli accordi a
# 4-6 note, stanno 3-7 dB sopra il basso e la melodia e hanno picchi vicini al fondo scala. La velocity scritta si riduce di questo fattore.
_INSTRUMENT_VELOCITY = {"Jazz_Guitar": 0.78, "Electric_Piano_1": 0.8, "Overdriven_Guitar": 0.65}


def _instrument_velocity(name) -> float:
    name = str(name)
    if "Organ" in name:                                    # l'organo tiene le note lunghe e a pari velocity copre tutto
        return _ORGAN_VELOCITY
    return _INSTRUMENT_VELOCITY.get(name, 1.0)


def _scale_velocity(text: str, factor: float) -> str:
    return re.sub(r"(\d+)@", lambda m: f"{max(1, min(127, int(int(m.group(1)) * factor)))}@", text)


_KEY_NAMES = ("C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B")


def _written_symbols(written: str) -> List[str]:
    """I simboli del giro scritto a mano («Am F C G», anche con virgole o stanghette); ValueError se uno non e' un accordo."""
    from core.chords import parse_chord_symbol
    symbols = [s for s in re.split(r"[\s,|]+", written) if s]
    for symbol in symbols:
        parse_chord_symbol(symbol)
    return symbols


def _key_of_chords(written: str) -> str:
    """La tonalita' che meglio spiega un giro scritto a mano («Am F C G» -> «Am» o «C»), come la stima della melodia;
    '' se il giro non si legge (l'errore lo dara' _chord_loop)."""
    from core.chords import parse_chord_symbol
    from .melody_generate import estimate_key
    from .rhythm_generate import ChordSpan
    spans = []
    try:
        for i, symbol in enumerate(s for s in re.split(r"[\s,|]+", written) if s):
            chord = parse_chord_symbol(symbol)
            third = 3 if 3 in chord.intervals else 4 if 4 in chord.intervals else None
            seventh = 11 if 11 in chord.intervals else 10 if 10 in chord.intervals else None
            spans.append(ChordSpan(float(i), 1.0, chord.root_pc, 7 in chord.intervals, third, seventh))
    except ValueError:
        return ""
    if not spans:
        return ""
    tonic, mode = estimate_key(spans)
    return _KEY_NAMES[tonic] + ("m" if mode == "minor" else "")


def _tonic_progression(progression: str, key: str) -> str:
    """Il giro con ogni accordo sostituito dall'accordo della tonica («Am F C G» in La minore -> «Am Am Am Am»): il basso del pedale
    tiene la tonica sotto gli accordi che cambiano, con la fondamentale (e la quinta) della tonica."""
    from .rhythm_generate import parse_key
    tonic, mode, _flats = parse_key(key)
    symbol = _KEY_NAMES[tonic] + ("m" if mode == "minor" else "")
    return " ".join(re.sub(r"^(\d*)[A-G][#b]?\S*$", lambda m: m.group(1) + symbol, tok) if not tok.endswith((":", "@")) else tok
                    for tok in progression.split())


_SYMBOL_NOTE = re.compile(r"([A-G][#b]?)")


def _transpose_symbol(symbol: str, semitones: int) -> str:
    """Un simbolo d'accordo («Am7», «C/E») trasposto di 'semitones': la fondamentale e l'eventuale basso dopo la barra."""
    if not semitones % 12:
        return symbol

    def move(m):
        pc = (_ROOT_PC[m.group(1)[0]] + m.group(1).count("#") - m.group(1)[1:].count("b") + semitones) % 12
        return _KEY_NAMES[pc]
    head, slash, bass = symbol.partition("/")
    head = _SYMBOL_NOTE.sub(move, head, count=1)
    return head + slash + (_SYMBOL_NOTE.sub(move, bass, count=1) if bass else "")


def _chord_loop(written: str, bars: int, bar_beats: float = 4.0, transpose: int = 0) -> Optional[str]:
    """Il giro scritto a mano («Am F C G») ripetuto per 'bars' battute, come testo di accordi: un accordo per battuta intera,
    qualunque sia la metrica (la griglia e' l'ottavo, e ogni accordo dura quanti ottavi ha la battuta), trasposto di
    'transpose' semitoni quando il brano modula."""
    symbols = _written_symbols(written)                     # ValueError se non e' un accordo
    if not symbols:
        return None
    eighths = max(1, int(round(bar_beats * 2)))
    return "8: " + " ".join(f"{eighths}{_transpose_symbol(symbols[i % len(symbols)], transpose)}" for i in range(bars))


def quick_song(options: Optional[dict] = None) -> dict:
    """Un brano completo.

    options (tutte facoltative): genre, mood, duration (secondi; oppure bars o loop), seed, key, bpm, meter, form, ensemble,
    melody ('nessuna' o uno stile), ending, modulation, density (0-1, piu' semplice o piu' ricco), chords (un giro scritto a
    mano), variability, e parts: {parte: {seed, style, instrument}} per le scelte di ogni parte (PARTS).
    Restituisce {text, name, seed, key, bpm, meter, bars, seconds, genre, mood, form, ensemble, fallback, sections, loop,
    seeds, choices}."""
    from . import song_generate as E
    from .rhythm_generate import parse_key as rg_parse_key
    parse_key_now = lambda k: tuple(rg_parse_key(k)[:2])
    from core.i18n import tr as _tr
    from core.instruments import make_instrument_available
    from core.project_io import parse_project_text
    c = resolve(options)
    meter, bpm, key = c["meter"], c["bpm"], c["key"]
    header = lambda k: f"ST: 2.6\nTempo: {bpm} BPM\nMetrica: {meter}\nTonalita: {k}\n\n"
    bar_beats = E._bar_beats(parse_project_text(header(key), "Brano"))
    beats_per_bar = bar_beats

    # la durata: secondi -> battute, a frasi intere
    if c["bars"]:
        target = c["bars"]
    elif c["duration"]:
        target = _phrases(float(c["duration"]) * bpm / 60.0 / beats_per_bar, 4)
    else:
        target = _phrases(60.0 * bpm / 60.0 / beats_per_bar, 4)
    form = "loop" if c["loop"] else c["form"]
    loops = 4 if c["loop"] else None
    short = bool(c["duration"]) and float(c["duration"]) <= 20 and not c["bars"]
    sections = _form_sections(form, target, loops, short)
    total_bars = sum(b for _n, _r, b in sections)

    # l'intensita' di ogni ruolo, spostata dalla densita'
    shift = int(round((c["density"] - 0.5) * 2))
    def level(name):
        return _LEVELS[max(0, min(2, _LEVELS.index(name) + shift))]
    verse_i, chorus_i = (level(c["intensities"][0]), level(c["intensities"][1]))
    intensity = {"intro": "light", "verse": verse_i, "chorus": chorus_i, "bridge": verse_i if verse_i != "light" else "normal",
                 "solo": chorus_i, "end": chorus_i, "loop": chorus_i}
    variability = c["variability"] if c["variability"] is not None else 0.2 + 0.4 * c["density"]
    variability = float(variability)
    styles = {"verse": c["prog"][0], "intro": c["prog"][0], "chorus": c["prog"][1], "solo": c["prog"][0], "bridge": c["prog"][2],
              "end": c["prog"][1], "loop": c["prog"][0]}

    # quali parti suonano
    active = [p for p in PARTS if p != "progression" and p in c["instruments"]]
    if "comp2" in active and c["density"] < 0.25:
        active.remove("comp2")                              # piu' semplice: un solo accompagnamento
    if "pad" in active and c["density"] < 0.25:
        active.remove("pad")
    if c["melody"] == "nessuna" and "melody" in active:
        active.remove("melody")
    if _MOOD_COLOR.get(c["mood"], {}).get("sparse"):          # l'intimita': meno parti (niente secondo accompagnamento, pad, fiati)
        active = [p for p in active if p not in ("comp2", "pad", "horn")]
    for name in set(c["instruments"].values()):
        make_instrument_available(name)

    # il finale che sfuma: un'ultima frase in cui resta solo l'accompagnamento, piano piano
    if c["ending"] == "sfumato":
        name, role, bars = sections[-1]
        if role == "end" and bars >= 8:
            sections[-1] = (name, role, bars - 4)
        sections.append((tr("Sfumato"), "fade", 4))
        total_bars = sum(b for _n, _r, b in sections)
    intensity["fade"] = "light"
    styles["fade"] = c["prog"][1]
    # lo stacco del genere (3c): una o due battute prima dell'ultimo ritornello (o dell'assolo), solo con almeno due ritornelli
    brk = _GENRE_BREAK.get(c["genre"]) if options.get("breaks", True) not in (False, 0, "0", "no") else None
    if brk and not short:
        where, kind, brk_bars = brk
        chorus_at = [i for i, (_n, r, _b) in enumerate(sections) if r == "chorus"]
        at = (chorus_at[-1] if len(chorus_at) >= 2 else None) if where == "before_last_chorus" else \
            next((i for i, (_n, r, _b) in enumerate(sections) if r == "solo"), None)
        if at is not None and at > 0:
            sections.insert(at, (tr("Break"), "break", brk_bars))
            total_bars = sum(b for _n, _r, b in sections)
    intensity["break"] = "full"
    styles["break"] = c["prog"][1]
    # la curva dell'energia (8.6): sale, picco o cala, al posto dell'intensita' ricavata dal nome della sezione
    curve = options.get("energy") if options.get("energy") in ENERGY_CURVES else None
    section_level: Dict[int, str] = {}
    if curve:
        movable = [i for i, (_n, r, _b) in enumerate(sections) if r in ("verse", "chorus", "bridge", "solo", "loop")]
        for i, name in zip(movable, energy_levels(curve, len(movable))):
            section_level[i] = level(name)

    # la modulazione: dall'ultimo ritornello in poi un tono sopra
    mod_from = -1
    if c["modulation"]:
        chorus_idx = [i for i, (_n, r, _b) in enumerate(sections) if r == "chorus"]
        mod_from = chorus_idx[-1] if chorus_idx else -1          # senza un ritornello (aaba, blues) niente modulazione: il salto arriverebbe secco
    last = len(sections) - 1
    fading = c["ending"] == "sfumato"
    harmony: Dict[Tuple, dict] = {}                          # accordi, accompagnamenti, basso, melodia: uguali nelle ripetizioni
    drum_texts: Dict[Tuple, str] = {}                        # la batteria: in un loop cambia a ogni giro (i fill)
    section_filled: Dict[int, bool] = {}                     # le sezioni che finiscono con un fill (quella dopo entra col crash)
    boxes: List[str] = []
    patterns: Dict[str, str] = {}                            # i pattern del testo compatto (core.compact_text), uno per battuta ripetuta
    raw_patterns: Dict[str, str] = {}                        # gli stessi, come li ha scritti il generatore (prima del micro-tempo)
    human = _float(options.get("human"), 1.0)                # «Umano» (8.3): 0 = griglia esatta, 1 = il micro-tempo dello stile
    compact_on = options.get("compact", True) not in (False, 0, "0", "no")
    out_sections: List[dict] = []
    swing = swing_word(c["genre"], bpm, options.get("swing"))
    delta = _MOOD_COLOR.get(c["mood"], {}).get("swing", 0)
    if swing and delta and options.get("swing") in (None, ""):
        word, _eq, value = swing.partition("=")
        swing = f"{word}={max(52, min(72, int(value) + delta))}"                 # l'atmosfera tira o rilassa lo swing del genere
    start_bar = 0
    chords_track = "Piano"
    # sviluppo del tema (8.2, 8.4): con piu' ritornelli nella stessa tonalita' e un finale dopo, la melodia del ritornello si scrive
    # una volta in un pattern e l'ultimo ritornello la riprende un'ottava sopra (il culmine del brano), se lo strumento ci arriva
    chorus_ids = [i for i, (_n, r, _b) in enumerate(sections) if r == "chorus"]
    develop = (options.get("development", True) not in (False, 0, "0", "no") and "melody" in active and len(chorus_ids) >= 2
               and mod_from < 0 and chorus_ids[-1] < last and any(r == "end" for _n, r, _b in sections[chorus_ids[-1] + 1:]))
    dev_pattern = ""
    harm_body = ""
    # la melodia anche nella strofa (3a): non nei brani brevissimi (una o due sezioni), dove la strofa e' l'attesa del ritornello
    verse_melody = options.get("verse_melody", True) not in (False, 0, "0", "no") and not short and len(sections) >= 3
    # la seconda voce: su richiesta il tema in terze nell'ultimo ritornello; senza richiesta, quella del genere (terze o seste
    # parallele sotto la melodia, 2c) in ogni ritornello. second_voice=False la toglie
    asked = options.get("second_voice")
    auto_voice = (_GENRE_SECOND_VOICE.get(c["genre"]) or (_MOOD_COLOR.get(c["mood"], {}).get("voice") if c["genre"] not in _NO_TONE_GENRES else None)) \
        if asked in (None, "") else None
    if develop and "melody" in c["instruments"] and (asked in (True, 1, "1", "si") or auto_voice):
        taken = {c["instruments"][p] for p in active if p in c["instruments"]}
        harm = _GENRE_HARM.get(c["genre"]) if _GENRE_HARM.get(c["genre"]) not in taken else None
        harm = harm or _HARM_FOR.get(c["instruments"]["melody"], "Flute")
        if harm in taken:                                     # due parti non possono avere lo stesso strumento (il nome della traccia)
            harm = next((h for h in ("Flute", "Clarinet", "Oboe", "Violin", "Alto_Sax") if h not in taken), harm)
        c["instruments"]["harm"] = harm
        active.append("harm")
        from core.instruments import make_instrument_available as _available
        _available(c["instruments"]["harm"])
    for idx, (sname, role, bars) in enumerate(sections):
        skey = _shift_key(key, 2) if 0 <= mod_from <= idx else key
        closing = idx == last and not fading or (fading and role == "end")
        base = header(skey)
        sidx = 0 if form == "loop" else idx                  # in un loop l'armonia e' sempre la stessa
        seed_of = lambda part, offset=0: (c["seeds"][part] * 1000 + sidx * 17 + offset) % (2 ** 31)
        lvl = section_level.get(idx, intensity[role])
        # il ponte di un'atmosfera quieta, sul pedale (8.5): il basso tiene la tonica sotto gli accordi che cambiano
        pedal_bridge = role == "bridge" and MOODS_DATA[c["mood"]][4] <= 2
        pedal_verse = role in ("verse", "intro") and _MOOD_COLOR.get(c["mood"], {}).get("pedal_verse")      # la tesa: la tonica tenuta sotto la strofa
        pedal_ok = not (c["parts"].get("bass") or {}).get("style") and c["styles"]["bass"] not in ("walking", "blues", "shuffle")
        # il pedale (8.5): il basso tiene la tonica sotto gli accordi che cambiano. Una nota lunga per battuta; solo il basso a
        # ottavi del rock tiene il suo disegno, ma sempre sulla tonica
        bass_style = "pedal" if (pedal_bridge or (pedal_verse and c["styles"]["bass"] != "eighths")) and pedal_ok else c["styles"]["bass"]
        tonic_bass = bool((pedal_bridge or pedal_verse) and pedal_ok)
        cache = ("loop" if form == "loop" else sname, role, bars, skey, closing, lvl, bass_style, tonic_bass)
        if cache not in harmony:
            written = _chord_loop(c["chords"], bars, bar_beats, (rg_parse_key(skey)[0] - rg_parse_key(key)[0]) % 12) if c["chords"] else None
            progression = written or E.generate(base, "progression", {
                "key": skey, "style": styles[role], "bars": bars, "chord_bars": 1.0, "seed": seed_of("progression"),
                "ending": closing and c["ending"] != "sfumato", "variability": variability,
                "inversions": _float(options.get("inversions"), 0.35)})["text"]
            colored = progression
            how = _MOOD_COLOR.get(c["mood"], {}).get("chords")
            if how and not written:
                from .rhythm_generate import parse_key
                tonic_pc, mode_now = parse_key(skey)[:2]
                colored = _color_chords(progression, tonic_pc, how, _melody_scale(c["genre"], tonic_pc, mode_now))   # solo settime della scala
            if closing and not written and c["ending"] != "sfumato" and c["genre"] in _FINAL_CHORD:
                progression = _color_last_chord(progression, _FINAL_CHORD[c["genre"]])
                colored = _color_last_chord(colored, _FINAL_CHORD[c["genre"]])
            temp = E.add_track(base, chords_track, progression)["text"]                # il basso: le triadi
            temp_color = E.add_track(base, chords_track, colored)["text"] if colored != progression else temp
            temp_bass = E.add_track(base, chords_track, _tonic_progression(progression, skey))["text"] if tonic_bass else temp
            project = parse_project_text(temp, "Brano")
            project_color = parse_project_text(temp_color, "Brano") if colored != progression else project       # la melodia: gli accordi suonati
            bodies = {}
            reg_text = temp_color                              # gli accompagnamenti vedono dove suonano il basso e la melodia (registri)
            for p, part in sorted(enumerate(active), key=lambda ip: ip[1] not in ("bass", "melody")):
                if role == "break":
                    if part == "drums" or part not in _BREAK_PARTS[_GENRE_BREAK[c["genre"]][1]]:
                        continue
                elif role not in _enters(c["genre"], part, verse_melody) or part == "drums" or (role == "fade" and part != "comp"):
                    continue
                common = {"seed": seed_of(part, p + 1), "bars": bars, "intensity": lvl, "variability": variability}
                if part in ("comp", "comp2", "horn", "pad"):
                    body = E.generate(reg_text, "comping", {**common, "source": chords_track, "style": c["styles"][part],
                                                        "instrument": c["instruments"][part],
                                                        "voice_leading": options.get("voice_leading", True) not in (False, 0, "0", "no"),
                                                        "symbols": options.get("symbols", True) not in (False, 0, "0", "no")})["text"]
                elif part == "bass":
                    body = E.generate(temp_bass, "bass", {**common, "source": chords_track, "style": bass_style,
                                                     "instrument": c["instruments"]["bass"],
                                                     "ending": closing and c["ending"] != "sfumato"})["text"]
                else:
                    mstyle = _MELODY_STYLE[c["melody"]]
                    if role == "verse" and "verse" not in _ENTER["melody"]:     # la strofa: piu' rada e piu' leggera del ritornello
                        mstyle = _VERSE_MELODY_STYLE.get(mstyle, mstyle)
                    body = E._quick_melody(project_color, chords_track, c["instruments"]["melody"], mstyle, skey, bars,
                                           seed_of("melody", 99 if role != "verse" else 98), "light" if role == "verse" else lvl,
                                           {**E._variation({"seed": seed_of("melody", 99)}),
                                            "scale_kind": _GENRE_SCALE.get(c["genre"], ""),
                                            "figure": _figures_for(c["genre"], c["instruments"]["melody"])
                                            if options.get("figures", True) not in (False, 0, "0", "no") else ""})
                if role == "break" and _GENRE_BREAK[c["genre"]][1] == "hit":
                    from .arrange import _first_hit_only
                    body = _first_hit_only(body)
                    if body is None:
                        continue
                bodies[part] = body
                if part == "melody" and role == "chorus" and "harm" in active:
                    from core.instruments import get_instrument as _gi
                    voice_kind = auto_voice or "thirds"
                    harm_instrument = _gi(c["instruments"]["harm"])
                    tonic_pc, mode_now = parse_key_now(skey)
                    voice = _second_voice(body, E._chords_of(project_color, chords_track, None)[0],
                                          _melody_scale(c["genre"], tonic_pc, mode_now), voice_kind,
                                          harm_instrument.range_low, harm_instrument.range_high, bars * bar_beats)
                    if voice:
                        bodies["_voice"] = voice
                if part in ("bass", "melody") and role != "break":
                    try:
                        grown = E.add_track(reg_text, c["instruments"][part], body, name="Registro" + part, compact=False)["text"]
                        parse_project_text(grown, "Brano")
                        reg_text = grown
                    except Exception:
                        pass                                   # il registro e' solo un riguardo: senza, l'accompagnamento resta com'era
            harmony[cache] = bodies
        bodies = dict(harmony[cache])
        brk_kind = _GENRE_BREAK[c["genre"]][1] if role == "break" else None
        if "drums" in active and brk_kind == "hit":
            from .arrange import _break_drums
            bodies["drums"] = _break_drums(bars * beats_per_bar)
        elif "drums" in active and (role in _enters(c["genre"], "drums") or brk_kind == "fill"):
            variant = idx if form == "loop" else 0
            # i fill legati alla forma: il fill sull'ultima battuta quando cambia sezione (non prima di un break, che e' gia' un fill, ne' in
            # un loop) e il crash sul primo tempo della sezione che arriva dopo un fill, e sempre su quello del ritornello
            fill_last = (form != "loop" and idx < last and role not in ("break", "fade") and brk_kind is None
                         and sections[idx + 1][1] not in ("break", "fade"))
            crash_first = idx > 0 and form != "loop" and role not in ("break", "fade") and (
                role == "chorus" or section_filled.get(idx - 1, False))
            section_filled[idx] = fill_last
            dkey = cache + (variant, fill_last, crash_first)
            if dkey not in drum_texts:
                drum_texts[dkey] = E.generate(base, "drums", {
                    "seed": (c["seeds"]["drums"] * 1000 + idx * 17 + 5 + variant) % (2 ** 31), "bars": bars, "intensity": lvl, "variability": variability,
                    "style": c["styles"]["drums"], "ending": closing and c["ending"] != "sfumato",
                    "fill_every": 1 if brk_kind == "fill" else c.get("drum_fill", 4),
                    "fill_last": fill_last, "crash_first": crash_first})["text"]
            bodies["drums"] = drum_texts[dkey]
            if closing and c["ending"] != "sfumato" and c["genre"] in _FINAL_HITS:
                bodies["drums"] = _final_hits(bodies["drums"])
        sec_start = start_bar * beats_per_bar
        for part in active:
            if part not in bodies:
                continue
            body = bodies[part].strip("\n")
            vfactor = _MOOD_COLOR.get(c["mood"], {}).get("velocity")
            if vfactor and vfactor != 1:                       # l'atmosfera suona piu' piano o piu' forte
                body = _scale_velocity(body, vfactor)
            hot = _instrument_velocity(c["instruments"].get(part, ""))
            if hot != 1:                                       # gli strumenti che a pari velocity coprono le altre parti suonano piu' piano
                body = _scale_velocity(body, hot)
            if fading and role == "end":
                body = _scale_velocity(body, 0.85)
            elif role == "fade":
                body = _scale_velocity(body, 0.55)
            if closing and part == "comp" and c["ending"] != "sfumato" and c["genre"] in _FINAL_CHORD:
                body = _color_last_voicing(body, skey, _FINAL_CHORD[c["genre"]])
            if closing and c["ending"] == "rallentando" and part == "comp":
                body = _rallentando(body, bars * beats_per_bar, bpm)
            if compact_on:                                    # barre e pattern: il testo si legge e si modifica, il suono e' lo stesso
                from .compact_text import compact
                label = {"melody": "Melodia"}.get(part) or (bass_style if part == "bass" else c["styles"].get(part)) or part
                made_text = compact(body, bar_beats, label, existing=raw_patterns)
                raw_patterns.update(made_text["patterns"])
                patterns.update({n: (humanize_drums(b, c["styles"]["drums"], human) if part == "drums" else b)
                                 for n, b in made_text["patterns"].items()})
                body = made_text["text"]
            if part == "drums":
                body = humanize_drums(body, c["styles"]["drums"], human)
            elif part in ("bass", "comp"):
                body = humanize_part(body, part, c["genre"], human)
            if develop and part == "melody" and role == "chorus":
                from .compact_text import _camel
                dev_pattern = dev_pattern or "Melodia" + _camel(sname)
                patterns.setdefault(dev_pattern, body)
                body = "%" + dev_pattern
                if idx == chorus_ids[-1]:
                    from core.instruments import get_instrument
                    top = _top_pitch(patterns[dev_pattern], c["instruments"]["melody"], c["meter"])
                    if top is not None and top + 12 <= get_instrument(c["instruments"]["melody"]).range_high:
                        body += ".octave(1)"
                    harm_body = "%" + dev_pattern + ".thirds"
                if auto_voice:
                    harm_body = "%" + dev_pattern + {"thirds": ".step(-2)", "sixths": ".step(-5)"}[auto_voice] + \
                        (".octave(1)" if body.endswith(".octave(1)") else "")
                if bodies.get("_voice") and (auto_voice or idx == chorus_ids[-1]):
                    voice_pattern = dev_pattern + "Voce"
                    patterns.setdefault(voice_pattern, bodies["_voice"])
                    harm_body = "%" + voice_pattern + (".octave(1)" if body.endswith(".octave(1)") else "")
                elif auto_voice and "harm" in c["instruments"] and not harm_body.endswith(".octave(1)"):
                    # la seconda voce sta sotto la melodia (terze, seste): se esce sotto l'estensione del suo strumento sale d'ottava
                    from core.instruments import get_instrument
                    low = _top_pitch(patterns[dev_pattern], c["instruments"]["melody"], c["meter"], lowest=True)
                    if low is not None and low - (9 if auto_voice == "sixths" else 4) < get_instrument(c["instruments"]["harm"]).range_low:
                        harm_body += ".octave(1)"
            if swing and part in _SWING_PARTS:
                body = swing + " " + body.lstrip()
            boxes.append(E._box_header(part_track(c, part), sname, sec_start) + "\n" + E._indent(body))
        if harm_body and "harm" in active and (idx == chorus_ids[-1] or (auto_voice and role == "chorus")):
            boxes.append(E._box_header(part_track(c, "harm"), sname, sec_start) + "\n" + E._indent((swing + " " if swing else "") + harm_body))
        out_sections.append({"name": sname, "role": role, "bars": bars, "start_bar": start_bar, "key": skey})
        start_bar += bars

    seconds = int(round(total_bars * beats_per_bar * 60.0 / bpm))
    label = _genre_labels()[c["genre"]]
    mood_label = _mood_labels()[c["mood"]]
    saved = {k: c[k] for k in ("genre", "mood", "seed", "key", "bpm", "meter", "form", "ensemble", "melody", "ending", "modulation",
                              "density", "chords")}
    saved["bars"] = target                                  # le battute chieste: rigenerando si ottiene la stessa forma
    saved["loop"] = c["loop"]
    saved["seeds"] = c["seeds"]
    saved["styles"] = {p: s for p, s in c["styles"].items() if s}
    saved["instruments"] = c["instruments"]
    if c["formation"]:
        saved["formation"] = c["formation"]
    lines = [_tr("// Un brano in 60 secondi: genere {genre}, atmosfera {mood}, seme {seed}.", genre=c["genre"], mood=c["mood"], seed=c["seed"]),
             "// quick: " + json.dumps(saved, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
             "", header(key).rstrip("\n"), ""]
    kit = _GENRE_KIT.get(c["genre"]) if "drums" in active and options.get("kit", True) not in (False, 0, "0", "no") else None
    if kit:
        kit_name = _kit_name(kit[0])
        lines += [_tr("// Il kit di batteria del genere: si cambia il programma (vedi Gestione strumenti) o si toglie il blocco."), "",
                  f"Strumento {kit_name}:\n  program={kit[1]} percussione=si", ""]
    for part in active:
        if kit and part == "drums":
            lines += [f"Traccia {part_track(c, part)} [{kit_name}]:", ""]
            continue
        lines += [E.add_track("", c["instruments"][part], "", name=part_track(c, part))["text"].rstrip("\n").split("\n")[0].rstrip(), ""]
    fx_rows = _mood_fx(c["genre"], c["mood"]) if options.get("effects", True) not in (False, 0, "0", "no") else ()
    if fx_rows:
        lines += [_tr("// Gli effetti di partenza del genere e dell'atmosfera (catena master): si cambiano o si tolgono come gli altri."), "",
                  "Catena master:\n" + "\n".join("  " + r for r in fx_rows), ""]
    if patterns:
        lines.append(_tr("// I pattern: le battute che si ripetono, scritte una volta sola."))
        lines.append("")
        lines += ["\n\n".join(f"Pattern %{n}:\n  " + b.replace("\n", "\n  ") for n, b in patterns.items()), ""]
    lines.append(_tr("// Le sezioni, ognuna in un box (vista Struttura): si spostano e si copiano."))
    lines.append("")
    lines += ["\n\n".join(boxes)]
    text = "\n".join(lines).rstrip("\n") + "\n"
    return {"text": text, "name": f"{label} {mood_label}", "seed": c["seed"], "key": key, "bpm": bpm, "meter": meter,
            "bars": total_bars, "seconds": seconds, "genre": c["genre"], "mood": c["mood"], "form": form, "ensemble": c["ensemble"],
            "fallback": c["fallback"], "sections": out_sections, "loop": c["loop"], "seeds": c["seeds"],
            "parts": active, "choices": saved, "formation": c["formation"], "left_out": c["left_out"]}


def part_track(c: dict, part: str) -> str:
    """Il nome della traccia di una parte: lo strumento (intestazione breve, «Bass:»)."""
    return c["instruments"][part]


def _float(value, default: float) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def _second_voice(body: str, chords, scale: set, kind: str, low: int, high: int, total: float) -> Optional[str]:
    """La seconda voce sotto la melodia, costruita sugli accordi: per ogni nota la nota dell'accordo una terza (o una sesta) sotto;
    se l'accordo non ce l'ha, la nota della scala a quella distanza che non sta a un semitono da una nota dell'accordo; altrimenti la
    nota dell'accordo piu' vicina sotto. Gli abbellimenti non si raddoppiano, un bend si armonizza sulla nota d'arrivo. Il testo e'
    sulla griglia dei sedicesimi; None se la melodia non ci sta (terzine): allora resta la voce per gradi della scala."""
    from core.notation import parse_track_text
    from .melody_generate import _chord_pcs
    from .rhythm_generate import _note_token, pitch_to_midi
    try:
        events = parse_track_text(body, {}, default_octave=4)
    except Exception:
        return None
    want = (3, 4) if kind == "thirds" else (8, 9)
    center = sum(want) / 2.0

    def chord_at(t):
        current = chords[0]
        for span in chords:
            if span.start_beat <= t + 1e-6:
                current = span
        return current

    def pick(m, span):
        chord = set(_chord_pcs(span))
        for d in want:
            if (m - d) % 12 in chord:
                return m - d
        for d in want:
            p = m - d
            if p % 12 in scale and not any((p - c) % 12 in (1, 11) for c in chord):
                return p
        near = [m - d for d in range(2, 10) if (m - d) % 12 in chord]
        return min(near, key=lambda p: abs((m - p) - center)) if near else None

    tokens, cursor = [], 0.0
    for ev in events:
        if ev.kind not in ("note", "slide", "rest"):
            return None
        if ev.kind == "rest" or getattr(ev, "grace", None) or ev.duration <= 0:
            continue
        units, at = ev.duration * 4, ev.start * 4
        if abs(units - round(units)) > 1e-6 or abs(at - round(at)) > 1e-6:
            return None
        if ev.start < cursor - 1e-6:
            continue
        letter, octave = (ev.slide_points[-1] if ev.kind == "slide" and ev.slide_points else (ev.letter, ev.octave))
        melody_pitch = pitch_to_midi(letter, octave)
        pitch = pick(melody_pitch, chord_at(ev.start))
        if pitch is None:
            continue
        while pitch < low:
            pitch += 12
        if pitch > high or pitch >= melody_pitch:
            continue                                   # alzata d'ottava salirebbe sopra la melodia: le voci non si incrociano
        if ev.start > cursor + 1e-6:
            gap = int(round((ev.start - cursor) * 4))
            tokens.append(f"{gap if gap > 1 else ''}r")
        velocity = max(1, int((ev.velocity or 90) * 0.85))
        n = int(round(units))
        tokens.append(f"{velocity}@ {n if n > 1 else ''}{_note_token(pitch % 12, pitch // 12 - 1)}")
        cursor = ev.start + ev.duration
    if not tokens:
        return None
    if total > cursor + 1e-6:
        gap = int(round((total - cursor) * 4))
        if gap > 0:
            tokens.append(f"{gap if gap > 1 else ''}r")
    return "16: " + " ".join(tokens)


def _top_pitch(body: str, instrument: str, meter: str, lowest: bool = False) -> Optional[int]:
    """La nota piu' alta (MIDI; la piu' bassa con lowest=True) di un testo di melodia, o None se non si legge."""
    try:
        from core.model import Project
        from st_language.midi import resolve_event_notes, sounding_events
        project = Project(name="t", time_sig=meter)
        track = project.add_track("M", instrument, body)
        found = None
        for ev in sounding_events(track.parsed_events(project.patterns, meter=project.meter())):
            notes, _v = resolve_event_notes(ev, track.instrument)
            if notes:
                value = min(notes) if lowest else max(notes)
                found = value if found is None else (min(found, value) if lowest else max(found, value))
        return found
    except Exception:
        return None


def _rallentando(body: str, bar_beats_total: float, bpm: int) -> str:
    """Il tempo che scende nelle ultime due battute di un box (core.arrange); se il testo non si legge, resta com'e'."""
    try:
        from core.arrange import _with_rallentando
        return _with_rallentando(body, max(0.0, bar_beats_total - 8.0), bar_beats_total, float(bpm))
    except Exception:
        return body


def quick_surprise(seed: Optional[int] = None) -> dict:
    """Una combinazione a caso fra quelle ammesse: genere, atmosfera ammessa, forma, organico e durata."""
    rng = random.Random(seed if seed is not None else random.randrange(2 ** 31))
    genre = rng.choice(GENRES)
    recipe = GENRES_DATA[genre]
    return {"genre": genre, "mood": rng.choice(recipe["moods"]), "duration": rng.choice(DURATIONS[:6]),
            "form": rng.choice(FORMS) if rng.random() < 0.3 else recipe["form"],
            "ensemble": rng.choice(ENSEMBLES) if rng.random() < 0.3 else recipe["ens"], "seed": rng.randrange(2 ** 31)}


def quick_daily(day: Optional[str] = None) -> dict:
    """Il brano del giorno: genere, atmosfera, durata e seme che dipendono solo dalla data (AAAA-MM-GG, di default quella di oggi
    in UTC), uguali per tutti. Si passa a quick_song; lo stesso giorno, con la stessa versione di SoundText, esce lo stesso brano
    su ogni computer e telefono. {day, genre, mood, duration, seed}."""
    import datetime
    import hashlib
    if day is None:
        day = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    day = datetime.date.fromisoformat(day).isoformat()
    digest = int(hashlib.sha256(("soundtext-brano-del-giorno/" + day).encode()).hexdigest(), 16)
    rng = random.Random(digest)
    genre = rng.choice(GENRES)
    return {"day": day, "genre": genre, "mood": rng.choice(GENRES_DATA[genre]["moods"]), "duration": 60, "seed": rng.randrange(2 ** 31)}


def quick_read(text: str) -> Optional[dict]:
    """Le scelte salvate in un brano fatto da «Un brano in 60 secondi» (il commento «// quick: {...}»), o None."""
    for line in text.split("\n")[:8]:
        if line.startswith("// quick: "):
            try:
                data = json.loads(line[len("// quick: "):])
            except ValueError:
                return None
            if isinstance(data, dict) and data.get("genre") in GENRES_DATA:
                return data
    return None
