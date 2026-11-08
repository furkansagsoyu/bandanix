#!/usr/bin/env bash
# description: Pano geçmişi: Super+V ile son kopyaladıkların, arama, sabitleme ve otomatik yapıştırma
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APP="$DATA/bandanix/pano"
BIN="$HOME/.local/bin/bandanix-pano"
AUTOSTART="${XDG_CONFIG_HOME:-$HOME/.config}/autostart/bandanix-pano.desktop"
YEDEK="$HOME/.local/bin/bandanix-yedek"

if [ ! -x "$YEDEK" ]; then
  echo "• bandanix-yedek bulunamadı. Bu parçayı Bandanix klasöründeki ./install.sh ile kur."
  exit 1
fi
missing=()
/usr/bin/python3 -c "import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk" 2>/dev/null \
  || missing+=(python3-gi gir1.2-gtk-3.0)
command -v xdotool >/dev/null || missing+=(xdotool)
command -v xprop >/dev/null || missing+=(x11-utils)
if [ ${#missing[@]} -gt 0 ]; then
  echo "• Sistem paketleri kuruluyor: ${missing[*]}"
  sudo apt install "${missing[@]}"
fi

# 1) the bandanix-pano command
mkdir -p "$APP" "$(dirname "$BIN")" "$(dirname "$AUTOSTART")"
cp "$HERE/bandanix_pano.py" "$HERE/pano_gecmis.py" "$HERE/pano_bekci.py" "$HERE/pano_ui.py" "$APP/"
cat > "$BIN" <<EOF
#!/bin/sh
exec /usr/bin/python3 "$APP/bandanix_pano.py" "\$@"
EOF
chmod +x "$BIN"

# 2) the clipboard watcher: at every login, and now (restarted with the new version)
cat > "$AUTOSTART" <<EOF
[Desktop Entry]
Type=Application
Name=Bandanix pano geçmişi
Comment=Kopyalananları Super+V listesi için saklar
Exec=$BIN _bekci
Terminal=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
EOF
pkill -f "bandanix_pano.py _bekci" 2>/dev/null || true
sleep 0.3
setsid "$BIN" _bekci >/dev/null 2>&1 < /dev/null &

# 3) the keyboard shortcut (old values remembered so uninstall puts them back)
KISAYOL="$HERE/../core/bandanix_kisayol.py"
mapfile -t MARKS < <(/usr/bin/python3 "$KISAYOL" isaretler bandanix-pano)
"$YEDEK" isaretle pano "${MARKS[@]}"
if ! /usr/bin/python3 "$KISAYOL" kur bandanix-pano "Bandanix pano geçmişi" "$BIN" "$("$BIN" _kisayol-ayari)" "<Primary><Alt>v"; then
  echo "  theme.toml içindeki [pano] kisayol değerini değiştirip yeniden kur."
fi
echo "• Bundan sonra kopyaladıkların listeye girer. Terminalden: bandanix-pano liste"
