#!/usr/bin/env bash
# description: Güç modları (Serin, Eco, Dengeli, Turbo), fan modu ve Cooler Boost; bandanix-guc komutu
# kurulu: ~/.local/bin/bandanix-guc
# yetki: sudo
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APP="$DATA/bandanix/guc"
BIN="$HOME/.local/bin/bandanix-guc"
HELPER=/usr/local/sbin/bandanix-guc-yaz
SUDOERS=/etc/sudoers.d/bandanix-guc
SERVICE=/etc/systemd/system/bandanix-guc.service
EC=/sys/devices/platform/msi-ec
NO_TURBO=/sys/devices/system/cpu/intel_pstate/no_turbo
BOOST=/sys/devices/system/cpu/cpufreq/boost

if [ ! -d "$EC" ] && [ ! -f "$NO_TURBO" ] && [ ! -f "$BOOST" ]; then
  echo "• Bu bilgisayarda ayarlanabilir güç modu bulunamadı; bu parça kurulmadı."
  exit 0
fi
ME=$(id -un)
if [[ ! "$ME" =~ ^[a-z_][a-z0-9_-]*$ ]]; then
  echo "• Kullanıcı adı beklenmedik karakterler içeriyor ($ME); kurulmadı."
  exit 1
fi

# 1) the bandanix-guc command
mkdir -p "$APP" "$(dirname "$BIN")"
cp "$HERE/bandanix_guc.py" "$APP/"
cat > "$BIN" <<EOF
#!/bin/sh
exec /usr/bin/python3 "$APP/bandanix_guc.py" "\$@"
EOF
chmod +x "$BIN"

# 2) remember how things were before Bandanix (only the first time)
if [ ! -f "$APP/onceki" ]; then
  shift_mode=$(cat "$EC/shift_mode" 2>/dev/null || echo -)
  fan_mode=$(cat "$EC/fan_mode" 2>/dev/null || echo -)
  turbo=-
  [ -f "$NO_TURBO" ] && { [ "$(cat "$NO_TURBO")" = 0 ] && turbo=on || turbo=off; }
  [ ! -f "$NO_TURBO" ] && [ -f "$BOOST" ] && { [ "$(cat "$BOOST")" = 1 ] && turbo=on || turbo=off; }
  echo "${shift_mode:--} ${fan_mode:--} $turbo" > "$APP/onceki"
fi

# 3) the root helper, the permission to run it, and the boot/resume service
echo "• Güç modunu yazan küçük yardımcı kuruluyor (şifren sorulabilir)."
sudo install -o root -g root -m 0755 "$HERE/bandanix-guc-yaz" "$HELPER"
TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT
printf '# Bandanix: %s may run only the power-mode helper without a password.\n%s ALL=(root) NOPASSWD: %s\n' \
  "$ME" "$ME" "$HELPER" > "$TMP"
if ! sudo visudo -cqf "$TMP"; then
  echo "• sudoers satırı doğrulanamadı; kurulmadı."
  exit 1
fi
sudo install -o root -g root -m 0440 "$TMP" "$SUDOERS"
sudo install -o root -g root -m 0644 "$HERE/systemd/bandanix-guc.service" "$SERVICE"
sudo systemctl daemon-reload
sudo systemctl enable bandanix-guc.service >/dev/null 2>&1

echo
"$BIN"
echo
echo "• Mod değiştirmek için: bandanix-guc serin   (ya da Bandanix Ayarlar → Performans)"
