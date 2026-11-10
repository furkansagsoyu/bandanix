#!/usr/bin/env python3
"""Lock screen settings for the Bandanix look: the clock like the Brave new tab page
(big light time, "Salı, 10 Kasım" under it), fixed instead of wandering, media controls on.

  kilit_ekrani.py anahtarlar   the dconf keys this changes (for bandanix-yedek)
  kilit_ekrani.py uygula       write them (font from theme.toml [fonts] ui, else Ubuntu)
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

BASE = "/org/cinnamon/desktop/screensaver"
THEME = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "bandanix" / "theme.toml"


def font_family() -> str:
    try:
        import tomllib
        name = tomllib.loads(THEME.read_text(encoding="utf-8")).get("fonts", {}).get("ui", "")
    except Exception:
        name = ""
    return name if isinstance(name, str) and re.fullmatch(r"[\w .-]{1,60}", name) else "Ubuntu"


def values() -> dict[str, str]:
    family = font_family()
    return {
        "use-custom-format": "true",
        "time-format": "'%H:%M'",
        "date-format": "'%A, %-d %B'",            # Salı, 10 Kasım (in the session's language)
        "font-time": f"'{family} Light 72'",
        "font-date": f"'{family} 20'",
        "font-message": f"'{family} 14'",
        "floating-widgets": "false",
        "allow-media-control": "true",
        "show-album-art": "true",
    }


def main(argv: list[str]) -> int:
    if argv == ["anahtarlar"]:
        print("\n".join(f"dconf:{BASE}/{k}" for k in values()))
        return 0
    if argv == ["uygula"]:
        for key, value in values().items():
            subprocess.run(["dconf", "write", f"{BASE}/{key}", value], check=True)
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
