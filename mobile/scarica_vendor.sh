#!/usr/bin/env bash
# Scarica in mobile/vendor/ (non versionata) i componenti di terzi del
# prototipo SoundText Mobile, con versioni fisse e controllo SHA-256:
#   - Pyodide 314.0.7 (Python 3.14 in WebAssembly, MPL 2.0) con numpy e packaging;
#   - st-language e mido, le stesse versioni di requirements.txt (wheel py3-none-any);
#   - js-synthesizer 1.13.0 (FluidSynth 2.4.6 in WebAssembly, BSD-3 + LGPL 2.1);
#   - il SoundFont TimGM6mb (GPL 2), dallo stesso pacchetto Debian di
#     core/soundfont_downloads.py;
#   - verovio 6.3.0 (incisione della partitura in WebAssembly, LGPL 3.0), la
#     stessa versione della vista Partitura di SoundText;
#   - vosk-browser 0.0.8 (riconoscimento vocale Kaldi/Vosk in WebAssembly,
#     Apache 2.0) e i modelli piccoli di Alphacephei (Apache 2.0) per italiano,
#     inglese, francese e spagnolo,
#     per la dettatura senza rete; il modello si riconfeziona in .tar.gz,
#     il formato che legge vosk-browser.
# Poi: venv/bin/python mobile/build.py
set -euo pipefail
cd "$(dirname "$0")"
V=vendor
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

get() {  # url destinazione sha256
  curl -fsSL "$1" -o "$2.part"
  echo "$3  $2.part" | sha256sum -c --quiet
  mv "$2.part" "$2"
}

mkdir -p $V/pyodide $V/wheels $V/js-synthesizer $V/soundfont $V/verovio

PY=https://cdn.jsdelivr.net/pyodide/v314.0.7/full
get $PY/pyodide.js          $V/pyodide/pyodide.js          3141b814715a72e59b51b1b18b9ceae5bf19f7c852417e431bb0a34feadf825c
get $PY/pyodide.mjs         $V/pyodide/pyodide.mjs         6f1d60f7bf529beb300f0f47983c921d3982363640ba20af0e38efdddbc66109
get $PY/pyodide.asm.mjs     $V/pyodide/pyodide.asm.mjs     f7cdc8ece80678ceb712f8e65ebe6d3a83203a180c399865f49612a051693635
get $PY/pyodide.asm.wasm    $V/pyodide/pyodide.asm.wasm    cc36e3cab04fdfc9a63ff13eb52eae2b911bf46c025cc7b281f394bd3de1d5e6
get $PY/python_stdlib.zip   $V/pyodide/python_stdlib.zip   fa1957e5777068fc4f7437f96d860ae2fbe9c19732ba06c84e004ec16dd7dd7a
get $PY/pyodide-lock.json   $V/pyodide/pyodide-lock.json   5dc2fc119108bc148c7457dc86e7675b5c87e1cafd420b9c34c1eaef7b36c010
get $PY/numpy-2.4.6-cp314-cp314-pyemscripten_2026_0_wasm32.whl \
    $V/pyodide/numpy-2.4.6-cp314-cp314-pyemscripten_2026_0_wasm32.whl \
    a292c1f5d7d8a2208cd5e94fc467604c131cabcd2fc14fed6eefde121e7fabdf
get $PY/packaging-26.1-py3-none-any.whl $V/pyodide/packaging-26.1-py3-none-any.whl \
    565acbbea54da30348b6d68b6a54373e6f777987db9f1db6966b4b3a5060d303

PYPI=https://files.pythonhosted.org/packages/py3
rm -f $V/wheels/st_language-*.whl   # una sola versione: la snapshot di Pyodide dipende dalle wheel
get $PYPI/s/st-language/st_language-2.12.2-py3-none-any.whl $V/wheels/st_language-2.12.2-py3-none-any.whl \
    d647dc82fa2656a67cbd61a4903d67a9b7c8219ce01a8a27bf9e53329f500bb8
get $PYPI/m/mido/mido-1.3.3-py3-none-any.whl $V/wheels/mido-1.3.3-py3-none-any.whl \
    01033c9b10b049e4436fca2762194ca839b09a4334091dd3c34e7f4ae674fd8a
echo '["mido-1.3.3-py3-none-any.whl", "st_language-2.12.2-py3-none-any.whl"]' > $V/wheels/wheels.json

# npm pubblica l'impronta SHA-512 (campo "integrity" del pacchetto)
curl -fsSL https://registry.npmjs.org/js-synthesizer/-/js-synthesizer-1.13.0.tgz -o "$TMP/jss.tgz"
test "$(openssl dgst -sha512 -binary "$TMP/jss.tgz" | base64 -w0)" = \
     "KXhyJcY90mUvJwbfF1aBNurodm16w8R/wrZYRRc+SSlm58EtL88bspbs7ixtAmoV9QQvf/2EuPAwxj2ExdZSmQ=="
