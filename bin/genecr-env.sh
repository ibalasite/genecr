#!/usr/bin/env bash
# bin/genecr-env.sh — single source of truth for genecr runtime paths
# Usage: source "$HOME/.claude/skills/genecr/bin/genecr-env.sh"
#
# Skills MUST source this to discover templates/tools, and MUST NOT hardcode
# any path under the developer's working tree (e.g. C:\projects\genecr). The
# only thing skills may write to the user's CWD is the output/<feature-slug>/ folder.

_PY_HOME=$(python3 -c "import os; print(os.path.expanduser('~').replace('\\\\', '/'))" 2>/dev/null || echo "$HOME")
export GENECR_DIR="${GENECR_DIR:-$_PY_HOME/.claude/skills/genecr}"
export GENECR_BIN="$GENECR_DIR/bin"
export GENECR_TEMPLATES="$GENECR_DIR/templates"
export GENECR_TOOLS="$GENECR_DIR/tools/bin"
export GENECR_ASSETS="$GENECR_DIR/assets"
export GENECR_REFERENCES="$GENECR_DIR/references"
