"""
Riconoscimento automatico della tonalita' di un progetto dall'analisi delle
note effettivamente scritte nelle tracce (batteria esclusa: non ha altezza),
con l'algoritmo di Krumhansl-Schmuckler: un istogramma delle 12 classi di
altezza (pesato per durata) viene confrontato, per correlazione, con i 24
"profili tonali" empirici di Krumhansl & Kessler (uno per ciascuna possibile
tonica maggiore/minore) - si sceglie la tonalita' il cui profilo correla
meglio con quanto effettivamente scritto. Usato dalla voce di menu
**Progetto -> Analizza tonalita'...** (gui.main_window_project).

Solo un'euristica statistica (nessuna vera "comprensione" armonica): puo'
sbagliare su brani brevi, molto cromatici, o che modulano - come qualunque
altra implementazione dello stesso algoritmo classico, e' pensata come punto
di partenza/suggerimento, non come verdetto infallibile.
"""

from typing import Dict, List, Optional, Tuple

from .chords import note_name_to_pc, parse_chord_symbol, pc_to_letter
from .model import Pattern, Project
from .notation import parse_track_text

# Profili tonali di Krumhansl & Kessler (1982): peso "atteso" di ciascun
# grado della scala (indice 0 = tonica, in semitoni sopra) nella musica
# tonale occidentale, ricavato empiricamente da esperimenti di percezione.
# Sono i pesi canonici usati dall'algoritmo di Krumhansl-Schmuckler.
MAJOR_PROFILE = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
MINOR_PROFILE = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]


def _pitch_classes_for_note_like(kind: str, letter: Optional[str] = None,
                                  symbol: Optional[str] = None) -> List[int]:
    """Classi di altezza (0-11) di un singolo evento/sotto-evento intonato
    (nota, slide o accordo); [] per tutto cio' che non ha altezza (pause,
    percussioni, sustain, marcatori di tempo). Per gli accordi si usano le
    classi di altezza astratte del simbolo (fondamentale + intervalli):
    non serve il voicing concreto (dipendente da strumento/registro) per
    stimare la tonalita'."""
    if kind in ("note", "slide"):
        return [note_name_to_pc(letter)]
    if kind == "chord":
        try:
            chord = parse_chord_symbol(symbol)
        except ValueError:
            return []
        return [(chord.root_pc + iv) % 12 for iv in chord.intervals]
    return []


def _event_pitch_classes(ev) -> List[int]:
    if ev.kind == "block":
        pcs = []
        for item in ev.items or []:
            pcs.extend(_pitch_classes_for_note_like(item.get("kind"), item.get("letter"), item.get("symbol")))
        return pcs
    return _pitch_classes_for_note_like(ev.kind, ev.letter, ev.symbol)


def build_pitch_class_histogram(project: Project, midi_dir: Optional[str] = None) -> List[float]:
    """Istogramma delle 12 classi di altezza (indice 0 = Do, 1 = Do#, ...),
    pesato per la durata (in beat) delle note effettivamente scritte in
    tutte le tracce NON percussive del progetto. Include gli accordi (ogni
    nota dell'accordo pesata per l'intera durata dell'evento) e i
    sotto-eventi intonati dei blocchi [...]; ignora pause, sustain,
    marcatori di tempo e le tracce/eventi percussivi."""
    histogram = [0.0] * 12
    for track in project.tracks:
        if track.instrument.is_percussion:
            continue
        for ev in track.parsed_events(project.patterns, midi_dir=midi_dir, meter=project.meter()):
            for pc in _event_pitch_classes(ev):
                histogram[pc] += ev.duration
    return histogram


def _correlation(a: List[float], b: List[float]) -> float:
    """Coefficiente di correlazione di Pearson tra due sequenze della stessa
    lunghezza. Ritorna 0.0 (invece di sollevare ZeroDivisionError) se una
    delle due ha varianza nulla (es. istogramma piatto/vuoto)."""
    n = len(a)
    mean_a = sum(a) / n
    mean_b = sum(b) / n
    num = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n))
    den_a = sum((a[i] - mean_a) ** 2 for i in range(n))
    den_b = sum((b[i] - mean_b) ** 2 for i in range(n))
    if den_a == 0 or den_b == 0:
        return 0.0
    return num / (den_a * den_b) ** 0.5


def detect_key(project: Project, midi_dir: Optional[str] = None) -> Optional[str]:
    """Stima la tonalita' del progetto con l'algoritmo di
    Krumhansl-Schmuckler (vedi modulo), nel formato di Project.key (es.
    'C', 'Am', 'F#' - vedi core.chords.parse_key_signature). Ritorna None
    se non ci sono abbastanza note intonate da analizzare (progetto vuoto,
    con sole tracce percussive, o con solo pause/sustain)."""
    best = _best_key(build_pitch_class_histogram(project, midi_dir=midi_dir))
    if best is None:
        return None
    return _key_name(*best)


