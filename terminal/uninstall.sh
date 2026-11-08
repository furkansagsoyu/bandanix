#!/usr/bin/env bash
set -euo pipefail

DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APP="$DATA/bandanix/terminal"
STATE="$APP/state"
RC="$HOME/.bashrc"
BASE="/org/gnome/terminal/legacy/profiles:"

# 1) ~/.bashrc: remove only our marked block
if [[ -f $RC ]] && grep -qF "# >>> bandanix terminal >>>" "$RC"; then
  sed -i '/^# >>> bandanix terminal >>>$/,/^# <<< bandanix terminal <<<$/d' "$RC"
  echo "• ~/.bashrc içindeki Bandanix satırı kaldırıldı"
fi

# 2) GNOME Terminal: give the default back, delete our profile
if command -v dconf >/dev/null && [[ -s $STATE/uuid ]]; then
  uuid=$(< "$STATE/uuid")
  if [[ $(dconf read "$BASE/default" | tr -d "'") == "$uuid" ]]; then
    if [[ -s $STATE/previous-default ]]; then
      dconf write "$BASE/default" "'$(< "$STATE/previous-default")'"
    else
      dconf reset "$BASE/default"
    fi
  fi
  list=$(dconf read "$BASE/list")
  list=${list//", '$uuid'"/}
  list=${list//"'$uuid', "/}
  list=${list//"'$uuid'"/}
  if [[ $list == "[]" || -z $list ]]; then
    dconf reset "$BASE/list"
  else
    dconf write "$BASE/list" "$list"
  fi
  dconf reset -f "$BASE/:$uuid/"
  echo "• Bandanix terminal profili silindi, eski profilin yeniden varsayılan"
fi

# 3) files
rm -rf "$APP" "${XDG_CACHE_HOME:-$HOME/.cache}/bandanix/fetch.cache"
rm -f "$HOME/.local/bin/bandanix-fetch"
rmdir "$DATA/bandanix" 2>/dev/null || true
echo "• Terminal paketi kaldırıldı (değişiklikler yeni açılan terminallerde geçerli)"
