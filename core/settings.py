"""
Impostazioni persistenti dell'applicazione, salvate in
~/.config/soundtext/settings.json su Linux (%APPDATA%\\SoundText\\ su
Windows, ~/Library/Application Support/SoundText/ su macOS), separate da
instruments.json. Gestisce il percorso del SoundFont (.sf2) predefinito
usato da fluidsynth per la riproduzione, eventuali override per singolo
strumento (vedi get_instrument_soundfont), ed e' pensato per essere esteso.
"""

import json
import os
import sys
from typing import Dict, List, Optional

# La variabile d'ambiente SOUNDTEXT_CONFIG_DIR sostituisce la cartella di
# configurazione (impostazioni, strumenti personalizzati, suoni del
# metronomo): la usano i test per non leggere ne' scrivere la configurazione
# reale dell'utente. Unica definizione: core.instruments la importa da qui.
if os.environ.get("SOUNDTEXT_CONFIG_DIR"):
    CONFIG_DIR = os.environ["SOUNDTEXT_CONFIG_DIR"]
elif sys.platform == "win32":
    CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "SoundText")
elif sys.platform == "darwin":
    CONFIG_DIR = os.path.expanduser("~/Library/Application Support/SoundText")
else:
    CONFIG_DIR = os.path.expanduser("~/.config/soundtext")
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")

_cache = None


def _load() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    data = {}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}
    _cache = data
    return data


def _save():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(_cache, f, indent=2, ensure_ascii=False)


def get_soundfont_path() -> Optional[str]:
    return _load().get("soundfont_path")


def set_soundfont_path(path: str):
    _load()
    _cache["soundfont_path"] = path
    _save()


def clear_soundfont_path():
    _load()
    _cache.pop("soundfont_path", None)
    _save()


def get_instrument_soundfont(instrument_name: str) -> Optional[str]:
    """SoundFont specifico per questo strumento (vedi Gestione strumenti),
    usato in riproduzione al posto di quello predefinito su tutti i canali
    MIDI assegnati a tracce con questo strumento. None se lo strumento non
    ha un override e deve usare il SoundFont predefinito."""
    return _load().get("instrument_soundfonts", {}).get(instrument_name)


def set_instrument_soundfont(instrument_name: str, path: str):
    _load()
    _cache.setdefault("instrument_soundfonts", {})[instrument_name] = path
    _save()


def clear_instrument_soundfont(instrument_name: str):
    _load()
    overrides = _cache.get("instrument_soundfonts")
    if overrides and instrument_name in overrides:
        del overrides[instrument_name]
        _save()


def get_all_instrument_soundfonts() -> Dict[str, str]:
    return dict(_load().get("instrument_soundfonts", {}))


def get_drum_kit_override(instrument_name: str) -> Optional[int]:
    """Numero di Program Change del drum kit General MIDI 2 (vedi
    core.instruments.GM_DRUM_KITS) scelto dall'utente per questo strumento a
    percussioni, applicato sopra al suo gm_program (vedi Gestione strumenti:
    a differenza degli altri campi, il kit percussioni si puo' cambiare
    anche per gli strumenti predefiniti come 'Drums'). None se lo strumento
    non ha un override e va usato il kit di base del profilo."""
    return _load().get("drum_kit_overrides", {}).get(instrument_name)


def set_drum_kit_override(instrument_name: str, program: int):
    _load()
    _cache.setdefault("drum_kit_overrides", {})[instrument_name] = int(program)
    _save()


def clear_drum_kit_override(instrument_name: str):
    _load()
    overrides = _cache.get("drum_kit_overrides")
    if overrides and instrument_name in overrides:
        del overrides[instrument_name]
        _save()


def get_all_drum_kit_overrides() -> Dict[str, int]:
    return dict(_load().get("drum_kit_overrides", {}))


def get_last_quantization_grid() -> int:
    return _load().get("audio_import_grid", 16)


def set_last_quantization_grid(denominator: int):
    _load()
    _cache["audio_import_grid"] = denominator
    _save()


def get_last_quantization_ternary() -> bool:
    return _load().get("audio_import_ternary", False)


