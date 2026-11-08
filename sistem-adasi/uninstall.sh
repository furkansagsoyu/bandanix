#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
BIN="$HOME/.local/bin/bandanix-sistem"

# 1) stop the watcher and the pill, remove the login entry
[ -x "$BIN" ] && "$BIN" kapat >/dev/null || true
rm -f "${XDG_CONFIG_HOME:-$HOME/.config}/autostart/bandanix-sistem.desktop"

# 2) files
rm -rf "$DATA/bandanix/sistem-adasi"
rm -f "$BIN" "${XDG_STATE_HOME:-$HOME/.local/state}/bandanix/sistem-sustur.json"
source "$HERE/../ortak/ada/kur.sh"
ada_temizle
rmdir "$DATA/bandanix" 2>/dev/null || true
echo "• Sistem adası kaldırıldı."
