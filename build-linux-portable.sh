#!/usr/bin/env bash
#
# Crea una build PORTABLE di SoundText per Linux (eseguibile SoundText +
# dati), pronta da distribuire come tar.gz: chi la riceve scompatta e
# lancia ./SoundText, senza installare Python, pip o altro (FluidSynth
# incluso, se presente sulla macchina di build - vedi sotto).
#
# Va eseguito DENTRO una copia completa del repository SoundText (serve
# main.py, requirements.txt, soundtext.spec, core/, gui/, midi/, assets/,
# docs/, songs/, examples/, soundfonts/), perche' PyInstaller compila per
# la piattaforma su cui gira: il risultato funziona solo su Linux con
# un'architettura e una libc compatibili con quelle della macchina di
# build (in genere: stessa distro/versione o piu' recente).
#
# Passi:
#   1. crea un virtualenv di build temporaneo (.build-venv, separato da
#      quello eventualmente creato da install.sh) e ci installa i
#      pacchetti da requirements.txt + PyInstaller;
#   2. lancia PyInstaller con soundtext.spec (modalita' onedir);
#   3. affianca all'eseguibile le cartelle dati dell'app (assets, docs,
#      songs demo, libreria midi, esempi) e, se presente, il SoundFont GM
#      incluso nel repository (soundfonts/FluidR3_GM.sf2);
#   4. cerca libfluidsynth.so di sistema (ldconfig) e, se la trova, la
#      copia insieme alle sue dipendenze non di sistema (via ldd) in una
#      cartella lib/ accanto all'eseguibile; rinomina l'eseguibile vero
#      in SoundText.bin e installa al suo posto un piccolo wrapper
#      SoundText che imposta LD_LIBRARY_PATH su lib/ prima di lanciarlo
#      (su Linux le .so non vengono cercate nella cartella dell'eseguibile
#      come le DLL su Windows, serve dirlo esplicitamente);
#   5. comprime tutto in SoundText-portable-linux-x64.tar.gz nella cartella
#      corrente.
#
# NOTA sulla portabilita' di FluidSynth: a differenza delle DLL Windows
# (scaricate gia' pronte dai release ufficiali), su Linux non esiste un
# equivalente "binario universale" - libfluidsynth dipende da glib,
# libsndfile e altre librerie di sistema che variano da distro a distro.
# Questo script bundla quella trovata sulla macchina di build (funziona
# bene se la build gira sulla distro piu' vecchia che vuoi supportare);
# se preferisci zero rischi di incompatibilita', distribuisci install.sh
# invece di questo pacchetto: installa fluidsynth con il package manager
# della macchina di destinazione.
#
# Uso:
#   ./build-linux-portable.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

info()  { printf '\033[1;36m==>\033[0m %s\n' "$1"; }
warn()  { printf '\033[1;33m!!\033[0m %s\n' "$1" >&2; }
error() { printf '\033[1;31mERRORE:\033[0m %s\n' "$1" >&2; }

for required in main.py requirements.txt soundtext.spec; do
    if [ ! -f "$ROOT/$required" ]; then
        error "Manca '$required': lancia questo script dalla radice di una copia completa del repository SoundText, non da una copia parziale."
        exit 1
    fi
done

PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
        ver="$("$cmd" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")' 2>/dev/null || true)"
        major="${ver%%.*}"
        minor="${ver##*.}"
        if [ -n "$major" ] && [ "$major" = 3 ] && [ "$minor" -ge 10 ] 2>/dev/null; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done
if [ -z "$PYTHON_CMD" ]; then
    error "Python 3.10+ non trovato nel PATH (serve solo per compilare la build, non per chi ricevera' il tar.gz)."
    exit 1
fi
info "Uso '$PYTHON_CMD' ($("$PYTHON_CMD" --version 2>&1)) per la build."

