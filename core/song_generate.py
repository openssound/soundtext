"""
Generare parti di un brano dal testo ST, senza interfaccia: giro armonico, batteria, basso, accompagnamento e
melodia con i generatori di core.rhythm_generate (le stesse scelte delle finestre «Genera …»), e scrivere una
traccia nuova o un box nel testo. Lo usano il brano in 60 secondi (core.quicksong) e il motore di SoundText Mobile
(mobile/engine.py).
"""

import re
from typing import Optional

GENERATORS = ("progression", "drums", "bass", "comping")
DEFAULT_VARIABILITY = 0.35          # il cursore Variabilita' delle finestre: 35%


def _indent(text: str) -> str:
    return "\n".join("  " + line if line.strip() else "" for line in text.split("\n"))


def _format_beat(beat: float) -> str:
    """core.project_io._format_beat"""
    beat = round(float(beat), 6)
    return str(int(beat)) if beat == int(beat) else str(beat)


def _box_header(track: str, name: str, beat: float) -> str:
    return f'Box {track} "{name.replace(chr(34), chr(39)).strip()}" |{_format_beat(beat)}:'


def _bar_beats(project) -> float:
    from core.rhythm_generate import project_bar_beats
    return project_bar_beats(project)


def _variation(options: dict) -> dict:
    """Variabilita' (una sola, per ritmo, note e dinamica come con le quote
    al 100%) e seme; senza seme se ne sceglie uno, che si restituisce."""
    import random
    from core.rhythm_generate import Variability
    value = float(options.get("variability", DEFAULT_VARIABILITY))
    seed = options.get("seed")
    if seed is None:
        seed = random.randrange(2 ** 31)
    return {"variability": Variability(value, value, value), "seed": int(seed)}


def _chords_of(project, source: Optional[str], exclude: Optional[str]):
    """Gli accordi da seguire: quelli della traccia 'source', altrimenti
    della prima traccia di note che ne ha (diversa da quella di
    destinazione). (accordi, nome della traccia)."""
    from core.rhythm_generate import extract_chords_from_track
    from core.i18n import tr
    candidates = [t for t in project.tracks if not t.is_audio and t.name != exclude]
    if source:
        candidates = [t for t in candidates if t.name == source]
        if not candidates:
            raise ValueError(tr("La traccia '{name}' non c'è.", name=source))
    for track in candidates:
        chords = extract_chords_from_track(track.text, project.patterns, midi_dir=None)
        if chords:
            return chords, track
    if source:
        raise ValueError(
            tr("La traccia '{source_name}' non contiene accordi da seguire: servono accordi scritti come simbolo (es. Cmaj7) o blocchi [...] di almeno due note; note singole (melodie, arpeggi) non bastano.", source_name=source))
    raise ValueError(tr("Nel brano non c'è ancora una traccia con degli accordi da seguire."))


def _instrument(project, name: str):
    from core.instruments import get_instrument
    for track in project.tracks:
        if track.instrument_name == name and not track.is_audio:
            return track.instrument
    return get_instrument(name)


def _performed(text: str, instrument, options: dict, seed: int, project) -> str:
    """«Esecuzione dello strumento» (pennate, pedale, note fantasma)."""
    if not options.get("performance"):
        return text
    from core.performance_style import perform, style_for
    style = style_for(instrument)
    return perform(text, style, seed=seed, patterns=project.patterns) if style else text


