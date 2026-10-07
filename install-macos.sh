#!/usr/bin/env bash
#
# Installer di SoundText per macOS.
#
# Cosa fa:
#   - verifica/installa Homebrew (chiede conferma prima di lanciare
#     l'installer ufficiale se non e' gia' presente);
#   - installa con Homebrew le dipendenze di sistema (fluidsynth,
#     portaudio, Python) col comando gia' documentato in docs/HELP.md;
#   - copia il codice sorgente in
#     ~/Library/Application Support/SoundText (senza mai cancellare le
#     sottocartelle songs/ e soundfonts/, dove l'app salva i progetti e i
#     SoundFont dell'utente, ne' settings.json/instruments.json che l'app
#     salva nella stessa cartella su macOS);
#   - il SoundFont GM incluso nel repository (soundfonts/FluidR3_GM.sf2)
#     finisce cosi' gia' esattamente dove l'app lo rileva automaticamente
#     su macOS, senza bisogno di scaricarlo a parte;
#   - crea un virtualenv Python dedicato e ci installa i pacchetti pip
#     (PySide6, mido, sounddevice, numpy, pedalboard);
#   - installa un comando "soundtext" in ~/.local/bin e un vero
#     SoundText.app in ~/Applications (con icona, visibile in Launchpad
#     e Spotlight).
#
# Uso:
#   ./install-macos.sh              installa (o aggiorna un'installazione esistente)
#   ./install-macos.sh --yes        come sopra, senza chiedere conferma
#   ./install-macos.sh --uninstall  rimuove comando e SoundText.app
#                                   (NON tocca ~/Library/Application Support/SoundText:
#                                   i tuoi progetti in songs/ restano al sicuro;
#                                   per cancellare anche quelli usa --purge)
#   ./install-macos.sh --purge      come --uninstall, ma cancella anche
#                                   ~/Library/Application Support/SoundText
#                                   (progetti in songs/, SoundFont personalizzati
#                                   E le impostazioni dell'app, che su macOS
#                                   vivono nella stessa cartella): chiede
#                                   conferma esplicita
#
set -euo pipefail

APP_NAME="SoundText"
INSTALL_DIR="$HOME/Library/Application Support/SoundText"
BIN_DIR="$HOME/.local/bin"
LAUNCHER="$BIN_DIR/soundtext"
APPS_DIR="$HOME/Applications"
APP_BUNDLE="$APPS_DIR/SoundText.app"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ASSUME_YES=0
ACTION="install"
for arg in "$@"; do
    case "$arg" in
        -y|--yes) ASSUME_YES=1 ;;
        --uninstall) ACTION="uninstall" ;;
        --purge) ACTION="purge" ;;
        -h|--help)
            sed -n '2,38p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "Opzione sconosciuta: $arg (usa --help)" >&2
            exit 1
            ;;
    esac
done

info()  { printf '\033[1;34m==>\033[0m %s\n' "$1"; }
warn()  { printf '\033[1;33m!!\033[0m %s\n' "$1" >&2; }
error() { printf '\033[1;31mERRORE:\033[0m %s\n' "$1" >&2; }

confirm() {
    [ "$ASSUME_YES" = 1 ] && return 0
    read -r -p "$1 [s/N] " reply
    case "$reply" in [sSyY]) return 0 ;; *) return 1 ;; esac
}

if [ "$(uname -s)" != "Darwin" ]; then
    error "Questo script e' per macOS. Su Linux usa ./install.sh, su Windows install.ps1."
    exit 1
fi

# ---------------------------------------------------------------------------
# Disinstallazione
# ---------------------------------------------------------------------------

do_uninstall() {
    info "Rimuovo comando e $APP_NAME.app..."
    rm -f "$LAUNCHER"
    rm -rf "$APP_BUNDLE"
    if [ "$ACTION" = "purge" ]; then
        if [ -d "$INSTALL_DIR" ]; then
            warn "Questo cancellera' anche '$INSTALL_DIR', inclusa la cartella"
            warn "songs/ con eventuali progetti salvati, soundfonts/ con eventuali"
            warn "SoundFont personalizzati, E le impostazioni dell'app"
            warn "(settings.json, instruments.json): su macOS vivono nella stessa"
            warn "cartella, a differenza di Linux/Windows."
            if confirm "Confermi la cancellazione completa di '$INSTALL_DIR'?"; then
                rm -rf "$INSTALL_DIR"
                info "Cancellato '$INSTALL_DIR'."
            else
                info "Cancellazione annullata: '$INSTALL_DIR' mantenuto."
            fi
        fi
    else
        info "'$INSTALL_DIR' mantenuto (contiene i tuoi progetti in songs/ e le impostazioni)."
        info "Per cancellare anche quello: ./install-macos.sh --purge"
    fi
    info "Disinstallazione completata."
    exit 0
}

