; Script Inno Setup per generare un vero installer .exe di SoundText per
; Windows (SoundText-setup-win64.exe): a differenza dello zip portable
; prodotto da build-windows-portable.ps1, questo installa l'app in
; Program Files, crea le voci nel menu Start e un icona sul Desktop
; (opzionale), e registra un disinstallatore in "App e funzionalita'".
;
; Prerequisito: build-windows-portable.ps1 deve essere gia' stato eseguito
; con successo, cosi' che dist\SoundText contenga SoundText.exe completo
; di tutte le cartelle dati e le DLL di FluidSynth.
;
; Uso:
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer-windows.iss

#define AppName "SoundText"
#define AppVersion "1.6.7"
#define AppPublisher "SoundText"
#define AppExeName "SoundText.exe"
#define DistDir "dist\SoundText"

[Setup]
AppId={{9E7B0B2E-6C7B-4E9C-9C2A-6C6E9F6A9C3A}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=.
OutputBaseFilename=SoundText-setup-win64
SetupIconFile=assets\soundtext.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
; la licenza (GPL-3.0) mostrata durante l'installazione
LicenseFile=LICENSE

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[CustomMessages]
italian.CompleteSetup=Completa installazione
english.CompleteSetup=Complete setup
italian.DownloadInstruments=Scarica strumenti
english.DownloadInstruments=Download instruments
italian.Examples=Esempi
english.Examples=Examples
italian.License=Licenza
english.License=License
italian.RunCompleteSetup=Completa l'installazione (controlla Visual C++ Redistributable e Python)
english.RunCompleteSetup=Complete the setup (checks Visual C++ Redistributable and Python)

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
; In Program Files i .bat, gli esempi e la licenza non si vedono: dal menu
; Start si raggiungono senza cercare la cartella d'installazione.
; Con cmd /k la finestra resta aperta: setup-windows.bat finisce con exit /b
; e si legge il riepilogo; scarica_strumenti.bat senza argomenti mostra il
; menu dei gruppi, e a fine download si vede l'esito.
Name: "{group}\{cm:CompleteSetup}"; Filename: "{cmd}"; Parameters: "/k setup-windows.bat"; WorkingDir: "{app}"; IconFilename: "{app}\{#AppExeName}"
Name: "{group}\{cm:DownloadInstruments}"; Filename: "{cmd}"; Parameters: "/k scarica_strumenti.bat"; WorkingDir: "{app}"; IconFilename: "{app}\{#AppExeName}"
Name: "{group}\{cm:Examples}"; Filename: "{app}\examples"
; LICENSE non ha estensione: Windows non saprebbe con cosa aprirlo
Name: "{group}\{cm:License}"; Filename: "{win}\notepad.exe"; Parameters: """{app}\LICENSE"""
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Casella spuntata nell'ultima pagina: setup-windows.bat in una finestra che
; resta aperta (cmd /k). nowait, perche' la finestra si chiude solo a mano e
; non deve bloccare la fine dell'installer ne' l'avvio di SoundText.
Filename: "{cmd}"; Parameters: "/k setup-windows.bat"; WorkingDir: "{app}"; Description: "{cm:RunCompleteSetup}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
