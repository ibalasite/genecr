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
#define AppVersion    "0.3.9"
#define AppPublisher  "ibalasite"
#define AppURL        "https://github.com/ibalasite/genecr"
#define ExeName       "genecr-gui.exe"
; --onedir 輸出整個資料夾（含 _internal/）
#define OnedirSource  "..\gui\dist\genecr-gui\*"

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
; 安裝時若舊版 GUI 還在跑、自動關閉（不彈窗問 user）
CloseApplications=force
CloseApplicationsFilter=*.exe
RestartApplications=no

[Languages]
Name: "default"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "建立桌面捷徑"; GroupDescription: "額外捷徑："; Flags: checkedonce

[Files]
; --onedir 產出：genecr-gui.exe + _internal/ 全部進 {app}
Source: "{#OnedirSource}"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs
; 安裝工具包 — 整個 python-embed/ 一起進 {app}\python-embed
Source: "..\gui\dist\python-embed\*"; DestDir: "{app}\python-embed"; \
    Flags: ignoreversion recursesubdirs createallsubdirs
; 協調腳本 — embed python 拿這支跑 pip install 到系統 Python
Source: "install_deps.py"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#ExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#ExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#ExeName}"; Description: "立刻啟動 {#AppName}"; Flags: nowait postinstall skipifsilent

; ─────────────────────────────────────────────────────────────────
; 防呆：installer 啟動前先 taskkill 任何還活著的 genecr-gui.exe
; 這是 CloseApplications=force 的雙重保險（後者靠 Restart Manager，
; 對於沒登記 RM 的 process 不一定攔得到；taskkill 是硬殺）。
; ─────────────────────────────────────────────────────────────────
[Code]
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  // /F 強制、/IM 依 image name 殺；訊息丟掉、不彈窗
  Exec(ExpandConstant('{cmd}'), '/C taskkill /F /IM genecr-gui.exe >nul 2>&1',
       '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := True;
end;
