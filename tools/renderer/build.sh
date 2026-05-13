#!/usr/bin/env bash
# tools/renderer/build.sh — gendoc-style build script.
# Called by top-level setup's _deploy_tools.
# Receives:
#   BIN_DIR     — destination for runtime executables (tools/bin/)
#   PACKAGE_DIR — this package's directory (tools/renderer/)
set -e

: "${BIN_DIR:?BIN_DIR not set (must be invoked by setup _deploy_tools)}"
: "${PACKAGE_DIR:?PACKAGE_DIR not set}"
: "${PY:=python}"   # fallback if invoked outside setup _deploy_tools

echo "[renderer] pip install (using $PY)"
"$PY" -m pip install -q -r "$PACKAGE_DIR/requirements.txt"

echo "[renderer] cp .py → $BIN_DIR"
for f in render.py pipeline.py orchestrate.py; do
  cp -f "$PACKAGE_DIR/$f" "$BIN_DIR/$f"
  chmod +x "$BIN_DIR/$f"
done
