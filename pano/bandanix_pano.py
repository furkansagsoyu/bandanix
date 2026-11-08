#!/usr/bin/env python3
"""bandanix-pano: clipboard history.

  bandanix-pano            open the list (Super+V runs this; pressing it again closes)
  bandanix-pano liste      print the history
  bandanix-pano temizle    delete everything that is not pinned
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pano_gecmis as pano  # noqa: E402

APP_ID = "io.github.furkansagsoyu.bandanix.pano"
USAGE = """Kullanım:
  bandanix-pano            pano geçmişini aç (Super+V ile aynı)
  bandanix-pano liste      geçmişi terminalde göster
  bandanix-pano temizle    sabitlenmemiş bütün geçmişi sil"""


def cmd_list() -> int:
    data = pano.items()
    if not data:
        print("Pano geçmişi boş. Bir şey kopyaladığında burada görünür.")
        return 0
    now = time.time()
    for n, it in enumerate(data, 1):
        pin = "📌 " if it["sabit"] else ""
        print(f"{n:>2}. {pin}{pano.title(it['metin'], 70)}   \033[2m{pano.ago(it['zaman'], now)}\033[0m")
    return 0


def cmd_clear() -> int:
    gone = pano.clear()
    print(f"• {gone} kayıt silindi. Sabitlenenler yerinde duruyor.")
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        from pano_ui import run          # GTK is imported only for the window itself
        return run(APP_ID)
    cmd = argv[0]
    if len(argv) == 1 and cmd == "liste":
        return cmd_list()
    if len(argv) == 1 and cmd == "temizle":
        return cmd_clear()
    if len(argv) == 1 and cmd == "_bekci":
        from pano_bekci import run as watch
        return watch()
    if len(argv) == 1 and cmd == "_kisayol-ayari":
        print(pano.setting("kisayol", "<Super>v"))
        return 0
    helped = cmd in ("-h", "--help", "yardim")
    print(USAGE, file=sys.stdout if helped else sys.stderr)
    return 0 if helped else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
