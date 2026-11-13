"""
Raccoglie i testi da tradurre (vedi core.i18n): il primo argomento di ogni
tr("...") in core/ e gui/ (quelli di st_language ripiegano sui cataloghi
della libreria), quelli di SoundText Mobile (mobile/: t("...") nel
JavaScript, data-i18n, aria-label, title e placeholder nella pagina,
tr("...") in engine.py), piu' i nomi che l'interfaccia prende dai dati
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
import html.parser
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def code_strings():
    out = set()
    for path in sorted(glob.glob(os.path.join(ROOT, "core", "*.py")) + glob.glob(os.path.join(ROOT, "gui", "*.py"))
                       + [os.path.join(ROOT, "scarica_strumenti.py"), os.path.join(ROOT, "mobile", "engine.py")]):
        tree = ast.parse(open(path, encoding="utf-8").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "tr" \
                    and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                out.add(node.args[0].value)
    return out


# t("...") nel JavaScript dell'app, anche spezzato in piu' pezzi con +
_JS_CALL = re.compile(r'\bt\(\s*((?:"(?:[^"\\\n]|\\.)*"\s*\+?\s*)+)')
_JS_PIECE = re.compile(r'"(?:[^"\\\n]|\\.)*"')
MOBILE_SCRIPTS = ("app/base.js", "app/editor.js", "app/voice.js", "app/hum.js", "app/songs-view.js", "app/create.js", "app/structure.js", "app/player.js", "app/score.js", "app/main.js")
MOBILE_PAGES = ("index.html",)
_HTML_ATTRIBUTES = ("aria-label", "title", "placeholder")


class _PageTexts(html.parser.HTMLParser):
    """I testi da tradurre di una pagina dell'app (vedi mobile/i18n.js)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = set()
        self._stack = []        # per ogni elemento aperto: raccoglie il testo?

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for name in _HTML_ATTRIBUTES:
            if attrs.get(name):
                self.out.add(attrs[name])
        if tag in ("input", "meta", "link", "br", "img"):
            return
        self._stack.append([] if "data-i18n" in attrs or tag == "title" else None)

    def handle_endtag(self, tag):
        if self._stack:
            text = self._stack.pop()
            if text is not None and "".join(text).strip():
                self.out.add("".join(text).strip())

    def handle_data(self, data):
        for text in self._stack:
            if text is not None:
                text.append(data)


def mobile_strings():
    """I testi dell'interfaccia di SoundText Mobile (mobile/i18n.js)."""
    out = set()
    for name in MOBILE_SCRIPTS:
        source = open(os.path.join(ROOT, "mobile", name), encoding="utf-8").read()
        for m in _JS_CALL.finditer(source):
            out.add("".join(json.loads(piece) for piece in _JS_PIECE.findall(m.group(1))))
    for name in MOBILE_PAGES:
        parser = _PageTexts()
        parser.feed(open(os.path.join(ROOT, "mobile", name), encoding="utf-8").read())
        out |= parser.out
    return {s for s in out if s.strip()}


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
    # profili NAM: tipi, suoni e usi dei profili consigliati (finestra di scelta del profilo)
    from core.nam import GEAR_TYPE_LABELS
    from core.nam_profiles import PROFILES, SOUNDS
    out |= set(GEAR_TYPE_LABELS.values()) | {w for words in SOUNDS.values() for w in words}
    out |= {p.use for p in PROFILES}
    # SoundFont di "Scarica e installa"
    from core.soundfont_downloads import SOUNDFONTS as SOUNDFONT_SOURCES
    out |= {s.label for s in SOUNDFONT_SOURCES} | {s.detail for s in SOUNDFONT_SOURCES}
    # strumenti SFZ di "Scarica e installa": nomi e dettagli dagli elenchi di scarica_strumenti.py
    from core.downloads import _split, load_script
    script = load_script()
    if script is not None:
        for name, desc, _url, _sub in script.GRUPPI + script.EXTRA + script.ORCHESTRA:
            out |= {text for text in _split(desc) if text}
        # e le descrizioni dei plugin nel registro del download
        out |= {desc for _name, desc, *_rest in script.PLUGIN_VST3 + script.PLUGIN_LV2}
    return out


def source_strings():
    return sorted(s for s in code_strings() | data_strings() | mobile_strings() if s.strip())


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
