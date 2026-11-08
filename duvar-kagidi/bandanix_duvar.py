#!/usr/bin/python3
"""bandanix-duvar: picks the Bandanix wallpaper for the chosen style and the time of day.

  bandanix-duvar gece|bandana|dalga|logo   choose a style (saved in theme.toml) and apply it
  bandanix-duvar uygula                    apply the saved style now
  bandanix-duvar guncelle                  run by the hourly timer; touches nothing if the
                                           current wallpaper isn't a Bandanix one
  bandanix-duvar ac | kapat                turn the time-of-day change on / off
  bandanix-duvar durum                     what is set right now
"""

from __future__ import annotations

import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path

STYLES = ("gece", "bandana", "dalga", "logo")
TIMER = "bandanix-duvar.timer"
HOME = Path.home()
WALLS = Path(os.environ.get("XDG_DATA_HOME") or HOME / ".local/share") / "backgrounds" / "bandanix"
THEME = Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config") / "bandanix" / "theme.toml"
URI_KEY = "/org/cinnamon/desktop/background/picture-uri"
OPT_KEY = "/org/cinnamon/desktop/background/picture-options"


def say(msg: str) -> None:
    print(f"• {msg}")


def time_of_day(hour: int) -> str:
    if 6 <= hour < 11:
        return "sabah"
    if 11 <= hour < 17:
        return "ogle"
    if 17 <= hour < 21:
        return "aksam"
    return "gece"


# ---- theme.toml (read and minimal in-place edit, keeping the user's other lines) ----
SECTION = "[duvar-kagidi]"
STYLE_RE = re.compile(r'^\s*stil\s*=\s*"([a-z]+)"')


def read_style() -> str:
    section = ""
    try:
        lines = THEME.read_text(encoding="utf-8").splitlines()
    except OSError:
        return "gece"
    for line in lines:
        if line.strip().startswith("["):
            section = line.strip()
        elif section == SECTION:
            m = STYLE_RE.match(line)
            if m and m.group(1) in STYLES:
                return m.group(1)
    return "gece"


def write_style(style: str) -> None:
    text = THEME.read_text(encoding="utf-8") if THEME.is_file() else ""
    lines = text.splitlines()
    out, section, done = [], "", False
    for line in lines:
        if line.strip().startswith("["):
            if section == SECTION and not done:      # section had no stil line
                out.append(f'stil = "{style}"')
                done = True
            section = line.strip()
        elif section == SECTION and STYLE_RE.match(line):
            line = re.sub(r'"[a-z]+"', f'"{style}"', line, count=1)
            done = True
        out.append(line)
    if section == SECTION and not done:
        out.append(f'stil = "{style}"')
        done = True
    if not done:
        out += ["", SECTION, f'stil = "{style}"            # gece, bandana, dalga ya da logo']
    THEME.parent.mkdir(parents=True, exist_ok=True)
    THEME.write_text("\n".join(out).rstrip("\n") + "\n", encoding="utf-8")


# ---- applying ---------------------------------------------------------------------
def dconf_read(key: str) -> str:
    try:
        return subprocess.run(["dconf", "read", key], capture_output=True, text=True).stdout.strip()
    except OSError:
        return ""


def dconf_write(key: str, value: str) -> None:
    subprocess.run(["dconf", "write", key, value], check=True)


def current_is_ours() -> bool:
    return dconf_read(URI_KEY).strip("'").startswith(f"file://{WALLS}/bandanix-")


def wanted_file(style: str, now: dt.datetime | None = None) -> Path:
    when = time_of_day((now or dt.datetime.now()).hour)
    return WALLS / f"bandanix-{style}-{when}.png"


def apply(style: str) -> Path:
    path = wanted_file(style)
    if not path.is_file():
        sys.exit(f"Duvar kağıdı bulunamadı: {path} (yeniden üretmek için: ./install.sh duvar-kagidi)")
    uri = f"'file://{path}'"
    if dconf_read(URI_KEY) != uri:
        dconf_write(URI_KEY, uri)
    if dconf_read(OPT_KEY) != "'zoom'":
        dconf_write(OPT_KEY, "'zoom'")
    return path


def timer(*args: str) -> int:
    try:
        return subprocess.run(["systemctl", "--user", *args, TIMER],
                              capture_output=True, text=True).returncode
    except OSError:
        return 1


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "durum"
    if cmd in STYLES:
        write_style(cmd)
        path = apply(cmd)
        say(f"Stil: {cmd} → {path.name}")
    elif cmd == "uygula":                             # apply the saved style now
        path = apply(read_style())
        say(f"Duvar kağıdı: {path.name}")
    elif cmd == "guncelle":
        if current_is_ours():                        # user picked something else: leave it
            apply(read_style())
    elif cmd == "ac":
        if timer("enable", "--now") == 0:
            apply(read_style())
            say("Günün saatine göre değişim açık.")
        else:
            say("Zamanlayıcı açılamadı (systemd kullanıcı oturumu yok mu?).")
    elif cmd == "kapat":
        timer("disable", "--now")
        say("Günün saatine göre değişim kapalı; şu anki duvar kağıdı sabit kalacak.")
    elif cmd == "durum":
        active = timer("is-active", "--quiet") == 0
        say(f"Stil: {read_style()} · zamana göre değişim: {'açık' if active else 'kapalı'}")
        say(f"Şu anki: {dconf_read(URI_KEY).strip(chr(39)) or '(yok)'}")
        if not current_is_ours():
            say("Şu an Bandanix dışı bir duvar kağıdı seçili; zamanlayıcı ona dokunmaz.")
    else:
        print(__doc__.strip())
        return 0 if cmd in ("-h", "--yardim", "yardim") else 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
