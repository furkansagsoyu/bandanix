#!/usr/bin/env bash
# description: Hızlı not kutusu: Super+N ile aç, yaz, Enter; notlar ~/Notlar içinde
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APP="$DATA/bandanix/not-kutusu"
BIN="$HOME/.local/bin/bandanix-not"
YEDEK="$HOME/.local/bin/bandanix-yedek"

if ! /usr/bin/python3 -c "import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk" 2>/dev/null; then
  echo "• GTK bağlantısı eksik, kuruluyor: python3-gi gir1.2-gtk-3.0"
  sudo apt install python3-gi gir1.2-gtk-3.0
fi
if [ ! -x "$YEDEK" ]; then
  echo "• bandanix-yedek bulunamadı. Bu parçayı Bandanix klasöründeki ./install.sh ile kur."
  exit 1
fi

# 1) the bandanix-not command
mkdir -p "$APP" "$(dirname "$BIN")"
cp "$HERE/bandanix_not.py" "$HERE/notes.py" "$HERE/not_kutusu_ui.py" "$APP/"
cat > "$BIN" <<EOF
#!/bin/sh
exec /usr/bin/python3 "$APP/bandanix_not.py" "\$@"
EOF
chmod +x "$BIN"

# 2) the keyboard shortcut (old values remembered so uninstall puts them back)
KISAYOL="$HERE/../core/bandanix_kisayol.py"
mapfile -t MARKS < <(/usr/bin/python3 "$KISAYOL" isaretler bandanix-not)
"$YEDEK" isaretle not-kutusu "${MARKS[@]}"
if ! /usr/bin/python3 "$KISAYOL" kur bandanix-not "Bandanix hızlı not" "$BIN" "$("$BIN" _kisayol-ayari)" "<Primary><Alt>n"; then
  echo "  theme.toml içindeki [not-kutusu] kisayol değerini değiştirip yeniden kur."
fi

echo "• Notlar şuraya kaydedilir: $("$BIN" _dosya-yolu)"
echo "• Terminalden: bandanix-not \"metin\"  ·  bandanix-not liste  ·  bandanix-not dosya"
