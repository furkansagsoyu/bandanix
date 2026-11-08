# Shared helpers for the Bandanix install/uninstall scripts (sourced, not run).

RED=$'\e[38;2;200;16;46m'
BOLD=$'\e[1m'
DIM=$'\e[2m'
RESET=$'\e[0m'

BANDANIX_CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/bandanix"

banner() {
  printf '%s%s' "$RED" "$BOLD"
  cat <<'EOF'
 ____      _     _   _  ____      _     _   _  ___ __  __
| __ )    / \   | \ | ||  _ \    / \   | \ | ||_ _|\ \/ /
|  _ \   / _ \  |  \| || | | |  / _ \  |  \| | | |  \  /
| |_) | / ___ \ | |\  || |_| | / ___ \ | |\  | | |  /  \
|____/ /_/   \_\|_| \_||____/ /_/   \_\|_| \_||___|/_/\_\
EOF
  printf '%s%s\n\n' "$RESET" "${DIM}Bandana'nın masaüstü kiti${RESET}"
}

# Every folder with an executable install.sh is a component.
list_components() {
  local dir
  for dir in "$ROOT"/*/; do
    [ -x "$dir/install.sh" ] && basename "$dir"
  done
}

describe() {
  sed -n 's/^# description: //p' "$ROOT/$1/install.sh" | head -n 1
}

# choose_components VERB [args...] -> fills the CHOSEN array
# args: nothing (interactive menu), --all, or component names.
choose_components() {
  local verb="$1"; shift
  local all=() c n i answer
  mapfile -t all < <(list_components)
  CHOSEN=()
  if [ ${#all[@]} -eq 0 ]; then
    echo "Hiç parça bulunamadı."; return 1
  fi

  local picked=0
  for c in "$@"; do
    case "$c" in
      --all) CHOSEN=("${all[@]}"); picked=1 ;;
      --*) ;;  # other flags (e.g. --purge) are handled by the caller
      *)
        if [ -x "$ROOT/$c/install.sh" ]; then CHOSEN+=("$c"); picked=1
        else echo "Bilinmeyen parça: $c"; return 1; fi ;;
    esac
  done
  [ "$picked" -eq 1 ] && return 0

  echo "${BOLD}Parçalar:${RESET}"
  i=1
  for c in "${all[@]}"; do
    printf '  %s%d)%s %-14s %s\n' "$RED" "$i" "$RESET" "$c" "$(describe "$c")"
    i=$((i + 1))
  done
  printf '  %sa)%s hepsi\n\n' "$RED" "$RESET"
  read -rp "Neyi $verb? (ör. 1 2, ya da a): " answer
  if [[ "$answer" =~ ^[aA] ]]; then
    CHOSEN=("${all[@]}")
    return 0
  fi
  for n in $answer; do
    if [[ "$n" =~ ^[0-9]+$ ]] && [ "$n" -ge 1 ] && [ "$n" -le ${#all[@]} ]; then
      CHOSEN+=("${all[$((n - 1))]}")
    else
      echo "Geçersiz seçim atlandı: $n"
    fi
  done
}

# ask "Question" -> 0 for yes (default), 1 for no. Non-interactive = yes.
ask() {
  local reply
  [ -t 0 ] || return 0
  read -rp "$1 [E/h] " reply
  [[ ! "$reply" =~ ^[hHnN] ]]
}
