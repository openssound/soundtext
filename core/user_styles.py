"""
Stili personali dei generatori (sezione "E" della proposta: imparare dai
propri brani): giri di batteria e disegni di basso, accompagnamento e riff
ricavati da un box o da un file MIDI (vedi core.style_learn) e salvati nella
cartella di configurazione, accanto agli strumenti personalizzati.

Nei generatori (core.rhythm_generate) uno stile personale si chiama
'user:<nome>'; ogni tipo ha il suo elenco, quindi lo stesso nome puo'
esistere come batteria e come basso.
"""

import json
import os
from typing import Dict, List, Optional

from .settings import CONFIG_DIR
from .i18n import tr

USER_STYLES_FILE = os.path.join(CONFIG_DIR, "generator_styles.json")

# Tipi di stile: batteria, basso, accompagnamento (polifonico), riff/melodia.
KINDS = ("drums", "bass", "comping", "riff")
KIND_LABELS = {"drums": "Batteria", "bass": "Basso", "comping": "Accompagnamento", "riff": "Riff/melodia"}
PREFIX = "user:"

_cache: Optional[Dict[str, Dict[str, dict]]] = None


def _empty() -> Dict[str, Dict[str, dict]]:
    return {kind: {} for kind in KINDS}


def _from_json(spec: dict) -> dict:
    """Le coppie (posizione, ruolo) tornano tuple e le battute di batteria
    liste di (nome, velocity): il JSON le ha salvate come liste."""
    out = dict(spec)
    if "main" in spec:   # batteria
        def slots(bar):
            return [[(name, int(vel)) for name, vel in hits] if hits else None for hits in bar]
        out["main"] = slots(spec["main"])
        out["fill"] = slots(spec["fill"]) if spec.get("fill") else None
        out["alts"] = [slots(bar) for bar in spec.get("alts", [])]
    else:                # basso, accompagnamento, riff
        def bar(events):
            return [(float(t), role) for t, role in events] if events is not None else None
        out["bar"] = bar(spec["bar"])
        out["variant"] = bar(spec.get("variant"))
        out["alts"] = [bar(b) for b in spec.get("alts", [])]
    return out


def load_user_styles(reload: bool = False) -> Dict[str, Dict[str, dict]]:
    """{tipo: {nome: specifica}}; un file illeggibile vale come vuoto."""
    global _cache
    if _cache is not None and not reload:
        return _cache
    data = _empty()
    if os.path.exists(USER_STYLES_FILE):
        try:
            with open(USER_STYLES_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for kind in KINDS:
                for name, spec in (raw.get(kind) or {}).items():
                    try:
                        data[kind][name] = _from_json(spec)
                    except (KeyError, TypeError, ValueError):
                        continue   # voce rovinata: si salta, le altre restano
        except (json.JSONDecodeError, OSError, AttributeError):
            data = _empty()
    _cache = data
    return data


def _save():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(USER_STYLES_FILE, "w", encoding="utf-8") as f:
        json.dump(load_user_styles(), f, indent=1, ensure_ascii=False)


def _check_kind(kind: str):
    if kind not in KINDS:
        raise ValueError(tr("Tipo di stile sconosciuto: '{kind}' (validi: {0})", ', '.join(KINDS), kind=kind))


def save_user_style(kind: str, name: str, spec: dict):
    _check_kind(kind)
    name = name.strip()
    if not name:
        raise ValueError(tr("Il nome dello stile non puo' essere vuoto."))
    load_user_styles()[kind][name] = spec
    _save()


def delete_user_style(kind: str, name: str):
    _check_kind(kind)
    if load_user_styles()[kind].pop(name, None) is not None:
        _save()


def rename_user_style(kind: str, old: str, new: str):
    _check_kind(kind)
    new = new.strip()
    styles = load_user_styles()[kind]
    if not new:
        raise ValueError(tr("Il nome dello stile non puo' essere vuoto."))
    if new != old and new in styles:
        raise ValueError(tr("Esiste gia' uno stile '{new}'.", new=new))
    styles[new] = styles.pop(old)
    _save()


def user_style_names(kind: str) -> List[str]:
    _check_kind(kind)
    return sorted(load_user_styles()[kind], key=str.lower)


def style_key(name: str) -> str:
    """Il nome con cui i generatori riconoscono lo stile personale."""
    return PREFIX + name


def get_user_style(kind: str, key: str) -> Optional[dict]:
    """La specifica dello stile 'user:<nome>' del tipo dato, o None."""
    if not isinstance(key, str) or not key.startswith(PREFIX):
        return None
    return load_user_styles().get(kind, {}).get(key[len(PREFIX):])