BUILD_VENV="$ROOT/.build-venv"
if [ ! -d "$BUILD_VENV" ]; then
    info "Creo il virtualenv di build in $BUILD_VENV..."
    "$PYTHON_CMD" -m venv "$BUILD_VENV"
else
    info "Virtualenv di build gia' presente, lo riuso."
fi
VENV_PYTHON="$BUILD_VENV/bin/python3"
VENV_PIP="$BUILD_VENV/bin/pip"

info "Installo le dipendenze dell'app e PyInstaller..."
"$VENV_PYTHON" -m pip install --upgrade pip wheel >/dev/null
"$VENV_PIP" install -r "$ROOT/requirements.txt"
"$VENV_PIP" install pyinstaller pyinstaller-hooks-contrib

info "Eseguo PyInstaller (prima volta: puo' richiedere diversi minuti)..."
rm -rf "$ROOT/build" "$ROOT/dist"
"$VENV_PYTHON" -m PyInstaller "$ROOT/soundtext.spec" --noconfirm

DIST_DIR="$ROOT/dist/SoundText"
if [ ! -f "$DIST_DIR/SoundText" ]; then
    error "PyInstaller non ha prodotto l'eseguibile SoundText in $DIST_DIR."
    exit 1
fi

info "Affianco all'eseguibile le cartelle dati dell'app..."
for dir in assets docs locales songs examples midi licenses; do
    # midi/: solo la cartella, vuota (la libreria MIDI e' dell'utente: le
    # sottocartelle e il file d'esempio del repository non si distribuiscono)
    if [ "$dir" = midi ]; then
        mkdir -p "$DIST_DIR/midi"
        continue
    fi
    if [ -d "$ROOT/$dir" ]; then
        cp -a "$ROOT/$dir" "$DIST_DIR/$dir"
    fi
