# installer/build-installer.ps1 — build genecr-installer-X.Y.Z.exe via Inno Setup
#
# Output: installer/dist/genecr-installer-{version}.exe
#
# Pipeline:
#   1. Ensure gui/dist/genecr-gui.exe exists (or build it)
#   2. Ensure ISCC.exe (Inno Setup compiler) available — install via winget if missing
#   3. Compile installer/genecr-installer.iss
#
# Usage:  .\installer\build-installer.ps1

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Split-Path -Parent $scriptDir
$guiExe    = Join-Path $repoRoot "gui\dist\genecr-gui.exe"
$iss       = Join-Path $scriptDir "genecr-installer.iss"

# ── 1. Ensure GUI exe exists ──────────────────────────────────
if (-not (Test-Path $guiExe)) {
    Write-Host "[build] gui/dist/genecr-gui.exe 不存在，先 build…" -ForegroundColor Yellow
    & (Join-Path $repoRoot "gui\build-exe.ps1")
    if (-not (Test-Path $guiExe)) {
        Write-Error "gui/build-exe.ps1 失敗"; exit 1
    }
}

# ── 2. Locate ISCC.exe ────────────────────────────────────────
function Find-Iscc {
    $cmd = Get-Command "iscc" -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($p in @(
        "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    )) {
        if ($p -and (Test-Path $p)) { return $p }
    }
    return $null
}

$iscc = Find-Iscc
if (-not $iscc) {
    Write-Host "[build] 找不到 Inno Setup (ISCC.exe)，嘗試用 winget 安裝…" -ForegroundColor Yellow
    $winget = Get-Command "winget" -ErrorAction SilentlyContinue
    if (-not $winget) {
        Write-Error "請先手動安裝 Inno Setup 6：https://jrsoftware.org/isdl.php"
        exit 1
    }
    & winget install -e --id JRSoftware.InnoSetup --accept-package-agreements --accept-source-agreements
    $iscc = Find-Iscc
    if (-not $iscc) { Write-Error "Inno Setup 安裝後仍找不到 ISCC.exe"; exit 1 }
}
Write-Host "[build] ISCC = $iscc" -ForegroundColor Cyan

# ── 3. Compile ────────────────────────────────────────────────
Push-Location $scriptDir
try {
    Write-Host "[build] 編譯 $iss …" -ForegroundColor Cyan
    & $iscc $iss
    $dist = Join-Path $scriptDir "dist"
    $latest = Get-ChildItem $dist -Filter "genecr-installer-*.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($latest) {
        $size = $latest.Length / 1MB
        Write-Host ""
        Write-Host "✅ 完成：$($latest.FullName)  ($([math]::Round($size,1)) MB)" -ForegroundColor Green
        Write-Host "   把這個 .exe 給朋友雙擊即可，會自動裝到 %LOCALAPPDATA%\Programs\genecr 並建立桌面捷徑。"
    } else {
        Write-Error "build 失敗，沒產生 installer"
    }
} finally {
    Pop-Location
}
