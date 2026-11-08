"""The watcher: a small Qt-free loop that reads the machine every 5 seconds and opens
the island only while something is wrong."""
from __future__ import annotations

import fcntl
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from bandanix_ada import tema

from . import olcum
from .kurallar import Rules, limits_from

INTERVAL = 5
RELAUNCH_AFTER = 300        # if the island was closed while the problem stays, wait this long

HOME = Path.home()
RUN = Path(os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()) / "bandanix"
STATE = RUN / "sistem-durum.json"
LOCK = RUN / "sistem-bekci.lock"
MUTE = Path(os.environ.get("XDG_STATE_HOME") or HOME / ".local" / "state") / "bandanix" / "sistem-sustur.json"
APP = Path(os.environ.get("XDG_DATA_HOME") or HOME / ".local" / "share") / "bandanix" / "sistem-adasi"
LAUNCHER = Path(os.environ.get("BANDANIX_SISTEM_ADA", str(APP / "ada-baslat")))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def read_json(path: Path, default):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, type(default)) else default
    except (OSError, ValueError):
        return default


# ---- muting (written by the island's right-click menu) --------------------------------
def load_mutes() -> dict:
    data = read_json(MUTE, {})
    until = data.get("kadar") if isinstance(data.get("kadar"), dict) else {}
    hidden = data.get("gizle") if isinstance(data.get("gizle"), list) else []
    return {"kadar": {k: v for k, v in until.items() if isinstance(v, (int, float))},
            "gizle": [k for k in hidden if isinstance(k, str)]}


def mute(kinds: list[str], seconds: float | None) -> None:
    """seconds=None: hide until these problems are over; else mute for that long."""
    data = load_mutes()
    if seconds is None:
        data["gizle"] = sorted(set(data["gizle"]) | set(kinds))
    else:
        until = time.time() + seconds
        for k in kinds:
            data["kadar"][k] = until
    write_json(MUTE, data)


def visible(problems: list[dict], now: float) -> list[dict]:
    """Drop muted problems; forget expired mutes and hides whose problem is gone."""
    data = load_mutes()
    active = {p["tur"] for p in problems}
    clean = {"kadar": {k: v for k, v in data["kadar"].items() if v > now},
             "gizle": [k for k in data["gizle"] if k in active]}
    if clean != data:
        write_json(MUTE, clean)
    return [p for p in problems if p["tur"] not in clean["kadar"] and p["tur"] not in clean["gizle"]]


# ---- the loop -------------------------------------------------------------------------
def sample(rules: Rules, now: float) -> dict:
    return rules.update(now, olcum.cpu_times(), olcum.temperature(), olcum.memory(), olcum.disks())


def limits() -> dict:
    return limits_from(tema.section(tema.load(), "sistem-adasi"))


def launch() -> subprocess.Popen | None:
    try:
        return subprocess.Popen([str(LAUNCHER)], stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                start_new_session=True)
    except OSError:
        return None


def run() -> int:
    RUN.mkdir(parents=True, exist_ok=True)
    lock = open(LOCK, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return 0                                   # another watcher is already running
    lock.write(str(os.getpid()))
    lock.flush()

    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    rules = Rules(limits())
    island = None
    launched_for, launched_at = None, 0.0
    try:
        while True:
            now = time.time()
            rules.limits = limits()
            state = sample(rules, now)
            state["gosterilen"] = visible(state["sorunlar"], now)
            write_json(STATE, state)
            if state["gosterilen"]:
                kinds = sorted(p["tur"] for p in state["gosterilen"])
                running = island is not None and island.poll() is None
                if not running and (kinds != launched_for or now - launched_at > RELAUNCH_AFTER):
                    island = launch()
                    launched_for, launched_at = kinds, now
            else:
                launched_for = None
            time.sleep(INTERVAL)
    finally:
        STATE.unlink(missing_ok=True)
