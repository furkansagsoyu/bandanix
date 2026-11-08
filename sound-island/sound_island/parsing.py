"""Pure parsing helpers (no Qt) so they can be unit-tested anywhere."""

from __future__ import annotations

import bisect
import re
from dataclasses import dataclass

# ASCII "unit separator": never appears in song titles, safe as a field delimiter.
SEP = "\x1f"

FOLLOW_FORMAT = SEP.join([
    "{{status}}",
    "{{title}}",
    "{{artist}}",
    "{{album}}",
    "{{mpris:artUrl}}",
    "{{mpris:length}}",
    "{{mpris:trackid}}",
])

# position is printed in microseconds (an integer), so it is locale-independent.
POLL_FORMAT = SEP.join(["{{status}}", "{{position}}"])


@dataclass(frozen=True)
class Track:
    track_id: str
    title: str
    artist: str
    album: str
    art_url: str
    length: float  # seconds


def _micro_to_seconds(raw: str) -> float | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        return int(float(raw.replace(",", "."))) / 1_000_000
    except ValueError:
        return None


def parse_metadata_line(line: str) -> tuple[str, Track | None]:
    """Parse one line of `playerctl metadata --follow --format FOLLOW_FORMAT`.

    Returns (status, track). track is None when nothing is playing
    (playerctl prints an empty line when the player disappears).
    """
    parts = line.rstrip("\r\n").split(SEP)
    if len(parts) != 7:
        return "", None
    status, title, artist, album, art, length, track_id = parts
    if not title.strip():
        return status, None
    seconds = _micro_to_seconds(length) or 0.0
    return status, Track(
        track_id=track_id or f"{artist}::{title}",
        title=title,
        artist=artist,
        album=album,
        art_url=art,
        length=seconds,
    )


def parse_poll_line(line: str) -> tuple[str, float | None]:
    """Parse `playerctl metadata --format POLL_FORMAT` -> (status, position seconds)."""
    parts = line.strip().split(SEP)
    if len(parts) != 2:
        return "", None
    return parts[0], _micro_to_seconds(parts[1])


_STAMP = re.compile(r"\[(\d+):(\d+(?:[.:]\d+)?)\]")


def parse_lrc(text: str) -> list[tuple[float, str]]:
    """Parse LRC synced lyrics into a sorted list of (seconds, line)."""
    out: list[tuple[float, str]] = []
    for raw in text.splitlines():
        stamps = _STAMP.findall(raw)
        if not stamps:
            continue
        lyric = _STAMP.sub("", raw).strip()
        for minutes, seconds in stamps:
            seconds = seconds.replace(":", ".")
            out.append((int(minutes) * 60 + float(seconds), lyric))
    out.sort(key=lambda item: item[0])
    return out


def line_at(times: list[float], lines: list[tuple[float, str]], pos: float) -> str:
    """Lyric line active at `pos` seconds ('' before the first line)."""
    if not lines:
        return ""
    i = bisect.bisect_right(times, pos) - 1
    return lines[i][1] if i >= 0 else ""


def pick_search_result(items, length: float) -> dict | None:
    """From an LRCLIB /api/search result, pick the best synced match."""
    if not isinstance(items, list):
        return None
    synced = [it for it in items if isinstance(it, dict) and it.get("syncedLyrics")]
    if not synced:
        return None
    if length > 0:
        close = [it for it in synced
                 if abs(float(it.get("duration") or 0) - length) <= 4]
        return close[0] if close else None
    return synced[0]


def fmt_time(seconds: float) -> str:
    s = max(0, int(seconds))
    return f"{s // 60}:{s % 60:02d}"
