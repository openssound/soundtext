"""
L'interprete della dettatura (core/dictation.py): ogni riga della tabella
«Che cosa si detta» del progetto di SoundText Mobile, nelle quattro lingue,
gli errori tipici del riconoscimento vocale e i comandi a voce. Il testo
prodotto deve anche leggersi in SoundText (validate_track_text).

Esecuzione:
    python3 -m pytest tests/test_dictation.py -v
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _config_isolation  # noqa: F401,E402

import pytest  # noqa: E402

from core.dictation import LANGUAGES, interpret  # noqa: E402
from core.notation import validate_track_text  # noqa: E402
from core.project_io import parse_project_text  # noqa: E402

PATTERNS = parse_project_text("ST: 2.6\nTempo: 100 BPM\n\nPattern %Tema:\n  8: c d e g 2e 2c\n", "Prova").patterns


def _valid(text: str) -> None:
    """Il testo dettato si legge come testo di una traccia; *+ e *- valgono
    nel modo relativo."""
    source = ("rel: " + text) if "*+" in text or "*-" in text else text
    ok, error = validate_track_text(source, PATTERNS)
    assert ok, (text, error)


# La tabella del progetto, riga per riga: (lingua, frase detta, testo ST).
TABLE = [
    # «do re mi fa sol» -> c d e f g
    ("it", "do re mi fa sol", "c d e f g"),
    ("en", "C D E F G", "c d e f g"),
    ("fr", "do ré mi fa sol", "c d e f g"),
    ("es", "do re mi fa sol", "c d e f g"),
    ("it", "la si", "a b"),
    ("en", "A B", "a b"),
    ("fr", "ut la si", "c a b"),
    ("es", "la si", "a b"),
    # «fa diesis», «si bemolle» -> f#, bb
    ("it", "fa diesis, si bemolle", "f# bb"),
    ("en", "F sharp, B flat", "f# bb"),
    ("fr", "fa dièse, si bémol", "f# bb"),
    ("es", "fa sostenido, si bemol", "f# bb"),
    # «do ottava cinque», «ottava sopra», «ottava sotto» -> c*5, *+, *-
    ("it", "do ottava cinque, re ottava sopra, mi ottava sotto", "c*5 d*+ e*-"),
    ("en", "C octave five, D octave up, E octave down", "c*5 d*+ e*-"),
    ("fr", "do octave cinq, ré octave au-dessus, mi octave en dessous", "c*5 d*+ e*-"),
    ("es", "do octava cinco, re octava arriba, mi octava abajo", "c*5 d*+ e*-"),
    ("it", "sol un'ottava sopra", "g*+"),
    ("it", "do ottava 4", "c*4"),
    # «quarti», «ottavi», «sedicesimi», «terzine di ottavi» -> 4:, 8:, 16:, 8T:
    ("it", "quarti do, ottavi re, sedicesimi mi, terzine di ottavi fa", "4: c 8: d 16: e 8T: f"),
    ("en", "quarters C, eighths D, sixteenths E, eighth note triplets F", "4: c 8: d 16: e 8T: f"),
    ("fr", "noires do, croches ré, doubles croches mi, triolets de croches fa", "4: c 8: d 16: e 8T: f"),
    ("es", "negras do, corcheas re, semicorcheas mi, tresillos de corcheas fa", "4: c 8: d 16: e 8T: f"),
    ("it", "semiminime do crome re semicrome mi", "4: c 8: d 16: e"),
    ("en", "crotchets C quavers D semiquavers E", "4: c 8: d 16: e"),
    # «do minima», «re semiminima puntata», «pausa», «due pause» -> c'2, d'4., r, 2r
    ("it", "do minima, re semiminima puntata, pausa, due pause", "c'2 d'4. r 2r"),
    ("en", "C half note, D dotted quarter, rest, two rests", "c'2 d'4. r 2r"),
    ("fr", "do blanche, ré noire pointée, silence, deux silences", "c'2 d'4. r 2r"),
    ("es", "do blanca, re negra con puntillo, silencio, dos silencios", "c'2 d'4. r 2r"),
    ("it", "mi croma, fa semibreve, pausa di minima", "e'8 f'1 r'2"),
    ("en", "E eighth, F whole, half rest, two dotted quarter rests", "e'8 f'1 r'2 2r'4."),
    ("en", "G minim, A crotchet", "g'2 a'4"),
    ("it", "tre do", "3c"),
    # «battuta», «stanghetta» -> |
    ("it", "do re battuta mi fa stanghetta", "c d | e f |"),
    ("en", "C D bar E F bar line", "c d | e f |"),
    ("fr", "do ré barre de mesure mi fa mesure", "c d | e f |"),
    ("es", "do re compás mi fa barra de compás", "c d | e f |"),
    # «la minore», «sol sette», «do maggiore settima», «re minore sette bemolle cinque»
    ("it", "la minore, sol sette, do maggiore settima, re minore sette bemolle cinque", "Am G7 Cmaj7 Dm7b5"),
    ("en", "A minor, G seven, C major seventh, D minor seven flat five", "Am G7 Cmaj7 Dm7b5"),
    ("fr", "la mineur, sol sept, do majeur septième, ré mineur sept bémol cinq", "Am G7 Cmaj7 Dm7b5"),
    ("es", "la menor, sol siete, do mayor séptima, re menor siete bemol cinco", "Am G7 Cmaj7 Dm7b5"),
    # e la frase d'esempio del progetto: «la minore, fa, do, sol» -> Am F C G
    ("it", "la minore, fa, do, sol", "Am F C G"),
    ("en", "A minor, F, C, G", "Am F C G"),
    ("fr", "la mineur, fa, do, sol", "Am F C G"),
    ("es", "la menor, fa, do, sol", "Am F C G"),
    # altre qualita'
    ("it", "do settima maggiore, si semidiminuito, mi bemolle diminuito sette, fa sus quattro",
     "Cmaj7 Bm7b5 Ebdim7 Fsus4"),
    ("en", "C major seven, B half diminished, E flat diminished seven, F sus four", "Cmaj7 Bm7b5 Ebdim7 Fsus4"),
    ("fr", "do septième majeure, si demi-diminué, mi bémol diminué sept, fa sus quatre",
     "Cmaj7 Bm7b5 Ebdim7 Fsus4"),
    ("es", "do séptima mayor, si semidisminuido, mi bemol disminuido siete, fa sus cuatro",
     "Cmaj7 Bm7b5 Ebdim7 Fsus4"),
    ("it", "la minore settima maggiore, do aumentato, re sei, sol nove, do maggiore", "AmMaj7 Caug D6 G9 C"),
    ("it", "fa diesis minore sette, do su mi", "F#m7 C/E"),
    ("en", "C over E, G slash B", "C/E G/B"),
    ("it", "sol 7 do", "G7 C"),
    # «ripeti due volte» -> 2( … )
    ("it", "ottavi do re mi fa ripeti due volte", "8: 2(c d e f)"),
    ("en", "eighths C D E F repeat twice", "8: 2(c d e f)"),
    ("fr", "croches do ré mi fa répète deux fois", "8: 2(c d e f)"),
    ("es", "corcheas do re mi fa repite dos veces", "8: 2(c d e f)"),
    ("it", "do re battuta mi fa battuta ripeti tre volte", "c d | 3(e f) |"),
    ("en", "A minor F repeat four times", "4(Am F)"),
    # «pattern Tema», «Tema invertito» -> %Tema, %Tema.invert
    ("it", "pattern Tema, Tema invertito", "%Tema %Tema.invert"),
    ("en", "pattern Tema, Tema inverted", "%Tema %Tema.invert"),
    ("fr", "motif Tema, Tema inversé", "%Tema %Tema.invert"),
    ("es", "patrón Tema, Tema invertido", "%Tema %Tema.invert"),
    ("it", "pattern tema retrogrado con le terze", "%Tema.retro.thirds"),
    ("it", "tema un'ottava sopra", "%Tema.octave(1)"),
]


@pytest.mark.parametrize("lang,phrase,expected", TABLE)
def test_table(lang, phrase, expected):
    result = interpret(phrase, lang, patterns=["Tema"])
    assert result["text"] == expected
    assert not result["unknown"] and not result["commands"]
    assert not any(it["uncertain"] for it in result["items"])
    _valid(result["text"])


def test_every_row_in_every_language():
    """Ogni lingua ha una frase per ogni riga della tabella del progetto
    (9 righe, la ripetizione e il pattern compresi)."""
    rows = ["c d e f g", "f# bb", "c*5 d*+ e*-", "4: c 8: d 16: e 8T: f", "c'2 d'4. r 2r", "c d | e f |",
            "Am G7 Cmaj7 Dm7b5", "8: 2(c d e f)", "%Tema %Tema.invert"]
    for lang in LANGUAGES:
        said = {expected for lg, _p, expected in TABLE if lg == lang}
        assert all(row in said for row in rows), lang


# Errori tipici del riconoscimento: la parola capita viene corretta e il
# pezzo resta segnalato come incerto, con la parola capita.
FIXES = [
    ("it", "do e mi", "c d e", ["e"]),                 # «re» capito come «e»
    ("it", "sol la sì", "g a b", ["sì"]),              # «si» capito come «sì»
    ("it", "fa là", "f a", ["là"]),
    ("it", "sole fa", "g f", ["sole"]),
    ("it", "so fa", "g f", ["so"]),
    ("it", "dò re", "c d", ["dò"]),
    ("it", "si bemolli", "bb", ["bemolli"]),
    ("en", "see dee ee", "c d e", ["see", "dee", "ee"]),
    ("en", "bee flat, gee sharp", "bb g#", ["bee", "gee"]),
    ("fr", "do raie mi", "c d e", ["raie"]),
    ("fr", "saule là scie", "g a b", ["saule", "là", "scie"]),
    ("fr", "mie dièze", "e#", ["mie"]),
    ("es", "sol la sí", "g a b", ["sí"]),
    ("es", "do rey mí", "c d e", ["rey", "mí"]),
    ("es", "lá menor", "Am", ["lá"]),
]


@pytest.mark.parametrize("lang,phrase,expected,heard", FIXES)
def test_recognition_errors(lang, phrase, expected, heard):
    result = interpret(phrase, lang)
    assert result["text"] == expected
    assert [it["heard"] for it in result["items"] if it["uncertain"]] == heard
    _valid(result["text"])


def test_e_is_and_between_chords():
    """Fra gli accordi «e» e' la congiunzione, non un re."""
    assert interpret("la minore, fa, do e sol")["text"] == "Am F C G"
    assert interpret("A minor, F, C and G", "en")["text"] == "Am F C G"
    assert interpret("la mineur, fa, do et sol", "fr")["text"] == "Am F C G"
    assert interpret("la menor, fa, do y sol", "es")["text"] == "Am F C G"


