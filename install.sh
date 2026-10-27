#!/usr/bin/env bash
#
# Installer di SoundText per Linux.
#
# Cosa fa:
#   - rileva la distribuzione e installa le dipendenze di sistema
#     (fluidsynth, portaudio, lilv) col package manager
#     giusto (apt/dnf/pacman/zypper);
#   - copia il codice sorgente in ~/.local/share/soundtext (senza mai
#     cancellare le sottocartelle songs/ e soundfonts/, dove l'app salva
#     i progetti e i SoundFont dell'utente);
#   - il SoundFont GM non lo installa: SoundText lo propone al primo
#     avvio (Suoni -> Scarica e installa);
#   - crea un virtualenv Python dedicato e ci installa i pacchetti pip
#     (PySide6, mido, sounddevice, numpy, pedalboard);
#   - installa un comando "soundtext" in ~/.local/bin (e, se manca,
#     aggiunge ~/.local/bin al PATH in ~/.bashrc o ~/.zshrc) e una voce nel
#     menu applicazioni (con icona); avviato dal menu, se il programma non
#     parte mostra un avviso col log (~/.local/state/soundtext/soundtext.log).
#
# Va lanciato dalla cartella del repository; se accanto allo script non ci
# sono i sorgenti (per esempio e' stato scaricato da solo), li scarica da
# GitHub.
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
# Con "curl ... | bash" BASH_SOURCE e' vuoto: si parte dalla cartella corrente
# (e, se li' non ci sono i sorgenti, li si scarica: vedi sotto).
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
SOURCE_URL="https://github.com/openssound/soundtext/archive/refs/heads/main.tar.gz"

ASSUME_YES=0
ACTION="install"
for arg in "$@"; do
    case "$arg" in
        -y|--yes) ASSUME_YES=1 ;;
        --uninstall) ACTION="uninstall" ;;
        --purge) ACTION="purge" ;;
        -h|--help)
            sed -n '2,38p' "${BASH_SOURCE[0]:-$0}" | sed 's/^# \{0,1\}//'
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
# Sorgenti: dalla cartella dello script, altrimenti scaricati da GitHub
# ---------------------------------------------------------------------------

has_sources() {
    [ -f "$1/main.py" ] && [ -f "$1/requirements.txt" ] && [ -d "$1/core" ] && [ -d "$1/gui" ]
}

if ! has_sources "$SRC_DIR"; then
    warn "Accanto allo script ($SRC_DIR) non ci sono i sorgenti di $APP_NAME"
    warn "(main.py, requirements.txt, core/, gui/): li scarico da GitHub."
    if ! command -v curl >/dev/null 2>&1; then
        error "curl non trovato: scarica il repository completo (Code -> Download ZIP"
        error "su https://github.com/openssound/soundtext, oppure git clone),"
        error "estrailo e lancia ./install.sh da quella cartella."
        exit 1
    fi
    DOWNLOAD_DIR="$(mktemp -d)"
    trap 'rm -rf "$DOWNLOAD_DIR"' EXIT
    if ! curl -fsSL "$SOURCE_URL" | tar -xz -C "$DOWNLOAD_DIR" --strip-components=1 \
        || ! has_sources "$DOWNLOAD_DIR"; then
        error "Download dei sorgenti non riuscito ($SOURCE_URL)."
        error "Scarica il repository completo (Code -> Download ZIP, oppure git"
        error "clone), estrailo e lancia ./install.sh da quella cartella."
        exit 1
    fi
    SRC_DIR="$DOWNLOAD_DIR"
    info "Sorgenti scaricati."
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
            pkgs=(python3-venv python3-pip fluidsynth libportaudio2 liblilv-0-0)
            ;;
        fedora)
            cmd=(sudo dnf install -y)
            pkgs=(python3-pip fluidsynth portaudio lilv-libs)
            ;;
        arch)
            cmd=(sudo pacman -S --needed --noconfirm)
            pkgs=(python-pip fluidsynth portaudio lilv)
            ;;
        opensuse)
            cmd=(sudo zypper install -y)
            pkgs=(python3-pip fluidsynth portaudio liblilv-0-0)
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

    if [ "${#failed[@]}" -gt 0 ]; then
        warn "Pacchetti non installati (nome diverso su questa distro o non"
        warn "disponibile nei repository abilitati): ${failed[*]}"
        warn "Vedi docs/HELP.md per alternative. L'app funziona comunque; senza"
        warn "fluidsynth non sentirai l'audio, senza portaudio non"
        warn "potrai registrare ne' ascoltare con loop e salti."
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
    # soundfonts/ e songs/ sono dell'utente: si creano vuote, non si copiano
    mkdir -p "$INSTALL_DIR/soundfonts" "$INSTALL_DIR/songs"
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

for needed in main.py requirements.txt; do
    if [ ! -f "$INSTALL_DIR/$needed" ]; then
        error "$INSTALL_DIR/$needed manca dopo la copia dei sorgenti: installazione interrotta."
        exit 1
    fi
done

