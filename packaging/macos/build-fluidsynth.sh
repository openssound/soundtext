#!/bin/bash
# Compila FluidSynth per SoundText.app (vedi build-macos.sh): un solo
# libfluidsynth.3.dylib, per l'architettura di questo Mac, che dipende solo
# da librerie e framework di sistema. glib e libsndfile (con ogg, vorbis,
# flac e opus, per i SoundFont .sf3) si compilano statiche e finiscono
# dentro la libreria: nell'app non serve Homebrew.
#
# Tutto con la versione minima di macOS dell'app (MACOSX_DEPLOYMENT_TARGET):
# le librerie di Homebrew sono compilate per il macOS su cui girano, e
# copiate da un Mac con macOS 15 l'app non partirebbe su macOS 13 e 14.
#
# FluidSynth e' fissato alla 2.4.7, come su Windows (build-release.yml): la
# 2.6 chiude SoundText con piu' di 5 gruppi audio
# (core.fluid.supports_channel_groups).
#
# Uso:
#     packaging/macos/build-fluidsynth.sh CARTELLA_DI_LAVORO
# Alla fine: CARTELLA_DI_LAVORO/prefix/lib/libfluidsynth.3.dylib
#
# Servono: cmake, pkg-config, Xcode Command Line Tools, python3 (meson e
# ninja si installano in un ambiente virtuale nella cartella di lavoro).

set -euo pipefail

WORK="$(mkdir -p "${1:?cartella di lavoro}" && cd "$1" && pwd)"
PREFIX="$WORK/prefix"
SRC="$WORK/src"
mkdir -p "$PREFIX" "$SRC"

export MACOSX_DEPLOYMENT_TARGET="${MACOSX_DEPLOYMENT_TARGET:-13.0}"
export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig"
export CFLAGS="-O2 -mmacosx-version-min=$MACOSX_DEPLOYMENT_TARGET"
export CXXFLAGS="$CFLAGS"
export LDFLAGS="-mmacosx-version-min=$MACOSX_DEPLOYMENT_TARGET"
JOBS="$(sysctl -n hw.ncpu)"

# nome, URL, sha256
SOURCES=(
  "libogg-1.3.6|https://github.com/xiph/ogg/releases/download/v1.3.6/libogg-1.3.6.tar.gz|83e6704730683d004d20e21b8f7f55dcb3383cdf84c0daedf30bde175f774638"
  "libvorbis-1.3.7|https://github.com/xiph/vorbis/releases/download/v1.3.7/libvorbis-1.3.7.tar.gz|0e982409a9c3fc82ee06e08205b1355e5c6aa4c36bca58146ef399621b0ce5ab"
  "flac-1.5.0|https://github.com/xiph/flac/releases/download/1.5.0/flac-1.5.0.tar.xz|f2c1c76592a82ffff8413ba3c4a1299b6c7ab06c734dee03fd88630485c2b920"
  "opus-1.5.2|https://github.com/xiph/opus/releases/download/v1.5.2/opus-1.5.2.tar.gz|65c1d2f78b9f2fb20082c38cbe47c951ad5839345876e46941612ee87f9a7ce1"
  "libsndfile-1.2.2|https://github.com/libsndfile/libsndfile/releases/download/1.2.2/libsndfile-1.2.2.tar.xz|3799ca9924d3125038880367bf1468e53a1b7e3686a934f098b7e1d286cdb80e"
  "glib-2.84.4|https://download.gnome.org/sources/glib/2.84/glib-2.84.4.tar.xz|8a9ea10943c36fc117e253f80c91e477b673525ae45762942858aef57631bb90"
  "fluidsynth-2.4.7|https://github.com/FluidSynth/fluidsynth/archive/refs/tags/v2.4.7.tar.gz|7fb0e328c66a24161049e2b9e27c3b6e51a6904b31b1a647f73cc1f322523e88"
)

