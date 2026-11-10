#!/usr/bin/env bash
set -euo pipefail

DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APP="$DATA/bandanix/spotify-tema"
BIN="$HOME/.local/bin/bandanix-spotify"
CONF="${XDG_CONFIG_HOME:-$HOME/.config}"

# 1) Spotify's own look back
if [[ -x $BIN ]]; then
  "$BIN" geri || true
  path=$(/usr/bin/python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import bandanix_spotify as b; print(b.detect()["yol"])' "$APP" 2>/dev/null || true)
else
  path=""
fi

# 2) the write permission Spicetify needed is taken back (Spotify's folder is root's again)
if [[ -n $path && -d $path && $path == /* && $path != "$HOME"* ]] && [[ -w $path ]]; then
  echo "• Spotify klasörünün izinleri eski hâline dönüyor (şifren sorulabilir)."
  sudo chmod -R go-w "$path" || echo "• İzinler değiştirilemedi; sorun değil, Spotify yine çalışır."
fi

# 3) our files; Spicetify too if we installed it
if [[ -f $APP/spicetify-bizden ]]; then
  rm -rf "$HOME/.spicetify" "$CONF/spicetify"
  echo "• Spicetify kaldırıldı."
else
  rm -rf "$CONF/spicetify/Themes/Bandanix"
fi
rm -rf "$APP"
rm -f "$BIN" "$CONF/autostart/bandanix-spotify.desktop"
echo "• Bandanix Spotify teması kaldırıldı."
