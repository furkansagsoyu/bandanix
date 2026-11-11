#!/usr/bin/env bash
# description: Saat, hava durumu, müzik, ayarlar ve bildirimler için üst kenar adası
# kurulu: ~/.local/bin/sound-island
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ID="bandanix-sound-island"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APP_DIR="$DATA/bandanix/sound-island"
BIN="$HOME/.local/bin/sound-island"
DESKTOP="$DATA/applications/$ID.desktop"
ICON="$DATA/icons/hicolor/scalable/apps/$ID.svg"
AUTOSTART="${XDG_CONFIG_HOME:-$HOME/.config}/autostart/$ID.desktop"

ask() {
  local reply
  [ -t 0 ] || return 0
  read -rp "$1 [E/h] " reply
  [[ ! "$reply" =~ ^[hHnN] ]]
}

# 1) system packages for Sound Island itself
missing=()
for pkg in playerctl cava python3-gi; do
  dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -q "install ok installed" \
    || missing+=("$pkg")
done
if [ ${#missing[@]} -gt 0 ]; then
  echo "• Sistem paketleri kuruluyor: ${missing[*]}"
  sudo apt install "${missing[@]}"
fi

# 2) shared island environment (Qt) + app files
source "$HERE/../ortak/ada/kur.sh"
ada_kur
echo "• Dosyalar kopyalanıyor: $APP_DIR"
mkdir -p "$APP_DIR"
rm -rf "$APP_DIR/sound_island" "$APP_DIR/.venv" "$APP_DIR/requirements.txt"   # old private env
mkdir -p "$APP_DIR/sound_island"
cp "$HERE"/sound_island/*.py "$APP_DIR/sound_island/"
cp "$HERE/../widget/bandanix_widget.py" "$APP_DIR/"

# 3) Komut ve eski uygulama menüsü kaydının temizlenmesi
mkdir -p "$(dirname "$BIN")"
rm -f -- "$DESKTOP" "$ICON"
cat > "$BIN" <<EOF
#!/usr/bin/env bash
export PYTHONPATH="$APP_DIR:$ADA_DIR/lib"
export QT_QPA_PLATFORM=xcb      # the island places itself on screen; Wayland does not allow that
exec "$ADA_PY" -m sound_island "\$@"
EOF
chmod +x "$BIN"
# 4) volume / brightness indicator replaces Cinnamon's own on-screen display
YEDEK="$HOME/.local/bin/bandanix-yedek"
OSD_KEY=/org/cinnamon/show-media-keys-osd
INDICATOR=$(PYTHONPATH="$HERE" /usr/bin/python3 -c "from sound_island.config import load_theme; print(load_theme().gosterge)")
if gsettings writable org.cinnamon show-media-keys-osd >/dev/null 2>&1 && [ -x "$YEDEK" ]; then
  if [ "$INDICATOR" = "True" ]; then
    "$YEDEK" isaretle sound-island "dconf:$OSD_KEY"
    # a true/false switch on current Cinnamon, a size choice ("disabled", "small"...) on old ones
    if gsettings range org.cinnamon show-media-keys-osd 2>/dev/null | grep -q "^type b"; then
      dconf write "$OSD_KEY" "false"
    else
      dconf write "$OSD_KEY" "'disabled'"
    fi
    echo "• Ses ve parlaklık göstergesi adada; Cinnamon'ın kendi göstergesi kapatıldı."
  else
    "$YEDEK" geri-al sound-island >/dev/null
    echo "• Ada göstergesi kapalı (theme.toml: gosterge = false); Cinnamon'ın göstergesi açık."
  fi
fi

# 5) optional autostart
if ask "Bandanix adası oturum açınca otomatik başlasın mı?"; then
  mkdir -p "$(dirname "$AUTOSTART")"
  cat > "$AUTOSTART" <<EOF
[Desktop Entry]
Type=Application
Name=Bandanix Adası
Exec="$BIN"
NoDisplay=true
Terminal=false
StartupNotify=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=4
EOF
  echo "• Otomatik başlatma açık"
else
  rm -f "$AUTOSTART"
  echo "• Otomatik başlatma kapalı"
fi

# 6) restart it with the new version
pkill -f "python -m sound_island" 2>/dev/null || true
if ask "Bandanix adası şimdi başlatılsın mı?"; then
  sleep 0.5
  setsid "$BIN" >/dev/null 2>&1 < /dev/null &
  echo "• Çalışıyor. Adayı açmak için üzerine gel, sekmeler arasında geçmek için kaydır."
fi
