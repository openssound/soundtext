"""
Colore per famiglia strumentale (la striscia a sinistra delle testate e dei
box delle tracce) ed etichetta del pan (C, L40, R73...), condivisi dalle
testate delle tracce (gui.track_header) e dalla vista Struttura brano.
"""

from core.instruments import get_instrument, gm_family_for_program
from core.model import AUDIO_INSTRUMENT_NAME

# Colore identificativo per famiglia strumentale, per una scansione visiva
# rapida delle tracce (striscia colorata a sinistra di ogni traccia).
_FAMILY_COLORS = {
    "Pianoforti": "#7ec9e8", "Percussioni intonate": "#c9a0ea", "Organi": "#e8c96d",
    "Chitarre": "#e8b86d", "Bassi": "#d97878", "Archi": "#8fd9b0",
    "Ensemble/Voci": "#d9d98f", "Ottoni": "#e89d6d", "Ance": "#e86d9d",
    "Fiati": "#6de8c9", "Synth Lead": "#a06de8", "Synth Pad": "#6d9de8",
    "Synth FX": "#e86d6d", "Etnici": "#b0e86d", "Percussivi": "#e8a06d",
    "Effetti sonori": "#999999",
}
_PERCUSSION_COLOR = "#d98cd9"
# Tracce audio (core.model.AUDIO_INSTRUMENT_NAME): colore proprio, diverso da
# ogni famiglia strumentale, per distinguerle a colpo d'occhio.
AUDIO_TRACK_COLOR = "#8fc9a8"


def _family_color(instrument_name: str) -> str:
    if instrument_name == AUDIO_INSTRUMENT_NAME:
        return AUDIO_TRACK_COLOR
    try:
        instr = get_instrument(instrument_name)
    except ValueError:
        return "#5aa9e6"
    if instr.is_percussion:
        return _PERCUSSION_COLOR
    return _FAMILY_COLORS.get(gm_family_for_program(instr.gm_program), "#5aa9e6")


def _pan_label(value: int) -> str:
    if value == 64:
        return "C"
    offset = round((value - 64) / 63 * 100)
    return f"L{-offset}" if offset < 0 else f"R{offset}"
