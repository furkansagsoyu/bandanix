# shellcheck shell=bash
# Shared helpers for the Bandanix install/uninstall scripts (sourced, not run).

RED=$'\e[38;2;200;16;46m'
BOLD=$'\e[1m'
DIM=$'\e[2m'
RESET=$'\e[0m'

# used by install.sh and uninstall.sh, which source this file

# shellcheck disable=SC2034
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

# Components that change system files say "# yetki: sudo" in their install.sh header.
needs_sudo() {
  head -n 6 "$ROOT/$1/install.sh" | grep -q '^# yetki: sudo'
}

# Can this user run sudo at all? (root, or a member of the sudo/admin/wheel group)
can_sudo() {
  [ "$(id -u)" -eq 0 ] && return 0
  id -nG | tr ' ' '\n' | grep -qxE 'sudo|admin|wheel'
}

# run_components install|uninstall -> runs each chosen component; one failing does not stop
# the others. Fills FAILED with the ones that did not finish.
run_components() {
  local action="$1" c
  FAILED=()
  for c in "${CHOSEN[@]}"; do
    echo
    echo "${RED}${BOLD}==> $c${RESET}"
    if "$ROOT/$c/$action.sh"; then
      # remember what was installed, so "bandanix guncelle" knows when the part changes
      if [ "$action" = install ]; then
        /usr/bin/python3 "$ROOT/core/bandanix_guncelle.py" kaydet "$c" || true
      else
        /usr/bin/python3 "$ROOT/core/bandanix_guncelle.py" sil "$c" || true
      fi
    else
      FAILED+=("$c")
      echo "${RED}• $c tamamlanamadı; diğer parçalarla devam ediliyor.${RESET}"
    fi
  done
}

# skip_sudo_components "kurulamaz" -> drops components that need sudo when this user can't use it
skip_sudo_components() {
  local c kept=() skipped=()
  can_sudo && return 0
  for c in "${CHOSEN[@]}"; do
    if needs_sudo "$c"; then skipped+=("$c"); else kept+=("$c"); fi
  done
  if [ ${#skipped[@]} -gt 0 ]; then
    echo "• Bu kullanıcı sudo kullanamadığı için şu parçalar $1: ${skipped[*]}"
    echo "  (Sistem dosyalarına dokunuyorlar; yönetici hesabından kurulabilirler.)"
    echo
  fi
  CHOSEN=("${kept[@]}")
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
