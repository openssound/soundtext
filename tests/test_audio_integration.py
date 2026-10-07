"""
Test di integrazione dei moduli di analisi audio sull'intera pipeline
(WAV scritto su disco -> attacchi e altezze, vedi core.audio_dsp).

Copre in particolare le note gravi: un rilevatore di attacchi che non
scatta sotto ~150Hz (com'era aubio.notes(), usato in una versione
precedente) perde l'intero registro del basso.

Esecuzione:
    python3 -m pytest tests/test_audio_integration.py -v
oppure:
    python3 tests/test_audio_integration.py
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys
import shutil
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

SR = 44100


def _write_wav(path, sig, samplerate=SR):
    import wave
    sig = sig / (np.max(np.abs(sig)) + 1e-9) * 0.9
    pcm = (sig * 32767).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(samplerate)
        wf.writeframes(pcm.tobytes())


def _make_tone(freq_hz, dur=1.0, attack=0.005, silence_pad=0.1):
    n = int(SR * dur)
    t = np.arange(n) / SR
    note = 0.55 * np.sin(2 * np.pi * freq_hz * t) + 0.2 * np.sin(2 * np.pi * 2 * freq_hz * t) \
        + 0.08 * np.sin(2 * np.pi * 3 * freq_hz * t)
    env = np.ones(n)
    a = max(1, int(attack * SR))
    env[:a] = np.linspace(0, 1, a)
    sig = note * env
    pad = np.zeros(int(SR * silence_pad))
    return np.concatenate([pad, sig])


def _make_legato_sequence(freqs_hz, note_dur=0.5, vibrato_hz=5.5, vibrato_depth_semi=0.3, seed=0):
    """Sequenza di note 'cantate' senza silenzio tra loro (transizioni
    legato) con vibrato e piccola deriva di intonazione, per simulare una
    voce non professionale invece di uno strumento vero."""
    rng = np.random.default_rng(seed)
    chunks = []
    for f in freqs_hz:
        n = int(SR * note_dur)
        t = np.arange(n) / SR
        drift = np.cumsum(rng.normal(0, 0.002, n))
        vibrato = vibrato_depth_semi * np.sin(2 * np.pi * vibrato_hz * t)
        freq_t = f * (2 ** ((vibrato + drift * 3.0) / 12))
        phase = 2 * np.pi * np.cumsum(freq_t) / SR
        note = 0.55 * np.sin(phase) + 0.2 * np.sin(2 * phase) + 0.08 * np.sin(3 * phase) + 0.03 * rng.normal(0, 1, n)
        env = np.ones(n)
        a = int(0.04 * SR)
        env[:a] = np.linspace(0, 1, a)
        env[-a:] = np.linspace(1, 0, a)
        chunks.append(note * env)
    return np.concatenate(chunks)


def _make_drum_hit(freq_fund, decay, dur=0.3, harmonics=None, noise=0.0, seed=0):
    n = int(SR * dur)
    t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * freq_fund * t)
    for h, amp in (harmonics or []):
        sig = sig + amp * np.sin(2 * np.pi * freq_fund * h * t)
    if noise:
        rng = np.random.default_rng(seed)
        sig = sig + noise * rng.normal(0, 1, n)
    return sig * np.exp(-t / decay)


def test_detect_melodic_notes_single_low_tone():
    """Regressione: con il vecchio aubio.notes() questo caso ritornava
    SEMPRE zero note (attacco mai rilevato sotto ~150Hz)."""
    from core.audio_pitch import detect_melodic_notes

    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "low.wav")
        _write_wav(path, _make_tone(82.41))  # Mi2, registro basso a 4 corde
        events = detect_melodic_notes(path)
        assert len(events) == 1, f"attese 1 nota, trovate {len(events)}: {events}"
        assert events[0].midi_pitch == 40, f"atteso MIDI 40 (e*2), trovato {events[0].midi_pitch}"
    finally:
        shutil.rmtree(tmpdir)


def test_detect_melodic_notes_legato_vocal_sequence():
    from core.audio_pitch import detect_melodic_notes

    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "legato.wav")
        # E2 E2 A2 G2 (le stesse prime 4 note usate durante il debug)
        _write_wav(path, _make_legato_sequence([82.41, 82.41, 110.00, 98.00]))
        events = detect_melodic_notes(path)
        assert len(events) >= 2, f"attese almeno 2 note distinte, trovate {len(events)}: {events}"
        pitches = [ev.midi_pitch for ev in events]
        # le prime due note (stessa altezza, E2=40) devono fondersi in una sola
        assert pitches[0] == 40
        assert 45 in pitches  # A2
        assert 43 in pitches  # G2
    finally:
        shutil.rmtree(tmpdir)


def test_detect_percussive_hits_real_pipeline():
    from core.audio_percussion import detect_percussive_hits

    kick = _make_drum_hit(60, 0.15, harmonics=[(2, 0.2)])
    snare = _make_drum_hit(200, 0.08, harmonics=[(1.7, 0.3)], noise=0.6, seed=1)
    hihat = _make_drum_hit(6000, 0.05, harmonics=[(1.3, 0.4), (1.7, 0.3)], noise=0.5, seed=2)

    total_len = int(SR * 2.0)
    buf = np.zeros(total_len)
    for offset, hit in [(0.0, kick), (0.5, snare), (1.0, hihat), (1.5, kick)]:
        start = int(offset * SR)
        end = min(start + len(hit), total_len)
        buf[start:end] += hit[:end - start]

    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "pattern.wav")
        _write_wav(path, buf)
        events = detect_percussive_hits(path)
        names = [ev.perc_name for ev in events]
        assert names == ["kick", "snare", "hihat", "kick"], names
    finally:
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    import inspect
    here = sys.modules[__name__]
    tests = [f for name, f in inspect.getmembers(here) if name.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        passed += 1
        print(f"OK  {t.__name__}")
    print(f"\n{passed}/{len(tests)} test superati.")