if [ "$ACTION" = "uninstall" ] || [ "$ACTION" = "purge" ]; then
    do_uninstall
fi

# ---------------------------------------------------------------------------
# Homebrew e dipendenze di sistema
# ---------------------------------------------------------------------------

if ! command -v brew >/dev/null 2>&1; then
    warn "Homebrew non trovato: serve per installare fluidsynth (sintesi audio)"
    warn "e portaudio (registrazione) senza doverli compilare a mano."
    if confirm "Lancio l'installer ufficiale di Homebrew (brew.sh) adesso?"; then
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        if [ -x /opt/homebrew/bin/brew ]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        elif [ -x /usr/local/bin/brew ]; then
            eval "$(/usr/local/bin/brew shellenv)"
        fi
    else
        warn "Continuo senza Homebrew: verranno installati solo i pacchetti Python"
        warn "(pip); senza fluidsynth l'app non produrra' audio. Vedi docs/HELP.md."
    fi
fi

if command -v brew >/dev/null 2>&1; then
    pkgs=(python@3.12 fluidsynth portaudio)
    info "Pacchetti Homebrew da installare: ${pkgs[*]}"
    if confirm "Procedo con 'brew install ${pkgs[*]}'?"; then
        failed=()
        for p in "${pkgs[@]}"; do
            if ! brew list --formula "$p" >/dev/null 2>&1; then
                brew install "$p" || failed+=("$p")
            fi
        done
        if [ "${#failed[@]}" -gt 0 ]; then
            warn "Pacchetti Homebrew non installati: ${failed[*]}. Vedi docs/HELP.md"
            warn "per alternative; l'app funziona comunque, ma senza fluidsynth non"
            warn "sentirai l'audio."
        fi
    else
        warn "Salto l'installazione delle dipendenze Homebrew."
    fi
fi

# ---------------------------------------------------------------------------
# Copia sorgenti e virtualenv Python
# ---------------------------------------------------------------------------

