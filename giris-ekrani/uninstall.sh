#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"

echo "• Giriş ekranı eski hâline dönüyor (şifren sorulabilir)."
/usr/bin/python3 "$HERE/bandanix_giris.py" _kaldir
rm -rf "$DATA/bandanix/giris-ekrani"
rm -f "$HOME/.local/bin/bandanix-giris"
rmdir "$DATA/bandanix" 2>/dev/null || true
echo "• Bandanix giriş ekranı kaldırıldı."
