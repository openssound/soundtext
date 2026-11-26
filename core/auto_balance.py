"""
Bilancia i volumi: ogni traccia suonata da sola, col suono vero del brano (il SoundFont scelto, quelli per traccia, gli
effetti), se ne misura il volume dove suona; dal ruolo della traccia (melodia, basso, batteria, accompagnamento, tappeto...)
si ricava il livello che deve avere rispetto alla melodia, e il volume della traccia (Mixer, 0-200) si porta li'.

La misura la fa chi sa suonare il brano: il computer (core.playback.render_project_mix, measure_levels qui sotto) o il
telefono (il calcolo fuori tempo dell'esportazione, mobile/app/balance.js); qui ci sono il riconoscimento dei ruoli, il
conto dei volumi e la scrittura nel testo, uguali per tutti e due.

Il volume di una traccia con le note scala la velocity e il volume del canale (CC7): misurato con FluidSynth, dimezzarlo vale
circa -23 dB, cioe' SLOPE_DB * log10(volume/100). Una traccia audio o con uno strumento plugin ha il volume come guadagno
(20 * log10). Con due passate (misura, volumi, misura, ritocco) lo scarto resta sotto il decibel.
"""

import json
import math
import re
from typing import Dict, List, Optional, Tuple

# il livello di ogni ruolo rispetto alla melodia (dB): la melodia davanti, basso e batteria appena sotto, gli accompagnamenti
# sotto, il tappeto di sfondo
ROLE_OFFSETS = {"melody": 0.0, "drums": -1.0, "bass": -2.0, "comp": -4.0, "comp2": -6.0, "horn": -5.0, "harm": -5.0,
                "pad": -10.0, "other": -6.0}
SLOPE_DB = 77.0            # dB per decade di volume di una traccia di note (velocity e CC7 insieme)
GAIN_SLOPE_DB = 20.0       # traccia audio o strumento plugin: il volume e' un guadagno
MIN_VOLUME, MAX_VOLUME = 10, 200
SILENCE_DB = -60.0         # una finestra sotto questa soglia non suona: non conta nella media
WINDOW_SECONDS = 0.1


def level_db(samples, rate: int) -> Optional[float]:
    """Il volume (dB, RMS) dove la traccia suona: le finestre di WINDOW_SECONDS sopra SILENCE_DB. None se non suona mai."""
    import numpy as np
    x = np.asarray(samples, dtype=np.float32)
    if x.ndim == 2:
        x = x.mean(axis=1)
    win = max(1, int(rate * WINDOW_SECONDS))
    n = len(x) // win
    if n == 0:
        return None
    frames = np.sqrt((x[: n * win].reshape(n, win) ** 2).mean(axis=1) + 1e-12)
    loud = frames[frames > 10 ** (SILENCE_DB / 20)]
    if not len(loud):
        return None
    return float(20 * math.log10(math.sqrt(float((loud ** 2).mean()))))


# ---------------------------------------------------------------- i ruoli

def quick_parts(text: str) -> Optional[Dict[str, str]]:
    """Le parti di un brano generato («// quick: {...}»): {nome della traccia: parte}. None per un brano scritto a mano."""
    m = re.search(r"^// quick: (\{.*\})\s*$", text or "", re.MULTILINE)
    if not m:
        return None
    try:
        saved = json.loads(m.group(1))
    except ValueError:
        return None
    instruments, tracks = saved.get("instruments") or {}, saved.get("tracks") or {}
    out = {tracks.get(part, name): part for part, name in instruments.items() if isinstance(name, str)}
    return out or None


def _stats(project, track) -> Optional[dict]:
    """Registro medio, quante note suonano insieme e quanto durano: per indovinare il ruolo di una traccia scritta a mano."""
    try:
        events = track.parsed_events(project.patterns, meter=project.meter())
    except Exception:
        return None
    from st_language.midi import resolve_event_notes, sounding_events
    pitches, sizes, durations = [], [], []
    for ev in sounding_events(events):
        try:
            notes, _v = resolve_event_notes(ev, track.instrument)
        except Exception:
            continue
        if not notes:
            continue
        pitches += list(notes)
        sizes.append(len(notes))
        durations.append(float(ev.duration))
    if not pitches:
        return None
    return {"pitch": sum(pitches) / len(pitches), "chord": sum(1 for s in sizes if s > 1) / len(sizes),
            "duration": sum(durations) / len(durations), "notes": len(sizes)}


