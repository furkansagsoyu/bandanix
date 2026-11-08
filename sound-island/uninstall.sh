#!/usr/bin/env bash
set -euo pipefail

ID="bandanix-sound-island"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"

pkill -f "python -m sound_island" 2>/dev/null || true
# Cinnamon's own volume / brightness display comes back
[ -x "$HOME/.local/bin/bandanix-yedek" ] && "$HOME/.local/bin/bandanix-yedek" geri-al sound-island || true
rm -rf "$DATA/bandanix/sound-island"
rm -f "$HOME/.local/bin/sound-island" \
      "$DATA/applications/$ID.desktop" \
      "$DATA/icons/hicolor/scalable/apps/$ID.svg" \
      "${XDG_CONFIG_HOME:-$HOME/.config}/autostart/$ID.desktop"
rmdir "$DATA/bandanix" 2>/dev/null || true
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../ortak/ada/kur.sh"
ada_temizle
echo "• Sound Island kaldırıldı (playerctl gibi sistem paketleri yerinde bırakıldı)."
