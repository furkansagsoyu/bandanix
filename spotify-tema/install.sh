#!/usr/bin/env bash
# description: Spotify teması: koyu gri zemin, yeşil yerine bandana kırmızısı (Spicetify ile)
# kurulu: ~/.local/share/bandanix/spotify-tema/bandanix_spotify.py
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APP="$DATA/bandanix/spotify-tema"
BIN="$HOME/.local/bin/bandanix-spotify"
AUTOSTART="${XDG_CONFIG_HOME:-$HOME/.config}/autostart/bandanix-spotify.desktop"
SPICE_DIR="$HOME/.spicetify"

# 1) our files and the bandanix-spotify command
mkdir -p "$APP/Bandanix" "$(dirname "$BIN")" "$(dirname "$AUTOSTART")"
cp "$HERE/bandanix_spotify.py" "$APP/"
cp "$HERE"/tema/Bandanix/* "$APP/Bandanix/"
cat > "$BIN" <<SH
#!/bin/sh
exec /usr/bin/python3 "$APP/bandanix_spotify.py" "\$@"
SH
chmod +x "$BIN"

# 2) is Spotify here, and not a snap?
case "$("$BIN" _tur)" in
  snap)
    echo "• Spotify Snap ile kurulu. Snap uygulamaları değiştirilemediği için tema uygulanamaz."
    echo "  Deb sürümüne geçiş için: $HERE/README.md → \"Snap'ten geçiş\". Sonra: ./install.sh spotify-tema"
    exit 0 ;;
  yok)
    echo "• Spotify bulunamadı. Spotify'ı kurduktan sonra: ./install.sh spotify-tema"
    exit 0 ;;
esac

# 3) Spicetify, from its official GitHub release, into ~/.spicetify (no changes to ~/.bashrc)
if [[ -x $SPICE_DIR/spicetify ]] || command -v spicetify >/dev/null; then
  echo "• Spicetify zaten kurulu."
else
  case "$(uname -m)" in
    x86_64) arch=amd64 ;;
    aarch64|arm64) arch=arm64 ;;
    *) echo "• Bu işlemci için Spicetify sürümü yok: $(uname -m)"; exit 1 ;;
  esac
  echo "• Spicetify indiriliyor (github.com/spicetify/cli)"
  url=$(curl -fsSL https://api.github.com/repos/spicetify/cli/releases/latest | /usr/bin/python3 -c '
import json, sys
arch = sys.argv[1]
for a in json.load(sys.stdin)["assets"]:
    if a["name"].endswith(f"linux-{arch}.tar.gz"):
        print(a["browser_download_url"])
        break' "$arch")
  if [[ -z $url ]]; then
    echo "• Spicetify'ın indirme adresi bulunamadı; internet bağlantını kontrol edip yeniden dene."
    exit 1
  fi
  tmp=$(mktemp -d)
  trap 'rm -rf "$tmp"' EXIT
  curl -fsSL "$url" -o "$tmp/spicetify.tar.gz"
  mkdir -p "$SPICE_DIR"
  tar -xzf "$tmp/spicetify.tar.gz" -C "$SPICE_DIR"
  chmod +x "$SPICE_DIR/spicetify"
  touch "$APP/spicetify-bizden"          # uninstall removes Spicetify only if we put it here
  echo "• Spicetify kuruldu: $("$SPICE_DIR/spicetify" -v)"
fi

# 4) once per login: re-apply after a Spotify update
cat > "$AUTOSTART" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Bandanix Spotify teması
Comment=Spotify güncellendiyse Bandanix temasını yeniden uygular
Exec=$BIN _oturum
NoDisplay=true
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=15
DESKTOP

# 5) apply (Spotify restarts if it is open)
"$BIN" uygula
