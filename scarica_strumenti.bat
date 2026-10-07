@echo off
rem Scarica e installa strumenti virtuali gratuiti (SFZ) per SoundText: il lavoro
rem lo fa scarica_strumenti.py (serve Python 3.8+), lo stesso su Linux, Windows e macOS.
rem Uso: scarica_strumenti.bat [host ^| libreria ^| tutto ^| gruppi...]  (senza argomenti: elenco)
setlocal
set "QUI=%~dp0"
where py >nul 2>nul && ( py -3 "%QUI%scarica_strumenti.py" %* & exit /b )
where python >nul 2>nul && ( python "%QUI%scarica_strumenti.py" %* & exit /b )
echo ERRORE: Python 3 non trovato. Installalo da https://www.python.org/downloads/ e rilancia.
exit /b 1
