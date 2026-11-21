#!/usr/bin/env python3
"""
Scarica e installa strumenti virtuali gratuiti (SFZ) e quello che serve per
suonarli in SoundText, su Linux, Windows e macOS. Basta Python 3.8+, senza
pacchetti in piu'.

Uso (su Windows "py" al posto di "python3"; su Linux anche ./scarica_strumenti.sh):
    python3 scarica_strumenti.py                  menu per scegliere i gruppi (elenco
                                                  se non e' un terminale)
    python3 scarica_strumenti.py host             7-Zip, sfizz, Surge XT e i plugin VST3 gratuiti
    python3 scarica_strumenti.py vst3             solo i plugin VST3 gratuiti: Dexed,
                                                  Airwindows Consolidated, Dragonfly
                                                  Reverb, OB-Xf, LSP Plugins (solo Linux),
                                                  Wolf Shaper e i plugin Chow (Windows e
                                                  macOS), per la chitarra AIDA-X, Chameleon,
                                                  Proteus, BYOD e NeuralRack, i
                                                  sintetizzatori JC-303, Six Sines e ChowKick
                                                  e gli effetti Zam
    python3 scarica_strumenti.py clap             plugin CLAP gratuiti che non esistono in
                                                  VST3: Ratatouille (Linux e Windows)
    python3 scarica_strumenti.py lv2              solo Linux: plugin LV2 gratuiti (Dragonfly
                                                  Reverb, LSP Plugins, Wolf Shaper, Geonkick,
                                                  Ratatouille, NeuralRack su ARM)
    python3 scarica_strumenti.py lilv             solo Linux: la libreria lilv, con cui
                                                  SoundText usa i plugin LV2 (apt)
    python3 scarica_strumenti.py libreria         il motore SFZ sfizioso per lo strumento
                                                  SFZ interno, gia' compilato (pochi MB);
                                                  dove non c'e' pronto, lo compila (~5 min)
    python3 scarica_strumenti.py libreria --compila
                                                  lo compila comunque, dai sorgenti
    python3 scarica_strumenti.py libreria --in CARTELLA
                                                  solo la libreria gia' compilata, in
                                                  CARTELLA (per gli installer)
    python3 scarica_strumenti.py strumenti-compilazione
                                                  installa git, cmake e il compilatore che
                                                  servono a "libreria"
    python3 scarica_strumenti.py nam-plugin       il plugin LV2 Neural Amp Modeler gia'
                                                  compilato: profili NAM 4-6 volte piu'
                                                  veloci (Linux e Windows x64)
    python3 scarica_strumenti.py piano basso      scarica i gruppi indicati
    python3 scarica_strumenti.py tutto            tutti i gruppi (esclusi gli extra)
    python3 scarica_strumenti.py extra_basso      extra: extra_basso, extra_piano,
                                                  extra_chitarre, extra_etnici,
                                                  extra_batterie
    python3 scarica_strumenti.py vsco-legni       orchestra (fuori da "tutto"): vsco-archi,
                                                  vsco-legni, vsco-ottoni, vsco-percussioni,
                                                  vcsl-vibrafono, vcsl-clavicembalo,
                                                  vcsl-percussioni

Gli strumenti vanno in ~/Strumenti (o nella cartella della variabile
STRUMENTI_DIR). I download si riprendono se interrotti e i gruppi gia'
presenti vengono saltati.
"""

import ctypes
import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

if sys.platform == "win32":
    SISTEMA = "windows"
elif sys.platform == "darwin":
    SISTEMA = "macos"
else:
    SISTEMA = "linux"

DEST = Path(os.environ.get("STRUMENTI_DIR") or Path.home() / "Strumenti")
FREEPATS = "https://freepats.zenvoid.org"

# Motore SFZ interno: sfizioso (fork di sfizz) a una versione provata con SoundText
SFIZIOSO_URL = "https://github.com/rullopat/sfizioso.git"
SFIZIOSO_COMMIT = "a87b25e41868b9fce61199109de6f21e87c837e3"
# Devono coincidere con core.sfz_engine (dove SoundText cerca la libreria)
LIB_FILE = {"windows": "sfizz.dll", "macos": "libsfizz.dylib"}.get(SISTEMA, "libsfizz.so")
# La stessa libreria gia' compilata, dalla release libsfizz-<commit corto> di
# SoundText (.github/workflows/libsfizz.yml): (sistema, architettura) ->
# (file, SHA-256). Uno SHA-256 vuoto vuol dire che il file per quel commit
# non c'e' ancora: si compila come prima. Quando cambia SFIZIOSO_COMMIT si
# rilancia il workflow e si copiano qui le righe del suo SHA256SUMS.
LIBSFIZZ_BASE = ("https://github.com/openssound/soundtext/releases/download/"
                 f"libsfizz-{SFIZIOSO_COMMIT[:7]}/")
_LIBSFIZZ_MAC = ("libsfizz-macos-universal.dylib", "fb3623424efa0f7d31549ca2e6083b0142043cd998793ce243d994a2c022d447")
LIBSFIZZ_FILES = {
    ("linux", "x86_64"): ("libsfizz-linux-x86_64.so", "5c06b5f227334bd713cec05ecfbe32c20d0dd0164885b9a463dbb7a61667e0f6"),
    ("windows", "x86_64"): ("sfizz-windows-x64.dll", "cfaadd77938ee5194e8f08da385e9958785cf0d391b55865feaf461a25e39430"),
    ("macos", "arm64"): _LIBSFIZZ_MAC,
    ("macos", "x86_64"): _LIBSFIZZ_MAC,
}


def user_lib_dir() -> Path:
    if SISTEMA == "windows":
        return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "SoundText" / "lib"
    if SISTEMA == "macos":
        return Path.home() / "Library" / "Application Support" / "SoundText" / "lib"
    return Path.home() / ".local" / "lib" / "soundtext"


# Cartella LV2 dell'utente, dove lilv cerca da se' (vedi core.lv2_host)
def user_lv2_dir() -> Path:
    if SISTEMA == "windows":
        return Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming") / "LV2"
    if SISTEMA == "macos":
        return Path.home() / "Library" / "Audio" / "Plug-Ins" / "LV2"
    return Path.home() / ".lv2"


# Plugin LV2 Neural Amp Modeler (motore NAM in C++, GPL-3.0): con lui SoundText
# calcola i profili NAM 4-6 volte piu' in fretta (vedi core.nam_plugin).
# Versione fissa, file verificati con lo SHA-256.
NAM_PLUGIN_VERSION = "v0.2.3"
NAM_PLUGIN_BASE = f"https://github.com/mikeoliphant/neural-amp-modeler-lv2/releases/download/{NAM_PLUGIN_VERSION}/"
NAM_PLUGIN_FILES = {
    "linux": ("neural_amp_modeler_lv2_linux_x64.tgz",
              "b866d44f535b770f423f99d1083c03ddbafb07e63ed639d11e7f10c7dffb2f5e"),
    "windows": ("neural_amp_modeler_lv2_win_x64.zip",
                "d64aec201ae0285e0adb9f1ac22e720d62a15c9947b9506e61dd7c6f8e9ad0ef"),
}
NAM_PLUGIN_DIR = "neural_amp_modeler.lv2"


# Sorgenti della voce "host" (modificabili da SoundText: Opzioni -> Sorgenti
# dei download, vedi core.downloads.apply_source_overrides)
SURGE_NIGHTLY_REPO = "surge-synthesizer/surge"          # Linux: il .deb Nightly
SURGE_REPO = "surge-synthesizer/releases-xt"            # Windows e macOS
SFIZZ_DEB_BASE = "https://download.opensuse.org/repositories/home:/sfztools:/sfizz/xUbuntu_24.04/amd64"
SFIZZ_UI_REPO = "sfztools/sfizz-ui"                     # installer di sfizz per Windows e macOS


# Cartella VST3 dell'utente (non servono i diritti di amministratore)
def user_vst3_dir() -> Path:
    if SISTEMA == "windows":
        return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "Programs" / "Common" / "VST3"
    if SISTEMA == "macos":
        return Path.home() / "Library" / "Audio" / "Plug-Ins" / "VST3"
    return Path.home() / ".vst3"


# Cartella CLAP dell'utente, fra quelle in cui SoundText li cerca (vedi
# core.clap_host.default_clap_dirs)
def user_clap_dir() -> Path:
    if SISTEMA == "windows":
        return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "Programs" / "Common" / "CLAP"
    if SISTEMA == "macos":
        return Path.home() / "Library" / "Audio" / "Plug-Ins" / "CLAP"
    return Path.home() / ".clap"


