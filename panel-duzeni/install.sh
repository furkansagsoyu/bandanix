#!/usr/bin/env bash
# description: Yüzen panel adaları: ortada menü ve pencereler, sağda tepsi
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THEME_CSS="$HOME/.themes/Bandanix/cinnamon/cinnamon.css"
MARKER="${XDG_DATA_HOME:-$HOME/.local/share}/bandanix/panel-duzeni/aktif"
YEDEK="$HOME/.local/bin/bandanix-yedek"

if [ ! -f "$THEME_CSS" ]; then
  echo "• Panel adaları Bandanix Cinnamon temasının üzerine kurulur."
  echo "  Önce temayı kur: ./install.sh cinnamon-tema"
  exit 1
fi
if [ ! -x "$YEDEK" ]; then
  echo "• bandanix-yedek bulunamadı. Bu parçayı Bandanix klasöründeki ./install.sh ile kur."
  exit 1
fi

# remember the applet layout and panel height before touching them
"$YEDEK" isaretle panel-duzeni dconf:/org/cinnamon/enabled-applets dconf:/org/cinnamon/panels-height \
  dconf:/org/cinnamon/panel-zone-icon-sizes

/usr/bin/python3 "$HERE/panel.py" uygula "$THEME_CSS"
mkdir -p "$(dirname "$MARKER")"
touch "$MARKER"   # tells the theme builder to keep the islands when the theme is rebuilt

echo "• Panel adaları uygulandı (düzen ve ikon boyutu: theme.toml → [panel])."
echo "• Panel bir saniyeliğine yenilenebilir; açık pencerelerin etkilenmez."
