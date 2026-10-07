<#
.SYNOPSIS
    Prepara uno zip con SOLO i file necessari per compilare/lanciare
    SoundText su Linux (build-linux-portable.sh o install.sh), da
    copiare sul PC Linux (es. CachyOS) senza portarsi dietro l'intero
    repository.
.DESCRIPTION
    Il repository e' pesante (quasi 1 GB) soprattutto per i SoundFont
    extra in soundfonts/ (Arachno, ColomboGMGS2, GeneralUser-GS, Timbres
    Of Heaven) che servono solo se li scegli manualmente dentro l'app:
    ne' build-linux-portable.sh ne' install.sh li usano. Questo script
    include solo:
      - main.py, requirements.txt, soundtext.spec
      - build-linux-portable.sh, install.sh
      - core/, gui/, locales/, licenses/, midi/, assets/, docs/ (senza guida_brano), songs/, examples/
      - soundfonts/FluidR3_GM.sf2 (il solo SoundFont di default)
    escludendo __pycache__/*.pyc, tests/, il manuale .docx e la guida PDF,
    le immagini della guida PDF (docs/guida_brano), gli script di
    Windows/macOS e i SoundFont extra.
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File package-for-linux.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Write-Info { param([string]$Msg) Write-Host "==> $Msg" -ForegroundColor Cyan }
function Write-Warn { param([string]$Msg) Write-Host "!! $Msg" -ForegroundColor Yellow }

$FilesToInclude = @(
    "main.py",
    "requirements.txt",
    "soundtext.spec",
    "build-linux-portable.sh",
    "install.sh",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "scarica_strumenti.sh",
    "scarica_strumenti.py",
    "setup-portable-linux.sh"
)
$DirsToInclude = @("core", "gui", "locales", "licenses", "midi", "assets", "docs", "songs", "examples")
$Soundfont = "soundfonts\FluidR3_GM.sf2"

foreach ($f in $FilesToInclude) {
    if (-not (Test-Path (Join-Path $Root $f))) {
        throw "Manca '$f': lancia questo script dalla radice del repository SoundText."
    }
}

$Staging = Join-Path $env:TEMP "soundtext-linux-package"
if (Test-Path $Staging) { Remove-Item -Recurse -Force $Staging }
New-Item -ItemType Directory -Path $Staging | Out-Null

Write-Info "Copio i file necessari..."
foreach ($f in $FilesToInclude) {
    Copy-Item (Join-Path $Root $f) (Join-Path $Staging $f) -Force
}
foreach ($d in $DirsToInclude) {
    $src = Join-Path $Root $d
    if (Test-Path $src) {
        Copy-Item $src (Join-Path $Staging $d) -Recurse -Force
    } else {
        Write-Warn "Cartella '$d' non trovata, saltata."
    }
}

# Le immagini della guida PDF non servono al programma: la guida e' docs\HELP.md.
Remove-Item (Join-Path $Staging "docs\guida_brano") -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $Staging "examples\*.wav") -Force -ErrorAction SilentlyContinue

Write-Info "Rimuovo __pycache__/*.pyc copiati per errore..."
Get-ChildItem $Staging -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force
Get-ChildItem $Staging -Recurse -File -Filter "*.pyc" -ErrorAction SilentlyContinue |
    Remove-Item -Force

$sf2Src = Join-Path $Root $Soundfont
if (Test-Path $sf2Src) {
    Write-Info "Includo solo il SoundFont di default (FluidR3_GM.sf2)..."
    New-Item -ItemType Directory -Path (Join-Path $Staging "soundfonts") -Force | Out-Null
    Copy-Item $sf2Src (Join-Path $Staging $Soundfont) -Force
} else {
    Write-Warn "$Soundfont non trovato: lo zip non avra' un SoundFont incluso."
}

$ZipOut = Join-Path $Root "SoundText-src-for-linux.zip"
if (Test-Path $ZipOut) { Remove-Item $ZipOut -Force }
Write-Info "Comprimo in $ZipOut..."
Compress-Archive -Path (Join-Path $Staging "*") -DestinationPath $ZipOut

Remove-Item -Recurse -Force $Staging

$sizeMB = [math]::Round((Get-Item $ZipOut).Length / 1MB, 1)
Write-Host ""
Write-Info "Fatto: $ZipOut ($sizeMB MB)"
Write-Host "Sul PC Linux: scompatta lo zip, poi dentro la cartella:"
Write-Host "  chmod +x build-linux-portable.sh install.sh"
Write-Host "  ./build-linux-portable.sh    # per il pacchetto portable"
Write-Host "  # oppure"
Write-Host "  ./install.sh                 # per l'installazione con dipendenze di sistema"