tar xzf "$TMP/jss.tgz" -C "$TMP"
cp "$TMP/package/dist/js-synthesizer.js" "$TMP/package/dist/js-synthesizer.worklet.js" \
   "$TMP/package/externals/libfluidsynth-2.4.6.js" "$TMP/package/LICENSE" $V/js-synthesizer/
( cd $V/js-synthesizer && sha256sum -c --quiet <<'EOF'
c7fac6ea6641c9b34ed68c9ea3bf506500f73236ed6389e77f214d627e2034b7  js-synthesizer.js
1b5e85c6402546ad21e843f1a8499e6e0d278cc76cc97306135043734ede0078  js-synthesizer.worklet.js
42ece3b53ef3289a3b30e0e1ebb4951e9da9987ae6ca975c57a0aabc91237f66  libfluidsynth-2.4.6.js
EOF
)

get https://deb.debian.org/debian/pool/main/t/timgm6mb-soundfont/timgm6mb-soundfont_1.3.orig.tar.gz "$TMP/tim.tgz" \
    af8f3a00e416dfb262bcaa904a1c84df04a51b72bbc1313aed012bc754bdf99b
tar xzf "$TMP/tim.tgz" -C "$TMP"
cp "$TMP/timgm6mb-soundfont_1.3/TimGM6mb.sf2" $V/soundfont/
echo "c5378b62028c920cb11e4803327983fee2f2cdff5dc89c708e39da417e51c854  $V/soundfont/TimGM6mb.sf2" | sha256sum -c --quiet

curl -fsSL https://registry.npmjs.org/verovio/-/verovio-6.3.0.tgz -o "$TMP/verovio.tgz"
test "$(openssl dgst -sha512 -binary "$TMP/verovio.tgz" | base64 -w0)" = \
     "1p6WhP/w3WrAhPVDTNUDH9UVPAZOnHnZVTWxclE8haHccVI/q8c+99vLH6rRgL9MuYaFR9HF4UJD6MyW2CfMwg=="
tar xzf "$TMP/verovio.tgz" -C "$TMP" package/dist/verovio-toolkit-wasm.js
cp "$TMP/package/dist/verovio-toolkit-wasm.js" $V/verovio/
echo "d794119cd5ea83a3e835849945f0289c91ac2bac427f4aa312c7010a800b46bd  $V/verovio/verovio-toolkit-wasm.js" | sha256sum -c --quiet

mkdir -p $V/vosk
curl -fsSL https://registry.npmjs.org/vosk-browser/-/vosk-browser-0.0.8.tgz -o "$TMP/vosk.tgz"
test "$(openssl dgst -sha512 -binary "$TMP/vosk.tgz" | base64 -w0)" = \
     "df9MuChirUGKxP/+4k8tBV6hJOic8IRdJXv64+ET0Ue5CddOzLZINiHOWCka765gBzHJWNtQKgaYakS0FXZIJA=="
tar xzf "$TMP/vosk.tgz" -C "$TMP" package/dist/vosk.js package/README.md
cp "$TMP/package/dist/vosk.js" $V/vosk/
echo "29504515526e974f4cb053cf08811c4de5fb2a74007c0a5a957db50eaa8d5d0c  $V/vosk/vosk.js" | sha256sum -c --quiet
# il modello: MD5 pubblicato da Alphacephei (model-list.json) e SHA-256
model() {  # nome-del-modello lingua md5 sha256
  get https://alphacephei.com/vosk/models/$1.zip "$TMP/$1.zip" $4
  echo "$3  $TMP/$1.zip" | md5sum -c --quiet
  ( cd "$TMP" && unzip -q "$1.zip" && \
    tar --sort=name --owner=0 --group=0 --numeric-owner --mtime=2022-07-12 -cf - "$1" | gzip -n -9 > "$1.tar.gz" )
  mv "$TMP/$1.tar.gz" $V/vosk/$2.tar.gz
}
model vosk-model-small-it-0.22 it fbd8f9c72cbb8c3dfa3e4581bd3585f4 \
      9ec65e75861d1c6c2e457cccd932705340dcdf233f5b239f00733b4de0bf3267
model vosk-model-small-en-us-0.15 en 09ab50ccd62b674cbaa231b825f9c1cb \
      30f26242c4eb449f948e42cb302dd7a686cb29a3423a8367f99ff41780942498
model vosk-model-small-fr-0.22 fr 8873b1234503f6edd55f54bfff31cf3e \
      cabf6180e177eb9b3a9a9d43a437bd5e549f3a7d09525e5d69a3fed787be12ad
model vosk-model-small-es-0.42 es 2d5c94f9859a84881a0ef744738ebd31 \
      09b239888f633ef2f0b4e09736e3d9936acfd810bc65d53fad45261762c6511f

echo "vendor/ pronta: $(du -sh $V | cut -f1)"
