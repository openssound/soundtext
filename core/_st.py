"""
Collega la libreria st_language (la notazione, usabile anche senza
SoundText) al resto del programma: i suoi messaggi passano dalle
traduzioni di SoundText (core.i18n) e i riferimenti &Nome si risolvono
nella libreria MIDI (core.midi_library).
"""

from st_language import _i18n, notation

from .i18n import tr


def _midi_ref_tokens(name_path, midi_dir):
    from . import midi_library     # import locale: evita una dipendenza circolare
    return midi_library.get_midi_ref_tokens(name_path, midi_dir)


_i18n.set_translator(tr)
notation.set_midi_ref_resolver(_midi_ref_tokens)
