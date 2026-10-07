#!/usr/bin/env bash
#
# Prepara l'ambiente per eseguire il pacchetto portable di SoundText per Linux
# (cartella con l'eseguibile "SoundText"). Va lanciato dalla cartella estratta.
#
# Cosa fa:
#   - rileva la distribuzione e installa con sudo le librerie di sistema che il
#     pacchetto non include: FluidSynth e un SoundFont GM (audio), PortAudio
#     (registrazione), lilv (plugin LV2) e le librerie grafiche richieste da Qt
#     (xcb, xkbcommon, EGL/GL);
#   - dà il permesso di esecuzione a SoundText e agli script;
#   - opzionale (--integra): crea la voce nel menu applicazioni con icona e il
#     comando "soundtext" in ~/.local/bin.
#
# Per i plugin e gli strumenti gratuiti usa poi ./scarica_strumenti.sh
#
# Uso:
#   ./setup-portable-linux.sh           installa le dipendenze e rende eseguibile
#   ./setup-portable-linux.sh --yes     senza chiedere conferma
#   ./setup-portable-linux.sh --integra come sopra + voce di menu e comando
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASSUME_YES=0
INTEGRA=0

info()  { printf '\033[1;34m==>\033[0m %s\n' "$1"; }
warn()  { printf '\033[1;33m!!\033[0m %s\n' "$1" >&2; }
error() { printf '\033[1;31mERRORE:\033[0m %s\n' "$1" >&2; }

while [ $# -gt 0 ]; do
    case "$1" in
        -y|--yes) ASSUME_YES=1 ;;
        --integra) INTEGRA=1 ;;
        -h|--help) sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) error "Opzione sconosciuta: $1 (usa --help)"; exit 1 ;;
    esac
    shift
done

confirm() {
    [ "$ASSUME_YES" = 1 ] && return 0
    read -r -p "$1 [s/N] " reply
    case "$reply" in [sSyY]) return 0 ;; *) return 1 ;; esac
}

if [ "$(uname -m)" != "x86_64" ]; then
    error "Il pacchetto e' per x86_64; questa macchina e' $(uname -m)."
    exit 1
fi

# --- Individua l'eseguibile ---------------------------------------------------
APPIMAGE="$SCRIPT_DIR/SoundText"
if [ ! -f "$APPIMAGE" ]; then
    error "Eseguibile 'SoundText' non trovato accanto a questo script: lancialo dalla cartella estratta."
    exit 1
fi
info "Eseguibile: $APPIMAGE"

# --- Dipendenze di sistema --------------------------------------------------
FAMILY=""
if [ -r /etc/os-release ]; then
    . /etc/os-release
    case "${ID:-} ${ID_LIKE:-}" in
        *arch*|*cachyos*|*manjaro*|*endeavouros*) FAMILY=arch ;;
        *fedora*|*rhel*|*centos*|*rocky*|*almalinux*|*nobara*) FAMILY=fedora ;;
        *debian*|*ubuntu*|*mint*|*pop*) FAMILY=debian ;;
        *suse*) FAMILY=opensuse ;;
    esac
fi

pkgs=(); cmd=()
case "$FAMILY" in
    debian)
        cmd=(sudo apt-get install -y)
        pkgs=(fluidsynth fluid-soundfont-gm libportaudio2 liblilv-0-0
              libxcb-cursor0 libxcb-xinerama0 libxkbcommon-x11-0 libegl1 libgl1 libxcb-icccm4
              libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxcb-shape0)
        ;;
    fedora)
        cmd=(sudo dnf install -y)
        pkgs=(fluidsynth fluid-soundfont-gm portaudio lilv-libs
              xcb-util-cursor libxkbcommon-x11 mesa-libEGL mesa-libGL
              xcb-util-wm xcb-util-image xcb-util-keysyms xcb-util-renderutil)
        ;;
    arch)
        cmd=(sudo pacman -S --needed --noconfirm)
        pkgs=(fluidsynth portaudio lilv xcb-util-cursor libxkbcommon-x11
              libglvnd xcb-util-wm xcb-util-image xcb-util-keysyms xcb-util-renderutil)
        ;;
    opensuse)
        cmd=(sudo zypper install -y)
        pkgs=(fluidsynth fluid-soundfont-gm portaudio liblilv-0-0
              libxcb-cursor0 libxkbcommon-x11-0 libEGL1 libGL1)
        ;;
    *)
        warn "Distribuzione non riconosciuta: installa a mano fluidsynth,"
        warn "un SoundFont GM, portaudio, lilv e le librerie xcb/xkbcommon/EGL."
        ;;
esac

if [ "${#pkgs[@]}" -gt 0 ]; then
    info "Distribuzione: $FAMILY"
    info "Pacchetti: ${pkgs[*]}"
    if confirm "Installo con '${cmd[*]}' (richiede sudo)?"; then
        [ "$FAMILY" = debian ] && sudo apt-get update
        failed=()
        for p in "${pkgs[@]}"; do
            "${cmd[@]}" "$p" || failed+=("$p")
        done
        if [ "${#failed[@]}" -gt 0 ]; then
            warn "Non installati (nome diverso o repository non abilitato): ${failed[*]}"
        fi
        if [ "$FAMILY" = arch ] && ! pacman -Qi soundfont-fluid >/dev/null 2>&1; then
            warn "SoundFont GM mancante: installa 'soundfont-fluid' da AUR (yay -S soundfont-fluid),"
            warn "oppure carica un tuo .sf2 dall'app."
        fi
    else
        warn "Salto l'installazione delle dipendenze di sistema."
    fi
fi

# --- Permessi e integrazione ------------------------------------------------
chmod +x "$APPIMAGE" "$SCRIPT_DIR"/SoundText.bin "$SCRIPT_DIR"/scarica_strumenti.sh 2>/dev/null || true
info "Permesso di esecuzione impostato."

if [ "$INTEGRA" = 1 ]; then
    BIN_DIR="$HOME/.local/bin"
    APP_DIR="$HOME/.local/share/applications"
    ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
    mkdir -p "$BIN_DIR" "$APP_DIR" "$ICON_DIR"
    ln -sf "$APPIMAGE" "$BIN_DIR/soundtext"

    [ -f "$SCRIPT_DIR/assets/icon.png" ] && cp "$SCRIPT_DIR/assets/icon.png" "$ICON_DIR/soundtext.png"

    cat > "$APP_DIR/soundtext.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=SoundText
GenericName=Editor di notazione musicale
Comment=Notazione musicale testuale con playback MIDI/SoundFont
Exec=$APPIMAGE %f
Path=$SCRIPT_DIR
Icon=soundtext
Terminal=false
Categories=AudioVideo;Audio;Music;
StartupWMClass=SoundText
DESK
    command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true
    info "Voce di menu e comando 'soundtext' creati (assicurati che ~/.local/bin sia nel PATH)."
    info "Se sposti la cartella, rilancia questo script con --integra."
fi

echo
info "Pronto. Avvia con: $APPIMAGE"