def set_last_quantization_ternary(ternary: bool):
    _load()
    _cache["audio_import_ternary"] = ternary
    _save()


def get_theme() -> str:
    return _load().get("theme", "dark")


def set_theme(name: str):
    _load()
    _cache["theme"] = "light" if name == "light" else "dark"
    _save()


def get_metronome_sound() -> str:
    return _load().get("metronome_sound", "Click")


def set_metronome_sound(name: str):
    _load()
    _cache["metronome_sound"] = name
    _save()


def get_metronome_volume() -> int:
    return _load().get("metronome_volume", 80)


def set_metronome_volume(volume: int):
    _load()
    _cache["metronome_volume"] = max(0, min(100, int(volume)))
    _save()


def get_humanize_enabled() -> bool:
    return _load().get("humanize_enabled", False)


def set_humanize_enabled(value: bool):
    _load()
    _cache["humanize_enabled"] = bool(value)
    _save()


def get_humanize_amount() -> int:
    return _load().get("humanize_amount", 50)


def set_humanize_amount(amount: int):
    _load()
    _cache["humanize_amount"] = max(0, min(100, int(amount)))
    _save()


def get_playback_gain() -> float:
    """Guadagno lineare applicato dal synth fluidsynth in riproduzione
    (vedi core.playback): il default di fluidsynth (0.2) e' percepito come
    troppo silenzioso, ma un valore troppo alto satura il segnale PRIMA
    ancora che arrivi al driver audio, sentito come un crepitio/
    distorsione (con 1.2, su brani reali con mix densi, clippa oltre il 90%
    delle finestre da mezzo secondo). 0.9 e' un compromesso ragionevole; regolabile da Playback -> Volume di
    sintesi (gain)..."""
    return _load().get("playback_gain", 0.9)


def set_playback_gain(value: float):
    _load()
    _cache["playback_gain"] = max(0.1, min(2.0, float(value)))
    _save()


# Livello di latenza del synth in tempo reale per il dialogo "Suona con la
# tastiera" (Bassa/Media/Alta = 256/512/1024), espresso come dimensione del
# period in campioni a 48kHz: con 4 period ~21/43/85ms. Su Windows (WASAPI
# condiviso, che ignora la dimensione del period) si traduce invece nel
# numero di period, vedi core.playback._live_buffer_settings. Piu' basso =
# tasti piu' reattivi ma rischio di crepitii su macchine lente; la scelta
# giusta dipende dall'hardware, per questo e' regolabile dall'utente.
LIVE_PERIOD_SIZE_CHOICES = (256, 512, 1024)
LIVE_PERIOD_SIZE_DEFAULT = 512


def get_live_period_size() -> int:
    value = _load().get("live_period_size", LIVE_PERIOD_SIZE_DEFAULT)
    return value if value in LIVE_PERIOD_SIZE_CHOICES else LIVE_PERIOD_SIZE_DEFAULT


def set_live_period_size(value: int):
    if value not in LIVE_PERIOD_SIZE_CHOICES:
        return
    _load()
    _cache["live_period_size"] = value
    _save()


def get_midi_import_recognize_chords() -> bool:
    """Se vero, un gruppo di note simultanee riconosciuto come una qualita'
    di accordo nota viene importato in forma implicita (es. 'Cmaj7') invece
    che come blocco esplicito '[...]'. Predefinito falso: preserva sempre
    fedelmente il voicing/registro originale del MIDI, come prima
    dell'introduzione di questa opzione."""
    return _load().get("midi_import_recognize_chords", False)


def set_midi_import_recognize_chords(value: bool):
    _load()
    _cache["midi_import_recognize_chords"] = bool(value)
    _save()


# Soglia (in semitoni) sotto cui un pitch bend non e' un slide: 0,5 e' il
# minimo sensato (sotto, l'arrotondamento al semitono lo scarta comunque), 1,2
# coincide con la soglia di sempre su un canale con sensibilita' RPN di 12.
MIDI_IMPORT_SLIDE_THRESHOLD_MIN = 0.5
MIDI_IMPORT_SLIDE_THRESHOLD_MAX = 1.2
MIDI_IMPORT_SLIDE_THRESHOLD_DEFAULT = 0.8


