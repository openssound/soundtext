"""
Cambiare il SoundFont (Opzioni) deve cambiare il suono anche dopo che
un altro e' gia' stato usato: prima il synth condiviso li accumulava e
suonava sempre quello caricato per ultimo.

Esecuzione:
    python3 -m pytest tests/test_soundfont_switch.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)
import os

import numpy as np
import pytest

TIM = "/usr/share/sounds/sf2/TimGM6mb.sf2"
FLUID = "/usr/share/sounds/sf2/FluidR3_GM.sf2"


@pytest.mark.skipif(not (os.path.exists(TIM) and os.path.exists(FLUID)), reason="SoundFont di prova assenti")
def test_switching_back_to_a_soundfont_already_used_changes_the_sound():
    from core import fluid, playback, settings
    from core.model import Project
    if not fluid.available():
        pytest.skip("libreria FluidSynth non installata")
    previous = settings.get_soundfont_path()

    def render(path):
        settings.set_soundfont_path(path)
        p = Project(name="t")
        p.add_track("Piano", "Piano", "4: [c*4 e*4 g*4] 7r")
        return playback.render_project_mix(p)[0]

    try:
        a, b, c = render(TIM), render(FLUID), render(TIM)
    finally:
        if previous:
            settings.set_soundfont_path(previous)
    n = min(len(a), len(b), len(c))
    different = np.abs(a[:n] - b[:n]).max()
    same = np.abs(a[:n] - c[:n]).max()
    assert different > 0.1
    assert same < different / 10            # di nuovo TimGM6mb, non FluidR3 caricato per ultimo
