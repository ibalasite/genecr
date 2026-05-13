# genecr setup.ps1 — Windows native (PowerShell) version
# Usage:
#   .\setup.ps1             # install (default)
#   .\setup.ps1 install     # clone repo (if missing) + deploy subskills
#   .\setup.ps1 uninstall   # remove deployed skills + runtime
#   .\setup.ps1 upgrade     # git pull + redeploy

param([string]$Command = "install")

$ErrorActionPreference = "Stop"

# UTF-8 console — avoid cp950/cp936 mojibake on zh-TW/zh-CN Windows
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {}

$RepoUrl         = "https://github.com/ibalasite/genecr.git"   # TODO: 改成實際 repo URL
$RuntimeDir      = Join-Path $env:USERPROFILE ".claude\skills\genecr"
$ClaudeSkillsDir = Join-Path $env:USERPROFILE ".claude\skills"

function Log($msg) { Write-Host $msg }

function Deploy-Skills {
    Log "[deploy] $RuntimeDir\skills\* -> $ClaudeSkillsDir\"
    if (-not (Test-Path $ClaudeSkillsDir)) {
        New-Item -ItemType Directory -Force -Path $ClaudeSkillsDir | Out-Null
    }
    $skillsSrc = Join-Path $RuntimeDir "skills"
    if (-not (Test-Path $skillsSrc)) {
        Log "  WARN: $skillsSrc not found, skip"
        return
    }
    Get-ChildItem -Path $skillsSrc -Directory | ForEach-Object {
        $dst = Join-Path $ClaudeSkillsDir $_.Name
        if (Test-Path $dst) { Remove-Item -Recurse -Force $dst }
        Copy-Item -Recurse $_.FullName $dst
        Log "  - $($_.Name)"
    }
}

function Do-Install {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Write-Error "git required"; exit 1 }

    if (Test-Path (Join-Path $RuntimeDir ".git")) {
        Log "[install] $RuntimeDir already exists, running upgrade..."
        Do-Upgrade; return
    }

    Log "[install] git clone $RepoUrl -> $RuntimeDir"
    $parent = Split-Path -Parent $RuntimeDir
    if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    git clone $RepoUrl $RuntimeDir

    Deploy-Skills

    Log ""
    Log "[install] done. Restart Claude Code to activate skills."
    Log "  - upgrade:   $RuntimeDir\setup.ps1 upgrade"
    Log "  - uninstall: $RuntimeDir\setup.ps1 uninstall"
}

function Do-Upgrade {
    if (-not (Test-Path (Join-Path $RuntimeDir ".git"))) {
        Write-Error "[upgrade] $RuntimeDir not found. Run install first."; exit 1
    }
    Log "[upgrade] git pull..."
    git -C $RuntimeDir pull --ff-only
    Deploy-Skills
    Log "[upgrade] done."
}

function Do-Uninstall {
    Log "[uninstall] remove deployed skills..."
    $skillsSrc = Join-Path $RuntimeDir "skills"
    if (Test-Path $skillsSrc) {
        Get-ChildItem -Path $skillsSrc -Directory | ForEach-Object {
            $dst = Join-Path $ClaudeSkillsDir $_.Name
            if (Test-Path $dst) { Remove-Item -Recurse -Force $dst; Log "  - removed $($_.Name)" }
        }
    }
    Log "[uninstall] delete $RuntimeDir..."
    if (Test-Path $RuntimeDir) { Remove-Item -Recurse -Force $RuntimeDir }
    Log "[uninstall] done."
}

switch ($Command.ToLower()) {
    "install"   { Do-Install }
    "upgrade"   { Do-Upgrade }
    "uninstall" { Do-Uninstall }
    default {
        Write-Host "Usage: .\setup.ps1 [install|uninstall|upgrade]"
        Write-Host "  install   - git clone + deploy subskills (default)"
        Write-Host "  uninstall - remove deployed skills + runtime"
        Write-Host "  upgrade   - git pull + redeploy"
        exit 1
    }
}
