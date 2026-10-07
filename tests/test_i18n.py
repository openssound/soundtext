"""
Test delle lingue dell'interfaccia (core.i18n, locales/*.json): cataloghi
completi e coerenti con i testi del codice, segnaposto conservati, scelta
della lingua, guida tradotta e finestra principale nelle quattro lingue.

Esecuzione:
    python3 -m pytest tests/test_i18n.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import json
import os
import string
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core import i18n
from core.i18n import LANGUAGES, tr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANSLATED = [code for code in LANGUAGES if code != i18n.SOURCE_LANGUAGE]


@pytest.fixture(autouse=True)
def _back_to_italian():
    yield
    i18n.set_language("it")


def _fields(text):
    return sorted((name, spec, conv) for _lit, name, spec, conv in string.Formatter().parse(text) if name is not None)


def _catalog(code):
    with open(os.path.join(ROOT, "locales", f"{code}.json"), encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize("code", TRANSLATED)
def test_catalog_covers_every_text_of_the_program(code):
    sys.path.insert(0, os.path.join(ROOT, "locales"))
    from extract import source_strings
    catalog = _catalog(code)
    missing = [s for s in source_strings() if not catalog.get(s)]
    assert not missing, f"{len(missing)} testi senza traduzione in {code}: {missing[:5]}"


@pytest.mark.parametrize("code", TRANSLATED)
def test_translations_keep_placeholders_and_edges(code):
    for source, translated in _catalog(code).items():
        assert _fields(source) == _fields(translated), (code, source)
        assert source.startswith((" ", "\n")) == translated.startswith((" ", "\n")), (code, source)
        assert source.endswith((" ", "\n")) == translated.endswith((" ", "\n")), (code, source)
        assert source.count("<b>") == translated.count("<b>"), (code, source)
        if source.startswith("&"):
            assert "&" in translated, (code, source)


def test_tr_translates_formats_and_falls_back():
    i18n.set_language("en")
    assert tr("Esporta MIDI...") == "Export MIDI..."
    assert tr("MIDI esportato: {path}", path="a.mid") == "MIDI exported: a.mid"
    assert tr("Testo che non e' nel catalogo {x}", x=1) == "Testo che non e' nel catalogo 1"
    i18n.set_language("it")
    assert tr("Esporta MIDI...") == "Esporta MIDI..."


def test_language_choice(monkeypatch):
    from core import settings
    monkeypatch.delenv("SOUNDTEXT_LANGUAGE", raising=False)
    monkeypatch.setenv("LANGUAGE", "")
    monkeypatch.setenv("LC_ALL", "")
    monkeypatch.setenv("LC_MESSAGES", "")
    monkeypatch.setenv("LANG", "fr_FR.UTF-8")
    old = settings.get_language()
    try:
        settings._cache.pop("language", None)
        assert i18n.configured_language() == "fr"               # dal sistema
        monkeypatch.setenv("LANG", "de_DE.UTF-8")
        monkeypatch.setattr(i18n.locale, "getlocale", lambda: ("de_DE", "UTF-8"))
        assert i18n.configured_language() == "en"               # lingua non disponibile: inglese
        settings.set_language("es")
        assert i18n.configured_language() == "es"               # scelta in Opzioni
        monkeypatch.setenv("SOUNDTEXT_LANGUAGE", "it")
        assert i18n.configured_language() == "it"               # variabile d'ambiente
    finally:
        if old is None:
            settings._cache.pop("language", None)
        else:
            settings.set_language(old)


@pytest.mark.parametrize("code", TRANSLATED)
def test_help_and_readme_exist_in_every_language(code):
    help_path = os.path.join(ROOT, "docs", "HELP.md")
    i18n.set_language(code)
    assert i18n.localized_doc(help_path) == os.path.join(ROOT, "docs", f"HELP.{code}.md")
    assert os.path.exists(os.path.join(ROOT, f"README.{code}.md"))
    i18n.set_language("it")
    assert i18n.localized_doc(help_path) == help_path


@pytest.mark.parametrize("code", TRANSLATED)
def test_translated_help_has_same_sections(code):
    """Stessi capitoli (numeri delle intestazioni) e stessi blocchi di codice
    dell'originale: un capitolo aggiunto a HELP.md e non tradotto fa
    fallire il test invece di mancare in silenzio nella guida tradotta."""
    import re

    def outline(name):
        with open(os.path.join(ROOT, "docs", name), encoding="utf-8") as f:
            text = f.read()
        sections = re.findall(r"^#{1,3} ([0-9]+[a-z]*(?:\.[0-9]+)?)", text, re.M)
        return sections, len(re.findall(r"^```", text, re.M))

    assert outline(f"HELP.{code}.md") == outline("HELP.md")


@pytest.mark.parametrize("code", LANGUAGES)
def test_main_window_in_every_language(code):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    i18n.set_language(code)
    from gui.main_window import MainWindow
    w = MainWindow()
    titles = [a.text() for a in w.menuBar().actions()]
    assert titles[0] == tr("&Progetto")
    w.project.add_track("Chitarra", "Guitar", "4: E A B E")
    w.refresh_mixer()
    w.open_effects_panel("Chitarra")
    w.effects_panel.add_effect("eq")
    card = w.effects_panel.cards[0]
    card.preset_combo.setCurrentIndex(card.preset_combo.findData("Più presenza"))
    effect = w.project.get_track("Chitarra").effects[0]
    assert effect.preset == "Più presenza" and effect.params["medi"] == 3        # il dato resta italiano
    assert card.preset_combo.currentText() == tr("Più presenza")
    w.effects_panel.close_panel()
