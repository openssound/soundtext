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

from core.i18n import tr

# ------------------------------------------------------------ valori

GENRES = ("pop", "rock", "ballata", "bossa", "jazz", "swing", "funk", "soul", "disco", "lofi", "elettronica",
          "orchestrale", "blues", "reggae", "country", "punk", "metal", "rocknroll", "samba", "chacha", "valzer",
          "marcia", "ballata68", "afro68", "balcanico78")
MOODS = ("allegra", "malinconica", "tesa", "epica", "calma", "sognante", "misteriosa", "romantica", "nostalgica",
         "festosa", "oscura")
DURATIONS = (15, 30, 45, 60, 90, 120, 180, 240)
FORMS = ("loop", "canzone", "aaba", "blues", "ponte")
ENSEMBLES = ("piano", "acustica", "elettrica", "elettronica", "orchestra")
MELODIES = ("nessuna", "cantabile", "vivace", "ballata", "aaba")
ENDINGS = ("cadenza", "rallentando", "sfumato")
PARTS = ("progression", "comp", "comp2", "horn", "bass", "drums", "melody")
_MELODY_STYLE = {"cantabile": "melody_period", "vivace": "melody_lively", "ballata": "melody_ballad", "aaba": "melody_aaba"}

# i parametri di ogni atmosfera: modo, fattore del tempo, intensita' (strofa, ritornello), giro armonico
# (strofa, ritornello, ponte), come stanno fra loro (energia 1-4)
MOODS_DATA = {
    "allegra": ("major", 1.10, ("normal", "full"), ("pop", "royal_road", "circle"), 3),
    "malinconica": ("minor", 0.88, ("light", "normal"), ("minor_pop", "andalusian", "minor_circle"), 1),
    "tesa": ("minor", 1.00, ("normal", "full"), ("minor_rock", "minor_cadence", "phrygian"), 3),
    "epica": ("minor", 1.05, ("normal", "full"), ("minor_epic", "minor_pop", "minor_cadence"), 4),
    "calma": ("major", 0.82, ("light", "normal"), ("canon", "ballad", "pop"), 1),
    "sognante": ("minor", 0.90, ("light", "normal"), ("dorian_vamp", "minor_pop", "dorian_vamp"), 1),
    "misteriosa": ("minor", 0.90, ("light", "normal"), ("phrygian", "minor_cadence", "phrygian"), 2),
    "romantica": ("major", 0.85, ("light", "normal"), ("ballad", "canon", "royal_road"), 1),
    "nostalgica": ("minor", 0.90, ("light", "normal"), ("line_cliche", "minor_pop", "line_cliche"), 1),
    "festosa": ("major", 1.10, ("normal", "full"), ("gospel", "pop", "mixolydian"), 4),
    "oscura": ("minor", 0.95, ("normal", "full"), ("phrygian", "minor_epic", "minor_three"), 3),
}

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
                ens="acustica", form="canzone", moods=("allegra", "malinconica", "tesa", "epica", "calma", "romantica", "nostalgica", "festosa", "sognante")),
    "rock": dict(meter="4/4", bpm=122, drums="rock", bass="eighths", comp="quarter_chords", comp2="block_chords", melody="vivace",
                 ens="elettrica", form="canzone", dist=True, moods=("allegra", "tesa", "epica", "oscura", "festosa", "malinconica")),
    "ballata": dict(meter="4/4", bpm=72, drums="halftime", bass="root", comp="arpeggio_up", comp2="sustained", melody="ballata",
                    ens="acustica", form="ponte", moods=("malinconica", "calma", "romantica", "nostalgica", "epica", "sognante")),
    "bossa": dict(meter="4/4", bpm=128, drums="bossa", bass="bossa", comp="bossa_comp", comp2="block_chords", melody="cantabile",
                  ens="acustica", form="canzone", moods=("allegra", "calma", "romantica", "nostalgica", "malinconica", "sognante"),
                  prog={"major": ("jazz_251", "turnaround", "circle"), "minor": ("minor_251", "minor_circle", "minor_251")}),
    "jazz": dict(meter="4/4", bpm=140, drums="swing", bass="walking", comp="quarter_chords", comp2="block_chords", melody="aaba",
                 ens="acustica", form="aaba", moods=("allegra", "malinconica", "calma", "romantica", "nostalgica", "misteriosa", "sognante"),
                 prog={"major": ("jazz_251", "rhythm_changes", "jazz_251"), "minor": ("minor_251", "minor_251", "minor_circle")}),
    "swing": dict(meter="4/4", bpm=160, drums="swing", bass="walking", comp="quarter_chords", comp2="block_chords", melody="vivace",
                  ens="acustica", form="aaba", moods=("allegra", "festosa", "romantica", "nostalgica", "malinconica"),
                  prog={"major": ("rhythm_changes", "jazz_251", "turnaround"), "minor": ("minor_251", "minor_circle", "minor_251")}),
    "funk": dict(meter="4/4", bpm=108, drums="funk", bass="octaves", comp="funk_stab", comp2="quarter_chords", melody="vivace",
                 ens="elettrica", form="canzone", moods=("allegra", "tesa", "festosa", "oscura", "misteriosa"),
                 prog={"major": ("mixolydian", "mixolydian", "gospel"), "minor": ("dorian_vamp", "minor_three", "dorian_vamp")}),
    "soul": dict(meter="4/4", bpm=92, drums="soul", bass="root_fifth", comp="broken_chord", comp2="block_chords", melody="ballata",
                 ens="acustica", form="canzone", moods=("allegra", "malinconica", "romantica", "nostalgica", "calma", "festosa"),
                 prog={"major": ("gospel", "pop", "ballad"), "minor": ("minor_pop", "minor_cadence", "minor_circle")}),
    "disco": dict(meter="4/4", bpm=118, drums="disco", bass="octaves", comp="funk_stab", comp2="quarter_chords", melody="vivace",
                  ens="elettrica", form="canzone", moods=("allegra", "festosa", "romantica", "malinconica"),
                  prog={"major": ("circle", "pop", "royal_road"), "minor": ("minor_circle", "minor_pop", "minor_cadence")}),
    "lofi": dict(meter="4/4", bpm=80, drums="hiphop", bass="root", comp="broken_chord", comp2="sustained", melody="ballata",
                 ens="elettronica", form="loop", moods=("calma", "malinconica", "nostalgica", "sognante", "romantica", "misteriosa"),
                 prog={"major": ("jazz_251", "gospel", "turnaround"), "minor": ("minor_251", "dorian_vamp", "minor_pop")}),
    "elettronica": dict(meter="4/4", bpm=124, drums="disco", bass="octaves", comp="sustained", comp2="arpeggio_up", melody="vivace",
                        ens="elettronica", form="canzone", moods=("allegra", "tesa", "epica", "oscura", "sognante", "misteriosa", "festosa")),
    "orchestrale": dict(meter="4/4", bpm=92, drums=None, bass="root", comp="sustained", comp2="arpeggio_up", melody="cantabile",
                        ens="orchestra", form="ponte", moods=MOODS),
    "blues": dict(meter="4/4", bpm=96, drums="shuffle", bass="blues", comp="quarter_chords", comp2="block_chords", melody="vivace",
                  ens="elettrica", form="blues", moods=("allegra", "malinconica", "tesa", "oscura", "calma", "nostalgica"),
                  prog={"major": ("blues_12", "blues_12", "blues_12"), "minor": ("minor_blues_12", "minor_blues_12", "minor_blues_12")}),
    "reggae": dict(meter="4/4", bpm=76, drums="reggae", bass="reggae", comp="skank_chords", comp2="sustained", melody="cantabile",
                   ens="elettrica", form="canzone", moods=("allegra", "calma", "festosa", "nostalgica", "sognante"),
                   prog={"major": ("three_chord", "pop", "mixolydian"), "minor": ("minor_three", "minor_pop", "minor_cadence")}),
    "country": dict(meter="4/4", bpm=108, drums="country", bass="root_fifth", comp="quarter_chords", comp2="broken_chord", melody="cantabile",
                    ens="acustica", form="canzone", moods=("allegra", "festosa", "malinconica", "nostalgica", "calma", "romantica"),
                    prog={"major": ("three_chord", "pop", "canon"), "minor": ("minor_pop", "minor_three", "minor_cadence")}),
    "punk": dict(meter="4/4", bpm=170, drums="punk", bass="eighths", comp="quarter_chords", comp2="block_chords", melody="vivace",
                 ens="elettrica", form="canzone", dist=True, moods=("tesa", "allegra", "epica", "oscura", "festosa"),
                 prog={"major": ("three_chord", "rock", "mixolydian"), "minor": ("minor_three", "minor_rock", "minor_three")}),
    "metal": dict(meter="4/4", bpm=150, drums="metal", bass="eighths", comp="quarter_chords", comp2="block_chords", melody="vivace",
                  ens="elettrica", form="canzone", dist=True, moods=("tesa", "epica", "oscura", "misteriosa"),
                  prog={"major": ("mixolydian", "rock", "mixolydian"), "minor": ("phrygian", "minor_epic", "minor_three")}),
    "rocknroll": dict(meter="4/4", bpm=150, drums="rocknroll", bass="root_fifth", comp="quarter_chords", comp2="block_chords", melody="vivace",
                      ens="elettrica", form="canzone", moods=("allegra", "festosa", "nostalgica", "tesa"),
                      prog={"major": ("doo_wop", "rock", "three_chord"), "minor": ("minor_rock", "minor_three", "minor_rock")}),
    "samba": dict(meter="4/4", bpm=100, drums="samba", bass="bossa", comp="bossa_comp", comp2="montuno", melody="vivace",
                  ens="acustica", form="canzone", moods=("allegra", "festosa", "romantica", "calma"),
                  prog={"major": ("jazz_251", "pop", "circle"), "minor": ("minor_251", "minor_circle", "minor_251")}),
    "chacha": dict(meter="4/4", bpm=112, drums="cha_cha", bass="bossa", comp="montuno", comp2="block_chords", melody="cantabile",
                   ens="acustica", form="canzone", moods=("allegra", "festosa", "romantica", "nostalgica"),
                   prog={"major": ("pop", "circle", "jazz_251"), "minor": ("minor_pop", "minor_circle", "minor_251")}),
    "valzer": dict(meter="3/4", bpm=96, drums="waltz", bass="waltz", comp="waltz_comp", comp2="sustained", melody="cantabile",
                   ens="acustica", form="canzone", moods=("allegra", "romantica", "nostalgica", "malinconica", "festosa", "epica")),
    "marcia": dict(meter="4/4", bpm=112, drums="march", bass="two_feel", comp="quarter_chords", comp2="block_chords", melody="vivace",
                   ens="orchestra", form="canzone", moods=("allegra", "epica", "festosa", "tesa"), drums_in_orchestra=True),
    "ballata68": dict(meter="6/8", bpm=66, drums="ballad_68", bass="root", comp="arpeggio_68", comp2="sustained", melody="ballata",
                      ens="acustica", form="ponte", moods=("malinconica", "romantica", "nostalgica", "calma", "sognante", "epica")),
    "afro68": dict(meter="6/8", bpm=96, drums="afro_68", bass="two_feel", comp="arpeggio_68", comp2="block_chords", melody="cantabile",
                   ens="acustica", form="canzone", moods=("allegra", "festosa", "sognante", "misteriosa", "calma")),
    "balcanico78": dict(meter="7/8", bpm=140, drums="balkan_78", bass="eighths", comp="block_chords", comp2="quarter_chords", melody="vivace",
                        ens="acustica", form="canzone", moods=("allegra", "festosa", "tesa", "misteriosa", "epica"),
                        prog={"major": ("mixolydian", "pop", "mixolydian"), "minor": ("phrygian", "minor_rock", "phrygian")}),
}

