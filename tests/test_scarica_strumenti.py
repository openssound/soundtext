"""
Test di scarica_strumenti.py (senza rete): elenco dei gruppi, archivi
GitHub, estrazione sicura, mappa GM della batteria, copia dei plugin VST3 e
cartelle della libreria uguali a quelle in cui la cerca core.sfz_engine.

Esecuzione:
    python3 -m pytest tests/test_scarica_strumenti.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import io
import os
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest

import scarica_strumenti as ss


def test_groups_and_extra_groups_are_consistent():
    nomi = [v[0] for v in ss.GRUPPI + ss.EXTRA]
    assert len(nomi) == len(set(nomi))
    for gruppo, _spazio, _membri in ss.EXTRA_GRUPPI:
        assert all(ss.trova(m) is not None for m in ss.trova_extra(gruppo))
    assert ss.trova("marimba")[2].endswith(".git") and ss.trova("nessuno") is None
    assert ss.trova_extra("extra_niente") is None


def test_github_archive_url():
    assert ss.archivio_github("https://github.com/sfzinstruments/Terkelsen.Marimba.git") == \
        "https://github.com/sfzinstruments/Terkelsen.Marimba/archive/HEAD.zip"


def test_extracts_zip_and_tar_but_not_paths_outside(tmp_path):
    z = tmp_path / "a.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("strumento/x.sfz", "<region> sample=*sine")
    ss.estrai(z, tmp_path / "zip")
    assert (tmp_path / "zip" / "strumento" / "x.sfz").exists()
    t = tmp_path / "a.tar.xz"
    with tarfile.open(t, "w:xz") as f:
        info = tarfile.TarInfo("y.sfz")
        info.size = 3
        f.addfile(info, io.BytesIO(b"abc"))
    ss.estrai(t, tmp_path / "tar")
    assert (tmp_path / "tar" / "y.sfz").read_bytes() == b"abc"
    cattivo = tmp_path / "cattivo.zip"
    with zipfile.ZipFile(cattivo, "w") as f:
        f.writestr("../fuori.sfz", "x")
    with pytest.raises(ss.Errore):
        ss.estrai(cattivo, tmp_path / "c")
    assert not (tmp_path / "fuori.sfz").exists()
    with pytest.raises(ss.Errore):
        ss.estrai(tmp_path / "x.rar", tmp_path / "r")


def test_drum_kit_gets_a_gm_copy(tmp_path):
    kit = tmp_path / "MuldjordKit"
    kit.mkdir()
    (kit / "kit.sfz").write_text("<region> key=48 sample=k.flac\n<region> key=50 sample=s.flac lokey=10\n")
    ss.crea_sfz_gm(tmp_path)
    gm = (kit / "kit-GM.sfz").read_text()
    assert "key=36" in gm and "key=38" in gm and "lokey=10" in gm
    ss.crea_sfz_gm(tmp_path)                                   # la copia GM non diventa sorgente
    assert sorted(p.name for p in kit.iterdir()) == ["kit-GM.sfz", "kit.sfz"]


def test_copies_every_vst3_bundle_once(tmp_path):
    src = tmp_path / "pacchetto"
    (src / "Synth.vst3" / "Contents" / "Inner.vst3").mkdir(parents=True)
    (src / "Synth.vst3" / "Contents" / "plugin.so").write_text("x")
    (src / "altro" / "Effetto.vst3").mkdir(parents=True)
    (src / "Synth.clap").write_text("x")
    dest = tmp_path / "VST3"
    ss.copia_vst3(src, dest)
    assert sorted(p.name for p in dest.iterdir()) == ["Effetto.vst3", "Synth.vst3"]
    assert (dest / "Synth.vst3" / "Contents" / "plugin.so").exists()
    ss.copia_vst3(src, dest)                                    # di nuovo: sostituisce
    (tmp_path / "vuoto").mkdir()
    with pytest.raises(ss.Errore):
        ss.copia_vst3(tmp_path / "vuoto", dest)


@pytest.mark.parametrize("platform, sistema", [("linux", "linux"), ("win32", "windows"), ("darwin", "macos")])
def test_library_location_matches_the_sfz_engine(monkeypatch, tmp_path, platform, sistema):
    from core import sfz_engine
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData" / "Local"))
    monkeypatch.setattr(sfz_engine.sys, "platform", platform)
    monkeypatch.setattr(ss, "SISTEMA", sistema)
    assert Path(sfz_engine.user_lib_dir()) == ss.user_lib_dir()


def test_list_and_unknown_group(capsys):
    assert ss.main([]) == 0
    out = capsys.readouterr().out
    assert "marimba" in out and "libreria" in out and "extra_batterie" in out
    assert ss.main(["nessun-gruppo"]) == 1
    assert "Gruppo sconosciuto" in capsys.readouterr().out


def test_menu_by_number_or_name_and_empty_exits(monkeypatch, capsys):
    nomi = [nome for nome, _desc in ss.voci_elenco()]
    assert nomi[-8:] == ["vst3", "host", "lv2", "lilv", "libreria", "strumenti-compilazione", "nam-plugin",
                         "tutto"] and len(nomi) == len(set(nomi))
    risposte = iter(["1 libreria", "boh", f"{len(nomi)},piano", ""])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(risposte))
    assert ss.menu() == [nomi[0], "libreria"]
    assert ss.menu() == ["tutto", "piano"]                     # "boh" scartato, si richiede
    assert "Scelta non valida: boh" in capsys.readouterr().out
    assert ss.menu() == []


def test_no_arguments_without_terminal_only_lists(monkeypatch, capsys):
    monkeypatch.setattr(ss.sys.stdin, "isatty", lambda: False, raising=False)
    monkeypatch.setattr("builtins.input", lambda _prompt: pytest.fail("menu fuori da un terminale"))
    assert ss.main([]) == 0
    assert "Gruppi disponibili" in capsys.readouterr().out


def test_gm_bank_description_says_it_is_incomplete():
    desc = ss.trova("gm-bank")[1]
    assert "INCOMPLETO" in desc and "segnaposto" in desc and "tutti i 128" not in desc


def test_placeholder_sfz_is_recognised(tmp_path):
    from core.sfz_engine import placeholder_only
    finto = tmp_path / "023-Harmonica.sfz"
    finto.write_text("//dummy\n<region> sample=*sine\n")
    vero = tmp_path / "001-Piano.sfz"
    vero.write_text("<region> sample=Piano/A0 v1.flac\n// sample=*sine\n")
    misto = tmp_path / "misto.sfz"
    misto.write_text("<region> sample=*saw\n<region> sample=x.wav\n")
    banco = tmp_path / "banco.sfz"
    banco.write_text('#include "023-Harmonica.sfz"\n#include "001-Piano.sfz"\n')
    solo_finti = tmp_path / "solo_finti.sfz"
    solo_finti.write_text('/* sample=a.wav */\n#include "023-Harmonica.sfz"\n')
    vuoto = tmp_path / "vuoto.sfz"
    vuoto.write_text("<control> default_path=x/\n")
    assert placeholder_only(str(finto)) and placeholder_only(str(solo_finti))
    assert not placeholder_only(str(vero)) and not placeholder_only(str(misto))
    assert not placeholder_only(str(banco)) and not placeholder_only(str(vuoto))
    assert not placeholder_only(str(tmp_path / "manca.sfz"))


@pytest.mark.parametrize("sistema, macchina, chiave", [
    ("linux", "x86_64", "linux-x86_64"), ("linux", "aarch64", "linux-aarch64"),
    ("windows", "AMD64", "windows"), ("macos", "arm64", "macos")])
def test_vst3_plugins_for_every_system(monkeypatch, sistema, macchina, chiave):
    monkeypatch.setattr(ss, "SISTEMA", sistema)
    monkeypatch.setattr(ss.platform, "machine", lambda: macchina)
    assert ss.chiave_sistema() == chiave
    nomi = {nome for nome, _d, _r, _rel, modelli in ss.PLUGIN_VST3 if chiave in modelli}
    # LSP Plugins esiste solo per Linux; su Linux ARM Dexed, Airwindows e OB-Xf non pubblicano build;
    # Wolf Shaper su Linux e' fra gli LV2 e i plugin Chow non hanno build per Linux
    attesi = {"linux-x86_64": {"Dexed", "Airwindows Consolidated", "Dragonfly Reverb", "LSP Plugins", "OB-Xf"},
              "linux-aarch64": {"Dragonfly Reverb", "LSP Plugins"}}.get(
                  chiave, {"Dexed", "Airwindows Consolidated", "Dragonfly Reverb", "OB-Xf", "Wolf Shaper",
                           "ChowTapeModel", "ChowCentaur", "ChowMatrix"})
    assert nomi == attesi


def test_vst3_install_goes_on_when_one_plugin_fails(monkeypatch, tmp_path):
    """Un plugin che non si scarica non ferma gli altri, ed e' segnalato alla fine."""
    monkeypatch.setattr(ss, "SISTEMA", "linux")
    monkeypatch.setattr(ss.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(ss, "user_vst3_dir", lambda: tmp_path / "vst3")

    def asset(repo, _release, _modello):
        if "dexed" in repo:
            raise ss.Errore("rete assente")
        return f"https://example.invalid/{repo.split('/')[1]}.zip"

    def scarica(_url, file):
        with zipfile.ZipFile(file, "w") as f:
            f.writestr(f"{file.stem}.vst3/Contents/x86_64-linux/{file.stem}.so", "x")

    monkeypatch.setattr(ss, "asset_github", asset)
    monkeypatch.setattr(ss, "scarica_file", scarica)
    assert ss.installa_plugin_vst3() == ["Dexed"]
    assert sorted(p.name for p in (tmp_path / "vst3").iterdir()) == \
        ["OB-Xf.vst3", "airwin2rack.vst3", "dragonfly-reverb.vst3", "lsp-plugins.vst3"]
    with pytest.raises(ss.Errore, match="Dexed"):
        ss.installa_vst3()


@pytest.mark.skipif(sys.platform == "win32", reason="permessi Unix")
def test_zip_keeps_executable_permissions(tmp_path):
    z = tmp_path / "p.zip"
    with zipfile.ZipFile(z, "w") as f:
        info = zipfile.ZipInfo("p.vst3/Contents/MacOS/p")
        info.external_attr = 0o755 << 16
        f.writestr(info, "x")
    ss.estrai(z, tmp_path / "out")
    assert os.access(tmp_path / "out" / "p.vst3" / "Contents" / "MacOS" / "p", os.X_OK)