def generate(text: str, kind: str, options: Optional[dict] = None) -> dict:
    """Il testo di una parte generata per il brano 'text': {text, seed}.

    kind: "progression" (giro armonico), "drums", "bass", "comping"
    (accompagnamento). options, tutte facoltative (i valori predefiniti
    delle finestre di SoundText):
    - comuni: seed, variability (0-1, 0.35), bars, intensity ("light",
      "normal", "full", "build"), track (la traccia di destinazione, che
      non fa da sorgente di accordi);
    - progression: key, style, chord_bars (0.5, 1, 2), ending;
    - drums: style, fill_every (4), phrase_fills (si'), ending (no), fill_last (no: fill sull'ultima battuta, la sezione cambia),
      crash_first (no: crash sul primo tempo),
      section_fills (si' se le altre tracce hanno dei box);
    - bass e comping: swing (50 dritto - 80: le crome in ritardo, come «swing=N»);
    - bass: source (traccia degli accordi), style, octave (2),
      variation_every (4), kick_track, performance, instrument ("Bass");
    - comping: source, style, instrument ("Piano"), octave, variation_every
      (4), voice_leading (si'), leave_space (si'), performance, symbols (no di
      partenza; si': gli accordi della progressione si scrivono come simbolo, «Am7», e il motore li suona col voicing dello strumento;
      "exact": solo i blocchi che un simbolo suona identici).
    ValueError con un messaggio leggibile se non si puo' generare."""
    from core.project_io import parse_project_text
    from core import rhythm_generate as rg
    options = dict(options or {})
    project = parse_project_text(text, "Brano")
    bar_beats = _bar_beats(project)
    variation = _variation(options)
    seed = variation["seed"]
    intensity = options.get("intensity", "normal")
    track_name = options.get("track")
    destination = project.find_track(track_name) if track_name else None
    start_beat = float(options.get("start_beat", rg.track_end_beat(project, destination)))

    if kind == "progression":
        key = options.get("key") or (project.key or "").strip() or "C"
        mode = rg.parse_key(key)[1]
        style = options.get("style") or next(n for n, spec in rg.PROGRESSION_STYLES.items() if spec["mode"] == mode)
        out = rg.generate_chord_progression(key, style, bars=int(options.get("bars", 0)),
                                            chord_bars=float(options.get("chord_bars", 1.0)), bar_beats=bar_beats,
                                            ending=bool(options.get("ending", False)),
                                            inversions=float(options.get("inversions", 0.0)), **variation)
    elif kind == "drums":
        styles = rg.drum_styles_for_meter(project.time_sig)
        style = options.get("style") or (styles[0] if styles else "rock")
        bars = int(options.get("bars", 8))
        sections = rg.section_end_bars(project, start_beat, 256, bar_beats, exclude_track_name=track_name)
        use_sections = options.get("section_fills", bool(sections))
        section_bars = rg.section_end_bars(project, start_beat, bars, bar_beats,
                                           exclude_track_name=track_name) if use_sections else []
        if options.get("fill_last"):
            section_bars = list(section_bars) + [bars - 1]         # la sezione finisce qui: fill sull'ultima battuta
        out = rg.generate_drum_pattern(style, bars=bars, fill_every=int(options.get("fill_every", 4)),
                                       intensity=intensity, phrase_fills=bool(options.get("phrase_fills", True)),
                                       ending=bool(options.get("ending", False)), kick_accents=None,
                                       section_fill_bars=section_bars,
                                       crash_first=bool(options.get("crash_first")), **variation)
    elif kind == "bass":
        chords, _source = _chords_of(project, options.get("source"), track_name)
        instrument = _instrument(project, options.get("instrument", "Bass"))
        kick = None
        if options.get("kick_track"):
            kick = rg.kick_beats_of_track(project, project.get_track(options["kick_track"]), start_beat) or None
        out = rg.generate_bass_from_chords(
            chords, options.get("style") or rg.BASS_STYLES[0], octave=int(options.get("octave", 2)),
            variation_every=int(options.get("variation_every", 4)),
            min_total_beats=int(options.get("bars", 4)) * bar_beats, bar_beats=bar_beats,
            intensity=intensity, kick_beats=kick, ending=bool(options.get("ending", False)), **variation)
        out = _performed(out, instrument, options, seed, project)
    elif kind == "comping":
        chords, _source = _chords_of(project, options.get("source"), track_name)
        instrument = _instrument(project, options.get("instrument", "Piano"))
        low, high = instrument.range_low, instrument.range_high
        if options.get("leave_space", True):
            low, high = rg.fit_register(low, high, True,
                                        rg.part_registers(project, exclude_track_name=track_name))
        out = rg.generate_melodic_line(
            chords, options.get("style") or rg.COMPING_STYLES[0],
            octave=int(options.get("octave", instrument.default_octave)),
            range_low=low, range_high=high, polyphonic=True,
            variation_every=int(options.get("variation_every", 4)),
            min_total_beats=int(options.get("bars", 4)) * bar_beats, bar_beats=bar_beats,
            intensity=intensity, voice_leading=bool(options.get("voice_leading", True)),
            key=None, meter=project.time_sig, repeats=(), **variation)
        out = _performed(out, instrument, options, seed, project)
        mode = options.get("symbols")
        if mode in (True, 1, "1", "si", "exact"):
            from core import chord_symbols as cs
            if mode != "exact":                                  # gli accordi della progressione come simboli («Am7»): il motore li voicizza
                out = cs.progression_symbols(out, rg._expand_chords_to_cover(chords, int(options.get("bars", 4)) * bar_beats))
            out = cs.chords_as_symbols(out, instrument)          # e gli altri blocchi, dove un simbolo suona le stesse note
    else:
        raise ValueError(f"generatore sconosciuto: {kind}")
    if kind in ("bass", "comping") and int(options.get("swing") or 50) > 50:
        out = rg.with_swing(out, options["swing"])
    return {"text": out, "seed": seed}


