# shellcheck shell=bash
# Sourced by island installers (Sound Island, Sistem adası).
# One Python environment with Qt for every island: ~/.local/share/bandanix/ada
ADA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/bandanix/ada"
ADA_PY="$ADA_DIR/.venv/bin/python"

ada_kur() {
  local here pkg missing=()
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  for pkg in python3-venv libxcb-cursor0; do
    dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -q "install ok installed" \
      || missing+=("$pkg")
  done
  if [ ${#missing[@]} -gt 0 ]; then
    echo "• Sistem paketleri kuruluyor: ${missing[*]}"
    sudo apt install "${missing[@]}"
  fi
  mkdir -p "$ADA_DIR/lib"
  rm -rf "$ADA_DIR/lib/bandanix_ada"
  cp -r "$here/bandanix_ada" "$ADA_DIR/lib/"
  if [ ! -x "$ADA_PY" ]; then
    echo "• Adalar için ortak Python ortamı oluşturuluyor: $ADA_DIR"
    /usr/bin/python3 -m venv "$ADA_DIR/.venv"
  fi
  echo "• Qt kuruluyor ya da güncelleniyor (ilk seferde bir dakika sürebilir)"
  "$ADA_DIR/.venv/bin/pip" install --quiet --disable-pip-version-check -r "$here/requirements.txt"
}

# Remove the shared environment once no island uses it any more.
ada_temizle() {
  local data="${XDG_DATA_HOME:-$HOME/.local/share}/bandanix"
  if [ ! -d "$data/sound-island" ] && [ ! -d "$data/sistem-adasi" ]; then
    rm -rf "$ADA_DIR"
    echo "• Adaların ortak Python ortamı da kaldırıldı."
  fi
}
