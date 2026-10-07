"""
Effetti del synth (primo passo degli effetti): l'"ambiente" del riverbero,
uno per tutto il brano (Project.reverb_room), in cui ogni traccia di testo
manda la sua parte di suono (Track.reverb, vedi core.midi_export).

L'ambiente predefinito ("stanza") ha esattamente i valori di partenza di
fluidsynth: i progetti che non lo cambiano suonano come prima. Anche con
l'invio a 0 l'ambiente puo' cambiare un po' il suono, perche' alcuni
SoundFont mandano gia' da soli una parte dei loro strumenti al riverbero.
"""

import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
from .i18n import tr

# chiave -> (etichetta, room size, damping, width, level) di fluidsynth
REVERB_ROOMS = {
    "stanza": ("Stanza piccola", 0.2, 0.0, 0.5, 0.9),
    "sala": ("Sala", 0.5, 0.3, 0.7, 0.9),
    "sala_grande": ("Sala grande", 0.7, 0.35, 0.8, 0.9),
    "chiesa": ("Chiesa", 0.9, 0.45, 1.0, 0.9),
}
DEFAULT_REVERB_ROOM = "stanza"


def reverb_params(room: str) -> Tuple[float, float, float, float]:
    """(room size, damping, width, level) dell'ambiente (quello predefinito
    per una chiave sconosciuta)."""
    _label, *params = REVERB_ROOMS.get(room, REVERB_ROOMS[DEFAULT_REVERB_ROOM])
    return tuple(params)


def reverb_cli_options(room: str) -> List[str]:
    """Opzioni '-o' della riga di comando di fluidsynth per l'ambiente."""
    size, damping, width, level = reverb_params(room)
    return ["-o", f"synth.reverb.room-size={size}", "-o", f"synth.reverb.damp={damping}",
            "-o", f"synth.reverb.width={width}", "-o", f"synth.reverb.level={level}"]


def apply_reverb(synth, room: str):
    """Imposta l'ambiente su un core.fluid.Synth gia' creato (resta valido
    anche dopo system_reset)."""
    size, damping, width, level = reverb_params(room)
    synth.set_reverb(roomsize=size, damping=damping, width=width, level=level)


# ---------------------------------------------------------------------------
# Catena di effetti per traccia (fase 2): elaborata dopo il rendering della
# traccia, con pedalboard (https://github.com/spotify/pedalboard, GPLv3).
# Chiavi ed etichette in italiano: sono anche quelle del file .st
# (blocco "Effetti <traccia>:", vedi core.project_io).
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EffectParam:
    key: str
    label: str
    minimum: float
    maximum: float
    default: float
    unit: str = ""
    step: float = 1.0
    # Parametro "a elenco" (modello d'amplificatore, cassa, suddivisione del
    # delay): ((chiave, etichetta), ...). Il valore e' l'indice della scelta;
    # nel file .st si scrive la chiave (vedi choice_key/clamp_params).
    choices: Tuple[Tuple[str, str], ...] = ()


def _choice(key, label, choices, default_key):
    keys = [k for k, _label in choices]
    return EffectParam(key, label, 0, len(choices) - 1, keys.index(default_key), choices=tuple(choices))


def choice_key(param: EffectParam, value: float) -> str:
    return param.choices[int(round(value))][0]


# Suddivisioni del delay a tempo: chiave -> durata in battiti (quarti).
DELAY_DIVISIONS = {"1/2": 2.0, "1/4": 1.0, "1/4p": 1.5, "1/4t": 2.0 / 3.0,
                   "1/8": 0.5, "1/8p": 0.75, "1/8t": 1.0 / 3.0, "1/16": 0.25}
_DELAY_CHOICES = [("libera", "Libera (ms)"), ("1/2", "1/2"), ("1/4", "1/4"), ("1/4p", "1/4 puntato"),
                  ("1/4t", "1/4 terzina"), ("1/8", "1/8"), ("1/8p", "1/8 puntato"),
                  ("1/8t", "1/8 terzina"), ("1/16", "1/16")]

AMP_MODELS = [("pulito", "Pulito"), ("crunch", "Crunch"), ("british", "British"), ("high_gain", "High gain")]
# Cassa dopo un profilo NAM: molti profili la includono gia' (catturati dal
# microfono davanti alla cassa); gli altri si completano con un file IR.
NAM_CABINETS = [("nessuna", "Nessuna / inclusa"), ("file", "File IR…")]

AMP_CABINETS = [("nessuna", "Nessuna"), ("combo_1x12", "Combo 1×12"), ("2x12", "2×12"),
                ("4x12", "4×12 chiusa"), ("vintage_1x10", "Vintage 1×10"),
                # la risposta all'impulso di una cassa vera, da un file WAV (Effect.ir)
                ("file", "File IR…")]


