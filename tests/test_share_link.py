"""Il link di un brano per SoundText Mobile (core/share_link.py): lo stesso formato di mobile/share.js."""
import base64
import shutil
import subprocess
import zlib
from pathlib import Path

import pytest

from core.share_link import LONG_LINK, MOBILE_URL, make_fragment, make_url, read_fragment

ROOT = Path(__file__).resolve().parent.parent
SONG = "ST: 2.6\nTempo: 120 BPM\n\nPiano:\n  4: c d e f | g a b c*5 |\n"


def test_round_trip_keeps_bytes_and_name():
    url = make_url("Prova à «due» & tre", SONG)
    assert url.startswith(MOBILE_URL + "#v=1&b=")
    name, data = read_fragment(url.split("#", 1)[1])
    assert name == "Prova à «due» & tre"
    assert data.decode("utf-8") == SONG


def test_payload_is_raw_deflate_base64url():
    fragment = make_fragment("x", SONG.encode())
    b64 = dict(p.split("=", 1) for p in fragment.split("&"))["b"]
    assert "=" not in b64 and "+" not in b64 and "/" not in b64
    raw = base64.urlsafe_b64decode(b64 + "=" * (-len(b64) % 4))
    assert zlib.decompress(raw, -15) == SONG.encode()


def test_too_large_and_wrong_version():
    with pytest.raises(ValueError):
        make_fragment("x", b"a" * ((1 << 20) + 1))
    with pytest.raises(ValueError):
        read_fragment("v=2&b=AA")
    assert read_fragment("v=1&n=x") is None
    assert LONG_LINK == 8000


@pytest.mark.skipif(not shutil.which("node"), reason="serve Node")
def test_mobile_app_reads_pc_link(tmp_path):
    url = make_url("Dal PC", SONG)
    script = tmp_path / "read.cjs"
    script.write_text(
        "const fs=require('fs');"
        "global.btoa=(s)=>Buffer.from(s,'binary').toString('base64');"
        "global.atob=(s)=>Buffer.from(s,'base64').toString('binary');"
        "const ShareLink=new Function(fs.readFileSync(process.argv[2],'utf8')+';return ShareLink;')();"
        "ShareLink.readFragment(process.argv[3]).then((r)=>process.stdout.write(r.name+'\\n'+new TextDecoder().decode(r.bytes)));")
    out = subprocess.run(["node", str(script), str(ROOT / "mobile" / "share.js"), url.split("#", 1)[1]],
                         capture_output=True, text=True, check=True).stdout
    assert out == "Dal PC\n" + SONG


def test_main_window_copies_link(monkeypatch):
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QMessageBox
    app = QApplication.instance() or QApplication([])
    from gui.main_window import MainWindow
    shown = []
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: shown.append(a[2]))
    w = MainWindow()
    w.project.name = "Mio brano"
    w.project.add_track("Melodia", "Piano", "4: c d e f |")
    w.copy_share_link()
    url = app.clipboard().text()
    assert url.startswith(MOBILE_URL + "#v=1&b=")
    name, data = read_fragment(url.split("#", 1)[1])
    assert name == "Mio brano" and "c d e f" in data.decode()
    assert shown and "Mio brano" in shown[0]
    assert any("Copia il link del brano" == a.text() for a in w.menuBar().actions()[0].menu().actions())


def test_project_keeps_quick_song_choices_for_remix():
    """Aprendo e risalvando un brano di «Un brano in 60 secondi» le sue scelte restano: il link dal PC permette il remix."""
    from core.project_io import parse_project_text, project_to_text
    from core.quicksong import quick_read, quick_song
    made = quick_song({"genre": "pop", "mood": "allegra", "duration": 15, "seed": 7})
    project = parse_project_text(made["text"], "Brano")
    assert json_of(project.quick)["seed"] == 7
    text = project_to_text(project)
    assert quick_read(text)["genre"] == "pop" and quick_read(text)["seed"] == 7
    assert text.splitlines()[0].startswith("ST:")
    assert project_to_text(parse_project_text(text, "Brano")) == text          # stabile a ogni salvataggio
    link = make_url("Brano", text)
    assert "// quick: {" in read_fragment(link.split("#", 1)[1])[1].decode()


def test_project_without_quick_choices_writes_none():
    from core.project_io import parse_project_text, project_to_text
    assert "// quick:" not in project_to_text(parse_project_text(SONG, "Brano"))


def json_of(text):
    import json
    return json.loads(text)


def test_symbols_do_not_make_the_link_much_longer_and_survive_the_round_trip():
    """♭ e ♯ sono tre byte in UTF-8: il link li comprime e li legge uguali, e resta sotto il limite dei messaggi."""
    from core.share_link import LONG_LINK, read_fragment
    ascii_song = "ST: 2.13\nTempo: 100 BPM\n\nPiano:\n" + "".join(f"  4: bb*4 c#*5 db*4 eb*4 f#*4 ab*4 | {i}\n" for i in range(1)) * 60
    symbols_song = ascii_song.replace("bb", "b♭").replace("c#", "c♯").replace("db", "d♭").replace("eb", "e♭").replace("f#", "f♯").replace("ab", "a♭")
    plain, marked = make_url("Dal PC", ascii_song), make_url("Dal PC", symbols_song)
    assert len(marked) < len(plain) * 1.2 and len(marked) < LONG_LINK
    name, data = read_fragment(marked.split("#", 1)[1])
    assert name == "Dal PC" and data.decode("utf-8") == symbols_song
