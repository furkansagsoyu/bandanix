#!/usr/bin/env bash
# Runs ShellCheck on every shell script in the repo.
#   scripts/denetle.sh                 errors only; exits 1 if there is one
#   scripts/denetle.sh warning         warnings too
#   scripts/denetle.sh warning --rapor report only (GitHub annotations), never fails
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
level="${1:-error}"
report=0
[ "${2:-}" = "--rapor" ] && report=1

if ! command -v shellcheck >/dev/null; then
  echo "shellcheck kurulu değil: sudo apt install shellcheck"
  exit 1
fi

files=()
while IFS= read -r f; do
  case "$f" in
    *.sh|*.bash) files+=("$f") ;;
    *) head -n 1 "$f" 2>/dev/null | grep -qE '^#!.*(ba)?sh' && files+=("$f") ;;
  esac
done < <(git ls-files 2>/dev/null || find . -type f -not -path './.git/*' | sed 's|^\./||')

echo "${#files[@]} betik denetleniyor (seviye: $level)"
if [ "$report" -eq 1 ]; then
  # file:line:col: level: message [SCxxxx]  ->  GitHub annotation of the same level
  shellcheck -x -S "$level" -f gcc "${files[@]}" \
    | sed -E -e 's/^([^:]+):([0-9]+):([0-9]+): error: (.*)$/::error file=\1,line=\2,col=\3::\4/' \
             -e 's/^([^:]+):([0-9]+):([0-9]+): (warning|note|info|style): (.*)$/::warning file=\1,line=\2,col=\3::\5/'
  exit 0
fi
shellcheck -x -S "$level" "${files[@]}"
