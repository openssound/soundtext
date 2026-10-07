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
#define AppVersion "1.6.0"
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

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
