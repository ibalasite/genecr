# gui/build-exe.ps1 — package genecr-gui.pyw into a single Windows .exe
#
# Output:  gui/dist/genecr-gui.exe   (~30-40 MB, no Python needed at runtime)
#
# Usage (from repo root or anywhere):
#   .\gui\build-exe.ps1
#
# First-time setup: pip install pyinstaller

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$source = Join-Path $scriptDir "genecr-gui.pyw"
$dist   = Join-Path $scriptDir "dist"
$build  = Join-Path $scriptDir "build"
$spec   = Join-Path $scriptDir "genecr-gui.spec"

if (-not (Test-Path $source)) {
    Write-Error "找不到 $source"
    exit 1
}

# Ensure pyinstaller installed
$py = $null
foreach ($cand in @("python3", "python")) {
    $cmd = Get-Command $cand -ErrorAction SilentlyContinue
    if ($cmd) {
        $ver = & $cand --version 2>&1
        if ($ver -match "^Python 3") { $py = $cand; break }
    }
}
if (-not $py) { Write-Error "需要 Python 3"; exit 1 }

Write-Host "[build] using $py" -ForegroundColor Cyan
& $py -m pip install -q pyinstaller

# Build single-file windowed exe (no console) named genecr-gui
Write-Host "[build] running PyInstaller…" -ForegroundColor Cyan
Push-Location $scriptDir
try {
    & $py -m PyInstaller `
        --noconfirm `
        --onefile `
        --windowed `
        --name "genecr-gui" `
        --distpath $dist `
        --workpath $build `
        --specpath $scriptDir `
        $source

    $exe = Join-Path $dist "genecr-gui.exe"
    if (Test-Path $exe) {
        $size = (Get-Item $exe).Length / 1MB
        Write-Host ""
        Write-Host "✅ 完成：$exe  ($([math]::Round($size,1)) MB)" -ForegroundColor Green
        Write-Host "   雙擊即可執行，免裝 Python。"
    } else {
        Write-Error "build 失敗，沒產生 .exe"
    }
} finally {
    Pop-Location
}
