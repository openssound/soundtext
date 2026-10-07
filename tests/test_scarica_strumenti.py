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
