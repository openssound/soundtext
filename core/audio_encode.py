"""
L'audio esportato in formati compressi: MP3, FLAC e OGG Vorbis, oltre al WAV.

write_audio(percorso, campioni, ...) sceglie il formato dall'estensione. Il
WAV si scrive come sempre (core.audio_tracks.write_wav, 24 bit, con il
tempo nel blocco "acid"); per gli altri formati si scrive un WAV temporaneo
e lo si converte in un processo a parte, con pedalboard (gia' fra le
dipendenze: ha dentro LAME, FLAC e Vorbis). Il processo a parte serve
perche' su alcuni processori senza AVX il codificatore MP3 di pedalboard
termina il programma con "istruzione non consentita" (SIGILL), che in Python
non si puo' intercettare: cosi' cade solo il processo di conversione, e
SoundText prova con "lame" o "ffmpeg" del sistema, se ci sono.

Il processo si avvia come "SoundText --converti-audio wav uscita" nell'app
impacchettata (vedi main.py), o come "python core/audio_encode.py wav uscita"
dai sorgenti. Qui il processo figlio usa solo numpy e pedalboard, senza
importare il resto di core.
"""

import os
import shutil
import subprocess
import sys
import tempfile

# estensione -> (nome mostrato, filtro del dialogo "Salva")
FORMATS = {
    ".wav": "WAV",
    ".mp3": "MP3",
    ".flac": "FLAC",
    ".ogg": "OGG Vorbis",
}
DEFAULT_FORMAT = ".wav"

MP3_QUALITY = "V0"           # VBR di LAME, il migliore (circa 220-260 kbps)
OGG_QUALITY = "256 kbps"
FLAC_BIT_DEPTH = 24
ENCODE_TIMEOUT = 600         # secondi


def format_of(path: str) -> str:
    """L'estensione di path se e' un formato supportato, altrimenti ''."""
    ext = os.path.splitext(path)[1].lower()
    return ext if ext in FORMATS else ""


def file_filter(ext: str) -> str:
    """Il filtro del dialogo "Salva" per il formato, es. "MP3 (*.mp3)"."""
    return f"{FORMATS[ext]} (*{ext})"


def all_filters() -> list:
    """I filtri di tutti i formati, nell'ordine di FORMATS."""
    return [file_filter(ext) for ext in FORMATS]


def ext_from_filter(selected_filter: str) -> str:
    """L'estensione del filtro scelto nel dialogo (WAV se non si riconosce)."""
    for ext in FORMATS:
        if selected_filter == file_filter(ext):
            return ext
    return DEFAULT_FORMAT


def with_extension(path: str, ext: str) -> str:
    """path con l'estensione ext: se ne ha gia' una dei formati la sostituisce,
    altrimenti la aggiunge (un nome come "Brano 1.2" resta intero)."""
    if format_of(path):
        return os.path.splitext(path)[0] + ext
    return path + ext


