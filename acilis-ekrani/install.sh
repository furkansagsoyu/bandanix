#!/usr/bin/env bash
# description: Açılış ekranı: siyah zeminde BANDANIX ve kırmızı ilerleme çizgisi, Bandanix GRUB menüsü
# kurulu: /usr/share/plymouth/themes/bandanix/bandanix.plymouth
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$HOME/.local/bin/bandanix-acilis"

if [ ! -d /usr/share/plymouth/themes ] && [ ! -d /boot/grub ]; then
  echo "• Bu bilgisayarda Plymouth ve GRUB bulunamadı; bu parça kurulmadı."
  exit 0
fi

mkdir -p "$(dirname "$BIN")"
cp "$HERE/bandanix-acilis" "$BIN"
chmod +x "$BIN"

echo "• Açılış ekranı sistem ayarı olduğu için şifren sorulacak."
sudo bash "$HERE/kok.sh" kur "$HERE"
echo
"$BIN" || true
echo
echo "• Yeniden başlatmadan görmek için: bandanix-acilis dene"
