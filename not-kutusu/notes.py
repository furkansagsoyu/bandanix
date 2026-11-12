"""Quick-notes file handling for the Bandanix note box (no GUI code here).

The notes live in one Markdown file, newest first:

    # Hızlı notlar

    ## 2026-11-08 20:50
    [ ] Bitirme danışmanına mail at

    ## 2026-11-08 20:45
    https://open-meteo.com

Anything the user writes by hand (text before the first note, odd lines) is kept as is.
"""
from __future__ import annotations

import datetime as dt
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

HOME = Path.home()
THEME = Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config") / "bandanix" / "theme.toml"
DRAFT = Path(os.environ.get("XDG_STATE_HOME") or HOME / ".local" / "state") / "bandanix" / "not-taslak.txt"

HEADER = "# Hızlı notlar"
STAMP_FMT = "%Y-%m-%d %H:%M"
HEADING_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s*$")
TODO_RE = re.compile(r"^(- )?\[( |x|X)\] ?")

DEFAULTS = {"dosya": "~/Notlar/hizli-notlar.md", "kisayol": "<Super>n"}


# ---- theme.toml -------------------------------------------------------------------------
def theme_value(section: str, key: str, default: str = "") -> str:
    current = ""
    try:
        lines = THEME.read_text(encoding="utf-8").splitlines()
    except OSError:
        return default
    for line in lines:
        s = line.strip()
        if s.startswith("["):
            current = s
        elif current == f"[{section}]":
            m = re.match(rf'^{re.escape(key)}\s*=\s*"([^"]*)"', s)
            if m:
                return m.group(1)
    return default


def setting(key: str) -> str:
    return theme_value("not-kutusu", key) or DEFAULTS[key]


def notes_path() -> Path:
    return Path(os.path.expanduser(setting("dosya")))


def accent() -> str:
    value = theme_value("colors", "accent", "#C8102E")
    return value if re.fullmatch(r"#[0-9A-Fa-f]{6}", value) else "#C8102E"


# ---- parsing ----------------------------------------------------------------------------
@dataclass
class Note:
    stamp: str          # "2026-11-08 20:50" exactly as in the file
    body: str           # text without the heading, surrounding blank lines removed

    @property
    def when(self) -> dt.datetime | None:
        try:
            return dt.datetime.strptime(self.stamp, STAMP_FMT)
        except ValueError:
            return None

    @property
    def todo(self) -> bool | None:
        """None = plain note, False = open task, True = done task."""
        m = TODO_RE.match(self.body)
        return None if not m else m.group(2) != " "

    @property
    def text(self) -> str:
        """Body without the task marker (what gets copied)."""
        return TODO_RE.sub("", self.body, count=1) if self.todo is not None else self.body

    @property
    def title(self) -> str:
        lines = self.text.splitlines() or [""]
        first = lines[0].strip()
        return first + (" …" if len(lines) > 1 else "")


def _blocks(lines: list[str]) -> list[tuple[int, int]]:
    """(heading index, end index) for each note, in file order."""
    starts = [i for i, line in enumerate(lines) if HEADING_RE.match(line)]
    return [(s, starts[n + 1] if n + 1 < len(starts) else len(lines)) for n, s in enumerate(starts)]


def _body(lines: list[str], start: int, end: int) -> str:
    return "\n".join(lines[start + 1:end]).strip("\n").rstrip()


def parse(text: str) -> list[Note]:
    lines = text.splitlines()
    return [Note(HEADING_RE.match(lines[s]).group(1), _body(lines, s, e)) for s, e in _blocks(lines)]


def read_notes(path: Path) -> list[Note]:
    try:
        return parse(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return []


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".hizli-not-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


# ---- changes ----------------------------------------------------------------------------
def clean(text: str) -> str:
    """Normalise a new note; a heading-looking line is indented so it can't split the note."""
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    lines = [(" " + line) if HEADING_RE.match(line) else line for line in lines]
    return "\n".join(lines).strip("\n")


def add(path: Path, text: str, now: dt.datetime | None = None) -> Note | None:
    body = clean(text)
    if not body.strip():
        return None
    stamp = (now or dt.datetime.now()).strftime(STAMP_FMT)
    try:
        old = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        old = HEADER + "\n"
    lines = old.splitlines()
    blocks = _blocks(lines)
    insert = blocks[0][0] if blocks else len(lines)
    head = lines[:insert]
    while head and not head[-1].strip():
        head.pop()
    new = head + ([""] if head else []) + [f"## {stamp}", body, ""] + lines[insert:]
    _write(path, "\n".join(new).rstrip("\n") + "\n")
    return Note(stamp, body)


def toggle(path: Path, note: Note, *, include_plain: bool = False) -> bool:
    """Toggle a task, optionally turning a plain note into a completed task."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    for s, e in _blocks(lines):
        if HEADING_RE.match(lines[s]).group(1) != note.stamp or _body(lines, s, e) != note.body:
            continue
        for i in range(s + 1, e):
            if lines[i].strip():
                m = TODO_RE.match(lines[i])
                if m:
                    mark = " " if m.group(2) != " " else "x"
                    lines[i] = lines[i][:m.start(2)] + mark + lines[i][m.end(2):]
                elif include_plain:
                    lines[i] = "[x] " + lines[i]
                else:
                    return False
                _write(path, "\n".join(lines) + "\n")
                return True
        return False
    return False


def delete(path: Path, note: Note) -> bool:
    """Remove the matching note block and preserve the surrounding Markdown."""
    try:
        with path.open(encoding="utf-8", newline="") as file:
            original = file.read()
    except OSError:
        return False
    lines = original.splitlines()
    for start, end in _blocks(lines):
        if HEADING_RE.match(lines[start]).group(1) == note.stamp and _body(lines, start, end) == note.body:
            raw = original.splitlines(keepends=True)
            _write(path, "".join(raw[:start] + raw[end:]))
            return True
    return False


# ---- draft ------------------------------------------------------------------------------
def load_draft() -> str:
    try:
        return DRAFT.read_text(encoding="utf-8")
    except OSError:
        return ""


def save_draft(text: str) -> None:
    if text.strip():
        DRAFT.parent.mkdir(parents=True, exist_ok=True)
        DRAFT.write_text(text, encoding="utf-8")
    else:
        DRAFT.unlink(missing_ok=True)


# ---- relative time ----------------------------------------------------------------------
DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
MONTHS = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]


def ago(when: dt.datetime | None, now: dt.datetime | None = None) -> str:
    if when is None:
        return ""
    now = now or dt.datetime.now()
    minutes = int((now - when).total_seconds() // 60)
    if 0 <= minutes < 1:
        return "az önce"
    if 0 <= minutes < 60:
        return f"{minutes} dk önce"
    days = (now.date() - when.date()).days
    hm = when.strftime("%H:%M")
    if days == 0:
        return f"bugün {hm}"
    if days == 1:
        return f"dün {hm}"
    if 1 < days < 7:
        return f"{DAYS[when.weekday()]} {hm}"
    if when.year == now.year:
        return f"{when.day} {MONTHS[when.month - 1]} {hm}"
    return f"{when.day} {MONTHS[when.month - 1]} {when.year}"