fetch() {
    local name url sha file
    IFS="|" read -r name url sha <<< "$1"
    file="$SRC/$(basename "$url")"
    [ -f "$file" ] || curl -fsSL --retry 3 -o "$file" "$url"
    if [ "$(shasum -a 256 "$file" | cut -d' ' -f1)" != "$sha" ]; then
        echo "sha256 diverso per $file: $(shasum -a 256 "$file" | cut -d' ' -f1)" >&2
        exit 1
    fi
    rm -rf "$SRC/$name"
    mkdir -p "$SRC/$name"
    tar -xf "$file" -C "$SRC/$name" --strip-components 1
    echo "$SRC/$name"
}

cmake_static() {     # cartella sorgente, opzioni in piu'
    local dir="$1"; shift
    cmake -S "$dir" -B "$dir/build" -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX="$PREFIX" -DCMAKE_PREFIX_PATH="$PREFIX" -DBUILD_SHARED_LIBS=OFF \
        -DCMAKE_OSX_DEPLOYMENT_TARGET="$MACOSX_DEPLOYMENT_TARGET" -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
        -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DBUILD_TESTING=OFF "$@" > "$dir/cmake.log"
    cmake --build "$dir/build" -j "$JOBS" > "$dir/build.log"
    cmake --install "$dir/build" > /dev/null
}

echo "== ogg, vorbis, flac, opus"
cmake_static "$(fetch "${SOURCES[0]}")"
cmake_static "$(fetch "${SOURCES[1]}")"
cmake_static "$(fetch "${SOURCES[2]}")" -DBUILD_PROGRAMS=OFF -DBUILD_EXAMPLES=OFF -DBUILD_DOCS=OFF \
    -DINSTALL_MANPAGES=OFF -DWITH_OGG=ON
cmake_static "$(fetch "${SOURCES[3]}")" -DOPUS_BUILD_PROGRAMS=OFF -DOPUS_BUILD_TESTING=OFF

echo "== libsndfile"
cmake_static "$(fetch "${SOURCES[4]}")" -DBUILD_PROGRAMS=OFF -DBUILD_EXAMPLES=OFF -DENABLE_EXTERNAL_LIBS=ON \
    -DENABLE_MPEG=OFF -DINSTALL_PKGCONFIG_MODULE=ON -DENABLE_CPACK=OFF

echo "== glib (con pcre2, libffi e proxy-libintl come sottoprogetti)"
if [ ! -x "$WORK/venv/bin/meson" ]; then
    python3 -m venv "$WORK/venv"
    "$WORK/venv/bin/pip" install -q "meson==1.8.2" "ninja==1.11.1.4" packaging
fi
GLIB="$(fetch "${SOURCES[5]}")"
PATH="$WORK/venv/bin:$PATH" meson setup "$GLIB/build" "$GLIB" --prefix="$PREFIX" --libdir=lib \
    --buildtype=release --default-library=static --wrap-mode=forcefallback --force-fallback-for=libpcre2-8 \
    -Dtests=false -Dintrospection=disabled -Dnls=disabled -Dman-pages=disabled -Ddocumentation=false \
    -Dsysprof=disabled -Dglib_debug=disabled -Dlibelf=disabled -Dxattr=false \
    -Dc_args="$CFLAGS" -Dc_link_args="$LDFLAGS" -Dobjc_args="$CFLAGS" > "$GLIB/meson.log"
PATH="$WORK/venv/bin:$PATH" ninja -C "$GLIB/build" > "$GLIB/build.log"
PATH="$WORK/venv/bin:$PATH" meson install -C "$GLIB/build" > /dev/null

