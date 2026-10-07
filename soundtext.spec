# -*- mode: python ; coding: utf-8 -*-
# Build PyInstaller di SoundText (modalita' onedir, finestra senza console),
# usata da build-windows-portable.ps1 e build-linux-portable.sh:
#
#     python -m PyInstaller soundtext.spec --noconfirm
#
# Stesse opzioni della build delle release (.github/workflows/build-release.yml).
# Le cartelle dati lette accanto all'eseguibile (assets/, docs/, locales/,
# examples/, ...: vedi core.version.get_app_root) non stanno qui: le
# affiancano gli script dopo la build.

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
