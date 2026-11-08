#!/usr/bin/env bash
set -euo pipefail

DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
YEDEK="$HOME/.local/bin/bandanix-yedek"

# 1) shortcut back to how it was, watcher stopped
if [ -x "$YEDEK" ]; then
  "$YEDEK" geri-al pano
fi
/usr/bin/python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../core/bandanix_kisayol.py" onar || true
pkill -f "bandanix_pano.py _bekci" 2>/dev/null || true
rm -f "${XDG_CONFIG_HOME:-$HOME/.config}/autostart/bandanix-pano.desktop"

# 2) files, including the history itself (it may hold private things)
rm -rf "$DATA/bandanix/pano"
rm -f "$HOME/.local/bin/bandanix-pano" "$DATA/bandanix/pano.json" "$DATA/bandanix/.pano.lock"
rmdir "$DATA/bandanix" 2>/dev/null || true
echo "• Bandanix pano geçmişi kaldırıldı; kayıtlı geçmiş de silindi."
