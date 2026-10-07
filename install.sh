#!/usr/bin/env bash
#
# Installer di SoundText per Linux.
#
# Cosa fa:
#   - rileva la distribuzione e installa le dipendenze di sistema
#     (fluidsynth, soundfont GM, portaudio, lilv) col package manager
#     giusto (apt/dnf/pacman/zypper);
#   - copia il codice sorgente in ~/.local/share/soundtext (senza mai
#     cancellare le sottocartelle songs/ e soundfonts/, dove l'app salva
#     i progetti e i SoundFont dell'utente);
#   - se il package manager non fornisce un SoundFont GM di sistema, copia
#     quello gia' incluso nel repository (soundfonts/FluidR3_GM.sf2) in
#     ~/.local/share/soundfonts/, dove l'app lo rileva automaticamente;
#   - crea un virtualenv Python dedicato e ci installa i pacchetti pip
#     (PySide6, mido, sounddevice, numpy, pedalboard);
#   - installa un comando "soundtext" in ~/.local/bin e una voce nel
#     menu applicazioni (con icona).
#
# Uso:
#   ./install.sh              installa (o aggiorna un'installazione esistente)
#   ./install.sh --yes        come sopra, senza chiedere conferma
#   ./install.sh --uninstall  rimuove comando, voce di menu e icona
#                             (NON tocca ~/.local/share/soundtext: i tuoi
#                             progetti in songs/ restano al sicuro; per
#                             cancellare anche quelli usa --purge)
#   ./install.sh --purge      come --uninstall, ma cancella anche
#                             ~/.local/share/soundtext (compresi i progetti
#                             salvati in songs/): chiede conferma esplicita
#
set -euo pipefail

APP_NAME="SoundText"
INSTALL_DIR="$HOME/.local/share/soundtext"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
LAUNCHER="$BIN_DIR/soundtext"
DESKTOP_FILE="$DESKTOP_DIR/soundtext.desktop"
ICON_FILE="$ICON_DIR/soundtext.png"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ASSUME_YES=0
ACTION="install"
for arg in "$@"; do
    case "$arg" in
        -y|--yes) ASSUME_YES=1 ;;
        --uninstall) ACTION="uninstall" ;;
        --purge) ACTION="purge" ;;
        -h|--help)
            sed -n '2,26p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
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

# ---------------------------------------------------------------------------
# Disinstallazione
# ---------------------------------------------------------------------------

do_uninstall() {
    info "Rimuovo comando, voce di menu e icona di $APP_NAME..."
    rm -f "$LAUNCHER" "$DESKTOP_FILE" "$ICON_FILE"
    command -v update-desktop-database >/dev/null 2>&1 && \
        update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
    if [ "$ACTION" = "purge" ]; then
        if [ -d "$INSTALL_DIR" ]; then
            warn "Questo cancellera' anche $INSTALL_DIR, inclusa la cartella"
            warn "songs/ con eventuali progetti salvati e soundfonts/ con"
            warn "eventuali SoundFont personalizzati."
            if confirm "Confermi la cancellazione completa di $INSTALL_DIR?"; then
                rm -rf "$INSTALL_DIR"
                info "Cancellato $INSTALL_DIR."
            else
                info "Cancellazione annullata: $INSTALL_DIR mantenuto."
            fi
        fi
    else
        info "$INSTALL_DIR mantenuto (contiene i tuoi progetti in songs/)."
        info "Per cancellare anche quello: ./install.sh --purge"
    fi
    info "Disinstallazione completata."
    exit 0
}

if [ "$ACTION" = "uninstall" ] || [ "$ACTION" = "purge" ]; then
    do_uninstall
fi

# ---------------------------------------------------------------------------
# Rilevamento distribuzione e installazione dipendenze di sistema
# ---------------------------------------------------------------------------

