#!/usr/bin/env bash
set -euo pipefail

YEDEK="$HOME/.local/bin/bandanix-yedek"

# Put back exactly the settings this component changed (theme names, GTK4 colours)
if [ -x "$YEDEK" ]; then
  "$YEDEK" geri-al cinnamon-tema
fi
rm -rf "$HOME/.themes/Bandanix"
rmdir "$HOME/.themes" 2>/dev/null || true
echo "• Bandanix teması kaldırıldı."
