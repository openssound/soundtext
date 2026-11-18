"""
Test dell'esportazione audio in MP3, FLAC e OGG (core.audio_encode): il
formato dall'estensione, la conversione in un processo a parte, il ripiego
su lame/ffmpeg del sistema, gli stem e il dialogo "Salva" con i formati.

Esecuzione:
    python3 -m pytest tests/test_audio_encode.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)

import os
import sys

import numpy as np
import pytest

from core import audio_encode
from core.audio_encode import (all_filters, convert_wav, ext_from_filter, file_filter, format_of,
                               with_extension, write_audio)
from core.audio_tracks import AUDIO_SAMPLE_RATE as RATE, read_wav, write_wav
from core.model import AudioClip, Project
from core.playback import render_stems_to_dir


def _tone(seconds=1.0, channels=2):
    t = np.arange(int(seconds * RATE)) / RATE
    x = (0.4 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    return np.stack([x] * channels, axis=1)


def _read(path):
    from pedalboard.io import AudioFile
    with AudioFile(path) as f:
        return f.read(f.frames), f.samplerate


def test_format_helpers():
    assert format_of("brano.MP3") == ".mp3" and format_of("brano.flac") == ".flac"
    assert format_of("brano.aiff") == "" and format_of("Brano 1.2") == ""
    assert with_extension("/x/brano.wav", ".mp3") == "/x/brano.mp3"
    assert with_extension("/x/Brano 1.2", ".ogg") == "/x/Brano 1.2.ogg"
    assert file_filter(".mp3") == "MP3 (*.mp3)" and len(all_filters()) == 4
    assert ext_from_filter("FLAC (*.flac)") == ".flac" and ext_from_filter("??") == ".wav"


def test_wav_is_written_as_before(tmp_path):
    path = str(tmp_path / "mix.wav")
    write_audio(path, _tone(), RATE, tempo=120)
    samples, rate = read_wav(path)
    assert rate == RATE and samples.shape == (RATE, 2)
    assert b"acid" in open(path, "rb").read()        # il tempo resta nel WAV


@pytest.mark.parametrize("ext", [".flac", ".ogg", ".mp3"])
def test_compressed_formats_are_readable(tmp_path, ext):
    path = str(tmp_path / ("mix" + ext))
    write_audio(path, _tone(2.0), RATE)
    audio, rate = _read(path)
    assert rate == RATE and audio.shape[0] == 2
    assert abs(audio.shape[1] / rate - 2.0) < 0.1       # l'MP3 aggiunge qualche millisecondo
    assert 0.2 < float(np.max(np.abs(audio))) < 0.6
    if ext != ".mp3":
        assert os.path.getsize(path) < os.path.getsize(_wav_size_reference(tmp_path))
    assert not [f for f in os.listdir(tmp_path) if f.startswith("soundtext_export_")]


def _wav_size_reference(tmp_path):
    path = str(tmp_path / "ref.wav")
    write_wav(path, _tone(2.0), RATE)
    return path


def test_falls_back_to_system_encoder_when_pedalboard_fails(tmp_path, monkeypatch):
    """Se il processo di pedalboard cade (es. SIGILL senza AVX) si prova con
    lame/ffmpeg; se non ce ne sono, un errore chiaro e nessun file a meta'."""
    src = str(tmp_path / "in.wav")
    write_wav(src, _tone(), RATE)
    failing = [sys.executable, "-c", "import sys; sys.exit(3)"]
    monkeypatch.setattr(audio_encode, "_child_command", lambda *_a: failing)
    calls = []

    def fake_system(ext, wav_path, out_path):
        script = f"import shutil; shutil.copy({wav_path!r}, {out_path!r})"
        calls.append(ext)
        return [("finto", [sys.executable, "-c", script])]

    monkeypatch.setattr(audio_encode, "_system_commands", fake_system)
    out = str(tmp_path / "out.mp3")
    assert convert_wav(src, out) == "finto" and os.path.getsize(out) > 0 and calls == [".mp3"]

    monkeypatch.setattr(audio_encode, "_system_commands", lambda *_a: [])
    out2 = str(tmp_path / "out2.ogg")
    with pytest.raises(RuntimeError, match="OGG Vorbis"):
        convert_wav(src, out2)
    assert not os.path.exists(out2)


def test_sigill_is_described():
    assert "SIGILL" in audio_encode._describe_failure("pedalboard", -4, "")


def test_stems_in_flac(tmp_path):
    src = str(tmp_path / "v.wav")
    write_wav(src, np.full((RATE, 1), 0.25, np.float32), RATE)
    p = Project(tempo_bpm=120)
    p.add_audio_track("Voce").audio_clips.append(AudioClip("V", src, 0.0))
    paths = render_stems_to_dir(p, str(tmp_path / "out"), fmt=".flac")
    assert [os.path.basename(x) for x in paths] == ["01 Voce.flac"]
    assert os.listdir(tmp_path / "out") == ["01 Voce.flac"]          # i WAV intermedi non restano
    audio, rate = _read(paths[0])
    assert rate == RATE and audio.shape[1] > 0


def test_save_dialog_offers_formats_and_remembers_the_choice(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QApplication, QFileDialog
    from core.settings import get_audio_export_format, set_audio_export_format
    from gui.wav_export import _ask_audio_path
    QApplication.instance() or QApplication([])
    seen = {}

    def fake_dialog(_parent, _title, directory, filters, selected, **_k):
        seen.update(directory=directory, filters=filters, selected=selected)
        return str(tmp_path / "brano"), "MP3 (*.mp3)"

    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(fake_dialog))
    set_audio_export_format(".wav")
    assert _ask_audio_path(None, "t", str(tmp_path / "brano.wav")) == str(tmp_path / "brano.mp3")
    assert seen["selected"] == "WAV (*.wav)" and "FLAC (*.flac)" in seen["filters"]
    assert get_audio_export_format() == ".mp3"
    # la prossima volta propone l'MP3
    _ask_audio_path(None, "t", str(tmp_path / "brano.wav"))
    assert seen["directory"].endswith("brano.mp3") and seen["selected"] == "MP3 (*.mp3)"
    # un'estensione scritta a mano vince sul filtro
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (str(tmp_path / "x.flac"), "MP3 (*.mp3)")))
    assert _ask_audio_path(None, "t", "y.wav").endswith("x.flac")
    # l'esportazione asciutta (re-amping) resta in WAV
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (str(tmp_path / "secco"), a[3])))
    assert _ask_audio_path(None, "t", "y.wav", wav_only=True).endswith("secco.wav")
    assert get_audio_export_format() == ".flac"
    set_audio_export_format(".wav")        # gli altri test si aspettano il WAV