# gruppo, descrizione, URL, cartella di destinazione
GRUPPI = [
    ("piano", "Piano a coda Salamander (SFZ+FLAC, ~740 MB)", f"{FREEPATS}/Piano/SalamanderGrandPiano/SalamanderGrandPiano-SFZ+FLAC-V3+20200602.tar.gz", "sfz"),
    ("upright", "Piano verticale piccolo (SFZ+FLAC, ~3 MB)", f"{FREEPATS}/Piano/UprightPianoKW/UprightPianoKW-small-SFZ+FLAC-20190703.7z", "sfz"),
    ("epiano", "Piano elettrico FM (SFZ+FLAC, ~25 MB)", "https://github.com/freepats/fm-piano1/releases/download/2019-09-16/FM-Piano1-SFZ+FLAC-20190916.7z", "sfz"),
    ("chitarra", "Chitarra classica spagnola (SFZ+FLAC, ~5 MB)", f"{FREEPATS}/Guitar/SpanishClassicalGuitar/SpanishClassicalGuitar-SFZ+FLAC-20190618.7z", "sfz"),
    ("chitarra-elettrica", "Chitarra elettrica pulita FreePats (SFZ+FLAC, ~125 MB)", "https://github.com/freepats/electric-guitar-FSBS-clean/releases/download/2026-08-07/EGuitarFSBS-clean-SFZ+FLAC-20260807.7z", "sfz"),
    ("chitarra-dist", "Chitarra elettrica distorta FreePats (SFZ+FLAC, ~315 MB)", "https://github.com/freepats/electric-guitar-FSBS-dist1/releases/download/2022-09-11/EGuitarFSBS-dist1-SFZ+FLAC-20220911.7z", "sfz"),
    ("emilyguitar", "Chitarra acustica Emilyguitar Karoryfer (corde d'acciaio, CC0, ~105 MB)", "https://github.com/sfzinstruments/karoryfer.emilyguitar/releases/download/v1.001/Karoryfer.Emilyguitar.v1.001.zip", "sfz"),
    ("contrabbasso", "Contrabbasso D. Smolken (CC0, arco e pizzicato, ~265 MB)", "https://github.com/sfzinstruments/dsmolken.double-bass/releases/download/v1.001/DSmolken.double_bass.v1.001.zip", "sfz"),
    ("pastabass", "Pastabass Karoryfer (basso, CC0, ~315 MB)", "https://github.com/sfzinstruments/karoryfer.pastabass/releases/download/v1.101/Karoryfer.Pastabass.v1.101.zip", "sfz"),
    ("basso", "Basso elettrico dita (SFZ+FLAC, ~3 MB)", "https://github.com/freepats/electric-bass-YR/releases/download/2019-09-30/FingerBassYR-SFZ+FLAC-20190930.7z", "sfz"),
    ("basso-plettro", "Basso elettrico plettro (SFZ+FLAC, ~3 MB)", "https://github.com/freepats/electric-bass-YR/releases/download/2019-09-30/PickedBassYR-SFZ+FLAC-20190930.7z", "sfz"),
    ("organo", "Organo a canne da chiesa (SFZ, ~13 MB)", f"{FREEPATS}/Organ/ChurchOrganEmulation/ChurchOrganEmulation-SFZ-20190924.tar.xz", "sfz"),
    ("arpa", "Arpa da concerto (SFZ+FLAC, ~5 MB)", f"{FREEPATS}/OrchestralStrings/ConcertHarp/ConcertHarp-SFZ+FLAC-20200702.tar.gz", "sfz"),
    ("sax", "Sax tenore (SFZ+FLAC, ~32 MB)", f"{FREEPATS}/Reed/TenorSaxophone/TenorSaxophone-SFZ+FLAC-20200717.tar.gz", "sfz"),
    ("batteria", "Batteria MuldjordKit in SFZ (per sfizz; crea anche la versione GM, ~165 MB)", "https://github.com/freepats/muldjordkit/releases/download/2020-10-18/MuldjordKit-SFZ+FLAC-20201018.7z", "sfz"),
    ("salamander-drums", "Batteria Salamander Drumkit (SFZ, ~485 MB, note GM)", "https://archive.org/download/SalamanderDrumkit/salamanderDrumkit.tar.bz2", "sfz"),
    ("drskit-sfz", "Batteria DRSKit in SFZ per sfizz (~1,5 GB, note GM; file: DrumGizmo/DRSKit/Stereo/)", "https://github.com/sfzinstruments/DrumGizmo.DRSKit.git", "sfz"),
    # Il banco upstream e' incompiuto: gli altri .sfz sono segnaposto "//dummy" con sample=*sine
    ("gm-bank", "Discord SFZ GM Bank, INCOMPLETO (~245 MB): campionati solo i GM 1-3 e 5 (pianoforti), "
                "26 chitarra acustica, 34 basso, 45-46 archi tremolo e pizzicato, 105 sitar, 112 shanai "
                "e il kit Standard; gli altri strumenti sono segnaposto a onda sinusoidale",
     "https://github.com/sfzinstruments/Discord-SFZ-GM-Bank.git", "sfz"),
    ("splendid-piano", "Piano a coda Splendid Grand Piano (Steinway, ~70 MB)", "https://github.com/sfzinstruments/SplendidGrandPiano.git", "sfz"),
    ("rhodes", "Piano Rhodes Mark I Stage 73, jRhodes3d (~165 MB)", "https://github.com/sfzinstruments/jlearman.jRhodes3d.git", "sfz"),
    ("epiano-vintage", "Piani elettrici Yamaha CP80, Hohner Pianet e Wurlitzer EP200 (~20 MB)", "https://github.com/sfzinstruments/GregSullivan.E-Pianos.git", "sfz"),
    ("cello", "Violoncello Karoryfer Bigcat (CC0, ~125 MB)", "https://github.com/sfzinstruments/karoryfer-bigcat.cello/releases/download/v1.001/Karoryfer_Bigcat_cello.v1.001.zip", "sfz"),
    ("string-cyborgs", "Archi String Cyborgs Karoryfer (~60 MB)", "https://github.com/sfzinstruments/karoryfer.string-cyborgs/releases/download/v1.001/Karoryfer.String_Cyborgs.v1.001.zip", "sfz"),
    ("meatbass", "Meatbass Karoryfer (basso elettrico, CC0, ~245 MB)", "https://github.com/sfzinstruments/karoryfer.meatbass/releases/download/v1.001/Karoryfer.Meatbass.v1.001.zip", "sfz"),
    ("weresax", "Weresax Karoryfer (sax, CC0, ~190 MB)", "https://github.com/sfzinstruments/karoryfer.weresax/releases/download/v1.003/Karoryfer.Weresax.v.1.003.zip", "sfz"),
    ("solosax", "Sax soprano, contralto, tenore e baritono MTG (~100 MB)", "https://github.com/sfzinstruments/MTG.SoloSax.git", "sfz"),
    ("steeldrum", "Steel drum cromatico, jlearman (~40 MB)", "https://github.com/sfzinstruments/jlearman.SteelDrum.git", "sfz"),
    ("marimba", "Marimba Terkelsen (~25 MB)", "https://github.com/sfzinstruments/Terkelsen.Marimba.git", "sfz"),
]
# Extra: non fanno parte di "tutto"; si scaricano a gruppi (extra_*) o per nome
EXTRA = [
    ("fashionbass", "Fashionbass Karoryfer (basso elettrico, ~300 MB)", "https://github.com/sfzinstruments/karoryfer.fashionbass/releases/download/v1.001/Karoryfer.Fashionbass.v1.001.zip", "sfz"),
    ("growlybass", "Growlybass Karoryfer (basso elettrico, ~160 MB)", "https://github.com/sfzinstruments/karoryfer.growlybass/releases/download/v1.002/Karoryfer.Growlybass.v1.002.zip", "sfz"),
    ("swagbass", "Swagbass Karoryfer (basso elettrico, ~140 MB)", "https://github.com/sfzinstruments/karoryfer.swagbass/releases/download/v1.001/Karoryfer.Swagbass.v1.001.zip", "sfz"),
    ("sneakybass", "Sneakybass Karoryfer (contrabbasso pizzicato, ~325 MB)", "https://github.com/sfzinstruments/karoryfer.sneakybass/releases/download/v1.000/Sneakybass_v1.000.zip", "sfz"),
    ("big-little-bass", "Big Little Bass Karoryfer (basso elettrico, ~250 MB)", "https://github.com/sfzinstruments/karoryfer.big-little-bass/releases/download/v1.000/Big_Little_Bass_1000.zip", "sfz"),
    ("ergo", "Ergo Karoryfer (contrabbasso elettrico, ~190 MB)", "https://github.com/sfzinstruments/karoryfer.ergo/releases/download/v1.001/Karoryfer.Ergo_EUB.v1.001.zip", "sfz"),
    ("black-blue-bassi", "Black And Blue Basses Karoryfer (raccolta di bassi, ~960 MB)", "https://github.com/sfzinstruments/karoryfer.black-and-blue-basses/releases/download/v1.002/Black_And_Blue_Basses_1002.zip", "sfz"),
    ("black-green-chitarre", "Black And Green Guitars Karoryfer (due chitarre elettriche pulite, da amplificare, ~480 MB)", "https://github.com/sfzinstruments/karoryfer.black-and-green-guitars/releases/download/v1.000/Karoryfer_Black_And_Green_Guitars_1000.zip", "sfz"),
    ("shinyguitar", "Shinyguitar Karoryfer (chitarra archtop da jazz, ~370 MB)", "https://github.com/sfzinstruments/karoryfer.shinyguitar/releases/download/v1.002/Karoryfer.Shinyguitar.v1.002.zip", "sfz"),
    ("scarypiano", "Scarypiano Karoryfer (piano, ~340 MB)", "https://github.com/sfzinstruments/karoryfer.scarypiano/releases/download/v1.002/Karoryfer.Scarypiano.v1.002.zip", "sfz"),
    ("osiris-piano", "Osiris Piano (~435 MB)", "https://github.com/sfzinstruments/Osiris_Piano/releases/download/v0.925/Osiris_Piano_0925.zip", "sfz"),
    ("erhu", "Erhu cinese (~75 MB)", "https://github.com/sfzinstruments/aliexpress-erhu/releases/download/v1.000/aliexpress-erhu_v1000.zip", "sfz"),
    ("cithara", "Cithara barbarica, lira medievale a 10 corde (~170 MB)", "https://github.com/sfzinstruments/cithara-barbarica/releases/download/v1.000/cithara-barbarica_v1000.zip", "sfz"),
    ("banjo", "Banjo a 5 corde Flame Studios (~245 MB)", "https://github.com/sfzinstruments/FlameStudios.Kay5StringBanjo.git", "sfz"),
    ("squidpipes", "Squidpipes Karoryfer (~40 MB)", "https://github.com/sfzinstruments/karoryfer.squidpipes/releases/download/v1.001/karoryfer.squidpipes-v1.001.zip", "sfz"),
    ("zither", "Cetra ungherese prime zither (~170 MB)", "https://github.com/sfzinstruments/hungarian_zither/releases/download/v1.001/hungarian_prime_zither_1001.zip", "sfz"),
    ("ganjo", "Ganjo, chitarra-banjo (~25 MB)", "https://github.com/sfzinstruments/ganjo/releases/download/v1.000/ganjo-v1.000.zip", "sfz"),
    ("horsepulse", "Horse Pulse Karoryfer (tagelharpa, ~140 MB)", "https://github.com/sfzinstruments/Karoryfer.HorsePulse/releases/download/v1.000/Karoryfer_Horse_Pulse_1000.zip", "sfz"),
    ("war-tuba", "War Tuba Karoryfer (~105 MB)", "https://github.com/sfzinstruments/karoryfer.war-tuba/releases/download/v1.002/Karoryfer_War_Tuba_v1002.zip", "sfz"),
    ("bear-sax", "Bear Sax Karoryfer (~125 MB)", "https://github.com/sfzinstruments/karoryfer.bear-sax/releases/download/v1.004/Karoryfer.Bear_Sax.v1.004.zip", "sfz"),
    ("virtuosity-drums", "Batteria Virtuosity Drums (~1,2 GB)", "https://github.com/sfzinstruments/virtuosity_drums/releases/download/v0.925/Virtuosity_Drums_v0.925.zip", "sfz"),
    ("unruly-drums", "Batteria Unruly Drums Karoryfer (~645 MB)", "https://github.com/sfzinstruments/karoryfer.unruly-drums/releases/download/v1.100/Unruly_Drums_1100.zip", "sfz"),
    ("swirly-drums", "Batteria Swirly Drums Karoryfer (~830 MB)", "https://github.com/sfzinstruments/karoryfer.swirly-drums/releases/download/v1.104/Swirly.Drums_1104.zip", "sfz"),
    ("big-rusty-drums", "Batteria Big Rusty Drums Karoryfer (~590 MB)", "https://github.com/sfzinstruments/karoryfer.big-rusty-drums/releases/download/v1.100/Big_Rusty_Drums_1100.zip", "sfz"),
    ("naked-drums", "Batteria Naked Drums Wilkinson Audio (multimicrofono, ~1,2 GB)", "https://github.com/sfzinstruments/WilkinsonAudio.NakedDrums.git", "sfz"),
    ("sonor-drums", "Batteria Sonor Force 3001 di Sam Greene (~35 MB)", "https://github.com/sfzinstruments/SamsSonor.git", "sfz"),
    ("hat-phat", "Charleston gigante The Hat With The Phat Karoryfer (~635 MB)", "https://github.com/sfzinstruments/Karoryfer.TheHatWithThePhat/releases/download/v1.001/The.Hat.With.The.Phat.bank.zip", "sfz"),
    ("frankensnare", "Raccolta di rullanti Frankensnare Karoryfer (~350 MB)", "https://github.com/sfzinstruments/karoryfer.frankensnare/releases/download/v2.100/Frankensnare_2100.zip", "sfz"),
]
# Gruppi di extra: nome, spazio totale, strumenti
EXTRA_GRUPPI = [
    ("extra_basso", "~2,3 GB", "fashionbass growlybass swagbass sneakybass big-little-bass ergo black-blue-bassi"),
    ("extra_piano", "~780 MB", "scarypiano osiris-piano"),
    ("extra_chitarre", "~850 MB", "black-green-chitarre shinyguitar"),
    ("extra_etnici", "~1,1 GB", "erhu cithara banjo squidpipes zither ganjo horsepulse war-tuba bear-sax"),
    ("extra_batterie", "~5,5 GB", "virtuosity-drums unruly-drums swirly-drums big-rusty-drums naked-drums sonor-drums hat-phat frankensnare"),
]

# Orchestra: VSCO 2 CE (archi, legni, ottoni, percussioni) e VCSL (vibrafono,
# clavicembali, percussioni), di Versilian Studios, CC0. Non hanno un
# archivio per strumento: si scaricano, uno per uno e senza git, i file .sfz
# del gruppo e i campioni che citano (vedi scarica_orchestra), da un commit
# fisso dei loro repository GitHub. Fuori da "tutto", come gli extra. I file
# con i keyswitch (-KS) no: cambiano articolazione con note basse che la
# notazione non manda.
VSCO_BASE = "https://raw.githubusercontent.com/sgossner/VSCO-2-CE/6dd651d55dde97fd4028699be9d4481f26917891/"
VCSL_BASE = "https://raw.githubusercontent.com/sgossner/VCSL/dfcf4a4918771eee884b96ad4493de82ef84daf6/"
ORCHESTRA = [
    ("vsco-archi", "Archi VSCO 2 CE: violini, viole, violoncelli, contrabbassi e violino solo (CC0, ~670 MB)",
     VSCO_BASE, "sfz"),
    ("vsco-legni", "Legni VSCO 2 CE: flauto, ottavino, oboe, clarinetto, fagotto (CC0, ~300 MB)", VSCO_BASE, "sfz"),
    ("vsco-ottoni", "Ottoni VSCO 2 CE: tromba, corno, trombone, tuba (CC0, ~330 MB)", VSCO_BASE, "sfz"),
    ("vsco-percussioni", "Percussioni VSCO 2 CE: timpani, glockenspiel, xilofono, marimba, campane, arpa "
                         "(CC0, ~150 MB)", VSCO_BASE, "sfz"),
    ("vcsl-vibrafono", "Vibrafono VCSL: battenti duri, morbidi e con l'archetto (CC0, ~100 MB)", VCSL_BASE, "sfz"),
    ("vcsl-clavicembalo", "Clavicembali VCSL: fiammingo, francese, italiano, inglese (CC0, ~390 MB)",
     VCSL_BASE, "sfz"),
    ("vcsl-percussioni", "Percussioni VCSL: cajon, conga, bongo, rullanti, piatti, gong, triangoli, "
                         "tamburelli (CC0, ~340 MB)", VCSL_BASE, "sfz"),
]
_VCSL_IDIOFONI = "Idiophones/Struck Idiophones/"
_VCSL_MEMBRANOFONI = "Membranophones/Struck Membranophones/"
# I file .sfz di ogni gruppo, come percorsi nel repository
ORCHESTRA_SFZ = {
    "vsco-archi": [f"{n}.sfz" for n in (
        "ViolinEnsSusVib ViolinEnsPizz ViolinEnsSpic ViolinEnsTrem ViolaEnsSusVib ViolaEnsPizz ViolaEnsSpic "
        "ViolaEnsTrem CelloEnsSusVib CelloEnsPizz CelloEnsSpic CelloEnsTrem ContrabassSusVB ContrabassPizz "
        "ContrabassSpic ContrabassTrem SViolinVib SViolinPizz SViolinSpic SViolinTrem").split()],
    "vsco-legni": [f"{n}.sfz" for n in (
        "FluteSusVib FluteSusNV FluteStac PiccoloSus PiccoloStac OboeSusVib OboeSusNV OboeStac ClarinetSus "
        "ClarinetStac BassoonSus BassoonVib BassoonStac").split()],
    "vsco-ottoni": [f"{n}.sfz" for n in (
        "TrumpetSus TrumpetSusVib TrumpetStac TrumpetStraightMuteSus TrumpetHarmonMuteSus FHornSus FHornStac "
        "FHornMute TromboneSus TromboneVib TromboneStac TubaSus TubaStac").split()],
    "vsco-percussioni": [f"{n}.sfz" for n in
                         "Timpani TimpaniRolls Glockenspiel Xylophone Marimba TubularBells Harp".split()],
    "vcsl-vibrafono": [f"{_VCSL_IDIOFONI}Vibraphone - {n}.sfz" for n in ("Hard Mallets", "Soft Mallets", "Bowed")],
    "vcsl-clavicembalo": [f"Chordophones/Zithers/Harpsichord, {n}.sfz" for n in (
        "English - Normal", "English - Lute", "Flemish - 8'", "Flemish - 4'", "Flemish - Full", "French",
        "Italian")],
    "vcsl-percussioni": [f"{_VCSL_IDIOFONI}{n}.sfz" for n in (
        "Cajon", "Clash Cymbals 1", "Clash Cymbals 2", "Claves", "Cowbells", "Agogo Bells", "Finger Cymbals",
        "Gong 1", "Gong 2", "Sleigh Bells", "Suspended Cymbal 1", "Suspended Cymbal 2", "Tambourine 1",
        "Tambourine 2", "Triangles", "Vibraslap")]
    + [f"{_VCSL_MEMBRANOFONI}{n}.sfz" for n in (
        "Bongos", "Conga", "Bass Drum 1", "Bass Drum 2", "Snare Drum, Modern 1", "Snare Drum, Modern 2",
        "Snare Drum, Modern 3", "Snare Drum, Rope Tension")],
}
# Guadagno aggiunto ai .sfz di VSCO 2 CE, in dB: suonano circa 8 dB sotto i
# suoni General MIDI. global_volume si somma ai volume= delle regioni.
VSCO_GUADAGNO_DB = 8
# Correzioni ai .sfz di VSCO 2 CE: file -> [(campioni delle regioni,
# opcode, valore di VSCO, valore corretto)], misurate nota per nota col
# motore SFZ. Timpani: il timpano piu' grave (c*2-g*2) usava il campione
# pianissimo fino a dinamica 80 (gli altri fino a 60) e a 70 suonava circa
# 27 dB sotto il timpano accanto: ora passa al campione forte da 61. I
# campioni piani del grave e dell'acuto (f*3-c*4) suonavano 10-19 dB sotto
# quello forte (le due alternanze del grave 8 dB diverse fra loro): il loro
# volume li porta circa 2 dB sotto, perche' crescendo la dinamica il suono
# non salti.
VSCO_CORREZIONI = {
    "Timpani.sfz": [("Timpani1_Hit_v1_", "hivel", "80", "60"), ("Timpani1_Hit_v3_", "lovel", "81", "61"),
                    ("Timpani1_Hit_v1_rr1_", "volume", "27", "44"), ("Timpani1_Hit_v1_rr2_", "volume", "27", "36"),
                    ("Timpani5_Hit_v1_", "volume", "23", "40")],
}


