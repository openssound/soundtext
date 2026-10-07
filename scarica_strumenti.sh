#!/usr/bin/env bash
# Scarica e installa strumenti virtuali gratuiti (SFZ) per SoundText: il lavoro
# lo fa scarica_strumenti.py, lo stesso su Linux, Windows e macOS.
# Uso: ./scarica_strumenti.sh [host | libreria | tutto | <gruppi>...]  (senza argomenti: elenco)
exec python3 "$(dirname "$0")/scarica_strumenti.py" "$@"