# in quali sezioni suona ogni parte
_ENTER = {
    "progression": (), "comp": ("intro", "verse", "chorus", "bridge", "solo", "end", "loop", "fade"),
    "comp2": ("chorus", "bridge", "solo", "end", "loop"), "horn": ("chorus", "solo", "end"),
    "bass": ("verse", "chorus", "bridge", "solo", "end", "loop"), "drums": ("verse", "chorus", "bridge", "solo", "end", "loop"),
    "melody": ("chorus", "solo", "end", "loop"),
}
_ENTER_FADE = ("comp",)


# ------------------------------------------------------------ etichette

def _genre_labels() -> Dict[str, str]:
    return {"pop": tr("Pop"), "rock": tr("Rock"), "ballata": tr("Ballata"), "bossa": tr("Bossa nova"), "jazz": tr("Jazz"),
            "swing": tr("Swing"), "funk": tr("Funk"), "soul": tr("Soul"), "disco": tr("Disco"), "lofi": tr("Lo-fi"),
            "elettronica": tr("Elettronica"), "orchestrale": tr("Orchestrale"), "blues": tr("Blues"), "reggae": tr("Reggae"),
            "country": tr("Country"), "punk": tr("Punk"), "metal": tr("Metal"), "rocknroll": tr("Rock'n'roll"),
            "samba": tr("Samba"), "chacha": tr("Cha-cha-cha"), "valzer": tr("Valzer"), "marcia": tr("Marcia"),
            "ballata68": tr("Ballata 6/8"), "afro68": tr("Afro 6/8"), "balcanico78": tr("Balcanico 7/8")}


