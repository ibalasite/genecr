# bin/genecr-env.ps1 — single source of truth for genecr runtime paths (PowerShell)
#
# Host-neutral: $env:GENECR_DIR is derived from this script's own location, so
# the same code works whether genecr is installed under:
#   $env:USERPROFILE\.claude\skills\genecr   (Claude Code)
#   $env:USERPROFILE\.codex\skills\genecr    (Codex CLI)
#   $env:USERPROFILE\.gemini\skills\genecr   (Gemini CLI)
#   or any other host's skill dir.
#
# Skills MUST dot-source this to discover templates/tools, and MUST NOT
# hardcode any developer-tree path. Only output/<feature-slug>/ is written
# to the user's CWD.

if (-not $env:GENECR_DIR) {
    # This file is at $env:GENECR_DIR\bin\genecr-env.ps1
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $env:GENECR_DIR = Split-Path -Parent $scriptDir
}
$env:GENECR_BIN        = Join-Path $env:GENECR_DIR "bin"
$env:GENECR_TEMPLATES  = Join-Path $env:GENECR_DIR "templates"
$env:GENECR_TOOLS      = Join-Path $env:GENECR_DIR "tools\bin"
$env:GENECR_ASSETS     = Join-Path $env:GENECR_DIR "assets"
$env:GENECR_REFERENCES = Join-Path $env:GENECR_DIR "references"

# Host detection (optional)
if     ($env:GENECR_DIR -match '\\\.codex\\')  { $env:GENECR_HOST = 'codex' }
elseif ($env:GENECR_DIR -match '\\\.claude\\') { $env:GENECR_HOST = 'claude' }
elseif ($env:GENECR_DIR -match '\\\.gemini\\') { $env:GENECR_HOST = 'gemini' }
else                                            { $env:GENECR_HOST = 'unknown' }