class Errore(Exception):
    pass


def tr(testo: str, *args) -> str:
    """Il messaggio nella lingua di SoundText (core.i18n del programma, che
    sta accanto allo script); in italiano se core.i18n non c'e'."""
    try:
        from core.i18n import tr as traduci
    except ImportError:
        return testo.format(*args) if args else testo
    return traduci(testo, *args)


def tr_descrizione(desc: str) -> str:
    """Una descrizione di GRUPPI o EXTRA tradotta a pezzi, come la mostra la
    finestra: "Piano a coda Salamander (SFZ+FLAC, ~740 MB)"."""
    if desc.endswith(")") and " (" in desc:
        testa, _sep, coda = desc.rpartition(" (")
        return f"{tr(testa)} ({tr(coda[:-1])})"
    return tr(desc)


def in_flatpak() -> bool:
    """SoundText gira dentro un Flatpak: niente apt ne' pip, e gli archivi
    .7z li estrae il pacchetto py7zr incluso nel Flatpak."""
    return os.path.exists("/.flatpak-info")


def comando_script() -> str:
    if SISTEMA == "windows":
        return "py scarica_strumenti.py"
    if SISTEMA == "linux":
        return "./scarica_strumenti.sh"
    return "python3 scarica_strumenti.py"


def voci_elenco() -> list:
    """(nome, descrizione) di tutto cio' che si puo' scaricare, nell'ordine
    dell'elenco: lo stesso ordine numera le voci del menu interattivo."""
    host = {"linux": tr("7zip + sfizz + Surge XT Nightly (apt, chiede la password) + i plugin VST3 della voce vst3"),
            "windows": tr("7-Zip (winget), Surge XT con i suoi dati (~300 MB) per l'utente, installer di sfizz, "
                          "i plugin VST3 della voce vst3"),
            "macos": tr("7-Zip (Homebrew), Surge XT con i suoi dati (~440 MB) per l'utente, installer di sfizz, "
                        "i plugin VST3 della voce vst3")}[SISTEMA]
    vst3 = ", ".join(nome for nome, _desc, _repo, _rel, modelli in PLUGIN_VST3 if chiave_sistema() in modelli)
    return ([(nome, tr_descrizione(desc)) for nome, desc, _url, _sotto in GRUPPI + EXTRA + ORCHESTRA]
            + [(nome, f"(extra, {spazio}) {membri}") for nome, spazio, membri in EXTRA_GRUPPI]
            + [("vst3", tr("plugin VST3 gratuiti nella cartella VST3 dell'utente: {}", vst3)),
               ("clap", tr("plugin CLAP gratuiti che non esistono in VST3, nella cartella CLAP dell'utente: {}",
                           ", ".join(nome for nome, *_r in PLUGIN_CLAP))),
               ("clap-con-vst3", tr("i plugin CLAP che stanno negli archivi dei plugin VST3 gratuiti, "
                                    "nella cartella CLAP dell'utente: {}", vst3)),
               ("host", host),
               ("lv2", tr("solo Linux: plugin LV2 gratuiti nella cartella LV2 dell'utente: {}",
                          ", ".join(nome for nome, *_r in PLUGIN_LV2))),
               ("lilv", tr("solo Linux: la libreria lilv per usare i plugin LV2 (apt, chiede la password)")),
               ("libreria", tr("motore SFZ sfizioso per lo strumento SFZ interno (gia' compilato, pochi MB)")
                if libreria_precompilata() else
                tr("motore SFZ sfizioso per lo strumento SFZ interno (compilato, ~5 min)")),
               ("strumenti-compilazione", tr("git, cmake e il compilatore che servono a 'libreria'")),
               ("nam-plugin", tr("plugin LV2 Neural Amp Modeler {}: profili NAM 4-6 volte piu' "
                                 "veloci (Linux e Windows x64, ~2 MB)", NAM_PLUGIN_VERSION)),
               ("tutto", tr("tutti i gruppi SFZ (esclusi gli extra_*)"))])


def elenco():
    print(tr("Gruppi disponibili (destinazione: {}):", DEST))
    for nome, desc in voci_elenco():
        print(f"  {nome:<14} {desc}")


def menu() -> list:
    """Menu interattivo (lanciato senza argomenti da un terminale, es. dal
    menu Start di Windows): elenco numerato, si scelgono le voci per numero
    o per nome. Ritorna gli argomenti da eseguire, [] per uscire."""
    voci = voci_elenco()
    print(tr("Strumenti e plugin gratuiti per SoundText (destinazione: {})", DEST))
    print(tr("Prima volta: scegli 'host' (7-Zip, sfizz, Surge XT) e 'libreria'.") + "\n")
    for i, (nome, desc) in enumerate(voci, 1):
        print(f"  {i:>3}. {nome:<18} {desc}")
    nomi = [nome for nome, _desc in voci]
    while True:
        try:
            risposta = input("\n" + tr("Numeri o nomi separati da spazi (Invio per uscire): "))
        except (EOFError, KeyboardInterrupt):
            print()
            return []
        scelte = []
        for parola in risposta.replace(",", " ").split():
            if parola.isdigit() and 1 <= int(parola) <= len(voci):
                scelte.append(nomi[int(parola) - 1])
            elif parola in nomi:
                scelte.append(parola)
            else:
                print(tr("Scelta non valida: {}", parola))
                break
        else:
            return scelte


def trova(nome: str):
    for voce in GRUPPI + EXTRA + ORCHESTRA:
        if voce[0] == nome:
            return voce
    return None


def trova_extra(nome: str):
    for gruppo, _spazio, membri in EXTRA_GRUPPI:
        if gruppo == nome:
            return membri.split()
    return None


# ---------------------------------------------------------------------------
# Download ed estrazione
# ---------------------------------------------------------------------------

USER_AGENT = "SoundText-scarica-strumenti"


def _richiesta(url: str, **headers):
    return urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **headers})


def scarica_file(url: str, dest: Path, tentativi: int = 3, silenzioso: bool = False):
    """Scarica url in dest riprendendo un download interrotto. 'silenzioso':
    senza l'avanzamento (i tanti file piccoli dell'orchestra), errori a parte.
    Se l'URL porta uno SHA-256 atteso (UrlVerificato), a download finito il file si controlla: se e' diverso si
    cancella e non si installa."""
    _scarica_file(url, dest, tentativi, silenzioso)
    atteso = getattr(url, "sha256", "")
    if atteso:
        digest = _sha256_file(Path(dest))
        if digest != atteso:
            Path(dest).unlink(missing_ok=True)
            raise Errore(tr("il file scaricato non e' quello atteso (SHA-256 {}...): non lo installo", digest[:12]))


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blocco in iter(lambda: f.read(1 << 20), b""):
            h.update(blocco)
    return h.hexdigest()


def _scarica_file(url: str, dest: Path, tentativi: int = 3, silenzioso: bool = False):
    dest.parent.mkdir(parents=True, exist_ok=True)
    for tentativo in range(1, tentativi + 1):
        gia = dest.stat().st_size if dest.exists() else 0
        req = _richiesta(url, **({"Range": f"bytes={gia}-"} if gia else {}))
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                riprende = gia and resp.status == 206
                totale = int(resp.headers.get("Content-Length") or 0) + (gia if riprende else 0)
                fatto = gia if riprende else 0
                ultimo = 0.0
                with open(dest, "ab" if riprende else "wb") as f:
                    while True:
                        blocco = resp.read(1 << 20)
                        if not blocco:
                            break
                        f.write(blocco)
                        fatto += len(blocco)
                        if not silenzioso and time.monotonic() - ultimo > 1:
                            ultimo = time.monotonic()
                            perc = f" {fatto * 100 // totale}%" if totale else ""
                            print(f"\r   {fatto / 1e6:.0f} MB{perc}   ", end="", flush=True)
                if not silenzioso:
                    print("\r   " + tr("{:.0f} MB scaricati", fatto / 1e6) + "      ")
                return
        except urllib.error.HTTPError as e:
            if e.code == 416 and gia:          # gia' completo
                return
            errore = e
        except (urllib.error.URLError, OSError) as e:
            errore = e
        print("\n   " + tr("errore ({}), tentativo {} di {}", errore, tentativo, tentativi))
        time.sleep(2 * tentativo)
    raise Errore(tr("download non riuscito: {}", url))


def _dentro(base: Path, nome: str) -> bool:
    try:
        (base / nome).resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def _link_dentro(base: Path, nome: str, destinazione: str) -> bool:
    """Un link simbolico (o fisso) dell'archivio che punta dentro la cartella di destinazione."""
    if not destinazione or destinazione.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", destinazione):
        return False
    return _dentro(base, os.path.normpath(os.path.join(os.path.dirname(nome), destinazione)))


def _controlla_percorsi(base: Path, voci, file: Path):
    """Rifiuta l'archivio se un percorso esce dalla cartella o un link punta fuori: voci = [(nome, destinazione del link o "")]."""
    for nome, destinazione in voci:
        if not nome or not _dentro(base, nome) or Path(nome).is_absolute() or (destinazione and not _link_dentro(base, nome, destinazione)):
            raise Errore(tr("percorso non valido nell'archivio: {}", nome or file.name))


def _voci_7z(sette: str, file: Path) -> list:
    """[(percorso, destinazione del link)] dall'elenco di 7-Zip (7z l -slt)."""
    r = subprocess.run([sette, "l", "-slt", "-ba", str(file)], capture_output=True, text=True, check=True)
    voci, corrente = [], {}
    for riga in r.stdout.splitlines() + [""]:
        if riga.strip() == "":
            if "Path" in corrente:
                voci.append((corrente["Path"], corrente.get("Symbolic Link", "") or corrente.get("Hard Link", "")))
            corrente = {}
        elif " = " in riga:
            chiave, _sep, valore = riga.partition(" = ")
            corrente[chiave.strip()] = valore
    return voci


def _voci_tar(comando: list, file: Path) -> list:
    """[(percorso, destinazione del link)] dall'elenco di tar (-tvf, con i link «nome -> destinazione»)."""
    nomi = subprocess.run(comando + ["-tf", str(file)], capture_output=True, text=True, check=True).stdout.splitlines()
    voci = [(nome, "") for nome in nomi]
    lungo = subprocess.run(comando + ["-tvf", str(file)], capture_output=True, text=True, check=True).stdout.splitlines()
    for riga, (nome, _vuoto) in zip(lungo, voci):
        if riga[:1] in ("l", "h"):
            _testa, sep, destinazione = riga.partition(" -> ")
            voci[voci.index((nome, ""))] = (nome, destinazione.strip() or "?")
            if not sep and riga[:1] == "h":                       # hard link: «link to»
                voci[voci.index((nome, "?"))] = (nome, riga.rsplit(" link to ", 1)[-1].strip() or "?")
    return voci


def programma_7z():
    for nome in ("7z", "7zz", "7za"):
        if shutil.which(nome):
            return shutil.which(nome)
    if SISTEMA == "windows":
        for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
            if base and Path(base, "7-Zip", "7z.exe").exists():
                return str(Path(base, "7-Zip", "7z.exe"))
    return None


def estrai(file: Path, cartella: Path):
    nome = file.name.lower()
    cartella.mkdir(parents=True, exist_ok=True)
    if nome.endswith(".zip"):
        with zipfile.ZipFile(file) as z:
            for membro in z.namelist():
                if not _dentro(cartella, membro):
                    raise Errore(tr("percorso non valido nell'archivio: {}", membro))
            if SISTEMA == "macos" and shutil.which("ditto"):
                # ditto conserva permessi, link simbolici e firme dei bundle
                # (i plugin per macOS), che zipfile perderebbe
                subprocess.run(["ditto", "-x", "-k", str(file), str(cartella)], check=True)
            else:
                z.extractall(cartella)
            # i permessi salvati nell'archivio (eseguibili): anche dopo ditto,
            # che non sempre li ripristina; i link simbolici restano com'erano
            for info in z.infolist():
                attributi = info.external_attr >> 16
                modo = attributi & 0o777
                destinazione = cartella / info.filename
                if (modo and not info.is_dir() and not stat.S_ISLNK(attributi)
                        and not destinazione.is_symlink() and destinazione.is_file()):
                    os.chmod(destinazione, modo | stat.S_IRUSR)
    elif re.search(r"\.(tar\.(gz|xz|bz2)|tgz)$", nome):
        with tarfile.open(file) as t:
            if hasattr(tarfile, "data_filter"):
                t.extractall(cartella, filter="data")
            else:
                for membro in t.getmembers():
                    if not _dentro(cartella, membro.name) or membro.issym() or membro.islnk():
                        raise Errore(tr("percorso non valido nell'archivio: {}", membro.name))
                t.extractall(cartella)
    elif nome.endswith(".7z"):
        sette = programma_7z()
        if sette:
            _controlla_percorsi(cartella, _voci_7z(sette, file), file)       # prima si guarda cosa c'e' dentro
            subprocess.run([sette, "x", "-y", f"-o{cartella}", str(file)], check=True, stdout=subprocess.DEVNULL)
            return
        try:
            import py7zr
        except ImportError:
            if in_flatpak():
                raise Errore(tr("per estrarre {} manca il pacchetto py7zr, che dovrebbe far parte del Flatpak: "
                                "segnalalo su https://github.com/openssound/soundtext/issues", file.name))
            raise Errore(tr("per estrarre {} serve 7-Zip (esegui prima: {} host) "
                            "oppure il pacchetto Python py7zr (pip install py7zr)", file.name, comando_script()))
        with py7zr.SevenZipFile(file) as z:
            _controlla_percorsi(cartella, [(i.filename, "") for i in z.list()], file)
            if any(getattr(i, "is_symlink", False) or getattr(i, "is_junction", False) for i in z.list()):
                raise Errore(tr("percorso non valido nell'archivio: {}", file.name))
        with py7zr.SevenZipFile(file) as z:
            z.extractall(cartella)
    elif nome.endswith(".deb"):
        estrai_deb(file, cartella)
    else:
        raise Errore(tr("formato sconosciuto: {}", file.name))


