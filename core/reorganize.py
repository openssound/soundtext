"""
Riorganizzazione della song attraverso l'uso (o meno) dei pattern:

- extract_patterns_for_project: individua blocchi di token ripetuti nelle
  tracce (anche non consecutivi) e li converte in pattern riutilizzabili
  (%Nome), compattando la notazione.
- expand_patterns_for_project: operazione inversa, sostituisce ogni
  riferimento (%pattern e &midi) con i token letterali corrispondenti,
  rendendo le tracce autosufficienti e rimuovendo i pattern ora inutilizzati.

Entrambe le funzioni accettano un progress_callback(fraction: float) opzionale
(fraction in [0.0, 1.0]) per alimentare una barra di progresso in GUI, e
l'estrazione ha un limite di tempo (timeout_seconds) e di ampiezza della
finestra di ricerca (max_window_cap) per garantire tempi di esecuzione
sempre limitati anche su tracce molto lunghe.
"""

import time
from typing import Dict, List, Optional, Tuple, Callable

from .arrangement import expand_pattern_refs_text
from .i18n import tr
from .notation import (tokenize, tokenize_spans, NotationError, Pattern, RE_ARP, RE_GRID, RE_KEY_MODE, RE_MIDI_REF, RE_PATTERN_REF,
                       RE_PITCH_MODE, RE_TRANSPOSE, RE_VELOCITY, _resolve_midi_ref, _state_effect, map_nested_tokens,
                       upgrade_pattern_state)
from st_language.transform import is_transform_reference, parse_reference
from .model import Project

# Le finestre di ricerca oltre questa lunghezza non vengono considerate: un
# pattern riutilizzabile ha senso come frase musicale breve (una o poche
# battute), non come blocco enorme; limitarle rende anche l'algoritmo molto
# piu' veloce (la complessita' per round e' O(n * max_window_cap^2) invece
# di O(n * (n/2)^2), indipendente dalla lunghezza della traccia).
DEFAULT_MAX_WINDOW_CAP = 24
DEFAULT_TIMEOUT_SECONDS = 8.0


def _next_pattern_name(existing_names, prefix: str = "Auto") -> str:
    i = 1
    while f"{prefix}{i}" in existing_names:
        i += 1
    return f"{prefix}{i}"


def _consolidate_consecutive_refs(tokens: List[str]) -> List[str]:
    """Trasforma '%Nome %Nome %Nome' in '3%Nome' (equivalente per i
    riferimenti a pattern, che ripetono semplicemente il contenuto)."""
    out = []
    i, n = 0, len(tokens)
    while i < n:
        tok = tokens[i]
        if tok.startswith("%"):
            count = 1
            while i + count < n and tokens[i + count] == tok:
                count += 1
            out.append(f"{count}{tok}" if count > 1 else tok)
            i += count
        else:
            out.append(tok)
            i += 1
    return out


def _is_pattern_ref(tok: str) -> bool:
    return tok.lstrip("0123456789").startswith("%")


def _is_state_command(tok: str) -> bool:
    """Vero per i comandi di stato (N: NT: N@ arp=), che non hanno un suono
    proprio: un pattern estratto non deve mai terminare con uno di questi
    'in sospeso' (rimarrebbe un cambio di griglia/velocity senza alcun
    evento sonoro associato all'interno del pattern stesso)."""
    return bool(RE_GRID.match(tok) or RE_VELOCITY.match(tok) or RE_ARP.match(tok))


def _is_pitch_state_command(tok: str) -> bool:
    """Vero per rel:/abs: e key=K: cambiano il modo di leggere le note che
    seguono. Un pattern parte sempre senza questo stato (in ottave assolute e
    senza tonalita'), quindi un blocco estratto da dopo un tale comando
    suonerebbe diverso."""
    return tok in ("rel:", "abs:") or tok.startswith("key=")


