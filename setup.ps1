# genecr setup.ps1 — Windows native (PowerShell), multi-host (Claude / Codex / Gemini / Copilot)
#
# Usage:
#   .\setup.ps1                          # install for auto-detected host
#   .\setup.ps1 install claude           # ~/.claude/skills/genecr
#   .\setup.ps1 install codex            # ~/.codex/skills/genecr
#   .\setup.ps1 install gemini           # ~/.gemini/skills/genecr
#   .\setup.ps1 install copilot          # ~/.copilot/skills/genecr
#   .\setup.ps1 install all              # all four hosts
#   .\setup.ps1 upgrade [target]
#   .\setup.ps1 uninstall [target]
#   .\setup.ps1 claude|codex|gemini|copilot|all  # shortcuts for install <target>

param(
    [string]$Command = "install",
    [string]$Target  = ""
)

$ErrorActionPreference = "Stop"

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {}

$RepoUrl = "https://github.com/ibalasite/genecr.git"

function Log($msg) { Write-Host $msg }

function Get-HostDir($hostName) {
    switch ($hostName) {
        "claude" { Join-Path $env:USERPROFILE ".claude\skills\genecr" }
        "codex"  { Join-Path $env:USERPROFILE ".codex\skills\genecr" }
        "gemini" { Join-Path $env:USERPROFILE ".gemini\skills\genecr" }
        "copilot" { Join-Path $env:USERPROFILE ".copilot\skills\genecr" }
    }
}
function Get-HostSkillsDir($hostName) {
    switch ($hostName) {
        "claude" { Join-Path $env:USERPROFILE ".claude\skills" }
        "codex"  { Join-Path $env:USERPROFILE ".codex\skills" }
        "gemini" { Join-Path $env:USERPROFILE ".gemini\skills" }
        "copilot" { Join-Path $env:USERPROFILE ".copilot\skills" }
    }
}

function Detect-HostFromSelf {
    $self = Split-Path -Parent $MyInvocation.MyCommand.Path
    if     ($self -match '\\\.codex\\')  { return "codex" }
    elseif ($self -match '\\\.claude\\') { return "claude" }
    elseif ($self -match '\\\.gemini\\') { return "gemini" }
    elseif ($self -match '\\\.copilot\\') { return "copilot" }
    else                                 { return "" }
}

function Resolve-Targets($t) {
    if     ($t -eq "all")    { return @("claude","codex","gemini","copilot") }
    elseif ($t -eq "claude") { return @("claude") }
    elseif ($t -eq "codex")  { return @("codex") }
    elseif ($t -eq "gemini") { return @("gemini") }
    elseif ($t -eq "copilot") { return @("copilot") }
    elseif ([string]::IsNullOrEmpty($t)) {
        $detected = Detect-HostFromSelf
        if ($detected) { return @($detected) }
        Log "[warn] cannot autodetect host; defaulting to claude"
        return @("claude")
    }
    else { Write-Error "unknown target: $t (use claude|codex|gemini|copilot|all)"; exit 1 }
}

function Deploy-Skills($runtime, $skillsDst) {
    Log "[deploy] $runtime\skills\* -> $skillsDst\"
    if (-not (Test-Path $skillsDst)) { New-Item -ItemType Directory -Force -Path $skillsDst | Out-Null }
    $skillsSrc = Join-Path $runtime "skills"
    if (-not (Test-Path $skillsSrc)) { Log "  WARN: $skillsSrc not found, skip"; return }
    Get-ChildItem -Path $skillsSrc -Directory | ForEach-Object {
        $dst = Join-Path $skillsDst $_.Name
        if (Test-Path $dst) { Remove-Item -Recurse -Force $dst }
        Copy-Item -Recurse $_.FullName $dst
        Log "  - $($_.Name)"
    }
}

