#!/usr/bin/env bash
# Links the plugin files into Klipper's extras dir. Re-run after reinstalling Klipper.
set -e
KLIPPER_DIR="${KLIPPER_DIR:-$HOME/klipper}"
DIR="$(cd "$(dirname "$0")" && pwd)"
[ -d "$KLIPPER_DIR/klippy/extras" ] || { echo "Klipper not found at $KLIPPER_DIR (set KLIPPER_DIR)"; exit 1; }
for f in stable_z_home.py wall_clock.py; do
    ln -sf "$DIR/$f" "$KLIPPER_DIR/klippy/extras/$f"
done
echo "Linked. Restart Klipper: sudo systemctl restart klipper"
