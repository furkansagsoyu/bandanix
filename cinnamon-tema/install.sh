#!/usr/bin/env bash
# description: Mint-Y tabanlı koyu Bandanix teması (pencereler, panel, menüler)
# kurulu: ~/.themes/Bandanix/gtk-3.0
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="${BANDANIX_TEMA_KAYNAK:-/usr/share/themes/Mint-Y-Dark-Red}"
THEME_DIR="$HOME/.themes/Bandanix"
GTK4_CSS="${XDG_CONFIG_HOME:-$HOME/.config}/gtk-4.0/gtk.css"
YEDEK="$HOME/.local/bin/bandanix-yedek"

ask() {
  local reply
  [ -t 0 ] || return 0
  read -rp "$1 [E/h] " reply
  [[ ! "$reply" =~ ^[hHnN] ]]
}

if [ ! -d "$SOURCE" ]; then
  echo "• Mint-Y-Dark-Red teması bulunamadı ($SOURCE)."
  echo "  Kurmak için: sudo apt install mint-themes"
  exit 1
fi
if [ ! -x "$YEDEK" ]; then
  echo "• bandanix-yedek bulunamadı. Bu parçayı Bandanix klasöründeki ./install.sh ile kur."
  exit 1
fi

# 1) build the theme into ~/.themes/Bandanix (from the Mint theme on this computer)
/usr/bin/python3 "$HERE/build_theme.py" --kaynak "$SOURCE" --hedef "$THEME_DIR" \
  --gtk4-css "$THEME_DIR/bandanix-gtk4.css"

# panel islands installed? keep them in the freshly built theme
if [ -f "${XDG_DATA_HOME:-$HOME/.local/share}/bandanix/panel-duzeni/aktif" ]; then
  /usr/bin/python3 "$HERE/../panel-duzeni/panel.py" css "$THEME_DIR/cinnamon/cinnamon.css"
  echo "• Panel adaları yeni temaya da eklendi."
fi

# 2) apply it, after remembering every setting we are about to change
if ask "Bandanix teması şimdi uygulansın mı?"; then
  "$YEDEK" isaretle cinnamon-tema \
    dconf:/org/cinnamon/desktop/interface/gtk-theme \
    dconf:/org/cinnamon/theme/name \
    dconf:/org/gnome/desktop/interface/gtk-theme \
    dconf:/org/gnome/desktop/interface/color-scheme \
    "dosya:~/.config/gtk-4.0/gtk.css"

  mkdir -p "$(dirname "$GTK4_CSS")"
  cp "$THEME_DIR/bandanix-gtk4.css" "$GTK4_CSS"
  dconf write /org/cinnamon/desktop/interface/gtk-theme "'Bandanix'"
  dconf write /org/cinnamon/theme/name "'Bandanix'"
  dconf write /org/gnome/desktop/interface/gtk-theme "'Bandanix'"
  dconf write /org/gnome/desktop/interface/color-scheme "'prefer-dark'"
  echo "• Tema uygulandı. Açık olan bazı uygulamalar yeni görünümü yeniden açılınca alır."
else
  echo "• Tema kuruldu ama uygulanmadı. İstediğinde: Sistem Ayarları → Temalar → Bandanix"
fi
