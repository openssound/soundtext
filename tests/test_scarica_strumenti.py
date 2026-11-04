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


# ---------------------------------------------------------------- orchestra

def test_orchestra_groups_are_listed_but_not_in_tutto():
    nomi = [v[0] for v in ss.ORCHESTRA]
    assert set(nomi) == set(ss.ORCHESTRA_SFZ)
    assert all(ss.trova(n) is not None for n in nomi)
    assert not set(nomi) & {v[0] for v in ss.GRUPPI}          # "tutto" scarica solo GRUPPI
    assert not any("-KS" in f or "Keyswitch" in f for files in ss.ORCHESTRA_SFZ.values() for f in files)
    assert {n for n, _d in ss.voci_elenco()} >= set(nomi)


def test_samples_of_an_sfz_file():
    testo = ("<control>\ndefault_path=Woodwinds\\Flute\\susvib\\\n<global> volume=0\n"
             "<region> sample=LDFlute_A3.wav lokey=67 // commento sample=no.wav\n"
             "<region>\nsample=Sotto cartella\\B 3.wav\nhikey=70\n"
             "<region> sample=LDFlute_A3.wav\n")
    assert ss.campioni_sfz(testo) == ["Woodwinds/Flute/susvib/LDFlute_A3.wav",
                                      "Woodwinds/Flute/susvib/Sotto cartella/B 3.wav"]
    assert ss.campioni_sfz("<region> sample=../Campioni/a.wav", "Idiophones/Struck") == ["Idiophones/Campioni/a.wav"]
    with pytest.raises(ss.Errore):
        ss.campioni_sfz("<region> sample=../../../fuori.wav", "una")


def test_gain_goes_in_global_once():
    con = ss._con_guadagno("<control>\ndefault_path=x/\n<global>\nvolume=0\n<region> sample=a.wav", 8)
    assert con.index("<global>") < con.index("global_volume=8") < con.index("<region>")
    assert ss._con_guadagno(con, 8) == con
    senza_global = ss._con_guadagno("<control>\ndefault_path=x/\n<region> sample=a.wav", 8)
    assert senza_global.index("default_path") < senza_global.index("global_volume=8") < senza_global.index("<region>")
    assert ss.campioni_sfz(senza_global) == ["x/a.wav"]


def _fake_repo(monkeypatch, files):
    """scarica_file finto: i file del "repository" in memoria, e i download fatti."""
    fatti = []

    def scarica_file(url, dest, tentativi=3, silenzioso=False):
        percorso = url.split("/0123abc/", 1)[1]
        from urllib.parse import unquote
        fatti.append(unquote(percorso))
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(files[unquote(percorso)])
    monkeypatch.setattr(ss, "scarica_file", scarica_file)
    return fatti


def test_orchestra_group_downloads_only_its_files_and_resumes(tmp_path, monkeypatch):
    files = {"FluteStac.sfz": b"<control>\ndefault_path=Woodwinds\\Flute\\\n<global>\n<region> sample=a b.wav\n"
                              b"<region> sample=c.wav\n",
             "Woodwinds/Flute/a b.wav": b"A" * 10, "Woodwinds/Flute/c.wav": b"C" * 10,
             "Woodwinds/Oboe/non.wav": b"no"}
    fatti = _fake_repo(monkeypatch, files)
    monkeypatch.setattr(ss, "DEST", tmp_path)
    monkeypatch.setitem(ss.ORCHESTRA_SFZ, "vsco-legni", ["FluteStac.sfz"])
    voce = ("vsco-legni", "Legni (CC0, ~1 MB)", "https://esempio/0123abc", "sfz")   # senza / finale
    ss.scarica(voce)
    cartella = tmp_path / "sfz" / "vsco-legni"
    assert fatti == ["FluteStac.sfz", "Woodwinds/Flute/a b.wav", "Woodwinds/Flute/c.wav"]
    assert (cartella / "Woodwinds" / "Flute" / "a b.wav").read_bytes() == b"A" * 10
    assert (cartella / ".completo").exists() and not list(cartella.rglob("*.part"))
    assert (cartella / "FluteStac.sfz").read_text().count("global_volume=8") == 1     # VSCO: +8 dB
    # interrotto a meta': riprende solo il file che manca
    (cartella / ".completo").unlink()
    (cartella / "Woodwinds" / "Flute" / "c.wav").unlink()
    fatti.clear()
    ss.scarica(voce)
    assert fatti == ["Woodwinds/Flute/c.wav"]
    assert (cartella / "FluteStac.sfz").read_text().count("global_volume=8") == 1