def _find_best_repeated_block(tokens: List[str], min_window: int, min_repeats: int,
                                max_window_cap: int, deadline: Optional[float]
                                ) -> Optional[Tuple[int, List[int]]]:
    """Cerca il blocco di token ripetuto (anche non consecutivo, non
    sovrapposto) che massimizza il risparmio in numero di token, limitando
    la finestra a max_window_cap ed interrompendosi comunque a 'deadline'
    (time.time() monotono) se la ricerca sta impiegando troppo tempo.
    Ritorna (lunghezza_blocco, posizioni_iniziali) oppure None.

    I blocchi candidati che contengono un riferimento a un altro pattern
    (%Nome) vengono scartati: un pattern estratto non deve mai contenere
    riferimenti ad altri pattern (nessun nesting).

    Se la traccia contiene rel:/abs:/key=, si considerano solo i blocchi che
    stanno interamente prima del primo di questi comandi: da li' in poi le
    note dipendono dallo stato e non possono essere spostate in un pattern."""
    n = len(tokens)
    if n < min_window * min_repeats:
        return None
    state_limit = next((i for i, t in enumerate(tokens) if _is_pitch_state_command(t)), n)

    best = None  # (risparmio, window, posizioni)
    max_window = min(n // min_repeats, max_window_cap)
    for window in range(max_window, min_window - 1, -1):
        if deadline is not None and time.time() > deadline:
            break
        seen: Dict[tuple, List[int]] = {}
        for start in range(0, n - window + 1):
            if start + window > state_limit:
                break  # il blocco tocca (o segue) un cambio di ottave/tonalita'
            block = tokens[start:start + window]
            if any(t.startswith("bar=") for t in block):
                continue  # un'ancora dice DOVE sta il testo: spostata in un pattern cambierebbe posto
            if any(t.startswith("transpose=") or t == "reset:" for t in block):
                continue  # trasposizione e reset: in un pattern valgono solo fino alla sua fine
            if any(_is_pattern_ref(t) for t in block):
                continue  # vietato: eviterebbe di poter nidificare pattern in pattern
            if _is_state_command(block[-1]):
                continue  # vietato: il pattern deve terminare con un evento sonoro (nota/accordo/pausa/percussione)
            key = tuple(block)
            seen.setdefault(key, []).append(start)
        for key, positions in seen.items():
            non_overlap = []
            last_end = -1
            for p in positions:
                if p >= last_end:
                    non_overlap.append(p)
                    last_end = p + window
            if len(non_overlap) >= min_repeats:
                savings = (window - 1) * len(non_overlap)
                if savings > 0 and (best is None or savings > best[0]):
                    best = (savings, window, non_overlap)
    if best is None:
        return None
    return best[1], best[2]


def extract_patterns_from_tokens(tokens: List[str], existing_pattern_names,
                                   min_window: int = 4, min_repeats: int = 2,
                                   max_extractions: int = 20, name_prefix: str = "Auto",
                                   max_window_cap: int = DEFAULT_MAX_WINDOW_CAP,
                                   timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
                                   progress_callback: Optional[Callable[[float], None]] = None
                                   ) -> Tuple[List[str], Dict[str, List[str]]]:
    """Individua blocchi di token ripetuti e li sostituisce con riferimenti
    %Nome, definendo i pattern corrispondenti. Non altera il significato
    musicale (i pattern sono una pura fattorizzazione della stessa sequenza).
    I pattern estratti non contengono mai riferimenti ad altri pattern (niente
    pattern nidificati). Il tempo di esecuzione e' sempre limitato: se
    timeout_seconds viene superato, la funzione si ferma e ritorna i pattern
    trovati fino a quel momento (mai un blocco indefinito).
    Ritorna (nuovi_token, {nome_pattern: [token...]})."""
    tokens = list(tokens)
    names = set(existing_pattern_names)
    new_patterns: Dict[str, List[str]] = {}
    deadline = (time.time() + timeout_seconds) if timeout_seconds else None

    # Pre-consolidamento: se lo stesso riferimento %Nome compare gia' ripetuto
    # consecutivamente (es. scritto per esteso invece di 'N%Nome'), unificarlo
    # subito evita di avvolgerlo inutilmente in un nuovo pattern "involucro".
    tokens = _consolidate_consecutive_refs(tokens)

    for i in range(max_extractions):
        if progress_callback:
            progress_callback(i / max_extractions)
        if deadline is not None and time.time() > deadline:
            break
        found = _find_best_repeated_block(tokens, min_window, min_repeats, max_window_cap, deadline)
        if not found:
            break
        window, positions = found
        block = tokens[positions[0]:positions[0] + window]
        name = _next_pattern_name(names, name_prefix)
        names.add(name)
        new_patterns[name] = block
        for p in reversed(positions):
            tokens[p:p + window] = [f"%{name}"]

    tokens = _consolidate_consecutive_refs(tokens)
    if progress_callback:
        progress_callback(1.0)
    return tokens, new_patterns


def extract_patterns_for_project(project: Project, min_window: int = 4,
                                   min_repeats: int = 2,
                                   max_window_cap: int = DEFAULT_MAX_WINDOW_CAP,
                                   timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
                                   progress_callback: Optional[Callable[[float], None]] = None
                                   ) -> Dict[str, Dict[str, List[str]]]:
    """Applica l'estrazione a ciascuna traccia del progetto, registrando i
    pattern trovati in project.patterns. Il prefisso dei nomi generati e' lo
    strumento della traccia (es. 'Guitar1', 'Guitar2', ...). progress_callback
    (se fornito) viene chiamato con una frazione 0.0-1.0 del lavoro totale
    (basata sul numero di tracce), utile per una barra di progresso in GUI.
    Ritorna un riepilogo {nome_traccia: {nome_pattern: [token...]}} dei
    pattern effettivamente creati (tracce senza ripetizioni utili non
    compaiono, anche se il testo puo' comunque essere stato leggermente
    compattato, es. consolidando riferimenti gia' ripetuti consecutivamente)."""
    summary = {}
    total = max(1, len(project.tracks))
    # Il timeout e' per-traccia: una song con molte tracce non deve sommare i
    # tempi limite fino a diventare comunque lenta nel complesso.
    per_track_timeout = timeout_seconds

    for idx, track in enumerate(project.tracks):
        def track_progress(frac, idx=idx):
            if progress_callback:
                progress_callback((idx + frac) / total)

        raw_tokens = tokenize(track.text)
        new_tokens, new_patterns = extract_patterns_from_tokens(
            raw_tokens, project.patterns.keys(), min_window=min_window, min_repeats=min_repeats,
            name_prefix=track.instrument_name, max_window_cap=max_window_cap,
            timeout_seconds=per_track_timeout, progress_callback=track_progress,
        )
        created = {name: Pattern(name=name, tokens=body_tokens) for name, body_tokens in new_patterns.items()}
        if created:
            project.patterns.update(created)
            summary[track.name] = new_patterns
        if new_tokens != raw_tokens:
            # quello che i pattern nuovi scrivono finisce con loro: se le note
            # dopo lo usavano si riscrive dopo il richiamo. Solo per i pattern
            # nuovi, gli altri richiami seguono gia' la regola.
            track.text = upgrade_pattern_state(" ".join(new_tokens), created)

    if progress_callback:
        progress_callback(1.0)
    return summary


def _has_reusable_ref(tok: str) -> bool:
    stripped = tok.lstrip("0123456789")
    return stripped.startswith("%") or stripped.startswith("&")


def _used_patterns(texts: List[str], patterns: Dict[str, Pattern]) -> Dict[str, Pattern]:
    """I pattern richiamati dai testi, anche da dentro altri pattern."""
    used: Dict[str, Pattern] = {}

    def visit(tokens: List[str]):
        for tok in tokens:
            map_nested_tokens(tok, note)

    def note(tok: str) -> str:
        name = None
        if is_transform_reference(tok):
            try:
                name = parse_reference(tok).pattern
            except NotationError:
                pass
        else:
            m = RE_PATTERN_REF.match(tok)
            name = m.group(2) if m else None
        if name in patterns and name not in used:
            used[name] = patterns[name]
            visit(patterns[name].tokens)
        return tok

    for text in texts:
        visit(tokenize(text))
    return used


def _nested_tokens(text_or_tokens) -> List[str]:
    """Tutti i token, anche quelli dentro gruppi N(...) e voci { ; }."""
    tokens = tokenize(text_or_tokens) if isinstance(text_or_tokens, str) else text_or_tokens
    found: List[str] = []

    def keep(tok: str) -> str:
        found.append(tok)
        return tok

    for tok in tokens:
        map_nested_tokens(tok, keep)
    return found


def expand_blockers(project: Project) -> List[str]:
    """Perche' i riferimenti di questo brano non si possono scrivere per
    esteso senza cambiare il suono, una frase per motivo ([] = si puo'). Il
    testo espanso non ha i confini di un pattern: quello che il pattern
    scrive resterebbe in vigore dopo di lui, e una funzione non ha testo in
    cui svolgersi. Serve una funzione di st-language che scriva il testo
    espanso rimettendo lo stato di prima."""
    texts = [track.text for track in project.tracks if not track.is_audio]
    used = _used_patterns(texts, project.patterns)
    reasons: List[str] = []
    tokens = [t for text in texts for t in _nested_tokens(text)]
    inner = [t for pattern in used.values() for t in _nested_tokens(pattern.tokens)]
    transforms = sorted({t for t in tokens + inner if is_transform_reference(t)})
    if transforms:
        reasons.append(tr("richiami con funzioni: {refs}", refs=", ".join(transforms[:5])))
    writers = sorted(name for name, pattern in used.items() if _state_effect(pattern.tokens, project.patterns)[1])
    if writers:
        reasons.append(tr("pattern che scrivono griglia, velocity, swing o arpeggio: {names}",
                          names=", ".join("%" + n for n in writers[:5])))
    modal = sorted(name for name, pattern in used.items()
                   if any(_changes_pitch_reading(t) for t in _nested_tokens(pattern.tokens)))
    if modal:
        reasons.append(tr("pattern che cambiano il modo di leggere le note: {names}",
                          names=", ".join("%" + n for n in modal[:5])))
    if used and any(_changes_pitch_reading(t) for t in tokens):
        reasons.append(tr("tracce con rel:, key= o transpose= insieme ai pattern"))
    midi = sorted({t for t in tokens + inner if (m := RE_MIDI_REF.match(t)) and m.group(3)})
    if midi:
        reasons.append(tr("riferimenti MIDI trasposti: {refs}", refs=", ".join(midi[:5])))
    return reasons


def _changes_pitch_reading(tok: str) -> bool:
    return bool(RE_PITCH_MODE.match(tok) or RE_KEY_MODE.match(tok) or RE_TRANSPOSE.match(tok))


def _expand_midi_refs(text: str, midi_dir: Optional[str]) -> str:
    """Il testo con i riferimenti &midi scritti per esteso."""
    def expand(tok: str) -> str:
        m = RE_MIDI_REF.match(tok)
        if not m:
            return tok
        return " ".join(_resolve_midi_ref(m.group(2), midi_dir, tok) * int(m.group(1) or 1))

    out, last = [], 0
    for tok, start, end in tokenize_spans(text):
        if "&" in tok:
            out += [text[last:start], map_nested_tokens(tok, expand)]
            last = end
    out.append(text[last:])
    return "".join(out)


def expand_patterns_for_project(project: Project, midi_dir: Optional[str] = None,
                                  progress_callback: Optional[Callable[[float], None]] = None
                                  ) -> Dict[str, Tuple[int, int]]:
    """Espande tutti i riferimenti %pattern e &midi di ogni traccia in token
    letterali, rendendo le tracce autosufficienti. Rimuove dal progetto i
    pattern (ormai inutilizzati). Ritorna {nome_traccia: (n_token_prima,
    n_token_dopo)} per le sole tracce effettivamente modificate. Il testo
    scritto nelle tracce e' testo vero: niente segni interni di expand_patterns.
    Solleva ValueError se il suono cambierebbe (vedi expand_blockers)."""
    reasons = expand_blockers(project)
    if reasons:
        raise ValueError("; ".join(reasons))
    summary = {}
    total = max(1, len(project.tracks))
    for idx, track in enumerate(project.tracks):
        if progress_callback:
            progress_callback(idx / total)
        instr = track.instrument
        raw_tokens = tokenize(track.text)
        if not any(_has_reusable_ref(t) for t in _nested_tokens(raw_tokens)):
            continue
        text = expand_pattern_refs_text(track.text, project.patterns, instr.default_octave)
        text = _expand_midi_refs(text, midi_dir)
        summary[track.name] = (len(raw_tokens), len(tokenize(text)))
        track.text = text

    if summary:
        project.patterns.clear()
    if progress_callback:
        progress_callback(1.0)
    return summary
