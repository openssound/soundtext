<#
.SYNOPSIS
    Crea una build PORTABLE di SoundText per Windows (SoundText.exe + dati),
    pronta da distribuire come zip: chi la riceve scompatta e lancia
    l'eseguibile, senza installare Python, pip o altro.
.DESCRIPTION
    Va eseguito DENTRO una copia completa del repository SoundText (serve
    main.py, requirements.txt, soundtext.spec, core/, gui/, midi/, assets/,
    docs/, songs/, examples/, soundfonts/) su un PC/VM Windows, perche'
    PyInstaller compila per la piattaforma su cui gira.

    Passi:
      1. crea un virtualenv di build temporaneo (.build-venv, separato da
         quello eventualmente creato da install.ps1) e ci installa i
         pacchetti da requirements.txt + PyInstaller;
      2. verifica che ci sia assets\soundtext.ico (versionato, generato
         da assets\icon.svg con generate_icons.py) per l'icona dell'eseguibile;
      3. lancia PyInstaller con soundtext.spec (modalita' onedir);
      4. affianca a SoundText.exe le cartelle dati dell'app (assets, docs,
         songs demo, libreria midi, esempi) e, se presente, il SoundFont GM
         incluso nel repository (soundfonts\FluidR3_GM.sf2);
      5. scarica (con conferma) le DLL di FluidSynth dai release ufficiali
         GitHub e le affianca a SoundText.exe: Windows le trova da li'
         tramite l'ordine di ricerca DLL standard, senza toccare il PATH
         di sistema;
      6. comprime tutto in SoundText-portable-win64.zip nella cartella
         corrente.
.PARAMETER Yes
    Non chiede conferma prima del download di FluidSynth.
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File build-windows-portable.ps1
#>
[CmdletBinding()]
param([switch]$Yes)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Write-Info { param([string]$Msg) Write-Host "==> $Msg" -ForegroundColor Cyan }
function Write-Warn { param([string]$Msg) Write-Host "!! $Msg" -ForegroundColor Yellow }

function Confirm-Action {
    param([string]$Prompt)
    if ($Yes) { return $true }
    $reply = Read-Host "$Prompt [s/N]"
    return ($reply -match "^[sSyY]")
}

function Find-Python {
    foreach ($cmd in @("python", "py")) {
        if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { continue }
        try { $verOut = & $cmd --version 2>&1 } catch { continue }
        if ($verOut -match "Python (\d+)\.(\d+)") {
            if ([int]$Matches[1] -eq 3 -and [int]$Matches[2] -ge 10) { return $cmd }
        }
    }
    return $null
}

foreach ($required in @("main.py", "requirements.txt", "soundtext.spec")) {
    if (-not (Test-Path (Join-Path $Root $required))) {
        throw "Manca '$required': lancia questo script dalla radice di una copia completa del repository SoundText, non da una copia parziale."
    }
}

$pythonCmd = Find-Python
if (-not $pythonCmd) {
    throw "Python 3.10+ non trovato nel PATH (serve solo per compilare la build, non per chi ricevera' lo zip). Installalo da python.org."
}
Write-Info "Uso '$pythonCmd' ($(& $pythonCmd --version)) per la build."

$BuildVenv = Join-Path $Root ".build-venv"
if (-not (Test-Path $BuildVenv)) {
    Write-Info "Creo il virtualenv di build in $BuildVenv..."
    & $pythonCmd -m venv $BuildVenv
    if ($LASTEXITCODE -ne 0) { throw "Creazione del virtualenv di build fallita." }
} else {
    Write-Info "Virtualenv di build gia' presente, lo riuso."
}
$venvPython = Join-Path $BuildVenv "Scripts\python.exe"
$venvPip = Join-Path $BuildVenv "Scripts\pip.exe"

Write-Info "Installo le dipendenze dell'app e PyInstaller..."
& $venvPython -m pip install --upgrade pip wheel | Out-Null
& $venvPip install -r (Join-Path $Root "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Installazione dei pacchetti dell'app fallita." }
& $venvPip install pyinstaller pyinstaller-hooks-contrib
if ($LASTEXITCODE -ne 0) { throw "Installazione di PyInstaller fallita." }

# assets\soundtext.ico e' versionato (multi-dimensione, generato da
# assets\icon.svg con generate_icons.py): nessuna conversione qui.
if (-not (Test-Path (Join-Path $Root "assets\soundtext.ico"))) {
    throw "Manca assets\soundtext.ico: rigeneralo con 'python generate_icons.py'."
}

Write-Info "Eseguo PyInstaller (prima volta: puo' richiedere diversi minuti)..."
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $Root "build"), (Join-Path $Root "dist")
& $venvPython -m PyInstaller (Join-Path $Root "soundtext.spec") --noconfirm
if ($LASTEXITCODE -ne 0) { throw "PyInstaller ha fallito: guarda l'errore sopra." }

$DistDir = Join-Path $Root "dist\SoundText"
if (-not (Test-Path (Join-Path $DistDir "SoundText.exe"))) {
    throw "PyInstaller non ha prodotto SoundText.exe in $DistDir."
}

