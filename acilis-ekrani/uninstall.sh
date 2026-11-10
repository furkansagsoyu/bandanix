#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "• Açılış ekranı ve GRUB teması Mint'inkine dönüyor (şifren sorulacak)."
sudo bash "$HERE/kok.sh" kaldir
rm -f "$HOME/.local/bin/bandanix-acilis"
echo "• Bandanix açılış ekranı kaldırıldı."
