"""
Mappa tastiera fisica -> nota/accordo/percussione per il dialogo "Suona con
la tastiera" (gui.keyboard_play_dialog): tre righe della tastiera italiana,
di 12 tasti ciascuna, ciascuna un'ottava sopra la precedente, percorse
cromaticamente a partire da C (do, do#, re, re#, mi, fa, fa#, sol, sol#, la,
la#, si). L'ottava della riga numerica e' scelta dall'utente nel dialogo
(vedi build_note_key_map); le altre due righe sono sempre un'ottava e due
ottave sopra quella.

Le costanti Qt::Key usate qui sono quelle "logiche" (legate al carattere che
il tasto produce nel layout di sistema attivo, non alla posizione fisica):
su una tastiera impostata su Italiano producono esattamente la disposizione
descritta sopra; con un layout diverso i tasti restano funzionanti ma la
disposizione fisica risultante puo' non corrispondere piu' 1:1 alle
etichette (numeri/lettere) qui sotto.
"""

from PySide6.QtCore import Qt
from core.i18n import tr

# Ordine cromatico dei 12 semitoni all'interno di ogni riga, a partire da C
# (vedi core.chords.note_name_to_pc per la conversione in classe di altezza).
CHROMATIC_FROM_C = ["c", "c#", "d", "d#", "e", "f", "f#", "g", "g#", "a", "a#", "b"]

# Le tre righe della tastiera fisica italiana (12 tasti ciascuna) -> scarto in
# ottave rispetto alla riga numerica (0 = la riga stessa, 1 = un'ottava sopra, ecc.).
NOTE_ROW_KEYS = [
    ([Qt.Key_1, Qt.Key_2, Qt.Key_3, Qt.Key_4, Qt.Key_5, Qt.Key_6, Qt.Key_7, Qt.Key_8, Qt.Key_9, Qt.Key_0,
      Qt.Key_Apostrophe, Qt.Key_Igrave], 0),
    ([Qt.Key_Q, Qt.Key_W, Qt.Key_E, Qt.Key_R, Qt.Key_T, Qt.Key_Y, Qt.Key_U, Qt.Key_I, Qt.Key_O, Qt.Key_P,
      Qt.Key_Egrave, Qt.Key_Plus], 1),
    ([Qt.Key_A, Qt.Key_S, Qt.Key_D, Qt.Key_F, Qt.Key_G, Qt.Key_H, Qt.Key_J, Qt.Key_K, Qt.Key_L,
      Qt.Key_Ograve, Qt.Key_Agrave, Qt.Key_Ugrave], 2),
]

# L'ultimo tasto della riga ASDF ('ù' su layout italiano) e' l'unico non
# coperto da gui.keyboard_scancodes (posizione fisica ambigua sui layout ISO
# europei, vedi quel modulo): come ripiego, Invio (sia quello principale sia
# quello del tastierino numerico) suona sempre la stessa nota di quel tasto,
# su qualunque layout - Invio non e' un tasto-carattere, quindi la sua
# posizione fisica e' gia' di per se' indipendente dal layout, esattamente
# come i tasti esecutivi (Ctrl/Alt/Maiusc/Tab/Bloc Maiusc/Spazio).
UGRAVE_ALIAS_KEYS = (Qt.Key_Return, Qt.Key_Enter)


def _alias_ugrave(note_key_map: dict) -> dict:
    target = note_key_map.get(Qt.Key_Ugrave)
    if target is not None:
        for alias_key in UGRAVE_ALIAS_KEYS:
            note_key_map[alias_key] = target
    return note_key_map


def build_note_key_map(base_octave: int):
    """tasto -> (lettera nota, ottava) per una data ottava di partenza (quella
    della riga numerica; le righe Q e A sono rispettivamente base_octave+1 e
    base_octave+2)."""
    note_key_map = {}
    for keys, octave_offset in NOTE_ROW_KEYS:
        for idx, key in enumerate(keys):
            note_key_map[key] = (CHROMATIC_FROM_C[idx], base_octave + octave_offset)
    return _alias_ugrave(note_key_map)


def build_scale_key_map(base_octave: int, key: str, scale_type: str = "diatonica"):
    """Come build_note_key_map, ma percorrendo solo le note della scala
    scelta (vedi core.chords.scale_pitch_classes: 'diatonica' 7 note,
    'pentatonica' 5 note, 'blues' 6 note) della tonalita' data invece che
    tutte e 12 cromaticamente: i 12 tasti di ogni riga coprono cosi' 12/N
    ottave invece di una sola (N = note della scala), avanzando per gradi
    (grado 1..N nell'ottava di base, poi si continua nella successiva), cosi'
    ogni tasto suona sempre una nota 'in tonalita'' invece che lasciare
    all'orecchio il compito di evitare le note estranee - piu' corta e' la
    scala, piu' ottave si riescono a coprire con gli stessi 12 tasti per riga
    (es. pentatonica: 12/5 = 2.4 ottave per riga, contro le 12/7 della
    diatonica).

    Solleva ValueError se 'key' o 'scale_type' non sono validi (vedi
    core.chords.scale_pitch_classes)."""
    from core.chords import scale_pitch_classes, pc_to_letter
    pcs = scale_pitch_classes(key, scale_type)  # N classi di altezza, in ordine crescente di grado dalla tonica
    note_key_map = {}
    for keys, octave_offset in NOTE_ROW_KEYS:
        for idx, k in enumerate(keys):
            extra_octave, degree = divmod(idx, len(pcs))
            note_key_map[k] = (pc_to_letter(pcs[degree]), base_octave + octave_offset + extra_octave)
    return _alias_ugrave(note_key_map)