def _mood_labels() -> Dict[str, str]:
    return {"allegra": tr("allegra"), "malinconica": tr("malinconica"), "tesa": tr("tesa"), "epica": tr("epica"),
            "calma": tr("calma"), "sognante": tr("sognante"), "misteriosa": tr("misteriosa"), "romantica": tr("romantica"),
            "nostalgica": tr("nostalgica"), "festosa": tr("festosa"), "oscura": tr("oscura")}


def _form_labels() -> Dict[str, str]:
    return {"loop": tr("loop di 8 battute"), "canzone": tr("strofa e ritornello"), "aaba": tr("AABA"),
            "blues": tr("blues di 12 battute"), "ponte": tr("canzone con ponte")}


def _ensemble_labels() -> Dict[str, str]:
    return {"piano": tr("solo piano"), "acustica": tr("band acustica"), "elettrica": tr("band elettrica"),
            "elettronica": tr("elettronico"), "orchestra": tr("orchestra")}


def _melody_labels() -> Dict[str, str]:
    return {"nessuna": tr("nessuna"), "cantabile": tr("cantabile"), "vivace": tr("vivace"), "ballata": tr("ballata"),
            "aaba": tr("AABA")}


def _ending_labels() -> Dict[str, str]:
    return {"cadenza": tr("cadenza"), "rallentando": tr("rallentando"), "sfumato": tr("sfumato")}


