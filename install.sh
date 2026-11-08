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
choose_components "kurmak istiyorsun" "$@"
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

for c in "${CHOSEN[@]}"; do
  echo
  echo "${RED}${BOLD}==> $c${RESET}"
  "$ROOT/$c/install.sh"
done

echo
echo "${RED}${BOLD}Bandanix hazır.${RESET}"
echo "Renkleri ve yazı tipini $BANDANIX_CONFIG/theme.toml dosyasından değiştirebilirsin."
