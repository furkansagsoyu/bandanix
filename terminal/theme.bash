# shellcheck shell=bash disable=SC2034
# (the BX_* values set here are read by bandanix.bash and bandanix-fetch)
# Bandanix: reads the few theme.toml keys that bash needs (sourced, not run).
# Sets BX_ACCENT, BX_R/BX_G/BX_B (accent as RGB), BX_PROMPT and BX_FETCH (1 = on).

__bx_read_theme() {
  BX_ACCENT="#C8102E"
  BX_PROMPT=1
  BX_FETCH=1
  local file="${XDG_CONFIG_HOME:-$HOME/.config}/bandanix/theme.toml"
  local line section="" re_section='^[[:space:]]*\[([^]]+)\]'
  local re_accent='^[[:space:]]*accent[[:space:]]*=[[:space:]]*"(#[0-9a-fA-F]{6})"'
  local re_prompt='^[[:space:]]*prompt[[:space:]]*=[[:space:]]*(true|false)'
  local re_fetch='^[[:space:]]*fetch_on_open[[:space:]]*=[[:space:]]*(true|false)'
  if [[ -r $file ]]; then
    while IFS= read -r line || [[ -n $line ]]; do
      if [[ $line =~ $re_section ]]; then
        section=${BASH_REMATCH[1]}
        continue
      fi
      case $section in
        colors)
          [[ $line =~ $re_accent ]] && BX_ACCENT=${BASH_REMATCH[1]} ;;
        terminal)
          if [[ $line =~ $re_prompt ]]; then
            [[ ${BASH_REMATCH[1]} == false ]] && BX_PROMPT=0
          elif [[ $line =~ $re_fetch ]]; then
            [[ ${BASH_REMATCH[1]} == false ]] && BX_FETCH=0
          fi ;;
      esac
    done < "$file"
  fi
  BX_R=$((16#${BX_ACCENT:1:2}))
  BX_G=$((16#${BX_ACCENT:3:2}))
  BX_B=$((16#${BX_ACCENT:5:2}))
  return 0
}