def write_audio(path: str, samples, samplerate: int, tempo=None, meter=(4, 4)) -> None:
    """Scrive samples (float, forma (frame, canali), [-1, 1]) nel formato
    dell'estensione di path: WAV 24 bit (con il tempo, vedi write_wav), MP3,
    FLAC 24 bit o OGG Vorbis. Solleva RuntimeError se la conversione non
    riesce in nessun modo."""
    from .audio_tracks import write_wav
    ext = format_of(path) or DEFAULT_FORMAT
    if ext == ".wav":
        write_wav(path, samples, samplerate, bits=24, tempo=tempo, meter=meter)
        return
    fd, tmp = tempfile.mkstemp(suffix=".wav", prefix="soundtext_export_")
    os.close(fd)
    try:
        write_wav(tmp, samples, samplerate, bits=24)
        convert_wav(tmp, path)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def convert_wav(wav_path: str, out_path: str) -> str:
    """Converte il WAV wav_path in out_path (formato dall'estensione).
    Ritorna con che cosa ("pedalboard", "lame", "ffmpeg"); RuntimeError se
    non ci riesce nessuno."""
    from .i18n import tr
    ext = format_of(out_path)
    if ext in ("", ".wav"):
        raise ValueError(f"Formato non convertibile: {out_path}")
    errors = []
    try:
        result = subprocess.run(_child_command(wav_path, out_path), capture_output=True, text=True,
                                timeout=ENCODE_TIMEOUT, **_no_window())
        if result.returncode == 0 and _nonempty(out_path):
            return "pedalboard"
        errors.append(_describe_failure("pedalboard", result.returncode, result.stderr))
    except (OSError, subprocess.TimeoutExpired) as e:
        errors.append(f"pedalboard: {e}")
    for name, command in _system_commands(ext, wav_path, out_path):
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=ENCODE_TIMEOUT,
                                    **_no_window())
        except (OSError, subprocess.TimeoutExpired) as e:
            errors.append(f"{name}: {e}")
            continue
        if result.returncode == 0 and _nonempty(out_path):
            return name
        errors.append(_describe_failure(name, result.returncode, result.stderr))
    _remove_quietly(out_path)
    raise RuntimeError(tr("Impossibile creare il file {fmt}: il codificatore non funziona su questo computer. "
                          "Esporta in WAV, oppure installa \"lame\" o \"ffmpeg\" e riprova.\n\nDettagli:\n{details}",
                          fmt=FORMATS[ext], details="\n".join(errors)))


def _nonempty(path: str) -> bool:
    return os.path.isfile(path) and os.path.getsize(path) > 0


def _remove_quietly(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


def _describe_failure(name: str, code: int, stderr: str) -> str:
    last = (stderr or "").strip().splitlines()[-1:] or [""]
    if code in (-4, 132):
        return f"{name}: istruzione non consentita dal processore (SIGILL)"
    return f"{name}: codice {code} {last[0]}".strip()


def _no_window() -> dict:
    """Su Windows il processo figlio non apre una finestra di console."""
    if sys.platform == "win32":
        return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    return {}


def _child_command(wav_path: str, out_path: str) -> list:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--converti-audio", wav_path, out_path]
    return [sys.executable, os.path.abspath(__file__), wav_path, out_path]


def _system_commands(ext: str, wav_path: str, out_path: str) -> list:
    """I programmi del sistema da provare se pedalboard non ce la fa."""
    commands = []
    lame = shutil.which("lame")
    if ext == ".mp3" and lame:
        commands.append(("lame", [lame, "--quiet", "-V", "0", wav_path, out_path]))
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        codec = {".mp3": ["-c:a", "libmp3lame", "-q:a", "0"],
                 ".flac": ["-c:a", "flac", "-sample_fmt", "s32"],
                 ".ogg": ["-c:a", "libvorbis", "-b:a", "256k"]}[ext]
        commands.append(("ffmpeg", [ffmpeg, "-y", "-loglevel", "error", "-i", wav_path, *codec, out_path]))
    return commands


# ---------------------------------------------------------------------------
# Il processo di conversione
# ---------------------------------------------------------------------------

def encode_main(argv) -> int:
    """Converte argv[0] (WAV) in argv[1] con pedalboard. Codice 0 se riesce."""
    if len(argv) != 2:
        sys.stderr.write("uso: audio_encode.py ingresso.wav uscita.(mp3|flac|ogg)\n")
        return 2
    from pedalboard.io import AudioFile
    src, dst = argv
    ext = os.path.splitext(dst)[1].lower()
    kwargs = {}
    if ext == ".mp3":
        kwargs["quality"] = MP3_QUALITY
    elif ext == ".ogg":
        kwargs["quality"] = OGG_QUALITY
    elif ext == ".flac":
        kwargs["bit_depth"] = FLAC_BIT_DEPTH
    with AudioFile(src) as reader:
        rate, channels = reader.samplerate, reader.num_channels
        with AudioFile(dst, "w", rate, channels, **kwargs) as writer:
            block = int(rate) * 10
            while reader.tell() < reader.frames:
                writer.write(reader.read(block))
    return 0


if __name__ == "__main__":
    sys.exit(encode_main(sys.argv[1:]))
