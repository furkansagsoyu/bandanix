#!/usr/bin/env bash
# Root part of the boot screen component, run once through sudo by install.sh / uninstall.sh.
#   kok.sh kur SOURCE_DIR     copy the themes, make them the default, rebuild GRUB and initramfs
#   kok.sh kaldir             give Mint's own boot screen and GRUB theme back
# BANDANIX_KOK points every path into a test folder (tests only).
set -euo pipefail

K="${BANDANIX_KOK:-}"
PLY="$K/usr/share/plymouth/themes/bandanix"
ALT_LINK="$K/usr/share/plymouth/themes/default.plymouth"
GRUBT="$K/boot/grub/themes/bandanix"
CFG="$K/etc/default/grub.d/99-bandanix.cfg"

say() { echo "• $*"; }

[[ $(id -u) -eq 0 || -n $K ]] || { echo "kok.sh sudo ile çalışmalı" >&2; exit 1; }

font_file() {
  local f
  for f in "$K/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf" "$(fc-match -f '%{file}' 'DejaVu Sans' 2>/dev/null || true)" \
           "$(fc-match -f '%{file}' sans 2>/dev/null || true)"; do
    [[ -n $f && -f $f ]] && { echo "$f"; return 0; }
  done
  return 1
}

# the name GRUB knows a .pf2 font by is stored inside the file ("NAME" section)
pf2_name() {
  python3 - "$1" <<'PY'
import struct, sys
data = open(sys.argv[1], "rb").read()
i = 0
while i + 8 <= len(data):
    tag, size = data[i:i + 4], struct.unpack(">I", data[i + 4:i + 8])[0]
    if tag == b"NAME":
        print(data[i + 8:i + 8 + size].rstrip(b"\0").decode())
        break
    i += 8 + size
PY
}

install_plymouth() {
  local src=$1
  if [[ ! -d $K/usr/share/plymouth/themes ]]; then
    say "Plymouth bulunamadı, açılış ekranı atlandı."
    return 0
  fi
  install -d -m 755 "$PLY"
  install -m 644 "$src"/plymouth/bandanix.plymouth "$src"/plymouth/bandanix.script "$src"/plymouth/*.png "$PLY"/
  update-alternatives --quiet --install "$ALT_LINK" default.plymouth "$PLY/bandanix.plymouth" 150
  update-alternatives --quiet --set default.plymouth "$PLY/bandanix.plymouth"
  say "Açılış ekranı: Bandanix"
}

install_grub() {
  local src=$1 font item small
  if [[ ! -d $K/boot/grub ]] || ! command -v update-grub >/dev/null || ! command -v grub-mkfont >/dev/null; then
    say "GRUB bulunamadı, GRUB teması atlandı."
    return 0
  fi
  if ! font=$(font_file); then
    say "GRUB için yazı tipi bulunamadı (DejaVu Sans), GRUB teması atlandı."
    return 0
  fi
  install -d -m 755 "$GRUBT"
  install -m 644 "$src"/grub/*.png "$GRUBT"/
  grub-mkfont -s 22 -o "$GRUBT/bandanix-22.pf2" "$font"
  grub-mkfont -s 16 -o "$GRUBT/bandanix-16.pf2" "$font"
  item=$(pf2_name "$GRUBT/bandanix-22.pf2")
  small=$(pf2_name "$GRUBT/bandanix-16.pf2")
  sed -e "s|@FONT_ITEM@|$item|g" -e "s|@FONT_SMALL@|$small|g" "$src/grub/theme.txt.in" > "$GRUBT/theme.txt"
  chmod 644 "$GRUBT/theme.txt"
  install -d -m 755 "$(dirname "$CFG")"
  cat > "$CFG" <<CFG
# Bandanix GRUB theme (acilis-ekrani). To undo: delete this file and run "sudo update-grub",
# or run acilis-ekrani/uninstall.sh in the Bandanix folder.
GRUB_THEME="/boot/grub/themes/bandanix/theme.txt"
CFG
  chmod 644 "$CFG"
  say "GRUB menüsü güncelleniyor"
  update-grub 2>&1 | tail -n 2 | sed 's/^/  /'
  say "GRUB teması: Bandanix"
}

rebuild_initramfs() {
  say "Açılış dosyası yeniden üretiliyor (1 dakika kadar sürebilir)"
  update-initramfs -u 2>&1 | tail -n 1 | sed 's/^/  /'
}

case "${1:-}" in
  kur)
    src=$(cd "${2:?kaynak klasör}" && pwd)
    install_plymouth "$src"
    install_grub "$src"
    [[ -f $PLY/bandanix.plymouth ]] && rebuild_initramfs
    ;;
  kaldir)
    had_plymouth=0
    if [[ -f $PLY/bandanix.plymouth ]]; then
      update-alternatives --quiet --remove default.plymouth "$PLY/bandanix.plymouth" || true
      rm -rf "$PLY"
      had_plymouth=1
      say "Açılış ekranı Mint'in kendi ekranına döndü"
    fi
    if [[ -f $CFG || -d $GRUBT ]]; then
      rm -f "$CFG"
      rm -rf "$GRUBT"
      if command -v update-grub >/dev/null; then
        update-grub 2>&1 | tail -n 2 | sed 's/^/  /'
      fi
      say "GRUB teması Mint'in kendi temasına döndü"
    fi
    if [[ $had_plymouth -eq 1 ]]; then rebuild_initramfs; fi
    ;;
  *)
    echo "Kullanım: kok.sh kur KAYNAK | kaldir" >&2
    exit 2
    ;;
esac
