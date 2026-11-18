"""
Test delle ottimizzazioni di memoria e prestazioni: limiti adattivi delle
cache (core.memory), thread dei render, buffer a 32 bit, cache su disco
con limite complessivo, versione del formato e mmap, validazione ritardata
nell'editor.

Esecuzione:
    python3 -m pytest tests/test_memory_performance.py -v
"""

import _config_isolation  # noqa: F401  (isola la configurazione: prima di importare core)

import os
import time

import numpy as np
import pytest

from core import disk_cache, memory

GB = 1024 ** 3
MB = 1024 ** 2


def test_cache_budget_follows_the_ram(monkeypatch):
    monkeypatch.delenv(memory.CACHE_ENV, raising=False)
    eight = memory.cache_budget_total(8 * GB)
    four = memory.cache_budget_total(4 * GB)
    assert eight == 2 * GB and four == GB                       # il 25%
    assert memory.cache_budget_total(512 * MB) == memory.CACHE_MIN_BYTES
    assert memory.cache_budget_total(64 * GB) == memory.CACHE_MAX_BYTES
    parts = sum(memory.cache_budget(n, 8 * GB) for n in memory.CACHE_SPLIT)
    assert abs(parts - eight) < 16                              # le proporzioni fanno il totale
    monkeypatch.setenv(memory.CACHE_ENV, "800")
    assert memory.cache_budget_total(64 * GB) == 800 * MB


def test_ram_is_known_on_this_system():
    total, free = memory.total_ram(), memory.available_ram()
    assert total and total > 256 * MB
    assert free and 0 < free <= total
    assert memory.peak_rss_mb() and memory.peak_rss_mb() > 10


def test_render_workers_shrink_with_little_free_ram():
    frames = 48000 * 120                                        # due minuti
    assert memory.render_workers(frames, 8, available=64 * GB, cpus=16) == 8
    small = memory.render_workers(frames, 8, available=2 * GB, cpus=16)
    assert 1 <= small < 8
    assert memory.render_workers(frames, 8, available=10 * MB, cpus=16) == 1
    assert memory.render_workers(frames, 3, available=64 * GB, cpus=16) == 3   # non piu' delle tracce
    assert memory.render_workers(frames, 8, available=64 * GB, cpus=2) == 2    # ne' dei core


def test_render_stems_uses_fewer_threads_with_4_gb(monkeypatch):
    from core import effect_render
    monkeypatch.setattr(memory, "available_ram", lambda: 2 * GB)   # meta' di 4 GB libera
    requests = [object()] * 8
    workers = effect_render.stem_workers(requests, frames=48000 * 240)
    assert 1 <= workers < 8


def test_clear_memory_caches_empties_every_module():
    from core import audio_tracks, clip_preview, effect_render, effects
    audio_tracks._decoded[("x",)] = (np.zeros((4, 2), np.float32), 48000)
    audio_tracks._stretch_cache[("y",)] = np.zeros(4)
    effect_render._cache["z"] = np.zeros(4)
    effects._nam_out_cache[("w",)] = np.zeros(4)
    clip_preview._cache[("v",)] = None
    memory.clear_memory_caches()
    assert not audio_tracks._decoded and not audio_tracks._stretch_cache
    assert not effect_render._cache and not effects._nam_out_cache and not clip_preview._cache


def test_mix_layers_keeps_the_base_and_grows_once():
    from core.audio_tracks import mix_layers
    base = np.full((100, 2), 0.25, np.float32)
    stem = np.full((50, 2), 0.5, np.float32)
    out = mix_layers(base, 48000, [], stems=[(stem, 80 / 48000)])
    assert out.dtype == np.float32 and out.shape == (130, 2)
    assert np.allclose(out[:80], 0.25) and np.allclose(out[80:100], 0.75) and np.allclose(out[100:], 0.5)
    assert np.allclose(base, 0.25)                               # base non si tocca