def estrai_deb(file: Path, cartella: Path):
    """I file di un pacchetto .deb, senza installarlo (niente password di
    amministratore): un .deb e' un archivio "ar" che contiene data.tar.*
    con i file. Serve per i plugin pubblicati su Linux solo cosi'."""
    with open(file, "rb") as f:
        if f.read(8) != b"!<arch>\n":
            raise Errore(tr("formato sconosciuto: {}", file.name))
        while True:
            intestazione = f.read(60)
            if len(intestazione) < 60:
                break
            membro = intestazione[:16].decode("ascii", "replace").strip().rstrip("/")
            dimensione = int(intestazione[48:58].decode("ascii").strip())
            if re.fullmatch(r"data\.tar(\.(gz|xz|bz2|zst))?", membro):
                with tempfile.TemporaryDirectory() as tmp:
                    dati = Path(tmp) / membro
                    dati.write_bytes(f.read(dimensione))
                    if membro.endswith(".zst"):
                        # zstd non e' nella libreria di Python (prima della 3.14): lo apre il tar del sistema
                        cartella.mkdir(parents=True, exist_ok=True)
                        try:
                            _controlla_percorsi(cartella, _voci_tar(["tar", "--zstd"], dati), file)
                            subprocess.run(["tar", "--zstd", "-xf", str(dati), "-C", str(cartella)], check=True,
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        except Errore:
                            raise
                        except (OSError, subprocess.CalledProcessError):
                            raise Errore(tr("per aprire {} servono tar e zstd (sudo apt-get install -y zstd)",
                                            file.name))
                        return
                    with tarfile.open(dati) as t:
                        if hasattr(tarfile, "data_filter"):
                            t.extractall(cartella, filter="data")
                        else:
                            for m in t.getmembers():
                                if not _dentro(cartella, m.name) or m.issym() or m.islnk():
                                    raise Errore(tr("percorso non valido nell'archivio: {}", m.name))
                            t.extractall(cartella)
                return
            f.seek(dimensione + dimensione % 2, 1)
    raise Errore(tr("formato sconosciuto: {}", file.name))


# Gli strumenti che si scaricano con git (o con l'archivio .zip di GitHub) a un commit fisso, non al ramo principale:
# se il repository venisse modificato dopo, SoundText scarica quello che ha provato. Le righe le scrive
# tools/aggiorna_pin_plugin.py (git ls-remote, senza scaricare niente).
# --- PIN_GIT_INIZIO (scritto da tools/aggiorna_pin_plugin.py) ---
PIN_GIT = {
    "https://github.com/sfzinstruments/Discord-SFZ-GM-Bank.git": "7a9c478fe331f94f246d33332f0adedb25bbbe27",
    "https://github.com/sfzinstruments/DrumGizmo.DRSKit.git": "b01448990a31f722542f1812e56159a97a6a2a82",
    "https://github.com/sfzinstruments/FlameStudios.Kay5StringBanjo.git": "a773f1625db53a8a4d1bc10098d867561e21fd09",
    "https://github.com/sfzinstruments/GregSullivan.E-Pianos.git": "8c3e581acda3594b553948ff0222d4f84a698376",
    "https://github.com/sfzinstruments/MTG.SoloSax.git": "b494d256549b3d088fdec176ce82867f8a1f58b2",
    "https://github.com/sfzinstruments/SamsSonor.git": "ef3e32058924ed1c3335e86d03094d3f310a9104",
    "https://github.com/sfzinstruments/SplendidGrandPiano.git": "1c595d827b7fd7f0be3134aaed0f90b3662a09cf",
    "https://github.com/sfzinstruments/Terkelsen.Marimba.git": "473e8dc5df1d8cafe3cde8d934e5be40f72e1d1e",
    "https://github.com/sfzinstruments/WilkinsonAudio.NakedDrums.git": "407732a548606ac715ad8f3fbac63d9f4df77c0d",
    "https://github.com/sfzinstruments/jlearman.SteelDrum.git": "dc15a36ad69a43b0d240fcbd0cc78fbc61b2b47e",
    "https://github.com/sfzinstruments/jlearman.jRhodes3d.git": "aea5b8d3e11e2f7102593789a4e0a0e41b30271a",
}
# --- PIN_GIT_FINE ---


def archivio_github(url_git: str) -> str:
    """https://github.com/a/b.git -> l'archivio .zip del commit fissato (PIN_GIT) o del ramo principale."""
    return re.sub(r"\.git$", "", url_git) + f"/archive/{PIN_GIT.get(url_git, 'HEAD')}.zip"


def clona_fissato(url: str, cartella: Path):
    """git clone --depth 1 del commit fissato in PIN_GIT (o del ramo principale se non c'e')."""
    commit = PIN_GIT.get(url)
    if not commit:
        subprocess.run(["git", "clone", "--depth", "1", url, str(cartella)], check=True)
        return
    cartella.mkdir(parents=True, exist_ok=True)
    for cmd in (["init", "-q"], ["remote", "add", "origin", url], ["fetch", "-q", "--depth", "1", "origin", commit],
                ["checkout", "-q", "FETCH_HEAD"]):
        subprocess.run(["git", "-C", str(cartella)] + cmd, check=True)


def _rimuovi(path: Path):
    def sblocca(func, p, _exc):          # Windows: i file di sola lettura di .git
        os.chmod(p, stat.S_IWRITE)
        func(p)
    if not path.exists():
        return
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=sblocca)
    else:
        shutil.rmtree(path, onerror=sblocca)


def scarica(voce):
    nome, desc, url, sotto = voce
    cartella = DEST / sotto / nome
    if (cartella / ".completo").exists():
        if nome.startswith("vsco-"):
            ritocca_vsco(cartella)          # le correzioni arrivate dopo il download
        print(f"== {nome}: " + tr("gia' presente, salto"))
        return
    print(f"== {nome}: {tr_descrizione(desc)}")
    download = DEST / "_download"
    if nome in ORCHESTRA_SFZ:
        scarica_orchestra(nome, url, cartella)
    elif url.endswith(".git"):
        _rimuovi(cartella)
        if shutil.which("git"):
            cartella.parent.mkdir(parents=True, exist_ok=True)
            clona_fissato(url, cartella)
        else:                  # senza git: l'archivio .zip di GitHub (nessuno di questi usa Git LFS)
            file = download / f"{nome}.zip"
            scarica_file(archivio_github(url), file)
            appoggio = DEST / sotto / f".{nome}.estrazione"
            _rimuovi(appoggio)
            estrai(file, appoggio)
            interne = list(appoggio.iterdir())
            (interne[0] if len(interne) == 1 and interne[0].is_dir() else appoggio).rename(cartella)
            _rimuovi(appoggio)
            file.unlink()
    else:
        file = download / url.rsplit("/", 1)[-1]
        scarica_file(url, file)
        estrai(file, cartella)
        if nome == "batteria":
            crea_sfz_gm(cartella)
        file.unlink()
    (cartella / ".completo").touch()
    print(f"   -> {cartella}")


_OPCODE_PERCORSO = re.compile(r"(default_path|sample)=(.+?)(?=\s+\w+=|$)")


def campioni_sfz(testo: str, cartella_sfz: str = "") -> list:
    """I campioni citati da un file .sfz, come percorsi relativi alla
    radice del repository ('cartella_sfz' e' la cartella del file):
    default_path + sample, con le barre alla Windows girate. Le librerie
    dell'orchestra non usano #include ne' #define."""
    import posixpath
    cartella_default, campioni = "", []
    for riga in testo.splitlines():
        for chiave, valore in _OPCODE_PERCORSO.findall(riga.split("//")[0].strip()):
            valore = valore.strip().replace("\\", "/")
            if chiave == "default_path":
                cartella_default = valore
            else:
                percorso = posixpath.normpath(posixpath.join(cartella_sfz, cartella_default, valore))
                if percorso.startswith("../") or percorso.startswith("/"):
                    raise Errore(tr("un campione fuori dalla libreria: {}", valore))
                if percorso not in campioni:
                    campioni.append(percorso)
    return campioni


def _url_file(base: str, percorso: str) -> str:
    import urllib.parse
    return base + urllib.parse.quote(percorso)


def _con_guadagno(testo: str, db: float) -> str:
    """Il .sfz con global_volume=db in <global> (o in un <global> nuovo
    dopo <control>, se non ce n'e'), una volta sola."""
    if "global_volume=" in testo:
        return testo
    riga = f"global_volume={db:g}  // SoundText: allineato ai suoni General MIDI"
    if re.search(r"<global>", testo):
        return re.sub(r"<global>", f"<global>\n{riga}", testo, count=1)
    m = re.search(r"<control>[^<]*", testo)
    if m:
        return testo[:m.end()] + f"<global>\n{riga}\n" + testo[m.end():]
    return f"<global>\n{riga}\n" + testo


def _con_correzioni(testo: str, correzioni: list) -> str:
    """Il .sfz con le correzioni di VSCO_CORREZIONI, regione per regione:
    si tocca solo l'opcode delle regioni con quei campioni, e solo se ha
    ancora il valore di VSCO."""
    parti = re.split(r"(?=<region>)", testo)
    for i, parte in enumerate(parti):
        for campione, opcode, vecchio, nuovo in correzioni:
            if campione in parte:
                parti[i] = parte = re.sub(rf"(?<![\w]){opcode}={vecchio}(?![\d])", f"{opcode}={nuovo}", parte)
    return "".join(parti)


def ritocca_vsco(cartella: Path):
    """Le correzioni di SoundText ai .sfz di un gruppo VSCO gia' scaricato:
    il guadagno (VSCO_GUADAGNO_DB) e le correzioni di VSCO_CORREZIONI.
    Si possono rifare: un file gia' corretto resta com'e'."""
    for file in cartella.glob("*.sfz"):
        testo = file.read_text(encoding="utf-8", errors="replace")
        nuovo = _con_correzioni(_con_guadagno(testo, VSCO_GUADAGNO_DB), VSCO_CORREZIONI.get(file.name, []))
        if nuovo != testo:
            file.write_text(nuovo, encoding="utf-8")


def scarica_orchestra(nome: str, base: str, cartella: Path):
    """I file .sfz del gruppo (ORCHESTRA_SFZ) e i campioni che citano,
    scaricati uno per uno da 'base' nella stessa disposizione del
    repository: un file gia' scaricato si salta, uno interrotto riprende
    (scarica_file, su un .part rinominato a download finito)."""
    def prendi(percorso: str) -> Path:
        dest = cartella / percorso
        if not dest.exists():
            parziale = dest.with_name(dest.name + ".part")
            scarica_file(_url_file(base, percorso), parziale, silenzioso=True)
            parziale.replace(dest)
        return dest

    base = base.rstrip("/") + "/"     # un indirizzo cambiato in "Sorgenti" puo' non finire con /
    sfz = ORCHESTRA_SFZ[nome]
    campioni = []
    for percorso in sfz:
        testo = prendi(percorso).read_text(encoding="utf-8", errors="replace")
        for campione in campioni_sfz(testo, percorso.rpartition("/")[0]):
            if campione not in campioni:
                campioni.append(campione)
    print("   " + tr("{} file .sfz, {} campioni", len(sfz), len(campioni)))
    fatto, ultimo = 0, 0.0
    for i, campione in enumerate(campioni, 1):
        fatto += prendi(campione).stat().st_size
        if time.monotonic() - ultimo > 1 or i == len(campioni):
            ultimo = time.monotonic()
            print("\r   " + tr("{} di {} campioni, {:.0f} MB", i, len(campioni), fatto / 1e6) + "   ",
                  end="", flush=True)
    print()
    if nome.startswith("vsco-"):
        ritocca_vsco(cartella)


# Il MuldjordKit non usa la mappa GM (kick=48, snare=50...): le percussioni di
# SoundText (kick=36, snare=38...) resterebbero mute. Ne crea una copia con le
# note GM, nella stessa cartella (i campioni restano quelli originali).
GM_MULDJORD = {48: 36, 49: 35, 50: 38, 51: 40, 52: 42, 53: 46, 54: 51, 55: 53, 56: 59, 57: 56,
               58: 49, 59: 57, 60: 52, 61: 50, 62: 48, 63: 47, 64: 45, 65: 37, 66: 39}


def crea_sfz_gm(cartella: Path):
    sorgenti = sorted(p for p in list(cartella.glob("*.sfz")) + list(cartella.glob("*/*.sfz"))
                      if not p.name.endswith("-GM.sfz"))
    if not sorgenti:
        return
    src = sorgenti[0]
    testo = src.read_text(encoding="utf-8", errors="replace")
    testo = re.sub(r"(?<![A-Za-z_])key=(\d+)",
                   lambda m: "key=%d" % GM_MULDJORD.get(int(m.group(1)), int(m.group(1))), testo)
    dst = src.with_name(src.stem + "-GM.sfz")
    dst.write_text("// Mappa GM (generata da scarica_strumenti)\n" + testo, encoding="utf-8")
    print(f"   -> {dst}")


# ---------------------------------------------------------------------------
# host: programmi e plugin
# ---------------------------------------------------------------------------

def _esegui(cmd, **kw):
    print("   $ " + " ".join(str(c) for c in cmd))
    subprocess.run([str(c) for c in cmd], check=True, **kw)