def track_roles(project, text: str = "") -> Dict[str, str]:
    """Il ruolo di ogni traccia che si puo' bilanciare: quello del brano generato, se lo e', altrimenti indovinato dalle note.
    La batteria e' batteria; fra le altre, una sola voce piu' grave e' il basso, la voce sola piu' acuta e' la melodia (le
    altre voci sole sono seconde voci), gli accordi tenuti a lungo sono il tappeto, gli altri accordi gli accompagnamenti (il
    piu' fitto e' il primo). Le tracce audio sono melodia se sono l'unica voce, altrimenti restano come sono."""
    tracks = [t for t in project.tracks if not getattr(t, "mute", False)]
    parts = quick_parts(text)
    if parts:
        roles = {}
        for t in tracks:
            part = parts.get(t.name)
            if part:
                roles[t.name] = "comp" if part == "progression" else part
        if roles:
            return roles
    roles: Dict[str, str] = {}
    stats = {}
    for t in tracks:
        if t.is_audio:
            continue
        if t.instrument.is_percussion:
            roles[t.name] = "drums"
            continue
        s = _stats(project, t)
        if s:
            stats[t.name] = s
    mono = sorted((n for n, s in stats.items() if s["chord"] < 0.3), key=lambda n: stats[n]["pitch"])
    poly = [n for n, s in stats.items() if s["chord"] >= 0.3]
    if mono and stats[mono[0]]["pitch"] < 52:
        roles[mono.pop(0)] = "bass"
    if mono:
        lead = max(mono, key=lambda n: (stats[n]["pitch"], stats[n]["notes"]))
        roles[lead] = "melody"
        for n in mono:
            roles.setdefault(n, "harm")
    comps = sorted((n for n in poly if stats[n]["duration"] < 2.0), key=lambda n: -stats[n]["notes"])
    for i, n in enumerate(comps):
        roles[n] = "comp" if i == 0 else "comp2"
    for n in poly:
        roles.setdefault(n, "pad")
    audio = [t.name for t in tracks if t.is_audio]
    if audio and "melody" not in roles.values() and len(audio) == 1:
        roles[audio[0]] = "melody"
    return roles


# ---------------------------------------------------------------- i volumi

def _slope(track) -> float:
    return GAIN_SLOPE_DB if (track.is_audio or getattr(track, "synth", "")) else SLOPE_DB


def target_volumes(project, levels: Dict[str, Optional[float]], roles: Dict[str, str]) -> Dict[str, int]:
    """I volumi nuovi (0-200) delle tracce misurate: ognuna al livello del suo ruolo (ROLE_OFFSETS) rispetto alla melodia,
    che resta com'e'. Senza melodia il riferimento e' la traccia che ci si avvicina di piu' (il primo accompagnamento...)."""
    measured = {n: l for n, l in levels.items() if l is not None and n in roles}
    if not measured:
        return {}
    ref_name = next((n for n in measured if roles[n] == "melody"), None)
    if ref_name is None:
        ref_name = min(measured, key=lambda n: -ROLE_OFFSETS.get(roles[n], -6.0))
    reference = measured[ref_name] - ROLE_OFFSETS.get(roles[ref_name], -6.0)
    out = {}
    for name, level in measured.items():
        track = project.find_track(name)
        if track is None:
            continue
        wanted = reference + ROLE_OFFSETS.get(roles[name], ROLE_OFFSETS["other"])
        factor = 10 ** ((wanted - level) / _slope(track))
        out[name] = int(round(max(MIN_VOLUME, min(MAX_VOLUME, max(1, track.volume) * factor))))
    return out


def measure_levels(project, names: List[str], stop_check=None) -> Dict[str, Optional[float]]:
    """Sul computer: il volume di ogni traccia suonata da sola, come si sente (core.playback.render_project_mix)."""
    from .playback import render_project_mix
    out = {}
    for name in names:
        track = project.find_track(name)
        if track is None:
            continue
        try:
            samples, rate = render_project_mix(project, stop_check=stop_check, tracks=[track], master=False)
        except Exception:
            out[name] = None
            continue
        out[name] = level_db(samples, rate)
    return out


def balance_project(project, text: str = "", passes: int = 2, stop_check=None) -> Dict[str, Tuple[int, int]]:
    """Sul computer: bilancia i volumi del progetto (in place). Ritorna {traccia: (volume di prima, volume nuovo)}."""
    roles = track_roles(project, text)
    before = {n: project.find_track(n).volume for n in roles if project.find_track(n) is not None}
    for _ in range(max(1, passes)):
        levels = measure_levels(project, list(roles), stop_check)
        volumes = target_volumes(project, levels, roles)
        for name, volume in volumes.items():
            project.find_track(name).volume = volume
    return {n: (before[n], project.find_track(n).volume) for n in before if project.find_track(n).volume != before[n]}


# ---------------------------------------------------------------- nel testo

_MIXER = re.compile(r"^Mixer (?P<name>[^\n:]+?):[ \t]*\n(?P<body>(?:[ \t]+.*\n?)*)", re.MULTILINE)   # nomi anche con spazi


def set_volumes_in_text(text: str, volumes: Dict[str, int]) -> str:
    """Il testo con i volumi delle tracce cambiati (blocchi «Mixer Nome:»): dove il blocco c'e' cambia solo «volume:»,
    altrimenti se ne aggiunge uno prima delle sezioni (i box). Il resto del testo non si tocca."""
    remaining = dict(volumes)

    def edit(m):
        name = m.group("name")
        if name not in remaining:
            return m.group(0)
        volume = remaining.pop(name)
        body = m.group("body")
        if re.search(r"\bvolume:\s*\d+", body):
            body = re.sub(r"\bvolume:\s*\d+", f"volume: {volume}", body, count=1)
        else:
            body = f"  volume: {volume}\n" + body
        return f"Mixer {name}:\n" + body

    text = _MIXER.sub(edit, text)
    if remaining:
        blocks = "".join(f"Mixer {name}:\n  volume: {volume}\n\n" for name, volume in remaining.items())
        m = re.search(r"^(// Le sezioni[^\n]*\n|Box |Clip |Audio )", text, re.MULTILINE)
        at = m.start() if m else len(text)
        if not m and not text.endswith("\n"):
            blocks = "\n" + blocks
        text = text[:at] + blocks + text[at:]
    return text
