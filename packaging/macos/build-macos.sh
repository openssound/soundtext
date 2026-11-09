#!/bin/bash
# Costruisce SoundText.app e la .dmg da distribuire, per l'architettura di
# questo Mac (arm64 = Apple Silicon, x86_64 = Intel). Lo usa il job
# build-macos di .github/workflows/build-release.yml; si puo' lanciare anche
# a mano su un Mac.
#
#     FLUIDSYNTH_LIB=.../libfluidsynth.3.dylib packaging/macos/build-macos.sh [vX.Y.Z]
#
# FLUIDSYNTH_LIB viene da packaging/macos/build-fluidsynth.sh. Il Python
# usato (PYTHON, predefinito python3) deve avere requirements.txt e
# pyinstaller installati.
#
# Firma:
#   - senza SOUNDTEXT_CODESIGN_IDENTITY: firma ad-hoc. L'app funziona, ma al
#     primo avvio macOS chiede di autorizzarla (Impostazioni di Sistema ->
#     Privacy e sicurezza -> Apri comunque): lo spiega il Leggimi nella .dmg;
#   - con SOUNDTEXT_CODESIGN_IDENTITY="Developer ID Application: ...": firma
#     con il certificato (gia' nel portachiavi) e il runtime "hardened"; con
#     anche APPLE_API_KEY_PATH, APPLE_API_KEY_ID e APPLE_API_ISSUER (chiave
#     API di App Store Connect) la .dmg si notarizza e si "graffa".

set -euo pipefail

cd "$(dirname "$0")/../.."
PYTHON="${PYTHON:-python3}"
VERSION="$(sed -n 's/^APP_VERSION = "\(.*\)"$/\1/p' core/version.py)"
TAG="${1:-v$VERSION}"
ARCH="$(uname -m)"
FLUIDSYNTH_LIB="${FLUIDSYNTH_LIB:?serve FLUIDSYNTH_LIB (vedi packaging/macos/build-fluidsynth.sh)}"
FLUIDSYNTH_LICENSES="${FLUIDSYNTH_LICENSES:-$(dirname "$FLUIDSYNTH_LIB")/../licenze}"
IDENTITY="${SOUNDTEXT_CODESIGN_IDENTITY:--}"
# la versione minima di macOS: quella di soundtext.spec, o SOUNDTEXT_MACOS_MINIMUM
MINIMUM_MACOS="${SOUNDTEXT_MACOS_MINIMUM:-$(sed -n 's/.*minimum_macos = .* or "\([0-9.]*\)".*/\1/p' soundtext.spec)}"
[ -n "$MINIMUM_MACOS" ] || { echo "versione minima di macOS non trovata in soundtext.spec" >&2; exit 1; }
export SOUNDTEXT_MACOS_MINIMUM="$MINIMUM_MACOS"
APP="dist/SoundText.app"
RES="$APP/Contents/Resources"
FW="$APP/Contents/Frameworks"
DMG="SoundText-macos-$ARCH-$TAG.dmg"

fail() { echo "ERRORE: $*" >&2; exit 1; }

# I file Mach-O dell'app (eseguibili e librerie), uno per riga.
macho_files() {
    find "$APP/Contents" -type f \( -name "*.dylib" -o -name "*.so" -o -perm -u+x \) -print0 |
        while IFS= read -r -d '' f; do
            case "$(file -b "$f")" in *Mach-O*) printf '%s\n' "$f" ;; esac
        done
}

echo "== PyInstaller ($ARCH, SoundText $VERSION, macOS $MINIMUM_MACOS e successivi)"
rm -rf build dist
"$PYTHON" -m PyInstaller soundtext.spec --noconfirm --log-level WARN
[ -x "$APP/Contents/MacOS/SoundText" ] || fail "SoundText.app non creata"

# Le cartelle lette a runtime (core.version.get_app_root: nell'app e'
# Contents/Resources). Stesso elenco del job Windows, senza songs/ e midi/:
# progetti e libreria MIDI dell'utente stanno fuori dall'app
# (~/Documents/SoundText, vedi core.version.pick_writable_dir).
echo "== Cartelle dati in Contents/Resources"
for dir in assets docs locales examples licenses; do
    cp -R "$dir" "$RES/"
done
rm -rf "$RES/docs/guida_brano"          # le immagini della guida PDF non servono al programma
cp LICENSE THIRD_PARTY_NOTICES.md scarica_strumenti.py "$RES/"
cp -R "$("$PYTHON" -c 'import os, verovio; print(os.path.join(os.path.dirname(verovio.__file__), "data"))')" \
    "$RES/verovio-data"
[ -f "$RES/docs/HELP.md" ] || fail "guida utente mancante"
[ -f "$RES/locales/en.json" ] || fail "traduzioni mancanti"
[ ! -e "$RES/docs/guida_brano" ] || fail "le immagini della guida PDF non devono stare nell'app"