def test_unknown_words_stay_flagged():
    result = interpret("do banana re")
    assert result["text"] == "c d" and result["unknown"] == ["banana"]
    unknown = [it for it in result["items"] if it["kind"] == "unknown"]
    assert unknown[0]["st"] == "" and unknown[0]["uncertain"]
    assert interpret("ottava sopra")["unknown"] == ["ottava sopra"]     # niente nota a cui darla


def test_modes():
    assert interpret("do re mi", mode="chords")["text"] == "C D E"
    assert interpret("la minore", mode="notes")["text"] == "Am"           # la qualita' fa sempre un accordo
    assert interpret("do fa sol")["mode"] == "notes"
    assert interpret("do fa sol sette")["mode"] == "chords"


def test_symbols_from_the_recognizer():
    assert interpret("Am F C G7", "en")["text"] == "Am F C G7"
    assert interpret("C/E F#m7", "en")["text"] == "C/E F#m7"
    assert interpret("sol7 do", "it")["text"] == "G7 C"


COMMANDS = [
    ("it", "cancella", "delete_last", None),
    ("it", "conferma", "confirm", None),
    ("it", "va bene", "confirm", None),
    ("it", "suona", "play", None),
    ("it", "suona tutto", "play_from_start", None),
    ("it", "inserisci nuova traccia flauto", "new_track", "flauto"),
    ("it", "aggiungi una traccia di flauto", "new_track", "di flauto"),
    ("it", "traccia nuova basso", "new_track", "basso"),
    ("it", "metti il tempo a novanta", "tempo", 90),
    ("it", "cancella l'ultima", "delete_last", None),
    ("en", "add a new track flute", "new_track", "flute"),
    ("en", "play", "play", None),
    ("fr", "ajoute une nouvelle piste flûte", "new_track", "flûte"),
    ("fr", "tempo à 90", "tempo", 90),
    ("es", "añade una nueva pista flauta", "new_track", "flauta"),
    ("es", "toca", "play", None),
    ("en", "confirm", "confirm", None),
    ("fr", "confirme", "confirm", None),
    ("es", "confirma", "confirm", None),
    ("it", "annulla", "undo", None),
    ("it", "suona la battuta", "play_bar", None),
    ("it", "suona da capo", "play_from_start", None),
    ("it", "suona dall'inizio", "play_from_start", None),
    ("it", "stop", "stop", None),
    ("it", "tempo novanta", "tempo", 90),
    ("it", "tempo centoventi", "tempo", 120),
    ("it", "tempo 72", "tempo", 72),
    ("it", "trasponi su di due", "transpose", 2),
    ("it", "trasponi giù di tre", "transpose", -3),
    ("it", "trasponi di meno uno", "transpose", -1),
    ("it", "vai alla battuta cinque", "goto_bar", 5),
    ("it", "nuova traccia pianoforte", "new_track", "pianoforte"),
    ("it", "fine dettatura", "end", None),
    ("it", "ripeti due volte", "repeat", 2),
    ("en", "delete", "delete_last", None),
    ("en", "undo", "undo", None),
    ("en", "play the bar", "play_bar", None),
    ("en", "play from the start", "play_from_start", None),
    ("en", "stop", "stop", None),
    ("en", "tempo ninety", "tempo", 90),
    ("en", "tempo one hundred twenty", "tempo", 120),
    ("en", "transpose up two", "transpose", 2),
    ("en", "transpose down by three semitones", "transpose", -3),
    ("en", "go to bar five", "goto_bar", 5),
    ("en", "new track piano", "new_track", "piano"),
    ("en", "end dictation", "end", None),
    ("en", "repeat twice", "repeat", 2),
    ("fr", "efface", "delete_last", None),
    ("fr", "annule", "undo", None),
    ("fr", "joue la mesure", "play_bar", None),
    ("fr", "joue depuis le début", "play_from_start", None),
    ("fr", "arrête", "stop", None),
    ("fr", "tempo quatre-vingt-dix", "tempo", 90),
    ("fr", "tempo soixante et onze", "tempo", 71),
    ("fr", "transpose de deux demi-tons vers le haut", "transpose", 2),
    ("fr", "transpose moins trois", "transpose", -3),
    ("fr", "va à la mesure cinq", "goto_bar", 5),
    ("fr", "nouvelle piste piano", "new_track", "piano"),
    ("fr", "fin de la dictée", "end", None),
    ("fr", "répète deux fois", "repeat", 2),
    ("es", "borra", "delete_last", None),
    ("es", "deshaz", "undo", None),
    ("es", "toca el compás", "play_bar", None),
    ("es", "toca desde el principio", "play_from_start", None),
    ("es", "para", "stop", None),
    ("es", "tempo noventa", "tempo", 90),
    ("es", "tempo ciento veinte", "tempo", 120),
    ("es", "transpón dos semitonos arriba", "transpose", 2),
    ("es", "transpón dos abajo", "transpose", -2),
    ("es", "ve al compás cinco", "goto_bar", 5),
    ("es", "nueva pista piano", "new_track", "piano"),
    ("es", "fin del dictado", "end", None),
    ("es", "repite dos veces", "repeat", 2),
]


