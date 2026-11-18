"""
Permesso del microfono su macOS (Impostazioni di Sistema -> Privacy e
sicurezza -> Microfono).

Se l'utente nega il permesso, macOS non da' errori: la scheda audio si apre
lo stesso e registra silenzio. La finestra di registrazione
(gui.audio_record_dialog) lo chiede qui prima di partire e alla fine della
ripresa, per dire all'utente dove riattivarlo.

Si chiede ad AVFoundation con ctypes (AVCaptureDevice
authorizationStatusForMediaType:), senza dipendenze in piu'. Fuori da
macOS, o se la chiamata non riesce, lo stato e' "" (sconosciuto) e la
registrazione procede come sempre.
"""

import ctypes
import ctypes.util
import sys

# AVAuthorizationStatus
_STATUS = {0: "not_determined", 1: "restricted", 2: "denied", 3: "authorized"}
SETTINGS_URL = "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"


def microphone_status() -> str:
    """"authorized", "denied", "restricted", "not_determined" o "" se non
    si sa (non macOS, o AVFoundation non risponde)."""
    if sys.platform != "darwin":
        return ""
    try:
        objc = ctypes.CDLL(ctypes.util.find_library("objc"))
        av = ctypes.CDLL("/System/Library/Frameworks/AVFoundation.framework/AVFoundation")
        objc.objc_getClass.restype = ctypes.c_void_p
        objc.objc_getClass.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]
        send = ctypes.CFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(
            ("objc_msgSend", objc))
        device = objc.objc_getClass(b"AVCaptureDevice")
        media_audio = ctypes.c_void_p.in_dll(av, "AVMediaTypeAudio")
        if not device or not media_audio.value:
            return ""
        status = send(device, objc.sel_registerName(b"authorizationStatusForMediaType:"), media_audio.value)
        return _STATUS.get(int(status), "")
    except (OSError, AttributeError, ValueError, TypeError):
        return ""


def microphone_blocked() -> bool:
    """Se macOS non lascia registrare (permesso negato o vietato da un
    profilo di gestione)."""
    return microphone_status() in ("denied", "restricted")
