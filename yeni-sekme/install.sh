#!/usr/bin/env bash
# description: Brave: yeni sekme sayfası (duvar kağıdı, saat, arama, kısayollar) ve koyu bordo renk teması
# kurulu: ~/.local/share/bandanix/yeni-sekme/eklenti/manifest.json
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APP="$DATA/bandanix/yeni-sekme"
EXT="$APP/eklenti"
THEME="$APP/tema"
BIN="$HOME/.local/bin/bandanix-sekme"

# 1) the new tab page (its background picture and ayar.js are kept, then rewritten below) and the theme
mkdir -p "$EXT" "$THEME" "$(dirname "$BIN")"
for f in "$HERE"/eklenti/*; do
  [[ $(basename "$f") == ayar.js && -f $EXT/ayar.js ]] && continue
  cp "$f" "$EXT/"
done
cp "$HERE"/tema/* "$THEME/"
cp "$HERE/bandanix_sekme.py" "$APP/"
cat > "$BIN" <<SH
#!/bin/sh
exec /usr/bin/python3 "$APP/bandanix_sekme.py" "\$@"
SH
chmod +x "$BIN"

# 2) colours from theme.toml, background from the desktop
"$BIN" guncelle

# 3) Brave: loading an unpacked folder can only be done by hand, once per folder
missing=$("$BIN" _durum | /usr/bin/python3 -c '
import json, sys
d = json.load(sys.stdin)
for key, name in (("eklenti", "Yeni sekme"), ("tema", "Tema")):
    if d[key + "_yuklu"] is not True:
        print(name + "\t" + d[key])')
if [[ -z $missing ]]; then
  echo "• Yeni sekme ve tema Brave'de zaten yüklü; yeni bir sekme açınca güncel hâlini görürsün."
  exit 0
fi

echo
echo "Son adım Brave'de, her klasör için bir kez yapılır:"
echo "  1. Açılan brave://extensions sayfasında sağ üstteki \"Geliştirici modu\"nu aç."
echo "  2. \"Paketlenmemiş öğe yükle\"ye bas."
echo "  3. Klasör penceresinde Ctrl+L'ye bas, aşağıdaki yolu yaz, \"Seç\"e bas:"
while IFS=$'\t' read -r name path; do
  printf '       %-11s %s\n' "$name" "$path"
done <<< "$missing"
if [[ $(wc -l <<< "$missing") -gt 1 ]]; then
  echo "  İkinci klasör için 2. ve 3. adımı tekrarla."
fi
if [[ $missing == *"Yeni sekme"* ]]; then
  echo "  Yeni sekme açınca Brave \"bu sayfayı bir eklenti değiştirdi\" diye sorarsa \"Değişiklikleri koru\" de."
fi
"$BIN" ac >/dev/null || echo "• Brave bulunamadı; Brave'i kurunca: bandanix-sekme ac"
