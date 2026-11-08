#!/usr/bin/env bash
set -euo pipefail

DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
UNITS="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
YEDEK="$HOME/.local/bin/bandanix-yedek"

# 1) stop and remove the hourly timer
systemctl --user disable --now bandanix-duvar.timer 2>/dev/null || true
rm -f "$UNITS/bandanix-duvar.timer" "$UNITS/bandanix-duvar.service"
systemctl --user daemon-reload 2>/dev/null || true

# 2) give the old wallpaper back, then remove the files
if [ -x "$YEDEK" ]; then
  "$YEDEK" geri-al duvar-kagidi
fi
rm -rf "$DATA/backgrounds/bandanix" "$DATA/bandanix/duvar-kagidi"
rm -f "$HOME/.local/bin/bandanix-duvar"
rmdir "$DATA/backgrounds" "$DATA/bandanix" 2>/dev/null || true
echo "• Bandanix duvar kağıtları kaldırıldı."
