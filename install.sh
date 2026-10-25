#!/usr/bin/env bash
# Links stable_z_home.py into Klipper's extras dir. Re-run after reinstalling Klipper.
set -e
KLIPPER_DIR="${KLIPPER_DIR:-$HOME/klipper}"
SRC="$(cd "$(dirname "$0")" && pwd)/stable_z_home.py"
[ -d "$KLIPPER_DIR/klippy/extras" ] || { echo "Klipper not found at $KLIPPER_DIR (set KLIPPER_DIR)"; exit 1; }
ln -sf "$SRC" "$KLIPPER_DIR/klippy/extras/stable_z_home.py"
echo "Linked. Restart Klipper: sudo systemctl restart klipper"