function Find-Python {
    # Windows MS Store stub for "python3" exits non-zero or opens the Store.
    # Try python3 first, fall back to python, verify it's actually Python 3.
    foreach ($cand in @("python3", "python")) {
        $cmd = Get-Command $cand -ErrorAction SilentlyContinue
        if (-not $cmd) { continue }
        try {
            $ver = & $cand --version 2>&1
            if ($ver -match "^Python 3") { return $cand }
        } catch {}
    }
    return $null
}

function Find-GitBash {
    # Prefer Git Bash over WSL's bash (System32\bash.exe is WSL, which can't
    # access Windows paths like C:\Users\...). Check Git installation first.
    foreach ($p in @(
        "$env:ProgramFiles\Git\bin\bash.exe",
        "${env:ProgramFiles(x86)}\Git\bin\bash.exe",
        "$env:LOCALAPPDATA\Programs\Git\bin\bash.exe"
    )) {
        if ($p -and (Test-Path $p)) { return $p }
    }
    # Fall back to PATH lookup, but skip if it's WSL's launcher.
    $cmd = Get-Command bash -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source -notmatch 'System32\\bash\.exe$') { return $cmd.Source }
    return $null
}

function Deploy-Tools($runtime) {
    # gendoc-style: walk $runtime/tools/<pkg>/, deploy each into tools/bin/.
    # Build script preference (Windows-friendly):
    #   1. tools/<pkg>/build.ps1 → run natively (no bash needed)
    #   2. tools/<pkg>/build.sh  → run via Git Bash (skip WSL bash)
    #   3. tools/<pkg>/<pkg>.py  → single-file copy
    $toolsDir = Join-Path $runtime "tools"
    if (-not (Test-Path $toolsDir)) { return }
    $binDir = Join-Path $toolsDir "bin"
    New-Item -ItemType Directory -Force -Path $binDir | Out-Null
    Log "[deploy] tools\<pkg>\ -> $binDir"
    Get-ChildItem -Path $toolsDir -Directory | Where-Object { $_.Name -ne "bin" } | ForEach-Object {
        $pkg = $_.Name
        $buildPs1 = Join-Path $_.FullName "build.ps1"
        $buildSh  = Join-Path $_.FullName "build.sh"
        $entry    = Join-Path $_.FullName "$pkg.py"
        $py = Find-Python
        if (-not $py) { Write-Warning "  ! Python 3 not found; skipped $pkg"; return }
        $env:BIN_DIR = $binDir
        $env:PACKAGE_DIR = $_.FullName
        $env:PY = $py
        try {
            if (Test-Path $buildPs1) {
                Log "  - build $pkg (build.ps1)"
                & $buildPs1
            } elseif (Test-Path $buildSh) {
                Log "  - build $pkg (build.sh via Git Bash)"
                $bashExe = Find-GitBash
                if (-not $bashExe) {
                    Write-Warning "  ! Git Bash not found (need Git for Windows or build.ps1); skipped $pkg"
                    return
                }
                & $bashExe $buildSh
            } elseif (Test-Path $entry) {
                Copy-Item -Force $entry (Join-Path $binDir "$pkg.py")
                Log "  - $pkg\$pkg.py -> bin\$pkg.py"
            }
        } finally {
            Remove-Item Env:BIN_DIR -ErrorAction SilentlyContinue
            Remove-Item Env:PACKAGE_DIR -ErrorAction SilentlyContinue
            Remove-Item Env:PY -ErrorAction SilentlyContinue
        }
    }
}

function Install-PythonDeps($runtime) {
    $req = Join-Path $runtime "tools\renderer\requirements.txt"
    if (-not (Test-Path $req)) { return }
    $py = Find-Python
    if (-not $py) { Log "[deps] Python 3 not found - skip pip install"; return }
    Log "[deps] pip install -r tools/renderer/requirements.txt"
    try { & $py -m pip install --quiet -r $req } catch { Log "[deps] WARN pip install failed - run manually: $py -m pip install -r $req"; return }
    Log "[deps] playwright install chromium (~150MB, one-time, may take 1-2 min)"
    try { & $py -m playwright install chromium } catch { Log "[deps] WARN chromium download failed - prototype layout audit will skip. Retry: $py -m playwright install chromium" }
}

