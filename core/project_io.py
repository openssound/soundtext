"""
Serializzazione/deserializzazione del progetto nel formato testuale
descritto nella sezione 7 delle specifiche (Tempo, Metrica, blocchi
Pattern %Nome:, blocchi <Strumento> <indice>:), esteso con:
- blocchi Strumento Nome: per incorporare nel file la definizione degli
  eventuali strumenti personalizzati usati dal progetto (caricamento
  automatico);
- blocchi Mixer Nome: per persistere volume/pan/mute/solo e invio a
  riverbero/chorus di ogni traccia (altrimenti andrebbero persi ad ogni
  salvataggio/ricaricamento).

Questo e' anche il formato di salvataggio nativo (estensione .st, letta
tramite ST-Syntax — la grammatica del SoundText Language):
resta leggibile e modificabile a mano, coerentemente con la filosofia
"notazione testuale" del prodotto.
"""

import re
import os
from typing import Optional, List

from .model import Project, Clip, AudioClip, AUDIO_INSTRUMENT_NAME, Effect
from .arrangement import flatten_clips_to_text
from .notation import upgrade_midi_refs
from .effects import DEFAULT_REVERB_ROOM, EFFECT_KINDS, REVERB_ROOMS, choice_key, clamp_params
from .instruments import (
    list_instrument_names, get_instrument, is_custom_instrument,
    ensure_instrument_available, resolve_instrument_type, InstrumentProfile,
)
from .version import get_app_root, pick_writable_dir, USER_DATA_ROOT
from st_language.stfile import (  # noqa: F401  (formato dei file .st, vedi st_language/stfile.py)
    RE_TEMPO, RE_METRICA, RE_MASTER, RE_KEY, RE_AMBIENTE, RE_TEMPO_LIST_HDR,
    RE_METRICA_LIST_HDR, RE_BAR_VALUE, RE_PATTERN_HDR, RE_INSTRUMENT_HDR, RE_MIXER_HDR,
    RE_EFFECTS_HDR, RE_MASTER_CHAIN_HDR, RE_EFFECT_ITEM, RE_SYNTH_HDR, RE_BOX_HDR, RE_AUDIO_HDR,
    RE_AUDIO_FILE, RE_AUDIO_TRIM, RE_AUDIO_GAIN, RE_AUDIO_INPUT, RE_AUDIO_CHANNELS,
    RE_TRACK_HDR, RE_TRACK_HDR_EXPLICIT, RE_KV_EQUALS, RE_KV_COLON, short_track_header,
    _TRACK_HDR_PATTERNS, VOLUME_MAX, _parse_bar_value_list, _si, _parse_kv_body,
    _convert_pan_to_0_127, _pan_0_127_to_normalized, _convert_volume, _parse_instrument_body,
    _parse_mixer_body, _notation_body_lines, _extract_named_blocks, _extract_box_blocks,
    RE_ST_VERSION, RE_PICKUP, LANGUAGE_VERSION, parse_pickup, format_pickup, instrument_blocks,
    RE_KEY_LIST_HDR, RE_TITLE, RE_COMPOSER, RE_LYRICIST, parse_key_list,
)


# Cartella predefinita per il salvataggio dei progetti (analoga a midi/ per la libreria)
DEFAULT_SONGS_DIR = os.path.join(get_app_root(), "songs")
# Cartella predefinita in cui l'utente tiene i propri file SoundFont (.sf2):
# punto di partenza dei dialoghi "Scegli SoundFont" (Playback e Gestione
# strumenti), cosi' da non dover navigare da zero ogni volta.
DEFAULT_SOUNDFONTS_DIR = os.path.join(get_app_root(), "soundfonts")


# Dove salvare i progetti/SoundFont quando la cartella accanto all'app non e'
# scrivibile (AppImage, installazione di sistema): vedi pick_writable_dir.
USER_SONGS_DIR = os.path.join(USER_DATA_ROOT, "songs")
USER_SOUNDFONTS_DIR = os.path.join(USER_DATA_ROOT, "soundfonts")


def ensure_songs_dir() -> str:
    return pick_writable_dir(DEFAULT_SONGS_DIR, USER_SONGS_DIR)