def test_convolution_and_oversampling_write_32_bit_output():
    from core import effects
    rng = np.random.default_rng(3)
    x = (rng.standard_normal((70000, 2)) * 0.2).astype(np.float32)
    ir = rng.standard_normal(500) * 0.01
    y = effects._convolve(x, ir)
    assert y.dtype == np.float32 and y.shape == x.shape
    ref = np.stack([np.convolve(x[:, c].astype(np.float64), ir)[:len(x)] for c in range(2)], axis=1)
    assert np.max(np.abs(y - ref)) < 1e-6                       # sotto -120 dB
    z = effects._oversampled([effects.Saturation(6.0)])(x, 48000)
    assert z.dtype == np.float32 and z.shape == x.shape


# ---------------------------------------------------------------------------
# Cache su disco
# ---------------------------------------------------------------------------

@pytest.fixture
def two_projects(tmp_path, monkeypatch):
    # un registro solo per il test: quello del processo elenca anche le cache
    # degli altri test (con pytest -n, nello stesso processo)
    registry = str(tmp_path / "registry.json")
    monkeypatch.setattr(disk_cache, "_registry_path", lambda: registry)
    yield tmp_path / "A.st", tmp_path / "B.st"
    disk_cache.wait_writes()
    disk_cache.set_project(None)


