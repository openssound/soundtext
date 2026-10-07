#!/usr/bin/env python3
"""
Scarica e installa strumenti virtuali gratuiti (SFZ) e quello che serve per
suonarli in SoundText, su Linux, Windows e macOS. Basta Python 3.8+, senza
pacchetti in piu'.

Uso (su Windows "py" al posto di "python3"; su Linux anche ./scarica_strumenti.sh):
    python3 scarica_strumenti.py                  elenca i gruppi
    python3 scarica_strumenti.py host             7-Zip, sfizz e Surge XT
    python3 scarica_strumenti.py libreria         compila il motore SFZ sfizioso per lo
                                                  strumento SFZ interno (~5 min)
    python3 scarica_strumenti.py piano basso      scarica i gruppi indicati
    python3 scarica_strumenti.py tutto            tutti i gruppi (esclusi gli extra)
    python3 scarica_strumenti.py extra_basso      extra: extra_basso, extra_piano,
                                                  extra_etnici, extra_batterie

Gli strumenti vanno in ~/Strumenti (o nella cartella della variabile
STRUMENTI_DIR). I download si riprendono se interrotti e i gruppi gia'
presenti vengono saltati.
"""

import ctypes
import json
import os
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


def user_lib_dir() -> Path:
    if SISTEMA == "windows":
        return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "SoundText" / "lib"
    if SISTEMA == "macos":
        return Path.home() / "Library" / "Application Support" / "SoundText" / "lib"
    return Path.home() / ".local" / "lib" / "soundtext"


# Cartella VST3 dell'utente (non servono i diritti di amministratore)
def user_vst3_dir() -> Path:
    if SISTEMA == "windows":
        return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "Programs" / "Common" / "VST3"
    if SISTEMA == "macos":
        return Path.home() / "Library" / "Audio" / "Plug-Ins" / "VST3"
    return Path.home() / ".vst3"


# gruppo, descrizione, URL, cartella di destinazione
GRUPPI = [
    ("piano", "Piano a coda Salamander (SFZ+FLAC, ~740 MB)", f"{FREEPATS}/Piano/SalamanderGrandPiano/SalamanderGrandPiano-SFZ+FLAC-V3+20200602.tar.gz", "sfz"),
    ("upright", "Piano verticale piccolo (SFZ+FLAC, ~3 MB)", f"{FREEPATS}/Piano/UprightPianoKW/UprightPianoKW-small-SFZ+FLAC-20190703.7z", "sfz"),
    ("epiano", "Piano elettrico FM (SFZ+FLAC, ~25 MB)", "https://github.com/freepats/fm-piano1/releases/download/2019-09-16/FM-Piano1-SFZ+FLAC-20190916.7z", "sfz"),
    ("chitarra", "Chitarra classica spagnola (SFZ+FLAC, ~5 MB)", f"{FREEPATS}/Guitar/SpanishClassicalGuitar/SpanishClassicalGuitar-SFZ+FLAC-20190618.7z", "sfz"),
    ("chitarra-elettrica", "Chitarra elettrica pulita FreePats (SFZ+FLAC, ~125 MB)", "https://github.com/freepats/electric-guitar-FSBS-clean/releases/download/2026-08-07/EGuitarFSBS-clean-SFZ+FLAC-20260807.7z", "sfz"),
    ("chitarra-dist", "Chitarra elettrica distorta FreePats (SFZ+FLAC, ~315 MB)", "https://github.com/freepats/electric-guitar-FSBS-dist1/releases/download/2022-09-11/EGuitarFSBS-dist1-SFZ+FLAC-20220911.7z", "sfz"),
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
    ("gm-bank", "Banco General MIDI completo in SFZ, Discord SFZ GM Bank (~180 MB, tutti i 128 strumenti)", "https://github.com/sfzinstruments/Discord-SFZ-GM-Bank.git", "sfz"),
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
    ("extra_etnici", "~1,1 GB", "erhu cithara banjo squidpipes zither ganjo horsepulse war-tuba bear-sax"),
    ("extra_batterie", "~5,5 GB", "virtuosity-drums unruly-drums swirly-drums big-rusty-drums naked-drums sonor-drums hat-phat frankensnare"),
]


class Errore(Exception):
    pass


def comando_script() -> str:
    if SISTEMA == "windows":
        return "py scarica_strumenti.py"
    if SISTEMA == "linux":
        return "./scarica_strumenti.sh"
    return "python3 scarica_strumenti.py"


