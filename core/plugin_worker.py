"""
Processo separato che carica ed esegue i plugin VST3 (con pedalboard) e
LV2 (con core.lv2_host), e gli strumenti SFZ del motore interno
(core.sfz_engine, riferimento "sfz:/percorso/file.sfz"). Gira fuori dall'app perche' un plugin puo'
bloccarsi o andare in crash (alcuni synth VST3 si piantano gia' al
caricamento): se succede, core.plugins uccide questo processo e ne avvia
un altro, e SoundText resta in piedi.

Protocollo: sullo stdin arrivano richieste, sullo stdout escono risposte,
ciascuna come pickle preceduto dalla lunghezza (8 byte, little endian). Lo
stdout "vero" del processo viene spostato su stderr appena si parte,
perche' molti plugin scrivono messaggi con printf: finirebbero in mezzo
alle risposte.

Richieste (tuple con il nome dell'operazione in testa):
    ("ping",)
    ("list_lv2",)                              -> [descrittore, ...]
    ("describe", ref)                           -> descrittore con i parametri
    ("process", ref, rate, params, state, audio) -> audio (effetto)
    ("render", ref, rate, params, state, events, seconds) -> audio (strumento)
    ("strings", ref, params, state)             -> {parametro: testo mostrato dal plugin}
    ("editor", ref, params, state)              -> {"params": ..., "state": ...}
    ("live_start", ref, rate, params, state, blocksize, pan) -> {"hostapi": ..., "latency_ms": ...}
    ("live_midi", data)                         -> nessuna risposta
Risposta: ("ok", valore) oppure ("error", messaggio).

"live_start" apre l'uscita audio in questo processo e da allora lo
strumento suona i messaggi MIDI di "live_midi" appena arrivano (il
dialogo "Suona con la tastiera", vedi core.playback.LivePluginSynth): le
note non fanno avanti e indietro come audio, e un crash del plugin chiude
solo questo processo. "live_midi" non ha risposta, per non far aspettare
chi suona.
"""

import base64
import collections
import os
import pickle
import struct
import sys
import traceback

import numpy as np
from core.i18n import tr

# Parametri "tecnici" che alcuni VST3 (quelli fatti con DPF) espongono come
# parametri normali: non hanno senso da regolare a mano.
HIDDEN_VST3_PARAMS = {"buffer_size_frames", "sample_rate_frames"}


# Architetture dei VST3 per Windows: cartella dentro il bundle
# (Contents/<cartella>/) e codice "Machine" dell'intestazione PE della DLL.
_WIN_ARCH_DIRS = {"AMD64": ("x86_64-win", "arm64ec-win"), "ARM64": ("arm64-win", "arm64ec-win", "x86_64-win"),
                  "x86": ("x86-win",)}
_PE_MACHINES = {0x8664: "x64", 0x014C: "x86 (32 bit)", 0xAA64: "ARM64", 0xA641: "ARM64EC"}


def pe_machine(path: str) -> str:
    """L'architettura di una DLL Windows (dall'intestazione PE), o ''."""
    try:
        with open(path, "rb") as f:
            head = f.read(4096)
        offset = struct.unpack_from("<I", head, 0x3C)[0]
        if head[:2] != b"MZ" or head[offset:offset + 4] != b"PE\0\0":
            return ""
        return _PE_MACHINES.get(struct.unpack_from("<H", head, offset + 4)[0], "")
    except (OSError, struct.error):
        return ""


def vst3_binary(bundle: str, machine: str):
    """(DLL da caricare, cartelle di architettura presenti) di un VST3 per
    Windows: il file stesso se e' un VST3 "a file singolo", altrimenti
    quella in Contents/<arch>-win/ adatta a questa macchina (None se manca)."""
    if os.path.isfile(bundle):
        return bundle, []
    contents = os.path.join(bundle, "Contents")
    present = sorted(d for d in (os.listdir(contents) if os.path.isdir(contents) else [])
                     if d.lower().endswith("-win"))
    for arch in _WIN_ARCH_DIRS.get(machine, ("x86_64-win",)):
        folder = os.path.join(contents, arch)
        if os.path.isdir(folder):
            for name in sorted(os.listdir(folder)):
                if name.lower().endswith(".vst3"):
                    return os.path.join(folder, name), present
    return None, present


def _windows_machine() -> str:
    """L'architettura per cui gira questo Python: "AMD64", "ARM64" o "x86"."""
    import platform
    if struct.calcsize("P") == 4:
        return "x86"
    return {"amd64": "AMD64", "x86_64": "AMD64", "arm64": "ARM64", "aarch64": "ARM64"}.get(
        platform.machine().lower(), "AMD64")