def detect_key_of_text(text: str, patterns: Dict[str, Pattern], default_octave: int = 4,
                       midi_dir: Optional[str] = None) -> Optional[str]:
    """Come detect_key, ma per il testo di un solo box/traccia (es. il box
    dopo cui accodare un nuovo giro armonico). Un giro di soli accordi e'
    ambiguo (Am F C G: Do maggiore o La minore? Cm Bb Ab Bb: il Si bemolle
    dura il doppio del Do minore), e il solo istogramma lo distingue male:
    al punteggio di Krumhansl-Schmuckler si sommano gli indizi degli accordi
    (vedi tonic_bonus)."""
    events = parse_track_text(text, patterns, default_octave=default_octave, midi_dir=midi_dir)
    histogram = [0.0] * 12
    chords = []   # (fondamentale, minore?, durata, terza maggiore?, settima minore?)
    for ev in events:
        for pc in _event_pitch_classes(ev):
            histogram[pc] += ev.duration
        if ev.kind == "chord":
            try:
                chord = parse_chord_symbol(ev.symbol)
            except ValueError:
                continue
            chords.append((chord.root_pc, 3 in chord.intervals and 4 not in chord.intervals, ev.duration,
                           4 in chord.intervals, 10 in chord.intervals))
    if sum(histogram) <= 0:
        return None

    total = sum(c[2] for c in chords)

    def tonic_bonus(key) -> float:
        """Quanto il box indica key come tonalita' attraverso i suoi accordi
        (0 senza accordi): primo accordo sulla tonica (i giri partono quasi
        sempre da li'), durata sulla tonica, cadenza V -> I (dominante con
        terza maggiore o sus, o il suo sostituto di tritono bII7, seguita
        dalla tonica: l'indizio dei giri II-V-I, che non partono dalla
        tonica; conta per intero se chiude il box, a meta' se la tonica
        apre o chiude il box)."""
        if not chords or total <= 0:
            return 0.0
        bonus = FIRST_CHORD_WEIGHT if chords[0][:2] == key else 0.0
        dominant = (key[0] + 7) % 12
        tritone_sub = (key[0] + 1) % 12   # bII7 -> I: il sostituto di tritono della dominante

        def cadence(a, b) -> bool:
            # dominante: terza maggiore, o settima minore senza terza minore (G7sus4)
            dominant_like = (a[3] or a[4]) and not a[1]
            return b[:2] == key and dominant_like and (a[0] == dominant or (a[0] == tritone_sub and a[3] and a[4]))

        pairs = list(zip(chords, chords[1:]))
        if pairs and cadence(*pairs[-1]):
            bonus += CADENCE_WEIGHT          # la cadenza che chiude il box
        elif key in (chords[0][:2], chords[-1][:2]) and any(cadence(a, b) for a, b in pairs):
            # a meta' giro conta meno, e solo se la tonica apre o chiude il
            # box: altrimenti e' una dominante secondaria (E7 -> Am in Do)
            bonus += CADENCE_WEIGHT / 2
        return bonus + TONIC_CHORD_WEIGHT * sum(c[2] for c in chords if c[:2] == key) / total

    scores = {key: score + tonic_bonus(key) for key, score in _key_scores(histogram).items()}
    return _key_name(*max(scores, key=scores.get))


def _key_name(tonic_pc: int, minor: bool) -> str:
    return pc_to_letter(tonic_pc).upper() + ("m" if minor else "")


# Pesi, rispetto alla correlazione di Krumhansl-Schmuckler (fra -1 e 1),
# degli indizi dati dagli accordi in detect_key_of_text: primo accordo sulla
# tonica, quota della durata sull'accordo di tonica, cadenza V -> I. Tarati
# perche' ogni giro di core.rhythm_generate.PROGRESSION_STYLES, in ogni
# tonalita', venga riconosciuto (vedi tests/test_key_detect.py).
FIRST_CHORD_WEIGHT = 0.5
TONIC_CHORD_WEIGHT = 0.3
CADENCE_WEIGHT = 0.5


def _key_scores(histogram: List[float]) -> Dict[Tuple[int, bool], float]:
    """Correlazione di Krumhansl-Schmuckler per ciascuna delle 24 tonalita'
    (tonica 0-11, minore?)."""
    scores = {}
    for root_pc in range(12):
        # profilo atteso, riallineato dai gradi di scala (relativi alla
        # tonica) alle classi di altezza assolute per l'ipotesi "tonica = root_pc"
        scores[(root_pc, False)] = _correlation(histogram, [MAJOR_PROFILE[(pc - root_pc) % 12] for pc in range(12)])
        scores[(root_pc, True)] = _correlation(histogram, [MINOR_PROFILE[(pc - root_pc) % 12] for pc in range(12)])
    return scores


def _best_key(histogram: List[float]) -> Optional[Tuple[int, bool]]:
    """(tonica 0-11, minore?) che meglio correla con l'istogramma, secondo
    Krumhansl-Schmuckler; None se l'istogramma e' vuoto."""
    if sum(histogram) <= 0:
        return None

    scores = _key_scores(histogram)
    return max(scores, key=scores.get)