def elenco():
    print(f"Gruppi disponibili (destinazione: {DEST}):")
    for nome, desc, _url, _sotto in GRUPPI + EXTRA:
        print(f"  {nome:<14} {desc}")
    for nome, spazio, membri in EXTRA_GRUPPI:
        print(f"  {nome:<14} (extra, {spazio}) {membri}")
    host = {"linux": "7zip + sfizz + Surge XT Nightly (apt, serve sudo)",
            "windows": "7-Zip (winget), Surge XT con i suoi dati (~300 MB) per l'utente, installer di sfizz",
            "macos": "7-Zip (Homebrew), Surge XT con i suoi dati (~440 MB) per l'utente, installer di sfizz"}[SISTEMA]
    print(f"  {'host':<14} {host}")
    print(f"  {'libreria':<14} motore SFZ sfizioso per lo strumento SFZ interno (compilato, ~5 min)")
    print(f"  {'tutto':<14} tutti i gruppi SFZ (esclusi gli extra_*)")


def trova(nome: str):
    for voce in GRUPPI + EXTRA:
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


def scarica_file(url: str, dest: Path, tentativi: int = 3):
    """Scarica url in dest riprendendo un download interrotto."""
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
                        if time.monotonic() - ultimo > 1:
                            ultimo = time.monotonic()
                            perc = f" {fatto * 100 // totale}%" if totale else ""
                            print(f"\r   {fatto / 1e6:.0f} MB{perc}   ", end="", flush=True)
                print(f"\r   {fatto / 1e6:.0f} MB scaricati      ")
                return
        except urllib.error.HTTPError as e:
            if e.code == 416 and gia:          # gia' completo
                return
            errore = e
        except (urllib.error.URLError, OSError) as e:
            errore = e
        print(f"\n   errore ({errore}), tentativo {tentativo} di {tentativi}")
        time.sleep(2 * tentativo)
    raise Errore(f"download non riuscito: {url}")


def _dentro(base: Path, nome: str) -> bool:
    try:
        (base / nome).resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


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
                    raise Errore(f"percorso non valido nell'archivio: {membro}")
            z.extractall(cartella)
    elif re.search(r"\.(tar\.(gz|xz|bz2)|tgz)$", nome):
        with tarfile.open(file) as t:
            if hasattr(tarfile, "data_filter"):
                t.extractall(cartella, filter="data")
            else:
                for membro in t.getmembers():
                    if not _dentro(cartella, membro.name) or membro.issym() or membro.islnk():
                        raise Errore(f"percorso non valido nell'archivio: {membro.name}")
                t.extractall(cartella)
    elif nome.endswith(".7z"):
        sette = programma_7z()
        if sette:
            subprocess.run([sette, "x", "-y", f"-o{cartella}", str(file)], check=True, stdout=subprocess.DEVNULL)
            return
        try:
            import py7zr
        except ImportError:
            raise Errore(f"per estrarre {file.name} serve 7-Zip (esegui prima: {comando_script()} host) "
                         "oppure il pacchetto Python py7zr (pip install py7zr)")
        with py7zr.SevenZipFile(file) as z:
            z.extractall(cartella)
    else:
        raise Errore(f"formato sconosciuto: {file.name}")


def archivio_github(url_git: str) -> str:
    """https://github.com/a/b.git -> l'archivio .zip del ramo principale."""
    return re.sub(r"\.git$", "", url_git) + "/archive/HEAD.zip"


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
        print(f"== {nome}: gia' presente, salto")
        return
    print(f"== {nome}: {desc}")
    download = DEST / "_download"
    if url.endswith(".git"):
        _rimuovi(cartella)
        if shutil.which("git"):
            cartella.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "clone", "--depth", "1", url, str(cartella)], check=True)
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


def asset_github(repo: str, release: str, modello: str) -> str:
    """URL del primo file della release (latest o un tag) che corrisponde al modello."""
    api = f"https://api.github.com/repos/{repo}/releases/" + ("latest" if release == "latest" else f"tags/{release}")
    with urllib.request.urlopen(_richiesta(api, Accept="application/vnd.github+json"), timeout=60) as resp:
        dati = json.load(resp)
    for asset in dati.get("assets", []):
        if re.fullmatch(modello, asset["name"]):
            return asset["browser_download_url"]
    raise Errore(f"nessun file {modello} nella release {release} di {repo}")


