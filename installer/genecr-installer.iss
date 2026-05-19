; genecr-installer.iss — Inno Setup 6 script
;
; Builds: installer/dist/genecr-installer-{version}.exe
; Bundles: gui/dist/genecr-gui.exe + gui/dist/python-embed/ （安裝工具包）
;          兩者皆由 `python installer/build.py` 一鍵產出
;
; Output is a single-file Windows installer that:
;  - Installs to %LOCALAPPDATA%\Programs\genecr (no admin needed)
;  - Creates Start menu + Desktop shortcuts
;  - Registers in Apps & Features (uninstall via Settings)
;
; Build:  python installer\build.py

#define AppName       "genecr"
#define AppVersion    "0.3.2"
#define AppPublisher  "ibalasite"
#define AppURL        "https://github.com/ibalasite/genecr"
#define ExeName       "genecr-gui.exe"
#define ExeSource     "..\gui\dist\genecr-gui.exe"

[Setup]
AppId={{B6A3F1C2-9E4D-4B7A-9F0E-3C8D1A5B7E29}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=dist
OutputBaseFilename=genecr-installer-{#AppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#ExeName}
UninstallDisplayName={#AppName} {#AppVersion}

[Languages]
Name: "default"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "建立桌面捷徑"; GroupDescription: "額外捷徑："; Flags: checkedonce

[Files]
Source: "{#ExeSource}"; DestDir: "{app}"; Flags: ignoreversion
; 安裝工具包 — 整個 python-embed/ 一起進 {app}\python-embed
Source: "..\gui\dist\python-embed\*"; DestDir: "{app}\python-embed"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#ExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#ExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#ExeName}"; Description: "立刻啟動 {#AppName}"; Flags: nowait postinstall skipifsilent