def windows_load_diagnosis(bundle: str) -> str:
    """Perche' Windows non carica il VST3, quando pedalboard dice solo
    "unsupported plugin format or scan failure": la versione per questa
    architettura manca, la DLL e' di un'altra architettura, le manca una
    DLL di cui ha bisogno, o non esporta GetPluginFactory. '' se non si
    trova niente di preciso."""
    machine = _windows_machine()
    binary, present = vst3_binary(bundle, machine)
    expected = {"AMD64": "x64", "ARM64": "ARM64", "x86": "x86 (32 bit)"}[machine]
    if binary is None:
        return tr("il plugin non ha la versione per questo Windows ({expected}); dentro ci sono: {present}",
                  expected=expected, present=", ".join(present) or tr("nessuna"))
    arch = pe_machine(binary)
    if arch and arch != expected and not (machine == "ARM64" and arch in ("ARM64EC", "x64")):
        return tr("il plugin e' per {arch}, SoundText e' per {expected}", arch=arch, expected=expected)
    if sys.platform != "win32":
        return ""
    import ctypes
    try:
        dll = ctypes.WinDLL(binary)
    except OSError as e:
        return tr("Windows non carica {name}: {error}", name=os.path.basename(binary),
                  error=(e.strerror or str(e)).strip())
    if not hasattr(dll, "GetPluginFactory"):
        return tr("{name} non e' un plugin VST3 (manca GetPluginFactory)", name=os.path.basename(binary))
    return ""


def parse_ref(ref: str):
    """'vst3:/percorso/X.vst3' o 'vst3:/percorso/X.vst3|Nome' (bundle con piu'
    plugin), 'lv2:uri' -> (formato, percorso o uri, nome o None)."""
    fmt, _, rest = ref.partition(":")
    if fmt == "vst3":
        path, _, name = rest.partition("|")
        return fmt, path, name or None
    return fmt, rest, None


def _vst3_binary(path: str) -> str:
    """Su Windows pedalboard non riesce a leggere un VST3 dato come cartella
    bundle ("unsupported plugin format or scan failure", es. Surge XT, sfizz):
    gli si passa la DLL dentro Contents/<arch>-win adatta a questa macchina
    (vedi vst3_binary). Altrove il bundle va bene."""
    if sys.platform != "win32" or not os.path.isdir(path):
        return path
    binary, _present = vst3_binary(path, _windows_machine())
    return binary or path