def ensure_soundfonts_dir() -> str:
    return pick_writable_dir(DEFAULT_SOUNDFONTS_DIR, USER_SOUNDFONTS_DIR)


# compute_bar_beat_offsets: nella libreria (vedi st_language.timing), riesportata.
from st_language.timing import compute_bar_beat_offsets  # noqa: E402,F401


def _instrument_body_text(instr: InstrumentProfile) -> str:
    return (
        f"program={instr.gm_program} percussione={'si' if instr.is_percussion else 'no'} "
        f"ottava={instr.default_octave} range={instr.range_low}-{instr.range_high} "
        f"poly={'si' if instr.polyphonic else 'no'} voicing={instr.voicing_style}"
        + (f" trasposizione={instr.transposition}" if getattr(instr, "transposition", 0) else "")
    )


def _name_matches_instrument_convention(track_name: str, instrument_name: str) -> bool:
    """Vero se il nome della traccia segue la convenzione '<Strumento>' o
    '<Strumento> <indice>' (es. 'Guitar', 'Guitar 1'), che consente di
    dedurre lo strumento dalla sola intestazione, come nel formato originale."""
    if track_name == instrument_name:
        matches = True
    else:
        matches = re.fullmatch(re.escape(instrument_name) + r" \d+", track_name) is not None
    # ...e solo se l'intestazione corta si rilegge come la stessa traccia
    header = short_track_header(f"{track_name}:", {instrument_name})
    return matches and header is not None and \
        (f"{header[0]} {header[1]}".strip() if header[1] else header[0]) == track_name


def _format_beat(beat: float) -> str:
    return str(int(beat)) if beat == int(beat) else str(beat)


def _parse_effects_body(body: str, base_dir: Optional[str] = None) -> List[Effect]:
    """Catena di effetti di un blocco 'Effetti Nome:'. Tipi sconosciuti
    (file di una versione piu' recente) si saltano; i parametri si
    riportano nei limiti."""
    effects = []
    for kind, rest in RE_EFFECT_ITEM.findall(body):
        kind = kind.lower()
        if kind not in EFFECT_KINDS:
            continue
        params, preset, ir, nam = {}, "", "", ""
        plugin, plugin_params, plugin_state = _parse_plugin_items(rest)
        for key, value in re.findall(r'([\w.]+)=("[^"]*"|[^\s]+)', rest):
            if key in ("ref", "stato") or key.startswith("p."):
                continue
            if key == "preset":
                preset = value.strip('"')
            elif key in ("ir", "nam"):
                # file IR della cassa o profilo NAM: relativo alla cartella del
                # .st, come le clip audio
                path = value.strip('"').replace("/", os.sep)
                if base_dir and path and not os.path.isabs(path):
                    path = os.path.normpath(os.path.join(base_dir, path))
                if key == "ir":
                    ir = path
                else:
                    nam = path
            else:
                params[key] = value if re.fullmatch(r"[A-Za-z_][\w/]*", value) else value.replace(",", ".")
        enabled = re.search(r"(^|\s)(spento|off)(\s|$)", rest) is None
        effects.append(Effect(kind=kind, params=clamp_params(kind, params), enabled=enabled, preset=preset,
                              ir=ir, nam=nam, plugin=plugin, plugin_params=plugin_params,
                              plugin_state=plugin_state))
    return effects


def _parse_plugin_items(text: str):
    """(ref, parametri, stato) di un plugin da 'ref="..." p.chiave=valore
    stato="..."' (effetto "plugin" o blocco "Plugin Nome:")."""
    ref, params, state = "", {}, ""
    for key, value in re.findall(r'([\w.]+)=("[^"]*"|[^\s]+)', text):
        value = value.strip('"')
        if key == "ref":
            ref = value
        elif key == "stato":
            state = value
        elif key.startswith("p.") and len(key) > 2:
            try:
                params[key[2:]] = float(value.replace(",", "."))
            except ValueError:
                pass
    return ref, params, state


def _plugin_items(ref: str, params: dict, state: str) -> List[str]:
    items = [f'ref="{ref}"']
    items += [f"p.{key}={float(value):g}" for key, value in params.items()]
    if state:
        items.append(f'stato="{state}"')
    return items