def _part_labels() -> Dict[str, str]:
    return {"progression": tr("Giro armonico"), "comp": tr("Accompagnamento"), "comp2": tr("Secondo accompagnamento"),
            "horn": tr("Ottoni"), "bass": tr("Basso"), "drums": tr("Batteria"), "melody": tr("Melodia")}


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
            role = "end" if i == n - 1 and n > 1 else "solo" if 0 < i < n - 1 else "verse"
            out.append((tr("Giro {n}", n=i + 1), role, 12))
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

    mode, tempo_factor, intensities, mood_prog, _energy = MOODS_DATA[mood]
    key = options.get("key") or ""
    if key:
        mode = rg.parse_key(key)[1]
        prog_mood = mood if MOODS_DATA[mood][0] == mode else ("malinconica" if mode == "minor" else "allegra")
    else:
        key = rng.choice(_KEYS[mode])
        prog_mood = mood
    prog_triple = (recipe.get("prog") or {}).get(mode) or MOODS_DATA[prog_mood][3]
    meter = options.get("meter") or recipe["meter"]
    bpm = _int(options.get("bpm"), 0) or int(round(recipe["bpm"] * tempo_factor))
    bpm = max(40, min(240, bpm))

    drum_styles = rg.drum_styles_for_meter(meter)
    drums = options.get("drums") or recipe["drums"]
    if drums is not None and drums not in drum_styles:
        drums = drum_styles[0] if drum_styles else None      # lo stile non esiste per questa metrica
    ensemble = options.get("ensemble") or recipe["ens"]
    if ensemble not in _ENSEMBLE_PARTS:
        raise ValueError(f"organico sconosciuto: {ensemble}")
    melody = options.get("melody", recipe["melody"])
    if melody is True:
        melody = recipe["melody"]
    if melody is False or melody in ("", None):
        melody = "nessuna"
    if melody not in _MELODY_STYLE and melody != "nessuna":
        raise ValueError(f"stile di melodia sconosciuto: {melody}")
    form = options.get("form") or recipe["form"]
    if form not in FORMS:
        raise ValueError(f"forma sconosciuta: {form}")
    ending = options.get("ending") or "cadenza"
    if ending not in ENDINGS:
        raise ValueError(f"finale sconosciuto: {ending}")

    density = options.get("density")
    density = 0.5 if density is None else max(0.0, min(1.0, float(density)))
    parts_in = dict(options.get("parts") or {})
    seeds = {}
    for part in PARTS:
        given = (parts_in.get(part) or {}).get("seed")
        seeds[part] = _int(given, 0) if given not in (None, "") else _random.Random(f"{seed}/{part}").randrange(2 ** 31)
    styles = {"drums": drums, "bass": recipe["bass"], "comp": recipe["comp"], "comp2": recipe["comp2"], "horn": "sustained",
              "progression": None}
    for part, spec in parts_in.items():
        if part in styles and spec.get("style"):
            styles[part] = spec["style"]
    instruments = dict(_ENSEMBLE_PARTS[ensemble])
    if recipe.get("dist") and ensemble == "elettrica":
        instruments["comp"] = "Distortion_Guitar"
    if drums is not None and "drums" not in instruments and (options.get("drums") or recipe.get("drums_in_orchestra")):
        instruments["drums"] = "Drums"                       # l'orchestra non ha la batteria, salvo una marcia o se la si sceglie
    if drums is None:
        instruments.pop("drums", None)
    for part, spec in parts_in.items():
        if spec.get("instrument") and part in instruments:
            instruments[part] = spec["instrument"]
    return {"genre": genre, "mood": mood, "requested_mood": options.get("mood", "allegra"), "fallback": fallback, "seed": seed, "key": key,
            "mode": mode, "bpm": bpm, "meter": meter, "form": form, "ensemble": ensemble, "melody": melody, "ending": ending,
            "modulation": bool(options.get("modulation")), "density": density, "loop": bool(options.get("loop")),
            "duration": options.get("duration"), "bars": _int(options.get("bars"), 0), "variability": options.get("variability"),
            "prog": list(prog_triple), "intensities": list(intensities), "styles": styles, "instruments": instruments, "seeds": seeds,
            "chords": str(options.get("chords") or "").strip(), "parts": parts_in}


