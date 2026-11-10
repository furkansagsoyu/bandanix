#!/usr/bin/env bash
set -euo pipefail

DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APP="$DATA/bandanix/yeni-sekme"
BIN="$HOME/.local/bin/bandanix-sekme"

if [[ -x $BIN ]]; then
  "$BIN" ac || true
fi
rm -rf "$APP"
rm -f "$BIN"
echo "• Yeni sekme dosyaları silindi."
echo "  Açılan brave://extensions sayfasında \"Bandanix Yeni Sekme\" kartındaki \"Kaldır\"a bas."
