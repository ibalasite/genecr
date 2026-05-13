# genecr setup.ps1 — Windows native (PowerShell), multi-host (Claude / Codex)
#
# Usage:
#   .\setup.ps1                          # install for auto-detected host
#   .\setup.ps1 install claude           # ~/.claude/skills/genecr
#   .\setup.ps1 install codex            # ~/.codex/skills/genecr
#   .\setup.ps1 install all              # both
#   .\setup.ps1 upgrade [target]
#   .\setup.ps1 uninstall [target]
#   .\setup.ps1 claude|codex|all         # shortcuts for install <target>

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

function Get-HostDir($host) {
    switch ($host) {
        "claude" { Join-Path $env:USERPROFILE ".claude\skills\genecr" }
        "codex"  { Join-Path $env:USERPROFILE ".codex\skills\genecr" }
    }
}
function Get-HostSkillsDir($host) {
    switch ($host) {
        "claude" { Join-Path $env:USERPROFILE ".claude\skills" }
        "codex"  { Join-Path $env:USERPROFILE ".codex\skills" }
    }
}

function Detect-HostFromSelf {
    $self = Split-Path -Parent $MyInvocation.MyCommand.Path
    if     ($self -match '\\\.codex\\')  { return "codex" }
    elseif ($self -match '\\\.claude\\') { return "claude" }
    else                                 { return "" }
}

function Resolve-Targets($t) {
    if     ($t -eq "all")    { return @("claude","codex") }
    elseif ($t -eq "claude") { return @("claude") }
    elseif ($t -eq "codex")  { return @("codex") }
    elseif ([string]::IsNullOrEmpty($t)) {
        $detected = Detect-HostFromSelf
        if ($detected) { return @($detected) }
        Log "[warn] cannot autodetect host; defaulting to claude"
        return @("claude")
    }
    else { Write-Error "unknown target: $t (use claude|codex|all)"; exit 1 }
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

function Deploy-Tools($runtime) {
    # gendoc-style: walk $runtime/tools/<pkg>/, deploy each into tools/bin/.
    #   1. tools/<pkg>/build.sh exists  → run it (BIN_DIR / PACKAGE_DIR injected)
    #   2. else cp tools/<pkg>/<pkg>.py → tools/bin/<pkg>.py (single-file convention)
    $toolsDir = Join-Path $runtime "tools"
    if (-not (Test-Path $toolsDir)) { return }
    $binDir = Join-Path $toolsDir "bin"
    New-Item -ItemType Directory -Force -Path $binDir | Out-Null
    Log "[deploy] tools\<pkg>\ -> $binDir"
    Get-ChildItem -Path $toolsDir -Directory | Where-Object { $_.Name -ne "bin" } | ForEach-Object {
        $pkg = $_.Name
        $build = Join-Path $_.FullName "build.sh"
        $entry = Join-Path $_.FullName "$pkg.py"
        if (Test-Path $build) {
            Log "  - build $pkg (build.sh)"
            $bash = Get-Command bash -ErrorAction SilentlyContinue
            if (-not $bash) { Write-Warning "  ! bash not in PATH; skipped $pkg/build.sh"; return }
            $py = Find-Python
            if (-not $py) { Write-Warning "  ! Python 3 not found; skipped $pkg/build.sh"; return }
            $env:BIN_DIR = $binDir
            $env:PACKAGE_DIR = $_.FullName
            $env:PY = $py
            & $bash.Source $build
            Remove-Item Env:BIN_DIR; Remove-Item Env:PACKAGE_DIR; Remove-Item Env:PY
        } elseif (Test-Path $entry) {
            Copy-Item -Force $entry (Join-Path $binDir "$pkg.py")
            Log "  - $pkg\$pkg.py -> bin\$pkg.py"
        }
    }
}

function Install-One($host) {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Write-Error "git required"; exit 1 }
    $runtime  = Get-HostDir $host
    $skillsDst = Get-HostSkillsDir $host
    if (Test-Path (Join-Path $runtime ".git")) {
        Log "[install:$host] $runtime already exists, running upgrade..."
        Upgrade-One $host; return
    }
    Log "[install:$host] git clone $RepoUrl -> $runtime"
    $parent = Split-Path -Parent $runtime
    if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    git clone $RepoUrl $runtime
    Deploy-Skills $runtime $skillsDst
    Deploy-Tools $runtime
    Log ""
    Log "[install:$host] done. Restart $host to activate skills."
}

function Upgrade-One($host) {
    $runtime  = Get-HostDir $host
    $skillsDst = Get-HostSkillsDir $host
    if (-not (Test-Path (Join-Path $runtime ".git"))) {
        Write-Warning "[upgrade:$host] $runtime not found. Run install first."
        return
    }
    Log "[upgrade:$host] git pull..."
    git -C $runtime pull --ff-only
    # Re-invoke freshly-pulled setup.ps1 so newly-added functions take effect (gendoc pattern).
    & (Join-Path $runtime "setup.ps1") "_post_upgrade" $host
    exit
}

function Post-Upgrade($host) {
    $runtime  = Get-HostDir $host
    $skillsDst = Get-HostSkillsDir $host
    Deploy-Skills $runtime $skillsDst
    Deploy-Tools $runtime
    Log "[upgrade:$host] done."
}

function Uninstall-One($host) {
    $runtime  = Get-HostDir $host
    $skillsDst = Get-HostSkillsDir $host
    Log "[uninstall:$host] remove deployed skills..."
    $skillsSrc = Join-Path $runtime "skills"
    if (Test-Path $skillsSrc) {
        Get-ChildItem -Path $skillsSrc -Directory | ForEach-Object {
            $dst = Join-Path $skillsDst $_.Name
            if (Test-Path $dst) { Remove-Item -Recurse -Force $dst; Log "  - removed $($_.Name)" }
        }
    }
    Log "[uninstall:$host] delete $runtime..."
    if (Test-Path $runtime) { Remove-Item -Recurse -Force $runtime }
    Log "[uninstall:$host] done."
}

switch ($Command.ToLower()) {
    "install"   { foreach ($h in Resolve-Targets $Target) { Install-One $h } }
    "upgrade"   { foreach ($h in Resolve-Targets $Target) { Upgrade-One $h } }
    "uninstall" { foreach ($h in Resolve-Targets $Target) { Uninstall-One $h } }
    "_post_upgrade" { Post-Upgrade $Target }
    "claude"    { foreach ($h in Resolve-Targets "claude") { Install-One $h } }
    "codex"     { foreach ($h in Resolve-Targets "codex")  { Install-One $h } }
    "all"       { foreach ($h in Resolve-Targets "all")    { Install-One $h } }
    default {
        Write-Host "Usage: .\setup.ps1 <command> [target]"
        Write-Host "  install [target]    git clone + deploy subskills (default)"
        Write-Host "  upgrade [target]    git pull + redeploy"
        Write-Host "  uninstall [target]  remove deployed skills + runtime"
        Write-Host "  claude|codex|all    shortcut for install <target>"
        Write-Host ""
        Write-Host "Targets: claude | codex | all | (auto-detect)"
        exit 1
    }
}
