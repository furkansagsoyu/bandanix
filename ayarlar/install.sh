#!/usr/bin/env bash
# description: Bandanix Ayarlar: bütün parçaların ayarları tek pencerede (bandanix komutu)
# kurulu: ~/.local/bin/bandanix
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APP="$DATA/bandanix/ayarlar"
BIN="$HOME/.local/bin/bandanix"
DESKTOP="$DATA/applications/bandanix-ayarlar.desktop"
ICON="$DATA/icons/hicolor/scalable/apps/bandanix-ayarlar.svg"

if ! /usr/bin/python3 -c "import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk" 2>/dev/null; then
  echo "• GTK bağlantısı eksik, kuruluyor: python3-gi gir1.2-gtk-3.0"
  sudo apt install python3-gi gir1.2-gtk-3.0
fi

# 1) the app and the bandanix command
mkdir -p "$APP" "$(dirname "$BIN")" "$(dirname "$DESKTOP")" "$(dirname "$ICON")"
rm -rf "$APP/bandanix_ayarlar"
cp -r "$HERE/bandanix_ayarlar" "$APP/"
echo "$ROOT" > "$DATA/bandanix/kaynak"          # installers live here
cat > "$BIN" <<EOF
#!/bin/sh
export PYTHONPATH="$APP"
exec /usr/bin/python3 -m bandanix_ayarlar "\$@"
EOF
chmod +x "$BIN"

# 2) menu entry with the bandana icon in this theme's colour
/usr/bin/python3 - "$HERE/data/bandanix-ayarlar.svg" "$ICON" <<'PY'
import re, sys, tomllib
from pathlib import Path
try:
    accent = tomllib.loads((Path.home() / ".config/bandanix/theme.toml").read_text())["colors"]["accent"]
except Exception:
    accent = "#C8102E"
if not re.fullmatch(r"#[0-9A-Fa-f]{6}", str(accent)):
    accent = "#C8102E"
rgb = ",".join(str(int(accent[i:i + 2], 16)) for i in (1, 3, 5))
Path(sys.argv[2]).write_text(Path(sys.argv[1]).read_text().replace("rgb(200,16,46)", f"rgb({rgb})"))
PY
cat > "$DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Name=Bandanix Ayarlar
Comment=Bandanix masaüstü kitinin ayarları
Exec=$BIN
Icon=bandanix-ayarlar
Terminal=false
Categories=Settings;DesktopSettings;
Keywords=bandanix;tema;duvar;panel;ada;pil;kısayol;yedek;
StartupNotify=true
EOF
gtk-update-icon-cache -q -t "$DATA/icons/hicolor" 2>/dev/null || true
echo "• Menüye eklendi: Bandanix Ayarlar  ·  terminalden: bandanix"