@pytest.mark.parametrize("lang,phrase,command,value", COMMANDS)
def test_commands(lang, phrase, command, value):
    result = interpret(phrase, lang)
    assert result["commands"] == [{"command": command, "value": value}]
    assert result["text"] == "" and not result["unknown"]


def test_commands_and_music_in_one_phrase():
    result = interpret("tempo novanta, la minore, fa, do, sol, suona da capo")
    assert result["text"] == "Am F C G"
    assert [c["command"] for c in result["commands"]] == ["tempo", "play_from_start"]
    assert [it["kind"] for it in result["items"]] == ["command", "chord", "chord", "chord", "chord", "command"]


def test_items_keep_what_was_said():
    """Ogni pezzo porta le parole dette: l'app le legge al lettore di schermo
    («inserito: la minore, fa, do, sol»)."""
    items = interpret("la minore, fa, re semiminima puntata")["items"]
    assert [(it["said"], it["st"]) for it in items] == [("la minore", "Am"), ("fa", "F"),
                                                        ("re semiminima puntata", "D'4.")]


def test_unknown_language_falls_back_to_italian():
    assert interpret("do re mi", "de")["text"] == "c d e"
    assert interpret("do re mi", "it-IT")["lang"] == "it"
    assert interpret("C D E", "en-US")["text"] == "c d e"