# ------------------------------------------------------------ il brano

_LEVELS = ("light", "normal", "full")


def _scale_velocity(text: str, factor: float) -> str:
    return re.sub(r"(\d+)@", lambda m: f"{max(1, int(int(m.group(1)) * factor))}@", text)


def _chord_loop(written: str, bars: int) -> Optional[str]:
    """Il giro scritto a mano («Am F C G») ripetuto per 'bars' battute, come testo di accordi (un accordo per battuta)."""
    from core.chords import parse_chord_symbol
    symbols = [s for s in re.split(r"[\s,|]+", written) if s]
    if not symbols:
        return None
    for s in symbols:
        parse_chord_symbol(s)                               # ValueError se non e' un accordo
    return "4: " + " ".join(f"4{symbols[i % len(symbols)]}" for i in range(bars))


def quick_song(options: Optional[dict] = None) -> dict:
    """Un brano completo.

    options (tutte facoltative): genre, mood, duration (secondi; oppure bars o loop), seed, key, bpm, meter, form, ensemble,
    melody ('nessuna' o uno stile), ending, modulation, density (0-1, piu' semplice o piu' ricco), chords (un giro scritto a
    mano), variability, e parts: {parte: {seed, style, instrument}} per le scelte di ogni parte (PARTS).
    Restituisce {text, name, seed, key, bpm, meter, bars, seconds, genre, mood, form, ensemble, fallback, sections, loop,
    seeds, choices}."""
    import engine as E
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
    if c["melody"] == "nessuna" and "melody" in active:
        active.remove("melody")
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

    # la modulazione: dall'ultimo ritornello in poi un tono sopra
    mod_from = -1
    if c["modulation"]:
        chorus_idx = [i for i, (_n, r, _b) in enumerate(sections) if r == "chorus"]
        mod_from = chorus_idx[-1] if chorus_idx else max(0, len(sections) - 1)
    last = len(sections) - 1
    fading = c["ending"] == "sfumato"
    harmony: Dict[Tuple, dict] = {}                          # accordi, accompagnamenti, basso, melodia: uguali nelle ripetizioni
    drum_texts: Dict[Tuple, str] = {}                        # la batteria: in un loop cambia a ogni giro (i fill)
    boxes: List[str] = []
    out_sections: List[dict] = []
    start_bar = 0
    chords_track = "Piano"
    for idx, (sname, role, bars) in enumerate(sections):
        skey = _shift_key(key, 2) if 0 <= mod_from <= idx else key
        closing = idx == last and not fading or (fading and role == "end")
        base = header(skey)
        sidx = 0 if form == "loop" else idx                  # in un loop l'armonia e' sempre la stessa
        seed_of = lambda part, offset=0: (c["seeds"][part] * 1000 + sidx * 17 + offset) % (2 ** 31)
        cache = ("loop" if form == "loop" else sname, role, bars, skey, closing)
        if cache not in harmony:
            written = _chord_loop(c["chords"], bars) if c["chords"] else None
            progression = written or E.generate(base, "progression", {
                "key": skey, "style": styles[role], "bars": bars, "chord_bars": 1.0, "seed": seed_of("progression"),
                "ending": closing and c["ending"] != "sfumato", "variability": variability})["text"]
            temp = E.add_track(base, chords_track, progression)["text"]
            project = parse_project_text(temp, "Brano")
            bodies = {}
            for p, part in enumerate(active):
                if role not in _ENTER[part] or part == "drums" or (role == "fade" and part != "comp"):
                    continue
                common = {"seed": seed_of(part, p + 1), "bars": bars, "intensity": intensity[role], "variability": variability}
                if part in ("comp", "comp2", "horn"):
                    body = E.generate(temp, "comping", {**common, "source": chords_track, "style": c["styles"][part],
                                                        "instrument": c["instruments"][part]})["text"]
                elif part == "bass":
                    body = E.generate(temp, "bass", {**common, "source": chords_track, "style": c["styles"]["bass"],
                                                     "instrument": c["instruments"]["bass"],
                                                     "ending": closing and c["ending"] != "sfumato"})["text"]
                else:
                    body = E._quick_melody(project, chords_track, c["instruments"]["melody"], _MELODY_STYLE[c["melody"]], skey, bars,
                                           seed_of("melody", 99), intensity[role], E._variation({"seed": seed_of("melody", 99)}))
                bodies[part] = body
            harmony[cache] = bodies
        bodies = dict(harmony[cache])
        if "drums" in active and role in _ENTER["drums"]:
            variant = idx if form == "loop" else 0
            dkey = cache + (variant,)
            if dkey not in drum_texts:
                drum_texts[dkey] = E.generate(base, "drums", {
                    "seed": (c["seeds"]["drums"] * 1000 + idx * 17 + 5 + variant) % (2 ** 31), "bars": bars, "intensity": intensity[role], "variability": variability,
                    "style": c["styles"]["drums"], "ending": closing and c["ending"] != "sfumato"})["text"]
            bodies["drums"] = drum_texts[dkey]
        sec_start = start_bar * beats_per_bar
        for part in active:
            if part not in bodies:
                continue
            body = bodies[part].strip("\n")
            if fading and role == "end":
                body = _scale_velocity(body, 0.85)
            elif role == "fade":
                body = _scale_velocity(body, 0.55)
            if closing and c["ending"] == "rallentando" and part == "comp":
                body = _rallentando(body, bars * beats_per_bar, bpm)
            boxes.append(E._box_header(part_track(c, part), sname, sec_start) + "\n" + E._indent(body))
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
    lines = [_tr("// Un brano in 60 secondi: genere {genre}, atmosfera {mood}, seme {seed}.", genre=c["genre"], mood=c["mood"], seed=c["seed"]),
             "// quick: " + json.dumps(saved, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
             "", header(key).rstrip("\n"), ""]
    for part in active:
        lines += [E.add_track("", c["instruments"][part], "", name=part_track(c, part))["text"].rstrip("\n").split("\n")[0].rstrip(), ""]
    lines.append(_tr("// Le sezioni, ognuna in un box (vista Struttura): si spostano e si copiano."))
    lines.append("")
    lines += ["\n\n".join(boxes)]
    text = "\n".join(lines).rstrip("\n") + "\n"
    return {"text": text, "name": f"{label} {mood_label}", "seed": c["seed"], "key": key, "bpm": bpm, "meter": meter,
            "bars": total_bars, "seconds": seconds, "genre": c["genre"], "mood": c["mood"], "form": form, "ensemble": c["ensemble"],
            "fallback": c["fallback"], "sections": out_sections, "loop": c["loop"], "seeds": c["seeds"],
            "parts": active, "choices": saved}


def part_track(c: dict, part: str) -> str:
    """Il nome della traccia di una parte: lo strumento (intestazione breve, «Bass:»)."""
    return c["instruments"][part]


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