echo "== FluidSynth"
# le librerie statiche portano le loro dipendenze solo in pkg-config --static
STATIC_LIBS="$(pkg-config --static --libs glib-2.0 gthread-2.0 sndfile)"
FS="$(fetch "${SOURCES[6]}")"
cmake -S "$FS" -B "$FS/build" -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$PREFIX" \
    -DCMAKE_PREFIX_PATH="$PREFIX" -DCMAKE_OSX_DEPLOYMENT_TARGET="$MACOSX_DEPLOYMENT_TARGET" \
    -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DBUILD_SHARED_LIBS=ON -DCMAKE_INSTALL_NAME_DIR="@rpath" \
    -DCMAKE_SHARED_LINKER_FLAGS="$STATIC_LIBS" -DCMAKE_EXE_LINKER_FLAGS="$STATIC_LIBS" \
    -Denable-framework=off -Denable-libsndfile=on -Denable-coreaudio=on -Denable-coremidi=on \
    -Denable-dbus=off -Denable-jack=off -Denable-sdl3=off -Denable-pulseaudio=off -Denable-pipewire=off \
    -Denable-readline=off -Denable-ladspa=off -Denable-libinstpatch=off -Denable-midishare=off \
    -Denable-network=off -Denable-ipv6=off -Denable-openmp=off -Denable-systemd=off -Denable-portaudio=off \
    > "$FS/cmake.log"
cmake --build "$FS/build" -j "$JOBS" --target libfluidsynth > "$FS/build.log"
cp "$FS"/build/src/libfluidsynth.3*.dylib "$PREFIX/lib/" 2>/dev/null || cp "$FS"/build/src/libfluidsynth*.dylib "$PREFIX/lib/"
LIB="$PREFIX/lib/libfluidsynth.3.dylib"
[ -f "$LIB" ] || LIB="$(ls "$PREFIX"/lib/libfluidsynth.*.dylib | head -1)"
install_name_tool -id "@rpath/libfluidsynth.3.dylib" "$LIB"

# I testi di licenza di quello che e' dentro la libreria (vedi
# licenses/fluidsynth-macos.txt): build-macos.sh li copia nell'app.
LICENZE="$PREFIX/licenze"
mkdir -p "$LICENZE"
copy_license() {     # nome nell'app, file (il primo che esiste)
    local name="$1"; shift
    for f in "$@"; do
        if [ -f "$f" ]; then cp "$f" "$LICENZE/$name.txt"; return; fi
    done
    echo "licenza di $name non trovata" >&2
    exit 1
}
copy_license FluidSynth "$FS/LICENSE"
copy_license GLib "$GLIB/COPYING" "$GLIB/LICENSES/LGPL-2.1-or-later.txt"
copy_license PCRE2 "$GLIB"/subprojects/pcre2-*/LICENCE.md "$GLIB"/subprojects/pcre2-*/LICENCE
copy_license libffi "$GLIB/subprojects/libffi/LICENSE"
copy_license proxy-libintl "$GLIB"/subprojects/proxy-libintl/COPYING*
copy_license zlib "$GLIB"/subprojects/zlib-*/LICENSE "$GLIB"/subprojects/zlib-*/README
copy_license libsndfile "$SRC/libsndfile-1.2.2/COPYING"
copy_license libogg "$SRC/libogg-1.3.6/COPYING"
copy_license libvorbis "$SRC/libvorbis-1.3.7/COPYING"
copy_license libFLAC "$SRC/flac-1.5.0/COPYING.Xiph"
copy_license libopus "$SRC/opus-1.5.2/COPYING"

# solo librerie di sistema, e la versione minima giusta
if otool -L "$LIB" | tail -n +2 | grep -v -E "^\s+(/usr/lib/|/System/Library/|@rpath/libfluidsynth)"; then
    echo "libfluidsynth dipende da librerie fuori dal sistema" >&2
    exit 1
fi
otool -l "$LIB" | grep -A4 LC_BUILD_VERSION | grep -q "minos $MACOSX_DEPLOYMENT_TARGET" || {
    echo "libfluidsynth non e' per macOS $MACOSX_DEPLOYMENT_TARGET" >&2; exit 1; }
echo "FluidSynth pronto: $LIB"
