#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THEME_CSS="$HOME/.themes/Bandanix/cinnamon/cinnamon.css"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
YEDEK="$HOME/.local/bin/bandanix-yedek"

# applet layout and height back as they were, then drop the island CSS
if [ -x "$YEDEK" ]; then
  "$YEDEK" geri-al panel-duzeni
fi
/usr/bin/python3 "$HERE/panel.py" kaldir "$THEME_CSS"
rm -rf "$DATA/bandanix/panel-duzeni"
echo "• Panel eski düzenine döndü."