def get_midi_import_slide_sensitive() -> bool:
    """Se vero, l'import MIDI usa la soglia slide personalizzata (vedi
    get_midi_import_slide_threshold) invece di quella di sempre. Predefinito
    falso: l'import resta identico a prima dell'introduzione dell'opzione."""
    return _load().get("midi_import_slide_sensitive", False)


def set_midi_import_slide_sensitive(value: bool):
    _load()
    _cache["midi_import_slide_sensitive"] = bool(value)
    _save()


def get_midi_import_slide_threshold() -> float:
    try:
        value = float(_load().get("midi_import_slide_threshold", MIDI_IMPORT_SLIDE_THRESHOLD_DEFAULT))
    except (TypeError, ValueError):
        value = MIDI_IMPORT_SLIDE_THRESHOLD_DEFAULT
    return max(MIDI_IMPORT_SLIDE_THRESHOLD_MIN, min(MIDI_IMPORT_SLIDE_THRESHOLD_MAX, value))


def set_midi_import_slide_threshold(value: float):
    _load()
    _cache["midi_import_slide_threshold"] = max(
        MIDI_IMPORT_SLIDE_THRESHOLD_MIN, min(MIDI_IMPORT_SLIDE_THRESHOLD_MAX, float(value)))
    _save()


def get_midi_import_min_bend_semitones():
    """Valore da passare a min_bend_semitones dell'import MIDI: la soglia
    scelta se l'opzione e' attiva, altrimenti None (comportamento di sempre)."""
    return get_midi_import_slide_threshold() if get_midi_import_slide_sensitive() else None


# --- Registrazione delle tracce audio (core.audio_recording) ---------------

def get_audio_input_device() -> str:
    """Etichetta ('nome (driver)') dell'ingresso scelto l'ultima volta."""
    return _load().get("audio_input_device", "")


def set_audio_input_device(label: str):
    _load()
    _cache["audio_input_device"] = label
    _save()


def get_input_latency_ms(device_label: str) -> float:
    """Compensazione manuale della latenza di registrazione per quel
    dispositivo (ms), in aggiunta a quella dichiarata dal driver."""
    return float(_load().get("input_latency_ms", {}).get(device_label, 0.0))


def set_input_latency_ms(device_label: str, value: float):
    _load()
    _cache.setdefault("input_latency_ms", {})[device_label] = float(value)
    _save()


def get_record_count_in_bars() -> int:
    return int(_load().get("record_count_in_bars", 1))


def set_record_count_in_bars(value: int):
    _load()
    _cache["record_count_in_bars"] = max(0, min(4, int(value)))
    _save()


def get_record_metronome() -> bool:
    return bool(_load().get("record_metronome", True))


def set_record_metronome(value: bool):
    _load()
    _cache["record_metronome"] = bool(value)
    _save()


def get_midi_input_port() -> str:
    """Nome dell'ultima tastiera MIDI scelta nel dialogo 'Suona con la
    tastiera' ('' = nessuna)."""
    return str(_load().get("midi_input_port", ""))


def set_midi_input_port(value: str):
    _load()
    _cache["midi_input_port"] = str(value or "")
    _save()


def get_plugin_dirs() -> List[str]:
    """Cartelle in piu' in cui cercare i plugin VST3 (oltre a quelle
    standard del sistema, vedi core.plugins.vst3_dirs)."""
    return list(_load().get("plugin_dirs", []))


def set_plugin_dirs(dirs: List[str]):
    _load()
    _cache["plugin_dirs"] = [d for d in dirs if d]
    _save()


def get_language() -> Optional[str]:
    """Lingua dell'interfaccia scelta in Opzioni ("it", "en", "fr", "es"),
    None se mai scelta (si usa quella del sistema, vedi core.i18n)."""
    return _load().get("language")


def set_language(code: str):
    """Vale dal prossimo avvio (vedi core.i18n)."""
    _load()
    _cache["language"] = code
    _save()
