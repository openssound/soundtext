#!/usr/bin/env bash
# Avvia SoundText dai sorgenti (Linux/macOS), senza installarlo.
#
#   ./run.sh [argomenti di main.py]
#
# Al primo avvio crea il virtualenv ./venv (ignorato da git) e ci installa
# requirements.txt; le volte successive reinstalla solo se requirements.txt
# e' cambiato. Per l'installazione completa (collegamento nel menu, pacchetti
# di sistema come fluidsynth) usa invece install.sh.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/venv"
PY="$VENV/bin/python"
STAMP="$VENV/.requirements-installed"

if [ ! -x "$PY" ]; then
    echo "Creo il virtualenv in $VENV..."
    if ! python3 -m venv "$VENV" >/dev/null 2>&1; then
        # Debian/Ubuntu senza python3-venv: venv senza pip, pacchetti
        # installati con il pip di sistema.
        rm -rf "$VENV"
        python3 -m venv --without-pip "$VENV"
    fi
fi

if [ ! -f "$STAMP" ] || [ "$ROOT/requirements.txt" -nt "$STAMP" ]; then
    echo "Installo le dipendenze Python..."
    # pedalboard >= 0.9.17 richiede AVX: senza, l'import va in SIGILL
    EXTRA=()
    if [ -r /proc/cpuinfo ] && ! grep -qw avx /proc/cpuinfo; then
        EXTRA=("pedalboard<0.9.17")
    fi
    if [ -x "$VENV/bin/pip" ]; then
        "$VENV/bin/pip" install -q -r "$ROOT/requirements.txt" "${EXTRA[@]}"
    else
        python3 -m pip --python "$PY" install -q -r "$ROOT/requirements.txt" "${EXTRA[@]}"
    fi
    touch "$STAMP"
fi

cd "$ROOT"
exec "$PY" "$ROOT/main.py" "$@"