# FluidSynth (2.4.7, con glib e libsndfile dentro: build-fluidsynth.sh) in
# Contents/Frameworks, dove core.fluid lo cerca per primo.
echo "== FluidSynth"
cp "$FLUIDSYNTH_LIB" "$FW/libfluidsynth.3.dylib"
mkdir -p "$RES/licenses/fluidsynth-macos"
if [ -d "$FLUIDSYNTH_LICENSES" ]; then
    cp "$FLUIDSYNTH_LICENSES"/* "$RES/licenses/fluidsynth-macos/"
fi

# Il motore SFZ interno gia' compilato (release libsfizz-*, universale), in
# lib/ dove core.sfz_engine lo cerca.
echo "== Motore SFZ interno (libsfizz)"
"$PYTHON" scarica_strumenti.py libreria --in "$RES/lib"

echo "== Componenti e licenze"
"$PYTHON" .github/scripts/avvisi_build.py "$RES/licenses/COMPONENTI.txt" \
    "FluidSynth 2.4.7 compilato per macOS $MINIMUM_MACOS ($ARCH) con dentro GLib e libsndfile (licenses/fluidsynth-macos.txt)" \
    "libsfizz: sfizioso, commit in scarica_strumenti.py (licenses/sfizioso.txt)"
[ -s "$RES/licenses/COMPONENTI.txt" ] || fail "COMPONENTI.txt mancante"

# Niente librerie di Homebrew (ci sarebbero solo sui Mac con Homebrew) e
# niente per un macOS piu' recente di quello dichiarato. Per i pacchetti
# Python conta il macOS che dichiara il loro wheel (i binari dentro possono
# portare un "minos" piu' alto senza usarlo: PySide6 6.11 dice 13, i suoi
# binari 15); per il resto (l'interprete Python con le sue librerie,
# FluidSynth, libsfizz, l'eseguibile) il minos dei binari.
echo "== Controllo delle librerie"
"$PYTHON" packaging/macos/wheel_minimum.py "$MINIMUM_MACOS" || fail "pacchetti Python per un macOS piu' recente"
bad=""
while IFS= read -r f; do
    if otool -L "$f" | tail -n +2 | grep -q -E "/opt/homebrew/|/usr/local/|/opt/local/"; then
        bad="$bad\n  $f: $(otool -L "$f" | grep -E "/opt/homebrew/|/usr/local/|/opt/local/" | head -1)"
    fi
    rel="${f#"$APP/Contents/"}"
    case "$rel" in
        MacOS/*|Resources/lib/*|Frameworks/Python.framework/*|Frameworks/python3__dot__*/lib-dynload/*) ;;
        Frameworks/*/*) continue ;;          # pacchetti Python: vale il wheel, controllato sopra
    esac
    minos="$(otool -l "$f" | awk '/LC_BUILD_VERSION/{b=1} b && /minos/{print $2; exit}')"
    if [ -n "$minos" ] && [ "$(printf '%s\n%s\n' "$minos" "$MINIMUM_MACOS" | sort -V | tail -1)" != "$MINIMUM_MACOS" ]; then
        bad="$bad\n  $rel: richiede macOS $minos"
    fi
done < <(macho_files)
[ -z "$bad" ] || fail "librerie non adatte a macOS $MINIMUM_MACOS:$(printf "$bad")"

# Prova di avvio senza schermo: Qt, FluidSynth dell'app, libsfizz,
# pedalboard, PortAudio, dati (main.py --self-test).
echo "== Prova di avvio"
# (libsfizz: quello dell'app, non uno gia' scaricato in ~/Library/Application Support)
out="$(QT_QPA_PLATFORM=offscreen SOUNDTEXT_SFZ_LIB="$PWD/$RES/lib/libsfizz.dylib" \
    "$APP/Contents/MacOS/SoundText" --self-test 2>&1)" || { echo "$out"; fail "la prova di avvio non e' passata"; }
echo "$out"
echo "$out" | grep -q "FluidSynth: 2.4.7 da .*SoundText.app" || fail "FluidSynth non e' quello dell'app"
echo "$out" | grep -q "motore SFZ: .*SoundText.app" || fail "libsfizz non e' quello dell'app"

# Firma: dall'interno verso l'esterno (librerie, framework, poi l'app con
# gli entitlements). Ad-hoc ("-") senza certificato.
echo "== Firma ($([ "$IDENTITY" = "-" ] && echo "ad-hoc" || echo "$IDENTITY"))"
opts=(--force --sign "$IDENTITY")
[ "$IDENTITY" = "-" ] || opts+=(--options runtime --timestamp)
while IFS= read -r f; do
    [ "$f" = "$APP/Contents/MacOS/SoundText" ] || codesign "${opts[@]}" "$f"
done < <(macho_files)
find "$APP/Contents" -type d -name "*.framework" -prune -print0 | while IFS= read -r -d '' fw; do
    codesign "${opts[@]}" "$fw"
done
codesign "${opts[@]}" --entitlements packaging/macos/entitlements.plist "$APP"
codesign --verify --deep --strict --verbose=2 "$APP"

echo "== Immagine disco $DMG"
staging="$(mktemp -d)"
trap 'rm -rf "$staging"' EXIT
cp -R "$APP" "$staging/"
ln -s /Applications "$staging/Applications"
if [ "$IDENTITY" = "-" ]; then
    cp packaging/macos/Leggimi.txt "$staging/Leggimi - Read me.txt"
fi
rm -f "$DMG"
hdiutil create -volname "SoundText" -srcfolder "$staging" -ov -format UDZO "$DMG" > /dev/null
if [ "$IDENTITY" != "-" ]; then
    codesign --force --sign "$IDENTITY" --timestamp "$DMG"
    if [ -n "${APPLE_API_KEY_PATH:-}" ]; then
        echo "== Notarizzazione"
        xcrun notarytool submit "$DMG" --key "$APPLE_API_KEY_PATH" --key-id "${APPLE_API_KEY_ID:?}" \
            --issuer "${APPLE_API_ISSUER:?}" --wait
        xcrun stapler staple "$DMG"
    fi
fi
hdiutil verify "$DMG" > /dev/null
echo "Pronto: $DMG ($(du -h "$DMG" | cut -f1))"
