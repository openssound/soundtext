#!/usr/bin/env bash
#
# Prepara l'ambiente per eseguire SoundText-x86_64.AppImage su Linux.
# Va scaricato e lanciato nella stessa cartella dell'AppImage.
#
# Cosa fa:
#   - rileva la distribuzione e installa con sudo le librerie di sistema che
#     l'AppImage non include: FUSE 2 (per montare l'AppImage), FluidSynth e un
#     SoundFont GM (audio), PortAudio (registrazione), lilv (plugin LV2) e le
#     librerie grafiche richieste da Qt (xcb, xkbcommon, EGL/GL);
#   - dà il permesso di esecuzione all'AppImage;
#   - opzionale (--integra): crea la voce nel menu applicazioni con icona e il
#     comando "soundtext" in ~/.local/bin.
#
# Uso:
#   ./setup-appimage.sh                 installa le dipendenze e rende eseguibile
#   ./setup-appimage.sh --yes           senza chiedere conferma
#   ./setup-appimage.sh --integra       come sopra + voce di menu e comando
#   ./setup-appimage.sh --appimage F    percorso dell'AppImage (default: quello
#                                       accanto allo script)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPIMAGE=""
ASSUME_YES=0
INTEGRA=0

info()  { printf '\033[1;34m==>\033[0m %s\n' "$1"; }
warn()  { printf '\033[1;33m!!\033[0m %s\n' "$1" >&2; }
error() { printf '\033[1;31mERRORE:\033[0m %s\n' "$1" >&2; }

while [ $# -gt 0 ]; do
    case "$1" in
        -y|--yes) ASSUME_YES=1 ;;
        --integra) INTEGRA=1 ;;
        --appimage) shift; APPIMAGE="${1:-}" ;;
        -h|--help) sed -n '2,19p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
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
    error "L'AppImage e' per x86_64; questa macchina e' $(uname -m)."
    exit 1
fi

# --- Individua l'AppImage ---------------------------------------------------
if [ -z "$APPIMAGE" ]; then
    for c in "$SCRIPT_DIR"/SoundText*.AppImage "$PWD"/SoundText*.AppImage; do
        [ -f "$c" ] && { APPIMAGE="$c"; break; }
    done
fi
if [ -z "$APPIMAGE" ] || [ ! -f "$APPIMAGE" ]; then
    error "AppImage non trovata: mettila accanto a questo script o usa --appimage <file>."
    exit 1
fi
APPIMAGE="$(readlink -f "$APPIMAGE")"
info "AppImage: $APPIMAGE"

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
        # libfuse2 si chiama libfuse2t64 su Ubuntu 24.04 e derivate recenti
        FUSE=libfuse2
        apt-cache show libfuse2t64 >/dev/null 2>&1 && FUSE=libfuse2t64
        pkgs=("$FUSE" fluidsynth fluid-soundfont-gm libportaudio2 liblilv-0-0
              libxcb-cursor0 libxcb-xinerama0 libxkbcommon-x11-0 libegl1 libgl1 libxcb-icccm4
              libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxcb-shape0)
        ;;
    fedora)
        cmd=(sudo dnf install -y)
        pkgs=(fuse-libs fluidsynth fluid-soundfont-gm portaudio lilv-libs
              xcb-util-cursor libxkbcommon-x11 mesa-libEGL mesa-libGL
              xcb-util-wm xcb-util-image xcb-util-keysyms xcb-util-renderutil)
        ;;
    arch)
        cmd=(sudo pacman -S --needed --noconfirm)
        pkgs=(fuse2 fluidsynth portaudio lilv xcb-util-cursor libxkbcommon-x11
              libglvnd xcb-util-wm xcb-util-image xcb-util-keysyms xcb-util-renderutil)
        ;;
    opensuse)
        cmd=(sudo zypper install -y)
        pkgs=(libfuse2 fluidsynth fluid-soundfont-gm portaudio liblilv-0-0
              libxcb-cursor0 libxkbcommon-x11-0 libEGL1 libGL1)
        ;;
    *)
        warn "Distribuzione non riconosciuta: installa a mano FUSE 2, fluidsynth,"
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
chmod +x "$APPIMAGE"
info "Permesso di esecuzione impostato."

if [ "$INTEGRA" = 1 ]; then
    BIN_DIR="$HOME/.local/bin"
    APP_DIR="$HOME/.local/share/applications"
    ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
    mkdir -p "$BIN_DIR" "$APP_DIR" "$ICON_DIR"
    ln -sf "$APPIMAGE" "$BIN_DIR/soundtext"

    # Estrae l'icona dall'AppImage (non serve FUSE: --appimage-extract)
    tmp="$(mktemp -d)"
    ( cd "$tmp" && "$APPIMAGE" --appimage-extract soundtext.png >/dev/null 2>&1 ) || true
    [ -f "$tmp/squashfs-root/soundtext.png" ] && cp "$tmp/squashfs-root/soundtext.png" "$ICON_DIR/soundtext.png"
    rm -rf "$tmp"

    cat > "$APP_DIR/soundtext.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=SoundText
GenericName=Editor di notazione musicale
Comment=Notazione musicale testuale con playback MIDI/SoundFont
Exec=$APPIMAGE %f
Icon=soundtext
Terminal=false
Categories=AudioVideo;Audio;Music;
StartupWMClass=SoundText
DESK
    command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true
    info "Voce di menu e comando 'soundtext' creati (assicurati che ~/.local/bin sia nel PATH)."
    info "Se sposti l'AppImage, rilancia questo script con --integra."
fi

echo
info "Pronto. Avvia con: $APPIMAGE"
