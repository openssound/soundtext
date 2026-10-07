"""
Test delle tracce audio (fase 1, core.audio_tracks): lettura/scrittura WAV,
importazione dei file, formato .st, cartella audio del progetto, mix sopra
al rendering MIDI ed esportazione del mix in WAV.

Esecuzione:
    python3 -m pytest tests/test_audio_tracks.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import struct
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import audio_tracks
from core.audio_tracks import (
    AUDIO_SAMPLE_RATE, AudioLayer, build_audio_layers, clip_duration_beats, clip_play_seconds,
    consolidate_project_audio, import_audio_file, layers_signature, mix_layers, mix_layers_into_wav,
    read_wav, read_wav_info, resample, waveform_peaks, write_wav,
)
from core.midi_export import channel_instrument_map, compute_project_duration_beats, export_project_to_midi
from core.model import AudioClip, Project
from core.project_io import load_project_file, parse_project_text, project_to_text, save_project_file
from core.tempo_map import build_tempo_beat_map


def _tone(seconds=1.0, rate=AUDIO_SAMPLE_RATE, channels=1, amp=0.5):
    t = np.arange(int(seconds * rate)) / rate
    mono = (amp * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    return np.repeat(mono.reshape(-1, 1), channels, axis=1)


def _write_float_wav(path, samples, rate):
    """WAV in virgola mobile (codifica 3), che il modulo 'wave' non legge."""
    data = samples.astype("<f4").tobytes()
    ch = samples.shape[1]
    fmt = struct.pack("<HHIIHH", 3, ch, rate, rate * ch * 4, ch * 4, 32)
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 4 + 8 + len(fmt) + 8 + len(data)) + b"WAVE")
        f.write(b"fmt " + struct.pack("<I", len(fmt)) + fmt)
        f.write(b"data" + struct.pack("<I", len(data)) + data)


@pytest.fixture(autouse=True)
def _isolated_staging(tmp_path, monkeypatch):
    staging = tmp_path / "staging"
    staging.mkdir()
    monkeypatch.setattr(audio_tracks, "staging_audio_dir", lambda: str(staging))
    return staging


# --------------------------------------------------------------- WAV

@pytest.mark.parametrize("bits", [16, 24])
def test_write_read_wav_round_trip(tmp_path, bits):
    path = str(tmp_path / "t.wav")
    samples = _tone(0.1, channels=2)
    write_wav(path, samples, AUDIO_SAMPLE_RATE, bits=bits)
    info = read_wav_info(path)
    assert (info.channels, info.samplerate, info.bits) == (2, AUDIO_SAMPLE_RATE, bits)
    back, rate = read_wav(path)
    assert rate == AUDIO_SAMPLE_RATE and back.shape == samples.shape
    assert np.max(np.abs(back - samples)) < (1e-4 if bits == 16 else 1e-6)


def test_reads_float_wav(tmp_path):
    path = str(tmp_path / "f.wav")
    samples = _tone(0.05, rate=44100)
    _write_float_wav(path, samples, 44100)
    back, rate = read_wav(path)
    assert rate == 44100
    assert np.allclose(back, samples, atol=1e-7)


def test_non_wav_is_rejected(tmp_path):
    path = tmp_path / "x.wav"
    path.write_bytes(b"not a wav at all")
    with pytest.raises(ValueError):
        read_wav_info(str(path))


def test_resample_changes_length_and_keeps_level():
    samples = _tone(1.0, rate=44100)
    out = resample(samples, 44100, 48000)
    assert len(out) == 48000
    assert abs(np.max(np.abs(out)) - 0.5) < 0.01


# --------------------------------------------------------------- importazione

def test_import_copies_48k_pcm_as_is(tmp_path):
    src = str(tmp_path / "take.wav")
    write_wav(src, _tone(0.2), AUDIO_SAMPLE_RATE, bits=16)
    dest_dir = str(tmp_path / "dest")
    out = import_audio_file(src, dest_dir)
    assert os.path.dirname(out) == dest_dir and os.path.basename(out) == "take.wav"
    assert open(out, "rb").read() == open(src, "rb").read()
    # un secondo import dello stesso file non sovrascrive il primo
    out2 = import_audio_file(src, dest_dir)
    assert out2 != out and os.path.basename(out2) == "take_2.wav"


def test_import_resamples_other_rates(tmp_path):
    src = str(tmp_path / "voce.wav")
    _write_float_wav(src, _tone(0.5, rate=44100), 44100)
    out = import_audio_file(src, str(tmp_path / "dest"))
    info = read_wav_info(out)
    assert (info.samplerate, info.bits) == (AUDIO_SAMPLE_RATE, 24)
    assert abs(info.seconds - 0.5) < 0.001


def test_import_of_a_broken_file_explains(tmp_path):
    src = tmp_path / "song.mp3"
    src.write_bytes(b"ID3fake")
    with pytest.raises(RuntimeError, match="song.mp3"):
        import_audio_file(str(src), str(tmp_path / "dest"))


def test_import_without_any_decoder_explains(tmp_path, monkeypatch):
    from core import audio_decode
    monkeypatch.setattr(audio_decode, "is_qt_decoder_available", lambda: False)
    monkeypatch.setattr(audio_decode, "is_ffmpeg_available", lambda: False)
    src = tmp_path / "song.mp3"
    src.write_bytes(b"ID3fake")
    with pytest.raises(RuntimeError, match="PySide6"):
        import_audio_file(str(src), str(tmp_path / "dest"))


# --------------------------------------------------------------- modello e formato .st

def _project_with_audio(tmp_path, seconds=1.0, start_beat=4.0):
    src = str(tmp_path / "voce take.wav")
    write_wav(src, _tone(seconds), AUDIO_SAMPLE_RATE, bits=16)
    p = Project(name="brano")
    p.add_track("Piano", "Piano", "4: c d e f")
    voce = p.add_audio_track("Voce")
    path = import_audio_file(src, audio_tracks.staging_audio_dir())
    voce.audio_clips.append(AudioClip("Strofa", path, start_beat, trim_start=0.25, gain_db=-3.0))
    voce.volume = 80
    voce.pan = 20
    return p


def test_audio_track_has_no_instrument_and_rejects_duplicate_names():
    p = Project()
    t = p.add_audio_track("Voce")
    assert t.is_audio and t.text == "" and t.instrument.name == "Audio"
    with pytest.raises(ValueError):
        p.add_audio_track("Voce")
    p.update_track("Voce", "Voce 2", "Piano")   # rinomina soltanto: resta audio
    assert p.tracks[0].name == "Voce 2" and p.tracks[0].is_audio


def test_save_consolidates_into_project_audio_dir_with_relative_paths(tmp_path):
    p = _project_with_audio(tmp_path)
    song = tmp_path / "canzoni" / "brano.st"
    song.parent.mkdir()
    save_project_file(p, str(song))

    audio_dir = tmp_path / "canzoni" / "brano_audio"
    assert (audio_dir / "voce take.wav").exists()
    clip = p.get_track("Voce").audio_clips[0]
    assert clip.file == str(audio_dir / "voce take.wav")   # aggiornato in memoria

    text = song.read_text()
    assert 'Audio Voce "Strofa" |4:' in text
    assert 'file="brano_audio/voce take.wav" trim=0.25,0 gain=-3' in text
    assert "Traccia Voce [Audio]:" in text

    q = load_project_file(str(song))
    voce = q.get_track("Voce")
    assert voce.is_audio and (voce.volume, voce.pan) == (80, 20)
    loaded = voce.audio_clips[0]
    assert loaded.file == str(audio_dir / "voce take.wav")
    assert (loaded.start_beat, loaded.trim_start, loaded.trim_end, loaded.gain_db) == (4.0, 0.25, 0.0, -3.0)
    assert q.get_track("Piano").text.strip() == "4: c d e f"


def test_save_as_elsewhere_copies_audio_to_the_new_project(tmp_path):
    p = _project_with_audio(tmp_path)
    first = tmp_path / "a" / "uno.st"
    first.parent.mkdir()
    save_project_file(p, str(first))
    second = tmp_path / "b" / "due.st"
    second.parent.mkdir()
    save_project_file(p, str(second))
    assert (tmp_path / "b" / "due_audio" / "voce take.wav").exists()
    assert (tmp_path / "a" / "uno_audio" / "voce take.wav").exists()   # l'originale resta
    assert load_project_file(str(second)).get_track("Voce").audio_clips[0].file == \
        str(tmp_path / "b" / "due_audio" / "voce take.wav")


def test_consolidate_keeps_distinct_files_with_same_name(tmp_path):
    p = Project()
    t = p.add_audio_track("Voce")
    for sub, amp in (("x", 0.2), ("y", 0.4)):
        d = tmp_path / sub
        d.mkdir()
        write_wav(str(d / "take.wav"), _tone(0.1, amp=amp), AUDIO_SAMPLE_RATE, bits=16)
        t.audio_clips.append(AudioClip(sub, str(d / "take.wav"), 0.0))
    assert consolidate_project_audio(p, str(tmp_path / "s.st")) == 2
    names = sorted(os.path.basename(c.file) for c in t.audio_clips)
    assert names == ["take.wav", "take_2.wav"]


def test_missing_file_keeps_clip_and_is_skipped_in_mix(tmp_path):
    text = ('Tempo: 120 BPM\nMetrica: 4/4\n\nAudio Voce "Persa" |2:\n  file="manca/x.wav"\n\n'
            'Traccia Voce [Audio]:\n')
    p = parse_project_text(text, base_dir=str(tmp_path))
    clip = p.get_track("Voce").audio_clips[0]
    assert clip.file == str(tmp_path / "manca" / "x.wav")
    assert audio_tracks.clip_is_missing(clip) and clip_play_seconds(clip) == 0.0
    assert build_audio_layers(p, p.tracks, build_tempo_beat_map(p)) == []
    # e sopravvive a un nuovo salvataggio
    assert 'file="manca/x.wav"' in project_to_text(p, base_dir=str(tmp_path))


def test_audio_named_like_instrument_header_is_not_a_track():
    """'Audio:' da solo non e' un'intestazione di traccia valida: le tracce
    audio si scrivono sempre in forma esplicita."""
    p = Project()
    p.add_audio_track("Audio")
    text = project_to_text(p)
    assert "Traccia Audio [Audio]:" in text
    assert parse_project_text(text).get_track("Audio").is_audio


# --------------------------------------------------------------- durata e MIDI

def test_clip_duration_follows_tempo_at_its_position(tmp_path):
    p = _project_with_audio(tmp_path, seconds=2.25, start_beat=0.0)   # 2 s riprodotti (trim 0.25)
    clip = p.get_track("Voce").audio_clips[0]
    assert clip_duration_beats(clip, build_tempo_beat_map(p)) == pytest.approx(4.0)   # 120 BPM
    p.tempo_bpm = 60
    assert clip_duration_beats(clip, build_tempo_beat_map(p)) == pytest.approx(2.0)


def test_midi_export_ignores_audio_tracks_and_duration_includes_them(tmp_path):
    p = _project_with_audio(tmp_path, seconds=10.25, start_beat=4.0)   # finisce al beat 24
    assert list(channel_instrument_map(p).values()) == ["Piano"]
    out = str(tmp_path / "x.mid")
    export_project_to_midi(p, out)
    import mido
    programs = [m for tr in mido.MidiFile(out).tracks for m in tr if m.type == "program_change"]
    assert len(programs) == 1
    assert compute_project_duration_beats(p) == pytest.approx(24.0)
    p.get_track("Voce").mute = True
    assert compute_project_duration_beats(p) == pytest.approx(4.0)


# --------------------------------------------------------------- mix

def test_build_layers_applies_gain_pan_master_and_offset(tmp_path):
    p = _project_with_audio(tmp_path)   # clip al beat 4 = 2 s, trim 0.25, -3 dB, volume 80
    p.master_volume = 50
    tempo_map = build_tempo_beat_map(p)
    [layer] = build_audio_layers(p, p.tracks, tempo_map)
    assert layer.start_seconds == pytest.approx(2.0)
    assert layer.gain == pytest.approx(10 ** (-3 / 20) * 0.8 * 0.5)
    assert layer.pan == 20
    [shifted] = build_audio_layers(p, p.tracks, tempo_map, offset_seconds=2.5)
    assert shifted.start_seconds == 0.0 and shifted.trim_start == pytest.approx(0.75)


def test_mix_places_clip_and_extends_the_base():
    rate = 1000
    base = np.zeros((500, 2), dtype=np.float32)
    layer_samples = np.ones((300, 1), dtype=np.float32) * 0.5

    import tempfile
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "l.wav")
        write_wav(path, layer_samples, rate, bits=24)
        layer = AudioLayer(path=path, start_seconds=0.4, trim_start=0.1, trim_end=0.0, gain=1.0, pan=127)
        mixed = mix_layers(base, rate, [layer])
    assert len(mixed) == 600                           # 0.4 s + 0.2 s riprodotti
    assert np.all(mixed[:400] == 0)
    assert np.allclose(mixed[400:, 1], 0.5, atol=1e-6)  # pan tutto a destra: destra piena
    assert np.allclose(mixed[400:, 0], 0.0, atol=1e-6)  # ...sinistra muta


def test_mix_into_empty_render_and_signature_changes_with_file(tmp_path):
    p = _project_with_audio(tmp_path, seconds=0.5, start_beat=0.0)
    layers = build_audio_layers(p, p.tracks, build_tempo_beat_map(p))
    base = str(tmp_path / "render.wav")
    write_wav(base, np.zeros((0, 2), dtype=np.float32), AUDIO_SAMPLE_RATE, bits=16)
    sig_before = layers_signature(layers)
    mix_layers_into_wav(base, layers)
    out, rate = read_wav(base)
    assert rate == AUDIO_SAMPLE_RATE and out.shape == (int(0.25 * AUDIO_SAMPLE_RATE), 2)
    assert np.max(np.abs(out)) > 0.1

    clip = p.get_track("Voce").audio_clips[0]
    write_wav(clip.file, _tone(0.6), AUDIO_SAMPLE_RATE, bits=16)
    assert layers_signature(layers) != sig_before


def test_waveform_peaks_cover_the_played_part(tmp_path):
    path = str(tmp_path / "w.wav")
    samples = np.concatenate([np.zeros((AUDIO_SAMPLE_RATE, 1)), np.full((AUDIO_SAMPLE_RATE, 1), 0.8)])
    write_wav(path, samples.astype(np.float32), AUDIO_SAMPLE_RATE, bits=16)
    peaks = waveform_peaks(AudioClip("w", path), 10)
    assert peaks.shape == (10,) and peaks[0] == 0 and peaks[-1] == pytest.approx(0.8, abs=0.01)
    trimmed = waveform_peaks(AudioClip("w", path, trim_start=1.0), 4)
    assert np.all(trimmed > 0.7)
    assert waveform_peaks(AudioClip("x", str(tmp_path / "manca.wav")), 4) is None


# --------------------------------------------------------------- esportazione WAV

def test_export_mix_of_audio_only_project_needs_no_synth(tmp_path, monkeypatch):
    from core import playback
    monkeypatch.setattr(playback, "_shared_synth", None)
    p = Project()
    t = p.add_audio_track("Chitarra")
    src = str(tmp_path / "gtr.wav")
    write_wav(src, _tone(1.0), AUDIO_SAMPLE_RATE, bits=16)
    t.audio_clips.append(AudioClip("Riff", src, 2.0))   # 1 s a 120 BPM
    out = str(tmp_path / "mix.wav")
    playback.render_project_mix_to_wav(p, out)
    info = read_wav_info(out)
    assert (info.channels, info.samplerate, info.bits) == (2, AUDIO_SAMPLE_RATE, 24)
    assert info.seconds == pytest.approx(2.0, abs=0.001)


def test_export_single_track_ignores_solo_mute_and_other_tracks(tmp_path, monkeypatch):
    from core import playback
    monkeypatch.setattr(playback, "_shared_synth", None)
    p = Project()
    src = str(tmp_path / "gtr.wav")
    write_wav(src, _tone(1.0), AUDIO_SAMPLE_RATE, bits=16)
    gtr = p.add_audio_track("Chitarra")
    gtr.audio_clips.append(AudioClip("Riff", src, 2.0))   # finisce a 2 s
    gtr.mute = True
    voice = p.add_audio_track("Voce")
    voice.audio_clips.append(AudioClip("Strofa", src, 8.0))   # finisce a 5 s
    voice.solo = True
    out = str(tmp_path / "chitarra.wav")
    playback.render_project_mix_to_wav(p, out, tracks=[gtr])
    assert read_wav_info(out).seconds == pytest.approx(2.0, abs=0.001)


def test_export_mix_with_notes_but_no_synth_explains(tmp_path, monkeypatch):
    from core import playback
    monkeypatch.setattr(playback, "_shared_synth", None)
    monkeypatch.setattr(playback.shutil, "which", lambda name: None)
    p = Project()
    p.add_track("Piano", "Piano", "4: c d e f")
    with pytest.raises(RuntimeError, match="SoundFont"):
        playback.render_project_mix_to_wav(p, str(tmp_path / "mix.wav"))


def test_export_mix_of_empty_project_explains(tmp_path):
    from core import playback
    with pytest.raises(RuntimeError, match="Niente da esportare"):
        playback.render_project_mix_to_wav(Project(), str(tmp_path / "mix.wav"))


def test_missing_clip_is_visible_but_does_not_lengthen_the_song(tmp_path):
    p = Project()
    p.add_track("Piano", "Piano", "4: c d e f")
    p.add_audio_track("Voce").audio_clips.append(AudioClip("Persa", str(tmp_path / "manca.wav"), 8.0))
    clip = p.get_track("Voce").audio_clips[0]
    assert clip_duration_beats(clip, build_tempo_beat_map(p)) == audio_tracks.MISSING_CLIP_BEATS
    assert compute_project_duration_beats(p) == pytest.approx(4.0)



# --------------------------------------------------------------- taglio e divisione

def _clip_2s(tmp_path, start_beat=4.0, trim_start=0.0):
    src = str(tmp_path / "c.wav")
    write_wav(src, np.linspace(-0.5, 0.5, AUDIO_SAMPLE_RATE * 2, dtype=np.float32).reshape(-1, 1),
              AUDIO_SAMPLE_RATE, bits=24)
    return AudioClip("C", src, start_beat, trim_start=trim_start)


def test_trim_start_keeps_the_audio_in_place(tmp_path):
    tempo = build_tempo_beat_map(Project(tempo_bpm=120))
    clip = _clip_2s(tmp_path, start_beat=4.0)
    audio_tracks.trim_clip_start_to_beat(clip, 5.0, tempo)       # +1 beat = +0,5 s
    assert (clip.start_beat, clip.trim_start) == (5.0, 0.5)
    audio_tracks.trim_clip_start_to_beat(clip, 0.0, tempo)       # oltre l'inizio del file
    assert (clip.start_beat, clip.trim_start) == (4.0, 0.0)
    audio_tracks.trim_clip_start_to_beat(clip, 20.0, tempo)      # oltre la fine
    assert clip.trim_start == pytest.approx(2.0 - audio_tracks.MIN_CLIP_SECONDS)


def test_trim_start_can_reveal_a_recorded_count_in(tmp_path):
    tempo = build_tempo_beat_map(Project(tempo_bpm=120))
    clip = _clip_2s(tmp_path, start_beat=4.0, trim_start=1.0)
    audio_tracks.trim_clip_start_to_beat(clip, 3.0, tempo)
    assert (clip.start_beat, clip.trim_start) == (3.0, 0.5)


def test_trim_end(tmp_path):
    tempo = build_tempo_beat_map(Project(tempo_bpm=120))
    clip = _clip_2s(tmp_path, start_beat=4.0)
    audio_tracks.trim_clip_end_to_beat(clip, 6.0, tempo)
    assert clip.trim_end == pytest.approx(1.0) and clip_play_seconds(clip) == pytest.approx(1.0)
    audio_tracks.trim_clip_end_to_beat(clip, 40.0, tempo)
    assert clip.trim_end == 0.0


def test_split_clip_in_two_contiguous_parts(tmp_path):
    tempo = build_tempo_beat_map(Project(tempo_bpm=120))
    clip = _clip_2s(tmp_path, start_beat=4.0, trim_start=0.25)
    second = audio_tracks.split_clip(clip, 6.0, tempo)
    assert clip_play_seconds(clip) == pytest.approx(1.0)
    assert (second.start_beat, second.trim_start, second.trim_end) == (6.0, 1.25, 0.0)
    assert second.name == "C (2)" and second.file == clip.file
    assert audio_tracks.split_clip(clip, 3.0, tempo) is None     # fuori dalla clip


def test_extract_clip_audio_writes_only_the_played_part(tmp_path):
    clip = _clip_2s(tmp_path, trim_start=0.5)
    clip.trim_end = 0.5
    out = str(tmp_path / "part.wav")
    audio_tracks.extract_clip_audio(clip, out)
    samples, _rate = read_wav(out)
    assert len(samples) == AUDIO_SAMPLE_RATE
    assert samples[0, 0] == pytest.approx(-0.25, abs=1e-3)