def test_eight_chord_progression_and_two_bar_melody():
    """Il criterio di accettazione: un giro di 8 accordi e una melodia di 2
    battute su griglia fissa."""
    giro = interpret("do, la minore, re minore sette, sol sette, mi minore, la minore sette, re minore, sol sette")
    assert giro["text"] == "C Am Dm7 G7 Em Am7 Dm G7"
    melody = interpret("ottavi do re mi fa sol la si do battuta do si la sol fa mi re do battuta")
    assert melody["text"] == "8: c d e f g a b c | c b a g f e d c |"
    for text in (giro["text"], melody["text"]):
        _valid(text)


@pytest.mark.parametrize("lang", LANGUAGES)
def test_random_phrases_never_break(lang):
    """Frasi a caso con le parole del lessico (e qualche parola estranea):
    l'interprete non si ferma mai e il testo che produce si legge sempre."""
    import random
    from core import dictation
    words = [w for cat, entries in dictation._LEXICON[lang].items() if cat not in ("pattern",)
             for phrase in entries for w in phrase.split()]
    words += list(dictation._FIXES[lang]["note"]) + ["banana", "7", "2", "Am", "G7", "C/E", "Tema"]
    rng = random.Random(lang)
    for _ in range(400):
        phrase = " ".join(rng.choice(words) for _ in range(rng.randint(1, 9)))
        result = interpret(phrase, lang, patterns=["Tema"])
        if result["text"]:
            _valid(result["text"])


