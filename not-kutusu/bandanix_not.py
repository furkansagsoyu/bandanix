#!/usr/bin/env python3
"""bandanix-not: the Bandanix quick note box.

  bandanix-not                  open the box (Super+N runs this; pressing it again closes)
  bandanix-not "some text"      add a note without opening the box
  bandanix-not liste [N]        print the last N notes (default 10)
  bandanix-not dosya            open the notes file in the default editor
"""
from __future__ import annotations

import ast
import json
import re
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
KEYS = "/org/cinnamon/desktop/keybindings"
SHORTCUT_ID = "bandanix-not"
FALLBACK = "<Primary><Alt>n"


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


# ---- keyboard shortcut (used by install.sh) ---------------------------------------------
def gv_str(s: str) -> str:
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


def gv_list(items: list[str]) -> str:
    return "[" + ", ".join(gv_str(i) for i in items) + "]" if items else "@as []"


def dconf_read(key: str) -> str:
    try:
        return subprocess.run(["dconf", "read", key], capture_output=True, text=True).stdout.strip()
    except OSError:
        return ""


def dconf_write(key: str, value: str) -> None:
    subprocess.run(["dconf", "write", key, value], check=True)


def parse_list(value: str) -> list[str]:
    value = value.removeprefix("@as").strip()
    try:
        items = ast.literal_eval(value) if value else []
    except (ValueError, SyntaxError):
        return []
    return [str(i) for i in items] if isinstance(items, list) else []


MOD_NAMES = {"primary": "ctrl", "control": "ctrl", "ctrl": "ctrl", "super": "super", "mod4": "super",
             "alt": "alt", "mod1": "alt", "shift": "shift", "meta": "meta", "hyper": "hyper"}


def norm_accel(accel: str) -> tuple[frozenset, str] | None:
    mods = re.findall(r"<(\w+)>", accel)
    key = re.sub(r"<\w+>", "", accel).strip().lower()
    if not key:
        return None
    return frozenset(MOD_NAMES.get(m.lower(), m.lower()) for m in mods), key


def pretty(accel: str) -> str:
    names = {"primary": "Ctrl", "control": "Ctrl", "ctrl": "Ctrl", "super": "Super",
             "alt": "Alt", "shift": "Shift"}
    mods = [names.get(m.lower(), m) for m in re.findall(r"<(\w+)>", accel)]
    key = re.sub(r"<\w+>", "", accel)
    return "+".join(mods + [key.upper() if len(key) == 1 else key])


def bindings_in_use() -> set:
    """Every accelerator Cinnamon already uses (defaults included), except our own."""
    texts = []
    try:
        texts.append(subprocess.run(["gsettings", "list-recursively", "org.cinnamon.desktop.keybindings"],
                                    capture_output=True, text=True).stdout)
    except OSError:
        pass
    try:
        dump = subprocess.run(["dconf", "dump", KEYS + "/"], capture_output=True, text=True).stdout
    except OSError:
        dump = ""
    section = ""
    for line in dump.splitlines():
        if line.startswith("["):
            section = line.strip("[]")
        elif section != f"custom-keybindings/{SHORTCUT_ID}":
            texts.append(line)
    accels = [a for text in texts for a in re.findall(r"'(<[^']*)'", text)]
    accels += spice_bindings()
    return {n for n in map(norm_accel, accels) if n}


def spice_bindings() -> list[str]:
    """Shortcuts that applets and desklets keep in their own settings
    (e.g. the notifications applet opens its list with Super+N)."""
    found = []
    for path in (HOME / ".config" / "cinnamon" / "spices").glob("*/*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        for item in data.values():
            if isinstance(item, dict) and item.get("type") == "keybinding":
                value = item.get("value", item.get("default", ""))
                if isinstance(value, str):
                    found += [v for v in value.split("::") if v]
    return found


def cmd_install_shortcut(home: str) -> int:
    wanted = notes.setting("kisayol")
    used = bindings_in_use()
    chosen = next((a for a in (wanted, FALLBACK) if norm_accel(a) and norm_accel(a) not in used), None)
    if chosen is None:
        print(f"• {pretty(wanted)} ve {pretty(FALLBACK)} başka işlere atanmış; kısayol eklenmedi.")
        print("  theme.toml içindeki [not-kutusu] kisayol değerini değiştirip yeniden kur.")
        return 1
    base = f"{KEYS}/custom-keybindings/{SHORTCUT_ID}"
    dconf_write(f"{base}/name", gv_str("Bandanix hızlı not"))
    dconf_write(f"{base}/command", gv_str(f"{home}/.local/bin/bandanix-not"))
    dconf_write(f"{base}/binding", gv_list([chosen]))
    # Cinnamon re-reads custom shortcuts only when custom-list changes, so take ours
    # out and put it back; otherwise a changed key would not be picked up until relogin
    others = [i for i in parse_list(dconf_read(f"{KEYS}/custom-list")) if i != SHORTCUT_ID]
    dconf_write(f"{KEYS}/custom-list", gv_list(others or ["__dummy__"]))
    dconf_write(f"{KEYS}/custom-list", gv_list(others + [SHORTCUT_ID]))
    if chosen != wanted:
        print(f"• {pretty(wanted)} başka bir işe atanmış, onun yerine {pretty(chosen)} kullanılıyor.")
    print(f"• Kısayol: {pretty(chosen)}")
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
    if cmd == "_kisayol" and len(argv) == 2:
        return cmd_install_shortcut(argv[1])
    if cmd == "_dosya-yolu" and len(argv) == 1:
        print(notes.notes_path())
        return 0
    return cmd_add(" ".join(argv))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