def _fill(key, mb=1):
    disk_cache.store(key, np.zeros((mb * MB // 8, 2), np.float32), wait=True)


def test_global_limit_removes_the_oldest_files_of_every_project(two_projects):
    a, b = two_projects
    disk_cache.set_project(str(a))
    _fill("a1")
    dir_a = disk_cache.cache_dir()
    old = time.time() - 1000
    for name in os.listdir(dir_a):
        os.utime(os.path.join(dir_a, name), (old, old))
    disk_cache.set_project(str(b))
    _fill("b1")
    _fill("b2")
    assert os.path.abspath(dir_a) in disk_cache.registered_dirs()
    assert disk_cache.total_size() >= 3 * MB
    removed = disk_cache.prune_global(max_bytes=int(2.5 * MB))
    assert removed == 1
    assert disk_cache.dir_size(dir_a) == 0                       # il piu' vecchio era di A
    assert disk_cache.load("b1") is not None and disk_cache.load("b2") is not None


def test_clear_all_and_removed_projects_leave_the_registry(two_projects):
    import shutil
    a, b = two_projects
    disk_cache.set_project(str(a))
    _fill("a1")
    dir_a = disk_cache.cache_dir()
    disk_cache.set_project(str(b))
    _fill("b1")
    assert disk_cache.clear_all() >= 2 * MB
    assert disk_cache.total_size() == 0
    shutil.rmtree(os.path.dirname(dir_a))                      # il progetto A non c'e' piu'
    assert os.path.abspath(dir_a) not in disk_cache.registered_dirs()


def test_cache_files_are_mapped_and_old_formats_go_first(two_projects):
    a, _b = two_projects
    disk_cache.set_project(str(a))
    _fill("k")
    data = disk_cache.load("k")
    assert isinstance(data, np.memmap) and not data.flags.writeable
    directory = disk_cache.cache_dir()
    stale = os.path.join(directory, "0" * 40 + ".npy")            # formato di prima
    np.save(stale, np.zeros((MB // 8, 2), np.float32))
    assert disk_cache.prune(directory, max_bytes=10 * MB) == 1    # sotto il limite, ma vecchio
    assert not os.path.exists(stale) and disk_cache.load("k") is not None


# ---------------------------------------------------------------------------
# Validazione ritardata nell'editor
# ---------------------------------------------------------------------------

def test_typing_validates_once_after_a_pause():
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from gui.main_window import MainWindow
    w = MainWindow()
    bar = "c d e f g a b c"
    w.project.add_track("Piano", "Piano", "8: " + " | ".join(bar for _ in range(500)) + " |")
    w.refresh_mixer()
    w.select_track("Piano")
    w._dirty = False
    calls = []
    original = w._validate_current

    def counting():
        calls.append(time.monotonic())
        original()
    timer = w._validation_timer_obj()
    timer.timeout.disconnect()
    timer.timeout.connect(counting)
    # l'attesa piu' lunga dei tasti anche su una macchina carica (test in parallelo)
    timer.setInterval(2000)
    cursor = w.editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    w.editor.setTextCursor(cursor)
    for _ in range(20):                                      # 20 tasti di fila
        QTest.keyClick(w.editor, "x")
    assert calls == [] and timer.isActive()                  # nessuna validazione mentre si scrive
    typed_at = time.monotonic()
    deadline = typed_at + 10.0
    while not calls and time.monotonic() < deadline:
        QTest.qWait(20)
    assert len(calls) == 1                                   # una sola, dopo la pausa
    assert calls[0] - typed_at >= 1.5
    assert "Sintassi valida" not in w.validation_label.text()    # le x sono un errore
    # con l'intervallo vero arriva entro circa un quarto di secondo
    timer.setInterval(w.VALIDATION_DELAY_MS)
    start = time.monotonic()
    QTest.keyClick(w.editor, "x")
    while len(calls) < 2 and time.monotonic() < start + 5.0:
        QTest.qWait(10)
    assert len(calls) == 2 and calls[1] - start >= 0.2


def test_flush_validation_validates_at_once():
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from gui.main_window import MainWindow
    w = MainWindow()
    w.project.add_track("Piano", "Piano", "4: c d e f |")
    w.refresh_mixer()
    w.select_track("Piano")
    w.editor.setPlainText("4: c d e f | zzz")
    w.flush_validation()
    assert "Sintassi valida" not in w.validation_label.text()
    w.editor.setPlainText("4: c d e f |")
    w.flush_validation()
    assert "Sintassi valida" in w.validation_label.text()


def test_global_prune_never_touches_the_open_project(two_projects):
    a, b = two_projects
    disk_cache.set_project(str(a))
    _fill("a1")
    disk_cache.set_project(str(b))                          # B e' il progetto aperto
    _fill("b1")
    _fill("b2")
    dir_b = disk_cache.cache_dir()
    old = time.time() - 1000
    for name in os.listdir(dir_b):                          # i file di B sono i piu' vecchi
        os.utime(os.path.join(dir_b, name), (old, old))
    disk_cache.prune_global(max_bytes=MB // 2)
    assert disk_cache.load("b1") is not None and disk_cache.load("b2") is not None
    assert disk_cache.dir_size(os.path.join(os.path.dirname(dir_b), "..", "A_audio", "cache")) == 0


def test_a_file_in_use_does_not_make_prune_remove_the_newer_ones(tmp_path, monkeypatch):
    directory = tmp_path / "cache"
    directory.mkdir()
    paths = []
    for i in range(3):
        path = directory / f"{i:040d}{disk_cache.SUFFIX}"
        np.save(path, np.zeros((MB // 8, 2), np.float32))
        os.utime(path, (1000 + i, 1000 + i))
        paths.append(str(path))
    real_remove = os.remove

    def remove(path):
        if path == paths[0]:
            raise PermissionError("in uso")                 # come un file mappato su Windows
        real_remove(path)
    monkeypatch.setattr(os, "remove", remove)
    disk_cache.prune(str(directory), max_bytes=int(2.5 * MB))
    assert all(os.path.exists(p) for p in paths)            # niente da togliere al suo posto


def test_stale_library_copies_are_removed(tmp_path, monkeypatch):
    import sys
    from core import sfz_engine
    if sys.platform == "win32":
        pytest.skip("su Windows si prova a cancellare, il pid non si controlla")
    folder = tmp_path / "soundtext-sfz"
    folder.mkdir()
    dead = folder / "libsfizz-999999999-3.so"
    mine = folder / f"libsfizz-{os.getpid()}-1.so"
    dead.write_bytes(b"x")
    mine.write_bytes(b"x")
    sfz_engine._remove_stale_copies(str(folder))
    assert not dead.exists() and mine.exists()


def test_render_log_counts_a_single_stem(monkeypatch):
    from core import effect_render
    effect_render.last_render_workers = 7
    monkeypatch.setattr(effect_render, "render_stem", lambda request, stop_check=None: None)
    effect_render.render_stems([object()])
    assert effect_render.last_render_workers == 1
