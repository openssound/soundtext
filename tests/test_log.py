"""
Test per core.log: il file di log raccoglie gli avvisi e le eccezioni non
gestite dei thread in background (es. quello di riproduzione). Eseguito in
un processo separato: setup_logging() modifica il logger radice e
threading.excepthook, che non devono restare modificati per gli altri test.

Esecuzione:
    python3 -m pytest tests/test_log.py -v
"""

import os
import subprocess
import sys
import textwrap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_log_file_collects_warnings_and_thread_exceptions(tmp_path):
    script = textwrap.dedent("""
        import logging, threading
        from core.log import setup_logging, LOG_FILE
        setup_logging()
        logging.getLogger("core.playback").warning("rendering fallito")
        def boom():
            raise RuntimeError("errore nel thread di riproduzione")
        t = threading.Thread(target=boom, name="riproduzione")
        t.start(); t.join()
        print(LOG_FILE)
    """)
    env = dict(os.environ, SOUNDTEXT_CONFIG_DIR=str(tmp_path), PYTHONPATH=ROOT)
    out = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    log_path = out.stdout.strip()
    assert log_path == str(tmp_path / "soundtext.log")
    content = open(log_path, encoding="utf-8").read()
    assert "rendering fallito" in content
    assert "Eccezione non gestita nel thread riproduzione" in content
    assert "RuntimeError: errore nel thread di riproduzione" in content
