#!/usr/bin/env bash
# description: Kodla çizilen Bandanix duvar kağıtları, günün saatine göre değişen tonlar
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

if ! /usr/bin/python3 -c "import PIL" 2>/dev/null; then
  echo "• Resim kütüphanesi eksik, kuruluyor: python3-pil"
  sudo apt install python3-pil
fi
if [ ! -x "$YEDEK" ]; then
  echo "• bandanix-yedek bulunamadı. Bu parçayı Bandanix klasöründeki ./install.sh ile kur."
  exit 1
fi

# 1) draw the wallpapers at this screen's size
/usr/bin/python3 "$HERE/build_wallpapers.py" --hedef "$WALLS" --boyut "${BANDANIX_DUVAR_BOYUT:-otomatik}"

# 2) the bandanix-duvar command and the hourly timer
mkdir -p "$APP" "$(dirname "$BIN")" "$UNITS"
cp "$HERE/bandanix_duvar.py" "$APP/"
cat > "$BIN" <<EOF
#!/bin/sh
exec /usr/bin/python3 "$APP/bandanix_duvar.py" "\$@"
EOF
chmod +x "$BIN"
cp "$HERE/systemd/bandanix-duvar.service" "$HERE/systemd/bandanix-duvar.timer" "$UNITS/"

# 3) apply
if ask "Bandanix duvar kağıdı uygulansın mı?"; then
  "$YEDEK" isaretle duvar-kagidi \
    dconf:/org/cinnamon/desktop/background/picture-uri \
    dconf:/org/cinnamon/desktop/background/picture-options
  "$BIN" uygula
  if systemctl --user daemon-reload 2>/dev/null && systemctl --user enable --now bandanix-duvar.timer 2>/dev/null; then
    echo "• Günün saatine göre değişim açık (sabah, öğle, akşam, gece)."
  else
    echo "• Zamanlayıcı açılamadı; duvar kağıdı sabit kalacak. Sonra denemek için: bandanix-duvar ac"
  fi
  echo "• Stil değiştirmek için: bandanix-duvar gece | bandana | dalga | logo"
else
  echo "• Duvar kağıtları üretildi ama uygulanmadı: $WALLS"
fi
