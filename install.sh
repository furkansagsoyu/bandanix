#!/usr/bin/env bash
# Bandanix installer.
#   ./install.sh                 interactive menu
#   ./install.sh --all           install everything
#   ./install.sh sound-island    install only the named component(s)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib.sh
source "$ROOT/scripts/lib.sh"

banner
if [ "${XDG_SESSION_TYPE:-}" = "wayland" ]; then
  echo "⚠ Şu an Cinnamon'ın deneysel Wayland oturumundasın. Bandanix X11 için yazıldı;"
  echo "  adalar ekranın köşesine kayabilir, kısayollar ve otomatik yapıştırma çalışmayabilir."
  echo "  Oturumu kapat, giriş ekranında oturum seçiminden \"Cinnamon\" (Wayland olmayan) seç."
  echo
fi
choose_components "kurmak istiyorsun" "$@"
skip_sudo_components "kurulmayacak"
if [ ${#CHOSEN[@]} -eq 0 ]; then
  echo "Hiçbir şey seçilmedi."
  exit 0
fi

mkdir -p "$BANDANIX_CONFIG"
if [ -f "$BANDANIX_CONFIG/theme.toml" ]; then
  echo "• Tema dosyan korunuyor: $BANDANIX_CONFIG/theme.toml"
else
  cp "$ROOT/theme.toml" "$BANDANIX_CONFIG/theme.toml"
  echo "• Tema dosyası kuruldu: $BANDANIX_CONFIG/theme.toml"
fi

# Core tools (always installed/updated, not shown in the menu)
CORE="${XDG_DATA_HOME:-$HOME/.local/share}/bandanix/core"
YEDEK="$HOME/.local/bin/bandanix-yedek"
mkdir -p "$CORE" "$(dirname "$YEDEK")"
cp "$ROOT"/core/*.py "$CORE/"
echo "$ROOT" > "$(dirname "$CORE")/kaynak"     # where Bandanix Ayarlar finds the installers
/usr/bin/python3 "$ROOT/core/bandanix_guncelle.py" kaydet core || true
cat > "$YEDEK" <<EOF
#!/bin/sh
exec /usr/bin/python3 "$CORE/bandanix_yedek.py" "\$@"
EOF
chmod +x "$YEDEK"

# Snapshot of the desktop before anything changes (the very first one is "orijinal")
if ! "$YEDEK" otomatik "${CHOSEN[*]} kurulumu öncesi"; then
  echo "• Uyarı: yedek alınamadı, kurulum yine de devam ediyor."
fi

run_components install

echo
if [ ${#FAILED[@]} -gt 0 ]; then
  echo "${RED}${BOLD}Kurulamayan parçalar: ${FAILED[*]}${RESET}"
  echo "Hatanın nedeni yukarıda, parçanın kendi başlığının altında yazıyor."
  echo "Düzelttikten sonra yalnızca onları kurmak için: ./install.sh ${FAILED[*]}"
  echo
fi
echo "${RED}${BOLD}Bandanix hazır.${RESET}"
echo "Renkleri ve yazı tipini $BANDANIX_CONFIG/theme.toml dosyasından değiştirebilirsin."
echo "Masaüstü yedeklerin için: bandanix-yedek liste"
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
  echo
  echo "Not: Bandanix komutları ~/.local/bin içinde ve bu klasör henüz komut yolunda değil."
  echo "Yeni bir terminal aç (terminal paketi kuruluysa) ya da oturumu kapatıp aç."
  echo "Bu terminalde hemen kullanmak için: export PATH=\"\$HOME/.local/bin:\$PATH\""
fi
[ ${#FAILED[@]} -eq 0 ]
