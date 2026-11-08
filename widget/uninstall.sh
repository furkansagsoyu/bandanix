#!/usr/bin/env bash
set -euo pipefail

DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
UNITS="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
YEDEK="$HOME/.local/bin/bandanix-yedek"

# 1) the desklet leaves the desktop (desklet list goes back to how it was)
if [ -x "$YEDEK" ]; then
  "$YEDEK" geri-al widget
fi
rm -rf "$DATA/cinnamon/desklets/bandanix-saat@furkansagsoyu"

# 2) weather timer and files
systemctl --user disable --now bandanix-hava.timer 2>/dev/null || true
rm -f "$UNITS/bandanix-hava.timer" "$UNITS/bandanix-hava.service"
systemctl --user daemon-reload 2>/dev/null || true
rm -rf "$DATA/bandanix/widget"
rm -f "$HOME/.local/bin/bandanix-widget" "${XDG_CACHE_HOME:-$HOME/.cache}/bandanix/hava.json"
rmdir "$DATA/bandanix" 2>/dev/null || true
echo "• Bandanix saat widget'ı kaldırıldı."
