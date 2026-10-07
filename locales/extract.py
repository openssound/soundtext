"""
Raccoglie i testi da tradurre (vedi core.i18n): il primo argomento di ogni
tr("...") in core/ e gui/, piu' i nomi che l'interfaccia prende dai dati
del motore (tipi di effetto, parametri, scelte, preset, famiglie di
strumenti, ambienti del riverbero, figure dei controlli di battuta).

Uso:
    python3 locales/extract.py            # elenca i testi mancanti in ogni catalogo
    python3 locales/extract.py --update   # aggiunge ai cataloghi le voci mancanti (vuote)
                                          # e toglie quelle che non servono piu'

Una voce vuota nel catalogo resta in italiano finche' non viene tradotta
(tests/test_i18n.py controlla che non ce ne siano).
"""

import ast
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _library_dir():
    """La cartella della libreria st_language installata (repository
    openssound/st-language): i suoi messaggi passano dalle traduzioni di
    SoundText, quindi vanno nei cataloghi dell'applicazione."""
    import st_language
    return os.path.dirname(os.path.abspath(st_language.__file__))


def code_strings():
    out = set()
    for path in sorted(glob.glob(os.path.join(ROOT, "core", "*.py")) + glob.glob(os.path.join(ROOT, "gui", "*.py"))
                       + glob.glob(os.path.join(_library_dir(), "*.py"))):
        tree = ast.parse(open(path, encoding="utf-8").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "tr" \
                    and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                out.add(node.args[0].value)
    return out


def data_strings():
    from core.effects import EFFECT_FAMILIES, EFFECT_KINDS, REVERB_ROOMS
    from core.instruments import GM_FAMILIES
    from gui.effects_panel import CUSTOM_PRESET
    out = set(EFFECT_FAMILIES) | {CUSTOM_PRESET}
    for info in EFFECT_KINDS.values():
        out.add(info["label"])
        out |= set(info["presets"])
        for p in info["params"]:
            out.add(p.label)
            out |= {label for _key, label in p.choices}
    out |= {label for label, *_rest in REVERB_ROOMS.values()}
    out |= {family for family, _start, _names in GM_FAMILIES}
    from core.metronome_sounds import SOUND_PRESETS
    out |= set(SOUND_PRESETS)
    from core.notation import _NOTE_VALUES
    out |= {name for _beats, *names in _NOTE_VALUES for name in names}
    return out


def source_strings():
    return sorted(s for s in code_strings() | data_strings() if s.strip())


def catalog_path(language):
    return os.path.join(ROOT, "locales", f"{language}.json")


def main():
    from core.i18n import LANGUAGES, SOURCE_LANGUAGE
    sources = source_strings()
    update = "--update" in sys.argv
    for language in LANGUAGES:
        if language == SOURCE_LANGUAGE:
            continue
        path = catalog_path(language)
        try:
            catalog = json.load(open(path, encoding="utf-8"))
        except (OSError, ValueError):
            catalog = {}
        missing = [s for s in sources if not catalog.get(s)]
        print(f"{language}: {len(sources)} testi, {len(missing)} da tradurre")
        if update:
            new = {s: catalog.get(s, "") for s in sources}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(new, f, ensure_ascii=False, indent=1, sort_keys=True)
                f.write("\n")


if __name__ == "__main__":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    main()
