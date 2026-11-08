#!/usr/bin/env bash
# description: floating now-playing island for Spotify and other players
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ID="bandanix-sound-island"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APP_DIR="$DATA/bandanix/sound-island"
BIN="$HOME/.local/bin/sound-island"
DESKTOP="$DATA/applications/$ID.desktop"
ICON="$DATA/icons/hicolor/scalable/apps/$ID.svg"
AUTOSTART="${XDG_CONFIG_HOME:-$HOME/.config}/autostart/$ID.desktop"
PY=/usr/bin/python3   # system Python on purpose, so conda/pyenv don't interfere

ask() {
  local reply
  [ -t 0 ] || return 0
  read -rp "$1 [Y/n] " reply
  [[ ! "$reply" =~ ^[nN] ]]
}

# 1) system packages
missing=()
for pkg in playerctl python3-venv libxcb-cursor0; do
  dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -q "install ok installed" \
    || missing+=("$pkg")
done
if [ ${#missing[@]} -gt 0 ]; then
  echo "• Installing system packages: ${missing[*]}"
  sudo apt install "${missing[@]}"
fi

# 2) app files + private Python environment
echo "• Copying files to $APP_DIR"
mkdir -p "$APP_DIR"
rm -rf "$APP_DIR/sound_island"
cp -r "$HERE/sound_island" "$HERE/requirements.txt" "$APP_DIR/"
if [ ! -x "$APP_DIR/.venv/bin/python" ]; then
  echo "• Creating Python environment"
  "$PY" -m venv "$APP_DIR/.venv"
fi
echo "• Installing Python dependencies (first time can take a minute)"
"$APP_DIR/.venv/bin/pip" install --quiet --disable-pip-version-check -r "$APP_DIR/requirements.txt"

# 3) launcher command, icon, app menu entry
mkdir -p "$(dirname "$BIN")" "$(dirname "$DESKTOP")" "$(dirname "$ICON")"
cat > "$BIN" <<EOF
#!/usr/bin/env bash
export PYTHONPATH="$APP_DIR"
exec "$APP_DIR/.venv/bin/python" -m sound_island "\$@"
EOF
chmod +x "$BIN"
cp "$HERE/data/$ID.svg" "$ICON"

cat > "$DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Name=Sound Island
Comment=Floating now-playing island (Bandanix)
Exec=$BIN
Icon=$ID
Terminal=false
Categories=AudioVideo;Audio;Utility;
StartupNotify=false
EOF
echo "• Added to the app menu: Sound Island"

# 4) optional autostart
if ask "Start Sound Island automatically when you log in?"; then
  mkdir -p "$(dirname "$AUTOSTART")"
  { cat "$DESKTOP"; echo "X-GNOME-Autostart-enabled=true"; } > "$AUTOSTART"
  echo "• Autostart on"
else
  rm -f "$AUTOSTART"
  echo "• Autostart off"
fi

# 5) restart it with the new version
pkill -f "python -m sound_island" 2>/dev/null || true
if ask "Start Sound Island now?"; then
  sleep 0.5
  setsid "$BIN" >/dev/null 2>&1 < /dev/null &
  echo "• Running. Play something in Spotify; right-click the island to quit."
fi
