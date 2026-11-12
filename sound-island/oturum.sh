#!/usr/bin/env bash
# Ada beklenmedik şekilde kapanırsa yeniden aç. Normal çıkışta oturumu bitir.
set -u

if [[ "${1:-}" == -h || "${1:-}" == --help ]]; then
  exec "$ADA_PY" -m sound_island "$@"
fi

STATE="${XDG_STATE_HOME:-$HOME/.local/state}/bandanix"
umask 077
mkdir -p -- "$STATE" || exec "$ADA_PY" -m sound_island "$@"
exec 9>"$STATE/ada-oturum.lock"
flock -n 9 || exit 0

# Yalnızca son oturumu sakla. Başarısız başlangıçlar da aynı dosyaya yazılır.
exec 8>"$STATE/ada-son-oturum.log"
attempts=0
while true; do
  started=$SECONDS
  "$ADA_PY" -X faulthandler -m sound_island "$@" 9>&- >&8 2>&8
  status=$?
  case "$status" in
    0|2|130|143) exit "$status" ;;
  esac
  printf '[ada] %(%F %T)T çıkış kodu %s\n' -1 "$status" >&8
  if (( SECONDS - started >= 60 )); then
    attempts=0
  fi
  attempts=$((attempts + 1))
  if (( attempts > 3 )); then
    exit "$status"
  fi
  sleep 1
done
