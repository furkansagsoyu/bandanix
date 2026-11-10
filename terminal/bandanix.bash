# shellcheck shell=bash
# Bandanix terminal: two-line prompt + bandanix-fetch when a terminal opens.
# Sourced from ~/.bashrc (the installer adds one marked line there).

[[ $- == *i* ]] || return 0   # only interactive shells

# Bandanix commands (bandanix-yedek, bandanix-duvar, ...) live in ~/.local/bin. Mint adds it
# to PATH only at login, so a folder created later is missing until the next login.
[[ ":$PATH:" == *":$HOME/.local/bin:"* ]] || PATH="$HOME/.local/bin:$PATH"

. "${BASH_SOURCE[0]%/*}/theme.bash"
__bx_read_theme

# Branch and environment names live in these variables and PS1 only refers to them.
# Bash never re-interprets a variable's value, so a branch named `$(cmd)` can't run code.
__BX_BRANCH="" __BX_ENV=""

__bx_ps1() {
  local code=$?
  local A="\[\e[38;2;${BX_R};${BX_G};${BX_B}m\]"
  local DIM="\[\e[38;2;150;150;160m\]" BOLD="\[\e[1m\]" R="\[\e[0m\]"
  local ERR="\[\e[38;2;255;59;92m\]"
  local host="" git="" env=""

  [[ -n $SSH_CONNECTION ]] && host="${DIM}\u@\h${R} "

  if __BX_BRANCH=$(git symbolic-ref --short -q HEAD 2>/dev/null \
                   || git rev-parse --short -q HEAD 2>/dev/null); then
    local dirty=""
    git diff --quiet --ignore-submodules HEAD 2>/dev/null || dirty=" ●"
    git="  ${DIM}⎇ \${__BX_BRANCH}${R}${A}${dirty}${R}"
  fi

  __BX_ENV=""
  if [[ -n $VIRTUAL_ENV ]]; then
    local path=${VIRTUAL_ENV%/}
    __BX_ENV=${path##*/}
    # ".venv" says nothing; show the project folder instead
    if [[ $__BX_ENV == .venv || $__BX_ENV == venv || $__BX_ENV == env ]]; then
      path=${path%/*}
      __BX_ENV=${path##*/}
    fi
  elif [[ -n $CONDA_DEFAULT_ENV ]]; then
    __BX_ENV=$CONDA_DEFAULT_ENV
  fi
  [[ -n $__BX_ENV ]] && env="  ${DIM}🐍 \${__BX_ENV}${R}"

  local tail
  if (( code == 0 )); then
    tail="${A}╰─❯${R} "
  else
    tail="${ERR}╰─✗ ${code} ❯${R} "
  fi
  PS1="${A}╭─${R} ${host}${A}${BOLD}\w${R}${git}${env}\n${tail}"
  return "$code"   # keep $? for anything else in PROMPT_COMMAND (e.g. VTE)
}

if (( BX_PROMPT )); then
  # Run first so we see the real exit code; keep whatever was already there.
  if [[ $(declare -p PROMPT_COMMAND 2>/dev/null) == "declare -a"* ]]; then
    [[ " ${PROMPT_COMMAND[*]} " == *" __bx_ps1 "* ]] \
      || PROMPT_COMMAND=(__bx_ps1 "${PROMPT_COMMAND[@]}")
  elif [[ ${PROMPT_COMMAND:-} != *__bx_ps1* ]]; then
    # PROMPT_COMMAND is a string here (the array case is above)
    # shellcheck disable=SC2128,SC2178
    PROMPT_COMMAND="__bx_ps1${PROMPT_COMMAND:+; $PROMPT_COMMAND}"
  fi
fi

# System info once per terminal window: not in VS Code, SSH or nested shells.
if (( BX_FETCH )) && [[ -z $SSH_CONNECTION && ${TERM_PROGRAM:-} != vscode \
      && -z ${BANDANIX_FETCH_SHOWN:-} && ${SHLVL:-1} -le 1 ]]; then
  export BANDANIX_FETCH_SHOWN=1
  [[ -x $HOME/.local/bin/bandanix-fetch ]] && "$HOME/.local/bin/bandanix-fetch"
fi
return 0
