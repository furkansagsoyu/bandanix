#!/usr/bin/env python3
"""Adds a Cinnamon custom keyboard shortcut for a Bandanix component (used by installers).

  bandanix_kisayol.py kur ID "Name" COMMAND WANTED FALLBACK
  bandanix_kisayol.py onar        (after an uninstall) make custom-list match the shortcuts

Picks WANTED (e.g. "<Super>v") unless Cinnamon, one of its custom shortcuts or an applet
already uses it; then FALLBACK; if both are taken it adds nothing and exits with 1.
The installer should mark the touched keys with `bandanix-yedek isaretle` first.
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
KEYS = "/org/cinnamon/desktop/keybindings"


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


def bindings_in_use(own_id: str) -> set:
    """Every accelerator Cinnamon already uses (defaults included), except own_id's."""
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
        elif section != f"custom-keybindings/{own_id}":
            texts.append(line)
    accels = [a for text in texts for a in re.findall(r"'(<[^']*)'", text)]
    accels += spice_bindings()
    return {n for n in map(norm_accel, accels) if n}


def install(own_id: str, name: str, command: str, wanted: str, fallback: str) -> int:
    used = bindings_in_use(own_id)
    chosen = next((a for a in (wanted, fallback) if norm_accel(a) and norm_accel(a) not in used), None)
    if chosen is None:
        print(f"• {pretty(wanted)} ve {pretty(fallback)} başka işlere atanmış; kısayol eklenmedi.")
        return 1
    base = f"{KEYS}/custom-keybindings/{own_id}"
    dconf_write(f"{base}/name", gv_str(name))
    dconf_write(f"{base}/command", gv_str(command))
    dconf_write(f"{base}/binding", gv_list([chosen]))
    # Cinnamon re-reads custom shortcuts only when custom-list changes, so take ours
    # out and put it back; otherwise a changed key would not be picked up until relogin
    others = [i for i in parse_list(dconf_read(f"{KEYS}/custom-list")) if i != own_id]
    dconf_write(f"{KEYS}/custom-list", gv_list(others or ["__dummy__"]))
    dconf_write(f"{KEYS}/custom-list", gv_list(others + [own_id]))
    if chosen != wanted:
        print(f"• {pretty(wanted)} başka bir işe atanmış, onun yerine {pretty(chosen)} kullanılıyor.")
    print(f"• Kısayol: {pretty(chosen)}")
    return 0


def marks(own_id: str) -> list[str]:
    """dconf keys an installer should hand to `bandanix-yedek isaretle`.

    custom-list itself is shared by every shortcut, so it is not restored from a backup
    (that would drop shortcuts added later); `onar` rebuilds it instead.
    """
    base = f"{KEYS}/custom-keybindings/{own_id}"
    return [f"dconf:{base}/name", f"dconf:{base}/command", f"dconf:{base}/binding"]


def repair() -> int:
    """custom-list = every custom shortcut that still has a command, in the current order."""
    try:
        dump = subprocess.run(["dconf", "dump", f"{KEYS}/custom-keybindings/"],
                              capture_output=True, text=True).stdout
    except OSError:
        return 1
    alive, section = [], ""
    for line in dump.splitlines():
        if line.startswith("["):
            section = line.strip("[]").strip("/")
        elif section and line.startswith("command=") and line.split("=", 1)[1].strip() not in ("", "''"):
            alive.append(section)
    current = parse_list(dconf_read(f"{KEYS}/custom-list"))
    wanted = [i for i in current if i in alive or i == "__dummy__"]
    wanted += [i for i in alive if i not in wanted]
    if wanted != current:
        dconf_write(f"{KEYS}/custom-list", gv_list(wanted or ["__dummy__"]))
    return 0


def main(argv: list[str]) -> int:
    if len(argv) == 6 and argv[0] == "kur":
        return install(*argv[1:])
    if len(argv) == 1 and argv[0] == "onar":
        return repair()
    if len(argv) == 2 and argv[0] == "isaretler":
        print("\n".join(marks(argv[1])))
        return 0
    print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
