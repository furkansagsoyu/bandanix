#!/usr/bin/env python3
"""bandanix-duvar: choose a Bandanix wallpaper.

  bandanix-duvar             list the wallpapers (the current one is marked)
  bandanix-duvar galata      use that wallpaper (the choice is kept in theme.toml)
  bandanix-duvar uygula      apply the wallpaper saved in theme.toml

The pictures live in ~/.local/share/backgrounds/bandanix with a liste.txt naming them,
so adding a wallpaper is one file and one line.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
WALLS = Path(os.environ.get("XDG_DATA_HOME") or HOME / ".local/share") / "backgrounds" / "bandanix"
THEME = Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config") / "bandanix" / "theme.toml"
URI_KEY = "/org/cinnamon/desktop/background/picture-uri"
OPTIONS_KEY = "/org/cinnamon/desktop/background/picture-options"
SECTION = "[duvar-kagidi]"
STYLE_RE = re.compile(r'^\s*stil\s*=\s*"([a-z0-9-]+)"')

USAGE = """Kullanım:
  bandanix-duvar             duvar kağıtlarını listele
  bandanix-duvar galata      o duvar kağıdını kullan
  bandanix-duvar uygula      theme.toml'daki seçimi uygula"""


def say(msg: str) -> None:
    print(f"• {msg}")


# ---- the list -----------------------------------------------------------------------------
def wallpapers(folder: Path = WALLS) -> list[tuple[str, str, Path]]:
    """(id, display name, file) in the order of liste.txt; only pictures that exist."""
    out = []
    try:
        lines = (folder / "liste.txt").read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = []
    for line in lines:
        m = re.match(r"^\s*([a-z0-9-]+)\s*=\s*(.+?)\s*$", line)
        if not m:
            continue
        for ext in (".jpg", ".png", ".webp"):
            path = folder / f"{m.group(1)}{ext}"
            if path.is_file():
                out.append((m.group(1), m.group(2), path))
                break
    return out


# ---- theme.toml (read and minimal in-place edit, keeping the user's other lines) ----------
def read_style() -> str:
    section = ""
    try:
        lines = THEME.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    for line in lines:
        if line.strip().startswith("["):
            section = line.strip()
        elif section == SECTION:
            m = STYLE_RE.match(line)
            if m:
                return m.group(1)
    return ""


def write_style(style: str) -> None:
    text = THEME.read_text(encoding="utf-8") if THEME.is_file() else ""
    out, section, done = [], "", False
    for line in text.splitlines():
        if line.strip().startswith("["):
            if section == SECTION and not done:
                out.append(f'stil = "{style}"')
                done = True
            section = line.strip()
        elif section == SECTION and STYLE_RE.match(line):
            line = re.sub(r'"[a-z0-9-]+"', f'"{style}"', line, count=1)
            done = True
        out.append(line)
    if section == SECTION and not done:
        out.append(f'stil = "{style}"')
        done = True
    if not done:
        out += ["", SECTION, f'stil = "{style}"']
    THEME.parent.mkdir(parents=True, exist_ok=True)
    THEME.write_text("\n".join(out).strip("\n") + "\n", encoding="utf-8")


# ---- applying -----------------------------------------------------------------------------
def dconf_read(key: str) -> str:
    try:
        return subprocess.run(["dconf", "read", key], capture_output=True, text=True).stdout.strip()
    except OSError:
        return ""


def dconf_write(key: str, value: str) -> None:
    subprocess.run(["dconf", "write", key, value], check=True)


def current() -> str:
    """Id of the Bandanix wallpaper on the desktop right now ('' if it is something else)."""
    uri = dconf_read(URI_KEY).strip("'")
    prefix = f"file://{WALLS}/"
    if not uri.startswith(prefix):
        return ""
    return Path(uri[len(prefix):]).stem


def chosen() -> tuple[str, str, Path] | None:
    walls = wallpapers()
    style = read_style()
    return next((w for w in walls if w[0] == style), walls[0] if walls else None)


def apply(wall: tuple[str, str, Path]) -> None:
    dconf_write(URI_KEY, f"'file://{wall[2]}'")
    dconf_write(OPTIONS_KEY, "'zoom'")


def cmd_list() -> int:
    walls = wallpapers()
    if not walls:
        say("Duvar kağıdı bulunamadı. Bandanix klasöründe: ./install.sh duvar-kagidi")
        return 1
    now = current()
    for wid, name, _ in walls:
        mark = "●" if wid == now else " "
        print(f" {mark} {wid:<14}{name}")
    print()
    print("Değiştirmek için: bandanix-duvar <ad>   (ör. bandanix-duvar " + walls[0][0] + ")")
    return 0


def cmd_use(wid: str) -> int:
    walls = wallpapers()
    wall = next((w for w in walls if w[0] == wid), None)
    if wall is None:
        say(f"\"{wid}\" diye bir duvar kağıdı yok. Seçenekler: {', '.join(w[0] for w in walls)}")
        return 2
    write_style(wid)
    apply(wall)
    say(f"Duvar kağıdı: {wall[1]}")
    say("Giriş ekranını da buna uydurmak için: bandanix-giris guncelle")
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        return cmd_list()
    cmd = argv[0]
    if len(argv) > 1:
        print(USAGE, file=sys.stderr)
        return 2
    if cmd == "uygula":
        wall = chosen()
        if wall is None:
            say("Duvar kağıdı bulunamadı.")
            return 1
        apply(wall)
        say(f"Duvar kağıdı: {wall[1]}")
        return 0
    if cmd == "_json":                      # for the Bandanix settings app
        print(json.dumps([{"id": w[0], "ad": w[1], "dosya": str(w[2])} for w in wallpapers()],
                         ensure_ascii=False))
        return 0
    if cmd in ("-h", "--help", "yardim"):
        print(USAGE)
        return 0
    return cmd_use(cmd)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
