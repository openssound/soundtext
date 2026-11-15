#!/bin/sh
# Avvia SoundText dentro il Flatpak.
# I plugin LV2 scaricati da "Scarica e installa" (~/.lv2) accanto a quelli
# delle estensioni Flatpak; ~/.vst3 e ~/.clap SoundText li guarda da se'.
export LV2_PATH="$HOME/.lv2:${LV2_PATH:-/app/extensions/Plugins/lv2}"
exec python3 /app/share/soundtext/main.py "$@"
