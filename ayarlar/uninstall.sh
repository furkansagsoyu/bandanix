#!/usr/bin/env bash
set -euo pipefail

DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
rm -rf "$DATA/bandanix/ayarlar"
rm -f "$HOME/.local/bin/bandanix" "$DATA/applications/bandanix-ayarlar.desktop" \
      "$DATA/icons/hicolor/scalable/apps/bandanix-ayarlar.svg"
rmdir "$DATA/bandanix" 2>/dev/null || true
echo "• Bandanix Ayarlar kaldırıldı. (Parçalar ve ayarların yerinde duruyor.)"
