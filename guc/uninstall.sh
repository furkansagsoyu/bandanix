#!/usr/bin/env bash
set -euo pipefail

DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APP="$DATA/bandanix/guc"
HELPER=/usr/local/sbin/bandanix-guc-yaz
SUDOERS=/etc/sudoers.d/bandanix-guc
SERVICE=/etc/systemd/system/bandanix-guc.service

if [ -e "$HELPER" ] || [ -e "$SUDOERS" ] || [ -e "$SERVICE" ] || [ -e /etc/bandanix-guc.conf ]; then
  echo "• Güç modu eski hâline dönüyor (şifren sorulabilir)."
  if [ -x "$HELPER" ]; then
    sudo "$HELPER" boost off 2>/dev/null || true
    read -r s f t < "$APP/onceki" 2>/dev/null || { s=comfort; f=auto; t=on; }
    sudo "$HELPER" geri "$s" "$f" "$t" 2>/dev/null || true
  fi
  sudo systemctl disable bandanix-guc.service >/dev/null 2>&1 || true
  sudo rm -f "$SERVICE" "$SUDOERS" "$HELPER" /etc/bandanix-guc.conf
  sudo systemctl daemon-reload
fi
rm -rf "$APP"
rm -f "$HOME/.local/bin/bandanix-guc"
rmdir "$DATA/bandanix" 2>/dev/null || true
echo "• Bandanix güç modları kaldırıldı."
