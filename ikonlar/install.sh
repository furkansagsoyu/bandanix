#!/usr/bin/env bash
# description: Bandanix klasör ikonları ve kırmızı kenarlı imleç
# kurulu: ~/.local/share/icons/Bandanix
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ICON_SRC="${BANDANIX_IKON_KAYNAK:-/usr/share/icons/Mint-Y-Red}"
CURSOR_SRC="${BANDANIX_IMLEC_KAYNAK:-/usr/share/icons/Bibata-Modern-Classic}"
ICONS="${XDG_DATA_HOME:-$HOME/.local/share}/icons"
CURSORS="$HOME/.icons"   # the X11 cursor library looks here on every system
DEFAULT_CURSOR="$HOME/.icons/default/index.theme"
YEDEK="$HOME/.local/bin/bandanix-yedek"

ask() {
  local reply
  [ -t 0 ] || return 0
  read -rp "$1 [E/h] " reply
  [[ ! "$reply" =~ ^[hHnN] ]]
}

for src in "$ICON_SRC" "$CURSOR_SRC"; do
  if [ ! -d "$src" ]; then
    echo "• Kaynak tema bulunamadı: $src"
    echo "  Kurmak için: sudo apt install mint-y-icons bibata-cursor-theme"
    exit 1
  fi
done
if ! /usr/bin/python3 -c "import PIL" 2>/dev/null; then
  echo "• Resim kütüphanesi eksik, kuruluyor: python3-pil"
  sudo apt install python3-pil
fi
if [ ! -x "$YEDEK" ]; then
  echo "• bandanix-yedek bulunamadı. Bu parçayı Bandanix klasöründeki ./install.sh ile kur."
  exit 1
fi

# 1) build: icons into ~/.local/share/icons, cursor into ~/.icons
rm -rf "$ICONS/Bandanix-Imlec"   # old location used by the first version
/usr/bin/python3 "$HERE/build_icons.py" --ikon-kaynak "$ICON_SRC" \
  --imlec-kaynak "$CURSOR_SRC" --hedef-klasor "$ICONS" --imlec-klasor "$CURSORS"

# 2) icons
if ask "Bandanix ikonları uygulansın mı?"; then
  "$YEDEK" isaretle ikonlar \
    dconf:/org/cinnamon/desktop/interface/icon-theme \
    dconf:/org/gnome/desktop/interface/icon-theme
  dconf write /org/cinnamon/desktop/interface/icon-theme "'Bandanix'"
  dconf write /org/gnome/desktop/interface/icon-theme "'Bandanix'"
  echo "• İkonlar uygulandı."
else
  echo "• İkonlar kuruldu ama uygulanmadı (Sistem Ayarları → Temalar → Simgeler)."
fi

# 3) cursor
if ask "Bandanix imleci uygulansın mı?"; then
  "$YEDEK" isaretle ikonlar \
    dconf:/org/cinnamon/desktop/interface/cursor-theme \
    dconf:/org/gnome/desktop/interface/cursor-theme \
    "dosya:~/.icons/default/index.theme"
  # if it is already selected, switch away and back so Cinnamon reloads the files
  if [ "$(dconf read /org/cinnamon/desktop/interface/cursor-theme)" = "'Bandanix-Imlec'" ]; then
    dconf write /org/cinnamon/desktop/interface/cursor-theme "'Bibata-Modern-Classic'"
    sleep 1
  fi
  dconf write /org/cinnamon/desktop/interface/cursor-theme "'Bandanix-Imlec'"
  dconf write /org/gnome/desktop/interface/cursor-theme "'Bandanix-Imlec'"
  mkdir -p "$(dirname "$DEFAULT_CURSOR")"
  printf '[Icon Theme]\nInherits=Bandanix-Imlec\n' > "$DEFAULT_CURSOR"
  echo "• İmleç uygulandı. Her yerde görünmesi için oturumu bir kez kapatıp açman gerekebilir."
else
  echo "• İmleç kuruldu ama uygulanmadı (Sistem Ayarları → Temalar → Fare imleci)."
fi