# Versioni fisse dei plugin gratuiti: per ogni repository il tag della release e lo SHA-256 di ogni file che
# SoundText scarica. Le righe le scrive tools/aggiorna_pin_plugin.py (dalle API di GitHub, senza scaricare niente):
# l'aggiornamento e' una scelta, con la differenza da guardare. Un file con uno SHA-256 diverso non si installa.
# --- PIN_INIZIO (scritto da tools/aggiorna_pin_plugin.py) ---
PIN_PLUGIN = {
    "AidaDSP/AIDA-X": {"tag": "1.1.0", "sha256": {
        "AIDA-X-1.1.0-linux-arm64.tar.xz": "bf9dc137d50bf569ec5243c6ccd81eee983699e1470044a980eeb3717bc55d28",
        "AIDA-X-1.1.0-linux-x86_64.tar.xz": "292b94f635e8adec95f23280fc94f1b6dd954b8a9440f3e51b7e9faa8bdbe543",
        "AIDA-X-1.1.0-macos-universal-10.15.dmg": "cea68478ed1923e79e7285d75a90fe8074dafc1a8884ee0ba7c9d1c92814a226",
        "AIDA-X-1.1.0-win64.zip": "648612e80a598b17778374e42c54fdddd4199a844f7b290ad38f6b3256551425",
    }},
    "Chowdhury-DSP/BYOD": {"tag": "v1.3.0", "sha256": {
        "BYOD-Linux-x64-1.3.0.deb": "c1803ae57b717bab04ef2072c10284bcb7d44fbe352d42645075b0c6875c9aeb",
        "BYOD-Mac-1.3.0.dmg": "997a0508b00a583d8563eb0e330c7e318fe43e7f4f3b06ba3d389221aeb7254a",
        "BYOD-Win-64bit-1.3.0.exe": "a53fb65cedf90f7673e21ac2d12f5b0778f003ae7f2e34e6c4301854a738c36c",
    }},
    "Chowdhury-DSP/ChowKick": {"tag": "v1.2.0", "sha256": {
        "ChowKick-Linux-x64-1.2.0.deb": "2c1328c65bd4af1c188f96d088d71527eccbdc5c434cafe57c8352f53969bb2f",
        "ChowKick-Mac-1.2.0.dmg": "de1833ac2bfd7f9d74ba61cb64f3fb7c600de348cba6b46d9c05c8df14d158f7",
        "ChowKick-Win-64bit-1.2.0.exe": "d136b3938111a118d64e1dfc01f6b153a8c3ee5641001aed31b42cb033616c82",
    }},
    "Chowdhury-DSP/ChowMatrix": {"tag": "v1.3.0", "sha256": {
        "ChowMatrix-Mac-1.3.0.dmg": "11705e4cfb023525e8b6830fb29feb046eac05688428a12a8fdad48dc9a9fdcf",
        "ChowMatrix-Win-1.3.0.exe": "b1e2451ae66362bf82112e77fccc48a1233780b6cbfb58fe1a588b17a77456c5",
    }},
    "GuitarML/Chameleon": {"tag": "v1.2.0", "sha256": {
        "Chameleon-Linux-x64-1.2.deb": "06b2ba4d8438fc90376485aff6ed3c732868c6bfb1b773a2c348c0e6ad6d1352",
        "Chameleon-Win-1.2.0.exe": "ac7e639eaad7c4db1aba556b6a489a17fd0dd4a67df49cbc5e126367a9a1d690",
        "Install-Chameleon-v1.2-Mac.dmg": "9387fb1f0d5f4efe26dcb7d179dbd0a29ec96f976643be0b551dc0a56125739e",
    }},
    "GuitarML/Proteus": {"tag": "v1.2", "sha256": {
        "Install-Proteus-v1.2-Mac.dmg": "7194c26d4b04f40811295ad4ebe1ef3d1bb033a9976f6789ebf3ec021430e7d0",
        "Proteus-Linux-x64-1.2.deb": "d3bf5a11127da6cf53af183390dc20350c15543617a8743b166c73f6a1a08e90",
        "Proteus-Win-1.2.0.exe": "f63f39d4f38113c6efb93e4440fb3de84c1397c1cc52294c4922a14f393309c6",
    }},
    "asb2m10/dexed": {"tag": "v1.1.0", "sha256": {
        "Dexed-1.1.0-lnx.zip": "3a1a01511e3428f432cc91c7bf5267d72bfcb68aded4f084d4f9d002dcc42da6",
        "Dexed-1.1.0-macOS.zip": "d6576d064313327e216cec9d6f62caa650b44746bc7c8d4b010df7f55d9b8ae3",
        "Dexed-1.1.0-win.zip": "4773150a3dfa281d1caef583f493a41ed99ea95b054b5a3479780799ed6279cc",
    }},
    "baconpaul/airwin2rack": {"tag": "DAWPlugin", "sha256": {
        "AirwindowsConsolidated-2026-11-15-59a227e-Linux.zip": "32cb5d1f6cc39128fee901d9e2add7d22a3c9fb2fa67963281aa3c13f0d2d158",
        "AirwindowsConsolidated-2026-11-15-59a227e-Windows.zip": "b2f0d0f02b8e129f56a6e6b25c62e2606105f77a283d4aa0d54766f44ec22f23",
        "airwindows-consolidated-macOS-2026-11-15-59a227e.dmg": "ca48c320070f1a05da5b2ff4c0549ded2de21af0f68123195780c94efac834d2",
    }},
    "baconpaul/six-sines": {"tag": "v1.2.1", "sha256": {
        "six-sines-Linux-2026-07-20-18ecb36.zip": "9b5353eebfec3e462c80ed8c0f53c965e6262bb38537518159cce71de7eace41",
        "six-sines-Windows-2026-07-20-18ecb36.zip": "9f7c7fa5cb1c5e11b53c0a9306ee443149cc7bc0a109380dbbe1578f3a7b6e5d",
        "six-sines-macOS-2026-07-20-18ecb36.dmg": "2da3de486551da88e06162a90ef917019c46a25c01d1ec0cdf5e0416b7394d6c",
    }},
    "brummer10/NeuralRack": {"tag": "v0.4.1", "sha256": {
        "NeuralRack-v0.4.1-lv2-linux-arm64.tar.xz": "c9ced67afeb8e48a8366f97e9e9b3899d6fdb09548d27e4d87010d48c5513bf5",
        "NeuralRack-v0.4.1-vst3-linux-x86_64.tar.xz": "9a0c20c5610ba542ec1895fb9efafc4d4bcde65b30324f522ecfce8a356207cc",
        "NeuralRack-vst3-v0.4.1-win64.zip": "522bd2ade9efcc906a132bd773b70df4b0744659546db5e9dcc8c4ccd4ddd0ae",
    }},
    "brummer10/Ratatouille.lv2": {"tag": "v0.9.12", "sha256": {
        "Ratatouille.lv2-clap-v0.9.12-linux-x86_64.tar.xz": "a81610b79053bbc759ce0eaa26d55a52363039a45cc87fc754b3671b43f338aa",
        "Ratatouille.lv2-clap-v0.9.12-win64.zip": "aeb7367f1afe8515589ba816f38c19361d4a6f6987140e0926e6fd573dc4662b",
        "Ratatouille.lv2-v0.9.12-linux-arm64.tar.xz": "9eba7b230e0258e83571ba377ac940b621cf1e9f1d38061047cc27ebf7f609b6",
        "Ratatouille.lv2-v0.9.12-linux-x86_64.tar.xz": "134a0cbd7de8537e68e9d5e0855567d3a4fc53036da75c8efe2ea8ea8aad22b3",
    }},
    "geonkick-synthesizer/geonkick": {"tag": "v3.9.1", "sha256": {
        "GNULinux_binaries_v3.9.1_basic.zip": "35107da8c32f46c69ca546b1ef7c98e40f0c3570b017b70dd618161c576abdd8",
    }},
    "jatinchowdhury18/AnalogTapeModel": {"tag": "v2.11.4", "sha256": {
        "ChowTapeModel-Mac-2.11.4.dmg": "9b37e2b6cb6c0a839ee9c65e1a958834ca647b3edfc4bd144115c483b4d64f82",
        "ChowTapeModel-Win-64bit-2.11.4.exe": "8ba6e91196067244837877d9ca4a8e4a1f5bfad60cf33fa699c8a5b41f1211bf",
    }},
    "jatinchowdhury18/KlonCentaur": {"tag": "v1.4.0", "sha256": {
        "ChowCentaur-Mac-1.4.0.dmg": "8b8c876cc9429d1c9d51d25a08fa3513398370b6b527067cb5d3982ca988bf3e",
        "ChowCentaur-Win-1.4.0.exe": "3ff707e3e49e7cac0bb0819219eefcc6ed59b281246b43fc0465c0fb1d198048",
    }},
    "lsp-plugins/lsp-plugins": {"tag": "1.2.37", "sha256": {
        "lsp-plugins-1.2.37-Linux-aarch64.7z": "d0fc5c5600bee23eb088f99f899b7dd0bae6da43dc12e020df3ad56e3e0ed15a",
        "lsp-plugins-1.2.37-Linux-x86_64.7z": "bbdfbfce4591ea07e7ac9dac0b1aca8ea7ccf9d850aafbf9ac0a347a1340ee55",
    }},
    "michaelwillis/dragonfly-reverb": {"tag": "3.2.10", "sha256": {
        "dragonfly-reverb-3.2.10-linux-arm64.tar.xz": "6c830ad1b1cc028b0f3c4f4c0a4b073d7193ba1c8783528ed9365df1fc9b23c2",
        "dragonfly-reverb-3.2.10-linux-x86_64.tar.xz": "59f1593120de82e31dd194e2ab1536af14fec2b3ec6ec45abf6d9c8ac02ef430",
        "dragonfly-reverb-3.2.10-macos-universal.dmg": "e0b854b92a4e51ce5851320fb1a9f91ab1a4309f997de070e175b3e5cab4adaf",
        "dragonfly-reverb-3.2.10-win64.zip": "ca5f35f9dcd9a33f06490d3c92f04061a1a798cb81257d5ca5851bdda0824c66",
    }},
    "midilab/jc303": {"tag": "v0.14.0", "sha256": {
        "jc303-0.14.0-linux_x64-plugins.zip": "378200f8ddda266873c9795feb6ee857fbae000a3b3537a7b42933dd277b370c",
        "jc303-0.14.0-macos_universal-plugins.zip": "dfdc9b7deb674d472dc8663ec03a8ea177bf5d752beac4058cd0ea309bd48107",
        "jc303-0.14.0-windows_x64-plugins.zip": "499c1bec494d9116999a52c13ae59ff503bdff32438e8ef4af5fce6408e08057",
    }},
    "pdesaulniers/wolf-shaper": {"tag": "v1.0.2", "sha256": {
        "wolf-shaper-v1.0.2+20230515144200-windows-x64.zip": "42a703a5f71b19855d9213d57f2261d2182c73c73d39730775188df3e4c47da9",
        "wolf-shaper-v1.0.2-linux-arm64.zip": "79a2e37416be98b8b393d0732c0e49af4f769cc9d0010ecd60e0d740233b46c2",
        "wolf-shaper-v1.0.2-linux-x64.zip": "8b844e9b535d2b8a8a07fc6cec207beae8161f7d6da36e4a856a766aa441b848",
        "wolf-shaper-v1.0.2-macos-universal.zip": "19bba017c8eed9b697712d0f1e769ab30eb785534c152e6783017735fe73de03",
    }},
    "sfztools/sfizz-ui": {"tag": "1.2.3", "sha256": {
        "sfizz-1.2.3-macos.pkg": "62c76af58bfec05ca6ef199befca7c2508e15a5e63bca076198d94f085c14da7",
        "sfizz-1.2.3-win64.exe": "56f57dfe443018e947b82b8e2bf4c9d824a9c961ff2b8eb6c5e929030b71b937",
    }},
    "surge-synthesizer/OB-Xf": {"tag": "v1.0.3", "sha256": {
        "ob-xf-Linux-v1.0.3.zip": "72b60c83cf6426337031df744c34a047104a9d95f1feaf6cd048ecfa39f74c96",
        "ob-xf-Windows-v1.0.3.zip": "149fda0649daf8a3aa0851801f92515f0dbf6203acf33c0edc7d3c445e80b1e7",
        "ob-xf-macOS-v1.0.3.dmg": "e6f52f453c476dfafbd3225b80c5c3ec341ec20be5748c6f70c01cef14e7e7a8",
    }},
    "surge-synthesizer/releases-xt": {"tag": "1.3.4", "sha256": {
        "surge-xt-macos-1.3.4-pluginsonly.zip": "37d8d809693adc86587b7bc75a2384fc4e905f259aa9b9a21777749d36fbf8aa",
        "surge-xt-portable-content-1.3.4.tar.gz": "7ed24822eab69f73101d8558222979b1bceb4882a780292bb7087309b7b101bd",
        "surge-xt-win64-1.3.4-pluginsonly.zip": "564e162c560af07ad4ed47fe1bfcd827cf97a575de30d06c48249aad2e7c35e6",
    }},
    "zamaudio/zam-plugins": {"tag": "4.5", "sha256": {
        "zam-plugins-4.5-linux-arm64.tar.xz": "4e02771b743afaaa2d6912eac083661c1d9ab0a92dd6787414f29e365877b4c2",
        "zam-plugins-4.5-linux-x86_64.tar.xz": "16b022cce2998d11d3dbcf15aa6fe176cd14576cad42250ae8cfc56d1b7add7a",
        "zam-plugins-4.5-macos-universal.dmg": "ac163eb25781b08936b80c12e809777e3aaa523887d0355504f2e6586c4e43cf",
        "zam-plugins-4.5-win64.zip": "745990b0acdda1cc319cd55aafdf61b6f258015810f310abd31d8bbe849e4da8",
    }},
}
# --- PIN_FINE ---


class UrlVerificato(str):
    """L'indirizzo di un file di una release, con lo SHA-256 atteso (scarica_file lo controlla a download finito)."""
    sha256 = ""
    nome = ""


def asset_github(repo: str, release: str, modello: str) -> str:
    """URL del primo file della release che corrisponde al modello. Per i repository di PIN_PLUGIN la release e' quella
    fissata (con "latest" si usa il tag in PIN_PLUGIN) e l'URL porta lo SHA-256 atteso; un file senza SHA-256 fissato
    non si scarica."""
    fissato = PIN_PLUGIN.get(repo)
    if fissato and release == "latest":
        release = fissato["tag"]
    api = f"https://api.github.com/repos/{repo}/releases/" + ("latest" if release == "latest" else f"tags/{release}")
    with urllib.request.urlopen(_richiesta(api, Accept="application/vnd.github+json"), timeout=60) as resp:
        dati = json.load(resp)
    for asset in dati.get("assets", []):
        if re.fullmatch(modello, asset["name"]):
            url = UrlVerificato(asset["browser_download_url"])
            url.nome = asset["name"]
            if fissato:
                if asset["name"] not in fissato["sha256"]:
                    raise Errore(tr("il file {} non e' fra quelli verificati: non lo scarico (aggiorna i riferimenti)", asset["name"]))
                url.sha256 = fissato["sha256"][asset["name"]]
                if not url.sha256:                      # release vecchia senza «digest»: da fissare con --calcola
                    print("   " + tr("attenzione: lo SHA-256 di {} non e' ancora fissato", asset["name"]))
            return url
    raise Errore(tr("nessun file {} nella release {} di {}", modello, release, repo))