def editor_position(rect, work):
    """Dove mettere la finestra dell'interfaccia di un plugin perche' si
    veda tutta, barra del titolo (e la X per chiuderla) compresa: rect e
    work sono (sinistra, alto, destra, basso) della finestra e dell'area di
    lavoro dello schermo. Se gia' sta dentro l'area resta dov'e' (None),
    altrimenti si centra; una finestra piu' grande dello schermo si
    allinea in alto a sinistra dell'area, cosi' la barra del titolo resta
    visibile."""
    left, top, right, bottom = rect
    w_left, w_top, w_right, w_bottom = work
    width, height = right - left, bottom - top
    if left >= w_left and top >= w_top and right <= w_right and bottom <= w_bottom:
        return None
    x = w_left + max(0, (w_right - w_left - width) // 2)
    y = w_top + max(0, (w_bottom - w_top - height) // 2)
    return x, y


def _place_editor_windows(stop, known=frozenset(), timeout: float = 15.0) -> None:
    """Solo Windows: la finestra dell'interfaccia di un plugin (aperta da
    pedalboard, che non ne sceglie la posizione) a volte compare in alto a
    sinistra con la barra del titolo fuori dallo schermo, senza la X per
    chiuderla. Si aspetta che compaia una nuova finestra di questo processo
    e la si sposta (vedi editor_position). 'known' sono le finestre che
    c'erano gia'; 'stop' si imposta quando l'interfaccia si chiude."""
    import ctypes
    import time
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    pid = os.getpid()
    deadline = time.monotonic() + timeout
    while not stop.is_set() and time.monotonic() < deadline:
        for hwnd in _process_windows(user32, pid):
            if hwnd in known:
                continue
            rect = wintypes.RECT()
            work = wintypes.RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                continue
            user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(work), 0)     # SPI_GETWORKAREA
            target = editor_position((rect.left, rect.top, rect.right, rect.bottom),
                                     (work.left, work.top, work.right, work.bottom))
            if target is not None:
                SWP_NOSIZE, SWP_NOZORDER = 0x0001, 0x0004
                user32.SetWindowPos(hwnd, None, target[0], target[1], 0, 0, SWP_NOSIZE | SWP_NOZORDER)
            user32.SetForegroundWindow(hwnd)
            return
        time.sleep(0.1)


def _process_windows(user32, pid: int) -> list:
    """Le finestre visibili di primo livello del processo pid (Windows)."""
    import ctypes
    from ctypes import wintypes
    found = []
    proto = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def each(hwnd, _lparam):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True
    user32.EnumWindows(proto(each), 0)
    return found


def _wasapi_output_device():
    """Su Windows l'uscita predefinita di PortAudio e' MME, con un buffer
    molto lungo: per suonare dal vivo si usa WASAPI (come LiveSynth)."""
    if sys.platform != "win32":
        return None
    import sounddevice as sd
    for api in sd.query_hostapis():
        if "WASAPI" in api["name"] and api["default_output_device"] >= 0:
            return api["default_output_device"]
    return None


class _Live:
    """Uno strumento che suona dal vivo: i messaggi MIDI arrivano in
    'pending' dal thread principale, il callback dell'uscita audio li
    passa allo strumento all'inizio del blocco successivo."""

    def __init__(self, inst, fmt: str, rate: int, pan: int = 64):
        self.inst, self.fmt, self.rate = inst, fmt, int(rate)
        self.pending = collections.deque()
        # pan a potenza costante, come core.effect_render.render_synth
        angle = (max(0, min(127, int(pan))) / 127.0) * np.pi / 2
        self.gains = np.array([np.cos(angle), np.sin(angle)], dtype=np.float32) * np.float32(np.sqrt(2.0))
        self.stream = None

    def render(self, frames: int) -> np.ndarray:
        msgs = []
        while self.pending:
            msgs.append(self.pending.popleft())
        if self.fmt == "vst3":
            y = self.inst.process([(m, 0.0) for m in msgs], duration=frames / self.rate,
                                  sample_rate=float(self.rate), num_channels=2, buffer_size=frames,
                                  reset=False).T
            out = np.zeros((frames, 2), dtype=np.float32)
            y = y[:frames, :2]
            out[:len(y), :y.shape[1]] = y
            if y.shape[1] == 1:
                out[:len(y), 1] = y[:, 0]
        else:
            out = self.inst.render([(0.0, m) for m in msgs], frames / self.rate)
        return out * self.gains

    def _callback(self, outdata, frames, _time_info, _status):
        try:
            outdata[:] = self.render(frames)
        except Exception:
            outdata.fill(0)

    def start(self, blocksize: int) -> dict:
        import sounddevice as sd
        self.stream = sd.OutputStream(samplerate=self.rate, channels=2, dtype="float32",
                                      blocksize=int(blocksize), latency=4 * int(blocksize) / self.rate,
                                      device=_wasapi_output_device(), callback=self._callback)
        self.stream.start()
        api = sd.query_hostapis(sd.query_devices(self.stream.device)["hostapi"])["name"]
        return {"hostapi": api, "latency_ms": round(self.stream.latency * 1000)}

    def stop(self):
        if self.stream is not None:
            self.stream.close()
            self.stream = None


class _Worker:
    def __init__(self):
        self.instances = {}          # (ref, rate) -> istanza
        self.applied_state = {}      # (ref, rate) -> stato gia' applicato
        self.live = None             # _Live, dopo "live_start"

    # -- caricamento -----------------------------------------------------
    def _vst3(self, ref: str):
        import pedalboard
        _fmt, path, name = parse_ref(ref)
        if not os.path.exists(path):
            raise RuntimeError(tr("plugin non trovato: {path}", path=path))
        binary = _vst3_binary(path)
        try:
            return pedalboard.VST3Plugin(binary, plugin_name=name) if name else pedalboard.VST3Plugin(binary)
        except Exception as e:
            # su Windows il messaggio di JUCE non dice perche': lo si cerca
            if sys.platform == "win32" and "Unable to scan plugin" in str(e):
                reason = windows_load_diagnosis(path)
                if reason:
                    raise RuntimeError(f"{e} — {reason}") from e
            raise

    def instance(self, ref: str, rate: int):
        key = (ref, int(rate))
        if key not in self.instances:
            fmt, target, _name = parse_ref(ref)
            if fmt == "vst3":
                self.instances[key] = self._vst3(ref)
            elif fmt == "lv2":
                from core.lv2_host import LV2Instance
                self.instances[key] = LV2Instance(target, int(rate))
            elif fmt == "sfz":
                from core.sfz_engine import SfzInstance
                self.instances[key] = SfzInstance(target, int(rate))
            else:
                raise RuntimeError(tr("formato di plugin sconosciuto: {fmt}", fmt=fmt))
        return self.instances[key]

    def configure(self, ref: str, rate: int, params: dict, state: str):
        inst = self.instance(ref, rate)
        key = (ref, int(rate))
        fmt = parse_ref(ref)[0]
        if fmt == "vst3":
            if state and self.applied_state.get(key) != state:
                try:
                    inst.raw_state = base64.b64decode(state)
                except Exception:
                    pass
                self.applied_state[key] = state
            # inst.parameters costa molto la prima volta (Surge XT: 10 s): solo se serve
            available = inst.parameters if params else {}
            for k, v in (params or {}).items():
                if k in available:
                    try:
                        available[k].raw_value = float(v)
                    except Exception:
                        pass
        elif fmt == "lv2":
            from core.lv2_host import decode_state
            files = decode_state(state)
            if set(inst.files) - set(files):
                # un file tolto non si "scarica": si riparte da un plugin nuovo
                inst.close()
                del self.instances[key]
                inst = self.instance(ref, rate)
            inst.set_values(params or {})
            inst.set_files(files)
        return inst

    # -- descrizione -----------------------------------------------------
    def describe(self, ref: str) -> dict:
        fmt, target, _name = parse_ref(ref)
        if fmt == "lv2":
            from core.lv2_host import lv2_plugin_info
            info = lv2_plugin_info(target)
            if info is None:
                raise RuntimeError(tr("plugin LV2 non trovato: {target}", target=target))
            return _lv2_descriptor(info)
        if fmt == "sfz":
            self.instance(ref, 48000)      # un file che non si carica si scopre qui
            return {"ref": ref, "format": "sfz", "name": os.path.splitext(os.path.basename(target))[0],
                    "vendor": "", "category": "SFZ", "instrument": True, "params": [], "state": "",
                    "problem": ""}
        inst = self.instance(ref, 48000)
        params = []
        for key, p in inst.parameters.items():
            if key in HIDDEN_VST3_PARAMS:
                continue
            # un parametro che non si lascia leggere si salta: il plugin resta usabile
            try:
                entry = {"key": key, "label": p.name, "minimum": 0.0, "maximum": 1.0,
                         "default": float(p.raw_value), "raw": True, "text": p.string_value,
                         "units": p.units or "", "toggled": False, "integer": False, "logarithmic": False,
                         "choices": []}
            except Exception:
                continue
            try:
                values = getattr(p, "valid_values", None)
                if values and 1 < len(values) <= 64 and all(isinstance(v, str) for v in values):
                    steps = len(values) - 1
                    entry["choices"] = [(i / steps, str(v)) for i, v in enumerate(values)]
                elif getattr(p, "type", None) is bool:
                    entry["toggled"] = True
            except Exception:
                pass
            params.append(entry)
        try:
            state = base64.b64encode(inst.raw_state).decode("ascii")
        except Exception:
            state = ""          # senza stato iniziale si usa lo stesso
        return {"ref": ref, "format": "vst3", "name": inst.name, "vendor": inst.manufacturer_name or "",
                "category": inst.category or "", "instrument": bool(inst.is_instrument),
                "params": params, "state": state, "problem": ""}

    def strings(self, ref: str, params: dict, state: str) -> dict:
        if parse_ref(ref)[0] != "vst3":
            return {}
        inst = self.configure(ref, 48000, params, state)
        return {k: p.string_value for k, p in inst.parameters.items() if k not in HIDDEN_VST3_PARAMS}

    def editor(self, ref: str, params: dict, state: str) -> dict:
        if parse_ref(ref)[0] != "vst3":
            raise RuntimeError(tr("l'interfaccia grafica e' disponibile solo per i plugin VST3"))
        inst = self.configure(ref, 48000, params, state)
        if sys.platform == "win32":
            import threading
            import ctypes
            stop = threading.Event()
            try:
                known = frozenset(_process_windows(ctypes.windll.user32, os.getpid()))
                threading.Thread(target=_place_editor_windows, args=(stop, known), daemon=True).start()
            except Exception:                         # non deve mai impedire di aprire l'interfaccia
                pass
            try:
                inst.show_editor()
            finally:
                stop.set()
        else:
            inst.show_editor()
        values = {k: float(p.raw_value) for k, p in inst.parameters.items() if k not in HIDDEN_VST3_PARAMS}
        new_state = base64.b64encode(inst.raw_state).decode("ascii")
        self.applied_state[(ref, 48000)] = new_state
        return {"params": values, "state": new_state}

    # -- audio -----------------------------------------------------------
    def process(self, ref, rate, params, state, audio):
        if parse_ref(ref)[0] == "sfz":
            raise RuntimeError(tr("uno strumento SFZ non elabora audio"))
        inst = self.configure(ref, rate, params, state)
        audio = np.ascontiguousarray(audio, dtype=np.float32)
        if parse_ref(ref)[0] == "vst3":
            y = inst.process(np.ascontiguousarray(audio.T), float(rate), reset=True).T
            if y.ndim == 1:
                y = y[:, None]
            if y.shape[1] == 1:
                y = np.repeat(y, 2, axis=1)
            out = np.zeros((len(audio), 2), dtype=np.float32)
            out[:min(len(y), len(out))] = y[:len(out), :2]
            return out
        inst.reset()
        return inst.process(audio)

    def render(self, ref, rate, params, state, events, seconds):
        inst = self.configure(ref, rate, params, state)
        if parse_ref(ref)[0] == "vst3":
            y = inst.process([(bytes(data), float(t)) for t, data in events], duration=float(seconds),
                             sample_rate=float(rate), num_channels=2, reset=True)
            return np.ascontiguousarray(y.T[:, :2], dtype=np.float32)
        inst.reset()
        return inst.render([(float(t), bytes(data)) for t, data in events], float(seconds))

    def live_start(self, ref, rate, params, state, blocksize, pan):
        if self.live is not None:
            self.live.stop()
            self.live = None
        inst = self.configure(ref, rate, params, state)
        fmt = parse_ref(ref)[0]
        inst.reset()
        if fmt == "sfz":
            inst.set_realtime()
        live = _Live(inst, fmt, rate, pan)
        info = live.start(blocksize)
        self.live = live
        return info

    def handle(self, request):
        op = request[0]
        if op == "live_midi":
            if self.live is not None:
                self.live.pending.append(bytes(request[1]))
            return None
        if op == "live_start":
            return self.live_start(*request[1:])
        if op == "ping":
            return "pong"
        if op == "_sleep":          # solo per i test: un plugin che non risponde
            import time
            time.sleep(float(request[1]))
            return "sveglio"
        if op == "_crash":          # solo per i test: un plugin che fa cadere il processo
            os._exit(3)
        if op == "list_lv2":
            from core.lv2_host import list_lv2_plugins
            return [_lv2_descriptor(i, with_params=False) for i in list_lv2_plugins()]
        if op == "describe":
            return self.describe(request[1])
        if op == "strings":
            return self.strings(*request[1:])
        if op == "editor":
            return self.editor(*request[1:])
        if op == "process":
            return self.process(*request[1:])
        if op == "render":
            return self.render(*request[1:])
        raise RuntimeError(tr("richiesta sconosciuta: {op}", op=op))


def _lv2_descriptor(info, with_params: bool = True) -> dict:
    out = {"ref": "lv2:" + info.uri, "format": "lv2", "name": info.name, "vendor": info.author,
           "category": info.category, "instrument": info.instrument, "problem": info.problem,
           "params": [], "state": ""}
    if with_params:
        out["params"] = [{"key": p.symbol, "label": p.name, "minimum": p.minimum, "maximum": p.maximum,
                          "default": p.default, "raw": False, "text": "", "units": "",
                          "toggled": p.toggled, "integer": p.integer, "logarithmic": p.logarithmic,
                          "choices": p.choices} for p in info.params]
        out["files"] = [{"key": f.uri, "label": f.label} for f in info.files]
    return out


def _read_exact(stream, n: int) -> bytes:
    data = b""
    while len(data) < n:
        chunk = stream.read(n - len(data))
        if not chunk:
            raise EOFError
        data += chunk
    return data


def main():
    # Lo stdout del processo diventa quello del protocollo; quello che i
    # plugin scrivono con printf va su stderr.
    proto_out = os.fdopen(os.dup(1), "wb")
    os.dup2(2, 1)
    sys.stdout = sys.stderr
    proto_in = sys.stdin.buffer
    worker = _Worker()
    while True:
        try:
            size = struct.unpack("<Q", _read_exact(proto_in, 8))[0]
            request = pickle.loads(_read_exact(proto_in, size))
        except EOFError:
            return
        try:
            reply = ("ok", worker.handle(request))
        except Exception as e:     # l'errore del plugin torna all'app come testo
            traceback.print_exc()
            reply = ("error", str(e) or e.__class__.__name__)
        if request[0] == "live_midi":
            continue
        data = pickle.dumps(reply, protocol=pickle.HIGHEST_PROTOCOL)
        proto_out.write(struct.pack("<Q", len(data)) + data)
        proto_out.flush()


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    main()
