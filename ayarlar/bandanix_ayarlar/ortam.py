"""Paths, theme.toml editing, the component list and backups (no GTK here, easy to test)."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
DATA = Path(os.environ.get("XDG_DATA_HOME") or HOME / ".local" / "share")
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config")
THEME = CONFIG / "bandanix" / "theme.toml"
CORE = DATA / "bandanix" / "core"
BIN = HOME / ".local" / "bin"
BANDANA_RED = "#C8102E"

NAMES = {
    "cinnamon-tema": "Cinnamon Teması", "duvar-kagidi": "Duvar Kağıtları", "giris-ekrani": "Giriş Ekranı",
    "ikonlar": "İkonlar ve İmleç", "not-kutusu": "Hızlı Not", "panel-duzeni": "Panel Düzeni",
    "pano": "Pano Geçmişi", "pil": "Pil Sağlığı", "sistem-adasi": "Sistem Adası",
    "sound-island": "Sound Island", "terminal": "Terminal", "widget": "Saat Widget'ı",
    "ayarlar": "Bandanix Ayarlar",
}
# used when the Bandanix folder can't be found (install.sh files hold the same "# kurulu:" lines)
MARKERS = {
    "cinnamon-tema": "~/.themes/Bandanix/gtk-3.0", "duvar-kagidi": "~/.local/bin/bandanix-duvar",
    "giris-ekrani": "~/.local/bin/bandanix-giris", "ikonlar": "~/.local/share/icons/Bandanix",
    "not-kutusu": "~/.local/bin/bandanix-not", "panel-duzeni": "~/.local/share/bandanix/panel-duzeni/aktif",
    "pano": "~/.local/bin/bandanix-pano", "pil": "~/.local/bin/bandanix-pil",
    "sistem-adasi": "~/.local/bin/bandanix-sistem", "sound-island": "~/.local/bin/sound-island",
    "terminal": "~/.local/bin/bandanix-fetch", "widget": "~/.local/bin/bandanix-widget",
    "ayarlar": "~/.local/bin/bandanix",
}


# ---- where the Bandanix folder is ------------------------------------------------------------
def is_repo(path: Path) -> bool:
    return (path / "install.sh").is_file() and (path / "core").is_dir() and (path / "scripts").is_dir()


def source() -> Path | None:
    """The Bandanix folder with the installers (remembered by ./install.sh)."""
    here = Path(__file__).resolve().parents[2]
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


# ---- components -----------------------------------------------------------------------------
def expand(path: str) -> Path:
    return Path(os.path.expanduser(path.strip()))


def components(src: Path | None = None) -> list[dict]:
    """[{id, ad, aciklama, kurulu}] for every component, in menu order."""
    src = source() if src is None else src
    out = []
    if src is not None:
        for d in sorted(src.iterdir()):
            script = d / "install.sh"
            if not (script.is_file() and os.access(script, os.X_OK)):
                continue
            desc, marker = "", MARKERS.get(d.name, "")
            for line in script.read_text(encoding="utf-8").splitlines()[:6]:
                if line.startswith("# description:"):
                    desc = line.split(":", 1)[1].strip()
                elif line.startswith("# kurulu:"):
                    marker = line.split(":", 1)[1].strip()
            out.append({"id": d.name, "ad": NAMES.get(d.name, d.name), "aciklama": desc,
                        "kurulu": bool(marker) and expand(marker).exists()})
    else:
        for cid, marker in MARKERS.items():
            out.append({"id": cid, "ad": NAMES.get(cid, cid), "aciklama": "",
                        "kurulu": expand(marker).exists()})
    return out


def installed(cid: str) -> bool:
    marker = MARKERS.get(cid)
    return bool(marker) and expand(marker).exists()


# ---- theme.toml -----------------------------------------------------------------------------
def load() -> dict:
    try:
        import tomllib
        data = tomllib.loads(THEME.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def get(section: str, key: str, default, data: dict | None = None):
    data = load() if data is None else data
    sec = data.get(section) if isinstance(data.get(section), dict) else {}
    value = sec.get(key, default)
    if isinstance(default, bool):
        return value if isinstance(value, bool) else default
    if isinstance(default, int):
        return value if isinstance(value, int) and not isinstance(value, bool) else default
    if isinstance(default, str):
        return value if isinstance(value, str) else default
    return value


def toml_value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
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
    path = path or THEME
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


def valid_hex(value: str) -> bool:
    return bool(re.fullmatch(r"#[0-9A-Fa-f]{6}", value or ""))


# ---- shortcuts --------------------------------------------------------------------------------
SHORTCUTS = {"not-kutusu": ("bandanix-not", "Hızlı not", "<Super>n"),
             "pano": ("bandanix-pano", "Pano geçmişi", "<Super>v")}


def core_module(name: str):
    """Import a helper from the installed core (or the Bandanix folder)."""
    for folder in (CORE, (source() or Path("/nonexistent")) / "core"):
        if (folder / f"{name}.py").is_file():
            if str(folder) not in sys.path:
                sys.path.insert(0, str(folder))
            try:
                return __import__(name)
            except Exception:
                return None
    return None


def pretty_accel(accel: str) -> str:
    names = {"primary": "Ctrl", "control": "Ctrl", "ctrl": "Ctrl", "super": "Super",
             "alt": "Alt", "shift": "Shift"}
    mods = [names.get(m.lower(), m) for m in re.findall(r"<(\w+)>", accel)]
    key = re.sub(r"<\w+>", "", accel)
    return "+".join(mods + [key.upper() if len(key) == 1 else key]) if key else "—"


def current_shortcut(own_id: str) -> str:
    try:
        out = subprocess.run(["dconf", "read", f"/org/cinnamon/desktop/keybindings/custom-keybindings/{own_id}/binding"],
                             capture_output=True, text=True).stdout
    except OSError:
        return ""
    found = re.findall(r"'([^']*)'", out)
    return found[0] if found else ""


# ---- backups ----------------------------------------------------------------------------------
def backups() -> list[dict]:
    yedek = core_module("bandanix_yedek")
    if yedek is None:
        return []
    out = []
    try:
        for b in yedek.all_backups():
            out.append({"no": b.no, "tarih": f"{b.when:%d.%m.%Y %H:%M}",
                        "tur": yedek.TYPE_LABEL.get(b.kind, b.kind), "not": b.info.get("not", "")})
    except Exception:
        return []
    return out
