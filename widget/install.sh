#!/usr/bin/env bash
# description: Masaüstünde büyük saat, tarih, hava durumu ve sistem bilgisi (Cinnamon desklet)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APP="$DATA/bandanix/widget"
BIN="$HOME/.local/bin/bandanix-widget"
UNITS="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
UUID="bandanix-saat@furkansagsoyu"
DESKLETS="$DATA/cinnamon/desklets"
YEDEK="$HOME/.local/bin/bandanix-yedek"

if [ ! -x "$YEDEK" ]; then
  echo "• bandanix-yedek bulunamadı. Bu parçayı Bandanix klasöründeki ./install.sh ile kur."
  exit 1
fi

# 1) the bandanix-widget command (weather helper)
mkdir -p "$APP" "$(dirname "$BIN")" "$UNITS"
cp "$HERE/bandanix_widget.py" "$APP/"
cat > "$BIN" <<EOF
#!/bin/sh
exec /usr/bin/python3 "$APP/bandanix_widget.py" "\$@"
EOF
chmod +x "$BIN"

# 2) city for the weather (asked only the first time)
if ! "$BIN" _sehir-var; then
  if [ -t 0 ]; then
    until "$BIN" sehir; do
      read -rp "Tekrar denemek ister misin? [E/h] " again
      [[ "$again" =~ ^[hHnN] ]] && break
    done
  else
    echo "• Şehir sorulamadı. Sonra ayarlamak için: bandanix-widget sehir <şehir adı>"
  fi
else
  "$BIN" guncelle >/dev/null || true
fi

# 3) every 30 minutes
cp "$HERE/systemd/bandanix-hava.service" "$HERE/systemd/bandanix-hava.timer" "$UNITS/"
if ! { systemctl --user daemon-reload && systemctl --user enable --now bandanix-hava.timer; } 2>/dev/null; then
  echo "• Zamanlayıcı açılamadı; hava durumu elle güncellenebilir: bandanix-widget guncelle"
fi

# 4) the desklet itself, with this theme's accent and font
rm -rf "$DESKLETS/$UUID"
"$BIN" _desklet-kopyala "$HERE/desklet/$UUID" "$DESKLETS/$UUID"

# 5) put it on the desktop (old desklet list remembered for uninstall)
"$YEDEK" isaretle widget dconf:/org/cinnamon/enabled-desklets dconf:/org/cinnamon/next-desklet-id
"$BIN" _desklet-ac
echo "• Saat masaüstüne eklendi. Yerini değiştirmek için sürükleyebilirsin."
echo "• Şehri değiştirmek için: bandanix-widget sehir <şehir adı>"
