"""Reads the shared Bandanix theme file. Works fine without it (defaults)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - older Pythons just use defaults
    tomllib = None

BANDANA_RED = "#C8102E"
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def default_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "bandanix" / "theme.toml"


@dataclass(frozen=True)
class Theme:
    accent: str = BANDANA_RED
    font: str = ""
    follow_cover: bool = True
    hide_when_idle: bool = True
    bars: str = "auto"          # "auto" = real audio via cava if installed, "simulated"


BAR_MODES = ("auto", "simulated")


def load_theme(path: Path | None = None) -> Theme:
    path = path or default_path()
    if tomllib is None or not path.is_file():
        return Theme()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Theme()

    defaults = Theme()
    colors = data.get("colors") if isinstance(data.get("colors"), dict) else {}
    fonts = data.get("fonts") if isinstance(data.get("fonts"), dict) else {}
    own = data.get("sound-island") if isinstance(data.get("sound-island"), dict) else {}

    accent = colors.get("accent")
    font = fonts.get("ui")
    follow = own.get("follow_cover")
    hide = own.get("hide_when_idle")
    bars = own.get("bars")
    return Theme(
        bars=bars if bars in BAR_MODES else defaults.bars,
        accent=accent if isinstance(accent, str) and _HEX.match(accent) else defaults.accent,
        font=font.strip() if isinstance(font, str) else defaults.font,
        follow_cover=follow if isinstance(follow, bool) else defaults.follow_cover,
        hide_when_idle=hide if isinstance(hide, bool) else defaults.hide_when_idle,
    )
