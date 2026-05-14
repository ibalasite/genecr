# tools/renderer/build.ps1 — Windows-native (PowerShell) build script.
# Called by top-level setup.ps1's Deploy-Tools when build.ps1 is preferred over build.sh.
# Receives via env vars:
#   BIN_DIR     — destination for runtime executables (tools/bin/)
#   PACKAGE_DIR — this package's directory (tools/renderer/)
#   PY          — python executable to use (e.g. "python3" or "python")

$ErrorActionPreference = "Stop"

if (-not $env:BIN_DIR)     { Write-Error "BIN_DIR not set (must be invoked by setup Deploy-Tools)" }
if (-not $env:PACKAGE_DIR) { Write-Error "PACKAGE_DIR not set" }
if (-not $env:PY)          { $env:PY = "python" }

Write-Host "[renderer] pip install (using $($env:PY))"
& $env:PY -m pip install -q -r (Join-Path $env:PACKAGE_DIR "requirements.txt")

Write-Host "[renderer] cp .py -> $($env:BIN_DIR)"
foreach ($f in @("render.py","pipeline.py","orchestrate.py")) {
    Copy-Item -Force (Join-Path $env:PACKAGE_DIR $f) (Join-Path $env:BIN_DIR $f)
}