def _relative_path(path: str, base_dir: Optional[str]) -> str:
    if base_dir:
        try:
            path = os.path.relpath(os.path.abspath(path), os.path.abspath(base_dir))
        except ValueError:   # Windows: dischi diversi, resta assoluto
            pass
    return path.replace(os.sep, "/")


def _effects_body_lines(effects: List[Effect], base_dir: Optional[str] = None) -> List[str]:
    lines = []
    for effect in effects:
        params = clamp_params(effect.kind, effect.params)
        kinds = {param.key: param for param in EFFECT_KINDS[effect.kind]["params"]}
        # Il delay libero (in ms) non scrive la suddivisione: i progetti di
        # prima del delay a tempo restano identici.
        items = [f"{key}={choice_key(kinds[key], value)}" if kinds[key].choices else f"{key}={value:g}"
                 for key, value in params.items()
                 if not (key == "suddivisione" and value == kinds[key].default)]
        if effect.preset:
            items.append(f'preset="{effect.preset}"')
        if effect.nam:
            items.append(f'nam="{_relative_path(effect.nam, base_dir)}"')
        if effect.ir:
            items.append(f'ir="{_relative_path(effect.ir, base_dir)}"')
        if effect.kind == "plugin" and effect.plugin:
            items += _plugin_items(effect.plugin, effect.plugin_params, effect.plugin_state)
        if not effect.enabled:
            items.append("spento")
        lines.append(f"  {effect.kind}: " + " ".join(items))
    return lines


def register_embedded_instruments(text: str) -> List[str]:
    """Registra automaticamente (se non gia' disponibili) gli strumenti
    personalizzati definiti nel testo del progetto. Ritorna i nomi
    effettivamente registrati ora (per un eventuale messaggio all'utente)."""
    return _prepare_embedded_instruments(text)


def _prepare_embedded_instruments(text: str) -> List[str]:
    newly_registered = []
    for name, body in instrument_blocks(text.splitlines()):
        if ensure_instrument_available(_parse_instrument_body(name, body)):
            newly_registered.append(name)
    return newly_registered


def _parse_audio_clip_body(name: str, start_beat: float, body: str,
                           base_dir: Optional[str]) -> Optional[AudioClip]:
    m = RE_AUDIO_FILE.search(body)
    if not m or not m.group(1).strip():
        return None
    path = m.group(1).strip().replace("/", os.sep)
    if base_dir and not os.path.isabs(path):
        path = os.path.normpath(os.path.join(base_dir, path))
    clip = AudioClip(name=name, file=path, start_beat=start_beat)
    t = RE_AUDIO_TRIM.search(body)
    if t:
        clip.trim_start, clip.trim_end = float(t.group(1)), float(t.group(2))
    g = RE_AUDIO_GAIN.search(body)
    if g:
        clip.gain_db = float(g.group(1))
    return clip


def _audio_clip_body_text(clip: AudioClip, base_dir: Optional[str]) -> str:
    path = clip.file
    if base_dir:
        try:
            path = os.path.relpath(os.path.abspath(path), os.path.abspath(base_dir))
        except ValueError:   # Windows: dischi diversi, resta assoluto
            pass
    parts = [f'file="{path.replace(os.sep, "/")}"']
    if clip.trim_start or clip.trim_end:
        parts.append(f"trim={round(clip.trim_start, 4):g},{round(clip.trim_end, 4):g}")
    if clip.gain_db:
        parts.append(f"gain={round(clip.gain_db, 2):g}")
    return " ".join(parts)


