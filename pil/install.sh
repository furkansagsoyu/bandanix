#!/usr/bin/env bash
# description: Pil sağlığı: şarjı %80'de durdurur, pil azalınca uyarır, bandanix-pil komutu
# kurulu: ~/.local/bin/bandanix-pil
# yetki: sudo
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APP="$DATA/bandanix/pil"
BIN="$HOME/.local/bin/bandanix-pil"
UNITS="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
HELPER=/usr/local/sbin/bandanix-pil-yaz
SUDOERS=/etc/sudoers.d/bandanix-pil
SERVICE=/etc/systemd/system/bandanix-pil-sinir.service

ask() {
  local reply
  [ -t 0 ] || return 0
  read -rp "$1 [E/h] " reply
  [[ ! "$reply" =~ ^[hHnN] ]]
}

limit_file() {
  local f
  for f in /sys/class/power_supply/BAT*/charge_control_end_threshold; do
    [ -f "$f" ] && { printf '%s' "$f"; return 0; }
  done
  return 1
}

if ! ls /sys/class/power_supply/BAT*/capacity >/dev/null 2>&1; then
  echo "• Pil bulunamadı; bu parça dizüstü bilgisayarlar için."
  exit 0
fi
command -v notify-send >/dev/null || { echo "• Bildirim aracı eksik, kuruluyor: libnotify-bin"; sudo apt install libnotify-bin; }

# 1) the bandanix-pil command and the 2-minute check
mkdir -p "$APP" "$(dirname "$BIN")" "$UNITS"
cp "$HERE/bandanix_pil.py" "$APP/"
cat > "$BIN" <<EOF
#!/bin/sh
exec /usr/bin/python3 "$APP/bandanix_pil.py" "\$@"
EOF
chmod +x "$BIN"
cp "$HERE/systemd/bandanix-pil.service" "$HERE/systemd/bandanix-pil.timer" "$UNITS/"
if systemctl --user daemon-reload 2>/dev/null && systemctl --user enable --now bandanix-pil.timer 2>/dev/null; then
  echo "• Pil kontrolü açık: %$("$BIN" alt) altına inince bildirim gelir."
else
  echo "• Zamanlayıcı açılamadı; düşük pil bildirimi çalışmayacak."
fi

# 2) the hardware charge limit (only if this laptop has one)
if ! FILE=$(limit_file); then
  echo "• Bu bilgisayar donanımsal şarj sınırını desteklemiyor."
  echo "  Onun yerine şarj %$("$BIN" ust) olunca \"çıkarabilirsin\" bildirimi gelecek."
  exit 0
fi

UST=$("$BIN" ust)
if ! ask "Şarj %$UST'de dursun mu? (pilin ömrünü uzatır; gerektiğinde: bandanix-pil tam)"; then
  echo "• Şarj sınırı değiştirilmedi. Sonra açmak için: ./install.sh pil"
  exit 0
fi

ME=$(id -un)
if [[ ! "$ME" =~ ^[a-z_][a-z0-9_-]*$ ]]; then
  echo "• Kullanıcı adı beklenmedik karakterler içeriyor ($ME); şarj sınırı kurulmadı."
  exit 1
fi

# remember the limit from before Bandanix (only the first time, so a reinstall keeps it)
[ -f "$APP/onceki-sinir" ] || cat "$FILE" > "$APP/onceki-sinir"

echo "• Şarj sınırını yazan küçük yardımcı kuruluyor (şifren sorulabilir)."
sudo install -o root -g root -m 0755 "$HERE/bandanix-pil-yaz" "$HELPER"

TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT
printf '# Bandanix: %s may run only the charge-limit helper without a password.\n%s ALL=(root) NOPASSWD: %s\n' \
  "$ME" "$ME" "$HELPER" > "$TMP"
if ! sudo visudo -cqf "$TMP"; then
  echo "• sudoers satırı doğrulanamadı; şarj sınırı kurulmadı."
  exit 1
fi
sudo install -o root -g root -m 0440 "$TMP" "$SUDOERS"

sudo install -o root -g root -m 0644 "$HERE/systemd/bandanix-pil-sinir.service" "$SERVICE"
sudo systemctl daemon-reload
sudo systemctl enable bandanix-pil-sinir.service >/dev/null 2>&1

"$BIN" sinir "$UST"
echo "• Bu seferlik tam şarj için: bandanix-pil tam   ·   durum için: bandanix-pil"
