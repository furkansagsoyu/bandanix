"""Shared colour helpers for the Bandanix theme and icon builders (standard library only)."""

from __future__ import annotations

import colorsys
import os
import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

DEFAULT_ACCENT = "#C8102E"
RGB = tuple[int, int, int]


def hex_to_rgb(value: str) -> RGB:
    v = value.lstrip("#")[:6]
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


def rgb_to_hex(rgb: RGB) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def hls(rgb: RGB) -> tuple[float, float, float]:
    return colorsys.rgb_to_hls(*(c / 255 for c in rgb))


def from_hls(h: float, l: float, s: float) -> RGB:
    r, g, b = colorsys.hls_to_rgb(h, max(0.0, min(1.0, l)), max(0.0, min(1.0, s)))
    return round(r * 255), round(g * 255), round(b * 255)


def is_accent(rgb: RGB) -> bool:
    """A red that belongs to the accent family (narrow band: orange warnings stay out)."""
    h, l, s = hls(rgb)
    return s >= 0.35 and 0.12 <= l <= 0.88 and (h <= 0.035 or h >= 0.95)


def is_neutral(rgb: RGB) -> bool:
    return hls(rgb)[2] < 0.15


def shift_accent(rgb: RGB, source_accent: RGB, target_accent: RGB) -> RGB:
    """Move a red from the source family to the target accent, keeping its lighter/darker step."""
    _, l, _ = hls(rgb)
    _, sl, _ = hls(source_accent)
    th, tl, ts = hls(target_accent)
    return from_hls(th, tl + (l - sl), ts)


def read_accent() -> str:
    """The accent colour from ~/.config/bandanix/theme.toml (bandana red if unset)."""
    path = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "bandanix" / "theme.toml"
    if tomllib and path.is_file():
        try:
            accent = tomllib.loads(path.read_text(encoding="utf-8")).get("colors", {}).get("accent")
            if isinstance(accent, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", accent):
                return accent
        except (OSError, ValueError):
            pass
    return DEFAULT_ACCENT