function Install-One($hostName) {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Write-Error "git required"; exit 1 }
    $runtime  = Get-HostDir $hostName
    $skillsDst = Get-HostSkillsDir $hostName
    if (Test-Path (Join-Path $runtime ".git")) {
        Log "[install:$hostName] $runtime already exists, running upgrade..."
        Upgrade-One $hostName; return
    }
    Log "[install:$hostName] git clone $RepoUrl -> $runtime"
    $parent = Split-Path -Parent $runtime
    if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    git clone $RepoUrl $runtime
    Deploy-Skills $runtime $skillsDst
    Deploy-Tools $runtime
    Install-PythonDeps $runtime
    Log ""
    Log "[install:$hostName] done. Restart $hostName to activate skills."
}

function Upgrade-One($hostName) {
    $runtime  = Get-HostDir $hostName
    $skillsDst = Get-HostSkillsDir $hostName
    if (-not (Test-Path (Join-Path $runtime ".git"))) {
        Write-Warning "[upgrade:$hostName] $runtime not found. Run install first."
        return
    }
    Log "[upgrade:$hostName] git pull..."
    git -C $runtime pull --ff-only
    # Re-invoke freshly-pulled setup.ps1 so newly-added functions take effect (gendoc pattern).
    & (Join-Path $runtime "setup.ps1") "_post_upgrade" $hostName
    exit
}

function Post-Upgrade($hostName) {
    $runtime  = Get-HostDir $hostName
    $skillsDst = Get-HostSkillsDir $hostName
    Deploy-Skills $runtime $skillsDst
    Deploy-Tools $runtime
    Install-PythonDeps $runtime
    Log "[upgrade:$hostName] done."
}

function Uninstall-One($hostName) {
    $runtime  = Get-HostDir $hostName
    $skillsDst = Get-HostSkillsDir $hostName
    Log "[uninstall:$hostName] remove deployed skills..."
    $skillsSrc = Join-Path $runtime "skills"
    if (Test-Path $skillsSrc) {
        Get-ChildItem -Path $skillsSrc -Directory | ForEach-Object {
            $dst = Join-Path $skillsDst $_.Name
            if (Test-Path $dst) { Remove-Item -Recurse -Force $dst; Log "  - removed $($_.Name)" }
        }
    }
    Log "[uninstall:$hostName] delete $runtime..."
    if (Test-Path $runtime) { Remove-Item -Recurse -Force $runtime }
    Log "[uninstall:$hostName] done."
}

switch ($Command.ToLower()) {
    "install"   { foreach ($h in Resolve-Targets $Target) { Install-One $h } }
    "upgrade"   { foreach ($h in Resolve-Targets $Target) { Upgrade-One $h } }
    "uninstall" { foreach ($h in Resolve-Targets $Target) { Uninstall-One $h } }
    "_post_upgrade" { Post-Upgrade $Target }
    "claude"    { foreach ($h in Resolve-Targets "claude") { Install-One $h } }
    "codex"     { foreach ($h in Resolve-Targets "codex")  { Install-One $h } }
    "gemini"    { foreach ($h in Resolve-Targets "gemini") { Install-One $h } }
    "copilot"   { foreach ($h in Resolve-Targets "copilot") { Install-One $h } }
    "all"       { foreach ($h in Resolve-Targets "all")    { Install-One $h } }
    default {
        Write-Host "Usage: .\setup.ps1 <command> [target]"
        Write-Host "  install [target]      git clone + deploy subskills (default)"
        Write-Host "  upgrade [target]      git pull + redeploy"
        Write-Host "  uninstall [target]    remove deployed skills + runtime"
        Write-Host "  claude|codex|gemini|copilot|all  shortcut for install <target>"
        Write-Host ""
        Write-Host "Targets: claude | codex | gemini | copilot | all | (auto-detect)"
        exit 1
    }
}
