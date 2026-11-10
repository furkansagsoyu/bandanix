#!/usr/bin/env bash
# description: Brave yeni sekme sayfası: duvar kağıdı, büyük saat, arama ve en çok girdiğin siteler
# kurulu: ~/.local/share/bandanix/yeni-sekme/eklenti/manifest.json
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APP="$DATA/bandanix/yeni-sekme"
EXT="$APP/eklenti"
BIN="$HOME/.local/bin/bandanix-sekme"

# 1) the extension (its background picture and ayar.js are kept, then rewritten below)
mkdir -p "$EXT" "$(dirname "$BIN")"
for f in "$HERE"/eklenti/*; do
  [[ $(basename "$f") == ayar.js && -f $EXT/ayar.js ]] && continue
  cp "$f" "$EXT/"
done
cp "$HERE/bandanix_sekme.py" "$APP/"
cat > "$BIN" <<SH
#!/bin/sh
exec /usr/bin/python3 "$APP/bandanix_sekme.py" "\$@"
SH
chmod +x "$BIN"
echo "• Eklenti klasörü: $EXT"

# 2) colours from theme.toml, background from the desktop
"$BIN" guncelle

# 3) Brave: loading an unpacked extension can only be done by hand, once
state=$("$BIN" 2>/dev/null | awk -F'  +' '/^Brave/{print $2}')
if [[ $state == yüklü ]]; then
  echo "• Brave'de zaten yüklü; yeni bir sekme açınca güncel hâlini görürsün."
  exit 0
fi
if command -v xclip >/dev/null; then
  printf '%s' "$EXT" | xclip -selection clipboard && copied=" (yol panoya kopyalandı)"
fi
cat <<TXT

Son adım Brave'de, bir kez yapılır:
  1. Açılan brave://extensions sayfasında sağ üstteki "Geliştirici modu"nu aç.
  2. "Paketlenmemiş öğe yükle"ye bas.
  3. Klasör penceresinde Ctrl+L'ye bas, şu yolu yapıştır, "Seç"e bas${copied:-}:
     $EXT
  Yeni sekme açınca Brave "bu sayfayı bir eklenti değiştirdi" diye sorarsa "Değişiklikleri koru" de.
TXT
"$BIN" ac || echo "• Brave bulunamadı; Brave'i kurunca: bandanix-sekme ac"
