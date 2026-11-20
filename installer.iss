; =====================================================================
; PyClean Pro v2.3 - Script de Instalador Oficial de Windows (Inno Setup)
; Genera el instalador estándar de Windows: PyCleanPro-Setup.exe
; =====================================================================

#define MyAppName "PyClean Pro"
#define MyAppVersion "2.7.0"
#define MyAppPublisher "chemkes1999"
#define MyAppURL "https://github.com/chemkes1999/cleanerpc"
#define MyAppExeName "PyCleanPro.exe"

[Setup]
AppId={{8A329731-C684-48FE-95C4-749B0F1C9901}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
VersionInfoVersion=2.7.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Instalador oficial de {#MyAppName}
VersionInfoProductName={#MyAppName}
VersionInfoCopyright=Copyright (c) 2026 {#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=PyCleanPro-Setup
SetupIconFile=assets\pyclean_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Binario principal compilado por PyInstaller
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; Archivo README de instrucciones
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
