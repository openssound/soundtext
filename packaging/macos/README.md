# SoundText.app per macOS

Qui c'è tutto quello che serve per costruire la `.dmg` per macOS. Lo usa il job
`build-macos` di `.github/workflows/build-release.yml` a ogni tag `v*`, una volta
per architettura: `macos-15` per Apple Silicon e `macos-15-intel` per Intel.

| File | Cosa fa |
|---|---|
| `build-fluidsynth.sh` | compila FluidSynth 2.4.7 per macOS 13 e successivi, con glib e libsndfile statiche dentro: un solo `libfluidsynth.3.dylib` che dipende solo dal sistema |
| `build-macos.sh` | PyInstaller (`soundtext.spec`, con `BUNDLE`), cartelle dati in `Contents/Resources`, FluidSynth in `Contents/Frameworks`, libsfizz, licenze, controlli, prova di avvio (`--self-test`), firma, `.dmg` |
| `wheel_minimum.py` | controlla che i pacchetti Python non chiedano un macOS più recente del minimo dell'app |
| `entitlements.plist` | microfono e caricamento di plugin di altri produttori, con il runtime "hardened" |
| `Leggimi.txt` | va nella `.dmg` quando l'app è firmata ad-hoc: come aprirla la prima volta |

## Su un Mac

```bash
packaging/macos/build-fluidsynth.sh fluidsynth-build
python3 -m venv venv && venv/bin/pip install -r requirements.txt pyinstaller
FLUIDSYNTH_LIB="$PWD/fluidsynth-build/prefix/lib/libfluidsynth.3.dylib" PYTHON="$PWD/venv/bin/python" \
    packaging/macos/build-macos.sh
```

Servono cmake, pkg-config e gli Xcode Command Line Tools. Il Python di
Homebrew è compilato per il macOS su cui gira: con quello `build-macos.sh` si
ferma, perché l'app non partirebbe su macOS 13. In quel caso c'è il Python
di python.org, oppure `SOUNDTEXT_MACOS_MINIMUM=14.0` per una prova che dichiara
il minimo vero.

## Firma Developer ID e notarizzazione

Senza secret l'app si firma ad-hoc: funziona, ma al primo avvio macOS chiede
di autorizzarla (`Leggimi.txt`). Con un account Apple Developer, questi secret
del repository attivano la firma e la notarizzazione:

| Secret | Contenuto |
|---|---|
| `MACOS_CERTIFICATE` | il certificato "Developer ID Application" esportato in `.p12`, in base64 |
| `MACOS_CERTIFICATE_PASSWORD` | la password del `.p12` |
| `MACOS_CODESIGN_IDENTITY` | il nome del certificato, per esempio `Developer ID Application: Nome (TEAMID)` |
| `APPLE_API_KEY` | la chiave API di App Store Connect (`.p8`), in base64 |
| `APPLE_API_KEY_ID`, `APPLE_API_ISSUER` | ID della chiave e Issuer ID, da App Store Connect → Utenti e accesso → Chiavi |

Il certificato si importa in un portachiavi temporaneo del runner, che viene
cancellato a fine job. La `.dmg` notarizzata viene anche "graffata" (`stapler`),
così si apre senza avvisi anche senza rete.
