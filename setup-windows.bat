@echo off
rem Prepara l'ambiente per SoundText portable su Windows. Va lanciato dalla
rem cartella estratta (quella con SoundText.exe).
rem
rem Cosa fa:
rem   - controlla il Microsoft Visual C++ Redistributable (serve a Qt/PySide6)
rem     e, se manca, propone di installarlo con winget;
rem   - controlla Python 3 (serve solo a scarica_strumenti.bat per scaricare
rem     plugin e strumenti gratuiti) e, se manca, propone di installarlo con winget.
rem FluidSynth e il motore audio sono gia' dentro il pacchetto.
rem
rem Uso: setup-windows.bat
setlocal EnableDelayedExpansion

where winget >nul 2>nul
if errorlevel 1 (
    set "WINGET=0"
    echo winget non trovato: le installazioni vanno fatte a mano dai siti ufficiali.
) else (
    set "WINGET=1"
)

echo.
echo [1/2] Visual C++ Redistributable
set "VCOK=0"
reg query "HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" /v Installed 2>nul | find "0x1" >nul && set "VCOK=1"
if "!VCOK!"=="1" (
    echo   gia' installato.
) else (
    echo   non trovato.
    if "!WINGET!"=="1" (
        set /p R="  Lo installo con winget? [s/N] "
        if /i "!R!"=="s" winget install --id Microsoft.VCRedist.2015+.x64 -e --accept-source-agreements --accept-package-agreements
    ) else (
        echo   Scaricalo da https://aka.ms/vs/17/release/vc_redist.x64.exe
    )
)

echo.
echo [2/2] Python 3 (per scarica_strumenti.bat)
set "PYOK=0"
where py >nul 2>nul && set "PYOK=1"
where python >nul 2>nul && set "PYOK=1"
if "!PYOK!"=="1" (
    echo   gia' installato.
) else (
    echo   non trovato.
    if "!WINGET!"=="1" (
        set /p R="  Lo installo con winget? [s/N] "
        if /i "!R!"=="s" winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
    ) else (
        echo   Scaricalo da https://www.python.org/downloads/
    )
)

echo.
echo Pronto. Avvia SoundText.exe; per plugin e strumenti gratuiti usa scarica_strumenti.bat
exit /b 0
