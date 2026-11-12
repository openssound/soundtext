"""
Dettatura: la frase riconosciuta dal riconoscimento vocale diventa testo ST.

«la minore, fa, do, sol» -> `Am F C G`; «ottavi, do re mi fa» -> `8: c d e f`;
«tempo novanta» -> il comando tempo 90. Quattro lingue (italiano, inglese,
francese, spagnolo), con i nomi delle note di ognuna (do re mi / C D E), e le
correzioni degli errori tipici del riconoscimento («re» capito come «e», «si»
come «sì», «sol» come «sole»...): una parola corretta resta segnalata come
incerta. Le parole che l'interprete non capisce non diventano note: restano
nell'elenco, segnalate, con il testo vuoto.

Modulo puro (niente Qt, niente numpy): lo usa il motore dell'app mobile
(mobile/engine.py) e potra' usarlo SoundText sul computer.

    interpret(frase, lingua="it", mode="auto", patterns=()) -> dict

Il risultato:
- text: il testo ST dei pezzi musicali, separati da uno spazio;
- items: i pezzi nell'ordine detto, ognuno {said, st, kind, uncertain, heard}
  (kind: note, chord, rest, grid, bar, pattern, repeat, command, unknown;
  i comandi hanno anche command e value; heard e' la parola capita dal
  riconoscimento quando l'interprete l'ha corretta);
- commands: i comandi detti, {command, value};
- unknown: le parole non capite;
- mode: "notes" o "chords", quello usato.

mode "auto": se nella frase c'e' un accordo con la sua qualita' («la
minore», «sol sette»), anche i nomi soli diventano accordi («la minore, fa,
do, sol» -> Am F C G); altrimenti sono note. "notes" e "chords" lo fissano
(per esempio secondo la riga in cui sta il cursore).

«ottava sopra» / «ottava sotto» danno `*+` / `*-`, che valgono nel modo
relativo (`rel:`). «ripeti due volte» racchiude i pezzi dettati dopo
l'ultima stanghetta della frase (`2( ... )`); se nella frase non ce ne sono
diventa il comando repeat, che l'app applica all'ultima battuta o alla
selezione.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, Iterable, List, Optional, Tuple

from st_language.chords import CHORD_QUALITIES

LANGUAGES = ("it", "en", "fr", "es")


def _strip_accents(word: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", word) if unicodedata.category(c) != "Mn")


# ------------------------------------------------------------------ numeri

_IT_UNITS = ["zero", "uno", "due", "tre", "quattro", "cinque", "sei", "sette", "otto", "nove"]
_IT_TEENS = ["dieci", "undici", "dodici", "tredici", "quattordici", "quindici", "sedici", "diciassette",
             "diciotto", "diciannove"]
_IT_TENS = {20: "venti", 30: "trenta", 40: "quaranta", 50: "cinquanta", 60: "sessanta", 70: "settanta",
            80: "ottanta", 90: "novanta"}


def _it_numbers() -> Dict[str, int]:
    words = {}
    for n in range(100):
        if n < 10:
            forms = [_IT_UNITS[n]]
        elif n < 20:
            forms = [_IT_TEENS[n - 10]]
        else:
            tens, unit = _IT_TENS[n // 10 * 10], n % 10
            if unit == 0:
                forms = [tens]
            elif unit in (1, 8):                       # ventuno, ventotto
                forms = [tens[:-1] + _IT_UNITS[unit], tens + _IT_UNITS[unit]]
            elif unit == 3:
                forms = [tens + "tre", tens + "tré"]
            else:
                forms = [tens + _IT_UNITS[unit]]
        for f in forms:
            words[f] = n
    for hundreds, prefix in ((100, "cento"), (200, "duecento"), (300, "trecento")):
        words[prefix] = hundreds
        for word, n in list(words.items()):
            if 0 < n < 100:
                words[prefix + word] = hundreds + n
                if word.startswith("o"):               # centotto
                    words[prefix[:-1] + word] = hundreds + n
    words.update({"un": 1, "una": 1})
    return words


_EN_UNITS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven",
             "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
_EN_TENS = {20: "twenty", 30: "thirty", 40: "forty", 50: "fifty", 60: "sixty", 70: "seventy", 80: "eighty",
            90: "ninety"}


def _en_numbers() -> Dict[str, int]:
    words = {}
    for n in range(100):
        if n < 20:
            words[_EN_UNITS[n]] = n
        else:
            tens, unit = _EN_TENS[n // 10 * 10], n % 10
            words[tens if unit == 0 else f"{tens} {_EN_UNITS[unit]}"] = n
    for hundreds in (1, 2, 3):
        heads = [f"{_EN_UNITS[hundreds]} hundred"] + (["a hundred", "hundred"] if hundreds == 1 else [])
        for head in heads:
            words[head] = hundreds * 100
            for word, n in list(words.items()):
                if 0 < n < 100:
                    words[f"{head} {word}"] = hundreds * 100 + n
                    words[f"{head} and {word}"] = hundreds * 100 + n
    return words


_FR_UNITS = ["zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix", "onze",
             "douze", "treize", "quatorze", "quinze", "seize", "dix sept", "dix huit", "dix neuf"]
_FR_TENS = {20: "vingt", 30: "trente", 40: "quarante", 50: "cinquante", 60: "soixante"}


def _fr_below_100(n: int) -> List[str]:
    if n < 20:
        return [_FR_UNITS[n]]
    if n < 70:
        tens, unit = _FR_TENS[n // 10 * 10], n % 10
        if unit == 0:
            return [tens]
        return [f"{tens} et un"] if unit == 1 else [f"{tens} {_FR_UNITS[unit]}"]
    if n < 80:                                         # soixante-dix, soixante et onze
        rest = n - 60
        return ["soixante et onze"] if rest == 11 else [f"soixante {_FR_UNITS[rest]}"]
    rest = n - 80
    if rest == 0:
        return ["quatre vingts", "quatre vingt"]
    return [f"quatre vingt {_FR_UNITS[rest]}"]


def _fr_numbers() -> Dict[str, int]:
    words = {}
    for n in range(100):
        for f in _fr_below_100(n):
            words[f] = n
    for hundreds in (1, 2, 3):
        heads = ["cent"] if hundreds == 1 else [f"{_FR_UNITS[hundreds]} cents", f"{_FR_UNITS[hundreds]} cent"]
        for head in heads:
            words[head] = hundreds * 100
            for n in range(1, 100):
                for f in _fr_below_100(n):
                    words[f"{head} {f}"] = hundreds * 100 + n
    words["une"] = 1
    return words


_ES_BELOW_30 = ["cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez", "once",
                "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete", "dieciocho", "diecinueve",
                "veinte", "veintiuno", "veintidós", "veintitrés", "veinticuatro", "veinticinco", "veintiséis",
                "veintisiete", "veintiocho", "veintinueve"]
_ES_TENS = {30: "treinta", 40: "cuarenta", 50: "cincuenta", 60: "sesenta", 70: "setenta", 80: "ochenta",
            90: "noventa"}


def _es_below_100(n: int) -> str:
    if n < 30:
        return _ES_BELOW_30[n]
    tens, unit = _ES_TENS[n // 10 * 10], n % 10
    return tens if unit == 0 else f"{tens} y {_ES_BELOW_30[unit]}"


def _es_numbers() -> Dict[str, int]:
    words = {_es_below_100(n): n for n in range(100)}
    words["cien"] = 100
    for hundreds, head in ((1, "ciento"), (2, "doscientos"), (3, "trescientos")):
        if hundreds > 1:
            words[head] = hundreds * 100
        for n in range(1, 100):
            words[f"{head} {_es_below_100(n)}"] = hundreds * 100 + n
    words.update({"un": 1, "una": 1})
    return words


# ------------------------------------------------------------------ lessici
#
# Per ogni lingua: categoria -> {frase: valore}. Le frasi di piu' parole sono
# scritte con gli spazi (i trattini e gli apostrofi della frase detta
# diventano spazi). Le correzioni degli errori del riconoscimento sono a
# parte (FIXES): la parola capita -> la parola giusta, segnalata come incerta.

_LEXICON = {
    "it": {
        "note": {"do": "c", "re": "d", "mi": "e", "fa": "f", "sol": "g", "la": "a", "si": "b"},
        "acc": {"diesis": "#", "bemolle": "b", "#": "#", "♯": "#", "♭": "b"},
        "qual": {"minore": "m", "min": "m", "maggiore": "maj", "maj": "maj", "sette": "7", "settima": "7",
                 "sei": "6", "sesta": "6", "nove": "9", "nona": "9", "undici": "11", "undicesima": "11",
                 "tredici": "13", "tredicesima": "13", "cinque": "5", "quinta": "5", "diminuito": "dim",
                 "diminuita": "dim", "semidiminuito": "m7b5", "semidiminuita": "m7b5", "aumentato": "aug",
                 "aumentata": "aug", "eccedente": "aug", "sus": "sus", "sospeso": "sus", "sospesa": "sus",
                 "add": "add", "aggiunta": "add", "aggiunto": "add", "bemolle": "b", "diesis": "#"},
        "susnum": {"due": "2", "seconda": "2", "quattro": "4", "quarta": "4", "nove": "9", "nona": "9",
                   "undici": "11"},
        "slash": {"su": "", "basso": "", "con basso": "", "con il basso": "", "barra": ""},
        "dur": {"semibreve": "1", "minima": "2", "semiminima": "4", "croma": "8", "semicroma": "16",
                "biscroma": "32", "semibiscroma": "64", "quarto": "4", "ottavo": "8", "sedicesimo": "16"},
        "dot": {"puntata": ".", "puntato": "."},
        "grid": {"semibrevi": "1:", "minime": "2:", "semiminime": "4:", "quarti": "4:", "crome": "8:",
                 "ottavi": "8:", "semicrome": "16:", "sedicesimi": "16:", "biscrome": "32:",
                 "trentaduesimi": "32:", "terzine": "8T:", "terzine di ottavi": "8T:",
                 "terzine di crome": "8T:", "terzine di quarti": "4T:", "terzine di semiminime": "4T:",
                 "terzine di sedicesimi": "16T:", "terzine di semicrome": "16T:", "terzine di minime": "2T:"},
        "rest": {"pausa": "r", "pause": "r", "silenzio": "r"},
        "of": {"di": ""},
        "bar": {"battuta": "|", "stanghetta": "|", "barra di battuta": "|"},
        "oct": {"ottava": ""},
        "up": {"sopra": "+", "su": "+", "in alto": "+", "alta": "+"},
        "down": {"sotto": "-", "giù": "-", "giu": "-", "in basso": "-", "bassa": "-"},
        "repeat": {"ripeti": "", "ripetere": "", "ripetilo": ""},
        "times": {"volte": "", "volta": ""},
        "count": {},
        "pattern": {"pattern": "", "richiama": "", "motivo": ""},
        "pfunc": {"invertito": ".invert", "inverso": ".invert", "inversione": ".invert",
                  "retrogrado": ".retro", "al contrario": ".retro", "con le terze": ".thirds", "terze": ".thirds",
                  "ottava sopra": ".octave(1)", "un ottava sopra": ".octave(1)", "ottava sotto": ".octave(-1)",
                  "un ottava sotto": ".octave(-1)", "aumentato": ".augment(2)", "diminuito": ".diminish(2)"},
        "conj": {"e": "", "ed": ""},
        "filler": {"poi": "", "virgola": "", "un": "", "una": "", "uno": "", "l": "", "di": "", "nota": "",
                   "accordo": "", "accordi": "", "note": "",
                   "inserisci": "", "aggiungi": "", "metti": "", "scrivi": "", "crea": "", "fai": "", "il": "",
                   "per": "", "favore": ""},
    },
    "en": {
        "note": {"c": "c", "d": "d", "e": "e", "f": "f", "g": "g", "a": "a", "b": "b"},
        "acc": {"sharp": "#", "flat": "b", "#": "#", "♯": "#", "♭": "b"},
        "qual": {"minor": "m", "min": "m", "m": "m", "major": "maj", "maj": "maj", "seven": "7", "seventh": "7",
                 "six": "6", "sixth": "6", "nine": "9", "ninth": "9", "eleven": "11", "eleventh": "11",
                 "thirteen": "13", "thirteenth": "13", "five": "5", "fifth": "5", "diminished": "dim",
                 "dim": "dim", "half diminished": "m7b5", "augmented": "aug", "aug": "aug", "sus": "sus",
                 "suspended": "sus", "add": "add", "added": "add", "flat": "b", "sharp": "#"},
        "susnum": {"two": "2", "second": "2", "four": "4", "fourth": "4", "nine": "9", "ninth": "9",
                   "eleven": "11"},
        "slash": {"over": "", "slash": "", "bass": "", "with bass": "", "on": ""},
        "dur": {"whole": "1", "whole note": "1", "half": "2", "half note": "2", "quarter": "4",
                "quarter note": "4", "eighth": "8", "eighth note": "8", "sixteenth": "16", "sixteenth note": "16",
                "thirty second": "32", "thirty second note": "32", "semibreve": "1", "minim": "2",
                "crotchet": "4", "quaver": "8", "semiquaver": "16", "demisemiquaver": "32"},
        "dotted": {"dotted": "."},
        "dot": {},
        "grid": {"whole notes": "1:", "halves": "2:", "half notes": "2:", "quarters": "4:", "quarter notes": "4:",
                 "eighths": "8:", "eighth notes": "8:", "sixteenths": "16:", "sixteenth notes": "16:",
                 "thirty seconds": "32:", "thirty second notes": "32:", "minims": "2:", "crotchets": "4:",
                 "quavers": "8:", "semiquavers": "16:", "triplets": "8T:", "eighth note triplets": "8T:",
                 "eighth triplets": "8T:", "triplet eighths": "8T:", "quarter note triplets": "4T:",
                 "quarter triplets": "4T:", "triplet quarters": "4T:", "sixteenth note triplets": "16T:",
                 "sixteenth triplets": "16T:"},
        "rest": {"rest": "r", "rests": "r"},
        "of": {"of": ""},
        "bar": {"bar": "|", "bar line": "|", "barline": "|", "measure": "|"},
        "oct": {"octave": ""},
        "up": {"up": "+", "above": "+", "higher": "+"},
        "down": {"down": "-", "below": "-", "lower": "-"},
        "repeat": {"repeat": "", "repeat that": "", "repeat it": ""},
        "times": {"times": "", "time": ""},
        "count": {"twice": 2, "thrice": 3},
        "pattern": {"pattern": "", "call": ""},
        "pfunc": {"inverted": ".invert", "inversion": ".invert", "retrograde": ".retro", "reversed": ".retro",
                  "backwards": ".retro", "with thirds": ".thirds", "thirds": ".thirds",
                  "octave up": ".octave(1)", "an octave up": ".octave(1)", "octave down": ".octave(-1)",
                  "an octave down": ".octave(-1)", "augmented": ".augment(2)", "diminished": ".diminish(2)"},
        "conj": {"and": ""},
        "filler": {"then": "", "comma": "", "an": "", "the": "", "note": "", "chord": "", "chords": "",
                   "notes": "", "insert": "", "add": "", "write": "", "create": "", "put": "", "make": "",
                   "please": ""},
    },
    "fr": {
        "note": {"do": "c", "ut": "c", "ré": "d", "mi": "e", "fa": "f", "sol": "g", "la": "a", "si": "b"},
        "acc": {"dièse": "#", "bémol": "b", "#": "#", "♯": "#", "♭": "b"},
        "qual": {"mineur": "m", "mineure": "m", "majeur": "maj", "majeure": "maj", "maj": "maj", "sept": "7",
                 "septième": "7", "six": "6", "sixte": "6", "neuf": "9", "neuvième": "9", "onze": "11",
                 "treize": "13", "cinq": "5", "quinte": "5", "diminué": "dim", "diminuée": "dim",
                 "demi diminué": "m7b5", "demi diminuée": "m7b5", "augmenté": "aug", "augmentée": "aug",
                 "sus": "sus", "suspendu": "sus", "suspendue": "sus", "add": "add", "ajoutée": "add",
                 "bémol": "b", "dièse": "#"},
        "susnum": {"deux": "2", "seconde": "2", "quatre": "4", "quarte": "4", "neuf": "9", "onze": "11"},
        "slash": {"sur": "", "basse": "", "avec basse": "", "avec la basse": "", "barre": ""},
        "dur": {"ronde": "1", "blanche": "2", "noire": "4", "croche": "8", "double croche": "16",
                "triple croche": "32"},
        "dot": {"pointée": ".", "pointé": "."},
        "grid": {"rondes": "1:", "blanches": "2:", "noires": "4:", "croches": "8:", "doubles croches": "16:",
                 "double croches": "16:", "triples croches": "32:", "triolets": "8T:",
                 "triolets de croches": "8T:", "triolets de noires": "4T:", "triolets de doubles croches": "16T:",
                 "triolets de blanches": "2T:"},
        "rest": {"silence": "r", "silences": "r", "pause": "r", "pauses": "r", "soupir": "r", "soupirs": "r"},
        "of": {"de": "", "d": ""},
        "bar": {"barre de mesure": "|", "mesure": "|", "barre": "|"},
        "oct": {"octave": ""},
        "up": {"au dessus": "+", "en haut": "+", "plus haut": "+", "supérieure": "+"},
        "down": {"en dessous": "-", "au dessous": "-", "en bas": "-", "plus bas": "-", "inférieure": "-"},
        "repeat": {"répète": "", "répéter": "", "répétez": "", "répète ça": ""},
        "times": {"fois": ""},
        "count": {},
        "pattern": {"pattern": "", "motif": ""},
        "pfunc": {"inversé": ".invert", "renversé": ".invert", "inversion": ".invert", "rétrograde": ".retro",
                  "à l envers": ".retro", "avec les tierces": ".thirds", "tierces": ".thirds",
                  "octave au dessus": ".octave(1)", "une octave au dessus": ".octave(1)",
                  "octave en dessous": ".octave(-1)", "une octave en dessous": ".octave(-1)",
                  "augmenté": ".augment(2)", "diminué": ".diminish(2)"},
        "conj": {"et": ""},
        "filler": {"puis": "", "ensuite": "", "virgule": "", "une": "", "un": "", "l": "", "de": "", "le": "",
                   "note": "", "accord": "", "accords": "", "notes": "",
                   "insère": "", "insérer": "", "ajoute": "", "ajouter": "", "écris": "", "crée": "", "mets": ""},
    },
    "es": {
        "note": {"do": "c", "re": "d", "mi": "e", "fa": "f", "sol": "g", "la": "a", "si": "b"},
        "acc": {"sostenido": "#", "bemol": "b", "#": "#", "♯": "#", "♭": "b"},
        "qual": {"menor": "m", "mayor": "maj", "maj": "maj", "siete": "7", "séptima": "7", "seis": "6",
                 "sexta": "6", "nueve": "9", "novena": "9", "once": "11", "trece": "13", "cinco": "5",
                 "quinta": "5", "disminuido": "dim", "disminuida": "dim", "semidisminuido": "m7b5",
                 "semidisminuida": "m7b5", "aumentado": "aug", "aumentada": "aug", "sus": "sus",
                 "suspendido": "sus", "suspendida": "sus", "add": "add", "añadida": "add", "bemol": "b",
                 "sostenido": "#"},
        "susnum": {"dos": "2", "segunda": "2", "cuatro": "4", "cuarta": "4", "nueve": "9", "once": "11"},
        "slash": {"sobre": "", "bajo": "", "con bajo": "", "con el bajo": "", "barra": ""},
        "dur": {"redonda": "1", "blanca": "2", "negra": "4", "corchea": "8", "semicorchea": "16", "fusa": "32",
                "semifusa": "64"},
        "dot": {"con puntillo": ".", "puntillo": ".", "punteada": ".", "punteado": "."},
        "grid": {"redondas": "1:", "blancas": "2:", "negras": "4:", "corcheas": "8:", "semicorcheas": "16:",
                 "fusas": "32:", "tresillos": "8T:", "tresillos de corchea": "8T:", "tresillos de corcheas": "8T:",
                 "tresillos de negra": "4T:", "tresillos de negras": "4T:", "tresillos de semicorcheas": "16T:",
                 "tresillos de blancas": "2T:"},
        "rest": {"silencio": "r", "silencios": "r", "pausa": "r", "pausas": "r"},
        "of": {"de": ""},
        "bar": {"compás": "|", "barra de compás": "|", "barra": "|"},
        "oct": {"octava": ""},
        "up": {"arriba": "+", "más alta": "+", "superior": "+"},
        "down": {"abajo": "-", "más baja": "-", "inferior": "-"},
        "repeat": {"repite": "", "repetir": "", "repítelo": ""},
        "times": {"veces": "", "vez": ""},
        "count": {},
        "pattern": {"patrón": "", "pattern": "", "motivo": ""},
        "pfunc": {"invertido": ".invert", "inversión": ".invert", "retrógrado": ".retro", "al revés": ".retro",
                  "con terceras": ".thirds", "terceras": ".thirds", "octava arriba": ".octave(1)",
                  "una octava arriba": ".octave(1)", "octava abajo": ".octave(-1)",
                  "una octava abajo": ".octave(-1)", "aumentado": ".augment(2)", "disminuido": ".diminish(2)"},
        "conj": {"y": "", "e": ""},
        "filler": {"luego": "", "después": "", "coma": "", "un": "", "una": "", "el": "", "de": "", "nota": "",
                   "acorde": "", "acordes": "", "notas": "",
                   "inserta": "", "insertar": "", "añade": "", "agrega": "", "escribe": "", "crea": "", "pon": "",
                   "por": "", "favor": ""},
    },
}

# Il modello italiano di Vosk (riconoscimento senza rete) non ha le parole
# composte con «semi»/«bis» e le scrive staccate: «semi minima».
for _cat in ("dur", "grid", "qual"):
    for _word, _value in list(_LEXICON["it"][_cat].items()):
        for _prefix in ("semibis", "semi", "bis"):
            if _word.startswith(_prefix) and " " not in _word:
                _split = " ".join(("semi bis" if _prefix == "semibis" else _prefix, _word[len(_prefix):]))
                _LEXICON["it"][_cat].setdefault(_split, _value)
                break

# Errori tipici del riconoscimento: parola capita -> parola giusta. Per le
# note solo dove la parola capita non ha un senso musicale suo.
_FIXES = {
    "it": {"note": {"dò": "do", "dó": "do", "doh": "do", "ré": "re", "rè": "re", "mì": "mi", "fà": "fa",
                    "sole": "sol", "so": "sol", "soul": "sol", "là": "la", "lá": "la", "sì": "si", "sí": "si"},
           "acc": {"bemolli": "bemolle", "bemol": "bemolle", "diesi": "diesis"}},
    "en": {"note": {"see": "c", "sea": "c", "cee": "c", "si": "c", "dee": "d", "de": "d", "ee": "e",
                    "eff": "f", "ef": "f", "gee": "g", "jee": "g", "ay": "a", "eh": "a", "be": "b", "bee": "b"}},
    "fr": {"note": {"re": "ré", "rè": "ré", "rai": "ré", "raie": "ré", "dos": "do", "dot": "do", "mie": "mi",
                    "mis": "mi", "mit": "mi", "sole": "sol", "saule": "sol", "là": "la", "las": "la", "scie": "si",
                    "sis": "si", "ci": "si"},
           "acc": {"dièze": "dièse", "diese": "dièse", "bemol": "bémol", "bémols": "bémol"}},
    "es": {"note": {"dó": "do", "ré": "re", "rey": "re", "mí": "mi", "fá": "fa", "lá": "la", "sí": "si",
                    "sola": "sol"},
           "acc": {"bemoles": "bemol", "sostenida": "sostenido"}},
}

# «re» capito come «e»: in italiano «e» fra le note e' quasi sempre un re
# (segnalato come incerto); fra gli accordi e' la congiunzione.
_E_AS_RE = {"it": "e"}

_NUMBERS = {"it": _it_numbers(), "en": _en_numbers(), "fr": _fr_numbers(), "es": _es_numbers()}

# Comandi: nome, schema, segno del valore. Nello schema le parole separate
# da «|» sono alternative, «?» rende facoltativa la parola, «#» e' un numero,
# «*» il resto della frase. Vince lo schema che copre piu' parole.
_COMMANDS = {
    "it": [
        ("delete_last", "cancella|cancellalo|togli l? ultima|ultimo?", 1),
        ("undo", "annulla", 1),
        ("play_bar", "suona la? battuta", 1),
        ("play_from_start", "suona da|dal|dall capo|inizio|principio", 1),
        ("play_from_start", "suona tutto", 1),
        ("play_from_start", "suona il brano", 1),
        ("play", "suona|riproduci", 1),
        ("stop", "stop|ferma|fermati|basta", 1),
        ("tempo", "tempo a|à? #", 1),
        ("transpose", "trasponi|trasporta di? più|piu? # semitoni?", 1),
        ("transpose", "trasponi|trasporta su|sopra di # semitoni?", 1),
        ("transpose", "trasponi|trasporta su|sopra # semitoni?", 1),
        ("transpose", "trasponi|trasporta giù|giu|sotto di? # semitoni?", -1),
        ("transpose", "trasponi|trasporta di? meno # semitoni?", -1),
        ("goto_bar", "vai|va|torna alla|a battuta #", 1),
        ("new_track", "nuova? traccia nuova? *", 1),
        ("end", "fine della? dettatura", 1),
        ("confirm", "conferma|confermo|ok|okay", 1),
        ("confirm", "va bene", 1),
    ],
    "en": [
        ("delete_last", "delete|erase|scratch that?", 1),
        ("undo", "undo", 1),
        ("play_bar", "play the|this? bar|measure", 1),
        ("play_from_start", "play from the? start|beginning|top", 1),
        ("play_from_start", "play everything|all", 1),
        ("play", "play", 1),
        ("stop", "stop", 1),
        ("tempo", "set? tempo|bpm to? #", 1),
        ("transpose", "transpose by? plus? # semitones?", 1),
        ("transpose", "transpose up by? # semitones?", 1),
        ("transpose", "transpose down by? # semitones?", -1),
        ("transpose", "transpose by? minus # semitones?", -1),
        ("goto_bar", "go to bar|measure #", 1),
        ("new_track", "a? new? track *", 1),
        ("end", "end|stop|finish dictation", 1),
        ("confirm", "confirm|ok|okay|yes", 1),
    ],
    "fr": [
        ("delete_last", "efface|effacer|supprime|supprimer", 1),
        ("undo", "annule|annuler", 1),
        ("play_bar", "joue|jouer la|cette mesure", 1),
        ("play_from_start", "joue|jouer depuis|du|au le? début|commencement", 1),
        ("play_from_start", "joue|jouer tout", 1),
        ("play", "joue|jouer|lecture", 1),
        ("stop", "stop|arrête|arrete", 1),
        ("tempo", "tempo a|à? #", 1),
        ("transpose", "transpose|transposer de? # demi? tons?", 1),
        ("transpose", "transpose|transposer plus de? # demi? tons?", 1),
        ("transpose", "transpose|transposer de? # demi? tons? vers le haut", 1),
        ("transpose", "transpose|transposer moins de? # demi? tons?", -1),
        ("transpose", "transpose|transposer de? # demi? tons? vers le bas", -1),
        ("goto_bar", "va|aller|allez à|a la mesure #", 1),
        ("new_track", "nouvelle? piste *", 1),
        ("end", "fin de la? dictée", 1),
        ("confirm", "confirme|confirmer|ok|okay|oui", 1),
    ],
    "es": [
        ("delete_last", "borra|borrar|bórralo", 1),
        ("undo", "deshaz|deshacer", 1),
        ("play_bar", "toca|tocar el|este? compás", 1),
        ("play_from_start", "toca|tocar desde el? principio|inicio|comienzo", 1),
        ("play_from_start", "toca|tocar todo", 1),
        ("play", "toca|tocar|reproduce", 1),
        ("stop", "para|parar|detén|detente|stop", 1),
        ("tempo", "tempo a|à? #", 1),
        ("transpose", "transpón|transpon|transporta|transponer más|mas|arriba? # semitonos? arriba?", 1),
        ("transpose", "transpón|transpon|transporta|transponer # semitonos? abajo", -1),
        ("transpose", "transpón|transpon|transporta|transponer menos|abajo # semitonos? abajo?", -1),
        ("goto_bar", "ve|ir|vete|vamos al compás #", 1),
        ("new_track", "nueva? pista *", 1),
        ("end", "fin del dictado", 1),
        ("confirm", "confirma|confirmar|ok|okay|vale", 1),
        ("end", "termina|terminar el dictado", 1),
    ],
}


def _command_schema(text: str) -> list:
    out = []
    for part in text.split():
        optional = part.endswith("?")
        part = part.rstrip("?")
        words = part.split("|")
        out.append((part if part in ("#", "*") else frozenset(words + [_strip_accents(w) for w in words]),
                    optional))
    return out


class _Language:
    """Il lessico di una lingua pronto per la ricerca: categoria -> frase
    (tupla di parole) -> (valore, parola giusta se corretta)."""

    def __init__(self, lang: str):
        self.lang = lang
        self.table: Dict[str, Dict[Tuple[str, ...], Tuple[object, Optional[str]]]] = {}
        for cat, entries in _LEXICON[lang].items():
            table = self.table.setdefault(cat, {})
            for phrase, value in entries.items():
                for variant in {phrase, _strip_accents(phrase)}:
                    table.setdefault(tuple(_words(variant)), (value, None))
        for cat, fixes in _FIXES.get(lang, {}).items():
            table = self.table[cat]
            for heard, right in fixes.items():
                value = _LEXICON[lang][cat].get(right, right)
                table.setdefault((heard,), (value, right))
        self.table["num"] = {}
        for phrase, n in _NUMBERS[lang].items():
            for variant in {phrase, _strip_accents(phrase)}:
                self.table["num"].setdefault(tuple(_words(variant)), (n, None))
        self.longest = {cat: max((len(k) for k in t), default=0) for cat, t in self.table.items()}
        self.commands = [(name, _command_schema(schema), sign) for name, schema, sign in _COMMANDS[lang]]


def _words(text: str) -> List[str]:
    return [w for w in re.split(r"[\s'’\-]+", text.lower()) if w]


_LANGS: Dict[str, _Language] = {}


def _language(lang: str) -> _Language:
    lang = (lang or "it").split("-")[0].split("_")[0].lower()
    if lang not in LANGUAGES:
        lang = "it"
    if lang not in _LANGS:
        _LANGS[lang] = _Language(lang)
    return _LANGS[lang]


# ------------------------------------------------------------------ frase

_SYMBOL = re.compile(r"^([A-G])([#b♯♭]?)([A-Za-z0-9#♭]*)(?:/([A-G])([#b♯♭]?))?$")


def _chord_symbol(raw: str) -> Optional[Tuple[str, str, str, str]]:
    """Un accordo scritto gia' come simbolo dal riconoscimento («G7», «F#m»,
    «C/E»): (lettera, alterazione, qualita', basso)."""
    m = _SYMBOL.match(raw)
    if not m or len(raw) < 2:
        return None
    letter, acc, quality, bass, bass_acc = m.groups()
    acc = {"♯": "#", "♭": "b"}.get(acc, acc)
    if quality not in CHORD_QUALITIES:
        return None
    return letter, acc, quality, (bass + {"♯": "#", "♭": "b"}.get(bass_acc, bass_acc)) if bass else ""


class _Token:
    __slots__ = ("word", "raw", "symbol")

    def __init__(self, word, raw, symbol=None):
        self.word, self.raw, self.symbol = word, raw, symbol


def _tokens(phrase: str) -> List[_Token]:
    out = []
    for raw in re.findall(r"[^\s,.;:!?«»\"“”()\[\]]+", phrase.replace("’", "'")):
        symbol = _chord_symbol(raw)
        if symbol:
            out.append(_Token(raw.lower(), raw, symbol))
            continue
        for piece in re.split(r"['\-]+", raw):
            # «sol7», «fa#»: i numeri e i segni si staccano dalle parole
            for part in re.findall(r"\d+|[#♯♭/]|[^\d#♯♭/]+", piece):
                out.append(_Token(part.lower(), part))
    return out


def _item(kind: str, said: List[_Token], st: str = "", heard: Optional[str] = None, **extra) -> dict:
    item = {"kind": kind, "said": " ".join(t.raw for t in said), "st": st, "uncertain": heard is not None,
            "heard": heard}
    item.update(extra)
    return item


def _compose(item: dict) -> None:
    """Il token ST di una nota, di un accordo o di una pausa dalle sue parti:
    moltiplicatore, base, ottava, valore."""
    parts = item["parts"]
    mult = parts.get("mult") or ""
    item["st"] = f"{mult}{parts['base']}{parts.get('octave', '')}{parts.get('value', '')}"


def _quality(fragments: List[str]) -> Optional[str]:
    """La qualita' ST di un accordo dai pezzi detti (["m", "7", "b", "5"] ->
    "m7b5"), None se non e' una qualita' che SoundText conosce."""
    frags = list(fragments)
    for word in ("maj", "dim"):                        # «settima maggiore», «settima diminuita»
        if word in frags:
            k = frags.index(word)
            if k > 0 and frags[k - 1] in ("7", "9", "13"):
                frags[k - 1], frags[k] = frags[k], frags[k - 1]
    text = "".join(frags).replace("mmaj", "mMaj")
    if text == "maj":
        return ""
    if text.endswith("sus"):
        text += "4"
    return text if text in CHORD_QUALITIES else None


class _Parser:
    def __init__(self, tokens: List[_Token], lang: _Language, chords: bool, patterns: Dict[str, str]):
        self.t = tokens
        self.lang = lang
        self.chords = chords
        self.patterns = patterns
        self.items: List[dict] = []

    # ricerca nel lessico: (valore, fine, parola giusta se corretta)
    def look(self, i: int, cat: str):
        table = self.lang.table.get(cat, {})
        for n in range(min(self.lang.longest.get(cat, 0), len(self.t) - i), 0, -1):
            key = tuple(tok.word for tok in self.t[i:i + n])
            if key in table:
                value, fixed = table[key]
                return value, i + n, fixed
        if cat == "num" and i < len(self.t) and self.t[i].word.isdigit():
            return int(self.t[i].word), i + 1, None
        return None

    def run(self) -> List[dict]:
        i = 0
        while i < len(self.t):
            i = self.step(i)
        return self.items

    def step(self, i: int) -> int:
        for fn in (self.command, self.grid, self.bar, self.repeat, self.octave, self.pattern, self.atom):
            end = fn(i)
            if end is not None:
                return end
        tok = self.t[i]
        if self.look(i, "conj") and (self.chords or tok.word not in _E_AS_RE.get(self.lang.lang, ())):
            return i + 1
        found = self.look(i, "filler")
        if found:
            return found[1]
        self.items.append(_item("unknown", [tok], heard=tok.raw))
        return i + 1

    # -- comandi
    def command(self, i: int) -> Optional[int]:
        best = None
        for name, schema, sign in self.lang.commands:
            end, value = self.match(schema, i)
            if end is not None and (best is None or end > best[0]):
                best = (end, name, value * sign if isinstance(value, int) else value)
        if best is None:
            return None
        end, name, value = best
        self.items.append(_item("command", self.t[i:end], command=name, value=value))
        return end

    def match(self, schema, i: int):
        value = None
        for k, (want, optional) in enumerate(schema):
            if want == "*":
                if i >= len(self.t):
                    return None, None
                value = " ".join(tok.raw for tok in self.t[i:])
                i = len(self.t)
                continue
            if want == "#":
                found = self.look(i, "num")
                if found is None:
                    if optional:
                        continue
                    return None, None
                value, i = found[0], found[1]
                continue
            if i < len(self.t) and (self.t[i].word in want or _strip_accents(self.t[i].word) in want):
                i += 1
            elif not optional:
                return None, None
        return i, value

    # -- griglia, stanghetta
    def grid(self, i: int) -> Optional[int]:
        found = self.look(i, "grid")
        if not found:
            return None
        self.items.append(_item("grid", self.t[i:found[1]], found[0]))
        return found[1]

    def bar(self, i: int) -> Optional[int]:
        found = self.look(i, "bar")
        if not found:
            return None
        self.items.append(_item("bar", self.t[i:found[1]], "|"))
        return found[1]

    # -- «ripeti due volte»
    def repeat(self, i: int) -> Optional[int]:
        found = self.look(i, "repeat")
        if not found:
            return None
        end, count = found[1], 2
        counted = self.look(end, "count")
        number = self.look(end, "num")
        if counted:
            count, end = counted[0], counted[1]
        elif number and number[0] > 1:
            count, end = number[0], number[1]
            times = self.look(end, "times")
            if times:
                end = times[1]
        said = self.t[i:end]
        music = ("note", "chord", "rest", "grid", "pattern", "repeat")
        stop = len(self.items)
        while stop > 0 and self.items[stop - 1]["kind"] == "bar":
            stop -= 1
        start = stop
        while start > 0 and self.items[start - 1]["kind"] in music:
            start -= 1
        while start < stop and self.items[start]["kind"] == "grid":   # «ottavi» resta fuori dal gruppo
            start += 1
        inner = self.items[start:stop]
        if not inner:
            self.items.append(_item("command", said, command="repeat", value=count))
            return end
        group = _item("repeat", [], f"{count}({' '.join(it['st'] for it in inner)})", count=count,
                      children=inner)
        group["said"] = " ".join([it["said"] for it in inner] + [tok.raw for tok in said])
        group["uncertain"] = any(it["uncertain"] for it in inner)
        self.items[start:stop] = [group]
        return end

    # -- «ottava cinque», «ottava sopra»
    def octave(self, i: int) -> Optional[int]:
        found = self.look(i, "oct")
        if not found:
            return None
        end = found[1]
        number = self.look(end, "num")
        up, down = self.look(end, "up"), self.look(end, "down")
        if number and 0 <= number[0] <= 9:
            mark, end = f"*{number[0]}", number[1]
        elif up:
            mark, end = "*+", up[1]
        elif down:
            mark, end = "*-", down[1]
        else:
            return None
        last = self.items[-1] if self.items else None
        if not last or last["kind"] not in ("note", "chord") or "octave" in last["parts"]:
            self.items.append(_item("unknown", self.t[i:end], heard=" ".join(t.raw for t in self.t[i:end])))
            return end
        last["parts"]["octave"] = mark
        last["said"] += " " + " ".join(tok.raw for tok in self.t[i:end])
        _compose(last)
        return end

    # -- «pattern Tema», «Tema invertito»
    def pattern(self, i: int) -> Optional[int]:
        named = self.known_pattern(i)
        if named:
            name, end = named
        else:
            found = self.look(i, "pattern")
            if not found or found[1] >= len(self.t):
                return None
            end = found[1]
            named = self.known_pattern(end)
            if named:
                name, end = named
            else:
                raw = re.sub(r"\W", "", self.t[end].raw)
                if not raw:
                    return None
                name, end = raw[0].upper() + raw[1:], end + 1
        st = "%" + name
        while True:
            func = self.look(end, "pfunc")
            if not func:
                break
            st += func[0]
            end = func[1]
        self.items.append(_item("pattern", self.t[i:end], st))
        return end

    def known_pattern(self, i: int) -> Optional[Tuple[str, int]]:
        if i < len(self.t):
            key = _strip_accents(re.sub(r"\W", "", self.t[i].word))
            if key in self.patterns:
                return self.patterns[key], i + 1
        return None

    # -- note, accordi, pause (con il moltiplicatore davanti)
    def atom(self, i: int) -> Optional[int]:
        mult = ""
        start = i
        number = self.look(i, "num")
        if number and number[1] < len(self.t) and (self.look(number[1], "rest") or self.is_root(number[1])
                                                    or self.value_before_rest(number[1])):
            if number[0] < 1:
                return None
            mult = "" if number[0] == 1 else str(number[0])
            i = number[1]
        value = self.value_before_rest(i)               # «half rest», «dotted quarter rest»
        if value:
            item = _item("rest", self.t[start:value[1]], parts={"base": "r", "mult": mult, "value": value[0]})
            _compose(item)
            self.items.append(item)
            return value[1]
        rest = self.look(i, "rest")
        if rest:
            item = _item("rest", self.t[start:rest[1]], parts={"base": "r", "mult": mult})
            end = self.duration(rest[1], item, allow_of=True)
            item["said"] = " ".join(t.raw for t in self.t[start:end])
            _compose(item)
            self.items.append(item)
            return end
        root = self.root(i)
        if not root:
            return None
        letter, end, heard = root
        tok = self.t[i]
        if tok.symbol:                                  # «G7», «F#m» scritti dal riconoscimento
            sym_letter, acc, quality, bass = tok.symbol
            chord = bool(quality) or self.chords or bool(bass)
            base = (sym_letter + acc + quality + ("/" + bass if bass else "")) if chord \
                else sym_letter.lower() + acc
            item = _item("chord" if chord else "note", self.t[start:end], parts={"base": base, "mult": mult})
        else:
            acc = self.look(end, "acc")
            accidental = ""
            if acc:
                accidental, end = acc[0], acc[1]
                heard = heard or (self.t[end - 1].raw if acc[2] else None)
            quality, end = self.quality(end)
            bass = self.slash(end)                     # «do su mi»: un accordo col basso
            chord = quality is not None or self.chords or bass is not None
            if chord:
                base = letter.upper() + accidental + (quality or "")
                if bass:
                    base += "/" + bass[0]
                    end = bass[1]
            else:
                base = letter + accidental
            item = _item("chord" if chord else "note", self.t[start:end], parts={"base": base, "mult": mult},
                         heard=heard)
        end = self.duration(end, item)
        item["said"] = " ".join(t.raw for t in self.t[start:end])
        _compose(item)
        self.items.append(item)
        return end

    def value_before_rest(self, i: int) -> Optional[Tuple[str, int]]:
        dotted = self.look(i, "dotted")
        j = dotted[1] if dotted else i
        found = self.look(j, "dur")
        if not found:
            return None
        rest = self.look(found[1], "rest")
        if not rest:
            return None
        return f"'{found[0]}{'.' if dotted else ''}", rest[1]

    def is_root(self, i: int) -> bool:
        return self.root(i) is not None

    def root(self, i: int):
        if i >= len(self.t):
            return None
        tok = self.t[i]
        if tok.symbol:
            return tok.symbol[0].lower(), i + 1, None
        if tok.word in _E_AS_RE.get(self.lang.lang, ()):
            if self.chords:
                return None
            return "d", i + 1, tok.raw
        found = self.look(i, "note")
        if not found:
            return None
        letter, end, fixed = found
        return letter, end, (tok.raw if fixed else None)

    def quality(self, i: int) -> Tuple[Optional[str], int]:
        """I pezzi della qualita' dopo la fondamentale, il piu' lungo che fa
        una qualita' valida."""
        frags, ends = [], []
        j = i
        while j < len(self.t):
            after_sus = frags and frags[-1] in ("sus", "add")
            found = self.look(j, "susnum") if after_sus else None
            found = found or self.look(j, "qual")
            if not found and self.t[j].word.isdigit() and self.t[j].word in ("5", "6", "7", "9", "11", "13"):
                found = (self.t[j].word, j + 1, None)
            if not found:
                break
            frags.append(found[0])
            j = found[1]
            ends.append(j)
        for n in range(len(frags), 0, -1):
            q = _quality(frags[:n])
            if q is not None:
                return q, ends[n - 1]
        return None, i

    def slash(self, i: int) -> Optional[Tuple[str, int]]:
        found = self.look(i, "slash")
        if not found:
            return None
        root = self.root(found[1])
        if not root or self.t[found[1]].symbol:
            return None
        letter, end, _heard = root
        acc = self.look(end, "acc")
        if acc:
            return letter.upper() + acc[0], acc[1]
        return letter.upper(), end

    def duration(self, i: int, item: dict, allow_of: bool = False) -> int:
        """Il valore di nota detto dopo una nota, un accordo o una pausa
        («minima», «semiminima puntata», «dotted quarter», «pausa di minima»)."""
        j = i
        dotted = ""
        of = self.look(j, "of") if allow_of else None
        if of:
            j = of[1]
        before = self.look(j, "dotted")
        if before:
            dotted, j = ".", before[1]
        found = self.look(j, "dur")
        if not found:
            return i
        grid = self.look(j, "grid")                    # «E eighth note triplets»: la griglia dopo la nota
        if grid and grid[1] > found[1]:
            return i
        value, j = found[0], found[1]
        after = self.look(j, "dot")
        if after:
            dotted, j = ".", after[1]
        item["parts"]["value"] = f"'{value}{dotted}"
        return j


def interpret(phrase: str, lang: str = "it", mode: str = "auto", patterns: Iterable[str] = ()) -> dict:
    """La frase riconosciuta -> testo ST, pezzi e comandi (vedi il docstring
    del modulo). patterns: i nomi dei pattern del brano, per riconoscere
    «Tema invertito» senza la parola «pattern» e scriverli con le maiuscole
    giuste."""
    language = _language(lang)
    tokens = _tokens(phrase or "")
    known = {_strip_accents(p.lstrip("%").lower()): p.lstrip("%") for p in patterns}
    chords = mode == "chords"
    items = _Parser(tokens, language, chords, known).run()
    if mode == "auto" and not chords and any(it["kind"] == "chord" for it in _flat(items)):
        chords = True
        items = _Parser(tokens, language, chords, known).run()
    for it in _flat(items):
        it.pop("parts", None)
    return {
        "text": " ".join(it["st"] for it in items if it["st"]),
        "items": items,
        "commands": [{"command": it["command"], "value": it["value"]} for it in items if it["kind"] == "command"],
        "unknown": [it["said"] for it in items if it["kind"] == "unknown"],
        "mode": "chords" if chords else "notes",
        "lang": language.lang,
    }


def _flat(items: List[dict]):
    for it in items:
        yield it
        yield from _flat(it.get("children", []))


def vocabulary(lang: str = "it", patterns: Iterable[str] = ()) -> List[str]:
    """Le parole che l'interprete capisce in una lingua (note, qualita',
    valori, griglie, numeri fino a 300, comandi) piu' i nomi dei pattern del
    brano: la grammatica del riconoscimento vocale locale, che cosi' sceglie
    solo fra parole attese («re» non diventa «e»). Senza le correzioni degli
    errori, che con la grammatica non servono."""
    language = _language(lang)
    words = set()
    for cat, entries in _LEXICON[language.lang].items():
        for phrase in entries:
            words.update(_words(phrase))
    for phrase in _NUMBERS[language.lang]:
        words.update(_words(phrase))
    for _name, schema, _sign in _COMMANDS[language.lang]:
        for part in schema.split():
            part = part.rstrip("?")
            if part not in ("#", "*"):
                words.update(w for w in part.split("|"))
    words.update(_words(" ".join(p.lstrip("%") for p in patterns)))
    return sorted(w for w in words if re.fullmatch(r"[^\W\d_]+", w))


# Gli strumenti che si possono dire dopo «nuova traccia» (il motore li
# riconosce con st_language.instruments): solo per la grammatica.
_INSTRUMENT_WORDS = {
    "it": ["pianoforte", "piano", "chitarra", "basso", "batteria", "archi", "violino", "violoncello", "flauto",
           "tromba", "sassofono", "organo", "voce", "clarinetto"],
    "en": ["piano", "guitar", "bass", "drums", "strings", "violin", "cello", "flute", "trumpet", "saxophone",
           "organ", "voice", "clarinet"],
    "fr": ["piano", "guitare", "basse", "batterie", "cordes", "violon", "violoncelle", "flûte", "trompette",
           "saxophone", "orgue", "voix", "clarinette"],
    "es": ["piano", "guitarra", "bajo", "batería", "cuerdas", "violín", "violonchelo", "flauta", "trompeta",
           "saxofón", "órgano", "voz", "clarinete"],
}

# Lo strumento di SoundText per ogni parola di _INSTRUMENT_WORDS (nell'ordine
# dell'inglese; in italiano «pianoforte» e «piano» sono lo stesso).
_INSTRUMENT_NAMES = ["Piano", "Guitar", "Bass", "Drums", "Strings", "Violin", "Cello", "Flute", "Trumpet",
                     "Sax", "Organ", "Voice", "Clarinet"]


def instrument_name(spoken: str, lang: str = "it") -> Optional[str]:
    """«nuova traccia basso»: lo strumento di SoundText («Bass») per la parola
    detta, o None se non e' uno strumento che la dettatura conosce."""
    language = _language(lang)
    names = [_strip_accents(w) for w in _INSTRUMENT_WORDS[language.lang]]
    canon = _INSTRUMENT_NAMES if len(names) == len(_INSTRUMENT_NAMES) else _INSTRUMENT_NAMES[:1] + _INSTRUMENT_NAMES
    for word in _words(spoken or ""):
        word = _strip_accents(word)
        if word in names:
            return canon[names.index(word)]
    return None


def grammar(lang: str = "it", patterns: Iterable[str] = ()) -> List[str]:
    """La grammatica del riconoscimento vocale locale (Vosk): solo le parole
    che l'interprete usa, piu' le frasi di piu' parole del lessico e dei
    comandi («semi minima puntata», «suona la battuta», «nuova traccia
    chitarra»), da cui Vosk ricava quali parole si seguono, e «[unk]», che
    raccoglie quello che non e' musica invece di forzarlo in una nota."""
    language = _language(lang)
    phrases = set()
    for cat, entries in _LEXICON[language.lang].items():
        phrases.update(" ".join(_words(p)) for p in entries if len(_words(p)) > 1)
    for _name, schema, _sign in _COMMANDS[language.lang]:
        words = []
        for part in schema.split():
            part = part.rstrip("?")
            if part in ("#", "*"):
                break
            words.append(part.split("|")[0])
        if len(words) > 1:
            phrases.add(" ".join(words))
    lex = _LEXICON[language.lang]
    # le coppie che si dicono di seguito: «fa diesis», «la minore»,
    # «semi minima puntata» (in inglese «dotted quarter»)
    for note in lex["note"]:
        phrases.update(f"{note} {w}" for w in list(lex["acc"]) + list(lex["qual"]) if w.isalpha() or " " in w)
    for value in lex["dur"]:
        phrases.update(f"{value} {dot}" for dot in lex["dot"])
        phrases.update(f"{dot} {value}" for dot in lex.get("dotted", {}))
    head = {"it": "nuova traccia", "en": "new track", "fr": "nouvelle piste", "es": "nueva pista"}[language.lang]
    phrases.update(f"{head} {w}" for w in _INSTRUMENT_WORDS[language.lang])
    words = set(vocabulary(lang, patterns)) | set(_INSTRUMENT_WORDS[language.lang])
    return sorted(phrases) + sorted(words) + ["[unk]"]
