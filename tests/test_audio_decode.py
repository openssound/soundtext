"""
Lettura dei file audio senza programmi esterni (core.audio_decode): i WAV li
legge SoundText, gli altri formati il decodificatore di Qt Multimedia
incluso in PySide6 (ffmpeg resta solo come ripiego); ricampionamento di
qualita' (core.audio_tracks.resample_hq).

Per non versionare file audio, il formato "compresso" e' un WAV mu-law
costruito qui: SoundText non lo legge da se', quindi passa davvero per il
decodificatore di Qt.
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from core import audio_decode
from core.audio_tracks import AUDIO_SAMPLE_RATE, import_audio_file, read_wav, read_wav_info, resample_hq

qt_decoder = pytest.mark.skipif(not audio_decode.is_qt_decoder_available(),
                                reason="PySide6 senza il decodificatore di Qt Multimedia")


def _mulaw_encode(x):
    """G.711 mu-law (come l'algoritmo di riferimento, su campioni a 16 bit)."""
    pcm = np.round(np.asarray(x, dtype=np.float64) * 32767).astype(np.int32)
    sign = np.where(pcm < 0, 0x80, 0)
    mag = np.minimum(np.abs(pcm), 32635) + 0x84
    exponent = np.floor(np.log2(mag)).astype(np.int32) - 7
    mantissa = (mag >> (exponent + 3)) & 0x0F
    return (~(sign | (exponent << 4) | mantissa) & 0xFF).astype(np.uint8)


def _write_mulaw_wav(path, samples, rate):
    """WAV G.711 mu-law (formato 7), stereo o mono."""
    samples = np.asarray(samples)
    if samples.ndim == 1:
        samples = samples[:, None]
    ch = samples.shape[1]
    data = _mulaw_encode(np.clip(samples, -1, 1)).reshape(-1).tobytes()
    fmt = struct.pack("<HHIIHHH", 7, ch, rate, rate * ch, ch, 8, 0)
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 4 + 8 + len(fmt) + 8 + 4 + 8 + len(data)) + b"WAVE")
        f.write(b"fmt " + struct.pack("<I", len(fmt)) + fmt)
        f.write(b"fact" + struct.pack("<II", 4, len(samples)))
        f.write(b"data" + struct.pack("<I", len(data)) + data)


def _sine(freq, seconds, rate, amp=0.5):
    return (amp * np.sin(2 * np.pi * freq * np.arange(int(seconds * rate)) / rate)).astype(np.float32)


def _snr_db(y, ref):
    err = y - ref
    return 10 * np.log10(np.mean(ref ** 2) / np.mean(err ** 2))


# --------------------------------------------------------------- ricampionamento

@pytest.mark.parametrize("src,dst,freq", [(44100, 48000, 15000), (48000, 44100, 15000),
                                          (96000, 48000, 5000), (22050, 48000, 3000), (44056, 48000, 2000)])
def test_resample_hq_is_accurate_also_on_the_highs(src, dst, freq):
    y = resample_hq(_sine(freq, 3.0, src)[:, None], src, dst)[:, 0]
    assert len(y) == round(3.0 * dst)
    ref = _sine(freq, 3.0, dst)
    middle = slice(len(y) // 8, 7 * len(y) // 8)
    assert _snr_db(y[middle], ref[middle]) > 90


def test_resample_hq_removes_what_does_not_fit():
    # 30 kHz non esiste a 48 kHz: niente ritorno come falsa frequenza
    y = resample_hq(_sine(30000, 1.0, 96000), 96000, 48000)
    assert np.sqrt(np.mean(y[2000:-2000] ** 2)) < 1e-4


def test_resample_hq_keeps_shape():
    stereo = np.stack([_sine(440, 0.3, 44100), _sine(660, 0.3, 44100)], axis=1)
    assert resample_hq(stereo, 44100, 48000).shape == (round(0.3 * 48000), 2)
    assert resample_hq(stereo[:, 0], 44100, 48000).shape == (round(0.3 * 48000),)


# --------------------------------------------------------------- decodifica

def test_wav_is_read_without_decoders(tmp_path, monkeypatch):
    monkeypatch.setattr(audio_decode, "is_qt_decoder_available", lambda: False)
    monkeypatch.setattr(audio_decode, "is_ffmpeg_available", lambda: False)
    from core.audio_tracks import write_wav
    src = str(tmp_path / "voce.wav")
    write_wav(src, np.stack([_sine(440, 0.5, 48000)] * 2, axis=1), 48000, bits=24)
    out = audio_decode.decode_audio_file_to_wav(src)
    try:
        samples, rate = read_wav(out)
        assert rate == 44100 and samples.shape == (22050, 1)
    finally:
        os.remove(out)


@qt_decoder
def test_qt_decodes_a_format_soundtext_does_not_read(tmp_path, monkeypatch):
    monkeypatch.setattr(audio_decode, "is_ffmpeg_available", lambda: False)
    src = str(tmp_path / "telefono.wav")
    _write_mulaw_wav(src, _sine(440, 0.5, 8000), 8000)
    with pytest.raises(ValueError):
        read_wav_info(src)
    samples, rate = audio_decode.read_audio(src)
    assert rate == 8000 and samples.shape == (4000, 1)
    ref = _sine(440, 0.5, 8000)
    assert _snr_db(samples[:, 0], ref) > 30          # mu-law: 8 bit


@qt_decoder
def test_audio_track_import_through_qt(tmp_path, monkeypatch):
    monkeypatch.setattr(audio_decode, "is_ffmpeg_available", lambda: False)
    src = str(tmp_path / "coro.wav")
    _write_mulaw_wav(src, np.stack([_sine(440, 0.5, 22050), _sine(330, 0.5, 22050)], axis=1), 22050)
    out = import_audio_file(src, str(tmp_path / "dest"))
    info = read_wav_info(out)
    assert (info.samplerate, info.channels, info.bits) == (AUDIO_SAMPLE_RATE, 2, 24)
    assert abs(info.seconds - 0.5) < 0.001


@qt_decoder
def test_decode_for_note_recognition_through_qt(tmp_path, monkeypatch):
    monkeypatch.setattr(audio_decode, "is_ffmpeg_available", lambda: False)
    src = str(tmp_path / "nota.wav")
    _write_mulaw_wav(src, np.stack([_sine(440, 1.0, 16000)] * 2, axis=1), 16000)
    out = audio_decode.decode_audio_file_to_wav(src)
    try:
        info = read_wav_info(out)
        assert (info.samplerate, info.channels, info.bits) == (44100, 1, 16)
        assert abs(info.seconds - 1.0) < 0.001
    finally:
        os.remove(out)


def test_missing_file_and_broken_file_explain(tmp_path):
    with pytest.raises(RuntimeError, match="nope.mp3"):
        audio_decode.read_audio(str(tmp_path / "nope.mp3"))
    broken = tmp_path / "rotto.mp3"
    broken.write_bytes(b"not audio at all" * 10)
    with pytest.raises(RuntimeError, match="rotto.mp3"):
        audio_decode.read_audio(str(broken))
