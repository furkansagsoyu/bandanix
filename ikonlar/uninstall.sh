#!/usr/bin/env bash
set -euo pipefail

ICONS="${XDG_DATA_HOME:-$HOME/.local/share}/icons"
YEDEK="$HOME/.local/bin/bandanix-yedek"

# Put back exactly the settings this component changed (icon/cursor theme, default cursor)
if [ -x "$YEDEK" ]; then
  "$YEDEK" geri-al ikonlar
fi
rm -rf "$ICONS/Bandanix" "$ICONS/Bandanix-Imlec" "$HOME/.icons/Bandanix-Imlec"
rmdir "$HOME/.icons/default" "$HOME/.icons" 2>/dev/null || true
echo "• Bandanix ikonları ve imleci kaldırıldı."
