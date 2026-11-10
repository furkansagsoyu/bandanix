#!/usr/bin/env bash
# Run every component's unit tests (the same thing GitHub Actions runs on each push).
#   scripts/testler.sh            all components
#   scripts/testler.sh pil guc    only these
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

if [ $# -gt 0 ]; then
  dirs=("$@")
else
  dirs=()
  for t in */tests; do dirs+=("${t%/tests}"); done
fi

failed=()
for d in "${dirs[@]}"; do
  [ -d "$d/tests" ] || { echo "• $d: test klasörü yok"; continue; }
  printf '%-16s ' "$d"
  if out=$(cd "$d" && /usr/bin/python3 -m unittest discover -s tests 2>&1); then
    echo "$out" | grep -E '^Ran [0-9]+ test' | tr -d '\n'; echo " ✓"
  else
    echo "✗"
    echo "$out" | sed 's/^/    /'
    failed+=("$d")
  fi
done

if [ ${#failed[@]} -gt 0 ]; then
  echo
  echo "Başarısız: ${failed[*]}"
  exit 1
fi
