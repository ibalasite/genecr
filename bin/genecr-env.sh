#!/usr/bin/env bash
# bin/genecr-env.sh — single source of truth for genecr runtime paths
#
# Host-neutral: GENECR_DIR is derived from this script's own location, so the
# same code works whether genecr is installed under:
#   ~/.claude/skills/genecr   (Claude Code)
#   ~/.codex/skills/genecr    (Codex CLI)
#   ~/.gemini/skills/genecr   (Gemini CLI)
#   or any other host's skill dir.
#
# Skills MUST source this to discover templates/tools, and MUST NOT hardcode
# any path under the developer's working tree (e.g. C:\projects\genecr). The
# only thing skills may write to the user's CWD is the output/<feature-slug>/ folder.
#
# Usage:
#   # Preferred: discover via GENECR_DIR (already exported by host, or auto-detect)
#   source "$GENECR_DIR/bin/genecr-env.sh"
#
#   # Or auto-discover when GENECR_DIR is not set yet:
#   if [ -z "$GENECR_DIR" ]; then
#     for d in "$HOME/.codex/skills/genecr" "$HOME/.claude/skills/genecr" "$HOME/.gemini/skills/genecr"; do
#       [ -d "$d" ] && export GENECR_DIR="$d" && break
#     done
#   fi
#   source "$GENECR_DIR/bin/genecr-env.sh"

if [ -z "$GENECR_DIR" ]; then
  # Derive from this script's own location: $GENECR_DIR/bin/genecr-env.sh
  _SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
  GENECR_DIR="$(dirname "$_SCRIPT_DIR")"
fi
export GENECR_DIR
export GENECR_BIN="$GENECR_DIR/bin"
export GENECR_TEMPLATES="$GENECR_DIR/templates"
export GENECR_TOOLS="$GENECR_DIR/tools/bin"
export GENECR_ASSETS="$GENECR_DIR/assets"
export GENECR_REFERENCES="$GENECR_DIR/references"

# Host detection (optional, for skills that want to print which host they're under)
case "$GENECR_DIR" in
  *"/.codex/"*)  export GENECR_HOST="codex"  ;;
  *"/.claude/"*) export GENECR_HOST="claude" ;;
  *"/.gemini/"*) export GENECR_HOST="gemini" ;;
  *)             export GENECR_HOST="unknown" ;;
esac
