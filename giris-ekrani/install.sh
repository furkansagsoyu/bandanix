#!/usr/bin/env bash
# description: Giriş ekranı: Bandanix duvar kağıdının bulanık hâli, Bandanix teması, ikonları ve imleci
# kurulu: ~/.local/bin/bandanix-giris
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APP="$DATA/bandanix/giris-ekrani"
BIN="$HOME/.local/bin/bandanix-giris"

if [ ! -f /usr/share/xgreeters/slick-greeter.desktop ] && ! command -v slick-greeter >/dev/null; then
  echo "• Bu bilgisayarda Slick Greeter (Mint'in giriş ekranı) yok; bu parça kurulmadı."
  exit 0
fi
if ! /usr/bin/python3 -c "import PIL" 2>/dev/null; then
  echo "• Resim kütüphanesi eksik, kuruluyor: python3-pil"
  sudo apt install python3-pil
fi

mkdir -p "$APP" "$(dirname "$BIN")"
cp "$HERE/bandanix_giris.py" "$APP/"
cat > "$BIN" <<EOF
#!/bin/sh
exec /usr/bin/python3 "$APP/bandanix_giris.py" "\$@"
EOF
chmod +x "$BIN"

echo "• Giriş ekranı sistem ayarı olduğu için şifren sorulacak."
"$BIN" guncelle
