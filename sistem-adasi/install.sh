#!/usr/bin/env bash
# description: Sistem adası: işlemci, sıcaklık, RAM ya da disk sınırı aşınca beliren uyarı hapı
# kurulu: ~/.local/bin/bandanix-sistem
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APP="$DATA/bandanix/sistem-adasi"
BIN="$HOME/.local/bin/bandanix-sistem"

# 1) shared island environment (Qt), used only by the pill itself
source "$HERE/../ortak/ada/kur.sh"
ada_kur

# 2) files and commands: the watcher runs on the system Python (no Qt), the pill on the island env
mkdir -p "$APP" "$(dirname "$BIN")"
rm -rf "$APP/bandanix_sistem"
cp -r "$HERE/bandanix_sistem" "$APP/"
cat > "$BIN" <<EOF
#!/bin/sh
export PYTHONPATH="$APP:$ADA_DIR/lib"
exec /usr/bin/python3 -m bandanix_sistem "\$@"
EOF
cat > "$APP/ada-baslat" <<EOF
#!/bin/sh
export PYTHONPATH="$APP:$ADA_DIR/lib"
exec "$ADA_PY" -m bandanix_sistem _ada
EOF
chmod +x "$BIN" "$APP/ada-baslat"

# 3) (re)start watching with the new version
"$BIN" kapat >/dev/null
"$BIN" ac
echo
"$BIN"
echo
echo "• Sağlıklı bir bilgisayarda ada görünmez. Görünüşünü denemek için: bandanix-sistem dene"
