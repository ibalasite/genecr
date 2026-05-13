# tools/renderer/setup.ps1 — install (default) | upgrade | uninstall
param([string]$Command = "install")
$ErrorActionPreference = "Stop"

$PkgDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$ToolsDir = Split-Path -Parent $PkgDir
$BinDir  = Join-Path $ToolsDir "bin"
$Files   = @("render.py", "pipeline.py", "orchestrate.py")

switch ($Command) {
  "install" {
    New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
    Write-Host "[renderer] installing python deps"
    python -m pip install -q -r (Join-Path $PkgDir "requirements.txt")
    Write-Host "[renderer] placing scripts -> $BinDir"
    foreach ($f in $Files) {
      Copy-Item -Force (Join-Path $PkgDir $f) (Join-Path $BinDir $f)
      Write-Host "[renderer]   $BinDir\$f"
    }
    Write-Host "[renderer] install done"
  }
  "upgrade" {
    Write-Host "[renderer] upgrading python deps"
    python -m pip install -q --upgrade -r (Join-Path $PkgDir "requirements.txt")
    & $MyInvocation.MyCommand.Path install
  }
  "uninstall" {
    foreach ($f in $Files) {
      $p = Join-Path $BinDir $f
      if (Test-Path $p) {
        Remove-Item -Force $p
        Write-Host "[renderer] removed $p"
      }
    }
    Write-Host "[renderer] uninstall done (python deps left intact)"
  }
  default {
    Write-Host "usage: setup.ps1 {install|upgrade|uninstall}"
    exit 1
  }
}