def test_words_split_by_the_offline_recognizer():
    """Il modello italiano di Vosk scrive staccate le parole con «semi» e
    «bis»: l'interprete le riunisce, e la grammatica le contiene."""
    from core.dictation import vocabulary
    assert interpret("re semi minima puntata, mi semi croma, fa semi breve, sol bis croma")["text"] == \
        "d'4. e'16 f'1 g'32"
    assert interpret("semi crome do re, si semi diminuito")["text"] == "16: C D Bm7b5"
    words = vocabulary("it", ["Tema"])
    assert {"semi", "minima", "bis", "croma", "tema", "do", "re", "diesis"} <= set(words)
    assert all(" " not in w and not w.isdigit() for w in words)



@pytest.mark.parametrize("lang", LANGUAGES)
def test_grammar_for_the_offline_recognizer(lang):
    """La grammatica di Vosk contiene ogni parola delle frasi della tabella
    e dei comandi (altrimenti il riconoscimento non potrebbe dirle), solo
    parole che l'interprete usa, qualche frase intera e [unk] in fondo."""
    import re
    from core.dictation import _INSTRUMENT_WORDS, grammar, vocabulary
    entries = grammar(lang, ["Tema"])
    assert entries[-1] == "[unk]" and len(entries) == len(set(entries))
    assert "semi minima puntata" in entries or lang != "it"
    words = {w for e in entries[:-1] for w in e.split()}
    assert words <= set(vocabulary(lang, ["Tema"])) | set(_INSTRUMENT_WORDS[lang])
    said = [p for lg, p, _e in TABLE + [(c[0], c[1], None) for c in COMMANDS] if lg == lang]
    for phrase in said:
        for word in re.split(r"[\s,'\-]+", phrase.lower()):
            if word and not word.isdigit() and not re.fullmatch(r"[a-g][#b]?\d*|[a-g]m\d*", word):
                assert word in words, (phrase, word)


def test_instruments_for_a_new_track():
    """«nuova traccia basso»: ogni strumento che il riconoscitore conosce ha
    il suo strumento di SoundText, che fa una traccia valida."""
    from core.dictation import _INSTRUMENT_WORDS, instrument_name
    from core.project_io import parse_project_text
    for lang, words in _INSTRUMENT_WORDS.items():
        for word in words:
            name = instrument_name(word, lang)
            assert name, (lang, word)
            project = parse_project_text(f"ST: 2.6\nTempo: 100 BPM\n\nTraccia X [{name}]:\n  4: c d e f\n", "x")
            assert project.tracks[0].instrument.resolved, (lang, word, name)
    assert instrument_name("pianoforte", "it") == instrument_name("piano", "it") == "Piano"
    assert instrument_name("basso", "it") == "Bass"
    assert instrument_name("batería", "es") == "Drums"
    assert instrument_name("la flûte", "fr") == "Flute"
    assert instrument_name("pippo", "it") is None
    assert instrument_name("", "en") is None


def test_asking_words_around_the_music_are_ignored():
    """«inserisci», «aggiungi», «scrivi», «per favore»: si puo' chiedere con
    parole proprie, senza che diventino note o parole non capite."""
    for lang, phrase, text in [
        ("it", "inserisci la minore fa do sol", "Am F C G"),
        ("it", "scrivi do re mi per favore", "c d e"),
        ("it", "aggiungi ottavi do re mi fa", "8: c d e f"),
        ("en", "insert A minor", "Am"),
        ("en", "write C D E please", "c d e"),
        ("fr", "ajoute la mineur", "Am"),
        ("es", "añade la menor por favor", "Am"),
    ]:
        r = interpret(phrase, lang)
        assert (r["text"], r["commands"], r["unknown"]) == (text, [], []), (lang, phrase, r)
