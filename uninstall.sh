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
choose_components "remove" "$@"

for c in "${CHOSEN[@]}"; do
  echo "${RED}${BOLD}==> removing $c${RESET}"
  "$ROOT/$c/uninstall.sh"
done

if [ "$PURGE" -eq 1 ]; then
  rm -rf "$BANDANIX_CONFIG"
  echo "• Theme file removed."
elif [ ${#CHOSEN[@]} -gt 0 ]; then
  echo "• Theme file kept in $BANDANIX_CONFIG (use --purge to remove it)."
fi
