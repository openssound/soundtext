"""
La miniatura delle note di un box, per la vista Struttura brano
(gui.arrangement_view.BoxItem): da testo del box le note da disegnare come
trattini, ciascuna con inizio e durata in beat dall'inizio del box e una
"corsia" verticale (l'altezza MIDI per melodie e accordi, una riga per
suono per la batteria).

Il calcolo passa dal parser della notazione, quindi si tiene in una cache
legata a testo, strumento, pattern, metrica e posizione del box: ridisegnare
la vista (scorrere, selezionare, zoomare) non rianalizza niente.
"""

from collections import OrderedDict
from dataclasses import dataclass
from typing import List, Optional, Tuple

_CACHE_MAX = 4096
_cache: "OrderedDict[tuple, Optional[ClipPreview]]" = OrderedDict()


@dataclass(frozen=True)
class ClipPreview:
    notes: Tuple[Tuple[float, float, int], ...]   # (inizio, durata, corsia)
    low: int                                      # corsia piu' bassa e piu' alta
    high: int
    percussion: bool                              # corsie = suoni di batteria, non altezze


def patterns_key(patterns) -> tuple:
    """Una chiave che cambia quando cambia un pattern (i box li usano con %Nome)."""
    return tuple(sorted((name, tuple(p.tokens)) for name, p in (patterns or {}).items()))


def clip_preview(text: str, instrument, patterns, meter=None, origin_beat: float = 0.0,
                 patterns_sig: Optional[tuple] = None, meter_key=None) -> Optional[ClipPreview]:
    """La miniatura del testo di un box suonato da 'instrument'; None se il
    testo non ha note (o non si legge: la vista disegna solo il box).
    meter_key: cio' che definisce la metrica (metrica, cambi, levare): il
    Meter non ha uno stato confrontabile, e senza chiave la cache vale
    solo per lo stesso oggetto."""
    key = (text, instrument.name, instrument.default_octave, instrument.is_percussion,
           patterns_sig if patterns_sig is not None else patterns_key(patterns),
           meter_key if meter_key is not None else id(meter), round(origin_beat, 6))
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]
    try:
        preview = _compute(text, instrument, patterns, meter, origin_beat)
    except Exception:            # testo con errori: la vista Testo li segnala, qui niente miniatura
        preview = None
    _cache[key] = preview
    if len(_cache) > _CACHE_MAX:
        _cache.popitem(last=False)
    return preview


def _compute(text, instrument, patterns, meter, origin_beat) -> Optional[ClipPreview]:
    from st_language.chords import parse_chord_symbol, pitch_to_midi, voice_chord
    from .notation import parse_track_text
    events = parse_track_text(text, patterns or {}, default_octave=instrument.default_octave,
                              meter=meter, origin_beat=origin_beat)
    octave = instrument.default_octave
    drums: List[str] = []                         # i suoni di batteria, nell'ordine in cui compaiono
    hits: List[Tuple[float, float, int]] = []     # colpi di batteria: corsia = indice in drums
    pitched: List[Tuple[float, float, int]] = []  # note e accordi: corsia = altezza MIDI

    def add(item, start, duration):
        kind = item.get("kind")
        if kind == "note" and item.get("letter"):
            pitched.append((start, duration, pitch_to_midi(item["letter"], item.get("octave") or octave)))
        elif kind == "chord" and item.get("symbol"):
            try:
                voiced = voice_chord(parse_chord_symbol(item["symbol"]), item.get("octave") or octave, instrument)
            except Exception:
                voiced = []
            pitched.extend((start, duration, p) for p in voiced)
        elif kind == "percussion" and item.get("name"):
            if item["name"] not in drums:
                drums.append(item["name"])
            hits.append((start, duration, drums.index(item["name"])))

    for event in events:
        if event.duration <= 0 or event.kind in ("rest", "sustain", "tempo_marker"):
            continue
        start = event.start          # gia' dall'inizio del box: origin_beat serve solo alle ancore bar=N
        if event.kind == "block":
            for item in event.items or []:
                add(item, start, event.duration)
        elif event.kind == "slide":
            add({"kind": "note", "letter": event.letter, "octave": event.octave}, start, event.duration)
        else:
            add({"kind": event.kind, "letter": event.letter, "octave": event.octave,
                 "symbol": event.symbol, "name": event.name}, start, event.duration)
    # una traccia di batteria mostra i colpi; le altre le altezze (se un
    # testo mescola i due, le corsie non sarebbero confrontabili)
    use_hits = bool(hits) and (instrument.is_percussion or not pitched)
    notes = hits if use_hits else pitched
    if not notes:
        return None
    lanes = [lane for _s, _d, lane in notes]
    return ClipPreview(tuple(notes), min(lanes), max(lanes), use_hits)
