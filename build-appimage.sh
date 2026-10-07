#!/usr/bin/env bash
#
# Crea un AppImage di SoundText per Linux a partire dalla build PyInstaller
# gia' prodotta da build-linux-portable.sh (dist/SoundText/): chi la riceve
# scarica il file .AppImage, gli da' il permesso di esecuzione e lo lancia,
# senza installare Python, pip o altro.
#
# Va eseguito DOPO ./build-linux-portable.sh (serve dist/SoundText/), dalla
# radice di una copia completa del repository SoundText (serve anche
# assets/icon.png). Come build-linux-portable.sh, il risultato funziona
# solo su Linux con architettura e libc compatibili con quelle della
# macchina di build (in genere: stessa distro/versione o piu' recente) -
# vedi le note su GLIBC in build-linux-portable.sh.
#
# Passi:
#   1. verifica che dist/SoundText/ esista (creata da build-linux-portable.sh)
#      e che sia disponibile appimagetool (lo scarica in .build-tools/ se
#      manca, riusandolo nelle build successive);
#   2. prepara SoundText.AppDir/ (AppRun, .desktop, icona, contenuto di
#      dist/SoundText/ sotto usr/bin/);
#   3. lancia appimagetool per produrre SoundText-x86_64.AppImage nella
#      cartella corrente.
#
# Uso:
#   ./build-linux-portable.sh   (prima, se non gia' fatto)
#   ./build-appimage.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

info()  { printf '\033[1;36m==>\033[0m %s\n' "$1"; }
warn()  { printf '\033[1;33m!!\033[0m %s\n' "$1" >&2; }
error() { printf '\033[1;31mERRORE:\033[0m %s\n' "$1" >&2; }

DIST_DIR="$ROOT/dist/SoundText"
if [ ! -f "$DIST_DIR/SoundText" ]; then
    error "Manca '$DIST_DIR/SoundText': lancia prima ./build-linux-portable.sh per produrre la build PyInstaller."
    exit 1
fi

if [ ! -f "$ROOT/assets/icon.png" ]; then
    error "Manca 'assets/icon.png': lancia questo script dalla radice di una copia completa del repository SoundText."
    exit 1
fi

TOOLS_DIR="$ROOT/.build-tools"
APPIMAGETOOL="$TOOLS_DIR/appimagetool-x86_64.AppImage"
if [ ! -x "$APPIMAGETOOL" ]; then
    info "Scarico appimagetool in $APPIMAGETOOL..."
    mkdir -p "$TOOLS_DIR"
    curl -fsSL -o "$APPIMAGETOOL" \
        "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "$APPIMAGETOOL"
else
    info "appimagetool gia' presente in $TOOLS_DIR, lo riuso."
fi

APPDIR="$ROOT/SoundText.AppDir"
info "Preparo $APPDIR..."
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
cp -a "$DIST_DIR/." "$APPDIR/usr/bin/"

cat > "$APPDIR/AppRun" <<'EOF'
#!/usr/bin/env bash
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$HERE/usr/bin/SoundText" "$@"
EOF
chmod +x "$APPDIR/AppRun"

cp "$ROOT/assets/icon.png" "$APPDIR/soundtext.png"
ln -sf soundtext.png "$APPDIR/.DirIcon"

cat > "$APPDIR/soundtext.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=SoundText
GenericName=Editor di notazione musicale
Comment=Notazione musicale testuale con playback MIDI/SoundFont
Exec=SoundText %f
Icon=soundtext
Terminal=false
Categories=AudioVideo;Audio;Music;
StartupWMClass=SoundText
EOF

info "Genero SoundText-x86_64.AppImage..."
APPIMAGE_OUT="$ROOT/SoundText-x86_64.AppImage"
rm -f "$APPIMAGE_OUT"
ARCH=x86_64 "$APPIMAGETOOL" "$APPDIR" "$APPIMAGE_OUT"

echo
info "Fatto: $APPIMAGE_OUT"
echo "Chi lo riceve deve dare i permessi di esecuzione se necessario"
echo "(chmod +x SoundText-x86_64.AppImage) e lanciarlo: nessun Python o"
echo "installazione richiesti."