def copia_vst3(radice: Path, dest: Path, estensione: str = ".vst3", obbligatorio: bool = True) -> int:
    """Copia ogni bundle (.vst3, o .lv2 con estensione=".lv2") trovato sotto
    radice nella cartella dest. Restituisce quanti ne ha copiati; se non ce
    n'e' nessuno e 'obbligatorio', e' un errore."""
    dest.mkdir(parents=True, exist_ok=True)
    trovati = 0
    for root, dirs, files in os.walk(radice):
        for nome in list(dirs) + files:
            if nome.lower().endswith(estensione):
                src, dst = Path(root, nome), dest / nome
                if dst.is_dir():
                    _rimuovi(dst)
                elif dst.exists():
                    dst.unlink()
                (shutil.copytree if src.is_dir() else shutil.copy2)(src, dst)
                print(f"   -> {dst}")
                trovati += 1
                if nome in dirs:
                    dirs.remove(nome)            # dentro un bundle non si cerca
    if not trovati and obbligatorio:
        raise Errore(tr("nessun plugin {} nell'archivio", estensione[1:].upper()))
    return trovati


def cartella_dati_surge() -> Path:
    """Dove Surge XT cerca i dati senza installer (vedi SurgeStorage.cpp di
    Surge): su Windows una cartella SurgeXTData accanto ai plugin, su macOS
    Application Support dell'utente."""
    if SISTEMA == "windows":
        return user_vst3_dir() / "SurgeXTData"
    return Path.home() / "Library" / "Application Support" / "Surge XT"


def installa_dati_surge(sorgente: Path):
    dest = cartella_dati_surge()
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copytree(sorgente, dest, dirs_exist_ok=True)
    print(f"   -> {dest}")


def amministratore_linux() -> list:
    """Il comando per eseguire come amministratore: sudo da un terminale
    (chiede li' la password), pkexec senza terminale (la finestra
    "Scarica e installa" di SoundText: la password la chiede una finestra
    del sistema). [] se non c'e' modo."""
    if sys.stdin is not None and sys.stdin.isatty():
        return ["sudo"]
    return ["pkexec"] if shutil.which("pkexec") else []


def host_linux():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        # leggibile dall'utente _apt, altrimenti apt avvisa che scarica fuori dalla sandbox
        tmp.chmod(0o755)
        pacchetti = ["7zip"]
        if subprocess.run(["dpkg", "-s", "surge-xt"], capture_output=True).returncode != 0:
            print("== " + tr("Scarico Surge XT (sintetizzatore VST3/LV2, Nightly dal GitHub ufficiale)"))
            url = asset_github(SURGE_NIGHTLY_REPO, "Nightly", r"surge-xt-linux-x64-NIGHTLY-.*\.deb")
            scarica_file(url, tmp / "surge-xt.deb")
            pacchetti.append(tmp / "surge-xt.deb")
        if subprocess.run(["dpkg", "-s", "sfizz"], capture_output=True).returncode != 0:
            print("== " + tr("Scarico sfizz (player SFZ per Ubuntu 24.04)"))
            base = SFIZZ_DEB_BASE.rstrip("/")
            scarica_file(f"{base}/libsfizz1_1.2.3-0_amd64.deb", tmp / "libsfizz1.deb")
            scarica_file(f"{base}/sfizz_1.2.3-0_amd64.deb", tmp / "sfizz.deb")
            pacchetti += [tmp / "libsfizz1.deb", tmp / "sfizz.deb"]
        admin = amministratore_linux()
        if not admin:
            raise Errore(tr("serve la password di amministratore: dal terminale, nella cartella di SoundText, "
                            "esegui ./scarica_strumenti.sh host"))
        print("== " + tr("Installo {}", ", ".join(Path(p).stem if isinstance(p, Path) else p for p in pacchetti))
              + " (apt" + (": " + tr("la password la chiede una finestra del sistema") if admin == ["pkexec"] else "")
              + ")")
        # un solo comando da amministratore: la password si chiede una volta
        _esegui(admin + ["sh", "-c", 'apt-get update && apt-get install -y "$@"', "sh"] + pacchetti)


def host_windows_macos():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        print("== 7-Zip (" + tr("per gli strumenti in .7z") + ")")
        if programma_7z():
            print("   " + tr("gia' presente"))
        elif SISTEMA == "windows" and shutil.which("winget"):
            _esegui(["winget", "install", "--id", "7zip.7zip", "-e", "--accept-source-agreements"])
        elif SISTEMA == "macos" and shutil.which("brew"):
            _esegui(["brew", "install", "sevenzip"])
        else:
            print("   " + tr("installalo da https://www.7-zip.org (oppure: pip install py7zr)"))
        print("== " + tr("Surge XT (sintetizzatore VST3), nella cartella VST3 dell'utente"))
        modello = (r"surge-xt-win64-[\d.]+-pluginsonly\.zip" if SISTEMA == "windows"
                   else r"surge-xt-macos-[\d.]+-pluginsonly\.zip")
        scarica_file(asset_github(SURGE_REPO, "latest", modello), tmp / "surge.zip")
        estrai(tmp / "surge.zip", tmp / "surge")
        copia_vst3(tmp / "surge", user_vst3_dir())
        print("== " + tr("Dati di fabbrica di Surge XT (preset, wavetable)"))
        scarica_file(asset_github(SURGE_REPO, "latest",
                                  r"surge-xt-portable-content-[\d.]+\.tar\.gz"), tmp / "surge-dati.tar.gz")
        estrai(tmp / "surge-dati.tar.gz", tmp / "surge-dati")
        installa_dati_surge(next((tmp / "surge-dati").rglob("SurgeXTData")))
        print("== " + tr("sfizz (player SFZ, VST3): avvio il suo installer"))
        if SISTEMA == "windows":
            scarica_file(asset_github(SFIZZ_UI_REPO, "latest", r"sfizz-[\d.]+-win64\.exe"), tmp / "sfizz.exe")
            avvia_installer_windows(tmp / "sfizz.exe")
        else:
            pkg = Path.home() / "Downloads" / "sfizz-macos.pkg"
            scarica_file(asset_github(SFIZZ_UI_REPO, "latest", r"sfizz-[\d.]+-macos\.pkg"), pkg)
            _esegui(["open", "-W", pkg])


# ---------------------------------------------------------------------------
# plugin VST3 gratuiti e open source, dalle release ufficiali su GitHub, nella
# cartella VST3 dell'utente (niente diritti di amministratore)
# ---------------------------------------------------------------------------

# nome, descrizione, repository, release ("latest" o un tag), file per sistema
# (chiave_sistema(): "windows", "macos", "linux-x86_64", "linux-aarch64")
PLUGIN_VST3 = [
    ("Dexed", "sintetizzatore FM, emula lo Yamaha DX7", "asb2m10/dexed", "latest",
     {"linux-x86_64": r"Dexed-[\d.]+-lnx\.zip", "windows": r"Dexed-[\d.]+-win\.zip",
      "macos": r"Dexed-[\d.]+-macOS\.zip"}),
    ("Airwindows Consolidated", "oltre 400 effetti Airwindows in un solo plugin", "baconpaul/airwin2rack",
     "DAWPlugin",
     {"linux-x86_64": r"AirwindowsConsolidated-[\d-]+-[0-9a-f]+-Linux\.zip",
      "windows": r"AirwindowsConsolidated-[\d-]+-[0-9a-f]+-Windows\.zip",
      "macos": r"airwindows-consolidated-macOS-[\d-]+-[0-9a-f]+\.dmg"}),
    ("Dragonfly Reverb", "riverberi di sala, stanza e piastra", "michaelwillis/dragonfly-reverb", "latest",
     {"linux-x86_64": r"dragonfly-reverb-[\d.]+-linux-x86_64\.tar\.xz",
      "linux-aarch64": r"dragonfly-reverb-[\d.]+-linux-arm64\.tar\.xz",
      "windows": r"dragonfly-reverb-[\d.]+-win64\.zip",
      "macos": r"dragonfly-reverb-[\d.]+-macos-universal\.dmg"}),
    # LSP pubblica solo build per Linux (e FreeBSD): niente Windows e macOS
    ("LSP Plugins", "compressori, equalizzatori, limiter, riverberi e delay da studio", "lsp-plugins/lsp-plugins",
     "latest",
     {"linux-x86_64": r"lsp-plugins-[\d.]+-Linux-x86_64\.7z",
      "linux-aarch64": r"lsp-plugins-[\d.]+-Linux-aarch64\.7z"}),
    ("OB-Xf", "sintetizzatore analogico stile Oberheim OB-X (GPL-3.0)", "surge-synthesizer/OB-Xf", "latest",
     {"linux-x86_64": r"ob-xf-Linux-v[\d.]+\.zip", "windows": r"ob-xf-Windows-v[\d.]+\.zip",
      "macos": r"ob-xf-macOS-v[\d.]+\.dmg"}),
    ("Wolf Shaper", "waveshaper e distorsione (GPL-3.0; su Linux e' fra i plugin LV2)", "pdesaulniers/wolf-shaper",
     "latest",
     {"windows": r"wolf-shaper-v[\d.]+\+\d+-windows-x64\.zip", "macos": r"wolf-shaper-v[\d.]+-macos-universal\.zip"}),
    # I plugin Chow per Windows esistono solo come installer .exe: lo si
    # avvia (come per sfizz) e Windows chiede di confermare l'installazione
    ("ChowTapeModel", "saturazione da registratore a nastro (GPL-3.0)", "jatinchowdhury18/AnalogTapeModel", "latest",
     {"windows": r"ChowTapeModel-Win-64bit-[\d.]+\.exe", "macos": r"ChowTapeModel-Mac-[\d.]+\.dmg"}),
    ("ChowCentaur", "overdrive per chitarra, emula il Klon Centaur (BSD-3)", "jatinchowdhury18/KlonCentaur",
     "latest",
     {"windows": r"ChowCentaur-Win-[\d.]+\.exe", "macos": r"ChowCentaur-Mac-[\d.]+\.dmg"}),
    ("ChowMatrix", "delay a rami (BSD-3)", "Chowdhury-DSP/ChowMatrix", "latest",
     {"windows": r"ChowMatrix-Win-[\d.]+\.exe", "macos": r"ChowMatrix-Mac-[\d.]+\.dmg"}),
    # Amplificatori per chitarra a reti neurali. AIDA-X ha un modello e una cassa
    # gia' dentro e ne carica altri dalla sua finestra; i due di GuitarML su Linux esistono solo
    # come pacchetto .deb, che si apre senza installarlo (vedi estrai_deb)
    ("AIDA-X", "amplificatore per chitarra a modelli neurali, con un amplificatore e una cassa gia' dentro (GPL-3.0)",
     "AidaDSP/AIDA-X", "latest",
     {"linux-x86_64": r"AIDA-X-[\d.]+-linux-x86_64\.tar\.xz", "linux-aarch64": r"AIDA-X-[\d.]+-linux-arm64\.tar\.xz",
      "windows": r"AIDA-X-[\d.]+-win64\.zip", "macos": r"AIDA-X-[\d.]+-macos-universal-[\d.]+\.dmg"}),
    ("Chameleon", "amplificatore per chitarra vintage con tre suoni pronti (GPL-3.0)", "GuitarML/Chameleon", "latest",
     {"linux-x86_64": r"Chameleon-Linux-x64-[\d.]+\.deb", "windows": r"Chameleon-Win-[\d.]+\.exe",
      "macos": r"Install-Chameleon-v[\d.]+-Mac\.dmg"}),
    ("Proteus", "amplificatori e pedali per chitarra da modelli neurali, da caricare dalla sua finestra (GPL-3.0)",
     "GuitarML/Proteus", "latest",
     {"linux-x86_64": r"Proteus-Linux-x64-[\d.]+\.deb", "windows": r"Proteus-Win-[\d.]+\.exe",
      "macos": r"Install-Proteus-v[\d.]+-Mac\.dmg"}),
    ("BYOD", "catena di distorsioni, pedali e amplificatori per chitarra da comporre (GPL-3.0)",
     "Chowdhury-DSP/BYOD", "latest",
     {"linux-x86_64": r"BYOD-Linux-x64-[\d.]+\.deb", "windows": r"BYOD-Win-64bit-[\d.]+\.exe",
      "macos": r"BYOD-Mac-[\d.]+\.dmg"}),
    # NeuralRack su Linux ARM esiste solo in LV2 (vedi PLUGIN_LV2)
    ("NeuralRack", "amplificatore per chitarra: un modello NAM o AIDA-X con la sua cassa IR (BSD-3)",
     "brummer10/NeuralRack", "latest",
     {"linux-x86_64": r"NeuralRack-v[\d.]+-vst3-linux-x86_64\.tar\.xz", "windows": r"NeuralRack-vst3-v[\d.]+-win64\.zip"}),
    ("JC-303", "sintetizzatore di basso, clone del Roland TB-303 (GPL-3.0)", "midilab/jc303", "latest",
     {"linux-x86_64": r"jc303-[\d.]+-linux_x64-plugins\.zip", "windows": r"jc303-[\d.]+-windows_x64-plugins\.zip",
      "macos": r"jc303-[\d.]+-macos_universal-plugins\.zip"}),
    ("Six Sines", "sintetizzatore FM a sei operatori (MIT)", "baconpaul/six-sines", "latest",
     {"linux-x86_64": r"six-sines-Linux-[\d-]+-[0-9a-f]+\.zip", "windows": r"six-sines-Windows-[\d-]+-[0-9a-f]+\.zip",
      "macos": r"six-sines-macOS-[\d-]+-[0-9a-f]+\.dmg"}),
    ("ChowKick", "sintetizzatore di cassa in stile drum machine (BSD-3)", "Chowdhury-DSP/ChowKick", "latest",
     {"linux-x86_64": r"ChowKick-Linux-x64-[\d.]+\.deb", "windows": r"ChowKick-Win-64bit-[\d.]+\.exe",
      "macos": r"ChowKick-Mac-[\d.]+\.dmg"}),
    ("Zam plugins", "compressori, equalizzatori, delay, gate e saturazione (GPL-2.0)", "zamaudio/zam-plugins", "latest",
     {"linux-x86_64": r"zam-plugins-[\d.]+-linux-x86_64\.tar\.xz", "linux-aarch64": r"zam-plugins-[\d.]+-linux-arm64\.tar\.xz",
      "windows": r"zam-plugins-[\d.]+-win64\.zip", "macos": r"zam-plugins-[\d.]+-macos-universal\.dmg"}),
]


