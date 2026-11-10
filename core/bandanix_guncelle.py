#!/usr/bin/env python3
"""Keeping an installed Bandanix up to date with its folder.

Every successful `./install.sh <part>` records a fingerprint of that part's files. Later, a part
whose files no longer match its fingerprint is "waiting for an update". `bandanix guncelle`
pulls from GitHub (only when the folder has no local changes) and reinstalls exactly those parts.

  bandanix_guncelle.py kaydet PART...     record the fingerprint (install.sh calls this)
  bandanix_guncelle.py sil PART...        forget it (uninstall.sh calls this)
  bandanix_guncelle.py durum [--fetch] [--json]
  bandanix_guncelle.py guncelle           what `bandanix guncelle` runs
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
DATA = Path(os.environ.get("XDG_DATA_HOME") or HOME / ".local" / "share")
STATE = DATA / "bandanix" / "kurulum"          # one file per part: its fingerprint
CORE_DEST = DATA / "bandanix" / "core"
SKIP_NAMES = {"tests", "__pycache__", "README.md", ".git"}
CORE = "core"                                   # the shared helpers are tracked like a part


def say(msg: str) -> None:
    print(f"• {msg}")


# ---- where the Bandanix folder is -------------------------------------------------------------
def is_repo(path: Path) -> bool:
    return (path / "install.sh").is_file() and (path / "core").is_dir() and (path / "scripts").is_dir()


def source() -> Path | None:
    here = Path(__file__).resolve().parent.parent
    if is_repo(here):
        return here
    try:
        saved = Path((DATA / "bandanix" / "kaynak").read_text(encoding="utf-8").strip())
    except OSError:
        saved = None
    if saved and is_repo(saved):
        return saved
    guess = HOME / "bandanix"
    return guess if is_repo(guess) else None


# ---- parts and fingerprints -----------------------------------------------------------------
def header(root: Path, part: str) -> dict:
    out = {}
    try:
        lines = (root / part / "install.sh").read_text(encoding="utf-8").splitlines()[:8]
    except OSError:
        return out
    for line in lines:
        for key in ("description", "kurulu", "yetki"):
            if line.startswith(f"# {key}:"):
                out[key] = line.split(":", 1)[1].strip()
    return out


def parts(root: Path) -> list[str]:
    return sorted(d.name for d in root.iterdir()
                  if (d / "install.sh").is_file() and os.access(d / "install.sh", os.X_OK))


def installed(root: Path, part: str) -> bool:
    marker = header(root, part).get("kurulu")
    return bool(marker) and Path(os.path.expanduser(marker)).exists()


def files_of(folder: Path):
    for path in sorted(folder.rglob("*")):
        rel = path.relative_to(folder)
        if any(p in SKIP_NAMES for p in rel.parts) or path.suffix == ".pyc" or not path.is_file():
            continue
        yield rel, path


def fingerprint(root: Path, part: str) -> str:
    """Hash of the files that end up installed: the part's folder (tests and README aside),
    plus the shared island library for parts whose installer uses it."""
    h = hashlib.sha256()
    folders = [root / part]
    if part != CORE:
        try:
            if "ortak/ada" in (root / part / "install.sh").read_text(encoding="utf-8"):
                folders.append(root / "ortak" / "ada")
        except OSError:
            pass
    for folder in folders:
        for rel, path in files_of(folder):
            h.update(f"{folder.name}/{rel}\0".encode())
            h.update(path.read_bytes())
            h.update(b"\0")
    return h.hexdigest()


def recorded(part: str) -> str | None:
    try:
        return (STATE / part).read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def record(root: Path, part: str) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / part).write_text(fingerprint(root, part) + "\n", encoding="utf-8")


def forget(part: str) -> None:
    try:
        (STATE / part).unlink()
    except OSError:
        pass


def pending(root: Path) -> dict:
    """{degisen: [installed parts whose files changed], kayitsiz: [installed, never recorded],
    core: shared helpers changed}"""
    changed, unknown = [], []
    for part in parts(root):
        if not installed(root, part):
            continue
        old = recorded(part)
        if old is None:
            unknown.append(part)
        elif old != fingerprint(root, part):
            changed.append(part)
    old_core = recorded(CORE)
    return {"degisen": changed, "kayitsiz": unknown,
            "core": old_core is not None and old_core != fingerprint(root, CORE)}


# ---- git ------------------------------------------------------------------------------------
def git(root: Path, *args: str, timeout: float = 30) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                              timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return subprocess.CompletedProcess(args, 1, "", str(e))


def git_state(root: Path, fetch: bool) -> dict:
    """{git: is a clone, kirli: local changes, geride: commits on GitHub not here (None = unknown)}"""
    if git(root, "rev-parse", "--is-inside-work-tree").stdout.strip() != "true":
        return {"git": False, "kirli": False, "geride": None}
    dirty = bool(git(root, "status", "--porcelain").stdout.strip())
    if fetch:
        git(root, "fetch", "-q", timeout=20)
    r = git(root, "rev-list", "--count", "HEAD..@{u}")
    behind = int(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip().isdigit() else None
    return {"git": True, "kirli": dirty, "geride": behind}


def status(root: Path, fetch: bool) -> dict:
    return {**git_state(root, fetch), **pending(root)}


# ---- commands -------------------------------------------------------------------------------
def copy_core(root: Path) -> None:
    CORE_DEST.mkdir(parents=True, exist_ok=True)
    for f in (root / "core").glob("*.py"):
        shutil.copyfile(f, CORE_DEST / f.name)
    record(root, CORE)


def cmd_update(root: Path) -> int:
    st = git_state(root, fetch=False)
    if not st["git"]:
        say("Bandanix klasörü bir git klasörü değil; GitHub'dan çekme atlandı.")
    elif st["kirli"]:
        say("Klasörde commit edilmemiş değişiklikler var; GitHub'dan çekme atlandı, yalnızca değişen parçalar kurulacak.")
    else:
        say("GitHub'dan güncellemeler alınıyor")
        r = git(root, "pull", "--ff-only", "-q", timeout=120)
        if r.returncode != 0:
            say("Çekilemedi: " + (r.stderr.strip().splitlines() or ["bilinmeyen hata"])[-1])
            say("Klasördeki hâliyle devam ediliyor.")

    p = pending(root)
    if p["kayitsiz"]:
        for part in p["kayitsiz"]:
            record(root, part)
        say("İlk kez çalıştı: " + ", ".join(p["kayitsiz"]) + " için kayıt alındı. "
            "Bunlar bundan sonraki değişikliklerde güncellenecek.")
    if p["core"] or recorded(CORE) is None:
        copy_core(root)
        if p["core"]:
            say("Ortak araçlar güncellendi.")
    if not p["degisen"]:
        say("Her şey güncel.")
        return 0
    say("Güncellenecek parçalar: " + ", ".join(p["degisen"]))
    return subprocess.call([str(root / "install.sh"), *p["degisen"]], cwd=root)


def main(argv: list[str]) -> int:
    root = source()
    if root is None:
        say("Bandanix klasörü bulunamadı (~/bandanix). Klasörde bir kez ./install.sh çalıştır.")
        return 1
    cmd, rest = (argv[0], argv[1:]) if argv else ("durum", [])
    if cmd == "kaydet" and rest:
        for part in rest:
            record(root, part)
        return 0
    if cmd == "sil" and rest:
        for part in rest:
            forget(part)
        return 0
    if cmd == "guncelle" and not rest:
        return cmd_update(root)
    if cmd == "durum" and set(rest) <= {"--fetch", "--json"}:
        st = status(root, "--fetch" in rest)
        if "--json" in rest:
            print(json.dumps(st, ensure_ascii=False))
            return 0
        if st["geride"]:
            print(f"GitHub'da {st['geride']} yeni değişiklik var.")
        if st["degisen"]:
            print("Güncellenmeyi bekleyen parçalar: " + ", ".join(st["degisen"]))
        if not st["geride"] and not st["degisen"] and not st["core"]:
            print("Her şey güncel.")
        return 0
    print(__doc__.split("\n\n", 2)[2].strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
