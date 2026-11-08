#!/usr/bin/env python3
"""bandanix-not: the Bandanix quick note box.

  bandanix-not                  open the box (Super+N runs this; pressing it again closes)
  bandanix-not "some text"      add a note without opening the box
  bandanix-not liste [N]        print the last N notes (default 10)
  bandanix-not dosya            open the notes file in the default editor
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HOME = Path.home()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import notes  # noqa: E402

USAGE = """Kullanım:
  bandanix-not                  not kutusunu aç (Super+N ile aynı)
  bandanix-not "market: süt"    kutuyu açmadan not ekle
  bandanix-not liste [N]        son N notu göster (varsayılan 10)
  bandanix-not dosya            not dosyasını editörde aç"""

APP_ID = "io.github.furkansagsoyu.bandanix.not"


# ---- command line -----------------------------------------------------------------------
def cmd_list(count: int) -> int:
    items = notes.read_notes(notes.notes_path())[:count]
    if not items:
        print("Henüz not yok. Eklemek için: Super+N ya da bandanix-not \"metin\"")
        return 0
    for note in items:
        mark = {None: "•", False: "☐", True: "☑"}[note.todo]
        lines = note.text.splitlines() or [""]
        print(f"{mark} {lines[0]}   \033[2m{notes.ago(note.when)}\033[0m")
        for extra in lines[1:]:
            print(f"  {extra}")
    return 0


def cmd_file() -> int:
    path = notes.notes_path()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(notes.HEADER + "\n", encoding="utf-8")
    subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"• {path}")
    return 0


def cmd_add(text: str) -> int:
    if notes.add(notes.notes_path(), text) is None:
        print("• Boş not eklenmedi.")
        return 1
    print("• Not eklendi.")
    return 0


# ---- entry ------------------------------------------------------------------------------
def main(argv: list[str]) -> int:
    if not argv:
        from not_kutusu_ui import run   # GTK is imported only for the box itself
        return run(APP_ID)
    cmd = argv[0]
    if cmd in ("-h", "--help", "yardim"):
        print(USAGE)
        return 0
    if cmd == "liste" and len(argv) <= 2:
        if len(argv) == 2 and not argv[1].isdigit():
            print(USAGE, file=sys.stderr)
            return 2
        return cmd_list(int(argv[1]) if len(argv) == 2 else 10)
    if cmd == "dosya" and len(argv) == 1:
        return cmd_file()
    if cmd == "_kisayol-ayari" and len(argv) == 1:
        print(notes.setting("kisayol"))
        return 0
    if cmd == "_dosya-yolu" and len(argv) == 1:
        print(notes.notes_path())
        return 0
    return cmd_add(" ".join(argv))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
