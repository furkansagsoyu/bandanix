#!/usr/bin/env python3
"""bandanix-sekme: the Bandanix new tab page and colour theme for Brave.

  bandanix-sekme             are the page and the theme loaded in Brave, which wallpaper it shows
  bandanix-sekme guncelle    take the colours from theme.toml and the current desktop wallpaper
  bandanix-sekme ac          open brave://extensions (to load or remove the extension)

The new tab page lives in ~/.local/share/bandanix/yeni-sekme/eklenti, the theme next to it in
.../yeni-sekme/tema (Brave does not allow a theme and a page in one extension). Brave reads its files from
there on every new tab, so writing a new background or ayar.js needs no reload.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

HOME = Path.home()
DATA = Path(os.environ.get("XDG_DATA_HOME") or HOME / ".local/share")
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config")
EXT = DATA / "bandanix" / "yeni-sekme" / "eklenti"
THEME_DIR = DATA / "bandanix" / "yeni-sekme" / "tema"
THEME = CONFIG / "bandanix" / "theme.toml"
WALLS = DATA / "backgrounds" / "bandanix"
URI_KEY = "/org/cinnamon/desktop/background/picture-uri"
BRAVE_DIRS = (CONFIG / "BraveSoftware" / "Brave-Browser",
              HOME / ".var/app/com.brave.Browser/config/BraveSoftware/Brave-Browser")
PICTURE_EXT = (".jpg", ".jpeg", ".png", ".webp")

USAGE = """Kullanım:
  bandanix-sekme             yeni sekme ve tema Brave'de yüklü mü, hangi duvar kağıdı görünüyor
  bandanix-sekme guncelle    renkleri theme.toml'dan, arka planı masaüstü duvar kağıdından al
  bandanix-sekme ac          Brave'de eklentiler sayfasını aç
  bandanix-sekme ac tema     Brave'de görünüm ayarlarını aç (temayı kaldırmak için)"""


def say(msg: str) -> None:
    print(f"• {msg}")


