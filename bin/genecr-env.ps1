# bin/genecr-env.ps1 — single source of truth for genecr runtime paths (PowerShell)
# Usage: . "$env:USERPROFILE\.claude\skills\genecr\bin\genecr-env.ps1"
#
# Skills MUST dot-source this to discover templates/tools, and MUST NOT hardcode
# any path under the developer's working tree. Only output/<feature-slug>/ is
# written into the user's CWD.

if (-not $env:GENECR_DIR) {
    $env:GENECR_DIR = Join-Path $env:USERPROFILE ".claude\skills\genecr"
}
$env:GENECR_BIN        = Join-Path $env:GENECR_DIR "bin"
$env:GENECR_TEMPLATES  = Join-Path $env:GENECR_DIR "templates"
$env:GENECR_TOOLS      = Join-Path $env:GENECR_DIR "tools\bin"
$env:GENECR_ASSETS     = Join-Path $env:GENECR_DIR "assets"
$env:GENECR_REFERENCES = Join-Path $env:GENECR_DIR "references"
