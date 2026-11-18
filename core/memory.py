"""
Memoria del computer e limiti delle cache in memoria.

Le cache dei moduli audio (file decodificati, time-stretch, uscite NAM,
tracce elaborate) hanno un limite in byte che dipende dalla RAM fisica: il
25% del totale, fra 400 MB e 4 GB, diviso fra le quattro cache nelle
proporzioni di sempre (con 8 GB i limiti restano quelli di prima, con 4 GB
si dimezzano). La variabile d'ambiente SOUNDTEXT_CACHE_MB forza il totale.

clear_memory_caches() svuota tutte le cache (alla chiusura o all'apertura
di un progetto, e fra un test e l'altro); peak_rss_mb() da' il picco di
memoria del processo, per il log degli export.
"""

import logging
import os
import sys
from typing import Optional

MB = 1024 * 1024
GB = 1024 * MB

CACHE_SHARE_OF_RAM = 0.25
CACHE_MIN_BYTES = 400 * MB
CACHE_MAX_BYTES = 4 * GB
# proporzioni fra le cache (512 + 600 + 256 + 256 MB di prima)
CACHE_SPLIT = {"decoded": 0.32, "stem": 0.37, "stretch": 0.16, "nam": 0.15}
CACHE_ENV = "SOUNDTEXT_CACHE_MB"

# memoria di uno stem durante il render: frame x 2 canali x 4 byte per i
# buffer intermedi degli effetti (misurato: circa 6 copie)
STEM_MEMORY_FACTOR = 6
MAX_RENDER_WORKERS = 8


def _windows_memory():
    import ctypes

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

    status = MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return None
    return status.ullTotalPhys, status.ullAvailPhys


def total_ram() -> Optional[int]:
    """La RAM fisica in byte (None se non si riesce a saperlo)."""
    try:
        if sys.platform == "win32":
            info = _windows_memory()
            return info[0] if info else None
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (ValueError, OSError, AttributeError):
        return None


def _linux_available() -> Optional[int]:
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    return None


def available_ram() -> Optional[int]:
    """La RAM libera in questo momento, in byte. Su Linux MemAvailable
    (comprende la cache dei file, che il sistema libera quando serve); su
    macOS, senza psutil, una stima prudente: un terzo della RAM fisica."""
    try:
        if sys.platform == "win32":
            info = _windows_memory()
            return info[1] if info else None
        if sys.platform.startswith("linux"):
            value = _linux_available()
            if value is not None:
                return value
            return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_AVPHYS_PAGES")
    except (ValueError, OSError, AttributeError):
        return None
    try:
        import psutil
        return int(psutil.virtual_memory().available)
    except Exception:
        pass
    if sys.platform == "darwin":
        value = _macos_available()
        if value is not None:
            return value
    total = total_ram()
    return total // 3 if total else None


def _macos_available() -> Optional[int]:
    """Pagine libere, inattive e riutilizzabili (vm_stat), come la memoria
    disponibile di Monitoraggio Attivita'."""
    import re
    import subprocess
    try:
        out = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=2).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    size = re.search(r"page size of (\d+) bytes", out)
    pages = 0
    for key in ("Pages free", "Pages inactive", "Pages speculative", "Pages purgeable"):
        match = re.search(re.escape(key) + r":\s+(\d+)", out)
        if match:
            pages += int(match.group(1))
    return pages * int(size.group(1)) if size and pages else None


def cache_budget_total(ram: Optional[int] = None) -> int:
    """Il totale delle cache in memoria, in byte."""
    forced = os.environ.get(CACHE_ENV, "").strip()
    if forced:
        try:
            return max(16 * MB, int(float(forced) * MB))
        except ValueError:
            logging.getLogger(__name__).warning("%s non valido: %r", CACHE_ENV, forced)
    ram = total_ram() if ram is None else ram
    if not ram:
        return int(1.6 * GB)                          # i limiti di prima
    return int(min(CACHE_MAX_BYTES, max(CACHE_MIN_BYTES, ram * CACHE_SHARE_OF_RAM)))


def cache_budget(name: str, ram: Optional[int] = None) -> int:
    """Il limite in byte della cache 'name' (decoded, stem, stretch, nam)."""
    return int(cache_budget_total(ram) * CACHE_SPLIT[name])


def render_workers(frames: int, jobs: int, channels: int = 2, available: Optional[int] = None,
                   cpus: Optional[int] = None) -> int:
    """Quante tracce elaborare insieme: non piu' di 8, dei core, delle
    tracce, e di quante ne stanno nella meta' della RAM libera."""
    cpus = cpus if cpus is not None else (os.cpu_count() or 1)
    limit = max(1, min(MAX_RENDER_WORKERS, cpus, jobs))
    available = available_ram() if available is None else available
    if available and frames > 0:
        per_stem = max(1, frames * channels * 4 * STEM_MEMORY_FACTOR)
        limit = max(1, min(limit, int(available * 0.5) // per_stem))
    return limit


def clear_memory_caches() -> None:
    """Svuota le cache in memoria di tutti i moduli (gia' importati)."""
    for name in ("core.audio_tracks", "core.effect_render", "core.effects", "core.clip_preview",
                 "core.audio_percussion"):
        module = sys.modules.get(name)
        clear = getattr(module, "clear_caches", None) if module is not None else None
        if clear is not None:
            clear()


def peak_rss_mb() -> Optional[float]:
    """Il picco di memoria del processo, in MB (None se non disponibile)."""
    try:
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes

            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

            counters = PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(counters)
            # i tipi a 64 bit: senza, l'handle (-1, il processo corrente)
            # passava troncato e la chiamata falliva
            current = ctypes.windll.kernel32.GetCurrentProcess
            current.restype = wintypes.HANDLE
            info = ctypes.windll.psapi.GetProcessMemoryInfo
            info.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wintypes.DWORD]
            info.restype = wintypes.BOOL
            if not info(current(), ctypes.byref(counters), counters.cb):
                return None
            return counters.PeakWorkingSetSize / MB
        import resource
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return peak / MB if sys.platform == "darwin" else peak / 1024.0   # macOS in byte, Linux in kB
    except Exception:
        return None