# tipo -> (etichetta, famiglia, parametri, preset {nome: {parametro: valore}})
EFFECT_KINDS: Dict[str, dict] = {
    "eq": {
        "label": "EQ a 3 bande", "family": "Tono",
        "params": [EffectParam("bassi", "Bassi", -12, 12, 0, "dB", 0.5),
                   EffectParam("medi", "Medi", -12, 12, 0, "dB", 0.5),
                   EffectParam("alti", "Alti", -12, 12, 0, "dB", 0.5)],
        "presets": {"Neutro": {"bassi": 0, "medi": 0, "alti": 0},
                    "Più calore": {"bassi": 3, "medi": 0, "alti": -2},
                    "Più presenza": {"bassi": -1, "medi": 3, "alti": 2},
                    "Brillante": {"bassi": 0, "medi": -1, "alti": 4},
                    "Voce radio": {"bassi": -9, "medi": 4, "alti": -4}},
    },
    "compressore": {
        "label": "Compressore", "family": "Dinamica",
        "params": [EffectParam("soglia", "Soglia", -40, 0, -18, "dB", 0.5),
                   EffectParam("rapporto", "Rapporto", 1, 20, 3, ":1", 0.5),
                   EffectParam("attacco", "Attacco", 1, 100, 10, "ms"),
                   EffectParam("rilascio", "Rilascio", 20, 500, 150, "ms"),
                   EffectParam("guadagno", "Guadagno", 0, 18, 3, "dB", 0.5)],
        "presets": {"Morbido": {"soglia": -18, "rapporto": 2, "attacco": 20, "rilascio": 200, "guadagno": 2},
                    "Voce": {"soglia": -20, "rapporto": 4, "attacco": 5, "rilascio": 120, "guadagno": 4},
                    "Batteria": {"soglia": -15, "rapporto": 4, "attacco": 2, "rilascio": 80, "guadagno": 3},
                    "Basso": {"soglia": -18, "rapporto": 5, "attacco": 10, "rilascio": 150, "guadagno": 4},
                    "Deciso": {"soglia": -24, "rapporto": 8, "attacco": 3, "rilascio": 100, "guadagno": 6},
                    "Colla del mix": {"soglia": -14, "rapporto": 2, "attacco": 30, "rilascio": 200,
                                      "guadagno": 1}},
    },
    "limiter": {
        "label": "Limiter", "family": "Dinamica",
        "params": [EffectParam("guadagno", "Guadagno", 0, 18, 0, "dB", 0.5),
                   EffectParam("tetto", "Tetto", -12, 0, -1, "dB", 0.5),
                   EffectParam("rilascio", "Rilascio", 10, 1000, 100, "ms", 5)],
        "presets": {"Sicurezza": {"guadagno": 0, "tetto": -1, "rilascio": 100},
                    "Più forte": {"guadagno": 6, "tetto": -1, "rilascio": 80},
                    "Molto forte": {"guadagno": 12, "tetto": -1, "rilascio": 50}},
    },
    "noise_gate": {
        "label": "Noise gate", "family": "Dinamica",
        "params": [EffectParam("soglia", "Soglia", -80, -10, -50, "dB", 0.5),
                   EffectParam("rapporto", "Rapporto", 1.5, 20, 10, ":1", 0.5),
                   EffectParam("attacco", "Attacco", 1, 50, 1, "ms"),
                   EffectParam("rilascio", "Rilascio", 10, 1000, 100, "ms", 5)],
        "presets": {"Leggero": {"soglia": -60, "rapporto": 4, "attacco": 1, "rilascio": 200},
                    "Voce": {"soglia": -50, "rapporto": 10, "attacco": 1, "rilascio": 100},
                    "Chitarra": {"soglia": -45, "rapporto": 10, "attacco": 2, "rilascio": 80},
                    "Batteria": {"soglia": -35, "rapporto": 20, "attacco": 1, "rilascio": 60}},
    },
    "passa_alto": {
        "label": "Filtro passa-alto", "family": "Tono",
        "params": [EffectParam("frequenza", "Frequenza", 20, 2000, 80, "Hz", 5),
                   EffectParam("pendenza", "Pendenza", 6, 24, 12, "dB/ott", 6)],
        "presets": {"Pulizia bassi": {"frequenza": 80, "pendenza": 12},
                    "Voce": {"frequenza": 100, "pendenza": 18},
                    "Chitarra nel mix": {"frequenza": 150, "pendenza": 12},
                    "Sottile": {"frequenza": 400, "pendenza": 24}},
    },
    "passa_basso": {
        "label": "Filtro passa-basso", "family": "Tono",
        "params": [EffectParam("frequenza", "Frequenza", 200, 20000, 8000, "Hz", 50),
                   EffectParam("pendenza", "Pendenza", 6, 24, 12, "dB/ott", 6)],
        "presets": {"Morbido": {"frequenza": 8000, "pendenza": 6},
                    "Scuro": {"frequenza": 3000, "pendenza": 12},
                    "Ovattato": {"frequenza": 1000, "pendenza": 24},
                    "Dietro una porta": {"frequenza": 500, "pendenza": 24}},
    },
    "nam": {
        "label": "Profilo NAM", "family": "Saturazione",
        # Un amplificatore o pedale "catturato" con Neural Amp Modeler (file
        # .nam, vedi core.nam): Ingresso come la manopola "input" del plugin.
        "params": [EffectParam("ingresso", "Ingresso", -24, 24, 0, "dB", 0.5),
                   _choice("cassa", "Cassa", NAM_CABINETS, "nessuna"),
                   EffectParam("livello", "Livello", -30, 12, 0, "dB", 0.5)],
        "presets": {"Neutro": {"ingresso": 0, "livello": 0},
                    "Piu' spinto": {"ingresso": 6, "livello": -4},
                    "Piu' pulito": {"ingresso": -6, "livello": 4}},
    },
    "distorsione": {
        "label": "Distorsione", "family": "Saturazione",
        "params": [EffectParam("spinta", "Spinta", 0, 40, 15, "dB", 0.5),
                   EffectParam("tono", "Tono", 0, 100, 60, "%"),
                   EffectParam("livello", "Livello", -24, 6, -6, "dB", 0.5),
                   EffectParam("mix", "Mix", 0, 100, 100, "%")],
        "presets": {"Calda": {"spinta": 6, "tono": 70, "livello": -3, "mix": 100},
                    "Crunch": {"spinta": 14, "tono": 60, "livello": -7, "mix": 100},
                    "Overdrive": {"spinta": 22, "tono": 55, "livello": -10, "mix": 100},
                    "Fuzz": {"spinta": 36, "tono": 40, "livello": -14, "mix": 100},
                    "Parallela": {"spinta": 24, "tono": 50, "livello": -8, "mix": 35}},
    },
    "amplificatore": {
        "label": "Amplificatore", "family": "Saturazione",
        # Bassi/Medi/Alti/Presenza sulla scala 0-10 degli amplificatori veri:
        # sono le manopole del tone stack (vedi tone_stack_ir), non dei dB.
        "params": [_choice("modello", "Modello", AMP_MODELS, "crunch"),
                   _choice("cassa", "Cassa", AMP_CABINETS, "combo_1x12"),
                   EffectParam("guadagno", "Guadagno", 0, 40, 18, "dB", 0.5),
                   EffectParam("bassi", "Bassi", 0, 10, 5, "", 0.5),
                   EffectParam("medi", "Medi", 0, 10, 6, "", 0.5),
                   EffectParam("alti", "Alti", 0, 10, 5, "", 0.5),
                   EffectParam("presenza", "Presenza", 0, 10, 5, "", 0.5),
                   EffectParam("potenza", "Potenza", 0, 100, 40, "%"),
                   EffectParam("livello", "Livello", -30, 6, -10, "dB", 0.5)],
        "presets": {"Pulito brillante": {"modello": "pulito", "cassa": "combo_1x12", "guadagno": 10,
                                         "bassi": 5, "medi": 5, "alti": 7, "presenza": 6, "potenza": 20,
                                         "livello": -6},
                    "Blues": {"modello": "crunch", "cassa": "combo_1x12", "guadagno": 18,
                              "bassi": 5, "medi": 6, "alti": 5, "presenza": 5, "potenza": 40, "livello": -10},
                    "Vintage": {"modello": "crunch", "cassa": "vintage_1x10", "guadagno": 14,
                                "bassi": 4, "medi": 7, "alti": 5, "presenza": 4, "potenza": 55, "livello": -8},
                    "Rock classico": {"modello": "british", "cassa": "4x12", "guadagno": 24,
                                      "bassi": 6, "medi": 7, "alti": 6, "presenza": 6, "potenza": 45,
                                      "livello": -12},
                    "Metal": {"modello": "high_gain", "cassa": "4x12", "guadagno": 30,
                              "bassi": 7, "medi": 3, "alti": 6, "presenza": 6, "potenza": 25,
                              "livello": -14}},
    },
    "delay": {
        "label": "Delay", "family": "Spazio",
        "params": [_choice("suddivisione", "A tempo", _DELAY_CHOICES, "libera"),
                   EffectParam("tempo", "Tempo", 20, 1500, 375, "ms", 5),
                   EffectParam("ripetizioni", "Ripetizioni", 0, 90, 30, "%"),
                   EffectParam("mix", "Mix", 0, 100, 25, "%")],
        "presets": {"Slapback": {"tempo": 90, "ripetizioni": 0, "mix": 25},
                    "Eco corto": {"tempo": 250, "ripetizioni": 25, "mix": 20},
                    "Eco lungo": {"tempo": 500, "ripetizioni": 40, "mix": 25},
                    "Spaziale": {"tempo": 750, "ripetizioni": 60, "mix": 30},
                    "A tempo 1/4": {"suddivisione": "1/4", "ripetizioni": 30, "mix": 22},
                    "A tempo 1/8 puntato": {"suddivisione": "1/8p", "ripetizioni": 35, "mix": 25}},
    },
    "riverbero": {
        "label": "Riverbero", "family": "Spazio",
        "params": [EffectParam("stanza", "Stanza", 0, 100, 50, "%"),
                   EffectParam("smorzamento", "Smorzamento", 0, 100, 50, "%"),
                   EffectParam("ampiezza", "Ampiezza", 0, 100, 100, "%"),
                   EffectParam("mix", "Mix", 0, 100, 20, "%")],
        "presets": {"Stanza": {"stanza": 30, "smorzamento": 50, "ampiezza": 80, "mix": 15},
                    "Sala": {"stanza": 60, "smorzamento": 40, "ampiezza": 100, "mix": 22},
                    "Piastra": {"stanza": 50, "smorzamento": 20, "ampiezza": 100, "mix": 25},
                    "Cattedrale": {"stanza": 90, "smorzamento": 30, "ampiezza": 100, "mix": 30}},
    },
    "chorus": {
        "label": "Chorus", "family": "Spazio",
        "params": [EffectParam("velocita", "Velocità", 0.1, 5, 1.0, "Hz", 0.1),
                   EffectParam("profondita", "Profondità", 0, 100, 25, "%"),
                   EffectParam("mix", "Mix", 0, 100, 50, "%")],
        "presets": {"Leggero": {"velocita": 0.6, "profondita": 15, "mix": 35},
                    "Classico": {"velocita": 1.0, "profondita": 25, "mix": 50},
                    "Ampio": {"velocita": 0.4, "profondita": 45, "mix": 60}},
    },
    "phaser": {
        "label": "Phaser", "family": "Spazio",
        "params": [EffectParam("velocita", "Velocità", 0.05, 5, 0.5, "Hz", 0.05),
                   EffectParam("profondita", "Profondità", 0, 100, 50, "%"),
                   EffectParam("ritorno", "Ritorno", 0, 90, 30, "%"),
                   EffectParam("mix", "Mix", 0, 100, 50, "%")],
        "presets": {"Lento": {"velocita": 0.2, "profondita": 60, "ritorno": 30, "mix": 50},
                    "Medio": {"velocita": 0.6, "profondita": 50, "ritorno": 40, "mix": 50},
                    "Veloce": {"velocita": 2.0, "profondita": 40, "ritorno": 20, "mix": 40}},
    },
    "plugin": {
        "label": "Plugin (VST3/LV2)", "family": "Plugin",
        # Un plugin esterno (Effect.plugin, vedi core.plugins): i suoi
        # parametri sono in Effect.plugin_params; qui solo il dosaggio.
        "params": [EffectParam("mix", "Mix", 0, 100, 100, "%"),
                   EffectParam("livello", "Livello", -24, 12, 0, "dB", 0.5)],
        "presets": {"Neutro": {"mix": 100, "livello": 0},
                    "Metà": {"mix": 50, "livello": 0}},
    },
}
EFFECT_FAMILIES = ("Dinamica", "Tono", "Saturazione", "Spazio", "Plugin")

