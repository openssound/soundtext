import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)

import numpy as np

from core import audio_stream


class _FakeStream:
    opened = []

    def __init__(self, samplerate, channels, dtype, latency, callback):
        self.callback, self.active, self.closed = callback, False, False
        _FakeStream.opened.append(self)

    def start(self):
        self.active = True

    def stop(self):
        self.active = False

    def close(self):
        self.closed = True

    def pull(self, frames):
        out = np.zeros((frames, 2), np.float32)
        self.callback(out, frames, None, None)
        return out


class _FakeSd:
    OutputStream = _FakeStream


def _player(monkeypatch):
    _FakeStream.opened = []
    monkeypatch.setattr(audio_stream, "_sd", _FakeSd)
    return audio_stream.ClickPlayer(44100)


def test_clicks_are_mixed_and_finish(monkeypatch):
    player = _player(monkeypatch)
    assert player.play(np.full(100, 0.5, np.float32), 0.5)
    assert player.play(np.full(50, 0.5, np.float32), 1.0)
    out = _FakeStream.opened[0].pull(80)
    assert np.allclose(out[:50, 0], 0.75) and np.allclose(out[50:80, 1], 0.25)
    _FakeStream.opened[0].pull(80)
    assert player._voices == [] and len(_FakeStream.opened) == 1      # un solo flusso


def test_a_stopped_or_idle_stream_is_reopened(monkeypatch):
    """Il caso del metronomo muto fino al riavvio: l'uscita audio si ferma
    (dispositivo cambiato o sospeso) e il click dopo deve riaprirla."""
    player = _player(monkeypatch)
    player.play(np.ones(10, np.float32))
    _FakeStream.opened[0].active = False                     # flusso perso
    player.play(np.ones(10, np.float32))
    assert len(_FakeStream.opened) == 2 and _FakeStream.opened[0].closed
    player._last_sound -= player.IDLE_SECONDS + 1            # dopo una pausa
    player.play(np.ones(10, np.float32))
    assert len(_FakeStream.opened) == 3


def test_metronome_plays_clicks_through_the_player(monkeypatch):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    import gui.metronome_engine as me
    played = []

    class Player:
        def play(self, samples, volume):
            played.append((len(samples), volume))
            return True

    monkeypatch.setattr(me, "_shared_click_player", lambda rate: Player())
    engine = me.MetronomeEngine()
    engine._play_click(True)
    engine._play_click(False)
    assert len(played) == 2 and played[0][0] > 0
