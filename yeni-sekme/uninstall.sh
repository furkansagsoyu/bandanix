#!/usr/bin/env bash
set -euo pipefail

DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APP="$DATA/bandanix/yeni-sekme"
BIN="$HOME/.local/bin/bandanix-sekme"

if [[ -x $BIN ]]; then
  "$BIN" ac || true
  "$BIN" ac tema || true
fi
rm -rf "$APP"
rm -f "$BIN"
echo "• Yeni sekme ve tema dosyaları silindi. Brave'de iki adım kaldı:"
echo "  1. brave://extensions sayfasında \"Bandanix Yeni Sekme\" kartındaki \"Kaldır\"a bas."
echo "  2. brave://settings/appearance sayfasında temanın yanındaki \"Varsayılana sıfırla\"ya bas."