# Catena tipica per il master (pulsante "+ Catena di mastering" del pannello):
# (tipo, preset).
MASTERING_CHAIN = (("eq", "Neutro"), ("compressore", "Colla del mix"), ("limiter", "Più forte"))


def effect_params(kind: str):
    return EFFECT_KINDS[kind]["params"]


def default_params(kind: str) -> Dict[str, float]:
    return {p.key: float(p.default) for p in effect_params(kind)}


def clamp_params(kind: str, params: Dict[str, float]) -> Dict[str, float]:
    """I parametri del tipo, completati con i valori predefiniti e riportati
    nei limiti (quelli sconosciuti si scartano)."""
    out = default_params(kind)
    for p in effect_params(kind):
        if p.key not in params:
            continue
        value = params[p.key]
        if p.choices:
            keys = [k for k, _label in p.choices]
            if isinstance(value, str) and value in keys:
                out[p.key] = float(keys.index(value))
                continue
        try:
            value = float(max(p.minimum, min(p.maximum, float(value))))
        except (TypeError, ValueError):
            continue
        out[p.key] = float(round(value)) if p.choices else value
    return out


def inactive_params(kind: str, params: Dict[str, float]) -> set:
    """Parametri che al momento non contano (la manopola si spegne): il
    tempo in ms del delay quando e' a tempo col brano."""
    if kind == "delay" and clamp_params(kind, params)["suddivisione"] > 0:
        return {"tempo"}
    return set()


def delay_seconds(params: Dict[str, float], bpm: float) -> float:
    """Il tempo del delay: in ms, o dalla suddivisione e dal BPM del brano."""
    p = clamp_params("delay", params)
    division = _DELAY_CHOICES[int(p["suddivisione"])][0]
    if division in DELAY_DIVISIONS and bpm and bpm > 0:
        return min(3.0, DELAY_DIVISIONS[division] * 60.0 / float(bpm))
    return p["tempo"] / 1000.0


def preset_params(kind: str, preset: str) -> Dict[str, float]:
    return clamp_params(kind, EFFECT_KINDS[kind]["presets"][preset])


def matching_preset(kind: str, params: Dict[str, float]) -> str:
    """Il nome del preset che ha esattamente questi parametri, o ''."""
    current = clamp_params(kind, params)
    for name, values in EFFECT_KINDS[kind]["presets"].items():
        if clamp_params(kind, values) == current:
            return name
    return ""


def format_value(param: EffectParam, value: float) -> str:
    if param.choices:
        return tr(param.choices[int(round(value))][1])
    if param.unit == ":1":
        return f"{value:g}:1".replace(".", ",")
    if param.unit == "Hz" and value >= 1000:
        return f"{value / 1000:g} kHz".replace(".", ",")
    if param.unit == "dB" and value > 0:
        text = f"+{value:g}"
    else:
        text = f"{value:g}"
    text = text.replace(".", ",").replace("-", "−")
    return f"{text} {param.unit}" if param.unit else text


try:
    import pedalboard as _pedalboard
except ImportError:   # effetti non disponibili: la catena si ignora (vedi effects_available)
    _pedalboard = None


def effects_available() -> bool:
    return _pedalboard is not None


def active_effects(effects) -> list:
    """Gli effetti accesi, di tipo conosciuto."""
    return [e for e in (effects or []) if e.enabled and e.kind in EFFECT_KINDS]


def uses_ir_file(effect) -> bool:
    """L'effetto (amplificatore o profilo NAM) usa la cassa da file IR (Effect.ir)."""
    if effect.kind not in EFFECT_KINDS:
        return False
    cabinet = next((p for p in effect_params(effect.kind) if p.key == "cassa"), None)
    return cabinet is not None and choice_key(cabinet, clamp_params(effect.kind, effect.params)["cassa"]) == "file"


def _file_signature(path: str) -> tuple:
    try:
        stat = os.stat(path)
        return (os.path.abspath(path), stat.st_mtime, stat.st_size)
    except OSError:
        return (path, None)


def _ir_signature(effect) -> tuple:
    """La parte della chiave di cache che dipende dai file dell'effetto
    (IR della cassa, profilo NAM): cambia se il file cambia su disco."""
    signature = ()
    if uses_ir_file(effect):
        signature += _file_signature(effect.ir)
    if effect.kind == "nam":
        signature += _file_signature(effect.nam)
    if effect.kind == "plugin":
        from .plugins import signature as plugin_signature
        signature += plugin_signature(effect.plugin, effect.plugin_params, effect.plugin_state)
    return signature


def chain_signature(effects, bpm: float = 120.0) -> str:
    """Parte della chiave di cache che dipende dalla catena (e dal BPM, per
    il delay a tempo; e dal file IR della cassa, se cambia su disco)."""
    chain = active_effects(effects)
    synced = any(e.kind == "delay" and inactive_params(e.kind, e.params) for e in chain)
    return repr(([(e.kind, sorted(clamp_params(e.kind, e.params).items())) + _ir_signature(e) for e in chain],
                 float(bpm) if synced else None))


def tail_seconds(effects, bpm: float = 120.0) -> float:
    """Quanto lasciare suonare dopo la fine della traccia: code di delay e
    riverbero (al massimo 8 secondi)."""
    tail = 0.0
    for e in active_effects(effects):
        p = clamp_params(e.kind, e.params)
        if e.kind == "delay":
            fb = p["ripetizioni"] / 100.0
            repeats = 1 if fb <= 0 else min(12.0, np.log(0.001) / np.log(max(fb, 1e-3)))
            tail = max(tail, delay_seconds(e.params, bpm) * (repeats + 1))
        elif e.kind in ("amplificatore", "nam"):
            ir = load_ir_file(e.ir, 48000) if uses_ir_file(e) else None
            tail = max(tail, 0.1 if ir is None else len(ir) / 48000.0 + 0.1)   # rete e risposta della cassa
        elif e.kind == "riverbero":
            tail = max(tail, 0.5 + 5.5 * p["stanza"] / 100.0)
        elif e.kind in ("chorus", "phaser"):
            tail = max(tail, 0.1)
        elif e.kind == "plugin":
            # la coda di un plugin non si conosce: se ne lascia abbastanza
            # (il silenzio in eccesso si toglie, vedi apply_effect_chain)
            tail = max(tail, 4.0)
    return min(8.0, tail)


