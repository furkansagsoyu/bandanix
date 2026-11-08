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
choose_components "install" "$@"
if [ ${#CHOSEN[@]} -eq 0 ]; then
  echo "Nothing selected."
  exit 0
fi

mkdir -p "$BANDANIX_CONFIG"
if [ -f "$BANDANIX_CONFIG/theme.toml" ]; then
  echo "• Keeping your theme file: $BANDANIX_CONFIG/theme.toml"
else
  cp "$ROOT/theme.toml" "$BANDANIX_CONFIG/theme.toml"
  echo "• Theme file installed: $BANDANIX_CONFIG/theme.toml"
fi

for c in "${CHOSEN[@]}"; do
  echo
  echo "${RED}${BOLD}==> $c${RESET}"
  "$ROOT/$c/install.sh"
done

echo
echo "${RED}${BOLD}Bandanix is ready.${RESET}"
echo "Change colours and fonts in $BANDANIX_CONFIG/theme.toml"