def avvia_installer_windows(installer: Path):
    """Un installer .exe: Start-Process fa comparire la richiesta dei
    diritti di amministratore (subprocess no) e aspetta che finisca."""
    _esegui(["powershell", "-NoProfile", "-Command", f"Start-Process -Wait -FilePath '{installer}'"])


def chiave_sistema() -> str:
    if SISTEMA != "linux":
        return SISTEMA
    macchina = platform.machine().lower()
    return "linux-aarch64" if macchina in ("aarch64", "arm64") else "linux-x86_64"


def vst3_da_dmg(dmg: Path, tmp: Path, dest: Path):
    """macOS: monta l'immagine e copia i VST3 che contiene; se sono dentro un
    installer .pkg lo si apre con pkgutil (senza eseguirlo, quindi senza
    password di amministratore)."""
    mnt = tmp / "volume"
    mnt.mkdir()
    _esegui(["hdiutil", "attach", "-nobrowse", "-readonly", "-mountpoint", mnt, dmg])
    try:
        if any(mnt.rglob("*.vst3")):
            copia_vst3(mnt, dest)
            return
        aperti = tmp / "pacchetti"
        aperti.mkdir()
        for i, pkg in enumerate(sorted(mnt.rglob("*.pkg"))):
            _esegui(["pkgutil", "--expand-full", pkg, aperti / f"{i}-{pkg.stem}"])
        copia_vst3(aperti, dest)
    finally:
        subprocess.run(["hdiutil", "detach", str(mnt), "-quiet"], check=False)


def installa_plugin_vst3() -> list:
    """Scarica e installa i plugin di PLUGIN_VST3 disponibili per questo
    sistema; un plugin che non riesce non ferma gli altri. Restituisce i
    nomi di quelli non riusciti."""
    dest = user_vst3_dir()
    falliti = []
    for nome, desc, repo, release, modelli in PLUGIN_VST3:
        modello = modelli.get(chiave_sistema())
        if modello is None:
            print(f"== {nome}: " + tr("non c'e' una versione per questo sistema, salto"))
            continue
        print(f"== {nome} ({tr(desc)}), " + tr("nella cartella VST3 dell'utente"))
        try:
            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                url = asset_github(repo, release, modello)
                archivio = tmp / url.rsplit("/", 1)[-1]
                scarica_file(url, archivio)
                if archivio.suffix == ".dmg":
                    vst3_da_dmg(archivio, tmp, dest)
                elif archivio.suffix == ".exe":
                    print("   " + tr("avvio il suo installer: conferma l'installazione nella finestra di Windows"))
                    avvia_installer_windows(archivio)
                else:
                    estrai(archivio, tmp / "estratto")
                    copia_vst3(tmp / "estratto", dest)
        except (Errore, OSError, subprocess.CalledProcessError, urllib.error.URLError) as e:
            print("   " + tr("non riuscito: {}", e))
            falliti.append(nome)
    return falliti


def installa_vst3():
    falliti = installa_plugin_vst3()
    if falliti:
        raise Errore(tr("plugin VST3 non installati: {} (rilancia per riprovare)", ", ".join(falliti)))


# ---------------------------------------------------------------------------
# plugin LV2 gratuiti e open source, nella cartella LV2 dell'utente: solo su
# Linux, dove SoundText li usa con la libreria lilv (vedi core.lv2_host)
# ---------------------------------------------------------------------------

PLUGIN_LV2 = [
    ("Dragonfly Reverb", "riverberi di sala, stanza, piastra e prime riflessioni (GPL-3.0)",
     "michaelwillis/dragonfly-reverb", "latest",
     {"linux-x86_64": r"dragonfly-reverb-[\d.]+-linux-x86_64\.tar\.xz",
      "linux-aarch64": r"dragonfly-reverb-[\d.]+-linux-arm64\.tar\.xz"}),
    ("LSP Plugins", "compressori, equalizzatori, limiter e delay da studio (LGPL-3.0)", "lsp-plugins/lsp-plugins",
     "latest",
     {"linux-x86_64": r"lsp-plugins-[\d.]+-Linux-x86_64\.7z",
      "linux-aarch64": r"lsp-plugins-[\d.]+-Linux-aarch64\.7z"}),
    ("Wolf Shaper", "waveshaper e distorsione (GPL-3.0)", "pdesaulniers/wolf-shaper", "latest",
     {"linux-x86_64": r"wolf-shaper-v[\d.]+-linux-x64\.zip", "linux-aarch64": r"wolf-shaper-v[\d.]+-linux-arm64\.zip"}),
    ("Geonkick", "sintetizzatore di batteria e percussioni (GPL-3.0)", "geonkick-synthesizer/geonkick", "latest",
     {"linux-x86_64": r"GNULinux_binaries_v[\d.]+_basic\.zip"}),
    ("Ratatouille", "amplificatore per chitarra: carica e miscela modelli NAM e AIDA-X (BSD-3)",
     "brummer10/Ratatouille.lv2", "latest",
     {"linux-x86_64": r"Ratatouille\.lv2-v[\d.]+-linux-x86_64\.tar\.xz",
      "linux-aarch64": r"Ratatouille\.lv2-v[\d.]+-linux-arm64\.tar\.xz"}),
    # su Linux x86_64 NeuralRack e' fra i VST3
    ("NeuralRack", "amplificatore per chitarra: un modello NAM o AIDA-X con la sua cassa IR (BSD-3)",
     "brummer10/NeuralRack", "latest", {"linux-aarch64": r"NeuralRack-v[\d.]+-lv2-linux-arm64\.tar\.xz"}),
]

# Plugin CLAP gratuiti e open source che non esistono in VST3 (di un plugin che
# ha anche il VST3 SoundText mostra solo quello), nella cartella CLAP dell'utente
PLUGIN_CLAP = [
    ("Ratatouille", "amplificatore per chitarra: carica e miscela modelli NAM e AIDA-X (BSD-3)",
     "brummer10/Ratatouille.lv2", "latest",
     {"linux-x86_64": r"Ratatouille\.lv2-clap-v[\d.]+-linux-x86_64\.tar\.xz",
      "windows": r"Ratatouille\.lv2-clap-v[\d.]+-win64\.zip"}),
]


def lilv_presente() -> bool:
    """La libreria lilv con cui SoundText carica i plugin LV2 (come la
    cerca core.lv2_host)."""
    import ctypes.util
    nome = ctypes.util.find_library("lilv-0") or "liblilv-0.so.0"
    try:
        ctypes.CDLL(nome)
        return True
    except OSError:
        return False


def installa_lilv():
    """lilv con apt (Debian, Ubuntu e derivate), con la password di amministratore."""
    if SISTEMA != "linux":
        raise Errore(tr("i plugin LV2 si usano solo su Linux"))
    if lilv_presente():
        print("== lilv: " + tr("gia' presente"))
        return
    if not shutil.which("apt-get"):
        raise Errore(tr("installa la libreria lilv con il gestore di pacchetti del sistema (pacchetto lilv)"))
    admin = amministratore_linux()
    if not admin:
        raise Errore(tr("serve la password di amministratore: dal terminale esegui sudo apt-get install -y liblilv-0-0"))
    print("== " + tr("Installo {}", "lilv") + " (liblilv-0-0, apt"
          + (": " + tr("la password la chiede una finestra del sistema") if admin == ["pkexec"] else "") + ")")
    _esegui(admin + ["apt-get", "install", "-y", "liblilv-0-0"])


def _installa_plugin(elenco: list, dest: Path, estensione: str, dove: str) -> list:
    """Scarica i plugin di 'elenco' disponibili per questo sistema e ne
    copia i bundle con 'estensione' in dest; un plugin che non riesce non
    ferma gli altri. Restituisce i nomi di quelli non riusciti."""
    falliti = []
    for nome, desc, repo, release, modelli in elenco:
        modello = modelli.get(chiave_sistema())
        if modello is None:
            print(f"== {nome}: " + tr("non c'e' una versione per questo sistema, salto"))
            continue
        print(f"== {nome} ({tr(desc)}), " + dove)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                url = asset_github(repo, release, modello)
                archivio = tmp / url.rsplit("/", 1)[-1]
                scarica_file(url, archivio)
                estrai(archivio, tmp / "estratto")
                copia_vst3(tmp / "estratto", dest, estensione)
        except (Errore, OSError, subprocess.CalledProcessError, urllib.error.URLError) as e:
            print("   " + tr("non riuscito: {}", e))
            falliti.append(nome)
    return falliti


def installa_lv2():
    if SISTEMA != "linux":
        print("== lv2: " + tr("i plugin LV2 si usano solo su Linux, salto"))
        return
    falliti = _installa_plugin(PLUGIN_LV2, user_lv2_dir(), ".lv2", tr("nella cartella LV2 dell'utente"))
    if not lilv_presente():
        print("   " + tr("Attenzione: manca la libreria lilv, senza la quale SoundText non usa i plugin LV2 "
                         "({} lilv, oppure sudo apt-get install -y liblilv-0-0)", comando_script()))
    if falliti:
        raise Errore(tr("plugin LV2 non installati: {} (rilancia per riprovare)", ", ".join(falliti)))


def installa_clap():
    falliti = _installa_plugin(PLUGIN_CLAP, user_clap_dir(), ".clap", tr("nella cartella CLAP dell'utente"))
    if falliti:
        raise Errore(tr("plugin CLAP non installati: {} (rilancia per riprovare)", ", ".join(falliti)))


def installa_clap_con_vst3():
    """I file .clap che stanno negli stessi archivi dei plugin VST3 gratuiti
    (PLUGIN_VST3): per chi vuole anche il CLAP di un plugin che ha il VST3.
    Un archivio senza CLAP, o che non si puo' aprire senza eseguirlo
    (installer .exe, immagini .dmg), si salta; non e' un errore."""
    dest = user_clap_dir()
    falliti = []
    for nome, desc, repo, release, modelli in PLUGIN_VST3:
        modello = modelli.get(chiave_sistema())
        if modello is None:
            continue
        if re.search(r"\.(exe|dmg|deb)\b", modello):
            print(f"== {nome}: " + tr("si installa con un programma di installazione, non cerco il CLAP, salto"))
            continue
        print(f"== {nome} ({tr(desc)}), " + tr("nella cartella CLAP dell'utente"))
        try:
            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                url = asset_github(repo, release, modello)
                archivio = tmp / url.rsplit("/", 1)[-1]
                scarica_file(url, archivio)
                estrai(archivio, tmp / "estratto")
                if not copia_vst3(tmp / "estratto", dest, ".clap", obbligatorio=False):
                    print("   " + tr("nessun plugin CLAP in questo archivio, salto"))
        except (Errore, OSError, subprocess.CalledProcessError, urllib.error.URLError) as e:
            print("   " + tr("non riuscito: {}", e))
            falliti.append(nome)
    if falliti:
        raise Errore(tr("plugin CLAP non installati: {} (rilancia per riprovare)", ", ".join(falliti)))


def installa_host():
    if SISTEMA == "linux":
        host_linux()
    else:
        host_windows_macos()
    installa_vst3()


# ---------------------------------------------------------------------------
# libreria: il motore SFZ sfizioso compilato
# ---------------------------------------------------------------------------

def visual_studio() -> str:
    """Cartella di Visual Studio (o dei Build Tools) con il compilatore C++, o ''."""
    vswhere = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                   "Microsoft Visual Studio", "Installer", "vswhere.exe")
    if not vswhere.exists():
        return ""
    out = subprocess.run([str(vswhere), "-latest", "-products", "*", "-requires",
                          "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property", "installationPath"],
                         capture_output=True, text=True)
    return out.stdout.strip()


# Strumenti per compilare sfizioso che mancano, e come installarli:
# (descrizione, comando per installarlo da se')
def strumenti_compilazione_mancanti() -> list:
    manca = []
    if SISTEMA == "linux":
        if not shutil.which("git"):
            manca.append(("git", "sudo apt-get install -y git"))
        if not (shutil.which("g++") and shutil.which("make")):
            manca.append((tr("il compilatore C++ e make"), "sudo apt-get install -y build-essential"))
        if not shutil.which("cmake"):
            manca.append(("cmake", "sudo apt-get install -y cmake"))
    elif SISTEMA == "windows":
        if not shutil.which("git") and not _git_windows():
            manca.append(("Git", "winget install --id Git.Git -e"))
        if not visual_studio():
            manca.append((tr("Visual Studio Build Tools con il carico di lavoro C++"),
                          "winget install --id Microsoft.VisualStudio.2022.BuildTools -e --override "
                          "\"--passive --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended\""))
    elif subprocess.run(["xcode-select", "-p"], capture_output=True).returncode != 0:
        # danno anche git e il compilatore; cmake, se manca, arriva da pip (vedi installa_libreria)
        manca.append((tr("gli strumenti da riga di comando di Xcode (git e il compilatore)"), "xcode-select --install"))
    return manca


def _git_windows() -> str:
    """git.exe appena installato con winget: il PATH di questo processo non
    lo sa ancora."""
    for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"),
                 os.environ.get("LOCALAPPDATA") and str(Path(os.environ["LOCALAPPDATA"], "Programs"))):
        if base and Path(base, "Git", "cmd", "git.exe").exists():
            return str(Path(base, "Git", "cmd"))
    return ""


def motivo_installazione_impossibile() -> str:
    """Perche' gli strumenti mancanti non si possono installare da qui, '' se si puo'."""
    if SISTEMA == "linux":
        if not shutil.which("apt-get"):
            return "installali con il gestore di pacchetti del sistema"
        if not amministratore_linux():
            return tr("serve la password di amministratore: dal terminale esegui {} strumenti-compilazione",
                      comando_script())
    elif SISTEMA == "windows" and not shutil.which("winget"):
        return tr("manca winget (App Installer, dal Microsoft Store)")
    return ""


def controlla_strumenti_compilazione():
    manca = strumenti_compilazione_mancanti()
    if manca:
        raise Errore(tr("per compilare sfizioso servono:") + "\n    - "
                     + "\n    - ".join(f"{nome}: {comando}" for nome, comando in manca))