def build_janko_key_map(base_octave: int):
    """Layout isomorfo ispirato alla tastiera Jankó: due 'righe logiche' a
    toni interi (0,2,4,6,8,10 semitoni dalla tonica su una riga, 1,3,5,7,9,11
    sull'altra, un semitono sopra), cosi' un dato intervallo o accordo ha
    sempre la STESSA forma fisica ovunque sulla tastiera, indipendentemente
    dalla tonalita' o dalla posizione di partenza — a differenza delle righe
    cromatiche di build_note_key_map, dove la stessa forma "si sposta"
    cambiando ottava riga per riga.

    Le tre righe fisiche si alternano per parita' (riga numerica e riga ASDF
    = riga logica pari, riga QWERTY = riga logica dispari, intercalata tra
    le due): esattamente come sulla tastiera Jankó reale, dove le righe pari
    si ripetono identiche per raggiungere lo stesso accordo con la mano in
    due posizioni diverse invece di offrire nuova estensione. Copre quindi 2
    ottave cromatiche piene (24 semitoni) — non le 3 di build_note_key_map —
    con la riga numerica e la riga ASDF che suonano esattamente le stesse 12
    note: e' il prezzo dell'isomorfismo, non un difetto."""
    from core.chords import midi_note, midi_to_pitch
    base_midi = midi_note(0, base_octave)  # tonica di riferimento (Do dell'ottava scelta)
    note_key_map = {}
    for row_idx, (keys, _unused_octave_offset) in enumerate(NOTE_ROW_KEYS):
        parity = row_idx % 2
        for col, k in enumerate(keys):
            note_key_map[k] = midi_to_pitch(base_midi + 2 * col + parity)
    return _alias_ugrave(note_key_map)


# Le tre righe fisiche (36 tasti in tutto, vedi NOTE_ROW_KEYS) appiattite in
# un'unica lista, nell'ordine di core.instruments.PERCUSSION_MAP (usata al
# posto di build_note_key_map quando lo strumento della traccia e' percussivo:
# le percussioni non hanno ottava, quindi qui non conta lo scarto d'ottava per
# riga). Riga numerica (1-9 poi 0 ' ì), poi riga Q, poi riga A, solo se
# PERCUSSION_MAP ne ha abbastanza da riempirle.
PERCUSSION_KEYS = [key for keys, _octave_offset in NOTE_ROW_KEYS for key in keys]


# Fila inferiore (Z...//) -> qualita' dell'accordo: tenuta premuta insieme
# al tasto-nota (una qualsiasi delle righe di build_note_key_map/
# build_scale_key_map/build_janko_key_map) fa suonare l'accordo corrispondente
# invece della nota singola. Ogni voce e' (etichetta, intervalli in semitoni
# dalla fondamentale) - stesso formato di core.chords.CHORD_QUALITIES, qui
# pero' elencati direttamente: alcune di queste non hanno un corrispettivo
# 1:1 nel dizionario globale (es. il Power Chord qui include il raddoppio
# d'ottava esplicito [0, 7, 12], mentre la qualita' '5' generica in
# CHORD_QUALITIES e' solo [0, 7]).
QUALITY_ROW_KEYS = {
    Qt.Key_Z: ("Maggiore", [0, 4, 7]),
    Qt.Key_X: ("Minore", [0, 3, 7]),
    Qt.Key_C: (tr("7ª Dominante"), [0, 4, 7, 10]),
    Qt.Key_V: (tr("Minore 7"), [0, 3, 7, 10]),
    Qt.Key_B: (tr("Maggiore 7"), [0, 4, 7, 11]),
    Qt.Key_N: (tr("Sospeso (sus4)"), [0, 5, 7]),
    Qt.Key_M: (tr("Aggiunta 9ª (add9)"), [0, 4, 7, 14]),
    Qt.Key_Comma: (tr("Diminuito 7"), [0, 3, 6, 9]),
    Qt.Key_Period: (tr("Power Chord"), [0, 7, 12]),
}
# '/' e' un caso a parte (raddoppia la fondamentale un'ottava sotto, non e'
# una vera qualita' d'accordo dipendente da core.chords.voice_chord): gestito
# direttamente in gui.keyboard_play_dialog.
BASS_DOUBLE_KEY = Qt.Key_Slash

# Tasti esecutivi (mano sinistra). NOTA: Qt non distingue in modo portabile
# il tasto Ctrl/Alt/Maiusc sinistro da quello destro tramite Qt::Key (la
# stessa costante arriva da entrambi i lati): questi rispondono quindi a
# Ctrl/Alt/Maiusc in generale, anche se il layout descritto prevede quello
# sinistro per ergonomia (mano sinistra sui tasti-qualita' e su questi).
SUSTAIN_KEY = Qt.Key_CapsLock      # tenuto premuto: sustain (pedale hold)
STRUM_KEY = Qt.Key_Alt              # tenuto premuto: strumming (note dell'accordo in rapida sequenza)
BEND_KEY = Qt.Key_Shift             # tenuto premuto: bending (nota/accordo alzati di BEND_SEMITONES)
INVERSION_KEY = Qt.Key_Control      # tenuto premuto: 1a inversione (fondamentale un'ottava sopra)
VELOCITY_TOGGLE_KEY = Qt.Key_Tab    # commuta (non tenuto premuto): Piano/Forte
ARPEGGIATOR_KEY = Qt.Key_Space      # tenuto premuto: arpeggio continuo a tempo
VELOCITY_LOW = 60    # "Piano"
VELOCITY_HIGH = 110  # "Forte" (stato di partenza)
