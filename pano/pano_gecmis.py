"""Clipboard history storage for Bandanix (no GUI code here).

~/.local/share/bandanix/pano.json, readable only by the user:
    {"ogeler": [{"metin": "...", "zaman": 1762620000.0, "sabit": false}, ...]}   newest first
Every change is a locked read-modify-write, so the watcher and the list box never clash.
"""
from __future__ import annotations

import datetime as dt
import fcntl
import json
import os
import re
from contextlib import contextmanager
from pathlib import Path

HOME = Path.home()
DATA = Path(os.environ.get("XDG_DATA_HOME") or HOME / ".local" / "share") / "bandanix"
FILE = DATA / "pano.json"
LOCK = DATA / ".pano.lock"
THEME = Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config") / "bandanix" / "theme.toml"

LIMIT = 50                 # unpinned items kept
MAX_CHARS = 20_000         # longer copies are not stored
PASSWORD_HINT = "x-kde-passwordManagerHint"   # set by KeePassXC and other password managers


# ---- file -------------------------------------------------------------------------------
def _load() -> list[dict]:
    try:
        data = json.loads(FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    items = data.get("ogeler") if isinstance(data, dict) else None
    out = []
    for it in items if isinstance(items, list) else []:
        if isinstance(it, dict) and isinstance(it.get("metin"), str):
            out.append({"metin": it["metin"], "zaman": float(it.get("zaman") or 0),
                        "sabit": bool(it.get("sabit"))})
    return out


def _save(items: list[dict]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix(f".{os.getpid()}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump({"ogeler": items}, fh, ensure_ascii=False)
    os.chmod(tmp, 0o600)
    os.replace(tmp, FILE)


@contextmanager
def _locked():
    DATA.mkdir(parents=True, exist_ok=True)
    with open(LOCK, "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def items() -> list[dict]:
    """Pinned first (in their order), then the rest, newest first."""
    data = _load()
    return [i for i in data if i["sabit"]] + [i for i in data if not i["sabit"]]


# ---- changes ----------------------------------------------------------------------------
def acceptable(text: str | None, targets: list[str] = ()) -> bool:
    if not text or not text.strip() or len(text) > MAX_CHARS:
        return False
    return PASSWORD_HINT not in targets


def add(text: str, now: float) -> bool:
    """New copy on top; an existing identical text moves to the top (keeps its pin)."""
    if not acceptable(text):
        return False
    with _locked():
        data = _load()
        old = next((i for i in data if i["metin"] == text), None)
        data = [i for i in data if i["metin"] != text]
        data.insert(0, {"metin": text, "zaman": now, "sabit": bool(old and old["sabit"])})
        unpinned = [i for i in data if not i["sabit"]]
        drop = {id(i) for i in unpinned[LIMIT:]}
        _save([i for i in data if id(i) not in drop])
    return True


def _change(text: str, fn) -> bool:
    with _locked():
        data = _load()
        for n, it in enumerate(data):
            if it["metin"] == text:
                fn(data, n)
                _save(data)
                return True
    return False


def toggle_pin(text: str) -> bool:
    def flip(data, n):
        data[n]["sabit"] = not data[n]["sabit"]
    return _change(text, flip)


def delete(text: str) -> bool:
    return _change(text, lambda data, n: data.pop(n))


def clear() -> int:
    """Remove everything that is not pinned; returns how many went."""
    with _locked():
        data = _load()
        keep = [i for i in data if i["sabit"]]
        _save(keep)
    return len(data) - len(keep)


# ---- display helpers --------------------------------------------------------------------
def fold(s: str) -> str:
    """Case-insensitive matching that knows Turkish İ/ı."""
    return s.replace("İ", "i").replace("I", "ı").lower()


def matches(text: str, query: str) -> bool:
    return all(word in fold(text) for word in fold(query).split())


def title(text: str, width: int = 90) -> str:
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    first = re.sub(r"\s+", " ", lines[0]) if lines else ""
    if len(first) > width:
        first = first[:width - 1] + "…"
    return first + (" …" if len(lines) > 1 and not first.endswith("…") else "")


MONTHS = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]


def ago(stamp: float, now: float) -> str:
    seconds = now - stamp
    if seconds < 60:
        return "az önce"
    if seconds < 3600:
        return f"{int(seconds // 60)} dk önce"
    when, today = dt.datetime.fromtimestamp(stamp), dt.datetime.fromtimestamp(now).date()
    days = (today - when.date()).days
    if days == 0:
        return f"bugün {when:%H:%M}"
    if days == 1:
        return f"dün {when:%H:%M}"
    return f"{when.day} {MONTHS[when.month - 1]}"


TERMINALS = {"gnome-terminal", "gnome-terminal-server", "xfce4-terminal", "mate-terminal",
             "tilix", "terminator", "kitty", "alacritty", "konsole", "xterm", "uxterm",
             "urxvt", "st", "wezterm", "org.wezfurlong.wezterm", "foot", "guake", "tilda",
             "ptyxis", "blackbox", "com.raggesilver.blackbox", "kgx", "terminology"}


def paste_keys(window_class: str) -> str:
    """Ctrl+Shift+V for terminals, Ctrl+V everywhere else."""
    return "ctrl+shift+v" if window_class.strip().lower() in TERMINALS else "ctrl+v"


def setting(key: str, default: str) -> str:
    current = ""
    try:
        lines = THEME.read_text(encoding="utf-8").splitlines()
    except OSError:
        return default
    for line in lines:
        s = line.strip()
        if s.startswith("["):
            current = s
        elif current == "[pano]":
            m = re.match(rf'^{key}\s*=\s*"([^"]*)"', s)
            if m and m.group(1):
                return m.group(1)
    return default