def _has_short_header(instrument: str) -> bool:
    """«Bass:» vale per gli strumenti del catalogo e, da st-language 2.12.2,
    per i nomi General MIDI scritti per intero («Flute:», «Violin:»); gli
    altri si scrivono «Traccia Nome [Strumento]:»."""
    from core.instruments import all_instruments
    from st_language.instruments import is_instrument_name
    return instrument in all_instruments() or is_instrument_name(instrument)


def add_track(text: str, instrument: str, body: str, name: Optional[str] = None, compact: bool = True) -> dict:
    """Il brano con una traccia nuova in fondo: {text, name, start}.

    Il nome e' quello dato o quello dello strumento, con un numero se c'e'
    gia' una traccia che si chiama cosi'. L'intestazione e' la forma breve
    «Bass:» quando il nome e' lo strumento, altrimenti
    «Traccia Nome [Strumento]:». Il resto del file non cambia.

    compact (default): il testo dei generatori si scrive diviso in battute, e le battute che si ripetono diventano pattern
    «Pattern %Nome:» messi subito prima della traccia (core.compact_text): il suono non cambia."""
    from core.project_io import parse_project_text
    taken, project = set(), None
    try:
        project = parse_project_text(text, "Brano")
        taken = {t.name for t in project.tracks}
    except Exception:
        project = None
    base = (name or instrument).strip()
    candidate, n = base, 2
    while candidate in taken:
        candidate, n = f"{base} {n}", n + 1
    if candidate == instrument and re.match(r"^[A-Za-z]\w*$", candidate) and _has_short_header(instrument):
        header = f"{candidate}:"
    else:
        header = f"Traccia {candidate} [{instrument}]:"
    blocks = ""
    if compact and project is not None:
        from core.compact_text import compact_for_project
        from core.rhythm_generate import split_swing
        word, plain = split_swing(body.strip())                  # lo swing in testa resta fuori dai pattern
        made = compact_for_project(project, plain, re.sub(r"\W", "", candidate))
        body = (word + " " if word else "") + made["text"]
        blocks = "".join(f"Pattern %{n}:\n  {b}\n\n" for n, b in made["patterns"].items())
    lines = "\n".join("  " + line if line.strip() else "" for line in body.strip().split("\n"))
    head = text.rstrip("\n")
    head_blocks = (head + "\n\n" if head else "") + blocks
    new = head_blocks + header + "\n" + lines + "\n"
    return {"text": new, "name": candidate, "start": len(head_blocks)}


# la nota piu' grave vera degli archi acuti (la libreria da' a tutta la famiglia degli archi l'estensione del violoncello)
REAL_LOW = {"Violin": 55, "Fiddle": 55, "Viola": 48}
MELODY_MIN_OCTAVE = 4      # la melodia parte almeno dall'ottava 4: chitarre e archi partivano dalla 3, sotto l'accompagnamento


def _quick_melody(project, source: str, instrument_name: str, style: str, key: str, bars: int, seed: int,
                  intensity: str, variation: dict, comfort_high: Optional[int] = None) -> str:
    """La melodia di un brano veloce; 'comfort_high' (facoltativo): la nota piu' alta dove lo strumento suona pieno (un fiato),
    un tetto sopra il registro scelto (non sposta la melodia, vedi generate_phrase_melody)."""
    from core import rhythm_generate as rg
    from core.instruments import get_instrument
    chords, _track = _chords_of(project, source, None)
    instrument = get_instrument(instrument_name)
    bar_beats = _bar_beats(project)
    return rg.generate_melodic_line(
        chords, style, octave=max(instrument.default_octave, MELODY_MIN_OCTAVE),
        range_low=max(instrument.range_low, REAL_LOW.get(instrument_name, 0)),
        range_high=instrument.range_high, polyphonic=False, variation_every=4, min_total_beats=bars * bar_beats,
        bar_beats=bar_beats, intensity=intensity, voice_leading=True, key=key, meter=project.time_sig, repeats=(),
        **({"comfort_high": comfort_high} if comfort_high else {}), **variation)
