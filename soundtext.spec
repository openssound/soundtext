# -*- mode: python ; coding: utf-8 -*-
# Build PyInstaller di SoundText (modalita' onedir, finestra senza console),
# usata da build-windows-portable.ps1, build-linux-portable.sh e, su macOS,
# da packaging/macos/build-macos.sh, che ne fa SoundText.app (BUNDLE qui
# sotto, con Info.plist e icona):
#
#     python -m PyInstaller soundtext.spec --noconfirm
#
# Stesse opzioni della build delle release (.github/workflows/build-release.yml).
# Le cartelle dati lette accanto all'eseguibile (assets/, docs/, locales/,
# examples/, ...: vedi core.version.get_app_root) non stanno qui: le
# affiancano gli script dopo la build.

import os
import re
import sys

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files("verovio") + collect_data_files("st_language")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SoundText",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon="assets/soundtext.ico" if sys.platform == "win32" else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="SoundText",
)

if sys.platform == "darwin":
    # La versione e' una sola, in core/version.py.
    with open("core/version.py", encoding="utf-8") as f:
        version = re.search(r'APP_VERSION = "([^"]+)"', f.read()).group(1)
    # La versione minima di macOS e' quella di Qt (PySide6 6.11: macOS 13);
    # packaging/macos/build-macos.sh controlla che nell'app non ci sia niente
    # che chieda di piu' (SOUNDTEXT_MACOS_MINIMUM la cambia, per esempio per
    # una prova con il Python di Homebrew).
    minimum_macos = os.environ.get("SOUNDTEXT_MACOS_MINIMUM") or "13.0"
    app = BUNDLE(
        coll,
        name="SoundText.app",
        icon="assets/SoundText.icns",
        bundle_identifier="org.openssound.soundtext",
        version=version,
        info_plist={
            "CFBundleName": "SoundText",
            "CFBundleDisplayName": "SoundText",
            "CFBundleShortVersionString": version,
            "CFBundleVersion": version,
            "LSMinimumSystemVersion": minimum_macos,
            "LSApplicationCategoryType": "public.app-category.music",
            "NSHighResolutionCapable": True,
            # senza, macOS nega il microfono (o chiude l'app) alla prima registrazione
            "NSMicrophoneUsageDescription":
                "SoundText usa il microfono o la scheda audio per registrare le tracce audio.",
            "NSHumanReadableCopyright": "SoundText, licenza GPL-3.0",
            # i brani .st: doppio clic nel Finder apre SoundText (main.py, QFileOpenEvent)
            "UTExportedTypeDeclarations": [{
                "UTTypeIdentifier": "org.openssound.soundtext.song",
                "UTTypeDescription": "Brano SoundText",
                "UTTypeConformsTo": ["public.plain-text"],
                "UTTypeIconFile": "SoundText.icns",
                "UTTypeTagSpecification": {"public.filename-extension": ["st"]},
            }],
            "CFBundleDocumentTypes": [{
                "CFBundleTypeName": "Brano SoundText",
                "CFBundleTypeRole": "Editor",
                "LSHandlerRank": "Owner",
                "LSItemContentTypes": ["org.openssound.soundtext.song"],
                "CFBundleTypeIconFile": "SoundText.icns",
            }],
        },
    )
