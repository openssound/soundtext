#!/usr/bin/env bash
# Avvia SoundText dai sorgenti (Linux/macOS, e Windows da Git Bash), senza
# installarlo.
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
STAMP="$VENV/.requirements-installed"

case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*)
        # Windows: il virtualenv ha Scripts/ al posto di bin/, e "python3"
        # di solito non c'e' (o e' l'alias che apre il Microsoft Store).
        BIN="$VENV/Scripts"
        PY="$BIN/python.exe"
        if command -v py >/dev/null 2>&1; then
            PYTHON=(py -3)
        else
            PYTHON=(python)
        fi
        ;;
    *)
        BIN="$VENV/bin"
        PY="$BIN/python"
        PYTHON=(python3)
        ;;
esac

if ! "${PYTHON[@]}" -c "" >/dev/null 2>&1; then
    echo "Python 3 non trovato: installalo (https://www.python.org/downloads/) e riprova." >&2
    exit 1
fi

if [ ! -x "$PY" ]; then
    echo "Creo il virtualenv in $VENV..."
    if ! "${PYTHON[@]}" -m venv "$VENV" >/dev/null 2>&1; then
        # Debian/Ubuntu senza python3-venv: venv senza pip, pacchetti
        # installati con il pip di sistema.
        rm -rf "$VENV"
        "${PYTHON[@]}" -m venv --without-pip "$VENV"
    fi
fi

if [ ! -f "$STAMP" ] || [ "$ROOT/requirements.txt" -nt "$STAMP" ]; then
    echo "Installo le dipendenze Python..."
    # pedalboard >= 0.9.17 richiede AVX: senza, l'import va in SIGILL
    EXTRA=()
    if [ -r /proc/cpuinfo ] && ! grep -qw avx /proc/cpuinfo; then
        EXTRA=("pedalboard<0.9.17")
    fi
    if [ -x "$PY" ] && "$PY" -m pip --version >/dev/null 2>&1; then
        "$PY" -m pip install -q -r "$ROOT/requirements.txt" ${EXTRA[@]+"${EXTRA[@]}"}
    else
        "${PYTHON[@]}" -m pip --python "$PY" install -q -r "$ROOT/requirements.txt" ${EXTRA[@]+"${EXTRA[@]}"}
    fi
    touch "$STAMP"
fi

cd "$ROOT"
exec "$PY" "$ROOT/main.py" "$@"
