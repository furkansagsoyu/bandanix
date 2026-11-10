#!/usr/bin/env bash
# description: VS Code için Bandanix Dark renk teması (nötr koyu arayüz, kırmızı vurgu)
# kurulu: ~/.local/share/bandanix/vscode-tema/kurulu
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APP="$DATA/bandanix/vscode-tema"
VSIX="$APP/bandanix-dark.vsix"

# 1) which editors are here? (VS Code, VSCodium, Insiders)
editors=()
for cmd in code codium code-insiders; do
  command -v "$cmd" >/dev/null 2>&1 && editors+=("$cmd")
done
if [[ ${#editors[@]} -eq 0 ]]; then
  echo "• VS Code bulunamadı (code ya da codium komutu yok). Önce onu kur, sonra: ./install.sh vscode-tema" >&2
  exit 1
fi

# 2) pack the theme
mkdir -p "$APP"
id=$(/usr/bin/python3 "$HERE/paket.py" "$HERE/eklenti" "$VSIX")
echo "• Tema paketlendi: $VSIX"

# 3) install with the editor's own command
: > "$APP/kurulu.yeni"
for cmd in "${editors[@]}"; do
  if "$cmd" --install-extension "$VSIX" --force >/dev/null 2>"$APP/hata.log"; then
    echo "$cmd" >> "$APP/kurulu.yeni"
    echo "• $cmd: $id kuruldu"
  else
    echo "• $cmd: kurulamadı ($(tail -n 1 "$APP/hata.log"))" >&2
  fi
done
rm -f "$APP/hata.log"
if [[ ! -s $APP/kurulu.yeni ]]; then
  rm -f "$APP/kurulu.yeni"
  exit 1
fi
mv "$APP/kurulu.yeni" "$APP/kurulu"

echo "• Temayı seçmek için VS Code'da: Ctrl+K, ardından Ctrl+T → Bandanix Dark"