find_python() {
    local cmd ver major minor
    for cmd in python3.13 python3.12 python3.11 python3.10 python3; do
        if command -v "$cmd" >/dev/null 2>&1; then
            ver="$("$cmd" --version 2>&1 | awk '{print $2}')"
            major="${ver%%.*}"
            minor="${ver#*.}"; minor="${minor%%.*}"
            if [ "$major" = "3" ] && [ "${minor:-0}" -ge 10 ] 2>/dev/null; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON_CMD="$(find_python)" || {
    error "Python 3.10+ non trovato nel PATH."
    error "Installalo con 'brew install python@3.12' e rilancia questo script,"
    error "oppure da python.org, poi assicurati che sia nel PATH."
    exit 1
}
info "Uso '$PYTHON_CMD' ($($PYTHON_CMD --version))"

info "Copio i sorgenti in '$INSTALL_DIR'..."
mkdir -p "$INSTALL_DIR"
if [ "$SRC_DIR" != "$INSTALL_DIR" ]; then
    # Si copia solo quello che serve al programma (elenco esplicito): niente
    # test, script di build, manuali Word, README, ecc. Le cartelle si
    # fondono con quelle gia' presenti, senza cancellare nulla dell'utente.
    APP_ITEMS=(main.py core gui locales assets docs licenses
               requirements.txt LICENSE THIRD_PARTY_NOTICES.md
               scarica_strumenti.py scarica_strumenti.sh scarica_profili_nam.py)
    for item in "${APP_ITEMS[@]}"; do
        [ -e "$SRC_DIR/$item" ] && cp -a "$SRC_DIR/$item" "$INSTALL_DIR"/
    done
    # examples/: solo i progetti, non i render audio (.wav)
    if [ -d "$SRC_DIR/examples" ]; then
        mkdir -p "$INSTALL_DIR/examples"
        for f in "$SRC_DIR"/examples/*; do
            case "$f" in *.wav) continue ;; esac
            [ -e "$f" ] && cp -a "$f" "$INSTALL_DIR/examples/"
        done
    fi
    # soundfonts/: solo il SoundFont GM di default (gli altri sono dell'utente)
    mkdir -p "$INSTALL_DIR/soundfonts" "$INSTALL_DIR/songs"
    [ -f "$SRC_DIR/soundfonts/FluidR3_GM.sf2" ] && \
        cp -a "$SRC_DIR/soundfonts/FluidR3_GM.sf2" "$INSTALL_DIR/soundfonts/"
    # La guida PDF va in docs/, accanto a HELP.md
    cp -a "$SRC_DIR"/SoundText_Guida_dal_primo_accordo_al_WAV.pdf "$INSTALL_DIR/docs/" 2>/dev/null || true
    find "$INSTALL_DIR" -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
    # Si tolgono i file che non servono al programma e che le versioni
    # precedenti dello script (che copiavano tutto il repository) possono
    # aver lasciato: manuale Word, PDF nella radice, immagini della guida PDF,
    # note di pubblicazione, script che preparano gli installer.
    # Solo qui, nella cartella di installazione: se si lancia lo script dalla
    # cartella stessa (SRC_DIR == INSTALL_DIR) sono file del repository e
    # restano dove sono.
    rm -f "$INSTALL_DIR/SoundText_Manuale_Utente.docx" \
          "$INSTALL_DIR/SoundText_Guida_dal_primo_accordo_al_WAV.pdf" \
          "$INSTALL_DIR/build-appimage.sh" \
          "$INSTALL_DIR/build-linux-portable.sh" \
          "$INSTALL_DIR/build-windows-portable.ps1" \
          "$INSTALL_DIR/installer-windows.iss" \
          "$INSTALL_DIR/package-for-linux.ps1"
    rm -rf "$INSTALL_DIR/docs/guida_brano"
    rm -f "$INSTALL_DIR/docs/PUBBLICARE_SU_PYPI.md" "$INSTALL_DIR/locales/extract.py"
    # Libreria MIDI: l'installazione porta la cartella midi/ vuota, senza le
    # sottocartelle e il file d'esempio del repository (la libreria e' dell'utente
    # e la riempie lui). Dalle installazioni precedenti si tolgono solo i file
    # d'esempio rimasti identici all'originale e le sottocartelle che restano
    # vuote: file e cartelle dell'utente, anche modificati, non si toccano.
    mkdir -p "$INSTALL_DIR/midi"
    if [ -d "$SRC_DIR/midi" ]; then
        while IFS= read -r -d '' shipped; do
            rel="${shipped#"$SRC_DIR"/}"
            if cmp -s "$shipped" "$INSTALL_DIR/$rel"; then
                rm -f "$INSTALL_DIR/$rel"
            fi
        done < <(find "$SRC_DIR/midi" -type f -print0)
        for shipped_dir in "$SRC_DIR"/midi/*/; do
            [ -d "$shipped_dir" ] || continue
            rmdir "$INSTALL_DIR/midi/$(basename "$shipped_dir")" 2>/dev/null || true
        done
    fi
fi
# rsync/cp non cancellano mai file esistenti non presenti nella sorgente:
# songs/, soundfonts/ e le impostazioni dell'utente restano intatti tra un
# aggiornamento e l'altro.

if [ -f "$INSTALL_DIR/soundfonts/FluidR3_GM.sf2" ]; then
    info "SoundFont GM incluso nel repository gia' in '$INSTALL_DIR/soundfonts/'"
    info "(l'app lo rileva automaticamente li', nessun download necessario)."
else
    warn "Nessun SoundFont GM trovato in '$INSTALL_DIR/soundfonts/': senza,"
    warn "l'app non produrra' audio. Impostane uno da Playback -> Scegli"
    warn "SoundFont (.sf2)... dentro l'app, oppure mettilo in"
    warn "'$INSTALL_DIR/soundfonts/FluidR3_GM.sf2'."
fi

info "Creo il virtualenv Python (puo' richiedere qualche minuto, PySide6 e' grande)..."
"$PYTHON_CMD" -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip wheel >/dev/null

"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

# ---------------------------------------------------------------------------
# Comando "soundtext"
# ---------------------------------------------------------------------------

info "Installo il comando 'soundtext' in '$BIN_DIR'..."
mkdir -p "$BIN_DIR"
cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
exec "$INSTALL_DIR/venv/bin/python3" "$INSTALL_DIR/main.py" "\$@"
EOF
chmod +x "$LAUNCHER"

# ---------------------------------------------------------------------------
# SoundText.app (icona, Launchpad/Spotlight)
# ---------------------------------------------------------------------------

info "Creo $APP_NAME.app in '$APPS_DIR'..."
mkdir -p "$APPS_DIR" "$APP_BUNDLE/Contents/MacOS" "$APP_BUNDLE/Contents/Resources"

cat > "$APP_BUNDLE/Contents/MacOS/soundtext" <<EOF
#!/bin/bash
exec "$LAUNCHER" "\$@"
EOF
chmod +x "$APP_BUNDLE/Contents/MacOS/soundtext"

if command -v sips >/dev/null 2>&1 && command -v iconutil >/dev/null 2>&1 \
    && [ -f "$INSTALL_DIR/assets/icon.png" ]; then
    ICONSET_PARENT="$(mktemp -d)"
    ICONSET_DIR="$ICONSET_PARENT/SoundText.iconset"
    mkdir -p "$ICONSET_DIR"
    for size in 16 32 128 256 512; do
        sips -z "$size" "$size" "$INSTALL_DIR/assets/icon.png" \
            --out "$ICONSET_DIR/icon_${size}x${size}.png" >/dev/null
        double=$((size * 2))
        sips -z "$double" "$double" "$INSTALL_DIR/assets/icon.png" \
            --out "$ICONSET_DIR/icon_${size}x${size}@2x.png" >/dev/null
    done
    iconutil -c icns "$ICONSET_DIR" -o "$APP_BUNDLE/Contents/Resources/SoundText.icns"
    rm -rf "$ICONSET_PARENT"
    ICON_KEY="<key>CFBundleIconFile</key><string>SoundText.icns</string>"
else
    warn "sips/iconutil non trovati o icona sorgente mancante: SoundText.app avra' l'icona di default."
    ICON_KEY=""
fi

cat > "$APP_BUNDLE/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>SoundText</string>
    <key>CFBundleDisplayName</key><string>SoundText</string>
    <key>CFBundleIdentifier</key><string>org.soundtext.app</string>
    <key>CFBundleVersion</key><string>1.0.0</string>
    <key>CFBundleShortVersionString</key><string>1.0.0</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleExecutable</key><string>soundtext</string>
    $ICON_KEY
    <key>NSHighResolutionCapable</key><true/>
    <key>LSMinimumSystemVersion</key><string>10.14</string>
    <key>NSMicrophoneUsageDescription</key><string>SoundText usa il microfono per l'importazione audio (registrazione e trascrizione in note musicali).</string>
</dict>
</plist>
EOF

LSREGISTER="/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister"
[ -x "$LSREGISTER" ] && "$LSREGISTER" -f "$APP_BUNDLE" >/dev/null 2>&1 || true

echo
info "Installazione completata."
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    warn "'$BIN_DIR' non e' nel tuo PATH, quindi 'soundtext' da terminale non"
    warn "funzionera' finche' non lo aggiungi (SoundText.app funziona gia' comunque)."
    if [ "${SHELL##*/}" = "zsh" ]; then
        warn "Con zsh (shell predefinita su macOS): aggiungi 'export PATH=\"$BIN_DIR:\$PATH\"'"
        warn "al tuo ~/.zshrc, poi riapri il terminale."
    else
        warn "Con bash su macOS: aggiungi 'export PATH=\"$BIN_DIR:\$PATH\"' al tuo"
        warn "~/.bash_profile (non ~/.bashrc: Terminal.app apre shell di login), poi"
        warn "riapri il terminale."
    fi
fi
echo "Avvia $APP_NAME da Launchpad/Spotlight ('$APP_BUNDLE'), oppure da terminale con: soundtext"