def installa_strumenti_compilazione():
    """Installa quello che manca per compilare sfizioso (vedi
    strumenti_compilazione_mancanti): apt su Linux (una sola password),
    winget su Windows, l'installer di Xcode su macOS."""
    manca = strumenti_compilazione_mancanti()
    if not manca:
        print("== " + tr("strumenti per compilare: gia' presenti"))
        return
    motivo = motivo_installazione_impossibile()
    if motivo:
        raise Errore(tr("non posso installare gli strumenti per compilare: {}", motivo))
    print("== " + tr("Installo gli strumenti per compilare: {}", ", ".join(nome for nome, _c in manca)))
    if SISTEMA == "linux":
        admin = amministratore_linux()
        pacchetti = [c.rsplit(" ", 1)[-1] for _n, c in manca]
        if admin == ["pkexec"]:
            print("   " + tr("la password di amministratore la chiede una finestra del sistema"))
        _esegui(admin + ["sh", "-c", 'apt-get update && apt-get install -y "$@"', "sh"] + pacchetti)
    elif SISTEMA == "windows":
        accordi = ["--accept-source-agreements", "--accept-package-agreements"]
        if any(nome == "Git" for nome, _c in manca):
            _esegui(["winget", "install", "--id", "Git.Git", "-e", *accordi])
            cartella = _git_windows()
            if cartella:
                os.environ["PATH"] = cartella + os.pathsep + os.environ.get("PATH", "")
        if not visual_studio():
            print("   Visual Studio Build Tools: " + tr("qualche GB, puo' volerci piu' di mezz'ora"))
            _esegui(["winget", "install", "--id", "Microsoft.VisualStudio.2022.BuildTools", "-e", *accordi,
                     "--override", "--passive --wait --add Microsoft.VisualStudio.Workload.VCTools "
                     "--includeRecommended"])
    else:
        subprocess.run(["xcode-select", "--install"], check=False)
        print("   " + tr("Conferma l'installazione nella finestra di macOS; aspetto che finisca..."))
        fine = time.monotonic() + 3600
        while subprocess.run(["xcode-select", "-p"], capture_output=True).returncode != 0:
            if time.monotonic() > fine:
                raise Errore(tr("gli strumenti di Xcode non risultano installati dopo un'ora: rilancia quando "
                                "l'installazione e' finita"))
            time.sleep(10)
    rimasti = strumenti_compilazione_mancanti()
    if rimasti:
        raise Errore(tr("mancano ancora: {}", ", ".join(nome for nome, _c in rimasti)))
    print("   " + tr("fatto"))


def libreria_compilata(build: Path) -> Path:
    modelli = {"windows": "**/sfizz*.dll", "macos": "**/libsfizz*.dylib", "linux": "**/libsfizz.so*"}[SISTEMA]
    for path in sorted(build.glob(modelli)):
        if path.is_file() and not path.is_symlink():
            return path
    raise Errore(tr("la libreria compilata non si trova"))


def installa_plugin_nam():
    """Il plugin LV2 Neural Amp Modeler gia' compilato, nella cartella LV2
    dell'utente: SoundText lo usa per calcolare i profili NAM."""
    dest = user_lv2_dir() / NAM_PLUGIN_DIR
    stamp = dest / "soundtext.versione"
    if stamp.exists() and stamp.read_text().strip() == NAM_PLUGIN_VERSION:
        print("== nam-plugin: " + tr("Neural Amp Modeler {} gia' installato in {}, salto", NAM_PLUGIN_VERSION, dest))
        return
    import platform as _platform
    voce = NAM_PLUGIN_FILES.get(SISTEMA)
    if voce is None or _platform.machine().lower() not in ("x86_64", "amd64"):
        print("== nam-plugin: " + tr("non c'e' una versione pronta per questo sistema ({}, {}): SoundText continua "
                                     "a calcolare i profili NAM da se', piu' lentamente", SISTEMA, _platform.machine()))
        return
    nome, sha = voce
    print(f"== nam-plugin: Neural Amp Modeler {NAM_PLUGIN_VERSION} (LV2, GPL-3.0)")
    download = DEST / "_download"
    file = download / nome
    scarica_file(NAM_PLUGIN_BASE + nome, file)
    import hashlib
    digest = hashlib.sha256(file.read_bytes()).hexdigest()
    if digest != sha:
        file.unlink()
        raise Errore(tr("il file scaricato non e' quello atteso (SHA-256 {}...): non lo installo", digest[:12]))
    appoggio = Path(tempfile.mkdtemp(prefix="nam-lv2-"))
    try:
        estrai(file, appoggio)
        trovato = next(appoggio.rglob(NAM_PLUGIN_DIR), None)
        if trovato is None or not trovato.is_dir():
            raise Errore(tr("nell'archivio manca la cartella {}", NAM_PLUGIN_DIR))
        _rimuovi(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(trovato, dest)
    finally:
        _rimuovi(appoggio)
    file.unlink()
    stamp.write_text(NAM_PLUGIN_VERSION + "\n")
    print(f"   -> {dest}")


def architettura() -> str:
    """x86_64 o arm64, come le chiavi di LIBSFIZZ_FILES."""
    macchina = platform.machine().lower()
    return {"amd64": "x86_64", "x64": "x86_64", "aarch64": "arm64"}.get(macchina, macchina)


def libreria_precompilata() -> tuple:
    """(file, SHA-256) della libreria gia' compilata per questo sistema, o
    None se non c'e' (Linux ARM, o release non ancora pubblicata)."""
    voce = LIBSFIZZ_FILES.get((SISTEMA, architettura()))
    return voce if voce and voce[1] else None


def installa_e_prova(src: Path, dest: Path) -> str:
    """Copia la libreria in dest e la prova da li' (si carica, ha
    sfizz_create_synth): '' se va, altrimenti il motivo, e dest si toglie.
    Si prova la copia e non l'originale: su Windows una DLL caricata resta
    bloccata finche' il processo non finisce, e l'originale sta in una
    cartella temporanea da cancellare subito."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    try:
        ctypes.CDLL(str(dest)).sfizz_create_synth
    except (OSError, AttributeError) as e:
        try:
            dest.unlink()
        except OSError:
            pass
        return str(e)
    return ""


def scarica_libreria_precompilata(dest: Path) -> bool:
    """Scarica la libreria gia' compilata in dest (il file LIB_FILE),
    controllando lo SHA-256: True se e' installata e si carica, False se
    per questo sistema non c'e' o non si carica (glibc troppo vecchia...),
    e allora si puo' compilare. Uno SHA-256 diverso ferma tutto (Errore)."""
    voce = libreria_precompilata()
    if voce is None:
        print("   " + tr("non c'e' una versione gia' compilata per questo sistema ({}, {})", SISTEMA, architettura()))
        return False
    nome, sha = voce
    print("== libreria: " + tr("scarico sfizioso {} gia' compilato", SFIZIOSO_COMMIT[:7]))
    appoggio = Path(tempfile.mkdtemp(prefix="libsfizz-"))
    try:
        file = appoggio / nome
        scarica_file(LIBSFIZZ_BASE + nome, file)
        import hashlib
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        if digest != sha:
            raise Errore(tr("il file scaricato non e' quello atteso (SHA-256 {}...): non lo installo", digest[:12]))
        problema = installa_e_prova(file, dest / LIB_FILE)
        if problema:
            print("   " + tr("la libreria gia' compilata non si carica su questo sistema ({})", problema))
            return False
    finally:
        _rimuovi(appoggio)
    return True


def installa_libreria(compila: bool = False, cartella: Path = None):
    """Il motore SFZ interno nella cartella dell'utente: gia' compilato se
    c'e' per questo sistema, altrimenti (o con compila=True) dai sorgenti.
    Con 'cartella' (le build degli installer) solo quello gia' compilato, li'."""
    if cartella is not None:
        if libreria_precompilata() is None:
            print("== libreria: " + tr("non c'e' una versione gia' compilata per questo sistema ({}, {})",
                                       SISTEMA, architettura()))
        elif not scarica_libreria_precompilata(cartella):
            raise Errore(tr("la libreria gia' compilata non si carica su questo sistema"))
        else:
            print(f"   -> {cartella / LIB_FILE}")
        return
    lib_dir = user_lib_dir()
    stamp = lib_dir / "sfizioso.commit"
    if (lib_dir / LIB_FILE).exists() and stamp.exists() and stamp.read_text().strip() == SFIZIOSO_COMMIT:
        print("== libreria: " + tr("sfizioso {} gia' installato in {}, salto", SFIZIOSO_COMMIT[:7], lib_dir))
        return
    if not compila:
        if scarica_libreria_precompilata(lib_dir):
            stamp.write_text(SFIZIOSO_COMMIT + "\n")
            print(f"   -> {lib_dir / LIB_FILE}")
            print("   " + tr("In SoundText: Traccia -> Strumento plugin... -> Strumento SFZ (interno)..."))
            return
        print("   " + tr("la compilo dai sorgenti"))
    compila_libreria(lib_dir, stamp)


def compila_libreria(lib_dir: Path, stamp: Path):
    if strumenti_compilazione_mancanti() and sys.stdin is not None and sys.stdin.isatty() \
            and not motivo_installazione_impossibile():
        nomi = ", ".join(nome for nome, _c in strumenti_compilazione_mancanti())
        if input(tr("Per compilare mancano: {}. Li installo? [s/N] ", nomi)).strip().lower() in ("s", "si", "sí", "y", "yes", "o", "oui"):
            installa_strumenti_compilazione()
    controlla_strumenti_compilazione()
    print("== libreria: " + tr("compilo sfizioso {} (qualche minuto)", SFIZIOSO_COMMIT[:7]))
    tmp = Path(tempfile.mkdtemp(prefix="sfizioso-"))
    try:
        cmake, generatore = shutil.which("cmake"), []
        if not cmake:
            print("   " + tr("cmake non c'e': lo prendo da pip in un ambiente temporaneo"))
            subprocess.run([sys.executable, "-m", "venv", str(tmp / "venv")], check=True)
            bindir = tmp / "venv" / ("Scripts" if SISTEMA == "windows" else "bin")
            pacchetti = ["cmake"] if SISTEMA == "windows" else ["cmake", "ninja"]
            subprocess.run([str(bindir / "python"), "-m", "pip", "install", "-q", *pacchetti], check=True)
            cmake = str(bindir / "cmake")
            if SISTEMA != "windows":
                generatore = ["-G", "Ninja", f"-DCMAKE_MAKE_PROGRAM={bindir / 'ninja'}"]
        src, build = tmp / "src", tmp / "build"
        _esegui(["git", "init", "-q", src])
        _esegui(["git", "-C", src, "remote", "add", "origin", SFIZIOSO_URL])
        _esegui(["git", "-C", src, "fetch", "-q", "--depth", "1", "origin", SFIZIOSO_COMMIT])
        _esegui(["git", "-C", src, "checkout", "-q", "FETCH_HEAD"])
        _esegui(["git", "-C", src, "submodule", "update", "-q", "--init", "--recursive", "--depth", "1"])
        if SISTEMA == "windows":
            generatore = ["-A", "x64"]          # Visual Studio, trovato da cmake
        _esegui([cmake, "-S", src, "-B", build, *generatore, "-DCMAKE_BUILD_TYPE=Release",
                 "-DSFIZZ_JACK=OFF", "-DSFIZZ_RENDER=OFF", "-DSFIZZ_SHARED=ON", "-DENABLE_LTO=OFF"])
        _esegui([cmake, "--build", build, "--config", "Release", "--target", "sfizz_shared",
                 "--parallel", str(os.cpu_count() or 2)])
        problema = installa_e_prova(libreria_compilata(build), lib_dir / LIB_FILE)
        if problema:
            raise Errore(tr("la libreria compilata non si carica: {}", problema))
        stamp.write_text(SFIZIOSO_COMMIT + "\n")
        print(f"   -> {lib_dir / LIB_FILE}")
        print("   " + tr("In SoundText: Traccia -> Strumento plugin... -> Strumento SFZ (interno)..."))
    finally:
        _rimuovi(tmp)


# ---------------------------------------------------------------------------

def main(argv) -> int:
    if not argv:
        if not sys.stdin.isatty():
            elenco()
            return 0
        argv = menu()
        if not argv:
            return 0
    if not programma_7z():
        try:
            import py7zr  # noqa: F401
        except ImportError:
            if not in_flatpak():
                print(tr("Attenzione: manca 7-Zip, servira' per gli strumenti in .7z (esegui prima: {} host)",
                         comando_script()))
    compila = "--compila" in argv
    argv = [arg for arg in argv if arg != "--compila"]
    cartella = None
    if "--in" in argv:
        i = argv.index("--in")
        if i + 1 >= len(argv):
            print(tr("--in vuole una cartella"))
            return 1
        cartella = Path(argv[i + 1])
        del argv[i:i + 2]
    try:
        for arg in argv:
            if arg == "host":
                installa_host()
            elif arg == "vst3":
                installa_vst3()
            elif arg == "libreria":
                installa_libreria(compila=compila, cartella=cartella)
            elif arg == "strumenti-compilazione":
                installa_strumenti_compilazione()
            elif arg == "lv2":
                installa_lv2()
            elif arg == "clap":
                installa_clap()
            elif arg == "clap-con-vst3":
                installa_clap_con_vst3()
            elif arg == "lilv":
                installa_lilv()
            elif arg == "nam-plugin":
                installa_plugin_nam()
            elif arg == "tutto":
                for voce in GRUPPI:
                    scarica(voce)
            elif arg.startswith("extra_"):
                membri = trova_extra(arg)
                if membri is None:
                    print(tr("Gruppo sconosciuto: {}", arg))
                    elenco()
                    return 1
                for m in membri:
                    scarica(trova(m))
            else:
                voce = trova(arg)
                if voce is None:
                    print(tr("Gruppo sconosciuto: {}", arg))
                    elenco()
                    return 1
                scarica(voce)
    except (Errore, subprocess.CalledProcessError) as e:
        print(tr("ERRORE: {}", e))
        return 1
    except KeyboardInterrupt:
        print("\n" + tr("Interrotto: rilancia lo stesso comando per riprendere."))
        return 130
    print("\n" + tr("Fatto. In SoundText: Traccia -> Strumento plugin... -> Strumento SFZ (interno)... e scegli\n"
                    "un file .sfz da {} (serve \"{} libreria\");\n"
                    "oppure sfizz (VST3), poi \"Interfaccia del plugin...\" e carica il file .sfz.",
                    DEST / "sfz", comando_script()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