def test_vcsl_files_are_not_raised(tmp_path, monkeypatch):
    files = {"Idiophones/Claves.sfz": b"<group>\n<region> sample=Claves/c.wav\n", "Idiophones/Claves/c.wav": b"x"}
    _fake_repo(monkeypatch, files)
    monkeypatch.setattr(ss, "DEST", tmp_path)
    monkeypatch.setitem(ss.ORCHESTRA_SFZ, "vcsl-percussioni", ["Idiophones/Claves.sfz"])
    ss.scarica(("vcsl-percussioni", "Percussioni", "https://esempio/0123abc/", "sfz"))
    sfz = tmp_path / "sfz" / "vcsl-percussioni" / "Idiophones" / "Claves.sfz"
    assert "global_volume" not in sfz.read_text()
    assert (sfz.parent / "Claves" / "c.wav").exists()


def test_vsco_timpani_low_drum_switches_layer_like_the_others(tmp_path):
    """VSCO usa il campione pianissimo del timpano grave fino a dinamica 80
    (gli altri fino a 60): SoundText sposta la soglia a 60/61."""
    testo = ("<control>\ndefault_path=Percussion\\Timpani\\\n<global>\nvolume=0\n<group>\n"
             "<region>\nsample=Timpani1_Hit_v1_rr1_Sum.wav\nlokey=36\nhikey=43\nlovel=0\nhivel=80\n"
             "<region>\nsample=Timpani1_Hit_v3_rr1_Sum.wav\nlokey=36\nhikey=43\nlovel=81\nhivel=127\n"
             "<region>\nsample=Timpani2_Hit_v4_rr1_Sum.wav\nlokey=44\nhikey=47\nlovel=111\nhivel=127\n"
             "<region>\nsample=Timpani5_Hit_v1_rr1_Sum.wav\nlokey=53\nhikey=60\nlovel=0\nhivel=80\n")
    (tmp_path / "Timpani.sfz").write_text(testo)
    (tmp_path / "TimpaniRolls.sfz").write_text(testo)           # lo stesso testo: qui non si tocca
    ss.ritocca_vsco(tmp_path)
    corretto = (tmp_path / "Timpani.sfz").read_text()
    regioni = corretto.split("<region>")[1:]
    assert "hivel=60" in regioni[0] and "lovel=61" in regioni[1]
    assert "lovel=111" in regioni[2] and "hivel=80" in regioni[3]     # le altre regioni restano
    assert corretto.count("global_volume=8") == 1
    rolls = (tmp_path / "TimpaniRolls.sfz").read_text()
    assert "hivel=80" in rolls.split("<region>")[1] and "global_volume=8" in rolls
    ss.ritocca_vsco(tmp_path)                                 # rifarlo non cambia niente
    assert (tmp_path / "Timpani.sfz").read_text() == corretto


def test_already_downloaded_vsco_group_gets_the_new_corrections(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "DEST", tmp_path)
    cartella = tmp_path / "sfz" / "vsco-percussioni"
    cartella.mkdir(parents=True)
    (cartella / ".completo").touch()
    (cartella / "Timpani.sfz").write_text("<global>\n<region> sample=Timpani1_Hit_v1_rr1.wav hivel=80\n")
    monkeypatch.setattr(ss, "scarica_file", lambda *a, **k: pytest.fail("non deve scaricare"))
    ss.scarica(ss.trova("vsco-percussioni"))
    assert "hivel=60" in (cartella / "Timpani.sfz").read_text()
