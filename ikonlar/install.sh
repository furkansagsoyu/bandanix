#!/usr/bin/env bash
# description: Bandanix klasör ikonları ve kırmızı kenarlı imleç
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ICON_SRC="${BANDANIX_IKON_KAYNAK:-/usr/share/icons/Mint-Y-Red}"
CURSOR_SRC="${BANDANIX_IMLEC_KAYNAK:-/usr/share/icons/Bibata-Modern-Classic}"
ICONS="${XDG_DATA_HOME:-$HOME/.local/share}/icons"
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

# 1) build both themes into ~/.local/share/icons
/usr/bin/python3 "$HERE/build_icons.py" --ikon-kaynak "$ICON_SRC" \
  --imlec-kaynak "$CURSOR_SRC" --hedef-klasor "$ICONS"

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
  dconf write /org/cinnamon/desktop/interface/cursor-theme "'Bandanix-Imlec'"
  dconf write /org/gnome/desktop/interface/cursor-theme "'Bandanix-Imlec'"
  mkdir -p "$(dirname "$DEFAULT_CURSOR")"
  printf '[Icon Theme]\nInherits=Bandanix-Imlec\n' > "$DEFAULT_CURSOR"
  echo "• İmleç uygulandı. Bazı açık uygulamalar yeni imleci yeniden açılınca gösterir."
else
  echo "• İmleç kuruldu ama uygulanmadı (Sistem Ayarları → Temalar → Fare imleci)."
fi
