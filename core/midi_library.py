"""
Libreria MIDI riutilizzabile (cartella midi/, anche con sottocartelle):
indice dei file, risoluzione dei riferimenti &Nome / &Sottocartella/Nome
usati nelle tracce (vedi core.notation.expand_patterns) e loro conversione
in token, con cache.
"""

import os
from collections import defaultdict
from typing import Dict, List, Optional

from .version import get_app_root, pick_writable_dir, USER_DATA_ROOT


# Cartella di libreria MIDI: <radice_app>/midi  (analoga a examples/ per i pattern)
DEFAULT_MIDI_DIR = os.path.join(get_app_root(), "midi")

USER_MIDI_DIR = os.path.join(USER_DATA_ROOT, "midi")

def ensure_midi_dir(midi_dir: Optional[str] = None) -> str:
    """Cartella della libreria MIDI: quella richiesta, o midi/ accanto
    all'app, o USER_MIDI_DIR se quest'ultima non e' scrivibile (AppImage:
    altrimenti importare/rinominare/eliminare nella libreria fallirebbe)."""
    if midi_dir:
        os.makedirs(midi_dir, exist_ok=True)
        return midi_dir
    return pick_writable_dir(DEFAULT_MIDI_DIR, USER_MIDI_DIR)

class AmbiguousMidiRefError(Exception):
    """Sollevato quando &"Nome" corrisponde a piu' file in sottocartelle diverse."""
    def __init__(self, name, candidates):
        self.name = name
        self.candidates = candidates
        super().__init__(
            f"'{name}' e' ambiguo: trovato in {', '.join(candidates)}. "
            f"Specifica la sottocartella, es. &\"{candidates[0]}\""
        )

def _walk_midi_files(base_dir: str):
    """Genera (percorso_relativo_senza_estensione_con_/, percorso_assoluto)
    per ogni file .mid/.midi sotto base_dir, comprese le sottocartelle."""
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if f.lower().endswith((".mid", ".midi")):
                abspath = os.path.join(root, f)
                rel = os.path.relpath(abspath, base_dir)
                rel_noext = os.path.splitext(rel)[0].replace(os.sep, "/")
                yield rel_noext, abspath

def build_midi_index(midi_dir: Optional[str] = None):
    """Ritorna (index, paths):
      - index: {nome_file_senza_estensione: [percorsi_relativi, ...]}  (per la ricerca ricorsiva per nome)
      - paths: {percorso_relativo: percorso_assoluto}                  (per i riferimenti qualificati Sub/Nome)
    """
    base = ensure_midi_dir(midi_dir)
    index: Dict[str, List[str]] = defaultdict(list)
    paths: Dict[str, str] = {}
    for rel, abspath in _walk_midi_files(base):
        paths[rel] = abspath
        basename = rel.split("/")[-1]
        index[basename].append(rel)
    return index, paths

def resolve_midi_ref(name_path: str, midi_dir: Optional[str] = None) -> str:
    """Risolve un riferimento &Nome o &Sottocartella/Nome nel percorso assoluto
    del file .mid corrispondente. Se 'Nome' non contiene '/', la ricerca e'
    ricorsiva su tutte le sottocartelle della libreria; se il nome compare in
    piu' sottocartelle diverse solleva AmbiguousMidiRefError."""
    index, paths = build_midi_index(midi_dir)

    if "/" in name_path:
        if name_path in paths:
            return paths[name_path]
        raise FileNotFoundError(name_path)

    matches = index.get(name_path, [])
    if len(matches) == 1:
        return paths[matches[0]]
    if len(matches) == 0:
        raise FileNotFoundError(name_path)
    raise AmbiguousMidiRefError(name_path, sorted(matches))

def list_midi_library(midi_dir: Optional[str] = None) -> List[str]:
    """Ritorna i percorsi relativi (senza estensione, con '/' per le
    sottocartelle) di tutti i file .mid disponibili nella libreria,
    es. ['Guitar/Intro', 'Blues/shuffle', 'bass_line']."""
    _, paths = build_midi_index(midi_dir)
    return sorted(paths.keys())

_midi_ref_cache: Dict[str, List[str]] = {}

def get_midi_ref_tokens(name_path: str, midi_dir: Optional[str] = None) -> List[str]:
    """Usata da notation.expand_patterns per risolvere un riferimento &Nome
    (ricerca ricorsiva) o &Sottocartella/Nome (percorso qualificato): ritorna
    i token del canale primario del file MIDI corrispondente.
    Puo' sollevare FileNotFoundError o AmbiguousMidiRefError."""
    from .midi_convert import analyze_midi, pick_primary_channel  # import locale: evita il ciclo
    from .midi_to_tokens import channel_to_tokens

    cache_key = (midi_dir or DEFAULT_MIDI_DIR, name_path)
    if cache_key in _midi_ref_cache:
        return _midi_ref_cache[cache_key]
    path = resolve_midi_ref(name_path, midi_dir)  # puo' sollevare le eccezioni sopra
    _, tpb, channels = analyze_midi(path)
    primary = pick_primary_channel(channels)
    tokens = channel_to_tokens(primary, tpb) if primary else []
    _midi_ref_cache[cache_key] = tokens
    return tokens

def clear_midi_ref_cache():
    _midi_ref_cache.clear()

def render_tokens_to_midi(tokens_text: str, instrument_name: str, tempo_bpm: int, path: str):
    """Rigenera un file MIDI a partire da testo di notazione (usato dalla
    libreria MIDI per 'salvare' le modifiche fatte in stile-pattern)."""
    from .model import Project
    from .midi_export import export_project_to_midi

    project = Project(name="preview", tempo_bpm=tempo_bpm)
    project.add_track("Preview", instrument_name, tokens_text)
    export_project_to_midi(project, path, only_audible=False)
    clear_midi_ref_cache()