def parse_project_text(text: str, project_name: str = "Progetto", base_dir: Optional[str] = None) -> Project:
    """base_dir e' la cartella del file .st: i percorsi (relativi) dei file
    delle clip audio vengono risolti rispetto a essa."""
    # Passo 1: registra automaticamente gli strumenti personalizzati incorporati
    # nel file (cosi' che siano gia' disponibili quando si incontrano le tracce
    # che li usano, indipendentemente dall'ordine dei blocchi).
    _prepare_embedded_instruments(text)

    # Passo 2: raccoglie i blocchi 'Mixer <TrackName>:' (volume/pan/mute/solo
    # per traccia).
    track_mixer_overrides = {
        name: _parse_mixer_body(body)
        for name, body in _extract_named_blocks(text.splitlines(), RE_MIXER_HDR)
    }
    track_effects = {
        name: _parse_effects_body(body, base_dir)
        for name, body in _extract_named_blocks(text.splitlines(), RE_EFFECTS_HDR)
    }

    track_synths = {
        name: _parse_plugin_items(body)
        for name, body in _extract_named_blocks(text.splitlines(), RE_SYNTH_HDR)
    }

    master_chain = [effect for _name, body in _extract_named_blocks(text.splitlines(), RE_MASTER_CHAIN_HDR)
                    for effect in _parse_effects_body(body, base_dir)]

    project = Project(name=project_name)
    project.master_effects = master_chain
    # Gli strumenti definiti nel file valgono per le tracce di questo brano,
    # anche se in locale c'e' gia' uno strumento con lo stesso nome definito
    # diversamente (per esempio da un altro brano aperto prima).
    project.instruments = {
        name: _parse_instrument_body(name, body)
        for name, body in instrument_blocks(text.splitlines())
    }
    lines = text.splitlines()

    mode = None            # None | "pattern" | "instrument" | "mixer" | "track"
    current_name = None
    current_instrument = None
    buffer = []

    def flush():
        nonlocal mode, current_name, current_instrument, buffer
        # Le righe del testo di una traccia restano righe: un commento '//'
        # arriva fino a fine riga, unite con uno spazio si mangerebbe il resto.
        body = ("\n" if mode in ("track", "pattern") else " ").join(buffer).strip()
        if mode in ("track", "pattern"):
            body = upgrade_midi_refs(body)      # &Nome delle versioni prima della 2.6
        if mode == "pattern" and current_name:
            project.add_pattern(current_name, body)
        elif mode == "track" and current_name:
            if current_instrument == AUDIO_INSTRUMENT_NAME:
                track = project.add_audio_track(current_name)
                m_in, m_ch = RE_AUDIO_INPUT.search(body), RE_AUDIO_CHANNELS.search(body)
                track.input_profile = m_in.group(1) if m_in else ""
                track.input_channels = m_ch.group(1) if m_ch else ""
            else:
                track = project.add_track(current_name, current_instrument, body)
            if current_name in track_mixer_overrides:
                overrides = track_mixer_overrides[current_name]
                if "volume" in overrides:
                    track.volume = overrides["volume"]
                if "pan" in overrides:
                    track.pan = overrides["pan"]
                if "mute" in overrides:
                    track.mute = overrides["mute"]
                if "solo" in overrides:
                    track.solo = overrides["solo"]
                if "reverb" in overrides:
                    track.reverb = overrides["reverb"]
                if "chorus" in overrides:
                    track.chorus = overrides["chorus"]
            if current_name in track_effects:
                track.effects = track_effects[current_name]
            if current_name in track_synths and track_synths[current_name][0]:
                track.synth, track.synth_params, track.synth_state = track_synths[current_name]
        # mode == "instrument"/"mixer": nessuna azione qui, gia' applicati sopra
        mode, current_name, current_instrument, buffer = None, None, None, []

    for raw_line in lines:
        line = raw_line.strip()

        if line == "":
            if mode:
                flush()
            continue

        m = RE_ST_VERSION.match(line)
        if m:
            if mode:
                flush()
            project.st_version = (int(m.group(1)), int(m.group(2)))
            continue

        m = RE_PICKUP.match(line)
        if m:
            if mode:
                flush()
            project.pickup = parse_pickup(m.group(1))
            continue

        m = RE_TEMPO_LIST_HDR.match(line)
        if m:
            if mode:
                flush()
            project.tempo_changes = _parse_bar_value_list(m.group(1), is_metrica=False)
            bar1 = next((v for b, v in project.tempo_changes if b == 1), None)
            project.tempo_bpm = bar1 if bar1 is not None else project.tempo_changes[0][1]
            continue

        m = RE_TEMPO.match(line)
        if m:
            if mode:
                flush()
            project.tempo_bpm = int(m.group(1))
            continue

        m = RE_METRICA_LIST_HDR.match(line)
        if m:
            if mode:
                flush()
            project.metrica_changes = _parse_bar_value_list(m.group(1), is_metrica=True)
            bar1 = next((v for b, v in project.metrica_changes if b == 1), None)
            project.time_sig = bar1 if bar1 is not None else project.metrica_changes[0][1]
            continue

        m = RE_METRICA.match(line)
        if m:
            if mode:
                flush()
            project.time_sig = m.group(1)
            continue

        m = RE_MASTER.match(line)
        if m:
            if mode:
                flush()
            project.master_volume = _convert_volume(m.group(1))
            continue

        m = RE_KEY_LIST_HDR.match(line)
        if m:
            if mode:
                flush()
            project.key_changes = parse_key_list(m.group(1))
            first = next((k for b, k in project.key_changes if b == 1), None)
            project.key = first if first is not None else project.key_changes[0][1]
            continue

        m = RE_KEY.match(line)
        if m:
            if mode:
                flush()
            project.key = m.group(1).strip()
            continue

        found = None
        for rx, attr in ((RE_TITLE, "title"), (RE_COMPOSER, "composer"), (RE_LYRICIST, "lyricist")):
            m = rx.match(line)
            if m:
                found = (attr, m.group(1).strip())
                break
        if found:
            if mode:
                flush()
            setattr(project, *found)
            continue

        m = RE_AMBIENTE.match(line)
        if m:
            if mode:
                flush()
            room = m.group(1).lower()
            project.reverb_room = room if room in REVERB_ROOMS else DEFAULT_REVERB_ROOM
            continue

        m = RE_PATTERN_HDR.match(line)
        if m:
            if mode:
                flush()
            mode, current_name = "pattern", m.group(1)
            continue

        m = RE_INSTRUMENT_HDR.match(line)
        if m:
            if mode:
                flush()
            mode, current_name = "instrument", m.group(1)
            continue

        m = RE_MIXER_HDR.match(line)
        if m:
            if mode:
                flush()
            mode, current_name = "mixer", m.group(1)
            continue

        m = RE_EFFECTS_HDR.match(line) or RE_MASTER_CHAIN_HDR.match(line) or RE_SYNTH_HDR.match(line)
        if m:
            if mode:
                flush()
            mode, current_name = "effects", m.group(1)   # gia' letto nella pre-scansione
            continue

        m = RE_BOX_HDR.match(line)
        if m:
            if mode:
                flush()
            # Il contenuto e' gia' raccolto da _extract_box_blocks: qui basta
            # saltare il blocco senza farlo confluire nel body della traccia
            # o del pattern precedente.
            mode, current_name = "box", None
            continue

        m = RE_AUDIO_HDR.match(line)
        if m:
            if mode:
                flush()
            # Come per i Box: il contenuto e' raccolto a parte (vedi Passo 3).
            mode, current_name = "box", None
            continue

        m = RE_TRACK_HDR_EXPLICIT.match(line)
        if m:
            instr_name = m.group(2)
            if instr_name != AUDIO_INSTRUMENT_NAME and instr_name not in list_instrument_names():
                profile = resolve_instrument_type(instr_name, instr_name)
                ensure_instrument_available(profile)
            if mode:
                flush()
            current_name = m.group(1).strip()
            current_instrument = instr_name
            mode = "track"
            continue

        header = short_track_header(line, list_instrument_names())
        if header:
            if mode:
                flush()
            instr, idx = header
            current_name = f"{instr} {idx}".strip() if idx else instr
            current_instrument = instr
            mode = "track"
            continue

        # riga di corpo (token della traccia/pattern corrente, o parametri strumento/mixer)
        if mode:
            buffer.append(line)
        # righe non riconosciute al di fuori di un blocco vengono ignorate
        # (commenti liberi / righe descrittive del documento)

    if mode:
        flush()

    # Passo 3: assegna alle rispettive tracce i box della vista Struttura
    # brano (pre-scansionati sopra, indipendenti dall'ordine nel file) e
    # ricalcola il testo derivato di ogni traccia che ne ha (vedi
    # core.arrangement.flatten_clips_to_text - nessun'altra parte della
    # pipeline va toccata, legge semplicemente Track.text come sempre).
    for track_name, box_name, start_beat, body in _extract_box_blocks(lines):
        try:
            track = project.get_track(track_name)
        except KeyError:
            continue
        if not track.is_audio:
            track.clips.append(Clip(name=box_name, text=upgrade_midi_refs(body), start_beat=start_beat))
    for track_name, clip_name, start_beat, body in _extract_box_blocks(lines, RE_AUDIO_HDR):
        try:
            track = project.get_track(track_name)
        except KeyError:
            continue
        clip = _parse_audio_clip_body(clip_name, start_beat, body, base_dir)
        if track.is_audio and clip is not None:
            track.audio_clips.append(clip)
    for t in project.tracks:
        if t.clips:
            t.text = flatten_clips_to_text(t.clips, project.patterns, t.instrument.default_octave,
                                           meter=project.meter())

    return project