Write-Info "Affianco a SoundText.exe le cartelle dati dell'app..."
foreach ($dir in @("assets", "docs", "locales", "songs", "examples", "midi", "licenses")) {
    # midi\: solo la cartella, vuota (la libreria MIDI e' dell'utente: le
    # sottocartelle e il file d'esempio del repository non si distribuiscono)
    if ($dir -eq "midi") {
        New-Item -ItemType Directory -Force -Path (Join-Path $DistDir "midi") | Out-Null
        continue
    }
    $srcPath = Join-Path $Root $dir
    if (Test-Path $srcPath) {
        Copy-Item $srcPath (Join-Path $DistDir $dir) -Recurse -Force
    }
}
# Le immagini della guida PDF (e i suoi script) non servono al programma: la
# guida utente e' docs\HELP.md. Il manuale Word e il PDF, nella radice, non
# vengono copiati affatto.
Remove-Item (Join-Path $DistDir "docs\guida_brano") -Recurse -Force -ErrorAction SilentlyContinue
# Gli esempi si distribuiscono come .st: i render audio (.wav) restano fuori.
Remove-Item (Join-Path $DistDir "examples\*.wav") -Force -ErrorAction SilentlyContinue
# Licenza (GPL-3.0) e avvisi delle librerie di terze parti: vanno sempre
# distribuiti con il programma (vedi THIRD_PARTY_NOTICES.md).
foreach ($file in @("LICENSE", "THIRD_PARTY_NOTICES.md", "scarica_strumenti.py", "scarica_strumenti.bat", "setup-windows.bat")) {
    Copy-Item (Join-Path $Root $file) $DistDir -Force
}
# Dati di Verovio (caratteri musicali della vista Partitura) accanto
# all'eseguibile, in verovio-data (vedi core.score_render): cosi' non
# dipende da cosa PyInstaller ha incluso del pacchetto.
$verovioData = & $venvPython -c "import os, verovio; print(os.path.join(os.path.dirname(verovio.__file__), 'data'))"
if ($LASTEXITCODE -eq 0 -and $verovioData -and (Test-Path $verovioData)) {
    Copy-Item $verovioData (Join-Path $DistDir "verovio-data") -Recurse -Force
} else {
    Write-Warning "Verovio non trovato: la build non avra' la vista Partitura."
}

$sf2Src = Join-Path $Root "soundfonts\FluidR3_GM.sf2"
if (Test-Path $sf2Src) {
    Write-Info "Includo il SoundFont GM (FluidR3_GM.sf2)..."
    New-Item -ItemType Directory -Force -Path (Join-Path $DistDir "soundfonts") | Out-Null
    Copy-Item $sf2Src (Join-Path $DistDir "soundfonts\FluidR3_GM.sf2") -Force
} else {
    Write-Warn "soundfonts\FluidR3_GM.sf2 non trovato nel repository: la build non avra' un SoundFont incluso."
}

# --- FluidSynth: le DLL vanno affiancate a SoundText.exe. La cartella
# dell'eseguibile e' nell'ordine di ricerca DLL standard di Windows, quindi
# non serve toccare il PATH di sistema come fa install.ps1. ---
$FluidCache = Join-Path $Root ".build-fluidsynth"
$fluidDll = $null
if (Test-Path $FluidCache) {
    $fluidDll = Get-ChildItem $FluidCache -Recurse -Filter "libfluidsynth*.dll" -ErrorAction SilentlyContinue | Select-Object -First 1
}
if (-not $fluidDll) {
    if (Confirm-Action "Scarico FluidSynth (motore audio) dai release ufficiali GitHub per includerlo nella build?") {
        Write-Info "Cerco l'ultima release di FluidSynth su GitHub..."
        try {
            $release = Invoke-RestMethod "https://api.github.com/repos/FluidSynth/fluidsynth/releases/latest"
            $asset = $release.assets | Where-Object { $_.name -match "win10-x64.*\.zip$" } | Select-Object -First 1
        } catch {
            Write-Warn "Impossibile contattare GitHub ($($_.Exception.Message))."
            $asset = $null
        }
        if ($asset) {
            $zipPath = Join-Path $env:TEMP $asset.name
            Write-Info "Scarico $($asset.name) ($([math]::Round($asset.size / 1MB, 1)) MB)..."
            Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zipPath
            if (Test-Path $FluidCache) { Remove-Item $FluidCache -Recurse -Force }
            Expand-Archive -Path $zipPath -DestinationPath $FluidCache -Force
            Remove-Item $zipPath
            $fluidDll = Get-ChildItem $FluidCache -Recurse -Filter "libfluidsynth*.dll" -ErrorAction SilentlyContinue | Select-Object -First 1
        } else {
            Write-Warn "Nessun asset win10-x64 trovato nell'ultima release di FluidSynth."
        }
    }
} else {
    Write-Info "Riuso FluidSynth gia' scaricato in $FluidCache."
}
if ($fluidDll) {
    Write-Info "Includo le DLL di FluidSynth da $($fluidDll.Directory.FullName)..."
    Copy-Item (Join-Path $fluidDll.Directory.FullName "*.dll") $DistDir -Force
    $fluidExe = Join-Path $fluidDll.Directory.FullName "fluidsynth.exe"
    if (Test-Path $fluidExe) { Copy-Item $fluidExe $DistDir -Force }
} else {
    Write-Warn "FluidSynth non incluso: la build compilata non produrra' audio finche' non aggiungi"
    Write-Warn "manualmente le DLL di FluidSynth nella cartella di SoundText.exe."
}

Write-Info "Comprimo in SoundText-portable-win64.zip..."
$zipOut = Join-Path $Root "SoundText-portable-win64.zip"
Remove-Item -ErrorAction SilentlyContinue $zipOut
Compress-Archive -Path $DistDir -DestinationPath $zipOut

Write-Host ""
Write-Info "Fatto: $zipOut"
Write-Host "Chi lo riceve deve solo scompattare lo zip e lanciare SoundText.exe: nessun Python, pip o installazione richiesti."
