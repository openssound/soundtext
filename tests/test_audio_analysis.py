"""
Test dei componenti di analisi audio (eseguibili senza sounddevice/ffmpeg
installati, solo numpy):
- core.audio_percussion._classify_band (classificazione kick/snare/hihat)
- core.audio_pitch._buf_size_for_min_freq (dimensionamento finestra pitch)

Esecuzione:
    python3 -m pytest tests/test_audio_analysis.py -v
oppure:
    python3 tests/test_audio_analysis.py
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from core.audio_percussion import _classify_band
from core.audio_pitch import _buf_size_for_min_freq, DEFAULT_BUF_SIZE

SR = 44100
N = 4096
_FREQS = np.fft.rfftfreq(N, d=1.0 / SR)


def _make_signal(low_amp, mid_amp, high_amp, seed):
    """Costruisce un segnale con un profilo spettrale per banda controllato
    (fase casuale, ampiezza target per banda), per testare la
    classificazione su spettri realistici senza dipendere da toni puri
    (che concentrerebbero l'energia in pochi bin e non sono rappresentativi
    di un vero colpo percussivo a banda larga)."""
    rng = np.random.default_rng(seed)
    mag = np.zeros_like(_FREQS)
    mag[_FREQS < 150] = low_amp
    mag[(_FREQS >= 150) & (_FREQS < 1000)] = mid_amp
    mag[_FREQS >= 1000] = high_amp
    phase = rng.uniform(0, 2 * np.pi, size=len(_FREQS))
    spectrum = mag * np.exp(1j * phase)
    sig = np.fft.irfft(spectrum, N)
    sig = sig / (np.max(np.abs(sig)) + 1e-9)
    return sig.astype(np.float32)


def test_kick_dominant_low_band():
    sig = _make_signal(1.0, 0.05, 0.01, seed=1)
    name, velocity = _classify_band(sig, SR)
    assert name == "kick"
    assert 1 <= velocity <= 127


def test_snare_mid_and_high_balanced():
    sig = _make_signal(0.05, 0.8, 0.6, seed=2)
    name, _ = _classify_band(sig, SR)
    assert name == "snare"


def test_hihat_high_dominant():
    sig = _make_signal(0.02, 0.05, 1.0, seed=3)
    name, _ = _classify_band(sig, SR)
    assert name == "hihat"


def test_empty_window_defaults_to_snare_without_crashing():
    name, velocity = _classify_band(np.zeros(0, dtype=np.float32), SR)
    assert name == "snare"
    assert velocity == 60


def test_classification_not_biased_toward_high_band_by_bin_count():
    # Regressione: una versione precedente sommava (invece di mediare) le
    # ampiezze per banda, favorendo sistematicamente la banda alta (che ha
    # ~100x piu' bin di quella bassa) indipendentemente dal contenuto
    # spettrale reale. Un segnale con energia bassa chiaramente dominante
    # deve restare "kick", non scivolare verso "hihat".
    sig = _make_signal(1.0, 0.02, 0.02, seed=4)
    name, _ = _classify_band(sig, SR)
    assert name == "kick"


def _make_signal_3band(a_low, a_mid, a_high, mid_boundary_hz, seed):
    """Come _make_signal, ma con un confine banda-bassa/media personalizzato
    (usato per simulare un 'boom' di bocca, la cui energia si concentra
    tipicamente 150-350Hz, non sotto i 150Hz come una vera cassa)."""
    rng = np.random.default_rng(seed)
    mag = np.zeros_like(_FREQS)
    mag[_FREQS < 150] = a_low
    mag[(_FREQS >= 150) & (_FREQS < mid_boundary_hz)] = a_mid
    mag[_FREQS >= mid_boundary_hz] = a_high
    phase = rng.uniform(0, 2 * np.pi, size=len(_FREQS))
    spectrum = mag * np.exp(1j * phase)
    sig = np.fft.irfft(spectrum, N)
    sig = sig / (np.max(np.abs(sig)) + 1e-9)
    return sig.astype(np.float32)


def test_beatbox_mode_does_not_overtrigger_kick_on_generic_voiced_sound():
    # Regressione: un primo tentativo di calibrazione beatbox allargava la
    # banda bassa fino a 250Hz, che ricade nel fondamentale vocale di
    # QUALUNQUE suono vocalizzato (non solo un "boom" di kick) — risultato
    # concreto: troppi colpi (anche snare/hihat imitati con la bocca)
    # classificati come kick. Un suono con energia concentrata 150-350Hz
    # (fuori dalla banda bassa, che resta 0-150Hz anche in modalita'
    # beatbox) NON deve essere classificato come kick.
    voiced_sound = _make_signal_3band(0.10, 1.0, 0.3, mid_boundary_hz=350, seed=10)
    assert _classify_band(voiced_sound, SR, beatbox=False)[0] != "kick"
    assert _classify_band(voiced_sound, SR, beatbox=True)[0] != "kick"


def test_beatbox_mode_kick_threshold_is_only_mildly_more_permissive():
    # La soglia beatbox e' comunque leggermente piu' permissiva di quella
    # di default (0.38 contro 0.45): un segnale con energia bassa
    # genuinamente dominante ma non quanto una cassa vera puo' ribaltare la
    # classificazione tra le due modalita', a conferma che la ricalibrazione
    # fa ancora qualcosa (non e' un semplice alias della modalita' normale).
    borderline = _make_signal(0.42, 0.3, 0.2, seed=11)
    assert _classify_band(borderline, SR, beatbox=False)[0] != "kick"
    assert _classify_band(borderline, SR, beatbox=True)[0] == "kick"


def test_beatbox_mode_does_not_break_real_drum_spectra():
    kick = _make_signal(1.0, 0.05, 0.01, seed=1)
    hihat = _make_signal(0.02, 0.05, 1.0, seed=3)
    assert _classify_band(kick, SR, beatbox=True)[0] == "kick"
    assert _classify_band(hihat, SR, beatbox=True)[0] == "hihat"


def test_buf_size_grows_for_low_frequencies():
    assert _buf_size_for_min_freq(None) == DEFAULT_BUF_SIZE
    assert _buf_size_for_min_freq(220.0) == DEFAULT_BUF_SIZE
    assert _buf_size_for_min_freq(80.0) > DEFAULT_BUF_SIZE
    assert _buf_size_for_min_freq(41.2) > _buf_size_for_min_freq(80.0)


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
