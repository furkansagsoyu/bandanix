"""Reads ~/.config/bandanix/theme.toml for the islands (accent, font, own section)."""
from __future__ import annotations

import os
import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

BANDANA_RED = "#C8102E"
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "bandanix" / "theme.toml"


def load() -> dict:
    if tomllib is None:
        return {}
    try:
        data = tomllib.loads(path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def section(data: dict, name: str) -> dict:
    value = data.get(name)
    return value if isinstance(value, dict) else {}


def accent(data: dict) -> str:
    value = section(data, "colors").get("accent")
    return value if isinstance(value, str) and _HEX.match(value) else BANDANA_RED


def font(data: dict) -> str:
    value = section(data, "fonts").get("ui")
    return value.strip() if isinstance(value, str) else ""
