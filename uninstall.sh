#!/usr/bin/env bash
# Bandanix uninstaller.
#   ./uninstall.sh                 interactive menu
#   ./uninstall.sh --all           remove everything (theme file is kept)
#   ./uninstall.sh --all --purge   remove everything including the theme file
#   ./uninstall.sh sound-island    remove only the named component(s)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib.sh
source "$ROOT/scripts/lib.sh"

PURGE=0
for arg in "$@"; do
  [ "$arg" = "--purge" ] && PURGE=1
done

banner
choose_components "kaldırmak istiyorsun" "$@"

skip_sudo_components "kaldırılmayacak"
run_components uninstall
if [ ${#FAILED[@]} -gt 0 ]; then
  echo
  echo "${RED}${BOLD}Kaldırılamayan parçalar: ${FAILED[*]}${RESET}"
fi

if [ "$PURGE" -eq 1 ]; then
  rm -rf "$BANDANIX_CONFIG"
  echo "• Tema dosyası kaldırıldı."
elif [ ${#CHOSEN[@]} -gt 0 ]; then
  echo "• Tema dosyası $BANDANIX_CONFIG içinde bırakıldı (silmek için --purge kullan)."
fi