done
# Le immagini della guida PDF (e i suoi script) non servono al programma: la
# guida utente e' docs/HELP.md. Il manuale Word e il PDF, nella radice, non
# vengono copiati affatto.
rm -rf "$DIST_DIR/docs/guida_brano"
# Gli esempi si distribuiscono come .st: i render audio (.wav) restano fuori.
rm -f "$DIST_DIR"/examples/*.wav
# Licenza (GPL-3.0) e avvisi delle librerie di terze parti: vanno sempre
# distribuiti con il programma (vedi THIRD_PARTY_NOTICES.md).
cp "$ROOT/LICENSE" "$ROOT/THIRD_PARTY_NOTICES.md" "$DIST_DIR/"
# Script per scaricare gli strumenti virtuali (SFZ): il .sh lancia il .py.
cp "$ROOT/scarica_strumenti.sh" "$ROOT/scarica_strumenti.py" "$DIST_DIR/"
# Script che installa le librerie di sistema necessarie (FluidSynth, PortAudio, lilv, Qt).
cp "$ROOT/setup-portable-linux.sh" "$DIST_DIR/"
chmod +x "$DIST_DIR/setup-portable-linux.sh" "$DIST_DIR/scarica_strumenti.sh"
# Dati di Verovio (caratteri musicali della vista Partitura) accanto
# all'eseguibile, in verovio-data (vedi core.score_render): cosi' non
# dipende da cosa PyInstaller ha incluso del pacchetto.
VEROVIO_DATA="$("$VENV_PYTHON" -c "import os, verovio; print(os.path.join(os.path.dirname(verovio.__file__), 'data'))" 2>/dev/null || true)"
if [ -n "$VEROVIO_DATA" ] && [ -d "$VEROVIO_DATA" ]; then
    cp -a "$VEROVIO_DATA" "$DIST_DIR/verovio-data"
else
    warn "Verovio non trovato: la build non avra' la vista Partitura."
fi

SF2_SRC="$ROOT/soundfonts/FluidR3_GM.sf2"
if [ -f "$SF2_SRC" ]; then
    info "Includo il SoundFont GM (FluidR3_GM.sf2)..."
    mkdir -p "$DIST_DIR/soundfonts"
    cp "$SF2_SRC" "$DIST_DIR/soundfonts/FluidR3_GM.sf2"
else
    warn "soundfonts/FluidR3_GM.sf2 non trovato nel repository: la build non avra' un SoundFont incluso."
fi

# ---------------------------------------------------------------------------
# FluidSynth: individua libfluidsynth.so di sistema e le sue dipendenze non
# di sistema, le copia in lib/ accanto all'eseguibile, e trasforma
# l'eseguibile PyInstaller in SoundText.bin dietro un wrapper SoundText che
# imposta LD_LIBRARY_PATH (le .so non vengono cercate accanto
# all'eseguibile su Linux come invece succede per le DLL su Windows).
# ---------------------------------------------------------------------------

find_libfluidsynth() {
    if command -v ldconfig >/dev/null 2>&1; then
        ldconfig -p 2>/dev/null | grep -m1 'libfluidsynth\.so' | sed -E 's/.*=> //'
    fi
}

# librerie di base che devono venire dal sistema di destinazione (glibc,
# librerie grafiche/audio condivise con il resto del desktop): bundlarle
# rischierebbe conflitti di versione con quelle gia' caricate dal resto del
# sistema (X11, ALSA, PulseAudio...). Si bundla solo cio' che e' specifico
# di FluidSynth e difficile da trovare gia' installato.
is_system_lib() {
    case "$1" in
        libc.so*|libm.so*|libdl.so*|librt.so*|libpthread.so*|ld-linux*|\
        libgcc_s.so*|libstdc++.so*|libasound.so*|libpulse*.so*|libjack.so*|\
        libX11.so*|libgobject-2.0.so*|libglib-2.0.so*|libgio-2.0.so*|\
        libsystemd.so*|libdbus-1.so*)
            return 0 ;;
        *) return 1 ;;
    esac
}

FLUID_LIB="$(find_libfluidsynth || true)"
if [ -n "$FLUID_LIB" ] && [ -f "$FLUID_LIB" ]; then
    info "Trovato $FLUID_LIB, lo includo insieme alle sue dipendenze..."
    mkdir -p "$DIST_DIR/lib"
    cp -L "$FLUID_LIB" "$DIST_DIR/lib/"
    if command -v ldd >/dev/null 2>&1; then
        deps="$(ldd "$FLUID_LIB" 2>/dev/null | awk '{print $1, $3}')"
        while read -r name path; do
            [ -z "$path" ] && continue
            [ ! -f "$path" ] && continue
            is_system_lib "$name" && continue
            cp -L "$path" "$DIST_DIR/lib/" 2>/dev/null || true
        done <<< "$deps"
    fi
    mv "$DIST_DIR/SoundText" "$DIST_DIR/SoundText.bin"
    cat > "$DIST_DIR/SoundText" <<'LAUNCHER'
#!/usr/bin/env bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export LD_LIBRARY_PATH="$DIR/lib:${LD_LIBRARY_PATH:-}"
exec "$DIR/SoundText.bin" "$@"
LAUNCHER
    chmod +x "$DIST_DIR/SoundText"
else
    warn "libfluidsynth non trovata sul sistema di build: la build non avra' audio finche' non installi"
    warn "fluidsynth (col package manager della distro di destinazione) prima di lanciare SoundText."
fi

info "Comprimo in SoundText-portable-linux-x64.tar.gz..."
TAR_OUT="$ROOT/SoundText-portable-linux-x64.tar.gz"
rm -f "$TAR_OUT"
tar -C "$ROOT/dist" -czf "$TAR_OUT" SoundText

echo
info "Fatto: $TAR_OUT"
echo "Chi lo riceve deve scompattare il tar.gz, dare i permessi di esecuzione se necessario"
echo "(chmod +x SoundText/SoundText) e lanciare ./SoundText/SoundText: nessun Python o"
echo "installazione richiesti (FluidSynth incluso se era presente sulla macchina di build)."