# ---------------------------------------------------------------------------
# Casse d'amplificatore: risposte all'impulso generate qui (nessun file audio
# nel programma), a fase minima, dalla curva di frequenza tipica di ciascuna:
# taglio dei bassi, "botta" della cassa, presenza, taglio netto degli acuti
# (un altoparlante per chitarra non riproduce oltre i 5-6 kHz) e un po' di
# irregolarita' fissa, come in un altoparlante vero.
# ---------------------------------------------------------------------------

# cassa -> (passa-alto Hz, ordine), [(frequenza, dB, larghezza in ottave)], (passa-basso Hz, ordine)
_CABINET_CURVES = {
    "combo_1x12": ((85, 2), [(110, 3, 0.35), (800, -2, 0.6), (2200, 4, 0.6)], (5500, 4)),
    "2x12": ((75, 2), [(105, 4, 0.35), (500, -2.5, 0.6), (2600, 5, 0.5)], (5000, 4)),
    "4x12": ((65, 3), [(95, 6, 0.3), (400, -3, 0.6), (1800, 3, 0.5), (3200, 4, 0.4)], (4500, 5)),
    "vintage_1x10": ((120, 2), [(1500, 5, 0.7)], (4000, 4)),
}
_IR_LENGTH = 2048
_ir_cache: Dict[Tuple[str, int], np.ndarray] = {}