def project_to_text(project: Project, base_dir: Optional[str] = None) -> str:
    """base_dir e' la cartella in cui verra' salvato il file: i percorsi
    dei file delle clip audio vi vengono scritti relativi (vedi
    core.audio_tracks)."""
    if project.tempo_changes:
        tempo_line = "Tempo: " + ", ".join(f"{b}: {v}" for b, v in project.tempo_changes)
    else:
        tempo_line = f"Tempo: {project.tempo_bpm} BPM"
    if project.metrica_changes:
        metrica_line = "Metrica: " + ", ".join(f"{b}: {v}" for b, v in project.metrica_changes)
    else:
        metrica_line = f"Metrica: {project.time_sig}"
    # la versione del linguaggio in cima (i lettori piu' vecchi la ignorano)
    lines = ["ST: %d.%d" % LANGUAGE_VERSION]
    for label, value in (("Titolo", project.title), ("Autore", project.composer), ("Parole", project.lyricist)):
        if value:
            lines.append(f"{label}: {value}")
    lines += [tempo_line, metrica_line]
    if project.pickup:
        lines.append(f"Levare: {format_pickup(project.pickup)}")
    if project.master_volume != 100:
        lines.append(f"Master: {project.master_volume}")
    if project.key_changes:
        # la tonalita' della battuta 1 e' quella del campo Tonalita' (project.key)
        changes = [(b, project.key if b == 1 and project.key else k) for b, k in project.key_changes]
        lines.append("Tonalita: " + ", ".join(f"{b}: {k}" for b, k in changes))
    elif project.key:
        lines.append(f"Tonalita: {project.key}")
    if project.reverb_room != DEFAULT_REVERB_ROOM:
        lines.append(f"Ambiente: {project.reverb_room}")
    lines.append("")

    # Strumenti personalizzati usati dal progetto: vengono incorporati nel file
    # cosi' che aprendolo altrove (o dopo aver ripulito la configurazione
    # locale) vengano registrati automaticamente invece di far perdere le tracce.
    # Prima quelli definiti nel brano stesso (Project.instruments), poi i
    # personalizzati locali usati dalle tracce e non ancora definiti.
    seen = dict(project.instruments)
    for t in project.tracks:
        if not t.is_audio and is_custom_instrument(t.instrument_name) and t.instrument_name not in seen:
            seen[t.instrument_name] = t.instrument
    for name, instr in seen.items():
        lines.append(f"Strumento {name}:")
        lines.append("  " + _instrument_body_text(instr))
        lines.append("")

    # Le tracce (nome, strumento e, se non hanno box, il testo) subito dopo
    # gli strumenti personalizzati: chi apre il file le vede in cima, e
    # l'intestazione corta "Lead8basslead:" trova gia' definito lo strumento
    # che nomina. La lettura non dipende dalla posizione dei blocchi.
    for t in project.tracks:
        if t.is_audio:
            # Sempre in forma esplicita: "Audio:" da solo non e' un'intestazione
            # di traccia valida (Audio non e' fra gli strumenti).
            lines.append(f"Traccia {t.name} [{AUDIO_INSTRUMENT_NAME}]:")
            settings = []
            if t.input_profile:
                settings.append(f"ingresso={t.input_profile}")
            if t.input_channels:
                settings.append(f"canali={t.input_channels}")
            if settings:
                lines.append("  " + " ".join(settings))
            lines.append("")
            continue
        if _name_matches_instrument_convention(t.name, t.instrument_name):
            lines.append(f"{t.name}:")
        else:
            lines.append(f"Traccia {t.name} [{t.instrument_name}]:")
        # Con dei box il testo della traccia si ricostruisce da quelli alla
        # lettura (sezione 12.4 della specifica): riscriverlo raddoppierebbe
        # il file. Resta l'intestazione, che dice nome e strumento.
        if not t.clips:
            lines.extend(_notation_body_lines(t.text))
        lines.append("")

    for name, pat in project.patterns.items():
        lines.append(f"Pattern %{name}:")
        lines.append("  " + " ".join(pat.tokens))
        lines.append("")

    # Mixer non-default per traccia: persiste volume/pan/mute/solo (altrimenti
    # andrebbero perduti ad ogni salvataggio/ricaricamento). Le tracce con
    # impostazioni tutte di default non generano alcun blocco, per non
    # appesantire inutilmente i file piu' semplici.
    for t in project.tracks:
        if t.volume != 100 or t.pan != 64 or t.mute or t.solo or t.reverb or t.chorus:
            lines.append(f"Mixer {t.name}:")
            sends = (f" riverbero: {t.reverb}" if t.reverb else "") + (f" chorus: {t.chorus}" if t.chorus else "")
            lines.append(
                f"  volume: {t.volume} pan: {_pan_0_127_to_normalized(t.pan)} "
                f"mute: {'si' if t.mute else 'no'} solo: {'si' if t.solo else 'no'}{sends}"
            )
            lines.append("")

    # Catene di effetti (solo le tracce che ne hanno) e del master.
    for t in project.tracks:
        if t.effects:
            lines.append(f"Effetti {t.name}:")
            lines.extend(_effects_body_lines(t.effects, base_dir))
            lines.append("")
    for t in project.tracks:
        if t.synth and not t.is_audio:
            lines.append(f"Plugin {t.name}:")
            lines.append("  " + " ".join(_plugin_items(t.synth, t.synth_params, t.synth_state)))
            lines.append("")
    if project.master_effects:
        lines.append("Catena master:")
        lines.extend(_effects_body_lines(project.master_effects, base_dir))
        lines.append("")

    # Box della vista Struttura brano: solo per le tracce che li usano, cosi'
    # i progetti senza arrangiamento a box non generano alcun blocco.
    for t in project.tracks:
        for clip in sorted(t.clips, key=lambda c: c.start_beat):
            box_name = clip.name.replace('"', "'")
            lines.append(f'Box {t.name} "{box_name}" |{_format_beat(clip.start_beat)}:')
            lines.extend(_notation_body_lines(clip.text))
            lines.append("")

    for t in project.tracks:
        for clip in sorted(t.audio_clips, key=lambda c: c.start_beat):
            clip_name = clip.name.replace('"', "'")
            lines.append(f'Audio {t.name} "{clip_name}" |{_format_beat(clip.start_beat)}:')
            lines.append("  " + _audio_clip_body_text(clip, base_dir))
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def load_project_file(path: str) -> Project:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    name = os.path.splitext(os.path.basename(path))[0]
    return parse_project_text(text, project_name=name, base_dir=os.path.dirname(os.path.abspath(path)))


def save_project_file(project: Project, path: str):
    """Salva il progetto in path. Prima porta nella cartella audio del
    progetto ('<Nome>_audio/' accanto al file) i file delle clip audio che
    stanno ancora altrove (progetto mai salvato, 'Salva con nome'): vedi
    core.audio_tracks.consolidate_project_audio."""
    if any(t.audio_clips for t in project.tracks):
        from .audio_tracks import consolidate_project_audio
        consolidate_project_audio(project, path)
    text = project_to_text(project, base_dir=os.path.dirname(os.path.abspath(path)))
    # Tutto o niente: si scrive un file temporaneo accanto e lo si mette al
    # posto del vecchio solo alla fine, cosi' un crash o un disco pieno a
    # meta' salvataggio non lasciano un progetto troncato.
    tmp = f"{path}.{os.getpid()}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
