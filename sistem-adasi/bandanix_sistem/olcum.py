"""Reading the machine's state straight from /proc and /sys (no psutil, no Qt).

Set BANDANIX_SISTEM_KOK to a folder with fake proc/ and sys/ trees for tests.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(os.environ.get("BANDANIX_SISTEM_KOK", "/"))
PROC = ROOT / "proc"
SYS = ROOT / "sys"
TICKS = os.sysconf("SC_CLK_TCK") if hasattr(os, "sysconf") else 100
PAGE = os.sysconf("SC_PAGE_SIZE") if hasattr(os, "sysconf") else 4096


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


# ---- CPU -------------------------------------------------------------------------------
def cpu_times() -> tuple[int, int] | None:
    """(busy, total) jiffies since boot, from the first line of /proc/stat."""
    for line in _read(PROC / "stat").splitlines():
        if line.startswith("cpu "):
            nums = [int(x) for x in line.split()[1:] if x.isdigit()]
            if len(nums) < 4:
                return None
            idle = nums[3] + (nums[4] if len(nums) > 4 else 0)      # idle + iowait
            total = sum(nums[:8])                                    # guest is inside user
            return total - idle, total
    return None


def cpu_count() -> int:
    return max(1, sum(1 for line in _read(PROC / "stat").splitlines()
                      if re.match(r"^cpu\d+ ", line))) or 1


# ---- temperature -----------------------------------------------------------------------
CPU_SENSORS = ("coretemp", "k10temp", "zenpower", "cpu_thermal", "acpitz")


def temperature() -> float | None:
    """Hottest CPU sensor in °C (Intel package / AMD Tctl preferred), else hottest zone."""
    best: dict[str, float] = {}
    for hw in sorted((SYS / "class" / "hwmon").glob("hwmon*")):
        name = _read(hw / "name").strip()
        if name not in CPU_SENSORS:
            continue
        for inp in hw.glob("temp*_input"):
            raw = _read(inp).strip()
            if raw.lstrip("-").isdigit():
                value = int(raw) / 1000
                if 0 < value < 150:
                    best[name] = max(best.get(name, 0.0), value)
    for name in CPU_SENSORS:
        if name in best:
            return round(best[name], 1)
    zones = []
    for zone in (SYS / "class" / "thermal").glob("thermal_zone*"):
        raw = _read(zone / "temp").strip()
        if raw.lstrip("-").isdigit() and 0 < int(raw) / 1000 < 150:
            zones.append(int(raw) / 1000)
    return round(max(zones), 1) if zones else None


# ---- memory ----------------------------------------------------------------------------
def memory() -> tuple[int, int] | None:
    """(used, total) bytes; used = total - MemAvailable, like the system monitor."""
    info = {}
    for line in _read(PROC / "meminfo").splitlines():
        m = re.match(r"^(\w+):\s+(\d+)", line)
        if m:
            info[m.group(1)] = int(m.group(2)) * 1024
    total, avail = info.get("MemTotal"), info.get("MemAvailable")
    if not total or avail is None:
        return None
    return total - avail, total


# ---- disks -----------------------------------------------------------------------------
@dataclass
class Disk:
    path: str
    percent: float
    free: int


def disks(paths=("/", str(Path.home()))) -> list[Disk]:
    """Usage like `df`: used / (used + available to users). Each device once."""
    out, seen = [], set()
    for path in paths:
        try:
            st = os.statvfs(path)
            dev = os.stat(path).st_dev
        except OSError:
            continue
        if dev in seen or st.f_blocks == 0:
            continue
        seen.add(dev)
        used = (st.f_blocks - st.f_bfree) * st.f_frsize
        free = st.f_bavail * st.f_frsize
        out.append(Disk(path, round(used / (used + free) * 100, 1) if used + free else 0.0, free))
    return out


# ---- processes -------------------------------------------------------------------------
PROTECTED = {
    "cinnamon", "cinnamon-session", "cinnamon-launcher", "cinnamon-killer-daemon",
    "Xorg", "Xwayland", "systemd", "dbus-daemon", "dbus-broker", "pipewire",
    "pipewire-pulse", "wireplumber", "pulseaudio", "nemo-desktop", "gnome-keyring-d",
    "at-spi-bus-laun", "at-spi2-registr", "xdg-desktop-por", "xdg-document-po",
    "xdg-permission-", "gvfsd", "csd-power", "csd-media-keys", "lightdm",
}


INTERPRETERS = {"python", "python3", "node", "java", "bash", "sh", "perl", "ruby", "php"}


@dataclass
class Group:
    name: str
    pids: list[int] = field(default_factory=list)
    ticks: int = 0
    rss: int = 0
    mine: bool = True          # every process belongs to this user
    protected: bool = False


def processes() -> dict[str, Group]:
    """Processes grouped by name: cumulative CPU ticks and memory."""
    groups: dict[str, Group] = {}
    me, own = os.getuid(), os.getpid()
    for entry in PROC.iterdir() if PROC.is_dir() else []:
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        stat = _read(entry / "stat")
        close = stat.rfind(")")
        if close < 0 or pid == own:
            continue
        name = stat[stat.find("(") + 1:close]
        rest = stat[close + 2:].split()
        if len(rest) < 13:
            continue
        ticks = int(rest[11]) + int(rest[12])            # utime + stime
        statm = _read(entry / "statm").split()
        rss = int(statm[1]) * PAGE if len(statm) > 1 and statm[1].isdigit() else 0
        if rss == 0 and ticks == 0:
            continue                                      # kernel threads
        try:
            uid = entry.stat().st_uid
        except OSError:
            continue
        key = name
        if name in INTERPRETERS:
            # "python3" alone says nothing and grouping would close unrelated scripts
            args = [a for a in _read(entry / "cmdline").split("\0") if a]
            if any("bandanix_sistem" in a or "bandanix-sistem" in a for a in args):
                continue                                  # the island itself and its watcher
            script = next((a for a in args[1:] if not a.startswith("-")), "")
            key = f"{name} {Path(script).name}".strip() + f" #{pid}"
            name = f"{name} {Path(script).name}".strip()
        g = groups.setdefault(key, Group(name, protected=name in PROTECTED or name.startswith("csd-")))
        g.pids.append(pid)
        g.ticks += ticks
        g.rss += rss
        g.mine = g.mine and uid == me
    return groups


def cpu_usage(before: dict[str, Group], after: dict[str, Group], seconds: float,
              cpus: int) -> dict[str, float]:
    """Percent of the whole machine per group between two samples."""
    if seconds <= 0:
        return {}
    out = {}
    for name, g in after.items():
        prev = before.get(name)
        delta = g.ticks - (prev.ticks if prev else g.ticks)
        if delta > 0:
            out[name] = delta / TICKS / seconds / cpus * 100
    return out


# ---- formatting ------------------------------------------------------------------------
def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit in ("B", "KB", "MB") else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"
