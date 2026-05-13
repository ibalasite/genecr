#!/usr/bin/env bash
# tools/renderer/setup.sh — install (default) | upgrade | uninstall
set -e

CMD="${1:-install}"
PKG_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TOOLS_DIR="$( cd "$PKG_DIR/.." && pwd )"
BIN_DIR="$TOOLS_DIR/bin"
FILES=(render.py pipeline.py orchestrate.py)

case "$CMD" in
  install)
    mkdir -p "$BIN_DIR"
    echo "[renderer] installing python deps"
    python -m pip install -q -r "$PKG_DIR/requirements.txt"
    echo "[renderer] placing scripts → $BIN_DIR"
    for f in "${FILES[@]}"; do
      cp -f "$PKG_DIR/$f" "$BIN_DIR/$f"
      chmod +x "$BIN_DIR/$f"
      echo "[renderer]   $BIN_DIR/$f"
    done
    echo "[renderer] install done"
    ;;
  upgrade)
    echo "[renderer] upgrading python deps"
    python -m pip install -q --upgrade -r "$PKG_DIR/requirements.txt"
    "$0" install
    ;;
  uninstall)
    for f in "${FILES[@]}"; do
      if [ -f "$BIN_DIR/$f" ]; then
        rm -f "$BIN_DIR/$f"
        echo "[renderer] removed $BIN_DIR/$f"
      fi
    done
    echo "[renderer] uninstall done (python deps left intact)"
    ;;
  *)
    echo "usage: $0 {install|upgrade|uninstall}"
    exit 1
    ;;
esac