def copia_vst3(radice: Path, dest: Path):
    """Copia ogni bundle .vst3 trovato sotto radice nella cartella dest."""
    dest.mkdir(parents=True, exist_ok=True)
    trovati = 0
    for root, dirs, files in os.walk(radice):
        for nome in list(dirs) + files:
            if nome.lower().endswith(".vst3"):
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
    if not trovati:
        raise Errore("nessun plugin VST3 nell'archivio")


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


def host_linux():
    _esegui(["sudo", "apt-get", "update"])
    print("== Installo 7zip")
    _esegui(["sudo", "apt-get", "install", "-y", "7zip"])
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        # leggibile dall'utente _apt, altrimenti apt avvisa che scarica fuori dalla sandbox
        tmp.chmod(0o755)
        if subprocess.run(["dpkg", "-s", "surge-xt"], capture_output=True).returncode != 0:
            print("== Installo Surge XT (sintetizzatore VST3/LV2, Nightly dal GitHub ufficiale)")
            url = asset_github("surge-synthesizer/surge", "Nightly", r"surge-xt-linux-x64-NIGHTLY-.*\.deb")
            scarica_file(url, tmp / "surge-xt.deb")
            _esegui(["sudo", "apt-get", "install", "-y", tmp / "surge-xt.deb"])
        if subprocess.run(["dpkg", "-s", "sfizz"], capture_output=True).returncode != 0:
            print("== Installo sfizz (player SFZ per Ubuntu 24.04)")
            base = "https://download.opensuse.org/repositories/home:/sfztools:/sfizz/xUbuntu_24.04/amd64"
            scarica_file(f"{base}/libsfizz1_1.2.3-0_amd64.deb", tmp / "libsfizz1.deb")
            scarica_file(f"{base}/sfizz_1.2.3-0_amd64.deb", tmp / "sfizz.deb")
            _esegui(["sudo", "apt-get", "install", "-y", tmp / "libsfizz1.deb", tmp / "sfizz.deb"])


def host_windows_macos():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        print("== 7-Zip (per gli strumenti in .7z)")
        if programma_7z():
            print("   gia' presente")
        elif SISTEMA == "windows" and shutil.which("winget"):
            _esegui(["winget", "install", "--id", "7zip.7zip", "-e", "--accept-source-agreements"])
        elif SISTEMA == "macos" and shutil.which("brew"):
            _esegui(["brew", "install", "sevenzip"])
        else:
            print("   installalo da https://www.7-zip.org (oppure: pip install py7zr)")
        print("== Surge XT (sintetizzatore VST3), nella cartella VST3 dell'utente")
        modello = (r"surge-xt-win64-[\d.]+-pluginsonly\.zip" if SISTEMA == "windows"
                   else r"surge-xt-macos-[\d.]+-pluginsonly\.zip")
        scarica_file(asset_github("surge-synthesizer/releases-xt", "latest", modello), tmp / "surge.zip")
        estrai(tmp / "surge.zip", tmp / "surge")
        copia_vst3(tmp / "surge", user_vst3_dir())
        print("== Dati di fabbrica di Surge XT (preset, wavetable)")
        scarica_file(asset_github("surge-synthesizer/releases-xt", "latest",
                                  r"surge-xt-portable-content-[\d.]+\.tar\.gz"), tmp / "surge-dati.tar.gz")
        estrai(tmp / "surge-dati.tar.gz", tmp / "surge-dati")
        installa_dati_surge(next((tmp / "surge-dati").rglob("SurgeXTData")))
        print("== sfizz (player SFZ, VST3): avvio il suo installer")
        if SISTEMA == "windows":
            scarica_file(asset_github("sfztools/sfizz-ui", "latest", r"sfizz-[\d.]+-win64\.exe"), tmp / "sfizz.exe")
            # Start-Process fa comparire la richiesta dei diritti di amministratore (subprocess no)
            _esegui(["powershell", "-NoProfile", "-Command",
                     f"Start-Process -Wait -FilePath '{tmp / 'sfizz.exe'}'"])
        else:
            pkg = Path.home() / "Downloads" / "sfizz-macos.pkg"
            scarica_file(asset_github("sfztools/sfizz-ui", "latest", r"sfizz-[\d.]+-macos\.pkg"), pkg)
            _esegui(["open", "-W", pkg])


def installa_host():
    if SISTEMA == "linux":
        host_linux()
    else:
        host_windows_macos()


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


