#!/usr/bin/env bash
# description: Bandanix duvar kağıtları: Kemer, Galata, Gün Batımı, İpek
# kurulu: ~/.local/bin/bandanix-duvar
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
WALLS="$DATA/backgrounds/bandanix"
APP="$DATA/bandanix/duvar-kagidi"
BIN="$HOME/.local/bin/bandanix-duvar"
UNITS="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
YEDEK="$HOME/.local/bin/bandanix-yedek"

ask() {
  local reply
  [ -t 0 ] || return 0
  read -rp "$1 [E/h] " reply
  [[ ! "$reply" =~ ^[hHnN] ]]
}

if [ ! -x "$YEDEK" ]; then
  echo "• bandanix-yedek bulunamadı. Bu parçayı Bandanix klasöründeki ./install.sh ile kur."
  exit 1
fi

# 0) the old drawn wallpapers and their hourly timer are gone
if [ -f "$UNITS/bandanix-duvar.timer" ]; then
  systemctl --user disable --now bandanix-duvar.timer 2>/dev/null || true
  rm -f "$UNITS/bandanix-duvar.timer" "$UNITS/bandanix-duvar.service"
  systemctl --user daemon-reload 2>/dev/null || true
fi
rm -f "$WALLS"/bandanix-*-*.png

# 1) the pictures and the bandanix-duvar command
mkdir -p "$WALLS" "$APP" "$(dirname "$BIN")"
cp "$HERE"/resimler/* "$WALLS/"
cp "$HERE/bandanix_duvar.py" "$APP/"
cat > "$BIN" <<EOF
#!/bin/sh
exec /usr/bin/python3 "$APP/bandanix_duvar.py" "\$@"
EOF
chmod +x "$BIN"

# 2) apply (the wallpaper you had before is remembered for uninstall)
if ask "Bandanix duvar kağıdı uygulansın mı?"; then
  "$YEDEK" isaretle duvar-kagidi \
    dconf:/org/cinnamon/desktop/background/picture-uri \
    dconf:/org/cinnamon/desktop/background/picture-options
  "$BIN" uygula
fi
echo
"$BIN"