DISTRO_FAMILY=""
if [ -r /etc/os-release ]; then
    . /etc/os-release
    ID_ALL="${ID:-} ${ID_LIKE:-}"
    case "$ID_ALL" in
        *arch*|*cachyos*|*manjaro*|*endeavouros*) DISTRO_FAMILY="arch" ;;
        *fedora*|*rhel*|*centos*|*rocky*|*almalinux*|*nobara*) DISTRO_FAMILY="fedora" ;;
        *debian*|*ubuntu*|*mint*|*pop*) DISTRO_FAMILY="debian" ;;
        *suse*|*opensuse*) DISTRO_FAMILY="opensuse" ;;
    esac
fi

install_system_deps() {
    local pkgs=() cmd=() failed=()

    case "$DISTRO_FAMILY" in
        debian)
            cmd=(sudo apt-get install -y)
            pkgs=(python3-venv python3-pip fluidsynth fluid-soundfont-gm libportaudio2 liblilv-0-0)
            ;;
        fedora)
            cmd=(sudo dnf install -y)
            pkgs=(python3-pip fluidsynth fluid-soundfont-gm portaudio lilv-libs)
            ;;
        arch)
            cmd=(sudo pacman -S --needed --noconfirm)
            pkgs=(python-pip fluidsynth portaudio lilv)
            ;;
        opensuse)
            cmd=(sudo zypper install -y)
            pkgs=(python3-pip fluidsynth fluid-soundfont-gm portaudio liblilv-0-0)
            ;;
        *)
            warn "Distribuzione non riconosciuta automaticamente."
            warn "Installa manualmente le dipendenze di sistema descritte in"
            warn "docs/HELP.md (sezione 'Installazione su Linux') e poi rilancia"
            warn "questo script con --yes per saltare la parte di sistema, oppure"
            warn "assicurati che 'python3 -m venv' funzioni e fluidsynth sia gia'"
            warn "installato prima di continuare."
            confirm "Continuo comunque con la sola parte Python (venv + pip)?" || exit 1
            return
            ;;
    esac

    info "Distribuzione rilevata: $DISTRO_FAMILY"
    info "Pacchetti di sistema da installare: ${pkgs[*]}"
    confirm "Procedo con '${cmd[*]} ${pkgs[*]}' (richiede sudo)?" || {
        warn "Salto l'installazione delle dipendenze di sistema."
        return
    }

    for p in "${pkgs[@]}"; do
        if ! "${cmd[@]}" "$p"; then
            failed+=("$p")
        fi
    done

    if [ "$DISTRO_FAMILY" = "arch" ]; then
        if ! pacman -Qi soundfont-fluid >/dev/null 2>&1; then
            local aur=""
            command -v yay  >/dev/null 2>&1 && aur=yay
            command -v paru >/dev/null 2>&1 && aur=paru
            if [ -n "$aur" ]; then
                info "Installo il SoundFont GM da AUR con $aur..."
                "$aur" -S --needed --noconfirm soundfont-fluid || failed+=("soundfont-fluid (AUR)")
            else
                warn "Nessun SoundFont GM di sistema trovato e nessun helper AUR"
                warn "(yay/paru) disponibile: uso quello incluso nel repository come"
                warn "ripiego (vedi passo successivo). Per un pacchetto di sistema"
                warn "installa 'soundfont-fluid' da AUR manualmente."
            fi
        fi
    fi

    if [ "${#failed[@]}" -gt 0 ]; then
        warn "Pacchetti non installati (nome diverso su questa distro o non"
        warn "disponibile nei repository abilitati): ${failed[*]}"
        warn "Vedi docs/HELP.md per alternative. L'app funziona comunque; senza"
        warn "fluidsynth/soundfont non sentirai l'audio, senza portaudio non"
        warn "potrai registrare ne' ascoltare con loop e salti."
    fi
}

