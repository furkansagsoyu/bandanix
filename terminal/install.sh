#!/usr/bin/env bash
# description: Bandanix prompt, terminal renk şeması ve açılışta bandanix-fetch
# kurulu: ~/.local/bin/bandanix-fetch
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APP="$DATA/bandanix/terminal"
STATE="$APP/state"
BIN="$HOME/.local/bin/bandanix-fetch"
RC="$HOME/.bashrc"
MARK_START="# >>> bandanix terminal >>>"
MARK_END="# <<< bandanix terminal <<<"

# 1) files
mkdir -p "$APP" "$STATE" "$(dirname "$BIN")"
cp "$HERE/bandanix.bash" "$HERE/theme.bash" "$APP/"
cp "$HERE/bin/bandanix-fetch" "$BIN"
chmod +x "$BIN"
rm -f "${XDG_CACHE_HOME:-$HOME/.cache}/bandanix/fetch.cache"   # refresh CPU/GPU info
echo "• Dosyalar kopyalandı: $APP"

# 2) ~/.bashrc: one marked block, after a backup
touch "$RC"
if grep -qF "$MARK_START" "$RC"; then
  echo "• ~/.bashrc zaten ayarlı"
else
  backup="$RC.bandanix-yedek-$(date +%Y%m%d-%H%M%S)"
  cp "$RC" "$backup"
  {
    echo
    echo "$MARK_START"
    echo "[ -f \"$APP/bandanix.bash\" ] && . \"$APP/bandanix.bash\""
    echo "$MARK_END"
  } >> "$RC"
  echo "• ~/.bashrc dosyasına Bandanix satırı eklendi (yedek: $backup)"
fi

# 3) GNOME Terminal: a separate "Bandanix" profile, made the default
BASE="/org/gnome/terminal/legacy/profiles:"
BUILTIN_DEFAULT="b1dcc9dd-5262-4d8d-a863-c897e6d979b9"
if ! command -v gnome-terminal >/dev/null || ! command -v dconf >/dev/null; then
  echo "• GNOME Terminal bulunamadı, renk profili atlandı (prompt ve fetch yine çalışır)"
  exit 0
fi

# shellcheck source=theme.bash
. "$HERE/theme.bash"
__bx_read_theme

if [[ -s $STATE/uuid ]]; then
  uuid=$(< "$STATE/uuid")
else
  uuid=$(< /proc/sys/kernel/random/uuid)
  echo "$uuid" > "$STATE/uuid"
fi

current=$(dconf read "$BASE/default" | tr -d "'")
[[ -z $current ]] && current=$BUILTIN_DEFAULT
if [[ $current != "$uuid" ]]; then
  echo "$current" > "$STATE/previous-default"   # restored on uninstall
fi

list=$(dconf read "$BASE/list")
if [[ -z $list || $list == "@as []" ]]; then
  list="['$current']"
fi
if [[ $list != *"'$uuid'"* ]]; then
  list="${list%]}, '$uuid']"
fi
dconf write "$BASE/list" "$list"

P="$BASE/:$uuid"
dconf write "$P/visible-name" "'Bandanix'"
dconf write "$P/use-theme-colors" "false"
dconf write "$P/background-color" "'#121214'"
dconf write "$P/foreground-color" "'#E8E6E3'"
dconf write "$P/palette" "['#1C1C1F', '#C8102E', '#6FBF73', '#E5B567', '#6C9EF8', '#C678DD', '#56B6C2', '#C9C7C4', '#4A4A50', '#FF3B5C', '#8FD694', '#F2CC8F', '#8AB4FF', '#D7A1F0', '#7FD3DD', '#F5F3F0']"
dconf write "$P/bold-color-same-as-fg" "true"
dconf write "$P/cursor-colors-set" "true"
dconf write "$P/cursor-background-color" "'$BX_ACCENT'"
dconf write "$P/cursor-foreground-color" "'#121214'"
dconf write "$P/highlight-colors-set" "true"
dconf write "$P/highlight-background-color" "'$BX_ACCENT'"
dconf write "$P/highlight-foreground-color" "'#F5F3F0'"
dconf write "$BASE/default" "'$uuid'"
echo "• \"Bandanix\" terminal profili oluşturuldu ve varsayılan yapıldı (eski profilin duruyor)"
echo "• Görmek için yeni bir terminal penceresi aç."