info "Creo il virtualenv Python (puo' richiedere qualche minuto, PySide6 e' grande)..."
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip wheel >/dev/null
# pedalboard >= 0.9.17 richiede AVX: senza, l'import va in SIGILL
PIP_EXTRA=()
if [ -r /proc/cpuinfo ] && ! grep -qw avx /proc/cpuinfo; then
    PIP_EXTRA=("pedalboard<0.9.17")
fi
if ! "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" "${PIP_EXTRA[@]}"; then
    # python-rtmidi e' facoltativo (solo tastiere MIDI esterne) ed e' il
    # pacchetto che piu' spesso va compilato (servono gli header ALSA e un
    # compilatore): senza, il resto dell'installazione non si blocca.
    warn "pip non e' riuscito a installare tutti i pacchetti: riprovo senza"
    warn "python-rtmidi (facoltativo, serve solo per suonare con una tastiera MIDI)."
    REQ_NO_RTMIDI="$(mktemp)"
    grep -v '^python-rtmidi' "$INSTALL_DIR/requirements.txt" > "$REQ_NO_RTMIDI"
    "$INSTALL_DIR/venv/bin/pip" install -r "$REQ_NO_RTMIDI" "${PIP_EXTRA[@]}"
    rm -f "$REQ_NO_RTMIDI"
fi

if ! "$INSTALL_DIR/venv/bin/python3" -c "import PySide6, st_language, mido" >/dev/null 2>&1; then
    error "Il virtualenv non riesce a importare PySide6/st_language/mido: guarda"
    error "gli errori di pip qui sopra e rilancia lo script."
    exit 1
fi

# ---------------------------------------------------------------------------
# Comando "soundtext", voce di menu e icona
# ---------------------------------------------------------------------------

info "Installo il comando 'soundtext' in $BIN_DIR..."
mkdir -p "$BIN_DIR"
# Da terminale l'output resta nel terminale; avviato dal menu applicazioni
# (nessun terminale) va in un log e, se il programma si chiude con un
# errore, un avviso dice dove guardare invece di non far comparire nulla.
cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
if [ -t 2 ]; then
    exec "$INSTALL_DIR/venv/bin/python3" "$INSTALL_DIR/main.py" "\$@"
fi
LOG="\${XDG_STATE_HOME:-\$HOME/.local/state}/soundtext/soundtext.log"
mkdir -p "\$(dirname "\$LOG")"
"$INSTALL_DIR/venv/bin/python3" "$INSTALL_DIR/main.py" "\$@" >"\$LOG" 2>&1
status=\$?
if [ "\$status" -ne 0 ]; then
    msg="SoundText non si e' avviato (errore \$status). Dettagli in \$LOG"
    if command -v notify-send >/dev/null 2>&1; then
        notify-send -i soundtext "SoundText" "\$msg"
    elif command -v zenity >/dev/null 2>&1; then
        zenity --error --text="\$msg"
    elif command -v kdialog >/dev/null 2>&1; then
        kdialog --error "\$msg"
    fi
fi
exit "\$status"
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
    PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'
    case "${SHELL##*/}" in
        zsh)  RC_FILE="$HOME/.zshrc" ;;
        bash) RC_FILE="$HOME/.bashrc" ;;
        *)    RC_FILE="" ;;
    esac
    if [ -n "${FISH_VERSION:-}" ] || [ "${SHELL##*/}" = "fish" ]; then
        warn "$BIN_DIR non e' nel tuo PATH: con fish aggiungilo con"
        warn "'fish_add_path $BIN_DIR' (la voce nel menu applicazioni funziona gia')."
    elif [ -z "$RC_FILE" ]; then
        warn "$BIN_DIR non e' nel tuo PATH, quindi 'soundtext' da terminale non"
        warn "funzionera' finche' non aggiungi '$PATH_LINE' al file di avvio"
        warn "della tua shell (la voce nel menu applicazioni funziona gia')."
    elif [ -f "$RC_FILE" ] && grep -qF "$PATH_LINE" "$RC_FILE"; then
        info "$BIN_DIR e' gia' aggiunto al PATH in $RC_FILE: apri un nuovo terminale."
    elif confirm "Aggiungo $BIN_DIR al PATH in $RC_FILE, per usare 'soundtext' da terminale?"; then
        printf '\n# SoundText (install.sh)\n%s\n' "$PATH_LINE" >> "$RC_FILE"
        info "Aggiunto a $RC_FILE: apri un nuovo terminale per usare 'soundtext'."
    else
        warn "$BIN_DIR non e' nel tuo PATH, quindi 'soundtext' da terminale non"
        warn "funzionera' finche' non aggiungi '$PATH_LINE' a $RC_FILE"
        warn "(la voce nel menu applicazioni funziona gia')."
    fi
fi
echo "Avvia $APP_NAME dal menu applicazioni, oppure da terminale con: soundtext"
if [ ! -f "$HOME/.local/lib/soundtext/libsfizz.so" ]; then
    echo "Facoltativo: per suonare i file .sfz senza plugin (Strumento SFZ interno) compila"
    echo "il motore sfizioso con: $INSTALL_DIR/scarica_strumenti.sh libreria"
fi