install_soundfont() {
    local target_dir="$HOME/.local/share/soundfonts"
    local target="$target_dir/FluidR3_GM.sf2"
    local candidate

    for candidate in \
        "$target" \
        "$HOME/.soundfonts/FluidR3_GM.sf2" \
        /usr/share/sounds/sf2/FluidR3_GM.sf2 \
        /usr/share/soundfonts/FluidR3_GM.sf2 \
        /usr/share/sounds/sf2/default.sf2 \
        /usr/share/soundfonts/default.sf2
    do
        if [ -f "$candidate" ]; then
            info "SoundFont GM gia' presente in $candidate."
            return
        fi
    done

    local bundled="$INSTALL_DIR/soundfonts/FluidR3_GM.sf2"
    if [ -f "$bundled" ]; then
        info "Copio il SoundFont GM incluso nel repository in $target..."
        mkdir -p "$target_dir"
        cp "$bundled" "$target"
    else
        warn "Nessun SoundFont GM trovato: senza, l'app non produrra' audio."
        warn "Impostane uno da Riproduzione -> Scegli SoundFont (.sf2)... dentro l'app."
    fi
}

install_system_deps

# ---------------------------------------------------------------------------
# Copia sorgenti e virtualenv Python
# ---------------------------------------------------------------------------

info "Copio i sorgenti in $INSTALL_DIR..."
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
# songs/ e soundfonts/ dell'utente restano intatti tra un aggiornamento e l'altro.

install_soundfont

info "Creo il virtualenv Python (puo' richiedere qualche minuto, PySide6 e' grande)..."
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip wheel >/dev/null
# pedalboard >= 0.9.17 richiede AVX: senza, l'import va in SIGILL
PIP_EXTRA=()
if [ -r /proc/cpuinfo ] && ! grep -qw avx /proc/cpuinfo; then
    PIP_EXTRA=("pedalboard<0.9.17")
fi
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" "${PIP_EXTRA[@]}"

# ---------------------------------------------------------------------------
# Comando "soundtext", voce di menu e icona
# ---------------------------------------------------------------------------

info "Installo il comando 'soundtext' in $BIN_DIR..."
mkdir -p "$BIN_DIR"
cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
exec "$INSTALL_DIR/venv/bin/python3" "$INSTALL_DIR/main.py" "\$@"
EOF
chmod +x "$LAUNCHER"

info "Installo icona e voce nel menu applicazioni..."
mkdir -p "$ICON_DIR" "$DESKTOP_DIR"
cp "$INSTALL_DIR/assets/icon.png" "$ICON_FILE"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=$APP_NAME
GenericName=Editor di notazione musicale
Comment=Notazione musicale testuale con playback MIDI/SoundFont
Exec=$LAUNCHER %f
Icon=soundtext
Terminal=false
Categories=AudioVideo;Audio;Music;
StartupWMClass=SoundText
EOF
command -v update-desktop-database >/dev/null 2>&1 && \
    update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && \
    gtk-update-icon-cache -f "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true

echo
info "Installazione completata."
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    warn "$BIN_DIR non e' nel tuo PATH, quindi 'soundtext' da terminale non"
    warn "funzionera' finche' non lo aggiungi. La voce nel menu applicazioni"
    warn "funziona comunque gia' da subito."
    if [ -n "${FISH_VERSION:-}" ] || [ "${SHELL##*/}" = "fish" ]; then
        warn "Con fish: fish_add_path $BIN_DIR"
    else
        warn "Con bash/zsh: aggiungi 'export PATH=\"$BIN_DIR:\$PATH\"' al tuo"
        warn "~/.bashrc o ~/.zshrc, poi riapri il terminale."
    fi
fi
echo "Avvia $APP_NAME dal menu applicazioni, oppure da terminale con: soundtext"
if [ ! -f "$HOME/.local/lib/soundtext/libsfizz.so" ]; then
    echo "Facoltativo: per suonare i file .sfz senza plugin (Strumento SFZ interno) compila"
    echo "il motore sfizioso con: $INSTALL_DIR/scarica_strumenti.sh libreria"
fi
