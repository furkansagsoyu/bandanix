#!/usr/bin/env bash
set -euo pipefail

DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APP="$DATA/bandanix/vscode-tema"
ID="furkansagsoyu.bandanix-dark"

# only the editors we installed into; your settings.json is never touched
if [[ -s $APP/kurulu ]]; then
  while read -r cmd; do
    [[ -n $cmd ]] && command -v "$cmd" >/dev/null 2>&1 || continue
    if "$cmd" --uninstall-extension "$ID" >/dev/null 2>&1; then
      echo "• $cmd: $ID kaldırıldı"
    else
      echo "• $cmd: $ID zaten kurulu değil"
    fi
  done < "$APP/kurulu"
fi
rm -rf "$APP"
echo "• Bandanix Dark kaldırıldı. VS Code'da başka bir tema seçmek için: Ctrl+K, ardından Ctrl+T"
