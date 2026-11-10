"""Writing to ~/.config/bandanix/theme.toml, shared by every Bandanix component.

set_values() changes only the given keys: other lines, their order and the comments
after values stay exactly as the user left them.
"""
from __future__ import annotations

import os
import re
from pathlib import Path


def theme_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "bandanix" / "theme.toml"


def toml_value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".") if value != int(value) else f"{value:.1f}"
    if isinstance(value, int):
        return str(value)
    return '"' + str(value).replace("\\", "").replace('"', "") + '"'


def trailing_comment(line: str) -> str:
    """The '   # ...' part after a value (a '#' inside a quoted value does not count)."""
    value = line.split("=", 1)[1] if "=" in line else ""
    stripped = value.lstrip()
    start = len(value) - len(stripped)
    if stripped.startswith('"'):
        end = stripped.find('"', 1)
        start += end + 1 if end > 0 else len(stripped)
    else:
        token = re.match(r"[^\s#]*", stripped)
        start += token.end()
    hash_at = value.find("#", start)
    if hash_at < 0:
        return ""
    gap = value[start:hash_at]
    return (gap if gap.strip() == "" else "  ") + value[hash_at:].rstrip()


def set_values(section: str, values: dict, path: Path | None = None) -> None:
    """Set keys in [section], keeping every other line and the comments after values."""
    path = path or theme_path()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = []
    header = f"[{section}]"
    todo = dict(values)
    out, current = [], ""

    def flush():
        for k, v in todo.items():
            out.append(f"{k} = {toml_value(v)}")
        todo.clear()

    for line in lines:
        s = line.strip()
        if s.startswith("["):
            if current == header:
                trailing = []
                while out and not out[-1].strip():
                    trailing.append(out.pop())
                flush()
                out.extend(trailing or [""])
            current = s
        elif current == header:
            m = re.match(r"^\s*([A-Za-z0-9_-]+)\s*=", line)
            if m and m.group(1) in todo:
                line = f"{m.group(1)} = {toml_value(todo.pop(m.group(1)))}" + trailing_comment(line)
        out.append(line)
    if current == header:
        flush()
    if todo:
        if out and out[-1].strip():
            out.append("")
        out.append(header)
        flush()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out).strip("\n") + "\n", encoding="utf-8")
