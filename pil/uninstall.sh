#!/usr/bin/env bash
set -euo pipefail

DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APP="$DATA/bandanix/pil"
UNITS="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/bandanix/pil.json"
HELPER=/usr/local/sbin/bandanix-pil-yaz
SUDOERS=/etc/sudoers.d/bandanix-pil
SERVICE=/etc/systemd/system/bandanix-pil-sinir.service
CONF=/etc/bandanix-pil.conf

# 1) stop the 2-minute check
systemctl --user disable --now bandanix-pil.timer 2>/dev/null || true
rm -f "$UNITS/bandanix-pil.timer" "$UNITS/bandanix-pil.service"
systemctl --user daemon-reload 2>/dev/null || true

# 2) give the old charge limit back, then remove the root parts
if [ -e "$HELPER" ] || [ -e "$SUDOERS" ] || [ -e "$SERVICE" ] || [ -e "$CONF" ]; then
  echo "• Şarj sınırı eski hâline dönüyor (şifren sorulabilir)."
  PREV=$(cat "$APP/onceki-sinir" 2>/dev/null || echo 100)
  if [ -x "$HELPER" ]; then
    sudo "$HELPER" "$PREV" 2>/dev/null && echo "• Şarj sınırı: %$PREV" || true
  fi
  sudo systemctl disable bandanix-pil-sinir.service >/dev/null 2>&1 || true
  sudo rm -f "$SERVICE" "$SUDOERS" "$HELPER" "$CONF"
  sudo systemctl daemon-reload
fi

# 3) the command and its files
rm -rf "$APP"
rm -f "$HOME/.local/bin/bandanix-pil" "$STATE"
rmdir "$DATA/bandanix" 2>/dev/null || true
echo "• Bandanix pil yardımcısı kaldırıldı."
