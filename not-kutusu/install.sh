#!/usr/bin/env bash
# description: Hızlı not kutusu: Super+N ile aç, yaz, Enter; notlar ~/Notlar içinde
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APP="$DATA/bandanix/not-kutusu"
BIN="$HOME/.local/bin/bandanix-not"
YEDEK="$HOME/.local/bin/bandanix-yedek"
KEYS=/org/cinnamon/desktop/keybindings
CUSTOM="$KEYS/custom-keybindings/bandanix-not"

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
"$YEDEK" isaretle not-kutusu \
  "dconf:$KEYS/custom-list" \
  "dconf:$CUSTOM/name" "dconf:$CUSTOM/command" "dconf:$CUSTOM/binding"
"$BIN" _kisayol "$HOME" || true

echo "• Notlar şuraya kaydedilir: $("$BIN" _dosya-yolu)"
echo "• Terminalden: bandanix-not \"metin\"  ·  bandanix-not liste  ·  bandanix-not dosya"
