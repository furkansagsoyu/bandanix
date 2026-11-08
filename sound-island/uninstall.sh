#!/usr/bin/env bash
set -euo pipefail

ID="bandanix-sound-island"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"

pkill -f "python -m sound_island" 2>/dev/null || true
rm -rf "$DATA/bandanix/sound-island"
rm -f "$HOME/.local/bin/sound-island" \
      "$DATA/applications/$ID.desktop" \
      "$DATA/icons/hicolor/scalable/apps/$ID.svg" \
      "${XDG_CONFIG_HOME:-$HOME/.config}/autostart/$ID.desktop"
rmdir "$DATA/bandanix" 2>/dev/null || true
echo "• Sound Island removed (system packages like playerctl are left installed)."