def controlla_strumenti_compilazione():
    manca = []
    if not shutil.which("git"):
        manca.append({"windows": "Git: winget install --id Git.Git -e",
                      "macos": "git: xcode-select --install",
                      "linux": "git: sudo apt-get install -y git"}[SISTEMA])
    if SISTEMA == "windows" and not visual_studio():
        manca.append("Visual Studio Build Tools con il carico di lavoro C++:\n"
                     "      winget install --id Microsoft.VisualStudio.2022.BuildTools -e --override "
                     "\"--passive --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended\"")
    if SISTEMA == "macos" and subprocess.run(["xcode-select", "-p"], capture_output=True).returncode != 0:
        manca.append("gli strumenti da riga di comando di Xcode: xcode-select --install")
    if SISTEMA == "linux" and not (shutil.which("g++") and shutil.which("make")):
        manca.append("il compilatore C++ e make: sudo apt-get install -y build-essential")
    if SISTEMA == "linux" and not shutil.which("cmake"):
        # da pip servirebbe python3-venv, che su Debian/Ubuntu spesso manca
        manca.append("cmake: sudo apt-get install -y cmake")
    if manca:
        raise Errore("per compilare sfizioso servono:\n    - " + "\n    - ".join(manca))


def libreria_compilata(build: Path) -> Path:
    modelli = {"windows": "**/sfizz*.dll", "macos": "**/libsfizz*.dylib", "linux": "**/libsfizz.so*"}[SISTEMA]
    for path in sorted(build.glob(modelli)):
        if path.is_file() and not path.is_symlink():
            return path
    raise Errore("la libreria compilata non si trova")


def installa_libreria():
    lib_dir = user_lib_dir()
    stamp = lib_dir / "sfizioso.commit"
    if (lib_dir / LIB_FILE).exists() and stamp.exists() and stamp.read_text().strip() == SFIZIOSO_COMMIT:
        print(f"== libreria: sfizioso {SFIZIOSO_COMMIT[:7]} gia' installato in {lib_dir}, salto")
        return
    controlla_strumenti_compilazione()
    print(f"== libreria: compilo sfizioso {SFIZIOSO_COMMIT[:7]} (qualche minuto)")
    tmp = Path(tempfile.mkdtemp(prefix="sfizioso-"))
    try:
        cmake, generatore = shutil.which("cmake"), []
        if not cmake:
            print("   cmake non c'e': lo prendo da pip in un ambiente temporaneo")
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
        lib = libreria_compilata(build)
        try:
            ctypes.CDLL(str(lib)).sfizz_create_synth
        except (OSError, AttributeError) as e:
            raise Errore(f"la libreria compilata non si carica: {e}")
        lib_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(lib, lib_dir / LIB_FILE)
        stamp.write_text(SFIZIOSO_COMMIT + "\n")
        print(f"   -> {lib_dir / LIB_FILE}")
        print("   In SoundText: Traccia -> Strumento plugin... -> Strumento SFZ (interno)...")
    finally:
        _rimuovi(tmp)


# ---------------------------------------------------------------------------

def main(argv) -> int:
    if not argv:
        elenco()
        return 0
    if not programma_7z():
        try:
            import py7zr  # noqa: F401
        except ImportError:
            print(f"Attenzione: manca 7-Zip, servira' per gli strumenti in .7z (esegui prima: {comando_script()} host)")
    try:
        for arg in argv:
            if arg == "host":
                installa_host()
            elif arg == "libreria":
                installa_libreria()
            elif arg == "tutto":
                for voce in GRUPPI:
                    scarica(voce)
            elif arg.startswith("extra_"):
                membri = trova_extra(arg)
                if membri is None:
                    print(f"Gruppo sconosciuto: {arg}")
                    elenco()
                    return 1
                for m in membri:
                    scarica(trova(m))
            else:
                voce = trova(arg)
                if voce is None:
                    print(f"Gruppo sconosciuto: {arg}")
                    elenco()
                    return 1
                scarica(voce)
    except (Errore, subprocess.CalledProcessError) as e:
        print(f"ERRORE: {e}")
        return 1
    except KeyboardInterrupt:
        print("\nInterrotto: rilancia lo stesso comando per riprendere.")
        return 130
    print(f"""
Fatto. In SoundText: Traccia -> Strumento plugin... -> Strumento SFZ (interno)... e scegli
un file .sfz da {DEST / 'sfz'} (serve "{comando_script()} libreria");
oppure sfizz (VST3), poi "Interfaccia del plugin..." e carica il file .sfz.""")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