def cabinet_ir(cabinet: str, samplerate: int) -> np.ndarray:
    """Risposta all'impulso (float32) della cassa, normalizzata perche' in
    media nella banda utile non cambi il volume."""
    key = (cabinet, samplerate)
    if key in _ir_cache:
        return _ir_cache[key]
    (hp, hp_order), bumps, (lp, lp_order) = _CABINET_CURVES[cabinet]
    n = 8192
    f = np.fft.rfftfreq(n, 1.0 / samplerate)
    f[0] = 1.0
    db = (10 * np.log10(1.0 / (1.0 + (hp / f) ** (2 * hp_order)))
          + 10 * np.log10(1.0 / (1.0 + (f / lp) ** (2 * lp_order))))
    octaves = np.log2(f / 1000.0)
    for freq, gain, width in bumps:
        db += gain * np.exp(-0.5 * ((octaves - np.log2(freq / 1000.0)) / width) ** 2)
    rng = np.random.RandomState(sum(map(ord, cabinet)))
    for freq in np.geomspace(200, 5000, 9):
        db += rng.uniform(-1.5, 1.5) * np.exp(-0.5 * ((octaves - np.log2(freq / 1000.0)) / 0.12) ** 2)
    band = (f >= 100) & (f <= 5000)
    db -= 20 * np.log10(np.mean(10 ** (db[band] / 20)))
    magnitude = np.maximum(10 ** (db / 20), 1e-6)
    # fase minima dal cepstro reale
    full = np.concatenate([magnitude, magnitude[-2:0:-1]])
    cepstrum = np.fft.ifft(np.log(full)).real
    fold = np.zeros_like(cepstrum)
    fold[0] = cepstrum[0]
    fold[1:n // 2] = 2 * cepstrum[1:n // 2]
    fold[n // 2] = cepstrum[n // 2]
    ir = np.fft.ifft(np.exp(np.fft.fft(fold))).real[:_IR_LENGTH]
    ir[-256:] *= np.linspace(1.0, 0.0, 256)
    ir = ir.astype(np.float32)
    _ir_cache[key] = ir
    return ir


IR_MAX_SECONDS = 1.0
_ir_file_cache: Dict[tuple, np.ndarray] = {}


def _normalize_ir(ir: np.ndarray, samplerate: int) -> np.ndarray:
    """In media nella banda utile (100 Hz - 5 kHz) la cassa non cambia il
    volume: stesso criterio delle casse interne."""
    n = 1 << int(np.ceil(np.log2(max(len(ir), 4096))))
    f = np.fft.rfftfreq(n, 1.0 / samplerate)
    band = (f >= 100) & (f <= 5000)
    level = float(np.mean(np.abs(np.fft.rfft(ir, n))[band]))
    return ir / level if level > 1e-9 else ir


def _fft_resample(x: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    """Ricampionamento di un segnale breve (una IR) nel dominio della
    frequenza: esatto nella banda comune, senza aliasing."""
    n_out = int(round(len(x) * dst_rate / float(src_rate)))
    spectrum = np.fft.rfft(x)
    out = np.zeros(n_out // 2 + 1, dtype=complex)
    keep = min(len(out), len(spectrum))
    out[:keep] = spectrum[:keep]
    return np.fft.irfft(out, n_out) * (n_out / float(len(x)))


def load_ir_file(path: str, samplerate: int) -> Optional[np.ndarray]:
    """La risposta all'impulso di una cassa da un file WAV (mono: media dei
    canali), alla frequenza data, al massimo IR_MAX_SECONDS e normalizzata
    come le casse interne. None se il file manca o non e' leggibile."""
    if not path:
        return None
    try:
        stat = os.stat(path)
    except OSError:
        return None
    key = (os.path.abspath(path), stat.st_mtime, stat.st_size, samplerate)
    if key in _ir_file_cache:
        return _ir_file_cache[key]
    try:
        from .audio_tracks import read_wav
        samples, rate = read_wav(path)
        ir = samples.astype(np.float64).mean(axis=1)[:int(IR_MAX_SECONDS * rate)]
        if rate != samplerate:
            ir = _fft_resample(ir, rate, samplerate)
    except Exception:
        logging.getLogger(__name__).warning("File IR non leggibile: %s", path, exc_info=True)
        return None
    ir = ir[:int(IR_MAX_SECONDS * samplerate)]
    if len(ir) == 0 or not np.any(ir):
        return None
    if len(ir) > 512:
        ir[-256:] *= np.linspace(1.0, 0.0, 256)
    ir = _normalize_ir(ir, samplerate).astype(np.float32)
    _ir_file_cache[key] = ir
    return ir


def ir_file_problem(path: str) -> str:
    """'' se il file IR si puo' usare, altrimenti il motivo (per il pannello)."""
    if not path:
        return tr("nessun file scelto")
    if not os.path.exists(path):
        return tr("file non trovato")
    if load_ir_file(path, 48000) is None:
        return tr("non e' un WAV leggibile")
    return ""


def _convolve(x: np.ndarray, ir: np.ndarray) -> np.ndarray:
    """Convoluzione (frame, canali) con 'ir', a blocchi con la FFT; stessa
    lunghezza dell'ingresso (la coda di 40 ms e' coperta da tail_seconds)."""
    frames = len(x)
    if frames == 0:
        return x
    block = 1 << 16
    nfft = 1 << int(np.ceil(np.log2(block + len(ir) - 1)))
    spectrum = np.fft.rfft(ir, nfft)[:, None]
    out = np.zeros((frames + nfft, x.shape[1]), dtype=np.float64)
    for start in range(0, frames, block):
        piece = x[start:start + block]
        out[start:start + nfft] += np.fft.irfft(np.fft.rfft(piece, nfft, axis=0) * spectrum, nfft, axis=0)
    return out[:frames].astype(np.float32)


# ---------------------------------------------------------------------------
# Sovracampionamento delle distorsioni: una saturazione genera armoniche ben
# oltre i 24 kHz che a 48 kHz "si ripiegano" in frequenze spurie non
# armoniche (il frizzare ruvido dell'high gain sulle note acute). Si lavora
# quindi a 4x la frequenza (192 kHz), con filtri FIR a fase lineare prima e
# dopo; a pezzi, per non tenere in memoria il brano intero a 192 kHz.
# ---------------------------------------------------------------------------

OVERSAMPLING = 4
_OS_TAPS = 129            # (taps - 1) divisibile per 2 * OVERSAMPLING: ritardo intero da compensare
_OS_BLOCK = 32768         # frame (alla frequenza originale) per pezzo
_os_filters: Dict[int, np.ndarray] = {}


def _os_filter(factor: int) -> np.ndarray:
    """FIR passa-basso (Kaiser) con taglio al 90% della Nyquist originale."""
    if factor not in _os_filters:
        n = np.arange(_OS_TAPS) - (_OS_TAPS - 1) / 2.0
        fc = 0.45 / factor
        h = 2 * fc * np.sinc(2 * fc * n) * np.kaiser(_OS_TAPS, 9.0)
        _os_filters[factor] = h / h.sum()
    return _os_filters[factor]


class _Upsampler:
    """Interpolazione x'factor' a pezzi consecutivi, in forma polifase: ogni
    fase del FIR lavora alla frequenza originale (niente zeri da filtrare)."""

    def __init__(self, h: np.ndarray, factor: int, channels: int):
        taps = -(-len(h) // factor) * factor
        h = np.concatenate([h, np.zeros(taps - len(h))]) * factor
        self.factor = factor
        self.phases = [h[p::factor] for p in range(factor)]
        self.history = np.zeros((len(self.phases[0]) - 1, channels))

    def process(self, x: np.ndarray) -> np.ndarray:
        buf = np.concatenate([self.history, x])
        self.history = buf[len(buf) - len(self.history):]
        out = np.empty((len(x) * self.factor, x.shape[1]))
        for c in range(x.shape[1]):
            for p, hp in enumerate(self.phases):
                out[p::self.factor, c] = np.convolve(buf[:, c], hp, "valid")
        return out


class _Downsampler:
    """Filtro FIR e decimazione /'factor' a pezzi consecutivi, in forma
    polifase: si calcolano solo i campioni che si tengono."""

    def __init__(self, h: np.ndarray, factor: int, channels: int):
        taps = -(-len(h) // factor) * factor
        h = np.concatenate([h, np.zeros(taps - len(h))])
        self.factor = factor
        self.phases = [h[p::factor] for p in range(factor)]
        self.history = np.zeros((taps, channels))

    def process(self, v: np.ndarray) -> np.ndarray:
        f = self.factor
        span = len(self.phases[0])
        buf = np.concatenate([self.history, v])
        self.history = buf[len(buf) - len(self.history):]
        frames = len(v) // f
        out = np.zeros((frames, v.shape[1]))
        for c in range(v.shape[1]):
            for p, hp in enumerate(self.phases):
                seq = buf[f - p::f, c][:frames + span - 1]
                out[:, c] += np.convolve(seq, hp, "valid")
        return out


@dataclass(frozen=True)
class Saturation:
    """Saturazione tanh(guadagno * x): identica a pedalboard.Distortion
    (verificato), ma calcolata con numpy, molto piu' veloce a 192 kHz."""
    drive_db: float


@dataclass(frozen=True)
class PowerSaturation:
    """Saturazione delle valvole finali: tanh asimmetrica (un po' di
    polarizzazione, quindi anche armoniche pari, piu' "calde"), con il
    guadagno per i segnali piccoli riportato a 1: con poca spinta il
    livello non cambia, con tanta i picchi si arrotondano."""
    drive_db: float
    bias: float = 0.2

    def apply(self, x: np.ndarray) -> np.ndarray:
        g = 10 ** (self.drive_db / 20.0)
        slope = g * (1.0 - np.tanh(self.bias) ** 2)
        return ((np.tanh(g * x + self.bias) - np.tanh(self.bias)) / slope).astype(np.float32)


@dataclass(frozen=True)
class TubeStage:
    """Stadio a valvole del preamplificatore: tanh(guadagno * x) come
    Saturation, piu' lo spostamento del punto di lavoro sui colpi forti.
    Quando il segnale supera la soglia di conduzione della griglia, il
    condensatore di accoppiamento si carica e la polarizzazione si sposta
    (in fretta, 'attack_ms') per poi tornare lentamente ('release_ms'):
    sui colpi forti lo stadio perde un po' di guadagno e distorce in modo
    asimmetrico (armoniche pari), poi "respira" e torna com'era. Piano e'
    identico a Saturation. 'amount' e' lo spostamento massimo della
    polarizzazione (limitato, come dalla corrente di griglia)."""
    drive_db: float
    amount: float = 0.8
    threshold: float = 0.5
    attack_ms: float = 2.0
    release_ms: float = 60.0


class _TubeState:
    """Lo stato (l'inviluppo) di un TubeStage da un pezzo al successivo."""
    CONTROL_HZ = 1000.0          # l'inviluppo si calcola a circa 1 kHz: varia in decine di ms

    def __init__(self, stage: TubeStage, rate: float):
        self.stage = stage
        self.gain = np.float32(10 ** (stage.drive_db / 20.0))
        # blocco di controllo potenza di due: divide esattamente i pezzi di
        # _oversampled, quindi il risultato non dipende da come si spezza il segnale
        self.block = 1 << max(0, int(np.floor(np.log2(rate / self.CONTROL_HZ))))
        block_ms = 1000.0 * self.block / rate
        self.attack = 1.0 - np.exp(-block_ms / stage.attack_ms)
        self.release = 1.0 - np.exp(-block_ms / stage.release_ms)
        self.env = 0.0
        self.last_bias = 0.0

    def process(self, x: np.ndarray) -> np.ndarray:
        u = x * self.gain
        st = self.stage
        n = len(u)
        starts = np.arange(0, n, self.block)
        # quanto la griglia va oltre la soglia di conduzione, blocco per blocco
        over = np.maximum(np.maximum.reduceat(u.max(axis=1), starts) - st.threshold, 0.0)
        bias = np.empty(len(starts))
        env = self.env
        for i, level in enumerate(over):
            env += (self.attack if level > env else self.release) * (level - env)
            # lo spostamento e' limitato (corrente di griglia): tende ad 'amount'
            bias[i] = -st.amount * env / (1.0 + env)
        self.env = env
        # polarizzazione campione per campione, interpolata fra le fini dei
        # blocchi (valore noto solo a blocco finito): nessuna estrapolazione
        # a fine pezzo, quindi identica elaborando il segnale tutto insieme
        ends = np.concatenate([[0.0], np.minimum(starts + self.block, n)])
        values = np.concatenate([[self.last_bias], bias])
        self.last_bias = float(bias[-1]) if len(bias) else self.last_bias
        b = np.interp(np.arange(1, n + 1), ends, values).astype(np.float32)[:, None]
        # tanh intorno al punto di lavoro spostato; togliere tanh(b) evita il
        # "tonfo" in bassa frequenza (lo fa il condensatore del circuito vero)
        return np.tanh(u + b) - np.tanh(b)


def _oversampled(stages: list, factor: int = OVERSAMPLING):
    """Stadio numpy (vedi apply_effect_chain) che fa passare il segnale per
    'stages' (Saturation o plugin di pedalboard) a 'factor' volte la
    frequenza di campionamento. Stessa lunghezza e nessun ritardo rispetto
    all'ingresso."""
    def run(x: np.ndarray, rate: int) -> np.ndarray:
        frames, channels = x.shape
        if frames == 0:
            return x
        h = _os_filter(factor)
        up, down = _Upsampler(h, factor, channels), _Downsampler(h, factor, channels)
        # un Pedalboard per ogni plugin: lo stato dei filtri passa da un pezzo al successivo
        ops = [_TubeState(st, rate * factor) if isinstance(st, TubeStage)
               else st if isinstance(st, (Saturation, PowerSaturation)) else _pedalboard.Pedalboard([st])
               for st in stages]
        delay = (_OS_TAPS - 1) // factor               # ritardo dei due FIR, in frame originali
        padded = np.concatenate([x, np.zeros((delay, channels), dtype=x.dtype)])
        out = []
        for start in range(0, len(padded), _OS_BLOCK):
            high = up.process(padded[start:start + _OS_BLOCK].astype(np.float64)).astype(np.float32)
            for op in ops:
                if isinstance(op, Saturation):
                    high = np.tanh(high * np.float32(10 ** (op.drive_db / 20.0)))
                elif isinstance(op, PowerSaturation):
                    high = op.apply(high)
                elif isinstance(op, _TubeState):
                    high = op.process(high)
                else:
                    high = op(np.ascontiguousarray(high.T), rate * factor, reset=start == 0).T
            out.append(down.process(high.astype(np.float64)))
        return np.concatenate(out)[delay:delay + frames].astype(np.float32)
    return run


NAM_TARGET_LOUDNESS_DB = -18.0    # come la normalizzazione del plugin NAM


def _nam_normalization_db(path: str) -> float:
    """Guadagno che porta il profilo alla loudness di riferimento, dichiarata
    nel file o misurata (cosi' profili diversi suonano a volume simile)."""
    from .nam import NamError, load_nam, reference_loudness
    try:
        loudness = reference_loudness(load_nam(path))
    except NamError:
        return 0.0
    if loudness is None:
        return 0.0
    return float(max(-24.0, min(24.0, NAM_TARGET_LOUDNESS_DB - loudness)))


def _nam_stage(x: np.ndarray, rate: int, path: str) -> np.ndarray:
    """Il segnale (mono: media dei canali) attraverso il profilo NAM, alla
    sua frequenza di campionamento; uscita uguale sui due canali. Senza un
    profilo valido il suono passa invariato."""
    from .nam import NamError, load_nam, process
    try:
        model = load_nam(path)
    except NamError as e:
        logging.getLogger(__name__).warning("Profilo NAM non usato (%s): %s", path, e)
        return x
    mono = x.mean(axis=1)
    if model.sample_rate != rate:
        y = process(model, _fft_resample(mono, rate, model.sample_rate))
        y = _fft_resample(y, model.sample_rate, rate)[:len(mono)]
        y = np.concatenate([y, np.zeros(len(mono) - len(y))])
    else:
        y = process(model, mono)
    return np.repeat(y[:, None], x.shape[1], axis=1).astype(np.float32)


def _distortion_stage(stages: list):
    """Le saturazioni, sovracampionate."""
    return _oversampled(stages)


# ---------------------------------------------------------------------------
# Tone stack: il circuito passivo Bassi/Medi/Alti degli amplificatori Fender
# e Marshall (lo stesso schema, con componenti diversi), dal modello
# analitico di D. Yeh e J. O. Smith, "Discretization of the '59 Fender
# Bassman Tone Stack" (DAFx 2006). Le tre manopole interagiscono come nel
# circuito vero (alzare gli alti tocca anche i medi, i medi a 0 scavano). Il
# filtro (3° ordine) si discretizza con la trasformata bilineare e si usa
# come risposta all'impulso.
# ---------------------------------------------------------------------------

#            R1 (alti)  R2 (bassi) R3 (medi)  R4      C1        C2      C3
TONE_STACKS = {
    "fender": (250e3, 1e6, 25e3, 56e3, 250e-12, 20e-9, 20e-9),
    "marshall": (220e3, 1e6, 22e3, 33e3, 470e-12, 22e-9, 22e-9),
}
_TONE_STACK_IR = 4096
_tone_cache: Dict[tuple, np.ndarray] = {}


def _tone_stack_analog(t: float, m: float, l: float, R1, R2, R3, R4, C1, C2, C3):
    """Coefficienti di H(s) = (b1 s + b2 s^2 + b3 s^3) / (1 + a1 s + a2 s^2 + a3 s^3)."""
    b1 = t * C1 * R1 + m * C3 * R3 + l * (C1 * R2 + C2 * R2) + (C1 * R3 + C2 * R3)
    b2 = (t * (C1 * C2 * R1 * R4 + C1 * C3 * R1 * R4) - m * m * (C1 * C3 * R3 ** 2 + C2 * C3 * R3 ** 2)
          + m * (C1 * C3 * R1 * R3 + C1 * C3 * R3 ** 2 + C2 * C3 * R3 ** 2)
          + l * (C1 * C2 * R1 * R2 + C1 * C2 * R2 * R4 + C1 * C3 * R2 * R4)
          + l * m * (C1 * C3 * R2 * R3 + C2 * C3 * R2 * R3)
          + (C1 * C2 * R1 * R3 + C1 * C2 * R3 * R4 + C1 * C3 * R3 * R4))
    b3 = (l * m * (C1 * C2 * C3 * R1 * R2 * R3 + C1 * C2 * C3 * R2 * R3 * R4)
          - m * m * (C1 * C2 * C3 * R1 * R3 ** 2 + C1 * C2 * C3 * R3 ** 2 * R4)
          + m * (C1 * C2 * C3 * R1 * R3 ** 2 + C1 * C2 * C3 * R3 ** 2 * R4)
          + t * C1 * C2 * C3 * R1 * R3 * R4 - t * m * C1 * C2 * C3 * R1 * R3 * R4
          + t * l * C1 * C2 * C3 * R1 * R2 * R4)
    a1 = (C1 * R1 + C1 * R3 + C2 * R3 + C2 * R4 + C3 * R4) + m * C3 * R3 + l * (C1 * R2 + C2 * R2)
    a2 = (m * (C1 * C3 * R1 * R3 - C2 * C3 * R3 * R4 + C1 * C3 * R3 ** 2 + C2 * C3 * R3 ** 2)
          + l * m * (C1 * C3 * R2 * R3 + C2 * C3 * R2 * R3) - m * m * (C1 * C3 * R3 ** 2 + C2 * C3 * R3 ** 2)
          + l * (C1 * C2 * R2 * R4 + C1 * C2 * R1 * R2 + C1 * C3 * R2 * R4 + C2 * C3 * R2 * R4)
          + (C1 * C2 * R1 * R4 + C1 * C3 * R1 * R4 + C1 * C2 * R3 * R4 + C1 * C2 * R1 * R3
             + C1 * C3 * R3 * R4 + C2 * C3 * R3 * R4))
    a3 = (l * m * (C1 * C2 * C3 * R1 * R2 * R3 + C1 * C2 * C3 * R2 * R3 * R4)
          - m * m * (C1 * C2 * C3 * R1 * R3 ** 2 + C1 * C2 * C3 * R3 ** 2 * R4)
          + m * (C1 * C2 * C3 * R3 ** 2 * R4 + C1 * C2 * C3 * R1 * R3 ** 2 - C1 * C2 * C3 * R1 * R3 * R4)
          + l * C1 * C2 * C3 * R1 * R2 * R4 + C1 * C2 * C3 * R1 * R3 * R4)
    return [0.0, b1, b2, b3], [1.0, a1, a2, a3]


def _bilinear(b: list, a: list, rate: float):
    """Da H(s) (coefficienti in potenze crescenti di s) a H(z) (in potenze
    crescenti di z^-1), con s = 2 fs (1 - z^-1) / (1 + z^-1)."""
    order = len(a) - 1
    k = 2.0 * rate
    num = np.zeros(order + 1)
    den = np.zeros(order + 1)
    for i in range(order + 1):
        term = np.array([1.0])
        for _ in range(i):
            term = np.convolve(term, [1.0, -1.0])
        for _ in range(order - i):
            term = np.convolve(term, [1.0, 1.0])
        num += b[i] * k ** i * term
        den += a[i] * k ** i * term
    return num / den[0], den / den[0]


def _iir_impulse(num: np.ndarray, den: np.ndarray, length: int) -> np.ndarray:
    y = np.zeros(length)
    x = np.zeros(length)
    x[0] = 1.0
    for n in range(length):
        acc = 0.0
        for i in range(len(num)):
            if n - i >= 0:
                acc += num[i] * x[n - i]
        for i in range(1, len(den)):
            if n - i >= 0:
                acc -= den[i] * y[n - i]
        y[n] = acc
    return y


def _tone_knob(value: float) -> float:
    return min(1.0, max(0.0, value / 10.0))


def tone_stack_ir(stack: str, bass: float, mid: float, treble: float, rate: int) -> np.ndarray:
    """Risposta all'impulso del tone stack con le manopole 0-10. Il livello
    e' normalizzato una volta per tipo di circuito (manopole a meta' = 0 dB
    in media nella banda utile), non per posizione: girare le manopole
    cambia il volume come su un amplificatore vero."""
    key = (stack, bass, mid, treble, rate)
    if key in _tone_cache:
        return _tone_cache[key]
    values = TONE_STACKS[stack]
    # il potenziometro dei bassi e' logaritmico
    l = np.exp((_tone_knob(bass) - 1.0) * 3.4) if bass > 0 else 0.0
    num, den = _bilinear(*_tone_stack_analog(_tone_knob(treble), _tone_knob(mid), l, *values), rate)
    ir = _iir_impulse(num, den, _TONE_STACK_IR)
    ref_key = (stack, rate)
    if ref_key not in _tone_cache:
        l_ref = np.exp((0.5 - 1.0) * 3.4)
        ref = _iir_impulse(*_bilinear(*_tone_stack_analog(0.5, 0.5, l_ref, *values), rate), _TONE_STACK_IR)
        f = np.fft.rfftfreq(_TONE_STACK_IR, 1.0 / rate)
        band = (f >= 100) & (f <= 5000)
        _tone_cache[ref_key] = np.array([np.mean(np.abs(np.fft.rfft(ref))[band])])
    ir = (ir / _tone_cache[ref_key][0]).astype(np.float32)
    _tone_cache[key] = ir
    return ir


# modello -> quanto si sposta il punto di lavoro delle valvole sui colpi forti
# (vedi TubeStage): piu' marcato nei modelli "vintage" che respirano col tocco.
_AMP_BIAS_SHIFT = {"pulito": 0.5, "crunch": 1.0, "british": 0.8, "high_gain": 0.8}

# modello -> taglio dei condensatori di accoppiamento dopo ogni stadio (Hz):
# tolgono il sub-basso che la distorsione asimmetrica genera come differenza
# fra le note di un accordo (il "brontolio" sotto un power chord). I Marshall
# si combinano con la "risonanza" qui sotto.
_AMP_COUPLING_HZ = {"pulito": 30.0, "crunch": 60.0, "british": 50.0, "high_gain": 50.0}

# modello -> (frequenza Hz, dB) della "risonanza" finale: restituisce la zona
# delle fondamentali basse (il Mi basso della chitarra e' a 82 Hz) tolta
# dall'accoppiamento, lasciando fuori il sub-basso. Tarata perche' il
# bilanciamento dei bassi resti quello di prima.
_AMP_RESONANCE = {"pulito": (90.0, 0.0), "crunch": (90.0, 3.0), "british": (90.0, 6.0), "high_gain": (90.0, 6.0)}

# modello -> tone stack
_AMP_TONE_STACK = {"pulito": "fender", "crunch": "fender", "british": "marshall", "high_gain": "marshall"}

_AMP_VOICING = {
    # modello -> (passa-alto prima della saturazione Hz, (frequenza, dB) spinta dei medi, guadagno in piu', stadi)
    "pulito": (50, (800, 0), -12, 1),
    "crunch": (80, (800, 3), 0, 1),
    "british": (90, (1200, 5), 4, 2),
    "high_gain": (110, (1000, 6), 11, 2),
}

# Saturazione dipendente dalla frequenza, come in uno stadio a valvole: il
# condensatore di catodo da' meno guadagno ai bassi, che quindi saturano
# meno (suono "stretto", meno fango sugli accordi bassi), e la capacita'
# della valvola (effetto Miller) addolcisce gli acuti che entrano nello
# stadio. Si fa con pre-enfasi e de-enfasi: prima di ogni saturazione i
# bassi si abbassano di 'pre' dB, dopo se ne restituiscono 'de' (un po'
# meno fra uno stadio e l'altro); dopo l'ultimo stadio se ne restituiscono
# 'finale' dB, scelti perche' il bilanciamento dei bassi resti quello di
# prima: cambia come distorcono, non quanti bassi ci sono.
# modello -> (frequenza dello scaffale dei bassi Hz, pre dB, de dB, finale dB, taglio Miller Hz)
_AMP_STAGE_EQ = {
    "pulito": (120, 3.0, 3.0, 3.0, 12000),
    "crunch": (150, 6.0, 4.0, 5.0, 10000),
    "british": (150, 8.0, 5.0, 9.0, 9000),
    "high_gain": (200, 12.0, 8.0, 13.0, 8000),
}


def _plugin_stage(effect, mix: float):
    """Stadio di un plugin esterno (elaborato nel processo dei plugin, vedi
    core.plugins). Se il plugin non si carica o non risponde il suono passa
    invariato, e l'errore finisce nel log."""
    def stage(x, rate, effect=effect, mix=mix):
        from .plugins import PluginError, process_audio
        if not effect.plugin:
            return x
        try:
            wet = process_audio(effect.plugin, effect.plugin_params, effect.plugin_state, x, rate)
        except PluginError as e:
            logging.getLogger(__name__).warning("Plugin %s non usato: %s", effect.plugin, e)
            return x
        if mix >= 1.0:
            return wet
        return (x * (1.0 - mix) + wet * mix).astype(np.float32)
    return stage


def _plugins(effect, bpm: float = 120.0) -> list:
    """Gli stadi di un effetto: plugin di pedalboard o funzioni numpy
    (array (frame, 2) -> array), vedi apply_effect_chain."""
    pb = _pedalboard
    p = clamp_params(effect.kind, effect.params)
    kind = effect.kind
    if kind == "eq":
        return [pb.LowShelfFilter(cutoff_frequency_hz=200, gain_db=p["bassi"], q=0.707),
                pb.PeakFilter(cutoff_frequency_hz=1000, gain_db=p["medi"], q=0.8),
                pb.HighShelfFilter(cutoff_frequency_hz=4000, gain_db=p["alti"], q=0.707)]
    if kind == "compressore":
        return [pb.Compressor(threshold_db=p["soglia"], ratio=p["rapporto"],
                              attack_ms=p["attacco"], release_ms=p["rilascio"]),
                pb.Gain(gain_db=p["guadagno"])]
    if kind == "limiter":
        # Il Limiter di pedalboard alza il livello di quanto si abbassa la
        # soglia (massimizzatore) e taglia a 0 dB: 'tetto' riporta sotto.
        return [pb.Limiter(threshold_db=-p["guadagno"], release_ms=p["rilascio"]),
                pb.Gain(gain_db=p["tetto"])]
    if kind == "noise_gate":
        return [pb.NoiseGate(threshold_db=p["soglia"], ratio=p["rapporto"],
                             attack_ms=p["attacco"], release_ms=p["rilascio"])]
    if kind in ("passa_alto", "passa_basso"):
        # Filtri del primo ordine (6 dB/ottava) in cascata per la pendenza.
        cls = pb.HighpassFilter if kind == "passa_alto" else pb.LowpassFilter
        return [cls(cutoff_frequency_hz=p["frequenza"]) for _ in range(int(round(p["pendenza"] / 6)))]
    if kind == "nam":
        stages = [pb.Gain(gain_db=p["ingresso"]), lambda x, rate, path=effect.nam: _nam_stage(x, rate, path)]
        if uses_ir_file(effect) and load_ir_file(effect.ir, 48000) is not None:
            stages.append(lambda x, rate, path=effect.ir: _convolve(x, load_ir_file(path, rate)))
        stages.append(pb.Gain(gain_db=p["livello"] + _nam_normalization_db(effect.nam)))
        return stages
    if kind == "plugin":
        return [_plugin_stage(effect, p["mix"] / 100.0), pb.Gain(gain_db=p["livello"])]
    if kind == "distorsione":
        # Tono: filtro passa-basso dopo la saturazione, da 1 a 12 kHz.
        saturate = _distortion_stage([Saturation(p["spinta"])])
        after = [pb.LowpassFilter(cutoff_frequency_hz=1000.0 * 12.0 ** (p["tono"] / 100.0)),
                 pb.Gain(gain_db=p["livello"])]
        mix = p["mix"] / 100.0
        if mix >= 1.0:
            return [saturate] + after

        def parallel(x, rate, saturate=saturate, after=after, mix=mix):
            wet = pb.Pedalboard(after)(np.ascontiguousarray(saturate(x, rate).T), rate, reset=True).T
            return (x * (1.0 - mix) + wet * mix).astype(np.float32)
        return [parallel]
    if kind == "amplificatore":
        model = choice_key(effect_params(kind)[0], p["modello"])
        cabinet = choice_key(effect_params(kind)[1], p["cassa"])
        tight, (mid_hz, mid_db), extra, stages = _AMP_VOICING[model]
        drive = max(0.0, p["guadagno"] + extra)
        # I filtri lineari prima della saturazione girano alla frequenza
        # normale; a 4x solo le saturazioni (e il filtro fra i due stadi).
        shelf_hz, pre_db, de_db, final_db, miller_hz = _AMP_STAGE_EQ[model]
        bias_amount = _AMP_BIAS_SHIFT[model]
        coupling = [pb.HighpassFilter(cutoff_frequency_hz=_AMP_COUPLING_HZ[model]),
                    pb.HighpassFilter(cutoff_frequency_hz=_AMP_COUPLING_HZ[model])]
        # pre-enfasi del primo stadio (lineare: alla frequenza normale)
        stages_list = [pb.HighpassFilter(cutoff_frequency_hz=tight),
                       pb.PeakFilter(cutoff_frequency_hz=mid_hz, gain_db=mid_db, q=0.7),
                       pb.LowShelfFilter(cutoff_frequency_hz=shelf_hz, gain_db=-pre_db, q=0.707),
                       pb.LowpassFilter(cutoff_frequency_hz=miller_hz)]
        if stages == 2:
            # fra i due stadi: de-enfasi del primo e pre-enfasi del secondo in
            # un solo filtro, piu' il taglio degli acuti dell'accoppiamento
            saturation = [TubeStage(drive * 0.6, bias_amount), *coupling,
                          pb.LowpassFilter(cutoff_frequency_hz=7000),
                          pb.LowShelfFilter(cutoff_frequency_hz=shelf_hz, gain_db=de_db - pre_db, q=0.707),
                          TubeStage(drive * 0.5, bias_amount)]
        else:
            saturation = [TubeStage(drive, bias_amount)]
        stages_list.append(_distortion_stage(saturation))
        # accoppiamento dopo l'ultimo stadio (lineare: alla frequenza normale)
        stages_list += [pb.HighpassFilter(cutoff_frequency_hz=_AMP_COUPLING_HZ[model]),
                        pb.HighpassFilter(cutoff_frequency_hz=_AMP_COUPLING_HZ[model])]
        # de-enfasi dopo l'ultimo stadio, e la "risonanza" che restituisce la
        # zona delle fondamentali basse tolta dall'accoppiamento
        stages_list.append(pb.LowShelfFilter(cutoff_frequency_hz=shelf_hz, gain_db=final_db, q=0.707))
        resonance_hz, resonance_db = _AMP_RESONANCE[model]
        if resonance_db:
            stages_list.append(pb.PeakFilter(cutoff_frequency_hz=resonance_hz, gain_db=resonance_db, q=0.9))
        # tone stack del circuito del modello (Fender o Marshall)
        stack = _AMP_TONE_STACK[model]
        tone = (stack, p["bassi"], p["medi"], p["alti"])
        stages_list.append(lambda x, rate, tone=tone: _convolve(x, tone_stack_ir(*tone, rate)))
        # stadio di potenza: "sag" (l'alimentazione che cede sui colpi forti:
        # una compressione lenta e morbida) e saturazione delle valvole finali
        power = p["potenza"] / 100.0
        if power > 0:
            stages_list.append(pb.Compressor(threshold_db=-12.0, ratio=1.0 + 1.5 * power,
                                             attack_ms=15.0, release_ms=180.0))
            stages_list.append(_oversampled([PowerSaturation(18.0 * power)], factor=2))
            # la saturazione asimmetrica crea una componente continua: la
            # toglie, come il trasformatore d'uscita di un amplificatore vero
            stages_list += [pb.HighpassFilter(cutoff_frequency_hz=10), pb.HighpassFilter(cutoff_frequency_hz=10)]
        # presenza: gli acuti controllati dalla controreazione del finale
        stages_list.append(pb.HighShelfFilter(cutoff_frequency_hz=3500, gain_db=(p["presenza"] - 5.0) * 1.2,
                                              q=0.707))
        if cabinet == "file":
            if load_ir_file(effect.ir, 48000) is not None:
                stages_list.append(lambda x, rate, path=effect.ir:
                                   _convolve(x, load_ir_file(path, rate)))
            else:
                # file mancante: si ripiega sulla cassa interna piu' versatile
                logging.getLogger(__name__).warning("File IR non disponibile (%s): cassa Combo 1x12", effect.ir)
                cabinet = "combo_1x12"
        if cabinet in _CABINET_CURVES:
            ir = cabinet_ir(cabinet, 48000)
            stages_list.append(lambda x, rate, ir=ir, cabinet=cabinet:
                               _convolve(x, ir if rate == 48000 else cabinet_ir(cabinet, rate)))
        stages_list.append(pb.Gain(gain_db=p["livello"]))
        return stages_list
    if kind == "delay":
        return [pb.Delay(delay_seconds=delay_seconds(p, bpm), feedback=p["ripetizioni"] / 100.0,
                         mix=p["mix"] / 100.0)]
    if kind == "riverbero":
        wet = p["mix"] / 100.0
        return [pb.Reverb(room_size=p["stanza"] / 100.0, damping=p["smorzamento"] / 100.0,
                          width=p["ampiezza"] / 100.0, wet_level=wet, dry_level=1.0 - wet * 0.5)]
    if kind == "chorus":
        return [pb.Chorus(rate_hz=p["velocita"], depth=p["profondita"] / 100.0, centre_delay_ms=7.0,
                          feedback=0.0, mix=p["mix"] / 100.0)]
    if kind == "phaser":
        return [pb.Phaser(rate_hz=p["velocita"], depth=p["profondita"] / 100.0, centre_frequency_hz=1300,
                          feedback=p["ritorno"] / 100.0, mix=p["mix"] / 100.0)]
    return []


def apply_effect_chain(samples: np.ndarray, samplerate: int, effects,
                       with_tail: bool = True, bpm: float = 120.0) -> np.ndarray:
    """La traccia 'samples' (float32, forma (frame, 2)) passata attraverso
    gli effetti accesi, nell'ordine. Con 'with_tail' si aggiunge in fondo il
    silenzio che serve a far finire le code di delay e riverbero (poi il
    silenzio vero in eccesso viene tolto). Senza pedalboard, o senza effetti
    accesi, torna 'samples' invariato."""
    chain = active_effects(effects)
    if not chain or _pedalboard is None or len(samples) == 0:
        return samples
    x = np.asarray(samples, dtype=np.float32)
    tail = int(tail_seconds(chain, bpm) * samplerate) if with_tail else 0
    if tail:
        x = np.concatenate([x, np.zeros((tail, x.shape[1]), dtype=np.float32)])
    # I plugin consecutivi di pedalboard girano insieme; le funzioni numpy
    # (la cassa dell'amplificatore) in mezzo, nell'ordine della catena.
    y = x
    pending = []

    def flush(y):
        if not pending:
            return y
        board = _pedalboard.Pedalboard(list(pending))
        pending.clear()
        return board(np.ascontiguousarray(y.T), samplerate, reset=True).T.astype(np.float32)
    for stage in (st for e in chain for st in _plugins(e, bpm)):
        if callable(stage) and not isinstance(stage, _pedalboard.Plugin):
            y = stage(flush(y), samplerate)
        else:
            pending.append(stage)
    y = flush(y)
    if tail:
        loud = np.nonzero(np.abs(y[len(samples):]).max(axis=1) > 1e-5)[0]
        y = y[:len(samples) + (int(loud[-1]) + 1 if len(loud) else 0)]
    return np.ascontiguousarray(y)
