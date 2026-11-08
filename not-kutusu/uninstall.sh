#!/usr/bin/env bash
set -euo pipefail

DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
STATE="${XDG_STATE_HOME:-$HOME/.local/state}"
YEDEK="$HOME/.local/bin/bandanix-yedek"

# 1) take the shortcut away (custom shortcut list goes back to how it was)
if [ -x "$YEDEK" ]; then
  "$YEDEK" geri-al not-kutusu
fi
/usr/bin/python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../core/bandanix_kisayol.py" onar || true

# 2) the command and its files; the notes themselves stay
rm -rf "$DATA/bandanix/not-kutusu"
rm -f "$HOME/.local/bin/bandanix-not" "$STATE/bandanix/not-taslak.txt"
rmdir "$DATA/bandanix" 2>/dev/null || true
echo "• Bandanix not kutusu kaldırıldı. Notların yerinde duruyor (~/Notlar)."