# ---- settings -----------------------------------------------------------------------------
def theme() -> dict:
    try:
        import tomllib
        data = tomllib.loads(THEME.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    colors = data.get("colors") if isinstance(data.get("colors"), dict) else {}
    fonts = data.get("fonts") if isinstance(data.get("fonts"), dict) else {}
    accent = colors.get("accent", "")
    font = fonts.get("ui", "")
    return {
        "accent": accent if isinstance(accent, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", accent) else "#C8102E",
        "font": font if isinstance(font, str) and re.fullmatch(r"[\w .-]{0,60}", font) else "",
    }


def background() -> Path | None:
    for f in sorted(EXT.glob("arka-plan.*")):
        if f.suffix.lower() in PICTURE_EXT:
            return f
    return None


def write_settings(source_name: str | None = None) -> None:
    t, bg = theme(), background()
    values = {
        "accent": t["accent"],
        "font": t["font"],
        # the version number makes Brave load a new picture instead of the cached one
        "arkaPlan": f"{bg.name}?v={int(bg.stat().st_mtime)}" if bg else "",
    }
    if source_name is None:
        source_name = read_settings().get("kaynak", "")
    values["kaynak"] = source_name
    text = ("// Written by bandanix-sekme (theme.toml colours and the current wallpaper).\n"
            f"window.BANDANIX = {json.dumps(values, ensure_ascii=False)};\n")
    tmp = EXT / ".ayar.js.yeni"
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(EXT / "ayar.js")


def read_settings() -> dict:
    try:
        text = (EXT / "ayar.js").read_text(encoding="utf-8")
        return json.loads(text[text.index("{"):text.rindex("}") + 1])
    except (OSError, ValueError):
        return {}


# ---- background ---------------------------------------------------------------------------
def desktop_wallpaper() -> Path | None:
    try:
        out = subprocess.run(["dconf", "read", URI_KEY], capture_output=True, text=True).stdout.strip()
    except OSError:
        return None
    uri = out.strip("'")
    if not uri.startswith("file://"):
        return None
    path = Path(unquote(uri[len("file://"):]))
    return path if path.is_file() and path.suffix.lower() in PICTURE_EXT else None


def set_background(source: Path) -> None:
    for old in EXT.glob("arka-plan.*"):
        old.unlink()
    suffix = ".jpg" if source.suffix.lower() == ".jpeg" else source.suffix.lower()
    shutil.copyfile(source, EXT / f"arka-plan{suffix}")
    write_settings(source.stem)


# ---- Brave --------------------------------------------------------------------------------
def loaded_in_brave(folder: Path = EXT) -> bool | None:
    """True if a Brave profile has this folder loaded (page or theme); None if Brave was never run."""
    seen = False
    for base in BRAVE_DIRS:
        if not base.is_dir():
            continue
        for prefs in list(base.glob("*/Secure Preferences")) + list(base.glob("*/Preferences")):
            seen = True
            try:
                data = json.loads(prefs.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            settings = (data.get("extensions") or {}).get("settings") or {}
            for ext in settings.values():
                if isinstance(ext, dict) and ext.get("path") == str(folder):
                    return True
    return False if seen else None


def brave_command() -> list[str] | None:
    for cmd in ("brave-browser", "brave", "brave-browser-stable"):
        if shutil.which(cmd):
            return [cmd]
    if shutil.which("flatpak") and subprocess.run(["flatpak", "info", "com.brave.Browser"],
                                                  capture_output=True).returncode == 0:
        return ["flatpak", "run", "com.brave.Browser"]
    return None


def open_extensions(page: str = "brave://extensions") -> bool:
    cmd = brave_command()
    if cmd is None:
        return False
    subprocess.Popen([*cmd, page], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
    return True


# ---- commands -----------------------------------------------------------------------------
def cmd_show() -> int:
    if not (EXT / "manifest.json").is_file():
        say("Yeni sekme kurulu değil. Bandanix klasöründe: ./install.sh yeni-sekme")
        return 1
    words = {True: "Brave'de yüklü", False: "Brave'de yüklü değil (bandanix-sekme ac)", None: "Brave hiç açılmamış"}
    print(f"Yeni sekme    {words[loaded_in_brave(EXT)]}")
    if (THEME_DIR / "manifest.json").is_file():
        print(f"Tema          {words[loaded_in_brave(THEME_DIR)]}")
    source = read_settings().get("kaynak") or "-"
    print(f"Arka plan     {source}")
    return 0


def cmd_update() -> int:
    if not (EXT / "manifest.json").is_file():
        say("Yeni sekme kurulu değil. Bandanix klasöründe: ./install.sh yeni-sekme")
        return 1
    wall = desktop_wallpaper()
    if wall is not None:
        set_background(wall)
        say(f"Yeni sekme arka planı: {wall.stem}")
    else:
        write_settings()
        say("Masaüstü duvar kağıdı okunamadı; arka plan değişmedi.")
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        return cmd_show()
    cmd = argv[0]
    if cmd == "guncelle" and len(argv) == 1:
        return cmd_update()
    if cmd == "ac" and len(argv) <= 2 and argv[1:] in ([], ["tema"]):
        if not open_extensions("brave://settings/appearance" if argv[1:] == ["tema"] else "brave://extensions"):
            say("Brave bulunamadı.")
            return 1
        return 0
    if cmd == "_durum" and len(argv) == 1:              # for install.sh
        print(json.dumps({"eklenti": str(EXT), "tema": str(THEME_DIR),
                          "eklenti_yuklu": loaded_in_brave(EXT), "tema_yuklu": loaded_in_brave(THEME_DIR),
                          "arka_plan": read_settings().get("kaynak", "")}, ensure_ascii=False))
        return 0
    if cmd == "_arka-plan" and len(argv) == 2:         # called by bandanix-duvar after a change
        source = Path(argv[1])
        if not (EXT / "manifest.json").is_file() or not source.is_file():
            return 1
        set_background(source)
        return 0
    helped = cmd in ("-h", "--help", "yardim")
    print(USAGE, file=sys.stdout if helped else sys.stderr)
    return 0 if helped else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
